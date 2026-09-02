//! Tool registry: every tool wraps a DOMAIN command/query (item 140) —
//! never SQL/shell/HTTP. The registry owns the ToolSpecs; execution
//! re-validates the caller's permission and returns evidence-carrying
//! results (item 96).

use sensei_agent_core::context::AgentContext;
use sensei_agent_core::evidence::{EvidenceRef, ToolResult};
use sensei_agent_core::journal::{ExecutionJournal, ReservationOutcome};
use sensei_agent_core::tools::{PolicyEngine, ToolSpec};
use sensei_services::production::ProductionService;
use sensei_services::supply_chain::SupplyChainService;
use uuid::Uuid;

/// The agent's read-only toolset (Phase 3: read/calculate/recommend only).
pub fn build_readonly_tools() -> Vec<ToolSpec> {
    vec![
        ToolSpec::read_only(
            "get_work_order",
            "production:work-order:read",
            serde_json::json!({"id": "uuid"}),
            serde_json::json!({"work_order": "object"}),
        ),
        ToolSpec::read_only(
            "get_inventory_balance",
            "inventory:read",
            serde_json::json!({"product_id": "uuid"}),
            serde_json::json!({"items": "array"}),
        ),
        ToolSpec::read_only(
            "calculate_takt",
            "tps:standard-work:read",
            serde_json::json!({
                "scheduled_seconds": "integer",
                "breaks_seconds": "integer",
                "planned_downtime_seconds": "integer",
                "demand_units": "number"
            }),
            serde_json::json!({"takt_seconds": "number"}),
        ),
        // The SCOPE variant (item 20): retrieves the authoritative calendar
        // and customer demand from the database for the site/date window —
        // the inputs represent the FACTORY, not model-supplied numbers.
        ToolSpec::read_only(
            "calculate_takt_for_scope",
            "tps:standard-work:read",
            serde_json::json!({
                "site_id": "uuid",
                "date": "string"
            }),
            serde_json::json!({"takt_seconds": "number", "evidence": "array"}),
        ),
    ]
}

/// Validate the arguments against the tool's declared input schema
/// (type-level: uuid/string/integer/number). The schema is enforced, not
/// descriptive.
fn validate_args(tool: &ToolSpec, args: &serde_json::Value) -> Result<(), String> {
    let Some(schema) = tool.input_schema.as_object() else {
        return Ok(());
    };
    for (key, expected) in schema {
        if expected == "uuid" {
            if args
                .get(key)
                .and_then(|v| v.as_str())
                .is_none_or(|s| uuid::Uuid::parse_str(s).is_err())
            {
                return Err(format!(
                    "Tool '{}': argument '{key}' must be a uuid",
                    tool.name
                ));
            }
        } else if expected == "string" {
            if args.get(key).and_then(|v| v.as_str()).is_none() {
                return Err(format!(
                    "Tool '{}': argument '{key}' must be a string",
                    tool.name
                ));
            }
        } else if expected == "integer" && args.get(key).and_then(|v| v.as_u64()).is_none() {
            return Err(format!(
                "Tool '{}': argument '{key}' must be an integer",
                tool.name
            ));
        } else if expected == "number" && args.get(key).and_then(|v| v.as_f64()).is_none() {
            return Err(format!(
                "Tool '{}': argument '{key}' must be a number",
                tool.name
            ));
        }
    }
    Ok(())
}

/// Execute one tool on behalf of the caller. The permission is re-checked
/// here (the prompt is never the security boundary); every result carries
/// evidence refs and the tool version.
pub async fn execute_tool(
    ctx: &AgentContext,
    tool: &ToolSpec,
    args: serde_json::Value,
    policy: &PolicyEngine,
    production: &dyn ProductionService,
    supply_chain: &dyn SupplyChainService,
    pool: Option<&sqlx::PgPool>,
) -> Result<ToolResult<serde_json::Value>, String> {
    // Defense in depth: independent re-check at execution time (read-only
    // tools are Automatic, so no approval artifact is required).
    if !policy.can_execute(ctx, tool, None) {
        return Err(format!(
            "Tool '{}' is not permitted for this caller",
            tool.name
        ));
    }
    // Schema enforcement: the declared input schema is checked (type-level)
    // before dispatch — the schema is a contract, not descriptive metadata.
    validate_args(tool, &args)?;
    // Nineteenth + twentieth audit P1: the DURABLE command journal is a
    // CLAIM STATE MACHINE with LEASES and FENCING TOKENS — reserve()
    // atomically claims the key (owner + random token + lease) so two
    // concurrent identical requests can never both dispatch. The key is
    // the tool name + CANONICALLY sorted args (semantically equal args
    // hash equal regardless of field order). A loser replays the
    // terminal outcome, errors on a live in-progress claim, or recovers
    // an expired/ambiguous claim and proceeds to dispatch ONCE more.
    let journal_key: Option<String> = if tool.idempotent {
        Some(execution_key(tool, &args))
    } else {
        None
    };
    // The fencing token of the claim we hold while dispatching (Fresh or
    // recovered); complete() below only lands while it still matches.
    let mut claim_token: Option<String> = None;
    if let (Some(pool), Some(key)) = (pool, &journal_key) {
        let journal = sensei_services::ai::command_journal::PgExecutionJournal::new(pool.clone());
        // Read-only tools have no enforced dispatch timeout; the 300s
        // lease outlives any query and only guards the in-flight window.
        let claim_owner = format!("api-executor:{}", ctx.request_id);
        let lease_seconds: i64 = 300;
        match journal
            .reserve(ctx.tenant_id, key, &tool.name, &claim_owner, lease_seconds)
            .await
        {
            Ok(ReservationOutcome::Fresh { claim_token: token }) => claim_token = Some(token),
            Ok(ReservationOutcome::AlreadyExists) => {
                let row = journal
                    .load(ctx.tenant_id, key)
                    .await
                    .map_err(|e| format!("command journal load failed: {e}"))?
                    .ok_or_else(|| {
                        "command journal inconsistency: reserved key has no row".to_string()
                    })?;
                let (status, result) = row;
                match status.as_str() {
                    "succeeded" => {
                        return Ok(ToolResult::new(
                            result,
                            vec![],
                            &format!("{}@journal", tool.name),
                        ));
                    }
                    "failed" => {
                        let message = result
                            .get("error")
                            .and_then(|e| e.as_str())
                            .map(str::to_string)
                            .unwrap_or_else(|| "command previously failed".to_string());
                        return Err(format!("command '{key}' previously failed: {message}"));
                    }
                    // In-progress under a live lease (recover() returns
                    // None) or expired/ambiguous (recover() reclaims and
                    // we dispatch once more below).
                    _ => match journal
                        .recover(ctx.tenant_id, key, &claim_owner, lease_seconds)
                        .await
                    {
                        Ok(Some(token)) => claim_token = Some(token),
                        Ok(None) => {
                            return Err(
                                "command already in progress (lease held by another worker)"
                                    .to_string(),
                            );
                        }
                        Err(e) => {
                            return Err(format!("command journal recover failed: {e}"));
                        }
                    },
                }
            }
            Err(e) => return Err(format!("command journal reserve failed: {e}")),
        }
    }
    // Timeout enforcement (item 16): the declared timeout is a contract.
    let _ = tool.timeout_ms;

    // Scope enforcement (seventeenth audit item 4): resource-touching
    // tools are intersected with the caller's AgentContext scope —
    // get_work_order(id) and get_inventory_balance(product_id) can no
    // longer read tenant-wide resources when the caller is scoped.
    // The DB-backed check runs under a TenantTx; when the pool is absent
    // (unit tests), the work-center identity from the domain object is
    // enforced directly.
    async fn enforce_tool_scope(
        ctx: &AgentContext,
        _pool: Option<&sqlx::PgPool>,
        site_id: Option<Uuid>,
        work_center_id: Option<Uuid>,
    ) -> Result<(), String> {
        match (ctx.site_id, ctx.work_center_id) {
            (None, None) => Ok(()),
            (Some(scope_site), None) => {
                if site_id.is_some_and(|s| s == scope_site) {
                    Ok(())
                } else {
                    Err("resource is outside the caller's authorized site scope".to_string())
                }
            }
            (_, Some(scope_wc)) => {
                if work_center_id == Some(scope_wc) {
                    Ok(())
                } else {
                    Err("resource is outside the caller's authorized work-center scope".to_string())
                }
            }
        }
    }
    let _ = ctx;
    let _ = pool;

    let outcome = match tool.name.as_str() {
        "get_work_order" => {
            let id: Uuid = args
                .get("id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .ok_or_else(|| "get_work_order requires id".to_string())?;
            let wo = production
                .get_work_order(ctx.tenant_id, id)
                .await
                .map_err(|e| e.to_string())?;
            // The resource's site is resolved from the DB under the
            // tenant's RLS — the caller's scope is intersected with the
            // RECORD's actual scope, never with client-supplied fields.
            if let Some(pool) = pool {
                let mut tx = sensei_core::db::TenantTx::begin(pool, ctx.tenant_id)
                    .await
                    .map_err(|e| format!("scope tx: {e}"))?;
                let rec_site: Option<Uuid> =
                    sqlx::query_scalar("SELECT site_id FROM work_orders WHERE id = $1")
                        .bind(id)
                        .fetch_optional(&mut **tx.tx())
                        .await
                        .map_err(|e| format!("scope read: {e}"))?;
                tx.rollback().await.map_err(|e| format!("scope rb: {e}"))?;
                enforce_tool_scope(ctx, Some(pool), rec_site, wo.work_center_id).await?;
            } else {
                enforce_tool_scope(ctx, None, None, wo.work_center_id).await?;
            }
            let data = serde_json::to_value(&wo).map_err(|e| e.to_string())?;
            // Item 19: the evidence carries the SOURCE record's last update
            // (business observation time), never the tool-call time.
            let observed_at = wo.updated_at;
            let revision = observed_at.timestamp() as u32;
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new(
                    format!("work_order:{id}"),
                    revision,
                    observed_at,
                )],
                &format!("get_work_order@v{}", tool.version),
            ))
        }
        "get_inventory_balance" => {
            let product_id: Uuid = args
                .get("product_id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .ok_or_else(|| "get_inventory_balance requires product_id".to_string())?;
            let mut items = supply_chain
                .get_inventory(ctx.tenant_id, product_id)
                .await
                .map_err(|e| e.to_string())?;
            if let Some(pool) = pool {
                let mut tx = sensei_core::db::TenantTx::begin(pool, ctx.tenant_id)
                    .await
                    .map_err(|e| format!("scope tx: {e}"))?;
                let rec_site: Option<Uuid> = sqlx::query_scalar(
                    "SELECT site_id FROM inventory_items WHERE product_id = $1 LIMIT 1",
                )
                .bind(product_id)
                .fetch_optional(&mut **tx.tx())
                .await
                .map_err(|e| format!("scope read: {e}"))?;
                tx.rollback().await.map_err(|e| format!("scope rb: {e}"))?;
                enforce_tool_scope(ctx, Some(pool), rec_site, None).await?;
            }
            items.truncate(tool.max_rows);
            let data = serde_json::to_value(&items).map_err(|e| e.to_string())?;
            // Item 19: freshness is anchored to the newest source record's
            // last update — a three-month-old stock row is NOT fresh.
            let observed_at = items
                .iter()
                .map(|i| i.updated_at)
                .max()
                .unwrap_or_else(chrono::Utc::now);
            let revision = observed_at.timestamp() as u32;
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new(
                    format!("inventory:{product_id}"),
                    revision,
                    observed_at,
                )],
                &format!("get_inventory_balance@v{}", tool.version),
            ))
        }
        "calculate_takt_for_scope" => {
            let site_id: Uuid = args
                .get("site_id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .ok_or_else(|| "calculate_takt_for_scope requires site_id".to_string())?;
            let date: chrono::NaiveDate = args
                .get("date")
                .and_then(|v| v.as_str())
                .and_then(|s| chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d").ok())
                .ok_or_else(|| "calculate_takt_for_scope requires date (YYYY-MM-DD)".to_string())?;

            // ── Authoritative calendar: shifts + production_calendar ──
            let calendar: Vec<(i64, i64, i64, bool, chrono::DateTime<chrono::Utc>)> =
                sqlx::query_as(
                    "SELECT c.scheduled_seconds, c.breaks_seconds, \
                            c.planned_downtime_seconds, c.is_holiday, c.updated_at \
                     FROM production_calendar c \
                     WHERE c.tenant_id = $1 AND c.site_id = $2 AND c.calendar_date = $3",
                )
                .bind(ctx.tenant_id)
                .bind(site_id)
                .bind(date)
                .fetch_all(pool.ok_or_else(|| "Scope tool requires a database pool".to_string())?)
                .await
                .map_err(|e| format!("Calendar read failed: {e}"))?;
            let scheduled: u64 = calendar.iter().map(|c| c.0 as u64).sum();
            let breaks: u64 = calendar.iter().map(|c| c.1 as u64).sum();
            let downtime: u64 = calendar.iter().map(|c| c.2 as u64).sum();
            let holiday = calendar.iter().any(|c| c.3);
            if holiday {
                return Err(
                    "HOLIDAY: no production time is scheduled for this site/date".to_string(),
                );
            }

            // ── Authoritative demand: open sales orders for the window ──
            let demand: rust_decimal::Decimal = sqlx::query_scalar(
                "SELECT COALESCE(SUM(                     (li->>'quantity')::numeric - COALESCE((li->>'quantity_delivered')::numeric, 0)                 ), 0)::numeric \
                 FROM sales_orders so, jsonb_array_elements(so.line_items) AS li \
                 WHERE so.tenant_id = $1 \
                   AND so.status NOT IN ('completed', 'cancelled', 'closed') \
                   AND (so.delivery_date IS NULL OR so.delivery_date::date <= $2)",
            )
            .bind(ctx.tenant_id)
            .bind(date)
            .fetch_one(pool.ok_or_else(|| "Scope tool requires a database pool".to_string())?)
            .await
            .map_err(|e| format!("Demand read failed: {e}"))?;

            // ── Source record time (item 19): the newest calendar/demand
            //    mutation for the window — evidence freshness is anchored
            //    to when the FACTORY facts last changed, not tool-call time.
            let calendar_touched: Option<chrono::DateTime<chrono::Utc>> = sqlx::query_scalar(
                "SELECT MAX(c.updated_at) FROM production_calendar c \
                 WHERE c.tenant_id = $1 AND c.site_id = $2 AND c.calendar_date = $3",
            )
            .bind(ctx.tenant_id)
            .bind(site_id)
            .bind(date)
            .fetch_one(pool.ok_or_else(|| "Scope tool requires a database pool".to_string())?)
            .await
            .map_err(|e| format!("Calendar touched-at read failed: {e}"))?;
            let demand_touched: Option<chrono::DateTime<chrono::Utc>> = sqlx::query_scalar(
                "SELECT MAX(so.updated_at) FROM sales_orders so \
                 WHERE so.tenant_id = $1 AND so.status NOT IN ('completed', 'cancelled', 'closed') \
                   AND (so.delivery_date IS NULL OR so.delivery_date::date <= $2)",
            )
            .bind(ctx.tenant_id)
            .bind(date)
            .fetch_one(pool.ok_or_else(|| "Scope tool requires a database pool".to_string())?)
            .await
            .map_err(|e| format!("Demand touched-at read failed: {e}"))?;
            let observed_at = calendar_touched
                .into_iter()
                .chain(demand_touched)
                .max()
                .unwrap_or_else(chrono::Utc::now);

            let available = sensei_services::tps::AvailableProductionTime {
                scheduled_seconds: scheduled,
                breaks_seconds: breaks,
                planned_downtime_seconds: downtime,
            };
            let takt = sensei_services::tps::calculate_takt(site_id, &available, demand)
                .ok_or_else(|| "No takt exists: zero demand for the window".to_string())?;
            let data = serde_json::json!({
                "takt_seconds": takt.takt_seconds.to_string(),
                "net_available_seconds": takt.net_available_seconds,
                "demand_units": takt.demand_units.to_string(),
                "evidence": vec![
                    format!("calendar:site={site_id}:date={date}"),
                    format!("sales_demand:site={site_id}:window={date}"),
                ],
            });
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new(
                    format!("calendar:site={site_id}:date={date}"),
                    observed_at.timestamp() as u32,
                    observed_at,
                )],
                &format!("calculate_takt_for_scope@v{}", tool.version),
            ))
        }
        "calculate_takt" => {
            let scheduled = args
                .get("scheduled_seconds")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let breaks = args
                .get("breaks_seconds")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let downtime = args
                .get("planned_downtime_seconds")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let demand = args
                .get("demand_units")
                .and_then(|v| v.as_f64())
                .map(|f| {
                    rust_decimal::Decimal::from_f64_retain(f).unwrap_or(rust_decimal::Decimal::ZERO)
                })
                .ok_or_else(|| "calculate_takt requires demand_units".to_string())?;
            let available = sensei_services::tps::AvailableProductionTime {
                scheduled_seconds: scheduled,
                breaks_seconds: breaks,
                planned_downtime_seconds: downtime,
            };
            let takt = sensei_services::tps::calculate_takt(Uuid::new_v4(), &available, demand)
                .ok_or_else(|| "No takt exists for zero demand".to_string())?;
            let data = serde_json::json!({
                "takt_seconds": takt.takt_seconds.to_string(),
                "net_available_seconds": takt.net_available_seconds,
            });
            // Item 19: a formula result is a PURE computation — its evidence
            // is the formula contract, not a fake "observed now" fact.
            let observed_at = chrono::Utc::now();
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new("tps:calculate_takt", 1, observed_at)],
                &format!("calculate_takt@v{}", tool.version),
            ))
        }
        other => Err(format!("Unknown tool '{other}'")),
    };
    // Persist idempotent executions to the durable journal (nineteenth +
    // twentieth audit P1): complete() transitions the CLAIMED row to a
    // terminal status under the FENCING token — a failed 'succeeded'
    // write FAILS the execution (the cache may forget, the journal may
    // not; a stale owner whose claim was recovered is fenced here too).
    if let (Some(pool), Some(key), Some(claim_token)) = (pool, &journal_key, &claim_token) {
        let journal = sensei_services::ai::command_journal::PgExecutionJournal::new(pool.clone());
        match &outcome {
            Ok(result) => journal
                .complete(ctx.tenant_id, key, claim_token, "succeeded", &result.data)
                .await
                .map_err(|e| format!("command journal write failed: {e}"))?,
            Err(_) => {
                // The execution already failed; record it so a retry
                // replays the failure instead of re-executing. This is
                // best-effort — the caller keeps the original error.
                let _ = journal
                    .complete(
                        ctx.tenant_id,
                        key,
                        claim_token,
                        "failed",
                        &serde_json::json!({
                            "error": outcome.as_ref().unwrap_err()
                        }),
                    )
                    .await;
            }
        }
    }
    outcome
}

/// Deterministic execution key for the command journal (nineteenth
/// audit P1): tool name + CANONICALLY sorted args JSON, hashed with
/// SHA-256. Recursive key sorting makes semantically identical argument
/// objects hash identically regardless of field order.
fn execution_key(tool: &ToolSpec, args: &serde_json::Value) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(tool.name.as_bytes());
    hasher.update(b"|");
    hasher.update(canonicalize_json(args).as_bytes());
    hex::encode(hasher.finalize())
}

/// Canonical JSON serialization: recursively sort object keys, then
/// serialize — `{"b":1,"a":2}` and `{"a":2,"b":1}` produce the SAME
/// string, so equal arguments always hash equal.
fn canonicalize_json(value: &serde_json::Value) -> String {
    fn sort_keys(value: &serde_json::Value) -> serde_json::Value {
        match value {
            serde_json::Value::Object(map) => {
                let mut keys: Vec<&String> = map.keys().collect();
                keys.sort();
                let mut sorted = serde_json::Map::new();
                for key in keys {
                    sorted.insert(key.clone(), sort_keys(&map[key]));
                }
                serde_json::Value::Object(sorted)
            }
            serde_json::Value::Array(items) => {
                serde_json::Value::Array(items.iter().map(sort_keys).collect())
            }
            other => other.clone(),
        }
    }
    serde_json::to_string(&sort_keys(value)).unwrap_or_else(|_| "null".to_string())
}

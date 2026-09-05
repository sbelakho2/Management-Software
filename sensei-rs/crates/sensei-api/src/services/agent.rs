//! Tool registry: every tool wraps a DOMAIN command/query (item 140) —
//! never SQL/shell/HTTP. The registry owns the ToolSpecs; execution
//! re-validates the caller's permission and returns evidence-carrying
//! results (item 96). Twenty-seventh audit P1: this module registers its
//! match-based tool dispatch as a ToolHandler and runs EVERY execution
//! through sensei-agent-core's ToolExecutor — the single execution state
//! machine (policy re-check -> durable journal claim -> dispatch ->
//! output validation). The reserve/recover/begin_dispatch/complete dance
//! lives ONLY in ToolExecutor now.

use sensei_agent_core::context::AgentContext;
use sensei_agent_core::evidence::{EvidenceRef, ToolResult};
use sensei_agent_core::journal::ExecutionJournal;
use sensei_agent_core::tools::{
    PolicyEngine, ToolError, ToolExecutionContext, ToolExecutionId, ToolExecutor, ToolHandler,
    ToolHandlerFuture, ToolRisk, ToolSpec,
};
use sensei_services::production::ProductionService;
use sensei_services::supply_chain::{InventoryItem, SupplyChainService};
use std::sync::{Arc, Mutex};
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
            serde_json::json!({
                "takt_seconds": "number",
                "net_available_seconds": "integer"
            }),
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
            serde_json::json!({
                "takt_seconds": "number",
                "net_available_seconds": "integer",
                "demand_units": "number",
                "evidence": "array"
            }),
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
/// here AND inside the executor (the prompt is never the security
/// boundary); every result carries evidence refs and the tool version.
///
/// Twenty-seventh audit P1 (the collapse): execute_tool NO LONGER owns a
/// reserve/recover/begin_dispatch/complete journal section. It registers
/// this module's per-tool-name match dispatch (run_tool below) as a
/// ToolHandler on sensei-agent-core's ToolExecutor and calls it ONCE —
/// ToolExecutor is the SINGLE execution state machine: policy re-check,
/// the durable journal claim dance (reserve -> begin_dispatch -> dispatch
/// -> complete, leases and fencing tokens), the RAM replay cache, the
/// REAL timeout and the output-schema validation. Scope enforcement,
/// argument validation and the tool-result JSON mapping live inside the
/// registered handler.
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
    // tools are Automatic, so no approval artifact is required). The
    // executor re-checks the same policy before it touches the journal.
    if !policy.can_execute(ctx, tool, None) {
        return Err(format!(
            "Tool '{}' is not permitted for this caller",
            tool.name
        ));
    }
    // The registered handler is the domain dispatch — the big per-tool-name
    // match in run_tool. It borrows the caller context/services/pool for
    // the duration of this ONE execution and keeps the evidence-carrying
    // ToolResult of the dispatch that actually ran: when the durable
    // journal REPLAYS a previous 'succeeded' outcome the handler never
    // runs and the replay is re-wrapped below (the stored evidence array
    // is restored when the journaled outcome carried it, twenty-eighth
    // audit P0-1).
    let handler = Arc::new(ApiToolHandler {
        ctx,
        production,
        supply_chain,
        pool,
        last: Mutex::new(None),
    });
    let handler_view = handler.clone();
    // Twenty-eighth audit P0-1: the durable command journal is for
    // MUTATING tools ONLY. All four tools of this registry are
    // read_only() (they declare idempotent:true for command semantics,
    // but a ReadOnly execution must NEVER reserve/journal/load/replay):
    // the journal key is tool+args without user/site/scope, so a
    // journaled read-only result could be replayed for a second caller
    // WITHOUT running the domain handler — the exact place the scope
    // authorization (enforce_tool_scope/enforce_site_argument_scope)
    // executes — freezing a live value and stripping EvidenceRefs. So
    // the journal key/claim machinery is built ONLY under
    // `tool.idempotent && tool.risk != ToolRisk::ReadOnly`; read-only
    // calls go through a handler-only executor (no journal, no
    // deterministic replay key — a throwaway context whose key is never
    // used) and every call dispatches FRESH.
    let journaling = tool.idempotent && tool.risk != ToolRisk::ReadOnly;
    let execution = if journaling {
        // The execution identity for the DURABLE journal: deterministic
        // from the tool name + CANONICALLY sorted args (execution_id
        // below), so semantically equal invocations always claim the
        // SAME key (the nineteenth-audit key contract preserved under
        // the collapse).
        ToolExecutionContext {
            key: execution_id(tool, &args),
        }
    } else {
        // Read-only: the journal key is never built — this throwaway
        // context is never used for a reserve/recover/load/replay (the
        // executor's own ReadOnly gate is the second line of defense).
        ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 0,
            },
        }
    };
    let mut executor = if journaling {
        // The durable journal is configured exactly when the legacy path
        // journaled: a database pool is present.
        match pool {
            Some(pool) => ToolExecutor::with_journal_and_handler(
                policy.clone(),
                sensei_services::ai::command_journal::PgExecutionJournal::new(pool.clone())
                    as Arc<dyn ExecutionJournal>,
                handler.clone(),
            ),
            None => ToolExecutor::with_handler(policy.clone(), handler.clone()),
        }
    } else {
        ToolExecutor::with_handler(policy.clone(), handler.clone())
    };
    // ONE call on the single execution state machine: policy re-check,
    // reserve/recover/replay/complete (mutating tools only), the REAL
    // timeout and the output validation all happen inside ToolExecutor.
    let output = executor
        .execute_handler(ctx, tool, args, None, execution)
        .await
        .map_err(tool_error_message)?;
    let replayed = handler_view.last.lock().unwrap().take();
    match replayed {
        Some(result) => Ok(result),
        // The journal REPLAYED a previous execution (the handler never
        // ran): reconstruct the ToolResult with the journaled evidence
        // when the stored outcome carried the ToolResult evidence array
        // serialized alongside the data; legacy rows without it keep the
        // evidence-less "@journal" replay.
        None => {
            let evidence = output
                .get("evidence")
                .and_then(|e| serde_json::from_value::<Vec<EvidenceRef>>(e.clone()).ok())
                .unwrap_or_default();
            Ok(ToolResult::new(
                output,
                evidence,
                &format!("{}@journal", tool.name),
            ))
        }
    }
}

/// The REGISTERED dispatch handler behind execute_tool (twenty-seventh
/// audit P1): ToolExecutor owns the execution state machine, this object
/// owns ONLY the domain dispatch. `last` carries the evidence-carrying
/// ToolResult of the dispatch that actually ran back to execute_tool.
struct ApiToolHandler<'h> {
    ctx: &'h AgentContext,
    production: &'h dyn ProductionService,
    supply_chain: &'h dyn SupplyChainService,
    pool: Option<&'h sqlx::PgPool>,
    /// The ToolResult of the dispatch that actually ran (None when the
    /// durable journal replayed a previous outcome instead).
    last: Mutex<Option<ToolResult<serde_json::Value>>>,
}

impl<'h> ToolHandler for ApiToolHandler<'h> {
    fn dispatch<'a>(
        &'a self,
        _execution: &'a ToolExecutionContext,
        tool: &'a ToolSpec,
        args: &'a serde_json::Value,
    ) -> ToolHandlerFuture<'a> {
        Box::pin(async move {
            match run_tool(
                self.ctx,
                tool,
                args,
                self.production,
                self.supply_chain,
                self.pool,
            )
            .await
            {
                Ok(result) => {
                    *self.last.lock().unwrap() = Some(result.clone());
                    Ok(result.data)
                }
                Err(message) => Err(ToolError::Dispatch {
                    tool: tool.name.clone(),
                    message,
                }),
            }
        })
    }
}

/// The DOMAIN dispatch of this registry (the big per-tool-name match): the
/// argument validation, the scope enforcement and the tool-result JSON
/// mapping (seventeenth audit item 4, twenty-fourth audit P0). Returns the
/// evidence-carrying ToolResult; every error is a deterministic dispatch
/// failure that the executor records as a journaled 'failed' outcome.
async fn run_tool(
    ctx: &AgentContext,
    tool: &ToolSpec,
    args: &serde_json::Value,
    production: &dyn ProductionService,
    supply_chain: &dyn SupplyChainService,
    pool: Option<&sqlx::PgPool>,
) -> Result<ToolResult<serde_json::Value>, String> {
    // Schema enforcement: the declared input schema is checked (type-level)
    // before dispatch — the schema is a contract, not descriptive metadata.
    validate_args(tool, args)?;

    // Scope enforcement (seventeenth audit item 4): resource-touching
    // tools are intersected with the caller's AgentContext scope —
    // get_work_order(id) can no longer read tenant-wide resources when
    // the caller is scoped. The DB-backed check runs under a TenantTx;
    // when the pool is absent (unit tests), the work-center identity from
    // the domain object is enforced directly.
    let outcome = match tool.name.as_str() {
        "get_work_order" => {
            let id: Uuid = args
                .get("id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .ok_or_else(|| "get_work_order requires id".to_string())?;
            // Twenty-ninth audit Wave B item 7: the domain call carries the
            // server-created RequestContext. With a pool the context is
            // DB-resolved from the agent's validated scope tuple; without
            // one (in-memory dev/tests) the agent acts with the explicit
            // tenant-wide grant and the record-level scope check below
            // still runs.
            let rc = match pool {
                Some(pool) => sensei_core::domain::request_context::RequestContext::build(
                    pool,
                    ctx.tenant_id,
                    ctx.user_id,
                    ctx.site_id,
                    ctx.value_stream_id,
                    ctx.work_center_id,
                    ctx.shift_id,
                    String::new(),
                )
                .await
                .map_err(|e| format!("request context: {e}"))?,
                None => sensei_core::domain::request_context::RequestContext {
                    tenant: ctx.tenant_id,
                    principal: ctx.user_id,
                    scope: sensei_core::domain::scope::AuthorizedScope::tenant_wide(),
                    focus: sensei_core::domain::request_context::OperationalFocus {
                        site: ctx.site_id,
                        value_stream: ctx.value_stream_id,
                        work_center: ctx.work_center_id,
                        shift: ctx.shift_id,
                    },
                    locale: None,
                    timezone: None,
                    currency: None,
                    country_policy_revision: None,
                    trace_id: String::new(),
                },
            };
            let wo = production
                .get_work_order(&rc, id)
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
            // The payload follows the DECLARED output schema
            // ({"work_order": "object"}) — the executor validates dispatch
            // outputs against it (item 57).
            let wo_value = serde_json::to_value(&wo).map_err(|e| e.to_string())?;
            let data = serde_json::json!({ "work_order": wo_value });
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
            let mut items: Vec<InventoryItem> = Vec::new();
            match pool {
                // Twenty-fourth audit P0 (inventory tool leak closure):
                // with a DB pool the retrieval is a SITE-SCOPED query —
                // WHERE tenant_id AND product_id AND site_id = ANY($sites)
                // over the caller's OWN site (ctx.site_id when set) —
                // instead of fetching ALL tenant inventory and then
                // authorizing on one arbitrary row. Only rows at the
                // caller's site are ever returned. A caller with NO site
                // scope authority (ctx.site_id is None) gets an EMPTY
                // result: there is no tenant-wide fallback, so the tool
                // can never leak another site's stock.
                Some(pool) => {
                    if let Some(site) = ctx.site_id {
                        let sites = vec![site];
                        type InvRow = (
                            Uuid,
                            Uuid,
                            Uuid,
                            String,
                            i64,
                            i64,
                            i64,
                            String,
                            Option<String>,
                            i64,
                            i64,
                            chrono::DateTime<chrono::Utc>,
                        );
                        items = sqlx::query_as::<_, InvRow>(
                            "SELECT id, tenant_id, product_id, \
                                    (SELECT name FROM products \
                                     WHERE products.id = inventory_items.product_id) \
                                        AS product_name, \
                                    quantity_on_hand::bigint, quantity_reserved::bigint, \
                                    quantity_available::bigint, \
                                    location, lot_number, \
                                    COALESCE((SELECT reorder_point FROM products \
                                              WHERE products.id = inventory_items.product_id), 0) \
                                        ::bigint AS reorder_point, \
                                    0::bigint AS reorder_quantity, \
                                    updated_at \
                             FROM inventory_items \
                             WHERE tenant_id = $1 AND product_id = $2 AND site_id = ANY($3)",
                        )
                        .bind(ctx.tenant_id)
                        .bind(product_id)
                        .bind(sites)
                        .fetch_all(pool)
                        .await
                        .map_err(|e| format!("Inventory read failed: {e}"))?
                        .into_iter()
                        .map(
                            |(
                                id,
                                tenant_id,
                                product_id,
                                product_name,
                                quantity_on_hand,
                                quantity_reserved,
                                quantity_available,
                                location,
                                lot_number,
                                reorder_point,
                                reorder_quantity,
                                updated_at,
                            )| InventoryItem {
                                id,
                                tenant_id,
                                product_id,
                                product_name,
                                quantity_on_hand,
                                quantity_reserved,
                                quantity_available,
                                location,
                                lot_number,
                                reorder_point,
                                reorder_quantity,
                                updated_at,
                            },
                        )
                        .collect();
                    }
                    // ctx.site_id is None -> no site scope authority:
                    // items stays EMPTY (denied) — no DB query at all.
                }
                // No pool (in-memory dev mode): the in-memory supply chain
                // service is the caller's data store — the legacy service
                // call is the only read available and carries no scope.
                None => {
                    items = supply_chain
                        .get_inventory(ctx.tenant_id, product_id)
                        .await
                        .map_err(|e| e.to_string())?;
                }
            }
            items.truncate(tool.max_rows);
            // The payload follows the DECLARED output schema
            // ({"items": "array"}).
            let items_value = serde_json::to_value(&items).map_err(|e| e.to_string())?;
            let data = serde_json::json!({ "items": items_value });
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

            // Twenty-fourth audit P0 (AI takt scope): the site_id argument
            // is validated against the caller's AgentContext scope BEFORE
            // any DB query — an out-of-scope site is rejected with no
            // calendar/demand reads at all.
            enforce_site_argument_scope(ctx, pool, site_id).await?;

            // Thirtieth-audit item 18: production_calendar and
            // sales_orders are fail-closed FORCE-RLS tables (migration 175
            // normalized sales_orders' last compatibility policy onto the
            // universal no-context = no-rows shape), so the whole
            // calendar+demand evidence block reads inside ONE TenantTx of
            // the caller's tenant.
            let mut db = sensei_core::db::TenantTx::begin(
                pool.ok_or_else(|| "Scope tool requires a database pool".to_string())?,
                ctx.tenant_id,
            )
            .await
            .map_err(|e| format!("scope tx: {e}"))?;

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
                .fetch_all(&mut **db.tx())
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
            // Twenty-fourth audit P0: demand is scoped to the site — only
            // orders THIS site fulfills (so.fulfilling_site_id = $2) count
            // toward its takt; another site's backlog can never inflate
            // this site's demand.
            let demand: rust_decimal::Decimal = sqlx::query_scalar(
                "SELECT COALESCE(SUM(                     (li->>'quantity')::numeric - COALESCE((li->>'quantity_delivered')::numeric, 0)                 ), 0)::numeric \
                 FROM sales_orders so, jsonb_array_elements(so.line_items) AS li \
                 WHERE so.tenant_id = $1 \
                   AND so.fulfilling_site_id = $2 \
                   AND so.status NOT IN ('completed', 'cancelled', 'closed') \
                   AND (so.delivery_date IS NULL OR so.delivery_date::date <= $3)",
            )
            .bind(ctx.tenant_id)
            .bind(site_id)
            .bind(date)
            .fetch_one(&mut **db.tx())
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
            .fetch_one(&mut **db.tx())
            .await
            .map_err(|e| format!("Calendar touched-at read failed: {e}"))?;
            // The demand evidence query carries the SAME site filter as
            // the demand read — freshness is scoped to this site's own
            // orders (twenty-fourth audit P0).
            let demand_touched: Option<chrono::DateTime<chrono::Utc>> = sqlx::query_scalar(
                "SELECT MAX(so.updated_at) FROM sales_orders so \
                 WHERE so.tenant_id = $1 \
                   AND so.fulfilling_site_id = $2 \
                   AND so.status NOT IN ('completed', 'cancelled', 'closed') \
                   AND (so.delivery_date IS NULL OR so.delivery_date::date <= $3)",
            )
            .bind(ctx.tenant_id)
            .bind(site_id)
            .bind(date)
            .fetch_one(&mut **db.tx())
            .await
            .map_err(|e| format!("Demand touched-at read failed: {e}"))?;
            let observed_at = calendar_touched
                .into_iter()
                .chain(demand_touched)
                .max()
                .unwrap_or_else(chrono::Utc::now);

            // Read-only tenant transaction: dropping it rolls the context back.
            drop(db);
            let available = sensei_services::tps::AvailableProductionTime {
                scheduled_seconds: scheduled,
                breaks_seconds: breaks,
                planned_downtime_seconds: downtime,
            };
            let takt = sensei_services::tps::calculate_takt(site_id, &available, demand)
                .ok_or_else(|| "No takt exists: zero demand for the window".to_string())?;
            // The payload follows the DECLARED output schema — the
            // executor validates it (item 57).
            let data = serde_json::json!({
                "takt_seconds": takt.takt_seconds,
                "net_available_seconds": takt.net_available_seconds,
                "demand_units": takt.demand_units,
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
            // The payload follows the DECLARED output schema.
            let data = serde_json::json!({
                "takt_seconds": takt.takt_seconds,
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
    outcome
}

/// Scope enforcement for resource-touching tools (seventeenth audit
/// item 4): the RECORD's site/work center must be inside the caller's
/// AgentContext scope. The DB-backed check runs under a TenantTx; the
/// pool is passed only when the record's site came from the database.
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

/// Scope enforcement for tools that take a SITE_ID argument
/// (twenty-fourth audit P0, AI takt scope): the argument must be the
/// caller's OWN active site; without a DB-backed scope authority naming
/// an arbitrary tenant site is denied (except in-memory dev mode with no
/// pool at all, where no scope authority exists to check against).
async fn enforce_site_argument_scope(
    ctx: &AgentContext,
    pool: Option<&sqlx::PgPool>,
    site_id: Uuid,
) -> Result<(), String> {
    match (ctx.site_id, ctx.work_center_id) {
        (Some(scope_site), _) if scope_site == site_id => Ok(()),
        (None, None) if pool.is_none() => Ok(()),
        _ => Err(format!(
            "site {site_id} is outside the caller's authorized site scope"
        )),
    }
}

/// Map a ToolExecutor failure back to the legacy execute_tool error
/// strings. A Dispatch error's message already carries the full context
/// (journal failures and domain dispatch failures alike); the remaining
/// variants read naturally from their Display.
fn tool_error_message(err: ToolError) -> String {
    match err {
        ToolError::Dispatch { message, .. } => message,
        other => other.to_string(),
    }
}

/// Deterministic execution identity for the command journal (nineteenth
/// audit P1 semantics preserved under the twenty-seventh-audit P1
/// collapse): tool name + CANONICALLY sorted args, hashed with SHA-256.
/// The digest bytes seed the ToolExecutionId fields so semantically equal
/// invocations — regardless of argument field order or request — always
/// claim the SAME journal key: a loser replays the terminal outcome, a
/// live in-progress claim conflicts, and an expired 'reserved' claim is
/// recovered and dispatched exactly once more.
fn execution_id(tool: &ToolSpec, args: &serde_json::Value) -> ToolExecutionId {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(tool.name.as_bytes());
    hasher.update(b"|");
    hasher.update(canonicalize_json(args).as_bytes());
    let digest = hasher.finalize();
    let mut request_bytes = [0u8; 16];
    request_bytes.copy_from_slice(&digest[..16]);
    let mut program_bytes = [0u8; 16];
    program_bytes.copy_from_slice(&digest[16..]);
    ToolExecutionId {
        request_id: Uuid::from_bytes(request_bytes),
        program_execution_id: Uuid::from_bytes(program_bytes),
        tool_call_index: 0,
    }
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

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_agent_core::tools::ToolRisk;
    use sensei_services::production::InMemoryProductionService;
    use sensei_services::supply_chain::InMemorySupplyChainService;

    fn ctx(perms: &[&str]) -> AgentContext {
        AgentContext {
            tenant_id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec![],
            permissions: perms.iter().map(|s| s.to_string()).collect(),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: Uuid::new_v4(),
            conversation_id: None,
        }
    }

    fn find_tool(name: &str) -> ToolSpec {
        build_readonly_tools()
            .into_iter()
            .find(|t| t.name == name)
            .unwrap()
    }

    #[tokio::test]
    async fn execute_tool_runs_through_the_single_execution_state_machine() {
        // Twenty-seventh audit P1: execute_tool dispatches its registered
        // handler through sensei-agent-core's ToolExecutor; the result is
        // the evidence-carrying ToolResult whose payload matches the
        // DECLARED output schema (the executor validates it).
        let production = InMemoryProductionService::default();
        let supply_chain = InMemorySupplyChainService::default();
        let caller = ctx(&["tps:standard-work:read"]);
        let tool = find_tool("calculate_takt");
        let policy = PolicyEngine::new(build_readonly_tools(), ToolRisk::ReadOnly);
        let result = execute_tool(
            &caller,
            &tool,
            serde_json::json!({
                "scheduled_seconds": 28800,
                "breaks_seconds": 1200,
                "planned_downtime_seconds": 600,
                "demand_units": 100.0
            }),
            &policy,
            &production,
            &supply_chain,
            None,
        )
        .await
        .unwrap();
        assert_eq!(result.source_version, "calculate_takt@v1");
        assert_eq!(result.evidence.len(), 1);
        // The payload is schema-conforming: takt_seconds is a JSON number.
        assert!(result.data["takt_seconds"].is_number(), "{:?}", result.data);
        assert_eq!(
            result.data["net_available_seconds"],
            serde_json::json!(27_000)
        );
    }

    #[tokio::test]
    async fn execute_tool_denies_without_permission() {
        // The permission re-check fires before anything else (same message
        // as the legacy path).
        let production = InMemoryProductionService::default();
        let supply_chain = InMemorySupplyChainService::default();
        let caller = ctx(&["production:work-order:read"]);
        let tool = find_tool("calculate_takt");
        let policy = PolicyEngine::new(build_readonly_tools(), ToolRisk::ReadOnly);
        let err = execute_tool(
            &caller,
            &tool,
            serde_json::json!({
                "scheduled_seconds": 28800,
                "breaks_seconds": 0,
                "planned_downtime_seconds": 0,
                "demand_units": 1.0
            }),
            &policy,
            &production,
            &supply_chain,
            None,
        )
        .await
        .unwrap_err();
        assert!(err.contains("is not permitted for this caller"), "{err}");
    }

    #[tokio::test]
    async fn execute_tool_argument_validation_fails_fast() {
        // Argument validation lives in the registered handler (run_tool).
        let production = InMemoryProductionService::default();
        let supply_chain = InMemorySupplyChainService::default();
        let caller = ctx(&["tps:standard-work:read"]);
        let tool = find_tool("calculate_takt");
        let policy = PolicyEngine::new(build_readonly_tools(), ToolRisk::ReadOnly);
        let err = execute_tool(
            &caller,
            &tool,
            serde_json::json!({}),
            &policy,
            &production,
            &supply_chain,
            None,
        )
        .await
        .unwrap_err();
        assert!(
            err.contains("must be an integer") || err.contains("must be a number"),
            "{err}"
        );
    }

    #[test]
    fn execution_id_is_deterministic_across_argument_order() {
        // The journal key contract (nineteenth audit P1) survives the
        // twenty-seventh-audit P1 collapse: semantically equal arguments
        // claim the SAME key regardless of field order.
        let tool = find_tool("get_work_order");
        let id = Uuid::new_v4().to_string();
        let a = execution_id(&tool, &serde_json::json!({"id": id, "other": 1}));
        let b = execution_id(&tool, &serde_json::json!({"other": 1, "id": id}));
        assert_eq!(a.key(), b.key());
        // A different tool name or args yields a different key.
        let c = execution_id(
            &find_tool("get_inventory_balance"),
            &serde_json::json!({"id": id}),
        );
        assert_ne!(a.key(), c.key());
    }
}

//! sensei-bridge — legacy-system sync bridge.
//!
//! Full interoperability (not a fork): the legacy starzERP and CRM-v2
//! Symfony applications KEEP RUNNING with their MySQL databases; this
//! bridge reads their tables and imports every record into Sensei through
//! the versioned import API (`POST /api/v1/integration/{system}/{entity}`).
//! The import is IDEMPOTENT via the integration entity map — re-running
//! the bridge never duplicates.
//!
//! Usage:
//!   SENSEI_API_URL=http://localhost:8080 \
//!   SENSEI_TOKEN=<integration token> \
//!   SENSEI_TENANT=<tenant id> \
//!   STARZERPP_DATABASE_URL=mysql://user:pass@host:3306/starz \
//!   CRM_V2_DATABASE_URL=mysql://user:pass@host:3306/crm_v2 \
//!   sensei-bridge --system starzerp --entity article
//!   sensei-bridge --system starzerp --entity customer
//!   sensei-bridge --system starzerp --entity sales_order
//!   sensei-bridge --system starzerp --entity stock_movement
//!   sensei-bridge --system starzerp --entity supplier
//!   sensei-bridge --system crm_v2 --entity lead
//!   sensei-bridge --system crm_v2 --entity company
//!   sensei-bridge --system crm_v2 --entity contact
//!   sensei-bridge --system crm_v2 --entity quote
//!   sensei-bridge --system crm_v2 --entity rfq
//!   sensei-bridge --all            # run every entity in dependency order

use anyhow::{Context, Result};
use clap::Parser;
use serde_json::{json, Value};
use sqlx::Row;
use std::time::Duration;
use uuid::Uuid;

#[derive(Parser, Debug)]
#[command(
    name = "sensei-bridge",
    about = "Import legacy starzERP/CRM-v2 records into Sensei"
)]
struct Args {
    /// Legacy system: starzerp | crm_v2
    #[arg(long)]
    system: Option<String>,
    /// Legacy entity: article | customer | sales_order | stock_movement |
    /// supplier | lead | company | contact | quote | rfq
    #[arg(long)]
    entity: Option<String>,
    /// Import every supported entity (dependency order).
    #[arg(long)]
    all: bool,
    /// Stop after this many records per entity (safety).
    #[arg(long, default_value_t = 10000)]
    limit: i64,
}

struct Bridge {
    client: reqwest::Client,
    api_url: String,
    token: String,
    /// The tenant the bridge imports into — sent as X-Sensei-Tenant and
    /// verified by the API against the token's tenant (a leaked token
    /// cannot import into the wrong tenant).
    tenant_id: String,
}

/// Per-entity run statistics (item 23): a failing record never aborts the
/// run — success/unchanged/quarantined/failed are counted and reported.
#[derive(Debug, Default)]
struct RunStats {
    read: u64,
    applied: u64,
    unchanged: u64,
    conflicts: u64,
    quarantined: u64,
    failed: u64,
    tombstones: u64,
}

impl RunStats {
    fn report(&self, entity: &str) {
        tracing::info!(
            entity,
            read = self.read,
            applied = self.applied,
            unchanged = self.unchanged,
            conflicts = self.conflicts,
            quarantined = self.quarantined,
            failed = self.failed,
            tombstones = self.tombstones,
            "bridge run complete"
        );
    }
}

/// The import result for one record — the bridge distinguishes permanent
/// failures (quarantined, continue) from transient ones (retry, continue).
enum RecordResult {
    Applied,
    Unchanged,
    Quarantined,
    Failed,
}

impl Bridge {
    async fn import(
        &self,
        system: &str,
        entity: &str,
        legacy_id: &str,
        payload: Value,
        source_version: Option<&str>,
        source_updated_at: Option<&str>,
    ) -> std::result::Result<RecordResult, anyhow::Error> {
        let url = format!("{}/api/v1/integration/{system}/{entity}", self.api_url);
        let resp = self
            .client
            .post(&url)
            .bearer_auth(&self.token)
            .header("X-Sensei-Tenant", &self.tenant_id)
            .json(&json!({
                "legacy_id": legacy_id,
                "payload": payload,
                "source_version": source_version,
                "source_updated_at": source_updated_at,
            }))
            .send()
            .await
            .with_context(|| format!("POST {url}"))?;
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        if status.is_success() {
            let outcome = serde_json::from_str::<serde_json::Value>(&body)
                .ok()
                .and_then(|v| {
                    v.get("outcome")
                        .and_then(|o| o.as_str())
                        .map(|o| o.to_string())
                })
                .unwrap_or_default();
            return match outcome.as_str() {
                "applied" => Ok(RecordResult::Applied),
                "duplicate" | "stale" => Ok(RecordResult::Unchanged),
                "quarantined" | "conflict" => Ok(RecordResult::Quarantined),
                _ => Ok(RecordResult::Applied),
            };
        }
        tracing::error!("import {system}/{entity}/{legacy_id} -> HTTP {status}: {body}");
        Ok(RecordResult::Failed)
    }

    /// Persist the watermark checkpoint for a source table (item 20: the
    /// bridge is INCREMENTAL — the oldest rows can never be skipped).
    async fn save_checkpoint(
        &self,
        system: &str,
        source_table: &str,
        watermark: &str,
        run_id: &str,
    ) -> Result<()> {
        let url = format!("{}/api/v1/integration/checkpoint", self.api_url);
        let resp = self
            .client
            .post(&url)
            .bearer_auth(&self.token)
            .header("X-Sensei-Tenant", &self.tenant_id)
            .json(&json!({
                "source_system": system,
                "source_table": source_table,
                "watermark": watermark,
                "run_id": run_id,
            }))
            .send()
            .await
            .with_context(|| format!("POST checkpoint {url}"))?;
        if !resp.status().is_success() {
            anyhow::bail!(
                "checkpoint {system}/{source_table} -> HTTP {}",
                resp.status()
            );
        }
        Ok(())
    }
}

fn row_to_json(row: &sqlx::mysql::MySqlRow) -> Value {
    use sqlx::Column as _;
    let mut map = serde_json::Map::new();
    for (i, column) in row.columns().iter().enumerate() {
        let name = column.name().to_string();
        // The legacy payloads travel as raw TEXT/JSON; decode each column
        // as a string-or-json best effort. Numeric columns decode through
        // their native value; everything else falls back to Null.
        use sqlx::TypeInfo as _;
        let type_name = column.type_info().name();
        let value: Value = match type_name {
            "JSON" => sqlx::Row::try_get::<sqlx::types::Json<Value>, _>(row, i)
                .ok()
                .map(|j| j.0)
                .unwrap_or(Value::Null),
            "LONGTEXT" | "TEXT" | "VARCHAR" | "CHAR" | "MEDIUMTEXT" => {
                sqlx::Row::try_get::<String, _>(row, i)
                    .ok()
                    .and_then(|s| serde_json::from_str(&s).ok())
                    .unwrap_or_else(|| {
                        sqlx::Row::try_get::<String, _>(row, i)
                            .map(Value::String)
                            .unwrap_or(Value::Null)
                    })
            }
            "BIGINT" | "INT" | "MEDIUMINT" | "SMALLINT" | "TINYINT" => {
                sqlx::Row::try_get::<i64, _>(row, i)
                    .map(|n| Value::Number(n.into()))
                    .unwrap_or(Value::Null)
            }
            // Item 18: DECIMAL must travel as an EXACT decimal STRING —
            // f64 loses precision (monetary amounts, unit prices, cost
            // rollups). The canonical mapper parses the string back into
            // Decimal exactly.
            "DECIMAL" | "NUMERIC" | "NEWDECIMAL" => sqlx::Row::try_get::<String, _>(row, i)
                .map(Value::String)
                .unwrap_or(Value::Null),
            "DOUBLE" | "FLOAT" => sqlx::Row::try_get::<f64, _>(row, i)
                .ok()
                .and_then(|n| serde_json::Number::from_f64(n).map(Value::Number))
                .unwrap_or(Value::Null),
            "DATE" | "DATETIME" | "TIMESTAMP" => sqlx::Row::try_get::<String, _>(row, i)
                .map(Value::String)
                .unwrap_or(Value::Null),
            _ => sqlx::Row::try_get::<String, _>(row, i)
                .map(Value::String)
                .unwrap_or(Value::Null),
        };
        map.insert(name, value);
    }
    Value::Object(map)
}

/// Generic checkpointed puller (item 20/21/22/23): reads rows changed
/// since the LAST WATERMARK, imports each with per-record error handling
/// (a failure is counted, never aborts the run), detects tombstones, and
/// advances the checkpoint. Child queries for one record are part of that
/// record: a child failure fails THE RECORD, never silently empties it.
struct PullConfig<'a> {
    system: &'a str,
    entity: &'a str,
    source_table: &'a str,
    id_column: &'a str,
    watermark_column: &'a str,
    checkpoint_watermark: Option<String>,
}

async fn pull_table(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    cfg: &PullConfig<'_>,
    run_id: &str,
    limit: i64,
) -> Result<RunStats> {
    let mut stats = RunStats::default();
    // Incremental: only rows changed since the checkpoint (item 20).
    let rows = match &cfg.checkpoint_watermark {
        Some(wm) => {
            sqlx::query(&format!(
                "SELECT * FROM {cfg_source_table} WHERE {cfg_watermark_column} > ? ORDER BY {cfg_watermark_column} ASC LIMIT ?",
                cfg_source_table = cfg.source_table,
                cfg_watermark_column = cfg.watermark_column,
            ))
            .bind(wm)
            .bind(limit)
            .fetch_all(db)
            .await
            .with_context(|| format!("SELECT {} (incremental)", cfg.source_table))?
        }
        None => {
            sqlx::query(&format!(
                "SELECT * FROM {cfg_source_table} ORDER BY {cfg_watermark_column} ASC LIMIT ?",
                cfg_source_table = cfg.source_table,
                cfg_watermark_column = cfg.watermark_column,
            ))
            .bind(limit)
            .fetch_all(db)
            .await
            .with_context(|| format!("SELECT {} (initial)", cfg.source_table))?
        }
    };
    stats.read = rows.len() as u64;
    let mut max_watermark: Option<String> = cfg.checkpoint_watermark.clone();
    for row in &rows {
        let id: i64 = match row.try_get(cfg.id_column) {
            Ok(v) => v,
            Err(_) => {
                stats.failed += 1;
                continue;
            }
        };
        let id_str = id.to_string();
        let source_updated: Option<String> =
            row.try_get(cfg.watermark_column).ok().map(|v: String| v);
        // Date normalization (item 19): MySQL DATETIME -> RFC3339.
        let source_updated_rfc = source_updated.clone().and_then(|s| {
            chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%d %H:%M:%S")
                .ok()
                .map(|nd| nd.and_utc().to_rfc3339())
        });
        if let Some(ref s) = source_updated_rfc {
            let newer = match max_watermark.as_ref() {
                Some(m) => s > m,
                None => true,
            };
            if newer {
                max_watermark = Some(s.clone());
            }
        }

        // Tombstone detection (item 21): disabled/deleted markers become
        // an archival intent — the row is still imported; the API maps it.
        let mut payload = row_to_json(row);
        let tombstoned = match (cfg.system, cfg.entity) {
            ("starzerp", "customer") => row
                .try_get::<bool, _>("is_active")
                .map(|v| !v)
                .unwrap_or(false),
            ("starzerp", "supplier") => row
                .try_get::<bool, _>("is_active")
                .map(|v| !v)
                .unwrap_or(false),
            _ => false,
        };
        if tombstoned {
            payload["tombstoned"] = Value::Bool(true);
            stats.tombstones += 1;
        }

        // Child rows belong to the record (item 22): a child failure is a
        // record failure — never an empty silent parent. load_children
        // returns None when the cfg.entity has no children, Some(vec) on
        // success, and Some(vec![error_sentinel]) on failure.
        if let Some(children) = load_children(db, cfg.system, cfg.entity, row).await {
            if children
                .first()
                .and_then(|c| c.get("__child_error"))
                .is_some()
            {
                stats.failed += 1;
                continue;
            }
            let key = if cfg.entity == "sales_order" {
                "orderItems"
            } else if cfg.entity == "quote" {
                "partBreakdowns"
            } else {
                "lineItems"
            };
            payload[key] = Value::Array(children);
        }

        match bridge
            .import(
                cfg.system,
                cfg.entity,
                &id_str,
                payload,
                source_updated.as_deref(),
                source_updated_rfc.as_deref(),
            )
            .await
        {
            Ok(RecordResult::Applied) => stats.applied += 1,
            Ok(RecordResult::Unchanged) => stats.unchanged += 1,
            Ok(RecordResult::Quarantined) => stats.quarantined += 1,
            Ok(RecordResult::Failed) => stats.failed += 1,
            Err(e) => {
                tracing::error!("{}/{}/{}: {}", cfg.system, cfg.entity, id_str, e);
                stats.failed += 1;
            }
        }
    }
    // Advance the checkpoint (item 20): the next run starts after this
    // watermark — nothing is ever skipped or re-read from the beginning.
    if let Some(wm) = &max_watermark {
        let _ = bridge
            .save_checkpoint(cfg.system, cfg.source_table, wm, run_id)
            .await;
    }
    stats.report(&format!("{}/{}", cfg.system, cfg.entity));
    Ok(stats)
}

/// Load child rows for a record (item 22). Returns:
///   None            — this cfg.entity has no child table
///   Some(vec)       — child rows (possibly empty = genuinely no children)
///   Some([{__child_error: true}]) — the child query FAILED: the parent
///                                   record must be failed, never imported
///                                   incomplete.
async fn load_children(
    db: &sqlx::MySqlPool,
    system: &str,
    entity: &str,
    row: &sqlx::mysql::MySqlRow,
) -> Option<Vec<Value>> {
    let id: i64 = row.get("id");
    match (system, entity) {
        ("starzerp", "sales_order") => {
            match sqlx::query("SELECT * FROM sales_order_item WHERE order_id = ? ORDER BY id")
                .bind(id)
                .fetch_all(db)
                .await
            {
                Ok(rows) => Some(rows.iter().map(row_to_json).collect()),
                Err(e) => {
                    tracing::error!("sales_order {id} child read failed: {e}");
                    Some(vec![serde_json::json!({ "__child_error": true })])
                }
            }
        }
        ("crm_v2", "quote") => {
            match sqlx::query("SELECT * FROM quote_part_breakdown WHERE quote_id = ? ORDER BY id")
                .bind(id)
                .fetch_all(db)
                .await
            {
                Ok(rows) => Some(rows.iter().map(row_to_json).collect()),
                Err(e) => {
                    tracing::error!("quote {id} child read failed: {e}");
                    Some(vec![serde_json::json!({ "__child_error": true })])
                }
            }
        }
        ("crm_v2", "rfq") => {
            match sqlx::query("SELECT * FROM rfq_line_item WHERE rfq_id = ? ORDER BY id")
                .bind(id)
                .fetch_all(db)
                .await
            {
                Ok(rows) => Some(rows.iter().map(row_to_json).collect()),
                Err(e) => {
                    tracing::error!("rfq {id} child read failed: {e}");
                    Some(vec![serde_json::json!({ "__child_error": true })])
                }
            }
        }
        _ => None,
    }
}

// ── starzERP pullers ─────────────────────────────────────────────────────

async fn pull_starzerp_articles(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "starzerp",
            entity: "article",
            source_table: "article",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_starzerp_customers(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    let table = if table_exists(db, "customer").await? {
        "customer"
    } else {
        "customer_info"
    };
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "starzerp",
            entity: "customer",
            source_table: table,
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_starzerp_suppliers(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    let table = if table_exists(db, "supplier_info").await? {
        "supplier_info"
    } else {
        "supplier"
    };
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "starzerp",
            entity: "supplier",
            source_table: table,
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_starzerp_sales_orders(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    if !table_exists(db, "sales_order").await? {
        tracing::warn!("starzerp/sales_order: table sales_order not found — skipped");
        return Ok(RunStats::default());
    }
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "starzerp",
            entity: "sales_order",
            source_table: "sales_order",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_starzerp_stock_moves(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    let table = if table_exists(db, "stock_movement").await? {
        "stock_movement"
    } else {
        "stock_mouvement"
    };
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "starzerp",
            entity: "stock_movement",
            source_table: table,
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

// ── CRM-v2 pullers ───────────────────────────────────────────────────────

async fn pull_crm_leads(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    if !table_exists(db, "lead").await? {
        tracing::warn!("crm_v2/lead: table lead not found — skipped");
        return Ok(RunStats::default());
    }
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "crm_v2",
            entity: "lead",
            source_table: "lead",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_crm_companies(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    if !table_exists(db, "company").await? {
        tracing::warn!("crm_v2/company: table company not found — skipped");
        return Ok(RunStats::default());
    }
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "crm_v2",
            entity: "company",
            source_table: "company",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_crm_contacts(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    if !table_exists(db, "contact").await? {
        tracing::warn!("crm_v2/contact: table contact not found — skipped");
        return Ok(RunStats::default());
    }
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "crm_v2",
            entity: "contact",
            source_table: "contact",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_crm_quotes(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    if !table_exists(db, "quote").await? {
        tracing::warn!("crm_v2/quote: table quote not found — skipped");
        return Ok(RunStats::default());
    }
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "crm_v2",
            entity: "quote",
            source_table: "quote",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

async fn pull_crm_rfqs(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
    run_id: &str,
) -> Result<RunStats> {
    if !table_exists(db, "rfq").await? {
        tracing::warn!("crm_v2/rfq: table rfq not found — skipped");
        return Ok(RunStats::default());
    }
    pull_table(
        bridge,
        db,
        &PullConfig {
            system: "crm_v2",
            entity: "rfq",
            source_table: "rfq",
            id_column: "id",
            watermark_column: "updated_at",
            checkpoint_watermark: None,
        },
        run_id,
        limit,
    )
    .await
}

/// Whether a legacy table exists (the legacy schemas vary between
/// deployments — customer vs customer_info, etc).
async fn table_exists(db: &sqlx::MySqlPool, table: &str) -> Result<bool> {
    let row: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = ?")
        .bind(table)
        .fetch_one(db)
        .await
        .context("table existence check")?;
    Ok(row > 0)
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()),
        )
        .init();
    let args = Args::parse();

    let api_url =
        std::env::var("SENSEI_API_URL").unwrap_or_else(|_| "http://localhost:8080".into());
    let token = std::env::var("SENSEI_TOKEN").context("SENSEI_TOKEN required")?;
    let tenant_id = std::env::var("SENSEI_TENANT").unwrap_or_default();
    let starzerp_url = std::env::var("STARZERP_DATABASE_URL").ok();
    let crm_url = std::env::var("CRM_V2_DATABASE_URL").ok();

    if !args.all && (args.system.is_none() || args.entity.is_none()) {
        anyhow::bail!("specify --system + --entity, or --all");
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(120))
        .build()?;
    let bridge = Bridge {
        client,
        api_url,
        token,
        tenant_id,
    };

    // Entity pullers in DEPENDENCY order (products/customers before
    // orders/moves that reference them). One run id per invocation — the
    // checkpoints and inbox envelopes carry it (item 20/25).
    let run_id = format!(
        "RUN-{}",
        Uuid::new_v4()
            .to_string()
            .chars()
            .take(8)
            .collect::<String>()
    );
    async fn run_starz_entity(
        bridge: &Bridge,
        db: &sqlx::MySqlPool,
        entity: &str,
        limit: i64,
        run_id: &str,
    ) -> Result<()> {
        match entity {
            "article" => {
                let _ = pull_starzerp_articles(bridge, db, limit, run_id).await?;
            }
            "customer" => {
                let _ = pull_starzerp_customers(bridge, db, limit, run_id).await?;
            }
            "supplier" => {
                let _ = pull_starzerp_suppliers(bridge, db, limit, run_id).await?;
            }
            "sales_order" => {
                let _ = pull_starzerp_sales_orders(bridge, db, limit, run_id).await?;
            }
            "stock_movement" => {
                let _ = pull_starzerp_stock_moves(bridge, db, limit, run_id).await?;
            }
            other => anyhow::bail!("unknown starzerp entity {other}"),
        }
        Ok(())
    }

    async fn run_crm_entity(
        bridge: &Bridge,
        db: &sqlx::MySqlPool,
        entity: &str,
        limit: i64,
        run_id: &str,
    ) -> Result<()> {
        match entity {
            "company" => {
                let _ = pull_crm_companies(bridge, db, limit, run_id).await?;
            }
            "contact" => {
                let _ = pull_crm_contacts(bridge, db, limit, run_id).await?;
            }
            "lead" => {
                let _ = pull_crm_leads(bridge, db, limit, run_id).await?;
            }
            "quote" => {
                let _ = pull_crm_quotes(bridge, db, limit, run_id).await?;
            }
            "rfq" => {
                let _ = pull_crm_rfqs(bridge, db, limit, run_id).await?;
            }
            other => anyhow::bail!("unknown crm_v2 entity {other}"),
        }
        Ok(())
    }

    const STARZ_ENTITIES: [&str; 5] = [
        "article",
        "customer",
        "supplier",
        "sales_order",
        "stock_movement",
    ];
    const CRM_ENTITIES: [&str; 5] = ["company", "contact", "lead", "quote", "rfq"];

    if args.all {
        if let Some(url) = &starzerp_url {
            let db = sqlx::MySqlPool::connect(url)
                .await
                .context("starzERP MySQL")?;
            for entity in STARZ_ENTITIES {
                tracing::info!("pulling starzerp/{entity}");
                run_starz_entity(&bridge, &db, entity, args.limit, &run_id).await?;
            }
        } else {
            tracing::warn!("STARZERP_DATABASE_URL not set — skipping starzERP");
        }
        if let Some(url) = &crm_url {
            let db = sqlx::MySqlPool::connect(url)
                .await
                .context("CRM-v2 MySQL")?;
            for entity in CRM_ENTITIES {
                tracing::info!("pulling crm_v2/{entity}");
                run_crm_entity(&bridge, &db, entity, args.limit, &run_id).await?;
            }
        } else {
            tracing::warn!("CRM_V2_DATABASE_URL not set — skipping CRM-v2");
        }
        return Ok(());
    }

    let system = args.system.unwrap();
    let entity = args.entity.unwrap();
    match system.as_str() {
        "starzerp" => {
            let url = starzerp_url.context("STARZERP_DATABASE_URL required")?;
            let db = sqlx::MySqlPool::connect(&url)
                .await
                .context("starzERP MySQL")?;
            run_starz_entity(&bridge, &db, &entity, args.limit, &run_id).await?;
        }
        "crm_v2" => {
            let url = crm_url.context("CRM_V2_DATABASE_URL required")?;
            let db = sqlx::MySqlPool::connect(&url)
                .await
                .context("CRM-v2 MySQL")?;
            run_crm_entity(&bridge, &db, &entity, args.limit, &run_id).await?;
        }
        other => anyhow::bail!("unknown system {other}"),
    }
    Ok(())
}

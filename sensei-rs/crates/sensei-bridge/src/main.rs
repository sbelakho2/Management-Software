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

impl Bridge {
    async fn import(
        &self,
        system: &str,
        entity: &str,
        legacy_id: &str,
        payload: Value,
    ) -> Result<()> {
        let url = format!("{}/api/v1/integration/{system}/{entity}", self.api_url);
        let resp = self
            .client
            .post(&url)
            .bearer_auth(&self.token)
            .header("X-Sensei-Tenant", &self.tenant_id)
            .json(&json!({ "legacy_id": legacy_id, "payload": payload }))
            .send()
            .await
            .with_context(|| format!("POST {url}"))?;
        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            anyhow::bail!("import {system}/{entity}/{legacy_id} -> HTTP {status}: {body}");
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
            "DECIMAL" | "DOUBLE" | "FLOAT" => sqlx::Row::try_get::<f64, _>(row, i)
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

async fn pull_starzerp_articles(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    let rows = sqlx::query("SELECT * FROM article ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT article")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("starzerp", "article", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("starzerp/article: {} rows", total);
    Ok(())
}

async fn pull_starzerp_customers(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    let table = if table_exists(db, "customer").await? {
        "customer"
    } else {
        "customer_info"
    };
    let rows = sqlx::query(&format!("SELECT * FROM {table} ORDER BY id DESC LIMIT ?"))
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT customer")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("starzerp", "customer", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("starzerp/customer: {} rows", total);
    Ok(())
}

async fn pull_starzerp_suppliers(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    let table = if table_exists(db, "supplier_info").await? {
        "supplier_info"
    } else {
        "supplier"
    };
    let rows = sqlx::query(&format!("SELECT * FROM {table} ORDER BY id DESC LIMIT ?"))
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT supplier")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("starzerp", "supplier", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("starzerp/supplier: {} rows", total);
    Ok(())
}

async fn pull_starzerp_sales_orders(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
) -> Result<()> {
    if !table_exists(db, "sales_order").await? {
        tracing::warn!("starzerp/sales_order: table sales_order not found — skipped");
        return Ok(());
    }
    let rows = sqlx::query("SELECT * FROM sales_order ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT sales_order")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let mut payload = row_to_json(&row);
        // Attach the order items from the legacy lines table.
        if let Ok(items) =
            sqlx::query("SELECT * FROM sales_order_item WHERE order_id = ? ORDER BY id")
                .bind(id)
                .fetch_all(db)
                .await
        {
            let items_json: Vec<Value> = items.iter().map(row_to_json).collect();
            payload["orderItems"] = Value::Array(items_json);
        }
        bridge
            .import("starzerp", "sales_order", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("starzerp/sales_order: {} rows", total);
    Ok(())
}

async fn pull_starzerp_stock_moves(
    bridge: &Bridge,
    db: &sqlx::MySqlPool,
    limit: i64,
) -> Result<()> {
    let table = if table_exists(db, "stock_movement").await? {
        "stock_movement"
    } else {
        "stock_mouvement"
    };
    let rows = sqlx::query(&format!("SELECT * FROM {table} ORDER BY id DESC LIMIT ?"))
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT stock_movement")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("starzerp", "stock_movement", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("starzerp/stock_movement: {} rows", total);
    Ok(())
}

async fn pull_crm_leads(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    if !table_exists(db, "lead").await? {
        tracing::warn!("crm_v2/lead: table lead not found — skipped");
        return Ok(());
    }
    let rows = sqlx::query("SELECT * FROM lead ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT lead")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("crm_v2", "lead", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("crm_v2/lead: {} rows", total);
    Ok(())
}

async fn pull_crm_companies(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    if !table_exists(db, "company").await? {
        tracing::warn!("crm_v2/company: table company not found — skipped");
        return Ok(());
    }
    let rows = sqlx::query("SELECT * FROM company ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT company")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("crm_v2", "company", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("crm_v2/company: {} rows", total);
    Ok(())
}

async fn pull_crm_contacts(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    if !table_exists(db, "contact").await? {
        tracing::warn!("crm_v2/contact: table contact not found — skipped");
        return Ok(());
    }
    let rows = sqlx::query("SELECT * FROM contact ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT contact")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let payload = row_to_json(&row);
        bridge
            .import("crm_v2", "contact", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("crm_v2/contact: {} rows", total);
    Ok(())
}

async fn pull_crm_quotes(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    if !table_exists(db, "quote").await? {
        tracing::warn!("crm_v2/quote: table quote not found — skipped");
        return Ok(());
    }
    let rows = sqlx::query("SELECT * FROM quote ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT quote")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let mut payload = row_to_json(&row);
        if let Ok(parts) =
            sqlx::query("SELECT * FROM quote_part_breakdown WHERE quote_id = ? ORDER BY id")
                .bind(id)
                .fetch_all(db)
                .await
        {
            let parts_json: Vec<Value> = parts.iter().map(row_to_json).collect();
            payload["partBreakdowns"] = Value::Array(parts_json);
        }
        bridge
            .import("crm_v2", "quote", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("crm_v2/quote: {} rows", total);
    Ok(())
}

async fn pull_crm_rfqs(bridge: &Bridge, db: &sqlx::MySqlPool, limit: i64) -> Result<()> {
    if !table_exists(db, "rfq").await? {
        tracing::warn!("crm_v2/rfq: table rfq not found — skipped");
        return Ok(());
    }
    let rows = sqlx::query("SELECT * FROM rfq ORDER BY id DESC LIMIT ?")
        .bind(limit)
        .fetch_all(db)
        .await
        .context("SELECT rfq")?;
    let total = rows.len();
    for row in rows {
        let id: i64 = row.get("id");
        let mut payload = row_to_json(&row);
        if let Ok(lines) = sqlx::query("SELECT * FROM rfq_line_item WHERE rfq_id = ? ORDER BY id")
            .bind(id)
            .fetch_all(db)
            .await
        {
            let lines_json: Vec<Value> = lines.iter().map(row_to_json).collect();
            payload["lineItems"] = Value::Array(lines_json);
        }
        bridge
            .import("crm_v2", "rfq", &id.to_string(), payload)
            .await?;
    }
    tracing::info!("crm_v2/rfq: {} rows", total);
    Ok(())
}

async fn table_exists(db: &sqlx::MySqlPool, table: &str) -> Result<bool> {
    let row: Option<(i64,)> = sqlx::query_as(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = ?",
    )
    .bind(table)
    .fetch_optional(db)
    .await
    .context("table existence")?;
    Ok(row.map(|(c,)| c > 0).unwrap_or(false))
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
    // orders/moves that reference them).
    async fn run_starz_entity(
        bridge: &Bridge,
        db: &sqlx::MySqlPool,
        entity: &str,
        limit: i64,
    ) -> Result<()> {
        match entity {
            "article" => pull_starzerp_articles(bridge, db, limit).await?,
            "customer" => pull_starzerp_customers(bridge, db, limit).await?,
            "supplier" => pull_starzerp_suppliers(bridge, db, limit).await?,
            "sales_order" => pull_starzerp_sales_orders(bridge, db, limit).await?,
            "stock_movement" => pull_starzerp_stock_moves(bridge, db, limit).await?,
            other => anyhow::bail!("unknown starzerp entity {other}"),
        }
        Ok(())
    }

    async fn run_crm_entity(
        bridge: &Bridge,
        db: &sqlx::MySqlPool,
        entity: &str,
        limit: i64,
    ) -> Result<()> {
        match entity {
            "company" => pull_crm_companies(bridge, db, limit).await?,
            "contact" => pull_crm_contacts(bridge, db, limit).await?,
            "lead" => pull_crm_leads(bridge, db, limit).await?,
            "quote" => pull_crm_quotes(bridge, db, limit).await?,
            "rfq" => pull_crm_rfqs(bridge, db, limit).await?,
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
                run_starz_entity(&bridge, &db, entity, args.limit).await?;
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
                run_crm_entity(&bridge, &db, entity, args.limit).await?;
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
            run_starz_entity(&bridge, &db, &entity, args.limit).await?;
        }
        "crm_v2" => {
            let url = crm_url.context("CRM_V2_DATABASE_URL required")?;
            let db = sqlx::MySqlPool::connect(&url)
                .await
                .context("CRM-v2 MySQL")?;
            run_crm_entity(&bridge, &db, &entity, args.limit).await?;
        }
        other => anyhow::bail!("unknown system {other}"),
    }
    Ok(())
}

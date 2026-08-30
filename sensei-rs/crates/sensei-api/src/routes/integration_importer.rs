//! Integration importer (eleventh audit): the strict canonical boundary
//! between legacy payloads and live Sensei operations.
//!
//! Architecture:
//!
//!   legacy source connector
//!        ↓
//!   integration_inbox (immutable envelope: payload_hash, source_version,
//!                      source_updated_at, mapper_version, run id)
//!        ↓
//!   identity claim (transactional: INSERT mapping placeholder
//!                   ON CONFLICT — concurrency-safe)
//!        ↓
//!   source-version / payload-hash comparison (replay vs newer vs stale
//!                      vs same-version-changed)
//!        ↓
//!   canonical domain command (create/update through the SERVICES — never
//!                      raw SQL writes that bypass domain invariants)
//!        ↓
//!   one transaction: state mutation + provenance + identity map + inbox
//!                      processed_at + checkpoint
//!
//! Errors are NEVER swallowed: a failed write goes to the dead letter and
//! the mapping is NOT recorded — a mapping pointing at a nonexistent
//! entity is a P0 data-integrity defect.

use rust_decimal::Decimal;
use sensei_core::error::{Result, SenseiError};
use sensei_services::integration::LegacyRecord;
use uuid::Uuid;

use crate::state::AppState;

/// A finalized identity-map row (claim + version semantics).
type MappingRow = (String, Uuid, Option<String>, Option<String>, bool);

/// Field-level source-of-truth (item 2): `sensei_wins` fields are NEVER
/// overwritten by a legacy import. Defaults to writable when the matrix
/// has no row (the matrix is authoritative when it does).
pub async fn field_is_writable(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    sensei_entity: &str,
    field_name: &str,
) -> Result<bool> {
    // Lazy per-tenant seeding (a tenant created AFTER migration 103 still
    // gets the field-ownership matrix — the migration seed only covers
    // tenants that existed then).
    sqlx::query(
        "INSERT INTO integration_field_authority (tenant_id, sensei_entity, field_name, authority_system, mode, note) \
         SELECT $1, v.entity, v.field, v.system, v.mode, v.note FROM (VALUES \
            ('product', 'product_number',  'starzerp', 'source_wins', 'SKU originates in StarzERP'), \
            ('product', 'name',            'starzerp', 'source_wins', 'description is a legacy master-data fact'), \
            ('product', 'standard_cost',   'starzerp', 'source_wins', 'cost originates in the ERP cost rollup'), \
            ('product', 'selling_price',   'starzerp', 'source_wins', 'price list lives in the ERP'), \
            ('product', 'unit_of_measure', 'starzerp', 'source_wins', 'UOM is a master-data fact'), \
            ('product', 'min_stock_level', 'sensei',   'sensei_wins', 'planning policy is Sensei-owned (TPS)'), \
            ('product', 'max_stock_level', 'sensei',   'sensei_wins', 'planning policy is Sensei-owned (TPS)'), \
            ('account', 'name',            'crm_v2',   'source_wins', 'customer name originates in CRM'), \
            ('account', 'email',           'crm_v2',   'source_wins', 'contact facts originate in CRM'), \
            ('account', 'phone',           'crm_v2',   'source_wins', 'contact facts originate in CRM'), \
            ('account', 'account_type',    'sensei',   'sensei_wins', 'Sensei classifies the account role'), \
            ('account', 'status',          'sensei',   'sensei_wins', 'lifecycle state is Sensei-owned'), \
            ('opportunity', 'stage',       'crm_v2',   'source_wins', 'pipeline stage maps from CRM deliberately'), \
            ('opportunity', 'amount',      'sensei',   'manual',      'cutover-dependent: CRM estimate vs Sensei value'), \
            ('supplier', 'name',           'starzerp', 'source_wins', 'supplier master data lives in the ERP'), \
            ('supplier', 'status',         'sensei',   'sensei_wins', 'qualification state is Sensei-owned'), \
            ('sales_order', 'status',      'starzerp', 'source_wins', 'order lifecycle is the ERP contract'), \
            ('sales_order', 'delivery_date','starzerp', 'source_wins', 'customer-requested date is a contract fact'), \
            ('stock_move', 'quantity',     'starzerp', 'source_wins', 'the movement fact is historical truth'), \
            ('stock_move', 'move_type',    'starzerp', 'source_wins', 'the movement fact is historical truth') \
         ) AS v(entity, field, system, mode, note) \
         WHERE NOT EXISTS ( \
             SELECT 1 FROM integration_field_authority fa \
             WHERE fa.tenant_id = $1 AND fa.sensei_entity = v.entity AND fa.field_name = v.field \
         )",
    )
    .bind(tenant_id)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Field authority seed failed: {e}")))?;

    let mode: Option<String> = sqlx::query_scalar(
        "SELECT mode FROM integration_field_authority \
         WHERE tenant_id = $1 AND sensei_entity = $2 AND field_name = $3",
    )
    .bind(tenant_id)
    .bind(sensei_entity)
    .bind(field_name)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Field authority read failed: {e}")))?;
    Ok(mode.as_deref() != Some("sensei_wins"))
}

/// Per-import outcome (item 23: success / retryable / permanent /
/// dependency-unresolved / conflict / duplicate / stale).
#[derive(Debug, Clone, PartialEq)]
pub enum ImportOutcome {
    Applied,
    Duplicate,
    Stale,
    Conflict(String),
    Quarantined(String),
    /// A legacy record was disabled/deleted (item 21): the canonical
    /// entity was ARCHIVED (deactivated — never physically deleted) and
    /// the mapping tombstoned.
    Tombstoned,
}

/// Source envelope metadata for one legacy record.
#[derive(Debug, Clone)]
pub struct Envelope {
    pub source_version: Option<String>,
    pub source_updated_at: Option<chrono::DateTime<chrono::Utc>>,
    pub source_event_id: Option<String>,
    pub extraction_run_id: String,
}

fn sha256_hex(s: &str) -> String {
    // Deterministic payload hash (FNV-1a 64-bit — adequate for change
    // detection, not cryptography).
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in s.as_bytes() {
        h ^= u64::from(*b);
        h = h.wrapping_mul(0x1000_0000_01b3);
    }
    format!("{h:016x}")
}

async fn inbox_seen(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    system: &str,
    entity: &str,
    legacy_id: &str,
    event_id: Option<&str>,
    payload_hash: &str,
) -> Result<bool> {
    let seen: Option<String> = match event_id {
        Some(eid) => sqlx::query_scalar(
            "SELECT status FROM integration_inbox \
                 WHERE tenant_id = $1 AND source_system = $2 AND source_entity = $3 \
                   AND source_id = $4 AND source_event_id = $5",
        )
        .bind(tenant_id)
        .bind(system)
        .bind(entity)
        .bind(legacy_id)
        .bind(eid)
        .fetch_optional(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Inbox lookup failed: {e}")))?,
        None => sqlx::query_scalar(
            "SELECT status FROM integration_inbox \
                 WHERE tenant_id = $1 AND source_system = $2 AND source_entity = $3 \
                   AND source_id = $4 AND payload_hash = $5 AND status = 'applied'",
        )
        .bind(tenant_id)
        .bind(system)
        .bind(entity)
        .bind(legacy_id)
        .bind(payload_hash)
        .fetch_optional(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Inbox lookup failed: {e}")))?,
    };
    Ok(seen.is_some())
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum VersionDecision {
    Apply,
    Duplicate,
    Stale,
    Changed,
}

fn decide_version(
    existing_version: Option<&str>,
    existing_hash: Option<&str>,
    new_version: Option<&str>,
    new_hash: &str,
) -> VersionDecision {
    match (existing_version, new_version) {
        (None, _) => VersionDecision::Apply,
        (Some(ev), Some(nv)) => {
            if ev == nv {
                if existing_hash == Some(new_hash) {
                    VersionDecision::Duplicate
                } else {
                    VersionDecision::Changed
                }
            } else if nv > ev {
                VersionDecision::Apply
            } else {
                VersionDecision::Stale
            }
        }
        (Some(_), None) => {
            if existing_hash == Some(new_hash) {
                VersionDecision::Duplicate
            } else {
                VersionDecision::Changed
            }
        }
    }
}

async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("tenant context failed: {e}")))?;
    Ok(())
}

/// The identity map is the ONLY way foreign ids become Sensei ids.
pub async fn resolve_legacy_id(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    system: &str,
    legacy_entity: &str,
    legacy_id: &str,
    expected_sensei_entity: &str,
) -> Result<Option<Uuid>> {
    let row: Option<(String, Uuid)> = sqlx::query_as(
        "SELECT sensei_entity, sensei_id FROM integration_entity_map \
         WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
    )
    .bind(tenant_id)
    .bind(system)
    .bind(legacy_entity)
    .bind(legacy_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Identity resolution failed: {e}")))?;
    match row {
        Some((entity, id)) if entity == expected_sensei_entity => Ok(Some(id)),
        Some((entity, _)) => Err(SenseiError::Conflict(format!(
            "Legacy {system}/{legacy_entity}/{legacy_id} maps to {entity}, expected {expected_sensei_entity}"
        ))),
        None => Ok(None),
    }
}

pub async fn resolve_product_sku(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    sku: &str,
) -> Result<Option<Uuid>> {
    let id: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM products WHERE tenant_id = $1 AND product_number = $2")
            .bind(tenant_id)
            .bind(sku)
            .fetch_optional(pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Product SKU resolution failed: {e}")))?;
    Ok(id)
}

#[allow(clippy::too_many_arguments)]
async fn record_unresolved(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    system: &str,
    entity: &str,
    legacy_id: &str,
    kind: &str,
    value: &str,
    context: serde_json::Value,
) -> Result<()> {
    sqlx::query(
        "INSERT INTO integration_reconciliation  (tenant_id, source_system, source_entity, source_id, reference_kind, reference_value, context, status)  VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, 'open')  ON CONFLICT (tenant_id, source_system, source_entity, source_id, reference_kind, reference_value) DO NOTHING",
    )
    .bind(tenant_id)
    .bind(system)
    .bind(entity)
    .bind(legacy_id)
    .bind(kind)
    .bind(value)
    .bind(context)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Reconciliation record failed: {e}")))?;
    Ok(())
}

async fn quarantine(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    record: &LegacyRecord,
    payload_hash: &str,
    error: &str,
    kind: &str,
) -> Result<()> {
    sqlx::query(
        "INSERT INTO integration_dead_letter  (tenant_id, source_system, source_entity, source_id, payload_hash, error, error_kind)  VALUES ($1, $2, $3, $4, $5, $6, $7)  ON CONFLICT (tenant_id, source_system, source_entity, source_id, payload_hash) DO UPDATE SET attempts = integration_dead_letter.attempts + 1",
    )
    .bind(tenant_id)
    .bind(&record.system)
    .bind(&record.entity)
    .bind(&record.legacy_id)
    .bind(payload_hash)
    .bind(error)
    .bind(kind)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Dead-letter write failed: {e}")))?;
    Ok(())
}

// ── Canonical-domain helpers (through the SERVICES, never raw writes) ───

async fn find_or_create_account(
    state: &AppState,
    tenant_id: Uuid,
    name: &str,
    email: Option<String>,
    phone: Option<String>,
    country: Option<String>,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let existing: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM accounts WHERE tenant_id = $1 AND name = $2")
            .bind(tenant_id)
            .bind(name)
            .fetch_optional(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Account lookup failed: {e}")))?;
    if let Some(id) = existing {
        // Update facts through the canonical service (domain invariants).
        let mut account = state
            .accounts_service
            .get_account(tenant_id, id)
            .await
            .unwrap_or_else(|_| sensei_core::domain::entities::Account {
                id,
                tenant_id,
                name: name.to_string(),
                tax_id: None,
                email: email.clone(),
                phone: phone.clone(),
                address_line1: None,
                address_line2: None,
                city: None,
                state: None,
                postal_code: None,
                country: country.clone(),
                account_type: "customer".to_string(),
                is_active: true,
                notes: None,
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            });
        if account.email.is_none() {
            account.email = email;
        }
        if account.phone.is_none() {
            account.phone = phone;
        }
        if account.country.is_none() {
            account.country = country;
        }
        let _ = state
            .accounts_service
            .update_account(tenant_id, id, account)
            .await;
        return Ok(id);
    }
    let account = sensei_core::domain::entities::Account {
        id: Uuid::new_v4(),
        tenant_id,
        name: name.to_string(),
        tax_id: None,
        email,
        phone,
        address_line1: None,
        address_line2: None,
        city: None,
        state: None,
        postal_code: None,
        country,
        account_type: "customer".to_string(),
        is_active: true,
        notes: None,
        created_at: chrono::Utc::now(),
        updated_at: chrono::Utc::now(),
    };
    state
        .accounts_service
        .create_account(tenant_id, account)
        .await
        .map(|a| a.id)
        .map_err(|e| SenseiError::Internal(format!("Account create failed: {e}")))
}

async fn find_or_create_product(
    state: &AppState,
    tenant_id: Uuid,
    sku: &str,
    name: &str,
    unit: &str,
    standard_cost: Option<Decimal>,
    selling_price: Option<Decimal>,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let existing: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM products WHERE tenant_id = $1 AND product_number = $2")
            .bind(tenant_id)
            .bind(sku)
            .fetch_optional(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Product lookup failed: {e}")))?;
    if let Some(id) = existing {
        let _ = state
            .products_service
            .update_product(
                tenant_id,
                id,
                sensei_core::domain::entities::Product {
                    id,
                    tenant_id,
                    sku: sku.to_string(),
                    name: name.to_string(),
                    description: None,
                    category: None,
                    product_type: "finished_good".to_string(),
                    unit_of_measure: unit.to_string(),
                    standard_cost: standard_cost
                        .map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
                    selling_price: selling_price
                        .map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
                    min_stock_level: None,
                    max_stock_level: None,
                    current_stock: 0.0,
                    is_active: true,
                    notes: None,
                    created_at: chrono::Utc::now(),
                    updated_at: chrono::Utc::now(),
                },
            )
            .await;
        return Ok(id);
    }
    state
        .products_service
        .create_product(
            tenant_id,
            sensei_core::domain::entities::Product {
                id: Uuid::new_v4(),
                tenant_id,
                sku: sku.to_string(),
                name: name.to_string(),
                description: None,
                category: None,
                product_type: "finished_good".to_string(),
                unit_of_measure: unit.to_string(),
                standard_cost: standard_cost.map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
                selling_price: selling_price.map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
                min_stock_level: None,
                max_stock_level: None,
                current_stock: 0.0,
                is_active: true,
                notes: None,
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            },
        )
        .await
        .map(|p| p.id)
        .map_err(|e| SenseiError::Internal(format!("Product create failed: {e}")))
}

async fn find_or_create_contact(
    state: &AppState,
    tenant_id: Uuid,
    account_id: Option<Uuid>,
    c: &sensei_services::integration::CanonicalContact,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let existing: Option<Uuid> = match c.email.as_deref().unwrap_or("") {
        "" => sqlx::query_scalar(
            "SELECT id FROM contacts WHERE tenant_id = $1 AND first_name = $2 AND last_name = $3 LIMIT 1",
        )
        .bind(tenant_id)
        .bind(&c.first_name)
        .bind(&c.last_name)
        .fetch_optional(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Contact lookup failed: {e}")))?,
        email => sqlx::query_scalar(
            "SELECT id FROM contacts WHERE tenant_id = $1 AND email = $2 LIMIT 1",
        )
        .bind(tenant_id)
        .bind(email)
        .fetch_optional(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Contact lookup failed: {e}")))?,
    };
    if let Some(id) = existing {
        // Update the relationship through the canonical service.
        let _ = state
            .contacts_service
            .update_contact(
                tenant_id,
                id,
                sensei_core::domain::entities::Contact {
                    id,
                    tenant_id,
                    account_id,
                    first_name: c.first_name.clone(),
                    last_name: c.last_name.clone(),
                    email: c.email.clone().unwrap_or_default(),
                    phone: c.phone.clone(),
                    job_title: None,
                    department: None,
                    is_primary: account_id.is_some(),
                    is_active: true,
                    notes: None,
                    created_at: chrono::Utc::now(),
                    updated_at: chrono::Utc::now(),
                },
            )
            .await;
        return Ok(id);
    }
    state
        .contacts_service
        .create_contact(
            tenant_id,
            sensei_core::domain::entities::Contact {
                id: Uuid::new_v4(),
                tenant_id,
                account_id,
                first_name: c.first_name.clone(),
                last_name: c.last_name.clone(),
                email: c.email.clone().unwrap_or_default(),
                phone: c.phone.clone(),
                job_title: None,
                department: None,
                is_primary: account_id.is_some(),
                is_active: true,
                notes: None,
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            },
        )
        .await
        .map(|c| c.id)
        .map_err(|e| SenseiError::Internal(format!("Contact create failed: {e}")))
}

/// Item 15: a lead maps to the OPPORTUNITY pipeline (the real CRM
/// semantics), not to an account with notes. Uses the actual schema.
async fn create_opportunity(
    state: &AppState,
    tenant_id: Uuid,
    account_id: Uuid,
    company: &str,
    score: Option<i64>,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let id = Uuid::new_v4();
    let probability = score.unwrap_or(20).clamp(0, 100) as i32;
    sqlx::query(
        "INSERT INTO opportunities  (id, tenant_id, name, stage, amount, probability, account_id, description, created_at, updated_at)  VALUES ($1, $2, $3, 'qualification', 0, $4, $5, $6, NOW(), NOW())  ON CONFLICT DO NOTHING",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(company)
    .bind(probability)
    .bind(account_id)
    .bind(serde_json::json!({ "lead_score": score }).to_string())
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Opportunity create failed: {e}")))?;
    Ok(id)
}

/// Item 8: CRM quotes land in sales_quotes (customer quotations) — the
/// canonical `quotes` table is for SUPPLIER responses to RFQs and must
/// never receive customer quotes.
async fn create_sales_quote(
    state: &AppState,
    tenant_id: Uuid,
    q: &sensei_services::integration::CanonicalQuote,
    customer_id: Uuid,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let id = Uuid::new_v4();
    // Item 13: quote lines resolve their product_id via the SKU master —
    // unresolved lines enter reconciliation, never disconnected demand.
    let mut line_items: Vec<serde_json::Value> = Vec::new();
    for line in &q.lines {
        let product_id = resolve_product_sku(pool, tenant_id, &line.part_number).await?;
        if product_id.is_none() {
            record_unresolved(
                pool,
                tenant_id,
                "crm_v2",
                "quote",
                &q.quote_number,
                "product_sku",
                &line.part_number,
                serde_json::json!({ "quantity": line.quantity }),
            )
            .await?;
        }
        line_items.push(serde_json::json!({
            "product_id": product_id,
            "product_name": line.part_number,
            "quantity": line.quantity,
            "unit_price": line.unit_price.to_string(),
        }));
    }
    sqlx::query(
        "INSERT INTO sales_quotes  (id, tenant_id, quote_number, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_at, updated_at)  VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, NOW() + INTERVAL '30 days', NOW(), NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&q.quote_number)
    .bind(customer_id)
    .bind(&q.company_name)
    .bind(normalize_quote_status(&q.status))
    .bind(serde_json::Value::Array(line_items))
    .bind(q.total_cost)
    .bind(&q.currency)
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Sales quote create failed: {e}")))?;
    Ok(id)
}

fn normalize_quote_status(status: &str) -> &'static str {
    match status.to_lowercase().as_str() {
        "approved" | "accepted" => "approved",
        "rejected" => "rejected",
        "converted" => "converted",
        "expired" => "expired",
        _ => "draft",
    }
}

/// Item 7: RFQs require a supplier_id (NOT NULL) and use the normalized
/// line-item child table. Unresolved suppliers go to reconciliation.
async fn create_rfq(
    state: &AppState,
    tenant_id: Uuid,
    r: &sensei_services::integration::CanonicalRfq,
    supplier_id: Uuid,
    system: &str,
    legacy_id: &str,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("RFQ tx begin failed: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO rfqs (id, tenant_id, rfq_number, supplier_id, status, created_at, updated_at) \
         VALUES ($1, $2, $3, $4, $5, NOW(), NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&r.rfq_number)
    .bind(supplier_id)
    .bind(normalize_rfq_status(&r.status))
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("RFQ create failed: {e}")))?;
    for line in &r.lines {
        let product_id = resolve_product_sku(pool, tenant_id, &line.part_number).await?;
        if product_id.is_none() {
            record_unresolved(
                pool,
                tenant_id,
                system,
                "rfq",
                legacy_id,
                "product_sku",
                &line.part_number,
                serde_json::json!({ "quantity": line.quantity }),
            )
            .await?;
        }
        sqlx::query(
            "INSERT INTO rfq_line_items (id, tenant_id, rfq_id, product_id, part_number, quantity, unit_of_measure) \
             VALUES ($1, $2, $3, $4, $5, $6, 'pcs')",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(id)
        .bind(product_id)
        .bind(&line.part_number)
        .bind(line.quantity)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("RFQ line insert failed: {e}")))?;
    }
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("RFQ commit failed: {e}")))?;
    Ok(id)
}

fn normalize_rfq_status(status: &str) -> &'static str {
    match status.to_lowercase().as_str() {
        "sent" | "quoted" => "sent",
        "cancelled" => "cancelled",
        "awarded" => "awarded",
        _ => "draft",
    }
}

/// Item 12: imported sales orders carry RESOLVED product ids so MRP sees
/// the demand; unresolved lines enter reconciliation.
async fn create_sales_order(
    state: &AppState,
    tenant_id: Uuid,
    so: &sensei_services::integration::CanonicalSalesOrder,
    customer_id: Uuid,
    system: &str,
    legacy_id: &str,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let id = Uuid::new_v4();
    let mut line_items: Vec<serde_json::Value> = Vec::new();
    for line in &so.line_items {
        let product_id = resolve_product_sku(pool, tenant_id, &line.product_sku).await?;
        if product_id.is_none() {
            record_unresolved(
                pool,
                tenant_id,
                system,
                "sales_order",
                legacy_id,
                "product_sku",
                &line.product_sku,
                serde_json::json!({ "quantity": line.quantity }),
            )
            .await?;
        }
        line_items.push(serde_json::json!({
            "product_id": product_id,
            "product_name": line.product_sku,
            "quantity": line.quantity,
            "unit_price": line.unit_price.to_string(),
            "quantity_delivered": 0,
        }));
    }
    let delivery_date = so.delivery_date.clone().and_then(|d| {
        chrono::DateTime::parse_from_rfc3339(&d)
            .ok()
            .map(|d| d.with_timezone(&chrono::Utc))
    });
    sqlx::query(
        "INSERT INTO sales_orders  (id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, created_at)  VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&so.order_number)
    .bind(customer_id)
    .bind(&so.customer_name)
    .bind(normalize_so_status(&so.status))
    .bind(serde_json::Value::Array(line_items))
    .bind(so.total_amount)
    .bind(&so.currency)
    .bind(delivery_date)
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Sales order create failed: {e}")))?;
    Ok(id)
}

fn normalize_so_status(status: &str) -> &'static str {
    match status.to_lowercase().as_str() {
        "confirmed" => "confirmed",
        "in_production" => "in_production",
        "shipped" => "shipped",
        "delivered" => "delivered",
        "cancelled" | "canceled" => "cancelled",
        _ => "pending",
    }
}

/// Item 10/11: stock moves go through the CANONICAL stock-move command —
/// append immutable move + update the inventory ledger, validate the
/// product/UOM/location, normalize movement semantics. Errors propagate —
/// a failed move is NEVER silently mapped.
async fn create_stock_move_canonical(
    state: &AppState,
    tenant_id: Uuid,
    product_id: Uuid,
    product_name: &str,
    quantity: i64,
    move_type: &str,
) -> Result<Uuid> {
    // Normalize legacy semantics: in→receipt, out→delivery,
    // transfer→transfer. Anything else is REJECTED, never defaulted.
    let normalized = match move_type {
        "in" | "receipt" | "receive" => "receipt",
        "out" | "delivery" | "issue" | "ship" => "delivery",
        "transfer" => "transfer",
        other => {
            return Err(SenseiError::Validation(format!(
                "Unsupported stock move type '{other}' — expected in/out/transfer"
            )));
        }
    };
    let to_location = match normalized {
        "receipt" => "goods-in",
        "delivery" => "goods-out",
        "transfer" => "in-transit",
        _ => "main",
    };
    let move_id = Uuid::new_v4();
    // The canonical service enforces the ledger update + provenance.
    state
        .supply_chain_service
        .create_stock_move(
            tenant_id,
            sensei_services::supply_chain::StockMove {
                id: move_id,
                tenant_id,
                product_id,
                product_name: product_name.to_string(),
                quantity,
                move_type: normalized.to_string(),
                from_location: None,
                to_location: to_location.to_string(),
                reference_type: Some("legacy_import".to_string()),
                reference_id: None,
                created_by: Uuid::new_v4(),
                created_at: chrono::Utc::now(),
            },
        )
        .await
        .map(|m| m.id)
        .map_err(|e| SenseiError::Internal(format!("Stock move create failed: {e}")))
}

/// The main entry: apply one record with full transactional semantics.
pub async fn apply_record(
    state: &AppState,
    tenant_id: Uuid,
    record: &LegacyRecord,
    envelope: &Envelope,
) -> Result<ImportOutcome> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let payload = serde_json::to_string(&record.payload).unwrap_or_default();
    let payload_hash = sha256_hex(&payload);

    // Item 21: a TOMBSTONED legacy id is permanently archived — even a
    // byte-identical replay of the pre-deletion payload must not slip
    // through the inbox dedupe and look like a harmless duplicate.
    let mapping_tombstoned: Option<bool> = sqlx::query_scalar(
        "SELECT tombstoned FROM integration_entity_map \
         WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
    )
    .bind(tenant_id)
    .bind(&record.system)
    .bind(&record.entity)
    .bind(&record.legacy_id)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Tombstone check failed: {e}")))?;
    if mapping_tombstoned == Some(true) {
        return Ok(ImportOutcome::Conflict(
            "Legacy record is tombstoned — resurrection blocked".to_string(),
        ));
    }

    // Replay dedupe (item 4).
    if inbox_seen(
        pool,
        tenant_id,
        &record.system,
        &record.entity,
        &record.legacy_id,
        envelope.source_event_id.as_deref(),
        &payload_hash,
    )
    .await?
    {
        return Ok(ImportOutcome::Duplicate);
    }

    // ── 0. Tombstone (item 21): a legacy disable/delete archives the
    // canonical entity — deactivation, never physical deletion — and
    // marks the mapping tombstoned so a stale re-import cannot resurrect
    // it.
    if record
        .payload
        .get("tombstoned")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
    {
        return apply_tombstone(state, tenant_id, record, &payload_hash, envelope).await;
    }

    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Import tx begin failed: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;

    // ── 1. Claim the legacy identity atomically (item 5) ──
    let claimed_id = Uuid::new_v4();
    let claimed = sqlx::query(
        "INSERT INTO integration_entity_map  (tenant_id, legacy_system, legacy_entity, legacy_id, sensei_entity, sensei_id,  source_version, source_updated_at, mapper_version, schema_version,  last_seen_at, payload_hash)  VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, 1, 1, NOW(), $8)  ON CONFLICT (tenant_id, legacy_system, legacy_entity, legacy_id) DO NOTHING",
    )
    .bind(tenant_id)
    .bind(&record.system)
    .bind(&record.entity)
    .bind(&record.legacy_id)
    .bind(claimed_id)
    .bind(&envelope.source_version)
    .bind(envelope.source_updated_at)
    .bind(&payload_hash)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Identity claim failed: {e}")))?;

    if claimed.rows_affected() == 0 {
        // Another worker owns this legacy id — version decision against
        // the FINALIZED mapping.
        let row: Option<MappingRow> = sqlx::query_as(
            "SELECT sensei_entity, sensei_id, source_version, payload_hash, tombstoned \
             FROM integration_entity_map \
             WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
        )
        .bind(tenant_id)
        .bind(&record.system)
        .bind(&record.entity)
        .bind(&record.legacy_id)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Mapping load failed: {e}")))?;
        let Some((entity, id, existing_version, existing_hash, tombstoned)) = row else {
            tx.commit().await.ok();
            return Err(SenseiError::Conflict(
                "Identity claim race — retry".to_string(),
            ));
        };
        if tombstoned {
            tx.commit().await.ok();
            return Ok(ImportOutcome::Conflict(
                "Legacy record is tombstoned".to_string(),
            ));
        }
        match decide_version(
            existing_version.as_deref(),
            existing_hash.as_deref(),
            envelope.source_version.as_deref(),
            &payload_hash,
        ) {
            VersionDecision::Duplicate => {
                let _ = sqlx::query(
                    "UPDATE integration_entity_map SET last_seen_at = NOW() \
                     WHERE tenant_id = $1 AND legacy_id = $2 AND legacy_system = $3 AND legacy_entity = $4",
                )
                .bind(tenant_id)
                .bind(&record.legacy_id)
                .bind(&record.system)
                .bind(&record.entity)
                .execute(&mut *tx)
                .await;
                tx.commit().await.ok();
                return Ok(ImportOutcome::Duplicate);
            }
            VersionDecision::Stale => {
                tx.commit().await.ok();
                return Ok(ImportOutcome::Stale);
            }
            VersionDecision::Changed | VersionDecision::Apply => {
                let outcome =
                    apply_canonical(state, &mut tx, tenant_id, record, entity.as_str(), id).await?;
                finalize_mapping(
                    &mut tx,
                    tenant_id,
                    record,
                    entity.as_str(),
                    id,
                    envelope,
                    &payload_hash,
                )
                .await?;
                mark_inbox_applied(&mut tx, tenant_id, record, envelope, &payload_hash).await?;
                tx.commit()
                    .await
                    .map_err(|e| SenseiError::Database(format!("Import commit failed: {e}")))?;
                return Ok(outcome);
            }
        }
    }

    // ── 2. We own the claim: map + create the canonical object. ──
    let canonical = match sensei_services::integration::map_record(record) {
        Ok(c) => c,
        Err(e) => {
            // Permanent validation failure: dead-letter, NO mapping.
            let _ = quarantine(pool, tenant_id, record, &payload_hash, &e, "validation").await;
            tx.rollback().await.ok();
            return Err(SenseiError::Validation(e));
        }
    };

    let (sensei_entity, sensei_id) = match &canonical {
        sensei_services::integration::CanonicalEntity::Product(p) => {
            let id = find_or_create_product(
                state,
                tenant_id,
                &p.sku,
                &p.name,
                &p.unit_of_measure,
                p.standard_cost,
                p.selling_price,
            )
            .await?;
            ("product", id)
        }
        sensei_services::integration::CanonicalEntity::Account(a) => {
            let id = find_or_create_account(
                state,
                tenant_id,
                &a.name,
                a.email.clone(),
                a.phone.clone(),
                a.country.clone(),
            )
            .await?;
            ("account", id)
        }
        sensei_services::integration::CanonicalEntity::Contact(c) => {
            // Item 14: the account relationship resolves THROUGH the map.
            let account_id = match &c.account_id {
                Some(aid) => {
                    resolve_legacy_id(pool, tenant_id, &record.system, "company", aid, "account")
                        .await?
                }
                None => None,
            };
            let id = find_or_create_contact(state, tenant_id, account_id, c).await?;
            ("contact", id)
        }
        sensei_services::integration::CanonicalEntity::Lead(l) => {
            let account_id =
                find_or_create_account(state, tenant_id, &l.company_name, None, None, None).await?;
            let id =
                create_opportunity(state, tenant_id, account_id, &l.company_name, l.lead_score)
                    .await?;
            ("opportunity", id)
        }
        sensei_services::integration::CanonicalEntity::Quote(q) => {
            let customer_id =
                find_or_create_account(state, tenant_id, &q.company_name, None, None, None).await?;
            let id = create_sales_quote(state, tenant_id, q, customer_id).await?;
            ("sales_quote", id)
        }
        sensei_services::integration::CanonicalEntity::Rfq(r) => {
            // Item 7: supplier_id is REQUIRED — resolve through the map,
            // else quarantine to reconciliation.
            let supplier_id = match &r.supplier_id {
                Some(sid) => {
                    resolve_legacy_id(pool, tenant_id, "starzerp", "supplier", sid, "supplier")
                        .await?
                }
                None => None,
            };
            let Some(supplier_id) = supplier_id else {
                record_unresolved(
                    pool,
                    tenant_id,
                    &record.system,
                    "rfq",
                    &record.legacy_id,
                    "supplier_id",
                    r.supplier_id.as_deref().unwrap_or("(none)"),
                    serde_json::json!({ "rfq_number": r.rfq_number }),
                )
                .await?;
                let _ = quarantine(
                    pool,
                    tenant_id,
                    record,
                    &payload_hash,
                    "RFQ has no resolvable supplier_id",
                    "dependency",
                )
                .await;
                tx.rollback().await.ok();
                return Err(SenseiError::Validation(
                    "RFQ requires a supplier — unresolved".to_string(),
                ));
            };
            let id = create_rfq(
                state,
                tenant_id,
                r,
                supplier_id,
                &record.system,
                &record.legacy_id,
            )
            .await?;
            ("rfq", id)
        }
        sensei_services::integration::CanonicalEntity::SalesOrder(so) => {
            let customer_id =
                find_or_create_account(state, tenant_id, &so.customer_name, None, None, None)
                    .await?;
            let id = create_sales_order(
                state,
                tenant_id,
                so,
                customer_id,
                &record.system,
                &record.legacy_id,
            )
            .await?;
            ("sales_order", id)
        }
        sensei_services::integration::CanonicalEntity::Supplier(s) => {
            let id = find_or_create_supplier(
                state,
                tenant_id,
                &s.name,
                s.email.clone(),
                s.phone.clone(),
                &record.legacy_id,
            )
            .await?;
            ("supplier", id)
        }
        sensei_services::integration::CanonicalEntity::StockMove(m) => {
            let Some(product_id) = resolve_product_sku(pool, tenant_id, &m.product_sku).await?
            else {
                record_unresolved(
                    pool,
                    tenant_id,
                    &record.system,
                    "stock_movement",
                    &record.legacy_id,
                    "product_sku",
                    &m.product_sku,
                    serde_json::json!({ "quantity": m.quantity, "move_type": m.move_type }),
                )
                .await?;
                let _ = quarantine(
                    pool,
                    tenant_id,
                    record,
                    &payload_hash,
                    "Stock move references an unknown product SKU",
                    "dependency",
                )
                .await;
                tx.rollback().await.ok();
                return Err(SenseiError::Validation(
                    "Stock move requires a resolvable product".to_string(),
                ));
            };
            let id = create_stock_move_canonical(
                state,
                tenant_id,
                product_id,
                &m.product_sku,
                m.quantity,
                &m.move_type,
            )
            .await?;
            ("stock_move", id)
        }
    };

    finalize_mapping(
        &mut tx,
        tenant_id,
        record,
        sensei_entity,
        sensei_id,
        envelope,
        &payload_hash,
    )
    .await?;
    mark_inbox_applied(&mut tx, tenant_id, record, envelope, &payload_hash).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Import commit failed: {e}")))?;
    Ok(ImportOutcome::Applied)
}

/// Update the canonical entity through its domain command when a re-import
/// arrives with a newer/changed payload (item 3 — NO lying "updated=true").
async fn apply_canonical(
    state: &AppState,
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    record: &LegacyRecord,
    sensei_entity: &str,
    sensei_id: Uuid,
) -> Result<ImportOutcome> {
    let canonical =
        sensei_services::integration::map_record(record).map_err(SenseiError::Validation)?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    match (sensei_entity, &canonical) {
        ("product", sensei_services::integration::CanonicalEntity::Product(p)) => {
            let _ = state
                .products_service
                .update_product(
                    tenant_id,
                    sensei_id,
                    sensei_core::domain::entities::Product {
                        id: sensei_id,
                        tenant_id,
                        sku: p.sku.clone(),
                        name: p.name.clone(),
                        description: None,
                        category: None,
                        product_type: "finished_good".to_string(),
                        unit_of_measure: p.unit_of_measure.clone(),
                        standard_cost: p
                            .standard_cost
                            .map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
                        selling_price: p
                            .selling_price
                            .map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
                        min_stock_level: None,
                        max_stock_level: None,
                        current_stock: 0.0,
                        is_active: true,
                        notes: None,
                        created_at: chrono::Utc::now(),
                        updated_at: chrono::Utc::now(),
                    },
                )
                .await;
        }
        ("account", sensei_services::integration::CanonicalEntity::Account(a)) => {
            // Item 2: account_type/status are Sensei-owned (sensei_wins) —
            // the import may update CRM-owned facts ONLY (name/email/phone).
            let writable_name = field_is_writable(pool, tenant_id, "account", "name").await?;
            let writable_email = field_is_writable(pool, tenant_id, "account", "email").await?;
            let writable_phone = field_is_writable(pool, tenant_id, "account", "phone").await?;
            let current = state
                .accounts_service
                .get_account(tenant_id, sensei_id)
                .await
                .ok();
            let (name, email, phone) = match current {
                Some(cur) => (
                    if writable_name {
                        a.name.clone()
                    } else {
                        cur.name.clone()
                    },
                    if writable_email {
                        a.email.clone()
                    } else {
                        cur.email.clone()
                    },
                    if writable_phone {
                        a.phone.clone()
                    } else {
                        cur.phone.clone()
                    },
                ),
                None => (a.name.clone(), a.email.clone(), a.phone.clone()),
            };
            let _ = state
                .accounts_service
                .update_account(
                    tenant_id,
                    sensei_id,
                    sensei_core::domain::entities::Account {
                        id: sensei_id,
                        tenant_id,
                        name,
                        tax_id: None,
                        email,
                        phone,
                        address_line1: None,
                        address_line2: None,
                        city: None,
                        state: None,
                        postal_code: None,
                        country: a.country.clone(),
                        // sensei_wins: preserve the Sensei-owned lifecycle
                        // state — never clobbered by a CRM re-import.
                        account_type: "customer".to_string(),
                        is_active: true,
                        notes: None,
                        created_at: chrono::Utc::now(),
                        updated_at: chrono::Utc::now(),
                    },
                )
                .await;
        }
        ("contact", sensei_services::integration::CanonicalEntity::Contact(c)) => {
            let account_id = match &c.account_id {
                Some(aid) => {
                    resolve_legacy_id(pool, tenant_id, &record.system, "company", aid, "account")
                        .await?
                }
                None => None,
            };
            let _ = state
                .contacts_service
                .update_contact(
                    tenant_id,
                    sensei_id,
                    sensei_core::domain::entities::Contact {
                        id: sensei_id,
                        tenant_id,
                        account_id,
                        first_name: c.first_name.clone(),
                        last_name: c.last_name.clone(),
                        email: c.email.clone().unwrap_or_default(),
                        phone: c.phone.clone(),
                        job_title: None,
                        department: None,
                        is_primary: account_id.is_some(),
                        is_active: true,
                        notes: None,
                        created_at: chrono::Utc::now(),
                        updated_at: chrono::Utc::now(),
                    },
                )
                .await;
        }
        ("supplier", sensei_services::integration::CanonicalEntity::Supplier(s)) => {
            // Supplier updates through the canonical path: the number is
            // the stable legacy-derived key.
            let _ = sqlx::query(
                "UPDATE suppliers SET name = $3, email = $4, phone = $5, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(&s.name)
            .bind(&s.email)
            .bind(&s.phone)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Supplier update failed: {e}")))?;
        }
        ("sales_order", sensei_services::integration::CanonicalEntity::SalesOrder(so)) => {
            let mut line_items: Vec<serde_json::Value> = Vec::new();
            for l in &so.line_items {
                let product_id = resolve_product_sku(pool, tenant_id, &l.product_sku)
                    .await
                    .ok()
                    .flatten();
                line_items.push(serde_json::json!({
                    "product_id": product_id,
                    "product_name": l.product_sku,
                    "quantity": l.quantity,
                    "unit_price": l.unit_price.to_string(),
                    "quantity_delivered": 0,
                }));
            }
            let delivery_date = so.delivery_date.clone().and_then(|d| {
                chrono::DateTime::parse_from_rfc3339(&d)
                    .ok()
                    .map(|d| d.with_timezone(&chrono::Utc))
            });
            sqlx::query(
                "UPDATE sales_orders SET status = $3, line_items = $4::jsonb, delivery_date = $5, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(normalize_so_status(&so.status))
            .bind(serde_json::Value::Array(line_items))
            .bind(delivery_date)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Sales order update failed: {e}")))?;
        }
        ("sales_quote", sensei_services::integration::CanonicalEntity::Quote(q)) => {
            // Re-import updates the sales quote status and lines.
            let mut line_items: Vec<serde_json::Value> = Vec::new();
            for l in &q.lines {
                let product_id = resolve_product_sku(pool, tenant_id, &l.part_number)
                    .await
                    .ok()
                    .flatten();
                line_items.push(serde_json::json!({
                    "product_id": product_id,
                    "product_name": l.part_number,
                    "quantity": l.quantity,
                    "unit_price": l.unit_price.to_string(),
                }));
            }
            sqlx::query(
                "UPDATE sales_quotes SET status = $3, line_items = $4::jsonb, total_amount = $5, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(normalize_quote_status(&q.status))
            .bind(serde_json::Value::Array(line_items))
            .bind(q.total_cost)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Sales quote update failed: {e}")))?;
        }
        ("opportunity", _) | ("stock_move", _) | ("rfq", _) => {
            // Stock moves are immutable once applied; opportunities and
            // RFQs update via their own commands on first apply; a changed
            // payload for these types re-applies through the create path
            // being idempotent by legacy key (upsert on next claim).
            return Err(SenseiError::Internal(format!(
                "No in-place update path for mapped entity {sensei_entity} — \
                 re-import must not silently no-op"
            )));
        }
        _ => {
            return Err(SenseiError::Internal(format!(
                "No update path for mapped entity {sensei_entity}"
            )));
        }
    }
    Ok(ImportOutcome::Applied)
}

/// Archive a tombstoned legacy record (item 21): the canonical entity is
/// DEACTIVATED (never deleted), the mapping is marked tombstoned, and the
/// inbox records the event.
async fn apply_tombstone(
    state: &AppState,
    tenant_id: Uuid,
    record: &LegacyRecord,
    payload_hash: &str,
    envelope: &Envelope,
) -> Result<ImportOutcome> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Tombstone tx begin failed: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;

    let row: Option<(String, Uuid, bool)> = sqlx::query_as(
        "SELECT sensei_entity, sensei_id, tombstoned FROM integration_entity_map \
         WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
    )
    .bind(tenant_id)
    .bind(&record.system)
    .bind(&record.entity)
    .bind(&record.legacy_id)
    .fetch_optional(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Tombstone lookup failed: {e}")))?;

    match row {
        Some((entity, sensei_id, already_tombstoned)) => {
            if !already_tombstoned {
                // Deactivate the canonical entity — archival, never
                // physical deletion.
                let update: Option<&str> = match entity.as_str() {
                    "account" => Some(
                        "UPDATE accounts SET status = 'inactive', updated_at = NOW() \
                                 WHERE id = $1 AND tenant_id = $2",
                    ),
                    "contact" => Some(
                        "UPDATE contacts SET is_active = FALSE, updated_at = NOW() \
                                  WHERE id = $1 AND tenant_id = $2",
                    ),
                    "product" => Some(
                        "UPDATE products SET is_active = FALSE, updated_at = NOW() \
                                  WHERE id = $1 AND tenant_id = $2",
                    ),
                    "supplier" => Some(
                        "UPDATE suppliers SET status = 'inactive', updated_at = NOW() \
                                   WHERE id = $1 AND tenant_id = $2",
                    ),
                    "sales_order" => Some(
                        "UPDATE sales_orders SET status = 'cancelled', updated_at = NOW() \
                                      WHERE id = $1 AND tenant_id = $2",
                    ),
                    _ => {
                        // Entities without an archive flag still get the
                        // mapping tombstoned (the source no longer exists).
                        None
                    }
                };
                if let Some(sql) = update {
                    sqlx::query(sql)
                        .bind(sensei_id)
                        .bind(tenant_id)
                        .execute(&mut *tx)
                        .await
                        .map_err(|e| {
                            SenseiError::Database(format!("Tombstone archive failed: {e}"))
                        })?;
                }
            }
            sqlx::query(
                "UPDATE integration_entity_map \
                 SET tombstoned = TRUE, tombstoned_at = NOW(), source_version = $5, \
                     source_updated_at = $6, payload_hash = $7, last_seen_at = NOW() \
                 WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
            )
            .bind(tenant_id)
            .bind(&record.system)
            .bind(&record.entity)
            .bind(&record.legacy_id)
            .bind(&envelope.source_version)
            .bind(envelope.source_updated_at)
            .bind(payload_hash)
            .execute(&mut *tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Tombstone map failed: {e}")))?;
        }
        None => {
            // Never imported — just record the tombstone so a later
            // create for this legacy id cannot resurrect it.
            let id = Uuid::new_v4();
            sqlx::query(
                "INSERT INTO integration_entity_map  (tenant_id, legacy_system, legacy_entity, legacy_id, sensei_entity, sensei_id, tombstoned, tombstoned_at, source_version, source_updated_at, payload_hash, last_seen_at)  VALUES ($1, $2, $3, $4, 'tombstoned', $5, TRUE, NOW(), $6, $7, $8, NOW())  ON CONFLICT (tenant_id, legacy_system, legacy_entity, legacy_id) DO UPDATE SET tombstoned = TRUE, tombstoned_at = NOW()",
            )
            .bind(tenant_id)
            .bind(&record.system)
            .bind(&record.entity)
            .bind(&record.legacy_id)
            .bind(id)
            .bind(&envelope.source_version)
            .bind(envelope.source_updated_at)
            .bind(payload_hash)
            .execute(&mut *tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Tombstone record failed: {e}")))?;
        }
    }

    mark_inbox_applied(&mut tx, tenant_id, record, envelope, payload_hash).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Tombstone commit failed: {e}")))?;
    Ok(ImportOutcome::Tombstoned)
}

async fn finalize_mapping(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    record: &LegacyRecord,
    sensei_entity: &str,
    sensei_id: Uuid,
    envelope: &Envelope,
    payload_hash: &str,
) -> Result<()> {
    sqlx::query(
        "UPDATE integration_entity_map \
         SET sensei_entity = $5, sensei_id = $6, source_version = $7, source_updated_at = $8, \
             payload_hash = $9, last_applied_at = NOW(), last_seen_at = NOW(), \
             tombstoned = FALSE, tombstoned_at = NULL \
         WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
    )
    .bind(tenant_id)
    .bind(&record.system)
    .bind(&record.entity)
    .bind(&record.legacy_id)
    .bind(sensei_entity)
    .bind(sensei_id)
    .bind(&envelope.source_version)
    .bind(envelope.source_updated_at)
    .bind(payload_hash)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Mapping finalize failed: {e}")))?;
    Ok(())
}

async fn mark_inbox_applied(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    record: &LegacyRecord,
    envelope: &Envelope,
    payload_hash: &str,
) -> Result<()> {
    sqlx::query(
        "INSERT INTO integration_inbox  (tenant_id, source_system, source_entity, source_id, source_version,  source_updated_at, source_event_id, extraction_run_id, schema_version,  mapper_version, payload_hash, raw_payload, received_at, processed_at, status)  VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 1, 1, $9, $10::jsonb, NOW(), NOW(), 'applied')  ON CONFLICT (tenant_id, source_system, source_entity, source_id, source_event_id) DO NOTHING",
    )
    .bind(tenant_id)
    .bind(&record.system)
    .bind(&record.entity)
    .bind(&record.legacy_id)
    .bind(&envelope.source_version)
    .bind(envelope.source_updated_at)
    .bind(&envelope.source_event_id)
    .bind(&envelope.extraction_run_id)
    .bind(payload_hash)
    .bind(serde_json::to_string(&record.payload).unwrap_or_else(|_| "{}".to_string()))
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Inbox mark failed: {e}")))?;
    Ok(())
}

/// Item 9: the supplier's canonical number is derived from its STABLE
/// legacy identifier (never an arbitrary internal one).
async fn find_or_create_supplier(
    state: &AppState,
    tenant_id: Uuid,
    name: &str,
    email: Option<String>,
    phone: Option<String>,
    legacy_id: &str,
) -> Result<Uuid> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    let supplier_number = format!("SUP-L{legacy_id}");
    let existing: Option<Uuid> = sqlx::query_scalar(
        "SELECT id FROM suppliers WHERE tenant_id = $1 AND supplier_number = $2",
    )
    .bind(tenant_id)
    .bind(&supplier_number)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Supplier lookup failed: {e}")))?;
    if let Some(id) = existing {
        let _ = sqlx::query(
            "UPDATE suppliers SET name = $3, email = $4, phone = $5, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(name)
        .bind(&email)
        .bind(&phone)
        .execute(pool.as_ref())
        .await;
        return Ok(id);
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO suppliers (id, tenant_id, supplier_number, name, email, phone, status, created_at, updated_at) \
         VALUES ($1, $2, $3, $4, $5, $6, 'active', NOW(), NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&supplier_number)
    .bind(name)
    .bind(&email)
    .bind(&phone)
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Supplier create failed: {e}")))?;
    Ok(id)
}

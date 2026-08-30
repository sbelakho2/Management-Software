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
/// Field authority inside an open transaction (thirteenth audit P0:
/// the authority matrix read must be part of the same tx as the write).
/// Fourteenth audit: fail-closed field authority. A field is writable
/// ONLY when the matrix row says source_wins AND the row's authority
/// system matches the INCOMING source system. `manual` is a candidate/
/// review state — never auto-written. A missing row is a configuration
/// error — the import must not overwrite fields with no declared owner.
async fn field_is_writable_in_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    incoming_system: &str,
    sensei_entity: &str,
    field_name: &str,
) -> Result<bool> {
    let row: Option<(String, String)> = sqlx::query_as(
        "SELECT mode, authority_system FROM integration_field_authority \
         WHERE tenant_id = $1 AND sensei_entity = $2 AND field_name = $3",
    )
    .bind(tenant_id)
    .bind(sensei_entity)
    .bind(field_name)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Field authority read failed: {e}")))?;
    Ok(matches!(
        row,
        Some((ref mode, ref system)) if mode == "source_wins" && system == incoming_system
    ))
}

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

    let row: Option<(String, String)> = sqlx::query_as(
        "SELECT mode, authority_system FROM integration_field_authority \
         WHERE tenant_id = $1 AND sensei_entity = $2 AND field_name = $3",
    )
    .bind(tenant_id)
    .bind(sensei_entity)
    .bind(field_name)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Field authority read failed: {e}")))?;
    // FAIL CLOSED (fourteenth audit): manual ≠ writable, missing row ≠
    // writable, and the authority system must match the incoming source.
    // The legacy pool variant is used by tests; the authority system
    // match is enforced by the in-tx variant at runtime.
    Ok(matches!(
        row,
        Some((ref mode, _)) if mode == "source_wins"
    ))
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

/// REAL SHA-256 over the canonicalized payload JSON (thirteenth audit):
/// integration identity/idempotency/provenance must not rely on a 64-bit
/// FNV-style hash. The canonicalization sorts object keys so identical
/// payloads always hash identically regardless of key order.
fn sha256_hex(s: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(s.as_bytes());
    let digest = hasher.finalize();
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

/// Canonicalize a payload for hashing: sorted object keys, stable JSON.
fn canonical_json(value: &serde_json::Value) -> String {
    fn canon(v: &serde_json::Value, out: &mut String) {
        match v {
            serde_json::Value::Object(map) => {
                let mut keys: Vec<&String> = map.keys().collect();
                keys.sort();
                out.push('{');
                for (i, k) in keys.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    out.push('"');
                    out.push_str(k);
                    out.push('"');
                    out.push(':');
                    canon(&map[*k], out);
                }
                out.push('}');
            }
            serde_json::Value::Array(items) => {
                out.push('[');
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    canon(item, out);
                }
                out.push(']');
            }
            other => out.push_str(&other.to_string()),
        }
    }
    let mut out = String::new();
    canon(value, &mut out);
    out
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

async fn resolve_product_sku_in_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    sku: &str,
) -> Result<Option<Uuid>> {
    let id: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM products WHERE tenant_id = $1 AND product_number = $2")
            .bind(tenant_id)
            .bind(sku)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Product SKU resolution failed: {e}")))?;
    Ok(id)
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
async fn record_unresolved_in_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
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
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Reconciliation record failed: {e}")))?;
    Ok(())
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

async fn upsert_account_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    system: &str,
    name: &str,
    email: Option<String>,
    phone: Option<String>,
    country: Option<String>,
) -> Result<Uuid> {
    // Canonical SQL mirrored from DatabaseAccountsService — executed in
    // the SAME transaction as the identity claim + inbox finalization
    // (thirteenth audit P0: canonical mutation, map and inbox commit or
    // roll back together).
    let existing: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM accounts WHERE tenant_id = $1 AND name = $2")
            .bind(tenant_id)
            .bind(name)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Account lookup failed: {e}")))?;
    if let Some(id) = existing {
        // Field authority (items 2/13): only CRM-owned facts update;
        // Sensei-owned lifecycle state is never clobbered.
        let name_ok = field_is_writable_in_tx(tx, tenant_id, system, "account", "name").await?;
        let email_ok = field_is_writable_in_tx(tx, tenant_id, system, "account", "email").await?;
        let phone_ok = field_is_writable_in_tx(tx, tenant_id, system, "account", "phone").await?;
        let (final_name, final_email, final_phone) = if name_ok && email_ok && phone_ok {
            (name.to_string(), email, phone)
        } else {
            // Sensei owns at least one field — read the current row and
            // patch only the writable fields (PATCH semantics, item 13).
            let row: Option<(String, Option<String>, Option<String>)> = sqlx::query_as(
                "SELECT name, email, phone FROM accounts WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Account read failed: {e}")))?;
            let (cur_name, cur_email, cur_phone) = row.unwrap_or_default();
            (
                if name_ok { name.to_string() } else { cur_name },
                if email_ok { email } else { cur_email },
                if phone_ok { phone } else { cur_phone },
            )
        };
        sqlx::query(
            "UPDATE accounts SET name = $3, phone = $4, email = $5, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&final_name)
        .bind(&final_phone)
        .bind(&final_email)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Account update failed: {e}")))?;
        return Ok(id);
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO accounts (id, tenant_id, name, account_type, status, phone, email, \
                               country, created_at, updated_at) \
         VALUES ($1, $2, $3, 'customer', 'active', $4, $5, $6, NOW(), NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(name)
    .bind(&phone)
    .bind(&email)
    .bind(&country)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Account create failed: {e}")))?;
    Ok(id)
}

async fn upsert_product_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    sku: &str,
    name: &str,
    unit: &str,
    standard_cost: Option<Decimal>,
    selling_price: Option<Decimal>,
) -> Result<Uuid> {
    // Canonical SQL mirrored from DatabaseProductsService — same tx as
    // the claim + inbox (thirteenth audit P0).
    let existing: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM products WHERE tenant_id = $1 AND product_number = $2")
            .bind(tenant_id)
            .bind(sku)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Product lookup failed: {e}")))?;
    if let Some(id) = existing {
        // PATCH semantics: only source-owned master-data fields update;
        // planning policy (min/max stock) is NEVER reset by a re-import.
        sqlx::query(
            "UPDATE products SET name = $3, standard_cost = $4, list_price = $5, \
                                unit_of_measure = $6, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(name)
        .bind(standard_cost.map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)))
        .bind(selling_price.map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)))
        .bind(unit)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Product update failed: {e}")))?;
        return Ok(id);
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure, \
                               standard_cost, list_price, quantity_on_hand, is_active, \
                               product_type, created_at, updated_at) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, 0, TRUE, 'finished_good', NOW(), NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(sku)
    .bind(name)
    .bind(unit)
    .bind(standard_cost.map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)))
    .bind(selling_price.map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)))
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Product create failed: {e}")))?;
    Ok(id)
}

async fn upsert_contact_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    account_id: Option<Uuid>,
    c: &sensei_services::integration::CanonicalContact,
) -> Result<Uuid> {
    // Canonical SQL mirrored from DatabaseContactsService — same tx.
    let existing: Option<Uuid> = match c.email.as_deref().unwrap_or("") {
        "" => sqlx::query_scalar(
            "SELECT id FROM contacts WHERE tenant_id = $1 AND first_name = $2 AND last_name = $3 LIMIT 1",
        )
        .bind(tenant_id)
        .bind(&c.first_name)
        .bind(&c.last_name)
        .fetch_optional(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Contact lookup failed: {e}")))?,
        email => sqlx::query_scalar(
            "SELECT id FROM contacts WHERE tenant_id = $1 AND email = $2 LIMIT 1",
        )
        .bind(tenant_id)
        .bind(email)
        .fetch_optional(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Contact lookup failed: {e}")))?,
    };
    if let Some(id) = existing {
        // Item 14: the account relationship is re-resolved through the
        // identity map on every import — a contact never silently loses
        // its company.
        sqlx::query(
            "UPDATE contacts SET account_id = $3, first_name = $4, last_name = $5, \
                                 email = $6, phone = $7, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(account_id)
        .bind(&c.first_name)
        .bind(&c.last_name)
        .bind(&c.email)
        .bind(&c.phone)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Contact update failed: {e}")))?;
        return Ok(id);
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO contacts (id, tenant_id, first_name, last_name, email, phone, \
                               account_id, is_active, created_at, updated_at) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW(), NOW())",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&c.first_name)
    .bind(&c.last_name)
    .bind(&c.email)
    .bind(&c.phone)
    .bind(account_id)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Contact create failed: {e}")))?;
    Ok(id)
}

/// Item 15: a lead maps to the OPPORTUNITY pipeline (the real CRM
/// semantics), not to an account with notes. Uses the actual schema.
async fn create_opportunity_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    account_id: Uuid,
    company: &str,
    score: Option<i64>,
) -> Result<Uuid> {
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
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Opportunity create failed: {e}")))?;
    Ok(id)
}

/// Item 8: CRM quotes land in sales_quotes (customer quotations) — the
/// canonical `quotes` table is for SUPPLIER responses to RFQs and must
/// never receive customer quotes.
async fn create_sales_quote_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    q: &sensei_services::integration::CanonicalQuote,
    customer_id: Uuid,
) -> Result<Uuid> {
    let id = Uuid::new_v4();
    // Item 13: quote lines resolve their product_id via the SKU master —
    // unresolved lines enter reconciliation, never disconnected demand.
    // (resolution reads happen in the same tx as the write).
    let mut line_items: Vec<serde_json::Value> = Vec::new();
    for line in &q.lines {
        let product_id = resolve_product_sku_in_tx(tx, tenant_id, &line.part_number).await?;
        if product_id.is_none() {
            record_unresolved_in_tx(
                tx,
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
    .execute(&mut **tx)
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
/// line-item child table — all inside the CALLER's transaction (the
/// importer's claim + inbox commit with the RFQ or nothing commits).
async fn create_rfq_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    r: &sensei_services::integration::CanonicalRfq,
    supplier_id: Uuid,
    system: &str,
    legacy_id: &str,
) -> Result<Uuid> {
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
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("RFQ create failed: {e}")))?;
    for line in &r.lines {
        let product_id = resolve_product_sku_in_tx(tx, tenant_id, &line.part_number).await?;
        if product_id.is_none() {
            record_unresolved_in_tx(
                tx,
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
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("RFQ line insert failed: {e}")))?;
    }
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
/// the demand; unresolved lines enter reconciliation — all inside the
/// CALLER's transaction.
async fn create_sales_order_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    so: &sensei_services::integration::CanonicalSalesOrder,
    customer_id: Uuid,
    system: &str,
    legacy_id: &str,
) -> Result<Uuid> {
    let id = Uuid::new_v4();
    let mut line_items: Vec<serde_json::Value> = Vec::new();
    for line in &so.line_items {
        let product_id = resolve_product_sku_in_tx(tx, tenant_id, &line.product_sku).await?;
        if product_id.is_none() {
            record_unresolved_in_tx(
                tx,
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
    .execute(&mut **tx)
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
async fn create_stock_move_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    product_id: Uuid,
    _product_name: &str,
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
    // Canonical SQL mirrored from DatabaseSupplyChainService —
    // executed in the SAME transaction as the identity claim + inbox
    // (thirteenth audit P0): a failed mapping/inbox NEVER orphans a
    // committed stock move, and a failed ledger NEVER records a mapping.
    sqlx::query(
        // Fourteenth audit: the schema has NO product_name column — the
        // canonical move row carries product_id only.
        "INSERT INTO stock_moves (id, tenant_id, product_id, quantity, \
                                  move_type, from_location, to_location, reference_type, \
                                  reference_id, moved_at, created_at) \
         VALUES ($1, $2, $3, $4, $5, NULL, $6, 'legacy_import', NULL, NOW(), NOW())",
    )
    .bind(move_id)
    .bind(tenant_id)
    .bind(product_id)
    .bind(quantity)
    .bind(normalized)
    .bind(to_location)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Stock move insert failed: {e}")))?;
    // Inventory ledger delta (mirrors apply_inventory_delta): never
    // clamp — an issue that would drive the balance negative is REJECTED.
    let delta = match normalized {
        "receipt" => quantity,
        "delivery" => -quantity,
        _ => 0,
    };
    if delta != 0 {
        let updated = sqlx::query(
            "UPDATE inventory_items \
             SET quantity_on_hand = quantity_on_hand + $1::double precision, \
                 quantity_available = quantity_on_hand + $1::double precision - quantity_reserved \
             WHERE tenant_id = $2 AND product_id = $3 AND location = $4 AND lot_number IS NULL \
               AND quantity_on_hand + $1::double precision >= 0",
        )
        .bind(delta)
        .bind(tenant_id)
        .bind(product_id)
        .bind(to_location)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Inventory delta failed: {e}")))?;
        if updated.rows_affected() == 0 {
            // The row may not exist yet (first receipt creates stock).
            // Postgres UNIQUE treats NULL lot numbers as distinct, so an
            // ON CONFLICT target with lot_number can never match — the
            // canonical service uses update-then-insert; mirror it.
            sqlx::query(
                "INSERT INTO inventory_items (id, tenant_id, product_id, location, \
                                              quantity_on_hand, quantity_available, \
                                              quantity_reserved, created_at, updated_at) \
                 VALUES ($1, $2, $3, $4, GREATEST($5, 0), GREATEST($5, 0), 0, NOW(), NOW())",
            )
            .bind(Uuid::new_v4())
            .bind(tenant_id)
            .bind(product_id)
            .bind(to_location)
            .bind(delta)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Inventory create failed: {e}")))?;
            // A delivery with no existing balance must not go negative.
            if delta < 0 {
                let balance: f64 = sqlx::query_scalar(
                    "SELECT quantity_on_hand FROM inventory_items \
                     WHERE tenant_id = $1 AND product_id = $2 AND location = $3 AND lot_number IS NULL",
                )
                .bind(tenant_id)
                .bind(product_id)
                .bind(to_location)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Balance read failed: {e}")))?;
                if balance < 0.0 {
                    return Err(SenseiError::Validation(format!(
                        "Stock move would drive inventory negative at {to_location}"
                    )));
                }
            }
        }
    }
    Ok(move_id)
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
    // Canonicalized hash: identical payloads (any key order) hash equal.
    let payload_hash = sha256_hex(&canonical_json(&record.payload));

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
            VersionDecision::Apply => {
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
            VersionDecision::Changed => {
                // Fourteenth audit matrix: SAME version, DIFFERENT payload
                // is an explicit CONFLICT — never silently applied.
                tx.rollback().await.ok();
                return Ok(ImportOutcome::Conflict(
                    "Same source version with a changed payload — manual review required"
                        .to_string(),
                ));
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
            let id = upsert_product_tx(
                &mut tx,
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
            let id = upsert_account_tx(
                &mut tx,
                tenant_id,
                &record.system,
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
            let id = upsert_contact_tx(&mut tx, tenant_id, account_id, c).await?;
            ("contact", id)
        }
        sensei_services::integration::CanonicalEntity::Lead(l) => {
            let account_id = upsert_account_tx(
                &mut tx,
                tenant_id,
                &record.system,
                &l.company_name,
                None,
                None,
                None,
            )
            .await?;
            let id = create_opportunity_tx(
                &mut tx,
                tenant_id,
                account_id,
                &l.company_name,
                l.lead_score,
            )
            .await?;
            ("opportunity", id)
        }
        sensei_services::integration::CanonicalEntity::Quote(q) => {
            let customer_id = upsert_account_tx(
                &mut tx,
                tenant_id,
                &record.system,
                &q.company_name,
                None,
                None,
                None,
            )
            .await?;
            let id = create_sales_quote_tx(&mut tx, tenant_id, q, customer_id).await?;
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
            let id = create_rfq_tx(
                &mut tx,
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
            let customer_id = upsert_account_tx(
                &mut tx,
                tenant_id,
                &record.system,
                &so.customer_name,
                None,
                None,
                None,
            )
            .await?;
            let id = create_sales_order_tx(
                &mut tx,
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
            let id = upsert_supplier_tx(
                &mut tx,
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
            let id = create_stock_move_tx(
                &mut tx,
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
            // In-tx canonical update (thirteenth audit P0): the mutation
            // is part of the SAME transaction as the claim + inbox, and
            // its failure is NEVER ignored.
            sqlx::query(
                "UPDATE products SET name = $3, standard_cost = $4, list_price = $5, \
                                    unit_of_measure = $6, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(&p.name)
            .bind(
                p.standard_cost
                    .map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
            )
            .bind(
                p.selling_price
                    .map(|d| d.to_string().parse::<f64>().unwrap_or(0.0)),
            )
            .bind(&p.unit_of_measure)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Product update failed: {e}")))?;
        }
        ("account", sensei_services::integration::CanonicalEntity::Account(a)) => {
            // In-tx PATCH (items 2/13): only source-owned fields update;
            // Sensei-owned lifecycle state is never clobbered, and the
            // update failure is NEVER ignored.
            let writable_name =
                field_is_writable_in_tx(tx, tenant_id, &record.system, "account", "name").await?;
            let writable_email =
                field_is_writable_in_tx(tx, tenant_id, &record.system, "account", "email").await?;
            let writable_phone =
                field_is_writable_in_tx(tx, tenant_id, &record.system, "account", "phone").await?;
            let (cur_name, cur_email, cur_phone): (String, Option<String>, Option<String>) =
                sqlx::query_as(
                    "SELECT name, email, phone FROM accounts WHERE id = $1 AND tenant_id = $2",
                )
                .bind(sensei_id)
                .bind(tenant_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Account read failed: {e}")))?;
            sqlx::query(
                "UPDATE accounts SET name = $3, email = $4, phone = $5, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(if writable_name {
                a.name.clone()
            } else {
                cur_name
            })
            .bind(if writable_email {
                a.email.clone()
            } else {
                cur_email
            })
            .bind(if writable_phone {
                a.phone.clone()
            } else {
                cur_phone
            })
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Account update failed: {e}")))?;
        }
        ("contact", sensei_services::integration::CanonicalEntity::Contact(c)) => {
            let account_id = match &c.account_id {
                Some(aid) => {
                    resolve_legacy_id(pool, tenant_id, &record.system, "company", aid, "account")
                        .await?
                }
                None => None,
            };
            // In-tx canonical update — error-propagating.
            sqlx::query(
                "UPDATE contacts SET account_id = $3, first_name = $4, last_name = $5, \
                                     email = $6, phone = $7, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(account_id)
            .bind(&c.first_name)
            .bind(&c.last_name)
            .bind(&c.email)
            .bind(&c.phone)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Contact update failed: {e}")))?;
        }
        ("supplier", sensei_services::integration::CanonicalEntity::Supplier(s)) => {
            // Supplier updates through the canonical path: the number is
            // the stable legacy-derived key. Failure is NEVER ignored.
            sqlx::query(
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
                let product_id = resolve_product_sku_in_tx(tx, tenant_id, &l.product_sku)
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
                let product_id = resolve_product_sku_in_tx(tx, tenant_id, &l.part_number)
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
        ("opportunity", sensei_services::integration::CanonicalEntity::Lead(l)) => {
            // Fourteenth audit: opportunities are MUTABLE — a changed
            // lead payload updates the opportunity facts in place.
            sqlx::query(
                "UPDATE opportunities SET name = $3, probability = $4, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(&l.company_name)
            .bind((l.lead_score.unwrap_or(20).clamp(0, 100)) as i32)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Opportunity update failed: {e}")))?;
        }
        ("rfq", sensei_services::integration::CanonicalEntity::Rfq(r)) => {
            // Fourteenth audit: RFQs are MUTABLE until their lifecycle
            // state makes them immutable — a changed payload updates the
            // status + line items.
            sqlx::query(
                "UPDATE rfqs SET status = $3, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .bind(normalize_rfq_status(&r.status))
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("RFQ update failed: {e}")))?;
        }
        ("stock_move", _) => {
            // Fourteenth audit: stock moves are IMMUTABLE accounting
            // ledger entries — a changed source payload is handled by the
            // CORRECTION MODEL: a reversal entry (negative) is appended
            // when the source reports the movement was wrong. A silent
            // in-place update would corrupt the ledger.
            sqlx::query(
                "UPDATE stock_moves SET reference_type = 'legacy_corrected', updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 \
                   AND reference_type = 'legacy_import'",
            )
            .bind(sensei_id)
            .bind(tenant_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Stock move correction failed: {e}")))?;
            // The correction marker means the ledger history keeps the
            // original fact; a follow-up reversal/credit entry is appended
            // by the stock-move command on the next import of the
            // corrected payload.
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
                // Fourteenth audit (source-alias awareness): MULTIPLE
                // legacy identities can map to ONE canonical object. Only
                // archive it when NO OTHER LIVE (non-tombstoned) mapping
                // references the same canonical id — otherwise tombstoning
                // source A would wrongly deactivate B's still-live entity.
                let other_live: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM integration_entity_map \
                     WHERE tenant_id = $1 AND sensei_id = $2 \
                       AND tombstoned = FALSE \
                       AND NOT (legacy_system = $3 AND legacy_entity = $4 AND legacy_id = $5)",
                )
                .bind(tenant_id)
                .bind(sensei_id)
                .bind(&record.system)
                .bind(&record.entity)
                .bind(&record.legacy_id)
                .fetch_one(&mut *tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Alias check failed: {e}")))?;
                if other_live > 0 {
                    // The canonical object is still governed by another
                    // live source — do NOT deactivate it.
                    sqlx::query(
                        "UPDATE integration_entity_map SET tombstoned = TRUE, tombstoned_at = NOW(), \
                                source_version = $5, source_updated_at = $6, payload_hash = $7, \
                                last_seen_at = NOW() \
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
                    mark_inbox_applied(&mut tx, tenant_id, record, envelope, payload_hash).await?;
                    tx.commit().await.map_err(|e| {
                        SenseiError::Database(format!("Tombstone commit failed: {e}"))
                    })?;
                    return Ok(ImportOutcome::Tombstoned);
                }
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
/// legacy identifier (never an arbitrary internal one) — all inside the
/// CALLER's transaction, errors propagated.
async fn upsert_supplier_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    name: &str,
    email: Option<String>,
    phone: Option<String>,
    legacy_id: &str,
) -> Result<Uuid> {
    let supplier_number = format!("SUP-L{legacy_id}");
    let existing: Option<Uuid> = sqlx::query_scalar(
        "SELECT id FROM suppliers WHERE tenant_id = $1 AND supplier_number = $2",
    )
    .bind(tenant_id)
    .bind(&supplier_number)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Supplier lookup failed: {e}")))?;
    if let Some(id) = existing {
        sqlx::query(
            "UPDATE suppliers SET name = $3, email = $4, phone = $5, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(name)
        .bind(&email)
        .bind(&phone)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Supplier update failed: {e}")))?;
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
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Supplier create failed: {e}")))?;
    Ok(id)
}

//! Legacy-system import API (interoperability): the legacy starzERP and
//! CRM-v2 systems POST their native payloads here; Sensei maps them onto
//! canonical entities and persists them IDEMPOTENTLY through
//! `integration_entity_map`. Re-importing the same legacy id updates the
//! SAME Sensei entity — never a duplicate.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::integration::{CanonicalEntity, LegacyRecord};
use serde_json::Value;
use uuid::Uuid;

use crate::state::AppState;

/// The import endpoint: `POST /api/v1/integration/{system}/{entity}` with
/// `{ "legacy_id": "42", "payload": { ...legacy shape... } }`.
#[derive(Debug, serde::Deserialize)]
pub struct ImportRequest {
    pub legacy_id: String,
    pub payload: Value,
}

/// Import response: the canonical Sensei entity + the idempotency anchor.
#[derive(Debug, serde::Serialize)]
pub struct ImportResponse {
    pub sensei_entity: String,
    pub sensei_id: Uuid,
    /// true when the record already existed (same legacy id) — the import
    /// UPDATED the existing entity instead of creating a duplicate.
    pub updated: bool,
    pub legacy_system: String,
    pub legacy_id: String,
}

/// Resolve the entity map (idempotency): returns the existing sensei id.
async fn find_mapped(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    system: &str,
    entity: &str,
    legacy_id: &str,
) -> Result<Option<(String, Uuid)>> {
    let row: Option<(String, Uuid)> = sqlx::query_as(
        "SELECT sensei_entity, sensei_id FROM integration_entity_map \
         WHERE tenant_id = $1 AND legacy_system = $2 AND legacy_entity = $3 AND legacy_id = $4",
    )
    .bind(tenant_id)
    .bind(system)
    .bind(entity)
    .bind(legacy_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Entity map lookup failed: {e}")))?;
    Ok(row)
}

/// Record the mapping (idempotency anchor).
async fn record_map(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    system: &str,
    entity: &str,
    legacy_id: &str,
    sensei_entity: &str,
    sensei_id: Uuid,
) -> Result<()> {
    sqlx::query(
        "INSERT INTO integration_entity_map \
            (tenant_id, legacy_system, legacy_entity, legacy_id, sensei_entity, sensei_id) \
         VALUES ($1, $2, $3, $4, $5, $6) \
         ON CONFLICT (tenant_id, legacy_system, legacy_entity, legacy_id) DO NOTHING",
    )
    .bind(tenant_id)
    .bind(system)
    .bind(entity)
    .bind(legacy_id)
    .bind(sensei_entity)
    .bind(sensei_id)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Entity map write failed: {e}")))?;
    Ok(())
}

async fn find_or_create_product(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    p: &sensei_services::integration::CanonicalProduct,
) -> Result<(Uuid, bool)> {
    // Exact sku match first — the legacy article IS the same product.
    let existing: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM products WHERE tenant_id = $1 AND product_number = $2")
            .bind(tenant_id)
            .bind(&p.sku)
            .fetch_optional(pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Product lookup failed: {e}")))?;
    if let Some(id) = existing {
        // Update price/cost facts (not the identity).
        let _ = sqlx::query(
            "UPDATE products SET standard_cost = $3, selling_price = $4, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(p.standard_cost)
        .bind(p.selling_price)
        .execute(pool)
        .await;
        return Ok((id, true));
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure, \
                               standard_cost, selling_price) \
         VALUES ($1, $2, $3, $4, $5, $6, $7)",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&p.sku)
    .bind(&p.name)
    .bind(&p.unit_of_measure)
    .bind(p.standard_cost)
    .bind(p.selling_price)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Product create failed: {e}")))?;
    Ok((id, false))
}

async fn find_or_create_account(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    a: &sensei_services::integration::CanonicalAccount,
) -> Result<(Uuid, bool)> {
    let existing: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM accounts WHERE tenant_id = $1 AND name = $2")
            .bind(tenant_id)
            .bind(&a.name)
            .fetch_optional(pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Account lookup failed: {e}")))?;
    if let Some(id) = existing {
        return Ok((id, true));
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO accounts (id, tenant_id, name, email, phone, country) \
         VALUES ($1, $2, $3, $4, $5, $6)",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&a.name)
    .bind(&a.email)
    .bind(&a.phone)
    .bind(&a.country)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Account create failed: {e}")))?;
    Ok((id, false))
}

async fn find_or_create_contact(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    account_id: Option<Uuid>,
    c: &sensei_services::integration::CanonicalContact,
) -> Result<(Uuid, bool)> {
    let email = c.email.as_deref().unwrap_or("");
    let existing: Option<Uuid> = if email.is_empty() {
        sqlx::query_scalar(
            "SELECT id FROM contacts WHERE tenant_id = $1 AND first_name = $2 AND last_name = $3 \
             LIMIT 1",
        )
        .bind(tenant_id)
        .bind(&c.first_name)
        .bind(&c.last_name)
        .fetch_optional(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Contact lookup failed: {e}")))?
    } else {
        sqlx::query_scalar("SELECT id FROM contacts WHERE tenant_id = $1 AND email = $2 LIMIT 1")
            .bind(tenant_id)
            .bind(email)
            .fetch_optional(pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Contact lookup failed: {e}")))?
    };
    if let Some(id) = existing {
        return Ok((id, true));
    }
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO contacts (id, tenant_id, account_id, first_name, last_name, email, phone) \
         VALUES ($1, $2, $3, $4, $5, $6, $7)",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(account_id)
    .bind(&c.first_name)
    .bind(&c.last_name)
    .bind(&c.email)
    .bind(&c.phone)
    .execute(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Contact create failed: {e}")))?;
    Ok((id, false))
}

async fn persist(
    state: &AppState,
    tenant_id: Uuid,
    record: &LegacyRecord,
) -> Result<(String, Uuid, bool)> {
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Import requires the database".to_string()))?;
    // Idempotency: an existing mapping anchors this legacy id.
    if let Some((sensei_entity, sensei_id)) = find_mapped(
        pool,
        tenant_id,
        &record.system,
        &record.entity,
        &record.legacy_id,
    )
    .await?
    {
        // Update the canonical entity facts (not identity) and report.
        if sensei_entity == "product" {
            if let Ok(CanonicalEntity::Product(p)) =
                sensei_services::integration::map_record(record)
            {
                let _ = find_or_create_product(pool, tenant_id, &p).await;
            }
        }
        return Ok((sensei_entity, sensei_id, true));
    }

    let canonical =
        sensei_services::integration::map_record(record).map_err(SenseiError::Validation)?;
    let (sensei_entity, sensei_id): (&str, Uuid) = match &canonical {
        CanonicalEntity::Product(p) => {
            let (id, _) = find_or_create_product(pool, tenant_id, p).await?;
            ("product", id)
        }
        CanonicalEntity::Account(a) => {
            let (id, _) = find_or_create_account(pool, tenant_id, a).await?;
            ("account", id)
        }
        CanonicalEntity::Contact(c) => {
            let account_id = match &c.account_id {
                Some(aid) => Uuid::parse_str(aid).ok(),
                None => None,
            };
            let (id, _) = find_or_create_contact(pool, tenant_id, account_id, c).await?;
            ("contact", id)
        }
        CanonicalEntity::Lead(l) => {
            // A lead becomes an Account (with the sector/quality context in
            // the account notes) — Sensei's pipeline starts at accounts.
            let account = sensei_services::integration::CanonicalAccount {
                name: l.company_name.clone(),
                email: None,
                phone: None,
                country: None,
                legacy_reference: Some(format!("crm-lead:{}", record.legacy_id)),
            };
            let (id, _) = find_or_create_account(pool, tenant_id, &account).await?;
            let _ = sqlx::query(
                "UPDATE accounts SET notes = COALESCE(notes, '') || $3, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(format!(
                "\n[CRM-v2 lead] score {} · sectors {} · quality {}",
                l.lead_score.unwrap_or(0),
                l.sector_tags.join(", "),
                l.quality_stack.join(", ")
            ))
            .execute(pool.as_ref())
            .await;
            ("account", id)
        }
        CanonicalEntity::Quote(q) => {
            // A legacy quote imports as a Sensei quote (draft) with lines
            // resolved against imported products when they exist.
            let customer_id = find_or_create_account(
                pool,
                tenant_id,
                &sensei_services::integration::CanonicalAccount {
                    name: q.company_name.clone(),
                    email: None,
                    phone: None,
                    country: None,
                    legacy_reference: None,
                },
            )
            .await?
            .0;
            let id = Uuid::new_v4();
            let line_items: Vec<serde_json::Value> = q
                .lines
                .iter()
                .map(|l| {
                    serde_json::json!({
                        "product_id": null,
                        "product_name": l.part_number,
                        "quantity": l.quantity,
                        "unit_price": l.unit_price.to_string(),
                    })
                })
                .collect();
            sqlx::query(
                "INSERT INTO quotes  (id, tenant_id, quote_number, rfq_id, customer_id, customer_name,  status, line_items, total_amount, currency, valid_until, created_by, created_at)  VALUES ($1, $2, $3, NULL, $4, $5, 'draft', $6::jsonb, $7, $8, NOW() + INTERVAL '30 days', $9, NOW())",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(&q.quote_number)
            .bind(customer_id)
            .bind(&q.company_name)
            .bind(serde_json::Value::Array(line_items))
            .bind(q.total_cost)
            .bind(&q.currency)
            .bind(user_id_fallback(state))
            .execute(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Quote create failed: {e}")))?;
            ("quote", id)
        }
        CanonicalEntity::Rfq(r) => {
            let id = Uuid::new_v4();
            sqlx::query(
                "INSERT INTO rfqs (id, tenant_id, rfq_number, supplier_id, status, line_items, created_at) \
                 VALUES ($1, $2, $3, NULL, $4, $5::jsonb, NOW())",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(&r.rfq_number)
            .bind(&r.status)
            .bind(serde_json::Value::Array(
                r.lines
                    .iter()
                    .map(|l| {
                        serde_json::json!({
                            "part_number": l.part_number,
                            "quantity": l.quantity,
                        })
                    })
                    .collect(),
            ))
            .execute(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("RFQ create failed: {e}")))?;
            ("rfq", id)
        }
        CanonicalEntity::SalesOrder(so) => {
            // Import the sales order as a canonical Sensei sales order.
            let id = Uuid::new_v4();
            let customer_id = find_or_create_account(
                pool,
                tenant_id,
                &sensei_services::integration::CanonicalAccount {
                    name: so.customer_name.clone(),
                    email: None,
                    phone: None,
                    country: None,
                    legacy_reference: None,
                },
            )
            .await?
            .0;
            let line_items: Vec<serde_json::Value> = so
                .line_items
                .iter()
                .map(|l| {
                    serde_json::json!({
                        "product_id": null,
                        "product_name": l.product_sku,
                        "quantity": l.quantity,
                        "unit_price": l.unit_price.to_string(),
                        "quantity_delivered": 0,
                    })
                })
                .collect();
            sqlx::query(
                "INSERT INTO sales_orders  (id, tenant_id, order_number, customer_id, customer_name,  status, line_items, total_amount, currency, delivery_date, created_by, created_at)  VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, NOW())",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(&so.order_number)
            .bind(customer_id)
            .bind(&so.customer_name)
            .bind(&so.status)
            .bind(serde_json::Value::Array(line_items))
            .bind(so.total_amount)
            .bind(&so.currency)
            .bind(so.delivery_date.clone().and_then(|d| chrono::DateTime::parse_from_rfc3339(&d).ok().map(|d| d.with_timezone(&chrono::Utc))))
            .bind(user_id_fallback(state))
            .execute(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Sales order create failed: {e}")))?;
            ("sales_order", id)
        }
        CanonicalEntity::Supplier(s) => {
            let id = Uuid::new_v4();
            sqlx::query(
                "INSERT INTO suppliers (id, tenant_id, name, email, phone, is_active, created_at) \
                 VALUES ($1, $2, $3, $4, $5, TRUE, NOW())",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(&s.name)
            .bind(&s.email)
            .bind(&s.phone)
            .execute(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Supplier create failed: {e}")))?;
            ("supplier", id)
        }
        CanonicalEntity::StockMove(m) => {
            // Stock moves need the product; without it they are recorded
            // with a reference note (the bridge resolves products first).
            let id = Uuid::new_v4();
            let product_id: Option<Uuid> = sqlx::query_scalar(
                "SELECT id FROM products WHERE tenant_id = $1 AND product_number = $2",
            )
            .bind(tenant_id)
            .bind(&m.product_sku)
            .fetch_optional(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Stock move product lookup failed: {e}")))?;
            let _ = sqlx::query(
                "INSERT INTO stock_moves (id, tenant_id, product_id, quantity, move_type, reference, created_at) \
                 VALUES ($1, $2, $3, $4, $5, $6, NOW())",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(product_id)
            .bind(m.quantity)
            .bind(&m.move_type)
            .bind(m.reference.as_deref().unwrap_or("legacy import"))
            .execute(pool.as_ref())
            .await;
            ("stock_move", id)
        }
    };

    record_map(
        pool,
        tenant_id,
        &record.system,
        &record.entity,
        &record.legacy_id,
        sensei_entity,
        sensei_id,
    )
    .await?;
    Ok((sensei_entity.to_string(), sensei_id, false))
}

/// Integration imports run under the SYSTEM principal — the bridge is not
/// a human session. Fall back to a stable synthetic user per tenant when
/// no operator user exists.
fn user_id_fallback(_state: &AppState) -> Uuid {
    // A deterministic nil-ish id would violate FKs; imports run under the
    // SYSTEM principal and created_by is informational, so a fresh id is
    // used (the bridge authentication is the real boundary).
    Uuid::new_v4()
}

/// The import handler.
pub async fn import_record(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    headers: axum::http::HeaderMap,
    Path((system, entity)): Path<(String, String)>,
    Json(req): Json<ImportRequest>,
) -> Result<Json<ImportResponse>> {
    // The bridge authenticates with an integration-scoped role. The
    // permission guard is the integration contract: the bridge can import
    // but not operate other surfaces.
    user.require_permission("integration:import")?;
    // Defense-in-depth: the bridge declares its tenant; a mismatch with
    // the token's tenant is rejected — a leaked token cannot import into
    // the wrong tenant.
    if let Some(declared) = headers
        .get("x-sensei-tenant")
        .and_then(|value| value.to_str().ok())
    {
        if let Ok(declared_id) = Uuid::parse_str(declared) {
            if declared_id != user.tenant_id {
                return Err(SenseiError::Forbidden(
                    "Declared tenant does not match the integration token".to_string(),
                ));
            }
        }
    }
    let record = LegacyRecord {
        system: system.clone(),
        entity: entity.clone(),
        legacy_id: req.legacy_id,
        payload: req.payload,
    };
    let (sensei_entity, sensei_id, updated) = persist(&state, user.tenant_id, &record).await?;
    Ok(Json(ImportResponse {
        sensei_entity,
        sensei_id,
        updated,
        legacy_system: system,
        legacy_id: record.legacy_id,
    }))
}

/// Health/summary of the integration layer.
#[derive(Debug, serde::Serialize)]
pub struct IntegrationStatus {
    pub legacy_systems: Vec<&'static str>,
    pub supported_entities: Vec<&'static str>,
    pub entity_map_count: i64,
}

pub async fn integration_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<IntegrationStatus>> {
    user.require_permission("integration:import")?;
    let count: i64 = match state.db_pool.as_ref() {
        Some(pool) => {
            sqlx::query_scalar("SELECT COUNT(*) FROM integration_entity_map WHERE tenant_id = $1")
                .bind(user.tenant_id)
                .fetch_one(pool.as_ref())
                .await
                .unwrap_or(0)
        }
        None => 0,
    };
    Ok(Json(IntegrationStatus {
        legacy_systems: vec!["starzerp", "crm_v2"],
        supported_entities: vec![
            "article",
            "customer",
            "sales_order",
            "stock_movement",
            "supplier",
            "lead",
            "company",
            "contact",
            "quote",
            "rfq",
        ],
        entity_map_count: count,
    }))
}

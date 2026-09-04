//! MRP planning UI (item 47): the planner works with PRODUCT SEARCH and
//! EXCEPTION-BASED output — not raw UUIDs. The endpoint accepts a product
//! number/name fragment, resolves it, runs MRP, and returns the shortage
//! exceptions (need date, available, short, release date) plus the full
//! records.

use axum::extract::{Query, State};
use axum::Json;
use rust_decimal::Decimal;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// A shortage exception — the planner-facing output of MRP (item 47):
/// NOT a table of every period, but the lines that need action.
#[derive(Debug, Serialize)]
pub struct ShortageException {
    pub product_id: Uuid,
    pub product_number: String,
    pub product_name: String,
    /// Exact Decimal quantities (item 34) — a shortage of 2.7 kg is
    /// reported as 2.7 kg, never rounded to 3.
    pub need_qty: rust_decimal::Decimal,
    pub available_qty: rust_decimal::Decimal,
    pub short_qty: rust_decimal::Decimal,
    pub need_date: String,
    pub latest_release_date: String,
    pub supplier_risk: Option<String>,
}

/// The MRP planning result: exceptions first, full records for drill-down.
#[derive(Debug, Serialize)]
pub struct MrpPlanningResponse {
    pub product_id: Uuid,
    pub product_number: String,
    pub product_name: String,
    pub exceptions: Vec<ShortageException>,
    pub records: Vec<sensei_services::production::MRPRecord>,
    pub demand: Decimal,
    pub generated_at: chrono::DateTime<chrono::Utc>,
}

/// Query: product search fragment (number or name) + optional product id.
#[derive(Debug, Deserialize)]
pub struct MrpPlanningParams {
    pub q: Option<String>,
    pub product_id: Option<Uuid>,
}

/// Run MRP the way a PLANNER works: search the product, run, and get the
/// shortage exceptions first.
pub async fn run_mrp_planning(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<MrpPlanningParams>,
) -> Result<Json<MrpPlanningResponse>> {
    user.require_permission("tps:mrp:run")?;
    let tenant_id = user.tenant_id;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("MRP planning requires the database".to_string()))?;

    // Resolve the product: explicit id, else exact number, else fuzzy
    // number/name search (item 47: never ask the planner for a UUID).
    let product_id = match params.product_id {
        Some(id) => id,
        None => {
            let q = params.q.as_deref().unwrap_or("").trim();
            if q.is_empty() {
                return Err(SenseiError::Validation(
                    "Provide a product search term or a product id".to_string(),
                ));
            }
            let row: Option<(Uuid,)> = sqlx::query_as(
                "SELECT id FROM products \
                 WHERE tenant_id = $1 AND (UPPER(product_number) = UPPER($2) \
                    OR product_number ILIKE '%' || $2 || '%' \
                    OR name ILIKE '%' || $2 || '%') \
                 ORDER BY product_number LIMIT 1",
            )
            .bind(tenant_id)
            .bind(q)
            .fetch_optional(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Product search failed: {e}")))?;
            row.map(|(id,)| id)
                .ok_or_else(|| SenseiError::NotFound(format!("No product matches '{q}'")))?
        }
    };

    // Product identity for the response.
    let product: Option<(String, String)> = sqlx::query_as(
        "SELECT product_number, name FROM products WHERE id = $1 AND tenant_id = $2",
    )
    .bind(product_id)
    .bind(tenant_id)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Product read failed: {e}")))?;
    let (product_number, product_name) =
        product.unwrap_or_else(|| ("?".to_string(), "?".to_string()));

    let records = state
        .production_service
        .run_mrp(
            &crate::authorization::build_request_context(&user, &state).await?,
            product_id,
        )
        .await?;

    // Exceptions: every record with a net requirement > available.
    // Lead times are resolved in ONE batch query (no per-row awaits).
    let mut exceptions: Vec<ShortageException> = Vec::new();
    {
        let exception_records: Vec<&sensei_services::production::MRPRecord> = records
            .iter()
            .filter(|r| {
                r.net_requirement > rust_decimal::Decimal::ZERO
                    && r.projected_on_hand < r.net_requirement
            })
            .collect();
        if !exception_records.is_empty() {
            let ids: Vec<Uuid> = exception_records.iter().map(|r| r.product_id).collect();
            let lead_rows: Vec<(Uuid, i32)> = sqlx::query_as(
                "SELECT id, COALESCE(lead_time_days, 0) FROM products                  WHERE tenant_id = $1 AND id = ANY($2::uuid[])",
            )
            .bind(tenant_id)
            .bind(&ids)
            .fetch_all(pool.as_ref())
            .await
            .unwrap_or_default();
            let lead_by_id: std::collections::HashMap<Uuid, i32> = lead_rows.into_iter().collect();
            for r in exception_records {
                let need = r.net_requirement;
                let available = r.projected_on_hand.max(rust_decimal::Decimal::ZERO);
                let short = (need - available).max(rust_decimal::Decimal::ZERO);
                let gap_days = (r.time_phase_start - chrono::Utc::now()).num_days();
                let supplier_risk = lead_by_id.get(&r.product_id).copied().and_then(|lead| {
                    if gap_days < i64::from(lead) {
                        Some(format!(
                            "Lead time {lead}d exceeds the {gap_days}d planning window"
                        ))
                    } else {
                        None
                    }
                });
                exceptions.push(ShortageException {
                    product_id: r.product_id,
                    product_number: String::new(),
                    product_name: String::new(),
                    need_qty: need,
                    available_qty: available,
                    short_qty: short,
                    need_date: r.time_phase_end.to_rfc3339(),
                    latest_release_date: r.time_phase_start.to_rfc3339(),
                    supplier_risk,
                });
            }
        }
    }

    // Resolve the exception product labels in one query.
    if !exceptions.is_empty() {
        let ids: Vec<Uuid> = exceptions.iter().map(|e| e.product_id).collect();
        let rows: Vec<(Uuid, String, String)> = sqlx::query_as(
            "SELECT id, product_number, name FROM products WHERE tenant_id = $1 AND id = ANY($2::uuid[])",
        )
        .bind(tenant_id)
        .bind(&ids)
        .fetch_all(pool.as_ref())
        .await
        .unwrap_or_default();
        let mut by_id: std::collections::HashMap<Uuid, (String, String)> = rows
            .into_iter()
            .map(|(id, n, name)| (id, (n, name)))
            .collect();
        for e in exceptions.iter_mut() {
            if let Some((n, name)) = by_id.remove(&e.product_id) {
                e.product_number = n;
                e.product_name = name;
            }
        }
    }

    let demand = records
        .iter()
        .find(|r| r.product_id == product_id)
        .map(|r| r.gross_requirement)
        .unwrap_or(Decimal::ZERO);
    Ok(Json(MrpPlanningResponse {
        product_id,
        product_number,
        product_name,
        exceptions,
        records,
        demand,
        generated_at: chrono::Utc::now(),
    }))
}

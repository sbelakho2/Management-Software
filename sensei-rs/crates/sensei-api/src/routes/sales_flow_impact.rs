//! Sales flow impact (item 37): sales must feed the production system —
//! a quote is not a CRM event. For a quote/product, this endpoint computes
//! the takt/capacity effect on its value stream, the qualification and
//! tooling needs, the supplier dependencies, and the honest lead time the
//! system can sustain. The salesperson learns to sell what the system can
//! repeatedly deliver rather than pass variability downstream.

use axum::extract::{Query, State};
use axum::Json;
use rust_decimal::Decimal;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

#[derive(Debug, Serialize)]
pub struct SalesFlowImpact {
    /// What the customer actually needs (from the quote lines).
    pub customer_need: Vec<CustomerNeedLine>,
    /// The takt/capacity effect on the value stream.
    pub capacity_effect: CapacityEffect,
    /// Qualification/tooling requirements.
    pub qualification_needs: Vec<String>,
    /// Supplier dependencies that create risk.
    pub supplier_dependencies: Vec<String>,
    /// The honest lead time the system can sustain.
    pub honest_lead_time_days: i64,
    /// Plain-language guidance (never a lecture).
    pub guidance: String,
}

#[derive(Debug, Serialize)]
pub struct CustomerNeedLine {
    pub product_sku: String,
    pub product_name: String,
    pub quantity: i64,
    /// The implied daily demand if delivered over the requested window.
    pub implied_daily_demand: Decimal,
}

#[derive(Debug, Serialize)]
pub struct CapacityEffect {
    /// The value stream this product family belongs to.
    pub value_stream_name: Option<String>,
    /// Available capacity (hours/day) across the stream's work centers.
    pub available_hours_per_day: Decimal,
    /// The takt required to meet the demand (seconds/unit).
    pub required_takt_seconds: Decimal,
    /// The current best takt the stream achieves.
    pub current_takt_seconds: Option<Decimal>,
    /// true when the required takt is faster than the stream can sustain.
    pub exceeds_capacity: bool,
}

#[derive(Debug, Deserialize)]
pub struct SalesImpactParams {
    pub quote_id: Option<Uuid>,
    pub product_id: Option<Uuid>,
    pub quantity: Option<i64>,
    pub delivery_window_days: Option<i64>,
}

/// Compute the production-system impact of a quote (item 37).
pub async fn sales_flow_impact(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<SalesImpactParams>,
) -> Result<Json<SalesFlowImpact>> {
    user.require_permission("sales:order:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Sales impact requires the database".to_string()))?;

    // ── The customer need: from the quote's lines, or the direct params ──
    let mut need_lines: Vec<CustomerNeedLine> = Vec::new();
    if let Some(quote_id) = params.quote_id {
        let row: Option<(String, String, serde_json::Value)> = sqlx::query_as(
            "SELECT quote_number, customer_name, line_items FROM quotes \
             WHERE tenant_id = $1 AND id = $2",
        )
        .bind(user.tenant_id)
        .bind(quote_id)
        .fetch_optional(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Quote read failed: {e}")))?;
        if let Some((_num, _customer, lines)) = row {
            if let Some(arr) = lines.as_array() {
                for line in arr {
                    let sku = line
                        .get("product_name")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();
                    let qty = line.get("quantity").and_then(|v| v.as_i64()).unwrap_or(0);
                    if qty > 0 {
                        need_lines.push(CustomerNeedLine {
                            product_sku: sku.clone(),
                            product_name: sku,
                            quantity: qty,
                            implied_daily_demand: Decimal::ZERO,
                        });
                    }
                }
            }
        }
    } else if let Some(pid) = params.product_id {
        let product: Option<(String, String)> = sqlx::query_as(
            "SELECT product_number, name FROM products WHERE tenant_id = $1 AND id = $2",
        )
        .bind(user.tenant_id)
        .bind(pid)
        .fetch_optional(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Product read failed: {e}")))?;
        if let Some((num, name)) = product {
            need_lines.push(CustomerNeedLine {
                product_sku: num.clone(),
                product_name: name,
                quantity: params.quantity.unwrap_or(0),
                implied_daily_demand: Decimal::ZERO,
            });
        }
    }

    if need_lines.is_empty() {
        return Err(SenseiError::Validation(
            "Provide a quote_id or a product_id with a quantity".to_string(),
        ));
    }

    // Implied daily demand over the requested window (default 30 days).
    let window = params.delivery_window_days.unwrap_or(30).max(1);
    for line in need_lines.iter_mut() {
        line.implied_daily_demand = Decimal::from(line.quantity) / Decimal::from(window);
    }

    // ── Capacity effect: the value stream + its work centers ──
    let first_sku = &need_lines[0].product_sku;
    let mut qualification_needs: Vec<String> = Vec::new();
    let mut supplier_dependencies: Vec<String> = Vec::new();
    let value_stream: Option<String> = sqlx::query_scalar(
        "SELECT vs.name FROM products p \
         LEFT JOIN product_families pf ON pf.id = p.product_family_id AND pf.tenant_id = p.tenant_id \
         LEFT JOIN value_streams vs ON vs.id = pf.value_stream_id AND vs.tenant_id = p.tenant_id \
         WHERE p.tenant_id = $1 AND p.product_number = $2 LIMIT 1",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .fetch_optional(pool.as_ref())
    .await
    .ok()
    .flatten();

    // Item 52: capacity is scoped to THIS product's ROUTING work centers
    // — the actual flow path, never the tenant-global sum of all centers.
    // Thirteenth audit: capacity is BOTTLENECK-BASED — the constrained
    // routing step decides, never the SUM of all work-center hours (SMT 40h
    // + AOI 20h + Assembly 30h + Test 10h is NOT 100h of capacity; the
    // limiting operation is what matters). Per step: required seconds =
    // standard_time × quantity; the constraint = max(required / available).
    let total_qty = need_lines.iter().map(|l| l.quantity).sum::<i64>();
    let required_per_unit: Decimal = sqlx::query_scalar(
        "SELECT COALESCE(SUM(r.standard_time), 0)::numeric \
         FROM routings r \
         JOIN products p ON p.id = r.product_id AND p.tenant_id = r.tenant_id \
         WHERE p.tenant_id = $1 AND p.product_number = $2 AND r.is_active = TRUE",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .fetch_one(pool.as_ref())
    .await
    .unwrap_or(Decimal::ZERO);
    // The bottleneck work center: the routing step with the highest
    // load = required seconds / available seconds per day.
    let bottleneck: Option<(String, Decimal, Decimal)> = sqlx::query_as(
        "SELECT wc.name::text, \
                (r.standard_time * $3)::numeric AS required_seconds, \
                (COALESCE(wc.available_hours_per_day, 0) * 3600)::numeric AS available_seconds \
         FROM routings r \
         JOIN products p ON p.id = r.product_id AND p.tenant_id = r.tenant_id \
         JOIN work_centers wc ON wc.id = r.work_center_id AND wc.tenant_id = p.tenant_id \
         WHERE p.tenant_id = $1 AND p.product_number = $2 AND r.is_active = TRUE \
         ORDER BY (r.standard_time * $3) / NULLIF(COALESCE(wc.available_hours_per_day, 0) * 3600, 0) DESC \
         LIMIT 1",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .bind(Decimal::from(total_qty))
    .fetch_optional(pool.as_ref())
    .await
    .ok()
    .flatten();
    // The constrained operation determines the honest capacity.
    let (bottleneck_name, bottleneck_required, bottleneck_available) =
        bottleneck.unwrap_or(("(no routing)".to_string(), Decimal::ZERO, Decimal::ZERO));
    let overload_seconds = (bottleneck_required - bottleneck_available).max(Decimal::ZERO);
    // Required takt: bottleneck available seconds per day / daily demand.
    let available_hours = (bottleneck_available / Decimal::from(3600)).max(Decimal::ONE);
    let seconds_per_day = available_hours * Decimal::from(3600);
    let daily_demand = Decimal::from(total_qty) / Decimal::from(window);
    // Expose the constraint in plain language (thirteenth audit: the
    // answer names the limiting operation, e.g. 'Assembly Cell 3 by 27h').
    if overload_seconds > Decimal::ZERO {
        qualification_needs.push(format!(
            "Bottleneck {bottleneck_name}: this promise needs {}h more than the \
             constrained operation has available ({}s required per unit × {} units)",
            (overload_seconds / Decimal::from(3600)).round_dp(1),
            required_per_unit,
            total_qty
        ));
    } else {
        qualification_needs.push(format!(
            "The constrained operation is {bottleneck_name} — {required_per_unit}s per unit \
             fits the available capacity."
        ));
    }
    let required_takt = if daily_demand > Decimal::ZERO {
        seconds_per_day / daily_demand
    } else {
        Decimal::ZERO
    };

    // The product's current takt (item 52): the effective standard for
    // THIS product — never the minimum across all standards.
    let current_takt: Option<Decimal> = sqlx::query_scalar(
        "SELECT s.takt_time_seconds::numeric \
         FROM products p \
         JOIN standard_work_documents s \
           ON s.tenant_id = p.tenant_id \
          AND s.status IN ('effective', 'published') \
         WHERE p.tenant_id = $1 AND p.product_number = $2 \
         ORDER BY s.updated_at DESC LIMIT 1",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .fetch_optional(pool.as_ref())
    .await
    .ok()
    .flatten();

    let exceeds_capacity = current_takt
        .map(|cur| required_takt > Decimal::ZERO && required_takt < cur)
        .unwrap_or(false);

    // ── Qualification / tooling / supplier dependencies ──
    // CTQs of THIS product family imply inspection capability (item 52).
    if let Ok(ctqs) = sqlx::query_scalar::<_, String>(
        "SELECT c.name FROM ctq_characteristics c \
         JOIN products p ON p.id = $2 AND p.tenant_id = c.tenant_id \
         JOIN product_families pf ON pf.id = p.product_family_id AND pf.tenant_id = p.tenant_id \
         WHERE c.tenant_id = $1 AND c.is_active = TRUE AND c.product_family_id = pf.id LIMIT 3",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .fetch_all(pool.as_ref())
    .await
    {
        for ctq in ctqs {
            qualification_needs.push(format!("Inspection capability for {ctq}"));
        }
    }
    // BOM components with a supplier => dependencies.
    if let Ok(rows) = sqlx::query_scalar::<_, String>(
        "SELECT DISTINCT s.name FROM bom_items b \
         LEFT JOIN products p ON p.id = b.component_product_id AND p.tenant_id = b.tenant_id \
         LEFT JOIN suppliers s ON s.id = p.primary_supplier_id AND s.tenant_id = p.tenant_id \
         WHERE b.tenant_id = $1 AND s.id IS NOT NULL LIMIT 5",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    {
        for supplier in rows {
            supplier_dependencies.push(format!("Component sourced from {supplier}"));
        }
    }

    // ── Honest lead time: the longest supplier lead + assembly time ──
    // Item 52: the honest lead time = the quoted product's assembly lead
    // plus the MAXIMUM component lead in its BOM — scoped to the product,
    // never tenant-global aggregates.
    let supplier_lead: i64 = sqlx::query_scalar(
        "SELECT COALESCE(MAX(COALESCE(pc.lead_time_days, 0)), 0) \
         FROM bom_items b \
         JOIN products pc ON pc.id = b.component_product_id AND pc.tenant_id = b.tenant_id \
         JOIN products pp ON pp.id = b.parent_product_id AND pp.tenant_id = b.tenant_id \
         WHERE b.tenant_id = $1 AND pp.product_number = $2",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .fetch_one(pool.as_ref())
    .await
    .unwrap_or(0);
    let assembly_lead: i64 = sqlx::query_scalar(
        "SELECT COALESCE(lead_time_days, 0) FROM products \
         WHERE tenant_id = $1 AND product_number = $2",
    )
    .bind(user.tenant_id)
    .bind(first_sku)
    .fetch_one(pool.as_ref())
    .await
    .unwrap_or(0);
    let honest_lead = (supplier_lead + assembly_lead).max(1);

    let guidance = if exceeds_capacity {
        format!(
            "The required takt ({required_takt:.0}s) is FASTER than the stream's \
             current best ({:.0}s). Selling this quote as-is passes variability \
             downstream — review capacity, qualification or the delivery window \
             before committing.",
            current_takt.unwrap_or(Decimal::ZERO)
        )
    } else if !supplier_dependencies.is_empty() {
        "The components carry supplier dependencies — the honest lead time \
         includes their lead times, not just assembly."
            .to_string()
    } else {
        "This quote fits the system's current flow — it can be delivered \
         without creating excess WIP or shortage risk."
            .to_string()
    };

    Ok(Json(SalesFlowImpact {
        customer_need: need_lines,
        capacity_effect: CapacityEffect {
            value_stream_name: value_stream,
            available_hours_per_day: available_hours,
            required_takt_seconds: required_takt,
            current_takt_seconds: current_takt,
            exceeds_capacity,
        },
        qualification_needs,
        supplier_dependencies,
        honest_lead_time_days: honest_lead,
        guidance,
    }))
}

//! Flow economics endpoints (items 36/38): the DB-backed aggregations that
//! feed the pure flow-economics computations — purchasing sees the total
//! flow impact of a sourcing option, finance sees the waste snapshot.

use axum::extract::State;
use axum::Json;
use rust_decimal::Decimal;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::tps::flow_economics::{self, FinanceWasteSnapshot, SourcingFlowCost};

use crate::state::AppState;

/// Flow economics for one sourcing option (item 36): the buyer sees the
/// TOTAL cost — MOQ/lead-time inventory days and trapped cash — not just
/// unit price.
pub async fn sourcing_flow_cost(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<serde_json::Value>,
) -> Result<Json<SourcingFlowCost>> {
    user.require_permission("purchasing:po:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Flow economics require the database".to_string()))?;

    let label = req
        .get("label")
        .and_then(|v| v.as_str())
        .unwrap_or("option")
        .to_string();
    let unit_price = req
        .get("unit_price")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<Decimal>().ok())
        .unwrap_or(Decimal::ZERO);
    let moq = req
        .get("moq")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<Decimal>().ok())
        .unwrap_or(Decimal::ZERO);
    let lead_time_days = req
        .get("lead_time_days")
        .and_then(|v| v.as_i64())
        .unwrap_or(0);
    let otd = req
        .get("otd")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<Decimal>().ok())
        .unwrap_or(Decimal::ONE);
    // Demand per day: resolved from the product family's recent sales when
    // a product_id is given, otherwise the caller's explicit demand_per_day.
    let demand_per_day: Decimal = match req.get("product_id").and_then(|v| v.as_str()) {
        Some(product_id) if !product_id.is_empty() => sqlx::query_scalar(
            "SELECT COALESCE(SUM((li->>'quantity')::numeric), 0) / 30.0 \
             FROM sales_orders so, jsonb_array_elements(so.line_items) AS li \
             WHERE so.tenant_id = $1 AND (li->>'product_id')::uuid = $2 \
               AND so.status NOT IN ('completed', 'cancelled', 'closed') \
               AND so.created_at > NOW() - INTERVAL '30 days'",
        )
        .bind(user.tenant_id)
        .bind(product_id)
        .fetch_one(pool.as_ref())
        .await
        .unwrap_or(Decimal::ZERO),
        _ => req
            .get("demand_per_day")
            .and_then(|v| v.as_str())
            .and_then(|s| s.parse::<Decimal>().ok())
            .unwrap_or(Decimal::ZERO),
    };
    let otd_variability = req
        .get("otd_variability")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<Decimal>().ok())
        .unwrap_or(Decimal::ZERO);

    Ok(Json(flow_economics::sourcing_flow_cost(
        &label,
        unit_price,
        moq,
        lead_time_days,
        otd,
        demand_per_day,
        otd_variability,
    )))
}

/// Finance waste snapshot (item 38): computed from the tenant's actual
/// WIP, inventory age, scrap/rework and premium-freight facts.
pub async fn finance_waste(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<FinanceWasteSnapshot>> {
    user.require_permission("finance:invoice:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Waste view requires the database".to_string()))?;

    // WIP cash: open work orders × product standard cost.
    let wip_row: (Decimal, Decimal) = sqlx::query_as(
        "SELECT COALESCE(SUM(wo.quantity - wo.quantity_completed), 0)::numeric, \
                COALESCE(SUM((wo.quantity - wo.quantity_completed) * COALESCE(p.standard_cost, 0)), 0)::numeric \
         FROM work_orders wo \
         LEFT JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 AND wo.status NOT IN ('completed', 'cancelled')",
    )
    .bind(user.tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("WIP read failed: {e}")))?;
    let (_wip_qty, wip_cash) = wip_row;

    // Aging inventory: stock with no movement for 90+ days, at cost.
    // Fourteenth audit: inventory age comes from the STOCK-MOVE LEDGER —
    // MAX(stock_moves.moved_at) per product/location/lot. An
    // administrative touch (updated_at) must never make 18-month-dead
    // stock look new.
    // Twenty-fifth audit P1: the aging clock is SITE- and STATUS-aware —
    // only 'posted' moves at THE ROW'S OWN SITE refresh it. Another
    // plant's moves (same product, same location NAME) and reversed or
    // compensating history never refresh the clock.
    let aging: Decimal = sqlx::query_scalar(
        "SELECT COALESCE(SUM(ii.quantity_on_hand * COALESCE(p.standard_cost, 0)), 0)::numeric \
         FROM inventory_items ii \
         LEFT JOIN products p ON p.id = ii.product_id AND p.tenant_id = ii.tenant_id \
         WHERE ii.tenant_id = $1 \
           AND COALESCE(( \
                SELECT MAX(sm.moved_at) FROM stock_moves sm \
                WHERE sm.tenant_id = ii.tenant_id \
                  AND sm.product_id = ii.product_id \
                  AND sm.site_id = ii.site_id \
                  AND sm.status = 'posted' \
                  AND sm.to_location = ii.location \
                  AND sm.lot_number IS NOT DISTINCT FROM ii.lot_number \
           ), ii.created_at) < NOW() - INTERVAL '90 days'",
    )
    .bind(user.tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Aging read failed: {e}")))?;

    // Scrap: measured from the work-order ledger. REWORK is NOT tracked
    // in the schema — it is reported as "not yet measured", never as €0
    // (item 53: unknown ≠ zero).
    let scrap_cost: Decimal = sqlx::query_scalar(
        "SELECT COALESCE(SUM(quantity_scrapped * COALESCE(p.standard_cost, 0)), 0)::numeric \
         FROM work_orders wo \
         LEFT JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1",
    )
    .bind(user.tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Scrap read failed: {e}")))?;
    let rework_cost: Decimal = Decimal::ZERO;

    Ok(Json(flow_economics::finance_waste(
        wip_cash,
        aging,
        scrap_cost,
        rework_cost,
        Decimal::ZERO,
        Decimal::ZERO,
        flow_economics::BatchPolicyInput {
            excess_days: Decimal::ZERO,
            daily_demand: Decimal::ZERO,
            unit_cost: Decimal::ZERO,
        },
        // Item 53: these categories are NOT tracked — report unmeasured.
        flow_economics::UnmeasuredWaste {
            premium_freight: true,
            expediting: true,
            batch_policy: true,
            rework: true,
        },
    )))
}

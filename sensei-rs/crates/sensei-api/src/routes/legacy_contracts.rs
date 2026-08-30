//! Contract completions (item 69/70): frontend surfaces that called
//! endpoints with NO backend counterpart. Each of these has a REAL
//! backing table — the endpoint completes the contract instead of the
//! page silently 404ing.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Serialize;
use uuid::Uuid;

use crate::state::AppState;

type InspectionRow = (
    Uuid,
    String,
    String,
    Option<Uuid>,
    Option<Uuid>,
    String,
    String,
    Option<String>,
    Option<chrono::DateTime<chrono::Utc>>,
);
type CostRollupRow = (Uuid, Uuid, String, f64, f64, f64, f64, String, String);
type OperationRow = (
    Uuid,
    Uuid,
    i32,
    String,
    String,
    f64,
    Option<chrono::DateTime<chrono::Utc>>,
    Option<chrono::DateTime<chrono::Utc>>,
);
type BomRow = (
    Uuid,
    String,
    rust_decimal::Decimal,
    String,
    rust_decimal::Decimal,
);
type RoutingRow = (Uuid, i32, Uuid, String, f64, bool);

#[derive(Debug, Serialize)]
pub struct InspectionDto {
    pub id: Uuid,
    pub inspection_number: String,
    pub inspection_type: String,
    pub product_id: Option<Uuid>,
    pub work_order_id: Option<Uuid>,
    pub result: String,
    pub status: String,
    pub notes: Option<String>,
    pub inspected_at: Option<chrono::DateTime<chrono::Utc>>,
}

pub async fn list_inspections(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<InspectionDto>>> {
    user.require_permission("quality:ncr:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Inspections require the database".to_string()))?;
    let rows: Vec<InspectionRow> =
        sqlx::query_as(
            "SELECT id, inspection_number, inspection_type, product_id, work_order_id, result, status, notes, inspected_at \
             FROM inspections WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 200",
        )
        .bind(user.tenant_id)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Inspections read failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(
                |(
                    id,
                    inspection_number,
                    inspection_type,
                    product_id,
                    work_order_id,
                    result,
                    status,
                    notes,
                    inspected_at,
                )| {
                    InspectionDto {
                        id,
                        inspection_number,
                        inspection_type,
                        product_id,
                        work_order_id,
                        result,
                        status,
                        notes,
                        inspected_at,
                    }
                },
            )
            .collect(),
    ))
}

#[derive(Debug, Serialize)]
pub struct CostRollupDto {
    pub id: Uuid,
    pub product_id: Uuid,
    pub version: String,
    pub total_cost: f64,
    pub material_cost: f64,
    pub labor_cost: f64,
    pub overhead_cost: f64,
    pub currency: String,
    pub status: String,
}

pub async fn list_cost_rollups(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<CostRollupDto>>> {
    user.require_permission("finance:invoice:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Cost rollups require the database".to_string()))?;
    let rows: Vec<CostRollupRow> = sqlx::query_as(
        "SELECT id, product_id, version, total_cost, material_cost, labor_cost, overhead_cost, currency, status \
         FROM cost_rollups WHERE tenant_id = $1 ORDER BY computed_at DESC LIMIT 200",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Cost rollups read failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(
                |(
                    id,
                    product_id,
                    version,
                    total_cost,
                    material_cost,
                    labor_cost,
                    overhead_cost,
                    currency,
                    status,
                )| {
                    CostRollupDto {
                        id,
                        product_id,
                        version,
                        total_cost,
                        material_cost,
                        labor_cost,
                        overhead_cost,
                        currency,
                        status,
                    }
                },
            )
            .collect(),
    ))
}

pub async fn get_cost_rollup(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<CostRollupDto>> {
    user.require_permission("finance:invoice:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Cost rollups require the database".to_string()))?;
    let row: Option<CostRollupRow> = sqlx::query_as(
        "SELECT id, product_id, version, total_cost, material_cost, labor_cost, overhead_cost, currency, status \
         FROM cost_rollups WHERE id = $1 AND tenant_id = $2",
    )
    .bind(id)
    .bind(user.tenant_id)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Cost rollup read failed: {e}")))?;
    let Some((
        id,
        product_id,
        version,
        total_cost,
        material_cost,
        labor_cost,
        overhead_cost,
        currency,
        status,
    )) = row
    else {
        return Err(SenseiError::NotFound(id.to_string()));
    };
    Ok(Json(CostRollupDto {
        id,
        product_id,
        version,
        total_cost,
        material_cost,
        labor_cost,
        overhead_cost,
        currency,
        status,
    }))
}

#[derive(Debug, Serialize)]
pub struct WorkOrderOperationDto {
    pub id: Uuid,
    pub work_order_id: Uuid,
    pub sequence: i32,
    pub operation: String,
    pub status: String,
    pub standard_time: f64,
    pub started_at: Option<chrono::DateTime<chrono::Utc>>,
    pub completed_at: Option<chrono::DateTime<chrono::Utc>>,
}

pub async fn list_work_order_operations(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<WorkOrderOperationDto>>> {
    user.require_permission("production:work-order:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Operations require the database".to_string()))?;
    let rows: Vec<OperationRow> =
        sqlx::query_as(
            "SELECT id, work_order_id, sequence, operation, status, standard_time, started_at, completed_at \
             FROM work_order_operations WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 200",
        )
        .bind(user.tenant_id)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Operations read failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(
                |(
                    id,
                    work_order_id,
                    sequence,
                    operation,
                    status,
                    standard_time,
                    started_at,
                    completed_at,
                )| {
                    WorkOrderOperationDto {
                        id,
                        work_order_id,
                        sequence,
                        operation,
                        status,
                        standard_time,
                        started_at,
                        completed_at,
                    }
                },
            )
            .collect(),
    ))
}

#[derive(Debug, Serialize)]
pub struct ProductBomDto {
    pub component_product_id: Uuid,
    pub component_name: String,
    pub quantity: String,
    pub unit_of_measure: String,
    pub scrap_percent: String,
}

pub async fn get_product_bom(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(product_id): Path<Uuid>,
) -> Result<Json<Vec<ProductBomDto>>> {
    user.require_permission("master-data:products:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("BOM requires the database".to_string()))?;
    let rows: Vec<BomRow> =
        sqlx::query_as(
            "SELECT b.component_product_id, p.name, b.quantity, b.unit_of_measure, COALESCE(b.scrap_percent, 0) \
             FROM bom_items b \
             JOIN products p ON p.id = b.component_product_id AND p.tenant_id = b.tenant_id \
             WHERE b.parent_product_id = $1 AND b.tenant_id = $2 AND b.is_active = TRUE \
             ORDER BY b.created_at",
        )
        .bind(product_id)
        .bind(user.tenant_id)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("BOM read failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(
                |(
                    component_product_id,
                    component_name,
                    quantity,
                    unit_of_measure,
                    scrap_percent,
                )| {
                    ProductBomDto {
                        component_product_id,
                        component_name,
                        quantity: quantity.to_string(),
                        unit_of_measure,
                        scrap_percent: scrap_percent.to_string(),
                    }
                },
            )
            .collect(),
    ))
}

#[derive(Debug, Serialize)]
pub struct ProductRoutingDto {
    pub id: Uuid,
    pub sequence: i32,
    pub work_center_id: Uuid,
    pub operation: String,
    pub standard_time: f64,
    pub is_active: bool,
}

pub async fn get_product_routing(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(product_id): Path<Uuid>,
) -> Result<Json<Vec<ProductRoutingDto>>> {
    user.require_permission("master-data:products:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Routing requires the database".to_string()))?;
    let rows: Vec<RoutingRow> = sqlx::query_as(
        "SELECT id, sequence, work_center_id, operation, standard_time, is_active \
         FROM routings WHERE product_id = $1 AND tenant_id = $2 ORDER BY sequence",
    )
    .bind(product_id)
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Routing read failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(
                |(id, sequence, work_center_id, operation, standard_time, is_active)| {
                    ProductRoutingDto {
                        id,
                        sequence,
                        work_center_id,
                        operation,
                        standard_time,
                        is_active,
                    }
                },
            )
            .collect(),
    ))
}

//! Production Cells route handlers.
//!
//! Provides endpoints for managing production cells (manufacturing units),
//! including CRUD and utilization metrics.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::ProductionCell;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing production cells.
#[derive(Debug, Deserialize)]
pub struct ListProductionCellsParams {
    pub cell_type: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating a production cell.
#[derive(Debug, Deserialize)]
pub struct CreateProductionCellRequest {
    pub name: String,
    pub code: String,
    pub description: String,
    pub cell_type: String,
    pub location: Option<String>,
    pub capacity_per_shift: i32,
    pub shifts_per_day: i32,
    pub efficiency_target: f64,
    pub supervisor_id: Option<Uuid>,
}

/// Request body for updating a production cell.
#[derive(Debug, Deserialize)]
pub struct UpdateProductionCellRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub cell_type: Option<String>,
    pub location: Option<String>,
    pub is_active: Option<bool>,
    pub capacity_per_shift: Option<i32>,
    pub shifts_per_day: Option<i32>,
    pub efficiency_target: Option<f64>,
    pub supervisor_id: Option<Option<Uuid>>,
}

/// Utilization metrics for a production cell.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CellUtilizationMetrics {
    pub cell_id: Uuid,
    pub cell_name: String,
    pub capacity_per_shift: i32,
    pub shifts_per_day: i32,
    pub total_daily_capacity: i32,
    pub current_utilization_pct: f64,
    pub efficiency_target: f64,
    pub efficiency_vs_target_pct: f64,
}

// ── Production Cells ───────────────────────────────────────────────────────

/// List production cells with optional filters.
pub async fn list_production_cells(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListProductionCellsParams>,
) -> Result<Json<PaginatedResponse<ProductionCell>>> {
    let tenant_id = user.tenant_id;
    let store = state.production_cells.read().await;
    let mut cells: Vec<ProductionCell> = store
        .values()
        .filter(|c| c.tenant_id == tenant_id)
        .filter(|c| {
            if let Some(ref ct) = params.cell_type {
                c.cell_type == *ct
            } else {
                true
            }
        })
        .filter(|c| {
            if let Some(active) = params.is_active {
                c.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    cells.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(cells, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new production cell.
pub async fn create_production_cell(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateProductionCellRequest>,
) -> Result<Json<ProductionCell>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let cell = ProductionCell {
        id: new_id(),
        tenant_id,
        name: req.name,
        code: req.code,
        description: req.description,
        cell_type: req.cell_type,
        location: req.location,
        is_active: true,
        capacity_per_shift: req.capacity_per_shift,
        shifts_per_day: req.shifts_per_day,
        efficiency_target: req.efficiency_target,
        supervisor_id: req.supervisor_id,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.production_cells.write().await;
    store.insert(cell.id, cell.clone());
    Ok(Json(cell))
}

/// Get a production cell by ID.
pub async fn get_production_cell(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ProductionCell>> {
    let tenant_id = user.tenant_id;
    let store = state.production_cells.read().await;
    let cell = store
        .values()
        .find(|c| c.id == id && c.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Production cell {id} not found")))?;
    Ok(Json(cell))
}

/// Update a production cell.
pub async fn update_production_cell(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateProductionCellRequest>,
) -> Result<Json<ProductionCell>> {
    let tenant_id = user.tenant_id;
    let mut store = state.production_cells.write().await;
    let cell = store
        .get_mut(&id)
        .filter(|c| c.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Production cell {id} not found")))?;

    if let Some(name) = req.name {
        cell.name = name;
    }
    if let Some(desc) = req.description {
        cell.description = desc;
    }
    if let Some(ct) = req.cell_type {
        cell.cell_type = ct;
    }
    if let Some(loc) = req.location {
        cell.location = Some(loc);
    }
    if let Some(active) = req.is_active {
        cell.is_active = active;
    }
    if let Some(cps) = req.capacity_per_shift {
        cell.capacity_per_shift = cps;
    }
    if let Some(spd) = req.shifts_per_day {
        cell.shifts_per_day = spd;
    }
    if let Some(et) = req.efficiency_target {
        cell.efficiency_target = et;
    }
    if let Some(sid) = req.supervisor_id {
        cell.supervisor_id = sid;
    }
    cell.updated_at = Utc::now();
    Ok(Json(cell.clone()))
}

/// Get utilization metrics for a production cell.
pub async fn get_cell_utilization(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<CellUtilizationMetrics>> {
    let tenant_id = user.tenant_id;
    let store = state.production_cells.read().await;
    let cell = store
        .values()
        .find(|c| c.id == id && c.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Production cell {id} not found")))?;

    let total_capacity = cell.capacity_per_shift as f64 * cell.shifts_per_day as f64;

    // Estimate utilization based on available capacity and efficiency target
    let utilization_pct = if total_capacity > 0.0 {
        // Use a heuristic based on efficiency target as a proxy for utilization
        (cell.efficiency_target * 0.85).min(100.0)
    } else {
        0.0
    };

    let eff_target = cell.efficiency_target;
    let eff_vs_target = if eff_target > 0.0 {
        (utilization_pct / eff_target) * 100.0
    } else {
        0.0
    };

    let metrics = CellUtilizationMetrics {
        cell_id: cell.id,
        cell_name: cell.name,
        capacity_per_shift: cell.capacity_per_shift,
        shifts_per_day: cell.shifts_per_day,
        total_daily_capacity: cell.capacity_per_shift * cell.shifts_per_day,
        current_utilization_pct: utilization_pct,
        efficiency_target: eff_target,
        efficiency_vs_target_pct: eff_vs_target,
    };
    Ok(Json(metrics))
}

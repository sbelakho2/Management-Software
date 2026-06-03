//! Work Center route handlers.
//!
//! Provides endpoints for managing manufacturing work centers (production
//! cells / manufacturing units), including capacity, efficiency tracking,
//! and active/inactive status management.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{WorkCenter, WorkCenterStore};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing work centers.
#[derive(Debug, Deserialize)]
pub struct ListWorkCentersParams {
    pub is_active: Option<bool>,
    pub work_center_type: Option<String>,
    pub department: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating a work center.
#[derive(Debug, Deserialize)]
pub struct CreateWorkCenterRequest {
    pub work_center_number: String,
    pub name: String,
    pub description: Option<String>,
    pub work_center_type: String,
    pub department: Option<String>,
    pub location: Option<String>,
    pub capacity_per_shift: i32,
    pub shifts_per_day: i32,
    pub efficiency: f64,
    pub available_hours_per_day: f64,
    pub notes: Option<String>,
    pub supervisor_id: Option<Uuid>,
}

/// Request body for updating a work center.
#[derive(Debug, Deserialize)]
pub struct UpdateWorkCenterRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub work_center_type: Option<String>,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_active: Option<bool>,
    pub capacity_per_shift: Option<i32>,
    pub shifts_per_day: Option<i32>,
    pub efficiency: Option<f64>,
    pub available_hours_per_day: Option<f64>,
    pub notes: Option<String>,
    pub supervisor_id: Option<Uuid>,
}

/// Work center capacity overview.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkCenterCapacity {
    pub total_capacity_per_day: f64,
    pub effective_capacity_per_day: f64,
    pub utilization_percentage: f64,
}

/// Work center efficiency report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EfficiencyReport {
    pub work_center_id: Uuid,
    pub name: String,
    pub efficiency: f64,
    pub capacity_per_shift: i32,
    pub utilization: f64,
    pub is_overloaded: bool,
}

// ── Helpers ────────────────────────────────────────────────────────────────

fn get_store(state: &AppState) -> &WorkCenterStore {
    &state.work_centers
}

fn next_number() -> String {
    use std::sync::atomic::{AtomicU32, Ordering};
    static COUNTER: AtomicU32 = AtomicU32::new(1);
    format!("WC-{:05}", COUNTER.fetch_add(1, Ordering::Relaxed))
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all work centers with optional filters and pagination.
pub async fn list_work_centers(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWorkCentersParams>,
) -> Result<Json<PaginatedResponse<WorkCenter>>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let mut items: Vec<WorkCenter> = map
        .values()
        .filter(|wc| wc.tenant_id == tenant_id)
        .filter(|wc| match params.is_active {
            Some(active) => wc.is_active == active,
            None => true,
        })
        .filter(|wc| match &params.work_center_type {
            Some(t) => wc.work_center_type == *t,
            None => true,
        })
        .filter(|wc| match &params.department {
            Some(d) => wc.department.as_deref() == Some(d.as_str()),
            None => true,
        })
        .cloned()
        .collect();

    items.sort_by(|a, b| a.work_center_number.cmp(&b.work_center_number));
    let total = items.len();
    let page = params.page.unwrap_or(1);
    let per_page = params.per_page.unwrap_or(20).min(100);
    let total_pages = total.div_ceil(per_page);
    let start = (page.saturating_sub(1)) * per_page;
    let data: Vec<WorkCenter> = items.into_iter().skip(start).take(per_page).collect();

    Ok(Json(PaginatedResponse {
        data,
        total,
        page,
        per_page,
        total_pages,
    }))
}

/// Get a specific work center by ID.
pub async fn get_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<WorkCenter>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let wc = map
        .get(&id)
        .filter(|wc| wc.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?
        .clone();

    Ok(Json(wc))
}

/// Create a new work center.
pub async fn create_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateWorkCenterRequest>,
) -> Result<Json<WorkCenter>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let wc = WorkCenter {
        id: Uuid::new_v4(),
        tenant_id,
        work_center_number: next_number(),
        name: req.name,
        description: req.description.unwrap_or_default(),
        work_center_type: req.work_center_type,
        department: req.department,
        location: req.location,
        is_active: true,
        capacity_per_shift: req.capacity_per_shift,
        shifts_per_day: req.shifts_per_day,
        efficiency: req.efficiency,
        available_hours_per_day: req.available_hours_per_day,
        notes: req.notes.unwrap_or_default(),
        supervisor_id: req.supervisor_id,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };

    let store = get_store(&state);
    store.write().await.insert(wc.id, wc.clone());
    Ok(Json(wc))
}

/// Update a work center's editable fields.
pub async fn update_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateWorkCenterRequest>,
) -> Result<Json<WorkCenter>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let mut map = store.write().await;

    let wc = map
        .get_mut(&id)
        .filter(|wc| wc.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    if let Some(name) = req.name {
        wc.name = name;
    }
    if let Some(description) = req.description {
        wc.description = description;
    }
    if let Some(work_center_type) = req.work_center_type {
        wc.work_center_type = work_center_type;
    }
    if let Some(department) = req.department {
        wc.department = Some(department);
    }
    if let Some(location) = req.location {
        wc.location = Some(location);
    }
    if let Some(is_active) = req.is_active {
        wc.is_active = is_active;
    }
    if let Some(capacity) = req.capacity_per_shift {
        wc.capacity_per_shift = capacity;
    }
    if let Some(shifts) = req.shifts_per_day {
        wc.shifts_per_day = shifts;
    }
    if let Some(efficiency) = req.efficiency {
        wc.efficiency = efficiency;
    }
    if let Some(hours) = req.available_hours_per_day {
        wc.available_hours_per_day = hours;
    }
    if let Some(notes) = req.notes {
        wc.notes = notes;
    }
    if let Some(supervisor_id) = req.supervisor_id {
        wc.supervisor_id = Some(supervisor_id);
    }
    wc.updated_at = Utc::now();

    let result = wc.clone();
    Ok(Json(result))
}

/// Deactivate (soft-delete) a work center.
pub async fn deactivate_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let mut map = store.write().await;

    let wc = map
        .get_mut(&id)
        .filter(|wc| wc.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    wc.is_active = false;
    wc.updated_at = Utc::now();
    Ok(Json(()))
}

/// Get work center capacity and utilization metrics.
pub async fn get_work_center_capacity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<WorkCenterCapacity>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let wc = map
        .get(&id)
        .filter(|wc| wc.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    let total_capacity_per_day = wc.capacity_per_shift as f64 * wc.shifts_per_day as f64;
    let effective_capacity_per_day = total_capacity_per_day * wc.efficiency / 100.0;
    let utilization_percentage = if wc.available_hours_per_day > 0.0 {
        (wc.available_hours_per_day / (wc.shifts_per_day as f64 * 8.0)) * 100.0
    } else {
        0.0
    };

    Ok(Json(WorkCenterCapacity {
        total_capacity_per_day,
        effective_capacity_per_day,
        utilization_percentage,
    }))
}

/// Get efficiency report for all active work centers.
pub async fn get_efficiency_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<EfficiencyReport>>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let report: Vec<EfficiencyReport> = map
        .values()
        .filter(|wc| wc.tenant_id == tenant_id && wc.is_active)
        .map(|wc| {
            let _capacity = wc.capacity_per_shift as f64 * wc.shifts_per_day as f64;
            let utilization = if wc.available_hours_per_day > 0.0 {
                (wc.available_hours_per_day / (wc.shifts_per_day as f64 * 8.0)) * 100.0
            } else {
                0.0
            };
            EfficiencyReport {
                work_center_id: wc.id,
                name: wc.name.clone(),
                efficiency: wc.efficiency,
                capacity_per_shift: wc.capacity_per_shift,
                utilization,
                is_overloaded: utilization > 100.0,
            }
        })
        .collect();

    Ok(Json(report))
}

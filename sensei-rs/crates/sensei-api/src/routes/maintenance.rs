//! Maintenance route handlers.
//!
//! Provides endpoints for maintenance work requests, preventive maintenance
//! schedules, and equipment management.

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::maintenance::{EquipmentRecord, MaintenanceWorkRequest, PMSchedule};
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing work requests.
#[derive(Debug, Deserialize)]
pub struct ListWorkRequestsParams {
    pub status: Option<String>,
    pub priority: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing PM schedules.
#[derive(Debug, Deserialize)]
pub struct ListPmSchedulesParams {
    pub equipment_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing equipment.
#[derive(Debug, Deserialize)]
pub struct ListEquipmentParams {
    pub equipment_type: Option<String>,
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating work request status.
#[derive(Debug, Deserialize)]
pub struct UpdateWorkRequestStatusRequest {
    pub status: String,
}

/// Request body for assigning a work request.
#[derive(Debug, Deserialize)]
pub struct AssignWorkRequestRequest {
    /// The technician to assign the request to. Must match the
    /// authenticated user; client-supplied ids for other users are
    /// rejected.
    pub assigned_to: Uuid,
}

/// Request body for updating equipment status.
#[derive(Debug, Deserialize)]
pub struct UpdateEquipmentStatusRequest {
    pub status: String,
}

// ── Work Requests ──────────────────────────────────────────────────────────

/// List all maintenance work requests with optional filters.
pub async fn list_work_requests(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWorkRequestsParams>,
) -> Result<Json<PaginatedResponse<MaintenanceWorkRequest>>> {
    let tenant_id = user.tenant_id;
    let requests = state
        .maintenance_service
        .list_work_requests(tenant_id, params.status.as_deref(), params.priority.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(requests))
}

/// Create a new maintenance work request.
pub async fn create_work_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<MaintenanceWorkRequest>,
) -> Result<Json<MaintenanceWorkRequest>> {
    let tenant_id = user.tenant_id;
    let request = state
        .maintenance_service
        .create_work_request(tenant_id, req)
        .await?;
    Ok(Json(request))
}

/// Get a specific work request by ID.
pub async fn get_work_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<MaintenanceWorkRequest>> {
    let tenant_id = user.tenant_id;
    let request = state
        .maintenance_service
        .get_work_request(tenant_id, id)
        .await?;
    Ok(Json(request))
}

/// Update a work request's status.
pub async fn update_work_request_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateWorkRequestStatusRequest>,
) -> Result<Json<MaintenanceWorkRequest>> {
    let tenant_id = user.tenant_id;
    let request = state
        .maintenance_service
        .update_work_request_status(tenant_id, id, &req.status)
        .await?;
    Ok(Json(request))
}

/// Assign a work request to a technician.
///
/// Only the authenticated user may be assigned; a client-supplied
/// `assigned_to` that differs from the token user is rejected so the
/// handler never trusts the client for the actor identity.
pub async fn assign_work_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<AssignWorkRequestRequest>,
) -> Result<Json<MaintenanceWorkRequest>> {
    use sensei_core::error::SenseiError;
    if req.assigned_to != user.user_id {
        return Err(SenseiError::Forbidden(
            "Work requests can only be assigned to yourself".to_string(),
        ));
    }
    let tenant_id = user.tenant_id;
    let request = state
        .maintenance_service
        .assign_work_request(tenant_id, id, req.assigned_to)
        .await?;
    Ok(Json(request))
}

// ── PM Schedules ───────────────────────────────────────────────────────────

/// List all PM schedules with optional filters.
pub async fn list_pm_schedules(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListPmSchedulesParams>,
) -> Result<Json<PaginatedResponse<PMSchedule>>> {
    let tenant_id = user.tenant_id;
    let schedules = state
        .maintenance_service
        .list_pm_schedules(tenant_id, params.equipment_id, params.page, params.per_page)
        .await?;
    Ok(Json(schedules))
}

/// Create a new PM schedule.
pub async fn create_pm_schedule(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PMSchedule>,
) -> Result<Json<PMSchedule>> {
    let tenant_id = user.tenant_id;
    let schedule = state
        .maintenance_service
        .create_pm_schedule(tenant_id, req)
        .await?;
    Ok(Json(schedule))
}

/// Get a specific PM schedule by ID.
pub async fn get_pm_schedule(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PMSchedule>> {
    let tenant_id = user.tenant_id;
    let schedule = state
        .maintenance_service
        .get_pm_schedule(tenant_id, id)
        .await?;
    Ok(Json(schedule))
}

/// Complete a PM task.
pub async fn complete_pm_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PMSchedule>> {
    let tenant_id = user.tenant_id;
    let schedule = state
        .maintenance_service
        .complete_pm_task(tenant_id, id)
        .await?;
    Ok(Json(schedule))
}

/// Get all overdue PM tasks.
pub async fn get_overdue_pm_tasks(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<PMSchedule>>> {
    let tenant_id = user.tenant_id;
    let tasks = state
        .maintenance_service
        .get_overdue_pm_tasks(tenant_id)
        .await?;
    Ok(Json(tasks))
}

// ── Equipment ──────────────────────────────────────────────────────────────

/// List all registered equipment with optional filters.
pub async fn list_equipment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListEquipmentParams>,
) -> Result<Json<PaginatedResponse<EquipmentRecord>>> {
    let tenant_id = user.tenant_id;
    let equipment = state
        .maintenance_service
        .list_equipment(tenant_id, params.equipment_type.as_deref(), params.status.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(equipment))
}

/// Register new equipment.
pub async fn register_equipment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<EquipmentRecord>,
) -> Result<Json<EquipmentRecord>> {
    let tenant_id = user.tenant_id;
    let equipment = state
        .maintenance_service
        .register_equipment(tenant_id, req)
        .await?;
    Ok(Json(equipment))
}

/// Get a specific equipment record by ID.
pub async fn get_equipment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<EquipmentRecord>> {
    let tenant_id = user.tenant_id;
    let equipment = state
        .maintenance_service
        .get_equipment(tenant_id, id)
        .await?;
    Ok(Json(equipment))
}

// ── New: Update / Delete Handlers ──────────────────────────────────────────

/// Update a work request.
pub async fn update_work_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<MaintenanceWorkRequest>,
) -> Result<Json<MaintenanceWorkRequest>> {
    let tenant_id = user.tenant_id;
    let request = state
        .maintenance_service
        .update_work_request(tenant_id, id, req)
        .await?;
    Ok(Json(request))
}

/// Delete a work request.
pub async fn delete_work_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .maintenance_service
        .delete_work_request(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a PM schedule.
pub async fn update_pm_schedule(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PMSchedule>,
) -> Result<Json<PMSchedule>> {
    let tenant_id = user.tenant_id;
    let schedule = state
        .maintenance_service
        .update_pm_schedule(tenant_id, id, req)
        .await?;
    Ok(Json(schedule))
}

/// Delete a PM schedule.
pub async fn delete_pm_schedule(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .maintenance_service
        .delete_pm_schedule(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update an equipment record.
pub async fn update_equipment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<EquipmentRecord>,
) -> Result<Json<EquipmentRecord>> {
    let tenant_id = user.tenant_id;
    let equipment = state
        .maintenance_service
        .update_equipment(tenant_id, id, req)
        .await?;
    Ok(Json(equipment))
}

/// Delete an equipment record.
pub async fn delete_equipment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .maintenance_service
        .delete_equipment(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update equipment status.
pub async fn update_equipment_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateEquipmentStatusRequest>,
) -> Result<Json<EquipmentRecord>> {
    let tenant_id = user.tenant_id;
    let equipment = state
        .maintenance_service
        .update_equipment_status(tenant_id, id, &req.status)
        .await?;
    Ok(Json(equipment))
}

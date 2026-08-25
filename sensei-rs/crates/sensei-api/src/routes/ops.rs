//! Operations / Continuous Improvement route handlers.
//!
//! Provides endpoints for Andon events, improvement projects, A3 reports,
//! and risk management.

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::{A3, Andon, Project, Risk};
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing Andon events.
#[derive(Debug, Deserialize)]
pub struct ListAndonsParams {
    pub status: Option<String>,
    pub work_center_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing projects.
#[derive(Debug, Deserialize)]
pub struct ListProjectsParams {
    pub status: Option<String>,
    pub category: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing A3 reports.
#[derive(Debug, Deserialize)]
pub struct ListA3sParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing risks.
#[derive(Debug, Deserialize)]
pub struct ListRisksParams {
    pub status: Option<String>,
    pub category: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for completing a project.
#[derive(Debug, Deserialize)]
pub struct CompleteProjectRequest {
    pub savings_realized: f64,
}

/// Request body for resolving an Andon (resolution notes only — the actor
/// is always taken from the authenticated token).
#[derive(Debug, Deserialize)]
pub struct ResolveAndonRequest {
    pub resolution: String,
}

// ── Andon ──────────────────────────────────────────────────────────────────

/// List all Andon events with optional filters.
pub async fn list_andons(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListAndonsParams>,
) -> Result<Json<PaginatedResponse<Andon>>> {
    let tenant_id = user.tenant_id;
    let andons = state
        .ops_service
        .list_andons(tenant_id, params.status.as_deref(), params.work_center_id, params.page, params.per_page)
        .await?;
    Ok(Json(andons))
}

/// Raise a new Andon event.
pub async fn raise_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Andon>,
) -> Result<Json<Andon>> {
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .raise_andon(tenant_id, req)
        .await?;
    Ok(Json(andon))
}

/// Get a specific Andon event by ID.
pub async fn get_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Andon>> {
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .get_andon(tenant_id, id)
        .await?;
    Ok(Json(andon))
}

/// Acknowledge an Andon event.
///
/// The acknowledging user is derived from the authenticated token — the
/// client cannot spoof who acknowledged the signal.
pub async fn acknowledge_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Andon>> {
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .acknowledge_andon(tenant_id, id, user.user_id)
        .await?;
    Ok(Json(andon))
}

/// Resolve an Andon event.
///
/// The resolving user is derived from the authenticated token — the client
/// cannot spoof who resolved the signal.
pub async fn resolve_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ResolveAndonRequest>,
) -> Result<Json<Andon>> {
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .resolve_andon(tenant_id, id, user.user_id, &req.resolution)
        .await?;
    Ok(Json(andon))
}

// ── Projects ───────────────────────────────────────────────────────────────

/// List all improvement projects with optional filters.
pub async fn list_projects(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListProjectsParams>,
) -> Result<Json<PaginatedResponse<Project>>> {
    let tenant_id = user.tenant_id;
    let projects = state
        .ops_service
        .list_projects(tenant_id, params.status.as_deref(), params.category.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(projects))
}

/// Create a new improvement project.
pub async fn create_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Project>,
) -> Result<Json<Project>> {
    let tenant_id = user.tenant_id;
    let project = state
        .ops_service
        .create_project(tenant_id, req)
        .await?;
    Ok(Json(project))
}

/// Get a specific project by ID.
pub async fn get_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Project>> {
    let tenant_id = user.tenant_id;
    let project = state
        .ops_service
        .get_project(tenant_id, id)
        .await?;
    Ok(Json(project))
}

/// Complete a project and record realized savings.
pub async fn complete_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<CompleteProjectRequest>,
) -> Result<Json<Project>> {
    let tenant_id = user.tenant_id;
    let project = state
        .ops_service
        .complete_project(tenant_id, id, req.savings_realized)
        .await?;
    Ok(Json(project))
}

// ── A3 Reports ─────────────────────────────────────────────────────────────

/// List all A3 reports with optional filters.
pub async fn list_a3s(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListA3sParams>,
) -> Result<Json<PaginatedResponse<A3>>> {
    let tenant_id = user.tenant_id;
    let a3s = state
        .ops_service
        .list_a3s(tenant_id, params.status.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(a3s))
}

/// Create a new A3 report.
pub async fn create_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<A3>,
) -> Result<Json<A3>> {
    let tenant_id = user.tenant_id;
    let a3 = state
        .ops_service
        .create_a3(tenant_id, req)
        .await?;
    Ok(Json(a3))
}

/// Get a specific A3 report by ID.
pub async fn get_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    let tenant_id = user.tenant_id;
    let a3 = state
        .ops_service
        .get_a3(tenant_id, id)
        .await?;
    Ok(Json(a3))
}

/// Close an A3 report.
pub async fn close_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    let tenant_id = user.tenant_id;
    let a3 = state
        .ops_service
        .close_a3(tenant_id, id)
        .await?;
    Ok(Json(a3))
}

// ── Risks ──────────────────────────────────────────────────────────────────

/// List all risks with optional filters.
pub async fn list_risks(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListRisksParams>,
) -> Result<Json<PaginatedResponse<Risk>>> {
    let tenant_id = user.tenant_id;
    let risks = state
        .ops_service
        .list_risks(tenant_id, params.status.as_deref(), params.category.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(risks))
}

/// Create a new risk entry.
pub async fn create_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Risk>,
) -> Result<Json<Risk>> {
    let tenant_id = user.tenant_id;
    let risk = state
        .ops_service
        .create_risk(tenant_id, req)
        .await?;
    Ok(Json(risk))
}

/// Get a specific risk by ID.
pub async fn get_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Risk>> {
    let tenant_id = user.tenant_id;
    let risk = state
        .ops_service
        .get_risk(tenant_id, id)
        .await?;
    Ok(Json(risk))
}

// ── New: Update / Delete Handlers ──────────────────────────────────────────

/// Update an Andon signal.
pub async fn update_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Andon>,
) -> Result<Json<Andon>> {
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .update_andon(tenant_id, id, req)
        .await?;
    Ok(Json(andon))
}

/// Delete an Andon signal.
pub async fn delete_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .ops_service
        .delete_andon(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a project.
pub async fn update_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Project>,
) -> Result<Json<Project>> {
    let tenant_id = user.tenant_id;
    let project = state
        .ops_service
        .update_project(tenant_id, id, req)
        .await?;
    Ok(Json(project))
}

/// Delete a project.
pub async fn delete_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .ops_service
        .delete_project(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update an A3 report.
pub async fn update_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<A3>,
) -> Result<Json<A3>> {
    let tenant_id = user.tenant_id;
    let a3 = state
        .ops_service
        .update_a3(tenant_id, id, req)
        .await?;
    Ok(Json(a3))
}

/// Delete an A3 report.
pub async fn delete_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .ops_service
        .delete_a3(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a risk.
pub async fn update_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Risk>,
) -> Result<Json<Risk>> {
    let tenant_id = user.tenant_id;
    let risk = state
        .ops_service
        .update_risk(tenant_id, id, req)
        .await?;
    Ok(Json(risk))
}

/// Delete a risk.
pub async fn delete_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .ops_service
        .delete_risk(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Mark a risk as mitigated.
pub async fn mitigate_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Risk>> {
    let tenant_id = user.tenant_id;
    let risk = state
        .ops_service
        .mitigate_risk(tenant_id, id)
        .await?;
    Ok(Json(risk))
}

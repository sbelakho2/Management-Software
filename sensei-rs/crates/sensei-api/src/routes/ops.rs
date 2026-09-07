//! Operations / Continuous Improvement route handlers.
//!
//! Provides endpoints for improvement projects, A3 reports,
//! and risk management.
//!
//! The Andon surface was REMOVED in the thirtieth-first audit: the
//! canonical Andon routes live in `routes::andon` (scope-vector
//! authorized), and the legacy `/api/v1/ops/andons*` paths are direct
//! aliases to those handlers in the router.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::{Project, Risk, A3};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

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

/// Site entitlement helper (thirtieth-first audit): the canonical Andon
/// handlers now act on the FULL RequestContext scope vector
/// (`ctx.scope`) instead of the legacy site-vector form. This helper
/// (moved out of `routes::andon`, which re-exports it for the remaining
/// legacy importers such as `routes::work_centers`) computes the
/// DB-resolved SITE entitlement for callers that still consume the
/// vector form. Fail-closed: a context that cannot be built yields an
/// error, never a tenant-wide fallback.
pub(crate) async fn caller_sites(user: &AuthenticatedUser, state: &AppState) -> Result<Vec<Uuid>> {
    Ok(crate::authorization::build_request_context(user, state)
        .await?
        .authorized_sites())
}

// ── Projects ───────────────────────────────────────────────────────────────

/// List all improvement projects with optional filters.
pub async fn list_projects(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListProjectsParams>,
) -> Result<Json<PaginatedResponse<Project>>> {
    user.require_permission("tps:obeya:read")?;
    let tenant_id = user.tenant_id;
    let projects = state
        .ops_service
        .list_projects(
            tenant_id,
            params.status.as_deref(),
            params.category.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(projects))
}

/// Create a new improvement project.
pub async fn create_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Project>,
) -> Result<Json<Project>> {
    user.require_permission("tps:obeya:manage")?;
    let tenant_id = user.tenant_id;
    let project = state.ops_service.create_project(tenant_id, req).await?;
    Ok(Json(project))
}

/// Get a specific project by ID.
pub async fn get_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Project>> {
    user.require_permission("tps:obeya:read")?;
    let tenant_id = user.tenant_id;
    let project = state.ops_service.get_project(tenant_id, id).await?;
    Ok(Json(project))
}

/// Complete a project and record realized savings.
pub async fn complete_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<CompleteProjectRequest>,
) -> Result<Json<Project>> {
    user.require_permission("tps:obeya:manage")?;
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
    user.require_permission("tps:a3:read")?;
    let tenant_id = user.tenant_id;
    let a3s = state
        .ops_service
        .list_a3s(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(a3s))
}

/// Create a new A3 report.
pub async fn create_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<A3>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:create")?;
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.create_a3(tenant_id, req).await?;
    Ok(Json(a3))
}

/// Get a specific A3 report by ID.
pub async fn get_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:read")?;
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.get_a3(tenant_id, id).await?;
    Ok(Json(a3))
}

/// Close an A3 report.
pub async fn close_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:close")?;
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.close_a3(tenant_id, id).await?;
    Ok(Json(a3))
}

// ── Risks ──────────────────────────────────────────────────────────────────

/// List all risks with optional filters.
pub async fn list_risks(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListRisksParams>,
) -> Result<Json<PaginatedResponse<Risk>>> {
    user.require_permission("quality:audit:read")?;
    let tenant_id = user.tenant_id;
    let risks = state
        .ops_service
        .list_risks(
            tenant_id,
            params.status.as_deref(),
            params.category.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(risks))
}

/// Create a new risk entry.
pub async fn create_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Risk>,
) -> Result<Json<Risk>> {
    user.require_permission("quality:audit:create")?;
    let tenant_id = user.tenant_id;
    let risk = state.ops_service.create_risk(tenant_id, req).await?;
    Ok(Json(risk))
}

/// Get a specific risk by ID.
pub async fn get_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Risk>> {
    user.require_permission("quality:audit:read")?;
    let tenant_id = user.tenant_id;
    let risk = state.ops_service.get_risk(tenant_id, id).await?;
    Ok(Json(risk))
}

// ── Update / Delete Handlers ───────────────────────────────────────────────

/// Update a project.
pub async fn update_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Project>,
) -> Result<Json<Project>> {
    user.require_permission("tps:obeya:manage")?;
    let tenant_id = user.tenant_id;
    let project = state.ops_service.update_project(tenant_id, id, req).await?;
    Ok(Json(project))
}

/// Delete a project.
pub async fn delete_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("tps:obeya:manage")?;
    let tenant_id = user.tenant_id;
    state.ops_service.delete_project(tenant_id, id).await?;
    Ok(Json(()))
}

/// Update an A3 report.
pub async fn update_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<A3>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:edit")?;
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.update_a3(tenant_id, id, req).await?;
    Ok(Json(a3))
}

/// Delete an A3 report.
pub async fn delete_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("tps:a3:close")?;
    let tenant_id = user.tenant_id;
    state.ops_service.delete_a3(tenant_id, id).await?;
    Ok(Json(()))
}

/// Update a risk.
pub async fn update_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Risk>,
) -> Result<Json<Risk>> {
    user.require_permission("quality:audit:update")?;
    let tenant_id = user.tenant_id;
    let risk = state.ops_service.update_risk(tenant_id, id, req).await?;
    Ok(Json(risk))
}

/// Delete a risk.
pub async fn delete_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("quality:audit:update")?;
    let tenant_id = user.tenant_id;
    state.ops_service.delete_risk(tenant_id, id).await?;
    Ok(Json(()))
}

/// Mark a risk as mitigated.
pub async fn mitigate_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Risk>> {
    user.require_permission("quality:audit:update")?;
    let tenant_id = user.tenant_id;
    let risk = state.ops_service.mitigate_risk(tenant_id, id).await?;
    Ok(Json(risk))
}

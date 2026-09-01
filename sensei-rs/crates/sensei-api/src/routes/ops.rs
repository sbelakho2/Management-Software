//! Operations / Continuous Improvement route handlers.
//!
//! Provides endpoints for Andon events, improvement projects, A3 reports,
//! and risk management.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::{Andon, Project, Risk, A3};
use serde::Deserialize;
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
    user.require_permission("tps:andon:raise")?;
    let tenant_id = user.tenant_id;
    let andons = state
        .ops_service
        .list_andons(
            tenant_id,
            params.status.as_deref(),
            params.work_center_id,
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(andons))
}

/// Raise a new Andon event.
pub async fn raise_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Andon>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:raise")?;
    // Compatibility adapter (item 41): the legacy full-object route and
    // the safe command route MUST call the same command with the same
    // invariants — server-owned identity fields are ALWAYS re-derived,
    // never trusted from the client.
    let andon = Andon {
        id: Uuid::new_v4(),
        tenant_id: user.tenant_id,
        site_id: None,
        andon_number: String::new(),
        work_center_id: req.work_center_id,
        issue_type: req.issue_type,
        severity: req.severity,
        description: req.description,
        status: "active".to_string(),
        raised_by: user.user_id,
        acknowledged_by: None,
        resolved_by: None,
        resolution: None,
        response_time_seconds: None,
        resolution_time_seconds: None,
        created_at: chrono::Utc::now(),
        acknowledged_at: None,
        resolved_at: None,
        restart_authorized_by: None,
        restart_authorized_at: None,
        abnormal_condition_observed_at: None,
        contained_at: None,
        contained_by: None,
        contained_note: None,
        escalated: false,
        escalated_at: None,
        request_key: None,
    };
    state
        .ops_service
        .raise_andon(user.tenant_id, andon)
        .await
        .map(Json)
}

/// Get a specific Andon event by ID.
pub async fn get_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:raise")?;
    let tenant_id = user.tenant_id;
    let andon = state.ops_service.get_andon(tenant_id, id).await?;
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
    user.require_permission("tps:andon:ack")?;
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
    user.require_permission("tps:andon:resolve")?;
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

// ── New: Update / Delete Handlers ──────────────────────────────────────────

/// Update an Andon signal.
pub async fn update_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Andon>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:manage")?;
    let tenant_id = user.tenant_id;
    let andon = state.ops_service.update_andon(tenant_id, id, req).await?;
    Ok(Json(andon))
}

/// Void an Andon (append-only history; never physically deleted).
pub async fn void_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<crate::routes::andon::VoidAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:contain")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .void_andon(tenant_id, id, user.user_id, &req.reason)
        .await?;
    Ok(Json(andon))
}

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

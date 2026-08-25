//! Andon (real-time quality/status signal) route handlers.
//!
//! Provides endpoints for raising, acknowledging, resolving, and managing
//! Andon events – visual signals that alert teams to production issues.

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::Andon;
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

/// Request body for acknowledging an Andon.
#[derive(Debug, Deserialize)]
pub struct AcknowledgeAndonRequest {
    /// Ignored: the actor is always the authenticated user. Kept as
    /// `Option` so legacy clients sending it do not break.
    pub acknowledged_by: Option<Uuid>,
}

/// Request body for resolving an Andon.
#[derive(Debug, Deserialize)]
pub struct ResolveAndonRequest {
    /// Ignored: the actor is always the authenticated user. Kept as
    /// `Option` so legacy clients sending it do not break.
    pub resolved_by: Option<Uuid>,
    pub resolution: String,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all Andon events with optional status and work center filters.
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

/// Raise (create) a new Andon event.
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

/// Acknowledge an Andon event (assign a responder).
///
/// The actor is taken from the authenticated token; client-supplied actor
/// ids are never trusted.
pub async fn acknowledge_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    _req: Json<AcknowledgeAndonRequest>,
) -> Result<Json<Andon>> {
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .acknowledge_andon(tenant_id, id, user.user_id)
        .await?;
    Ok(Json(andon))
}

/// Resolve an Andon event with a resolution description.
///
/// The actor is taken from the authenticated token; client-supplied actor
/// ids are never trusted.
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

/// Update an existing Andon event.
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

/// Delete an Andon event.
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

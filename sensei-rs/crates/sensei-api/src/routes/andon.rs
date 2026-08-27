//! Andon (real-time quality/status signal) route handlers.
//!
//! Provides endpoints for raising, acknowledging, resolving, and managing
//! Andon events – visual signals that alert teams to production issues.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::Andon;
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

/// Client input for raising an Andon: only the operational facts. The
/// actor (raised_by), tenant, status, timestamps and event identity are
/// server-generated — a caller can never attribute an Andon to someone
/// else.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct RaiseAndonRequest {
    pub work_center_id: Uuid,
    pub issue_type: String, // quality, safety, maintenance, material, other
    pub severity: String,   // low, medium, high, critical
    pub description: String,
}

/// Raise (create) a new Andon event.
pub async fn raise_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RaiseAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:raise")?;
    let tenant_id = user.tenant_id;
    let andon = Andon {
        id: Uuid::new_v4(),
        tenant_id,
        andon_number: String::new(),
        work_center_id: req.work_center_id,
        issue_type: req.issue_type,
        severity: req.severity,
        description: req.description,
        status: "active".to_string(),
        // The actor is a server-generated identity field.
        raised_by: user.user_id,
        acknowledged_by: None,
        resolved_by: None,
        resolution: None,
        response_time_seconds: None,
        resolution_time_seconds: None,
        created_at: chrono::Utc::now(),
        acknowledged_at: None,
        resolved_at: None,
    };
    let andon = state.ops_service.raise_andon(tenant_id, andon).await?;
    Ok(Json(andon))
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
    user.require_permission("tps:andon:ack")?;
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
    user.require_permission("tps:andon:resolve")?;
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
    user.require_permission("tps:andon:contain")?;
    let tenant_id = user.tenant_id;
    let andon = state.ops_service.update_andon(tenant_id, id, req).await?;
    Ok(Json(andon))
}

/// Delete an Andon event.
/// Void an Andon (append-only operational history: production Andon
/// events are never physically deleted — abandoned/false signals are
/// marked `voided` with the actor and reason recorded).
pub async fn void_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<VoidAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:contain")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .void_andon(tenant_id, id, user.user_id, &req.reason)
        .await?;
    Ok(Json(andon))
}

/// Reason for voiding an Andon.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct VoidAndonRequest {
    pub reason: String,
}

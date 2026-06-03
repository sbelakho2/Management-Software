//! Risk Management route handlers.
//!
//! Provides endpoints for creating, assessing, mitigating, and managing
//! risk records as part of the continuous improvement framework.

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::Risk;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing risks.
#[derive(Debug, Deserialize)]
pub struct ListRisksParams {
    pub status: Option<String>,
    pub category: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all risk records with optional filters and pagination.
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

/// Create a new risk record.
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

/// Get a specific risk record by ID.
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

/// Update an existing risk record.
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

/// Delete (remove) a risk record.
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

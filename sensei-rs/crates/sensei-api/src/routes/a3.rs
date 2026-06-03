//! A3 Report route handlers.
//!
//! Provides endpoints for creating, reviewing, updating, and closing
//! A3 problem-solving reports following the structured A3 methodology.

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{A3ClosedEvent, A3CreatedEvent};
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::A3;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing A3 reports.
#[derive(Debug, Deserialize)]
pub struct ListA3sParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all A3 reports with optional status filter and pagination.
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

    // Publish A3 created event for notification triggers and downstream consumers.
    let event = A3CreatedEvent::new(
        tenant_id,
        a3.id,
        "standard".to_string(),
        a3.title.clone(),
        "medium".to_string(),
    );
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!("Failed to publish A3CreatedEvent: {e}");
    }

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

/// Update an existing A3 report.
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

/// Close an A3 report (mark as completed/closed).
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

    // Publish A3 closed event for notification triggers and downstream consumers.
    let event = A3ClosedEvent::new(tenant_id, id, "Closed".to_string());
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!("Failed to publish A3ClosedEvent: {e}");
    }

    Ok(Json(a3))
}

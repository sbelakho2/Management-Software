//! A3 Report route handlers.
//!
//! Provides endpoints for creating, reviewing, updating, and closing
//! A3 problem-solving reports following the structured A3 methodology.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{A3ClosedEvent, A3CreatedEvent};
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::A3;
use serde::Deserialize;
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
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.create_a3(tenant_id, req).await?;

    // Publish A3 created event for notification triggers and downstream
    // consumers, derived from the real entity fields (no hardcoded
    // "standard"/"medium" values).
    let a3_type = if a3.a3_type.is_empty() {
        "standard"
    } else {
        a3.a3_type.as_str()
    };
    let severity = if a3.severity.is_empty() {
        "medium"
    } else {
        a3.severity.as_str()
    };
    let event = A3CreatedEvent::new(
        tenant_id,
        a3.id,
        a3_type.to_string(),
        a3.title.clone(),
        severity.to_string(),
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
    let a3 = state.ops_service.get_a3(tenant_id, id).await?;
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
    let a3 = state.ops_service.update_a3(tenant_id, id, req).await?;
    Ok(Json(a3))
}

/// Close an A3 report (mark as completed/closed).
pub async fn close_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.close_a3(tenant_id, id).await?;

    // Publish A3 closed event; the outcome is the entity's actual status
    // after closure (e.g. "closed"), never a hardcoded value.
    let outcome = if a3.status.is_empty() {
        "closed"
    } else {
        a3.status.as_str()
    };
    let event = A3ClosedEvent::new(tenant_id, id, outcome.to_string());
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!("Failed to publish A3ClosedEvent: {e}");
    }

    Ok(Json(a3))
}

/// Delete an A3 report.
pub async fn delete_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state.ops_service.delete_a3(tenant_id, id).await?;
    Ok(Json(()))
}

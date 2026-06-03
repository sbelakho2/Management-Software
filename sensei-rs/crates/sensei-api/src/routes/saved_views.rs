//! Saved Views route handlers.
//!
//! Provides endpoints for managing user-saved view configurations,
//! including CRUD operations, RBAC-based sharing, and compound sorting.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{
    SavedViewCreatedEvent, SavedViewUpdatedEvent, SavedViewDeletedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{SavedView, SortConfig, ViewVisibility};

// ── Request DTOs ───────────────────────────────────────────────────────────

/// Query parameters for listing saved views.
#[derive(Debug, Deserialize)]
pub struct ListSavedViewsParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
    /// Optional filter by entity type.
    pub entity_type: Option<String>,
}

/// Request body for creating/updating a saved view.
#[derive(Debug, Deserialize)]
pub struct SavedViewRequest {
    pub name: String,
    pub entity_type: String,
    pub filters: serde_json::Value,
    /// Compound sort configuration (replaces sort_by/sort_order).
    #[serde(default)]
    pub sort_config: Vec<SortConfig>,
    pub columns: Vec<String>,
    pub is_default: Option<bool>,
    /// Visibility level for sharing.
    #[serde(default)]
    pub visibility: ViewVisibility,
    /// Explicit user IDs to share with.
    #[serde(default)]
    pub shared_with: Vec<Uuid>,
}

/// Request body for sharing a saved view.
#[derive(Debug, Deserialize)]
pub struct ShareViewRequest {
    /// The user IDs to share the view with.
    pub user_ids: Vec<Uuid>,
    /// The visibility level to set.
    pub visibility: ViewVisibility,
}

// ── Saved Views ────────────────────────────────────────────────────────────

/// List saved views visible to the current user with pagination.
///
/// Returns the user's own views + views shared with the user + views with
/// visibility >= Team (public to team/dept/org).
pub async fn list_saved_views(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListSavedViewsParams>,
) -> Result<Json<PaginatedResponse<SavedView>>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    let store = state.saved_views.read().await;

    let mut views: Vec<SavedView> = store
        .values()
        .filter(|v| {
            // Only views in the same tenant
            if v.tenant_id != tenant_id {
                return false;
            }
            // Filter by optional entity_type
            if let Some(ref etype) = params.entity_type {
                if v.entity_type != *etype {
                    return false;
                }
            }
            // Visibility check: user's own views OR views shared with user OR public views
            v.user_id == user_id
                || v.shared_with.contains(&user_id)
                || v.visibility != ViewVisibility::Private
        })
        .cloned()
        .collect();

    views.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(views, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new saved view.
pub async fn create_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<SavedViewRequest>,
) -> Result<Json<SavedView>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    let now = Utc::now();
    let is_default = req.is_default.unwrap_or(false);

    // If this is marked as default, unmark other defaults
    if is_default {
        let mut store = state.saved_views.write().await;
        for view in store.values_mut() {
            if view.tenant_id == tenant_id && view.user_id == user_id && view.entity_type == req.entity_type {
                view.is_default = false;
            }
        }
    }

    let view = SavedView {
        id: new_id(),
        tenant_id,
        user_id,
        name: req.name.clone(),
        entity_type: req.entity_type.clone(),
        filters: req.filters,
        sort_config: req.sort_config,
        columns: req.columns,
        is_default,
        visibility: req.visibility.clone(),
        shared_with: req.shared_with,
        created_at: now,
        updated_at: now,
    };

    // Publish domain event
    let event = SavedViewCreatedEvent::new(
        tenant_id,
        view.id,
        view.name.clone(),
        view.entity_type.clone(),
        user_id,
        view.visibility.to_string(),
    );
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!(error = %e, "Failed to publish SavedViewCreatedEvent");
    }

    let mut store = state.saved_views.write().await;
    store.insert(view.id, view.clone());
    Ok(Json(view))
}

/// Get a saved view by ID.
pub async fn get_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<SavedView>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    let store = state.saved_views.read().await;
    let view = store
        .values()
        .find(|v| {
            v.id == id
                && v.tenant_id == tenant_id
                && (v.user_id == user_id
                    || v.shared_with.contains(&user_id)
                    || v.visibility != ViewVisibility::Private)
        })
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Saved view {id} not found")))?;
    Ok(Json(view))
}

/// Update a saved view.
pub async fn update_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<SavedViewRequest>,
) -> Result<Json<SavedView>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    let now = Utc::now();
    let is_default = req.is_default.unwrap_or(false);

    let mut store = state.saved_views.write().await;

    // If marking as default, unmark other defaults for the same entity type first
    if is_default {
        let keys_to_unmark: Vec<Uuid> = store
            .iter()
            .filter(|(k, v)| {
                **k != id
                    && v.tenant_id == tenant_id
                    && v.user_id == user_id
                    && v.entity_type == req.entity_type
                    && v.is_default
            })
            .map(|(k, _)| *k)
            .collect();
        for key in keys_to_unmark {
            if let Some(v) = store.get_mut(&key) {
                v.is_default = false;
            }
        }
    }

    let view = store
        .get_mut(&id)
        .filter(|v| v.tenant_id == tenant_id && v.user_id == user_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Saved view {id} not found")))?;

    let _old_name = view.name.clone();
    let _old_visibility = view.visibility.clone();
    let _old_entity_type = view.entity_type.clone();

    view.name = req.name.clone();
    view.entity_type = req.entity_type.clone();
    view.filters = req.filters;
    view.sort_config = req.sort_config;
    view.columns = req.columns;
    view.is_default = is_default;
    view.visibility = req.visibility.clone();
    view.shared_with = req.shared_with;
    view.updated_at = now;

    let updated = view.clone();

    // Publish domain event
    let event = SavedViewUpdatedEvent::new(
        tenant_id,
        id,
        updated.name.clone(),
        updated.entity_type.clone(),
        user_id,
        updated.visibility.to_string(),
    );
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!(error = %e, "Failed to publish SavedViewUpdatedEvent");
    }

    Ok(Json(updated))
}

/// Delete a saved view.
pub async fn delete_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    let mut store = state.saved_views.write().await;

    let view_name = store
        .get(&id)
        .filter(|v| v.tenant_id == tenant_id && v.user_id == user_id)
        .map(|v| v.name.clone());

    let view_name = match view_name {
        Some(name) => name,
        None => return Err(SenseiError::NotFound(format!("Saved view {id} not found"))),
    };

    store.remove(&id);

    // Publish domain event
    let event = SavedViewDeletedEvent::new(tenant_id, id, view_name, user_id);
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!(error = %e, "Failed to publish SavedViewDeletedEvent");
    }

    Ok(Json(()))
}

/// Share a saved view with specific users or set its visibility level.
///
/// Only the creator of the saved view can share it.
pub async fn share_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(view_id): Path<Uuid>,
    Json(req): Json<ShareViewRequest>,
) -> Result<Json<SavedView>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;

    let mut store = state.saved_views.write().await;
    let view = store
        .get_mut(&view_id)
        .filter(|v| v.tenant_id == tenant_id && v.user_id == user_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Saved view {view_id} not found")))?;

    view.shared_with = req.user_ids;
    view.visibility = req.visibility;
    view.updated_at = Utc::now();

    let updated = view.clone();

    // Publish domain event for the share/visibility update
    let event = SavedViewUpdatedEvent::new(
        tenant_id,
        view_id,
        updated.name.clone(),
        updated.entity_type.clone(),
        user_id,
        updated.visibility.to_string(),
    );
    if let Err(e) = state.event_bus.publish(&event).await {
        tracing::warn!(error = %e, "Failed to publish SavedViewUpdatedEvent (share)");
    }

    Ok(Json(updated))
}

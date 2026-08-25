//! Saved Views route handlers.
//!
//! Provides endpoints for managing user-saved view configurations,
//! including CRUD operations, RBAC-based sharing, and compound sorting.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{
    SavedViewCreatedEvent, SavedViewDeletedEvent, SavedViewUpdatedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{SavedView, SortConfig, ViewVisibility};

/// Validate that every shared user exists in the requesting tenant.
async fn validate_shared_users(state: &AppState, tenant_id: Uuid, user_ids: &[Uuid]) -> Result<()> {
    if user_ids.is_empty() {
        return Ok(());
    }
    let users = state.users_service.list_users().await?;
    let tenant_user_ids: std::collections::HashSet<Uuid> = users
        .iter()
        .filter(|u| u.tenant_id == tenant_id)
        .map(|u| u.id)
        .collect();
    for id in user_ids {
        if !tenant_user_ids.contains(id) {
            return Err(SenseiError::Validation(format!(
                "User {id} does not exist in this tenant"
            )));
        }
    }
    Ok(())
}

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
    let store = state.saved_views.read(user.tenant_id).await;

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
    validate_shared_users(&state, tenant_id, &req.shared_with).await?;
    let now = Utc::now();
    let is_default = req.is_default.unwrap_or(false);

    // If this is marked as default, unmark other defaults
    if is_default {
        let mut store = state.saved_views.write(user.tenant_id).await;
        for view in store.values_mut() {
            if view.tenant_id == tenant_id
                && view.user_id == user_id
                && view.entity_type == req.entity_type
            {
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
        view_count: 0,
        last_used_at: None,
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

    let mut store = state.saved_views.write(user.tenant_id).await;
    store.insert(view.id, view.clone());
    Ok(Json(view))
}

/// Get a saved view by ID.
///
/// Records usage: increments `view_count` and refreshes `last_used_at`.
pub async fn get_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<SavedView>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    let mut store = state.saved_views.write(user.tenant_id).await;
    let view = store
        .values_mut()
        .find(|v| {
            v.id == id
                && v.tenant_id == tenant_id
                && (v.user_id == user_id
                    || v.shared_with.contains(&user_id)
                    || v.visibility != ViewVisibility::Private)
        })
        .ok_or_else(|| SenseiError::NotFound(format!("Saved view {id} not found")))?;
    view.view_count = view.view_count.saturating_add(1);
    view.last_used_at = Some(Utc::now());
    Ok(Json(view.clone()))
}

/// Request body for updating a saved view (partial update).
#[derive(Debug, Deserialize)]
pub struct UpdateSavedViewRequest {
    pub name: Option<String>,
    pub entity_type: Option<String>,
    pub filters: Option<serde_json::Value>,
    #[serde(default)]
    pub sort_config: Option<Vec<SortConfig>>,
    pub columns: Option<Vec<String>>,
    pub is_default: Option<bool>,
    #[serde(default)]
    pub visibility: Option<ViewVisibility>,
    #[serde(default)]
    pub shared_with: Option<Vec<Uuid>>,
}

/// Update a saved view (partial update semantics).
pub async fn update_saved_view(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateSavedViewRequest>,
) -> Result<Json<SavedView>> {
    let tenant_id = user.tenant_id;
    let user_id = user.user_id;
    if let Some(shared) = &req.shared_with {
        validate_shared_users(&state, tenant_id, shared).await?;
    }
    let now = Utc::now();
    let is_default = req.is_default.unwrap_or(false);

    let mut store = state.saved_views.write(user.tenant_id).await;

    // If marking as default, unmark other defaults for the same entity type first
    if is_default {
        let entity_type = req
            .entity_type
            .clone()
            .or_else(|| store.get(&id).map(|v| v.entity_type.clone()))
            .unwrap_or_default();
        let keys_to_unmark: Vec<Uuid> = store
            .iter()
            .filter(|(k, v)| {
                **k != id
                    && v.tenant_id == tenant_id
                    && v.user_id == user_id
                    && v.entity_type == entity_type
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

    if let Some(name) = &req.name {
        view.name = name.clone();
    }
    if let Some(entity_type) = &req.entity_type {
        view.entity_type = entity_type.clone();
    }
    if let Some(filters) = req.filters {
        view.filters = filters;
    }
    if let Some(sort_config) = req.sort_config {
        view.sort_config = sort_config;
    }
    if let Some(columns) = req.columns {
        view.columns = columns;
    }
    if let Some(is_default) = req.is_default {
        view.is_default = is_default;
    }
    if let Some(visibility) = &req.visibility {
        view.visibility = visibility.clone();
    }
    if let Some(shared_with) = &req.shared_with {
        view.shared_with = shared_with.clone();
    }
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
    let mut store = state.saved_views.write(user.tenant_id).await;

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
    validate_shared_users(&state, tenant_id, &req.user_ids).await?;

    let mut store = state.saved_views.write(user.tenant_id).await;
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

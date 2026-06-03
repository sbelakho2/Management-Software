//! Saved Views route handlers.
//!
//! Provides endpoints for managing user-saved view configurations,
//! including CRUD operations.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::SavedView;

// ── Request DTOs ───────────────────────────────────────────────────────────

/// Query parameters for listing saved views.
#[derive(Debug, Deserialize)]
pub struct ListSavedViewsParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a saved view.
#[derive(Debug, Deserialize)]
pub struct SavedViewRequest {
    pub name: String,
    pub entity_type: String,
    pub filters: serde_json::Value,
    pub sort_by: Option<String>,
    pub sort_order: Option<String>,
    pub columns: Vec<String>,
    pub is_default: Option<bool>,
}

// ── Saved Views ────────────────────────────────────────────────────────────

/// List saved views for the current user with pagination.
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
        .filter(|v| v.tenant_id == tenant_id && v.user_id == user_id)
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
        name: req.name,
        entity_type: req.entity_type,
        filters: req.filters,
        sort_by: req.sort_by,
        sort_order: req.sort_order,
        columns: req.columns,
        is_default,
        created_at: now,
        updated_at: now,
    };
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
        .find(|v| v.id == id && v.tenant_id == tenant_id && v.user_id == user_id)
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

    view.name = req.name;
    view.entity_type = req.entity_type;
    view.filters = req.filters;
    view.sort_by = req.sort_by;
    view.sort_order = req.sort_order;
    view.columns = req.columns;
    view.is_default = is_default;
    view.updated_at = now;
    Ok(Json(view.clone()))
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
    let exists = store
        .get(&id)
        .filter(|v| v.tenant_id == tenant_id && v.user_id == user_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("Saved view {id} not found")));
    }
    store.remove(&id);
    Ok(Json(()))
}

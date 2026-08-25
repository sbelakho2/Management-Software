//! Learning module management route handlers.
//!
//! Provides CRUD endpoints for learning/training modules.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::LearningModule;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing learning modules.
#[derive(Debug, Deserialize)]
pub struct ListModulesParams {
    pub category: Option<String>,
    pub difficulty: Option<String>,
    pub is_published: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a learning module.
#[derive(Debug, Deserialize)]
pub struct ModuleRequest {
    pub title: String,
    pub description: String,
    pub category: String,
    pub difficulty: String,
    pub estimated_duration_minutes: Option<i32>,
    pub content_url: Option<String>,
    pub is_published: bool,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// List all learning modules with optional filters.
pub async fn list_modules(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListModulesParams>,
) -> Result<Json<PaginatedResponse<LearningModule>>> {
    let store = state.learning_modules.read().await;
    let mut modules: Vec<LearningModule> = store
        .values()
        .filter(|m| m.tenant_id == user.tenant_id)
        .filter(|m| params.category.as_ref().is_none_or(|c| m.category == *c))
        .filter(|m| {
            params
                .difficulty
                .as_ref()
                .is_none_or(|d| m.difficulty == *d)
        })
        .filter(|m| params.is_published.is_none_or(|p| m.is_published == p))
        .cloned()
        .collect();
    modules.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
    let result = PaginatedResponse::new(modules, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new learning module.
pub async fn create_module(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ModuleRequest>,
) -> Result<Json<LearningModule>> {
    let now = Utc::now();
    let module = LearningModule {
        id: new_id(),
        tenant_id: user.tenant_id,
        title: req.title,
        description: req.description,
        category: req.category,
        difficulty: req.difficulty,
        estimated_duration_minutes: req.estimated_duration_minutes,
        content_url: req.content_url,
        is_published: req.is_published,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.learning_modules.write().await;
    store.insert(module.id, module.clone());
    Ok(Json(module))
}

/// Get a specific learning module by ID.
pub async fn get_module(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<LearningModule>> {
    let store = state.learning_modules.read().await;
    let module = store
        .values()
        .find(|m| m.id == id && m.tenant_id == user.tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Learning module {id} not found")))?;
    Ok(Json(module))
}

/// Update a learning module.
pub async fn update_module(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ModuleRequest>,
) -> Result<Json<LearningModule>> {
    let mut store = state.learning_modules.write().await;
    let module = store
        .get_mut(&id)
        .filter(|m| m.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Learning module {id} not found")))?;
    module.title = req.title;
    module.description = req.description;
    module.category = req.category;
    module.difficulty = req.difficulty;
    module.estimated_duration_minutes = req.estimated_duration_minutes;
    module.content_url = req.content_url;
    module.is_published = req.is_published;
    module.updated_at = Utc::now();
    Ok(Json(module.clone()))
}

/// Delete a learning module.
pub async fn delete_module(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let mut store = state.learning_modules.write().await;
    let exists = store
        .get(&id)
        .filter(|m| m.tenant_id == user.tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!(
            "Learning module {id} not found"
        )));
    }
    store.remove(&id);
    Ok(Json(()))
}

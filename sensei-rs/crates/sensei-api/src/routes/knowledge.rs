//! Knowledge pack management route handlers.
//!
//! Provides CRUD endpoints for knowledge packs used in the
//! training and continuous improvement system.

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
use crate::stores::KnowledgePack;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing knowledge packs.
#[derive(Debug, Deserialize)]
pub struct ListPacksParams {
    pub category: Option<String>,
    pub tag: Option<String>,
    pub is_published: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a knowledge pack.
#[derive(Debug, Deserialize)]
pub struct PackRequest {
    pub title: String,
    pub description: String,
    pub category: String,
    pub tags: Vec<String>,
    pub content: String,
    pub source_url: Option<String>,
    pub version: String,
    pub is_published: bool,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// List all knowledge packs with optional filters.
pub async fn list_packs(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListPacksParams>,
) -> Result<Json<PaginatedResponse<KnowledgePack>>> {
    user.require_permission("knowledge:read")?;
    let store = state.knowledge_packs.read(user.tenant_id).await;
    let mut packs: Vec<KnowledgePack> = store
        .values()
        .filter(|p| p.tenant_id == user.tenant_id)
        .filter(|p| params.category.as_ref().is_none_or(|c| p.category == *c))
        .filter(|p| {
            params
                .is_published
                .is_none_or(|p_flag| p.is_published == p_flag)
        })
        .filter(|p| {
            params
                .tag
                .as_ref()
                .is_none_or(|t| p.tags.iter().any(|tag| tag == t))
        })
        .cloned()
        .collect();
    packs.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
    let result = PaginatedResponse::new(packs, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new knowledge pack.
pub async fn create_pack(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PackRequest>,
) -> Result<Json<KnowledgePack>> {
    user.require_permission("knowledge:manage")?;
    let now = Utc::now();
    let pack = KnowledgePack {
        id: new_id(),
        tenant_id: user.tenant_id,
        title: req.title,
        description: req.description,
        category: req.category,
        tags: req.tags,
        content: req.content,
        source_url: req.source_url,
        version: req.version,
        is_published: req.is_published,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.knowledge_packs.write(user.tenant_id).await;
    store.insert(pack.id, pack.clone());
    Ok(Json(pack))
}

/// Get a specific knowledge pack by ID.
pub async fn get_pack(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<KnowledgePack>> {
    user.require_permission("knowledge:read")?;
    let store = state.knowledge_packs.read(user.tenant_id).await;
    let pack = store
        .values()
        .find(|p| p.id == id && p.tenant_id == user.tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Knowledge pack {id} not found")))?;
    Ok(Json(pack))
}

/// Update a knowledge pack.
pub async fn update_pack(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PackRequest>,
) -> Result<Json<KnowledgePack>> {
    user.require_permission("knowledge:manage")?;
    let mut store = state.knowledge_packs.write(user.tenant_id).await;
    let pack = store
        .get_mut(&id)
        .filter(|p| p.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Knowledge pack {id} not found")))?;
    pack.title = req.title;
    pack.description = req.description;
    pack.category = req.category;
    pack.tags = req.tags;
    pack.content = req.content;
    pack.source_url = req.source_url;
    pack.version = req.version;
    pack.is_published = req.is_published;
    pack.updated_at = Utc::now();
    Ok(Json(pack.clone()))
}

/// Delete a knowledge pack.
pub async fn delete_pack(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("knowledge:manage")?;
    let mut store = state.knowledge_packs.write(user.tenant_id).await;
    let exists = store
        .get(&id)
        .filter(|p| p.tenant_id == user.tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!(
            "Knowledge pack {id} not found"
        )));
    }
    store.remove(&id);
    Ok(Json(()))
}

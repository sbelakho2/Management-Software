//! Knowledge pack management route handlers.
//!
//! Provides CRUD endpoints for knowledge packs used in the
//! training and continuous improvement system.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
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
    /// Source authority (item 24): one of the enum classes.
    #[serde(default)]
    pub authority: Option<crate::stores::KnowledgeAuthority>,
    #[serde(default)]
    pub effective_from: Option<DateTime<Utc>>,
    #[serde(default)]
    pub effective_to: Option<DateTime<Utc>>,
    #[serde(default)]
    pub supersedes: Option<Uuid>,
    #[serde(default)]
    pub status: Option<crate::stores::KnowledgeStatus>,
    /// ACL prefilter: roles that may retrieve this pack (empty = all
    /// authenticated tenant users).
    #[serde(default)]
    pub allowed_roles: Option<Vec<String>>,
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
        // ACL prefilter: role-restricted packs are invisible to callers
        // without the role (never retrieved, never mentioned).
        .filter(|p| {
            p.allowed_roles.is_empty() || p.allowed_roles.iter().any(|r| user.roles.contains(r))
        })
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
        authority: req
            .authority
            .unwrap_or(crate::stores::KnowledgeAuthority::EmployeeNote),
        effective_from: req.effective_from,
        effective_to: req.effective_to,
        supersedes: req.supersedes,
        status: req.status.unwrap_or(if req.is_published {
            crate::stores::KnowledgeStatus::Effective
        } else {
            crate::stores::KnowledgeStatus::Draft
        }),
        allowed_roles: req.allowed_roles.unwrap_or_default(),
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.knowledge_packs.write(user.tenant_id).await;
    store.insert(pack.id, pack.clone());
    store.persist().await?;
    // Populate the DENSE retrieval leg (deterministic local embedding).
    if let Some(pool) = state.db_pool.as_ref() {
        let _ = crate::services::hybrid_retrieval::upsert_embedding(
            pool,
            user.tenant_id,
            "knowledge_pack",
            pack.id,
            &pack.title,
            &pack.content,
        )
        .await;
    }
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

/// Update a knowledge pack (item 23): the mutation is PERSISTED, the
/// authority/validity/ACL fields are updated, and the dense embedding is
/// REFRESHED — an administrator's update is immediately reflected in the
/// RAG corpus, never silently ignored.
pub async fn update_pack(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PackRequest>,
) -> Result<Json<KnowledgePack>> {
    user.require_permission("knowledge:manage")?;
    let mut store = state.knowledge_packs.write(user.tenant_id).await;
    let mut pack = store
        .get(&id)
        .filter(|p| p.tenant_id == user.tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Knowledge pack {id} not found")))?;
    pack.title = req.title;
    pack.description = req.description;
    pack.category = req.category;
    pack.tags = req.tags;
    pack.content = req.content;
    pack.source_url = req.source_url;
    pack.version = req.version;
    pack.is_published = req.is_published;
    if let Some(authority) = req.authority {
        pack.authority = authority;
    }
    if req.effective_from.is_some() {
        pack.effective_from = req.effective_from;
    }
    if req.effective_to.is_some() {
        pack.effective_to = req.effective_to;
    }
    if req.supersedes.is_some() {
        pack.supersedes = req.supersedes;
    }
    if let Some(status) = req.status {
        pack.status = status;
    }
    if req.allowed_roles.is_some() {
        pack.allowed_roles = req.allowed_roles.unwrap_or_default();
    }
    pack.updated_at = Utc::now();
    store.insert(pack.id, pack.clone());
    store.persist().await?;
    // Refresh the dense leg: the OLD embedding must never keep serving the
    // superseded content (item 23).
    if let Some(pool) = state.db_pool.as_ref() {
        let _ = crate::services::hybrid_retrieval::upsert_embedding(
            pool,
            user.tenant_id,
            "knowledge_pack",
            pack.id,
            &pack.title,
            &pack.content,
        )
        .await;
    }
    Ok(Json(pack))
}

/// Delete a knowledge pack (item 23): the removal is PERSISTED and the
/// dense embedding is REMOVED — deleted guidance can never resurface
/// through the RAG corpus.
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
    store.persist().await?;
    if let Some(pool) = state.db_pool.as_ref() {
        let _ = sqlx::query(
            "DELETE FROM document_embeddings \
             WHERE tenant_id = $1 AND document_type = 'knowledge_pack' AND document_id = $2",
        )
        .bind(user.tenant_id)
        .bind(id)
        .execute(pool.as_ref())
        .await;
    }
    Ok(Json(()))
}

//! Full-text search route handler.
//!
//! Provides a unified search endpoint across multiple entity types by
//! delegating to the [`SearchService`] (database-backed or in-memory).
//! Supports optional entity-type filtering and pagination.

use axum::{
    extract::{Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_services::ops::search::SearchResult;
use serde::{Deserialize, Serialize};

use crate::state::AppState;

// ── Query / Response DTOs ────────────────────────────────────────────────────

/// Query parameters for unified search.
#[derive(Debug, Deserialize)]
pub struct SearchParams {
    /// The search query string.
    pub q: String,
    /// Maximum number of results to return (default 10, max 50).
    pub limit: Option<usize>,
    /// Optional entity type filter: "task", "account", "contact", "product",
    /// "user", "kanban_board", "obeya_board", "knowledge_pack",
    /// "training_course", "work_center", etc.
    pub entity_type: Option<String>,
}

/// A facet bucket: entity type + number of matching results.
#[derive(Debug, Serialize)]
pub struct SearchFacet {
    pub entity_type: String,
    pub count: usize,
}

/// Unified search response.
#[derive(Debug, Serialize)]
pub struct SearchResponse {
    pub results: Vec<SearchResult>,
    pub total: usize,
    pub query: String,
    /// Facet counts grouped by result type, computed from the full result
    /// set (before the `limit` truncation).
    pub facets: Vec<SearchFacet>,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Unified search across users, accounts, contacts, products, and PM entities.
pub async fn search(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<SearchParams>,
) -> Result<Json<SearchResponse>> {
    let query = params.q.trim().to_string();
    let limit = params.limit.unwrap_or(10).clamp(1, 50);

    let results = state
        .search_service
        .search(user.tenant_id, &query, params.entity_type.as_deref())
        .await?;

    let total = results.len();

    // Facets group the full result set by entity type, ordered by count
    // descending.
    let mut facet_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    for result in &results {
        *facet_map.entry(result.result_type.clone()).or_insert(0) += 1;
    }
    let mut facets: Vec<SearchFacet> = facet_map
        .into_iter()
        .map(|(entity_type, count)| SearchFacet { entity_type, count })
        .collect();
    facets.sort_by(|a, b| {
        b.count
            .cmp(&a.count)
            .then_with(|| a.entity_type.cmp(&b.entity_type))
    });

    let results = results.into_iter().take(limit).collect();

    Ok(Json(SearchResponse {
        results,
        total,
        query,
        facets,
    }))
}

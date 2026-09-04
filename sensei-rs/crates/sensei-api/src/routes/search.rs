//! Full-text search route handler.
//!
//! Provides a unified search endpoint across multiple entity types by
//! delegating to the [`SearchService`] (database-backed or in-memory).
//! Supports optional entity-type filtering and pagination.
//!
//! # Authorization (twenty-ninth-audit Wave B item 10)
//!
//! Search is never a tenant-wide, type-unrestricted listing: the caller's
//! effective [`AllowedSearchProjection`] is precomputed here — every
//! result type whose read permission the caller lacks is dropped, and the
//! operational types (work centers, standard work, production cells) are
//! restricted to the caller's `RequestContext` authorized sites. The
//! projection is passed INTO the database search so candidate tables are
//! filtered before ranking; a caller with nothing admissible gets an
//! empty result set, never a fallback to an unrestricted search.

use axum::{
    extract::{Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_services::ops::search::SearchResult;
use serde::{Deserialize, Serialize};

use crate::authorization::search_policy::AllowedSearchProjection;
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

/// Results are merged per backend and truncated to this cap before the
/// response-level `limit` applies (mirrors the backends' own caps).
const MERGE_CAP: usize = 50;

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Unified search across users, accounts, contacts, products, and PM entities.
///
/// The admissible search surface is derived from the caller's live
/// permissions and operational scope BEFORE any backend query runs:
/// types the caller may not read are never searched, and a caller with no
/// admissible type receives an empty result set.
pub async fn search(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<SearchParams>,
) -> Result<Json<SearchResponse>> {
    let query = params.q.trim().to_string();
    let limit = params.limit.unwrap_or(10).clamp(1, 50);

    let projection =
        AllowedSearchProjection::for_caller(&state, &user, params.entity_type.as_deref()).await?;

    let results = if projection.entity_types().is_empty() {
        Vec::new()
    } else if let Some(pool) = &state.db_pool {
        // Database deployment: the admissible projection travels INTO the
        // search so candidate tables are filtered before ranking.
        crate::db_search_service::search_db_authorized(pool, user.tenant_id, &query, &projection)
            .await?
    } else {
        // In-memory/dev deployment (no site rows to entangle): run one
        // bounded search per admissible type so inadmissible types can
        // never leak through the untyped service contract.
        let mut merged: Vec<SearchResult> = Vec::new();
        for &result_type in projection.entity_types() {
            let partial = state
                .search_service
                .search(user.tenant_id, &query, Some(result_type))
                .await?;
            merged.extend(partial);
        }
        merged.sort_by(|a, b| {
            b.relevance
                .partial_cmp(&a.relevance)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.result_type.cmp(&b.result_type))
                .then_with(|| a.result_id.cmp(&b.result_id))
        });
        merged.truncate(MERGE_CAP);
        merged
    };

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

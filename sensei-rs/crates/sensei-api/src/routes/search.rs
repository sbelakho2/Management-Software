//! Full-text search route handler.
//!
//! Provides a unified search endpoint across multiple entity types by
//! delegating to the [`SearchService`] (database-backed or in-memory).

use axum::{Json, extract::{Query, State}};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_services::ops::search::SearchResult;

use crate::state::AppState;

// ── Query / Response DTOs ────────────────────────────────────────────────────

/// Query parameters for unified search.
#[derive(Debug, Deserialize)]
pub struct SearchParams {
    /// The search query string.
    pub q: String,
    /// Maximum number of results to return (default 10, max 50).
    pub limit: Option<usize>,
}

/// Unified search response.
#[derive(Debug, Serialize)]
pub struct SearchResponse {
    pub results: Vec<SearchResult>,
    pub total: usize,
    pub query: String,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Unified search across users, accounts, contacts, and products.
pub async fn search(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<SearchParams>,
) -> Result<Json<SearchResponse>> {
    let query = params.q.trim().to_string();
    let limit = params.limit.unwrap_or(10).max(1).min(50);

    let mut results = state
        .search_service
        .search(user.tenant_id, &query)
        .await?;

    let total = results.len();
    results.truncate(limit);

    Ok(Json(SearchResponse {
        results,
        total,
        query,
    }))
}

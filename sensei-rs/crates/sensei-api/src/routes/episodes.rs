//! Episode memory routes (fifteenth audit 12/14): historical operational
//! episodes (NCR, andon, standard change, customer complaint, supplier
//! issue) with ASSOCIATIVE retrieval — episodes are related through their
//! SHARED LINKS (supplier / machine / process / material / part family /
//! operator / work center), never through textual similarity. A
//! "connector intermittent failure" associates with the "crimp force
//! drop" on the same supplier even when the text is dissimilar.
//!
//! Episodes are a first-class organizational memory tier: `record` writes
//! the episode, `related` walks the links to find what happened before,
//! ranked by the number of links shared with the probe.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::episodes::{self, Episode};

// ── Request DTOs ─────────────────────────────────────────────────────────────

/// Body for `POST /api/v1/episodes`. `links` is a JSON array of
/// `{kind, id, label}` objects (supplier, machine, process, material,
/// part family, operator, work center) — the associative retrieval keys.
#[derive(Debug, Deserialize)]
pub struct RecordEpisodeRequest {
    pub episode_type: String, // ncr | andon | standard_change | customer_complaint | supplier_issue
    pub title: String,
    pub description: Option<String>,
    #[serde(default = "default_status")]
    pub status: String,
    pub outcome: Option<String>,
    pub confidence: Option<f64>,
    #[serde(default)]
    pub links: Vec<serde_json::Value>,
    pub source_entity_type: Option<String>,
    pub source_entity_id: Option<Uuid>,
}

fn default_status() -> String {
    "open".to_string()
}

/// Body for `POST /api/v1/episodes/related` — the probe links, plus an
/// optional result limit.
#[derive(Debug, Deserialize)]
pub struct RelatedRequest {
    #[serde(default)]
    pub links: Vec<serde_json::Value>,
    #[serde(default = "default_limit")]
    pub limit: i64,
}

fn default_limit() -> i64 {
    10
}

// ── Helpers ─────────────────────────────────────────────────────────────────

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Episode memory requires the database".to_string()))
        .map(|p| p.as_ref())
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `POST /api/v1/episodes` — record a historical operational episode (an
/// NCR resolved, an andon with a countermeasure, a standard changed) with
/// its associative links.
pub async fn record(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RecordEpisodeRequest>,
) -> Result<Json<Uuid>> {
    user.require_permission("knowledge:read")?;
    let p = pool(&state)?;
    let id = episodes::record_episode(
        p,
        user.tenant_id,
        &req.episode_type,
        &req.title,
        req.description.as_deref(),
        &req.status,
        req.outcome.as_deref(),
        req.confidence,
        req.links,
        req.source_entity_type.as_deref(),
        req.source_entity_id,
    )
    .await?;
    Ok(Json(id))
}

/// `GET /api/v1/episodes/{id}` — fetch one episode.
pub async fn get(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Episode>> {
    user.require_permission("knowledge:read")?;
    let p = pool(&state)?;
    Ok(Json(episodes::get_episode(p, user.tenant_id, id).await?))
}

/// `POST /api/v1/episodes/related` — ASSOCIATIVE retrieval: episodes
/// sharing ANY link (kind + id) with the probe are returned, ranked by
/// the number of shared links. Text is never consulted.
pub async fn related(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RelatedRequest>,
) -> Result<Json<Vec<Episode>>> {
    user.require_permission("knowledge:read")?;
    let p = pool(&state)?;
    let rows = episodes::find_related(p, user.tenant_id, &req.links, req.limit).await?;
    Ok(Json(rows))
}

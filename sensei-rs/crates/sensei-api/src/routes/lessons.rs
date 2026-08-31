//! Lesson routes (fifteenth audit items 46-47 + law A19): explicit lesson
//! objects with context signatures and APPLICABILITY.
//!
//! Yokoten is an EXPERIMENT, never blind replication: a lesson from
//! another site is offered as a comparison ("a similar issue was resolved
//! elsewhere — would you like to compare conditions?"), the local team
//! verifies applicability HERE, and only then may it be adopted. The
//! ladder is proposed -> verified (locally) -> adopted.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::lessons::{
    self, adopt, mark_verified, recommend_countermeasures, record_lesson, yokoten_match, Lesson,
    NewLesson,
};

// ── Request DTOs ────────────────────────────────────────────────────────────

/// Body for `POST /api/v1/lessons/{id}/verify` — the LOCAL verification
/// act. `verified_locally: true` means the local experiment passed
/// (status -> `verified`); `false` rejects the lesson outright.
#[derive(Debug, Deserialize)]
pub struct VerifyRequest {
    pub verified_locally: bool,
}

/// Body for `POST /api/v1/lessons/yokoten` — match proposed/verified
/// lessons against the local context.
#[derive(Debug, Deserialize)]
pub struct YokotenRequest {
    pub context_signature: serde_json::Value,
}

/// Body for `POST /api/v1/lessons/recommend` — the RECURRING condition
/// the team faces; prior countermeasures are offered as comparison
/// hypotheses, never prescriptions.
#[derive(Debug, Deserialize)]
pub struct RecommendRequest {
    pub condition_context: serde_json::Value,
}

// ── Helpers ─────────────────────────────────────────────────────────────────

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Lessons require the database".to_string()))
        .map(|p| p.as_ref())
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `POST /api/v1/lessons` — record a lesson. It always enters the ladder
/// as `proposed`; the local team decides whether the countermeasure
/// applies HERE.
pub async fn create(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<NewLesson>,
) -> Result<Json<Lesson>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    let id = record_lesson(p, user.tenant_id, req).await?;
    lessons::get_lesson(p, user.tenant_id, id).await.map(Json)
}

/// `POST /api/v1/lessons/{id}/verify` — the local verification act: only
/// a `proposed` lesson can become `verified` (experiment passed) or
/// `rejected` (experiment failed).
pub async fn verify(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<VerifyRequest>,
) -> Result<Json<Lesson>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    mark_verified(p, user.tenant_id, id, req.verified_locally).await?;
    lessons::get_lesson(p, user.tenant_id, id).await.map(Json)
}

/// `POST /api/v1/lessons/{id}/adopt` — the final yokoten gate: only a
/// lesson the local team verified can be adopted.
pub async fn adopt_handler(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Lesson>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    adopt(p, user.tenant_id, id).await?;
    lessons::get_lesson(p, user.tenant_id, id).await.map(Json)
}

/// `POST /api/v1/lessons/yokoten` — offer lessons that overlap the local
/// context signature as comparisons ("a similar issue was resolved
/// elsewhere — would you like to compare conditions?"). Only
/// proposed/verified lessons are offered; applicability is verified
/// locally, never assumed.
pub async fn yokoten(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<YokotenRequest>,
) -> Result<Json<Vec<Lesson>>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    let matches = yokoten_match(p, user.tenant_id, req.context_signature).await?;
    Ok(Json(matches))
}

/// `POST /api/v1/lessons/recommend` — for a RECURRING condition, offer
/// prior countermeasures whose context signature overlaps it as
/// comparison HYPOTHESES (fifteenth audit items 12/14). Only locally
/// verified/adopted lessons are offered — applicability still belongs to
/// the local team (A19), never assumed.
pub async fn recommend(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RecommendRequest>,
) -> Result<Json<Vec<Lesson>>> {
    user.require_permission("training:read")?;
    let p = pool(&state)?;
    let matches = recommend_countermeasures(p, user.tenant_id, req.condition_context).await?;
    Ok(Json(matches))
}

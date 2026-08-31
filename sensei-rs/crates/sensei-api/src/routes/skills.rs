//! TWI skill graph routes (fifteenth audit 37-39): job standards with
//! action/key points/REASONS/hazards/checks and a REAL skill graph with
//! demonstrated evidence, recency and turnover-resilience metrics (bus
//! factor, single-person knowledge concentration).
//!
//! The coverage endpoint makes "Shift 2 is technically staffed but only
//! one person can independently run AOI programming" DETECTABLE: it
//! reports how many principals can run each skill independently and
//! flags skills where that number is exactly one.

use axum::{
    extract::{Path, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::tps::skills::{
    DepartureForecast, JobStep, SkillCoverage, SkillLevel, TurnoverRisk,
};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Request DTOs ───────────────────────────────────────────────────────────

/// Body for creating a skill.
#[derive(Debug, Deserialize)]
pub struct CreateSkillRequest {
    pub skill_id: String,
    pub name: String,
    pub process: Option<String>,
    pub standard_id: Option<String>,
    #[serde(default)]
    pub critical: bool,
}

/// Body for creating a job standard under a skill.
///
/// TWI shape rule: every step must carry `action`, `key_points`,
/// `reasons`, `hazards` and `checks`. The `reasons` field MUST EXIST (the
/// WHY is essential) even when empty for trivial steps — a payload missing
/// `reasons` fails deserialization before reaching the service.
#[derive(Debug, Deserialize)]
pub struct CreateJobStandardRequest {
    pub standard_id: String,
    pub revision: i64,
    pub process: String,
    pub title: String,
    pub steps: Vec<JobStep>,
}

/// Body for recording an evidence-based qualification (promotion up the
/// skill ladder).
#[derive(Debug, Deserialize)]
pub struct QualifyRequest {
    pub principal_id: Uuid,
    pub level: SkillLevel,
    /// The demonstration evidence (certification ref, observation record,
    /// demonstrated-by, ...). Promotion is always explicit evidence-based.
    pub evidence: serde_json::Value,
}

// ── Handlers ───────────────────────────────────────────────────────────────

fn pool_or_err(state: &AppState) -> Result<std::sync::Arc<sqlx::PgPool>> {
    state
        .db_pool
        .clone()
        .ok_or_else(|| SenseiError::Database("Skills require the database".to_string()))
}

/// POST /api/v1/skills — create a skill (idempotent by skill_id).
pub async fn create_skill(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateSkillRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("training:manage")?;
    let pool = pool_or_err(&state)?;
    let id = sensei_services::tps::skills::create_skill(
        &pool,
        user.tenant_id,
        &req.skill_id,
        &req.name,
        req.process.as_deref(),
        req.standard_id.as_deref(),
        req.critical,
    )
    .await?;
    Ok(Json(
        serde_json::json!({ "id": id, "skill_id": req.skill_id }),
    ))
}

/// POST /api/v1/skills/{skill_id}/standards — create a TWI job standard
/// with steps (action, key points, reasons, hazards, checks).
pub async fn create_job_standard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(skill_id): Path<String>,
    Json(req): Json<CreateJobStandardRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("tps:standard-work:draft")?;
    let pool = pool_or_err(&state)?;
    let id = sensei_services::tps::skills::create_job_standard(
        &pool,
        user.tenant_id,
        &skill_id,
        &req.standard_id,
        req.revision,
        &req.process,
        &req.title,
        req.steps,
    )
    .await?;
    Ok(Json(
        serde_json::json!({ "id": id, "standard_id": req.standard_id }),
    ))
}

/// POST /api/v1/skills/{skill_id}/qualify — record an evidence-based
/// qualification for a principal on this skill.
pub async fn qualify(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(skill_id): Path<String>,
    Json(req): Json<QualifyRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("training:manage")?;
    let pool = pool_or_err(&state)?;
    let tenant_id = user.tenant_id;
    // Resolve the URL skill id to the skill's row id.
    let skill_uuid: Uuid = {
        let mut tx = pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin tx: {e}")))?;
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
        let id = sqlx::query_scalar("SELECT id FROM skills WHERE tenant_id = $1 AND skill_id = $2")
            .bind(tenant_id)
            .bind(&skill_id)
            .fetch_optional(&mut *tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read skill: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Skill {skill_id} not found")))?;
        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit tx: {e}")))?;
        id
    };
    sensei_services::tps::skills::record_qualification(
        &pool,
        tenant_id,
        req.principal_id,
        skill_uuid,
        req.level,
        req.evidence,
        None,
    )
    .await?;
    Ok(Json(
        serde_json::json!({ "skill_id": skill_id, "principal_id": req.principal_id, "level": req.level }),
    ))
}

/// GET /api/v1/skills/coverage — the skill graph leadership sees: bus
/// factor and single-person knowledge concentration per skill.
pub async fn coverage(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<SkillCoverage>>> {
    user.require_permission("training:read")?;
    let pool = pool_or_err(&state)?;
    let result = sensei_services::tps::skills::skill_coverage(&pool, user.tenant_id).await?;
    Ok(Json(result))
}

/// GET /api/v1/skills/turnover-risk — the site-level turnover-resilience
/// view (fifteenth audit 39/63): single-person knowledge concentration,
/// trainer coverage, and the key metric "% of critical operations with
/// >= 2 independent qualified people".
pub async fn turnover_risk(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<TurnoverRisk>> {
    user.require_permission("training:read")?;
    let pool = pool_or_err(&state)?;
    let result = sensei_services::tps::skills::turnover_risk(&pool, user.tenant_id).await?;
    Ok(Json(result))
}

/// GET /api/v1/skills/forecast/{principal_id} — skill-risk forecasting
/// (fifteenth audit items 39/63 + P3): if THIS principal left tomorrow,
/// which critical skills would become single-point? Succession gaps are
/// detectable before they happen.
pub async fn forecast_departure(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(principal_id): Path<Uuid>,
) -> Result<Json<DepartureForecast>> {
    user.require_permission("training:read")?;
    let pool = pool_or_err(&state)?;
    let result =
        sensei_services::tps::skills::forecast_departure(&pool, user.tenant_id, principal_id)
            .await?;
    Ok(Json(result))
}

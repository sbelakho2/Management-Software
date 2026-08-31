//! Corporate federation routes (fifteenth audit 29/46/66-67 + A19/A24):
//! cross-site aggregation with authorization. Corporate analytics are
//! MIX-NORMALIZED — a raw Bizerte-vs-Tangier FPY leaderboard is
//! forbidden; the comparison always carries the complexity adjustment.
//! Causal questions ("Why is Bizerte better at changeovers?") return
//! HYPOTHESES with evidence, never answers. Lesson propagation is the
//! corporate yokoten act: the source lesson is copied to the TARGET
//! tenant as `proposed` with `origin_site_id` set — the target tenant
//! verifies applicability locally via its own lesson endpoints.

use axum::extract::{Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::corporate::{
    causal_candidates, cross_site_analytics, CausalChain, CrossSiteAnalytics,
};
use sensei_services::tps::lessons::{self, Lesson};

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Corporate layer requires the database".to_string()))
        .map(|p| p.as_ref())
}

/// Query parameters for `GET /api/v1/corporate/causal` — defaults are
/// the canonical changeover question from item 67.
#[derive(Debug, Deserialize)]
pub struct CausalQuery {
    #[serde(default = "default_changeover")]
    pub metric_gap: String,
    #[serde(default = "default_changeover")]
    pub object_type: String,
}

fn default_changeover() -> String {
    "changeover".to_string()
}

/// Body for `POST /api/v1/corporate/lessons/propagate` — the corporate
/// yokoten act: copy THIS tenant's lesson to the target tenant as a
/// `proposed` offer.
#[derive(Debug, Deserialize)]
pub struct PropagateRequest {
    pub lesson_id: Uuid,
    pub target_tenant_id: Uuid,
}

/// `GET /api/v1/corporate/analytics` — the mix-normalized cross-site
/// view. `mix_normalized` is always true: the response shape exists so
/// consumers cannot build a naive leaderboard by accident.
pub async fn analytics(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<CrossSiteAnalytics>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let analytics = cross_site_analytics(p, user.tenant_id).await?;
    Ok(Json(analytics))
}

/// `GET /api/v1/corporate/causal?metric_gap=changeover&object_type=changeover`
/// — "Why is Bizerte better at changeovers?" answered with HYPOTHESES and
/// evidence; every candidate carries `epistemic_status = "hypothesis"`,
/// never "fact".
pub async fn causal(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(query): Query<CausalQuery>,
) -> Result<Json<CausalChain>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let chain = causal_candidates(p, user.tenant_id, &query.metric_gap, &query.object_type).await?;
    Ok(Json(chain))
}

/// `POST /api/v1/corporate/lessons/propagate` — copy the lesson from THIS
/// tenant to the TARGET tenant as `proposed` with `origin_site_id` set.
/// The copy runs in two tenant-scoped transactions (source read, target
/// insert); the target tenant then verifies locally via its own lesson
/// endpoints — the transfer is an experiment, never blind replication.
pub async fn propagate_lesson(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PropagateRequest>,
) -> Result<Json<Lesson>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let id = sensei_services::tps::corporate::propagate_lesson(
        p,
        user.tenant_id,
        req.target_tenant_id,
        req.lesson_id,
    )
    .await?;
    lessons::get_lesson(p, req.target_tenant_id, id)
        .await
        .map(Json)
}

//! Corporate federation routes (fifteenth audit 29/46/66-67 + A19/A24,
//! sixteenth audit items 1/25-28): cross-site aggregation with
//! authorization. Corporate analytics are STRATIFIED — FPY is reported
//! per product family and only the SAME family is comparable across
//! sites; a raw Bizerte-vs-Tangier FPY leaderboard is forbidden. Causal
//! questions ("Why is Bizerte better at changeovers?") return HYPOTHESES
//! with evidence, never answers. Lesson propagation is an OFFER, not a
//! write: the source proves federation membership server-side and the
//! target tenant verifies applicability locally via its own lesson
//! endpoints. `GET /api/v1/metrics/{metric_id}` exposes the ONE metric
//! engine: API, dashboard, AI and corporate rollup all call the same
//! Rust computers.

use axum::extract::{Path, Query, State};
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
use sensei_services::tps::metric_engine::{compute_metric, MetricResult};

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

/// `GET /api/v1/corporate/analytics` — the stratified cross-site view.
/// `stratified` carries the per-site FPY WITHIN the same product family:
/// the response shape exists so consumers cannot build a naive
/// leaderboard by accident.
pub async fn analytics(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<CrossSiteAnalytics>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let analytics = cross_site_analytics(p, user.tenant_id).await?;
    Ok(Json(analytics))
}

/// Query parameters for `GET /api/v1/metrics/{metric_id}` — the optional
/// site filter. Site-scoped metrics (fpy, scrap_rate) are computed for
/// that site; sales-order metrics (otd, lead_time) are tenant-level
/// because sales_orders carry no site scope in this schema.
#[derive(Debug, Deserialize)]
pub struct MetricQuery {
    pub site_id: Option<Uuid>,
}

/// `GET /api/v1/metrics/{metric_id}?site_id=...` (sixteenth audit items
/// 27-28): ONE executable metric engine — API, dashboard, AI and
/// corporate rollup all call the same Rust computers; the database metric
/// catalog DESCRIBES, Rust COMPUTES. Unknown metric ids are a Validation
/// error.
pub async fn metric_value(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(metric_id): Path<String>,
    Query(query): Query<MetricQuery>,
) -> Result<Json<MetricResult>> {
    user.require_permission("tps:kpi:read")?;
    let p = pool(&state)?;
    let result = compute_metric(p, user.tenant_id, &metric_id, query.site_id).await?;
    Ok(Json(result))
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

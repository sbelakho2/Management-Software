//! Site-edge replication routes (fifteenth audit 29/A15): sites enqueue
//! AUTHORIZED state projections; corporate pulls them. The log is the
//! local-first boundary — site operations never depend on the corporate
//! link; the corporate pull is atomic (claim + read in one transaction).

use axum::extract::{Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::replication::{self, ReplicationEntry};

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Replication requires the database".to_string()))
        .map(|p| p.as_ref())
}

/// Body for `POST /api/v1/replication/enqueue` — the site-local durable
/// enqueue of an AUTHORIZED state projection.
#[derive(Debug, Deserialize)]
pub struct EnqueueRequest {
    pub site_id: Option<Uuid>,
    pub entity_type: String,
    pub entity_id: Uuid,
    #[serde(default)]
    pub projection: serde_json::Value,
    pub source_event_id: Option<String>,
}

/// Query parameters for `GET /api/v1/replication/pull`.
#[derive(Debug, Deserialize)]
pub struct PullQuery {
    #[serde(default = "default_limit")]
    pub limit: i64,
}

fn default_limit() -> i64 {
    100
}

/// Response for the corporate pull: the claimed pending projections.
#[derive(Debug, serde::Serialize)]
pub struct PullResponse {
    pub entries: Vec<ReplicationEntry>,
}

/// `POST /api/v1/replication/enqueue` — site-local durable enqueue.
/// Never depends on the corporate link; the entry is durably queued in
/// the tenant's own transaction.
pub async fn enqueue(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<EnqueueRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("integration:status:read")?;
    let p = pool(&state)?;
    replication::enqueue_projection(
        p,
        user.tenant_id,
        req.site_id,
        &req.entity_type,
        req.entity_id,
        req.projection,
        req.source_event_id.as_deref(),
    )
    .await?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

/// `GET /api/v1/replication/pull?limit=100` — the corporate pull.
/// Returns the pending projections in order and marks them pulled in the
/// SAME transaction: a crash before processing leaves the projection
/// durably queued (durable once, no double projection).
pub async fn pull(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(query): Query<PullQuery>,
) -> Result<Json<PullResponse>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let entries = replication::pull_pending(p, user.tenant_id, query.limit).await?;
    Ok(Json(PullResponse { entries }))
}

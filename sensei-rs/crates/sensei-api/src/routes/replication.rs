//! Site-edge replication routes (fifteenth audit 29/A15 + sixteenth audit
//! items 15-17): sites enqueue versioned AUTHORIZED projections; corporate
//! claims a lease (claim -> apply -> ACK) so a crash after claim loses
//! only the lease, never the projection; data residency is enforced
//! deterministically BEFORE enqueue.

use axum::extract::{Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::replication::{self, ReplicationEntry, ReplicationEnvelope};

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Replication requires the database".to_string()))
        .map(|p| p.as_ref())
}

/// Body for `POST /api/v1/replication/enqueue` — the site-local durable
/// enqueue of an AUTHORIZED state projection plus its versioned envelope.
/// `source_country`/`destination_country` drive the deterministic
/// residency gate (item 17): when the destination differs from the source,
/// `restricted`/`personal` projections are rejected with 422.
#[derive(Debug, Deserialize)]
pub struct EnqueueRequest {
    pub site_id: Option<Uuid>,
    pub entity_type: String,
    pub entity_id: Uuid,
    /// The projection payload (`projection` is accepted as an alias).
    #[serde(default, alias = "projection")]
    pub payload: serde_json::Value,
    pub source_event_id: Option<String>,
    /// Envelope: versioned, typed projections (item 15).
    #[serde(default = "default_schema_version")]
    pub schema_version: u32,
    pub source_site: Option<Uuid>,
    #[serde(default)]
    pub projection_type: Option<String>,
    #[serde(default = "default_projection_revision")]
    pub projection_revision: u64,
    /// Residency gate inputs (item 17). The data policy itself is DERIVED
    /// server-side from the site manifest + country policy bundle — the
    /// client never declares its own classification.
    pub source_country: Option<String>,
    pub destination_country: Option<String>,
}

fn default_schema_version() -> u32 {
    1
}

fn default_projection_revision() -> u64 {
    1
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

/// Response for the corporate pull: the claimed pending projections, each
/// with its lease `claim_token` (ownership check for the later ACK).
#[derive(Debug, serde::Serialize)]
pub struct PullResponse {
    pub entries: Vec<ReplicationEntry>,
}

/// Body for `POST /api/v1/replication/ack`.
#[derive(Debug, Deserialize)]
pub struct AckRequest {
    pub id: Uuid,
    pub claim_token: Uuid,
}

/// Body for `POST /api/v1/replication/fail`.
#[derive(Debug, Deserialize)]
pub struct FailRequest {
    pub id: Uuid,
    pub claim_token: Uuid,
    #[serde(default)]
    pub error: String,
    #[serde(default = "default_retry_seconds")]
    pub retry_in_seconds: i64,
}

fn default_retry_seconds() -> i64 {
    60
}

/// `POST /api/v1/replication/enqueue` — site-local durable enqueue.
/// Never depends on the corporate link; the entry is durably queued in
/// the tenant's own transaction. The residency gate is applied BEFORE
/// enqueue: a `restricted`/`personal` projection whose destination
/// country differs from the source is blocked (422).
pub async fn enqueue(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<EnqueueRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("federation:replication:publish")?;
    let p = pool(&state)?;
    // SERVER-DERIVED POLICY (sixteenth audit item 29): the classification
    // comes from the site manifest's country and the tenant's country
    // policy bundle — the client's word is never trusted.
    let data_policy = replication::derive_data_policy(p, user.tenant_id, req.site_id).await?;
    let policy = replication::DataPolicy::parse(&data_policy)
        .map_err(sensei_core::error::SenseiError::Validation)?;
    if !replication::may_replicate(
        policy,
        req.source_country.as_deref(),
        req.destination_country.as_deref(),
    ) {
        return Err(SenseiError::HttpError {
            status: 422,
            message: "data residency policy blocks this projection".to_string(),
        });
    }
    let projection_type = req
        .projection_type
        .clone()
        .unwrap_or_else(|| req.entity_type.clone());
    let envelope = ReplicationEnvelope {
        schema_version: req.schema_version,
        source_event_id: req.source_event_id.clone(),
        source_site: req.source_site,
        projection_type,
        projection_revision: req.projection_revision,
        data_policy,
        payload: req.payload.clone(),
    };
    replication::enqueue_projection(
        p,
        user.tenant_id,
        req.site_id,
        &req.entity_type,
        req.entity_id,
        req.payload,
        req.source_event_id.as_deref(),
        &envelope,
        req.source_country.as_deref(),
        req.destination_country.as_deref(),
    )
    .await?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

/// `GET /api/v1/replication/pull?limit=100` — the corporate claim.
/// Returns the pending projections in order and leases them in the SAME
/// transaction (`claim_token`, 5-minute lease): a crash before processing
/// loses only the lease, never the projection (at-least-once, no double
/// projection); concurrent claims skip locked rows.
pub async fn pull(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(query): Query<PullQuery>,
) -> Result<Json<PullResponse>> {
    user.require_permission("federation:replication:consume")?;
    let p = pool(&state)?;
    let entries = replication::claim_batch(p, user.tenant_id, query.limit).await?;
    Ok(Json(PullResponse { entries }))
}

/// `POST /api/v1/replication/ack` — corporate ACK after applying the
/// projection. The `claim_token` is the ownership check: a stale worker's
/// ACK is rejected.
pub async fn ack(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<AckRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("federation:replication:consume")?;
    let p = pool(&state)?;
    replication::ack(p, user.tenant_id, req.id, req.claim_token).await?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

/// `POST /api/v1/replication/fail` — corporate fail after an apply error;
/// the row becomes claimable again once `retry_in_seconds` has passed.
pub async fn fail(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<FailRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("federation:replication:consume")?;
    let p = pool(&state)?;
    replication::fail(
        p,
        user.tenant_id,
        req.id,
        req.claim_token,
        &req.error,
        req.retry_in_seconds,
    )
    .await?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

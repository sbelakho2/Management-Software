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
/// Eighteenth audit P0-3: the client describes NO security properties of
/// the data it wants to export. It names the SOURCE EVENT (a canonical
/// operational event); the server derives the site, jurisdiction, data
/// class and policy revision into an [`AuthorizedProjection`], and the
/// artifact is what gets enqueued.
#[derive(Debug, Deserialize)]
pub struct EnqueueRequest {
    pub source_event_id: Uuid,
    pub entity_type: String,
    pub entity_id: Uuid,
    /// The projection payload (`projection` is accepted as an alias).
    #[serde(default, alias = "projection")]
    pub payload: serde_json::Value,
    /// Envelope: versioned, typed projections (item 15).
    #[serde(default = "default_schema_version")]
    pub schema_version: u32,
    #[serde(default)]
    pub projection_type: Option<String>,
    #[serde(default = "default_projection_revision")]
    pub projection_revision: u64,
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
    // Eighteenth audit P0-3: EVERYTHING is derived server-side from the
    // source event. The endpoint never asks the caller to describe the
    // security properties of the data it wants to export — a malicious
    // publisher cannot influence the residency decision by supplying
    // matching countries, omitting the destination, or omitting the site
    // (site omission is now an ERROR, never a silent "internal").
    let artifact =
        replication::authorize_projection(p, user.tenant_id, req.source_event_id, &req.entity_type)
            .await?;
    let policy = replication::DataPolicy::parse(&artifact.data_class)
        .map_err(sensei_core::error::SenseiError::Validation)?;
    // Nineteenth audit P0: the destination is DERIVED from the tenant's
    // federation memberships (the corporate group), never supplied by
    // the caller and never silently None. Restricted/Personal with no
    // derivable destination is DENIED by may_replicate.
    let target_jurisdiction: Option<replication::Jurisdiction> = {
        let country: Option<String> = sqlx::query_scalar(
            "SELECT sm.country FROM federation_memberships fm \
             JOIN site_manifests sm ON sm.tenant_id = fm.peer_tenant_id \
             WHERE fm.tenant_id = $1 LIMIT 1",
        )
        .bind(user.tenant_id)
        .fetch_optional(p)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!(
                "replication: federation target lookup failed: {e}"
            ))
        })?;
        match country {
            Some(country) => {
                let residency: Option<String> = sqlx::query_scalar(
                    "SELECT data_residency FROM country_policies \
                     WHERE tenant_id = $1 AND country = $2",
                )
                .bind(user.tenant_id)
                .bind(&country)
                .fetch_optional(p)
                .await
                .map_err(|e| {
                    sensei_core::error::SenseiError::Database(format!(
                        "replication: target policy lookup failed: {e}"
                    ))
                })?;
                match residency {
                    Some(residency) => replication::Jurisdiction::parse(&residency).ok(),
                    None => None,
                }
            }
            None => None,
        }
    };
    if !replication::may_replicate(
        policy,
        Some(&artifact.source_jurisdiction),
        target_jurisdiction.as_ref(),
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
        source_event_id: Some(artifact.source_event_id.to_string()),
        source_site: artifact.source_site,
        projection_type,
        projection_revision: req.projection_revision,
        data_policy: artifact.data_class.clone(),
        payload: req.payload.clone(),
    };
    replication::enqueue_projection(
        p,
        user.tenant_id,
        artifact.source_site,
        &req.entity_type,
        req.entity_id,
        req.payload,
        Some(&artifact.source_event_id.to_string()),
        &envelope,
        Some(&artifact.source_jurisdiction),
        target_jurisdiction.as_ref(),
    )
    .await?;
    Ok(Json(serde_json::json!({
        "ok": true,
        "authorized_projection": artifact,
    })))
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

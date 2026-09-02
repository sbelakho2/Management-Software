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
/// artifact is what gets enqueued. Twenty-second audit P0/P1-5: the
/// request carries ONLY the source event — NO client projection identity
/// anymore. Entity identity (the event's subject object), projection
/// type (the event's own type), schema version (1) and projection
/// revision (1) all derive SERVER-SIDE from the source event inside the
/// authorization step, so nothing a client sends can shift the
/// idempotency key the queue row is deduplicated on.
#[derive(Debug, Deserialize)]
pub struct EnqueueRequest {
    pub source_event_id: Uuid,
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
/// Never depends on the corporate link; the WHOLE fanout is durably
/// queued in ONE tenant-scoped transaction. Twentieth audit P0: the
/// destination is NO LONGER a single `LIMIT 1` guess over the federation
/// peers — the route loads EVERY FederationEdge the caller's tenant holds
/// (membership row + peer site manifest + peer country policy, all
/// server-derived) and enqueues ONE ROW PER EDGE that permits the
/// projection, evaluating `may_replicate` with THAT EDGE's own residency
/// policy and `allowed_data_classes`; twenty-second audit P0/P1-4: each
/// edge names the exact peer site, so every row records its own
/// target_site_id. Twenty-third audit P1 (fanout idempotency): every
/// validation happens BEFORE anything is written — the route authorizes
/// the event, derives the EXACT subject identity, and loads the edges,
/// and ONLY THEN calls the fanout function once; inside it every edge is
/// screened first and the inserts run
/// `ON CONFLICT (tenant_id, source_event_id, target_tenant_id,
/// target_site_id) DO NOTHING`, so repeated publishes of the same command
/// converge to the same complete set instead of 500-ing on the first
/// duplicate, and a mid-way failure rolls back atomically (no partial
/// success). The response carries the fanout report — `replication::FanoutReport`:
/// `enqueued_edges`
/// (newly enqueued), `already_present` (idempotent duplicates) and
/// `blocked` (edges the residency/class gate denied). A
/// Restricted/Personal projection that NO edge permits is a 422
/// (fail-closed — it is never silently dropped). Twenty-second audit
/// P0/P1-5: the request carries ONLY `source_event_id` — entity identity
/// (subject object), projection type (event type), schema version (1) and
/// projection revision (1) are all derived server-side from that one id.
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
    // Twenty-second audit P0/P1-5: the projection schema label is passed
    // EMPTY — authorize_projection derives it from the event's own type,
    // so the client cannot relabel the projection.
    let artifact =
        replication::authorize_projection(p, user.tenant_id, req.source_event_id, "").await?;
    let policy = replication::DataPolicy::parse(&artifact.data_class)
        .map_err(sensei_core::error::SenseiError::Validation)?;

    // Twenty-second audit P0/P1-5: the entity identity derives from the
    // source event's subject object — and ONLY from it. The request no
    // longer carries a client entity_type/entity_id fallback.
    // Twenty-third audit P1 (subject-count strictness): derivation is
    // EXACT — an event with NO subject object is a Validation error, and
    // an event projecting MULTIPLE subjects is a Validation error too
    // (multiple subjects require explicit projector semantics, none are
    // defined yet); exactly one subject yields the identity. Both errors
    // surface BEFORE anything is enqueued.
    let (entity_type, entity_id) =
        replication::derive_projection_identity(p, user.tenant_id, req.source_event_id).await?;

    // Twentieth audit P0: EVERY edge of the caller's federation graph is
    // loaded (NO LIMIT 1 — one edge per membership row's peer site, so
    // the gate below never checks an arbitrary country). This read and
    // every derivation above complete BEFORE the fanout starts — nothing
    // is written on a validation error.
    let edges = replication::load_federation_edges(p, user.tenant_id, artifact.source_site).await?;
    // Twenty-second audit P0/P1-5: the projection type is the source
    // EVENT's own type (server-derived inside authorize_projection — the
    // artifact schema label IS the event type when no client value is
    // accepted), and schema/projection revisions are server constants:
    // the client can never shift the idempotency key.
    let envelope = ReplicationEnvelope {
        schema_version: 1,
        source_event_id: Some(artifact.source_event_id.to_string()),
        source_site: artifact.source_site,
        projection_type: artifact.projection_schema.clone(),
        projection_revision: 1,
        data_policy: artifact.data_class.clone(),
        payload: artifact.projected_payload.clone(),
    };
    // Twenty-third audit P1: ONE fanout call, ONE transaction over ALL
    // edges. Per-edge gate denials come back as `blocked`; duplicates of
    // an already-published row come back as `already_present` (DO NOTHING
    // — idempotent convergence); a mid-way failure rolls back atomically.
    let report = replication::enqueue_projection_fanout(
        p,
        user.tenant_id,
        artifact.source_site,
        &entity_type,
        entity_id,
        artifact.projected_payload.clone(),
        &artifact.source_event_id.to_string(),
        &envelope,
        &artifact.source_jurisdiction,
        &edges,
    )
    .await?;
    // Restricted/Personal must never be silently dropped: with NO row
    // enqueued AND none already present (a fresh publish every edge
    // refused/blocked) the request is refused outright. An idempotent
    // retry of a publish that previously SUCCEEDED reports
    // already_present > 0 and stays a 200 — the duplicate never 500s.
    if report.newly_enqueued == 0
        && report.already_present == 0
        && matches!(
            policy,
            replication::DataPolicy::Restricted | replication::DataPolicy::Personal
        )
    {
        return Err(SenseiError::HttpError {
            status: 422,
            message: "no federation edge permits this restricted/personal projection — \
                      nothing was enqueued"
                .to_string(),
        });
    }
    Ok(Json(serde_json::json!({
        "ok": true,
        "enqueued_edges": report.newly_enqueued,
        "already_present": report.already_present,
        "blocked_edges": report.blocked,
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

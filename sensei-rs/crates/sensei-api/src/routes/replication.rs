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
/// Never depends on the corporate link; each entry is durably queued in
/// the tenant's own transaction. Twentieth audit P0: the destination is
/// NO LONGER a single `LIMIT 1` guess over the federation peers — the
/// route loads EVERY FederationEdge the caller's tenant holds (membership
/// row + peer site manifest + peer country policy, all server-derived)
/// and enqueues ONE ROW PER EDGE that permits the projection, evaluating
/// `may_replicate` with THAT EDGE's own residency policy and
/// `allowed_data_classes`; twenty-second audit P0/P1-4: each edge names
/// the exact peer site, so every row records its own target_site_id. The
/// response returns the number of edges enqueued; a Restricted/Personal
/// projection that no edge permits is a 422 (fail-closed — it is never
/// silently dropped). Twenty-second audit P0/P1-5: the request carries
/// ONLY `source_event_id` — entity identity (subject object), projection
/// type (event type), schema version (1) and projection revision (1) are
/// all derived server-side from that one id.
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
    // longer carries a client entity_type/entity_id fallback, so an event
    // without a subject object is refused: nothing client-supplied may
    // stand in for the identity the queue row is keyed on.
    let (entity_type, entity_id) =
        replication::derive_projection_identity(p, user.tenant_id, req.source_event_id)
            .await?
            .ok_or_else(|| {
                SenseiError::Validation(
                    "replication: the source event carries no subject object — the projection \
             identity cannot be derived, so it cannot be enqueued"
                        .to_string(),
                )
            })?;

    // Twentieth audit P0: EVERY edge of the caller's federation graph is
    // loaded (NO LIMIT 1 — one edge per membership row's peer site, so
    // the gate below never checks an arbitrary country), and the gate is
    // evaluated once PER EDGE with the edge's OWN residency policy.
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
    let mut enqueued_edges: u64 = 0;
    for edge in &edges {
        if !edge.allowed_data_classes.contains(&policy) {
            continue;
        }
        if !replication::may_replicate(
            policy,
            Some(&artifact.source_jurisdiction),
            Some(&edge.target_jurisdiction),
            &edge.residency_policy,
        ) {
            continue;
        }
        replication::enqueue_projection(
            p,
            user.tenant_id,
            artifact.source_site,
            &entity_type,
            entity_id,
            artifact.projected_payload.clone(),
            Some(&artifact.source_event_id.to_string()),
            &envelope,
            Some(&artifact.source_jurisdiction),
            edge,
        )
        .await?;
        enqueued_edges += 1;
    }
    // Restricted/Personal must never be silently dropped: with NO edge
    // permitting the projection the request is refused outright.
    if enqueued_edges == 0
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
        "enqueued_edges": enqueued_edges,
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

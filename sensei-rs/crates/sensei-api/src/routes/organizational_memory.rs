//! Organizational memory routes (fifteenth audit items 42-47 + A8/A18).
//!
//! Memory lives at personal / role / process / site / corporate tiers.
//! Promotion is DETERMINISTIC or reviewed — the AI proposes, it never
//! unilaterally promotes:
//!
//! - `observe` records an operator comment; the SAME context signature
//!   reinforces one memory (observation -> repeated at >= 2 occurrences,
//!   deterministic, no model in the loop),
//! - `propose` is a reviewed act that marks an observed/repeated/verified
//!   memory as `proposed`,
//! - `approve` is the final human gate: only a PROPOSED memory can become
//!   `approved`.
//!
//! Role-tier memory is anchored to the role slot and process-tier memory
//! to the process — an employee departure never deletes it.

use axum::extract::{Path, Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::organizational_memory::{
    self, approve_memory, list_memory, propose_memory, MemoryRecord,
};

// ── Request / response DTOs ─────────────────────────────────────────────────

/// Body for `POST /api/v1/memory/observe` — an operator comment becomes an
/// observation. `context_signature` is the identity of the memory: the same
/// signature + kind + tier reinforces ONE memory.
#[derive(Debug, Deserialize)]
pub struct ObserveRequest {
    pub tier: String,
    pub slot_id: Option<Uuid>,
    pub process: Option<String>,
    pub kind: String,
    pub content: String,
    #[serde(default)]
    pub context_signature: serde_json::Value,
}

/// Query parameters for `GET /api/v1/memory`.
#[derive(Debug, Deserialize)]
pub struct ListMemoryParams {
    pub tier: Option<String>,
    pub status: Option<String>,
}

// ── Helpers ─────────────────────────────────────────────────────────────────

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| {
            SenseiError::Database("Organizational memory requires the database".to_string())
        })
        .map(|p| p.as_ref())
}

// ── Deterministic kernel entry points (also used by the DB-contract gate) ──

/// Record (or reinforce) an observation through the deterministic kernel
/// and return the affected memory row.
pub async fn run_observe(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    req: ObserveRequest,
    created_by: Option<Uuid>,
) -> Result<MemoryRecord> {
    organizational_memory::record_observation(
        pool,
        tenant_id,
        &req.tier,
        req.slot_id,
        req.process.as_deref(),
        &req.kind,
        &req.content,
        req.context_signature.clone(),
        created_by,
    )
    .await?;
    organizational_memory::find_memory_by_signature(
        pool,
        tenant_id,
        &req.tier,
        req.slot_id,
        req.process.as_deref(),
        &req.kind,
        &req.context_signature,
    )
    .await
}

/// Propose a memory for approval (reviewed act).
pub async fn run_propose(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid) -> Result<MemoryRecord> {
    propose_memory(pool, tenant_id, id).await
}

/// Approve a proposed memory (final reviewed gate).
pub async fn run_approve(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid) -> Result<MemoryRecord> {
    approve_memory(pool, tenant_id, id).await
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `POST /api/v1/memory/observe` — record an operator comment as an
/// observation. The same context signature + kind + tier reinforces the
/// SAME memory; a second occurrence deterministically promotes it to
/// `repeated` (occurrence_count >= 2). The model never promotes beyond
/// that — propose/approve are separate reviewed acts.
pub async fn observe(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ObserveRequest>,
) -> Result<Json<MemoryRecord>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    Ok(Json(
        run_observe(p, user.tenant_id, req, Some(user.user_id)).await?,
    ))
}

/// `POST /api/v1/memory/{id}/propose` — a reviewed act: mark an
/// observation / repeated / verified memory as `proposed`. This is as far
/// as a model can take a memory.
pub async fn propose(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<MemoryRecord>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    Ok(Json(run_propose(p, user.tenant_id, id).await?))
}

/// `POST /api/v1/memory/{id}/approve` — the final gate: only a PROPOSED
/// memory can be approved. The AI can only have proposed, never approved.
pub async fn approve(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<MemoryRecord>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    Ok(Json(run_approve(p, user.tenant_id, id).await?))
}

/// `GET /api/v1/memory?tier=role&status=approved` — list memory rows,
/// optionally filtered by tier and status.
pub async fn list(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListMemoryParams>,
) -> Result<Json<Vec<MemoryRecord>>> {
    user.require_permission("training:manage")?;
    let p = pool(&state)?;
    let rows = list_memory(
        p,
        user.tenant_id,
        params.tier.as_deref(),
        params.status.as_deref(),
    )
    .await?;
    Ok(Json(rows))
}

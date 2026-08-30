//! A3 Report route handlers.
//!
//! Provides endpoints for creating, reviewing, updating, and closing
//! A3 problem-solving reports following the structured A3 methodology.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::A3;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing A3 reports.
#[derive(Debug, Deserialize)]
pub struct ListA3sParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all A3 reports with optional status filter and pagination.
pub async fn list_a3s(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListA3sParams>,
) -> Result<Json<PaginatedResponse<A3>>> {
    user.require_permission("tps:a3:read")?;
    let tenant_id = user.tenant_id;
    let a3s = state
        .ops_service
        .list_a3s(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(a3s))
}

/// Create a new A3 report.
pub async fn create_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<A3>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:create")?;
    let tenant_id = user.tenant_id;
    // The A3-created event is enqueued TRANSACTIONALLY inside the
    // service (thirteenth audit) — the route no longer best-effort
    // publishes, which would double-deliver with the outbox worker.
    let a3 = state.ops_service.create_a3(tenant_id, req).await?;
    Ok(Json(a3))
}

/// Get a specific A3 report by ID.
pub async fn get_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:read")?;
    let tenant_id = user.tenant_id;
    let a3 = state.ops_service.get_a3(tenant_id, id).await?;
    Ok(Json(a3))
}

/// Update an existing A3 report.
/// Client input for editing an A3: only the editable text fields. The
/// actor, identity and status are server-owned; `expected_version` is the
/// optimistic-concurrency token (mismatch -> 409).
#[derive(Debug, Clone, serde::Deserialize)]
pub struct UpdateA3Request {
    pub background: Option<String>,
    pub current_state: Option<String>,
    pub goal: Option<String>,
    pub root_cause_analysis: Option<String>,
    pub countermeasures: Option<String>,
    pub check_plan: Option<String>,
    pub follow_up: Option<String>,
    #[serde(default)]
    pub expected_version: Option<u64>,
    /// Structured evidence model (observed conditions, baselines, evidence
    /// refs, hypotheses, experiments, verifications, standardizations,
    /// learnings).
    #[serde(default)]
    pub observed_conditions: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub metric_baselines: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub evidence_refs: Option<Vec<String>>,
    #[serde(default)]
    pub cause_hypotheses: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub experiments: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub verifications: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub standardizations: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub learnings: Option<Vec<serde_json::Value>>,
}

pub async fn update_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateA3Request>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:edit")?;
    let tenant_id = user.tenant_id;
    let current = state.ops_service.get_a3(tenant_id, id).await?;
    // Optimistic concurrency: reject stale edits instead of overwriting.
    if let Some(expected) = req.expected_version {
        if current.version != expected {
            return Err(SenseiError::Conflict(format!(
                "VERSION_CONFLICT: A3 is at version {}, expected {expected}",
                current.version
            )));
        }
    }
    let mut updated = current;
    if let Some(v) = req.background {
        updated.background = v;
    }
    if let Some(v) = req.current_state {
        updated.current_state = v;
    }
    if let Some(v) = req.goal {
        updated.goal = v;
    }
    if let Some(v) = req.root_cause_analysis {
        updated.root_cause_analysis = v;
    }
    if let Some(v) = req.countermeasures {
        updated.countermeasures = v;
    }
    if let Some(v) = req.check_plan {
        updated.check_plan = v;
    }
    if let Some(v) = req.follow_up {
        updated.follow_up = v;
    }
    // The structured evidence model is writable through the API.
    if let Some(v) = req.observed_conditions {
        updated.observed_conditions = v;
    }
    if let Some(v) = req.metric_baselines {
        updated.metric_baselines = v;
    }
    if let Some(v) = req.evidence_refs {
        updated.evidence_refs = v;
    }
    if let Some(v) = req.cause_hypotheses {
        updated.cause_hypotheses = v;
    }
    if let Some(v) = req.experiments {
        updated.experiments = v;
    }
    if let Some(v) = req.verifications {
        updated.verifications = v;
    }
    if let Some(v) = req.standardizations {
        updated.standardizations = v;
    }
    if let Some(v) = req.learnings {
        updated.learnings = v;
    }
    // The DB owns the version increment (atomic CAS); `updated.version` is
    // the EXPECTED version the SQL compares against.
    let a3 = state.ops_service.update_a3(tenant_id, id, updated).await?;
    Ok(Json(a3))
}

/// Close an A3 report (mark as completed/closed).
pub async fn close_a3(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<A3>> {
    user.require_permission("tps:a3:close")?;
    let tenant_id = user.tenant_id;
    // The A3-close event is enqueued TRANSACTIONALLY inside the service —
    // the route no longer best-effort publishes (double delivery).
    let a3 = state.ops_service.close_a3(tenant_id, id).await?;
    Ok(Json(a3))
}

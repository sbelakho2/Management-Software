//! Process mining routes (fifteenth audit items 34/35/99): conformance
//! checking and hidden-loop detection over the operational_events log.
//!
//! Forge learns the EXPECTED path (the canonical standard) and the ACTUAL
//! path (what the event log shows the operation really did). Recurrence
//! loops — a condition that closes and reopens — are detected FROM
//! HISTORY; the API never announces "you are now practicing TPS". It
//! reports the observed path, the deviations, and the loops.

use axum::extract::{Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;

use crate::state::AppState;

use sensei_services::tps::process_mining::{self, ConformanceReport, PathStep};

/// Query parameters for the process-mining endpoints.
#[derive(Debug, Deserialize)]
pub struct ProcessMiningParams {
    pub object_type: String,
    #[serde(default = "default_window_days")]
    pub window_days: i64,
}

fn default_window_days() -> i64 {
    30
}

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Process mining requires the database".to_string()))
        .map(|p| p.as_ref())
}

/// `GET /api/v1/process-mining/conformance?object_type=andon&window_days=30`
/// — the conformance report: expected canonical path vs the actual
/// transitions from the event log, deviations, and hidden loops.
pub async fn conformance(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ProcessMiningParams>,
) -> Result<Json<ConformanceReport>> {
    user.require_permission("tps:read")?;
    if process_mining::expected_path(&params.object_type).is_empty() {
        return Err(SenseiError::Validation(format!(
            "object_type must be one of andon|ncr|a3 (got '{}')",
            params.object_type
        )));
    }
    let p = pool(&state)?;
    let report = process_mining::conformance_report(
        p,
        user.tenant_id,
        &params.object_type,
        params.window_days,
    )
    .await?;
    Ok(Json(report))
}

/// `GET /api/v1/process-mining/path?object_type=ncr&window_days=30` — the
/// ACTUAL path the operation walked: event types seen in the window with
/// their counts, ordered by first occurrence.
pub async fn path(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ProcessMiningParams>,
) -> Result<Json<Vec<PathStep>>> {
    user.require_permission("tps:read")?;
    if process_mining::expected_path(&params.object_type).is_empty() {
        return Err(SenseiError::Validation(format!(
            "object_type must be one of andon|ncr|a3 (got '{}')",
            params.object_type
        )));
    }
    let p = pool(&state)?;
    let steps = process_mining::discover_actual_path(
        p,
        user.tenant_id,
        &params.object_type,
        params.window_days,
    )
    .await?;
    Ok(Json(steps))
}

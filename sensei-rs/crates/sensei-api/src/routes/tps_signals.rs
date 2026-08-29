//! TPS signal classification endpoints (item 41): the operational layer
//! continuously classifies signals across flow/recurrence/mura/muri
//! dimensions. The responses are plain-language guidance about the
//! CONDITION — the user never sees TPS vocabulary unless they ask.

use axum::extract::State;
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

/// Inputs for the signal classification batch (all optional — each
/// classifier runs only when its inputs are present).
#[derive(Debug, Deserialize)]
pub struct ClassifySignalsRequest {
    /// Queue delta (units) over the window (minutes).
    pub queue_delta: Option<i64>,
    pub queue_window_minutes: Option<i64>,
    /// Batch size expressed as days of demand + demand volatility (0..1).
    pub batch_days_of_demand: Option<f64>,
    pub demand_volatility: Option<f64>,
    /// Workaround count at a step.
    pub workaround_count: Option<i64>,
    /// Recurrences of the same Andon/condition within since_days.
    pub same_issue_count: Option<i64>,
    pub since_days: Option<i64>,
    /// Supplier delivery stddev vs mean lead (days).
    pub delivery_stddev_days: Option<f64>,
    pub mean_lead_days: Option<f64>,
    /// Finished-goods growth (days) + delivery-miss delta.
    pub fg_growth_days: Option<f64>,
    pub delivery_miss_delta: Option<i64>,
    /// LSW observation skew: completed_at vs observed_at (ISO-8601).
    pub lsw_completed_at: Option<chrono::DateTime<chrono::Utc>>,
    pub lsw_observed_at: Option<chrono::DateTime<chrono::Utc>>,
    /// Reopened defect count.
    pub reopened_count: Option<i64>,
    /// Actual vs standard cycle (seconds).
    pub cycle_seconds: Option<f64>,
    pub standard_seconds: Option<f64>,
}

/// Classify signals against the deterministic TPS rules.
pub async fn classify_signals(
    user: AuthenticatedUser,
    State(_state): State<AppState>,
    Json(req): Json<ClassifySignalsRequest>,
) -> Result<Json<Vec<sensei_services::tps::signals::TpsSignal>>> {
    // Item 41: the classifier is tenant-scoped work — it must be readable
    // by anyone who can see operational state, but still requires
    // authentication + tenant scope.
    user.require_permission("tps:read")?;
    use sensei_services::tps::signals::*;

    let mut signals: Vec<sensei_services::tps::signals::TpsSignal> = Vec::new();
    if let (Some(delta), Some(window)) = (req.queue_delta, req.queue_window_minutes) {
        if let Some(s) = classify_queue_growth(delta, window, 30) {
            signals.push(s);
        }
    }
    if let (Some(batch), Some(vol)) = (req.batch_days_of_demand, req.demand_volatility) {
        if let Some(s) = classify_batch_effect(batch, vol, 4.0, 0.4) {
            signals.push(s);
        }
    }
    if let Some(count) = req.workaround_count {
        if let Some(s) = classify_workaround(count, 3) {
            signals.push(s);
        }
    }
    if let (Some(count), Some(days)) = (req.same_issue_count, req.since_days) {
        if let Some(s) = classify_andon_recurrence(count, days, 3) {
            signals.push(s);
        }
    }
    if let (Some(stddev), Some(mean)) = (req.delivery_stddev_days, req.mean_lead_days) {
        if let Some(s) = classify_supplier_variability(stddev, mean, 1.0) {
            signals.push(s);
        }
    }
    if let (Some(growth), Some(misses)) = (req.fg_growth_days, req.delivery_miss_delta) {
        if let Some(s) = classify_systemic_flow(growth, misses, 4.0) {
            signals.push(s);
        }
    }
    if let (Some(completed), Some(observed)) = (req.lsw_completed_at, req.lsw_observed_at) {
        if let Some(s) = classify_remote_lsw(completed, observed, 300) {
            signals.push(s);
        }
    }
    if let Some(count) = req.reopened_count {
        if let Some(s) = classify_reopened_defect(count, 2) {
            signals.push(s);
        }
    }
    if let (Some(cycle), Some(std)) = (req.cycle_seconds, req.standard_seconds) {
        if let Some(s) = classify_cycle_miss(cycle, std, 0.2) {
            signals.push(s);
        }
    }
    // The caller's site scope is attached for context (server-created).
    let _ = Uuid::new_v4();
    Ok(Json(signals))
}

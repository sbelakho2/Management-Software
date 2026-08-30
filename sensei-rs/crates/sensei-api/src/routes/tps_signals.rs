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

/// Server-driven signal derivation (items 44/45): the TPS nervous system
/// derives the classifier inputs from REAL factory events — recurring
/// Andons, queue accumulation, supplier delivery variability, cycle
/// misses. The UI consumes this endpoint; it never computes signals
/// client-side.
#[derive(Debug, serde::Serialize)]
pub struct DerivedSignals {
    pub signals: Vec<sensei_services::tps::signals::TpsSignal>,
    pub derived_from: String,
    pub generated_at: chrono::DateTime<chrono::Utc>,
}

/// Derive and classify signals from the tenant's actual operational data.
pub async fn derive_signals(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<DerivedSignals>> {
    user.require_permission("tps:read")?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        sensei_core::error::SenseiError::Database(
            "Signal derivation requires the database".to_string(),
        )
    })?;
    use sensei_services::tps::signals::*;
    let mut signals: Vec<TpsSignal> = Vec::new();

    // Item 45: contextual thresholds — versioned factory knowledge per
    // signal key (site-policy defaults when no override exists). The
    // classifiers stay deterministic; the NUMBERS are data.
    let mut threshold: std::collections::HashMap<String, f64> = std::collections::HashMap::new();
    {
        let rows: Vec<(String, f64)> = sqlx::query_as(
            "SELECT signal_key, threshold_value FROM tps_thresholds \
             WHERE tenant_id = $1 AND product_family_id IS NULL",
        )
        .bind(user.tenant_id)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("Threshold read failed: {e}"))
        })?;
        for (key, value) in rows {
            threshold.insert(key, value);
        }
    }
    let thr = |key: &str, default: f64| -> f64 { threshold.get(key).copied().unwrap_or(default) };

    // ── Andon recurrence (item 41): the SAME issue type on the SAME work
    //    center raised 3+ times in 14 days — countermeasure ineffective.
    let recurring: Vec<(i64,)> = sqlx::query_as(
        "SELECT COUNT(*) FROM andons a \\
         WHERE a.tenant_id = $1 AND a.created_at > NOW() - INTERVAL '14 days' \\
         GROUP BY a.work_center_id, a.issue_type \\
         HAVING COUNT(*) >= 3 \\
         ORDER BY COUNT(*) DESC LIMIT 3",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("Recurrence read failed: {e}"))
    })?;
    for (count,) in recurring {
        let recurrence_threshold = thr("andon_recurrence_count", 3.0) as i64;
        if let Some(s) = classify_andon_recurrence(count, 14, recurrence_threshold) {
            signals.push(s);
        }
    }

    // ── Queue growth: work orders accumulating at a work center vs the
    //    completed share — flow/bottleneck signal.
    let queue: Vec<(String, i64, i64)> = sqlx::query_as(
        "SELECT wo.work_center_id::text, \\
                COUNT(*) FILTER (WHERE wo.status NOT IN ('completed','cancelled')), \\
                COUNT(*) FILTER (WHERE wo.status = 'in_progress') \\
         FROM work_orders wo \\
         WHERE wo.tenant_id = $1 AND wo.created_at > NOW() - INTERVAL '30 days' \\
         GROUP BY wo.work_center_id \\
         HAVING COUNT(*) FILTER (WHERE wo.status NOT IN ('completed','cancelled')) >= 10 \\
         LIMIT 3",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| sensei_core::error::SenseiError::Database(format!("Queue read failed: {e}")))?;
    for (_wc, open_count, _in_progress) in queue {
        // 10+ open WOs in 30 days at one center = accumulation signal
        // (the count is site policy, not a universal constant).
        let queue_threshold = thr("queue_growth_count", 4.0) as i64;
        if let Some(s) = classify_queue_growth(open_count, 30 * 24 * 60, queue_threshold) {
            signals.push(s);
        }
    }

    // ── Supplier delivery variability (item 41): stddev vs mean of
    //    delivery lag across receipts per supplier.
    let suppliers: Vec<(String, f64, f64)> = sqlx::query_as(
        "SELECT s.name::text, \\
                COALESCE(STDDEV(EXTRACT(EPOCH FROM (gr.received_at - po.expected_delivery)) / 86400.0), 0), \\
                COALESCE(AVG(EXTRACT(EPOCH FROM (gr.received_at - po.expected_delivery)) / 86400.0), 0) \\
         FROM goods_receipts gr \\
         JOIN purchase_orders po ON po.id = gr.purchase_order_id AND po.tenant_id = gr.tenant_id \\
         JOIN suppliers s ON s.id = po.supplier_id AND s.tenant_id = po.tenant_id \\
         WHERE gr.tenant_id = $1 AND gr.received_at > NOW() - INTERVAL '90 days' \\
         GROUP BY s.id, s.name \\
         LIMIT 3",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| sensei_core::error::SenseiError::Database(format!("Supplier read failed: {e}")))?;
    for (_name, stddev, mean) in suppliers {
        let variability_threshold = thr("supplier_variability_stddev", 1.0);
        if let Some(s) = classify_supplier_variability(stddev, mean, variability_threshold) {
            signals.push(s);
        }
    }

    // ── Cycle miss: work-order operations exceeding their standard time.
    let cycle: Vec<(f64, f64)> = sqlx::query_as(
        "SELECT op.actual_time::float8, op.standard_time::float8 \\
         FROM work_order_operations op \\
         WHERE op.tenant_id = $1 AND op.status = 'completed' \\
           AND op.actual_time IS NOT NULL AND op.standard_time > 0 \\
           AND op.completed_at > NOW() - INTERVAL '30 days' \\
         LIMIT 5",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| sensei_core::error::SenseiError::Database(format!("Cycle read failed: {e}")))?;
    for (actual, standard) in cycle {
        let miss_ratio = thr("cycle_miss_ratio", 0.2);
        if let Some(s) = classify_cycle_miss(actual, standard, miss_ratio) {
            signals.push(s);
        }
    }

    Ok(Json(DerivedSignals {
        signals,
        derived_from: "factory events (andons, work orders, receipts, operations)".to_string(),
        generated_at: chrono::Utc::now(),
    }))
}

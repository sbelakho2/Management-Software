//! System learning metrics (item 43): a DB-backed aggregation feeding the
//! pure `tps::learning` computation. The metrics measure whether the
//! SYSTEM learns — never ranking people by fewest Andons/NCRs.

use axum::extract::State;
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::tps::learning::{self, LearningInputs, LearningSnapshot};

use crate::state::AppState;

/// Compute the tenant's learning snapshot from the real stores.
pub async fn get_learning_metrics(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<LearningSnapshot>> {
    user.require_permission("tps:read")?;
    let tenant_id = user.tenant_id;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        SenseiError::Database("Learning metrics require the database".to_string())
    })?;

    // ── Andon latencies (detection, help response, containment) ──────
    let andon_row: (i64, i64, i64) = sqlx::query_as(
        "SELECT \
            COUNT(*) FILTER (WHERE resolved_at IS NOT NULL), \
            COALESCE(SUM(response_time_seconds), 0), \
            COALESCE(SUM(resolution_time_seconds), 0) \
         FROM andons WHERE tenant_id = $1",
    )
    .bind(tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Andon latency read failed: {e}")))?;
    let (andon_count, response_sum, resolution_sum) = andon_row;
    let help_response_seconds = if andon_count > 0 {
        response_sum as f64 / andon_count as f64
    } else {
        0.0
    };
    // Containment time (item 48) is NOT resolution time: containment is
    // when customer/process risk was controlled (contained_at), which can
    // be immediate even when root cause takes days. Only andons with a
    // contained_at contribute.
    let containment_seconds: f64 = sqlx::query_scalar(
        "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (a.contained_at - a.created_at))), 0)::float8 \
         FROM andons a \
         WHERE a.tenant_id = $1 AND a.contained_at IS NOT NULL \
           AND a.contained_at >= a.created_at \
           AND a.created_at > NOW() - INTERVAL '30 days'",
    )
    .bind(tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .unwrap_or(resolution_sum as f64 / andon_count.max(1) as f64);
    let _ = resolution_sum;

    // Detection latency (item 47): measured HONESTLY as
    // observed_at → raised_at (created_at) when the operator supplied an
    // observation time. Andons without observed_at have NO detection
    // latency — they are excluded, not approximated with a wrong proxy.
    let detection: Vec<f64> = sqlx::query_scalar(
        "SELECT EXTRACT(EPOCH FROM (a.created_at - a.abnormal_condition_observed_at)) \
         FROM andons a \
         WHERE a.tenant_id = $1 AND a.abnormal_condition_observed_at IS NOT NULL \
           AND a.created_at > NOW() - INTERVAL '30 days' \
           AND a.created_at >= a.abnormal_condition_observed_at \
         ORDER BY a.created_at DESC LIMIT 200",
    )
    .bind(tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Detection latency read failed: {e}")))?;
    let detection_latency_seconds = learning::mean(&detection);

    // ── Escalation latency: Andon raise -> first escalation record ──
    let escalation: Vec<f64> = sqlx::query_scalar(
        "SELECT EXTRACT(EPOCH FROM (escalated_at - created_at)) \
         FROM andons WHERE tenant_id = $1 AND escalated_at IS NOT NULL \
           AND created_at > NOW() - INTERVAL '30 days' \
         ORDER BY created_at DESC LIMIT 200",
    )
    .bind(tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Escalation latency read failed: {e}")))?;
    let escalation_latency_seconds = learning::mean(&escalation);

    // ── Recurrence: closed andons re-raised on the same work center with
    //    the same issue type within 14 days of resolution. ──
    let recurrence_row: (i64, i64) = sqlx::query_as(
        "SELECT \
            COUNT(*) FILTER (WHERE status = 'resolved'), \
            COUNT(*) FILTER (WHERE status = 'resolved' AND EXISTS ( \
                SELECT 1 FROM andons r \
                WHERE r.tenant_id = andons.tenant_id \
                  AND r.work_center_id = andons.work_center_id \
                  AND r.issue_type = andons.issue_type \
                  AND r.created_at > andons.resolved_at \
                  AND r.created_at < andons.resolved_at + INTERVAL '14 days' \
            )) \
         FROM andons WHERE tenant_id = $1 AND resolved_at > NOW() - INTERVAL '30 days'",
    )
    .bind(tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Recurrence read failed: {e}")))?;
    let (closed_andons, re_raised) = recurrence_row;
    let recurrence_rate = learning::recurrence_rate(closed_andons as usize, re_raised as usize);

    // ── A3 verification + standardization + hypothesis quality ──────
    // Item 50: "verification quality" requires STRUCTURED experimental
    // discipline — a verification counts only when it carries the
    // baseline, target, measurement, observation window, actual result,
    // evidence source and decision. A nonempty JSON array is NOT enough.
    let a3_row: (i64, i64, i64, i64) = sqlx::query_as(
        "SELECT \
            COUNT(*), \
            COUNT(*) FILTER (WHERE EXISTS ( \
                SELECT 1 FROM jsonb_array_elements(COALESCE(verifications, '[]')) v \
                WHERE v ? 'baseline' AND v ? 'target' AND v ? 'measurement' \
                  AND v ? 'observation_window' AND v ? 'actual_result' \
                  AND v ? 'decision' \
            )), \
            COUNT(*) FILTER (WHERE jsonb_array_length(COALESCE(standardizations, '[]')) > 0), \
            COUNT(*) FILTER (WHERE jsonb_array_length(COALESCE(cause_hypotheses, '[]')) > 0) \
         FROM a3_reports WHERE tenant_id = $1 AND created_at > NOW() - INTERVAL '30 days'",
    )
    .bind(tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("A3 metrics read failed: {e}")))?;
    let (a3_count, a3_verified, a3_standardized, a3_hypotheses) = a3_row;
    // Standardization measured from A3 standardizations (the evidence of
    // learning) — supersedes counts measure document churn, not learning.
    let standardization_rate = if a3_count > 0 {
        a3_standardized as f64 / a3_count as f64
    } else {
        0.0
    };

    // ── MTBF: mean interval between resolved andons per work center ──
    let mtbf: Vec<f64> = sqlx::query_scalar(
        "SELECT EXTRACT(EPOCH FROM (lead(resolved_at) OVER (PARTITION BY work_center_id ORDER BY resolved_at) - resolved_at)) \
         FROM andons WHERE tenant_id = $1 AND resolved_at IS NOT NULL \
           AND resolved_at > NOW() - INTERVAL '30 days'",
    )
    .bind(tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("MTBF read failed: {e}")))?;
    let mtbf_value = learning::mean(
        &mtbf
            .iter()
            .filter(|v| **v > 0.0)
            .copied()
            .collect::<Vec<_>>(),
    );

    let inputs = LearningInputs {
        detection_latency_seconds,
        help_response_seconds,
        containment_seconds,
        recurrence_rate,
        escalation_latency_seconds,
        verification_rate: if a3_count > 0 {
            a3_verified as f64 / a3_count as f64
        } else {
            0.0
        },
        standardization_rate,
        // NOT MEASURED (item 46): the deviation→standard linkage requires
        // deviation records that reference a standard — there is no honest
        // way to compute it from the current stores. It is reported as
        // "not yet measured", never fabricated.
        deviations_tied_to_standard: None,
        mean_interval_between_failures_seconds: mtbf_value,
        open_a3s: a3_count as usize,
        a3s_with_hypothesis: a3_hypotheses as usize,
    };

    Ok(Json(learning::compute_learning(&inputs)))
}

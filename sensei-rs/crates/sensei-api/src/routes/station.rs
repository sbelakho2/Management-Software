//! Operator station + team-lead interval control (items 31/32): the
//! backend aggregations that power the Jidoka-instinctive screens.
//!
//! Station: CURRENT JOB (part/order/required/done), RIGHT NOW pitch
//! target vs actual vs gap, CURRENT STEP with expected time, and the
//! plain-language help categories (the operator never sees Andon terms).
//!
//! Interval control: plan-vs-actual per pitch interval with the
//! abnormality timeline for a gap — "what stopped flow, when, how long,
//! who responded".

use axum::extract::{Query, State};
use axum::Json;
use chrono::{Timelike, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// One station line in the operator's CURRENT JOB block.
#[derive(Debug, Serialize)]
pub struct CurrentJob {
    pub work_order_id: Uuid,
    pub wo_number: String,
    pub product_name: String,
    pub required_qty: i64,
    pub completed_qty: i64,
    pub remaining_qty: i64,
}

/// The pitch block (RIGHT NOW).
#[derive(Debug, Serialize)]
pub struct PitchNow {
    pub target: i64,
    pub actual: i64,
    pub gap: i64,
    pub interval_start: chrono::DateTime<Utc>,
}

/// One step of the standard work.
#[derive(Debug, Serialize)]
pub struct StepNow {
    pub position: usize,
    pub total_steps: usize,
    pub description: String,
    pub expected_seconds: Option<i64>,
    pub is_critical: bool,
}

/// The operator station snapshot (item 31).
#[derive(Debug, Serialize)]
pub struct StationSnapshot {
    pub current_job: Option<CurrentJob>,
    pub pitch: Option<PitchNow>,
    pub current_step: Option<StepNow>,
    pub quality_check: Option<String>,
    pub work_center_name: String,
    pub help_categories: Vec<String>,
    pub generated_at: chrono::DateTime<Utc>,
}

/// Query: station for a work center (or the caller's active work center).
#[derive(Debug, Deserialize)]
pub struct StationParams {
    pub work_center_id: Option<Uuid>,
}

/// The operator's station snapshot — item 31: the screen shows CURRENT
/// JOB, RIGHT NOW pitch, CURRENT STEP, KEY POINT/QUALITY CHECK and the
/// plain-language help categories ("Quality", "Material", "Machine",
/// "Method / instructions", "Safety", "I cannot keep pace", "Something
/// else"). The operator never needs Andon terminology.
pub async fn get_station_snapshot(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<StationParams>,
) -> Result<Json<StationSnapshot>> {
    user.require_permission("tps:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Station requires the database".to_string()))?;

    // Resolve the work center: explicit, else the caller's assignment.
    let work_center_id = match params.work_center_id {
        Some(wc) => Some(wc),
        None => {
            let ctx = crate::routes::agent::build_context(&user, &state).await;
            ctx.work_center_id
        }
    };
    let work_center_name: String = match work_center_id {
        Some(wc) => {
            sqlx::query_scalar("SELECT name FROM work_centers WHERE id = $1 AND tenant_id = $2")
                .bind(wc)
                .bind(user.tenant_id)
                .fetch_one(pool.as_ref())
                .await
                .unwrap_or_else(|_| "UNKNOWN WORK CENTER".to_string())
        }
        None => "NO WORK CENTER ASSIGNED".to_string(),
    };

    // CURRENT JOB: the open work order at this work center.
    let current_job: Option<CurrentJob> = match work_center_id {
        Some(wc) => {
            let row: Option<(Uuid, String, String, i64, i64)> = sqlx::query_as(
                "SELECT wo.id, wo.wo_number, wo.product_name, wo.quantity, wo.quantity_completed \
                 FROM work_orders wo \
                 WHERE wo.tenant_id = $1 AND wo.work_center_id = $2 \
                   AND wo.status NOT IN ('completed', 'cancelled') \
                 ORDER BY wo.created_at DESC LIMIT 1",
            )
            .bind(user.tenant_id)
            .bind(wc)
            .fetch_optional(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Station job read failed: {e}")))?;
            row.map(|(id, num, name, qty, done)| CurrentJob {
                work_order_id: id,
                wo_number: num,
                product_name: name,
                required_qty: qty,
                completed_qty: done,
                remaining_qty: (qty - done).max(0),
            })
        }
        None => None,
    };

    // RIGHT NOW pitch: actual completed this hour vs the standard takt.
    let pitch: Option<PitchNow> = match (&current_job, work_center_id) {
        (Some(job), Some(wc)) => {
            let now = Utc::now();
            let interval_start = now
                .date_naive()
                .and_hms_opt(now.hour(), 0, 0)
                .map(|d| d.and_utc())
                .unwrap_or(now);
            let actual: i64 = sqlx::query_scalar(
                "SELECT COALESCE(SUM(quantity_completed), 0)::bigint \
                 FROM production_events \
                 WHERE tenant_id = $1 AND work_center_id = $2 \
                   AND occurred_at >= $3 AND event_type = 'produced'",
            )
            .bind(user.tenant_id)
            .bind(wc)
            .bind(interval_start)
            .fetch_one(pool.as_ref())
            .await
            .unwrap_or(0);
            // Pitch target: the takt-derived hourly plan for this job.
            let takt: Option<i64> = sqlx::query_scalar(
                "SELECT (3600.0 / NULLIF(takt_time_seconds, 0))::bigint \
                 FROM standard_work_documents \
                 WHERE tenant_id = $1 AND status IN ('effective', 'published') \
                 ORDER BY updated_at DESC LIMIT 1",
            )
            .bind(user.tenant_id)
            .fetch_one(pool.as_ref())
            .await
            .ok();
            let target = takt.unwrap_or(60);
            let _ = job.wo_number.clone();
            Some(PitchNow {
                target,
                actual,
                gap: actual - target,
                interval_start,
            })
        }
        _ => None,
    };

    // CURRENT STEP: the first unfinished step of the standard (item 31:
    // step 3/8 "Attach connector", expected time).
    let current_step: Option<StepNow> = sqlx::query_as(
        "SELECT jsonb_array_length(COALESCE(steps, '[]')), steps \
         FROM standard_work_documents \
         WHERE tenant_id = $1 AND status IN ('effective', 'published') \
         ORDER BY updated_at DESC LIMIT 1",
    )
    .bind(user.tenant_id)
    .fetch_optional(pool.as_ref())
    .await
    .ok()
    .flatten()
    .map(|(total, steps): (i64, serde_json::Value)| {
        let arr = steps.as_array().cloned().unwrap_or_default();
        let first = arr.first().cloned().unwrap_or_default();
        let desc = first
            .get("description")
            .and_then(|v| v.as_str())
            .map(|v| v.to_string())
            .unwrap_or_else(|| "Follow the standard".to_string());
        let expected = match first.get("standard_time") {
            Some(v) => v.as_i64(),
            None => None,
        };
        let critical = match first.get("is_critical") {
            Some(v) => v.as_bool().unwrap_or(false),
            None => false,
        };
        StepNow {
            position: 1,
            total_steps: total.max(0) as usize,
            description: desc,
            expected_seconds: expected,
            is_critical: critical,
        }
    });

    // KEY POINT / QUALITY CHECK: the CTQ bound to this work center.
    let quality_check: Option<String> = match work_center_id {
        Some(_wc) => sqlx::query_scalar(
            "SELECT name FROM ctq_characteristics \
             WHERE tenant_id = $1 AND is_active = TRUE \
             ORDER BY created_at DESC LIMIT 1",
        )
        .bind(user.tenant_id)
        .fetch_optional(pool.as_ref())
        .await
        .ok()
        .flatten(),
        None => None,
    };

    Ok(Json(StationSnapshot {
        current_job,
        pitch,
        current_step,
        quality_check,
        work_center_name,
        // Item 31: plain-language categories — Jidoka becomes instinctive,
        // the operator never learns Andon terminology.
        help_categories: vec![
            "Quality".to_string(),
            "Material".to_string(),
            "Machine".to_string(),
            "Method / instructions".to_string(),
            "Safety".to_string(),
            "I cannot keep pace".to_string(),
            "Something else".to_string(),
        ],
        generated_at: Utc::now(),
    }))
}

/// One interval of the plan-vs-actual board (item 32).
#[derive(Debug, Serialize)]
pub struct IntervalRow {
    pub interval_start: chrono::DateTime<Utc>,
    pub plan: i64,
    pub actual: i64,
    pub gap: i64,
    /// The abnormality timeline for a gap (what stopped flow).
    pub abnormalities: Vec<IntervalAbnormality>,
}

#[derive(Debug, Serialize)]
pub struct IntervalAbnormality {
    pub andon_number: String,
    pub issue_type: String,
    pub severity: String,
    pub created_at: chrono::DateTime<Utc>,
    pub response_seconds: Option<i64>,
    pub resolved: bool,
}

/// The team-lead interval board (item 32): plan vs actual per pitch
/// interval with the "what stopped flow?" timeline.
pub async fn get_interval_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<StationParams>,
) -> Result<Json<Vec<IntervalRow>>> {
    user.require_permission("tps:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Interval board requires the database".to_string()))?;
    let work_center_id = match params.work_center_id {
        Some(wc) => wc,
        None => crate::routes::agent::build_context(&user, &state)
            .await
            .work_center_id
            .ok_or_else(|| SenseiError::Validation("No work center assigned".to_string()))?,
    };

    // The last 4 hourly intervals.
    let mut rows: Vec<IntervalRow> = Vec::new();
    for back in (0..4).rev() {
        let now = Utc::now();
        let start = now
            .date_naive()
            .and_hms_opt(now.hour(), 0, 0)
            .map(|d| d.and_utc())
            .unwrap_or(now)
            - chrono::Duration::hours(back as i64);
        let end = start + chrono::Duration::hours(1);
        let actual: i64 = sqlx::query_scalar(
            "SELECT COALESCE(SUM(quantity_completed), 0)::bigint \
             FROM production_events \
             WHERE tenant_id = $1 AND work_center_id = $2 \
               AND occurred_at >= $3 AND occurred_at < $4 AND event_type = 'produced'",
        )
        .bind(user.tenant_id)
        .bind(work_center_id)
        .bind(start)
        .bind(end)
        .fetch_one(pool.as_ref())
        .await
        .unwrap_or(0);
        let plan: i64 = sqlx::query_scalar(
            "SELECT COALESCE((3600.0 / NULLIF(takt_time_seconds, 0))::bigint, 60) \
             FROM standard_work_documents \
             WHERE tenant_id = $1 AND status IN ('effective', 'published') \
             ORDER BY updated_at DESC LIMIT 1",
        )
        .bind(user.tenant_id)
        .fetch_one(pool.as_ref())
        .await
        .unwrap_or(60);
        let abnormalities: Vec<IntervalAbnormality> = sqlx::query_as(
            "SELECT andon_number, issue_type, severity, created_at, response_time_seconds, \
                    status = 'resolved' \
             FROM andons \
             WHERE tenant_id = $1 AND work_center_id = $2 \
               AND created_at >= $3 AND created_at < $4 \
             ORDER BY created_at ASC",
        )
        .bind(user.tenant_id)
        .bind(work_center_id)
        .bind(start)
        .bind(end)
        .fetch_all(pool.as_ref())
        .await
        .unwrap_or_default()
        .into_iter()
        .map(
            |(n, t, s, c, r, d): (
                String,
                String,
                String,
                chrono::DateTime<Utc>,
                Option<i64>,
                bool,
            )| {
                IntervalAbnormality {
                    andon_number: n,
                    issue_type: t,
                    severity: s,
                    created_at: c,
                    response_seconds: r,
                    resolved: d,
                }
            },
        )
        .collect();
        rows.push(IntervalRow {
            interval_start: start,
            plan,
            actual,
            gap: actual - plan,
            abnormalities,
        });
    }
    Ok(Json(rows))
}

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
use sensei_core::db::TenantTx;
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
    /// None when the job has no frozen standard — the UI must show
    /// STANDARD UNAVAILABLE, never a fabricated target.
    pub target: Option<i64>,
    pub actual: i64,
    pub gap: Option<i64>,
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
    /// The bound WorkStep's key point — why THIS step matters
    /// (thirteenth audit: the operator learns, not just follows).
    #[serde(default)]
    pub key_point: Option<String>,
    #[serde(default)]
    pub why_key_point_matters: Option<String>,
    #[serde(default)]
    pub safety_warning: Option<String>,
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

    // Wave C RLS (thirtieth-audit item 18): every table the snapshot
    // reads (work_centers, work_orders, production_events,
    // standard_work_documents, work_order_operations, products,
    // ctq_characteristics) is tenant-owned fail-closed FORCE RLS since
    // migration 175 — the whole snapshot runs on ONE TenantTx of the
    // caller's tenant.
    let mut db = TenantTx::begin(pool, user.tenant_id)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin station tx: {e}")))?;

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
                .fetch_one(&mut **db.tx())
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
                   AND wo.status IN ('in_progress', 'released') \
                 ORDER BY CASE WHEN wo.status = 'in_progress' THEN 0 ELSE 1 END, \
                          wo.actual_start DESC NULLS LAST, wo.created_at ASC LIMIT 1",
            )
            .bind(user.tenant_id)
            .bind(wc)
            .fetch_optional(&mut **db.tx())
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
        (Some(job), Some(_wc)) => {
            let now = Utc::now();
            let interval_start = now
                .date_naive()
                .and_hms_opt(now.hour(), 0, 0)
                .map(|d| d.and_utc())
                .unwrap_or(now);
            // Pitch ACTUAL (fourteenth audit): JOB-level semantics — only
            // the CURRENT work order's production counts this hour; a
            // previous job on the same work center must not inflate it.
            let actual: i64 = sqlx::query_scalar(
                "SELECT COALESCE(SUM(e.good_qty), 0)::bigint \
                 FROM production_events e \
                 WHERE e.tenant_id = $1 AND e.work_order_id = $2 \
                   AND e.created_at >= $3 AND e.event_type = 'produced'",
            )
            .bind(user.tenant_id)
            .bind(job.work_order_id)
            .bind(interval_start)
            .fetch_one(&mut **db.tx())
            .await
            .unwrap_or(0);
            // Pitch TARGET (fourteenth audit): ONLY the work order's
            // FROZEN standard revision — no tenant-global or product
            // fallback. A WO without a frozen standard has NO target: the
            // UI says STANDARD UNAVAILABLE, never a fabricated 60/h.
            let takt: Option<i64> = sqlx::query_scalar(
                "SELECT (3600.0 / NULLIF(s.takt_time_seconds, 0))::bigint \
                 FROM work_orders wo \
                 JOIN standard_work_documents s \
                   ON s.id = wo.standard_work_id AND s.tenant_id = wo.tenant_id \
                  AND s.status = 'effective' \
                  AND (s.effective_from IS NULL OR s.effective_from <= NOW()) \
                  AND (s.effective_to IS NULL OR s.effective_to > NOW()) \
                 WHERE wo.id = $1 AND wo.tenant_id = $2 \
                 LIMIT 1",
            )
            .bind(job.work_order_id)
            .bind(user.tenant_id)
            .fetch_one(&mut **db.tx())
            .await
            .ok();
            Some(PitchNow {
                target: takt,
                actual,
                gap: takt.map(|t| actual - t),
                interval_start,
            })
        }
        _ => None,
    };

    // CURRENT STEP (items 37 + thirteenth audit): the EXECUTION POINTER —
    // the first pending/in-progress operation of THIS work order, shown at
    // its ORDINAL position (1/3, not 10/30), bound to the RELEASED
    // standard's matching WorkStep so the operator sees the key point,
    // the WHY, the safety warning and the step's criticality.
    let current_step: Option<StepNow> = match current_job.as_ref() {
        Some(job) => {
            let row: Option<(String, i64, i64, i64, serde_json::Value)> = sqlx::query_as(
                "SELECT op.operation, op.standard_time::bigint, \
                        op.ordinal_position, \
                        (SELECT COUNT(*) FROM work_order_operations o2 \
                         WHERE o2.work_order_id = op.work_order_id), \
                        COALESCE(sw.steps, '[]') \
                 FROM work_order_operations op \
                 JOIN work_orders wo ON wo.id = op.work_order_id AND wo.tenant_id = op.tenant_id \
                 LEFT JOIN standard_work_documents sw \
                   ON sw.id = wo.standard_work_id AND sw.tenant_id = wo.tenant_id \
                 WHERE op.work_order_id = $1 AND op.tenant_id = $2 \
                   AND op.status IN ('pending', 'in_progress') \
                 ORDER BY op.ordinal_position ASC LIMIT 1",
            )
            .bind(job.work_order_id)
            .bind(user.tenant_id)
            .fetch_optional(&mut **db.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("Step read failed: {e}")))?;
            row.map(|(operation, standard_time, ordinal, total, steps)| {
                // Bind the operation to the released standard's WorkStep
                // by name/description — the operator sees the step's
                // reasons, not a bare operation label.
                let steps_arr = steps.as_array().cloned().unwrap_or_default();
                let step = steps_arr.iter().find(|st| {
                    st.get("description")
                        .and_then(|d| d.as_str())
                        .map(|d| {
                            d.to_lowercase().contains(&operation.to_lowercase())
                                || operation.to_lowercase().contains(&d.to_lowercase())
                        })
                        .unwrap_or(false)
                });
                let key_point = step
                    .and_then(|st| st.get("key_points"))
                    .and_then(|k| k.as_str())
                    .map(|k| k.to_string());
                let why = step
                    .and_then(|st| st.get("why_key_point_matters"))
                    .and_then(|k| k.as_str())
                    .map(|k| k.to_string());
                let safety = step
                    .and_then(|st| st.get("safety_warning"))
                    .and_then(|k| k.as_str())
                    .map(|k| k.to_string());
                let is_critical = step
                    .and_then(|st| st.get("is_critical"))
                    .and_then(|k| k.as_bool())
                    .unwrap_or(false);
                StepNow {
                    position: ordinal.max(0) as usize,
                    total_steps: total.max(0) as usize,
                    description: operation,
                    expected_seconds: Some(standard_time),
                    is_critical,
                    key_point,
                    why_key_point_matters: why,
                    safety_warning: safety,
                }
            })
        }
        None => None,
    };

    // KEY POINT / QUALITY CHECK (fourteenth audit): resolved for the
    // CURRENT OPERATION — the released standard's matching WorkStep
    // carries its own quality_checks (solder paste vs SMT placement vs
    // AOI...), with the product family's CTQ set as a safety net. Never
    // a single arbitrary family pick.
    let quality_check: Option<String> = match current_job.as_ref() {
        Some(job) => {
            let row: Option<(String, serde_json::Value)> = sqlx::query_as(
                "SELECT op.operation, COALESCE(sw.steps, '[]') \
                 FROM work_order_operations op \
                 JOIN work_orders wo ON wo.id = op.work_order_id AND wo.tenant_id = op.tenant_id \
                 LEFT JOIN standard_work_documents sw \
                   ON sw.id = wo.standard_work_id AND sw.tenant_id = wo.tenant_id \
                 WHERE op.work_order_id = $1 AND op.tenant_id = $2 \
                   AND op.status IN ('pending', 'in_progress') \
                 ORDER BY op.ordinal_position ASC LIMIT 1",
            )
            .bind(job.work_order_id)
            .bind(user.tenant_id)
            .fetch_optional(&mut **db.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("Step checks read failed: {e}")))?;
            match row {
                Some((operation, steps)) => {
                    let arr = steps.as_array().cloned().unwrap_or_default();
                    let step = arr.iter().find(|st| {
                        st.get("description")
                            .and_then(|d| d.as_str())
                            .map(|d| {
                                d.to_lowercase().contains(&operation.to_lowercase())
                                    || operation.to_lowercase().contains(&d.to_lowercase())
                            })
                            .unwrap_or(false)
                    });
                    let step_checks: Vec<String> = step
                        .and_then(|st| st.get("quality_checks"))
                        .and_then(|q| q.as_array())
                        .map(|q| {
                            q.iter()
                                .filter_map(|c| c.as_str().map(|x| x.to_string()))
                                .collect()
                        })
                        .unwrap_or_default();
                    if !step_checks.is_empty() {
                        Some(step_checks.join(" · "))
                    } else {
                        // Safety net: the product family's CTQ set.
                        let product_id: Option<Uuid> = sqlx::query_scalar(
                            "SELECT product_id FROM work_orders WHERE id = $1 AND tenant_id = $2",
                        )
                        .bind(job.work_order_id)
                        .bind(user.tenant_id)
                        .fetch_optional(&mut **db.tx())
                        .await
                        .ok()
                        .flatten();
                        let family: Option<Uuid> = match product_id {
                            Some(pid) => sqlx::query_scalar(
                                "SELECT product_family_id FROM products WHERE id = $1 AND tenant_id = $2",
                            )
                            .bind(pid)
                            .bind(user.tenant_id)
                            .fetch_optional(&mut **db.tx())
                            .await
                            .ok()
                            .flatten(),
                            None => None,
                        };
                        match family {
                            Some(family_id) => {
                                let names: Vec<String> = sqlx::query_scalar(
                                    "SELECT name FROM ctq_characteristics \
                                     WHERE tenant_id = $1 AND is_active = TRUE AND product_family_id = $2 \
                                     ORDER BY created_at DESC LIMIT 5",
                                )
                                .bind(user.tenant_id)
                                .bind(family_id)
                                .fetch_all(&mut **db.tx())
                                .await
                                .unwrap_or_default();
                                if names.is_empty() {
                                    None
                                } else {
                                    Some(names.join(" · "))
                                }
                            }
                            None => None,
                        }
                    }
                }
                None => None,
            }
        }
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
    // Wave C RLS: the interval-board reads run on ONE TenantTx of the
    // caller's tenant (see get_station_snapshot).
    let mut db = TenantTx::begin(pool, user.tenant_id)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin interval tx: {e}")))?;
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
            "SELECT COALESCE(SUM(e.good_qty), 0)::bigint \
             FROM production_events e \
             JOIN work_orders wo ON wo.id = e.work_order_id AND wo.tenant_id = e.tenant_id \
             WHERE e.tenant_id = $1 AND wo.work_center_id = $2 \
               AND e.created_at >= $3 AND e.created_at < $4 AND e.event_type = 'produced'",
        )
        .bind(user.tenant_id)
        .bind(work_center_id)
        .bind(start)
        .bind(end)
        .fetch_one(&mut **db.tx())
        .await
        .unwrap_or(0);
        let plan: i64 = sqlx::query_scalar(
            "SELECT COALESCE((3600.0 / NULLIF(takt_time_seconds, 0))::bigint, 60) \
             FROM standard_work_documents \
             WHERE tenant_id = $1 AND status IN ('effective', 'published') \
             ORDER BY updated_at DESC LIMIT 1",
        )
        .bind(user.tenant_id)
        .fetch_one(&mut **db.tx())
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
        .fetch_all(&mut **db.tx())
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

//! Today (daily dashboard / aggregated view) route handlers.
//!
//! Provides a single aggregated endpoint that returns a real-time snapshot
//! of the day's key metrics across production, quality, and operations,
//! designed for "Today Screen" / daily stand-up dashboards.

use axum::{Json, extract::State};
use chrono::Utc;
use serde::Serialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;

use crate::state::AppState;

// ── Response DTOs ──────────────────────────────────────────────────────────

/// Aggregated daily snapshot returned by the `/api/v1/today` endpoint.
#[derive(Debug, Serialize)]
pub struct TodaySnapshot {
    pub date: String,
    pub work_orders: WorkOrderSummary,
    pub quality: QualitySummary,
    pub operations: OperationsSummary,
}

/// Summary of work order activity for the day.
#[derive(Debug, Serialize)]
pub struct WorkOrderSummary {
    pub total_active: usize,
    pub completed_today: usize,
    pub in_progress: usize,
    pub overdue: usize,
}

/// Summary of quality events for the day.
#[derive(Debug, Serialize)]
pub struct QualitySummary {
    pub active_andons: usize,
    pub open_ncrs: usize,
    pub open_capas: usize,
}

/// Summary of operations/continuous improvement activity for the day.
#[derive(Debug, Serialize)]
pub struct OperationsSummary {
    pub open_risks: usize,
    pub open_a3s: usize,
    pub active_projects: usize,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// Get the aggregated "Today" dashboard snapshot.
///
/// Aggregates data from work orders, quality (Andon, NCR, CAPA),
/// and operations (risks, A3 reports, projects) into a single
/// response for daily stand-up and management dashboards.
pub async fn get_today_snapshot(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<TodaySnapshot>> {
    let tenant_id = user.tenant_id;
    let today = Utc::now().date_naive();
    let date_str = today.to_string();

    // ── Work Orders ──────────────────────────────────────────────────
    let all_work_orders = state
        .production_service
        .list_work_orders(tenant_id, None, None, Some(1), Some(10_000))
        .await?;

    let work_order_summary = {
        let orders = &all_work_orders.data;
        let total_active = orders
            .iter()
            .filter(|o| o.status != "Cancelled" && o.status != "Completed")
            .count();
        let completed_today = orders
            .iter()
            .filter(|o| {
                o.status == "Completed"
                    && o.updated_at.date_naive() == today
            })
            .count();
        let in_progress = orders
            .iter()
            .filter(|o| o.status == "InProgress" || o.status == "In Progress")
            .count();
        let overdue = orders
            .iter()
            .filter(|o| {
                o.status != "Completed"
                    && o.status != "Cancelled"
                    && o.scheduled_end.map_or(false, |end| end.date_naive() < today)
            })
            .count();

        WorkOrderSummary {
            total_active,
            completed_today,
            in_progress,
            overdue,
        }
    };

    // ── Quality (Andon events) ───────────────────────────────────────
    let all_andons = state
        .ops_service
        .list_andons(tenant_id, None, None, Some(1), Some(10_000))
        .await?;

    let active_andons = all_andons
        .data
        .iter()
        .filter(|a| a.status == "Active" || a.status == "Open")
        .count();

    // ── Quality (NCRs via quality_service) ───────────────────────────
    // List NCRs with minimal filters to count open records.
    let all_ncrs = state
        .quality_service
        .list_ncrs(tenant_id, None, None, None, Some(1), Some(10_000))
        .await?;
    let open_ncrs = all_ncrs.data.len();

    // List CAPAs with minimal filters to count open records.
    let all_capas = state
        .quality_service
        .list_capas(tenant_id, None, None, Some(1), Some(10_000))
        .await?;
    let open_capas = all_capas.data.len();

    // ── Operations (Risks, A3s, Projects) ────────────────────────────
    let all_risks = state
        .ops_service
        .list_risks(tenant_id, None, None, Some(1), Some(10_000))
        .await?;

    let open_risks = all_risks
        .data
        .iter()
        .filter(|r| r.status == "Open" || r.status == "Active")
        .count();

    let all_a3s = state
        .ops_service
        .list_a3s(tenant_id, None, Some(1), Some(10_000))
        .await?;

    let open_a3s = all_a3s
        .data
        .iter()
        .filter(|a| a.status != "Closed")
        .count();

    let all_projects = state
        .ops_service
        .list_projects(tenant_id, None, None, Some(1), Some(10_000))
        .await?;

    let active_projects = all_projects
        .data
        .iter()
        .filter(|p| p.status != "Completed" && p.status != "Cancelled")
        .count();

    // ── Assemble response ────────────────────────────────────────────
    Ok(Json(TodaySnapshot {
        date: date_str,
        work_orders: work_order_summary,
        quality: QualitySummary {
            active_andons,
            open_ncrs,
            open_capas,
        },
        operations: OperationsSummary {
            open_risks,
            open_a3s,
            active_projects,
        },
    }))
}

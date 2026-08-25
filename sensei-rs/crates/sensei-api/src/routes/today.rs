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
use sensei_services::ops::{A3, Andon, Project, Risk};
use sensei_services::production::WorkOrder;
use sensei_services::quality::{CapaExtended, CapaStatusEx, NcrStatus, NonConformance};
use uuid::Uuid;

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

/// Page through every work order in the tenant.
async fn fetch_all_work_orders(state: &AppState, tenant_id: Uuid) -> Result<Vec<WorkOrder>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .production_service
            .list_work_orders(tenant_id, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Page through every Andon in the tenant.
async fn fetch_all_andons(state: &AppState, tenant_id: Uuid) -> Result<Vec<Andon>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .ops_service
            .list_andons(tenant_id, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Page through every NCR in the tenant.
async fn fetch_all_ncrs(state: &AppState, tenant_id: Uuid) -> Result<Vec<NonConformance>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .quality_service
            .list_ncrs(tenant_id, None, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Page through every CAPA in the tenant.
async fn fetch_all_capas(state: &AppState, tenant_id: Uuid) -> Result<Vec<CapaExtended>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .quality_service
            .list_capas(tenant_id, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Page through every risk in the tenant.
async fn fetch_all_risks(state: &AppState, tenant_id: Uuid) -> Result<Vec<Risk>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .ops_service
            .list_risks(tenant_id, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Page through every A3 in the tenant.
async fn fetch_all_a3s(state: &AppState, tenant_id: Uuid) -> Result<Vec<A3>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .ops_service
            .list_a3s(tenant_id, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Page through every project in the tenant.
async fn fetch_all_projects(state: &AppState, tenant_id: Uuid) -> Result<Vec<Project>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .ops_service
            .list_projects(tenant_id, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

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
    let all_work_orders = fetch_all_work_orders(&state, tenant_id).await?;

    let work_order_summary = {
        let total_active = all_work_orders
            .iter()
            .filter(|o| o.status != "Cancelled" && o.status != "Completed")
            .count();
        let completed_today = all_work_orders
            .iter()
            .filter(|o| o.status == "Completed" && o.updated_at.date_naive() == today)
            .count();
        let in_progress = all_work_orders
            .iter()
            .filter(|o| {
                o.status == "InProgress" || o.status == "In Progress" || o.status == "in_progress"
            })
            .count();
        let overdue = all_work_orders
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
    let all_andons = fetch_all_andons(&state, tenant_id).await?;
    let active_andons = all_andons
        .iter()
        .filter(|a| a.status == "Active" || a.status == "Open" || a.status == "active")
        .count();

    // ── Quality (NCRs via quality_service) ───────────────────────────
    // "Open" means not closed/cancelled — page through everything and
    // count the records that are still active.
    let all_ncrs = fetch_all_ncrs(&state, tenant_id).await?;
    let open_ncrs = all_ncrs
        .iter()
        .filter(|n| n.status != NcrStatus::Closed && n.status != NcrStatus::Cancelled)
        .count();

    // CAPAs: open excludes Closed/Rejected/Cancelled.
    let all_capas = fetch_all_capas(&state, tenant_id).await?;
    let open_capas = all_capas
        .iter()
        .filter(|c| {
            c.status != CapaStatusEx::Closed
                && c.status != CapaStatusEx::Rejected
                && c.status != CapaStatusEx::Cancelled
        })
        .count();

    // ── Operations (Risks, A3s, Projects) ────────────────────────────
    let all_risks = fetch_all_risks(&state, tenant_id).await?;
    let open_risks = all_risks
        .iter()
        .filter(|r| r.status == "Open" || r.status == "Active")
        .count();

    let all_a3s = fetch_all_a3s(&state, tenant_id).await?;
    let open_a3s = all_a3s.iter().filter(|a| a.status != "Closed").count();

    let all_projects = fetch_all_projects(&state, tenant_id).await?;
    let active_projects = all_projects
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

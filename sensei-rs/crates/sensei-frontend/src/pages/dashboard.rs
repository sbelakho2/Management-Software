//! Dashboard page — the main authenticated landing page.
//!
//! Rams design system — uses MetricDisplay components in a 4-column grid
//! and a Module for quick links. Header/nav elements removed since they
//! are now provided by RootLayout / RackSidebar.

use crate::api::{
    finance::FinanceApi, hr::HrApi, maintenance::MaintenanceApi, ops::OpsApi,
    production::ProductionApi, quality::QualityApi, supply_chain::SupplyChainApi,
};
use crate::components::metric_display::MetricDisplay;
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// Dashboard metrics fetched on mount.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
struct DashboardMetrics {
    open_ncrs: usize,
    active_capas: usize,
    open_work_orders: usize,
    open_work_requests: usize,
    total_employees: usize,
    pending_leave: usize,
    active_projects: usize,
    active_andons: usize,
    total_invoices: usize,
    total_inventory_items: usize,
    overdue_pm_tasks: usize,
    active_risks: usize,
    /// Item 4: which domains FAILED to load. A failed request must NEVER
    /// look like a healthy zero — the tile renders UNAVAILABLE instead.
    #[serde(default)]
    pub unavailable: Vec<String>,
}

impl DashboardMetrics {
    fn unavailable(&mut self, domain: &str) {
        if !self.unavailable.iter().any(|d| d == domain) {
            self.unavailable.push(domain.to_string());
        }
    }
}

/// Dashboard page component.
#[component]
pub fn DashboardPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");

    // Fetch real dashboard metrics
    let app_state_for_data = app_state.clone();
    let metrics = ArcLocalResource::new(move || {
        let state = app_state_for_data.clone();
        async move {
            let client = state.api_client();
            let mut m = DashboardMetrics::default();

            // Quality
            match QualityApi::list_ncrs(&client).await {
                Ok(ncrs) => {
                    m.open_ncrs = ncrs
                        .iter()
                        .filter(|n| n.status == "Open" || n.status == "open")
                        .count();
                }
                Err(_) => m.unavailable("quality"),
            }
            match QualityApi::list_capas(&client).await {
                Ok(capas) => {
                    m.active_capas = capas
                        .iter()
                        .filter(|c| c.status != "Closed" && c.status != "closed")
                        .count();
                }
                Err(_) => m.unavailable("quality"),
            }

            // Production
            match ProductionApi::list_work_orders(&client).await {
                Ok(wos) => {
                    m.open_work_orders = wos
                        .iter()
                        .filter(|wo| wo.status != "Completed" && wo.status != "completed")
                        .count();
                }
                Err(_) => m.unavailable("production"),
            }

            // Maintenance
            match MaintenanceApi::list_work_requests(&client).await {
                Ok(wrs) => {
                    m.open_work_requests = wrs
                        .iter()
                        .filter(|wr| wr.status != "Completed" && wr.status != "completed")
                        .count();
                }
                Err(_) => m.unavailable("maintenance"),
            }
            match MaintenanceApi::list_pm_schedules(&client).await {
                Ok(pms) => {
                    m.overdue_pm_tasks = pms
                        .iter()
                        .filter(|pm| pm.status == "Overdue" || pm.status == "overdue")
                        .count();
                }
                Err(_) => m.unavailable("maintenance"),
            }

            // HR
            match HrApi::list_employees(&client).await {
                Ok(emps) => m.total_employees = emps.len(),
                Err(_) => m.unavailable("hr"),
            }
            match HrApi::list_leave_requests(&client).await {
                Ok(leaves) => {
                    m.pending_leave = leaves
                        .iter()
                        .filter(|l| l.status == "Pending" || l.status == "pending")
                        .count();
                }
                Err(_) => m.unavailable("hr"),
            }

            // Operations
            match OpsApi::list_andons(&client).await {
                Ok(andons) => {
                    m.active_andons = andons
                        .iter()
                        .filter(|a| a.status != "Resolved" && a.status != "resolved")
                        .count();
                }
                Err(_) => m.unavailable("operations"),
            }
            match OpsApi::list_projects(&client).await {
                Ok(projects) => {
                    m.active_projects = projects
                        .iter()
                        .filter(|p| {
                            p.status != "Completed"
                                && p.status != "completed"
                                && p.status != "Closed"
                                && p.status != "closed"
                        })
                        .count();
                }
                Err(_) => m.unavailable("operations"),
            }
            match OpsApi::list_risks(&client).await {
                Ok(risks) => {
                    m.active_risks = risks
                        .iter()
                        .filter(|r| r.status != "Mitigated" && r.status != "mitigated")
                        .count();
                }
                Err(_) => m.unavailable("operations"),
            }

            // Finance
            match FinanceApi::list_invoices(&client).await {
                Ok(invs) => m.total_invoices = invs.len(),
                Err(_) => m.unavailable("finance"),
            }

            // Supply Chain
            match SupplyChainApi::list_inventory(&client).await {
                Ok(inv) => m.total_inventory_items = inv.len(),
                Err(_) => m.unavailable("supply-chain"),
            }

            m
        }
    });

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-4">"SYSTEM OVERVIEW"</h1>
            {move || metrics.map(|m| {
                let m = &**m;
                // Item 4: a failed domain is a BUSINESS STATE, not a zero.
                // Render the UNAVAILABLE banner and mark the affected tiles.
                let unavailable = m.unavailable.clone();
                let has_failures = !unavailable.is_empty();
                let unavailable_clone = unavailable.clone();
                let is_unavail = move |d: &str| unavailable_clone.iter().any(|u| u == d);
                view! {
                    {if has_failures {
                        view! {
                            <div class="rams-alert rams-alert--danger rams-mb-4" role="alert">
                                <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                                <span>" "</span>
                                {format!(
                                    "Could not obtain {} — values below are NOT confirmed. Check connectivity or permissions.",
                                    unavailable.join(", ")
                                )}
                            </div>
                        }.into_any()
                    } else {
                        ().into_any()
                    }}
                    // Quality & Production (4 metrics — respects 5-element rule)
                    <div class="module rams-mb-4">
                        <div class="module-header">
                            <h3 class="module-title">"QUALITY & PRODUCTION"</h3>
                        </div>
                        <div class="module-content">
                            <div class="rams-grid rams-grid--cols-4 rams-gap-4">
                                <MetricDisplay value={
        if is_unavail("quality") {
            "UNAVAILABLE".to_string()
        } else {
            m.open_ncrs.to_string()
        }
    } label="OPEN NCRs".to_string() />
                                <MetricDisplay value={
        if is_unavail("quality") {
            "UNAVAILABLE".to_string()
        } else {
            m.active_capas.to_string()
        }
    } label="ACTIVE CAPAs".to_string() />
                                <MetricDisplay value={
        if is_unavail("production") {
            "UNAVAILABLE".to_string()
        } else {
            m.open_work_orders.to_string()
        }
    } label="OPEN WORK ORDERS".to_string() />
                                <MetricDisplay value={
        if is_unavail("maintenance") {
            "UNAVAILABLE".to_string()
        } else {
            m.open_work_requests.to_string()
        }
    } label="WORK REQUESTS".to_string() />
                            </div>
                        </div>
                    </div>
                    // HR & Operations (4 metrics)
                    <div class="module rams-mb-4">
                        <div class="module-header">
                            <h3 class="module-title">"HR & OPERATIONS"</h3>
                        </div>
                        <div class="module-content">
                            <div class="rams-grid rams-grid--cols-4 rams-gap-4">
                                <MetricDisplay value={
        if is_unavail("hr") {
            "UNAVAILABLE".to_string()
        } else {
            m.total_employees.to_string()
        }
    } label="EMPLOYEES".to_string() />
                                <MetricDisplay value={
        if is_unavail("hr") {
            "UNAVAILABLE".to_string()
        } else {
            m.pending_leave.to_string()
        }
    } label="PENDING LEAVE".to_string() />
                                <MetricDisplay value={
        if is_unavail("operations") {
            "UNAVAILABLE".to_string()
        } else {
            m.active_projects.to_string()
        }
    } label="ACTIVE PROJECTS".to_string() />
                                <MetricDisplay value={
        if is_unavail("operations") {
            "UNAVAILABLE".to_string()
        } else {
            m.active_andons.to_string()
        }
    } label="ACTIVE ANDONS".to_string() />
                            </div>
                        </div>
                    </div>
                    // Finance & Supply Chain (4 metrics)
                    <div class="module rams-mb-4">
                        <div class="module-header">
                            <h3 class="module-title">"FINANCE & SUPPLY CHAIN"</h3>
                        </div>
                        <div class="module-content">
                            <div class="rams-grid rams-grid--cols-4 rams-gap-4">
                                <MetricDisplay value={
        if is_unavail("finance") {
            "UNAVAILABLE".to_string()
        } else {
            m.total_invoices.to_string()
        }
    } label="INVOICES".to_string() />
                                <MetricDisplay value={
        if is_unavail("supply-chain") {
            "UNAVAILABLE".to_string()
        } else {
            m.total_inventory_items.to_string()
        }
    } label="INVENTORY ITEMS".to_string() />
                                <MetricDisplay value={
        if is_unavail("maintenance") {
            "UNAVAILABLE".to_string()
        } else {
            m.overdue_pm_tasks.to_string()
        }
    } label="OVERDUE PM TASKS".to_string() />
                                <MetricDisplay value={
        if is_unavail("operations") {
            "UNAVAILABLE".to_string()
        } else {
            m.active_risks.to_string()
        }
    } label="ACTIVE RISKS".to_string() />
                            </div>
                        </div>
                    </div>
                }.into_any()
            }).unwrap_or_else(|| view! {
                <div class="module rams-mb-4">
                    <div class="module-content">
                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted)">"LOADING SYSTEM METRICS..."</p>
                    </div>
                </div>
            }.into_any())}

            <Module title="QUICK LINKS".to_string()>
                <div class="rams-flex rams-flex--wrap rams-gap-2">
                    <a href="/quality/ncrs" class="rams-btn rams-btn--ghost rams-btn--md">"VIEW NCRs"</a>
                    <a href="/quality/capa" class="rams-btn rams-btn--ghost rams-btn--md">"VIEW CAPAs"</a>
                    <a href="/production/work-orders" class="rams-btn rams-btn--ghost rams-btn--md">"WORK ORDERS"</a>
                    <a href="/maintenance/work-requests" class="rams-btn rams-btn--ghost rams-btn--md">"MAINTENANCE REQUESTS"</a>
                    <a href="/hr/employees" class="rams-btn rams-btn--ghost rams-btn--md">"EMPLOYEES"</a>
                    <a href="/supply-chain/inventory" class="rams-btn rams-btn--ghost rams-btn--md">"INVENTORY"</a>
                    <a href="/ops/andons" class="rams-btn rams-btn--ghost rams-btn--md">"ANDON BOARD"</a>
                    <a href="/finance/invoices" class="rams-btn rams-btn--ghost rams-btn--md">"INVOICES"</a>
                </div>
            </Module>
        </div>
    }
}

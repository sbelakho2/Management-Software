//! Executive / CEO dashboard reactive store.
//!
//! Mirrors the Zustand [`executive.ts`](frontend/src/stores/executive.ts) store.

use crate::api::client::{ApiClient, ApiError};
use crate::api::executive::{
    CeoDashboardResponse, CrossFunctionalKpiResponse, EmployeeRiskRequest,
    EmployeeRiskResponse, ExecutiveApi, Nl2SqlRequest, Nl2SqlResponse, SqdcpResponse,
    StrategicDirectivesResponse,
};
use leptos::prelude::*;

/// Reactive store for executive dashboard data.
#[derive(Debug, Clone)]
pub struct ExecutiveStore {
    // NL2SQL
    pub nl2sql_result: RwSignal<Option<Nl2SqlResponse>>,
    pub nl2sql_loading: RwSignal<bool>,
    pub nl2sql_error: RwSignal<Option<String>>,
    // Risk analysis
    pub risk_result: RwSignal<Option<EmployeeRiskResponse>>,
    pub risk_loading: RwSignal<bool>,
    pub risk_error: RwSignal<Option<String>>,
    // SQDCP
    pub sqdcp: RwSignal<Option<SqdcpResponse>>,
    pub sqdcp_loading: RwSignal<bool>,
    pub sqdcp_error: RwSignal<Option<String>>,
    // KPI Summary
    pub kpi_summary: RwSignal<Option<CrossFunctionalKpiResponse>>,
    pub kpi_loading: RwSignal<bool>,
    pub kpi_error: RwSignal<Option<String>>,
    // Strategic Directives
    pub directives: RwSignal<Option<StrategicDirectivesResponse>>,
    pub directives_loading: RwSignal<bool>,
    pub directives_error: RwSignal<Option<String>>,
    // CEO Dashboard (aggregate)
    pub ceo_dashboard: RwSignal<Option<CeoDashboardResponse>>,
    pub ceo_dashboard_loading: RwSignal<bool>,
    pub ceo_dashboard_error: RwSignal<Option<String>>,
}

impl ExecutiveStore {
    pub fn new() -> Self {
        Self {
            nl2sql_result: RwSignal::new(None),
            nl2sql_loading: RwSignal::new(false),
            nl2sql_error: RwSignal::new(None),
            risk_result: RwSignal::new(None),
            risk_loading: RwSignal::new(false),
            risk_error: RwSignal::new(None),
            sqdcp: RwSignal::new(None),
            sqdcp_loading: RwSignal::new(false),
            sqdcp_error: RwSignal::new(None),
            kpi_summary: RwSignal::new(None),
            kpi_loading: RwSignal::new(false),
            kpi_error: RwSignal::new(None),
            directives: RwSignal::new(None),
            directives_loading: RwSignal::new(false),
            directives_error: RwSignal::new(None),
            ceo_dashboard: RwSignal::new(None),
            ceo_dashboard_loading: RwSignal::new(false),
            ceo_dashboard_error: RwSignal::new(None),
        }
    }

    pub async fn run_nl2sql(&self, client: &ApiClient, question: &str) {
        self.nl2sql_loading.set(true);
        self.nl2sql_error.set(None);
        match ExecutiveApi::nl2sql_query(client, &Nl2SqlRequest { question: question.to_string() }).await {
            Ok(data) => self.nl2sql_result.set(Some(data)),
            Err(e) => self.nl2sql_error.set(Some(e.to_string())),
        }
        self.nl2sql_loading.set(false);
    }

    pub async fn analyze_risk(&self, client: &ApiClient, employee_name: &str, department: Option<&str>) {
        self.risk_loading.set(true);
        self.risk_error.set(None);
        let req = EmployeeRiskRequest {
            employee_name: employee_name.to_string(),
            department: department.map(|s| s.to_string()),
            tenure_months: None,
            overtime_hours_weekly: None,
            skip_rate: None,
            peer_comparison: None,
        };
        match ExecutiveApi::get_risk_analysis(client, &req).await {
            Ok(data) => self.risk_result.set(Some(data)),
            Err(e) => self.risk_error.set(Some(e.to_string())),
        }
        self.risk_loading.set(false);
    }

    pub async fn fetch_sqdcp(&self, client: &ApiClient) {
        self.sqdcp_loading.set(true);
        self.sqdcp_error.set(None);
        match ExecutiveApi::get_sqdcp_summary(client).await {
            Ok(data) => self.sqdcp.set(Some(data)),
            Err(e) => self.sqdcp_error.set(Some(e.to_string())),
        }
        self.sqdcp_loading.set(false);
    }

    pub async fn fetch_kpi_summary(&self, client: &ApiClient) {
        self.kpi_loading.set(true);
        self.kpi_error.set(None);
        match ExecutiveApi::get_kpi_dashboard(client).await {
            Ok(data) => self.kpi_summary.set(Some(data)),
            Err(e) => self.kpi_error.set(Some(e.to_string())),
        }
        self.kpi_loading.set(false);
    }

    pub async fn fetch_directives(&self, client: &ApiClient) {
        self.directives_loading.set(true);
        self.directives_error.set(None);
        match ExecutiveApi::get_strategic_directives(client).await {
            Ok(data) => self.directives.set(Some(data)),
            Err(e) => self.directives_error.set(Some(e.to_string())),
        }
        self.directives_loading.set(false);
    }

    pub async fn fetch_ceo_dashboard(&self, client: &ApiClient) {
        self.ceo_dashboard_loading.set(true);
        self.ceo_dashboard_error.set(None);
        match ExecutiveApi::get_ceo_dashboard(client).await {
            Ok(data) => self.ceo_dashboard.set(Some(data)),
            Err(e) => self.ceo_dashboard_error.set(Some(e.to_string())),
        }
        self.ceo_dashboard_loading.set(false);
    }

    /// Clear all executive results.
    pub fn clear_results(&self) {
        self.nl2sql_result.set(None);
        self.risk_result.set(None);
        self.sqdcp.set(None);
        self.kpi_summary.set(None);
        self.directives.set(None);
        self.ceo_dashboard.set(None);
        self.nl2sql_error.set(None);
        self.risk_error.set(None);
        self.sqdcp_error.set(None);
        self.kpi_error.set(None);
        self.directives_error.set(None);
        self.ceo_dashboard_error.set(None);
    }
}

impl Default for ExecutiveStore {
    fn default() -> Self {
        Self::new()
    }
}

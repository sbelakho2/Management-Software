//! Executive / CEO dashboard API endpoints.
//!
//! NL2SQL, risk analysis, SQDCP, strategic directives, CEO dashboard.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Nl2SqlRequest {
    pub question: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Nl2SqlResponse {
    pub query_id: String,
    pub natural_language: String,
    pub generated_sql: String,
    pub explanation: String,
    pub result: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmployeeRiskRequest {
    pub employee_name: String,
    pub department: Option<String>,
    pub tenure_months: Option<i32>,
    pub overtime_hours_weekly: Option<f64>,
    pub skip_rate: Option<f64>,
    pub peer_comparison: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmployeeRiskResponse {
    pub employee_name: String,
    pub retention_risk: String,
    pub retention_score: f64,
    pub burnout_risk: String,
    pub burnout_score: f64,
    pub risk_factors: Vec<String>,
    pub recommendations: Vec<String>,
    pub confidence: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SqdcpPillar {
    pub status: String,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SqdcpResponse {
    pub safety: SqdcpPillar,
    pub quality: SqdcpPillar,
    pub delivery: SqdcpPillar,
    pub cost: SqdcpPillar,
    pub people: SqdcpPillar,
    pub generated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrossFunctionalKpiResponse {
    pub quality_score: f64,
    pub delivery_score: f64,
    pub cost_efficiency: f64,
    pub workforce_utilization: f64,
    pub inventory_health: f64,
    pub overall_score: f64,
    pub details: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrategicDirective {
    pub priority: String,
    pub title: String,
    pub description: String,
    pub severity: String,
    pub category: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrategicDirectivesResponse {
    pub directives: Vec<StrategicDirective>,
    pub generated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataThreadSummary {
    pub latest_snapshot_date: Option<String>,
    pub exported_record_count: i32,
    pub fact_counts: HashMap<String, i32>,
    pub lineage_link_count: i32,
    pub reasoning_trace_count: i32,
    pub event_bus: HashMap<String, serde_json::Value>,
    pub cross_domain: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CognitiveObeySummary {
    pub trend_warnings: Vec<TrendWarning>,
    pub warning_count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrendWarning {
    pub metric_id: String,
    pub direction: String,
    pub days_to_breach: i32,
    pub confidence: f64,
    pub recommendation: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CeoInsight {
    pub title: Option<String>,
    pub description: Option<String>,
    pub recommendation: Option<String>,
    pub severity: Option<String>,
    pub category: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CeoDashboardResponse {
    pub data_thread: DataThreadSummary,
    pub sqdcp: SqdcpResponse,
    pub kpi_summary: CrossFunctionalKpiResponse,
    pub insights: Vec<CeoInsight>,
    pub cognitive_obeya: Option<CognitiveObeySummary>,
    pub generated_at: String,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct ExecutiveApi;

impl ExecutiveApi {
    pub async fn get_executive_summary(
        client: &ApiClient,
    ) -> Result<CeoDashboardResponse, ApiError> {
        client.get("/api/v1/executive/summary").await
    }

    pub async fn get_kpi_dashboard(
        client: &ApiClient,
    ) -> Result<CrossFunctionalKpiResponse, ApiError> {
        client.get("/api/v1/executive/kpi-dashboard").await
    }

    pub async fn nl2sql_query(
        client: &ApiClient,
        req: &Nl2SqlRequest,
    ) -> Result<Nl2SqlResponse, ApiError> {
        client.post("/api/v1/executive/nl2sql", req).await
    }

    pub async fn get_risk_analysis(
        client: &ApiClient,
        req: &EmployeeRiskRequest,
    ) -> Result<EmployeeRiskResponse, ApiError> {
        client
            .post("/api/v1/executive/employee-risk/analyze", req)
            .await
    }

    pub async fn get_sqdcp_summary(client: &ApiClient) -> Result<SqdcpResponse, ApiError> {
        client.get("/api/v1/executive/sqdcp").await
    }

    pub async fn get_strategic_directives(
        client: &ApiClient,
    ) -> Result<StrategicDirectivesResponse, ApiError> {
        client.get("/api/v1/executive/strategic-directives").await
    }

    pub async fn get_ceo_dashboard(client: &ApiClient) -> Result<CeoDashboardResponse, ApiError> {
        client.get("/api/v1/executive/ceo-dashboard").await
    }
}

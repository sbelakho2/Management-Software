//! Analytics and ML insights API endpoints.
//!
//! ML insights, performance trends, system health, KPI summary.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MlInsight {
    pub id: String,
    #[serde(rename = "type")]
    pub insight_type: String,
    pub title: String,
    pub description: String,
    pub confidence: f64,
    pub impact: String,
    pub category: String,
    pub model_name: String,
    pub action_items: Option<Vec<String>>,
    pub severity: Option<String>,
    pub recommendation: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceTrend {
    pub metric: String,
    pub current_value: f64,
    pub previous_value: f64,
    pub change_percent: f64,
    pub trend: String,
    pub prediction_7d: f64,
    pub prediction_30d: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    pub status: String,
    pub uptime_seconds: i64,
    pub database: DatabaseHealth,
    pub ml_models: MlModelsHealth,
    pub last_checked: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseHealth {
    pub connected: bool,
    pub latency_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MlModelsHealth {
    pub active: i32,
    pub failed: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiSummary {
    pub metric: String,
    pub value: f64,
    pub target: Option<f64>,
    pub unit: Option<String>,
    pub trend: Option<String>,
    pub change_percent: Option<f64>,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct AnalyticsApi;

impl AnalyticsApi {
    pub async fn get_insights(client: &ApiClient) -> Result<Vec<MlInsight>, ApiError> {
        client.get("/api/v1/analytics/insights").await
    }

    pub async fn get_performance_trends(
        client: &ApiClient,
    ) -> Result<Vec<PerformanceTrend>, ApiError> {
        client.get("/api/v1/analytics/trends").await
    }

    pub async fn get_system_health(client: &ApiClient) -> Result<SystemHealth, ApiError> {
        client.get("/api/v1/analytics/health").await
    }

    pub async fn get_kpi_summary(client: &ApiClient) -> Result<Vec<KpiSummary>, ApiError> {
        client.get("/api/v1/analytics/kpi-summary").await
    }
}

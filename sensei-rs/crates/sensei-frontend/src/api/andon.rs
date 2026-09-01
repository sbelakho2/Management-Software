//! Andon system API endpoints.
//!
//! Raise, acknowledge, resolve, escalate andon events; analytics.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// The CANONICAL Andon contract — shared with the backend via
/// sensei-contracts (thirteenth audit): no independent DTO exists twice.
pub type AndonEventDto = sensei_contracts::Andon;

/// The operator's raise inputs (canonical command DTO — the server
/// derives actor/tenant/status/work center).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RaiseAndonData {
    pub work_center_id: Option<String>,
    pub issue_type: String,
    pub severity: String,
    pub description: String,
}

/// The safe Andon raise command DTO — the operator's inputs only; the
/// server derives actor/tenant/status (item 40).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RaiseAndonCommandRequest {
    pub issue_type: String,
    pub severity: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolveAndonData {
    pub resolution: String,
    pub root_cause: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndonAnalytics {
    pub avg_response_time_minutes: f64,
    pub avg_resolution_time_minutes: f64,
    pub total_signals: i32,
    pub uptime_impact_percent: f64,
    pub signals_by_category: HashMap<String, i32>,
    pub top_problem_stations: Vec<ProblemStation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProblemStation {
    pub station_id: String,
    pub count: i32,
    pub downtime_hours: f64,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct AndonApi;

impl AndonApi {
    pub async fn list_andons(client: &ApiClient) -> Result<Vec<AndonEventDto>, ApiError> {
        client.get("/api/v1/andon").await
    }

    pub async fn get_andon(client: &ApiClient, id: &str) -> Result<AndonEventDto, ApiError> {
        client.get(&format!("/api/v1/andon/{}", id)).await
    }

    pub async fn raise_andon(
        client: &ApiClient,
        data: &RaiseAndonData,
    ) -> Result<AndonEventDto, ApiError> {
        client.post("/api/v1/andon", data).await
    }

    pub async fn acknowledge_andon(
        client: &ApiClient,
        id: &str,
    ) -> Result<AndonEventDto, ApiError> {
        client
            .post(
                &format!("/api/v1/andon/{}/acknowledge", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn resolve_andon(
        client: &ApiClient,
        id: &str,
        data: &ResolveAndonData,
    ) -> Result<AndonEventDto, ApiError> {
        client
            .post(&format!("/api/v1/andon/{}/resolve", id), data)
            .await
    }

    pub async fn escalate_andon(client: &ApiClient, id: &str) -> Result<AndonEventDto, ApiError> {
        client
            .post(
                &format!("/api/v1/andon/{}/escalate", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn get_andon_analytics(
        client: &ApiClient,
        days: Option<i32>,
    ) -> Result<AndonAnalytics, ApiError> {
        let path = match days {
            Some(d) => format!("/api/v1/andon/analytics?days={}", d),
            None => "/api/v1/andon/analytics".to_string(),
        };
        client.get(&path).await
    }
}

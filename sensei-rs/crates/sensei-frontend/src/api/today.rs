//! Today screen API endpoints.
//!
//! Priorities, commitments, abnormalities, shift handover, micro-drills, pulses.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopPriority {
    pub id: String,
    pub title: String,
    #[serde(rename = "type")]
    pub priority_type: String,
    pub due_date: Option<String>,
    pub priority: Option<String>,
    pub status: Option<String>,
    pub assigned_to: Option<String>,
    pub related_entity_id: Option<String>,
    pub related_entity_type: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopRisk {
    pub id: String,
    pub title: String,
    pub severity: String,
    pub area: String,
    pub mitigated: Option<bool>,
    pub score: Option<f64>,
    pub owner: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TodaysCommitment {
    pub id: String,
    pub description: String,
    pub due_time: Option<String>,
    pub completed: Option<bool>,
    #[serde(rename = "type")]
    pub commitment_type: String,
    pub related_to: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Abnormality {
    pub id: String,
    #[serde(rename = "type")]
    pub abnormality_type: String,
    pub description: String,
    pub severity: String,
    pub status: String,
    pub detected_at: String,
    pub station_id: Option<i32>,
    pub resolved: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuickMetric {
    pub id: String,
    pub label: String,
    pub value: f64,
    pub unit: Option<String>,
    pub trend: Option<String>,
    pub change_percentage: Option<f64>,
    pub target: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LswSummary {
    pub id: String,
    pub date: String,
    pub score: Option<f64>,
    pub status: String,
    pub completed_checks: Option<i32>,
    pub total_checks: Option<i32>,
    pub notes: Option<String>,
    pub safety_observations: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MicroDrill {
    pub id: String,
    pub title: String,
    pub assigned_to: Option<String>,
    pub status: String,
    pub due_date: Option<String>,
    pub drill_type: String,
    pub completed_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalPulseSummary {
    pub id: i32,
    pub message: String,
    pub severity: String,
    pub highlight_metric_name: Option<String>,
    pub highlight_metric_value: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandoverNoteSummary {
    pub id: i32,
    pub station_id: i32,
    pub severity: String,
    pub safety: String,
    pub quality: String,
    pub delivery: String,
    pub cost: String,
    pub people: String,
    pub notes: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TodayScreenData {
    pub user_id: String,
    pub user_name: String,
    pub current_date: String,
    pub greeting: String,
    pub top_priorities: Vec<TopPriority>,
    pub top_risks: HashMap<String, Vec<TopRisk>>,
    pub todays_commitments: Vec<TodaysCommitment>,
    pub abnormalities: Vec<Abnormality>,
    pub quick_metrics: Vec<QuickMetric>,
    pub lsw_summary: Option<LswSummary>,
    pub todays_micro_drills: Vec<MicroDrill>,
    pub active_pulses: Vec<GlobalPulseSummary>,
    pub active_handovers: Vec<HandoverNoteSummary>,
    pub active_risks: Option<Vec<ActiveRisk>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveRisk {
    pub id: String,
    pub title: String,
    pub severity: String,
    pub area: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompletePriorityRequest {
    pub priority_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcknowledgeAbnormalityRequest {
    pub abnormality_id: String,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct TodayApi;

impl TodayApi {
    pub async fn get_today(
        client: &ApiClient,
        user_id: &str,
        user_name: Option<&str>,
    ) -> Result<TodayScreenData, ApiError> {
        let safe_name = user_name.filter(|n| !n.trim().is_empty()).unwrap_or("User");
        client
            .get(&format!("/api/v1/today/screen/{}/{}", user_id, safe_name))
            .await
    }

    pub async fn get_priorities(client: &ApiClient) -> Result<Vec<TopPriority>, ApiError> {
        client.get("/api/v1/today/priorities").await
    }

    pub async fn get_commitments(client: &ApiClient) -> Result<Vec<TodaysCommitment>, ApiError> {
        client.get("/api/v1/today/commitments").await
    }

    pub async fn get_abnormalities(client: &ApiClient) -> Result<Vec<Abnormality>, ApiError> {
        client.get("/api/v1/today/abnormalities").await
    }

    pub async fn complete_priority(
        client: &ApiClient,
        req: &CompletePriorityRequest,
    ) -> Result<TopPriority, ApiError> {
        client.post("/api/v1/today/priorities/complete", req).await
    }

    pub async fn acknowledge_abnormality(
        client: &ApiClient,
        req: &AcknowledgeAbnormalityRequest,
    ) -> Result<Abnormality, ApiError> {
        client
            .post("/api/v1/today/abnormalities/acknowledge", req)
            .await
    }
}

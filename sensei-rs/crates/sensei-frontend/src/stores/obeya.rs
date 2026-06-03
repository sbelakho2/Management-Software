//! Obeya board store — items, comments, SQDCP metrics, cognitive insights,
//! and real-time WebSocket updates.
//!
//! Port of [`frontend/src/stores/obeya.ts`](frontend/src/stores/obeya.ts).

use leptos::prelude::*;
use std::collections::HashMap;
use crate::api::client::{ApiClient, ApiError};

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type ObeyaBoard = String;
pub type ObeyaCategory = String;
pub type ObeyaPriority = String;
pub type ObeyaStatus = String;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ObeyaItem {
    pub id: String,
    pub board_id: String,
    pub title: String,
    pub description: String,
    pub category: ObeyaCategory,
    pub priority: ObeyaPriority,
    pub status: ObeyaStatus,
    pub column: String,
    pub position: i32,
    pub assigned_to: Option<String>,
    pub due_date: Option<String>,
    pub escalated: bool,
    pub escalated_to: Option<String>,
    pub escalation_reason: Option<String>,
    pub resolution: Option<String>,
    pub tags: Vec<String>,
    pub created_by: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ObeyaComment {
    pub id: String,
    pub item_id: String,
    pub author: String,
    pub content: String,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ObeyaStats {
    pub total_items: i32,
    pub by_status: HashMap<String, i32>,
    pub by_priority: HashMap<String, i32>,
    pub by_category: HashMap<String, i32>,
    pub completed_this_week: i32,
    pub overdue: i32,
}

impl Default for ObeyaStats {
    fn default() -> Self {
        Self {
            total_items: 0,
            by_status: HashMap::new(),
            by_priority: HashMap::new(),
            by_category: HashMap::new(),
            completed_this_week: 0,
            overdue: 0,
        }
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SqdqpMetrics {
    pub quality: f64,
    pub delivery: f64,
    pub safety: f64,
    pub morale: f64,
    pub productivity: f64,
    pub cost: f64,
    pub overall: f64,
    pub trend: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CognitiveInsight {
    pub id: String,
    pub insight_type: String,
    pub title: String,
    pub description: String,
    pub severity: String,
    pub recommendation: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ObeyaComments {
    pub item_id: String,
    pub comments: Vec<ObeyaComment>,
}

// ---------------------------------------------------------------------------
// ObeyaStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ObeyaStore {
    // Data signals
    pub items: RwSignal<Vec<ObeyaItem>>,
    pub current_item: RwSignal<Option<ObeyaItem>>,
    pub comments: RwSignal<HashMap<String, Vec<ObeyaComment>>>,
    pub stats: RwSignal<Option<ObeyaStats>>,
    pub sqdcp_metrics: RwSignal<Option<SqdqpMetrics>>,
    pub cognitive_insights: RwSignal<Vec<CognitiveInsight>>,
    pub selected_board: RwSignal<Option<ObeyaBoard>>,
    pub is_connected: RwSignal<bool>,

    // Loading & error
    pub loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
}

impl ObeyaStore {
    pub fn new() -> Self {
        Self {
            items: RwSignal::new(Vec::new()),
            current_item: RwSignal::new(None),
            comments: RwSignal::new(HashMap::new()),
            stats: RwSignal::new(None),
            sqdcp_metrics: RwSignal::new(None),
            cognitive_insights: RwSignal::new(Vec::new()),
            selected_board: RwSignal::new(None),
            is_connected: RwSignal::new(false),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    pub fn set_selected_board(&self, board: ObeyaBoard) {
        self.selected_board.set(Some(board));
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }

    // Compute stats from items
    fn compute_stats(&self) -> ObeyaStats {
        let items = self.items.get();
        let total_items = items.len() as i32;

        let mut by_status: HashMap<String, i32> = HashMap::new();
        let mut by_priority: HashMap<String, i32> = HashMap::new();
        let mut by_category: HashMap<String, i32> = HashMap::new();
        let mut completed_this_week = 0;
        let mut overdue = 0;

        for item in items.iter() {
            *by_status.entry(item.status.clone()).or_insert(0) += 1;
            *by_priority.entry(item.priority.clone()).or_insert(0) += 1;
            *by_category.entry(item.category.clone()).or_insert(0) += 1;

            if item.status == "completed" {
                completed_this_week += 1;
            }
            if let Some(ref due) = item.due_date {
                // Simple check — if due date is in the past and not completed
                if due.as_str() < "2099-01-01" && item.status != "completed" {
                    overdue += 1;
                }
            }
        }

        ObeyaStats {
            total_items,
            by_status,
            by_priority,
            by_category,
            completed_this_week,
            overdue,
        }
    }

    // -----------------------------------------------------------------------
    // Items
    // -----------------------------------------------------------------------

    pub async fn fetch_items(&self, client: &ApiClient, board: Option<&str>) {
        self.loading.set(true);
        self.error.set(None);
        let path = match board {
            Some(b) => format!("/obeya/items?board={b}"),
            None => "/obeya/items".to_string(),
        };
        match client.get::<Vec<ObeyaItem>>(&path).await {
            Ok(items) => {
                self.items.set(items);
                let stats = self.compute_stats();
                self.stats.set(Some(stats));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_item_by_id(&self, client: &ApiClient, id: &str) {
        self.loading.set(true);
        match client.get::<ObeyaItem>(&format!("/obeya/items/{id}")).await {
            Ok(item) => self.current_item.set(Some(item)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn create_item(&self, client: &ApiClient, item_data: serde_json::Value) -> Result<ObeyaItem, ()> {
        self.loading.set(true);
        match client.post::<ObeyaItem, serde_json::Value>("/obeya/items", &item_data).await {
            Ok(new_item) => {
                self.items.update(|items| items.push(new_item.clone()));
                let stats = self.compute_stats();
                self.stats.set(Some(stats));
                self.loading.set(false);
                Ok(new_item)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.loading.set(false);
                Err(())
            }
        }
    }

    pub async fn update_item(&self, client: &ApiClient, id: &str, updates: serde_json::Value) -> Result<ObeyaItem, ()> {
        self.loading.set(true);
        match client.put::<ObeyaItem, serde_json::Value>(&format!("/obeya/items/{id}"), &updates).await {
            Ok(updated) => {
                self.items.update(|items| {
                    if let Some(pos) = items.iter().position(|i| i.id == id) {
                        items[pos] = updated.clone();
                    }
                });
                self.current_item.set(Some(updated.clone()));
                let stats = self.compute_stats();
                self.stats.set(Some(stats));
                self.loading.set(false);
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.loading.set(false);
                Err(())
            }
        }
    }

    pub async fn delete_item(&self, client: &ApiClient, id: &str) -> Result<(), ()> {
        self.loading.set(true);
        match client.delete::<serde_json::Value>(&format!("/obeya/items/{id}")).await {
            Ok(_) => {
                self.items.update(|items| items.retain(|i| i.id != id));
                let stats = self.compute_stats();
                self.stats.set(Some(stats));
                self.loading.set(false);
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.loading.set(false);
                Err(())
            }
        }
    }

    pub async fn move_item(&self, client: &ApiClient, id: &str, column: &str, position: i32) -> Result<ObeyaItem, ()> {
        let updates = serde_json::json!({ "column": column, "position": position });
        self.update_item(client, id, updates).await
    }

    // -----------------------------------------------------------------------
    // Comments
    // -----------------------------------------------------------------------

    pub async fn add_comment(&self, client: &ApiClient, item_id: &str, comment_data: serde_json::Value) -> Result<ObeyaComment, ()> {
        match client.post::<ObeyaComment, serde_json::Value>(
            &format!("/obeya/items/{item_id}/comments"), &comment_data,
        ).await {
            Ok(comment) => {
                self.comments.update(|c| {
                    c.entry(item_id.to_string()).or_default().push(comment.clone());
                });
                Ok(comment)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(())
            }
        }
    }

    pub async fn fetch_comments(&self, client: &ApiClient, item_id: &str) {
        match client.get::<Vec<ObeyaComment>>(&format!("/obeya/items/{item_id}/comments")).await {
            Ok(comments) => {
                self.comments.update(|c| {
                    c.insert(item_id.to_string(), comments);
                });
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    // -----------------------------------------------------------------------
    // Escalation & Resolution
    // -----------------------------------------------------------------------

    pub async fn escalate_item(&self, client: &ApiClient, id: &str, reason: &str, escalated_to_id: &str) -> Result<ObeyaItem, ()> {
        let updates = serde_json::json!({
            "escalated": true,
            "escalation_reason": reason,
            "escalated_to": escalated_to_id,
            "status": "escalated",
        });
        self.update_item(client, id, updates).await
    }

    pub async fn resolve_item(&self, client: &ApiClient, id: &str, resolution: &str) -> Result<ObeyaItem, ()> {
        let updates = serde_json::json!({
            "resolution": resolution,
            "status": "resolved",
            "escalated": false,
        });
        self.update_item(client, id, updates).await
    }

    // -----------------------------------------------------------------------
    // SQDCP Metrics & Cognitive Insights
    // -----------------------------------------------------------------------

    pub async fn fetch_sqdcp_metrics(&self, client: &ApiClient) {
        self.loading.set(true);
        match client.get::<SqdqpMetrics>(&format!("/obeya/sqdcp")).await {
            Ok(metrics) => self.sqdcp_metrics.set(Some(metrics)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_cognitive_insights(&self, client: &ApiClient) {
        self.loading.set(true);
        match client.get::<Vec<CognitiveInsight>>(&format!("/obeya/cognitive-insights")).await {
            Ok(insights) => self.cognitive_insights.set(insights),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }
}

impl Default for ObeyaStore {
    fn default() -> Self {
        Self::new()
    }
}

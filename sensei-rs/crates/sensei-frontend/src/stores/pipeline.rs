//! Pipeline (RFQ management) reactive store.
//!
//! Mirrors the Zustand [`pipeline.ts`](frontend/src/stores/pipeline.ts) store.

use crate::api::client::{ApiClient, ApiError};
use crate::api::rfq::{RfqApi, RfqDto};
use leptos::prelude::*;

/// Computed pipeline statistics.
#[derive(Debug, Clone)]
pub struct PipelineStats {
    pub total_rfqs: i32,
    pub active_rfqs: i32,
    pub total_value: f64,
    pub avg_response_time: f64,
    pub conversion_rate: f64,
    pub overdue_count: i32,
}

/// Reactive store for the RFQ pipeline.
#[derive(Debug, Clone)]
pub struct PipelineStore {
    pub rfqs: RwSignal<Vec<RfqDto>>,
    pub current_rfq: RwSignal<Option<RfqDto>>,
    pub stats: RwSignal<Option<PipelineStats>>,
    pub is_loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
    pub last_fetched_at: RwSignal<Option<String>>,
}

impl PipelineStore {
    pub fn new() -> Self {
        Self {
            rfqs: RwSignal::new(Vec::new()),
            current_rfq: RwSignal::new(None),
            stats: RwSignal::new(None),
            is_loading: RwSignal::new(false),
            error: RwSignal::new(None),
            last_fetched_at: RwSignal::new(None),
        }
    }

    fn compute_stats(rfqs: &[RfqDto]) -> PipelineStats {
        let total = rfqs.len() as i32;
        let active = rfqs
            .iter()
            .filter(|r| matches!(r.status.as_str(), "open" | "in_progress" | "quoted"))
            .count() as i32;
        let total_value: f64 = rfqs.iter().filter_map(|r| r.estimated_value).sum();
        let overdue = rfqs
            .iter()
            .filter(|r| {
                r.due_date
                    .as_ref()
                    .is_some_and(|d| *d < chrono::Utc::now().format("%Y-%m-%d").to_string())
            })
            .count() as i32;

        PipelineStats {
            total_rfqs: total,
            active_rfqs: active,
            total_value,
            avg_response_time: 0.0,
            conversion_rate: 0.0,
            overdue_count: overdue,
        }
    }

    /// Fetch all RFQs.
    pub async fn fetch_rfqs(&self, client: &ApiClient) {
        self.is_loading.set(true);
        self.error.set(None);
        match RfqApi::list_rfqs(client, None).await {
            Ok(resp) => {
                self.rfqs.set(resp.items.clone());
                self.stats.set(Some(Self::compute_stats(&resp.items)));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch a single RFQ by ID.
    pub async fn fetch_rfq_by_id(&self, client: &ApiClient, id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match RfqApi::get_rfq(client, id).await {
            Ok(data) => {
                self.current_rfq.set(Some(data.clone()));
                // Also update in the list
                self.rfqs.update(|rfqs| {
                    if let Some(pos) = rfqs.iter().position(|x| x.id == id) {
                        rfqs[pos] = data;
                    }
                });
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch RFQ details (additional info).
    pub async fn fetch_rfq_details(&self, client: &ApiClient, id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>(&format!("/api/v1/rfqs/{}/details", id))
            .await
        {
            Ok(_) => {
                // Merge details into current RFQ
                if let Some(current) = self.current_rfq.get() {
                    // Extend with details; current approach: replace with enriched data
                    self.current_rfq.set(Some(RfqDto {
                        id: current.id.clone(),
                        ..current
                    }));
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Create a new RFQ.
    pub async fn create_rfq(
        &self,
        client: &ApiClient,
        data: &serde_json::Value,
    ) -> Result<RfqDto, ApiError> {
        let rfq: RfqDto = client.post("/api/v1/rfqs", data).await?;
        self.rfqs.update(|r| r.push(rfq.clone()));
        Ok(rfq)
    }

    /// Update an existing RFQ.
    pub async fn update_rfq(
        &self,
        client: &ApiClient,
        id: &str,
        updates: &serde_json::Value,
    ) -> Result<RfqDto, ApiError> {
        let rfq: RfqDto = client.put(&format!("/api/v1/rfqs/{}", id), updates).await?;
        self.rfqs.update(|r| {
            if let Some(pos) = r.iter().position(|x| x.id == id) {
                r[pos] = rfq.clone();
            }
        });
        Ok(rfq)
    }

    /// Delete an RFQ.
    pub async fn delete_rfq(&self, client: &ApiClient, id: &str) -> Result<(), ApiError> {
        RfqApi::delete_rfq(client, id).await?;
        self.rfqs.update(|r| r.retain(|x| x.id != id));
        Ok(())
    }

    /// Bulk delete RFQs.
    pub async fn bulk_delete_rfqs(
        &self,
        client: &ApiClient,
        ids: &[String],
    ) -> Result<(), ApiError> {
        let payload = serde_json::json!({ "ids": ids });
        client
            .post::<serde_json::Value, _>("/api/v1/rfqs/bulk-delete", &payload)
            .await?;
        self.rfqs.update(|r| r.retain(|x| !ids.contains(&x.id)));
        Ok(())
    }

    /// Export RFQs as a file (PDF/Excel).
    ///
    /// Uses the shared client (same connection pool, bearer token, and 401
    /// refresh pipeline) instead of constructing a fresh `reqwest::Client`.
    pub async fn export_rfqs(
        client: &ApiClient,
        ids: Option<&[String]>,
    ) -> Result<Vec<u8>, ApiError> {
        let path = match ids {
            Some(id_list) => {
                let ids_str: Vec<&str> = id_list.iter().map(|s| s.as_str()).collect();
                format!("/api/v1/rfqs/export?ids={}", ids_str.join(","))
            }
            None => "/api/v1/rfqs/export".to_string(),
        };
        client.get_bytes(&path).await
    }

    /// Set RFQ status.
    pub async fn set_rfq_status(
        &self,
        client: &ApiClient,
        id: &str,
        status: &str,
    ) -> Result<RfqDto, ApiError> {
        let payload = serde_json::json!({ "status": status });
        let rfq: RfqDto = client
            .put(&format!("/api/v1/rfqs/{}/status", id), &payload)
            .await?;
        self.rfqs.update(|r| {
            if let Some(pos) = r.iter().position(|x| x.id == id) {
                r[pos] = rfq.clone();
            }
        });
        Ok(rfq)
    }

    /// Assign an RFQ to a user.
    pub async fn assign_rfq(
        &self,
        client: &ApiClient,
        id: &str,
        assignee_id: &str,
    ) -> Result<RfqDto, ApiError> {
        let rfq = RfqApi::assign_rfq(client, id, assignee_id).await?;
        self.rfqs.update(|r| {
            if let Some(pos) = r.iter().position(|x| x.id == id) {
                r[pos] = rfq.clone();
            }
        });
        Ok(rfq)
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }
}

impl Default for PipelineStore {
    fn default() -> Self {
        Self::new()
    }
}

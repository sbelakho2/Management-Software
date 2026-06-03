//! Quoting Helper reactive store.
//!
//! Mirrors the Zustand [`quoting-helper.ts`](frontend/src/stores/quoting-helper.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// A work packet for quoting.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkPacketDto {
    pub id: String,
    pub rfq_id: String,
    pub title: String,
    pub description: Option<String>,
    pub estimated_hours: Option<f64>,
    pub hourly_rate: Option<f64>,
    pub material_cost: Option<f64>,
    pub total_cost: Option<f64>,
    pub status: Option<String>,
    pub created_at: Option<String>,
}

/// Reactive store for quoting helper data.
#[derive(Debug, Clone)]
pub struct QuotingHelperStore {
    /// Work packets for the current RFQ.
    pub work_packets: RwSignal<Vec<WorkPacketDto>>,
    /// Clarifications for the current RFQ.
    pub clarifications: RwSignal<Vec<serde_json::Value>>,
    /// Quote memory / historical data.
    pub quote_memory: RwSignal<Option<serde_json::Value>>,
    /// Whether a fetch is in flight.
    pub is_loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl QuotingHelperStore {
    pub fn new() -> Self {
        Self {
            work_packets: RwSignal::new(Vec::new()),
            clarifications: RwSignal::new(Vec::new()),
            quote_memory: RwSignal::new(None),
            is_loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch work packets for an RFQ.
    pub async fn fetch_work_packets(&self, client: &ApiClient, rfq_id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<WorkPacketDto>>(&format!("/api/v1/quoting/work-packets/{}", rfq_id))
            .await
        {
            Ok(data) => self.work_packets.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Generate work packets for an RFQ.
    pub async fn generate_work_packets(
        &self,
        client: &ApiClient,
        rfq_id: &str,
    ) -> Result<Vec<WorkPacketDto>, ApiError> {
        let packets: Vec<WorkPacketDto> = client
            .post(&format!("/api/v1/quoting/generate/{}", rfq_id), &serde_json::json!({}))
            .await?;
        self.work_packets.set(packets.clone());
        Ok(packets)
    }

    /// Update a work packet.
    pub async fn update_work_packet(
        &self,
        client: &ApiClient,
        packet_id: &str,
        data: &serde_json::Value,
    ) -> Result<WorkPacketDto, ApiError> {
        let packet: WorkPacketDto = client
            .put(&format!("/api/v1/quoting/work-packets/{}", packet_id), data)
            .await?;
        self.work_packets.update(|p| {
            if let Some(pos) = p.iter().position(|x| x.id == packet_id) {
                p[pos] = packet.clone();
            }
        });
        Ok(packet)
    }

    /// Calculate cost for a quote.
    pub async fn calculate_cost(
        &self,
        client: &ApiClient,
        quote_id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client
            .post(&format!("/api/v1/quoting/calculate/{}", quote_id), &serde_json::json!({}))
            .await
    }

    /// Fetch clarifications for an RFQ.
    pub async fn fetch_clarifications(&self, client: &ApiClient, rfq_id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<serde_json::Value>>(&format!("/api/v1/quoting/clarifications/{}", rfq_id))
            .await
        {
            Ok(data) => self.clarifications.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch quote memory for an RFQ.
    pub async fn fetch_quote_memory(&self, client: &ApiClient, rfq_id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>(&format!("/api/v1/quoting/memory/{}", rfq_id))
            .await
        {
            Ok(data) => self.quote_memory.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Convert a quote to an NPI (New Product Introduction).
    pub async fn convert_to_npi(
        &self,
        client: &ApiClient,
        quote_id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client
            .post(&format!("/api/v1/quoting/convert-to-npi/{}", quote_id), &serde_json::json!({}))
            .await
    }
}

impl Default for QuotingHelperStore {
    fn default() -> Self {
        Self::new()
    }
}

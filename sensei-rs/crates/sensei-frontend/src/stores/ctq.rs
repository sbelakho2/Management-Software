//! CTQ (Critical-to-Quality) reactive store.
//!
//! Mirrors the Zustand [`ctq.ts`](frontend/src/stores/ctq.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A CTQ measurement data point.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CtqMeasurementDto {
    pub id: String,
    pub ctq_id: String,
    pub value: f64,
    pub measured_at: String,
    pub measured_by: Option<String>,
    pub notes: Option<String>,
}

/// A Critical-to-Quality metric.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CtqDto {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub category: Option<String>,
    pub unit: Option<String>,
    pub target: Option<f64>,
    pub upper_spec_limit: Option<f64>,
    pub lower_spec_limit: Option<f64>,
    pub status: String,
    pub measurements: Option<Vec<CtqMeasurementDto>>,
    pub created_at: Option<String>,
}

/// CTQ statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CtqStatsDto {
    pub total_ctqs: i32,
    pub on_target: i32,
    pub out_of_spec: i32,
    pub needing_attention: i32,
    pub avg_cpk: f64,
    pub measured_today: i32,
    pub by_category: HashMap<String, i32>,
}

/// Reactive store for CTQ data.
#[derive(Debug, Clone)]
pub struct CtqStore {
    pub ctqs: RwSignal<Vec<CtqDto>>,
    pub stats: RwSignal<Option<CtqStatsDto>>,
    pub is_loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
    pub last_fetched_at: RwSignal<Option<String>>,
}

const CACHE_DURATION_MS: u64 = 30_000; // 30 seconds

impl CtqStore {
    pub fn new() -> Self {
        Self {
            ctqs: RwSignal::new(Vec::new()),
            stats: RwSignal::new(None),
            is_loading: RwSignal::new(false),
            error: RwSignal::new(None),
            last_fetched_at: RwSignal::new(None),
        }
    }

    fn is_cache_valid(&self) -> bool {
        if let Some(ts) = self.last_fetched_at.get() {
            if let Ok(parsed) = chrono::DateTime::parse_from_rfc3339(&ts) {
                let elapsed = chrono::Utc::now()
                    .signed_duration_since(parsed.with_timezone(&chrono::Utc))
                    .num_milliseconds() as u64;
                return elapsed < CACHE_DURATION_MS;
            }
        }
        false
    }

    /// Fetch all CTQs with stats (cached).
    pub async fn fetch_ctqs(&self, client: &ApiClient) {
        if self.is_cache_valid() {
            return;
        }
        self.is_loading.set(true);
        self.error.set(None);

        // Fetch CTQs
        match client.get::<Vec<CtqDto>>("/api/v1/ctq").await {
            Ok(data) => {
                self.ctqs.set(data.clone());
                // Compute stats locally
                let total = data.len() as i32;
                let on_target = data.iter().filter(|c| c.status == "on_target").count() as i32;
                let out_of_spec = data.iter().filter(|c| c.status == "out_of_spec").count() as i32;
                let needing_attention = data.iter().filter(|c| c.status == "attention").count() as i32;
                let measured_today = data
                    .iter()
                    .filter(|c| {
                        c.measurements.as_ref().map_or(false, |m| {
                            m.iter().any(|meas| {
                                meas.measured_at.starts_with(
                                    &chrono::Utc::now().format("%Y-%m-%d").to_string(),
                                )
                            })
                        })
                    })
                    .count() as i32;
                let mut by_category = HashMap::new();
                for ctq in &data {
                    if let Some(ref cat) = ctq.category {
                        *by_category.entry(cat.clone()).or_insert(0) += 1;
                    }
                }
                self.stats.set(Some(CtqStatsDto {
                    total_ctqs: total,
                    on_target,
                    out_of_spec,
                    needing_attention,
                    avg_cpk: 0.0, // Would need historical data to compute
                    measured_today,
                    by_category,
                }));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.last_fetched_at.set(Some(chrono::Utc::now().to_rfc3339()));
        self.is_loading.set(false);
    }

    /// Fetch a single CTQ by ID.
    pub async fn fetch_ctq_by_id(&self, client: &ApiClient, id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match client.get::<CtqDto>(&format!("/api/v1/ctq/{}", id)).await {
            Ok(data) => {
                self.ctqs.update(|ctqs| {
                    if let Some(pos) = ctqs.iter().position(|x| x.id == id) {
                        ctqs[pos] = data;
                    } else {
                        ctqs.push(data);
                    }
                });
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Create a new CTQ.
    pub async fn create_ctq(&self, client: &ApiClient, data: &serde_json::Value) -> Result<CtqDto, ApiError> {
        let ctq: CtqDto = client.post("/api/v1/ctq", data).await?;
        self.ctqs.update(|c| c.push(ctq.clone()));
        Ok(ctq)
    }

    /// Update an existing CTQ.
    pub async fn update_ctq(&self, client: &ApiClient, id: &str, updates: &serde_json::Value) -> Result<CtqDto, ApiError> {
        let ctq: CtqDto = client.put(&format!("/api/v1/ctq/{}", id), updates).await?;
        self.ctqs.update(|c| {
            if let Some(pos) = c.iter().position(|x| x.id == id) {
                c[pos] = ctq.clone();
            }
        });
        Ok(ctq)
    }

    /// Delete a CTQ.
    pub async fn delete_ctq(&self, client: &ApiClient, id: &str) -> Result<(), ApiError> {
        client.delete::<serde_json::Value>(&format!("/api/v1/ctq/{}", id)).await?;
        self.ctqs.update(|c| c.retain(|x| x.id != id));
        Ok(())
    }

    /// Add a measurement to a CTQ.
    pub async fn add_measurement(
        &self,
        client: &ApiClient,
        ctq_id: &str,
        data: &serde_json::Value,
    ) -> Result<CtqMeasurementDto, ApiError> {
        let measurement: CtqMeasurementDto =
            client.post(&format!("/api/v1/ctq/{}/measurements", ctq_id), data).await?;
        self.ctqs.update(|c| {
            if let Some(ctq) = c.iter_mut().find(|x| x.id == ctq_id) {
                ctq.measurements.get_or_insert(Vec::new()).push(measurement.clone());
            }
        });
        Ok(measurement)
    }

    /// Export CTQs as PDF or Excel.
    pub async fn export_ctqs(
        client: &ApiClient,
        format: &str,
    ) -> Result<Vec<u8>, ApiError> {
        let client_inner = reqwest::Client::new();
        let url = client.url(&format!("/api/v1/ctq/export?format={}", format));
        let resp = client_inner.get(&url).send().await.map_err(|e| ApiError::Http(e.to_string()))?;
        let bytes = resp.bytes().await.map_err(|e| ApiError::Http(e.to_string()))?;
        Ok(bytes.to_vec())
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }
}

impl Default for CtqStore {
    fn default() -> Self {
        Self::new()
    }
}

//! Exceptions (operational issues / escalations) reactive store.
//!
//! Mirrors the Zustand [`exceptions.ts`](frontend/src/stores/exceptions.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// An operational exception.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExceptionDto {
    pub id: String,
    pub title: String,
    pub description: String,
    pub severity: String,
    pub status: String,
    pub category: Option<String>,
    pub source: Option<String>,
    pub owner: Option<String>,
    pub assigned_to: Option<String>,
    pub escalated_to: Option<String>,
    pub resolution_notes: Option<String>,
    pub created_at: String,
    pub updated_at: Option<String>,
}

/// Exception trend data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExceptionTrendDto {
    pub date: String,
    pub count: i32,
    pub by_severity: HashMap<String, i32>,
    pub by_category: HashMap<String, i32>,
}

/// Exception statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExceptionStatsDto {
    pub total: i32,
    pub open: i32,
    pub acknowledged: i32,
    pub escalated: i32,
    pub resolved: i32,
    pub avg_resolution_time_hours: f64,
}

/// Reactive store for exceptions.
#[derive(Debug, Clone)]
pub struct ExceptionsStore {
    pub exceptions: RwSignal<Vec<ExceptionDto>>,
    pub trends: RwSignal<Vec<ExceptionTrendDto>>,
    pub stats: RwSignal<Option<ExceptionStatsDto>>,
    pub loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
}

impl ExceptionsStore {
    pub fn new() -> Self {
        Self {
            exceptions: RwSignal::new(Vec::new()),
            trends: RwSignal::new(Vec::new()),
            stats: RwSignal::new(None),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch exceptions with optional filters.
    pub async fn fetch_exceptions(&self, client: &ApiClient, filters: &HashMap<String, String>) {
        self.loading.set(true);
        self.error.set(None);
        let mut query = Vec::new();
        for (k, v) in filters {
            query.push(format!("{}={}", k, v));
        }
        let path = if query.is_empty() {
            "/api/v1/exceptions".to_string()
        } else {
            format!("/api/v1/exceptions?{}", query.join("&"))
        };
        match client.get::<Vec<ExceptionDto>>(&path).await {
            Ok(data) => self.exceptions.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch a single exception by ID.
    pub async fn fetch_exception_by_id(&self, client: &ApiClient, id: &str) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<ExceptionDto>(&format!("/api/v1/exceptions/{}", id))
            .await
        {
            Ok(data) => {
                self.exceptions.update(|excs| {
                    if let Some(pos) = excs.iter().position(|x| x.id == id) {
                        excs[pos] = data;
                    } else {
                        excs.push(data);
                    }
                });
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Acknowledge an exception.
    pub async fn acknowledge_exception(
        &self,
        client: &ApiClient,
        id: &str,
    ) -> Result<ExceptionDto, ApiError> {
        let exc: ExceptionDto = client
            .post(
                &format!("/api/v1/exceptions/{}/acknowledge", id),
                &serde_json::json!({}),
            )
            .await?;
        self.exceptions.update(|excs| {
            if let Some(pos) = excs.iter().position(|x| x.id == id) {
                excs[pos] = exc.clone();
            }
        });
        Ok(exc)
    }

    /// Escalate an exception.
    pub async fn escalate_exception(
        &self,
        client: &ApiClient,
        id: &str,
        escalate_to: &str,
        reason: &str,
    ) -> Result<ExceptionDto, ApiError> {
        let payload = serde_json::json!({
            "escalated_to": escalate_to,
            "reason": reason,
        });
        let exc: ExceptionDto = client
            .post(&format!("/api/v1/exceptions/{}/escalate", id), &payload)
            .await?;
        self.exceptions.update(|excs| {
            if let Some(pos) = excs.iter().position(|x| x.id == id) {
                excs[pos] = exc.clone();
            }
        });
        Ok(exc)
    }

    /// Resolve an exception.
    pub async fn resolve_exception(
        &self,
        client: &ApiClient,
        id: &str,
        resolution_notes: &str,
    ) -> Result<ExceptionDto, ApiError> {
        let payload = serde_json::json!({ "resolution_notes": resolution_notes });
        let exc: ExceptionDto = client
            .post(&format!("/api/v1/exceptions/{}/resolve", id), &payload)
            .await?;
        self.exceptions.update(|excs| {
            if let Some(pos) = excs.iter().position(|x| x.id == id) {
                excs[pos] = exc.clone();
            }
        });
        Ok(exc)
    }

    /// Assign an exception to an owner.
    pub async fn assign_exception(
        &self,
        client: &ApiClient,
        id: &str,
        owner_id: &str,
    ) -> Result<ExceptionDto, ApiError> {
        let payload = serde_json::json!({ "owner_id": owner_id });
        let exc: ExceptionDto = client
            .post(&format!("/api/v1/exceptions/{}/assign", id), &payload)
            .await?;
        self.exceptions.update(|excs| {
            if let Some(pos) = excs.iter().position(|x| x.id == id) {
                excs[pos] = exc.clone();
            }
        });
        Ok(exc)
    }

    /// Add a comment to an exception.
    pub async fn add_comment(
        &self,
        client: &ApiClient,
        id: &str,
        comment: &str,
    ) -> Result<serde_json::Value, ApiError> {
        let payload = serde_json::json!({ "comment": comment });
        client
            .post(&format!("/api/v1/exceptions/{}/comments", id), &payload)
            .await
    }

    /// Fetch exception trends.
    pub async fn fetch_trends(&self, client: &ApiClient, days: i32) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<ExceptionTrendDto>>(&format!("/api/v1/exceptions/trends?days={}", days))
            .await
        {
            Ok(data) => self.trends.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch exception stats.
    pub async fn fetch_stats(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<ExceptionStatsDto>("/api/v1/exceptions/stats")
            .await
        {
            Ok(data) => self.stats.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }
}

impl Default for ExceptionsStore {
    fn default() -> Self {
        Self::new()
    }
}

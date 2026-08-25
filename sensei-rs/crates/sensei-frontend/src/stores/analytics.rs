//! Analytics reactive store.
//!
//! Mirrors the Zustand [`analytics.ts`](frontend/src/stores/analytics.ts) store.

use crate::api::client::ApiClient;
use leptos::prelude::*;

/// Reactive store for analytics data.
#[derive(Debug, Clone)]
pub struct AnalyticsStore {
    /// Insights data.
    pub insights: RwSignal<Option<serde_json::Value>>,
    /// Trends data.
    pub trends: RwSignal<Option<serde_json::Value>>,
    /// System health data.
    pub health: RwSignal<Option<serde_json::Value>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl AnalyticsStore {
    pub fn new() -> Self {
        Self {
            insights: RwSignal::new(None),
            trends: RwSignal::new(None),
            health: RwSignal::new(None),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch analytics insights.
    pub async fn fetch_insights(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/analytics/insights")
            .await
        {
            Ok(data) => {
                self.insights.set(Some(data));
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }

    /// Fetch analytics trends.
    pub async fn fetch_trends(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/analytics/trends")
            .await
        {
            Ok(data) => {
                self.trends.set(Some(data));
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }

    /// Fetch system health.
    pub async fn fetch_health(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/analytics/health")
            .await
        {
            Ok(data) => {
                self.health.set(Some(data));
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }
}

impl Default for AnalyticsStore {
    fn default() -> Self {
        Self::new()
    }
}

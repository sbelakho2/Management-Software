//! IT Monitoring reactive store.
//!
//! Mirrors the Zustand [`it-monitoring.ts`](frontend/src/stores/it-monitoring.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;

/// Reactive store for IT monitoring data.
#[derive(Debug, Clone)]
pub struct ItMonitoringStore {
    /// System health overview.
    pub system_health: RwSignal<Option<serde_json::Value>>,
    /// Server statistics.
    pub server_stats: RwSignal<Option<serde_json::Value>>,
    /// Service statuses.
    pub services: RwSignal<Vec<serde_json::Value>>,
    /// IT alerts.
    pub alerts: RwSignal<Vec<serde_json::Value>>,
    /// Active user counts.
    pub active_users: RwSignal<Option<serde_json::Value>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
    /// Timestamp of last full fetch (for cache expiry).
    pub last_fetched_at: RwSignal<Option<String>>,
}

const CACHE_DURATION_MS: u64 = 15_000; // 15 seconds

impl ItMonitoringStore {
    pub fn new() -> Self {
        Self {
            system_health: RwSignal::new(None),
            server_stats: RwSignal::new(None),
            services: RwSignal::new(Vec::new()),
            alerts: RwSignal::new(Vec::new()),
            active_users: RwSignal::new(None),
            loading: RwSignal::new(false),
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

    /// Fetch all monitoring data at once (with caching).
    pub async fn fetch_all(&self, client: &ApiClient) {
        if self.is_cache_valid() {
            return;
        }
        self.loading.set(true);
        self.error.set(None);

        // Fetch all endpoints concurrently
        let health = client
            .get::<serde_json::Value>("/api/v1/monitoring/health")
            .await;
        let stats = client
            .get::<serde_json::Value>("/api/v1/monitoring/server-stats")
            .await;
        let svcs = client
            .get::<Vec<serde_json::Value>>("/api/v1/monitoring/services")
            .await;
        let alrts = client
            .get::<Vec<serde_json::Value>>("/api/v1/monitoring/alerts")
            .await;
        let users = client
            .get::<serde_json::Value>("/api/v1/monitoring/active-users")
            .await;

        if let Ok(ref h) = health {
            self.system_health.set(Some(h.clone()));
        }
        if let Ok(ref s) = stats {
            self.server_stats.set(Some(s.clone()));
        }
        if let Ok(ref s) = svcs {
            self.services.set(s.clone());
        }
        if let Ok(ref a) = alrts {
            self.alerts.set(a.clone());
        }
        if let Ok(ref u) = users {
            self.active_users.set(Some(u.clone()));
        }

        // Collect errors from any failed fetches
        let errors: Vec<String> = [
            health.as_ref().err(),
            stats.as_ref().err(),
            svcs.as_ref().err(),
            alrts.as_ref().err(),
            users.as_ref().err(),
        ]
        .iter()
        .filter_map(|r| *r)
        .map(|e| e.to_string())
        .collect();

        if !errors.is_empty() {
            self.error.set(Some(errors.join("; ")));
        }

        self.last_fetched_at
            .set(Some(chrono::Utc::now().to_rfc3339()));
        self.loading.set(false);
    }

    /// Fetch system health only.
    pub async fn fetch_system_health(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/monitoring/health")
            .await
        {
            Ok(data) => self.system_health.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch server stats only.
    pub async fn fetch_server_stats(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/monitoring/server-stats")
            .await
        {
            Ok(data) => self.server_stats.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch services only.
    pub async fn fetch_services(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<serde_json::Value>>("/api/v1/monitoring/services")
            .await
        {
            Ok(data) => self.services.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch alerts.
    pub async fn fetch_alerts(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<serde_json::Value>>("/api/v1/monitoring/alerts")
            .await
        {
            Ok(data) => self.alerts.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch active user data.
    pub async fn fetch_active_users(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/monitoring/active-users")
            .await
        {
            Ok(data) => self.active_users.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Clear the cache (force refetch on next call).
    pub fn clear_cache(&self) {
        self.last_fetched_at.set(None);
    }

    /// Restart a service by name.
    pub async fn restart_service(
        &self,
        client: &ApiClient,
        service_name: &str,
    ) -> Result<serde_json::Value, ApiError> {
        let payload = serde_json::json!({ "service": service_name });
        client.post("/api/v1/monitoring/restart", &payload).await
    }
}

impl Default for ItMonitoringStore {
    fn default() -> Self {
        Self::new()
    }
}

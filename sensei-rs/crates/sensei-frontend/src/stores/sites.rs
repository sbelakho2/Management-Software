//! Sites (facilities / locations) reactive store.
//!
//! Mirrors the Zustand [`sites.ts`](frontend/src/stores/sites.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A site/facility DTO matching the backend API response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SiteDto {
    pub id: String,
    pub name: String,
    pub code: Option<String>,
    pub address: Option<String>,
    pub city: Option<String>,
    pub country: Option<String>,
    pub timezone: Option<String>,
    pub is_active: bool,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

/// Reactive store for sites data.
#[derive(Debug, Clone)]
pub struct SitesStore {
    /// List of sites.
    pub sites: RwSignal<Vec<SiteDto>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl SitesStore {
    pub fn new() -> Self {
        Self {
            sites: RwSignal::new(Vec::new()),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch all sites.
    pub async fn fetch_sites(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<SiteDto>>("/api/v1/sites").await {
            Ok(sites) => {
                self.sites.set(sites);
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }

    /// Create a new site.
    pub async fn create_site(
        &self,
        client: &ApiClient,
        payload: &serde_json::Value,
    ) -> Result<SiteDto, ApiError> {
        let site: SiteDto = client.post("/api/v1/sites", payload).await?;
        self.sites.update(|s| s.push(site.clone()));
        Ok(site)
    }

    /// Update an existing site.
    pub async fn update_site(
        &self,
        client: &ApiClient,
        id: &str,
        payload: &serde_json::Value,
    ) -> Result<SiteDto, ApiError> {
        let site: SiteDto = client
            .put(&format!("/api/v1/sites/{}", id), payload)
            .await?;
        self.sites.update(|s| {
            if let Some(pos) = s.iter().position(|x| x.id == id) {
                s[pos] = site.clone();
            }
        });
        Ok(site)
    }
}

impl Default for SitesStore {
    fn default() -> Self {
        Self::new()
    }
}

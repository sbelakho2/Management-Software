//! Today screen reactive store — item 30: consumes the REAL backend
//! `/api/v1/today` snapshot (server-scoped, site-timezone).

use crate::api::client::ApiClient;
use crate::api::today::{get_today_snapshot, TodaySnapshot};
use leptos::prelude::*;

/// Reactive store for the Today snapshot.
#[derive(Debug, Clone)]
pub struct TodayStore {
    /// The fetched Today snapshot.
    pub data: RwSignal<Option<TodaySnapshot>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl TodayStore {
    pub fn new() -> Self {
        Self {
            data: RwSignal::new(None),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch the server-generated Today snapshot.
    pub async fn fetch_today(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match get_today_snapshot(client).await {
            Ok(data) => {
                self.data.set(Some(data));
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }
}

impl Default for TodayStore {
    fn default() -> Self {
        Self::new()
    }
}

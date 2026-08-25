//! Today screen reactive store.
//!
//! Mirrors the Zustand [`today.ts`](frontend/src/stores/today.ts) store.

use crate::api::client::ApiClient;
use crate::api::today::{TodayApi, TodayScreenData};
use leptos::prelude::*;

/// Reactive store for today screen data.
#[derive(Debug, Clone)]
pub struct TodayStore {
    /// The fetched today screen data.
    pub data: RwSignal<Option<TodayScreenData>>,
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

    /// Fetch the today screen for a given user.
    pub async fn fetch_today_screen(
        &self,
        client: &ApiClient,
        user_id: &str,
        user_name: Option<&str>,
    ) {
        self.loading.set(true);
        self.error.set(None);
        match TodayApi::get_today(client, user_id, user_name).await {
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

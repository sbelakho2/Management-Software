//! Quotes reactive store.
//!
//! Mirrors the Zustand [`quotes.ts`](frontend/src/stores/quotes.ts) store.

use crate::api::client::{ApiClient, ApiError};
use crate::api::rfq::{QuoteApi, QuoteDto, QuoteStats};
use leptos::prelude::*;
use std::collections::HashMap;

/// Reactive store for quotes.
#[derive(Debug, Clone)]
pub struct QuotesStore {
    pub quotes: RwSignal<Vec<QuoteDto>>,
    pub stats: RwSignal<Option<QuoteStats>>,
    pub is_loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
    pub last_fetched_at: RwSignal<Option<String>>,
}

const CACHE_DURATION_MS: u64 = 30_000; // 30 seconds

impl QuotesStore {
    pub fn new() -> Self {
        Self {
            quotes: RwSignal::new(Vec::new()),
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

    /// Fetch all quotes (cached).
    pub async fn fetch_quotes(&self, client: &ApiClient) {
        if self.is_cache_valid() {
            return;
        }
        self.is_loading.set(true);
        self.error.set(None);
        match QuoteApi::list_quotes(client, None).await {
            Ok(resp) => {
                self.quotes.set(resp.items.clone());
                self.last_fetched_at.set(Some(chrono::Utc::now().to_rfc3339()));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch a single quote by ID.
    pub async fn fetch_quote_by_id(&self, client: &ApiClient, id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match QuoteApi::get_quote(client, id).await {
            Ok(data) => {
                self.quotes.update(|q| {
                    if let Some(pos) = q.iter().position(|x| x.id == id) {
                        q[pos] = data;
                    } else {
                        q.push(data);
                    }
                });
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Create a new quote.
    pub async fn create_quote(&self, client: &ApiClient, data: &serde_json::Value) -> Result<QuoteDto, ApiError> {
        let quote: QuoteDto = client.post("/api/v1/quotes", data).await?;
        self.quotes.update(|q| q.push(quote.clone()));
        Ok(quote)
    }

    /// Update an existing quote.
    pub async fn update_quote(&self, client: &ApiClient, id: &str, updates: &serde_json::Value) -> Result<QuoteDto, ApiError> {
        let quote: QuoteDto = client.put(&format!("/api/v1/quotes/{}", id), updates).await?;
        self.quotes.update(|q| {
            if let Some(pos) = q.iter().position(|x| x.id == id) {
                q[pos] = quote.clone();
            }
        });
        Ok(quote)
    }

    /// Delete a quote.
    pub async fn delete_quote(&self, client: &ApiClient, id: &str) -> Result<(), ApiError> {
        QuoteApi::delete_quote(client, id).await?;
        self.quotes.update(|q| q.retain(|x| x.id != id));
        Ok(())
    }

    /// Export a quote as PDF or Excel.
    pub async fn export_quote(
        client: &ApiClient,
        id: &str,
        format: &str,
    ) -> Result<Vec<u8>, ApiError> {
        let req_client = reqwest::Client::new();
        let url = client.url(&format!("/api/v1/quotes/{}/export?format={}", id, format));
        let resp = req_client
            .get(&url)
            .send()
            .await
            .map_err(|e| ApiError::Http(e.to_string()))?;
        let bytes = resp
            .bytes()
            .await
            .map_err(|e| ApiError::Http(e.to_string()))?;
        Ok(bytes.to_vec())
    }

    /// Send a quote to a customer.
    pub async fn send_quote(&self, client: &ApiClient, id: &str) -> Result<QuoteDto, ApiError> {
        let quote = QuoteApi::send_quote(client, id, None).await?;
        self.quotes.update(|q| {
            if let Some(pos) = q.iter().position(|x| x.id == id) {
                q[pos] = quote.clone();
            }
        });
        Ok(quote)
    }

    /// Approve a quote.
    pub async fn approve_quote(&self, client: &ApiClient, id: &str, rationale: &str) -> Result<QuoteDto, ApiError> {
        let quote = QuoteApi::approve_quote(client, id, Some(rationale)).await?;
        self.quotes.update(|q| {
            if let Some(pos) = q.iter().position(|x| x.id == id) {
                q[pos] = quote.clone();
            }
        });
        Ok(quote)
    }

    /// Reject a quote.
    pub async fn reject_quote(&self, client: &ApiClient, id: &str, reason: &str) -> Result<QuoteDto, ApiError> {
        let quote = QuoteApi::reject_quote(client, id, reason).await?;
        self.quotes.update(|q| {
            if let Some(pos) = q.iter().position(|x| x.id == id) {
                q[pos] = quote.clone();
            }
        });
        Ok(quote)
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }
}

impl Default for QuotesStore {
    fn default() -> Self {
        Self::new()
    }
}

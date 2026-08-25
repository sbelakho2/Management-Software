//! Currency exchange rate reactive store.
//!
//! Mirrors the Zustand [`currency-store.ts`](frontend/src/stores/currency-store.ts) store.

use leptos::prelude::*;
use std::collections::HashMap;

/// Supported currency codes.
pub type CurrencyCode = String;

/// Exchange rates map (target currency -> rate relative to base).
pub type ExchangeRates = HashMap<String, f64>;

/// Supported currencies with metadata.
pub const CURRENCIES: &[&str] = &[
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR", "MAD", "BRL", "MXN", "SEK",
    "NOK", "DKK", "NZD", "KRW", "SGD", "HKD", "TRY", "ZAR", "PLN", "THB", "ILS", "AED",
];

/// Reactive store for currency exchange rate data.
#[derive(Debug, Clone)]
pub struct CurrencyStore {
    /// The currency used for display.
    pub display_currency: RwSignal<CurrencyCode>,
    /// The base currency for rate conversions.
    pub base_currency: RwSignal<CurrencyCode>,
    /// Exchange rates (target -> rate).
    pub rates: RwSignal<ExchangeRates>,
    /// Whether rates are being fetched.
    pub is_loading: RwSignal<bool>,
    /// Timestamp of last successful fetch.
    pub last_fetched: RwSignal<Option<String>>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl CurrencyStore {
    pub fn new() -> Self {
        Self {
            display_currency: RwSignal::new("USD".to_string()),
            base_currency: RwSignal::new("USD".to_string()),
            rates: RwSignal::new(HashMap::new()),
            is_loading: RwSignal::new(false),
            last_fetched: RwSignal::new(None),
            error: RwSignal::new(None),
        }
    }

    /// Set the display currency.
    pub fn set_display_currency(&self, currency: &str) {
        self.display_currency.set(currency.to_string());
    }

    /// Set the base currency.
    pub fn set_base_currency(&self, currency: &str) {
        self.base_currency.set(currency.to_string());
    }

    /// Fetch exchange rates from the API.
    pub async fn fetch_rates(&self, client: &crate::api::client::ApiClient) {
        self.is_loading.set(true);
        self.error.set(None);
        match client
            .get::<serde_json::Value>("/api/v1/currency/rates")
            .await
        {
            Ok(data) => {
                if let Some(rates_map) = data.get("rates").and_then(|r| r.as_object()) {
                    let mut rates = ExchangeRates::new();
                    for (k, v) in rates_map {
                        if let Some(val) = v.as_f64() {
                            rates.insert(k.clone(), val);
                        }
                    }
                    self.rates.set(rates);
                }
                self.last_fetched.set(Some(chrono::Utc::now().to_rfc3339()));
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.is_loading.set(false);
    }

    /// Convert an amount from one currency to another.
    pub fn convert(&self, amount: f64, from: &str, to: &str) -> f64 {
        if from == to {
            return amount;
        }
        let rates = self.rates.get();
        let base = self.base_currency.get();

        // Convert `from` → base → `to`
        let in_base = if from == &*base {
            amount
        } else {
            rates.get(from).map(|r| amount / r).unwrap_or(amount)
        };

        if to == &*base {
            in_base
        } else {
            rates.get(to).map(|r| in_base * r).unwrap_or(in_base)
        }
    }

    /// Format an amount in a given currency.
    pub fn format(&self, amount: f64, currency: &str) -> String {
        format!("{:.2} {}", amount, currency)
    }

    /// Format an amount in the display currency with the original value shown.
    pub fn format_with_original(&self, amount: f64, original_currency: &str) -> String {
        let display = self.display_currency.get();
        let converted = self.convert(amount, original_currency, &display);
        format!(
            "{:.2} {} ({:.2} {})",
            converted, display, amount, original_currency
        )
    }
}

impl Default for CurrencyStore {
    fn default() -> Self {
        Self::new()
    }
}

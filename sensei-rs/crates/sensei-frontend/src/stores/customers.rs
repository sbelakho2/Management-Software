//! Customers (Accounts) reactive store.
//!
//! Mirrors the Zustand [`customers.ts`](frontend/src/stores/customers.ts) store.

use crate::api::accounts::{AccountsApi, CustomerDto, UpdateAccountData};
use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;

/// Helper to extract a user-friendly error message.
fn get_error_message(error: &ApiError) -> String {
    match error {
        ApiError::Http(msg) => format!("Network error: {}", msg),
        ApiError::Status(code) => format!("Server error (status {})", code),
        ApiError::Json(msg) => format!("Parse error: {}", msg),
        ApiError::Auth(msg) => format!("Auth error: {}", msg),
    }
}

/// Reactive store for customers.
#[derive(Debug, Clone)]
pub struct CustomersStore {
    /// List of customers.
    pub customers: RwSignal<Vec<CustomerDto>>,
    /// Total number of customers (across pages).
    pub total_customers: RwSignal<i32>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl CustomersStore {
    pub fn new() -> Self {
        Self {
            customers: RwSignal::new(Vec::new()),
            total_customers: RwSignal::new(0),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch all customers.
    pub async fn fetch_customers(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match AccountsApi::list_accounts(client, None).await {
            Ok(resp) => {
                self.customers.set(resp.items);
                self.total_customers.set(resp.total);
            }
            Err(e) => {
                self.error.set(Some(get_error_message(&e)));
            }
        }
        self.loading.set(false);
    }

    /// Create a new customer.
    pub async fn create_customer(&self, client: &ApiClient, data: &serde_json::Value) {
        self.loading.set(true);
        self.error.set(None);
        let create_data: Result<crate::api::accounts::CreateAccountData, _> =
            serde_json::from_value(data.clone());
        match create_data {
            Ok(d) => match AccountsApi::create_account(client, &d).await {
                Ok(customer) => {
                    self.customers.update(|c| c.push(customer));
                }
                Err(e) => {
                    self.error.set(Some(get_error_message(&e)));
                }
            },
            Err(e) => {
                self.error.set(Some(format!("Invalid data: {}", e)));
            }
        }
        self.loading.set(false);
    }

    /// Update an existing customer.
    pub async fn update_customer(&self, client: &ApiClient, id: &str, data: &serde_json::Value) {
        self.loading.set(true);
        self.error.set(None);
        let update_data: Result<UpdateAccountData, _> = serde_json::from_value(data.clone());
        match update_data {
            Ok(d) => match AccountsApi::update_account(client, id, &d).await {
                Ok(customer) => {
                    self.customers.update(|c| {
                        if let Some(pos) = c.iter().position(|x| x.id == id) {
                            c[pos] = customer;
                        }
                    });
                }
                Err(e) => {
                    self.error.set(Some(get_error_message(&e)));
                }
            },
            Err(e) => {
                self.error.set(Some(format!("Invalid data: {}", e)));
            }
        }
        self.loading.set(false);
    }

    /// Delete a customer.
    pub async fn delete_customer(&self, client: &ApiClient, id: &str) {
        self.loading.set(true);
        self.error.set(None);
        match AccountsApi::delete_account(client, id, false).await {
            Ok(_) => {
                self.customers.update(|c| c.retain(|x| x.id != id));
            }
            Err(e) => {
                self.error.set(Some(get_error_message(&e)));
            }
        }
        self.loading.set(false);
    }

    /// Clear the current error.
    pub fn clear_error(&self) {
        self.error.set(None);
    }
}

impl Default for CustomersStore {
    fn default() -> Self {
        Self::new()
    }
}

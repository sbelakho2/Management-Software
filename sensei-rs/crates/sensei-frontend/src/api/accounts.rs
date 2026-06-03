//! Accounts (Customers, Suppliers, Prospects) API endpoints.
//!
//! CRUD for accounts, contacts, subsidiaries.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountListParams {
    pub status: Option<String>,
    pub account_type: Option<String>,
    pub industry: Option<String>,
    pub search: Option<String>,
    pub country: Option<String>,
    pub city: Option<String>,
    pub tier: Option<String>,
    pub parent_id: Option<String>,
    pub sort: Option<String>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateAccountData {
    pub name: String,
    pub legal_name: Option<String>,
    pub account_type: Option<String>,
    pub status: Option<String>,
    pub tier: Option<String>,
    pub industry: Option<String>,
    pub sub_industry: Option<String>,
    pub website: Option<String>,
    pub phone: Option<String>,
    pub email: Option<String>,
    pub address_line1: Option<String>,
    pub address_line2: Option<String>,
    pub city: Option<String>,
    pub state_province: Option<String>,
    pub postal_code: Option<String>,
    pub country: Option<String>,
    pub tax_id: Option<String>,
    pub registration_number: Option<String>,
    pub employees_count: Option<i32>,
    pub annual_revenue: Option<f64>,
    pub revenue_currency: Option<String>,
    pub description: Option<String>,
    pub internal_notes: Option<String>,
    pub custom_fields: Option<HashMap<String, serde_json::Value>>,
    pub tags: Option<Vec<String>>,
    pub parent_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateAccountData {
    pub name: Option<String>,
    pub legal_name: Option<String>,
    pub account_type: Option<String>,
    pub status: Option<String>,
    pub tier: Option<String>,
    pub industry: Option<String>,
    pub sub_industry: Option<String>,
    pub website: Option<String>,
    pub phone: Option<String>,
    pub email: Option<String>,
    pub address_line1: Option<String>,
    pub address_line2: Option<String>,
    pub city: Option<String>,
    pub state_province: Option<String>,
    pub postal_code: Option<String>,
    pub country: Option<String>,
    pub tax_id: Option<String>,
    pub registration_number: Option<String>,
    pub employees_count: Option<i32>,
    pub annual_revenue: Option<f64>,
    pub revenue_currency: Option<String>,
    pub description: Option<String>,
    pub internal_notes: Option<String>,
    pub custom_fields: Option<HashMap<String, serde_json::Value>>,
    pub tags: Option<Vec<String>>,
    pub parent_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountStats {
    pub total_accounts: i32,
    pub by_type: HashMap<String, i32>,
    pub by_status: HashMap<String, i32>,
    pub by_tier: HashMap<String, i32>,
    pub by_country: HashMap<String, i32>,
    pub new_this_month: i32,
    pub active_customers: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerDto {
    pub id: String,
    pub name: String,
    pub legal_name: Option<String>,
    pub account_type: Option<String>,
    pub status: Option<String>,
    pub tier: Option<String>,
    pub industry: Option<String>,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub city: Option<String>,
    pub country: Option<String>,
    pub tags: Option<Vec<String>>,
    pub created_at: String,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedAccountsResponse {
    pub items: Vec<CustomerDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContactDto {
    pub id: String,
    pub account_id: String,
    pub first_name: String,
    pub last_name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub job_title: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateContactData {
    pub account_id: String,
    pub first_name: String,
    pub last_name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub job_title: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedContactsResponse {
    pub items: Vec<ContactDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginationParams {
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountSearchResult {
    pub items: Vec<CustomerDto>,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct AccountsApi;

impl AccountsApi {
    pub async fn list_accounts(
        client: &ApiClient,
        params: Option<&AccountListParams>,
    ) -> Result<PaginatedAccountsResponse, ApiError> {
        let path = match params {
            Some(p) => {
                let mut q = Vec::new();
                if let Some(v) = &p.status {
                    q.push(format!("status={}", v));
                }
                if let Some(v) = &p.account_type {
                    q.push(format!("account_type={}", v));
                }
                if let Some(v) = &p.industry {
                    q.push(format!("industry={}", v));
                }
                if let Some(v) = &p.search {
                    q.push(format!("search={}", v));
                }
                if let Some(v) = &p.country {
                    q.push(format!("country={}", v));
                }
                if let Some(v) = &p.city {
                    q.push(format!("city={}", v));
                }
                if let Some(v) = &p.tier {
                    q.push(format!("tier={}", v));
                }
                if let Some(v) = &p.parent_id {
                    q.push(format!("parent_id={}", v));
                }
                if let Some(v) = &p.sort {
                    q.push(format!("sort={}", v));
                }
                if let Some(v) = p.page {
                    q.push(format!("page={}", v));
                }
                if let Some(v) = p.per_page {
                    q.push(format!("per_page={}", v));
                }
                if q.is_empty() {
                    "/api/v1/accounts".to_string()
                } else {
                    format!("/api/v1/accounts?{}", q.join("&"))
                }
            }
            None => "/api/v1/accounts".to_string(),
        };
        client.get(&path).await
    }

    pub async fn get_account(client: &ApiClient, id: &str) -> Result<CustomerDto, ApiError> {
        client.get(&format!("/api/v1/accounts/{}", id)).await
    }

    pub async fn create_account(
        client: &ApiClient,
        data: &CreateAccountData,
    ) -> Result<CustomerDto, ApiError> {
        client.post("/api/v1/accounts", data).await
    }

    pub async fn update_account(
        client: &ApiClient,
        id: &str,
        data: &UpdateAccountData,
    ) -> Result<CustomerDto, ApiError> {
        client.put(&format!("/api/v1/accounts/{}", id), data).await
    }

    pub async fn delete_account(
        client: &ApiClient,
        id: &str,
        hard_delete: bool,
    ) -> Result<serde_json::Value, ApiError> {
        let path = if hard_delete {
            format!("/api/v1/accounts/{}?hard_delete=true", id)
        } else {
            format!("/api/v1/accounts/{}", id)
        };
        client.delete(&path).await
    }

    pub async fn restore_account(
        client: &ApiClient,
        id: &str,
    ) -> Result<CustomerDto, ApiError> {
        client
            .post(&format!("/api/v1/accounts/{}/restore", id), &serde_json::json!({}))
            .await
    }

    pub async fn get_global_stats(client: &ApiClient) -> Result<AccountStats, ApiError> {
        client.get("/api/v1/accounts/stats").await
    }

    pub async fn list_subsidiaries(
        client: &ApiClient,
        id: &str,
        params: Option<&PaginationParams>,
    ) -> Result<PaginatedAccountsResponse, ApiError> {
        let path = match params {
            Some(p) => {
                let mut q = Vec::new();
                if let Some(v) = p.page {
                    q.push(format!("page={}", v));
                }
                if let Some(v) = p.per_page {
                    q.push(format!("per_page={}", v));
                }
                if q.is_empty() {
                    format!("/api/v1/accounts/{}/subsidiaries", id)
                } else {
                    format!("/api/v1/accounts/{}/subsidiaries?{}", id, q.join("&"))
                }
            }
            None => format!("/api/v1/accounts/{}/subsidiaries", id),
        };
        client.get(&path).await
    }

    pub async fn search_accounts(
        client: &ApiClient,
        query: &str,
        limit: Option<i32>,
    ) -> Result<Vec<CustomerDto>, ApiError> {
        let path = match limit {
            Some(l) => format!("/api/v1/accounts?search={}&per_page={}", query, l),
            None => format!("/api/v1/accounts?search={}", query),
        };
        let resp: PaginatedAccountsResponse = client.get(&path).await?;
        Ok(resp.items)
    }

    pub async fn list_contacts(
        client: &ApiClient,
        account_id: &str,
    ) -> Result<Vec<ContactDto>, ApiError> {
        client
            .get(&format!("/api/v1/accounts/{}/contacts", account_id))
            .await
    }

    pub async fn create_contact(
        client: &ApiClient,
        data: &CreateContactData,
    ) -> Result<ContactDto, ApiError> {
        client
            .post(&format!("/api/v1/accounts/{}/contacts", data.account_id), data)
            .await
    }
}

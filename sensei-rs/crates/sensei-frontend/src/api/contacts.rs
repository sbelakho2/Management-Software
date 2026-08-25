//! Contact management API endpoints.
//!
//! CRUD for contacts.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContactListParams {
    pub account_id: Option<String>,
    pub search: Option<String>,
    pub job_title: Option<String>,
    pub department: Option<String>,
    pub country: Option<String>,
    pub email_opt_out: Option<bool>,
    pub sort: Option<String>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContactResponse {
    pub id: String,
    pub first_name: String,
    pub last_name: String,
    pub display_name: String,
    pub email: Option<String>,
    pub phone_mobile: Option<String>,
    pub phone_work: Option<String>,
    pub job_title: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateContactData {
    pub first_name: String,
    pub last_name: String,
    pub email: Option<String>,
    pub phone_mobile: Option<String>,
    pub phone_work: Option<String>,
    pub job_title: Option<String>,
    pub account_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateContactData {
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub email: Option<String>,
    pub phone_mobile: Option<String>,
    pub phone_work: Option<String>,
    pub job_title: Option<String>,
    pub account_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedContactsResponse {
    pub items: Vec<ContactResponse>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct ContactsApi;

impl ContactsApi {
    pub async fn list_contacts(
        client: &ApiClient,
        params: Option<&ContactListParams>,
    ) -> Result<PaginatedContactsResponse, ApiError> {
        let path = build_contacts_query(params);
        client.get(&path).await
    }

    pub async fn get_contact(client: &ApiClient, id: &str) -> Result<ContactResponse, ApiError> {
        client.get(&format!("/api/v1/contacts/{}", id)).await
    }

    pub async fn create_contact(
        client: &ApiClient,
        data: &CreateContactData,
    ) -> Result<ContactResponse, ApiError> {
        client.post("/api/v1/contacts", data).await
    }

    pub async fn update_contact(
        client: &ApiClient,
        id: &str,
        data: &UpdateContactData,
    ) -> Result<ContactResponse, ApiError> {
        client.put(&format!("/api/v1/contacts/{}", id), data).await
    }

    pub async fn delete_contact(
        client: &ApiClient,
        id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client.delete(&format!("/api/v1/contacts/{}", id)).await
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn build_contacts_query(params: Option<&ContactListParams>) -> String {
    let Some(p) = params else {
        return "/api/v1/contacts".to_string();
    };

    let mut q = Vec::new();
    if let Some(v) = &p.account_id {
        q.push(format!("account_id={}", v));
    }
    if let Some(v) = &p.search {
        q.push(format!("search={}", v));
    }
    if let Some(v) = &p.job_title {
        q.push(format!("job_title={}", v));
    }
    if let Some(v) = &p.department {
        q.push(format!("department={}", v));
    }
    if let Some(v) = &p.country {
        q.push(format!("country={}", v));
    }
    if let Some(v) = p.email_opt_out {
        q.push(format!("email_opt_out={}", v));
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
        "/api/v1/contacts".to_string()
    } else {
        format!("/api/v1/contacts?{}", q.join("&"))
    }
}

//! RFQ (Request for Quote) and Quote API endpoints.
//!
//! RFQs, Quotes, line items, approvals, revisions, exports.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// DTOs — RFQ
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqListParams {
    pub status: Option<serde_json::Value>, // String or Vec<String>
    pub priority: Option<serde_json::Value>, // String or Vec<String>
    pub customer_id: Option<String>,
    pub assigned_to: Option<String>,
    pub search: Option<String>,
    pub due_date_from: Option<String>,
    pub due_date_to: Option<String>,
    pub received_date_from: Option<String>,
    pub received_date_to: Option<String>,
    pub tags: Option<Vec<String>>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateRfqData {
    pub customer_id: String,
    pub title: String,
    pub description: Option<String>,
    pub priority: Option<String>,
    pub due_date: String,
    pub received_date: String,
    pub estimated_value: Option<f64>,
    pub currency: Option<String>,
    pub notes: Option<String>,
    pub tags: Option<Vec<String>>,
    pub line_items: Option<Vec<CreateRfqLineItemData>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateRfqData {
    pub customer_id: Option<String>,
    pub title: Option<String>,
    pub description: Option<String>,
    pub status: Option<String>,
    pub priority: Option<String>,
    pub due_date: Option<String>,
    pub estimated_value: Option<f64>,
    pub currency: Option<String>,
    pub notes: Option<String>,
    pub assigned_to: Option<serde_json::Value>, // String or null
    pub tags: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateRfqLineItemData {
    pub part_number: String,
    pub description: String,
    pub quantity: f64,
    pub unit_of_measure: String,
    pub target_price: Option<f64>,
    pub notes: Option<String>,
    pub specifications: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateRfqLineItemData {
    pub part_number: Option<String>,
    pub description: Option<String>,
    pub quantity: Option<f64>,
    pub unit_of_measure: Option<String>,
    pub target_price: Option<f64>,
    pub notes: Option<String>,
    pub specifications: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqDto {
    pub id: String,
    pub customer_id: String,
    pub title: String,
    pub description: Option<String>,
    pub status: String,
    pub priority: Option<String>,
    pub due_date: Option<String>,
    pub received_date: Option<String>,
    pub estimated_value: Option<f64>,
    pub currency: Option<String>,
    pub notes: Option<String>,
    pub assigned_to: Option<String>,
    pub tags: Option<Vec<String>>,
    pub created_at: String,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqLineItemDto {
    pub id: String,
    pub rfq_id: String,
    pub part_number: String,
    pub description: String,
    pub quantity: f64,
    pub unit_of_measure: String,
    pub target_price: Option<f64>,
    pub notes: Option<String>,
    pub specifications: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedRfqsResponse {
    pub items: Vec<RfqDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqStats {
    pub total: i32,
    pub by_status: HashMap<String, i32>,
    pub by_priority: HashMap<String, i32>,
    pub total_value: f64,
    pub average_value: f64,
    pub win_rate: f64,
    pub average_response_time_days: f64,
    pub overdue: i32,
    pub due_this_week: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelineEvent {
    pub id: String,
    #[serde(rename = "type")]
    pub event_type: String,
    pub action: String,
    pub description: String,
    pub user_id: Option<String>,
    pub user_name: Option<String>,
    pub created_at: String,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

// ---------------------------------------------------------------------------
// DTOs — Quote
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteListParams {
    pub status: Option<serde_json::Value>, // String or Vec<String>
    pub rfq_id: Option<String>,
    pub customer_id: Option<String>,
    pub search: Option<String>,
    pub valid_from: Option<String>,
    pub valid_to: Option<String>,
    pub min_amount: Option<f64>,
    pub max_amount: Option<f64>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateQuoteData {
    pub rfq_id: String,
    pub valid_until: String,
    pub discount_percentage: Option<f64>,
    pub discount_amount: Option<f64>,
    pub tax_amount: Option<f64>,
    pub terms_and_conditions: Option<String>,
    pub notes: Option<String>,
    pub line_items: Vec<CreateQuoteLineItemData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateQuoteData {
    pub valid_until: Option<String>,
    pub discount_percentage: Option<f64>,
    pub discount_amount: Option<f64>,
    pub tax_amount: Option<f64>,
    pub terms_and_conditions: Option<String>,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateQuoteLineItemData {
    pub rfq_line_item_id: Option<String>,
    pub part_number: String,
    pub description: String,
    pub quantity: f64,
    pub unit_of_measure: String,
    pub unit_price: f64,
    pub cost: Option<f64>,
    pub lead_time_days: Option<i32>,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateQuoteLineItemData {
    pub part_number: Option<String>,
    pub description: Option<String>,
    pub quantity: Option<f64>,
    pub unit_of_measure: Option<String>,
    pub unit_price: Option<f64>,
    pub cost: Option<f64>,
    pub lead_time_days: Option<i32>,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteDto {
    pub id: String,
    pub rfq_id: Option<String>,
    pub customer_id: Option<String>,
    pub quote_number: Option<String>,
    pub status: String,
    pub subtotal: Option<f64>,
    pub discount_percentage: Option<f64>,
    pub discount_amount: Option<f64>,
    pub tax_amount: Option<f64>,
    pub total: Option<f64>,
    pub currency: Option<String>,
    pub valid_until: Option<String>,
    pub terms_and_conditions: Option<String>,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteLineItemDto {
    pub id: String,
    pub quote_id: String,
    pub rfq_line_item_id: Option<String>,
    pub part_number: String,
    pub description: String,
    pub quantity: f64,
    pub unit_of_measure: String,
    pub unit_price: f64,
    pub cost: Option<f64>,
    pub total: Option<f64>,
    pub lead_time_days: Option<i32>,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedQuotesResponse {
    pub items: Vec<QuoteDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteTotals {
    pub subtotal: f64,
    pub discount: f64,
    pub tax: f64,
    pub total: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteStats {
    pub total: i32,
    pub by_status: HashMap<String, i32>,
    pub total_value: f64,
    pub average_value: f64,
    pub average_margin: f64,
    pub approval_rate: f64,
    pub average_approval_time_hours: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalculateQuoteData {
    pub line_items: Vec<CalculateLineItem>,
    pub discount_percentage: Option<f64>,
    pub discount_amount: Option<f64>,
    pub tax_percentage: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalculateLineItem {
    pub quantity: f64,
    pub unit_price: f64,
}

// ---------------------------------------------------------------------------
// API — RFQ
// ---------------------------------------------------------------------------

pub struct RfqApi;

impl RfqApi {
    pub async fn list_rfqs(
        client: &ApiClient,
        params: Option<&RfqListParams>,
    ) -> Result<PaginatedRfqsResponse, ApiError> {
        let path = build_rfq_query(params);
        client.get(&path).await
    }

    pub async fn get_rfq(client: &ApiClient, id: &str) -> Result<RfqDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/rfqs/{}", id))
            .await
    }

    pub async fn create_rfq(client: &ApiClient, data: &CreateRfqData) -> Result<RfqDto, ApiError> {
        client.post("/api/v1/supply-chain/rfqs", data).await
    }

    pub async fn update_rfq(
        client: &ApiClient,
        id: &str,
        data: &UpdateRfqData,
    ) -> Result<RfqDto, ApiError> {
        client
            .put(&format!("/api/v1/supply-chain/rfqs/{}", id), data)
            .await
    }

    pub async fn delete_rfq(client: &ApiClient, id: &str) -> Result<serde_json::Value, ApiError> {
        client
            .delete(&format!("/api/v1/supply-chain/rfqs/{}", id))
            .await
    }

    pub async fn submit_rfq(client: &ApiClient, id: &str) -> Result<RfqDto, ApiError> {
        client
            .post(
                &format!("/api/v1/supply-chain/rfqs/{}/submit", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn mark_rfq_won(client: &ApiClient, id: &str) -> Result<RfqDto, ApiError> {
        client
            .post(&format!("/api/v1/rfqs/{}/won", id), &serde_json::json!({}))
            .await
    }

    pub async fn mark_rfq_lost(
        client: &ApiClient,
        id: &str,
        reason: Option<&str>,
    ) -> Result<RfqDto, ApiError> {
        #[derive(Serialize)]
        struct LostBody<'a> {
            reason: Option<&'a str>,
        }
        client
            .post(&format!("/api/v1/rfqs/{}/lost", id), &LostBody { reason })
            .await
    }

    pub async fn no_bid_rfq(
        client: &ApiClient,
        id: &str,
        reason: Option<&str>,
    ) -> Result<RfqDto, ApiError> {
        #[derive(Serialize)]
        struct NoBidBody<'a> {
            reason: Option<&'a str>,
        }
        client
            .post(
                &format!("/api/v1/rfqs/{}/no-bid", id),
                &NoBidBody { reason },
            )
            .await
    }

    pub async fn cancel_rfq(
        client: &ApiClient,
        id: &str,
        reason: Option<&str>,
    ) -> Result<RfqDto, ApiError> {
        #[derive(Serialize)]
        struct CancelBody<'a> {
            reason: Option<&'a str>,
        }
        client
            .post(
                &format!("/api/v1/supply-chain/rfqs/{}/cancel", id),
                &CancelBody { reason },
            )
            .await
    }

    pub async fn assign_rfq(
        client: &ApiClient,
        id: &str,
        user_id: &str,
    ) -> Result<RfqDto, ApiError> {
        #[derive(Serialize)]
        struct AssignBody<'a> {
            user_id: &'a str,
        }
        client
            .post(
                &format!("/api/v1/rfqs/{}/assign", id),
                &AssignBody { user_id },
            )
            .await
    }

    pub async fn unassign_rfq(client: &ApiClient, id: &str) -> Result<RfqDto, ApiError> {
        client
            .post(
                &format!("/api/v1/rfqs/{}/unassign", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn duplicate_rfq(client: &ApiClient, id: &str) -> Result<RfqDto, ApiError> {
        client
            .post(
                &format!("/api/v1/supply-chain/rfqs/{}", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn get_rfq_stats(
        client: &ApiClient,
        from_date: Option<&str>,
        to_date: Option<&str>,
    ) -> Result<RfqStats, ApiError> {
        let mut path = "/api/v1/rfqs/stats".to_string();
        let mut q = Vec::new();
        if let Some(v) = from_date {
            q.push(format!("from_date={}", v));
        }
        if let Some(v) = to_date {
            q.push(format!("to_date={}", v));
        }
        if !q.is_empty() {
            path = format!("{}?{}", path, q.join("&"));
        }
        client.get(&path).await
    }

    pub async fn get_rfq_timeline(
        client: &ApiClient,
        id: &str,
    ) -> Result<Vec<TimelineEvent>, ApiError> {
        client.get(&format!("/api/v1/rfqs/{}/timeline", id)).await
    }

    // ---- RFQ Line Items ----
    pub async fn list_rfq_line_items(
        client: &ApiClient,
        rfq_id: &str,
    ) -> Result<Vec<RfqLineItemDto>, ApiError> {
        client
            .get(&format!("/api/v1/rfqs/{}/line-items", rfq_id))
            .await
    }

    pub async fn create_rfq_line_item(
        client: &ApiClient,
        rfq_id: &str,
        data: &CreateRfqLineItemData,
    ) -> Result<RfqLineItemDto, ApiError> {
        client
            .post(&format!("/api/v1/rfqs/{}/line-items", rfq_id), data)
            .await
    }

    pub async fn update_rfq_line_item(
        client: &ApiClient,
        rfq_id: &str,
        line_item_id: &str,
        data: &UpdateRfqLineItemData,
    ) -> Result<RfqLineItemDto, ApiError> {
        client
            .put(
                &format!("/api/v1/rfqs/{}/line-items/{}", rfq_id, line_item_id),
                data,
            )
            .await
    }

    pub async fn delete_rfq_line_item(
        client: &ApiClient,
        rfq_id: &str,
        line_item_id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client
            .delete(&format!(
                "/api/v1/rfqs/{}/line-items/{}",
                rfq_id, line_item_id
            ))
            .await
    }

    pub async fn bulk_create_rfq_line_items(
        client: &ApiClient,
        rfq_id: &str,
        items: &[CreateRfqLineItemData],
    ) -> Result<Vec<RfqLineItemDto>, ApiError> {
        #[derive(Serialize)]
        struct BulkItemsBody<'a> {
            items: &'a [CreateRfqLineItemData],
        }
        client
            .post(
                &format!("/api/v1/rfqs/{}/line-items/bulk", rfq_id),
                &BulkItemsBody { items },
            )
            .await
    }

    pub async fn bulk_delete_rfq_line_items(
        client: &ApiClient,
        rfq_id: &str,
        line_item_ids: &[String],
    ) -> Result<serde_json::Value, ApiError> {
        #[derive(Serialize)]
        struct BulkDeleteBody<'a> {
            ids: &'a [String],
        }
        client
            .post(
                &format!("/api/v1/rfqs/{}/line-items/bulk-delete", rfq_id),
                &BulkDeleteBody { ids: line_item_ids },
            )
            .await
    }
}

// ---------------------------------------------------------------------------
// API — Quote
// ---------------------------------------------------------------------------

pub struct QuoteApi;

impl QuoteApi {
    pub async fn list_quotes(
        client: &ApiClient,
        params: Option<&QuoteListParams>,
    ) -> Result<PaginatedQuotesResponse, ApiError> {
        let path = build_quote_query(params);
        client.get(&path).await
    }

    pub async fn get_quote(client: &ApiClient, id: &str) -> Result<QuoteDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/quotes/{}", id))
            .await
    }

    pub async fn create_quote(
        client: &ApiClient,
        data: &CreateQuoteData,
    ) -> Result<QuoteDto, ApiError> {
        client.post("/api/v1/supply-chain/quotes", data).await
    }

    pub async fn update_quote(
        client: &ApiClient,
        id: &str,
        data: &UpdateQuoteData,
    ) -> Result<QuoteDto, ApiError> {
        client
            .put(&format!("/api/v1/supply-chain/quotes/{}", id), data)
            .await
    }

    pub async fn delete_quote(client: &ApiClient, id: &str) -> Result<serde_json::Value, ApiError> {
        client
            .delete(&format!("/api/v1/supply-chain/quotes/{}", id))
            .await
    }

    pub async fn submit_quote_for_approval(
        client: &ApiClient,
        id: &str,
    ) -> Result<QuoteDto, ApiError> {
        client
            .post(
                &format!("/api/v1/supply-chain/quotes/{}/submit", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn approve_quote(
        client: &ApiClient,
        id: &str,
        notes: Option<&str>,
    ) -> Result<QuoteDto, ApiError> {
        #[derive(Serialize)]
        struct ApproveBody<'a> {
            notes: Option<&'a str>,
        }
        client
            .post(
                &format!("/api/v1/supply-chain/quotes/{}/approve", id),
                &ApproveBody { notes },
            )
            .await
    }

    pub async fn reject_quote(
        client: &ApiClient,
        id: &str,
        reason: &str,
    ) -> Result<QuoteDto, ApiError> {
        #[derive(Serialize)]
        struct RejectBody<'a> {
            reason: &'a str,
        }
        client
            .post(
                &format!("/api/v1/supply-chain/quotes/{}/reject", id),
                &RejectBody { reason },
            )
            .await
    }

    pub async fn send_quote(
        client: &ApiClient,
        id: &str,
        email: Option<&str>,
    ) -> Result<QuoteDto, ApiError> {
        #[derive(Serialize)]
        struct SendBody<'a> {
            email: Option<&'a str>,
        }
        client
            .post(
                &format!("/api/v1/supply-chain/quotes/{}/submit", id),
                &SendBody { email },
            )
            .await
    }

    pub async fn accept_quote(client: &ApiClient, id: &str) -> Result<QuoteDto, ApiError> {
        client
            .post(
                &format!("/api/v1/supply-chain/quotes/{}/accept", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn customer_reject_quote(
        client: &ApiClient,
        id: &str,
        reason: Option<&str>,
    ) -> Result<QuoteDto, ApiError> {
        #[derive(Serialize)]
        struct RejectBody<'a> {
            reason: Option<&'a str>,
        }
        client
            .post(
                &format!("/api/v1/quotes/{}/customer-reject", id),
                &RejectBody { reason },
            )
            .await
    }

    pub async fn create_quote_revision(client: &ApiClient, id: &str) -> Result<QuoteDto, ApiError> {
        client
            .post(
                &format!("/api/v1/quotes/{}/revise", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn get_quote_versions(
        client: &ApiClient,
        id: &str,
    ) -> Result<Vec<QuoteDto>, ApiError> {
        client.get(&format!("/api/v1/quotes/{}/versions", id)).await
    }

    pub async fn calculate_quote_totals(
        client: &ApiClient,
        data: &CalculateQuoteData,
    ) -> Result<QuoteTotals, ApiError> {
        client.post("/api/v1/quotes/calculate", data).await
    }

    pub async fn get_quote_stats(
        client: &ApiClient,
        from_date: Option<&str>,
        to_date: Option<&str>,
    ) -> Result<QuoteStats, ApiError> {
        let mut path = "/api/v1/quotes/stats".to_string();
        let mut q = Vec::new();
        if let Some(v) = from_date {
            q.push(format!("from_date={}", v));
        }
        if let Some(v) = to_date {
            q.push(format!("to_date={}", v));
        }
        if !q.is_empty() {
            path = format!("{}?{}", path, q.join("&"));
        }
        client.get(&path).await
    }

    pub async fn get_quote_timeline(
        client: &ApiClient,
        id: &str,
    ) -> Result<Vec<TimelineEvent>, ApiError> {
        client.get(&format!("/api/v1/quotes/{}/timeline", id)).await
    }

    // ---- Quote Line Items ----
    pub async fn list_quote_line_items(
        client: &ApiClient,
        quote_id: &str,
    ) -> Result<Vec<QuoteLineItemDto>, ApiError> {
        client
            .get(&format!("/api/v1/quotes/{}/line-items", quote_id))
            .await
    }

    pub async fn create_quote_line_item(
        client: &ApiClient,
        quote_id: &str,
        data: &CreateQuoteLineItemData,
    ) -> Result<QuoteLineItemDto, ApiError> {
        client
            .post(&format!("/api/v1/quotes/{}/line-items", quote_id), data)
            .await
    }

    pub async fn update_quote_line_item(
        client: &ApiClient,
        quote_id: &str,
        line_item_id: &str,
        data: &UpdateQuoteLineItemData,
    ) -> Result<QuoteLineItemDto, ApiError> {
        client
            .put(
                &format!("/api/v1/quotes/{}/line-items/{}", quote_id, line_item_id),
                data,
            )
            .await
    }

    pub async fn delete_quote_line_item(
        client: &ApiClient,
        quote_id: &str,
        line_item_id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client
            .delete(&format!(
                "/api/v1/quotes/{}/line-items/{}",
                quote_id, line_item_id
            ))
            .await
    }

    pub async fn reorder_quote_line_items(
        client: &ApiClient,
        quote_id: &str,
        line_item_ids: &[String],
    ) -> Result<Vec<QuoteLineItemDto>, ApiError> {
        #[derive(Serialize)]
        struct ReorderBody<'a> {
            ids: &'a [String],
        }
        client
            .post(
                &format!("/api/v1/quotes/{}/line-items/reorder", quote_id),
                &ReorderBody { ids: line_item_ids },
            )
            .await
    }
}

// ---------------------------------------------------------------------------
// Helpers — query string builders
// ---------------------------------------------------------------------------

fn build_rfq_query(params: Option<&RfqListParams>) -> String {
    let Some(p) = params else {
        return "/api/v1/supply-chain/rfqs".to_string();
    };

    let mut q = Vec::new();
    if let Some(v) = &p.status {
        q.push(format!("status={}", v));
    }
    if let Some(v) = &p.priority {
        q.push(format!("priority={}", v));
    }
    if let Some(v) = &p.customer_id {
        q.push(format!("customer_id={}", v));
    }
    if let Some(v) = &p.assigned_to {
        q.push(format!("assigned_to={}", v));
    }
    if let Some(v) = &p.search {
        q.push(format!("search={}", v));
    }
    if let Some(v) = &p.due_date_from {
        q.push(format!("due_date_from={}", v));
    }
    if let Some(v) = &p.due_date_to {
        q.push(format!("due_date_to={}", v));
    }
    if let Some(v) = &p.received_date_from {
        q.push(format!("received_date_from={}", v));
    }
    if let Some(v) = &p.received_date_to {
        q.push(format!("received_date_to={}", v));
    }
    if let Some(v) = p.page {
        q.push(format!("page={}", v));
    }
    if let Some(v) = p.per_page {
        q.push(format!("per_page={}", v));
    }

    if q.is_empty() {
        "/api/v1/supply-chain/rfqs".to_string()
    } else {
        format!("/api/v1/rfqs?{}", q.join("&"))
    }
}

fn build_quote_query(params: Option<&QuoteListParams>) -> String {
    let Some(p) = params else {
        return "/api/v1/supply-chain/quotes".to_string();
    };

    let mut q = Vec::new();
    if let Some(v) = &p.status {
        q.push(format!("status={}", v));
    }
    if let Some(v) = &p.rfq_id {
        q.push(format!("rfq_id={}", v));
    }
    if let Some(v) = &p.customer_id {
        q.push(format!("customer_id={}", v));
    }
    if let Some(v) = &p.search {
        q.push(format!("search={}", v));
    }
    if let Some(v) = &p.valid_from {
        q.push(format!("valid_from={}", v));
    }
    if let Some(v) = &p.valid_to {
        q.push(format!("valid_to={}", v));
    }
    if let Some(v) = p.min_amount {
        q.push(format!("min_amount={}", v));
    }
    if let Some(v) = p.max_amount {
        q.push(format!("max_amount={}", v));
    }
    if let Some(v) = p.page {
        q.push(format!("page={}", v));
    }
    if let Some(v) = p.per_page {
        q.push(format!("per_page={}", v));
    }

    if q.is_empty() {
        "/api/v1/supply-chain/quotes".to_string()
    } else {
        format!("/api/v1/quotes?{}", q.join("&"))
    }
}

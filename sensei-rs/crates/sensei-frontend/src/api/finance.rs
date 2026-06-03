//! Finance management API endpoints.
//!
//! Invoices, Payments, Budgets, Journal Entries, Cost Rollups.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvoiceDto {
    pub id: String,
    pub tenant_id: String,
    pub invoice_number: String,
    pub customer_id: String,
    pub subtotal: f64,
    pub tax: f64,
    pub total: f64,
    pub currency: String,
    pub status: String,
    pub due_date: Option<String>,
    pub paid_at: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateInvoiceRequest {
    pub customer_id: String,
    pub line_items: Vec<InvoiceLineItemRequest>,
    pub due_date: Option<String>,
    pub currency: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvoiceLineItemRequest {
    pub description: String,
    pub quantity: f64,
    pub unit_price: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaymentDto {
    pub id: String,
    pub tenant_id: String,
    pub payment_number: String,
    pub invoice_id: String,
    pub amount: f64,
    pub currency: String,
    pub method: String,
    pub status: String,
    pub paid_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecordPaymentRequest {
    pub invoice_id: String,
    pub amount: f64,
    pub method: String,
    pub currency: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetDto {
    pub id: String,
    pub tenant_id: String,
    pub department: String,
    pub fiscal_year: String,
    pub allocated: f64,
    pub spent: f64,
    pub remaining: f64,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateBudgetRequest {
    pub department: String,
    pub fiscal_year: String,
    pub allocated: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JournalEntryDto {
    pub id: String,
    pub tenant_id: String,
    pub entry_number: String,
    pub description: String,
    pub debit: f64,
    pub credit: f64,
    pub account: String,
    pub posted_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PostJournalEntryRequest {
    pub description: String,
    pub debit: f64,
    pub credit: f64,
    pub account: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRollupDto {
    pub id: String,
    pub tenant_id: String,
    pub product_id: String,
    pub material_cost: f64,
    pub labor_cost: f64,
    pub overhead_cost: f64,
    pub total_cost: f64,
    pub currency: String,
    pub calculated_at: String,
}

pub struct FinanceApi;

impl FinanceApi {
    // ---- Invoices ----
    pub async fn list_invoices(client: &ApiClient) -> Result<Vec<InvoiceDto>, ApiError> {
        client.get("/api/v1/finance/invoices").await
    }

    pub async fn get_invoice(client: &ApiClient, id: &str) -> Result<InvoiceDto, ApiError> {
        client.get(&format!("/api/v1/finance/invoices/{}", id)).await
    }

    pub async fn create_invoice(client: &ApiClient, req: &CreateInvoiceRequest) -> Result<InvoiceDto, ApiError> {
        client.post("/api/v1/finance/invoices", req).await
    }

    // ---- Payments ----
    pub async fn list_payments(client: &ApiClient) -> Result<Vec<PaymentDto>, ApiError> {
        client.get("/api/v1/finance/payments").await
    }

    pub async fn record_payment(client: &ApiClient, req: &RecordPaymentRequest) -> Result<PaymentDto, ApiError> {
        client.post("/api/v1/finance/payments", req).await
    }

    // ---- Budgets ----
    pub async fn list_budgets(client: &ApiClient) -> Result<Vec<BudgetDto>, ApiError> {
        client.get("/api/v1/finance/budgets").await
    }

    pub async fn create_budget(client: &ApiClient, req: &CreateBudgetRequest) -> Result<BudgetDto, ApiError> {
        client.post("/api/v1/finance/budgets", req).await
    }

    // ---- Journal Entries ----
    pub async fn list_journal_entries(client: &ApiClient) -> Result<Vec<JournalEntryDto>, ApiError> {
        client.get("/api/v1/finance/journal-entries").await
    }

    pub async fn post_journal_entry(client: &ApiClient, req: &PostJournalEntryRequest) -> Result<JournalEntryDto, ApiError> {
        client.post("/api/v1/finance/journal-entries", req).await
    }

    // ---- Cost Rollups ----
    pub async fn list_cost_rollups(client: &ApiClient) -> Result<Vec<CostRollupDto>, ApiError> {
        client.get("/api/v1/finance/cost-rollups").await
    }

    pub async fn run_cost_rollup(client: &ApiClient, product_id: &str) -> Result<CostRollupDto, ApiError> {
        client.post(&format!("/api/v1/finance/cost-rollups/{}", product_id), &serde_json::json!({})).await
    }
}

//! Finance route handlers.
//!
//! Provides endpoints for invoice management, payment recording, budgeting,
//! journal entries, and cost rollups.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_services::finance::{Budget, CostRollup, Invoice, JournalEntry, Payment};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing invoices.
#[derive(Debug, Deserialize)]
pub struct ListInvoicesParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing payments.
#[derive(Debug, Deserialize)]
pub struct ListPaymentsParams {
    pub invoice_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing budgets.
#[derive(Debug, Deserialize)]
pub struct ListBudgetsParams {
    pub fiscal_year: Option<i32>,
    pub department: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing journal entries.
#[derive(Debug, Deserialize)]
pub struct ListJournalEntriesParams {
    pub account: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for marking an invoice as paid.
#[derive(Debug, Deserialize)]
pub struct MarkInvoicePaidRequest {
    pub payment_id: Uuid,
}

/// Request body for budget allocation.
#[derive(Debug, Deserialize)]
pub struct AllocateBudgetRequest {
    pub amount: rust_decimal::Decimal,
}

/// Request body for cost rollup.
#[derive(Debug, Deserialize)]
pub struct CostRollupRequest {
    pub product_id: Uuid,
}

/// Request body for the AP 3-way match.
#[derive(Debug, Deserialize)]
pub struct ThreeWayMatchRequest {
    /// The purchase order to match against.
    pub po_id: Uuid,
    /// Goods receipts belonging to the PO.
    pub receipt_ids: Vec<Uuid>,
    /// The supplier invoice to match.
    pub invoice_id: Uuid,
}

// ── Invoices ───────────────────────────────────────────────────────────────

/// List all invoices with optional filters.
pub async fn list_invoices(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListInvoicesParams>,
) -> Result<Json<PaginatedResponse<Invoice>>> {
    user.require_permission("finance:invoice:read")?;

    let tenant_id = user.tenant_id;
    let invoices = state
        .finance_service
        .list_invoices(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(invoices))
}

/// Create a new invoice.
pub async fn create_invoice(
    user: AuthenticatedUser,
    idem_key: crate::middleware::idempotency::OptionalIdempotencyKey,
    State(state): State<AppState>,
    Json(req): Json<Invoice>,
) -> Result<Json<Invoice>> {
    user.require_permission("finance:invoice:create")?;

    let tenant_id = user.tenant_id;
    // The actor always comes from the token — never from client JSON.
    let mut invoice = req;
    invoice.created_by = user.user_id;
    let invoice = state
        .finance_service
        .create_invoice(tenant_id, invoice, idem_key.0.as_deref())
        .await?;
    Ok(Json(invoice))
}

/// Get a specific invoice by ID.
pub async fn get_invoice(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Invoice>> {
    user.require_permission("finance:invoice:read")?;
    user.require_permission("finance:invoice:read")?;

    let tenant_id = user.tenant_id;
    let invoice = state.finance_service.get_invoice(tenant_id, id).await?;
    Ok(Json(invoice))
}

/// Mark an invoice as paid.
pub async fn mark_invoice_paid(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<MarkInvoicePaidRequest>,
) -> Result<Json<Invoice>> {
    user.require_permission("finance:invoice:approve")?;

    let tenant_id = user.tenant_id;
    let invoice = state
        .finance_service
        .mark_invoice_paid(tenant_id, id, req.payment_id)
        .await?;
    Ok(Json(invoice))
}

/// Update an invoice.
pub async fn update_invoice(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Invoice>,
) -> Result<Json<Invoice>> {
    user.require_permission("finance:invoice:create")?;
    user.require_permission("finance:invoice:update")?;

    let tenant_id = user.tenant_id;
    let invoice = state
        .finance_service
        .update_invoice(tenant_id, id, req)
        .await?;
    Ok(Json(invoice))
}

/// Delete an invoice.
pub async fn delete_invoice(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("finance:invoice:create")?;
    user.require_permission("finance:invoice:void")?;

    let tenant_id = user.tenant_id;
    state.finance_service.delete_invoice(tenant_id, id).await?;
    Ok(Json(()))
}

// ── Payments ───────────────────────────────────────────────────────────────

/// Record a payment.
pub async fn record_payment(
    user: AuthenticatedUser,
    idem_key: crate::middleware::idempotency::OptionalIdempotencyKey,
    State(state): State<AppState>,
    Json(req): Json<Payment>,
) -> Result<Json<Payment>> {
    user.require_permission("finance:payment:record")?;

    let tenant_id = user.tenant_id;
    let mut payment = req;
    payment.created_by = user.user_id;
    let payment = state
        .finance_service
        .record_payment(tenant_id, payment, idem_key.0.as_deref())
        .await?;
    Ok(Json(payment))
}

/// List payments with optional filters.
pub async fn list_payments(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListPaymentsParams>,
) -> Result<Json<PaginatedResponse<Payment>>> {
    user.require_permission("finance:invoice:read")?;
    user.require_permission("finance:payment:read")?;

    let tenant_id = user.tenant_id;
    let payments = state
        .finance_service
        .list_payments(tenant_id, params.invoice_id, params.page, params.per_page)
        .await?;
    Ok(Json(payments))
}

/// Update a payment.
pub async fn update_payment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Payment>,
) -> Result<Json<Payment>> {
    user.require_permission("finance:payment:void")?;
    user.require_permission("finance:payment:reverse")?;

    let tenant_id = user.tenant_id;
    let payment = state
        .finance_service
        .update_payment(tenant_id, id, req)
        .await?;
    Ok(Json(payment))
}

/// Delete a payment.
pub async fn delete_payment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("finance:payment:void")?;
    user.require_permission("finance:payment:reverse")?;

    let tenant_id = user.tenant_id;
    state.finance_service.delete_payment(tenant_id, id).await?;
    Ok(Json(()))
}

// ── Budgets ────────────────────────────────────────────────────────────────

/// List all budgets with optional filters.
pub async fn list_budgets(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListBudgetsParams>,
) -> Result<Json<PaginatedResponse<Budget>>> {
    user.require_permission("finance:budget:allocate")?;
    user.require_permission("finance:budget:read")?;

    let tenant_id = user.tenant_id;
    let budgets = state
        .finance_service
        .list_budgets(
            tenant_id,
            params.fiscal_year,
            params.department.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(budgets))
}

/// Create a new budget.
pub async fn create_budget(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Budget>,
) -> Result<Json<Budget>> {
    user.require_permission("finance:budget:allocate")?;
    user.require_permission("finance:budget:create")?;

    let tenant_id = user.tenant_id;
    let budget = state.finance_service.create_budget(tenant_id, req).await?;
    Ok(Json(budget))
}

/// Get a specific budget by ID.
pub async fn get_budget(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Budget>> {
    user.require_permission("finance:budget:allocate")?;
    user.require_permission("finance:budget:read")?;

    let tenant_id = user.tenant_id;
    let budget = state.finance_service.get_budget(tenant_id, id).await?;
    Ok(Json(budget))
}

/// Allocate budget amount.
pub async fn allocate_budget(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<AllocateBudgetRequest>,
) -> Result<Json<Budget>> {
    user.require_permission("finance:budget:allocate")?;
    user.require_permission("finance:budget:allocate")?;

    let tenant_id = user.tenant_id;
    let budget = state
        .finance_service
        .allocate_budget(tenant_id, id, req.amount)
        .await?;
    Ok(Json(budget))
}

/// Update a budget.
pub async fn update_budget(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Budget>,
) -> Result<Json<Budget>> {
    user.require_permission("finance:budget:allocate")?;
    user.require_permission("finance:budget:allocate")?;

    let tenant_id = user.tenant_id;
    let budget = state
        .finance_service
        .update_budget(tenant_id, id, req)
        .await?;
    Ok(Json(budget))
}

/// Delete a budget.
pub async fn delete_budget(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("finance:budget:allocate")?;
    user.require_permission("finance:budget:approve")?;

    let tenant_id = user.tenant_id;
    state.finance_service.delete_budget(tenant_id, id).await?;
    Ok(Json(()))
}

// ── Journal Entries ────────────────────────────────────────────────────────

/// Post a new journal entry.
pub async fn post_journal_entry(
    user: AuthenticatedUser,
    idem_key: crate::middleware::idempotency::OptionalIdempotencyKey,
    State(state): State<AppState>,
    Json(req): Json<JournalEntry>,
) -> Result<Json<JournalEntry>> {
    user.require_permission("finance:journal:post")?;

    let tenant_id = user.tenant_id;
    // posted_by is a server-generated identity field: the request can never
    // claim a different actor.
    let mut req = req;
    req.posted_by = user.user_id;
    let entry = state
        .finance_service
        .post_journal_entry(tenant_id, req, idem_key.0.as_deref())
        .await?;
    Ok(Json(entry))
}

/// Reverse a posted journal entry (correction-by-reversal).
pub async fn reverse_journal_entry(
    user: AuthenticatedUser,
    idem_key: crate::middleware::idempotency::OptionalIdempotencyKey,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<JournalEntry>> {
    user.require_permission("finance:journal:reverse")?;

    let tenant_id = user.tenant_id;
    let reversal = state
        .finance_service
        .reverse_journal_entry(tenant_id, id, user.user_id, idem_key.0.as_deref())
        .await?;
    Ok(Json(reversal))
}

/// List journal entries with optional filters.
pub async fn list_journal_entries(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListJournalEntriesParams>,
) -> Result<Json<PaginatedResponse<JournalEntry>>> {
    user.require_permission("finance:journal:post")?;
    user.require_permission("finance:journal:read")?;

    let tenant_id = user.tenant_id;
    let entries = state
        .finance_service
        .list_journal_entries(
            tenant_id,
            params.account.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(entries))
}

/// Update a journal entry.
pub async fn update_journal_entry(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<JournalEntry>,
) -> Result<Json<JournalEntry>> {
    user.require_permission("finance:journal:post")?;
    user.require_permission("finance:journal:reverse")?;

    let tenant_id = user.tenant_id;
    // Posted accounting entries are immutable: corrections must be
    // reversing entries, not history edits.
    let existing = state
        .finance_service
        .get_journal_entry(tenant_id, id)
        .await?;
    if existing.posted_by != uuid::Uuid::nil() {
        return Err(SenseiError::Conflict(
            "Posted journal entries are immutable — post a reversing entry instead".to_string(),
        ));
    }
    let entry = state
        .finance_service
        .update_journal_entry(tenant_id, id, req)
        .await?;
    Ok(Json(entry))
}

/// Delete a journal entry.
pub async fn delete_journal_entry(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("finance:journal:post")?;
    user.require_permission("finance:journal:reverse")?;

    let tenant_id = user.tenant_id;
    let existing = state
        .finance_service
        .get_journal_entry(tenant_id, id)
        .await?;
    if existing.posted_by != uuid::Uuid::nil() {
        return Err(SenseiError::Conflict(
            "Posted journal entries are immutable — post a reversing entry instead".to_string(),
        ));
    }
    state
        .finance_service
        .delete_journal_entry(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ── Cost Rollups ───────────────────────────────────────────────────────────

/// Run a cost rollup for a product.
pub async fn run_cost_rollup(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CostRollupRequest>,
) -> Result<Json<CostRollup>> {
    user.require_permission("finance:rollup:run")?;

    let tenant_id = user.tenant_id;
    let rollup = state
        .finance_service
        .run_cost_rollup(tenant_id, req.product_id)
        .await?;
    Ok(Json(rollup))
}

/// Get the cost rollup for a product.
pub async fn get_cost_rollup(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(product_id): Path<Uuid>,
) -> Result<Json<CostRollup>> {
    user.require_permission("finance:rollup:run")?;

    let tenant_id = user.tenant_id;
    let rollup = state
        .finance_service
        .get_cost_rollup(tenant_id, product_id)
        .await?;
    Ok(Json(rollup))
}

// ── AP 3-Way Matching ─────────────────────────────────────────────────────

/// Match a purchase order against its goods receipts and a supplier invoice.
///
/// Delegates the whole comparison to the finance service, which verifies
/// ownership and computes per-line verdicts; service `Validation` errors
/// surface as 400 responses.
pub async fn match_three_way(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ThreeWayMatchRequest>,
) -> Result<Json<sensei_services::finance::ThreeWayMatchResult>> {
    user.require_permission("finance:match:three-way")?;

    let tenant_id = user.tenant_id;
    let result = state
        .finance_service
        .match_three_way(tenant_id, req.po_id, req.receipt_ids, req.invoice_id)
        .await?;
    Ok(Json(result))
}

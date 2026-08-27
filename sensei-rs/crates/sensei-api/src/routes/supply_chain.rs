//! Supply Chain route handlers.
//!
//! Provides endpoints for RFQ, quotes, sales orders, purchase orders,
//! inventory management, and stock movements.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::supply_chain::{
    InventoryItem, PurchaseOrder, Quote, SalesOrder, StockMove, RFQ,
};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing RFQs.
#[derive(Debug, Deserialize)]
pub struct ListRfqsParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing quotes.
#[derive(Debug, Deserialize)]
pub struct ListQuotesParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing sales orders.
#[derive(Debug, Deserialize)]
pub struct ListSalesOrdersParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing purchase orders.
#[derive(Debug, Deserialize)]
pub struct ListPurchaseOrdersParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing inventory.
#[derive(Debug, Deserialize)]
pub struct ListInventoryParams {
    pub location: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing stock moves.
#[derive(Debug, Deserialize)]
pub struct ListStockMovesParams {
    pub product_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating RFQ status.
#[derive(Debug, Deserialize)]
pub struct UpdateRfqStatusRequest {
    pub status: String,
}

/// Request body for converting a quote to a purchase order.
#[derive(Debug, Deserialize)]
pub struct ConvertQuoteToOrderRequest {
    pub quote_id: Uuid,
}

/// Request body for updating sales order status.
#[derive(Debug, Deserialize)]
pub struct UpdateSalesOrderStatusRequest {
    pub status: String,
}

/// Request body for receiving a PO line.
#[derive(Debug, Deserialize)]
pub struct ReceivePoLineRequest {
    pub product_id: Uuid,
    pub quantity_received: i64,
}

/// Request body for inventory adjustment.
#[derive(Debug, Deserialize)]
pub struct AdjustInventoryRequest {
    pub product_id: Uuid,
    pub location: String,
    pub quantity_change: i64,
    pub reason: String,
}

// ── RFQs ───────────────────────────────────────────────────────────────────

/// Client input for creating an RFQ: only editable business fields. The
/// actor, tenant, ids and status are server-generated.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CreateRfqRequest {
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub items: Vec<sensei_services::supply_chain::RFQItem>,
    pub notes: String,
}

/// Client input for creating a quote.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CreateQuoteRequest {
    pub rfq_id: Option<Uuid>,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub line_items: Vec<sensei_services::supply_chain::QuoteLineItem>,
    pub currency: String,
    pub valid_until: chrono::DateTime<chrono::Utc>,
}

/// Client input for creating a sales order.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CreateSalesOrderRequest {
    pub customer_id: Uuid,
    pub customer_name: String,
    pub line_items: Vec<sensei_services::supply_chain::SalesOrderItem>,
    pub currency: String,
    pub delivery_date: Option<chrono::DateTime<chrono::Utc>>,
    pub shipping_address: String,
}

/// Client input for creating a purchase order.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CreatePurchaseOrderRequest {
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub line_items: Vec<sensei_services::supply_chain::POItem>,
    pub currency: String,
    pub expected_delivery: Option<chrono::DateTime<chrono::Utc>>,
}

/// List all RFQs with optional filters.
pub async fn list_rfqs(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListRfqsParams>,
) -> Result<Json<PaginatedResponse<RFQ>>> {
    user.require_permission("purchasing:rfq:manage")?;

    let tenant_id = user.tenant_id;
    let rfqs = state
        .supply_chain_service
        .list_rfqs(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(rfqs))
}

/// Create a new RFQ.
pub async fn create_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RFQ>,
) -> Result<Json<RFQ>> {
    user.require_permission("purchasing:rfq:create")?;
    let mut req = req;
    req.created_by = user.user_id;

    let tenant_id = user.tenant_id;
    let rfq = state
        .supply_chain_service
        .create_rfq(tenant_id, req)
        .await?;
    Ok(Json(rfq))
}

/// Get a specific RFQ by ID.
pub async fn get_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RFQ>> {
    user.require_permission("purchasing:rfq:manage")?;

    let tenant_id = user.tenant_id;
    let rfq = state.supply_chain_service.get_rfq(tenant_id, id).await?;
    Ok(Json(rfq))
}

/// Update an RFQ's status.
pub async fn update_rfq_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateRfqStatusRequest>,
) -> Result<Json<RFQ>> {
    user.require_permission("purchasing:rfq:submit")?;

    let tenant_id = user.tenant_id;
    let rfq = state
        .supply_chain_service
        .update_rfq_status(tenant_id, id, &req.status)
        .await?;
    Ok(Json(rfq))
}

// ── Quotes ─────────────────────────────────────────────────────────────────

/// List all quotes with optional filters.
pub async fn list_quotes(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListQuotesParams>,
) -> Result<Json<PaginatedResponse<Quote>>> {
    user.require_permission("purchasing:quote:create")?;

    let tenant_id = user.tenant_id;
    let quotes = state
        .supply_chain_service
        .list_quotes(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(quotes))
}

/// Create a new quote.
pub async fn create_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Quote>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:create")?;
    let mut req = req;
    req.created_by = user.user_id;

    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .create_quote(tenant_id, req)
        .await?;
    Ok(Json(quote))
}

/// Get a specific quote by ID.
pub async fn get_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:create")?;

    let tenant_id = user.tenant_id;
    let quote = state.supply_chain_service.get_quote(tenant_id, id).await?;
    Ok(Json(quote))
}

/// Approve a quote.
pub async fn approve_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:approve")?;

    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .approve_quote(tenant_id, id)
        .await?;
    Ok(Json(quote))
}

/// Convert a quote to a sales order.
pub async fn convert_quote_to_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ConvertQuoteToOrderRequest>,
) -> Result<Json<SalesOrder>> {
    user.require_permission("sales:order:create")?;

    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .convert_quote_to_order(tenant_id, req.quote_id, user.user_id)
        .await?;
    Ok(Json(order))
}

// ── Sales Orders ───────────────────────────────────────────────────────────

/// List all sales orders with optional filters.
pub async fn list_sales_orders(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListSalesOrdersParams>,
) -> Result<Json<PaginatedResponse<SalesOrder>>> {
    user.require_permission("sales:order:create")?;

    let tenant_id = user.tenant_id;
    let orders = state
        .supply_chain_service
        .list_sales_orders(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(orders))
}

/// Create a new sales order.
pub async fn create_sales_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<SalesOrder>,
) -> Result<Json<SalesOrder>> {
    user.require_permission("sales:order:create")?;
    let mut req = req;
    req.created_by = user.user_id;

    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .create_sales_order(tenant_id, req)
        .await?;
    Ok(Json(order))
}

/// Get a specific sales order by ID.
pub async fn get_sales_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<SalesOrder>> {
    user.require_permission("sales:order:create")?;

    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .get_sales_order(tenant_id, id)
        .await?;
    Ok(Json(order))
}

/// Update a sales order's status.
pub async fn update_sales_order_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateSalesOrderStatusRequest>,
) -> Result<Json<SalesOrder>> {
    user.require_permission("sales:order:status")?;

    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .update_sales_order_status(tenant_id, id, &req.status)
        .await?;
    Ok(Json(order))
}

// ── Purchase Orders ────────────────────────────────────────────────────────

/// List all purchase orders with optional filters.
pub async fn list_purchase_orders(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListPurchaseOrdersParams>,
) -> Result<Json<PaginatedResponse<PurchaseOrder>>> {
    let tenant_id = user.tenant_id;
    let orders = state
        .supply_chain_service
        .list_purchase_orders(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(orders))
}

/// Create a new purchase order.
pub async fn create_purchase_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PurchaseOrder>,
) -> Result<Json<PurchaseOrder>> {
    user.require_permission("purchasing:po:create")?;
    let mut req = req;
    req.created_by = user.user_id;

    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .create_purchase_order(tenant_id, req)
        .await?;
    Ok(Json(order))
}

/// Get a specific purchase order by ID.
pub async fn get_purchase_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PurchaseOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .get_purchase_order(tenant_id, id)
        .await?;
    Ok(Json(order))
}

/// Receive a line item on a purchase order.
pub async fn receive_po_line(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(po_id): Path<Uuid>,
    Json(req): Json<ReceivePoLineRequest>,
) -> Result<Json<PurchaseOrder>> {
    user.require_permission("purchasing:po:approve")?;

    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .receive_po_line(tenant_id, po_id, req.product_id, req.quantity_received)
        .await?;
    Ok(Json(order))
}

// ── Inventory ──────────────────────────────────────────────────────────────

/// List all inventory items with optional filters.
pub async fn list_inventory(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListInventoryParams>,
) -> Result<Json<PaginatedResponse<InventoryItem>>> {
    let tenant_id = user.tenant_id;
    let items = state
        .supply_chain_service
        .list_inventory(
            tenant_id,
            params.location.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(items))
}

/// Get inventory for a specific product across all locations.
pub async fn get_inventory(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(product_id): Path<Uuid>,
) -> Result<Json<Vec<InventoryItem>>> {
    let tenant_id = user.tenant_id;
    let items = state
        .supply_chain_service
        .get_inventory(tenant_id, product_id)
        .await?;
    Ok(Json(items))
}

/// Adjust inventory quantity for a product at a location.
pub async fn adjust_inventory(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<AdjustInventoryRequest>,
) -> Result<Json<InventoryItem>> {
    user.require_permission("inventory:adjust")?;

    let tenant_id = user.tenant_id;
    let item = state
        .supply_chain_service
        .adjust_inventory(
            tenant_id,
            req.product_id,
            &req.location,
            req.quantity_change,
            &req.reason,
        )
        .await?;
    Ok(Json(item))
}

// ── Stock Moves ────────────────────────────────────────────────────────────

/// Create a stock movement.
pub async fn create_stock_move(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<StockMove>,
) -> Result<Json<StockMove>> {
    user.require_permission("inventory:move")?;

    let tenant_id = user.tenant_id;
    let stock_move = state
        .supply_chain_service
        .create_stock_move(tenant_id, req)
        .await?;
    Ok(Json(stock_move))
}

/// List stock movements with optional product filter.
pub async fn list_stock_moves(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListStockMovesParams>,
) -> Result<Json<PaginatedResponse<StockMove>>> {
    let tenant_id = user.tenant_id;
    let moves = state
        .supply_chain_service
        .list_stock_moves(tenant_id, params.product_id, params.page, params.per_page)
        .await?;
    Ok(Json(moves))
}

// ── New: Update / Delete / Submit / Cancel / Accept / Reject ──────────────

/// Update an RFQ.
pub async fn update_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<RFQ>,
) -> Result<Json<RFQ>> {
    user.require_permission("purchasing:rfq:update")?;

    let tenant_id = user.tenant_id;
    let rfq = state
        .supply_chain_service
        .update_rfq(tenant_id, id, req)
        .await?;
    Ok(Json(rfq))
}

/// Delete an RFQ.
pub async fn delete_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("purchasing:rfq:delete")?;

    let tenant_id = user.tenant_id;
    state.supply_chain_service.delete_rfq(tenant_id, id).await?;
    Ok(Json(()))
}

/// Submit an RFQ (change status to "sent").
pub async fn submit_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RFQ>> {
    user.require_permission("purchasing:rfq:submit")?;

    let tenant_id = user.tenant_id;
    let rfq = state.supply_chain_service.submit_rfq(tenant_id, id).await?;
    Ok(Json(rfq))
}

/// Cancel an RFQ.
pub async fn cancel_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RFQ>> {
    user.require_permission("purchasing:rfq:cancel")?;

    let tenant_id = user.tenant_id;
    let rfq = state.supply_chain_service.cancel_rfq(tenant_id, id).await?;
    Ok(Json(rfq))
}

/// Update a quote.
pub async fn update_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Quote>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:update")?;

    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .update_quote(tenant_id, id, req)
        .await?;
    Ok(Json(quote))
}

/// Delete a quote.
pub async fn delete_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("purchasing:quote:update")?;

    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_quote(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Submit a quote (change status to "submitted").
pub async fn submit_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:update")?;

    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .submit_quote(tenant_id, id)
        .await?;
    Ok(Json(quote))
}

/// Accept a quote.
pub async fn accept_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:approve")?;

    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .accept_quote(tenant_id, id)
        .await?;
    Ok(Json(quote))
}

/// Reject a quote.
pub async fn reject_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Quote>> {
    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .reject_quote(tenant_id, id)
        .await?;
    Ok(Json(quote))
}

/// Update a sales order.
pub async fn update_sales_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<SalesOrder>,
) -> Result<Json<SalesOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .supply_chain_service
        .update_sales_order(tenant_id, id, req)
        .await?;
    Ok(Json(order))
}

/// Delete a sales order.
pub async fn delete_sales_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_sales_order(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a purchase order.
pub async fn update_purchase_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PurchaseOrder>,
) -> Result<Json<PurchaseOrder>> {
    user.require_permission("purchasing:po:create")?;

    let tenant_id = user.tenant_id;
    let po = state
        .supply_chain_service
        .update_purchase_order(tenant_id, id, req)
        .await?;
    Ok(Json(po))
}

/// Delete a purchase order.
pub async fn delete_purchase_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("purchasing:po:create")?;

    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_purchase_order(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Receive all line items on a purchase order.
pub async fn receive_full_po(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PurchaseOrder>> {
    let tenant_id = user.tenant_id;
    let po = state
        .supply_chain_service
        .receive_full_po(tenant_id, id)
        .await?;
    Ok(Json(po))
}

/// Update an inventory item.
pub async fn update_inventory(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<InventoryItem>,
) -> Result<Json<InventoryItem>> {
    let tenant_id = user.tenant_id;
    let item = state
        .supply_chain_service
        .update_inventory(tenant_id, id, req)
        .await?;
    Ok(Json(item))
}

/// Delete an inventory item.
pub async fn delete_inventory(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_inventory(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Delete a stock movement.
pub async fn delete_stock_move(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_stock_move(tenant_id, id)
        .await?;
    Ok(Json(()))
}

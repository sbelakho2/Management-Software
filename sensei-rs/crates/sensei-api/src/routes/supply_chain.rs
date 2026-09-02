//! Supply Chain route handlers.
//!
//! Provides endpoints for RFQ, quotes, sales orders, purchase orders,
//! inventory management, and stock movements.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::request_context::RequestContext;
use sensei_core::error::{Result, SenseiError};
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
    /// Optional SITE the caller wants the order anchored to when the
    /// status is `confirmed` (twenty-second audit P1): the site must be
    /// in the caller's entitlement sites, otherwise the request is
    /// Forbidden. The order's fulfilling site is only filled when it is
    /// still unset.
    #[serde(default)]
    pub requested_site_id: Option<Uuid>,
}

/// Client input for creating a sales order: ONLY the editable business
/// fields (twenty-second audit P2). Identity (`id`), ownership
/// (`tenant_id`, `created_by`, `order_number`, `status`) and the site
/// anchor are server-derived — the caller can at most REQUEST a site
/// that the handler intersects with the caller's entitlement.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CreateSalesOrderRequest {
    pub customer_id: Uuid,
    pub customer_name: String,
    pub line_items: Vec<sensei_services::supply_chain::SalesOrderItem>,
    pub currency: String,
    pub delivery_date: Option<chrono::DateTime<chrono::Utc>>,
    pub shipping_address: String,
    /// Optional requested fulfilling site; accepted ONLY when it is in
    /// the caller's entitlement sites (else 403). Defaults to the
    /// caller's ACTIVE site when unset and the caller is site-bound.
    #[serde(default)]
    pub requested_site_id: Option<Uuid>,
}

/// Client input for creating a purchase order: ONLY the editable
/// business fields. Identity/ownership (`id`, `tenant_id`, `created_by`,
/// `po_number`, `status`) and the receiving-site anchor are
/// server-derived; `requested_site_id` is intersected with the caller's
/// entitlement (else 403).
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CreatePurchaseOrderRequest {
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub line_items: Vec<sensei_services::supply_chain::POItem>,
    pub currency: String,
    pub expected_delivery: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub requested_site_id: Option<Uuid>,
}

/// Client input for updating a sales order: the mutable business fields
/// only — identity, status (use the status endpoint), timestamps and the
/// IMMUTABLE fulfilling site can never be rewritten through this body.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct UpdateSalesOrderRequest {
    pub customer_id: Uuid,
    pub customer_name: String,
    pub line_items: Vec<sensei_services::supply_chain::SalesOrderItem>,
    pub currency: String,
    pub delivery_date: Option<chrono::DateTime<chrono::Utc>>,
    pub shipping_address: String,
}

/// Client input for updating a purchase order: the mutable business
/// fields only — identity, status, timestamps and the IMMUTABLE
/// receiving site can never be rewritten through this body.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct UpdatePurchaseOrderRequest {
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub line_items: Vec<sensei_services::supply_chain::POItem>,
    pub currency: String,
    pub expected_delivery: Option<chrono::DateTime<chrono::Utc>>,
}

// ── Site-scope resolution (twenty-second audit P2) ────────────────────────

/// Full RequestContext scope resolution — the routes/andon.rs
/// `caller_sites` pattern replicated for supply-chain documents: the
/// caller's site scope comes from their ACTIVE role-slot assignments,
/// never from client input. Returns `None` when the deployment has no
/// database (in-memory mode has no sites to entangle).
async fn caller_scope(
    user: &AuthenticatedUser,
    state: &AppState,
) -> Result<Option<RequestContext>> {
    let Some(pool) = state.db_pool.as_ref() else {
        return Ok(None);
    };
    let ctx = crate::routes::agent::build_context(user, state).await;
    let rc = RequestContext::build(
        pool,
        user.tenant_id,
        user.user_id,
        ctx.site_id,
        ctx.value_stream_id,
        ctx.work_center_id,
        ctx.shift_id,
        String::new(),
    )
    .await?;
    Ok(Some(rc))
}

/// Intersect a client-requested site with the caller's entitlement: the
/// site is accepted ONLY when it is in the caller's entitlement sites,
/// otherwise Forbidden. Without a scope authority (in-memory mode) the
/// caller is not site-bound. When no site was requested, the caller's
/// ACTIVE site is used.
/// The caller's entitlement site set — None scope (in-memory/dev mode)
/// means the caller is not site-bound (permissive dev behavior).
fn entitlement_of(scope: &Option<RequestContext>) -> Option<&[Uuid]> {
    scope.as_ref().map(|rc| rc.authorized_sites())
}

fn resolve_site(
    scope: &Option<RequestContext>,
    requested_site_id: Option<Uuid>,
) -> Result<Option<Uuid>> {
    let Some(rc) = scope else {
        return Ok(requested_site_id);
    };
    if let Some(site) = requested_site_id {
        if !rc.entitlement_sites.contains(&site) {
            return Err(SenseiError::Forbidden(format!(
                "site {site} is not among the caller's entitlement sites"
            )));
        }
        Ok(Some(site))
    } else {
        Ok(rc.active_site)
    }
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
    // Twenty-second audit P0/P1: ordinary reads are scope-intersected —
    // a site-bound caller lists only their sites' orders; zero
    // entitlement lists nothing.
    let scope = caller_scope(&user, &state).await?;
    let orders = if entitlement_of(&scope).is_none_or(|sites| sites.is_empty()) {
        sensei_core::pagination::PaginatedResponse::new(Vec::new(), params.page, params.per_page)
    } else {
        state
            .supply_chain_service
            .list_sales_orders_scoped(
                tenant_id,
                entitlement_of(&scope).unwrap_or(&[]),
                params.status.as_deref(),
                params.page,
                params.per_page,
            )
            .await?
    };
    Ok(Json(orders))
}

/// Create a new sales order.
pub async fn create_sales_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateSalesOrderRequest>,
) -> Result<Json<SalesOrder>> {
    user.require_permission("sales:order:create")?;

    let tenant_id = user.tenant_id;
    // Twenty-second audit P2: the site anchor is SERVER-DERIVED from the
    // caller's RequestContext — the DTO site is accepted only when it is
    // in the caller's entitlement (else 403), and a site-bound caller
    // without a request falls back to their ACTIVE site.
    let scope = caller_scope(&user, &state).await?;
    let site_id = resolve_site(&scope, req.requested_site_id)?;
    let total: rust_decimal::Decimal = req
        .line_items
        .iter()
        .map(|li| rust_decimal::Decimal::from(li.quantity) * li.unit_price)
        .sum();
    let order = SalesOrder {
        id: Uuid::nil(),
        tenant_id,
        order_number: String::new(),
        customer_id: req.customer_id,
        customer_name: req.customer_name,
        status: String::new(),
        line_items: req.line_items,
        total_amount: total,
        currency: req.currency,
        delivery_date: req.delivery_date,
        shipping_address: req.shipping_address,
        created_by: user.user_id,
        created_at: chrono::Utc::now(),
        fulfilling_site_id: site_id,
    };
    let order = state
        .supply_chain_service
        .create_sales_order(tenant_id, order)
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
    let scope = caller_scope(&user, &state).await?;
    let order = if entitlement_of(&scope).is_none_or(|sites| sites.is_empty()) {
        return Err(sensei_core::error::SenseiError::NotFound(format!(
            "Sales order {id} not found"
        )));
    } else {
        state
            .supply_chain_service
            .get_sales_order_scoped(tenant_id, entitlement_of(&scope).unwrap_or(&[]), id)
            .await?
    };
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
    // Twenty-second audit P1: confirming a site-less order (quote →
    // order conversions name no site) is a dead end — the handler's
    // confirm path accepts an optional site (entitlement-intersected,
    // else 403) and confirms through the one-call service command.
    if req.status == "confirmed" {
        let scope = caller_scope(&user, &state).await?;
        let site_id = resolve_site(&scope, req.requested_site_id)?;
        if let Some(site_id) = site_id {
            let order = state
                .supply_chain_service
                .confirm_sales_order_with_site(tenant_id, id, site_id)
                .await?;
            return Ok(Json(order));
        }
    }
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
    user.require_permission("purchasing:po:create")?;
    let tenant_id = user.tenant_id;
    let scope = caller_scope(&user, &state).await?;
    let orders = if entitlement_of(&scope).is_none_or(|sites| sites.is_empty()) {
        sensei_core::pagination::PaginatedResponse::new(Vec::new(), params.page, params.per_page)
    } else {
        state
            .supply_chain_service
            .list_purchase_orders_scoped(
                tenant_id,
                entitlement_of(&scope).unwrap_or(&[]),
                params.status.as_deref(),
                params.page,
                params.per_page,
            )
            .await?
    };
    Ok(Json(orders))
}

/// Create a new purchase order.
pub async fn create_purchase_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreatePurchaseOrderRequest>,
) -> Result<Json<PurchaseOrder>> {
    user.require_permission("purchasing:po:create")?;

    let tenant_id = user.tenant_id;
    // Twenty-second audit P2: the receiving-site anchor is
    // SERVER-DERIVED from the caller's RequestContext — the DTO site is
    // accepted only when it is in the caller's entitlement (else 403),
    // and a site-bound caller without a request falls back to their
    // ACTIVE site.
    let scope = caller_scope(&user, &state).await?;
    let site_id = resolve_site(&scope, req.requested_site_id)?;
    let total: rust_decimal::Decimal = req
        .line_items
        .iter()
        .map(|li| rust_decimal::Decimal::from(li.quantity_ordered) * li.unit_price)
        .sum();
    let po = PurchaseOrder {
        id: Uuid::nil(),
        tenant_id,
        po_number: String::new(),
        supplier_id: req.supplier_id,
        supplier_name: req.supplier_name,
        status: String::new(),
        line_items: req.line_items,
        total_amount: total,
        currency: req.currency,
        expected_delivery: req.expected_delivery,
        created_by: user.user_id,
        created_at: chrono::Utc::now(),
        receiving_site_id: site_id,
    };
    let order = state
        .supply_chain_service
        .create_purchase_order(tenant_id, po)
        .await?;
    Ok(Json(order))
}

/// Get a specific purchase order by ID.
pub async fn get_purchase_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PurchaseOrder>> {
    user.require_permission("purchasing:po:read")?;
    let tenant_id = user.tenant_id;
    let scope = caller_scope(&user, &state).await?;
    let order = if entitlement_of(&scope).is_none_or(|sites| sites.is_empty()) {
        return Err(sensei_core::error::SenseiError::NotFound(format!(
            "Purchase order {id} not found"
        )));
    } else {
        state
            .supply_chain_service
            .get_purchase_order_scoped(tenant_id, entitlement_of(&scope).unwrap_or(&[]), id)
            .await?
    };
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
    user.require_permission("inventory:read")?;
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
    user.require_permission("inventory:read")?;
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
    user.require_permission("inventory:read")?;
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
    user.require_permission("purchasing:quote:approve")?;
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
    Json(req): Json<UpdateSalesOrderRequest>,
) -> Result<Json<SalesOrder>> {
    user.require_permission("sales:order:update")?;
    let tenant_id = user.tenant_id;
    // Twenty-second audit P2: a typed update body can only touch the
    // mutable business fields — identity, status (status endpoint),
    // timestamps and the IMMUTABLE fulfilling site stay with the
    // existing row (read-merge-write).
    let mut order = state
        .supply_chain_service
        .get_sales_order(tenant_id, id)
        .await?;
    order.customer_id = req.customer_id;
    order.customer_name = req.customer_name;
    order.line_items = req.line_items;
    order.currency = req.currency;
    order.delivery_date = req.delivery_date;
    order.shipping_address = req.shipping_address;
    order.total_amount = order
        .line_items
        .iter()
        .map(|li| rust_decimal::Decimal::from(li.quantity) * li.unit_price)
        .sum();
    let order = state
        .supply_chain_service
        .update_sales_order(tenant_id, id, order)
        .await?;
    Ok(Json(order))
}

/// Delete a sales order.
pub async fn delete_sales_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("sales:order:delete")?;
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
    Json(req): Json<UpdatePurchaseOrderRequest>,
) -> Result<Json<PurchaseOrder>> {
    user.require_permission("purchasing:po:create")?;

    let tenant_id = user.tenant_id;
    // Twenty-second audit P2: a typed update body can only touch the
    // mutable business fields — identity, status, timestamps and the
    // IMMUTABLE receiving site stay with the existing row
    // (read-merge-write).
    let mut po = state
        .supply_chain_service
        .get_purchase_order(tenant_id, id)
        .await?;
    po.supplier_id = req.supplier_id;
    po.supplier_name = req.supplier_name;
    po.line_items = req.line_items;
    po.currency = req.currency;
    po.expected_delivery = req.expected_delivery;
    po.total_amount = po
        .line_items
        .iter()
        .map(|li| rust_decimal::Decimal::from(li.quantity_ordered) * li.unit_price)
        .sum();
    let po = state
        .supply_chain_service
        .update_purchase_order(tenant_id, id, po)
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
    user.require_permission("purchasing:po:approve")?;
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
    user.require_permission("inventory:adjust")?;
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
    user.require_permission("inventory:adjust")?;
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
    user.require_permission("inventory:adjust")?;
    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_stock_move(tenant_id, id)
        .await?;
    Ok(Json(()))
}

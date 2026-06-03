//! Production / Manufacturing route handlers.
//!
//! Provides endpoints for work orders, production orders, BOM management,
//! and MRP (Material Requirements Planning).

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::production::{BOMItem, MRPRecord, ProductionOrder, WorkOrder};
use uuid::Uuid;

use crate::state::AppState;

/// Query parameters for listing work orders.
#[derive(Debug, Deserialize)]
pub struct ListWorkOrdersParams {
    pub status: Option<String>,
    pub work_center_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing production orders.
#[derive(Debug, Deserialize)]
pub struct ListProductionOrdersParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating work order status.
#[derive(Debug, Deserialize)]
pub struct UpdateWorkOrderStatusRequest {
    pub status: String,
}

/// Request body for reporting production.
#[derive(Debug, Deserialize)]
pub struct ReportProductionRequest {
    pub quantity_completed: i64,
    pub quantity_scrapped: i64,
}

/// Request body for running MRP.
#[derive(Debug, Deserialize)]
pub struct RunMrpRequest {
    pub product_id: Uuid,
}

// ── Work Orders ────────────────────────────────────────────────────────────

/// List all work orders with optional filters.
pub async fn list_work_orders(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWorkOrdersParams>,
) -> Result<Json<PaginatedResponse<WorkOrder>>> {
    let tenant_id = user.tenant_id;
    let orders = state
        .production_service
        .list_work_orders(tenant_id, params.status.as_deref(), params.work_center_id, params.page, params.per_page)
        .await?;
    Ok(Json(orders))
}

/// Create a new work order.
pub async fn create_work_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<WorkOrder>,
) -> Result<Json<WorkOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .create_work_order(tenant_id, req)
        .await?;
    Ok(Json(order))
}

/// Get a specific work order by ID.
pub async fn get_work_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<WorkOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .get_work_order(tenant_id, id)
        .await?;
    Ok(Json(order))
}

/// Update a work order's status.
pub async fn update_work_order_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateWorkOrderStatusRequest>,
) -> Result<Json<WorkOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .update_work_order_status(tenant_id, id, &req.status)
        .await?;
    Ok(Json(order))
}

/// Report production against a work order.
pub async fn report_production(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ReportProductionRequest>,
) -> Result<Json<WorkOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .report_production(tenant_id, id, req.quantity_completed, req.quantity_scrapped)
        .await?;
    Ok(Json(order))
}

// ── Production Orders ──────────────────────────────────────────────────────

/// List all production orders with optional filters.
pub async fn list_production_orders(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListProductionOrdersParams>,
) -> Result<Json<PaginatedResponse<ProductionOrder>>> {
    let tenant_id = user.tenant_id;
    let orders = state
        .production_service
        .list_production_orders(tenant_id, params.status.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(orders))
}

/// Create a new production order.
pub async fn create_production_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ProductionOrder>,
) -> Result<Json<ProductionOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .create_production_order(tenant_id, req)
        .await?;
    Ok(Json(order))
}

/// Get a specific production order by ID.
pub async fn get_production_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ProductionOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .get_production_order(tenant_id, id)
        .await?;
    Ok(Json(order))
}

/// Complete a production order.
pub async fn complete_production_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ProductionOrder>> {
    let tenant_id = user.tenant_id;
    let order = state
        .production_service
        .complete_production_order(tenant_id, id)
        .await?;
    Ok(Json(order))
}

// ── BOM (Bill of Materials) ────────────────────────────────────────────────

/// Add a BOM item.
pub async fn add_bom_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<BOMItem>,
) -> Result<Json<BOMItem>> {
    let tenant_id = user.tenant_id;
    let item = state
        .production_service
        .add_bom_item(tenant_id, req)
        .await?;
    Ok(Json(item))
}

/// Get the BOM for a product.
pub async fn get_bom(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(product_id): Path<Uuid>,
) -> Result<Json<Vec<BOMItem>>> {
    let tenant_id = user.tenant_id;
    let bom = state
        .production_service
        .get_bom(tenant_id, product_id)
        .await?;
    Ok(Json(bom))
}

// ── MRP (Material Requirements Planning) ───────────────────────────────────

/// Run MRP for a product.
pub async fn run_mrp(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RunMrpRequest>,
) -> Result<Json<Vec<MRPRecord>>> {
    let tenant_id = user.tenant_id;
    let records = state
        .production_service
        .run_mrp(tenant_id, req.product_id)
        .await?;
    Ok(Json(records))
}

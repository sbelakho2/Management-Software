//! RFQ management route handlers.
//!
//! Provides endpoints for managing Requests for Quotation (RFQs)
//! and their line items, delegating to the supply chain service.

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::supply_chain::{RFQ, RFQItem};
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

/// Request body for creating/updating an RFQ.
#[derive(Debug, Deserialize)]
pub struct RfqRequest {
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub notes: String,
}

/// Request body for adding/updating an RFQ line item.
#[derive(Debug, Deserialize)]
pub struct RfqLineItemRequest {
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: i64,
    pub unit_of_measure: String,
    pub target_price: Option<f64>,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Generate an RFQ number: `RFQ-YYYYMMDD-{8 hex chars}`.
fn generate_rfq_number() -> String {
    let date = chrono::Utc::now().format("%Y%m%d");
    let suffix: String = Uuid::new_v4()
        .as_simple()
        .encode_lower(&mut Uuid::encode_buffer())[..8]
        .to_string();
    format!("RFQ-{date}-{suffix}")
}

/// List all RFQs with optional filters.
pub async fn list_rfqs(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListRfqsParams>,
) -> Result<Json<PaginatedResponse<RFQ>>> {
    let tenant_id = user.tenant_id;
    let rfqs = state
        .supply_chain_service
        .list_rfqs(tenant_id, params.status.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(rfqs))
}

/// Create a new RFQ.
pub async fn create_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RfqRequest>,
) -> Result<Json<RFQ>> {
    let tenant_id = user.tenant_id;
    let rfq = RFQ {
        id: Uuid::new_v4(),
        tenant_id,
        rfq_number: generate_rfq_number(),
        supplier_id: req.supplier_id,
        supplier_name: req.supplier_name,
        status: "draft".to_string(),
        items: Vec::new(),
        notes: req.notes,
        created_by: user.user_id,
        created_at: chrono::Utc::now(),
    };
    let created = state.supply_chain_service.create_rfq(tenant_id, rfq).await?;
    Ok(Json(created))
}

/// Get a specific RFQ by ID.
pub async fn get_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RFQ>> {
    let tenant_id = user.tenant_id;
    let rfq = state.supply_chain_service.get_rfq(tenant_id, id).await?;
    Ok(Json(rfq))
}

/// Update an RFQ.
pub async fn update_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<RfqRequest>,
) -> Result<Json<RFQ>> {
    let tenant_id = user.tenant_id;
    let mut rfq = state.supply_chain_service.get_rfq(tenant_id, id).await?;
    rfq.supplier_id = req.supplier_id;
    rfq.supplier_name = req.supplier_name;
    rfq.notes = req.notes;
    let updated = state.supply_chain_service.update_rfq(tenant_id, id, rfq).await?;
    Ok(Json(updated))
}

/// Delete an RFQ.
pub async fn delete_rfq(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state.supply_chain_service.delete_rfq(tenant_id, id).await?;
    Ok(Json(()))
}

/// Add a line item to an RFQ.
pub async fn add_rfq_line_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(rfq_id): Path<Uuid>,
    Json(req): Json<RfqLineItemRequest>,
) -> Result<Json<RFQItem>> {
    let tenant_id = user.tenant_id;
    let item = RFQItem {
        line_item_id: Some(Uuid::new_v4()),
        product_id: req.product_id,
        product_name: req.product_name,
        quantity: req.quantity,
        unit_of_measure: req.unit_of_measure,
        target_price: req.target_price,
    };

    let mut rfq = state.supply_chain_service.get_rfq(tenant_id, rfq_id).await?;
    rfq.items.push(item.clone());
    state.supply_chain_service.update_rfq(tenant_id, rfq_id, rfq).await?;
    Ok(Json(item))
}

/// Update a line item within an RFQ.
///
/// The path `{item_id}` refers to the line item's stable `line_item_id`,
/// not the product id.
pub async fn update_rfq_line_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((rfq_id, item_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<RfqLineItemRequest>,
) -> Result<Json<RFQItem>> {
    let tenant_id = user.tenant_id;
    let mut rfq = state.supply_chain_service.get_rfq(tenant_id, rfq_id).await?;
    let item = rfq
        .items
        .iter_mut()
        .find(|i| i.line_item_id == Some(item_id))
        .ok_or_else(|| {
            sensei_core::error::SenseiError::NotFound(format!(
                "Line item {item_id} not found in RFQ {rfq_id}"
            ))
        })?;
    item.product_name = req.product_name;
    item.quantity = req.quantity;
    item.unit_of_measure = req.unit_of_measure;
    item.target_price = req.target_price;

    let updated_item = item.clone();
    state.supply_chain_service.update_rfq(tenant_id, rfq_id, rfq).await?;
    Ok(Json(updated_item))
}

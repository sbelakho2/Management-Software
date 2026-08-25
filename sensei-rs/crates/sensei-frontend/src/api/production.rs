//! Production management API endpoints.
//!
//! Work Orders, Production Orders, Bill of Materials, MRP.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderDto {
    pub id: String,
    pub tenant_id: String,
    pub work_order_number: String,
    pub product_id: String,
    pub quantity: f64,
    pub quantity_completed: Option<f64>,
    pub status: String,
    pub priority: String,
    pub due_date: Option<String>,
    pub assigned_to: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateWorkOrderRequest {
    pub product_id: String,
    pub quantity: f64,
    pub priority: String,
    pub due_date: Option<String>,
    pub assigned_to: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionOrderDto {
    pub id: String,
    pub tenant_id: String,
    pub production_order_number: String,
    pub product_id: String,
    pub planned_quantity: f64,
    pub produced_quantity: Option<f64>,
    pub status: String,
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateProductionOrderRequest {
    pub product_id: String,
    pub planned_quantity: f64,
    pub start_date: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BomItemDto {
    pub id: String,
    pub tenant_id: String,
    pub product_id: String,
    pub component_id: String,
    pub quantity: f64,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddBomItemRequest {
    pub product_id: String,
    pub component_id: String,
    pub quantity: f64,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MrpRecordDto {
    pub id: String,
    pub tenant_id: String,
    pub product_id: String,
    pub gross_requirement: f64,
    pub scheduled_receipts: f64,
    pub projected_on_hand: f64,
    pub net_requirement: f64,
    pub planned_order_release: Option<f64>,
    pub period: String,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct ProductionApi;

impl ProductionApi {
    // ---- Work Orders ----
    pub async fn list_work_orders(client: &ApiClient) -> Result<Vec<WorkOrderDto>, ApiError> {
        client.get("/api/v1/production/work-orders").await
    }

    pub async fn get_work_order(client: &ApiClient, id: &str) -> Result<WorkOrderDto, ApiError> {
        client
            .get(&format!("/api/v1/production/work-orders/{}", id))
            .await
    }

    pub async fn create_work_order(
        client: &ApiClient,
        req: &CreateWorkOrderRequest,
    ) -> Result<WorkOrderDto, ApiError> {
        client.post("/api/v1/production/work-orders", req).await
    }

    pub async fn update_work_order_status(
        client: &ApiClient,
        id: &str,
        status: &str,
    ) -> Result<WorkOrderDto, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> {
            status: &'a str,
        }
        client
            .put(
                &format!("/api/v1/production/work-orders/{}/status", id),
                &Body { status },
            )
            .await
    }

    // ---- Production Orders ----
    pub async fn list_production_orders(
        client: &ApiClient,
    ) -> Result<Vec<ProductionOrderDto>, ApiError> {
        client.get("/api/v1/production/orders").await
    }

    pub async fn get_production_order(
        client: &ApiClient,
        id: &str,
    ) -> Result<ProductionOrderDto, ApiError> {
        client
            .get(&format!("/api/v1/production/orders/{}", id))
            .await
    }

    pub async fn create_production_order(
        client: &ApiClient,
        req: &CreateProductionOrderRequest,
    ) -> Result<ProductionOrderDto, ApiError> {
        client.post("/api/v1/production/orders", req).await
    }

    // ---- BOM ----
    pub async fn get_bom(
        client: &ApiClient,
        product_id: &str,
    ) -> Result<Vec<BomItemDto>, ApiError> {
        client
            .get(&format!("/api/v1/production/bom/{}", product_id))
            .await
    }

    pub async fn add_bom_item(
        client: &ApiClient,
        req: &AddBomItemRequest,
    ) -> Result<BomItemDto, ApiError> {
        client.post("/api/v1/production/bom", req).await
    }

    // ---- MRP ----
    pub async fn run_mrp(
        client: &ApiClient,
        product_id: &str,
    ) -> Result<Vec<MrpRecordDto>, ApiError> {
        client
            .post(
                &format!("/api/v1/production/mrp/{}", product_id),
                &serde_json::json!({}),
            )
            .await
    }
}

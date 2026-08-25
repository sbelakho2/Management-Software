//! Supply Chain API endpoints.
//!
//! RFQs, Quotes, Sales Orders, Purchase Orders, Inventory, Stock Moves.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqDto {
    pub id: String,
    pub tenant_id: String,
    pub rfq_number: String,
    pub supplier_id: String,
    pub status: String,
    pub items: Vec<RfqItemDto>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqItemDto {
    pub id: String,
    pub product_id: String,
    pub quantity: f64,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateRfqRequest {
    pub supplier_id: String,
    pub items: Vec<RfqItemRequest>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfqItemRequest {
    pub product_id: String,
    pub quantity: f64,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteDto {
    pub id: String,
    pub tenant_id: String,
    pub quote_number: String,
    pub rfq_id: Option<String>,
    pub supplier_id: String,
    pub status: String,
    pub total: f64,
    pub currency: String,
    pub valid_until: Option<String>,
    pub line_items: Vec<QuoteLineItemDto>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteLineItemDto {
    pub id: String,
    pub product_id: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SalesOrderDto {
    pub id: String,
    pub tenant_id: String,
    pub sales_order_number: String,
    pub customer_id: String,
    pub status: String,
    pub total: f64,
    pub currency: String,
    pub items: Vec<SalesOrderItemDto>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SalesOrderItemDto {
    pub id: String,
    pub product_id: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PurchaseOrderDto {
    pub id: String,
    pub tenant_id: String,
    pub po_number: String,
    pub supplier_id: String,
    pub status: String,
    pub total: f64,
    pub currency: String,
    pub items: Vec<PoItemDto>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoItemDto {
    pub id: String,
    pub product_id: String,
    pub quantity_ordered: f64,
    pub quantity_received: f64,
    pub unit_price: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InventoryItemDto {
    pub id: String,
    pub tenant_id: String,
    pub product_id: String,
    pub product_name: String,
    pub quantity_on_hand: f64,
    pub quantity_reserved: f64,
    pub quantity_available: f64,
    pub location: Option<String>,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StockMoveDto {
    pub id: String,
    pub tenant_id: String,
    pub product_id: String,
    pub quantity: f64,
    pub move_type: String,
    pub from_location: Option<String>,
    pub to_location: Option<String>,
    pub reference: Option<String>,
    pub moved_at: String,
}

pub struct SupplyChainApi;

impl SupplyChainApi {
    // ---- RFQs ----
    pub async fn list_rfqs(client: &ApiClient) -> Result<Vec<RfqDto>, ApiError> {
        client.get("/api/v1/supply-chain/rfqs").await
    }

    pub async fn get_rfq(client: &ApiClient, id: &str) -> Result<RfqDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/rfqs/{}", id))
            .await
    }

    pub async fn create_rfq(
        client: &ApiClient,
        req: &CreateRfqRequest,
    ) -> Result<RfqDto, ApiError> {
        client.post("/api/v1/supply-chain/rfqs", req).await
    }

    // ---- Quotes ----
    pub async fn list_quotes(client: &ApiClient) -> Result<Vec<QuoteDto>, ApiError> {
        client.get("/api/v1/supply-chain/quotes").await
    }

    pub async fn get_quote(client: &ApiClient, id: &str) -> Result<QuoteDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/quotes/{}", id))
            .await
    }

    // ---- Sales Orders ----
    pub async fn list_sales_orders(client: &ApiClient) -> Result<Vec<SalesOrderDto>, ApiError> {
        client.get("/api/v1/supply-chain/sales-orders").await
    }

    pub async fn get_sales_order(client: &ApiClient, id: &str) -> Result<SalesOrderDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/sales-orders/{}", id))
            .await
    }

    // ---- Purchase Orders ----
    pub async fn list_purchase_orders(
        client: &ApiClient,
    ) -> Result<Vec<PurchaseOrderDto>, ApiError> {
        client.get("/api/v1/supply-chain/purchase-orders").await
    }

    pub async fn get_purchase_order(
        client: &ApiClient,
        id: &str,
    ) -> Result<PurchaseOrderDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/purchase-orders/{}", id))
            .await
    }

    // ---- Inventory ----
    pub async fn list_inventory(client: &ApiClient) -> Result<Vec<InventoryItemDto>, ApiError> {
        client.get("/api/v1/supply-chain/inventory").await
    }

    pub async fn get_inventory_item(
        client: &ApiClient,
        id: &str,
    ) -> Result<InventoryItemDto, ApiError> {
        client
            .get(&format!("/api/v1/supply-chain/inventory/{}", id))
            .await
    }

    // ---- Stock Moves ----
    pub async fn list_stock_moves(client: &ApiClient) -> Result<Vec<StockMoveDto>, ApiError> {
        client.get("/api/v1/supply-chain/stock-moves").await
    }
}

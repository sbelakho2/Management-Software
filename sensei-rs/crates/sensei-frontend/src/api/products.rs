//! Product catalog API endpoints.
//!
//! Products, BOM, routing.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductDto {
    pub id: String,
    pub name: String,
    pub part_number: String,
    pub revision: String,
    pub full_part_number: String,
    pub product_family: Option<String>,
    pub product_category: Option<String>,
    pub status: String,
    pub standard_cost: Option<f64>,
    pub lead_time_days: i32,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductDetailDto {
    pub id: String,
    pub name: String,
    pub part_number: String,
    pub revision: String,
    pub full_part_number: String,
    pub product_family: Option<String>,
    pub product_category: Option<String>,
    pub status: String,
    pub standard_cost: Option<f64>,
    pub lead_time_days: i32,
    pub description: Option<String>,
    pub unit_of_measure: String,
    pub weight_kg: Option<f64>,
    pub dimensions: Option<String>,
    pub standard_labor_hours: Option<f64>,
    pub setup_time_hours: Option<f64>,
    pub list_price: Option<f64>,
    pub reorder_point: Option<f64>,
    pub is_active: bool,
    pub bom_item_count: i32,
    pub routing_step_count: i32,
    pub created_at: String,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductListParams {
    pub search: Option<String>,
    pub product_family: Option<String>,
    pub product_category: Option<String>,
    pub status: Option<String>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedProductsResponse {
    pub items: Vec<ProductDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductStats {
    pub total_products: i32,
    pub active_products: i32,
    pub product_categories: i32,
    pub avg_lead_time_days: f64,
    pub low_stock_count: i32,
    pub recently_updated: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BomItemDto {
    pub id: String,
    pub product_id: String,
    pub component_id: String,
    pub component_name: Option<String>,
    pub quantity: f64,
    pub unit: String,
    pub level: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingStepDto {
    pub id: String,
    pub product_id: String,
    pub operation_number: i32,
    pub description: String,
    pub work_center: String,
    pub setup_time_hours: Option<f64>,
    pub run_time_hours: Option<f64>,
    pub sequence: i32,
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

pub struct ProductsApi;

impl ProductsApi {
    pub async fn list_products(
        client: &ApiClient,
        params: Option<&ProductListParams>,
    ) -> Result<PaginatedProductsResponse, ApiError> {
        let path = build_product_query(params);
        client.get(&path).await
    }

    pub async fn get_product(
        client: &ApiClient,
        id: &str,
    ) -> Result<ProductDetailDto, ApiError> {
        client.get(&format!("/api/v1/products/{}", id)).await
    }

    pub async fn create_product(
        client: &ApiClient,
        data: &serde_json::Value,
    ) -> Result<ProductDetailDto, ApiError> {
        client.post("/api/v1/products", data).await
    }

    pub async fn update_product(
        client: &ApiClient,
        id: &str,
        data: &serde_json::Value,
    ) -> Result<ProductDetailDto, ApiError> {
        client.put(&format!("/api/v1/products/{}", id), data).await
    }

    pub async fn delete_product(
        client: &ApiClient,
        id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client.delete(&format!("/api/v1/products/{}", id)).await
    }

    pub async fn get_product_stats(
        client: &ApiClient,
        id: &str,
    ) -> Result<ProductStats, ApiError> {
        client.get(&format!("/api/v1/products/{}/stats", id)).await
    }

    pub async fn get_product_bom(
        client: &ApiClient,
        product_id: &str,
    ) -> Result<Vec<BomItemDto>, ApiError> {
        client
            .get(&format!("/api/v1/products/{}/bom", product_id))
            .await
    }

    pub async fn get_product_routing(
        client: &ApiClient,
        product_id: &str,
    ) -> Result<Vec<RoutingStepDto>, ApiError> {
        client
            .get(&format!("/api/v1/products/{}/routing", product_id))
            .await
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn build_product_query(params: Option<&ProductListParams>) -> String {
    let Some(p) = params else {
        return "/api/v1/products".to_string();
    };

    let mut q = Vec::new();
    if let Some(v) = &p.search {
        q.push(format!("search={}", v));
    }
    if let Some(v) = &p.product_family {
        q.push(format!("product_family={}", v));
    }
    if let Some(v) = &p.product_category {
        q.push(format!("product_category={}", v));
    }
    if let Some(v) = &p.status {
        q.push(format!("status={}", v));
    }
    if let Some(v) = p.page {
        q.push(format!("page={}", v));
    }
    if let Some(v) = p.per_page {
        q.push(format!("per_page={}", v));
    }

    if q.is_empty() {
        "/api/v1/products".to_string()
    } else {
        format!("/api/v1/products?{}", q.join("&"))
    }
}

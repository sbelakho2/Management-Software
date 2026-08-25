//! Warehouse / inventory reactive store.
//!
//! Mirrors the Zustand [`warehouse.ts`](frontend/src/stores/warehouse.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WarehouseStatsDto {
    pub total_warehouses: i32,
    pub total_inventory_items: i32,
    pub total_stock_value: f64,
    pub low_stock_count: i32,
    pub out_of_stock_count: i32,
    pub pending_movements: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StockMovementDto {
    pub id: String,
    pub warehouse_id: String,
    pub product_id: String,
    pub movement_type: String,
    pub quantity: f64,
    pub reference: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LowStockItemDto {
    pub product_id: String,
    pub product_name: String,
    pub part_number: String,
    pub current_stock: f64,
    pub reorder_point: f64,
    pub shortage: f64,
    pub warehouse_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WarehouseDto {
    pub id: String,
    pub name: String,
    pub code: Option<String>,
    pub location: Option<String>,
    pub is_active: bool,
    pub created_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InventoryLevelDto {
    pub id: String,
    pub warehouse_id: String,
    pub product_id: String,
    pub product_name: Option<String>,
    pub quantity_on_hand: f64,
    pub quantity_allocated: f64,
    pub quantity_available: f64,
    pub reorder_point: Option<f64>,
    pub unit_of_measure: Option<String>,
}

/// Reactive store for warehouse / inventory data.
#[derive(Debug, Clone)]
pub struct WarehouseStore {
    pub stats: RwSignal<Option<WarehouseStatsDto>>,
    pub movements: RwSignal<Vec<StockMovementDto>>,
    pub low_stock_items: RwSignal<Vec<LowStockItemDto>>,
    pub warehouses: RwSignal<Vec<WarehouseDto>>,
    pub inventory_levels: RwSignal<Vec<InventoryLevelDto>>,
    pub loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
    pub last_fetched_at: RwSignal<Option<String>>,
}

const CACHE_DURATION_MS: u64 = 30_000; // 30 seconds

impl WarehouseStore {
    pub fn new() -> Self {
        Self {
            stats: RwSignal::new(None),
            movements: RwSignal::new(Vec::new()),
            low_stock_items: RwSignal::new(Vec::new()),
            warehouses: RwSignal::new(Vec::new()),
            inventory_levels: RwSignal::new(Vec::new()),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
            last_fetched_at: RwSignal::new(None),
        }
    }

    fn is_cache_valid(&self) -> bool {
        if let Some(ts) = self.last_fetched_at.get() {
            if let Ok(parsed) = chrono::DateTime::parse_from_rfc3339(&ts) {
                let elapsed = chrono::Utc::now()
                    .signed_duration_since(parsed.with_timezone(&chrono::Utc))
                    .num_milliseconds() as u64;
                return elapsed < CACHE_DURATION_MS;
            }
        }
        false
    }

    /// Fetch warehouse stats (with caching).
    pub async fn fetch_stats(&self, client: &ApiClient) {
        if self.is_cache_valid() {
            return;
        }
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<WarehouseStatsDto>("/api/v1/warehouse/stats")
            .await
        {
            Ok(data) => self.stats.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch stock movements.
    pub async fn fetch_movements(&self, client: &ApiClient, limit: i32) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<StockMovementDto>>(&format!("/api/v1/warehouse/movements?limit={}", limit))
            .await
        {
            Ok(data) => self.movements.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch low stock items.
    pub async fn fetch_low_stock(&self, client: &ApiClient, limit: i32) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<LowStockItemDto>>(&format!("/api/v1/warehouse/low-stock?limit={}", limit))
            .await
        {
            Ok(data) => self.low_stock_items.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch all warehouses.
    pub async fn fetch_warehouses(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<WarehouseDto>>("/api/v1/warehouse/warehouses")
            .await
        {
            Ok(data) => self.warehouses.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Fetch inventory levels, optionally filtered.
    pub async fn fetch_inventory_levels(&self, client: &ApiClient, params: &str) {
        self.loading.set(true);
        self.error.set(None);
        let path = if params.is_empty() {
            "/api/v1/warehouse/inventory".to_string()
        } else {
            format!("/api/v1/warehouse/inventory?{}", params)
        };
        match client.get::<Vec<InventoryLevelDto>>(&path).await {
            Ok(data) => self.inventory_levels.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    /// Sync inventory (trigger a sync with external systems).
    pub async fn sync_inventory(&self, client: &ApiClient) -> Result<serde_json::Value, ApiError> {
        client
            .post("/api/v1/warehouse/sync", &serde_json::json!({}))
            .await
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }
}

impl Default for WarehouseStore {
    fn default() -> Self {
        Self::new()
    }
}

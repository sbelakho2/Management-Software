//! Inventory route handlers.
//!
//! Provides endpoints for managing inventory items, stock moves,
//! and warehouses.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{InventoryItem, StockMove, Warehouse};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing inventory items.
#[derive(Debug, Deserialize)]
pub struct ListInventoryItemsParams {
    pub warehouse_id: Option<Uuid>,
    pub category: Option<String>,
    pub search: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing stock moves.
#[derive(Debug, Deserialize)]
pub struct ListStockMovesParams {
    pub item_id: Option<Uuid>,
    pub warehouse_id: Option<Uuid>,
    pub move_type: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing warehouses.
#[derive(Debug, Deserialize)]
pub struct ListWarehousesParams {
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating an inventory item.
#[derive(Debug, Deserialize)]
pub struct CreateInventoryItemRequest {
    pub sku: String,
    pub name: String,
    pub description: String,
    pub category: String,
    pub warehouse_id: Uuid,
    pub quantity_on_hand: f64,
    pub quantity_reserved: f64,
    pub unit_cost: f64,
    pub reorder_point: f64,
    pub reorder_quantity: f64,
}

/// Request body for updating an inventory item (partial).
#[derive(Debug, Deserialize)]
pub struct UpdateInventoryItemRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub warehouse_id: Option<Uuid>,
    pub quantity_on_hand: Option<f64>,
    pub quantity_reserved: Option<f64>,
    pub unit_cost: Option<f64>,
    pub reorder_point: Option<f64>,
    pub reorder_quantity: Option<f64>,
    pub is_active: Option<bool>,
}

/// Request body for recording a stock move.
#[derive(Debug, Deserialize)]
pub struct CreateStockMoveRequest {
    pub item_id: Uuid,
    pub warehouse_id: Uuid,
    pub move_type: String,
    pub quantity: f64,
    pub reference_type: Option<String>,
    pub reference_id: Option<Uuid>,
    pub notes: String,
}

/// Request body for creating a warehouse.
#[derive(Debug, Deserialize)]
pub struct CreateWarehouseRequest {
    pub name: String,
    pub code: String,
    pub location: String,
}

/// Inventory statistics response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InventoryStats {
    pub total_items: usize,
    pub total_value: f64,
    pub total_quantity_on_hand: f64,
    pub total_quantity_reserved: f64,
    pub low_stock_items: Vec<LowStockItem>,
    pub turnover_rate: f64,
}

/// A low stock inventory item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LowStockItem {
    pub id: Uuid,
    pub sku: String,
    pub name: String,
    pub quantity_on_hand: f64,
    pub reorder_point: f64,
}

// ── Inventory Items ────────────────────────────────────────────────────────

/// List inventory items with optional filters.
pub async fn list_inventory_items(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListInventoryItemsParams>,
) -> Result<Json<PaginatedResponse<InventoryItem>>> {
    let tenant_id = user.tenant_id;
    let store = state.inventory_items.read(user.tenant_id).await;
    let mut items: Vec<InventoryItem> = store
        .values()
        .filter(|i| i.tenant_id == tenant_id)
        .filter(|i| {
            if let Some(wid) = &params.warehouse_id {
                i.warehouse_id == *wid
            } else {
                true
            }
        })
        .filter(|i| {
            if let Some(ref cat) = params.category {
                i.category == *cat
            } else {
                true
            }
        })
        .filter(|i| {
            if let Some(ref s) = params.search {
                i.name.to_lowercase().contains(&s.to_lowercase())
                    || i.sku.to_lowercase().contains(&s.to_lowercase())
            } else {
                true
            }
        })
        .cloned()
        .collect();
    items.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(items, params.page, params.per_page);
    Ok(Json(result))
}

/// Get an inventory item by ID.
pub async fn get_inventory_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<InventoryItem>> {
    let tenant_id = user.tenant_id;
    let store = state.inventory_items.read(user.tenant_id).await;
    let item = store
        .values()
        .find(|i| i.id == id && i.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Inventory item {id} not found")))?;
    Ok(Json(item))
}

/// Create a new inventory item.
pub async fn create_inventory_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateInventoryItemRequest>,
) -> Result<Json<InventoryItem>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();

    if req.quantity_reserved > req.quantity_on_hand {
        return Err(SenseiError::Validation(format!(
            "quantity_reserved ({}) cannot exceed quantity_on_hand ({})",
            req.quantity_reserved, req.quantity_on_hand
        )));
    }

    let quantity_available = req.quantity_on_hand - req.quantity_reserved;
    let total_value = req.quantity_on_hand * req.unit_cost;
    let item = InventoryItem {
        id: new_id(),
        tenant_id,
        sku: req.sku,
        name: req.name,
        description: req.description,
        category: req.category,
        warehouse_id: req.warehouse_id,
        quantity_on_hand: req.quantity_on_hand,
        quantity_reserved: req.quantity_reserved,
        quantity_available,
        unit_cost: req.unit_cost,
        total_value,
        reorder_point: req.reorder_point,
        reorder_quantity: req.reorder_quantity,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.inventory_items.write(user.tenant_id).await;
    store.insert(item.id, item.clone());
    Ok(Json(item))
}

/// Update an inventory item.
pub async fn update_inventory_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateInventoryItemRequest>,
) -> Result<Json<InventoryItem>> {
    let tenant_id = user.tenant_id;
    let mut store = state.inventory_items.write(user.tenant_id).await;
    let item = store
        .get_mut(&id)
        .filter(|i| i.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Inventory item {id} not found")))?;
    if let Some(name) = req.name {
        item.name = name;
    }
    if let Some(desc) = req.description {
        item.description = desc;
    }
    if let Some(cat) = req.category {
        item.category = cat;
    }
    if let Some(wid) = req.warehouse_id {
        item.warehouse_id = wid;
    }
    if let Some(qoh) = req.quantity_on_hand {
        item.quantity_on_hand = qoh;
    }
    if let Some(qr) = req.quantity_reserved {
        item.quantity_reserved = qr;
    }
    if let Some(uc) = req.unit_cost {
        item.unit_cost = uc;
    }
    if let Some(rp) = req.reorder_point {
        item.reorder_point = rp;
    }
    if let Some(rq) = req.reorder_quantity {
        item.reorder_quantity = rq;
    }
    if let Some(active) = req.is_active {
        item.is_active = active;
    }

    // Reject inconsistent reservation state after applying the update.
    if item.quantity_reserved > item.quantity_on_hand {
        return Err(SenseiError::Validation(format!(
            "quantity_reserved ({}) cannot exceed quantity_on_hand ({})",
            item.quantity_reserved, item.quantity_on_hand
        )));
    }

    item.quantity_available = item.quantity_on_hand - item.quantity_reserved;
    item.total_value = item.quantity_on_hand * item.unit_cost;
    item.updated_at = Utc::now();
    Ok(Json(item.clone()))
}

// ── Stock Moves ────────────────────────────────────────────────────────────

/// List stock moves with optional filters.
pub async fn list_stock_moves(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListStockMovesParams>,
) -> Result<Json<PaginatedResponse<StockMove>>> {
    let tenant_id = user.tenant_id;
    let store = state.stock_moves.read(user.tenant_id).await;
    let mut moves: Vec<StockMove> = store
        .values()
        .filter(|m| m.tenant_id == tenant_id)
        .filter(|m| {
            if let Some(iid) = &params.item_id {
                m.item_id == *iid
            } else {
                true
            }
        })
        .filter(|m| {
            if let Some(wid) = &params.warehouse_id {
                m.warehouse_id == *wid
            } else {
                true
            }
        })
        .filter(|m| {
            if let Some(ref mt) = params.move_type {
                m.move_type == *mt
            } else {
                true
            }
        })
        .cloned()
        .collect();
    moves.sort_by_key(|a| std::cmp::Reverse(a.created_at));
    let result = PaginatedResponse::new(moves, params.page, params.per_page);
    Ok(Json(result))
}

/// Record a new stock move.
pub async fn create_stock_move(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateStockMoveRequest>,
) -> Result<Json<StockMove>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();

    if req.quantity <= 0.0 {
        return Err(SenseiError::Validation(
            "Stock move quantity must be greater than 0".to_string(),
        ));
    }

    // Transfers reference a warehouse; it must exist and belong to the
    // tenant before any quantity is adjusted.
    if req.move_type.starts_with("transfer_") {
        let warehouses = state.warehouses.read(user.tenant_id).await;
        let exists = warehouses
            .values()
            .any(|w| w.id == req.warehouse_id && w.tenant_id == tenant_id);
        if !exists {
            return Err(SenseiError::Validation(format!(
                "Warehouse {} does not exist for this tenant",
                req.warehouse_id
            )));
        }
    }

    // Update the inventory item's quantities
    let mut inv_store = state.inventory_items.write(user.tenant_id).await;
    if let Some(item) = inv_store
        .values_mut()
        .find(|i| i.id == req.item_id && i.tenant_id == tenant_id)
    {
        match req.move_type.as_str() {
            "receipt" | "adjustment_in" => {
                item.quantity_on_hand += req.quantity;
            }
            "issue" | "adjustment_out" | "transfer_out" => {
                // Never allow on-hand to go negative from an outgoing move.
                if req.quantity > item.quantity_on_hand {
                    return Err(SenseiError::Validation(format!(
                        "Insufficient on-hand quantity for item {}: have {}, need {}",
                        item.sku, item.quantity_on_hand, req.quantity
                    )));
                }
                item.quantity_on_hand -= req.quantity;
            }
            "transfer_in" => {
                item.quantity_on_hand += req.quantity;
            }
            _ => {
                return Err(SenseiError::Validation(format!(
                    "Unsupported move type: '{}'. Supported types: receipt, issue, adjustment_in, adjustment_out, transfer_in, transfer_out",
                    req.move_type
                )));
            }
        }
        item.quantity_available = item.quantity_on_hand - item.quantity_reserved;
        item.total_value = item.quantity_on_hand * item.unit_cost;
        item.updated_at = now;
    } else {
        return Err(SenseiError::NotFound(format!(
            "Inventory item {} not found",
            req.item_id
        )));
    }

    let stock_move = StockMove {
        id: new_id(),
        tenant_id,
        item_id: req.item_id,
        warehouse_id: req.warehouse_id,
        move_type: req.move_type,
        quantity: req.quantity,
        reference_type: req.reference_type,
        reference_id: req.reference_id,
        notes: req.notes,
        created_by: user.user_id,
        created_at: now,
    };
    let mut store = state.stock_moves.write(user.tenant_id).await;
    store.insert(stock_move.id, stock_move.clone());
    Ok(Json(stock_move))
}

// ── Warehouses ─────────────────────────────────────────────────────────────

/// List warehouses.
pub async fn list_warehouses(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWarehousesParams>,
) -> Result<Json<PaginatedResponse<Warehouse>>> {
    let tenant_id = user.tenant_id;
    let store = state.warehouses.read(user.tenant_id).await;
    let mut warehouses: Vec<Warehouse> = store
        .values()
        .filter(|w| w.tenant_id == tenant_id)
        .filter(|w| {
            if let Some(active) = params.is_active {
                w.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    warehouses.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(warehouses, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new warehouse.
pub async fn create_warehouse(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateWarehouseRequest>,
) -> Result<Json<Warehouse>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let warehouse = Warehouse {
        id: new_id(),
        tenant_id,
        name: req.name,
        code: req.code,
        location: req.location,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.warehouses.write(user.tenant_id).await;
    store.insert(warehouse.id, warehouse.clone());
    Ok(Json(warehouse))
}

// ── Inventory Statistics ───────────────────────────────────────────────────

/// Get inventory statistics.
pub async fn get_inventory_stats(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<InventoryStats>> {
    let tenant_id = user.tenant_id;
    let store = state.inventory_items.read(user.tenant_id).await;
    let items: Vec<&InventoryItem> = store
        .values()
        .filter(|i| i.tenant_id == tenant_id)
        .collect();

    let total_items = items.len();
    let total_value: f64 = items.iter().map(|i| i.total_value).sum();
    let total_quantity_on_hand: f64 = items.iter().map(|i| i.quantity_on_hand).sum();
    let total_quantity_reserved: f64 = items.iter().map(|i| i.quantity_reserved).sum();

    let low_stock_items: Vec<LowStockItem> = items
        .iter()
        .filter(|i| i.quantity_on_hand <= i.reorder_point)
        .map(|i| LowStockItem {
            id: i.id,
            sku: i.sku.clone(),
            name: i.name.clone(),
            quantity_on_hand: i.quantity_on_hand,
            reorder_point: i.reorder_point,
        })
        .collect();

    // Calculate turnover rate per item (total issued / average inventory),
    // then average across items with data. No hardcoded fallback values:
    // with no items or no moves the rate is simply 0.0.
    let moves_store = state.stock_moves.read(user.tenant_id).await;
    let mut turnover_rates: Vec<f64> = Vec::new();
    for item in &items {
        let issued: f64 = moves_store
            .values()
            .filter(|m| {
                m.tenant_id == tenant_id
                    && m.item_id == item.id
                    && (m.move_type == "issue"
                        || m.move_type == "adjustment_out"
                        || m.move_type == "transfer_out")
            })
            .map(|m| m.quantity)
            .sum();
        if issued > 0.0 && item.quantity_on_hand > 0.0 {
            turnover_rates.push(issued / item.quantity_on_hand);
        }
    }
    let turnover_rate = if turnover_rates.is_empty() {
        0.0
    } else {
        turnover_rates.iter().sum::<f64>() / turnover_rates.len() as f64
    };

    let stats = InventoryStats {
        total_items,
        total_value,
        total_quantity_on_hand,
        total_quantity_reserved,
        low_stock_items,
        turnover_rate,
    };
    Ok(Json(stats))
}

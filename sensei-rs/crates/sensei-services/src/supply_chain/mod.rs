//! Supply Chain domain services.
//!
//! Provides RFQ, quote, sales order, purchase order, inventory, and stock
//! movement management with in-memory storage for development and testing.
//!
//! # Architecture
//!
//! The supply chain service layer abstracts procurement, sales, and inventory
//! operations behind a trait, enabling the system to swap in real database-backed
//! implementations while keeping the in-memory implementation for unit tests
//! and demos.

mod database;
pub use database::DatabaseSupplyChainService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_core::domain::events::{
    DomainEvent, GoodsReceiptCreatedEvent, PurchaseOrderCreatedEvent, QuoteApprovedEvent,
    QuoteConvertedEvent, QuoteCreatedEvent, RFQCreatedEvent, RFQStatusChangedEvent,
    SalesOrderCreatedEvent, StockMoveCreatedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_event_bus::bus::EventBus;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// Request for Quotation sent to a supplier.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RFQ {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub rfq_number: String,
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub status: String, // draft, sent, quoted, expired, closed, cancelled
    pub items: Vec<RFQItem>,
    pub notes: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// A single line item within an RFQ.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RFQItem {
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: i64,
    pub unit_of_measure: String,
    pub target_price: Option<f64>,
}

/// A quote provided by a supplier or sent to a customer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Quote {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub quote_number: String,
    pub rfq_id: Option<Uuid>,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub status: String, // draft, submitted, approved, rejected, converted, expired
    pub line_items: Vec<QuoteLineItem>,
    pub total_amount: f64,
    pub currency: String,
    pub valid_until: DateTime<Utc>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// A single line item within a quote.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteLineItem {
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: i64,
    pub unit_price: f64,
    pub discount_percentage: f64,
    pub net_price: f64,
}

/// A sales order from a customer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SalesOrder {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub order_number: String,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub status: String, // pending, confirmed, in_production, shipped, delivered, cancelled
    pub line_items: Vec<SalesOrderItem>,
    pub total_amount: f64,
    pub currency: String,
    pub delivery_date: Option<DateTime<Utc>>,
    pub shipping_address: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// A single line item within a sales order.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SalesOrderItem {
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: i64,
    pub unit_price: f64,
    pub delivered_quantity: i64,
}

/// A purchase order sent to a supplier.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PurchaseOrder {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub po_number: String,
    pub supplier_id: Uuid,
    pub supplier_name: String,
    pub status: String, // draft, sent, confirmed, received, partially_received, cancelled
    pub line_items: Vec<POItem>,
    pub total_amount: f64,
    pub currency: String,
    pub expected_delivery: Option<DateTime<Utc>>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// A single line item within a purchase order.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct POItem {
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity_ordered: i64,
    pub quantity_received: i64,
    pub unit_price: f64,
}

/// An inventory item tracking stock levels at a location.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InventoryItem {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity_on_hand: i64,
    pub quantity_reserved: i64,
    pub quantity_available: i64,
    pub location: String,
    pub lot_number: Option<String>,
    pub reorder_point: i64,
    pub reorder_quantity: i64,
}

/// A stock movement recording inventory transfers between locations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StockMove {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: i64,
    pub move_type: String, // receipt, delivery, transfer, adjustment
    pub from_location: Option<String>,
    pub to_location: String,
    pub reference_type: Option<String>, // "sales_order", "purchase_order", "transfer"
    pub reference_id: Option<Uuid>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Supply chain service trait covering RFQ, quotes, sales orders,
/// purchase orders, inventory, and stock movements.
#[async_trait]
pub trait SupplyChainService: Send + Sync {
    // ── RFQ ─────────────────────────────────────────────────────────────
    /// Create a new Request for Quotation.
    async fn create_rfq(&self, tenant_id: Uuid, rfq: RFQ) -> Result<RFQ>;
    /// Get an RFQ by ID.
    async fn get_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<RFQ>;
    /// List RFQs with optional status filter and pagination.
    async fn list_rfqs(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<RFQ>>;
    /// Update the status of an RFQ.
    async fn update_rfq_status(&self, tenant_id: Uuid, id: Uuid, status: &str) -> Result<RFQ>;

    // ── Quotes ──────────────────────────────────────────────────────────
    /// Create a new quote.
    async fn create_quote(&self, tenant_id: Uuid, quote: Quote) -> Result<Quote>;
    /// Get a quote by ID.
    async fn get_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote>;
    /// List quotes with optional status filter and pagination.
    async fn list_quotes(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Quote>>;
    /// Approve a quote.
    async fn approve_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote>;
    /// Convert a quote to a sales order, copying line items and totals.
    async fn convert_quote_to_order(&self, tenant_id: Uuid, quote_id: Uuid) -> Result<SalesOrder>;

    // ── Sales Orders ────────────────────────────────────────────────────
    /// Create a new sales order.
    async fn create_sales_order(&self, tenant_id: Uuid, order: SalesOrder) -> Result<SalesOrder>;
    /// Get a sales order by ID.
    async fn get_sales_order(&self, tenant_id: Uuid, id: Uuid) -> Result<SalesOrder>;
    /// List sales orders with optional status filter and pagination.
    async fn list_sales_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SalesOrder>>;
    /// Update the status of a sales order.
    async fn update_sales_order_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<SalesOrder>;

    // ── Purchase Orders ─────────────────────────────────────────────────
    /// Create a new purchase order.
    async fn create_purchase_order(
        &self,
        tenant_id: Uuid,
        po: PurchaseOrder,
    ) -> Result<PurchaseOrder>;
    /// Get a purchase order by ID.
    async fn get_purchase_order(&self, tenant_id: Uuid, id: Uuid) -> Result<PurchaseOrder>;
    /// List purchase orders with optional status filter and pagination.
    async fn list_purchase_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PurchaseOrder>>;
    /// Receive a line item against a purchase order, updating received
    /// quantity and inventory.
    async fn receive_po_line(
        &self,
        tenant_id: Uuid,
        po_id: Uuid,
        product_id: Uuid,
        quantity_received: i64,
    ) -> Result<PurchaseOrder>;

    // ── Inventory ───────────────────────────────────────────────────────
    /// Get inventory for a specific product across all locations.
    async fn get_inventory(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<Vec<InventoryItem>>;
    /// List inventory with optional location filter and pagination.
    async fn list_inventory(
        &self,
        tenant_id: Uuid,
        location: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<InventoryItem>>;
    /// Adjust inventory quantity for a product at a location.
    async fn adjust_inventory(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
        location: &str,
        quantity_change: i64,
        reason: &str,
    ) -> Result<InventoryItem>;

    // ── Stock Movements ─────────────────────────────────────────────────
    /// Create a stock movement and update inventory levels accordingly.
    async fn create_stock_move(&self, tenant_id: Uuid, stock_move: StockMove) -> Result<StockMove>;
    /// List stock movements with optional product filter and pagination.
    async fn list_stock_moves(
        &self,
        tenant_id: Uuid,
        product_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<StockMove>>;
    /// Update an RFQ.
    async fn update_rfq(&self, tenant_id: Uuid, id: Uuid, rfq: RFQ) -> Result<RFQ>;
    /// Delete an RFQ.
    async fn delete_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Submit an RFQ (change status to "sent").
    async fn submit_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<RFQ>;
    /// Cancel an RFQ.
    async fn cancel_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<RFQ>;
    /// Update a quote.
    async fn update_quote(&self, tenant_id: Uuid, id: Uuid, quote: Quote) -> Result<Quote>;
    /// Delete a quote.
    async fn delete_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Submit a quote (change status to "submitted").
    async fn submit_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote>;
    /// Accept a quote.
    async fn accept_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote>;
    /// Reject a quote.
    async fn reject_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote>;
    /// Update a sales order.
    async fn update_sales_order(&self, tenant_id: Uuid, id: Uuid, order: SalesOrder) -> Result<SalesOrder>;
    /// Delete a sales order.
    async fn delete_sales_order(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Update a purchase order.
    async fn update_purchase_order(&self, tenant_id: Uuid, id: Uuid, po: PurchaseOrder) -> Result<PurchaseOrder>;
    /// Delete a purchase order.
    async fn delete_purchase_order(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Receive all line items on a purchase order.
    async fn receive_full_po(&self, tenant_id: Uuid, id: Uuid) -> Result<PurchaseOrder>;
    /// Update an inventory item.
    async fn update_inventory(&self, tenant_id: Uuid, id: Uuid, item: InventoryItem) -> Result<InventoryItem>;
    /// Delete an inventory item.
    async fn delete_inventory(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Delete a stock movement.
    async fn delete_stock_move(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`SupplyChainService`] trait.
///
/// Stores all entities in `HashMap`s and generates sequential document numbers.
/// Suitable for development, testing, and demo environments.
pub struct InMemorySupplyChainService {
    rfqs: RwLock<HashMap<Uuid, RFQ>>,
    quotes: RwLock<HashMap<Uuid, Quote>>,
    sales_orders: RwLock<HashMap<Uuid, SalesOrder>>,
    purchase_orders: RwLock<HashMap<Uuid, PurchaseOrder>>,
    inventory: RwLock<HashMap<String, InventoryItem>>, // key: "tenant_id:product_id:location"
    stock_moves: RwLock<HashMap<Uuid, StockMove>>,
    rfq_counter: RwLock<u64>,
    quote_counter: RwLock<u64>,
    so_counter: RwLock<u64>,
    po_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl InMemorySupplyChainService {
    /// Create a new empty [`InMemorySupplyChainService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            rfqs: RwLock::new(HashMap::new()),
            quotes: RwLock::new(HashMap::new()),
            sales_orders: RwLock::new(HashMap::new()),
            purchase_orders: RwLock::new(HashMap::new()),
            inventory: RwLock::new(HashMap::new()),
            stock_moves: RwLock::new(HashMap::new()),
            rfq_counter: RwLock::new(0),
            quote_counter: RwLock::new(0),
            so_counter: RwLock::new(0),
            po_counter: RwLock::new(0),
            event_bus,
        }
    }

    /// Publish a domain event if an event bus is configured.
    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!("Failed to publish event {}: {}", event.event_type(), e);
            }
        }
    }

    fn generate_rfq_number(counter: u64) -> String {
        format!("RFQ-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_quote_number(counter: u64) -> String {
        format!("QTE-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_so_number(counter: u64) -> String {
        format!("SO-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_po_number(counter: u64) -> String {
        format!("PO-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn inventory_key(tenant_id: Uuid, product_id: Uuid, location: &str) -> String {
        format!("{}:{}:{}", tenant_id, product_id, location)
    }

    async fn ensure_inventory_item(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
        product_name: &str,
        location: &str,
    ) -> InventoryItem {
        let key = Self::inventory_key(tenant_id, product_id, location);
        let mut store = self.inventory.write().await;
        if let Some(item) = store.get(&key) {
            item.clone()
        } else {
            let item = InventoryItem {
                id: Uuid::new_v4(),
                tenant_id,
                product_id,
                product_name: product_name.to_string(),
                quantity_on_hand: 0,
                quantity_reserved: 0,
                quantity_available: 0,
                location: location.to_string(),
                lot_number: None,
                reorder_point: 0,
                reorder_quantity: 0,
            };
            store.insert(key.clone(), item.clone());
            item
        }
    }
}

impl Default for InMemorySupplyChainService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl SupplyChainService for InMemorySupplyChainService {
    // ── RFQ ─────────────────────────────────────────────────────────────

    async fn create_rfq(&self, tenant_id: Uuid, mut rfq: RFQ) -> Result<RFQ> {
        let mut counter = self.rfq_counter.write().await;
        *counter += 1;
        let rfq_number = Self::generate_rfq_number(*counter);
        drop(counter);

        rfq.id = Uuid::new_v4();
        rfq.tenant_id = tenant_id;
        rfq.rfq_number = rfq_number;
        rfq.status = "draft".to_string();
        rfq.created_at = Utc::now();

        let id = rfq.id;
        let rfq_number = rfq.rfq_number.clone();
        let account_id = rfq.supplier_id;
        let result = rfq.clone();
        self.rfqs.write().await.insert(id, rfq.clone());
        self.publish_event(RFQCreatedEvent::new(tenant_id, id, rfq_number, account_id, String::new(), String::new())).await;
        Ok(result)
    }

    async fn get_rfq(&self, _tenant_id: Uuid, id: Uuid) -> Result<RFQ> {
        let store = self.rfqs.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))
    }

    async fn list_rfqs(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<RFQ>> {
        let store = self.rfqs.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|r| r.tenant_id == tenant_id && status.is_none_or(|s| r.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_rfq_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<RFQ> {
        let mut store = self.rfqs.write().await;
        let rfq = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        let old_status = rfq.status.clone();
        rfq.status = status.to_string();
        let result = rfq.clone();
        drop(store);
        self.publish_event(RFQStatusChangedEvent::new(tenant_id, id, old_status, status.to_string())).await;
        Ok(result)
    }

    // ── Quotes ──────────────────────────────────────────────────────────

    async fn create_quote(&self, tenant_id: Uuid, mut quote: Quote) -> Result<Quote> {
        let mut counter = self.quote_counter.write().await;
        *counter += 1;
        let quote_number = Self::generate_quote_number(*counter);
        drop(counter);

        quote.id = Uuid::new_v4();
        quote.tenant_id = tenant_id;
        quote.quote_number = quote_number;
        quote.status = "draft".to_string();
        quote.created_at = Utc::now();

        let id = quote.id;
        let quote_number = quote.quote_number.clone();
        let rfq_id = quote.rfq_id.unwrap_or(Uuid::nil());
        let total_amount = quote.total_amount;
        let currency = quote.currency.clone();
        let result = quote.clone();
        self.quotes.write().await.insert(id, quote.clone());
        self.publish_event(QuoteCreatedEvent::new(tenant_id, id, quote_number, rfq_id, total_amount, currency)).await;
        Ok(result)
    }

    async fn get_quote(&self, _tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let store = self.quotes.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))
    }

    async fn list_quotes(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Quote>> {
        let store = self.quotes.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|q| q.tenant_id == tenant_id && status.is_none_or(|s| q.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn approve_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let mut store = self.quotes.write().await;
        let quote = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;

        if quote.status == "approved" {
            return Err(SenseiError::Validation("Quote is already approved".to_string()));
        }
        if quote.status == "converted" {
            return Err(SenseiError::Validation(
                "Cannot approve a quote that has already been converted to an order".to_string(),
            ));
        }

        quote.status = "approved".to_string();
        let total_amount = quote.total_amount;
        let result = quote.clone();
        drop(store);
        self.publish_event(QuoteApprovedEvent::new(tenant_id, id, Uuid::nil(), total_amount)).await;
        Ok(result)
    }

    async fn convert_quote_to_order(
        &self,
        tenant_id: Uuid,
        quote_id: Uuid,
    ) -> Result<SalesOrder> {
        // Fetch and lock the quote
        let quote = {
            let mut store = self.quotes.write().await;
            let quote = store
                .get_mut(&quote_id)
                .ok_or_else(|| SenseiError::NotFound(format!("Quote {quote_id} not found")))?;

            if quote.status == "converted" {
                return Err(SenseiError::Validation(
                    "Quote has already been converted to an order".to_string(),
                ));
            }

            quote.status = "converted".to_string();
            quote.clone()
        };

        // Generate a new sales order number
        let mut counter = self.so_counter.write().await;
        *counter += 1;
        let so_number = Self::generate_so_number(*counter);
        drop(counter);

        // Copy line items from quote to sales order
        let so_items: Vec<SalesOrderItem> = quote
            .line_items
            .iter()
            .map(|li| SalesOrderItem {
                product_id: li.product_id,
                product_name: li.product_name.clone(),
                quantity: li.quantity,
                unit_price: li.net_price,
                delivered_quantity: 0,
            })
            .collect();

        let sales_order = SalesOrder {
            id: Uuid::new_v4(),
            tenant_id,
            order_number: so_number,
            customer_id: quote.customer_id,
            customer_name: quote.customer_name,
            status: "pending".to_string(),
            line_items: so_items,
            total_amount: quote.total_amount,
            currency: quote.currency,
            delivery_date: None,
            shipping_address: String::new(),
            created_by: quote.created_by,
            created_at: Utc::now(),
        };

        let sales_order_id = sales_order.id;
        self.sales_orders.write().await.insert(sales_order_id, sales_order.clone());
        self.publish_event(QuoteConvertedEvent::new(tenant_id, quote_id, sales_order_id)).await;
        Ok(sales_order)
    }

    // ── Sales Orders ────────────────────────────────────────────────────

    async fn create_sales_order(
        &self,
        tenant_id: Uuid,
        mut order: SalesOrder,
    ) -> Result<SalesOrder> {
        let mut counter = self.so_counter.write().await;
        *counter += 1;
        let so_number = Self::generate_so_number(*counter);
        drop(counter);

        order.id = Uuid::new_v4();
        order.tenant_id = tenant_id;
        order.order_number = so_number;
        order.status = "pending".to_string();
        order.created_at = Utc::now();

        let id = order.id;
        let so_number = order.order_number.clone();
        let account_id = order.customer_id;
        let total_amount = order.total_amount;
        let currency = order.currency.clone();
        let result = order.clone();
        self.sales_orders.write().await.insert(id, order.clone());
        self.publish_event(SalesOrderCreatedEvent::new(tenant_id, id, so_number, account_id, total_amount, currency)).await;
        Ok(result)
    }

    async fn get_sales_order(&self, _tenant_id: Uuid, id: Uuid) -> Result<SalesOrder> {
        let store = self.sales_orders.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))
    }

    async fn list_sales_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SalesOrder>> {
        let store = self.sales_orders.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|o| o.tenant_id == tenant_id && status.is_none_or(|s| o.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_sales_order_status(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<SalesOrder> {
        let mut store = self.sales_orders.write().await;
        let order = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
        order.status = status.to_string();
        Ok(order.clone())
    }

    // ── Purchase Orders ─────────────────────────────────────────────────

    async fn create_purchase_order(
        &self,
        tenant_id: Uuid,
        mut po: PurchaseOrder,
    ) -> Result<PurchaseOrder> {
        let mut counter = self.po_counter.write().await;
        *counter += 1;
        let po_number = Self::generate_po_number(*counter);
        drop(counter);

        po.id = Uuid::new_v4();
        po.tenant_id = tenant_id;
        po.po_number = po_number;
        po.status = "draft".to_string();
        po.created_at = Utc::now();

        let id = po.id;
        let po_number = po.po_number.clone();
        let supplier_id = po.supplier_id;
        let total_amount = po.total_amount;
        let currency = po.currency.clone();
        let result = po.clone();
        self.purchase_orders.write().await.insert(id, po.clone());
        self.publish_event(PurchaseOrderCreatedEvent::new(tenant_id, id, po_number, supplier_id, total_amount, currency)).await;
        Ok(result)
    }

    async fn get_purchase_order(&self, _tenant_id: Uuid, id: Uuid) -> Result<PurchaseOrder> {
        let store = self.purchase_orders.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))
    }

    async fn list_purchase_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PurchaseOrder>> {
        let store = self.purchase_orders.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|po| po.tenant_id == tenant_id && status.is_none_or(|s| po.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn receive_po_line(
        &self,
        tenant_id: Uuid,
        po_id: Uuid,
        product_id: Uuid,
        quantity_received: i64,
    ) -> Result<PurchaseOrder> {
        // Extract product_name before releasing the PO lock, to avoid borrow issues
        let product_name = {
            let mut store = self.purchase_orders.write().await;
            let po = store
                .get_mut(&po_id)
                .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {po_id} not found")))?;

            // Find and update the matching line item
            let mut line_found = false;
            let mut found_product_name = String::new();
            for item in &mut po.line_items {
                if item.product_id == product_id {
                    item.quantity_received += quantity_received;
                    found_product_name = item.product_name.clone();
                    line_found = true;
                    break;
                }
            }

            if !line_found {
                return Err(SenseiError::NotFound(format!(
                    "Product {product_id} not found in purchase order {po_id}"
                )));
            }

            // Update PO status based on receipt completeness
            let all_received = po.line_items.iter().all(|item| {
                item.quantity_received >= item.quantity_ordered
            });
            let any_received = po.line_items.iter().any(|item| item.quantity_received > 0);

            po.status = if all_received {
                "received".to_string()
            } else if any_received {
                "partially_received".to_string()
            } else {
                po.status.clone()
            };

            found_product_name
        }; // PO lock is released here

        // Update inventory: add received quantity
        let mut inv_store = self.inventory.write().await;
        let key = Self::inventory_key(tenant_id, product_id, "default");
        if let Some(inv) = inv_store.get_mut(&key) {
            inv.quantity_on_hand += quantity_received;
            inv.quantity_available = inv.quantity_on_hand - inv.quantity_reserved;
        } else {
            // Create inventory item if it doesn't exist
            let inv_item = InventoryItem {
                id: Uuid::new_v4(),
                tenant_id,
                product_id,
                product_name,
                quantity_on_hand: quantity_received,
                quantity_reserved: 0,
                quantity_available: quantity_received,
                location: "default".to_string(),
                lot_number: None,
                reorder_point: 0,
                reorder_quantity: 0,
            };
            inv_store.insert(key, inv_item);
        }
        drop(inv_store);

        self.publish_event(GoodsReceiptCreatedEvent::new(tenant_id, Uuid::new_v4(), po_id, quantity_received as f64)).await;

        // Re-acquire PO lock to return the updated PO
        let store = self.purchase_orders.read().await;
        Ok(store
            .get(&po_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {po_id} not found")))?)
    }

    // ── Inventory ───────────────────────────────────────────────────────

    async fn get_inventory(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<Vec<InventoryItem>> {
        let store = self.inventory.read().await;
        Ok(store
            .values()
            .filter(|item| item.tenant_id == tenant_id && item.product_id == product_id)
            .cloned()
            .collect())
    }

    async fn list_inventory(
        &self,
        tenant_id: Uuid,
        location: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<InventoryItem>> {
        let store = self.inventory.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|item| {
                item.tenant_id == tenant_id
                    && location.is_none_or(|loc| item.location == loc)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn adjust_inventory(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
        location: &str,
        quantity_change: i64,
        _reason: &str,
    ) -> Result<InventoryItem> {
        let key = Self::inventory_key(tenant_id, product_id, location);
        let mut store = self.inventory.write().await;

        // Auto-create inventory item if it doesn't exist yet
        if !store.contains_key(&key) {
            let item = InventoryItem {
                id: Uuid::new_v4(),
                tenant_id,
                product_id,
                product_name: String::new(),
                quantity_on_hand: 0,
                quantity_reserved: 0,
                quantity_available: 0,
                location: location.to_string(),
                lot_number: None,
                reorder_point: 0,
                reorder_quantity: 0,
            };
            store.insert(key.clone(), item);
        }

        let item = store.get_mut(&key).unwrap();
        item.quantity_on_hand += quantity_change;
        item.quantity_available = item.quantity_on_hand - item.quantity_reserved;

        // Ensure available doesn't go negative
        if item.quantity_available < 0 {
            item.quantity_available = 0;
        }
        if item.quantity_on_hand < 0 {
            item.quantity_on_hand = 0;
        }

        Ok(item.clone())
    }

    // ── Stock Movements ─────────────────────────────────────────────────

    async fn create_stock_move(
        &self,
        tenant_id: Uuid,
        mut stock_move: StockMove,
    ) -> Result<StockMove> {
        stock_move.id = Uuid::new_v4();
        stock_move.tenant_id = tenant_id;
        stock_move.created_at = Utc::now();

        let id = stock_move.id;
        let move_type = stock_move.move_type.clone();
        let product_id = stock_move.product_id;
        let product_name = stock_move.product_name.clone();
        let quantity = stock_move.quantity;
        let from_location = stock_move.from_location.clone();
        let to_location = stock_move.to_location.clone();

        // Update inventory based on move type
        match move_type.as_str() {
            "receipt" => {
                // Add to destination location
                let mut inv = self
                    .ensure_inventory_item(tenant_id, product_id, &product_name, &to_location)
                    .await;
                let key = Self::inventory_key(tenant_id, product_id, &to_location);
                let mut store = self.inventory.write().await;
                if let Some(existing) = store.get_mut(&key) {
                    existing.quantity_on_hand += quantity;
                    existing.quantity_available = existing.quantity_on_hand - existing.quantity_reserved;
                } else {
                    inv.quantity_on_hand = quantity;
                    inv.quantity_available = quantity;
                    store.insert(key, inv);
                }
            }
            "delivery" => {
                // Remove from source location (or default)
                let loc = from_location.as_deref().unwrap_or("default");
                let key = Self::inventory_key(tenant_id, product_id, loc);
                let mut store = self.inventory.write().await;
                if let Some(existing) = store.get_mut(&key) {
                    existing.quantity_on_hand -= quantity;
                    if existing.quantity_on_hand < 0 {
                        existing.quantity_on_hand = 0;
                    }
                    existing.quantity_available = existing.quantity_on_hand - existing.quantity_reserved;
                    if existing.quantity_available < 0 {
                        existing.quantity_available = 0;
                    }
                }
            }
            "transfer" => {
                // Remove from source
                if let Some(ref from) = from_location {
                    let from_key = Self::inventory_key(tenant_id, product_id, from);
                    let mut store = self.inventory.write().await;
                    if let Some(existing) = store.get_mut(&from_key) {
                        existing.quantity_on_hand -= quantity;
                        if existing.quantity_on_hand < 0 {
                            existing.quantity_on_hand = 0;
                        }
                        existing.quantity_available =
                            existing.quantity_on_hand - existing.quantity_reserved;
                        if existing.quantity_available < 0 {
                            existing.quantity_available = 0;
                        }
                    }
                }
                // Add to destination
                let mut inv = self
                    .ensure_inventory_item(tenant_id, product_id, &product_name, &to_location)
                    .await;
                let to_key = Self::inventory_key(tenant_id, product_id, &to_location);
                let mut store = self.inventory.write().await;
                if let Some(existing) = store.get_mut(&to_key) {
                    existing.quantity_on_hand += quantity;
                    existing.quantity_available = existing.quantity_on_hand - existing.quantity_reserved;
                } else {
                    inv.quantity_on_hand = quantity;
                    inv.quantity_available = quantity;
                    store.insert(to_key, inv);
                }
            }
            "adjustment" => {
                let loc = from_location.as_deref().unwrap_or(&to_location);
                let key = Self::inventory_key(tenant_id, product_id, loc);
                let mut store = self.inventory.write().await;
                if let Some(existing) = store.get_mut(&key) {
                    existing.quantity_on_hand += quantity;
                    if existing.quantity_on_hand < 0 {
                        existing.quantity_on_hand = 0;
                    }
                    existing.quantity_available = existing.quantity_on_hand - existing.quantity_reserved;
                    if existing.quantity_available < 0 {
                        existing.quantity_available = 0;
                    }
                } else {
                    let inv = InventoryItem {
                        id: Uuid::new_v4(),
                        tenant_id,
                        product_id,
                        product_name,
                        quantity_on_hand: quantity.max(0),
                        quantity_reserved: 0,
                        quantity_available: quantity.max(0),
                        location: loc.to_string(),
                        lot_number: None,
                        reorder_point: 0,
                        reorder_quantity: 0,
                    };
                    store.insert(key, inv);
                }
            }
            _ => {
                // Unknown move type, just store the move
            }
        }

        self.stock_moves.write().await.insert(id, stock_move.clone());
        self.publish_event(StockMoveCreatedEvent::new(
            tenant_id, id, product_id, quantity as f64,
            Uuid::nil(), Uuid::nil(), move_type,
        )).await;
        Ok(stock_move)
    }

    async fn list_stock_moves(
        &self,
        tenant_id: Uuid,
        product_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<StockMove>> {
        let store = self.stock_moves.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|sm| {
                sm.tenant_id == tenant_id
                    && product_id.is_none_or(|pid| sm.product_id == pid)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }
    // ── New: Update / Delete / Submit / Cancel / Accept / Reject ──────────

    async fn update_rfq(&self, _tenant_id: Uuid, id: Uuid, rfq: RFQ) -> Result<RFQ> {
        let mut store = self.rfqs.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        existing.supplier_id = rfq.supplier_id;
        existing.supplier_name = rfq.supplier_name;
        existing.status = rfq.status;
        existing.items = rfq.items;
        existing.notes = rfq.notes;
        // Preserve: id, tenant_id, rfq_number, created_by, created_at
        Ok(existing.clone())
    }

    async fn delete_rfq(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.rfqs.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        Ok(())
    }

    async fn submit_rfq(&self, _tenant_id: Uuid, id: Uuid) -> Result<RFQ> {
        let mut store = self.rfqs.write().await;
        let rfq = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        if rfq.status == "sent" || rfq.status == "cancelled" || rfq.status == "expired" {
            return Err(SenseiError::Validation(format!(
                "Cannot submit RFQ with status: {}",
                rfq.status
            )));
        }
        rfq.status = "sent".to_string();
        Ok(rfq.clone())
    }

    async fn cancel_rfq(&self, _tenant_id: Uuid, id: Uuid) -> Result<RFQ> {
        let mut store = self.rfqs.write().await;
        let rfq = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        if rfq.status == "cancelled" || rfq.status == "expired" {
            return Err(SenseiError::Validation(format!(
                "Cannot cancel RFQ with status: {}",
                rfq.status
            )));
        }
        rfq.status = "cancelled".to_string();
        Ok(rfq.clone())
    }

    async fn update_quote(&self, _tenant_id: Uuid, id: Uuid, quote: Quote) -> Result<Quote> {
        let mut store = self.quotes.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        existing.rfq_id = quote.rfq_id;
        existing.customer_id = quote.customer_id;
        existing.customer_name = quote.customer_name;
        existing.status = quote.status;
        existing.line_items = quote.line_items;
        existing.total_amount = quote.total_amount;
        existing.currency = quote.currency;
        existing.valid_until = quote.valid_until;
        // Preserve: id, tenant_id, quote_number, created_by, created_at
        Ok(existing.clone())
    }

    async fn delete_quote(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.quotes.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        Ok(())
    }

    async fn submit_quote(&self, _tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let mut store = self.quotes.write().await;
        let quote = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        if quote.status != "draft" {
            return Err(SenseiError::Validation(format!(
                "Cannot submit quote with status: {}",
                quote.status
            )));
        }
        quote.status = "submitted".to_string();
        Ok(quote.clone())
    }

    async fn accept_quote(&self, _tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let mut store = self.quotes.write().await;
        let quote = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        if quote.status != "submitted" {
            return Err(SenseiError::Validation(format!(
                "Cannot accept quote with status: {}",
                quote.status
            )));
        }
        quote.status = "approved".to_string();
        Ok(quote.clone())
    }

    async fn reject_quote(&self, _tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let mut store = self.quotes.write().await;
        let quote = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        if quote.status != "submitted" {
            return Err(SenseiError::Validation(format!(
                "Cannot reject quote with status: {}",
                quote.status
            )));
        }
        quote.status = "rejected".to_string();
        Ok(quote.clone())
    }

    async fn update_sales_order(&self, _tenant_id: Uuid, id: Uuid, order: SalesOrder) -> Result<SalesOrder> {
        let mut store = self.sales_orders.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("SalesOrder {id} not found")))?;
        existing.customer_id = order.customer_id;
        existing.customer_name = order.customer_name;
        existing.status = order.status;
        existing.line_items = order.line_items;
        existing.total_amount = order.total_amount;
        existing.currency = order.currency;
        existing.delivery_date = order.delivery_date;
        existing.shipping_address = order.shipping_address;
        // Preserve: id, tenant_id, order_number, created_by, created_at
        Ok(existing.clone())
    }

    async fn delete_sales_order(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.sales_orders.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("SalesOrder {id} not found")))?;
        Ok(())
    }

    async fn update_purchase_order(&self, _tenant_id: Uuid, id: Uuid, po: PurchaseOrder) -> Result<PurchaseOrder> {
        let mut store = self.purchase_orders.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PurchaseOrder {id} not found")))?;
        existing.supplier_id = po.supplier_id;
        existing.supplier_name = po.supplier_name;
        existing.status = po.status;
        existing.line_items = po.line_items;
        existing.total_amount = po.total_amount;
        existing.currency = po.currency;
        existing.expected_delivery = po.expected_delivery;
        // Preserve: id, tenant_id, po_number, created_by, created_at
        Ok(existing.clone())
    }

    async fn delete_purchase_order(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.purchase_orders.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PurchaseOrder {id} not found")))?;
        Ok(())
    }

    async fn receive_full_po(&self, tenant_id: Uuid, id: Uuid) -> Result<PurchaseOrder> {
        let mut store = self.purchase_orders.write().await;
        let po = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PurchaseOrder {id} not found")))?;

        if po.status == "received" || po.status == "cancelled" {
            return Err(SenseiError::Validation(format!(
                "Cannot receive PO with status: {}",
                po.status
            )));
        }

        for line in &mut po.line_items {
            let to_receive = line.quantity_ordered - line.quantity_received;
            if to_receive > 0 {
                line.quantity_received += to_receive;
            }
        }

        po.status = "received".to_string();
        let result = po.clone();
        drop(store);

        // Update inventory for received items
        for line in &result.line_items {
            let qty = line.quantity_ordered - line.quantity_received;
            if qty <= 0 {
                continue;
            }
            let inventory = self.inventory.read().await;
            let matching: Vec<(String, String)> = inventory
                .iter()
                .filter(|(_, i)| i.product_id == line.product_id && i.tenant_id == tenant_id)
                .map(|(k, i)| (k.clone(), i.location.clone()))
                .collect();
            drop(inventory);

            for (key, location) in matching {
                if let Err(e) = self
                    .adjust_inventory(tenant_id, line.product_id, &location, qty, &format!("PO receipt {id}"))
                    .await
                {
                    eprintln!("Inventory adjustment warning: {e}");
                }
                let _ = key;
            }
        }
        Ok(result)
    }

    async fn update_inventory(&self, _tenant_id: Uuid, id: Uuid, item: InventoryItem) -> Result<InventoryItem> {
        let mut store = self.inventory.write().await;
        // The inventory HashMap is keyed by "tenant_id:product_id:location" (String).
        // Find the entry by matching the item's UUID id.
        let key = store
            .iter()
            .find(|(_, v)| v.id == id)
            .map(|(k, _)| k.clone())
            .ok_or_else(|| SenseiError::NotFound(format!("InventoryItem {id} not found")))?;
        let existing = store.get_mut(&key).unwrap();
        existing.quantity_on_hand = item.quantity_on_hand;
        existing.quantity_reserved = item.quantity_reserved;
        existing.quantity_available = item.quantity_available;
        existing.location = item.location;
        existing.lot_number = item.lot_number;
        existing.reorder_point = item.reorder_point;
        existing.reorder_quantity = item.reorder_quantity;
        // Preserve: id, tenant_id, product_id, product_name
        Ok(existing.clone())
    }

    async fn delete_inventory(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.inventory.write().await;
        // The inventory HashMap is keyed by "tenant_id:product_id:location" (String).
        // Find the entry by matching the item's UUID id.
        let key = store
            .iter()
            .find(|(_, v)| v.id == id)
            .map(|(k, _)| k.clone())
            .ok_or_else(|| SenseiError::NotFound(format!("InventoryItem {id} not found")))?;
        store.remove(&key);
        Ok(())
    }

    async fn delete_stock_move(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.stock_moves.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("StockMove {id} not found")))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_rfq_lifecycle() {
        let service = InMemorySupplyChainService::default();
        let tenant_id = Uuid::new_v4();

        let rfq = RFQ {
            id: Uuid::nil(),
            tenant_id,
            rfq_number: String::new(),
            supplier_id: Uuid::new_v4(),
            supplier_name: "Acme Corp".to_string(),
            status: String::new(),
            items: vec![RFQItem {
                product_id: Uuid::new_v4(),
                product_name: "Widget".to_string(),
                quantity: 100,
                unit_of_measure: "pcs".to_string(),
                target_price: Some(9.99),
            }],
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created = service.create_rfq(tenant_id, rfq).await.unwrap();
        assert!(created.rfq_number.starts_with("RFQ-"));
        assert_eq!(created.status, "draft");

        let updated = service
            .update_rfq_status(tenant_id, created.id, "sent")
            .await
            .unwrap();
        assert_eq!(updated.status, "sent");
    }

    #[tokio::test]
    async fn test_quote_to_order_conversion() {
        let service = InMemorySupplyChainService::default();
        let tenant_id = Uuid::new_v4();

        let quote = Quote {
            id: Uuid::nil(),
            tenant_id,
            quote_number: String::new(),
            rfq_id: None,
            customer_id: Uuid::new_v4(),
            customer_name: "Big Buyer Inc.".to_string(),
            status: String::new(),
            line_items: vec![QuoteLineItem {
                product_id: Uuid::new_v4(),
                product_name: "Premium Widget".to_string(),
                quantity: 50,
                unit_price: 19.99,
                discount_percentage: 10.0,
                net_price: 17.99,
            }],
            total_amount: 899.50,
            currency: "USD".to_string(),
            valid_until: Utc::now() + chrono::Duration::days(30),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created_quote = service.create_quote(tenant_id, quote).await.unwrap();
        assert!(created_quote.quote_number.starts_with("QTE-"));

        // Approve the quote first
        let approved = service
            .approve_quote(tenant_id, created_quote.id)
            .await
            .unwrap();
        assert_eq!(approved.status, "approved");

        // Convert to sales order
        let order = service
            .convert_quote_to_order(tenant_id, created_quote.id)
            .await
            .unwrap();
        assert!(order.order_number.starts_with("SO-"));
        assert_eq!(order.total_amount, 899.50);
        assert_eq!(order.line_items.len(), 1);
        assert_eq!(order.line_items[0].product_name, "Premium Widget");

        // Verify quote is now converted
        let converted_quote = service.get_quote(tenant_id, created_quote.id).await.unwrap();
        assert_eq!(converted_quote.status, "converted");
    }

    #[tokio::test]
    async fn test_purchase_order_and_receipt() {
        let service = InMemorySupplyChainService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        let po = PurchaseOrder {
            id: Uuid::nil(),
            tenant_id,
            po_number: String::new(),
            supplier_id: Uuid::new_v4(),
            supplier_name: "SupplyCo".to_string(),
            status: String::new(),
            line_items: vec![POItem {
                product_id,
                product_name: "Raw Material".to_string(),
                quantity_ordered: 1000,
                quantity_received: 0,
                unit_price: 2.50,
            }],
            total_amount: 2500.0,
            currency: "USD".to_string(),
            expected_delivery: Some(Utc::now() + chrono::Duration::days(14)),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created_po = service.create_purchase_order(tenant_id, po).await.unwrap();
        assert!(created_po.po_number.starts_with("PO-"));

        // Receive partial delivery
        let partial = service
            .receive_po_line(tenant_id, created_po.id, product_id, 500)
            .await
            .unwrap();
        assert_eq!(partial.status, "partially_received");
        assert_eq!(partial.line_items[0].quantity_received, 500);

        // Receive the rest
        let full = service
            .receive_po_line(tenant_id, created_po.id, product_id, 500)
            .await
            .unwrap();
        assert_eq!(full.status, "received");
        assert_eq!(full.line_items[0].quantity_received, 1000);

        // Verify inventory was updated
        let inv = service
            .get_inventory(tenant_id, product_id)
            .await
            .unwrap();
        assert!(!inv.is_empty());
        assert_eq!(inv[0].quantity_on_hand, 1000);
    }

    #[tokio::test]
    async fn test_inventory_adjustment() {
        let service = InMemorySupplyChainService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        // First ensure inventory exists by doing an adjustment
        let adjusted = service
            .adjust_inventory(tenant_id, product_id, "Warehouse-A", 100, "initial stock")
            .await
            .unwrap();
        assert_eq!(adjusted.quantity_on_hand, 100);
        assert_eq!(adjusted.quantity_available, 100);

        // Negative adjustment
        let adjusted = service
            .adjust_inventory(tenant_id, product_id, "Warehouse-A", -20, "usage")
            .await
            .unwrap();
        assert_eq!(adjusted.quantity_on_hand, 80);
    }

    #[tokio::test]
    async fn test_stock_move_receipt() {
        let service = InMemorySupplyChainService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        let sm = StockMove {
            id: Uuid::nil(),
            tenant_id,
            product_id,
            product_name: "Test Item".to_string(),
            quantity: 200,
            move_type: "receipt".to_string(),
            from_location: None,
            to_location: "Dock-1".to_string(),
            reference_type: Some("purchase_order".to_string()),
            reference_id: Some(Uuid::new_v4()),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created = service
            .create_stock_move(tenant_id, sm)
            .await
            .unwrap();
        assert_eq!(created.move_type, "receipt");

        // Verify inventory was updated
        let inv = service
            .get_inventory(tenant_id, product_id)
            .await
            .unwrap();
        assert_eq!(inv[0].quantity_on_hand, 200);
        assert_eq!(inv[0].location, "Dock-1");
    }

    #[tokio::test]
    async fn test_stock_move_transfer() {
        let service = InMemorySupplyChainService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        // First receipt into Warehouse
        let sm1 = StockMove {
            id: Uuid::nil(),
            tenant_id,
            product_id,
            product_name: "Transfer Item".to_string(),
            quantity: 100,
            move_type: "receipt".to_string(),
            from_location: None,
            to_location: "Warehouse-A".to_string(),
            reference_type: None,
            reference_id: None,
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };
        service.create_stock_move(tenant_id, sm1).await.unwrap();

        // Transfer from Warehouse-A to Production-Line-1
        let sm2 = StockMove {
            id: Uuid::nil(),
            tenant_id,
            product_id,
            product_name: "Transfer Item".to_string(),
            quantity: 30,
            move_type: "transfer".to_string(),
            from_location: Some("Warehouse-A".to_string()),
            to_location: "Production-Line-1".to_string(),
            reference_type: None,
            reference_id: None,
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };
        service.create_stock_move(tenant_id, sm2).await.unwrap();

        // Check source inventory decreased
        let inv_a = service
            .get_inventory(tenant_id, product_id)
            .await
            .unwrap();
        let warehouse = inv_a.iter().find(|i| i.location == "Warehouse-A").unwrap();
        assert_eq!(warehouse.quantity_on_hand, 70);
    }
}

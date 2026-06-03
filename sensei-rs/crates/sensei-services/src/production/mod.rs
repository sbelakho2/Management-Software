//! Production/Manufacturing domain services.
//!
//! Provides work order management, production orders, bill of materials (BOM),
//! and material requirements planning (MRP) with in-memory storage for
//! development and testing.
//!
//! # Architecture
//!
//! The production service layer abstracts manufacturing operations behind a
//! trait, enabling the system to swap in real database-backed implementations
//! while keeping the in-memory implementation for unit tests and demos.

mod database;
pub use database::DatabaseProductionService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_core::domain::events::{
    DomainEvent, DowntimeRecordedEvent, MRPRunCompleted, ProductionOrderCompletedEvent,
    ProductionOrderStartedEvent, WorkOrderCreatedEvent, WorkOrderStatusChangedEvent,
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

/// A work order representing a manufacturing task on the shop floor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrder {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub wo_number: String,
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: i64,
    pub quantity_completed: i64,
    pub status: String, // created, released, in_progress, completed, cancelled, on_hold
    pub work_center_id: Option<Uuid>,
    pub priority: String, // low, normal, high, urgent
    pub scheduled_start: Option<DateTime<Utc>>,
    pub scheduled_end: Option<DateTime<Utc>>,
    pub actual_start: Option<DateTime<Utc>>,
    pub actual_end: Option<DateTime<Utc>>,
    pub assigned_to: Vec<Uuid>,
    pub notes: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A production order authorizing the manufacture of a specific product quantity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionOrder {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub order_number: String,
    pub product_id: Uuid,
    pub quantity_planned: i64,
    pub quantity_produced: i64,
    pub quantity_scrapped: i64,
    pub status: String, // planned, released, in_progress, completed, cancelled
    pub work_center_id: Option<Uuid>,
    pub planned_start: DateTime<Utc>,
    pub planned_end: DateTime<Utc>,
    pub actual_start: Option<DateTime<Utc>>,
    pub actual_end: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// A single line item in a bill of materials (BOM).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BOMItem {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub parent_product_id: Uuid,
    pub component_product_id: Uuid,
    pub component_name: String,
    pub quantity_required: f64,
    pub unit_of_measure: String,
    pub scrap_percentage: f64,
}

/// A material requirements planning (MRP) record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MRPRecord {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    pub gross_requirement: i64,
    pub scheduled_receipts: i64,
    pub projected_on_hand: i64,
    pub net_requirement: i64,
    pub planned_order_release: i64,
    pub time_phase_start: DateTime<Utc>,
    pub time_phase_end: DateTime<Utc>,
}

/// A work order operation / routing step.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderOperation {
    /// Unique identifier.
    pub id: Uuid,
    /// Parent work order ID.
    pub work_order_id: Uuid,
    /// Sequence number of the operation.
    pub operation_number: i32,
    /// Human-readable description of the operation.
    pub description: String,
    /// Work center where the operation is performed.
    pub work_center_id: Option<Uuid>,
    /// Setup time in minutes.
    pub setup_time_minutes: Option<i32>,
    /// Run time in minutes.
    pub run_time_minutes: Option<i32>,
    /// Status (pending, in_progress, completed, skipped, on_hold).
    pub status: String,
    /// When the operation started.
    pub started_at: Option<DateTime<Utc>>,
    /// When the operation completed.
    pub completed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Production service trait covering work orders, production orders,
/// bill of materials, and material requirements planning.
#[async_trait]
pub trait ProductionService: Send + Sync {
    // ── Work Orders ─────────────────────────────────────────────────────
    /// Create a new work order.
    async fn create_work_order(&self, tenant_id: Uuid, wo: WorkOrder) -> Result<WorkOrder>;
    /// Get a work order by ID.
    async fn get_work_order(&self, tenant_id: Uuid, id: Uuid) -> Result<WorkOrder>;
    /// List work orders with optional status and work center filters, with pagination.
    async fn list_work_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<WorkOrder>>;
    /// Update the status of a work order.
    async fn update_work_order_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<WorkOrder>;
    /// Report production completion for a work order.
    async fn report_production(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
        quantity_completed: i64,
        quantity_scrapped: i64,
    ) -> Result<WorkOrder>;
    /// List operations / routing steps for a work order.
    async fn list_work_order_operations(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
    ) -> Result<Vec<WorkOrderOperation>>;

    // ── Production Orders ───────────────────────────────────────────────
    /// Create a new production order.
    async fn create_production_order(
        &self,
        tenant_id: Uuid,
        order: ProductionOrder,
    ) -> Result<ProductionOrder>;
    /// Get a production order by ID.
    async fn get_production_order(&self, tenant_id: Uuid, id: Uuid) -> Result<ProductionOrder>;
    /// List production orders with optional status filter, with pagination.
    async fn list_production_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProductionOrder>>;
    /// Complete a production order.
    async fn complete_production_order(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<ProductionOrder>;

    // ── BOM ─────────────────────────────────────────────────────────────
    /// Add a BOM item.
    async fn add_bom_item(&self, tenant_id: Uuid, item: BOMItem) -> Result<BOMItem>;
    /// Get the entire BOM for a product (list of components).
    async fn get_bom(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<BOMItem>>;

    // ── MRP ─────────────────────────────────────────────────────────────
    /// Run MRP for a product and return the planning records.
    async fn run_mrp(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<MRPRecord>>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`ProductionService`] trait.
///
/// Stores work orders, production orders, BOM items, and MRP records
/// in memory using `HashMap`s. Suitable for development, testing, and
/// demo environments.
pub struct InMemoryProductionService {
    work_orders: RwLock<HashMap<Uuid, WorkOrder>>,
    production_orders: RwLock<HashMap<Uuid, ProductionOrder>>,
    bom_items: RwLock<HashMap<Uuid, BOMItem>>,
    mrp_records: RwLock<HashMap<Uuid, MRPRecord>>,
    /// Work order operations keyed by operation ID.
    wo_operations: RwLock<HashMap<Uuid, WorkOrderOperation>>,
    wo_counter: RwLock<u64>,
    po_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl InMemoryProductionService {
    /// Create a new empty [`InMemoryProductionService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            work_orders: RwLock::new(HashMap::new()),
            production_orders: RwLock::new(HashMap::new()),
            bom_items: RwLock::new(HashMap::new()),
            mrp_records: RwLock::new(HashMap::new()),
            wo_operations: RwLock::new(HashMap::new()),
            wo_counter: RwLock::new(0),
            po_counter: RwLock::new(0),
            event_bus,
        }
    }

    /// Publish a domain event via the optional event bus.
    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!(error = %e, "Failed to publish domain event");
            }
        }
    }

    fn generate_wo_number(counter: u64) -> String {
        format!("WO-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_po_number(counter: u64) -> String {
        format!("PO-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }
}

impl Default for InMemoryProductionService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl ProductionService for InMemoryProductionService {
    // ── Work Orders ─────────────────────────────────────────────────────

    async fn create_work_order(
        &self,
        tenant_id: Uuid,
        mut wo: WorkOrder,
    ) -> Result<WorkOrder> {
        let mut counter = self.wo_counter.write().await;
        *counter += 1;
        let wo_number = Self::generate_wo_number(*counter);
        drop(counter);

        wo.id = Uuid::new_v4();
        wo.tenant_id = tenant_id;
        wo.wo_number = wo_number;
        wo.status = "created".to_string();
        wo.quantity_completed = 0;
        wo.created_at = Utc::now();
        wo.updated_at = Utc::now();

        let id = wo.id;
        self.work_orders.write().await.insert(id, wo.clone());

        self.publish_event(WorkOrderCreatedEvent::new(
            tenant_id,
            id,
            wo.product_id,
            wo.priority.clone(),
            wo.work_center_id.map(|id| id.to_string()).unwrap_or_default(),
        ))
        .await;

        Ok(wo)
    }

    async fn get_work_order(&self, _tenant_id: Uuid, id: Uuid) -> Result<WorkOrder> {
        let store = self.work_orders.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))
    }

    async fn list_work_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<WorkOrder>> {
        let store = self.work_orders.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|wo| {
                wo.tenant_id == tenant_id
                    && status.is_none_or(|s| wo.status == s)
                    && work_center_id.is_none_or(|wc| wo.work_center_id == Some(wc))
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_work_order_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<WorkOrder> {
        let mut store = self.work_orders.write().await;
        let wo = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;

        let now = Utc::now();

        // Track actual start when moving to in_progress
        if status == "in_progress" && wo.actual_start.is_none() {
            wo.actual_start = Some(now);
        }

        // Track actual end when moving to completed
        if status == "completed" && wo.actual_end.is_none() {
            wo.actual_end = Some(now);
        }

        let old_status = wo.status.clone();
        wo.status = status.to_string();
        wo.updated_at = now;
        let wo_cloned = wo.clone();
        drop(store);

        self.publish_event(WorkOrderStatusChangedEvent::new(
            tenant_id,
            id,
            wo_cloned.wo_number.clone(),
            old_status,
            status.to_string(),
            Uuid::default(),
        ))
        .await;

        Ok(wo_cloned)
    }

    async fn report_production(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
        quantity_completed: i64,
        quantity_scrapped: i64,
    ) -> Result<WorkOrder> {
        let mut store = self.work_orders.write().await;
        let wo = store
            .get_mut(&work_order_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Work order {work_order_id} not found")))?;

        wo.quantity_completed += quantity_completed;
        wo.updated_at = Utc::now();

        // Auto-complete when quantity_completed >= quantity
        if wo.quantity_completed >= wo.quantity && wo.status != "completed" {
            wo.status = "completed".to_string();
            wo.actual_end = Some(Utc::now());
        }

        let wo_cloned = wo.clone();
        drop(store);

        if quantity_scrapped > 0 {
            self.publish_event(DowntimeRecordedEvent::new(
                tenant_id,
                wo_cloned.work_center_id.unwrap_or(Uuid::default()),
                quantity_scrapped as f64,
                "production_scrap".to_string(),
                format!("{} completed, {} scrapped", quantity_completed, quantity_scrapped),
            ))
            .await;
        }

        Ok(wo_cloned)
    }

    async fn list_work_order_operations(
        &self,
        _tenant_id: Uuid,
        work_order_id: Uuid,
    ) -> Result<Vec<WorkOrderOperation>> {
        // First verify the work order exists
        {
            let wo_store = self.work_orders.read().await;
            wo_store
                .get(&work_order_id)
                .ok_or_else(|| SenseiError::NotFound(format!("Work order {work_order_id} not found")))?;
        }

        let ops_store = self.wo_operations.read().await;
        let ops: Vec<WorkOrderOperation> = ops_store
            .values()
            .filter(|op| op.work_order_id == work_order_id)
            .cloned()
            .collect();
        Ok(ops)
    }

    // ── Production Orders ───────────────────────────────────────────────

    async fn create_production_order(
        &self,
        tenant_id: Uuid,
        mut order: ProductionOrder,
    ) -> Result<ProductionOrder> {
        let mut counter = self.po_counter.write().await;
        *counter += 1;
        let order_number = Self::generate_po_number(*counter);
        drop(counter);

        order.id = Uuid::new_v4();
        order.tenant_id = tenant_id;
        order.order_number = order_number;
        order.status = "planned".to_string();
        order.quantity_produced = 0;
        order.quantity_scrapped = 0;
        order.created_at = Utc::now();

        let id = order.id;
        self.production_orders.write().await.insert(id, order.clone());

        self.publish_event(ProductionOrderStartedEvent::new(
            tenant_id,
            id,
            order.product_id,
            order.quantity_planned,
            order.work_center_id.map(|id| id.to_string()).unwrap_or_default(),
        ))
        .await;

        Ok(order)
    }

    async fn get_production_order(&self, _tenant_id: Uuid, id: Uuid) -> Result<ProductionOrder> {
        let store = self.production_orders.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Production order {id} not found")))
    }

    async fn list_production_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProductionOrder>> {
        let store = self.production_orders.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|po| {
                po.tenant_id == tenant_id
                    && status.is_none_or(|s| po.status == s)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn complete_production_order(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<ProductionOrder> {
        let mut store = self.production_orders.write().await;
        let po = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Production order {id} not found")))?;

        if po.status == "completed" {
            return Err(SenseiError::Validation(
                "Production order is already completed".to_string(),
            ));
        }

        po.status = "completed".to_string();
        po.actual_end = Some(Utc::now());
        po.quantity_produced = po.quantity_planned;
        let po_cloned = po.clone();
        drop(store);

        self.publish_event(ProductionOrderCompletedEvent::new(
            tenant_id,
            id,
            po_cloned.product_id,
            po_cloned.quantity_produced,
            po_cloned.quantity_scrapped,
        ))
        .await;

        Ok(po_cloned)
    }

    // ── BOM ─────────────────────────────────────────────────────────────

    async fn add_bom_item(&self, tenant_id: Uuid, mut item: BOMItem) -> Result<BOMItem> {
        item.id = Uuid::new_v4();
        item.tenant_id = tenant_id;
        let id = item.id;
        self.bom_items.write().await.insert(id, item.clone());
        Ok(item)
    }

    async fn get_bom(&self, _tenant_id: Uuid, product_id: Uuid) -> Result<Vec<BOMItem>> {
        let store = self.bom_items.read().await;
        Ok(store
            .values()
            .filter(|item| item.parent_product_id == product_id)
            .cloned()
            .collect())
    }

    // ── MRP ─────────────────────────────────────────────────────────────

    async fn run_mrp(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<MRPRecord>> {
        let now = Utc::now();
        let mut records = Vec::new();

        // Compute a realistic MRP record based on demand
        // Gross requirement: sum of all active work orders for this product
        let gross_requirement: i64 = {
            let wo_store = self.work_orders.read().await;
            wo_store
                .values()
                .filter(|wo| {
                    wo.product_id == product_id
                        && wo.tenant_id == tenant_id
                        && wo.status != "completed"
                        && wo.status != "cancelled"
                })
                .map(|wo| wo.quantity - wo.quantity_completed)
                .sum()
        };

        // Scheduled receipts: sum of all production orders for this product
        let scheduled_receipts: i64 = {
            let po_store = self.production_orders.read().await;
            po_store
                .values()
                .filter(|po| {
                    po.product_id == product_id
                        && po.tenant_id == tenant_id
                        && po.status != "completed"
                        && po.status != "cancelled"
                })
                .map(|po| po.quantity_planned - po.quantity_produced)
                .sum()
        };

        // Projected on-hand: estimate from inventory-like logic
        let projected_on_hand = (scheduled_receipts - gross_requirement).max(0);

        // Net requirement: what we still need to order
        let net_requirement = (gross_requirement - scheduled_receipts).max(0);

        // Planned order release equals net requirement
        let planned_order_release = net_requirement;

        let record = MRPRecord {
            id: Uuid::new_v4(),
            tenant_id,
            product_id,
            gross_requirement,
            scheduled_receipts,
            projected_on_hand,
            net_requirement,
            planned_order_release,
            time_phase_start: now,
            time_phase_end: now + chrono::Duration::days(30),
        };

        self.publish_event(MRPRunCompleted::new(
            tenant_id,
            record.id,
            planned_order_release,
            net_requirement,
        ))
        .await;

        self.mrp_records
            .write()
            .await
            .insert(record.id, record.clone());
        records.push(record);

        Ok(records)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_and_get_work_order() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        let wo = WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id,
            product_name: "Test Product".to_string(),
            quantity: 100,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: None,
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let created = service
            .create_work_order(tenant_id, wo)
            .await
            .expect("should create work order");
        assert!(created.wo_number.starts_with("WO-"));
        assert_eq!(created.status, "created");

        let fetched = service
            .get_work_order(tenant_id, created.id)
            .await
            .expect("should fetch work order");
        assert_eq!(fetched.id, created.id);
    }

    #[tokio::test]
    async fn test_update_work_order_status() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();

        let wo = WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id: Uuid::new_v4(),
            product_name: "Test".to_string(),
            quantity: 50,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: None,
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let created = service.create_work_order(tenant_id, wo).await.unwrap();
        let updated = service
            .update_work_order_status(tenant_id, created.id, "in_progress")
            .await
            .unwrap();
        assert_eq!(updated.status, "in_progress");
        assert!(updated.actual_start.is_some());
    }

    #[tokio::test]
    async fn test_report_production_auto_completes() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();

        let wo = WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id: Uuid::new_v4(),
            product_name: "Test".to_string(),
            quantity: 10,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: None,
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let created = service.create_work_order(tenant_id, wo).await.unwrap();
        let reported = service
            .report_production(tenant_id, created.id, 10, 0)
            .await
            .unwrap();
        assert_eq!(reported.status, "completed");
        assert!(reported.actual_end.is_some());
    }

    #[tokio::test]
    async fn test_production_order_lifecycle() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();

        let po = ProductionOrder {
            id: Uuid::nil(),
            tenant_id,
            order_number: String::new(),
            product_id: Uuid::new_v4(),
            quantity_planned: 500,
            quantity_produced: 0,
            quantity_scrapped: 0,
            status: String::new(),
            work_center_id: None,
            planned_start: Utc::now(),
            planned_end: Utc::now() + chrono::Duration::days(7),
            actual_start: None,
            actual_end: None,
            created_at: Utc::now(),
        };

        let created = service
            .create_production_order(tenant_id, po)
            .await
            .expect("should create production order");
        assert!(created.order_number.starts_with("PO-"));
        assert_eq!(created.status, "planned");

        let completed = service
            .complete_production_order(tenant_id, created.id)
            .await
            .unwrap();
        assert_eq!(completed.status, "completed");
    }

    #[tokio::test]
    async fn test_bom_and_mrp() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();
        let component_id = Uuid::new_v4();

        let item = BOMItem {
            id: Uuid::nil(),
            tenant_id,
            parent_product_id: product_id,
            component_product_id: component_id,
            component_name: "Test Component".to_string(),
            quantity_required: 2.0,
            unit_of_measure: "pcs".to_string(),
            scrap_percentage: 0.05,
        };

        let added = service
            .add_bom_item(tenant_id, item)
            .await
            .expect("should add BOM item");
        assert_ne!(added.id, Uuid::nil());

        let bom = service
            .get_bom(tenant_id, product_id)
            .await
            .expect("should get BOM");
        assert_eq!(bom.len(), 1);
        assert_eq!(bom[0].component_name, "Test Component");

        // Run MRP — should produce a record even with no active work orders
        let mrp_records = service
            .run_mrp(tenant_id, product_id)
            .await
            .expect("should run MRP");
        assert!(!mrp_records.is_empty());
        assert_eq!(mrp_records[0].product_id, product_id);
    }
}

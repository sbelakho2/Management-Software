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
//!
//! # Request contexts (twenty-ninth audit Wave B item 7)
//!
//! Every operational method takes the server-created
//! [`RequestContext`](sensei_core::domain::request_context::RequestContext)
//! instead of a naked `tenant_id`: `ctx.tenant` is the tenant and `ctx.scope`
//! is the caller's DB-resolved authorization boundary. The database
//! implementation embeds the scope as a SQL predicate (see
//! [`crate::authz_sql::DbScopeFilter`]) in the SAME statement that reads or
//! mutates the row; a client-supplied work-center filter on
//! [`WorkOrderListFilter`] is always ANDed (a narrowing filter, never a
//! widening one).

mod database;
pub use database::DatabaseProductionService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::domain::events::{
    DomainEvent, DowntimeRecordedEvent, MRPRunCompleted, ProductionOrderCompletedEvent,
    ProductionOrderStartedEvent, WorkOrderCreatedEvent, WorkOrderStatusChangedEvent,
};
use sensei_core::domain::request_context::RequestContext;
use sensei_core::domain::scope::AuthorizedScope;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_event_bus::bus::EventBus;
use serde::{Deserialize, Serialize};
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
    #[serde(default)]
    pub quantity_scrapped: i64,
    #[serde(default)]
    pub short_close_qty: i64,
    #[serde(default)]
    pub short_close_reason: Option<String>,
    #[serde(default)]
    pub short_close_approved_by: Option<Uuid>,
    #[serde(default)]
    pub short_close_at: Option<DateTime<Utc>>,
    pub assigned_to: Vec<Uuid>,
    pub notes: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    /// Demand pegging (item 31): the sales-order line this work order
    /// serves — MRP then knows how much open SO demand is already covered
    /// by in-flight supply instead of using the max() heuristic.
    #[serde(default)]
    pub source_sales_order_id: Option<Uuid>,
    /// FROZEN MANUFACTURING CONFIGURATION (thirteenth audit P0): every
    /// revision is captured at release and immutable for the duration of
    /// the order — a later revision becoming effective NEVER changes what
    /// an in-progress order builds against.
    #[serde(default)]
    pub standard_work_id: Option<Uuid>,
    #[serde(default)]
    pub product_revision_id: Option<Uuid>,
    #[serde(default)]
    pub bom_revision_id: Option<Uuid>,
    #[serde(default)]
    pub routing_revision_id: Option<Uuid>,
    #[serde(default)]
    pub control_plan_revision_id: Option<Uuid>,
    #[serde(default)]
    pub ctq_characteristic_set: Vec<Uuid>,
    #[serde(default)]
    pub tooling_revision: Option<String>,
    /// Demand pegging at LINE granularity (partial/mixed fulfillment).
    #[serde(default)]
    pub source_sales_order_line_id: Option<Uuid>,
    #[serde(default)]
    pub customer_requirement_revision: Option<String>,
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
    #[serde(default)]
    pub quantity_scrapped: i64,
    pub status: String, // planned, released, in_progress, completed, cancelled
    pub work_center_id: Option<Uuid>,
    pub planned_start: DateTime<Utc>,
    pub planned_end: DateTime<Utc>,
    pub actual_start: Option<DateTime<Utc>>,
    pub actual_end: Option<DateTime<Utc>>,
    #[serde(default)]
    pub short_close_qty: f64,
    #[serde(default)]
    pub short_close_reason: Option<String>,
    #[serde(default)]
    pub short_close_approved_by: Option<Uuid>,
    #[serde(default)]
    pub short_close_at: Option<DateTime<Utc>>,
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
    pub quantity: rust_decimal::Decimal,
    pub unit_of_measure: String,
    pub scrap_percent: rust_decimal::Decimal,
}

/// A material requirements planning (MRP) record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MRPRecord {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    /// EXACT planning quantities (item 34): Decimal throughout — rounding
    /// to integer units is only valid for discrete parts. The planner
    /// never rounds meters/kilograms/liters; the UI may display rounded.
    pub gross_requirement: rust_decimal::Decimal,
    pub scheduled_receipts: rust_decimal::Decimal,
    pub projected_on_hand: rust_decimal::Decimal,
    pub net_requirement: rust_decimal::Decimal,
    pub planned_order_release: rust_decimal::Decimal,
    pub time_phase_start: DateTime<Utc>,
    pub time_phase_end: DateTime<Utc>,
    /// The product's unit of measure (m, kg, l, pcs...) — the UOM-aware
    /// planning unit (item 34).
    pub unit_of_measure: String,
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

/// A routing step used to generate work order operations.
///
/// Mirrors one row of the `routings` table: an operation performed at a work
/// center with standard setup/run times (in minutes).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingStep {
    /// Work center where the operation is performed.
    pub work_center_id: Option<Uuid>,
    /// Human-readable operation description.
    pub description: String,
    /// Standard setup time in minutes.
    pub setup_time_minutes: i32,
    /// Standard run time in minutes.
    pub run_time_minutes: i32,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Client-supplied narrowing filter for [`ProductionService::list_work_orders`].
///
/// `status`, `work_center_id` and the pagination window are the caller's
/// LIST filters — they intersect with the caller's authorized scope and can
/// never widen it (the work-center filter is ANDed with the scope predicate,
/// never ORed).
#[derive(Debug, Clone, Default)]
pub struct WorkOrderListFilter {
    pub status: Option<String>,
    /// NARROWING filter only: the scope of [`RequestContext`] decides what
    /// the caller may see; this filter only restricts it further.
    pub work_center_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

impl WorkOrderListFilter {
    pub fn new() -> Self {
        Self::default()
    }
}

/// Production service trait covering work orders, production orders,
/// bill of materials, and material requirements planning.
///
/// Twenty-ninth audit Wave B item 7: EVERY operational method takes the
/// server-created [`RequestContext`] — never a naked `tenant_id`. The
/// tenant is `ctx.tenant`; the caller's authorization boundary is
/// `ctx.scope`, which database-backed implementations enforce as a SQL
/// predicate in the same statement as the operation.
#[async_trait]
pub trait ProductionService: Send + Sync {
    // ── Work Orders ─────────────────────────────────────────────────────
    /// Create a new work order in the caller's tenant.
    ///
    /// Thirtieth-audit P0 item 3: the DESTINATION work center must sit
    /// inside the caller's EXACT scope. An anchored create resolves the
    /// destination through `work_centers` in the SAME statement (zero rows
    /// = the work center does not exist or is outside the scope →
    /// NotFound); an unanchored (no work center) create is a tenant-level
    /// claim and requires the explicit [`AuthorizedScope::TenantWide`]
    /// grant.
    async fn create_work_order(&self, ctx: &RequestContext, wo: WorkOrder) -> Result<WorkOrder>;
    /// Get a work order by ID — a row outside the caller's scope (or a
    /// nonexistent id) is indistinguishable: both NotFound.
    async fn get_work_order(&self, ctx: &RequestContext, id: Uuid) -> Result<WorkOrder>;
    /// List work orders: the caller's scope is always enforced; the
    /// client's status / work-center filters are NARROWING only.
    async fn list_work_orders(
        &self,
        ctx: &RequestContext,
        filter: &WorkOrderListFilter,
    ) -> Result<PaginatedResponse<WorkOrder>>;
    /// Update the status of a work order.
    async fn update_work_order_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        status: &str,
    ) -> Result<WorkOrder>;
    /// Update a work order's editable fields.
    ///
    /// Identity fields (`id`, `tenant_id`, `wo_number`, `created_at`) are
    /// preserved from the stored record; all other fields are taken from the
    /// supplied value. `work_center_id` is NOT editable here (thirtieth
    /// audit P0 item 3): the assignment is immutable through the generic
    /// edit and changes only through [`ProductionService::reassign_work_order`],
    /// which authorizes BOTH the source order and the destination work
    /// center in one statement.
    async fn update_work_order(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        wo: WorkOrder,
    ) -> Result<WorkOrder>;
    /// Reassign a work order to another work center (thirtieth audit P0
    /// item 3): an EXPLICIT, dual-authorized command. The single statement
    /// proves the SOURCE order is inside the caller's scope (the existing
    /// carrier predicate) AND that the DESTINATION work center is inside
    /// the same scope — an order on another site's work center can never
    /// be moved there, and an out-of-scope source or destination matches
    /// zero rows (NotFound).
    async fn reassign_work_order(
        &self,
        ctx: &RequestContext,
        work_order_id: Uuid,
        target_work_center_id: Uuid,
    ) -> Result<WorkOrder>;
    /// Report production completion for a work order.
    async fn report_production(
        &self,
        ctx: &RequestContext,
        work_order_id: Uuid,
        quantity_completed: i64,
        quantity_scrapped: i64,
        actor_id: Uuid,
    ) -> Result<WorkOrder>;
    /// List operations / routing steps for a work order.
    async fn list_work_order_operations(
        &self,
        ctx: &RequestContext,
        work_order_id: Uuid,
    ) -> Result<Vec<WorkOrderOperation>>;

    // ── Production Orders ───────────────────────────────────────────────
    /// Create a new production order.
    ///
    /// Thirtieth-audit P0 item 4: production orders are scoped through
    /// their work-center carrier (`production_orders.work_center_id` →
    /// `work_centers.site_id`) EXACTLY like work orders — the CREATE
    /// resolves the destination work center inside the caller's scope in
    /// the same statement, and an unanchored create requires the
    /// tenant-wide grant.
    async fn create_production_order(
        &self,
        ctx: &RequestContext,
        order: ProductionOrder,
    ) -> Result<ProductionOrder>;
    /// Get a production order by ID.
    async fn get_production_order(&self, ctx: &RequestContext, id: Uuid)
        -> Result<ProductionOrder>;
    /// List production orders with optional status filter, with pagination.
    async fn list_production_orders(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProductionOrder>>;
    /// Complete a production order.
    async fn complete_production_order(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        short_close_qty: i64,
        short_close_reason: Option<&str>,
        approver: Uuid,
    ) -> Result<ProductionOrder>;

    // ── BOM ─────────────────────────────────────────────────────────────
    /// Add a BOM item.
    async fn add_bom_item(&self, ctx: &RequestContext, item: BOMItem) -> Result<BOMItem>;
    /// Get the entire BOM for a product (list of components).
    async fn get_bom(&self, ctx: &RequestContext, product_id: Uuid) -> Result<Vec<BOMItem>>;

    // ── MRP ─────────────────────────────────────────────────────────────
    /// Run MRP for a product and return the planning records.
    async fn run_mrp(&self, ctx: &RequestContext, product_id: Uuid) -> Result<Vec<MRPRecord>>;
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
    /// Routings per product (used to generate work order operations).
    routings: RwLock<HashMap<Uuid, Vec<RoutingStep>>>,
    /// Current on-hand inventory per product (MRP input).
    inventory_on_hand: RwLock<HashMap<Uuid, i64>>,
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
            routings: RwLock::new(HashMap::new()),
            inventory_on_hand: RwLock::new(HashMap::new()),
            wo_counter: RwLock::new(0),
            po_counter: RwLock::new(0),
            event_bus,
        }
    }

    /// Seed the routing for a product (work order operation generation source).
    pub async fn seed_routing(&self, product_id: Uuid, steps: Vec<RoutingStep>) {
        self.routings.write().await.insert(product_id, steps);
    }

    /// Seed the current on-hand inventory quantity for a product (MRP input).
    pub async fn seed_inventory_on_hand(&self, product_id: Uuid, quantity: i64) {
        self.inventory_on_hand
            .write()
            .await
            .insert(product_id, quantity);
    }

    /// Publish a domain event via the optional event bus.
    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!(error = %e, "Failed to publish domain event");
            }
        }
    }

    /// Is this work order inside the caller's request context? The tenant
    /// is always enforced; the exact work-center scope is enforced on the
    /// row's work-center identity. The in-memory rows carry no site
    /// dimension (there is no site table), so a site-set scope cannot be
    /// contradicted — and an empty/no entitlement denies everything.
    /// Mirroring the DB carrier semantics (thirtieth audit P0 items 3-4):
    /// an order with NO work center is a tenant-level claim — only the
    /// explicit tenant-wide grant sees it; site/work-center scopes fail
    /// closed. A pure work-center scope requires its EXACT granted work
    /// center (thirtieth-audit P0 item 1 — never the whole site).
    fn wo_in_scope(ctx: &RequestContext, wo: &WorkOrder) -> bool {
        if wo.tenant_id != ctx.tenant {
            return false;
        }
        match &ctx.scope {
            AuthorizedScope::NoOperationalScope => false,
            AuthorizedScope::TenantWide => true,
            // No site data exists in-memory to contradict the scope, but an
            // unanchored order is never a site claim (fail closed).
            AuthorizedScope::Operational {
                sites,
                work_centers,
            } => {
                let Some(wc_id) = wo.work_center_id else {
                    return false;
                };
                !sites.is_empty() || work_centers.iter().any(|wc| wc.work_center == wc_id)
            }
        }
    }

    /// Is this production order inside the caller's request context? The
    /// production-order carrier is `production_orders.work_center_id`
    /// (same carrier semantics as work orders — thirtieth audit P0
    /// item 4): scoped callers only reach anchored orders, and a
    /// pure work-center scope only its exact granted work center(s).
    fn po_in_scope(ctx: &RequestContext, po: &ProductionOrder) -> bool {
        if po.tenant_id != ctx.tenant {
            return false;
        }
        match &ctx.scope {
            AuthorizedScope::NoOperationalScope => false,
            AuthorizedScope::TenantWide => true,
            AuthorizedScope::Operational {
                sites,
                work_centers,
            } => {
                let Some(wc_id) = po.work_center_id else {
                    return false;
                };
                !sites.is_empty() || work_centers.iter().any(|wc| wc.work_center == wc_id)
            }
        }
    }

    /// The context's tenant-side entitlement gate for the tenant-level
    /// commands (production orders / BOM / MRP): no entitlement → no
    /// command.
    fn tenant_entitled(ctx: &RequestContext) -> bool {
        !matches!(ctx.scope, AuthorizedScope::NoOperationalScope)
    }

    /// May this scope create/transfer onto the given destination work
    /// center? The in-memory rows carry no site dimension, so a site-set
    /// grant cannot be contradicted; a pure work-center grant requires
    /// its EXACT granted work center (thirtieth-audit P0 item 1 — a WC
    /// grant never widens).
    fn destination_granted(scope: &AuthorizedScope, dest: Uuid) -> bool {
        match scope {
            AuthorizedScope::NoOperationalScope => false,
            AuthorizedScope::TenantWide => true,
            AuthorizedScope::Operational {
                sites,
                work_centers,
            } => !sites.is_empty() || work_centers.iter().any(|wc| wc.work_center == dest),
        }
    }

    fn generate_wo_number(counter: u64) -> String {
        format!("WO-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_po_number(counter: u64) -> String {
        format!("PO-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    /// Generate the work order operations from the product's routing.
    ///
    /// Each routing step becomes one operation row (in sequence order).
    /// No-ops when the product has no routing configured.
    async fn generate_operations(&self, work_order: &WorkOrder) {
        let product_id = work_order.product_id;
        let steps = {
            let routings = self.routings.read().await;
            routings.get(&product_id).cloned()
        };
        let Some(steps) = steps else { return };
        if steps.is_empty() {
            return;
        }

        let now = Utc::now();
        let mut ops_store = self.wo_operations.write().await;
        for (idx, step) in steps.into_iter().enumerate() {
            let op = WorkOrderOperation {
                id: Uuid::new_v4(),
                work_order_id: work_order.id,
                operation_number: (idx + 1) as i32,
                description: step.description,
                work_center_id: step.work_center_id,
                setup_time_minutes: Some(step.setup_time_minutes),
                run_time_minutes: Some(step.run_time_minutes),
                status: "pending".to_string(),
                started_at: None,
                completed_at: None,
                created_at: now,
            };
            ops_store.insert(op.id, op);
        }
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
        ctx: &RequestContext,
        mut wo: WorkOrder,
    ) -> Result<WorkOrder> {
        if !Self::tenant_entitled(ctx) {
            return Err(SenseiError::Forbidden(
                "principal has no operational scope — cannot create a work order".to_string(),
            ));
        }
        // Thirtieth audit P0 item 3: the destination must be inside the
        // caller's exact scope. The in-memory rows carry no site dimension,
        // so a site-set scope cannot be contradicted — but an unanchored
        // order is a TENANT-level claim and requires the tenant-wide grant,
        // and a pure work-center scope may only create on ITS exact
        // work center(s).
        match (wo.work_center_id, &ctx.scope) {
            (None, AuthorizedScope::TenantWide) => {}
            (None, _) => {
                return Err(SenseiError::Forbidden(
                    "an unanchored work order requires the tenant-wide grant — anchor the order \
                     to a work center inside your scope"
                        .to_string(),
                ))
            }
            (Some(dest), scope) if !Self::destination_granted(scope, dest) => {
                return Err(SenseiError::Forbidden(
                    "the destination work center is outside the caller's authorized scope"
                        .to_string(),
                ))
            }
            _ => {}
        }
        let tenant_id = ctx.tenant;
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

        // Generate the operations from the product's routing (when configured).
        self.generate_operations(&wo).await;

        self.publish_event(WorkOrderCreatedEvent::new(
            tenant_id,
            id,
            wo.product_id,
            wo.priority.clone(),
            wo.work_center_id
                .map(|id| id.to_string())
                .unwrap_or_default(),
        ))
        .await;

        Ok(wo)
    }

    async fn get_work_order(&self, ctx: &RequestContext, id: Uuid) -> Result<WorkOrder> {
        let store = self.work_orders.read().await;
        let wo = store
            .get(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;
        if !Self::wo_in_scope(ctx, wo) {
            // Out-of-scope and nonexistent are indistinguishable (the DB
            // impl matches zero rows for both).
            return Err(SenseiError::NotFound(format!("Work order {id} not found")));
        }
        Ok(wo.clone())
    }

    async fn list_work_orders(
        &self,
        ctx: &RequestContext,
        filter: &WorkOrderListFilter,
    ) -> Result<PaginatedResponse<WorkOrder>> {
        let store = self.work_orders.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|wo| {
                Self::wo_in_scope(ctx, wo)
                    && filter.status.as_deref().is_none_or(|s| wo.status == s)
                    && filter
                        .work_center_id
                        .is_none_or(|wc| wo.work_center_id == Some(wc))
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, filter.page, filter.per_page))
    }

    async fn update_work_order_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        status: &str,
    ) -> Result<WorkOrder> {
        let mut store = self.work_orders.write().await;
        let wo = store
            .get_mut(&id)
            .filter(|wo| Self::wo_in_scope(ctx, wo))
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
            ctx.tenant,
            id,
            wo_cloned.wo_number.clone(),
            old_status,
            status.to_string(),
            Uuid::default(),
        ))
        .await;

        Ok(wo_cloned)
    }

    async fn update_work_order(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        mut wo: WorkOrder,
    ) -> Result<WorkOrder> {
        let mut store = self.work_orders.write().await;
        let existing = store
            .get(&id)
            .filter(|w| Self::wo_in_scope(ctx, w))
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;

        wo.id = existing.id;
        wo.tenant_id = existing.tenant_id;
        wo.wo_number = existing.wo_number;
        wo.created_at = existing.created_at;
        wo.updated_at = Utc::now();
        // Thirtieth audit P0 item 3: the work-center assignment is
        // immutable through the generic edit — it changes ONLY through
        // reassign_work_order (which authorizes both ends).
        wo.work_center_id = existing.work_center_id;
        // Progress is owned by the reporting flow; a partial edit must not
        // reset already-completed quantities.
        if wo.quantity_completed == 0 && existing.quantity_completed > 0 {
            wo.quantity_completed = existing.quantity_completed;
        }

        store.insert(id, wo.clone());
        drop(store);

        self.publish_event(WorkOrderStatusChangedEvent::new(
            ctx.tenant,
            id,
            wo.wo_number.clone(),
            existing.status,
            wo.status.clone(),
            Uuid::default(),
        ))
        .await;

        Ok(wo)
    }

    async fn reassign_work_order(
        &self,
        ctx: &RequestContext,
        work_order_id: Uuid,
        target_work_center_id: Uuid,
    ) -> Result<WorkOrder> {
        let mut store = self.work_orders.write().await;
        let wo = store
            .get_mut(&work_order_id)
            .filter(|wo| Self::wo_in_scope(ctx, wo))
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Work order {work_order_id} not found"))
            })?;
        // Dual authorization: the SOURCE is in scope (filter above); the
        // DESTINATION must also be inside the caller's exact scope. The
        // in-memory rows carry no site dimension, so a site-set scope
        // cannot be contradicted — a pure work-center scope may only
        // reassign to its EXACT granted work center(s) (any other
        // destination is a denial).
        match &ctx.scope {
            AuthorizedScope::Operational { .. }
                if !Self::destination_granted(&ctx.scope, target_work_center_id) =>
            {
                return Err(SenseiError::NotFound(format!(
                    "Work order {work_order_id} not found"
                )))
            }
            AuthorizedScope::TenantWide
            | AuthorizedScope::NoOperationalScope
            | AuthorizedScope::Operational { .. } => {}
        }
        wo.work_center_id = Some(target_work_center_id);
        wo.updated_at = Utc::now();
        Ok(wo.clone())
    }

    async fn report_production(
        &self,
        ctx: &RequestContext,
        work_order_id: Uuid,
        quantity_completed: i64,
        quantity_scrapped: i64,
        _actor_id: Uuid,
    ) -> Result<WorkOrder> {
        let mut store = self.work_orders.write().await;
        let wo = store
            .get_mut(&work_order_id)
            .filter(|wo| Self::wo_in_scope(ctx, wo))
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Work order {work_order_id} not found"))
            })?;

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
                ctx.tenant,
                wo_cloned.work_center_id.unwrap_or(Uuid::default()),
                quantity_scrapped as f64,
                "production_scrap".to_string(),
                format!(
                    "{} completed, {} scrapped",
                    quantity_completed, quantity_scrapped
                ),
            ))
            .await;
        }

        Ok(wo_cloned)
    }

    async fn list_work_order_operations(
        &self,
        ctx: &RequestContext,
        work_order_id: Uuid,
    ) -> Result<Vec<WorkOrderOperation>> {
        // First verify the work order exists and is in scope
        {
            let wo_store = self.work_orders.read().await;
            match wo_store.get(&work_order_id) {
                Some(wo) if Self::wo_in_scope(ctx, wo) => {}
                _ => {
                    return Err(SenseiError::NotFound(format!(
                        "Work order {work_order_id} not found"
                    )))
                }
            }
        }

        let ops_store = self.wo_operations.read().await;
        let mut ops: Vec<WorkOrderOperation> = ops_store
            .values()
            .filter(|op| op.work_order_id == work_order_id)
            .cloned()
            .collect();
        // Deterministic ordering: operations are returned in sequence order.
        ops.sort_by_key(|op| op.operation_number);
        Ok(ops)
    }

    // ── Production Orders ───────────────────────────────────────────────

    async fn create_production_order(
        &self,
        ctx: &RequestContext,
        mut order: ProductionOrder,
    ) -> Result<ProductionOrder> {
        if !Self::tenant_entitled(ctx) {
            return Err(SenseiError::Forbidden(
                "principal has no operational scope — cannot create a production order".to_string(),
            ));
        }
        // Thirtieth audit P0 item 4: production orders carry their scope
        // through the work center — an unanchored order is a tenant-level
        // claim (tenant-wide grant only), and a pure work-center scope may
        // only create on its EXACT work center(s).
        match (order.work_center_id, &ctx.scope) {
            (None, AuthorizedScope::TenantWide) => {}
            (None, _) => {
                return Err(SenseiError::Forbidden(
                    "an unanchored production order requires the tenant-wide grant — anchor the \
                     order to a work center inside your scope"
                        .to_string(),
                ))
            }
            (Some(dest), scope) if !Self::destination_granted(scope, dest) => {
                return Err(SenseiError::Forbidden(
                    "the destination work center is outside the caller's authorized scope"
                        .to_string(),
                ))
            }
            _ => {}
        }
        let tenant_id = ctx.tenant;
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
        self.production_orders
            .write()
            .await
            .insert(id, order.clone());

        self.publish_event(ProductionOrderStartedEvent::new(
            tenant_id,
            id,
            order.product_id,
            order.quantity_planned,
            order
                .work_center_id
                .map(|id| id.to_string())
                .unwrap_or_default(),
        ))
        .await;

        Ok(order)
    }

    async fn get_production_order(
        &self,
        ctx: &RequestContext,
        id: Uuid,
    ) -> Result<ProductionOrder> {
        let store = self.production_orders.read().await;
        let po = store
            .get(&id)
            .filter(|po| Self::po_in_scope(ctx, po))
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Production order {id} not found")))?;
        Ok(po)
    }

    async fn list_production_orders(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProductionOrder>> {
        let store = self.production_orders.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|po| Self::po_in_scope(ctx, po) && status.is_none_or(|s| po.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn complete_production_order(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        short_close_qty: i64,
        short_close_reason: Option<&str>,
        approver: Uuid,
    ) -> Result<ProductionOrder> {
        let mut store = self.production_orders.write().await;
        let po = store
            .get_mut(&id)
            .filter(|po| Self::po_in_scope(ctx, po))
            .ok_or_else(|| SenseiError::NotFound(format!("Production order {id} not found")))?;

        if po.status == "completed" {
            return Err(SenseiError::Validation(
                "Production order is already completed".to_string(),
            ));
        }

        // Completion must never fabricate output.
        let produced = po.quantity_produced as i64;
        let scrapped = po.quantity_scrapped as i64;
        let planned = po.quantity_planned as i64;
        let accounted = produced + scrapped + short_close_qty;
        if accounted != planned {
            return Err(SenseiError::Validation(format!(
                "Cannot complete: {accounted} of {planned} units accounted for \
                 (produced {produced} + scrap {scrapped} + short close {short_close_qty})."
            )));
        }
        if short_close_qty < 0 {
            return Err(SenseiError::Validation(
                "Short close quantity cannot be negative".to_string(),
            ));
        }
        if short_close_qty > 0 && short_close_reason.is_none_or(|r| r.trim().is_empty()) {
            return Err(SenseiError::Validation(
                "A short close requires a reason".to_string(),
            ));
        }

        po.status = "completed".to_string();
        po.actual_end = Some(Utc::now());
        po.short_close_qty = short_close_qty as f64;
        po.short_close_reason = short_close_reason.map(|s| s.to_string());
        po.short_close_approved_by = Some(approver);
        po.short_close_at = if short_close_qty > 0 {
            po.actual_end
        } else {
            None
        };
        let po_cloned = po.clone();
        drop(store);

        self.publish_event(ProductionOrderCompletedEvent::new(
            ctx.tenant,
            id,
            po_cloned.product_id,
            po_cloned.quantity_produced,
            po_cloned.quantity_scrapped,
        ))
        .await;

        Ok(po_cloned)
    }

    // ── BOM ─────────────────────────────────────────────────────────────

    async fn add_bom_item(&self, ctx: &RequestContext, mut item: BOMItem) -> Result<BOMItem> {
        if !Self::tenant_entitled(ctx) {
            return Err(SenseiError::Forbidden(
                "principal has no operational scope — cannot add a BOM item".to_string(),
            ));
        }
        item.id = Uuid::new_v4();
        item.tenant_id = ctx.tenant;
        let id = item.id;
        self.bom_items.write().await.insert(id, item.clone());
        Ok(item)
    }

    async fn get_bom(&self, ctx: &RequestContext, product_id: Uuid) -> Result<Vec<BOMItem>> {
        let store = self.bom_items.read().await;
        Ok(store
            .values()
            .filter(|item| {
                item.tenant_id == ctx.tenant
                    && !matches!(ctx.scope, AuthorizedScope::NoOperationalScope)
                    && item.parent_product_id == product_id
            })
            .cloned()
            .collect())
    }

    // ── MRP ─────────────────────────────────────────────────────────────

    async fn run_mrp(&self, ctx: &RequestContext, product_id: Uuid) -> Result<Vec<MRPRecord>> {
        if !Self::tenant_entitled(ctx) {
            return Err(SenseiError::Forbidden(
                "principal has no operational scope — cannot run MRP".to_string(),
            ));
        }
        let now = Utc::now();
        let mut records = Vec::new();

        // Compute a realistic MRP record based on demand — EXACT Decimal
        // throughout (item 34); the in-memory path mirrors the DB engine.
        let gross_requirement: rust_decimal::Decimal = {
            let wo_store = self.work_orders.read().await;
            wo_store
                .values()
                .filter(|wo| {
                    wo.product_id == product_id
                        && wo.tenant_id == ctx.tenant
                        && wo.status != "completed"
                        && wo.status != "cancelled"
                })
                .map(|wo| rust_decimal::Decimal::from(wo.quantity - wo.quantity_completed))
                .sum()
        };

        let scheduled_receipts: rust_decimal::Decimal = {
            let po_store = self.production_orders.read().await;
            po_store
                .values()
                .filter(|po| {
                    po.product_id == product_id
                        && po.tenant_id == ctx.tenant
                        && po.status != "completed"
                        && po.status != "cancelled"
                })
                .map(|po| rust_decimal::Decimal::from(po.quantity_planned - po.quantity_produced))
                .sum()
        };

        // Projected on-hand: current inventory + scheduled receipts − gross
        // requirement (never negative).
        let on_hand: rust_decimal::Decimal = {
            let inv = self.inventory_on_hand.read().await;
            inv.get(&product_id).copied().unwrap_or(0).into()
        };
        let projected_on_hand =
            (on_hand + scheduled_receipts - gross_requirement).max(rust_decimal::Decimal::ZERO);

        // Net requirement: what we still need to order.
        let net_requirement =
            (gross_requirement - scheduled_receipts - on_hand).max(rust_decimal::Decimal::ZERO);

        let planned_order_release = net_requirement;

        let record = MRPRecord {
            id: Uuid::new_v4(),
            tenant_id: ctx.tenant,
            product_id,
            gross_requirement,
            scheduled_receipts,
            projected_on_hand,
            net_requirement,
            planned_order_release,
            time_phase_start: now,
            time_phase_end: now + chrono::Duration::days(30),
            unit_of_measure: "pcs".to_string(),
        };

        self.publish_event(MRPRunCompleted::new(
            ctx.tenant,
            record.id,
            // The event carries COUNTS (planned orders, shortages), not
            // quantities — Decimal widens to i64 only at this boundary.
            planned_order_release
                .trunc()
                .to_string()
                .parse::<i64>()
                .unwrap_or(0),
            net_requirement
                .trunc()
                .to_string()
                .parse::<i64>()
                .unwrap_or(0),
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

    /// A tenant-wide request context for pure in-memory tests: the
    /// in-memory service is exercised with the legacy tenant-wide
    /// semantics (its rows carry no site dimension).
    fn rc(tenant_id: Uuid) -> RequestContext {
        RequestContext {
            tenant: tenant_id,
            principal: Uuid::new_v4(),
            scope: AuthorizedScope::tenant_wide(),
            focus: sensei_core::domain::request_context::OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }
    }

    #[tokio::test]
    async fn in_memory_scope_denies_foreign_work_centers() {
        use sensei_core::domain::scope::{AuthorizedScope, WorkCenterScope};
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();
        let wc_a = Uuid::new_v4();
        let wc_b = Uuid::new_v4();
        let base = |wc: Uuid| WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id: Uuid::new_v4(),
            product_name: "P".to_string(),
            quantity: 1,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: Some(wc),
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };
        let created_a = service
            .create_work_order(&rc(tenant_id), base(wc_a))
            .await
            .unwrap();
        service
            .create_work_order(&rc(tenant_id), base(wc_b))
            .await
            .unwrap();
        let scoped = RequestContext {
            tenant: tenant_id,
            principal: Uuid::new_v4(),
            scope: AuthorizedScope::Operational {
                sites: std::collections::HashSet::new(),
                work_centers: std::collections::HashSet::from([WorkCenterScope {
                    site: Uuid::new_v4(),
                    work_center: wc_a,
                }]),
            },
            focus: sensei_core::domain::request_context::OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        };
        assert!(service.get_work_order(&scoped, created_a.id).await.is_ok());
        let list = service
            .list_work_orders(&scoped, &WorkOrderListFilter::default())
            .await
            .unwrap();
        assert_eq!(
            list.total, 1,
            "a work-center scope lists only its own orders"
        );
    }

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
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };

        let created = service
            .create_work_order(&rc(tenant_id), wo)
            .await
            .expect("should create work order");
        assert!(created.wo_number.starts_with("WO-"));
        assert_eq!(created.status, "created");

        let fetched = service
            .get_work_order(&rc(tenant_id), created.id)
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
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };

        let created = service.create_work_order(&rc(tenant_id), wo).await.unwrap();
        let updated = service
            .update_work_order_status(&rc(tenant_id), created.id, "in_progress")
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
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };

        let created = service.create_work_order(&rc(tenant_id), wo).await.unwrap();
        let reported = service
            .report_production(&rc(tenant_id), created.id, 10, 0, Uuid::new_v4())
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
            short_close_qty: 0.0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            created_at: Utc::now(),
        };

        let created = service
            .create_production_order(&rc(tenant_id), po)
            .await
            .expect("should create production order");
        assert!(created.order_number.starts_with("PO-"));
        assert_eq!(created.status, "planned");

        // An unaccounted completion must be rejected (no fabricated output).
        let rejected = service
            .complete_production_order(&rc(tenant_id), created.id, 0, None, Uuid::new_v4())
            .await;
        assert!(rejected.is_err(), "completion without production must fail");

        // A documented short close reconciles the disposition.
        let completed = service
            .complete_production_order(
                &rc(tenant_id),
                created.id,
                500,
                Some("customer changed requirement"),
                Uuid::new_v4(),
            )
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
            quantity: rust_decimal::Decimal::from(2u32),
            unit_of_measure: "pcs".to_string(),
            scrap_percent: rust_decimal::Decimal::from_f64_retain(0.05)
                .unwrap_or(rust_decimal::Decimal::ZERO),
        };

        let added = service
            .add_bom_item(&rc(tenant_id), item)
            .await
            .expect("should add BOM item");
        assert_ne!(added.id, Uuid::nil());

        let bom = service
            .get_bom(&rc(tenant_id), product_id)
            .await
            .expect("should get BOM");
        assert_eq!(bom.len(), 1);
        assert_eq!(bom[0].component_name, "Test Component");

        // Run MRP — should produce a record even with no active work orders
        let mrp_records = service
            .run_mrp(&rc(tenant_id), product_id)
            .await
            .expect("should run MRP");
        assert!(!mrp_records.is_empty());
        assert_eq!(mrp_records[0].product_id, product_id);
    }

    #[tokio::test]
    async fn test_mrp_uses_real_on_hand_inventory() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        // 30 units already on hand.
        service.seed_inventory_on_hand(product_id, 30).await;

        // Active work order demands 100 units.
        let wo = WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id,
            product_name: "Widget".to_string(),
            quantity: 100,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: None,
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };
        service.create_work_order(&rc(tenant_id), wo).await.unwrap();

        let records = service.run_mrp(&rc(tenant_id), product_id).await.unwrap();
        let record = &records[0];

        // projected = on_hand + receipts − gross = 30 + 0 − 100 → 0 (clamped).
        assert_eq!(record.gross_requirement, rust_decimal::Decimal::from(100));
        assert_eq!(record.projected_on_hand, rust_decimal::Decimal::ZERO);
        // net = gross − receipts − on_hand = 100 − 0 − 30 = 70.
        assert_eq!(record.net_requirement, rust_decimal::Decimal::from(70));
        assert_eq!(
            record.planned_order_release,
            rust_decimal::Decimal::from(70)
        );

        // With enough stock the net requirement drops to zero.
        service.seed_inventory_on_hand(product_id, 150).await;
        let records = service.run_mrp(&rc(tenant_id), product_id).await.unwrap();
        assert_eq!(
            records[0].projected_on_hand,
            rust_decimal::Decimal::from(50)
        );
        assert_eq!(records[0].net_requirement, rust_decimal::Decimal::ZERO);
    }

    #[tokio::test]
    async fn test_create_work_order_generates_operations_from_routing() {
        let service = InMemoryProductionService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();
        let wc_a = Uuid::new_v4();
        let wc_b = Uuid::new_v4();

        service
            .seed_routing(
                product_id,
                vec![
                    RoutingStep {
                        work_center_id: Some(wc_a),
                        description: "Cut material".to_string(),
                        setup_time_minutes: 10,
                        run_time_minutes: 5,
                    },
                    RoutingStep {
                        work_center_id: Some(wc_b),
                        description: "Assemble".to_string(),
                        setup_time_minutes: 20,
                        run_time_minutes: 15,
                    },
                ],
            )
            .await;

        let wo = WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id,
            product_name: "Widget".to_string(),
            quantity: 10,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: None,
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };
        let created = service.create_work_order(&rc(tenant_id), wo).await.unwrap();

        let ops = service
            .list_work_order_operations(&rc(tenant_id), created.id)
            .await
            .unwrap();
        assert_eq!(ops.len(), 2);
        assert_eq!(ops[0].operation_number, 1);
        assert_eq!(ops[0].description, "Cut material");
        assert_eq!(ops[0].work_center_id, Some(wc_a));
        assert_eq!(ops[0].run_time_minutes, Some(5));
        assert_eq!(ops[1].operation_number, 2);
        assert_eq!(ops[1].description, "Assemble");
        assert_eq!(ops[1].setup_time_minutes, Some(20));
        assert_eq!(ops[1].status, "pending");

        // Products without a routing get no operations.
        let other = Uuid::new_v4();
        let wo2 = WorkOrder {
            id: Uuid::nil(),
            tenant_id,
            wo_number: String::new(),
            product_id: other,
            product_name: "Plain".to_string(),
            quantity: 1,
            quantity_completed: 0,
            status: String::new(),
            work_center_id: None,
            priority: "normal".to_string(),
            scheduled_start: None,
            scheduled_end: None,
            actual_start: None,
            actual_end: None,
            quantity_scrapped: 0,
            short_close_qty: 0,
            short_close_reason: None,
            short_close_approved_by: None,
            short_close_at: None,
            assigned_to: Vec::new(),
            notes: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            source_sales_order_id: None,
            standard_work_id: None,
            product_revision_id: None,
            bom_revision_id: None,
            routing_revision_id: None,
            control_plan_revision_id: None,
            ctq_characteristic_set: Vec::new(),
            tooling_revision: None,
            source_sales_order_line_id: None,
            customer_requirement_revision: None,
        };
        let created2 = service
            .create_work_order(&rc(tenant_id), wo2)
            .await
            .unwrap();
        let ops = service
            .list_work_order_operations(&rc(tenant_id), created2.id)
            .await
            .unwrap();
        assert!(ops.is_empty());
    }
}

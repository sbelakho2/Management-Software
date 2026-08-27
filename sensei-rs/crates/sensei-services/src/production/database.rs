//! PostgreSQL-backed production service using sqlx.
//!
//! Provides work order, production order, BOM, and MRP management
//! backed by PostgreSQL tables. Implements [`ProductionService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sqlx::PgPool;
use std::collections::HashMap;
use uuid::Uuid;

use super::{
    BOMItem, MRPRecord, ProductionOrder, ProductionService, WorkOrder, WorkOrderOperation,
};

// ---------------------------------------------------------------------------
// Row structs (map 1:1 to PostgreSQL rows)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct WorkOrderRow {
    id: Uuid,
    tenant_id: Uuid,
    wo_number: String,
    product_id: Uuid,
    product_name: String,
    quantity: i64,
    quantity_completed: i64,
    status: String,
    work_center_id: Option<Uuid>,
    priority: String,
    scheduled_start: Option<chrono::DateTime<Utc>>,
    scheduled_end: Option<chrono::DateTime<Utc>>,
    actual_start: Option<chrono::DateTime<Utc>>,
    actual_end: Option<chrono::DateTime<Utc>>,
    quantity_scrapped: i64,
    short_close_qty: i64,
    short_close_reason: Option<String>,
    short_close_approved_by: Option<Uuid>,
    short_close_at: Option<chrono::DateTime<Utc>>,
    assigned_to: Vec<Uuid>,
    notes: String,
    created_at: chrono::DateTime<Utc>,
    updated_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct ProductionOrderRow {
    id: Uuid,
    tenant_id: Uuid,
    order_number: String,
    product_id: Uuid,
    quantity_planned: i64,
    quantity_produced: i64,
    quantity_scrapped: i64,
    status: String,
    work_center_id: Option<Uuid>,
    planned_start: chrono::DateTime<Utc>,
    planned_end: chrono::DateTime<Utc>,
    actual_start: Option<chrono::DateTime<Utc>>,
    actual_end: Option<chrono::DateTime<Utc>>,
    short_close_qty: f64,
    short_close_reason: Option<String>,
    short_close_approved_by: Option<Uuid>,
    short_close_at: Option<chrono::DateTime<Utc>>,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct BomItemRow {
    id: Uuid,
    tenant_id: Uuid,
    parent_product_id: Uuid,
    component_product_id: Uuid,
    component_name: String,
    quantity_required: f64,
    unit_of_measure: String,
    scrap_percentage: f64,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct MrpRecordRow {
    id: Uuid,
    tenant_id: Uuid,
    product_id: Uuid,
    gross_requirement: i64,
    scheduled_receipts: i64,
    projected_on_hand: i64,
    net_requirement: i64,
    planned_order_release: i64,
    time_phase_start: chrono::DateTime<Utc>,
    time_phase_end: chrono::DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn wo_row_to_domain(r: WorkOrderRow) -> WorkOrder {
    WorkOrder {
        id: r.id,
        tenant_id: r.tenant_id,
        wo_number: r.wo_number,
        product_id: r.product_id,
        product_name: r.product_name,
        quantity: r.quantity,
        quantity_completed: r.quantity_completed,
        status: r.status,
        work_center_id: r.work_center_id,
        priority: r.priority,
        scheduled_start: r.scheduled_start,
        scheduled_end: r.scheduled_end,
        actual_start: r.actual_start,
        actual_end: r.actual_end,
        quantity_scrapped: r.quantity_scrapped,
        short_close_qty: r.short_close_qty,
        short_close_reason: r.short_close_reason,
        short_close_approved_by: r.short_close_approved_by,
        short_close_at: r.short_close_at,
        assigned_to: r.assigned_to,
        notes: r.notes,
        created_at: r.created_at,
        updated_at: r.updated_at,
    }
}

fn po_row_to_domain(r: ProductionOrderRow) -> ProductionOrder {
    ProductionOrder {
        id: r.id,
        tenant_id: r.tenant_id,
        order_number: r.order_number,
        product_id: r.product_id,
        quantity_planned: r.quantity_planned,
        quantity_produced: r.quantity_produced,
        quantity_scrapped: r.quantity_scrapped,
        status: r.status,
        work_center_id: r.work_center_id,
        planned_start: r.planned_start,
        planned_end: r.planned_end,
        actual_start: r.actual_start,
        actual_end: r.actual_end,
        short_close_qty: r.short_close_qty,
        short_close_reason: r.short_close_reason,
        short_close_approved_by: r.short_close_approved_by,
        short_close_at: r.short_close_at,
        created_at: r.created_at,
    }
}

fn bom_row_to_domain(r: BomItemRow) -> BOMItem {
    BOMItem {
        id: r.id,
        tenant_id: r.tenant_id,
        parent_product_id: r.parent_product_id,
        component_product_id: r.component_product_id,
        component_name: r.component_name,
        quantity_required: r.quantity_required,
        unit_of_measure: r.unit_of_measure,
        scrap_percentage: r.scrap_percentage,
    }
}

fn mrp_row_to_domain(r: MrpRecordRow) -> MRPRecord {
    MRPRecord {
        id: r.id,
        tenant_id: r.tenant_id,
        product_id: r.product_id,
        gross_requirement: r.gross_requirement,
        scheduled_receipts: r.scheduled_receipts,
        projected_on_hand: r.projected_on_hand,
        net_requirement: r.net_requirement,
        planned_order_release: r.planned_order_release,
        time_phase_start: r.time_phase_start,
        time_phase_end: r.time_phase_end,
    }
}

// ---------------------------------------------------------------------------
// Database service
// ---------------------------------------------------------------------------

/// PostgreSQL-backed implementation of [`ProductionService`].
/// Actor for production-event records (the caller's user id is bound by
/// the route; nil here means the report did not identify an operator).
fn operator_id() -> Uuid {
    Uuid::nil()
}

pub struct DatabaseProductionService {
    pool: PgPool,
}

impl DatabaseProductionService {
    /// Create a new [`DatabaseProductionService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Generate `work_order_operations` rows from the product's routing.
    ///
    /// Each active routing step becomes one operation in sequence order. The
    /// `work_order_operations.station_id` is NOT NULL, so each step's work
    /// center is resolved to its first station (falling back to any station
    /// of the tenant); steps whose work center has no station are skipped
    /// rather than failed.
    async fn generate_operations(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
        product_id: Uuid,
    ) -> Result<()> {
        #[derive(sqlx::FromRow)]
        struct RoutingStepRow {
            sequence: i32,
            work_center_id: Option<Uuid>,
            operation: String,
            standard_time: f64,
            setup_time: f64,
        }
        let steps: Vec<RoutingStepRow> = sqlx::query_as(
            "SELECT sequence, work_center_id, operation, standard_time, setup_time \
                 FROM routings WHERE product_id = $1 AND tenant_id = $2 AND is_active = TRUE \
                 ORDER BY sequence",
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to load routings: {e}")))?;

        if steps.is_empty() {
            return Ok(());
        }

        // Resolve station ids: prefer the work center's own station, then any
        // station of the tenant. Steps with no resolvable station are skipped.
        let mut station_for_wc: HashMap<Uuid, Uuid> = HashMap::new();
        for step in &steps {
            if let Some(wc_id) = step.work_center_id {
                if station_for_wc.contains_key(&wc_id) {
                    continue;
                }
                let station: Option<Uuid> = sqlx::query_scalar(
                    "SELECT id FROM stations WHERE tenant_id = $1 AND work_center_id = $2 \
                         ORDER BY created_at LIMIT 1",
                )
                .bind(tenant_id)
                .bind(wc_id)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to resolve station: {e}")))?;
                if let Some(st) = station {
                    station_for_wc.insert(wc_id, st);
                }
            }
        }
        let fallback_station: Option<Uuid> = sqlx::query_scalar(
            "SELECT id FROM stations WHERE tenant_id = $1 ORDER BY created_at LIMIT 1",
        )
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to resolve fallback station: {e}")))?;

        let now = Utc::now();
        for step in &steps {
            let station_id = step
                .work_center_id
                .and_then(|wc| station_for_wc.get(&wc).copied())
                .or(fallback_station);
            let Some(station_id) = station_id else {
                continue;
            };
            sqlx::query(
                "INSERT INTO work_order_operations \
                     (id, tenant_id, work_order_id, sequence, station_id, operation, status, \
                      standard_time, setup_time, created_at, updated_at) \
                     VALUES ($1,$2,$3,$4,$5,$6,'pending',$7,$8,$9,$9)",
            )
            .bind(Uuid::new_v4())
            .bind(tenant_id)
            .bind(work_order_id)
            .bind(step.sequence)
            .bind(station_id)
            .bind(&step.operation)
            .bind(step.standard_time)
            .bind(step.setup_time)
            .bind(now)
            .execute(&self.pool)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to create work order operation: {e}"))
            })?;
        }

        Ok(())
    }
}

#[async_trait]
impl ProductionService for DatabaseProductionService {
    // ── Work Orders ─────────────────────────────────────────────────────

    async fn create_work_order(&self, tenant_id: Uuid, mut wo: WorkOrder) -> Result<WorkOrder> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let wo_number = format!(
            "WO-{}-{}",
            now.format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );

        wo.id = id;
        wo.tenant_id = tenant_id;
        wo.wo_number = wo_number;
        wo.status = "created".to_string();
        wo.quantity_completed = 0;
        wo.created_at = now;
        wo.updated_at = now;

        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            INSERT INTO work_orders (
                id, tenant_id, wo_number, product_id, product_name,
                quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                scheduled_start, scheduled_end, actual_start, actual_end,
                short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                assigned_to, notes, created_at, updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22)
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      assigned_to, notes, created_at, updated_at
            "#,
        )
        .bind(wo.id)
        .bind(tenant_id)
        .bind(&wo.wo_number)
        .bind(wo.product_id)
        .bind(&wo.product_name)
        .bind(wo.quantity)
        .bind(wo.quantity_completed)
        .bind(&wo.status)
        .bind(wo.work_center_id)
        .bind(&wo.priority)
        .bind(wo.scheduled_start)
        .bind(wo.scheduled_end)
        .bind(wo.actual_start)
        .bind(wo.actual_end)
        .bind(wo.short_close_qty)
        .bind(&wo.short_close_reason)
        .bind(wo.short_close_approved_by)
        .bind(wo.short_close_at)
        .bind(&wo.assigned_to)
        .bind(&wo.notes)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create work order: {e}")))?;

        // Generate the operations from the product's routing (when configured).
        self.generate_operations(tenant_id, id, wo.product_id)
            .await?;

        Ok(wo_row_to_domain(row))
    }
    async fn get_work_order(&self, tenant_id: Uuid, id: Uuid) -> Result<WorkOrder> {
        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            SELECT id, tenant_id, wo_number, product_id, product_name,
                   quantity, quantity_completed, status, work_center_id, priority,
                   scheduled_start, scheduled_end, actual_start, actual_end,
                   assigned_to, notes, created_at, updated_at
            FROM work_orders
            WHERE id = $1 AND tenant_id = $2
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get work order: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;

        Ok(wo_row_to_domain(row))
    }

    async fn list_work_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<WorkOrder>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<WorkOrderRow> = sqlx::query_as(
            r#"
            SELECT id, tenant_id, wo_number, product_id, product_name,
                   quantity, quantity_completed, status, work_center_id, priority,
                   scheduled_start, scheduled_end, actual_start, actual_end,
                   assigned_to, notes, created_at, updated_at
            FROM work_orders
            WHERE tenant_id = $1
              AND ($2::text IS NULL OR status = $2)
              AND ($3::uuid IS NULL OR work_center_id = $3)
            ORDER BY created_at DESC
            LIMIT $4 OFFSET $5
            "#,
        )
        .bind(tenant_id)
        .bind(status)
        .bind(work_center_id)
        .bind(per_page as i64)
        .bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list work orders: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            r#"
            SELECT COUNT(*) FROM work_orders
            WHERE tenant_id = $1
              AND ($2::text IS NULL OR status = $2)
              AND ($3::uuid IS NULL OR work_center_id = $3)
            "#,
        )
        .bind(tenant_id)
        .bind(status)
        .bind(work_center_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to count work orders: {e}")))?;

        let items = items.into_iter().map(wo_row_to_domain).collect();
        Ok(PaginatedResponse {
            data: items,
            total: count as usize,
            page,
            per_page,
            total_pages: (count as usize).max(1).div_ceil(per_page),
        })
    }

    async fn update_work_order_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<WorkOrder> {
        let now = Utc::now();

        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            UPDATE work_orders
            SET status = $1,
                actual_start = CASE WHEN $1 = 'in_progress' AND actual_start IS NULL THEN $3 ELSE actual_start END,
                actual_end = CASE WHEN $1 = 'completed' AND actual_end IS NULL THEN $3 ELSE actual_end END,
                updated_at = $3
            WHERE id = $4 AND tenant_id = $2
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      assigned_to, notes, created_at, updated_at
            "#,
        )
        .bind(status)
        .bind(tenant_id)
        .bind(now)
        .bind(id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update work order status: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;

        Ok(wo_row_to_domain(row))
    }

    async fn update_work_order(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        wo: WorkOrder,
    ) -> Result<WorkOrder> {
        let now = Utc::now();

        // Identity fields come from the stored record; the caller-supplied
        // values for them are never trusted.
        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            UPDATE work_orders
            SET product_id = $1,
                product_name = $2,
                quantity = $3,
                quantity_completed = CASE WHEN $4 = 0 AND quantity_completed > 0 THEN quantity_completed ELSE $4 END,
                status = $5,
                work_center_id = $6,
                priority = $7,
                scheduled_start = $8,
                scheduled_end = $9,
                assigned_to = $10,
                notes = $11,
                updated_at = $12
            WHERE id = $13 AND tenant_id = $14
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      assigned_to, notes, created_at, updated_at
            "#,
        )
        .bind(wo.product_id)
        .bind(wo.product_name)
        .bind(wo.quantity)
        .bind(wo.quantity_completed)
        .bind(wo.quantity_scrapped)
        .bind(wo.status)
        .bind(wo.work_center_id)
        .bind(wo.priority)
        .bind(wo.scheduled_start)
        .bind(wo.scheduled_end)
        .bind(&wo.assigned_to)
        .bind(wo.notes)
        .bind(now)
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update work order: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;

        Ok(wo_row_to_domain(row))
    }

    async fn report_production(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
        quantity_completed: i64,
        quantity_scrapped: i64,
    ) -> Result<WorkOrder> {
        // Scrap reported by the shop floor must never disappear: negative
        // or absurd reports are rejected, and every report is appended to
        // the immutable production-event ledger.
        if quantity_completed < 0 || quantity_scrapped < 0 {
            return Err(SenseiError::Validation(
                "Production and scrap quantities cannot be negative".to_string(),
            ));
        }
        let now = Utc::now();

        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin report tx: {e}")))?;

        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            UPDATE work_orders
            SET quantity_completed = quantity_completed + $1,
                quantity_scrapped = quantity_scrapped + $5,
                status = CASE
                    WHEN quantity_completed + $1 >= quantity AND status != 'completed' THEN 'completed'
                    ELSE status
                END,
                actual_end = CASE
                    WHEN quantity_completed + $1 >= quantity AND status != 'completed' THEN $4
                    ELSE actual_end
                END,
                updated_at = $4
            WHERE id = $2 AND tenant_id = $3
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, quantity_scrapped,
                      short_close_qty, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      assigned_to, notes, created_at, updated_at
            "#,
        )
        .bind(quantity_completed)
        .bind(work_order_id)
        .bind(tenant_id)
        .bind(now)
        .bind(quantity_scrapped)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to report production: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work order {work_order_id} not found")))?;

        // Append to the immutable event ledger (same transaction).
        sqlx::query(
            "INSERT INTO production_events \
                (id, tenant_id, event_type, work_order_id, product_id, good_qty, \
                 scrap_qty, operator_id, occurred_at) \
             VALUES ($1, $2, 'produced', $3, $4, $5, $6, $7, $8)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(work_order_id)
        .bind(row.product_id)
        .bind(quantity_completed)
        .bind(quantity_scrapped)
        .bind(operator_id())
        .bind(now)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to record production event: {e}")))?;

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit report tx: {e}")))?;

        Ok(wo_row_to_domain(row))
    }

    // ── Production Orders ───────────────────────────────────────────────

    async fn create_production_order(
        &self,
        tenant_id: Uuid,
        mut order: ProductionOrder,
    ) -> Result<ProductionOrder> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let order_number = format!(
            "PO-{}-{}",
            now.format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );

        order.id = id;
        order.tenant_id = tenant_id;
        order.order_number = order_number;
        order.status = "planned".to_string();
        order.quantity_produced = 0;
        order.quantity_scrapped = 0;
        order.created_at = now;

        let row = sqlx::query_as::<_, ProductionOrderRow>(
            r#"
            INSERT INTO production_orders (
                id, tenant_id, order_number, product_id,
                quantity_planned, quantity_produced, quantity_scrapped,
                status, work_center_id, planned_start, planned_end,
                actual_start, actual_end, created_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            RETURNING id, tenant_id, order_number, product_id,
                      quantity_planned, quantity_produced, quantity_scrapped,
                      status, work_center_id, planned_start, planned_end,
                      actual_start, actual_end, created_at
            "#,
        )
        .bind(order.id)
        .bind(tenant_id)
        .bind(&order.order_number)
        .bind(order.product_id)
        .bind(order.quantity_planned)
        .bind(order.quantity_produced)
        .bind(order.quantity_scrapped)
        .bind(&order.status)
        .bind(order.work_center_id)
        .bind(order.planned_start)
        .bind(order.planned_end)
        .bind(order.actual_start)
        .bind(order.actual_end)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create production order: {e}")))?;

        Ok(po_row_to_domain(row))
    }

    async fn get_production_order(&self, tenant_id: Uuid, id: Uuid) -> Result<ProductionOrder> {
        let row = sqlx::query_as::<_, ProductionOrderRow>(
            r#"
            SELECT id, tenant_id, order_number, product_id,
                   quantity_planned, quantity_produced, quantity_scrapped,
                   status, work_center_id, planned_start, planned_end,
                   actual_start, actual_end, created_at
            FROM production_orders
            WHERE id = $1 AND tenant_id = $2
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get production order: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Production order {id} not found")))?;

        Ok(po_row_to_domain(row))
    }

    async fn list_production_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProductionOrder>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<ProductionOrderRow> = sqlx::query_as(
            r#"
            SELECT id, tenant_id, order_number, product_id,
                   quantity_planned, quantity_produced, quantity_scrapped,
                   status, work_center_id, planned_start, planned_end,
                   actual_start, actual_end, created_at
            FROM production_orders
            WHERE tenant_id = $1
              AND ($2::text IS NULL OR status = $2)
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            "#,
        )
        .bind(tenant_id)
        .bind(status)
        .bind(per_page as i64)
        .bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list production orders: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            r#"
            SELECT COUNT(*) FROM production_orders
            WHERE tenant_id = $1 AND ($2::text IS NULL OR status = $2)
            "#,
        )
        .bind(tenant_id)
        .bind(status)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to count production orders: {e}")))?;

        let items = items.into_iter().map(po_row_to_domain).collect();
        Ok(PaginatedResponse {
            data: items,
            total: count as usize,
            page,
            per_page,
            total_pages: (count as usize).max(1).div_ceil(per_page),
        })
    }

    async fn complete_production_order(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        short_close_qty: i64,
        short_close_reason: Option<&str>,
        approver: Uuid,
    ) -> Result<ProductionOrder> {
        let now = Utc::now();

        let mut tx =
            self.pool.begin().await.map_err(|e| {
                SenseiError::Database(format!("Failed to begin completion tx: {e}"))
            })?;

        let existing = sqlx::query_as::<_, ProductionOrderRow>(
            r#"
            SELECT id, tenant_id, order_number, product_id,
                   quantity_planned, quantity_produced, quantity_scrapped,
                   status, work_center_id, planned_start, planned_end,
                   actual_start, actual_end, created_at
            FROM production_orders
            WHERE id = $1 AND tenant_id = $2
            FOR UPDATE
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get production order: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Production order {id} not found")))?;

        if existing.status == "completed" {
            return Err(SenseiError::Validation(
                "Production order is already completed".to_string(),
            ));
        }

        // Completion must NEVER fabricate output: the dispositioned
        // quantity must reconcile with what actually happened.
        let produced = existing.quantity_produced as i64;
        let scrapped = existing.quantity_scrapped as i64;
        let planned = existing.quantity_planned as i64;
        let accounted = produced + scrapped + short_close_qty;
        if accounted < planned {
            return Err(SenseiError::Validation(format!(
                "Cannot complete: {accounted} of {planned} units accounted for \
                 (produced {produced} + scrap {scrapped} + short close {short_close_qty}). \
                 Report the remaining production or provide a short close."
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

        let row = sqlx::query_as::<_, ProductionOrderRow>(
            r#"
            UPDATE production_orders
            SET status = 'completed',
                actual_end = $1,
                short_close_qty = $4,
                short_close_reason = $5,
                short_close_approved_by = $6,
                short_close_at = CASE WHEN $4 > 0 THEN $1 ELSE NULL END,
                updated_at = $1
            WHERE id = $2 AND tenant_id = $3
            RETURNING id, tenant_id, order_number, product_id,
                      quantity_planned, quantity_produced, quantity_scrapped,
                      status, work_center_id, planned_start, planned_end,
                      actual_start, actual_end, created_at
            "#,
        )
        .bind(now)
        .bind(id)
        .bind(tenant_id)
        .bind(short_close_qty)
        .bind(short_close_reason)
        .bind(approver)
        .fetch_one(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to complete production order: {e}")))?;

        // Append the completion event to the ledger.
        sqlx::query(
            "INSERT INTO production_events \
                (id, tenant_id, event_type, work_order_id, product_id, good_qty, \
                 scrap_qty, reason_code, operator_id, occurred_at) \
             VALUES ($1, $2, 'completed', $3, $4, $5, $6, $7, $8, $9)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(id)
        .bind(row.product_id)
        .bind(produced)
        .bind(scrapped)
        .bind(short_close_reason.unwrap_or(""))
        .bind(approver)
        .bind(now)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to record completion event: {e}")))?;

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit completion tx: {e}")))?;

        Ok(po_row_to_domain(row))
    }

    // ── BOM ─────────────────────────────────────────────────────────────

    async fn add_bom_item(&self, tenant_id: Uuid, item: BOMItem) -> Result<BOMItem> {
        let id = Uuid::new_v4();

        let row = sqlx::query_as::<_, BomItemRow>(
            r#"
            INSERT INTO bom_items (
                id, tenant_id, parent_product_id, component_product_id,
                component_name, quantity_required, unit_of_measure, scrap_percentage
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING id, tenant_id, parent_product_id, component_product_id,
                      component_name, quantity_required, unit_of_measure, scrap_percentage
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(item.parent_product_id)
        .bind(item.component_product_id)
        .bind(&item.component_name)
        .bind(item.quantity_required)
        .bind(&item.unit_of_measure)
        .bind(item.scrap_percentage)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to add BOM item: {e}")))?;

        Ok(bom_row_to_domain(row))
    }

    async fn get_bom(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<BOMItem>> {
        let rows = sqlx::query_as::<_, BomItemRow>(
            r#"
            SELECT id, tenant_id, parent_product_id, component_product_id,
                   component_name, quantity_required, unit_of_measure, scrap_percentage
            FROM bom_items
            WHERE parent_product_id = $1 AND tenant_id = $2
            "#,
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get BOM: {e}")))?;

        Ok(rows.into_iter().map(bom_row_to_domain).collect())
    }

    // ── MRP ─────────────────────────────────────────────────────────────

    async fn run_mrp(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<MRPRecord>> {
        let now = Utc::now();

        let gross_requirement: i64 = sqlx::query_scalar(
            r#"
            SELECT COALESCE(SUM(quantity - quantity_completed), 0)
            FROM work_orders
            WHERE product_id = $1 AND tenant_id = $2 AND status NOT IN ('completed', 'cancelled')
            "#,
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("Failed to compute MRP gross requirement: {e}"))
        })?;

        let scheduled_receipts: i64 = sqlx::query_scalar(
            r#"
            SELECT COALESCE(SUM(quantity_planned - quantity_produced), 0)
            FROM production_orders
            WHERE product_id = $1 AND tenant_id = $2 AND status NOT IN ('completed', 'cancelled')
            "#,
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("Failed to compute MRP scheduled receipts: {e}"))
        })?;

        // Projected on-hand: real current inventory + scheduled receipts −
        // gross requirement (never negative), matching the in-memory impl.
        let on_hand: i64 = sqlx::query_scalar(
            r#"
            SELECT COALESCE(SUM(quantity_on_hand::bigint), 0)
            FROM inventory_items
            WHERE product_id = $1 AND tenant_id = $2
            "#,
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to compute MRP on-hand: {e}")))?;

        let projected_on_hand = (on_hand + scheduled_receipts - gross_requirement).max(0);
        let net_requirement = (gross_requirement - scheduled_receipts - on_hand).max(0);
        let planned_order_release = net_requirement;

        let id = Uuid::new_v4();
        let time_phase_start = now;
        let time_phase_end = now + chrono::Duration::days(30);

        let row = sqlx::query_as::<_, MrpRecordRow>(
            r#"
            INSERT INTO mrp_records (
                id, tenant_id, product_id, gross_requirement, scheduled_receipts,
                projected_on_hand, net_requirement, planned_order_release,
                time_phase_start, time_phase_end
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id, tenant_id, product_id, gross_requirement, scheduled_receipts,
                      projected_on_hand, net_requirement, planned_order_release,
                      time_phase_start, time_phase_end
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(product_id)
        .bind(gross_requirement)
        .bind(scheduled_receipts)
        .bind(projected_on_hand)
        .bind(net_requirement)
        .bind(planned_order_release)
        .bind(time_phase_start)
        .bind(time_phase_end)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create MRP record: {e}")))?;

        Ok(vec![mrp_row_to_domain(row)])
    }

    async fn list_work_order_operations(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
    ) -> Result<Vec<WorkOrderOperation>> {
        // First verify the work order exists and belongs to the tenant
        let wo_exists: bool = sqlx::query_scalar(
            "SELECT EXISTS(SELECT 1 FROM work_orders WHERE id = $1 AND tenant_id = $2)",
        )
        .bind(work_order_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to check work order existence: {e}")))?;

        if !wo_exists {
            return Err(SenseiError::NotFound(format!(
                "Work order {work_order_id} not found"
            )));
        }

        let rows = sqlx::query_as::<_, WorkOrderOperationRow>(
            r#"
            SELECT id, work_order_id, sequence, station_id, operation,
                   status, standard_time, setup_time,
                   started_at, completed_at, created_at
            FROM work_order_operations
            WHERE work_order_id = $1 AND tenant_id = $2
            ORDER BY sequence
            "#,
        )
        .bind(work_order_id)
        .bind(tenant_id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list work order operations: {e}")))?;

        Ok(rows
            .into_iter()
            .map(|r| WorkOrderOperation {
                id: r.id,
                work_order_id: r.work_order_id,
                operation_number: r.sequence,
                description: r.operation,
                work_center_id: Some(r.station_id),
                setup_time_minutes: Some(r.setup_time as i32),
                run_time_minutes: Some(r.standard_time as i32),
                status: r.status,
                started_at: r.started_at,
                completed_at: r.completed_at,
                created_at: r.created_at,
            })
            .collect())
    }
}

/// Database row for work order operations (columns actually mapped to the
/// domain [`WorkOrderOperation`]).
#[derive(Debug, Clone, sqlx::FromRow)]
struct WorkOrderOperationRow {
    id: Uuid,
    work_order_id: Uuid,
    sequence: i32,
    station_id: Uuid,
    operation: String,
    status: String,
    standard_time: f64,
    setup_time: f64,
    started_at: Option<chrono::DateTime<Utc>>,
    completed_at: Option<chrono::DateTime<Utc>>,
    created_at: chrono::DateTime<Utc>,
}

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
    source_sales_order_id: Option<Uuid>,
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
    quantity: rust_decimal::Decimal,
    unit_of_measure: String,
    scrap_percent: rust_decimal::Decimal,
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
        source_sales_order_id: r.source_sales_order_id,
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
        quantity: r.quantity,
        unit_of_measure: r.unit_of_measure,
        scrap_percent: r.scrap_percent,
    }
}

// ---------------------------------------------------------------------------
// Database service
// ---------------------------------------------------------------------------

/// PostgreSQL-backed implementation of [`ProductionService`].
/// Transaction-scoped tenant context for RLS (SET LOCAL app.tenant_id).
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> std::result::Result<(), SenseiError> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
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
        tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
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
        .fetch_all(&mut **tx)
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
                .fetch_optional(&mut **tx)
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
        .fetch_optional(&mut **tx)
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
            .execute(&mut **tx)
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

        // Item 28: the work-order state mutation and its workflow-driving
        // event are ONE transaction — a committed WO can never lose its
        // event to a post-commit publish failure.
        let mut self_tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin WO tx: {e}")))?;
        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            INSERT INTO work_orders (
                id, tenant_id, wo_number, product_id, product_name,
                quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                scheduled_start, scheduled_end, actual_start, actual_end,
                short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                assigned_to, notes, created_at, updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23)
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      quantity_scrapped, short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      assigned_to, notes, created_at, updated_at, source_sales_order_id
            "#,
        )
        .bind(wo.id)
        .bind(tenant_id)
        .bind(&wo.wo_number)
        .bind(wo.product_id)
        .bind(&wo.product_name)
        .bind(wo.quantity)
        .bind(wo.quantity_completed)
        .bind(wo.quantity_scrapped)
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
        .bind(wo.source_sales_order_id)
        .fetch_one(&mut *self_tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create work order: {e}")))?;

        // Generate the operations from the product's routing (when configured)
        // INSIDE the same transaction — operation rows cannot survive
        // independently of their parent, and routing/station reads see the
        // same snapshot as the insert (P0-2).
        self.generate_operations(&mut self_tx, tenant_id, id, wo.product_id)
            .await?;

        sensei_db::outbox::enqueue_outbox(
            &mut self_tx,
            tenant_id,
            "work_order",
            id,
            "sensei.production.work-order.created",
            serde_json::json!({
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "status": "created",
            }),
        )
        .await?;
        self_tx
            .commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit WO tx: {e}")))?;

        Ok(wo_row_to_domain(row))
    }
    async fn get_work_order(&self, tenant_id: Uuid, id: Uuid) -> Result<WorkOrder> {
        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            SELECT id, tenant_id, wo_number, product_id, product_name,
                   quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                   scheduled_start, scheduled_end, actual_start, actual_end,
                   quantity_scrapped, short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                   assigned_to, notes, created_at, updated_at, source_sales_order_id
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
                   quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                   scheduled_start, scheduled_end, actual_start, actual_end,
                   quantity_scrapped, short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                   assigned_to, notes, created_at, updated_at, source_sales_order_id
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

        // Validated lifecycle: Created -> Released -> InProgress ->
        // Completed; Released/InProgress -> OnHold; Created/Released ->
        // Cancelled. Anything else is an impossible jump and is rejected.
        let allowed = matches!(
            (status, status),
            (
                "created" | "released" | "in_progress" | "completed" | "on_hold" | "cancelled",
                _
            )
        );
        if !allowed {
            return Err(SenseiError::Validation(format!(
                "Unknown work order status '{status}'"
            )));
        }
        // Current state gates the transition.
        let current: Option<String> =
            sqlx::query_scalar("SELECT status FROM work_orders WHERE id = $1 AND tenant_id = $2")
                .bind(id)
                .bind(tenant_id)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to read work order status: {e}"))
                })?
                .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;
        let legal = matches!(
            (current.as_deref(), status),
            (Some("created"), "released" | "cancelled")
                | (Some("released"), "in_progress" | "on_hold" | "cancelled")
                | (Some("in_progress"), "completed" | "on_hold")
                | (Some("on_hold"), "in_progress")
        );
        if !legal {
            return Err(SenseiError::Conflict(format!(
                "Illegal work order transition '{}' -> '{}'",
                current.as_deref().unwrap_or("?"),
                status
            )));
        }

        // Item 28: the status transition and its workflow-driving event
        // are ONE transaction.
        let mut status_tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin WO status tx: {e}")))?;
        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            UPDATE work_orders
            SET status = $1,
                actual_start = CASE WHEN $1 = 'in_progress' AND actual_start IS NULL THEN $3 ELSE actual_start END,
                actual_end = CASE WHEN $1 = 'completed' AND actual_end IS NULL THEN $3 ELSE actual_end END,
                updated_at = $3
            WHERE id = $4 AND tenant_id = $2
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      quantity_scrapped, short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      assigned_to, notes, created_at, updated_at, source_sales_order_id
            "#,
        )
        .bind(status)
        .bind(tenant_id)
        .bind(now)
        .bind(id)
        .fetch_optional(&mut *status_tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update work order status: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work order {id} not found")))?;

        sensei_db::outbox::enqueue_outbox(
            &mut status_tx,
            tenant_id,
            "work_order",
            id,
            "sensei.production.work-order.status-changed",
            serde_json::json!({
                "wo_number": row.wo_number,
                "from_status": current,
                "to_status": status,
            }),
        )
        .await?;
        status_tx
            .commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit WO status tx: {e}")))?;

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
                quantity_scrapped = $5,
                status = $6,
                work_center_id = $7,
                priority = $8,
                scheduled_start = $9,
                scheduled_end = $10,
                assigned_to = $11,
                notes = $12,
                updated_at = $13
            WHERE id = $14 AND tenant_id = $15
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, quantity_scrapped, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      quantity_scrapped, short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      assigned_to, notes, created_at, updated_at, source_sales_order_id
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
        actor_id: Uuid,
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
        set_tenant_context(&mut tx, tenant_id).await?;

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
                      short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      assigned_to, notes, created_at, updated_at, source_sales_order_id
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
        // MES-grade provenance: WHO reported is part of the immutable event.
        .bind(actor_id)
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
                actual_start, actual_end,
                short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                created_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
            RETURNING id, tenant_id, order_number, product_id,
                      quantity_planned, quantity_produced, quantity_scrapped,
                      status, work_center_id, planned_start, planned_end,
                      actual_start, actual_end,
                      short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      created_at
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
        .bind(0i64)
        .bind(Option::<String>::None)
        .bind(Option::<Uuid>::None)
        .bind(Option::<chrono::DateTime<Utc>>::None)
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
                   actual_start, actual_end,
                   short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                   created_at
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
                   actual_start, actual_end,
                   short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                   created_at
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
                   actual_start, actual_end,
                   short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                   created_at
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
        if accounted != planned {
            return Err(SenseiError::Validation(format!(
                "Cannot complete: {accounted} of {planned} units accounted for \
                 (produced {produced} + scrap {scrapped} + short close {short_close_qty}). \
                 Disposition must reconcile EXACTLY — report the difference or provide a \
                 short close / approved overproduction variance."
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
                      actual_start, actual_end,
                      short_close_qty, short_close_reason, short_close_approved_by, short_close_at,
                      created_at
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
            WITH ins AS (
                INSERT INTO bom_items (
                    id, tenant_id, parent_product_id, component_product_id,
                    quantity, unit_of_measure, scrap_percent
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
                RETURNING id, tenant_id, parent_product_id, component_product_id,
                          quantity, unit_of_measure, scrap_percent
            )
            SELECT ins.id, ins.tenant_id, ins.parent_product_id, ins.component_product_id,
                   p.name AS component_name, ins.quantity, ins.unit_of_measure, ins.scrap_percent
            FROM ins JOIN products p ON p.id = ins.component_product_id
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(item.parent_product_id)
        .bind(item.component_product_id)
        .bind(item.quantity)
        .bind(&item.unit_of_measure)
        .bind(item.scrap_percent)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to add BOM item: {e}")))?;

        Ok(bom_row_to_domain(row))
    }

    async fn get_bom(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<BOMItem>> {
        // Item 29: ONE BOM vocabulary — quantity / scrap_percent (the
        // schema columns). The old quantity_required/scrap_percentage
        // aliases do not exist on bom_items and made get_bom fail at
        // runtime.
        let rows = sqlx::query_as::<_, BomItemRow>(
            r#"
            SELECT b.id, b.tenant_id, b.parent_product_id, b.component_product_id,
                   p.name AS component_name, b.quantity, b.unit_of_measure,
                   COALESCE(b.scrap_percent, 0) AS scrap_percent
            FROM bom_items b
            JOIN products p ON p.id = b.component_product_id AND p.tenant_id = b.tenant_id
            WHERE b.parent_product_id = $1 AND b.tenant_id = $2
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

        // ── 1. Independent demand for the product ──────────────────────
        // Demand = open SALES ORDERS (the customer pull) plus the
        // unfinished work-order backlog (execution supply already created
        // for demand). Sales demand drives planning; the work-order
        // backlog is the in-flight portion of that demand.
        let so_demand: rust_decimal::Decimal = sqlx::query_scalar(
            "SELECT COALESCE(SUM(                 (li->>'quantity')::numeric - COALESCE((li->>'quantity_delivered')::numeric, 0)             ), 0)::numeric \
             FROM sales_orders so, jsonb_array_elements(so.line_items) AS li \
             WHERE so.tenant_id = $1 \
               AND (li->>'product_id')::uuid = $2 \
               AND so.status NOT IN ('completed', 'cancelled', 'closed')",
        )
        .bind(tenant_id)
        .bind(product_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to compute sales demand: {e}")))?;
        let wo_backlog: rust_decimal::Decimal = sqlx::query_scalar(
            "SELECT COALESCE(SUM(quantity - quantity_completed), 0)::numeric \
             FROM work_orders \
             WHERE product_id = $1 AND tenant_id = $2 AND status NOT IN ('completed', 'cancelled')",
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to compute work-order backlog: {e}")))?;
        // Item 31 (demand pegging): work orders that CARRY their source
        // sales-order id are in-flight supply AGAINST that SO demand —
        // they shrink the remaining demand instead of being double
        // counted. Unpegged work orders (legacy WOs without a source
        // link) are INDEPENDENT demand and add on top.
        let pegged_backlog: rust_decimal::Decimal = sqlx::query_scalar(
            "SELECT COALESCE(SUM(quantity - quantity_completed), 0)::numeric \
             FROM work_orders \
             WHERE product_id = $1 AND tenant_id = $2 \
               AND source_sales_order_id IS NOT NULL \
               AND status NOT IN ('completed', 'cancelled')",
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to compute pegged backlog: {e}")))?;
        // Pegging semantics (item 31): with the WO→SO linkage present,
        // demand is EXACT — pegged supply covers SO demand, unpegged WOs
        // are independent demand (audit example: SO 1000 + pegged 600 +
        // independent 500 → 900, not the ambiguous 1000-or-1100 of max()).
        // WITHOUT the linkage (legacy WOs untagged) the max() heuristic
        // stays — it is the safe no-information answer that avoids
        // double-counting SOs already converted into work orders.
        let demand_qty = if pegged_backlog > rust_decimal::Decimal::ZERO {
            let so_remaining = (so_demand - pegged_backlog).max(rust_decimal::Decimal::ZERO);
            let independent_backlog =
                (wo_backlog - pegged_backlog).max(rust_decimal::Decimal::ZERO);
            so_remaining + independent_backlog
        } else if so_demand > wo_backlog {
            so_demand
        } else {
            wo_backlog
        };

        // ── 2. BOM explosion (multi-level, scrap-aware) ────────────────
        // gross[product] accumulates the quantity required at each level;
        // children of make items are exploded recursively (depth-limited).
        let mut gross: std::collections::HashMap<Uuid, rust_decimal::Decimal> =
            std::collections::HashMap::new();
        *gross
            .entry(product_id)
            .or_insert(rust_decimal::Decimal::ZERO) += demand_qty;
        // Item 17: earliest need date per product — the MIN over all paths
        // that require it (a component feeding two parents is needed by
        // the EARLIER one).
        let mut need_dates: std::collections::HashMap<Uuid, chrono::DateTime<Utc>> =
            std::collections::HashMap::new();
        // Cycle detection (item 16): each queue item carries its FULL
        // ancestry chain; a component that is an ancestor of its own parent
        // is a cycle and is REJECTED — the previous visited/in_stack pair
        // cleared the stack between levels and silently truncated cycles.
        // Item 17: each item also carries its requirement date, which
        // propagates BACKWARD through the BOM — a component is needed no
        // later than its parent's planned release.
        // Item 33: lead times are cached ON DISCOVERY — the initial map
        // holds only the root product; deeper components discovered during
        // traversal must NOT propagate requirements with a silent zero
        // lead time. load_leads_for() fetches any unknown leads.
        let mut lead_by_product: std::collections::HashMap<Uuid, i64> =
            std::collections::HashMap::new();
        {
            let rows: Vec<(Uuid, i32)> = sqlx::query_as(
                "SELECT id, COALESCE(lead_time_days, 0) FROM products \
                 WHERE tenant_id = $1 AND id = ANY($2::uuid[])",
            )
            .bind(tenant_id)
            .bind(gross.keys().copied().collect::<Vec<Uuid>>())
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to load lead times: {e}")))?;
            for (id, lead) in rows {
                lead_by_product.insert(id, i64::from(lead));
            }
        }
        // The root need date: the demand's own timing (earliest open
        // work-order due date); without one, the requirement is due NOW —
        // never an arbitrary now+30d default (item 17).
        // Item 32: the customer's REQUESTED/DELIVERY date is the primary
        // independent-demand time bucket — sales demand with no work order
        // yet must still drive the plan. Work-order dates (execution
        // supply) are secondary: the plan is due no later than BOTH.
        let so_due: Option<chrono::DateTime<Utc>> = sqlx::query_scalar(
            "SELECT MIN(delivery_date) FROM sales_orders so \
             WHERE so.tenant_id = $1 \
               AND EXISTS ( \
                   SELECT 1 FROM jsonb_array_elements(so.line_items) li \
                   WHERE (li->>'product_id')::uuid = $2 \
               ) \
               AND so.status NOT IN ('completed', 'cancelled', 'closed') \
               AND so.delivery_date IS NOT NULL",
        )
        .bind(tenant_id)
        .bind(product_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to load sales demand timing: {e}")))?;
        let wo_due: Option<chrono::DateTime<Utc>> = sqlx::query_scalar(
            "SELECT MIN(scheduled_end) FROM work_orders \
             WHERE product_id = $1 AND tenant_id = $2 \
               AND status NOT IN ('completed', 'cancelled')",
        )
        .bind(product_id)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to load demand timing: {e}")))?;
        let root_need = match (so_due, wo_due) {
            (Some(so), Some(wo)) => so.min(wo),
            (Some(so), None) => so,
            (None, Some(wo)) => wo,
            (None, None) => now,
        };
        need_dates.insert(product_id, root_need);

        let mut queue: Vec<(
            Uuid,
            rust_decimal::Decimal,
            chrono::DateTime<Utc>,
            Vec<Uuid>,
        )> = vec![(product_id, demand_qty, root_need, vec![])];
        while !queue.is_empty() {
            let mut next: Vec<(
                Uuid,
                rust_decimal::Decimal,
                chrono::DateTime<Utc>,
                Vec<Uuid>,
            )> = Vec::new();
            for (parent, qty, need_date, ancestors) in queue {
                let mut ancestry = ancestors.clone();
                ancestry.push(parent);
                let bom: Vec<(Uuid, rust_decimal::Decimal, rust_decimal::Decimal)> =
                    sqlx::query_as(
                        "SELECT component_product_id, quantity, COALESCE(scrap_percent, 0) \
                     FROM bom_items b \
                     WHERE b.parent_product_id = $1 AND b.tenant_id = $2 AND b.is_active = TRUE",
                    )
                    .bind(parent)
                    .bind(tenant_id)
                    .fetch_all(&self.pool)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to load BOM: {e}")))?;
                // Item 33: cache the lead time of every component AT
                // DISCOVERY (one batched query per level, never per row).
                let unknown: Vec<Uuid> = bom
                    .iter()
                    .map(|(c, _, _)| *c)
                    .filter(|c| !lead_by_product.contains_key(c))
                    .collect();
                if !unknown.is_empty() {
                    let rows: Vec<(Uuid, i32)> = sqlx::query_as(
                        "SELECT id, COALESCE(lead_time_days, 0) FROM products \
                         WHERE tenant_id = $1 AND id = ANY($2::uuid[])",
                    )
                    .bind(tenant_id)
                    .bind(&unknown)
                    .fetch_all(&self.pool)
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("Failed to load component leads: {e}"))
                    })?;
                    for (id, lead) in rows {
                        lead_by_product.insert(id, i64::from(lead));
                    }
                }
                for (component, per_unit, scrap) in bom {
                    if ancestry.contains(&component) {
                        let chain = ancestry
                            .iter()
                            .map(|u| u.to_string())
                            .collect::<Vec<_>>()
                            .join(" -> ");
                        return Err(SenseiError::Validation(format!(
                            "CYCLIC BOM detected: {chain} -> {component} — a BOM must be a DAG"
                        )));
                    }
                    // Gross includes the scrap factor: making 100 with 5%
                    // scrap consumes 105.
                    let need = qty
                        * per_unit
                        * (rust_decimal::Decimal::ONE
                            + scrap / rust_decimal::Decimal::from(100u32));
                    *gross
                        .entry(component)
                        .or_insert(rust_decimal::Decimal::ZERO) += need;
                    // Time phasing (item 17): the component is needed when
                    // the parent must START — the parent's need date offset
                    // back by the parent's lead time.
                    let parent_lead = lead_by_product.get(&parent).copied().unwrap_or(0);
                    let component_need = need_date - chrono::Duration::days(parent_lead);
                    need_dates
                        .entry(component)
                        .and_modify(|d| {
                            if component_need < *d {
                                *d = component_need;
                            }
                        })
                        .or_insert(component_need);
                    next.push((component, need, component_need, ancestry.clone()));
                }
            }
            queue = next;
        }

        // ── 3. Scheduled receipts + on-hand per product ────────────────
        // Production orders not yet complete are scheduled receipts;
        // on-hand comes from the inventory ledger (real sums, not
        // bigint truncation).
        let mut records: Vec<MRPRecord> = Vec::new();
        let mut products: Vec<Uuid> = gross.keys().copied().collect();
        if demand_qty > rust_decimal::Decimal::ZERO && !products.contains(&product_id) {
            products.push(product_id);
        }
        // Item 34: the product UOMs feed the records (a plan in meters is
        // never displayed as an integer count).
        let uom_by_product: std::collections::HashMap<Uuid, String> = {
            let rows: Vec<(Uuid, String)> = sqlx::query_as(
                "SELECT id, unit_of_measure FROM products \
                 WHERE tenant_id = $1 AND id = ANY($2::uuid[])",
            )
            .bind(tenant_id)
            .bind(&products)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to load product UOMs: {e}")))?;
            rows.into_iter().collect()
        };
        // Item 18: every policy figure arrives as Decimal directly from the
        // NUMERIC column — no f64 conversion anywhere in the engine.
        for p in products {
            let scheduled: rust_decimal::Decimal = sqlx::query_scalar(
                "SELECT COALESCE(SUM(quantity_planned - quantity_produced), 0)::numeric \
                 FROM production_orders \
                 WHERE product_id = $1 AND tenant_id = $2 AND status NOT IN ('completed', 'cancelled')",
            )
            .bind(p)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to compute scheduled receipts: {e}")))?;

            let on_hand: rust_decimal::Decimal = sqlx::query_scalar(
                "SELECT COALESCE(SUM(quantity_on_hand), 0)::numeric \
                 FROM inventory_items \
                 WHERE product_id = $1 AND tenant_id = $2",
            )
            .bind(p)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to compute on-hand: {e}")))?;

            let (safety_stock, lot_size, lead_days): (
                rust_decimal::Decimal,
                rust_decimal::Decimal,
                i32,
            ) = sqlx::query_as(
                "SELECT COALESCE(safety_stock, 0)::numeric, \
                            COALESCE(lot_size, 0)::numeric, COALESCE(lead_time_days, 0) \
                     FROM products WHERE id = $1 AND tenant_id = $2",
            )
            .bind(p)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to load product policy: {e}")))?;

            let gross_qty = *gross.get(&p).unwrap_or(&rust_decimal::Decimal::ZERO);

            // ── 4. Net requirements (safety stock included) ────────────
            let projected = on_hand + scheduled - gross_qty;
            let net = (safety_stock - projected).max(rust_decimal::Decimal::ZERO);

            // ── 5. Lot sizing: lot-for-lot unless a lot size is set ────
            let planned_receipt =
                if lot_size > rust_decimal::Decimal::ZERO && net > rust_decimal::Decimal::ZERO {
                    (net / lot_size).ceil() * lot_size
                } else {
                    net
                };

            // ── 6. Time phasing (item 17): the receipt requirement date
            // is the demand's own date PROPAGATED BACKWARD through the BOM
            // (component_need during the explosion); the release is offset
            // further back by THIS product's lead time. A component can
            // never inherit an arbitrary now+30d default.
            let receipt_date = need_dates.get(&p).copied().unwrap_or(root_need);
            let release_date = receipt_date - chrono::Duration::days(lead_days as i64);

            records.push(MRPRecord {
                id: Uuid::new_v4(),
                tenant_id,
                product_id: p,
                // Item 34: EXACT Decimal quantities — the plan never
                // rounds fractional UOMs. Ceiling belongs to discrete
                // display only, and even then not in the planner.
                gross_requirement: gross_qty,
                scheduled_receipts: scheduled,
                projected_on_hand: projected,
                net_requirement: net,
                planned_order_release: planned_receipt,
                time_phase_start: release_date,
                time_phase_end: receipt_date,
                unit_of_measure: uom_by_product
                    .get(&p)
                    .cloned()
                    .unwrap_or_else(|| "pcs".to_string()),
            });
        }

        // Source identity for the reproducible snapshot (item 19): the
        // ACTUAL ids of every input the plan consumed.
        let sales_order_ids: Vec<String> = {
            let rows: Vec<(Uuid,)> = sqlx::query_as(
                "SELECT DISTINCT so.id FROM sales_orders so, jsonb_array_elements(so.line_items) AS li \
                 WHERE so.tenant_id = $1 AND (li->>'product_id')::uuid = $2 \
                   AND so.status NOT IN ('completed', 'cancelled', 'closed')",
            )
            .bind(tenant_id)
            .bind(product_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to snapshot sales orders: {e}")))?;
            rows.into_iter().map(|(u,)| u.to_string()).collect()
        };
        let work_order_ids: Vec<String> = {
            let rows: Vec<(Uuid,)> = sqlx::query_as(
                "SELECT id FROM work_orders \
                 WHERE product_id = $1 AND tenant_id = $2 AND status NOT IN ('completed', 'cancelled')",
            )
            .bind(product_id)
            .bind(tenant_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to snapshot work orders: {e}")))?;
            rows.into_iter().map(|(u,)| u.to_string()).collect()
        };
        let receipt_ids: Vec<String> = {
            let rows: Vec<(Uuid,)> = sqlx::query_as(
                "SELECT id FROM production_orders \
                 WHERE tenant_id = $1 AND status NOT IN ('completed', 'cancelled') \
                   AND product_id = ANY($2::uuid[])",
            )
            .bind(tenant_id)
            .bind(gross.keys().copied().collect::<Vec<Uuid>>())
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to snapshot receipts: {e}")))?;
            rows.into_iter().map(|(u,)| u.to_string()).collect()
        };
        let bom_rows_snapshot: Vec<serde_json::Value> = {
            let rows: Vec<(Uuid, Uuid, rust_decimal::Decimal, rust_decimal::Decimal)> =
                sqlx::query_as(
                    "SELECT parent_product_id, component_product_id, quantity, \
                            COALESCE(scrap_percent, 0) \
                     FROM bom_items WHERE tenant_id = $1 AND is_active = TRUE",
                )
                .bind(tenant_id)
                .fetch_all(&self.pool)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to snapshot BOM: {e}")))?;
            rows.into_iter()
                .map(|(p, c, q, s)| {
                    serde_json::json!({
                        "parent": p.to_string(),
                        "component": c.to_string(),
                        "quantity": q.to_string(),
                        "scrap_percent": s.to_string(),
                    })
                })
                .collect()
        };
        let on_hand_ledger_snapshot: Vec<serde_json::Value> = {
            let rows: Vec<(Uuid, String, rust_decimal::Decimal, chrono::DateTime<Utc>)> =
                sqlx::query_as(
                    "SELECT product_id, location, quantity_on_hand::numeric, updated_at \
                     FROM inventory_items WHERE tenant_id = $1",
                )
                .bind(tenant_id)
                .fetch_all(&self.pool)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to snapshot inventory: {e}")))?;
            rows.into_iter()
                .map(|(p, loc, q, t)| {
                    serde_json::json!({
                        "product_id": p.to_string(),
                        "location": loc,
                        "quantity_on_hand": q.to_string(),
                        "updated_at": t.to_rfc3339(),
                    })
                })
                .collect()
        };
        let (policy_safety_stock, policy_lot_size, policy_lead_days) = {
            let (safety, lot, lead): (rust_decimal::Decimal, rust_decimal::Decimal, i32) =
                sqlx::query_as(
                    "SELECT COALESCE(safety_stock, 0)::numeric, \
                            COALESCE(lot_size, 0)::numeric, COALESCE(lead_time_days, 0) \
                     FROM products WHERE id = $1 AND tenant_id = $2",
                )
                .bind(product_id)
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to snapshot policy: {e}")))?;
            (safety.to_string(), lot.to_string(), lead)
        };

        // ── 7. Immutable snapshot: historic runs never change ──────────
        // The input snapshot captures AUTHORITATIVE SOURCE IDENTITY — the
        // actual sales-order/work-order ids and revisions, the BOM rows,
        // the ledger, policy and calendar — so an old result can be
        // reconstructed even when today's stock moves (item 19).
        let snapshot = serde_json::json!({
            "product_id": product_id,
            "demand": demand_qty,
            "gross_by_product": gross,
            "need_dates": need_dates.iter().map(|(k, v)| (k.to_string(), v.to_rfc3339())).collect::<Vec<_>>(),
            "demand_sources": {
                "open_sales_order_ids": sales_order_ids,
                "open_work_order_ids": work_order_ids,
                "scheduled_receipt_ids": receipt_ids,
                "bom_rows": bom_rows_snapshot,
                "on_hand_ledger": on_hand_ledger_snapshot,
            },
            "policy": {
                "safety_stock": policy_safety_stock,
                "lot_size": policy_lot_size,
                "lead_time_days": policy_lead_days,
            },
            "calculated_at": now,
        });
        let result_json =
            serde_json::to_value(&records).unwrap_or(serde_json::Value::Array(vec![]));
        // Reproducibility is a product invariant: a successful plan without
        // its promised audit snapshot is a FAILURE, not a silent success.
        sqlx::query(
            "INSERT INTO mrp_runs (id, tenant_id, product_id, status, input_snapshot, result, created_at) \
             VALUES ($1, $2, $3, 'completed', $4, $5, $6)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(product_id)
        .bind(snapshot)
        .bind(result_json)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("Failed to persist MRP run snapshot: {e}"))
        })?;

        Ok(records)
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

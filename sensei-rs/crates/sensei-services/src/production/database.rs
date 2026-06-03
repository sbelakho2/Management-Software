//! PostgreSQL-backed production service using sqlx.
//!
//! Provides work order, production order, BOM, and MRP management
//! backed by PostgreSQL tables. Implements [`ProductionService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sqlx::PgPool;
use uuid::Uuid;

use super::{BOMItem, MRPRecord, ProductionOrder, ProductionService, WorkOrder, WorkOrderOperation};

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
pub struct DatabaseProductionService {
    pool: PgPool,
}

impl DatabaseProductionService {
    /// Create a new [`DatabaseProductionService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl ProductionService for DatabaseProductionService {
    // ── Work Orders ─────────────────────────────────────────────────────

    async fn create_work_order(
        &self,
        tenant_id: Uuid,
        mut wo: WorkOrder,
    ) -> Result<WorkOrder> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let wo_number = format!("WO-{}-{}", now.format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

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
                quantity, quantity_completed, status, work_center_id, priority,
                scheduled_start, scheduled_end, actual_start, actual_end,
                assigned_to, notes, created_at, updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
            RETURNING id, tenant_id, wo_number, product_id, product_name,
                      quantity, quantity_completed, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
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
        .bind(&wo.assigned_to)
        .bind(&wo.notes)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create work order: {e}")))?;

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
            total_pages: ((count as usize).max(1) + per_page - 1) / per_page,
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

    async fn report_production(
        &self,
        tenant_id: Uuid,
        work_order_id: Uuid,
        quantity_completed: i64,
        _quantity_scrapped: i64,
    ) -> Result<WorkOrder> {
        let now = Utc::now();

        let row = sqlx::query_as::<_, WorkOrderRow>(
            r#"
            UPDATE work_orders
            SET quantity_completed = quantity_completed + $1,
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
                      quantity, quantity_completed, status, work_center_id, priority,
                      scheduled_start, scheduled_end, actual_start, actual_end,
                      assigned_to, notes, created_at, updated_at
            "#,
        )
        .bind(quantity_completed)
        .bind(work_order_id)
        .bind(tenant_id)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to report production: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work order {work_order_id} not found")))?;

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
        let order_number = format!("PO-{}-{}", now.format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

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
            total_pages: ((count as usize).max(1) + per_page - 1) / per_page,
        })
    }

    async fn complete_production_order(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<ProductionOrder> {
        let now = Utc::now();

        let existing = sqlx::query_as::<_, ProductionOrderRow>(
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

        if existing.status == "completed" {
            return Err(SenseiError::Validation(
                "Production order is already completed".to_string(),
            ));
        }

        let row = sqlx::query_as::<_, ProductionOrderRow>(
            r#"
            UPDATE production_orders
            SET status = 'completed',
                actual_end = $1,
                quantity_produced = quantity_planned,
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
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to complete production order: {e}")))?;

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
        .map_err(|e| SenseiError::Database(format!("Failed to compute MRP gross requirement: {e}")))?;

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
        .map_err(|e| SenseiError::Database(format!("Failed to compute MRP scheduled receipts: {e}")))?;

        let projected_on_hand = 0_i64;
        let net_requirement = (gross_requirement - scheduled_receipts - projected_on_hand).max(0);
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
            return Err(SenseiError::NotFound(format!("Work order {work_order_id} not found")));
        }

        let rows = sqlx::query_as::<_, WorkOrderOperationRow>(
            r#"
            SELECT id, tenant_id, work_order_id, sequence, station_id, operation,
                   status, standard_time, actual_time, setup_time, actual_setup_time,
                   started_at, completed_at, operator_id, notes, created_at, updated_at
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

        Ok(rows.into_iter().map(|r| WorkOrderOperation {
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
        }).collect())
    }
}

/// Database row for work order operations.
#[derive(Debug, Clone, sqlx::FromRow)]
struct WorkOrderOperationRow {
    id: Uuid,
    tenant_id: Uuid,
    work_order_id: Uuid,
    sequence: i32,
    station_id: Uuid,
    operation: String,
    status: String,
    standard_time: f64,
    actual_time: Option<f64>,
    setup_time: f64,
    actual_setup_time: Option<f64>,
    started_at: Option<chrono::DateTime<Utc>>,
    completed_at: Option<chrono::DateTime<Utc>>,
    operator_id: Option<Uuid>,
    notes: Option<String>,
    created_at: chrono::DateTime<Utc>,
    updated_at: chrono::DateTime<Utc>,
}

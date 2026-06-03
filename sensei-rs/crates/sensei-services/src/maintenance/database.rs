//! PostgreSQL-backed maintenance service using sqlx.
//!
//! Provides work request, PM schedule, and equipment management
//! backed by PostgreSQL tables. Implements [`MaintenanceService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::TenantId;
use serde_json;
use sqlx::PgPool;
use uuid::Uuid;

use super::{EquipmentRecord, MaintenanceService, MaintenanceWorkRequest, PMSchedule};

/// PostgreSQL-backed implementation of [`MaintenanceService`].
pub struct DatabaseMaintenanceService {
    pool: PgPool,
}

impl DatabaseMaintenanceService {
    /// Create a new [`DatabaseMaintenanceService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

// ---------------------------------------------------------------------------
// Row structs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct WorkRequestRow {
    id: Uuid,
    tenant_id: Uuid,
    equipment_id: Uuid,
    title: String,
    description: String,
    priority: String,
    status: String,
    requested_by: Uuid,
    assigned_to: Option<Uuid>,
    created_at: chrono::DateTime<Utc>,
    completed_at: Option<chrono::DateTime<Utc>>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct PmScheduleRow {
    id: Uuid,
    tenant_id: Uuid,
    equipment_id: Uuid,
    task_name: String,
    frequency_days: i32,
    last_performed: Option<chrono::DateTime<Utc>>,
    next_due: chrono::DateTime<Utc>,
    assigned_to: serde_json::Value,
    is_active: bool,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct EquipmentRow {
    id: Uuid,
    tenant_id: Uuid,
    equipment_code: String,
    name: String,
    equipment_type: String,
    location: String,
    status: String,
    install_date: chrono::DateTime<Utc>,
    last_maintenance: Option<chrono::DateTime<Utc>>,
    oee_percentage: f64,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn wr_row_to_domain(r: WorkRequestRow) -> MaintenanceWorkRequest {
    MaintenanceWorkRequest {
        id: r.id, tenant_id: r.tenant_id, equipment_id: r.equipment_id,
        title: r.title, description: r.description, priority: r.priority,
        status: r.status, requested_by: r.requested_by, assigned_to: r.assigned_to,
        created_at: r.created_at, completed_at: r.completed_at,
    }
}

fn pm_row_to_domain(r: PmScheduleRow) -> PMSchedule {
    let assigned_to: Vec<Uuid> = serde_json::from_value(r.assigned_to).unwrap_or_default();
    PMSchedule {
        id: r.id, tenant_id: r.tenant_id, equipment_id: r.equipment_id,
        task_name: r.task_name, frequency_days: r.frequency_days,
        last_performed: r.last_performed, next_due: r.next_due,
        assigned_to, is_active: r.is_active,
    }
}

fn eq_row_to_domain(r: EquipmentRow) -> EquipmentRecord {
    EquipmentRecord {
        id: r.id, tenant_id: r.tenant_id, equipment_code: r.equipment_code,
        name: r.name, equipment_type: r.equipment_type, location: r.location,
        status: r.status, install_date: r.install_date, last_maintenance: r.last_maintenance,
        oee_percentage: r.oee_percentage,
    }
}

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items, total: count as usize, page, per_page,
        total_pages: ((count as usize).max(1) + per_page - 1) / per_page,
    }
}

#[async_trait]
impl MaintenanceService for DatabaseMaintenanceService {
    // ── Work Requests ───────────────────────────────────────────────────

    async fn create_work_request(&self, tenant_id: TenantId, request: MaintenanceWorkRequest) -> Result<MaintenanceWorkRequest> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let status = if request.status.is_empty() { "submitted" } else { &request.status };
        let priority = if request.priority.is_empty() { "medium" } else { &request.priority };

        let row = sqlx::query_as::<_, WorkRequestRow>(
            r#"INSERT INTO maintenance_work_requests (id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NULL)
               RETURNING id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at"#,
        )
        .bind(id).bind(tenant_id).bind(request.equipment_id).bind(&request.title)
        .bind(&request.description).bind(priority).bind(status)
        .bind(request.requested_by).bind(request.assigned_to).bind(now)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to create work request: {e}")))?;

        Ok(wr_row_to_domain(row))
    }

    async fn get_work_request(&self, tenant_id: TenantId, id: Uuid) -> Result<MaintenanceWorkRequest> {
        let row = sqlx::query_as::<_, WorkRequestRow>(
            "SELECT id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at FROM maintenance_work_requests WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get work request: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;

        Ok(wr_row_to_domain(row))
    }

    async fn list_work_requests(&self, tenant_id: TenantId, status: Option<&str>, priority: Option<&str>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<MaintenanceWorkRequest>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<WorkRequestRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at
               FROM maintenance_work_requests WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR priority=$3)
               ORDER BY created_at DESC LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(status).bind(priority).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list work requests: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM maintenance_work_requests WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR priority=$3)",
        )
        .bind(tenant_id).bind(status).bind(priority).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count work requests: {e}")))?;

        Ok(paginate(items.into_iter().map(wr_row_to_domain).collect(), count, page, per_page))
    }

    async fn update_work_request_status(&self, tenant_id: TenantId, id: Uuid, status: &str) -> Result<MaintenanceWorkRequest> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, WorkRequestRow>(
            r#"UPDATE maintenance_work_requests SET status=$1, completed_at=CASE WHEN $1='completed' THEN $3 ELSE completed_at END
               WHERE id=$2 AND tenant_id=$4
               RETURNING id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at"#,
        )
        .bind(status).bind(id).bind(now).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update work request status: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;

        Ok(wr_row_to_domain(row))
    }

    async fn assign_work_request(&self, tenant_id: TenantId, id: Uuid, assigned_to: Uuid) -> Result<MaintenanceWorkRequest> {
        let row = sqlx::query_as::<_, WorkRequestRow>(
            r#"UPDATE maintenance_work_requests SET assigned_to=$1, status=CASE WHEN status='submitted' THEN 'approved' ELSE status END
               WHERE id=$2 AND tenant_id=$3
               RETURNING id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at"#,
        )
        .bind(assigned_to).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to assign work request: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;

        Ok(wr_row_to_domain(row))
    }

    // ── PM Schedules ───────────────────────────────────────────────────

    async fn create_pm_schedule(&self, tenant_id: TenantId, schedule: PMSchedule) -> Result<PMSchedule> {
        let id = Uuid::new_v4();
        let assigned_to_json = serde_json::to_value(&schedule.assigned_to).unwrap_or(serde_json::Value::Array(vec![]));
        let base = schedule.last_performed.unwrap_or_else(Utc::now);
        let next_due = base + chrono::Duration::days(schedule.frequency_days as i64);

        let row = sqlx::query_as::<_, PmScheduleRow>(
            r#"INSERT INTO pm_schedules (id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,TRUE)
               RETURNING id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active"#,
        )
        .bind(id).bind(tenant_id).bind(schedule.equipment_id).bind(&schedule.task_name)
        .bind(schedule.frequency_days).bind(schedule.last_performed).bind(next_due).bind(&assigned_to_json)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to create PM schedule: {e}")))?;

        Ok(pm_row_to_domain(row))
    }

    async fn get_pm_schedule(&self, tenant_id: TenantId, id: Uuid) -> Result<PMSchedule> {
        let row = sqlx::query_as::<_, PmScheduleRow>(
            "SELECT id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active FROM pm_schedules WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get PM schedule: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {id} not found")))?;

        Ok(pm_row_to_domain(row))
    }

    async fn list_pm_schedules(&self, tenant_id: TenantId, equipment_id: Option<Uuid>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<PMSchedule>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<PmScheduleRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active
               FROM pm_schedules WHERE tenant_id=$1 AND ($2::uuid IS NULL OR equipment_id=$2)
               ORDER BY next_due ASC LIMIT $3 OFFSET $4"#,
        )
        .bind(tenant_id).bind(equipment_id).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list PM schedules: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM pm_schedules WHERE tenant_id=$1 AND ($2::uuid IS NULL OR equipment_id=$2)",
        )
        .bind(tenant_id).bind(equipment_id).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count PM schedules: {e}")))?;

        Ok(paginate(items.into_iter().map(pm_row_to_domain).collect(), count, page, per_page))
    }

    async fn complete_pm_task(&self, tenant_id: TenantId, schedule_id: Uuid) -> Result<PMSchedule> {
        let now = Utc::now();

        let existing = sqlx::query_as::<_, PmScheduleRow>(
            "SELECT id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active FROM pm_schedules WHERE id = $1 AND tenant_id = $2",
        )
        .bind(schedule_id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get PM schedule: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {schedule_id} not found")))?;

        let next_due = now + chrono::Duration::days(existing.frequency_days as i64);

        let row = sqlx::query_as::<_, PmScheduleRow>(
            r#"UPDATE pm_schedules SET last_performed=$1, next_due=$2 WHERE id=$3 AND tenant_id=$4
               RETURNING id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active"#,
        )
        .bind(now).bind(next_due).bind(schedule_id).bind(tenant_id)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to complete PM task: {e}")))?;

        Ok(pm_row_to_domain(row))
    }

    async fn get_overdue_pm_tasks(&self, tenant_id: TenantId) -> Result<Vec<PMSchedule>> {
        let rows = sqlx::query_as::<_, PmScheduleRow>(
            "SELECT id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active FROM pm_schedules WHERE tenant_id = $1 AND is_active = TRUE AND next_due < NOW()",
        )
        .bind(tenant_id).fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get overdue PM tasks: {e}")))?;

        Ok(rows.into_iter().map(pm_row_to_domain).collect())
    }

    // ── Equipment ──────────────────────────────────────────────────────

    async fn register_equipment(&self, tenant_id: TenantId, equipment: EquipmentRecord) -> Result<EquipmentRecord> {
        let id = Uuid::new_v4();
        let equipment_code = format!("EQ-{}-{}", Utc::now().format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

        let row = sqlx::query_as::<_, EquipmentRow>(
            r#"INSERT INTO equipment_records (id, tenant_id, equipment_code, name, equipment_type, location, status, install_date, last_maintenance, oee_percentage)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
               RETURNING id, tenant_id, equipment_code, name, equipment_type, location, status, install_date, last_maintenance, oee_percentage"#,
        )
        .bind(id).bind(tenant_id).bind(&equipment_code).bind(&equipment.name)
        .bind(&equipment.equipment_type).bind(&equipment.location).bind(&equipment.status)
        .bind(equipment.install_date).bind(equipment.last_maintenance).bind(equipment.oee_percentage)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to register equipment: {e}")))?;

        Ok(eq_row_to_domain(row))
    }

    async fn get_equipment(&self, tenant_id: TenantId, id: Uuid) -> Result<EquipmentRecord> {
        let row = sqlx::query_as::<_, EquipmentRow>(
            "SELECT id, tenant_id, equipment_code, name, equipment_type, location, status, install_date, last_maintenance, oee_percentage FROM equipment_records WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get equipment: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;

        Ok(eq_row_to_domain(row))
    }

    async fn list_equipment(&self, tenant_id: TenantId, equipment_type: Option<&str>, status: Option<&str>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<EquipmentRecord>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<EquipmentRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, equipment_code, name, equipment_type, location, status, install_date, last_maintenance, oee_percentage
               FROM equipment_records WHERE tenant_id=$1 AND ($2::text IS NULL OR equipment_type=$2) AND ($3::text IS NULL OR status=$3)
               ORDER BY name LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(equipment_type).bind(status).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list equipment: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM equipment_records WHERE tenant_id=$1 AND ($2::text IS NULL OR equipment_type=$2) AND ($3::text IS NULL OR status=$3)",
        )
        .bind(tenant_id).bind(equipment_type).bind(status).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count equipment: {e}")))?;

        Ok(paginate(items.into_iter().map(eq_row_to_domain).collect(), count, page, per_page))
    }

    async fn update_equipment_status(&self, tenant_id: TenantId, id: Uuid, status: &str) -> Result<EquipmentRecord> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, EquipmentRow>(
            r#"UPDATE equipment_records SET status=$1, last_maintenance=CASE WHEN $1='operational' THEN $3 ELSE last_maintenance END
               WHERE id=$2 AND tenant_id=$4
               RETURNING id, tenant_id, equipment_code, name, equipment_type, location, status, install_date, last_maintenance, oee_percentage"#,
        )
        .bind(status).bind(id).bind(now).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update equipment status: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;

        Ok(eq_row_to_domain(row))
    }

    async fn update_work_request(&self, tenant_id: TenantId, id: Uuid, request: MaintenanceWorkRequest) -> Result<MaintenanceWorkRequest> {
        let row = sqlx::query_as::<_, WorkRequestRow>(
            r#"UPDATE maintenance_work_requests SET title=$1, description=$2, priority=$3, equipment_id=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at"#,
        )
        .bind(&request.title).bind(&request.description).bind(&request.priority).bind(request.equipment_id)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update work request: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;

        Ok(wr_row_to_domain(row))
    }

    async fn delete_work_request(&self, tenant_id: TenantId, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM maintenance_work_requests WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete work request: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("Work request {id} not found"))); }
        Ok(())
    }

    async fn update_pm_schedule(&self, tenant_id: TenantId, id: Uuid, schedule: PMSchedule) -> Result<PMSchedule> {
        let assigned_to_json = serde_json::to_value(&schedule.assigned_to).unwrap_or(serde_json::Value::Array(vec![]));
        let row = sqlx::query_as::<_, PmScheduleRow>(
            r#"UPDATE pm_schedules SET task_name=$1, frequency_days=$2, assigned_to=$3, is_active=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, equipment_id, task_name, frequency_days, last_performed, next_due, assigned_to, is_active"#,
        )
        .bind(&schedule.task_name).bind(schedule.frequency_days).bind(&assigned_to_json).bind(schedule.is_active)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update PM schedule: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {id} not found")))?;

        Ok(pm_row_to_domain(row))
    }

    async fn delete_pm_schedule(&self, tenant_id: TenantId, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM pm_schedules WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete PM schedule: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("PM schedule {id} not found"))); }
        Ok(())
    }

    async fn update_equipment(&self, tenant_id: TenantId, id: Uuid, equipment: EquipmentRecord) -> Result<EquipmentRecord> {
        let row = sqlx::query_as::<_, EquipmentRow>(
            r#"UPDATE equipment_records SET name=$1, equipment_type=$2, location=$3, oee_percentage=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, equipment_code, name, equipment_type, location, status, install_date, last_maintenance, oee_percentage"#,
        )
        .bind(&equipment.name).bind(&equipment.equipment_type).bind(&equipment.location).bind(equipment.oee_percentage)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update equipment: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;

        Ok(eq_row_to_domain(row))
    }

    async fn delete_equipment(&self, tenant_id: TenantId, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM equipment_records WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete equipment: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("Equipment {id} not found"))); }
        Ok(())
    }
}

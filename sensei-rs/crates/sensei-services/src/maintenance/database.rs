//! PostgreSQL-backed maintenance service using sqlx.
//!
//! Provides work request, PM schedule, and equipment management
//! backed by PostgreSQL tables. Implements [`MaintenanceService`].
//!
//! Every tenant-table statement runs inside a [`TenantTx`] (thirtieth-audit
//! item 7): the maintenance tables carry the universal fail-closed FORCE
//! RLS policy (migration 175), so the SET LOCAL app.tenant_id context is a
//! construction-time property of the handle, not a per-statement
//! afterthought. State transitions are ATOMIC CAS (item 16): the expected
//! predecessor status is carried in the UPDATE predicate — there is no
//! read/check/write window, and a miss reports zero rows.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::db::TenantTx;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::TenantId;
use sqlx::PgPool;
use uuid::Uuid;

use super::{
    work_request_predecessor, EquipmentRecord, MaintenanceService, MaintenanceWorkRequest,
    PMSchedule, WORK_REQUEST_STATUSES,
};

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

const WR_COLUMNS: &str = "id, tenant_id, equipment_id, title, description, priority, status, \
     requested_by, assigned_to, created_at, completed_at";

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
    assigned_to: Option<Uuid>,
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
    maintenance_completed_at: Option<chrono::DateTime<Utc>>,
    oee_percentage: f64,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn wr_row_to_domain(r: WorkRequestRow) -> MaintenanceWorkRequest {
    MaintenanceWorkRequest {
        id: r.id,
        tenant_id: r.tenant_id,
        equipment_id: r.equipment_id,
        title: r.title,
        description: r.description,
        priority: r.priority,
        status: r.status,
        requested_by: r.requested_by,
        assigned_to: r.assigned_to,
        created_at: r.created_at,
        completed_at: r.completed_at,
    }
}

fn pm_row_to_domain(r: PmScheduleRow) -> PMSchedule {
    // The pm_schedules table stores a single assigned user; the domain model
    // exposes a list, so a NULL assignment maps to an empty list.
    let assigned_to: Vec<Uuid> = r.assigned_to.into_iter().collect();
    PMSchedule {
        id: r.id,
        tenant_id: r.tenant_id,
        equipment_id: r.equipment_id,
        task_name: r.task_name,
        frequency_days: r.frequency_days,
        last_performed: r.last_performed,
        next_due: r.next_due,
        assigned_to,
        is_active: r.is_active,
    }
}

fn eq_row_to_domain(r: EquipmentRow) -> EquipmentRecord {
    EquipmentRecord {
        id: r.id,
        tenant_id: r.tenant_id,
        equipment_code: r.equipment_code,
        name: r.name,
        equipment_type: r.equipment_type,
        location: r.location,
        status: r.status,
        install_date: r.install_date,
        last_maintenance: r.last_maintenance,
        maintenance_completed_at: r.maintenance_completed_at,
        oee_percentage: r.oee_percentage,
    }
}

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items,
        total: count as usize,
        page,
        per_page,
        total_pages: (count as usize).max(1).div_ceil(per_page),
    }
}

#[async_trait]
impl MaintenanceService for DatabaseMaintenanceService {
    // ── Work Requests ───────────────────────────────────────────────────

    async fn create_work_request(
        &self,
        tenant_id: TenantId,
        request: MaintenanceWorkRequest,
    ) -> Result<MaintenanceWorkRequest> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let status = if request.status.is_empty() {
            "submitted"
        } else {
            &request.status
        };
        let priority = if request.priority.is_empty() {
            "medium"
        } else {
            &request.priority
        };

        // INSERT + outbox row in ONE tenant-scoped transaction: a committed
        // work request can never lose its created event (the outbox relay
        // observes the row only after this commit).
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin create work request: {e}"))
        })?;
        let row = sqlx::query_as::<_, WorkRequestRow>(&format!(
            r#"INSERT INTO maintenance_work_requests (id, tenant_id, equipment_id, title, description, priority, status, requested_by, assigned_to, created_at, completed_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NULL)
               RETURNING {WR_COLUMNS}"#
        ))
        .bind(id).bind(tenant_id).bind(request.equipment_id).bind(&request.title)
        .bind(&request.description).bind(priority).bind(status)
        .bind(request.requested_by).bind(request.assigned_to).bind(now)
        .fetch_one(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to create work request: {e}")))?;

        sensei_db::outbox::enqueue_outbox(
            db.tx(),
            tenant_id,
            "maintenance_work_request",
            id,
            "sensei.maintenance.work-request.created",
            serde_json::json!({
                "equipment_id": request.equipment_id,
                "status": status,
                "priority": priority,
            }),
        )
        .await?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit work request: {e}")))?;

        Ok(wr_row_to_domain(row))
    }

    async fn get_work_request(
        &self,
        tenant_id: TenantId,
        id: Uuid,
    ) -> Result<MaintenanceWorkRequest> {
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin get work request: {e}")))?;
        let row = sqlx::query_as::<_, WorkRequestRow>(&format!(
            "SELECT {WR_COLUMNS} FROM maintenance_work_requests WHERE id = $1 AND tenant_id = $2"
        ))
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get work request: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit work request read: {e}"))
        })?;

        row.map(wr_row_to_domain)
            .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))
    }

    async fn list_work_requests(
        &self,
        tenant_id: TenantId,
        status: Option<&str>,
        priority: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MaintenanceWorkRequest>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        // Items + count in ONE tenant-scoped transaction: both statements
        // observe the same snapshot (fail-closed RLS context included).
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin list work requests: {e}"))
        })?;
        let items: Vec<WorkRequestRow> = sqlx::query_as(&format!(
            r#"SELECT {WR_COLUMNS}
               FROM maintenance_work_requests WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR priority=$3)
               ORDER BY created_at DESC LIMIT $4 OFFSET $5"#
        ))
        .bind(tenant_id).bind(status).bind(priority).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to list work requests: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM maintenance_work_requests WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR priority=$3)",
        )
        .bind(tenant_id).bind(status).bind(priority)
        .fetch_one(&mut **db.tx()).await
        .map_err(|e| SenseiError::Database(format!("Failed to count work requests: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit work request list: {e}"))
        })?;

        Ok(paginate(
            items.into_iter().map(wr_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn update_work_request_status(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        status: &str,
    ) -> Result<MaintenanceWorkRequest> {
        // Canonical lifecycle (item 16): submitted -> approved ->
        // in_progress -> completed; submitted/approved -> cancelled. The
        // requested target is translated to its required PREDECESSOR, and
        // that predecessor is carried in the UPDATE's WHERE — the state
        // check and the write are ONE statement, so two racing transitions
        // can never both observe the same predecessor.
        if !WORK_REQUEST_STATUSES.contains(&status) {
            return Err(SenseiError::Validation(format!(
                "Unknown work request status '{status}'"
            )));
        }
        // 'submitted' is the entry state, never a target: the machine moves
        // strictly forward (except cancellation, handled separately).
        let cancelling = status == "cancelled";
        if !cancelling && work_request_predecessor(status).is_none() {
            return Err(SenseiError::Conflict(format!(
                "Work request {id} cannot transition to status '{status}'"
            )));
        }

        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin update work request status: {e}"))
        })?;
        let row = if cancelling {
            sqlx::query_as::<_, WorkRequestRow>(&format!(
                r#"UPDATE maintenance_work_requests SET status='cancelled'
                   WHERE id=$1 AND tenant_id=$2 AND status IN ('submitted','approved')
                   RETURNING {WR_COLUMNS}"#
            ))
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(&mut **db.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to cancel work request: {e}")))?
        } else {
            // work_request_predecessor is Some here (validated above).
            let predecessor = work_request_predecessor(status).expect("validated target");
            sqlx::query_as::<_, WorkRequestRow>(&format!(
                r#"UPDATE maintenance_work_requests SET status=$1, completed_at=CASE WHEN $1='completed' THEN NOW() ELSE completed_at END
                   WHERE id=$2 AND tenant_id=$3 AND status=$4
                   RETURNING {WR_COLUMNS}"#
            ))
            .bind(status).bind(id).bind(tenant_id).bind(predecessor)
            .fetch_optional(&mut **db.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to update work request status: {e}")))?
        };
        let Some(row) = row else {
            // Zero rows: the row does not exist in the required predecessor
            // state (missing id and stale-state id are indistinguishable).
            let required = if cancelling {
                "an open state ('submitted' or 'approved')"
            } else {
                work_request_predecessor(status).expect("validated target")
            };
            return Err(SenseiError::NotFound(format!(
                "Work request {id} not found in {required}"
            )));
        };
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit status update: {e}")))?;

        Ok(wr_row_to_domain(row))
    }

    async fn assign_work_request(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        assigned_to: Uuid,
    ) -> Result<MaintenanceWorkRequest> {
        // Assignment is the submitted -> approved transition, and an open
        // request (submitted/approved/in_progress) may be (re)assigned with
        // its status preserved. The assignable-state guard rides in the
        // UPDATE's WHERE: no read-then-write window (item 16). Terminal
        // requests (completed/cancelled) are immutable history and are
        // rejected below.
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin assign work request: {e}"))
        })?;
        let row = sqlx::query_as::<_, WorkRequestRow>(&format!(
            r#"UPDATE maintenance_work_requests SET assigned_to=$1,
                 status=CASE WHEN status='submitted' THEN 'approved' ELSE status END
               WHERE id=$2 AND tenant_id=$3 AND status IN ('submitted','approved','in_progress')
               RETURNING {WR_COLUMNS}"#
        ))
        .bind(assigned_to)
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to assign work request: {e}")))?;

        let row = match row {
            Some(row) => row,
            None => {
                // Zero rows: distinguish a missing request (NotFound) from
                // an assignment attempt on a CLOSED request (Conflict) —
                // the diagnostic read happens only after the atomic UPDATE
                // missed, so there is no check/write race.
                let current: Option<String> = sqlx::query_scalar(
                    "SELECT status FROM maintenance_work_requests WHERE id = $1 AND tenant_id = $2",
                )
                .bind(id)
                .bind(tenant_id)
                .fetch_optional(&mut **db.tx())
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to read work request state: {e}"))
                })?;
                return match current {
                    None => Err(SenseiError::NotFound(format!(
                        "Work request {id} not found"
                    ))),
                    Some(state) => Err(SenseiError::Conflict(format!(
                        "Work request {id} is {state} and can no longer be assigned"
                    ))),
                };
            }
        };
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit work request assign: {e}"))
        })?;

        Ok(wr_row_to_domain(row))
    }

    // ── PM Schedules ───────────────────────────────────────────────────

    async fn create_pm_schedule(
        &self,
        tenant_id: TenantId,
        schedule: PMSchedule,
    ) -> Result<PMSchedule> {
        let id = Uuid::new_v4();
        let assigned_to = schedule.assigned_to.first().copied();
        let base = schedule.last_performed.unwrap_or_else(Utc::now);
        let next_due = base + chrono::Duration::days(schedule.frequency_days as i64);

        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin create PM schedule: {e}"))
        })?;
        let row = sqlx::query_as::<_, PmScheduleRow>(
            r#"INSERT INTO pm_schedules (id, tenant_id, equipment_id, schedule_number, title, description,
                                         frequency_type, frequency_value, frequency_unit,
                                         last_performed_at, next_due_at, assigned_to, is_active)
               VALUES ($1,$2,$3,$4,$5,'', 'calendar', $6, 'days', $7, $8, $9, TRUE)
               RETURNING id, tenant_id, equipment_id, title AS "task_name", frequency_value AS "frequency_days",
                         last_performed_at AS "last_performed", next_due_at AS "next_due", assigned_to, is_active"#,
        )
        .bind(id).bind(tenant_id).bind(schedule.equipment_id)
        .bind(format!("PM-{}-{}", Utc::now().format("%Y%m%d"), &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]))
        .bind(&schedule.task_name)
        .bind(schedule.frequency_days).bind(schedule.last_performed).bind(next_due).bind(assigned_to)
        .fetch_one(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to create PM schedule: {e}")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit PM schedule: {e}")))?;

        Ok(pm_row_to_domain(row))
    }

    async fn get_pm_schedule(&self, tenant_id: TenantId, id: Uuid) -> Result<PMSchedule> {
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin get PM schedule: {e}")))?;
        let row = sqlx::query_as::<_, PmScheduleRow>(
            "SELECT id, tenant_id, equipment_id, title AS \"task_name\", frequency_value AS \"frequency_days\", \
                    last_performed_at AS \"last_performed\", next_due_at AS \"next_due\", assigned_to, is_active \
             FROM pm_schedules WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to get PM schedule: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit PM schedule read: {e}"))
        })?;

        row.map(pm_row_to_domain)
            .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {id} not found")))
    }

    async fn list_pm_schedules(
        &self,
        tenant_id: TenantId,
        equipment_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PMSchedule>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin list PM schedules: {e}"))
        })?;
        let items: Vec<PmScheduleRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, equipment_id, title AS "task_name", frequency_value AS "frequency_days",
                      last_performed_at AS "last_performed", next_due_at AS "next_due", assigned_to, is_active
               FROM pm_schedules WHERE tenant_id=$1 AND ($2::uuid IS NULL OR equipment_id=$2)
               ORDER BY next_due_at ASC LIMIT $3 OFFSET $4"#,
        )
        .bind(tenant_id).bind(equipment_id).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to list PM schedules: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM pm_schedules WHERE tenant_id=$1 AND ($2::uuid IS NULL OR equipment_id=$2)",
        )
        .bind(tenant_id).bind(equipment_id).fetch_one(&mut **db.tx()).await
        .map_err(|e| SenseiError::Database(format!("Failed to count PM schedules: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit PM schedule list: {e}"))
        })?;

        Ok(paginate(
            items.into_iter().map(pm_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn complete_pm_task(&self, tenant_id: TenantId, schedule_id: Uuid) -> Result<PMSchedule> {
        let now = Utc::now();

        // Read + roll-forward + occurrence ledger in ONE tenant-scoped
        // transaction: the completion and its evidence are inseparable (a
        // PM completion that lost its maintenance_occurrences row would be
        // unverifiable work).
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin complete PM task: {e}")))?;
        let existing = sqlx::query_as::<_, PmScheduleRow>(
            "SELECT id, tenant_id, equipment_id, title AS \"task_name\", frequency_value AS \"frequency_days\", \
                    last_performed_at AS \"last_performed\", next_due_at AS \"next_due\", assigned_to, is_active \
             FROM pm_schedules WHERE id = $1 AND tenant_id = $2",
        )
        .bind(schedule_id).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to get PM schedule: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {schedule_id} not found")))?;

        let next_due = now + chrono::Duration::days(existing.frequency_days as i64);

        let row = sqlx::query_as::<_, PmScheduleRow>(
            r#"UPDATE pm_schedules SET last_performed_at=$1, next_due_at=$2 WHERE id=$3 AND tenant_id=$4
               RETURNING id, tenant_id, equipment_id, title AS "task_name", frequency_value AS "frequency_days",
                         last_performed_at AS "last_performed", next_due_at AS "next_due", assigned_to, is_active"#,
        )
        .bind(now).bind(next_due).bind(schedule_id).bind(tenant_id)
        .fetch_one(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to complete PM task: {e}")))?;

        // Maintenance evidence: every completion records an occurrence
        // (technician, actual time, findings placeholder) so Leader
        // Standard Work and the future TPM agent can verify work was done.
        sqlx::query(
            "INSERT INTO maintenance_occurrences \
                (id, tenant_id, schedule_id, equipment_id, occurrence_type, \
                 technician_id, actual_start_at, actual_end_at, findings, created_at) \
             VALUES ($1, $2, $3, $4, 'pm_completion', $5, $6, $6, '', NOW())",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(schedule_id)
        .bind(existing.equipment_id)
        .bind(existing.assigned_to)
        .bind(now)
        .execute(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to record PM occurrence: {e}")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit PM completion: {e}")))?;

        Ok(pm_row_to_domain(row))
    }

    async fn get_overdue_pm_tasks(&self, tenant_id: TenantId) -> Result<Vec<PMSchedule>> {
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin list overdue PM tasks: {e}"))
        })?;
        let rows = sqlx::query_as::<_, PmScheduleRow>(
            "SELECT id, tenant_id, equipment_id, title AS \"task_name\", frequency_value AS \"frequency_days\", \
                    last_performed_at AS \"last_performed\", next_due_at AS \"next_due\", assigned_to, is_active \
             FROM pm_schedules WHERE tenant_id = $1 AND is_active = TRUE AND next_due_at < NOW()",
        )
        .bind(tenant_id).fetch_all(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to get overdue PM tasks: {e}")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit overdue PM read: {e}")))?;

        Ok(rows.into_iter().map(pm_row_to_domain).collect())
    }

    // ── Equipment ──────────────────────────────────────────────────────

    async fn register_equipment(
        &self,
        tenant_id: TenantId,
        equipment: EquipmentRecord,
    ) -> Result<EquipmentRecord> {
        let id = Uuid::new_v4();
        let equipment_code = format!(
            "EQ-{}-{}",
            Utc::now().format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );

        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin register equipment: {e}"))
        })?;
        let row = sqlx::query_as::<_, EquipmentRow>(
            r#"INSERT INTO equipment (id, tenant_id, equipment_number, name, equipment_type, location, status,
                                      install_date, last_maintenance, maintenance_completed_at, oee_percentage)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
               RETURNING id, tenant_id, equipment_number AS "equipment_code", name, equipment_type, location, status,
                         install_date, last_maintenance, maintenance_completed_at, oee_percentage"#,
        )
        .bind(id).bind(tenant_id).bind(&equipment_code).bind(&equipment.name)
        .bind(&equipment.equipment_type).bind(&equipment.location).bind(&equipment.status)
        .bind(equipment.install_date).bind(equipment.last_maintenance).bind(equipment.maintenance_completed_at)
        .bind(equipment.oee_percentage)
        .fetch_one(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to register equipment: {e}")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit equipment: {e}")))?;

        Ok(eq_row_to_domain(row))
    }

    async fn get_equipment(&self, tenant_id: TenantId, id: Uuid) -> Result<EquipmentRecord> {
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin get equipment: {e}")))?;
        let row = sqlx::query_as::<_, EquipmentRow>(
            "SELECT id, tenant_id, equipment_number AS \"equipment_code\", name, equipment_type, location, status, \
                    install_date, last_maintenance, maintenance_completed_at, oee_percentage \
             FROM equipment WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to get equipment: {e}")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit equipment read: {e}")))?;

        row.map(eq_row_to_domain)
            .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))
    }

    async fn list_equipment(
        &self,
        tenant_id: TenantId,
        equipment_type: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EquipmentRecord>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin list equipment: {e}")))?;
        let items: Vec<EquipmentRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, equipment_number AS "equipment_code", name, equipment_type, location, status,
                      install_date, last_maintenance, maintenance_completed_at, oee_percentage
               FROM equipment WHERE tenant_id=$1 AND ($2::text IS NULL OR equipment_type=$2) AND ($3::text IS NULL OR status=$3)
               ORDER BY name LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(equipment_type).bind(status).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to list equipment: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM equipment WHERE tenant_id=$1 AND ($2::text IS NULL OR equipment_type=$2) AND ($3::text IS NULL OR status=$3)",
        )
        .bind(tenant_id).bind(equipment_type).bind(status)
        .fetch_one(&mut **db.tx()).await
        .map_err(|e| SenseiError::Database(format!("Failed to count equipment: {e}")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit equipment list: {e}")))?;

        Ok(paginate(
            items.into_iter().map(eq_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn update_equipment_status(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        status: &str,
    ) -> Result<EquipmentRecord> {
        let now = Utc::now();
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin update equipment status: {e}"))
        })?;
        let row = sqlx::query_as::<_, EquipmentRow>(
            r#"UPDATE equipment SET status=$1,
                  last_maintenance = CASE WHEN $1='under_maintenance' THEN $3 ELSE last_maintenance END,
                  maintenance_completed_at = CASE WHEN $1='operational' THEN $3 ELSE maintenance_completed_at END
               WHERE id=$2 AND tenant_id=$4
               RETURNING id, tenant_id, equipment_number AS "equipment_code", name, equipment_type, location, status,
                         install_date, last_maintenance, maintenance_completed_at, oee_percentage"#,
        )
        .bind(status).bind(id).bind(now).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to update equipment status: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit equipment status: {e}"))
        })?;

        Ok(eq_row_to_domain(row))
    }

    async fn update_work_request(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        request: MaintenanceWorkRequest,
    ) -> Result<MaintenanceWorkRequest> {
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin update work request: {e}"))
        })?;
        let row = sqlx::query_as::<_, WorkRequestRow>(&format!(
            r#"UPDATE maintenance_work_requests SET title=$1, description=$2, priority=$3, equipment_id=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING {WR_COLUMNS}"#
        ))
        .bind(&request.title).bind(&request.description).bind(&request.priority).bind(request.equipment_id)
        .bind(id).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to update work request: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit work request update: {e}"))
        })?;

        Ok(wr_row_to_domain(row))
    }

    async fn delete_work_request(&self, tenant_id: TenantId, id: Uuid) -> Result<()> {
        // Maintenance requests are business history: they are CANCELLED,
        // never physically erased (the audit: completed maintenance and
        // request history must remain auditable).
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin cancel work request: {e}"))
        })?;
        let result = sqlx::query(
            "UPDATE maintenance_work_requests SET status = 'cancelled' \
             WHERE id = $1 AND tenant_id = $2 AND status NOT IN ('completed', 'cancelled')",
        )
        .bind(id)
        .bind(tenant_id)
        .execute(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to cancel work request: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit work request cancel: {e}"))
        })?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::Validation(
                "Only open maintenance requests can be cancelled; completed history is retained"
                    .to_string(),
            ));
        }
        Ok(())
    }

    async fn update_pm_schedule(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        schedule: PMSchedule,
    ) -> Result<PMSchedule> {
        let assigned_to = schedule.assigned_to.first().copied();
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin update PM schedule: {e}"))
        })?;
        let row = sqlx::query_as::<_, PmScheduleRow>(
            r#"UPDATE pm_schedules SET title=$1, frequency_value=$2, assigned_to=$3, is_active=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, equipment_id, title AS "task_name", frequency_value AS "frequency_days",
                         last_performed_at AS "last_performed", next_due_at AS "next_due", assigned_to, is_active"#,
        )
        .bind(&schedule.task_name).bind(schedule.frequency_days).bind(assigned_to).bind(schedule.is_active)
        .bind(id).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to update PM schedule: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {id} not found")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit PM schedule update: {e}"))
        })?;

        Ok(pm_row_to_domain(row))
    }

    async fn delete_pm_schedule(&self, tenant_id: TenantId, id: Uuid) -> Result<()> {
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin delete PM schedule: {e}"))
        })?;
        let result = sqlx::query("DELETE FROM pm_schedules WHERE id = $1 AND tenant_id = $2")
            .bind(id)
            .bind(tenant_id)
            .execute(&mut **db.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete PM schedule: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit PM schedule delete: {e}"))
        })?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("PM schedule {id} not found")));
        }
        Ok(())
    }

    async fn update_equipment(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        equipment: EquipmentRecord,
    ) -> Result<EquipmentRecord> {
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin update equipment: {e}")))?;
        let row = sqlx::query_as::<_, EquipmentRow>(
            r#"UPDATE equipment SET name=$1, equipment_type=$2, location=$3, oee_percentage=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, equipment_number AS "equipment_code", name, equipment_type, location, status,
                         install_date, last_maintenance, maintenance_completed_at, oee_percentage"#,
        )
        .bind(&equipment.name).bind(&equipment.equipment_type).bind(&equipment.location).bind(equipment.oee_percentage)
        .bind(id).bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await.map_err(|e| SenseiError::Database(format!("Failed to update equipment: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit equipment update: {e}"))
        })?;

        Ok(eq_row_to_domain(row))
    }

    async fn delete_equipment(&self, tenant_id: TenantId, id: Uuid) -> Result<()> {
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin delete equipment: {e}")))?;
        let result = sqlx::query("DELETE FROM equipment WHERE id = $1 AND tenant_id = $2")
            .bind(id)
            .bind(tenant_id)
            .execute(&mut **db.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete equipment: {e}")))?;
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit equipment delete: {e}"))
        })?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Equipment {id} not found")));
        }
        Ok(())
    }
}

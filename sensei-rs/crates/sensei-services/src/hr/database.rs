//! PostgreSQL-backed HR service using sqlx.
//!
//! Provides employee, training, leave, performance review, and timecard
//! management backed by PostgreSQL tables. Implements [`HrService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sqlx::PgPool;
use uuid::Uuid;

use super::{Employee, HrService, LeaveRequest, PerformanceReview, Timecard, TrainingRecord};

/// PostgreSQL-backed implementation of [`HrService`].
pub struct DatabaseHrService {
    pool: PgPool,
}

impl DatabaseHrService {
    /// Create a new [`DatabaseHrService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

// ---------------------------------------------------------------------------
// Row structs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct EmployeeRow {
    id: Uuid,
    tenant_id: Uuid,
    employee_code: String,
    user_id: Uuid,
    full_name: String,
    email: String,
    department: String,
    job_title: String,
    employment_type: String,
    status: String,
    hire_date: chrono::DateTime<Utc>,
    termination_date: Option<chrono::DateTime<Utc>>,
    supervisor_id: Option<Uuid>,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct TrainingRecordRow {
    id: Uuid,
    tenant_id: Uuid,
    employee_id: Uuid,
    course_name: String,
    provider: String,
    credits: i32,
    completed_at: chrono::DateTime<Utc>,
    expires_at: Option<chrono::DateTime<Utc>>,
    certificate_url: Option<String>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct LeaveRequestRow {
    id: Uuid,
    tenant_id: Uuid,
    employee_id: Uuid,
    leave_type: String,
    start_date: chrono::DateTime<Utc>,
    end_date: chrono::DateTime<Utc>,
    total_days: i32,
    status: String,
    reason: String,
    approved_by: Option<Uuid>,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct PerformanceReviewRow {
    id: Uuid,
    tenant_id: Uuid,
    employee_id: Uuid,
    reviewer_id: Uuid,
    review_period: String,
    overall_rating: f64,
    strengths: String,
    areas_for_improvement: String,
    goals: String,
    status: String,
    created_at: chrono::DateTime<Utc>,
    completed_at: Option<chrono::DateTime<Utc>>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct TimecardRow {
    id: Uuid,
    tenant_id: Uuid,
    employee_id: Uuid,
    date: chrono::DateTime<Utc>,
    clock_in: Option<chrono::DateTime<Utc>>,
    clock_out: Option<chrono::DateTime<Utc>>,
    total_hours: f64,
    overtime_hours: f64,
    status: String,
    approved_by: Option<Uuid>,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn emp_row_to_domain(r: EmployeeRow) -> Employee {
    Employee {
        id: r.id, tenant_id: r.tenant_id, employee_code: r.employee_code,
        user_id: r.user_id, full_name: r.full_name, email: r.email,
        department: r.department, job_title: r.job_title, employment_type: r.employment_type,
        status: r.status, hire_date: r.hire_date, termination_date: r.termination_date,
        supervisor_id: r.supervisor_id, created_at: r.created_at,
    }
}

fn tr_row_to_domain(r: TrainingRecordRow) -> TrainingRecord {
    TrainingRecord {
        id: r.id, tenant_id: r.tenant_id, employee_id: r.employee_id,
        course_name: r.course_name, provider: r.provider, credits: r.credits,
        completed_at: r.completed_at, expires_at: r.expires_at, certificate_url: r.certificate_url,
    }
}

fn lr_row_to_domain(r: LeaveRequestRow) -> LeaveRequest {
    LeaveRequest {
        id: r.id, tenant_id: r.tenant_id, employee_id: r.employee_id,
        leave_type: r.leave_type, start_date: r.start_date, end_date: r.end_date,
        total_days: r.total_days, status: r.status, reason: r.reason,
        approved_by: r.approved_by, created_at: r.created_at,
    }
}

fn pr_row_to_domain(r: PerformanceReviewRow) -> PerformanceReview {
    PerformanceReview {
        id: r.id, tenant_id: r.tenant_id, employee_id: r.employee_id,
        reviewer_id: r.reviewer_id, review_period: r.review_period,
        overall_rating: r.overall_rating, strengths: r.strengths,
        areas_for_improvement: r.areas_for_improvement, goals: r.goals,
        status: r.status, created_at: r.created_at, completed_at: r.completed_at,
    }
}

fn tc_row_to_domain(r: TimecardRow) -> Timecard {
    Timecard {
        id: r.id, tenant_id: r.tenant_id, employee_id: r.employee_id,
        date: r.date, clock_in: r.clock_in, clock_out: r.clock_out,
        total_hours: r.total_hours, overtime_hours: r.overtime_hours,
        status: r.status, approved_by: r.approved_by,
    }
}

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items, total: count as usize, page, per_page,
        total_pages: ((count as usize).max(1) + per_page - 1) / per_page,
    }
}

#[async_trait]
impl HrService for DatabaseHrService {
    // ── Employees ───────────────────────────────────────────────────────

    async fn create_employee(&self, tenant_id: Uuid, employee: Employee) -> Result<Employee> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let employee_code = format!("EMP-{}-{}", now.format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

        let row = sqlx::query_as::<_, EmployeeRow>(
            r#"
            INSERT INTO employees (id, tenant_id, employee_code, user_id, full_name, email, department, job_title, employment_type, status, hire_date, termination_date, supervisor_id, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'active',$10,NULL,$11,$12)
            RETURNING id, tenant_id, employee_code, user_id, full_name, email, department, job_title, employment_type, status, hire_date, termination_date, supervisor_id, created_at
            "#,
        )
        .bind(id).bind(tenant_id).bind(&employee_code).bind(employee.user_id)
        .bind(&employee.full_name).bind(&employee.email).bind(&employee.department)
        .bind(&employee.job_title).bind(&employee.employment_type).bind(employee.hire_date)
        .bind(employee.supervisor_id).bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create employee: {e}")))?;

        Ok(emp_row_to_domain(row))
    }

    async fn get_employee(&self, tenant_id: Uuid, id: Uuid) -> Result<Employee> {
        let row = sqlx::query_as::<_, EmployeeRow>(
            "SELECT id, tenant_id, employee_code, user_id, full_name, email, department, job_title, employment_type, status, hire_date, termination_date, supervisor_id, created_at FROM employees WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get employee: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))?;

        Ok(emp_row_to_domain(row))
    }

    async fn list_employees(&self, tenant_id: Uuid, department: Option<&str>, status: Option<&str>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<Employee>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<EmployeeRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, employee_code, user_id, full_name, email, department, job_title, employment_type, status, hire_date, termination_date, supervisor_id, created_at
               FROM employees WHERE tenant_id = $1 AND ($2::text IS NULL OR department = $2) AND ($3::text IS NULL OR status = $3)
               ORDER BY created_at DESC LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(department).bind(status).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list employees: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM employees WHERE tenant_id = $1 AND ($2::text IS NULL OR department = $2) AND ($3::text IS NULL OR status = $3)",
        )
        .bind(tenant_id).bind(department).bind(status)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count employees: {e}")))?;

        Ok(paginate(items.into_iter().map(emp_row_to_domain).collect(), count, page, per_page))
    }

    async fn update_employee_status(&self, tenant_id: Uuid, id: Uuid, status: &str) -> Result<Employee> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, EmployeeRow>(
            r#"UPDATE employees SET status = $1, termination_date = CASE WHEN $1 = 'terminated' THEN $3 ELSE termination_date END
               WHERE id = $2 AND tenant_id = $4
               RETURNING id, tenant_id, employee_code, user_id, full_name, email, department, job_title, employment_type, status, hire_date, termination_date, supervisor_id, created_at"#,
        )
        .bind(status).bind(id).bind(now).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update employee status: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))?;

        Ok(emp_row_to_domain(row))
    }

    async fn update_employee(&self, tenant_id: Uuid, id: Uuid, employee: Employee) -> Result<Employee> {
        let row = sqlx::query_as::<_, EmployeeRow>(
            r#"UPDATE employees SET full_name=$1, email=$2, department=$3, job_title=$4, employment_type=$5, supervisor_id=$6
               WHERE id=$7 AND tenant_id=$8
               RETURNING id, tenant_id, employee_code, user_id, full_name, email, department, job_title, employment_type, status, hire_date, termination_date, supervisor_id, created_at"#,
        )
        .bind(&employee.full_name).bind(&employee.email).bind(&employee.department)
        .bind(&employee.job_title).bind(&employee.employment_type).bind(employee.supervisor_id)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update employee: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))?;

        Ok(emp_row_to_domain(row))
    }

    async fn delete_employee(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM employees WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete employee: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("Employee {id} not found"))); }
        Ok(())
    }

    // ── Training ────────────────────────────────────────────────────────

    async fn record_training(&self, tenant_id: Uuid, record: TrainingRecord) -> Result<TrainingRecord> {
        let id = Uuid::new_v4();
        let row = sqlx::query_as::<_, TrainingRecordRow>(
            r#"INSERT INTO training_records (id, tenant_id, employee_id, course_name, provider, credits, completed_at, expires_at, certificate_url)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
               RETURNING id, tenant_id, employee_id, course_name, provider, credits, completed_at, expires_at, certificate_url"#,
        )
        .bind(id).bind(tenant_id).bind(record.employee_id).bind(&record.course_name)
        .bind(&record.provider).bind(record.credits).bind(record.completed_at)
        .bind(record.expires_at).bind(&record.certificate_url)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to record training: {e}")))?;

        Ok(tr_row_to_domain(row))
    }

    async fn list_training_records(&self, tenant_id: Uuid, employee_id: Uuid, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<TrainingRecord>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<TrainingRecordRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, employee_id, course_name, provider, credits, completed_at, expires_at, certificate_url
               FROM training_records WHERE employee_id = $1 AND tenant_id = $2 ORDER BY completed_at DESC LIMIT $3 OFFSET $4"#,
        )
        .bind(employee_id).bind(tenant_id).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list training records: {e}")))?;

        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM training_records WHERE employee_id = $1 AND tenant_id = $2")
            .bind(employee_id).bind(tenant_id).fetch_one(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to count training records: {e}")))?;

        Ok(paginate(items.into_iter().map(tr_row_to_domain).collect(), count, page, per_page))
    }

    async fn get_expired_certifications(&self, tenant_id: Uuid) -> Result<Vec<TrainingRecord>> {
        let rows = sqlx::query_as::<_, TrainingRecordRow>(
            r#"SELECT id, tenant_id, employee_id, course_name, provider, credits, completed_at, expires_at, certificate_url
               FROM training_records WHERE tenant_id = $1 AND expires_at IS NOT NULL AND expires_at < NOW()"#,
        )
        .bind(tenant_id).fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get expired certifications: {e}")))?;

        Ok(rows.into_iter().map(tr_row_to_domain).collect())
    }

    async fn update_training(&self, tenant_id: Uuid, id: Uuid, record: TrainingRecord) -> Result<TrainingRecord> {
        let row = sqlx::query_as::<_, TrainingRecordRow>(
            r#"UPDATE training_records SET course_name=$1, provider=$2, credits=$3, expires_at=$4, certificate_url=$5
               WHERE id=$6 AND tenant_id=$7
               RETURNING id, tenant_id, employee_id, course_name, provider, credits, completed_at, expires_at, certificate_url"#,
        )
        .bind(&record.course_name).bind(&record.provider).bind(record.credits)
        .bind(record.expires_at).bind(&record.certificate_url).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update training: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Training record {id} not found")))?;

        Ok(tr_row_to_domain(row))
    }

    async fn delete_training(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM training_records WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete training: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("Training record {id} not found"))); }
        Ok(())
    }

    // ── Leave ───────────────────────────────────────────────────────────

    async fn submit_leave_request(&self, tenant_id: Uuid, leave: LeaveRequest) -> Result<LeaveRequest> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let duration = leave.end_date.signed_duration_since(leave.start_date);
        let total_days = duration.num_days().max(1) as i32;

        let row = sqlx::query_as::<_, LeaveRequestRow>(
            r#"INSERT INTO leave_requests (id, tenant_id, employee_id, leave_type, start_date, end_date, total_days, status, reason, approved_by, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,'pending',$8,NULL,$9)
               RETURNING id, tenant_id, employee_id, leave_type, start_date, end_date, total_days, status, reason, approved_by, created_at"#,
        )
        .bind(id).bind(tenant_id).bind(leave.employee_id).bind(&leave.leave_type)
        .bind(leave.start_date).bind(leave.end_date).bind(total_days).bind(&leave.reason).bind(now)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to submit leave request: {e}")))?;

        Ok(lr_row_to_domain(row))
    }

    async fn approve_leave(&self, tenant_id: Uuid, id: Uuid, approved_by: Uuid) -> Result<LeaveRequest> {
        // NotFound when the request is missing; Validation when it is not pending.
        let exists: bool = sqlx::query_scalar(
            "SELECT EXISTS(SELECT 1 FROM leave_requests WHERE id = $1 AND tenant_id = $2)",
        )
        .bind(id).bind(tenant_id)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to check leave request: {e}")))?;
        if !exists {
            return Err(SenseiError::NotFound(format!("Leave request {id} not found")));
        }

        let row = sqlx::query_as::<_, LeaveRequestRow>(
            r#"UPDATE leave_requests SET status='approved', approved_by=$1 WHERE id=$2 AND tenant_id=$3 AND status='pending'
               RETURNING id, tenant_id, employee_id, leave_type, start_date, end_date, total_days, status, reason, approved_by, created_at"#,
        )
        .bind(approved_by).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to approve leave: {e}")))?
        .ok_or_else(|| SenseiError::Validation(format!(
            "Cannot approve a leave request that is not pending"
        )))?;

        Ok(lr_row_to_domain(row))
    }

    async fn reject_leave(&self, tenant_id: Uuid, id: Uuid) -> Result<LeaveRequest> {
        // NotFound when the request is missing; Validation when it is not pending.
        let exists: bool = sqlx::query_scalar(
            "SELECT EXISTS(SELECT 1 FROM leave_requests WHERE id = $1 AND tenant_id = $2)",
        )
        .bind(id).bind(tenant_id)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to check leave request: {e}")))?;
        if !exists {
            return Err(SenseiError::NotFound(format!("Leave request {id} not found")));
        }

        let row = sqlx::query_as::<_, LeaveRequestRow>(
            r#"UPDATE leave_requests SET status='rejected' WHERE id=$1 AND tenant_id=$2 AND status='pending'
               RETURNING id, tenant_id, employee_id, leave_type, start_date, end_date, total_days, status, reason, approved_by, created_at"#,
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to reject leave: {e}")))?
        .ok_or_else(|| SenseiError::Validation(format!(
            "Cannot reject a leave request that is not pending"
        )))?;

        Ok(lr_row_to_domain(row))
    }

    async fn list_leave_requests(&self, tenant_id: Uuid, employee_id: Option<Uuid>, status: Option<&str>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<LeaveRequest>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<LeaveRequestRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, employee_id, leave_type, start_date, end_date, total_days, status, reason, approved_by, created_at
               FROM leave_requests WHERE tenant_id=$1 AND ($2::uuid IS NULL OR employee_id=$2) AND ($3::text IS NULL OR status=$3)
               ORDER BY created_at DESC LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(employee_id).bind(status).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list leave requests: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM leave_requests WHERE tenant_id=$1 AND ($2::uuid IS NULL OR employee_id=$2) AND ($3::text IS NULL OR status=$3)",
        )
        .bind(tenant_id).bind(employee_id).bind(status).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count leave requests: {e}")))?;

        Ok(paginate(items.into_iter().map(lr_row_to_domain).collect(), count, page, per_page))
    }

    async fn update_leave(&self, tenant_id: Uuid, id: Uuid, leave: LeaveRequest) -> Result<LeaveRequest> {
        let row = sqlx::query_as::<_, LeaveRequestRow>(
            r#"UPDATE leave_requests SET leave_type=$1, start_date=$2, end_date=$3, reason=$4
               WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, employee_id, leave_type, start_date, end_date, total_days, status, reason, approved_by, created_at"#,
        )
        .bind(&leave.leave_type).bind(leave.start_date).bind(leave.end_date).bind(&leave.reason)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update leave: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Leave request {id} not found")))?;

        Ok(lr_row_to_domain(row))
    }

    async fn delete_leave(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM leave_requests WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete leave: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("Leave request {id} not found"))); }
        Ok(())
    }

    // ── Performance Reviews ─────────────────────────────────────────────

    async fn create_review(&self, tenant_id: Uuid, review: PerformanceReview) -> Result<PerformanceReview> {
        let now = Utc::now();
        let id = Uuid::new_v4();

        let row = sqlx::query_as::<_, PerformanceReviewRow>(
            r#"INSERT INTO performance_reviews (id, tenant_id, employee_id, reviewer_id, review_period, overall_rating, strengths, areas_for_improvement, goals, status, created_at, completed_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'draft',$10,NULL)
               RETURNING id, tenant_id, employee_id, reviewer_id, review_period, overall_rating, strengths, areas_for_improvement, goals, status, created_at, completed_at"#,
        )
        .bind(id).bind(tenant_id).bind(review.employee_id).bind(review.reviewer_id)
        .bind(&review.review_period).bind(review.overall_rating).bind(&review.strengths)
        .bind(&review.areas_for_improvement).bind(&review.goals).bind(now)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to create review: {e}")))?;

        Ok(pr_row_to_domain(row))
    }

    async fn complete_review(&self, tenant_id: Uuid, id: Uuid) -> Result<PerformanceReview> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, PerformanceReviewRow>(
            r#"UPDATE performance_reviews SET status='completed', completed_at=$1 WHERE id=$2 AND tenant_id=$3
               RETURNING id, tenant_id, employee_id, reviewer_id, review_period, overall_rating, strengths, areas_for_improvement, goals, status, created_at, completed_at"#,
        )
        .bind(now).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to complete review: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Review {id} not found")))?;

        Ok(pr_row_to_domain(row))
    }

    async fn list_reviews(&self, tenant_id: Uuid, employee_id: Option<Uuid>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<PerformanceReview>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<PerformanceReviewRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, employee_id, reviewer_id, review_period, overall_rating, strengths, areas_for_improvement, goals, status, created_at, completed_at
               FROM performance_reviews WHERE tenant_id=$1 AND ($2::uuid IS NULL OR employee_id=$2)
               ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        )
        .bind(tenant_id).bind(employee_id).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list reviews: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM performance_reviews WHERE tenant_id=$1 AND ($2::uuid IS NULL OR employee_id=$2)",
        )
        .bind(tenant_id).bind(employee_id).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count reviews: {e}")))?;

        Ok(paginate(items.into_iter().map(pr_row_to_domain).collect(), count, page, per_page))
    }

    async fn update_review(&self, tenant_id: Uuid, id: Uuid, review: PerformanceReview) -> Result<PerformanceReview> {
        let row = sqlx::query_as::<_, PerformanceReviewRow>(
            r#"UPDATE performance_reviews SET overall_rating=$1, strengths=$2, areas_for_improvement=$3, goals=$4, review_period=$5
               WHERE id=$6 AND tenant_id=$7
               RETURNING id, tenant_id, employee_id, reviewer_id, review_period, overall_rating, strengths, areas_for_improvement, goals, status, created_at, completed_at"#,
        )
        .bind(review.overall_rating).bind(&review.strengths).bind(&review.areas_for_improvement)
        .bind(&review.goals).bind(&review.review_period).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update review: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Review {id} not found")))?;

        Ok(pr_row_to_domain(row))
    }

    async fn delete_review(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM performance_reviews WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id).execute(&self.pool)
            .await.map_err(|e| SenseiError::Database(format!("Failed to delete review: {e}")))?;
        if result.rows_affected() == 0 { return Err(SenseiError::NotFound(format!("Review {id} not found"))); }
        Ok(())
    }

    // ── Timecards ───────────────────────────────────────────────────────

    async fn clock_in(&self, tenant_id: Uuid, employee_id: Uuid) -> Result<Timecard> {
        let now = Utc::now();
        let id = Uuid::new_v4();

        let row = sqlx::query_as::<_, TimecardRow>(
            r#"INSERT INTO timecards (id, tenant_id, employee_id, date, clock_in, clock_out, total_hours, overtime_hours, status, approved_by)
               VALUES ($1,$2,$3,$4,$5,NULL,0,0,'pending',NULL)
               RETURNING id, tenant_id, employee_id, date, clock_in, clock_out, total_hours, overtime_hours, status, approved_by"#,
        )
        .bind(id).bind(tenant_id).bind(employee_id).bind(now).bind(now)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to clock in: {e}")))?;

        Ok(tc_row_to_domain(row))
    }

    async fn clock_out(&self, tenant_id: Uuid, _employee_id: Uuid, timecard_id: Uuid) -> Result<Timecard> {
        let now = Utc::now();

        let row = sqlx::query_as::<_, TimecardRow>(
            r#"UPDATE timecards SET clock_out=$1,
                total_hours = EXTRACT(EPOCH FROM ($1 - clock_in)) / 3600.0,
                overtime_hours = GREATEST(EXTRACT(EPOCH FROM ($1 - clock_in)) / 3600.0 - 8.0, 0)
               WHERE id=$2 AND tenant_id=$3 AND clock_out IS NULL
               RETURNING id, tenant_id, employee_id, date, clock_in, clock_out, total_hours, overtime_hours, status, approved_by"#,
        )
        .bind(now).bind(timecard_id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to clock out: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Timecard {timecard_id} not found or already clocked out")))?;

        Ok(tc_row_to_domain(row))
    }

    async fn list_timecards(&self, tenant_id: Uuid, employee_id: Uuid, date_from: Option<chrono::DateTime<Utc>>, date_to: Option<chrono::DateTime<Utc>>, page: Option<usize>, per_page: Option<usize>) -> Result<PaginatedResponse<Timecard>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<TimecardRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, employee_id, date, clock_in, clock_out, total_hours, overtime_hours, status, approved_by
               FROM timecards WHERE tenant_id=$1 AND employee_id=$2
                 AND ($3::timestamptz IS NULL OR date >= $3) AND ($4::timestamptz IS NULL OR date <= $4)
               ORDER BY date DESC LIMIT $5 OFFSET $6"#,
        )
        .bind(tenant_id).bind(employee_id).bind(date_from).bind(date_to)
        .bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list timecards: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM timecards WHERE tenant_id=$1 AND employee_id=$2 AND ($3::timestamptz IS NULL OR date >= $3) AND ($4::timestamptz IS NULL OR date <= $4)",
        )
        .bind(tenant_id).bind(employee_id).bind(date_from).bind(date_to)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count timecards: {e}")))?;

        Ok(paginate(items.into_iter().map(tc_row_to_domain).collect(), count, page, per_page))
    }

    async fn update_timecard(&self, tenant_id: Uuid, id: Uuid, timecard: Timecard) -> Result<Timecard> {
        let row = sqlx::query_as::<_, TimecardRow>(
            r#"UPDATE timecards SET clock_in=$1, clock_out=$2, total_hours=$3, overtime_hours=$4, status=$5, approved_by=$6
               WHERE id=$7 AND tenant_id=$8
               RETURNING id, tenant_id, employee_id, date, clock_in, clock_out, total_hours, overtime_hours, status, approved_by"#,
        )
        .bind(timecard.clock_in).bind(timecard.clock_out).bind(timecard.total_hours)
        .bind(timecard.overtime_hours).bind(&timecard.status).bind(timecard.approved_by)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update timecard: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Timecard {id} not found")))?;

        Ok(tc_row_to_domain(row))
    }
}

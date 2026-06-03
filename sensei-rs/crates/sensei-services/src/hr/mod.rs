//! Human Resources domain services.
//!
//! Provides employee management, training records, leave management,
//! performance reviews, and timecard management with in-memory storage
//! for development and testing.
//!
//! # Architecture
//!
//! The HR service layer abstracts human resource operations behind a trait,
//! enabling the system to swap in real database-backed implementations
//! while keeping the in-memory implementation for unit tests and demos.

mod database;
pub use database::DatabaseHrService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_core::domain::events::{
    DomainEvent, EmployeeOnboardedEvent, LeaveRequestApprovedEvent, LeaveRequestCreatedEvent,
    PerformanceReviewCompletedEvent, TimecardSubmittedEvent, TrainingCompletedEvent,
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

/// An employee record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Employee {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub employee_code: String,
    pub user_id: Uuid,
    pub full_name: String,
    pub email: String,
    pub department: String,
    pub job_title: String,
    pub employment_type: String, // full_time, part_time, contract, intern
    pub status: String,          // active, on_leave, terminated
    pub hire_date: DateTime<Utc>,
    pub termination_date: Option<DateTime<Utc>>,
    pub supervisor_id: Option<Uuid>,
    pub created_at: DateTime<Utc>,
}

/// A training record for an employee.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingRecord {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub employee_id: Uuid,
    pub course_name: String,
    pub provider: String,
    pub credits: i32,
    pub completed_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
    pub certificate_url: Option<String>,
}

/// A leave / absence request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeaveRequest {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub employee_id: Uuid,
    pub leave_type: String, // annual, sick, personal, maternity, paternity, unpaid
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
    pub total_days: i32,
    pub status: String,   // pending, approved, rejected, cancelled
    pub reason: String,
    pub approved_by: Option<Uuid>,
    pub created_at: DateTime<Utc>,
}

/// A performance review for an employee.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceReview {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub employee_id: Uuid,
    pub reviewer_id: Uuid,
    pub review_period: String, // Q1_2026, Q2_2026, annual_2026
    pub overall_rating: f64,   // 1.0-5.0
    pub strengths: String,
    pub areas_for_improvement: String,
    pub goals: String,
    pub status: String,        // draft, submitted, acknowledged, completed
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

/// A timecard recording clock-in/out events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Timecard {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub employee_id: Uuid,
    pub date: DateTime<Utc>,
    pub clock_in: Option<DateTime<Utc>>,
    pub clock_out: Option<DateTime<Utc>>,
    pub total_hours: f64,
    pub overtime_hours: f64,
    pub status: String, // pending, approved, rejected
    pub approved_by: Option<Uuid>,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// HR service trait covering employees, training, leave, performance
/// reviews, and timecards.
#[async_trait]
pub trait HrService: Send + Sync {
    // ── Employees ───────────────────────────────────────────────────────
    /// Create a new employee.
    async fn create_employee(&self, tenant_id: Uuid, employee: Employee) -> Result<Employee>;
    /// Get an employee by ID.
    async fn get_employee(&self, tenant_id: Uuid, id: Uuid) -> Result<Employee>;
    /// List employees with optional department, status filters, and pagination.
    async fn list_employees(
        &self,
        tenant_id: Uuid,
        department: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Employee>>;
    /// Update an employee's status.
    async fn update_employee_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<Employee>;
    /// Update an employee's details.
    async fn update_employee(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        employee: Employee,
    ) -> Result<Employee>;
    /// Delete an employee.
    async fn delete_employee(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Training ────────────────────────────────────────────────────────
    /// Record a completed training course.
    async fn record_training(
        &self,
        tenant_id: Uuid,
        record: TrainingRecord,
    ) -> Result<TrainingRecord>;
    /// List training records for an employee with pagination.
    async fn list_training_records(
        &self,
        tenant_id: Uuid,
        employee_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<TrainingRecord>>;
    /// Get all training records with expired certifications.
    async fn get_expired_certifications(
        &self,
        tenant_id: Uuid,
    ) -> Result<Vec<TrainingRecord>>;
    /// Update a training record.
    async fn update_training(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        record: TrainingRecord,
    ) -> Result<TrainingRecord>;
    /// Delete a training record.
    async fn delete_training(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Leave ───────────────────────────────────────────────────────────
    /// Submit a new leave request.
    async fn submit_leave_request(
        &self,
        tenant_id: Uuid,
        leave: LeaveRequest,
    ) -> Result<LeaveRequest>;
    /// Approve a leave request.
    async fn approve_leave(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        approved_by: Uuid,
    ) -> Result<LeaveRequest>;
    /// Reject a leave request.
    async fn reject_leave(&self, tenant_id: Uuid, id: Uuid) -> Result<LeaveRequest>;
    /// List leave requests with optional employee, status filters, and pagination.
    async fn list_leave_requests(
        &self,
        tenant_id: Uuid,
        employee_id: Option<Uuid>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<LeaveRequest>>;
    /// Update a leave request.
    async fn update_leave(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        leave: LeaveRequest,
    ) -> Result<LeaveRequest>;
    /// Delete a leave request.
    async fn delete_leave(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Performance Reviews ─────────────────────────────────────────────
    /// Create a new performance review.
    async fn create_review(
        &self,
        tenant_id: Uuid,
        review: PerformanceReview,
    ) -> Result<PerformanceReview>;
    /// Complete a performance review.
    async fn complete_review(&self, tenant_id: Uuid, id: Uuid) -> Result<PerformanceReview>;
    /// List performance reviews with optional employee filter and pagination.
    async fn list_reviews(
        &self,
        tenant_id: Uuid,
        employee_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PerformanceReview>>;
    /// Update a performance review.
    async fn update_review(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        review: PerformanceReview,
    ) -> Result<PerformanceReview>;
    /// Delete a performance review.
    async fn delete_review(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Timecards ───────────────────────────────────────────────────────
    /// Clock in for an employee, creating a new timecard.
    async fn clock_in(&self, tenant_id: Uuid, employee_id: Uuid) -> Result<Timecard>;
    /// Clock out for an employee on the given timecard.
    async fn clock_out(
        &self,
        tenant_id: Uuid,
        employee_id: Uuid,
        timecard_id: Uuid,
    ) -> Result<Timecard>;
    /// List timecards for an employee with optional date range and pagination.
    async fn list_timecards(
        &self,
        tenant_id: Uuid,
        employee_id: Uuid,
        date_from: Option<DateTime<Utc>>,
        date_to: Option<DateTime<Utc>>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Timecard>>;
    /// Update a timecard.
    async fn update_timecard(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        timecard: Timecard,
    ) -> Result<Timecard>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`HrService`] trait.
///
/// Stores employees, training records, leave requests, performance reviews,
/// and timecards in memory using `HashMap`s. Suitable for development,
/// testing, and demo environments.
pub struct InMemoryHrService {
    employees: RwLock<HashMap<Uuid, Employee>>,
    training_records: RwLock<HashMap<Uuid, TrainingRecord>>,
    leave_requests: RwLock<HashMap<Uuid, LeaveRequest>>,
    performance_reviews: RwLock<HashMap<Uuid, PerformanceReview>>,
    timecards: RwLock<HashMap<Uuid, Timecard>>,
    emp_counter: RwLock<u64>,
    tr_counter: RwLock<u64>,
    lr_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl InMemoryHrService {
    /// Create a new empty [`InMemoryHrService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            employees: RwLock::new(HashMap::new()),
            training_records: RwLock::new(HashMap::new()),
            leave_requests: RwLock::new(HashMap::new()),
            performance_reviews: RwLock::new(HashMap::new()),
            timecards: RwLock::new(HashMap::new()),
            emp_counter: RwLock::new(0),
            tr_counter: RwLock::new(0),
            lr_counter: RwLock::new(0),
            event_bus,
        }
    }

    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!("Failed to publish event {}: {}", event.event_type(), e);
            }
        }
    }

    fn generate_employee_code(counter: u64) -> String {
        format!("EMP-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }
}

impl Default for InMemoryHrService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl HrService for InMemoryHrService {
    // ── Employees ───────────────────────────────────────────────────────

    async fn create_employee(
        &self,
        tenant_id: Uuid,
        mut employee: Employee,
    ) -> Result<Employee> {
        let mut counter = self.emp_counter.write().await;
        *counter += 1;
        let emp_code = Self::generate_employee_code(*counter);
        drop(counter);

        employee.id = Uuid::new_v4();
        employee.tenant_id = tenant_id;
        employee.employee_code = emp_code;
        employee.status = "active".to_string();
        employee.created_at = Utc::now();

        let id = employee.id;
        let department = employee.department.clone();
        let position = employee.job_title.clone();
        self.employees.write().await.insert(id, employee.clone());
        self.publish_event(EmployeeOnboardedEvent::new(
            tenant_id,
            id,
            department,
            position,
        ))
        .await;
        Ok(employee)
    }

    async fn get_employee(&self, _tenant_id: Uuid, id: Uuid) -> Result<Employee> {
        let store = self.employees.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))
    }

    async fn list_employees(
        &self,
        tenant_id: Uuid,
        department: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Employee>> {
        let store = self.employees.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|e| {
                e.tenant_id == tenant_id
                    && department.is_none_or(|d| e.department == d)
                    && status.is_none_or(|s| e.status == s)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_employee_status(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        status: &str,
    ) -> Result<Employee> {
        let mut store = self.employees.write().await;
        let emp = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))?;

        let valid_statuses = ["active", "on_leave", "terminated"];
        if !valid_statuses.contains(&status) {
            return Err(SenseiError::Validation(format!(
                "Invalid employee status: {status}. Must be one of: active, on_leave, terminated"
            )));
        }

        // Record termination date when status changes to terminated
        if status == "terminated" {
            emp.termination_date = Some(Utc::now());
        }

        emp.status = status.to_string();
        Ok(emp.clone())
    }

    // ── Training ────────────────────────────────────────────────────────

    async fn record_training(
        &self,
        tenant_id: Uuid,
        mut record: TrainingRecord,
    ) -> Result<TrainingRecord> {
        let mut counter = self.tr_counter.write().await;
        *counter += 1;
        drop(counter);

        record.id = Uuid::new_v4();
        record.tenant_id = tenant_id;

        let id = record.id;
        self.training_records.write().await.insert(id, record.clone());
        self.publish_event(TrainingCompletedEvent::new(
            tenant_id,
            record.employee_id,
            id,
            record.course_name.clone(),
            None,
            true,
        ))
        .await;
        Ok(record)
    }

    async fn list_training_records(
        &self,
        _tenant_id: Uuid,
        employee_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<TrainingRecord>> {
        let store = self.training_records.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|tr| tr.employee_id == employee_id)
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn get_expired_certifications(
        &self,
        _tenant_id: Uuid,
    ) -> Result<Vec<TrainingRecord>> {
        let now = Utc::now();
        let store = self.training_records.read().await;
        Ok(store
            .values()
            .filter(|tr| {
                tr.expires_at.is_some_and(|exp| exp < now)
            })
            .cloned()
            .collect())
    }

    // ── Leave ───────────────────────────────────────────────────────────

    async fn submit_leave_request(
        &self,
        tenant_id: Uuid,
        mut leave: LeaveRequest,
    ) -> Result<LeaveRequest> {
        let mut counter = self.lr_counter.write().await;
        *counter += 1;
        drop(counter);

        // Compute total days from start/end
        let duration = leave.end_date.signed_duration_since(leave.start_date);
        let total_days = duration.num_days().max(1) as i32;

        leave.id = Uuid::new_v4();
        leave.tenant_id = tenant_id;
        leave.total_days = total_days;
        leave.status = "pending".to_string();
        leave.created_at = Utc::now();

        let id = leave.id;
        self.leave_requests.write().await.insert(id, leave.clone());
        self.publish_event(LeaveRequestCreatedEvent::new(
            tenant_id,
            id,
            leave.employee_id,
            leave.leave_type.clone(),
            leave.start_date.to_string(),
            leave.end_date.to_string(),
        ))
        .await;
        Ok(leave)
    }

    async fn approve_leave(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        approved_by: Uuid,
    ) -> Result<LeaveRequest> {
        let mut store = self.leave_requests.write().await;
        let leave = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Leave request {id} not found")))?;

        if leave.status != "pending" {
            return Err(SenseiError::Validation(format!(
                "Cannot approve a leave request with status: {}",
                leave.status
            )));
        }

        leave.status = "approved".to_string();
        leave.approved_by = Some(approved_by);
        let result = leave.clone();
        let employee_id = result.employee_id;
        drop(store);
        self.publish_event(LeaveRequestApprovedEvent::new(
            tenant_id,
            id,
            employee_id,
            approved_by,
        ))
        .await;
        Ok(result)
    }

    async fn reject_leave(&self, _tenant_id: Uuid, id: Uuid) -> Result<LeaveRequest> {
        let mut store = self.leave_requests.write().await;
        let leave = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Leave request {id} not found")))?;

        if leave.status != "pending" {
            return Err(SenseiError::Validation(format!(
                "Cannot reject a leave request with status: {}",
                leave.status
            )));
        }

        leave.status = "rejected".to_string();
        Ok(leave.clone())
    }

    async fn list_leave_requests(
        &self,
        tenant_id: Uuid,
        employee_id: Option<Uuid>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<LeaveRequest>> {
        let store = self.leave_requests.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|l| {
                l.tenant_id == tenant_id
                    && employee_id.is_none_or(|eid| l.employee_id == eid)
                    && status.is_none_or(|s| l.status == s)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Performance Reviews ─────────────────────────────────────────────

    async fn create_review(
        &self,
        tenant_id: Uuid,
        mut review: PerformanceReview,
    ) -> Result<PerformanceReview> {
        review.id = Uuid::new_v4();
        review.tenant_id = tenant_id;
        review.status = "draft".to_string();
        review.created_at = Utc::now();

        let id = review.id;
        self.performance_reviews
            .write()
            .await
            .insert(id, review.clone());
        Ok(review)
    }

    async fn complete_review(&self, tenant_id: Uuid, id: Uuid) -> Result<PerformanceReview> {
        let mut store = self.performance_reviews.write().await;
        let review = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Performance review {id} not found")))?;

        if review.status == "completed" {
            return Err(SenseiError::Validation(
                "Performance review is already completed".to_string(),
            ));
        }

        review.status = "completed".to_string();
        review.completed_at = Some(Utc::now());
        let result = review.clone();
        let employee_id = result.employee_id;
        let review_period = result.review_period.clone();
        let _overall_rating = result.overall_rating;
        drop(store);
        self.publish_event(PerformanceReviewCompletedEvent::new(
            tenant_id,
            id,
            employee_id,
            result.reviewer_id,
            review_period,
        ))
        .await;
        Ok(result)
    }

    async fn list_reviews(
        &self,
        tenant_id: Uuid,
        employee_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PerformanceReview>> {
        let store = self.performance_reviews.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|r| {
                r.tenant_id == tenant_id
                    && employee_id.is_none_or(|eid| r.employee_id == eid)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Timecards ───────────────────────────────────────────────────────

    async fn clock_in(&self, tenant_id: Uuid, employee_id: Uuid) -> Result<Timecard> {
        let now = Utc::now();

        // Check for existing open timecard (no clock_out)
        {
            let store = self.timecards.read().await;
            let has_open = store.values().any(|tc| {
                tc.tenant_id == tenant_id
                    && tc.employee_id == employee_id
                    && tc.clock_out.is_none()
            });
            if has_open {
                return Err(SenseiError::Validation(
                    "Employee already has an open timecard. Clock out first.".to_string(),
                ));
            }
        }

        let timecard = Timecard {
            id: Uuid::new_v4(),
            tenant_id,
            employee_id,
            date: now,
            clock_in: Some(now),
            clock_out: None,
            total_hours: 0.0,
            overtime_hours: 0.0,
            status: "pending".to_string(),
            approved_by: None,
        };

        let id = timecard.id;
        let date = timecard.date;
        self.timecards.write().await.insert(id, timecard.clone());
        self.publish_event(TimecardSubmittedEvent::new(
            tenant_id,
            id,
            employee_id,
            "clock_in".to_string(),
            date.to_string(),
        ))
        .await;
        Ok(timecard)
    }

    async fn clock_out(
        &self,
        tenant_id: Uuid,
        employee_id: Uuid,
        timecard_id: Uuid,
    ) -> Result<Timecard> {
        let mut store = self.timecards.write().await;
        let tc = store
            .get_mut(&timecard_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Timecard {timecard_id} not found")))?;

        if tc.employee_id != employee_id {
            return Err(SenseiError::Validation(
                "Timecard does not belong to this employee".to_string(),
            ));
        }

        if tc.clock_out.is_some() {
            return Err(SenseiError::Validation(
                "Timecard is already clocked out".to_string(),
            ));
        }

        let now = Utc::now();
        tc.clock_out = Some(now);

        // Compute total hours
        if let Some(clock_in) = tc.clock_in {
            let duration = now.signed_duration_since(clock_in);
            let hours = duration.num_minutes() as f64 / 60.0;
            tc.total_hours = (hours * 100.0).round() / 100.0; // round to 2 decimals

            // Overtime: hours beyond 8 per shift
            tc.overtime_hours = if tc.total_hours > 8.0 {
                ((tc.total_hours - 8.0) * 100.0).round() / 100.0
            } else {
                0.0
            };
        }

        let result = tc.clone();
        drop(store);
        self.publish_event(TimecardSubmittedEvent::new(
            tenant_id,
            result.id,
            employee_id,
            "clock_out".to_string(),
            result.clock_in.map(|dt| dt.to_string()).unwrap_or_default(),
        ))
        .await;
        Ok(result)
    }

    async fn list_timecards(
        &self,
        tenant_id: Uuid,
        employee_id: Uuid,
        date_from: Option<DateTime<Utc>>,
        date_to: Option<DateTime<Utc>>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Timecard>> {
        let store = self.timecards.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|tc| {
                tc.tenant_id == tenant_id
                    && tc.employee_id == employee_id
                    && date_from.is_none_or(|from| tc.date >= from)
                    && date_to.is_none_or(|to| tc.date <= to)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }
    // ── New: Update / Delete ─────────────────────────────────────────────

    async fn update_employee(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        employee: Employee,
    ) -> Result<Employee> {
        let mut store = self.employees.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))?;
        existing.full_name = employee.full_name;
        existing.email = employee.email;
        existing.department = employee.department;
        existing.job_title = employee.job_title;
        existing.employment_type = employee.employment_type;
        existing.status = employee.status;
        existing.supervisor_id = employee.supervisor_id;
        // Preserve: id, tenant_id, employee_code, hire_date, created_at, termination_date
        Ok(existing.clone())
    }

    async fn delete_employee(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.employees.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Employee {id} not found")))?;
        Ok(())
    }

    async fn update_training(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        record: TrainingRecord,
    ) -> Result<TrainingRecord> {
        let mut store = self.training_records.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("TrainingRecord {id} not found")))?;
        existing.course_name = record.course_name;
        existing.provider = record.provider;
        existing.credits = record.credits;
        existing.completed_at = record.completed_at;
        existing.expires_at = record.expires_at;
        existing.certificate_url = record.certificate_url;
        // Preserve: id, tenant_id, employee_id
        Ok(existing.clone())
    }

    async fn delete_training(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.training_records.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("TrainingRecord {id} not found")))?;
        Ok(())
    }

    async fn update_leave(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        leave: LeaveRequest,
    ) -> Result<LeaveRequest> {
        let mut store = self.leave_requests.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("LeaveRequest {id} not found")))?;
        existing.leave_type = leave.leave_type;
        existing.start_date = leave.start_date;
        existing.end_date = leave.end_date;
        existing.total_days = leave.total_days;
        existing.status = leave.status;
        existing.reason = leave.reason;
        existing.approved_by = leave.approved_by;
        // Preserve: id, tenant_id, employee_id, created_at
        Ok(existing.clone())
    }

    async fn delete_leave(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.leave_requests.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("LeaveRequest {id} not found")))?;
        Ok(())
    }

    async fn update_review(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        review: PerformanceReview,
    ) -> Result<PerformanceReview> {
        let mut store = self.performance_reviews.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PerformanceReview {id} not found")))?;
        existing.reviewer_id = review.reviewer_id;
        existing.review_period = review.review_period;
        existing.overall_rating = review.overall_rating;
        existing.strengths = review.strengths;
        existing.areas_for_improvement = review.areas_for_improvement;
        existing.goals = review.goals;
        existing.status = review.status;
        // Preserve: id, tenant_id, employee_id, created_at, completed_at
        Ok(existing.clone())
    }

    async fn delete_review(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.performance_reviews.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PerformanceReview {id} not found")))?;
        Ok(())
    }

    async fn update_timecard(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        timecard: Timecard,
    ) -> Result<Timecard> {
        let mut store = self.timecards.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Timecard {id} not found")))?;
        existing.clock_in = timecard.clock_in;
        existing.clock_out = timecard.clock_out;
        existing.total_hours = timecard.total_hours;
        existing.overtime_hours = timecard.overtime_hours;
        existing.status = timecard.status;
        existing.approved_by = timecard.approved_by;
        // Preserve: id, tenant_id, employee_id, date
        Ok(existing.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_and_get_employee() {
        let service = InMemoryHrService::default();
        let tenant_id = Uuid::new_v4();
        let user_id = Uuid::new_v4();

        let emp = Employee {
            id: Uuid::nil(),
            tenant_id,
            employee_code: String::new(),
            user_id,
            full_name: "Jane Doe".to_string(),
            email: "jane.doe@example.com".to_string(),
            department: "Engineering".to_string(),
            job_title: "Senior Engineer".to_string(),
            employment_type: "full_time".to_string(),
            status: String::new(),
            hire_date: Utc::now(),
            termination_date: None,
            supervisor_id: None,
            created_at: Utc::now(),
        };

        let created = service
            .create_employee(tenant_id, emp)
            .await
            .expect("should create employee");
        assert!(created.employee_code.starts_with("EMP-"));
        assert_eq!(created.status, "active");

        let fetched = service
            .get_employee(tenant_id, created.id)
            .await
            .expect("should fetch employee");
        assert_eq!(fetched.id, created.id);
        assert_eq!(fetched.full_name, "Jane Doe");
    }

    #[tokio::test]
    async fn test_update_employee_status() {
        let service = InMemoryHrService::default();
        let tenant_id = Uuid::new_v4();

        let emp = Employee {
            id: Uuid::nil(),
            tenant_id,
            employee_code: String::new(),
            user_id: Uuid::new_v4(),
            full_name: "Test".to_string(),
            email: "test@example.com".to_string(),
            department: "Sales".to_string(),
            job_title: "Sales Rep".to_string(),
            employment_type: "full_time".to_string(),
            status: String::new(),
            hire_date: Utc::now(),
            termination_date: None,
            supervisor_id: None,
            created_at: Utc::now(),
        };

        let created = service.create_employee(tenant_id, emp).await.unwrap();
        let updated = service
            .update_employee_status(tenant_id, created.id, "on_leave")
            .await
            .unwrap();
        assert_eq!(updated.status, "on_leave");
    }

    #[tokio::test]
    async fn test_leave_request_lifecycle() {
        let service = InMemoryHrService::default();
        let tenant_id = Uuid::new_v4();
        let employee_id = Uuid::new_v4();
        let approver_id = Uuid::new_v4();

        let leave = LeaveRequest {
            id: Uuid::nil(),
            tenant_id,
            employee_id,
            leave_type: "annual".to_string(),
            start_date: Utc::now(),
            end_date: Utc::now() + chrono::Duration::days(5),
            total_days: 0,
            status: String::new(),
            reason: "Vacation".to_string(),
            approved_by: None,
            created_at: Utc::now(),
        };

        let submitted = service
            .submit_leave_request(tenant_id, leave)
            .await
            .expect("should submit leave");
        assert_eq!(submitted.status, "pending");
        assert_eq!(submitted.total_days, 5);

        let approved = service
            .approve_leave(tenant_id, submitted.id, approver_id)
            .await
            .unwrap();
        assert_eq!(approved.status, "approved");
        assert_eq!(approved.approved_by, Some(approver_id));
    }

    #[tokio::test]
    async fn test_performance_review() {
        let service = InMemoryHrService::default();
        let tenant_id = Uuid::new_v4();
        let employee_id = Uuid::new_v4();
        let reviewer_id = Uuid::new_v4();

        let review = PerformanceReview {
            id: Uuid::nil(),
            tenant_id,
            employee_id,
            reviewer_id,
            review_period: "Q1_2026".to_string(),
            overall_rating: 0.0,
            strengths: "Strong technical skills".to_string(),
            areas_for_improvement: "Communication".to_string(),
            goals: "Lead a project".to_string(),
            status: String::new(),
            created_at: Utc::now(),
            completed_at: None,
        };

        let created = service
            .create_review(tenant_id, review)
            .await
            .expect("should create review");
        assert_eq!(created.status, "draft");

        let completed = service
            .complete_review(tenant_id, created.id)
            .await
            .unwrap();
        assert_eq!(completed.status, "completed");
        assert!(completed.completed_at.is_some());
    }

    #[tokio::test]
    async fn test_timecard_clock_in_out() {
        let service = InMemoryHrService::default();
        let tenant_id = Uuid::new_v4();
        let employee_id = Uuid::new_v4();

        let tc = service
            .clock_in(tenant_id, employee_id)
            .await
            .expect("should clock in");
        assert!(tc.clock_in.is_some());
        assert!(tc.clock_out.is_none());
        assert_eq!(tc.status, "pending");

        let clocked_out = service
            .clock_out(tenant_id, employee_id, tc.id)
            .await
            .expect("should clock out");
        assert!(clocked_out.clock_out.is_some());
        assert!(clocked_out.total_hours >= 0.0);
    }

    #[tokio::test]
    async fn test_training_records() {
        let service = InMemoryHrService::default();
        let tenant_id = Uuid::new_v4();
        let employee_id = Uuid::new_v4();

        let record = TrainingRecord {
            id: Uuid::nil(),
            tenant_id,
            employee_id,
            course_name: "Safety Training".to_string(),
            provider: "OSHA".to_string(),
            credits: 8,
            completed_at: Utc::now(),
            expires_at: Some(Utc::now() - chrono::Duration::days(1)), // expired
            certificate_url: Some("https://example.com/cert".to_string()),
        };

        let created = service
            .record_training(tenant_id, record)
            .await
            .expect("should record training");
        assert_eq!(created.course_name, "Safety Training");

        let records = service
            .list_training_records(tenant_id, employee_id, None, None)
            .await
            .unwrap();
        assert_eq!(records.data.len(), 1);

        let expired = service
            .get_expired_certifications(tenant_id)
            .await
            .unwrap();
        assert_eq!(expired.len(), 1);
    }
}

//! Human Resources route handlers.
//!
//! Provides endpoints for employee management, training records, leave
//! requests, performance reviews, and timecard tracking.
//!
//! # Self-service identity (thirtieth-first-audit item 6)
//!
//! Self-service endpoints (`hr:leave:self`, `hr:timecard:self`) derive the
//! caller's employee record server-side through
//! [`HrService::employee_id_for_user`] — request DTOs carry NO identity
//! fields (`employee_id`, `tenant_id`, `status`, ...), and a client-submitted
//! employee id is never trusted. Manager/HR read access to another
//! employee's records lives on separate endpoints under
//! `/api/v1/hr/employees/{employee_id}/...` guarded by manage/read
//! permissions (never `*:self`).

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::hr::{Employee, LeaveRequest, PerformanceReview, Timecard, TrainingRecord};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing employees.
#[derive(Debug, Deserialize)]
pub struct ListEmployeesParams {
    pub department: Option<String>,
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing training records.
#[derive(Debug, Deserialize)]
pub struct ListTrainingRecordsParams {
    pub employee_id: Uuid,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing the caller's OWN leave requests
/// (self-service). No employee id: the caller's employee record is derived
/// server-side from the authenticated user.
#[derive(Debug, Deserialize)]
pub struct ListLeaveRequestsParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing performance reviews.
#[derive(Debug, Deserialize)]
pub struct ListReviewsParams {
    pub employee_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing the caller's OWN timecards (self-service).
/// No employee id: the caller's employee record is derived server-side from
/// the authenticated user.
#[derive(Debug, Deserialize)]
pub struct ListTimecardsParams {
    pub date_from: Option<DateTime<Utc>>,
    pub date_to: Option<DateTime<Utc>>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating employee status.
#[derive(Debug, Deserialize)]
pub struct UpdateEmployeeStatusRequest {
    pub status: String,
}

/// Request body for submitting a leave request (self-service).
///
/// Narrow by design: no `employee_id`/`tenant_id`/`id`/`status`/
/// `approved_by`/`total_days`/timestamps — the employee is derived
/// server-side from the authenticated user.
#[derive(Debug, Deserialize)]
pub struct SubmitSelfLeaveRequest {
    pub leave_type: String,
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
    pub reason: String,
}

/// Request body for updating the caller's OWN pending leave request
/// (self-service). Same narrow shape as [`SubmitSelfLeaveRequest`]; only
/// the four editable fields are accepted.
#[derive(Debug, Deserialize)]
pub struct UpdateSelfLeaveRequest {
    pub leave_type: String,
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
    pub reason: String,
}

/// Request body for clocking in (self-service).
///
/// Empty: the employee is derived server-side from the authenticated user.
#[derive(Debug, Deserialize)]
pub struct ClockInRequest {}

/// Request body for clocking out (self-service).
///
/// No `employee_id`: the employee is derived server-side from the
/// authenticated user and enforced by the service.
#[derive(Debug, Deserialize)]
pub struct ClockOutRequest {
    pub timecard_id: Uuid,
}

/// Request body for approving leave.
#[derive(Debug, Deserialize)]
pub struct ApproveLeaveRequest {
    /// Ignored: the approver is always the authenticated user. Kept as
    /// `Option` so legacy clients sending it do not break.
    pub approved_by: Option<Uuid>,
}

// ── Employees ──────────────────────────────────────────────────────────────

/// List all employees with optional filters.
pub async fn list_employees(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListEmployeesParams>,
) -> Result<Json<PaginatedResponse<Employee>>> {
    user.require_permission("hr:employee:read")?;

    let tenant_id = user.tenant_id;
    let employees = state
        .hr_service
        .list_employees(
            tenant_id,
            params.department.as_deref(),
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(employees))
}

/// Create a new employee.
pub async fn create_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Employee>,
) -> Result<Json<Employee>> {
    user.require_permission("hr:employee:manage")?;

    let tenant_id = user.tenant_id;
    let employee = state.hr_service.create_employee(tenant_id, req).await?;
    Ok(Json(employee))
}

/// Get a specific employee by ID.
pub async fn get_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Employee>> {
    user.require_permission("hr:employee:read")?;

    let tenant_id = user.tenant_id;
    let employee = state.hr_service.get_employee(tenant_id, id).await?;
    Ok(Json(employee))
}

/// Update an employee's status.
pub async fn update_employee_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateEmployeeStatusRequest>,
) -> Result<Json<Employee>> {
    user.require_permission("hr:employee:manage")?;

    let tenant_id = user.tenant_id;
    let employee = state
        .hr_service
        .update_employee_status(tenant_id, id, &req.status)
        .await?;
    Ok(Json(employee))
}

// ── Training ───────────────────────────────────────────────────────────────

/// Record a training completion.
pub async fn record_training(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<TrainingRecord>,
) -> Result<Json<TrainingRecord>> {
    user.require_permission("hr:training:manage")?;

    let tenant_id = user.tenant_id;
    let training = state.hr_service.record_training(tenant_id, req).await?;
    Ok(Json(training))
}

/// List training records with optional filters.
pub async fn list_training_records(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTrainingRecordsParams>,
) -> Result<Json<PaginatedResponse<TrainingRecord>>> {
    user.require_permission("hr:training:manage")?;

    let tenant_id = user.tenant_id;
    let records = state
        .hr_service
        .list_training_records(tenant_id, params.employee_id, params.page, params.per_page)
        .await?;
    Ok(Json(records))
}

/// Get all expired certifications.
pub async fn get_expired_certifications(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<TrainingRecord>>> {
    user.require_permission("hr:training:manage")?;

    let tenant_id = user.tenant_id;
    let records = state
        .hr_service
        .get_expired_certifications(tenant_id)
        .await?;
    Ok(Json(records))
}

// ── Leave Requests ─────────────────────────────────────────────────────────

/// Submit a leave request for the authenticated user (self-service).
///
/// The employee identity is derived server-side from the authenticated
/// user; the body carries no identity fields.
pub async fn submit_leave_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<SubmitSelfLeaveRequest>,
) -> Result<Json<LeaveRequest>> {
    user.require_permission("hr:leave:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    let leave = LeaveRequest {
        id: Uuid::new_v4(),
        tenant_id,
        employee_id,
        leave_type: req.leave_type,
        start_date: req.start_date,
        end_date: req.end_date,
        total_days: 0,
        status: String::new(),
        reason: req.reason,
        approved_by: None,
        created_at: Utc::now(),
    };
    let leave = state
        .hr_service
        .submit_leave_request(tenant_id, leave)
        .await?;
    Ok(Json(leave))
}

/// Approve a leave request.
///
/// The approver is taken from the authenticated token; client-supplied
/// actor ids are never trusted.
pub async fn approve_leave(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    _req: Json<ApproveLeaveRequest>,
) -> Result<Json<LeaveRequest>> {
    user.require_permission("hr:leave:approve")?;

    let tenant_id = user.tenant_id;
    let leave = state
        .hr_service
        .approve_leave(tenant_id, id, user.user_id)
        .await?;
    Ok(Json(leave))
}

/// Reject a leave request.
pub async fn reject_leave(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<LeaveRequest>> {
    user.require_permission("hr:leave:approve")?;

    let tenant_id = user.tenant_id;
    let leave = state.hr_service.reject_leave(tenant_id, id).await?;
    Ok(Json(leave))
}

/// List the authenticated user's OWN leave requests ("my leave",
/// self-service).
///
/// The employee identity is derived server-side from the authenticated
/// user — there is no client-supplied employee filter.
pub async fn list_leave_requests(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListLeaveRequestsParams>,
) -> Result<Json<PaginatedResponse<LeaveRequest>>> {
    user.require_permission("hr:leave:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    let requests = state
        .hr_service
        .list_leave_requests(
            tenant_id,
            Some(employee_id),
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(requests))
}

/// List ONE employee's leave requests (manager/HR read access — not a
/// self-service route; the target employee is a path parameter and the
/// guard is a manage/read permission, never `hr:leave:self`).
pub async fn list_employee_leave_requests(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(employee_id): Path<Uuid>,
    Query(params): Query<ListLeaveRequestsParams>,
) -> Result<Json<PaginatedResponse<LeaveRequest>>> {
    user.require_permission("hr:employee:read")?;

    let tenant_id = user.tenant_id;
    let requests = state
        .hr_service
        .list_leave_requests(
            tenant_id,
            Some(employee_id),
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(requests))
}

/// Update the authenticated user's OWN pending leave request
/// (self-service).
///
/// The employee identity is derived server-side; the service enforces that
/// the row belongs to that employee and is still `pending` (NotFound
/// otherwise). The narrow body accepts only the four editable fields.
pub async fn update_leave(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateSelfLeaveRequest>,
) -> Result<Json<LeaveRequest>> {
    user.require_permission("hr:leave:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    let leave = LeaveRequest {
        id,
        tenant_id,
        employee_id,
        leave_type: req.leave_type,
        start_date: req.start_date,
        end_date: req.end_date,
        total_days: 0,
        status: String::new(),
        reason: req.reason,
        approved_by: None,
        created_at: Utc::now(),
    };
    let updated = state
        .hr_service
        .update_self_leave(tenant_id, employee_id, id, leave)
        .await?;
    Ok(Json(updated))
}

/// Delete the authenticated user's OWN pending leave request
/// (self-service).
///
/// The employee identity is derived server-side; the service enforces that
/// the row belongs to that employee and is still `pending` (NotFound
/// otherwise).
pub async fn delete_leave(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("hr:leave:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    state
        .hr_service
        .delete_self_leave(tenant_id, employee_id, id)
        .await?;
    Ok(Json(()))
}

// ── Performance Reviews ────────────────────────────────────────────────────

/// Create a performance review.
pub async fn create_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PerformanceReview>,
) -> Result<Json<PerformanceReview>> {
    user.require_permission("hr:review:manage")?;

    let tenant_id = user.tenant_id;
    let review = state.hr_service.create_review(tenant_id, req).await?;
    Ok(Json(review))
}

/// Complete a performance review.
pub async fn complete_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PerformanceReview>> {
    user.require_permission("hr:review:manage")?;

    let tenant_id = user.tenant_id;
    let review = state.hr_service.complete_review(tenant_id, id).await?;
    Ok(Json(review))
}

/// List performance reviews with optional filters.
pub async fn list_reviews(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListReviewsParams>,
) -> Result<Json<PaginatedResponse<PerformanceReview>>> {
    user.require_permission("hr:review:manage")?;

    let tenant_id = user.tenant_id;
    let reviews = state
        .hr_service
        .list_reviews(tenant_id, params.employee_id, params.page, params.per_page)
        .await?;
    Ok(Json(reviews))
}

// ── Timecards ──────────────────────────────────────────────────────────────

/// Clock in the authenticated user (self-service).
///
/// The employee identity is derived server-side from the authenticated
/// user; the empty body carries no identity fields.
pub async fn clock_in(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    _req: Json<ClockInRequest>,
) -> Result<Json<Timecard>> {
    user.require_permission("hr:timecard:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    let timecard = state.hr_service.clock_in(tenant_id, employee_id).await?;
    Ok(Json(timecard))
}

/// Clock out the authenticated user on the given timecard (self-service).
///
/// The employee identity is derived server-side and enforced by the
/// service (the timecard must belong to that employee and still be open).
pub async fn clock_out(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ClockOutRequest>,
) -> Result<Json<Timecard>> {
    user.require_permission("hr:timecard:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    let timecard = state
        .hr_service
        .clock_out(tenant_id, employee_id, req.timecard_id)
        .await?;
    Ok(Json(timecard))
}

/// List the authenticated user's OWN timecards ("my timecards",
/// self-service).
///
/// The employee identity is derived server-side from the authenticated
/// user — there is no client-supplied employee filter.
pub async fn list_timecards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTimecardsParams>,
) -> Result<Json<PaginatedResponse<Timecard>>> {
    user.require_permission("hr:timecard:self")?;

    let tenant_id = user.tenant_id;
    let employee_id = state
        .hr_service
        .employee_id_for_user(tenant_id, user.user_id)
        .await?;
    let timecards = state
        .hr_service
        .list_timecards(
            tenant_id,
            employee_id,
            params.date_from,
            params.date_to,
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(timecards))
}

/// List ONE employee's timecards (manager/HR read access — not a
/// self-service route; the target employee is a path parameter and the
/// guard is a manage permission, never `hr:timecard:self`).
pub async fn list_employee_timecards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(employee_id): Path<Uuid>,
    Query(params): Query<ListTimecardsParams>,
) -> Result<Json<PaginatedResponse<Timecard>>> {
    user.require_permission("hr:timecard:manage")?;

    let tenant_id = user.tenant_id;
    let timecards = state
        .hr_service
        .list_timecards(
            tenant_id,
            employee_id,
            params.date_from,
            params.date_to,
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(timecards))
}

// ── New: Update / Delete Handlers ──────────────────────────────────────────

/// Update an employee's details.
pub async fn update_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Employee>,
) -> Result<Json<Employee>> {
    user.require_permission("hr:employee:manage")?;

    let tenant_id = user.tenant_id;
    let employee = state.hr_service.update_employee(tenant_id, id, req).await?;
    Ok(Json(employee))
}

/// Delete an employee.
pub async fn delete_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("hr:employee:manage")?;

    let tenant_id = user.tenant_id;
    state.hr_service.delete_employee(tenant_id, id).await?;
    Ok(Json(()))
}

/// Update a training record.
pub async fn update_training(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<TrainingRecord>,
) -> Result<Json<TrainingRecord>> {
    user.require_permission("hr:training:manage")?;

    let tenant_id = user.tenant_id;
    let record = state.hr_service.update_training(tenant_id, id, req).await?;
    Ok(Json(record))
}

/// Delete a training record.
pub async fn delete_training(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("hr:training:manage")?;

    let tenant_id = user.tenant_id;
    state.hr_service.delete_training(tenant_id, id).await?;
    Ok(Json(()))
}

/// Update a performance review.
pub async fn update_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PerformanceReview>,
) -> Result<Json<PerformanceReview>> {
    user.require_permission("hr:review:manage")?;

    let tenant_id = user.tenant_id;
    let review = state.hr_service.update_review(tenant_id, id, req).await?;
    Ok(Json(review))
}

/// Delete a performance review.
pub async fn delete_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("hr:review:manage")?;

    let tenant_id = user.tenant_id;
    state.hr_service.delete_review(tenant_id, id).await?;
    Ok(Json(()))
}

/// Update a timecard.
pub async fn update_timecard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Timecard>,
) -> Result<Json<Timecard>> {
    user.require_permission("hr:timecard:manage")?;

    let tenant_id = user.tenant_id;
    let timecard = state.hr_service.update_timecard(tenant_id, id, req).await?;
    Ok(Json(timecard))
}

//! Human Resources route handlers.
//!
//! Provides endpoints for employee management, training records, leave
//! requests, performance reviews, and timecard tracking.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::hr::{Employee, LeaveRequest, PerformanceReview, Timecard, TrainingRecord};
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

/// Query parameters for listing leave requests.
#[derive(Debug, Deserialize)]
pub struct ListLeaveRequestsParams {
    pub employee_id: Option<Uuid>,
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

/// Query parameters for listing timecards.
#[derive(Debug, Deserialize)]
pub struct ListTimecardsParams {
    pub employee_id: Uuid,
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

/// Request body for clocking in.
#[derive(Debug, Deserialize)]
pub struct ClockInRequest {
    pub employee_id: Uuid,
}

/// Request body for clocking out.
#[derive(Debug, Deserialize)]
pub struct ClockOutRequest {
    pub employee_id: Uuid,
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
    let tenant_id = user.tenant_id;
    let employees = state
        .hr_service
        .list_employees(tenant_id, params.department.as_deref(), params.status.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(employees))
}

/// Create a new employee.
pub async fn create_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<Employee>,
) -> Result<Json<Employee>> {
    let tenant_id = user.tenant_id;
    let employee = state
        .hr_service
        .create_employee(tenant_id, req)
        .await?;
    Ok(Json(employee))
}

/// Get a specific employee by ID.
pub async fn get_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Employee>> {
    let tenant_id = user.tenant_id;
    let employee = state
        .hr_service
        .get_employee(tenant_id, id)
        .await?;
    Ok(Json(employee))
}

/// Update an employee's status.
pub async fn update_employee_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateEmployeeStatusRequest>,
) -> Result<Json<Employee>> {
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
    let tenant_id = user.tenant_id;
    let training = state
        .hr_service
        .record_training(tenant_id, req)
        .await?;
    Ok(Json(training))
}

/// List training records with optional filters.
pub async fn list_training_records(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTrainingRecordsParams>,
) -> Result<Json<PaginatedResponse<TrainingRecord>>> {
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
    let tenant_id = user.tenant_id;
    let records = state
        .hr_service
        .get_expired_certifications(tenant_id)
        .await?;
    Ok(Json(records))
}

// ── Leave Requests ─────────────────────────────────────────────────────────

/// Submit a leave request.
pub async fn submit_leave_request(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<LeaveRequest>,
) -> Result<Json<LeaveRequest>> {
    let tenant_id = user.tenant_id;
    let leave = state
        .hr_service
        .submit_leave_request(tenant_id, req)
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
    let tenant_id = user.tenant_id;
    let leave = state
        .hr_service
        .reject_leave(tenant_id, id)
        .await?;
    Ok(Json(leave))
}

/// List leave requests with optional filters.
pub async fn list_leave_requests(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListLeaveRequestsParams>,
) -> Result<Json<PaginatedResponse<LeaveRequest>>> {
    let tenant_id = user.tenant_id;
    let requests = state
        .hr_service
        .list_leave_requests(tenant_id, params.employee_id, params.status.as_deref(), params.page, params.per_page)
        .await?;
    Ok(Json(requests))
}

// ── Performance Reviews ────────────────────────────────────────────────────

/// Create a performance review.
pub async fn create_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PerformanceReview>,
) -> Result<Json<PerformanceReview>> {
    let tenant_id = user.tenant_id;
    let review = state
        .hr_service
        .create_review(tenant_id, req)
        .await?;
    Ok(Json(review))
}

/// Complete a performance review.
pub async fn complete_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PerformanceReview>> {
    let tenant_id = user.tenant_id;
    let review = state
        .hr_service
        .complete_review(tenant_id, id)
        .await?;
    Ok(Json(review))
}

/// List performance reviews with optional filters.
pub async fn list_reviews(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListReviewsParams>,
) -> Result<Json<PaginatedResponse<PerformanceReview>>> {
    let tenant_id = user.tenant_id;
    let reviews = state
        .hr_service
        .list_reviews(tenant_id, params.employee_id, params.page, params.per_page)
        .await?;
    Ok(Json(reviews))
}

// ── Timecards ──────────────────────────────────────────────────────────────

/// Clock in an employee.
pub async fn clock_in(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ClockInRequest>,
) -> Result<Json<Timecard>> {
    let tenant_id = user.tenant_id;
    let timecard = state
        .hr_service
        .clock_in(tenant_id, req.employee_id)
        .await?;
    Ok(Json(timecard))
}

/// Clock out an employee.
pub async fn clock_out(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ClockOutRequest>,
) -> Result<Json<Timecard>> {
    let tenant_id = user.tenant_id;
    let timecard = state
        .hr_service
        .clock_out(tenant_id, req.employee_id, req.timecard_id)
        .await?;
    Ok(Json(timecard))
}

// ── New: Update / Delete Handlers ──────────────────────────────────────────

/// Update an employee's details.
pub async fn update_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Employee>,
) -> Result<Json<Employee>> {
    let tenant_id = user.tenant_id;
    let employee = state
        .hr_service
        .update_employee(tenant_id, id, req)
        .await?;
    Ok(Json(employee))
}

/// Delete an employee.
pub async fn delete_employee(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .hr_service
        .delete_employee(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a training record.
pub async fn update_training(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<TrainingRecord>,
) -> Result<Json<TrainingRecord>> {
    let tenant_id = user.tenant_id;
    let record = state
        .hr_service
        .update_training(tenant_id, id, req)
        .await?;
    Ok(Json(record))
}

/// Delete a training record.
pub async fn delete_training(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .hr_service
        .delete_training(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a leave request.
pub async fn update_leave(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<LeaveRequest>,
) -> Result<Json<LeaveRequest>> {
    let tenant_id = user.tenant_id;
    let leave = state
        .hr_service
        .update_leave(tenant_id, id, req)
        .await?;
    Ok(Json(leave))
}

/// Delete a leave request.
pub async fn delete_leave(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .hr_service
        .delete_leave(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a performance review.
pub async fn update_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PerformanceReview>,
) -> Result<Json<PerformanceReview>> {
    let tenant_id = user.tenant_id;
    let review = state
        .hr_service
        .update_review(tenant_id, id, req)
        .await?;
    Ok(Json(review))
}

/// Delete a performance review.
pub async fn delete_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .hr_service
        .delete_review(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Update a timecard.
pub async fn update_timecard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Timecard>,
) -> Result<Json<Timecard>> {
    let tenant_id = user.tenant_id;
    let timecard = state
        .hr_service
        .update_timecard(tenant_id, id, req)
        .await?;
    Ok(Json(timecard))
}

/// List timecards with optional filters.
pub async fn list_timecards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTimecardsParams>,
) -> Result<Json<PaginatedResponse<Timecard>>> {
    let tenant_id = user.tenant_id;
    let timecards = state
        .hr_service
        .list_timecards(tenant_id, params.employee_id, params.date_from, params.date_to, params.page, params.per_page)
        .await?;
    Ok(Json(timecards))
}

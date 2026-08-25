//! Human Resources API endpoints.
//!
//! Employees, Training Records, Leave Requests, Performance Reviews, Timecards.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmployeeDto {
    pub id: String,
    pub tenant_id: String,
    pub employee_code: String,
    pub name: String,
    pub email: String,
    pub department: String,
    pub position: String,
    pub status: String,
    pub hire_date: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateEmployeeRequest {
    pub name: String,
    pub email: String,
    pub department: String,
    pub position: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingRecordDto {
    pub id: String,
    pub tenant_id: String,
    pub employee_id: String,
    pub course_name: String,
    pub completed_at: String,
    pub expires_at: Option<String>,
    pub score: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecordTrainingRequest {
    pub employee_id: String,
    pub course_name: String,
    pub completed_at: String,
    pub expires_at: Option<String>,
    pub score: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeaveRequestDto {
    pub id: String,
    pub tenant_id: String,
    pub employee_id: String,
    pub leave_type: String,
    pub start_date: String,
    pub end_date: String,
    pub status: String,
    pub reason: Option<String>,
    pub approved_by: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubmitLeaveRequest {
    pub employee_id: String,
    pub leave_type: String,
    pub start_date: String,
    pub end_date: String,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceReviewDto {
    pub id: String,
    pub tenant_id: String,
    pub employee_id: String,
    pub reviewer_id: String,
    pub rating: i32,
    pub comments: Option<String>,
    pub status: String,
    pub review_date: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateReviewRequest {
    pub employee_id: String,
    pub reviewer_id: String,
    pub rating: i32,
    pub comments: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimecardDto {
    pub id: String,
    pub tenant_id: String,
    pub employee_id: String,
    pub clock_in: String,
    pub clock_out: Option<String>,
    pub total_hours: Option<f64>,
}

pub struct HrApi;

impl HrApi {
    // ---- Employees ----
    pub async fn list_employees(client: &ApiClient) -> Result<Vec<EmployeeDto>, ApiError> {
        client.get("/api/v1/hr/employees").await
    }

    pub async fn get_employee(client: &ApiClient, id: &str) -> Result<EmployeeDto, ApiError> {
        client.get(&format!("/api/v1/hr/employees/{}", id)).await
    }

    pub async fn create_employee(
        client: &ApiClient,
        req: &CreateEmployeeRequest,
    ) -> Result<EmployeeDto, ApiError> {
        client.post("/api/v1/hr/employees", req).await
    }

    // ---- Training ----
    pub async fn list_training_records(
        client: &ApiClient,
    ) -> Result<Vec<TrainingRecordDto>, ApiError> {
        client.get("/api/v1/hr/training").await
    }

    pub async fn record_training(
        client: &ApiClient,
        req: &RecordTrainingRequest,
    ) -> Result<TrainingRecordDto, ApiError> {
        client.post("/api/v1/hr/training", req).await
    }

    // ---- Leave ----
    pub async fn list_leave_requests(client: &ApiClient) -> Result<Vec<LeaveRequestDto>, ApiError> {
        client.get("/api/v1/hr/leave").await
    }

    pub async fn submit_leave(
        client: &ApiClient,
        req: &SubmitLeaveRequest,
    ) -> Result<LeaveRequestDto, ApiError> {
        client.post("/api/v1/hr/leave", req).await
    }

    // ---- Reviews ----
    pub async fn list_reviews(client: &ApiClient) -> Result<Vec<PerformanceReviewDto>, ApiError> {
        client.get("/api/v1/hr/reviews").await
    }

    pub async fn create_review(
        client: &ApiClient,
        req: &CreateReviewRequest,
    ) -> Result<PerformanceReviewDto, ApiError> {
        client.post("/api/v1/hr/reviews", req).await
    }

    // ---- Timecards ----
    pub async fn list_timecards(client: &ApiClient) -> Result<Vec<TimecardDto>, ApiError> {
        client.get("/api/v1/hr/timecards").await
    }

    pub async fn clock_in(client: &ApiClient, employee_id: &str) -> Result<TimecardDto, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> {
            employee_id: &'a str,
        }
        client
            .post("/api/v1/hr/timecards/clock-in", &Body { employee_id })
            .await
    }
}

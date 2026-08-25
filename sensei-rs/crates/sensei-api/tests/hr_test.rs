//! End-to-end tests for HR route handlers.
//!
//! Covers:
//! - CRUD /api/v1/hr/employees
//! - POST/GET /api/v1/hr/training
//! - POST/GET /api/v1/hr/leave
//! - POST/GET /api/v1/hr/reviews
//! - POST /api/v1/hr/timecards/clock-in, /clock-out
//! - Error cases (not_found, unauthenticated)

use axum::http::StatusCode;
use chrono::Utc;
use serde_json::Value;
use uuid::Uuid;

mod common;

// ── Employees ─────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_get_employee() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_code": "",
        "user_id": user_id.to_string(),
        "full_name": "John Doe",
        "email": "john.doe@sensei.test",
        "department": "Engineering",
        "job_title": "Software Engineer",
        "employment_type": "full_time",
        "status": "active",
        "hire_date": now,
        "termination_date": null,
        "supervisor_id": null,
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/hr/employees", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let emp_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!emp_id.is_empty());
    assert_eq!(json["full_name"], "John Doe");

    // Get the employee
    let req_get = app.get_authenticated(&format!("/api/v1/hr/employees/{}", emp_id), &token);
    let mut resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
    let json_get: Value = app.json_body(&mut resp_get).await;
    assert_eq!(json_get["full_name"], "John Doe");
}

#[tokio::test]
async fn test_list_employees() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/hr/employees", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
}

#[tokio::test]
async fn test_get_employee_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let id = Uuid::nil().to_string();
    let req = app.get_authenticated(&format!("/api/v1/hr/employees/{}", id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_employee_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    // Create employee
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_code": "",
        "user_id": user_id.to_string(),
        "full_name": "Jane Smith",
        "email": "jane.smith@sensei.test",
        "department": "Engineering",
        "job_title": "Senior Engineer",
        "employment_type": "full_time",
        "status": "active",
        "hire_date": now,
        "termination_date": null,
        "supervisor_id": null,
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/hr/employees", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let emp_id = json["id"].as_str().unwrap().to_string();

    // Update status
    let status_body = serde_json::json!({ "status": "on_leave" });
    let req_status = app.put_authenticated(
        &format!("/api/v1/hr/employees/{}/status", emp_id),
        &token,
        status_body,
    );
    let mut resp_status = app.send_request(req_status).await;
    assert_eq!(resp_status.status(), StatusCode::OK);
    let json_status: Value = app.json_body(&mut resp_status).await;
    assert_eq!(json_status["status"], "on_leave");
}

// ── Training Records ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_record_and_list_training() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let emp_id = Uuid::new_v4();
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_id": emp_id.to_string(),
        "course_name": "Safety Training",
        "provider": "OSHA",
        "credits": 8,
        "completed_at": now,
        "expires_at": null,
        "certificate_url": null,
    });
    let req = app.post_authenticated("/api/v1/hr/training", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let training_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!training_id.is_empty());

    // List training records
    let req_list = app.get_authenticated(
        &format!("/api/v1/hr/training?employee_id={}", emp_id),
        &token,
    );
    let resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
}

// ── Leave Requests ────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_submit_and_list_leave() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();
    let later = (Utc::now() + chrono::Duration::days(5)).to_rfc3339();

    let emp_id = Uuid::new_v4();
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_id": emp_id.to_string(),
        "leave_type": "annual",
        "start_date": now,
        "end_date": later,
        "total_days": 5,
        "status": "pending",
        "reason": "Annual vacation",
        "approved_by": null,
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/hr/leave", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let leave_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!leave_id.is_empty());

    // Approve leave
    let approve_body = serde_json::json!({ "approved_by": Uuid::new_v4().to_string() });
    let req_approve = app.post_authenticated(
        &format!("/api/v1/hr/leave/{}/approve", leave_id),
        &token,
        approve_body,
    );
    let resp_approve = app.send_request(req_approve).await;
    assert_eq!(resp_approve.status(), StatusCode::OK);
}

// ── Performance Reviews ───────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_list_reviews() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let emp_id = Uuid::new_v4();
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_id": emp_id.to_string(),
        "reviewer_id": Uuid::new_v4().to_string(),
        "review_period": "Q1_2026",
        "overall_rating": 4.5,
        "strengths": "Strong technical skills",
        "areas_for_improvement": "Communication",
        "goals": "Lead a project",
        "status": "draft",
        "created_at": now,
        "completed_at": null,
    });
    let req = app.post_authenticated("/api/v1/hr/reviews", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let review_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!review_id.is_empty());

    // List reviews
    let req_list = app.get_authenticated(
        &format!("/api/v1/hr/reviews?employee_id={}", emp_id),
        &token,
    );
    let resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
}

// ── Timecards ─────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_clock_in_and_out() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let emp_id = Uuid::new_v4();

    // Clock in
    let clock_in_body = serde_json::json!({ "employee_id": emp_id.to_string() });
    let req_in = app.post_authenticated("/api/v1/hr/timecards/clock-in", &token, clock_in_body);
    let mut resp_in = app.send_request(req_in).await;
    assert_eq!(resp_in.status(), StatusCode::OK);
    let json_in: Value = app.json_body(&mut resp_in).await;
    let timecard_id = json_in["id"].as_str().unwrap_or("").to_string();
    assert!(!timecard_id.is_empty());

    // Clock out
    let clock_out_body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "timecard_id": timecard_id,
    });
    let req_out = app.post_authenticated("/api/v1/hr/timecards/clock-out", &token, clock_out_body);
    let resp_out = app.send_request(req_out).await;
    assert_eq!(resp_out.status(), StatusCode::OK);
}

// ── Unauthenticated ───────────────────────────────────────────────────────────

#[tokio::test]
async fn test_hr_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/hr/employees");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

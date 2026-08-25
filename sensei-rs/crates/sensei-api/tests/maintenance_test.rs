//! End-to-end tests for maintenance route handlers.
//!
//! Covers:
//! - CRUD /api/v1/maintenance/work-requests
//! - CRUD /api/v1/maintenance/pm-schedules
//! - CRUD /api/v1/maintenance/equipment
//! - Error cases (not_found, unauthenticated)

use axum::http::StatusCode;
use serde_json::Value;
use uuid::Uuid;

mod common;

// ── Work Requests ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_get_work_request() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "equipment_id": Uuid::new_v4().to_string(),
        "title": "Fix conveyor belt",
        "description": "Conveyor belt #3 is making unusual noise",
        "priority": "High",
        "status": "Open",
        "requested_by": Uuid::new_v4().to_string(),
        "assigned_to": null,
        "created_at": "2025-01-01T00:00:00Z",
        "completed_at": null,
    });
    let req = app.post_authenticated("/api/v1/maintenance/work-requests", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let wr_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!wr_id.is_empty());
    assert_eq!(json["title"], "Fix conveyor belt");

    // Get the work request
    let req_get = app.get_authenticated(
        &format!("/api/v1/maintenance/work-requests/{}", wr_id),
        &token,
    );
    let mut resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
    let json_get: Value = app.json_body(&mut resp_get).await;
    assert_eq!(json_get["title"], "Fix conveyor belt");
}

#[tokio::test]
async fn test_list_work_requests() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/maintenance/work-requests", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
}

#[tokio::test]
async fn test_get_work_request_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let id = Uuid::nil().to_string();
    let req = app.get_authenticated(
        &format!("/api/v1/maintenance/work-requests/{}", id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_work_request_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "equipment_id": Uuid::new_v4().to_string(),
        "title": "Request for status update test",
        "description": "Testing status update",
        "priority": "Medium",
        "status": "Open",
        "requested_by": Uuid::new_v4().to_string(),
        "assigned_to": null,
        "created_at": "2025-01-01T00:00:00Z",
        "completed_at": null,
    });
    let req = app.post_authenticated("/api/v1/maintenance/work-requests", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let wr_id = json["id"].as_str().unwrap().to_string();

    // Update status
    let status_body = serde_json::json!({ "status": "InProgress" });
    let req_status = app.put_authenticated(
        &format!("/api/v1/maintenance/work-requests/{}/status", wr_id),
        &token,
        status_body,
    );
    let resp_status = app.send_request(req_status).await;
    assert_eq!(resp_status.status(), StatusCode::OK);
}

// ── PM Schedules ──────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_get_pm_schedule() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "equipment_id": Uuid::new_v4().to_string(),
        "task_name": "Monthly CNC Calibration",
        "frequency_days": 30,
        "last_performed": null,
        "next_due": "2025-02-01T00:00:00Z",
        "assigned_to": [Uuid::new_v4().to_string()],
        "is_active": true,
    });
    let req = app.post_authenticated("/api/v1/maintenance/pm-schedules", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let pm_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!pm_id.is_empty());

    // Get the PM schedule
    let req_get = app.get_authenticated(
        &format!("/api/v1/maintenance/pm-schedules/{}", pm_id),
        &token,
    );
    let resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_list_pm_schedules() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/maintenance/pm-schedules", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Equipment ─────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_register_and_get_equipment() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "equipment_code": "EQ-CNC-007",
        "name": "CNC Machine #7",
        "equipment_type": "CNC",
        "location": "Building A, Floor 2",
        "status": "Operational",
        "install_date": "2025-01-01T00:00:00Z",
        "last_maintenance": null,
        "oee_percentage": 85.0,
    });
    let req = app.post_authenticated("/api/v1/maintenance/equipment", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let equip_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!equip_id.is_empty());
    assert_eq!(json["name"], "CNC Machine #7");

    // Get equipment
    let req_get = app.get_authenticated(
        &format!("/api/v1/maintenance/equipment/{}", equip_id),
        &token,
    );
    let resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_list_equipment() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/maintenance/equipment", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Unauthenticated ───────────────────────────────────────────────────────────

#[tokio::test]
async fn test_maintenance_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/maintenance/work-requests");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

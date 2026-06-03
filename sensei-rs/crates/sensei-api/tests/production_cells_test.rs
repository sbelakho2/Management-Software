//! End-to-end tests for Production Cell endpoints.
//!
//! Covers: CRUD, utilization.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_production_cell() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Cell A",
        "code": "CELL-001",
        "description": "Assembly cell A",
        "cell_type": "Assembly",
        "location": "Building 1",
        "capacity_per_shift": 100,
        "shifts_per_day": 2,
        "efficiency_target": 0.85,
        "supervisor_id": null,
    });
    let req = app.post_authenticated("/api/v1/production-cells", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Cell A");
}

#[tokio::test]
async fn test_list_production_cells() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Cell B",
        "code": "CELL-002",
        "description": "Machining cell B",
        "cell_type": "Machining",
        "capacity_per_shift": 50,
        "shifts_per_day": 2,
        "efficiency_target": 0.80,
        "supervisor_id": null,
    });
    let req = app.post_authenticated("/api/v1/production-cells", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/production-cells", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_production_cell() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Cell Get",
        "code": "CELL-003",
        "description": "Assembly cell for get test",
        "cell_type": "Assembly",
        "capacity_per_shift": 80,
        "shifts_per_day": 2,
        "efficiency_target": 0.90,
        "supervisor_id": null,
    });
    let req = app.post_authenticated("/api/v1/production-cells", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let cell_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/production-cells/{}", cell_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], cell_id);
}

#[tokio::test]
async fn test_get_production_cell_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/production-cells/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_production_cell() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Cell Update",
        "code": "CELL-004",
        "description": "Assembly cell for update test",
        "cell_type": "Assembly",
        "capacity_per_shift": 60,
        "shifts_per_day": 2,
        "efficiency_target": 0.85,
        "supervisor_id": null,
    });
    let req = app.post_authenticated("/api/v1/production-cells", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let cell_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated Cell"});
    let req = app.put_authenticated(
        &format!("/api/v1/production-cells/{}", cell_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Cell");
}

#[tokio::test]
async fn test_get_cell_utilization() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Cell Util",
        "code": "CELL-005",
        "description": "Assembly cell for utilization test",
        "cell_type": "Assembly",
        "capacity_per_shift": 100,
        "shifts_per_day": 2,
        "efficiency_target": 0.95,
        "supervisor_id": null,
    });
    let req = app.post_authenticated("/api/v1/production-cells", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let cell_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(
        &format!("/api/v1/production-cells/{}/utilization", cell_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

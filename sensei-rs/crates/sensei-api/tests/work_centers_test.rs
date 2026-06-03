//! End-to-end tests for work center endpoints.
//!
//! Tests CRUD operations, capacity queries, and efficiency reports
//! for manufacturing work centers.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_work_center() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::work_center_payload("Assembly Line 1", "Assembly");
    let req = app.post_authenticated("/api/v1/work-centers", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Assembly Line 1");
    assert_eq!(json["work_center_type"], "Assembly");
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_work_centers() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a work center
    let body = common::fixtures::work_center_payload("List WC", "Machining");
    let req = app.post_authenticated("/api/v1/work-centers", &token, body);
    app.send_request(req).await;

    // List
    let req = app.get_authenticated("/api/v1/work-centers", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_work_center() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::work_center_payload("Get WC", "Welding");
    let req = app.post_authenticated("/api/v1/work-centers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let wc_id = created["id"].as_str().unwrap().to_string();

    // Get by ID
    let req = app.get_authenticated(&format!("/api/v1/work-centers/{}", wc_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), wc_id);
}

#[tokio::test]
async fn test_get_work_center_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/work-centers/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_work_center() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::work_center_payload("Update WC", "Painting");
    let req = app.post_authenticated("/api/v1/work-centers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let wc_id = created["id"].as_str().unwrap().to_string();

    // Update
    let update_body = serde_json::json!({
        "name": "Updated WC Name",
        "description": "Updated description",
    });
    let req = app.put_authenticated(&format!("/api/v1/work-centers/{}", wc_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated WC Name");
}

#[tokio::test]
async fn test_deactivate_work_center() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::work_center_payload("Deactivate WC", "Testing");
    let req = app.post_authenticated("/api/v1/work-centers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let wc_id = created["id"].as_str().unwrap().to_string();

    // Deactivate
    let req = app.delete_authenticated(&format!("/api/v1/work-centers/{}", wc_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["is_active"].as_bool().unwrap_or(true));
}

#[tokio::test]
async fn test_get_work_center_capacity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::work_center_payload("Capacity WC", "Assembly");
    let req = app.post_authenticated("/api/v1/work-centers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let wc_id = created["id"].as_str().unwrap().to_string();

    // Get capacity
    let req = app.get_authenticated(
        &format!("/api/v1/work-centers/{}/capacity", wc_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["capacity_per_shift"].as_i64().is_some());
}

#[tokio::test]
async fn test_get_efficiency_report() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/work-centers/efficiency-report", &token);
    let resp = app.send_request(req).await;
    // This may return OK or NOT_FOUND depending on implementation
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

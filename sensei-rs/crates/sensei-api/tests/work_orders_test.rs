//! End-to-end tests for work order endpoints.
//!
//! Tests CRUD, status transitions, operations, and statistics for
//! manufacturing work orders.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_work_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::work_order_payload("Test Product", 100);
    let req = app.post_authenticated("/api/v1/work-orders", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["product_name"], "Test Product");
    assert_eq!(json["quantity"], 100);
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_work_orders() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a work order first
    let body = common::fixtures::work_order_payload("List Test", 50);
    let req = app.post_authenticated("/api/v1/work-orders", &token, body);
    app.send_request(req).await;

    // List work orders
    let req = app.get_authenticated("/api/v1/work-orders", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_work_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a work order
    let body = common::fixtures::work_order_payload("Get Test", 75);
    let req = app.post_authenticated("/api/v1/work-orders", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let work_order_id = created["id"].as_str().unwrap().to_string();

    // Get by ID
    let req = app.get_authenticated(&format!("/api/v1/work-orders/{}", work_order_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), work_order_id);
}

#[tokio::test]
async fn test_get_work_order_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/work-orders/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_work_order_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a work order
    let body = common::fixtures::work_order_payload("Status Test", 60);
    let req = app.post_authenticated("/api/v1/work-orders", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let work_order_id = created["id"].as_str().unwrap().to_string();

    // Update status
    let status_body = serde_json::json!({ "status": "InProgress" });
    let req = app.put_authenticated(
        &format!("/api/v1/work-orders/{}/status", work_order_id),
        &token,
        status_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "InProgress");
}

#[tokio::test]
async fn test_delete_work_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a work order
    let body = common::fixtures::work_order_payload("Delete Test", 30);
    let req = app.post_authenticated("/api/v1/work-orders", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let work_order_id = created["id"].as_str().unwrap().to_string();

    // Delete (cancel)
    let req = app.delete_authenticated(&format!("/api/v1/work-orders/{}", work_order_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_work_order_stats() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a couple of work orders to get meaningful stats
    for i in 0..3 {
        let body = common::fixtures::work_order_payload(&format!("Stats Product {}", i), 10 * (i + 1));
        let req = app.post_authenticated("/api/v1/work-orders", &token, body);
        app.send_request(req).await;
    }

    let req = app.get_authenticated("/api/v1/work-orders/stats", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["total"].as_u64().unwrap_or(0) >= 3);
}

#[tokio::test]
async fn test_list_work_order_operations() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a work order
    let body = common::fixtures::work_order_payload("Ops Test", 40);
    let req = app.post_authenticated("/api/v1/work-orders", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let work_order_id = created["id"].as_str().unwrap().to_string();

    // List operations
    let req = app.get_authenticated(
        &format!("/api/v1/work-orders/{}/operations", work_order_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_array().is_some());
}

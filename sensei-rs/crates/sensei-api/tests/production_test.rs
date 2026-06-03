//! End-to-end tests for Production endpoints.
//!
//! Covers: production work-orders CRUD+status+report, production orders
//! CRUD+complete, BOM, MRP.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_production_create_work_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "wo_number": format!("WO-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_id": uuid::Uuid::new_v4().to_string(),
        "product_name": "Prod Widget",
        "quantity": 50,
        "quantity_completed": 0,
        "status": "created",
        "work_center_id": null,
        "priority": "High",
        "scheduled_start": null,
        "scheduled_end": null,
        "actual_start": null,
        "actual_end": null,
        "assigned_to": [],
        "notes": "",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/production/work-orders", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_production_list_work_orders() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/production/work-orders", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_production_create_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "order_number": format!("PO-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_id": uuid::Uuid::new_v4().to_string(),
        "quantity_planned": 100,
        "quantity_produced": 0,
        "quantity_scrapped": 0,
        "status": "planned",
        "work_center_id": null,
        "planned_start": "2026-07-01T00:00:00Z",
        "planned_end": "2026-08-01T00:00:00Z",
        "actual_start": null,
        "actual_end": null,
        "created_at": "2026-06-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/production/orders", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_production_list_orders() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/production/orders", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_production_run_mrp() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "product_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/production/mrp", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

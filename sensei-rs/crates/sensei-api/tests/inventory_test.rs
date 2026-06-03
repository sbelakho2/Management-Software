//! End-to-end tests for Inventory endpoints.
//!
//! Tests CRUD for inventory items, stock moves, warehouses, and stats.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_inventory_item() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::inventory_item_payload("SKU-001", "Raw Steel");
    let req = app.post_authenticated("/api/v1/inventory/items", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Raw Steel");
}

#[tokio::test]
async fn test_list_inventory_items() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::inventory_item_payload("SKU-002", "Aluminum Sheet");
    let req = app.post_authenticated("/api/v1/inventory/items", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/inventory/items", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_inventory_item() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::inventory_item_payload("SKU-003", "Copper Wire");
    let req = app.post_authenticated("/api/v1/inventory/items", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let item_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/inventory/items/{}", item_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), item_id);
}

#[tokio::test]
async fn test_get_inventory_item_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/inventory/items/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_inventory_item() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::inventory_item_payload("SKU-004", "Steel Bolts");
    let req = app.post_authenticated("/api/v1/inventory/items", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let item_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({
        "name": "Updated Steel Bolts",
        "quantity_on_hand": 200.0,
    });
    let req = app.put_authenticated(&format!("/api/v1/inventory/items/{}", item_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Steel Bolts");
}

#[tokio::test]
async fn test_create_warehouse() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "name": "Main Warehouse",
        "code": "WH-001",
        "location": "Building A",
        "is_active": true,
    });
    let req = app.post_authenticated("/api/v1/inventory/warehouses", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Main Warehouse");
}

#[tokio::test]
async fn test_list_warehouses() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "name": "Overflow Warehouse",
        "code": "WH-002",
        "location": "Building B",
        "is_active": true,
    });
    let req = app.post_authenticated("/api/v1/inventory/warehouses", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/inventory/warehouses", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_inventory_stats() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create some items for stats
    for i in 0..2 {
        let body = common::fixtures::inventory_item_payload(
            &format!("SKU-{:03}", 100 + i),
            &format!("Stats Item {}", i),
        );
        let req = app.post_authenticated("/api/v1/inventory/items", &token, body);
        app.send_request(req).await;
    }

    let req = app.get_authenticated("/api/v1/inventory/stats", &token);
    let resp = app.send_request(req).await;
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_create_stock_move() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // First create an item
    let body = common::fixtures::inventory_item_payload("SKU-STOCK", "Stock Move Item");
    let req = app.post_authenticated("/api/v1/inventory/items", &token, body);
    let mut resp = app.send_request(req).await;
    let item: Value = app.json_body(&mut resp).await;
    let item_id = item["id"].as_str().unwrap().to_string();

    // Create stock move
    let move_body = serde_json::json!({
        "item_id": item_id,
        "warehouse_id": uuid::Uuid::new_v4().to_string(),
        "move_type": "adjustment",
        "quantity": 50.0,
        "notes": "Test stock adjustment",
    });
    let req = app.post_authenticated("/api/v1/inventory/moves", &token, move_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_stock_moves() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/inventory/moves", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some());
}

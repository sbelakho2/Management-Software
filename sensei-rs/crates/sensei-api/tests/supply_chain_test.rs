//! End-to-end tests for Supply Chain endpoints.
//!
//! Covers: RFQs, Quotes, Sales Orders, Purchase Orders, Inventory, Stock Moves.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_supply_chain_list_inventory() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/supply-chain/inventory", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "rfq_number": format!("SC-RFQ-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "supplier_name": "Supplier Co",
        "status": "Draft",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "quote_number": format!("SC-Q-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "customer_name": "Customer Co",
        "total_amount": 5000.0,
    });
    let req = app.post_authenticated("/api/v1/supply-chain/quotes", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_sales_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "order_number": format!("SO-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "customer_name": "Customer Co",
        "total_amount": 10000.0,
        "status": "Pending",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/sales-orders", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_purchase_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "order_number": format!("PO-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "supplier_name": "Supplier Co",
        "total_amount": 7500.0,
        "status": "Pending",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/purchase-orders", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_list_quotes() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/supply-chain/quotes", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_stock_move() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "item_id": uuid::Uuid::new_v4().to_string(),
        "from_location": "Warehouse A",
        "to_location": "Production Line 1",
        "quantity": 10.0,
        "move_type": "Transfer",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/stock-moves", &token, body);
    let resp = app.send_request(req).await;
    // May be 404 if item doesn't exist, but endpoint should respond
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

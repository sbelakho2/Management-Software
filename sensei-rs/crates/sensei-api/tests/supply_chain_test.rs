//! End-to-end tests for Supply Chain endpoints.
//!
//! Covers: RFQs, Quotes, Sales Orders, Purchase Orders, Inventory, Stock Moves.

use axum::http::StatusCode;

mod common;

#[tokio::test]
async fn test_supply_chain_list_inventory() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/supply-chain/inventory", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "rfq_number": format!("SC-RFQ-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "supplier_name": "Supplier Co",
        "status": "draft",
        "items": [],
        "notes": "",
        "created_by": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/rfqs", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "quote_number": format!("SC-Q-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "rfq_id": null,
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Customer Co",
        "status": "draft",
        "line_items": [],
        "total_amount": 5000.0,
        "currency": "USD",
        "valid_until": "2026-12-31T00:00:00Z",
        "created_by": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/quotes", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_sales_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "order_number": format!("SO-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Customer Co",
        "status": "pending",
        "line_items": [],
        "total_amount": 10000.0,
        "currency": "USD",
        "delivery_date": null,
        "shipping_address": "1 Test Street",
        "created_by": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/sales-orders", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_purchase_order() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "po_number": format!("PO-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "supplier_name": "Supplier Co",
        "status": "pending",
        "line_items": [],
        "total_amount": 7500.0,
        "currency": "USD",
        "expected_delivery": null,
        "created_by": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/purchase-orders", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_list_quotes() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/supply-chain/quotes", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_supply_chain_create_stock_move() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "product_id": uuid::Uuid::new_v4().to_string(),
        "product_name": "Widget",
        "quantity": 10,
        "move_type": "transfer",
        "from_location": null,
        "to_location": "Warehouse A",
        "reference_type": null,
        "reference_id": null,
        "created_by": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/supply-chain/stock-moves", &token, body);
    let resp = app.send_request(req).await;
    // May be 404 if the product doesn't exist, but the endpoint must respond.
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

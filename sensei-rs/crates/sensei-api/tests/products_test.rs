//! End-to-end tests for Product endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_product() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Widget A",
        "sku": format!("SKU-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "description": "A test widget",
        "category": "Finished Goods",
        "product_type": "Finished Good",
        "unit_of_measure": "EA",
        "selling_price": 29.99,
        "standard_cost": 15.00,
    });
    let req = app.post_authenticated("/api/v1/products", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["name"], "Widget A");
}

#[tokio::test]
async fn test_list_products() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Product A",
        "sku": format!("SKU-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_type": "Raw Material",
        "unit_of_measure": "EA",
    });
    let req = app.post_authenticated("/api/v1/products", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/products", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_product() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Get Product",
        "sku": format!("SKU-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_type": "Finished Good",
        "unit_of_measure": "EA",
    });
    let req = app.post_authenticated("/api/v1/products", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let product_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/products/{}", product_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], product_id);
}

#[tokio::test]
async fn test_get_product_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/products/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_product() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Update Product",
        "sku": format!("SKU-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_type": "Finished Good",
        "unit_of_measure": "EA",
    });
    let req = app.post_authenticated("/api/v1/products", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let product_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({
        "name": "Updated Product",
        "sku": format!("SKU-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_type": "Finished Good",
        "unit_of_measure": "EA",
    });
    let req = app.put_authenticated(&format!("/api/v1/products/{}", product_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Product");
}

#[tokio::test]
async fn test_delete_product() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Delete Product",
        "sku": format!("SKU-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "product_type": "Finished Good",
        "unit_of_measure": "EA",
    });
    let req = app.post_authenticated("/api/v1/products", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let product_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/products/{}", product_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

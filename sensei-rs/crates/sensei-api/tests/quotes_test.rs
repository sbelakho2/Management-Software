//! End-to-end tests for Quote endpoints.
//!
//! Covers: CRUD, versions.

use axum::http::StatusCode;
use serde_json::{json, Value};

mod common;

/// Build a valid quote creation payload (all required fields present).
fn quote_payload(total_amount: f64) -> Value {
    json!({
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "line_items": [
            {
                "product_id": uuid::Uuid::new_v4().to_string(),
                "product_name": "Widget",
                "quantity": 10,
                "unit_price": 100.0,
                "discount_percentage": 0.0,
                "net_price": 1000.0,
            }
        ],
        "total_amount": total_amount,
        "currency": "USD",
        "valid_until": "2026-12-31T00:00:00Z",
    })
}

#[tokio::test]
async fn test_create_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/quotes", &token, quote_payload(15000.0));
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    // A real quote number must be generated (QTE-YYYYMMDD-xxxxxxxx).
    let number = json["quote_number"].as_str().unwrap_or("");
    assert!(
        number.starts_with("QTE-"),
        "quote_number must be generated, got '{number}'"
    );
    assert!(number.len() > 15);
}

#[tokio::test]
async fn test_create_quote_missing_required_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = json!({
        "customer_name": "Acme Corp",
        "total_amount": 1000.0,
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, body);
    let resp = app.send_request(req).await;
    // customer_id / line_items / currency / valid_until are required.
    assert!(
        resp.status() == StatusCode::UNPROCESSABLE_ENTITY
            || resp.status() == StatusCode::BAD_REQUEST
    );
}

#[tokio::test]
async fn test_list_quotes() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/quotes", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/quotes", &token, quote_payload(1000.0));
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/quotes/{}", quote_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/quotes", &token, quote_payload(2000.0));
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    let update = json!({
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "line_items": [
            {
                "product_id": uuid::Uuid::new_v4().to_string(),
                "product_name": "Widget",
                "quantity": 25,
                "unit_price": 100.0,
                "discount_percentage": 0.0,
                "net_price": 2500.0,
            }
        ],
        "total_amount": 2500.0,
        "currency": "USD",
        "valid_until": "2026-12-31T00:00:00Z",
    });
    let req = app.put_authenticated(&format!("/api/v1/quotes/{}", quote_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total_amount"], 2500.0);
}

#[tokio::test]
async fn test_delete_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/quotes", &token, quote_payload(500.0));
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/quotes/{}", quote_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_create_quote_version() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/quotes", &token, quote_payload(3000.0));
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    // Version creation is body-less.
    let req = app.post_authenticated(
        &format!("/api/v1/quotes/{}/versions", quote_id),
        &token,
        json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["version_number"], 1);

    // Second version numbers from max(existing) + 1, not count + 1.
    let req = app.post_authenticated(
        &format!("/api/v1/quotes/{}/versions", quote_id),
        &token,
        json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["version_number"], 2);

    // Listing returns both versions, ordered by version number.
    let req = app.get_authenticated(&format!("/api/v1/quotes/{}/versions", quote_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let versions: Value = app.json_body(&mut resp).await;
    assert!(versions.as_array().is_some_and(|a| a.len() == 2));
}

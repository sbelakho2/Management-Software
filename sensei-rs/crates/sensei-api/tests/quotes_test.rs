//! End-to-end tests for Quote endpoints.
//!
//! Covers: CRUD, versions.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "quote_number": format!("Q-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "customer_name": "Acme Corp",
        "total_amount": 15000.0,
        "status": "Draft",
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_quotes() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/quotes", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "quote_number": "Q-GET", "customer_name": "Test", "total_amount": 1000.0,
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/quotes/{}", quote_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "quote_number": "Q-UPD", "customer_name": "Test", "total_amount": 2000.0,
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"total_amount": 2500.0});
    let req = app.put_authenticated(&format!("/api/v1/quotes/{}", quote_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_delete_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "quote_number": "Q-DEL", "customer_name": "Test", "total_amount": 500.0,
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, body);
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
    let body = serde_json::json!({
        "quote_number": "Q-VER", "customer_name": "Test", "total_amount": 3000.0,
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap();

    let version = serde_json::json!({"version_notes": "Updated pricing"});
    let req = app.post_authenticated(
        &format!("/api/v1/quotes/{}/versions", quote_id),
        &token,
        version,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

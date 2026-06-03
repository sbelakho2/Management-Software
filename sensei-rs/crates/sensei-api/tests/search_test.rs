//! End-to-end tests for the unified search endpoint.
//!
//! Covers:
//! - GET /api/v1/search?q=...
//! - Empty query handling
//! - Unauthenticated access

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Search ────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_search_basic() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=test", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["results"].is_array());
    assert!(json["total"].is_number());
    assert_eq!(json["query"], "test");
}

#[tokio::test]
async fn test_search_empty_query() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["results"].is_array());
    assert_eq!(json["total"], 0);
}

#[tokio::test]
async fn test_search_with_limit() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=admin&limit=5", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["results"].is_array());
    assert_eq!(json["query"], "admin");
}

#[tokio::test]
async fn test_search_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/search?q=test");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

//! End-to-end tests for Smart Ingestion route handlers.
//!
//! Covers:
//! - GET /api/v1/smart-ingestion/{id}/status
//! - GET /api/v1/smart-ingestion/history
//!
//! Note: POST /api/v1/smart-ingestion/upload requires multipart form data
//! which is not easily testable via tower::ServiceExt::oneshot.

use axum::http::StatusCode;
use serde_json::Value;
use uuid::Uuid;

mod common;

// ── Ingestion Status ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_get_ingestion_status_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let id = Uuid::nil().to_string();
    let req = app.get_authenticated(
        &format!("/api/v1/smart-ingestion/{}/status", id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_list_ingestion_history() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/smart-ingestion/history", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
    // Should have data array and pagination fields
    assert!(json.get("data").is_some() || json.get("items").is_some() || json.is_array());
}

#[tokio::test]
async fn test_smart_ingestion_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/smart-ingestion/history");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

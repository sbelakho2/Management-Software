//! End-to-end tests for Audit Log endpoints.
//!
//! Covers: list, get, stats.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_list_audit_logs() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/audit-logs", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_audit_log() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/audit-logs/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_get_audit_log_stats() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/audit-logs/stats", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    // Stats response may have various shapes; just check it returns JSON
    assert!(json.is_object());
}

#[tokio::test]
async fn test_get_entity_audit_trail() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // The entity audit trail endpoint returns the entries for one entity
    // (empty when none exist yet).
    let req = app.get_authenticated(
        "/api/v1/audit-logs/entity/task/00000000-0000-0000-0000-000000000001",
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_array());
}

#[tokio::test]
async fn test_audit_logs_invalid_date_filter_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Invalid date parameters are a client error (400), not a silent
    // no-filter.
    let req = app.get_authenticated("/api/v1/audit-logs?date_from=not-a-date", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

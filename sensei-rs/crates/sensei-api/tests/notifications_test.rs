//! End-to-end tests for Notification endpoints.
//!
//! Covers: list, unread count, mark read, mark all read, preferences.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_list_notifications() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/notifications", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_unread_count() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/notifications/unread-count", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("unread_count") || json.is_number());
}

#[tokio::test]
async fn test_mark_all_read() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated(
        "/api/v1/notifications/read-all",
        &token,
        serde_json::json!({}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_preferences() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/notifications/preferences", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_preferences() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let update = serde_json::json!({
        "email_enabled": true,
        "in_app_enabled": true,
        "digest_frequency": "daily",
    });
    let req = app.put_authenticated("/api/v1/notifications/preferences", &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

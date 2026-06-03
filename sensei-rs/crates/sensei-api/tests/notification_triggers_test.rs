//! End-to-end tests for Notification Trigger endpoints.
//!
//! Covers: CRUD, toggle, test, list event types.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Andon Raised Alert", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Andon Raised Alert");
}

#[tokio::test]
async fn test_list_notification_triggers() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Trigger A", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/notification-triggers", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Get Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(
        &format!("/api/v1/notification-triggers/{}", trigger_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], trigger_id);
}

#[tokio::test]
async fn test_get_notification_trigger_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/notification-triggers/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Update Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated Trigger"});
    let req = app.put_authenticated(
        &format!("/api/v1/notification-triggers/{}", trigger_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Trigger");
}

#[tokio::test]
async fn test_delete_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Delete Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(
        &format!("/api/v1/notification-triggers/{}", trigger_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_toggle_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Toggle Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let req = app.patch_authenticated(
        &format!("/api/v1/notification-triggers/{}/toggle", trigger_id),
        &token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("is_active"));
}

#[tokio::test]
async fn test_list_event_types() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/notification-triggers/event-types", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

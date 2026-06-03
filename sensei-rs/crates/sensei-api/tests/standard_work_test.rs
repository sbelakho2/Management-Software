//! End-to-end tests for Standard Work endpoints.
//!
//! Covers: CRUD documents, create/list/get versions.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Document CRUD ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_standard_work() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("Assembly Guide", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["title"], "Assembly Guide");
}

#[tokio::test]
async fn test_list_standard_work() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("SW A", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/standard-work", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_standard_work() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("Get SW", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sw_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/standard-work/{}", sw_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], sw_id);
}

#[tokio::test]
async fn test_get_standard_work_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/standard-work/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_standard_work() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("Update SW", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sw_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"title": "Updated SW"});
    let req = app.put_authenticated(
        &format!("/api/v1/standard-work/{}", sw_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated SW");
}

#[tokio::test]
async fn test_delete_standard_work() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("Delete SW", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sw_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/standard-work/{}", sw_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Versions ───────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_version() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("Version SW", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sw_id = created["id"].as_str().unwrap();

    let version = serde_json::json!({"change_notes": "Initial version"});
    let req = app.post_authenticated(
        &format!("/api/v1/standard-work/{}/versions", sw_id),
        &token,
        version,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_versions() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("List Vers SW", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sw_id = created["id"].as_str().unwrap();

    let version = serde_json::json!({"change_notes": "Version notes"});
    let req = app.post_authenticated(
        &format!("/api/v1/standard-work/{}/versions", sw_id),
        &token,
        version,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/standard-work/{}/versions", sw_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

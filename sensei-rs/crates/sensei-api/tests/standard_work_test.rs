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
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
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
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
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
    let req = app.put_authenticated(&format!("/api/v1/standard-work/{}", sw_id), &token, update);
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
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
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

    let req = app.get_authenticated(&format!("/api/v1/standard-work/{}/versions", sw_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_version_scoped_to_document() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Two documents, each with a version.
    let mut version_ids = Vec::new();
    let mut sw_ids = Vec::new();
    for i in 0..2 {
        let body = common::fixtures::standard_work_payload(
            &format!("Scope SW {i}"),
            "Assembly",
            "Process A",
        );
        let req = app.post_authenticated("/api/v1/standard-work", &token, body);
        let mut resp = app.send_request(req).await;
        let created: Value = app.json_body(&mut resp).await;
        let sw_id = created["id"].as_str().unwrap().to_string();
        sw_ids.push(sw_id.clone());

        let version = serde_json::json!({"change_notes": format!("v{i}")});
        let req = app.post_authenticated(
            &format!("/api/v1/standard-work/{}/versions", sw_id),
            &token,
            version,
        );
        let mut resp = app.send_request(req).await;
        let v: Value = app.json_body(&mut resp).await;
        version_ids.push(v["id"].as_str().unwrap().to_string());
    }

    // A version fetched under the wrong document must 404.
    let req = app.get_authenticated(
        &format!(
            "/api/v1/standard-work/{}/versions/{}",
            sw_ids[1], version_ids[0]
        ),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // Under its own document it is found.
    let req = app.get_authenticated(
        &format!(
            "/api/v1/standard-work/{}/versions/{}",
            sw_ids[0], version_ids[0]
        ),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_put_cannot_set_approval_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::standard_work_payload("Approval SW", "Assembly", "Process A");
    let req = app.post_authenticated("/api/v1/standard-work", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sw_id = created["id"].as_str().unwrap();

    // approved_by/approved_at are not part of the update DTO; sending them
    // must have no effect (they stay None).
    let update = serde_json::json!({
        "title": "Tried to approve via PUT",
        "approved_by": uuid::Uuid::new_v4().to_string(),
        "approved_at": "2026-08-25T00:00:00Z",
    });
    let req = app.put_authenticated(&format!("/api/v1/standard-work/{}", sw_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Tried to approve via PUT");
    assert!(json["approved_by"].is_null());
    assert!(json["approved_at"].is_null());
    assert_eq!(json["status"], "Draft");
}

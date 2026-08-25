//! End-to-end tests for Andon endpoints.
//!
//! Tests raising, acknowledging, resolving, and CRUD operations
//! for the Andon (visual alert) system.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_raise_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::andon_payload("Assembly-1", "Quality issue detected");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_list_andons() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Raise an andon
    let body = common::fixtures::andon_payload("Line-2", "Machine stopped");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    app.send_request(req).await;

    // List
    let req = app.get_authenticated("/api/v1/andon", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["data"].as_array().unwrap_or(&vec![]).is_empty());
}

#[tokio::test]
async fn test_get_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::andon_payload("Station-3", "Material shortage");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let andon_id = created["id"].as_str().unwrap().to_string();

    // Get
    let req = app.get_authenticated(&format!("/api/v1/andon/{}", andon_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), andon_id);
}

#[tokio::test]
async fn test_get_andon_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(&format!("/api/v1/andon/{}", uuid::Uuid::new_v4()), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_acknowledge_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::andon_payload("Cell-4", "Safety issue");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let andon_id = created["id"].as_str().unwrap().to_string();

    // Acknowledge
    let req = app.post_authenticated(
        &format!("/api/v1/andon/{}/acknowledge", andon_id),
        &token,
        serde_json::json!({
            "acknowledged_by": uuid::Uuid::new_v4().to_string(),
        }),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_resolve_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::andon_payload("Line-5", "Tooling issue");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let andon_id = created["id"].as_str().unwrap().to_string();

    // Resolve
    let resolve_body = serde_json::json!({
        "resolved_by": uuid::Uuid::new_v4().to_string(),
        "resolution": "Replaced faulty tool",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/andon/{}/resolve", andon_id),
        &token,
        resolve_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::andon_payload("Station-6", "Initial problem");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let andon_id = created["id"].as_str().unwrap().to_string();

    // Update - Andon handler deserializes as full Andon struct
    let update_body = common::fixtures::andon_payload("Station-6", "Updated problem description");
    let req = app.put_authenticated(&format!("/api/v1/andon/{}", andon_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["description"], "Updated problem description");
}

#[tokio::test]
async fn test_delete_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::andon_payload("Cell-7", "To be deleted");
    let req = app.post_authenticated("/api/v1/andon", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let andon_id = created["id"].as_str().unwrap().to_string();

    // Delete
    let req = app.delete_authenticated(&format!("/api/v1/andon/{}", andon_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

//! End-to-end tests for Knowledge Pack endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_knowledge_pack() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Safety Procedures",
        "description": "Standard safety procedures pack",
        "category": "Safety",
        "tags": ["safety", "compliance"],
        "content": "Safety content here",
        "version": "1.0.0",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/knowledge-packs", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["title"], "Safety Procedures");
}

#[tokio::test]
async fn test_list_knowledge_packs() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Pack A",
        "description": "A knowledge pack",
        "category": "Safety",
        "tags": [],
        "content": "...",
        "version": "1.0.0",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/knowledge-packs", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/knowledge-packs", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_knowledge_pack() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Get Pack",
        "description": "Get pack description",
        "category": "Safety",
        "tags": [],
        "content": "...",
        "version": "1.0.0",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/knowledge-packs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let pack_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/knowledge-packs/{}", pack_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], pack_id);
}

#[tokio::test]
async fn test_update_knowledge_pack() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Update Pack",
        "description": "Update pack description",
        "category": "Safety",
        "tags": [],
        "content": "...",
        "version": "1.0.0",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/knowledge-packs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let pack_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({
        "title": "Updated Pack",
        "description": "Updated description",
        "category": "Safety",
        "tags": [],
        "content": "Updated content",
        "version": "1.1.0",
        "is_published": true,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/knowledge-packs/{}", pack_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Pack");
}

#[tokio::test]
async fn test_delete_knowledge_pack() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Delete Pack",
        "description": "Delete pack description",
        "category": "Safety",
        "tags": [],
        "content": "...",
        "version": "1.0.0",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/knowledge-packs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let pack_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/knowledge-packs/{}", pack_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

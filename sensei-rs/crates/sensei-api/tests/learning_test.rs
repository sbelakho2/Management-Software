//! End-to-end tests for Learning Module endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_learning_module() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Intro to Lean",
        "description": "Introduction to Lean Manufacturing",
        "category": "Lean",
        "difficulty": "beginner",
        "content_url": "https://training.example.com/lean-intro",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/learning/modules", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["title"], "Intro to Lean");
}

#[tokio::test]
async fn test_list_learning_modules() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Module A",
        "description": "Module A description",
        "category": "Lean",
        "difficulty": "beginner",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/learning/modules", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/learning/modules", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_learning_module() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Get Module",
        "description": "Get module description",
        "category": "Lean",
        "difficulty": "intermediate",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/learning/modules", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let module_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/learning/modules/{}", module_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], module_id);
}

#[tokio::test]
async fn test_update_learning_module() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Update Module",
        "description": "Update module description",
        "category": "Lean",
        "difficulty": "advanced",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/learning/modules", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let module_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({
        "title": "Updated Module",
        "description": "Updated description",
        "category": "Lean",
        "difficulty": "advanced",
        "is_published": true,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/learning/modules/{}", module_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Module");
}

#[tokio::test]
async fn test_delete_learning_module() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Delete Module",
        "description": "Delete module description",
        "category": "Lean",
        "difficulty": "beginner",
        "is_published": true,
    });
    let req = app.post_authenticated("/api/v1/learning/modules", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let module_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/learning/modules/{}", module_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

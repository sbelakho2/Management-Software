//! End-to-end tests for user management endpoints.
//!
//! Tests CRUD operations for user management (admin-level endpoints).
//! All endpoints require authentication.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_list_users() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/users", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Value = app.json_body(&mut resp).await;
    assert!(body["total"].as_u64().unwrap_or(0) >= 1);
    assert!(!body["data"].as_array().unwrap_or(&vec![]).is_empty());
}

#[tokio::test]
async fn test_list_users_paginated() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/users?page=1&per_page=10", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Value = app.json_body(&mut resp).await;
    assert_eq!(body["page"], 1);
    assert_eq!(body["per_page"], 10);
}

#[tokio::test]
async fn test_get_user() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = app.admin_user_id;

    let req = app.get_authenticated(&format!("/api/v1/users/{}", user_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Value = app.json_body(&mut resp).await;
    assert_eq!(body["email"], "admin@sensei.test");
}

#[tokio::test]
async fn test_get_user_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/users/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_user() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = app.admin_user_id;

    let body = serde_json::json!({ "name": "Updated Admin Name" });
    let req = app.put_authenticated(&format!("/api/v1/users/{}", user_id), &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Admin Name");
}

#[tokio::test]
async fn test_deactivate_and_activate_user() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = app.admin_user_id;

    // Deactivate
    let req = app.put_authenticated(
        &format!("/api/v1/users/{}/activate", user_id),
        &token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["is_active"].as_bool().unwrap_or(false));
}

#[tokio::test]
async fn test_update_user_roles() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = app.admin_user_id;

    let body = serde_json::json!({ "roles": ["admin", "manager"] });
    let req = app.put_authenticated(&format!("/api/v1/users/{}/roles", user_id), &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    let roles: Vec<String> = serde_json::from_value(json["roles"].clone()).unwrap();
    assert!(roles.contains(&"manager".to_string()));
}

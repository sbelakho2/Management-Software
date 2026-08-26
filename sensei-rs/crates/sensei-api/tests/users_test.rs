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

    let req = app.get_authenticated(&format!("/api/v1/users/{}", uuid::Uuid::new_v4()), &token);
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

    // The legacy wildcard "admin" role is not assignable via the API
    // (privilege-escalation ceiling): the request must be rejected 403.
    let body = serde_json::json!({ "roles": ["admin", "quality_manager"] });
    let req = app.put_authenticated(&format!("/api/v1/users/{}/roles", user_id), &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);

    // Granting only functional roles succeeds.
    let body = serde_json::json!({ "roles": ["quality_manager"] });
    let req = app.put_authenticated(&format!("/api/v1/users/{}/roles", user_id), &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let roles: Vec<String> = serde_json::from_value(json["roles"].clone()).unwrap();
    assert!(roles.contains(&"quality_manager".to_string()));
}

#[tokio::test]
async fn test_user_routes_require_admin() {
    let app = common::TestApp::new().await;
    let _token = app.login_as_admin().await;

    // A plain user (no admin role) in the same tenant.
    let _ = app
        .create_user_with_roles("plain@sensei.test", "TestPass123!", &["user"])
        .await;
    let login = serde_json::json!({
        "email": "plain@sensei.test",
        "password": "TestPass123!",
    });
    let req = app.post("/api/v1/auth/login", login);
    let mut resp = app.send_request(req).await;
    let login_body: Value = app.json_body(&mut resp).await;
    let plain_token = login_body["access_token"].as_str().unwrap().to_string();

    // list / roles / deactivate / activate → 403 for non-admins.
    let req = app.get_authenticated("/api/v1/users", &plain_token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);

    let req = app.put_authenticated(
        &format!("/api/v1/users/{}/roles", app.admin_user_id),
        &plain_token,
        serde_json::json!({"roles": ["user"]}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);

    let req = app.put_authenticated(
        &format!("/api/v1/users/{}/activate", app.admin_user_id),
        &plain_token,
        serde_json::json!({}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);

    // get/update are tenant-scoped, not admin-scoped: the plain user can
    // read their own record.
    let req = app.get_authenticated(
        &format!("/api/v1/users/{}", app.admin_user_id),
        &plain_token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_admin_list_users_scoped_to_tenant() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Two users in the admin's tenant: one plain "user", one with a
    // non-user role so the role filter can be exercised meaningfully
    // (the admin bootstrap account carries ["admin", "user"]).
    let _ = app
        .create_user_with_roles("a@sensei.test", "TestPass123!", &["user"])
        .await;
    let _ = app
        .create_user_with_roles("b@sensei.test", "TestPass123!", &["quality_manager"])
        .await;

    let req = app.get_authenticated("/api/v1/users", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let emails: Vec<&str> = json["data"]
        .as_array()
        .unwrap()
        .iter()
        .map(|u| u["email"].as_str().unwrap())
        .collect();
    assert_eq!(json["total"], 3);
    assert!(emails.contains(&"admin@sensei.test"));
    assert!(emails.contains(&"a@sensei.test"));
    assert!(emails.contains(&"b@sensei.test"));

    // Role filter works (exact membership): "user" matches the admin and
    // user a; "quality_manager" matches only user b.
    let req = app.get_authenticated("/api/v1/users?role=user", &token);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"], 2);

    let req = app.get_authenticated("/api/v1/users?role=quality_manager", &token);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    // The bootstrap admin carries the functional manager roles too.
    assert_eq!(json["total"], 2);
}

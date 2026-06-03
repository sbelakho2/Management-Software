//! End-to-end tests for authentication endpoints.
//!
//! Tests login, register, refresh, logout, password reset, and email
//! verification flows.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

/// Helper: login and return parsed response.
async fn login(app: &common::TestApp, email: &str, password: &str) -> (StatusCode, Value) {
    let body = serde_json::json!({ "email": email, "password": password });
    let req = app.post("/api/v1/auth/login", body);
    let mut resp = app.send_request(req).await;
    let status = resp.status();
    let body: Value = app.json_body(&mut resp).await;
    (status, body)
}

#[tokio::test]
async fn test_login_success() {
    let app = common::TestApp::new().await;
    let (status, body) = login(&app, "admin@sensei.test", &app.admin_password).await;

    assert_eq!(status, StatusCode::OK);
    assert!(!body["access_token"].as_str().unwrap_or("").is_empty());
    assert!(!body["refresh_token"].as_str().unwrap_or("").is_empty());
    assert_eq!(body["token_type"], "Bearer");
    assert!(body["user_id"].as_str().unwrap_or("").len() > 0);
    assert!(body["roles"].as_array().unwrap_or(&vec![]).len() > 0);
}

#[tokio::test]
async fn test_login_invalid_password() {
    let app = common::TestApp::new().await;
    let (status, _) = login(&app, "admin@sensei.test", "WrongPassword123!").await;
    assert_eq!(status, StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_login_nonexistent_user() {
    let app = common::TestApp::new().await;
    let (status, _) = login(&app, "nobody@sensei.test", "SomePass123!").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_register_success() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({
        "email": "newuser@sensei.test",
        "password": "StrongPass123!",
        "name": "New User",
    });
    let req = app.post("/api/v1/auth/register", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["access_token"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["token_type"], "Bearer");
}

#[tokio::test]
async fn test_register_duplicate_email() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({
        "email": "admin@sensei.test",
        "password": "StrongPass123!",
        "name": "Duplicate",
    });
    let req = app.post("/api/v1/auth/register", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_register_weak_password() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({
        "email": "weak@sensei.test",
        "password": "short",
        "name": "Weak",
    });
    let req = app.post("/api/v1/auth/register", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_register_missing_fields() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({
        "email": "missing@sensei.test",
    });
    let req = app.post("/api/v1/auth/register", body);
    let resp = app.send_request(req).await;
    assert!(resp.status().is_client_error());
}

#[tokio::test]
async fn test_refresh_token_success() {
    let app = common::TestApp::new().await;

    // First login
    let (_, login_body) = login(&app, "admin@sensei.test", &app.admin_password).await;
    let refresh_token = login_body["refresh_token"].as_str().unwrap();

    // Refresh
    let body = serde_json::json!({ "refresh_token": refresh_token });
    let req = app.post("/api/v1/auth/refresh", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["access_token"].as_str().unwrap_or("").is_empty());
    assert!(!json["refresh_token"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_refresh_token_invalid() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({ "refresh_token": "invalid-token-value" });
    let req = app.post("/api/v1/auth/refresh", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_logout_success() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.post_authenticated("/api/v1/auth/logout", &token, serde_json::json!({}));
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Value = app.json_body(&mut resp).await;
    assert_eq!(body["message"], "Logged out successfully");
}

#[tokio::test]
async fn test_get_me() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/auth/me", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Value = app.json_body(&mut resp).await;
    assert_eq!(body["email"], "admin@sensei.test");
    assert_eq!(body["name"], "Admin User");
}

#[tokio::test]
async fn test_get_me_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/auth/me");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_update_me() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({ "name": "Updated Admin" });
    let req = app.put_authenticated("/api/v1/auth/me", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Admin");
}

#[tokio::test]
async fn test_change_password() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "old_password": app.admin_password,
        "new_password": "NewStrongPass123!",
    });
    let req = app.put_authenticated("/api/v1/auth/me/password", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["message"].as_str().unwrap_or("").contains("Password"));
}

#[tokio::test]
async fn test_change_password_wrong_old() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "old_password": "WrongOldPassword1!",
        "new_password": "NewStrongPass123!",
    });
    let req = app.put_authenticated("/api/v1/auth/me/password", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_request_password_reset() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({ "email": "admin@sensei.test" });
    let req = app.post("/api/v1/auth/password-reset/request", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["message"].as_str().unwrap_or("").contains("If the email exists"));
}

#[tokio::test]
async fn test_request_password_reset_nonexistent() {
    let app = common::TestApp::new().await;

    // Should still succeed to avoid email enumeration
    let body = serde_json::json!({ "email": "doesnotexist@sensei.test" });
    let req = app.post("/api/v1/auth/password-reset/request", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["message"].as_str().unwrap_or("").contains("If the email exists"));
}

#[tokio::test]
async fn test_confirm_password_reset() {
    let app = common::TestApp::new().await;

    // Request reset to generate a token
    let body = serde_json::json!({ "email": "admin@sensei.test" });
    let req = app.post("/api/v1/auth/password-reset/request", body);
    let _resp = app.send_request(req).await;

    // Get the token from state
    let token_map = app.state.password_reset_tokens.read().await;
    let token = token_map.keys().next().unwrap().clone();
    drop(token_map);

    // Confirm reset
    let confirm_body = serde_json::json!({
        "token": token,
        "new_password": "ResetPass123!",
    });
    let req = app.post("/api/v1/auth/password-reset/confirm", confirm_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["message"], "Password has been reset successfully");
}

#[tokio::test]
async fn test_confirm_password_reset_invalid_token() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({
        "token": "invalid-token-value",
        "new_password": "NewPass123!",
    });
    let req = app.post("/api/v1/auth/password-reset/confirm", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_request_email_verification() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({ "email": "admin@sensei.test" });
    let req = app.post("/api/v1/auth/verify-email/request", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["message"].as_str().unwrap_or("").contains("If the email exists"));
}

#[tokio::test]
async fn test_confirm_email_verification() {
    let app = common::TestApp::new().await;

    // Request verification
    let body = serde_json::json!({ "email": "admin@sensei.test" });
    let req = app.post("/api/v1/auth/verify-email/request", body);
    let _resp = app.send_request(req).await;

    // Get the token from state
    let token_map = app.state.email_verification_tokens.read().await;
    let token = token_map.keys().next().unwrap().clone();
    drop(token_map);

    // Confirm verification
    let confirm_body = serde_json::json!({ "token": token });
    let req = app.post("/api/v1/auth/verify-email/confirm", confirm_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["message"], "Email verified successfully");
}

#[tokio::test]
async fn test_confirm_email_verification_invalid_token() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({ "token": "invalid-token" });
    let req = app.post("/api/v1/auth/verify-email/confirm", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_protected_endpoint_without_auth() {
    let app = common::TestApp::new().await;

    // All protected endpoints should return 401 without a token
    let protected_paths = vec![
        "/api/v1/auth/me",
        "/api/v1/users",
        "/api/v1/work-orders",
        "/api/v1/work-centers",
        "/api/v1/andon",
        "/api/v1/a3",
        "/api/v1/obeya/boards",
        "/api/v1/risk",
        "/api/v1/inventory/items",
        "/api/v1/mrp/demand",
        "/api/v1/tasks",
        "/api/v1/kanban/boards",
        "/api/v1/quality/ncrs",
        "/api/v1/kpi",
        "/api/v1/training/courses",
        "/api/v1/admin/system-health",
        "/api/v1/ctq/characteristics",
        "/api/v1/today",
        "/api/v1/lsw/standards",
        "/api/v1/notification-triggers",
        "/api/v1/standard-work",
        "/api/v1/state-machines",
        "/api/v1/saved-views",
        "/api/v1/contacts",
        "/api/v1/products",
        "/api/v1/audit-logs",
        "/api/v1/production-cells",
    ];

    for path in protected_paths {
        let req = app.get(path);
        let resp = app.send_request(req).await;
        assert_eq!(
            resp.status(),
            StatusCode::UNAUTHORIZED,
            "Path '{}' should require auth, got status {}",
            path,
            resp.status()
        );
    }
}

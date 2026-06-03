//! Authentication helpers for end-to-end tests.
//!
//! Provides utilities for logging in as different users and managing
//! authentication tokens during test execution.

use crate::common::setup::TestApp;
use axum::http::StatusCode;
use serde_json::Value;

/// Login as the admin user and return the parsed login response.
pub async fn admin_login(app: &TestApp) -> Value {
    let body = serde_json::json!({
        "email": "admin@sensei.test",
        "password": app.admin_password,
    });
    let req = app.post("/api/v1/auth/login", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK, "Admin login should succeed");
    app.json_body(&mut resp).await
}

/// Register a new user and return the parsed login response.
pub async fn register_user(
    app: &TestApp,
    email: &str,
    password: &str,
    name: &str,
) -> Value {
    let body = serde_json::json!({
        "email": email,
        "password": password,
        "name": name,
    });
    let req = app.post("/api/v1/auth/register", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK, "Registration should succeed");
    app.json_body(&mut resp).await
}

/// Extract the access token from a login/register response.
pub fn access_token(response: &Value) -> &str {
    response["access_token"]
        .as_str()
        .expect("Response missing access_token")
}

/// Extract the refresh token from a login/register response.
pub fn refresh_token(response: &Value) -> &str {
    response["refresh_token"]
        .as_str()
        .expect("Response missing refresh_token")
}

/// Extract the user ID from a login/register response.
pub fn user_id(response: &Value) -> uuid::Uuid {
    response["user_id"]
        .as_str()
        .and_then(|s| s.parse().ok())
        .expect("Response missing valid user_id")
}

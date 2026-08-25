//! End-to-end tests for Admin endpoints.
//!
//! Covers: system health, db stats, admin list users, deactivate user,
//! system logs, system config.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

/// The seeded test admin only carries the default "user" role; promote it
/// so the admin endpoints (which now enforce RBAC) are reachable.
async fn login_as_admin(app: &common::TestApp) -> String {
    app.state
        .users_service
        .update_user_roles(
            app.admin_user_id,
            vec!["admin".to_string(), "user".to_string()],
        )
        .await
        .expect("promoting the test admin should succeed");
    app.login_as_admin().await
}

#[tokio::test]
async fn test_get_system_health() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;
    let req = app.get_authenticated("/api/v1/admin/system-health", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "healthy");
    assert!(json.as_object().unwrap().contains_key("active_users"));
}

#[tokio::test]
async fn test_get_db_stats() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;
    let req = app.get_authenticated("/api/v1/admin/db-stats", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("total_users"));
    assert!(json.as_object().unwrap().contains_key("total_entities"));
}

#[tokio::test]
async fn test_admin_list_users() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;
    let req = app.get_authenticated("/api/v1/admin/users", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_admin_get_system_logs() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;
    let req = app.get_authenticated("/api/v1/admin/logs", &token);
    let resp = app.send_request(req).await;
    // Logs may be empty or present; just verify the endpoint works
    let status = resp.status();
    assert!(status == StatusCode::OK || status == StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_admin_get_system_config() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;
    let req = app.get_authenticated("/api/v1/admin/config", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("api_host"));
    assert!(json.as_object().unwrap().contains_key("api_port"));
}

#[tokio::test]
async fn test_admin_endpoints_require_admin_role() {
    let app = common::TestApp::new().await;

    // A plain user (no admin role) must be rejected with 403 on every
    // admin endpoint.
    let user_id = app
        .create_user_with_roles("plain@sensei.test", "PlainPass123!", &["user"])
        .await;
    assert!(!user_id.is_nil());

    let login_body = serde_json::json!({
        "email": "plain@sensei.test",
        "password": "PlainPass123!",
    });
    let req = app.post("/api/v1/auth/login", login_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let plain_token = json["access_token"].as_str().unwrap().to_string();

    for path in [
        "/api/v1/admin/system-health",
        "/api/v1/admin/db-stats",
        "/api/v1/admin/users",
        "/api/v1/admin/logs",
        "/api/v1/admin/config",
    ] {
        let req = app.get_authenticated(path, &plain_token);
        let resp = app.send_request(req).await;
        assert_eq!(
            resp.status(),
            StatusCode::FORBIDDEN,
            "admin endpoint '{}' must require the admin role",
            path
        );
    }
}

#[tokio::test]
async fn test_admin_users_are_tenant_scoped() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;

    // A user registered through the public endpoint belongs to a different
    // tenant (registration provisions a fresh tenant).
    let reg_body = serde_json::json!({
        "email": "other-tenant@sensei.test",
        "password": "StrongPass123!",
        "name": "Other Tenant User",
    });
    let req = app.post("/api/v1/auth/register", reg_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let reg: Value = app.json_body(&mut resp).await;
    let other_tenant_id = reg["user_id"].as_str().unwrap().to_string();

    // The admin sees only their own tenant's users (the admin + any user
    // created in the admin tenant), never the other tenant's user.
    let req = app.get_authenticated("/api/v1/admin/users", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let emails: Vec<String> = json["data"]
        .as_array()
        .map(|arr| {
            arr.iter()
                .filter_map(|u| u["email"].as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();
    assert!(
        emails.iter().any(|e| e == "admin@sensei.test"),
        "admin's own tenant users must be listed, got {emails:?}"
    );
    assert!(
        !emails.iter().any(|e| e == "other-tenant@sensei.test"),
        "users of other tenants must not be listed, got {emails:?}"
    );

    // Deactivating a user of another tenant is a 404 (not found in the
    // requester's tenant).
    let req = app.post_authenticated(
        &format!("/api/v1/admin/users/{}/deactivate", other_tenant_id),
        &token,
        serde_json::json!({}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_deactivate_user_in_own_tenant() {
    let app = common::TestApp::new().await;
    let token = login_as_admin(&app).await;

    let user_id = app
        .create_user_with_roles("victim@sensei.test", "VictimPass123!", &["user"])
        .await;

    let req = app.post_authenticated(
        &format!("/api/v1/admin/users/{}/deactivate", user_id),
        &token,
        serde_json::json!({}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let user = app
        .state
        .users_service
        .find_by_id(user_id)
        .await
        .expect("user should still exist (soft delete)");
    assert!(!user.is_active);
}

//! End-to-end tests for Tenant endpoints.
//!
//! Covers: list, create, get, update.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_list_tenants() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/tenants", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_create_tenant() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Test Tenant",
        "slug": format!("test-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "domain": "test.example.com",
    });
    let req = app.post_authenticated("/api/v1/tenants", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_get_tenant() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    // Use the admin's tenant ID
    let tenant_id = app.admin_tenant_id.to_string();
    let req = app.get_authenticated(&format!("/api/v1/tenants/{}", tenant_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], tenant_id);
}

#[tokio::test]
async fn test_update_tenant() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = app.admin_tenant_id.to_string();
    let update = serde_json::json!({"name": "Updated Tenant"});
    let req = app.put_authenticated(
        &format!("/api/v1/tenants/{}", tenant_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Tenant");
}

#[tokio::test]
async fn test_update_tenant_preserves_tenant_id_and_active() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = app.admin_tenant_id.to_string();

    // The tenant id comes from the path; the body cannot change it. The
    // body also carries no id field at all.
    let update = serde_json::json!({
        "name": "Renamed Tenant",
        "slug": "renamed-tenant",
        "id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.put_authenticated(
        &format!("/api/v1/tenants/{}", tenant_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], tenant_id, "tenant_id must come from the path");
    assert_eq!(json["name"], "Renamed Tenant");
    assert_eq!(json["is_active"], true);
}

#[tokio::test]
async fn test_tenant_isolation_for_non_admin() {
    let app = common::TestApp::new().await;
    let admin_token = app.login_as_admin().await;

    // Admin creates a second tenant.
    let body = serde_json::json!({
        "name": "Isolated Tenant",
        "slug": format!("iso-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
    });
    let req = app.post_authenticated("/api/v1/tenants", &admin_token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let created: Value = app.json_body(&mut resp).await;
    let foreign_tenant_id = created["id"].as_str().unwrap().to_string();

    // A plain user (admin's tenant) cannot see the foreign tenant.
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

    // GET on the foreign tenant → 404 (not visible).
    let req = app.get_authenticated(&format!("/api/v1/tenants/{}", foreign_tenant_id), &plain_token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // PUT on the foreign tenant → 404.
    let req = app.put_authenticated(
        &format!("/api/v1/tenants/{}", foreign_tenant_id),
        &plain_token,
        serde_json::json!({"name": "Hijack", "slug": "hijack"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // list does not expose the foreign tenant to the plain user.
    let req = app.get_authenticated("/api/v1/tenants", &plain_token);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let listed: Vec<Value> = serde_json::from_value(json).unwrap();
    assert!(
        !listed.iter().any(|t| t["id"] == foreign_tenant_id),
        "non-admin must not see foreign tenants"
    );

    // A plain user cannot create tenants at all.
    let req = app.post_authenticated(
        "/api/v1/tenants",
        &plain_token,
        serde_json::json!({"name": "Sneaky", "slug": "sneaky"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
}

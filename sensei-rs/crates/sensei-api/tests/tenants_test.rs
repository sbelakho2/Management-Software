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

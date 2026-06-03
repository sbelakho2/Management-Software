//! End-to-end tests for Account endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_account() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Acme Corp",
        "account_number": format!("ACC-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "account_type": "Customer",
        "email": "acme@example.com",
        "phone": "+1-555-0000",
        "is_active": true,
    });
    let req = app.post_authenticated("/api/v1/accounts", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Acme Corp");
}

#[tokio::test]
async fn test_list_accounts() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Account A", "account_number": "ACC-001", "account_type": "Customer",
    });
    let req = app.post_authenticated("/api/v1/accounts", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/accounts", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_account() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Get Account", "account_number": "ACC-GET", "account_type": "Customer",
    });
    let req = app.post_authenticated("/api/v1/accounts", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let acc_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/accounts/{}", acc_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], acc_id);
}

#[tokio::test]
async fn test_update_account() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Update Acc", "account_number": "ACC-UPD", "account_type": "Customer",
    });
    let req = app.post_authenticated("/api/v1/accounts", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let acc_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated Account", "account_type": "Customer"});
    let req = app.put_authenticated(&format!("/api/v1/accounts/{}", acc_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Account");
}

#[tokio::test]
async fn test_delete_account() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "name": "Delete Acc", "account_number": "ACC-DEL", "account_type": "Customer",
    });
    let req = app.post_authenticated("/api/v1/accounts", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let acc_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/accounts/{}", acc_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

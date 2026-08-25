//! End-to-end tests for Contact endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_contact() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+1-555-1234",
        "job_title": "Procurement Manager",
        "is_primary": true,
    });
    let req = app.post_authenticated("/api/v1/contacts", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["first_name"], "John");
}

#[tokio::test]
async fn test_list_contacts() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "first_name": "Jane", "last_name": "Doe", "email": "jane@example.com",
    });
    let req = app.post_authenticated("/api/v1/contacts", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/contacts", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_contact() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "first_name": "Get", "last_name": "Contact", "email": "get@example.com",
    });
    let req = app.post_authenticated("/api/v1/contacts", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let contact_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/contacts/{}", contact_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], contact_id);
}

#[tokio::test]
async fn test_get_contact_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/contacts/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_contact() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "first_name": "Update", "last_name": "Contact", "email": "update@example.com",
    });
    let req = app.post_authenticated("/api/v1/contacts", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let contact_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"first_name": "Updated", "last_name": "Contact", "email": "update@example.com"});
    let req = app.put_authenticated(&format!("/api/v1/contacts/{}", contact_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["first_name"], "Updated");
}

#[tokio::test]
async fn test_delete_contact() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "first_name": "Delete", "last_name": "Contact", "email": "delete@example.com",
    });
    let req = app.post_authenticated("/api/v1/contacts", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let contact_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/contacts/{}", contact_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

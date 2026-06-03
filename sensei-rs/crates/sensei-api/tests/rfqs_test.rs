//! End-to-end tests for RFQ endpoints.
//!
//! Covers: CRUD, line items.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "rfq_number": format!("RFQ-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "title": "RFQ for widgets",
        "status": "Draft",
        "supplier_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_rfqs() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/rfqs", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "rfq_number": "RFQ-GET", "title": "Get RFQ", "supplier_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/rfqs/{}", rfq_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "rfq_number": "RFQ-UPD", "title": "Update RFQ", "supplier_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"title": "Updated RFQ"});
    let req = app.put_authenticated(&format!("/api/v1/rfqs/{}", rfq_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_delete_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "rfq_number": "RFQ-DEL", "title": "Delete RFQ", "supplier_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/rfqs/{}", rfq_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

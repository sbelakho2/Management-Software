//! End-to-end tests for RFQ endpoints.
//!
//! Covers: CRUD, line items.

use axum::http::StatusCode;
use serde_json::{json, Value};

mod common;

/// Build a valid RFQ creation payload (supplier_name/notes required).
fn rfq_payload() -> Value {
    json!({
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "supplier_name": "Acme Supplies",
        "notes": "Requesting quotation for widgets",
    })
}

#[tokio::test]
async fn test_create_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/rfqs", &token, rfq_payload());
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    // A real rfq_number must be generated (RFQ-YYYYMMDD-xxxxxxxx).
    let number = json["rfq_number"].as_str().unwrap_or("");
    assert!(number.starts_with("RFQ-"), "rfq_number must be generated, got '{number}'");
    assert_eq!(json["supplier_name"], "Acme Supplies");
}

#[tokio::test]
async fn test_create_rfq_missing_required_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = json!({ "supplier_id": uuid::Uuid::new_v4().to_string() });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let resp = app.send_request(req).await;
    // supplier_name and notes are required.
    assert!(resp.status() == StatusCode::UNPROCESSABLE_ENTITY
        || resp.status() == StatusCode::BAD_REQUEST);
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
    let req = app.post_authenticated("/api/v1/rfqs", &token, rfq_payload());
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
    let req = app.post_authenticated("/api/v1/rfqs", &token, rfq_payload());
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap();

    let update = json!({
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "supplier_name": "New Supplier",
        "notes": "Updated notes",
    });
    let req = app.put_authenticated(&format!("/api/v1/rfqs/{}", rfq_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["supplier_name"], "New Supplier");
    assert_eq!(json["notes"], "Updated notes");
}

#[tokio::test]
async fn test_delete_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/rfqs", &token, rfq_payload());
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/rfqs/{}", rfq_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_rfq_line_item_crud() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated("/api/v1/rfqs", &token, rfq_payload());
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap().to_string();

    // Add a line item — it gets a stable line_item_id.
    let item = json!({
        "product_id": uuid::Uuid::new_v4().to_string(),
        "product_name": "Widget X",
        "quantity": 100,
        "unit_of_measure": "pcs",
        "target_price": 12.5,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/rfqs/{}/line-items", rfq_id),
        &token,
        item,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let item: Value = app.json_body(&mut resp).await;
    let line_item_id = item["line_item_id"].as_str().unwrap().to_string();
    assert!(line_item_id.len() > 0);
    assert_eq!(item["product_name"], "Widget X");

    // Update by line_item_id.
    let update = json!({
        "product_id": uuid::Uuid::new_v4().to_string(),
        "product_name": "Widget X Rev 2",
        "quantity": 250,
        "unit_of_measure": "box",
        "target_price": 11.0,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/rfqs/{}/line-items/{}", rfq_id, line_item_id),
        &token,
        update.clone(),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: Value = app.json_body(&mut resp).await;
    assert_eq!(updated["product_name"], "Widget X Rev 2");
    assert_eq!(updated["quantity"], 250);
    assert_eq!(updated["unit_of_measure"], "box");
    assert_eq!(updated["line_item_id"], line_item_id);

    // Updating a line item that does not exist → 404.
    let req = app.put_authenticated(
        &format!("/api/v1/rfqs/{}/line-items/{}", rfq_id, uuid::Uuid::new_v4()),
        &token,
        update.clone(),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // The RFQ must reflect the updated item.
    let req = app.get_authenticated(&format!("/api/v1/rfqs/{}", rfq_id), &token);
    let mut resp = app.send_request(req).await;
    let rfq: Value = app.json_body(&mut resp).await;
    let items = rfq["items"].as_array().unwrap();
    assert_eq!(items.len(), 1);
    assert_eq!(items[0]["line_item_id"], line_item_id);
    assert_eq!(items[0]["quantity"], 250);
}

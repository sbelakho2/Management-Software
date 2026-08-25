//! End-to-end tests for Quoting Helper endpoints.
//!
//! Covers: work packets generate/list/update, ingest RFQ documents,
//! build cost, convert to NPI.

use axum::http::StatusCode;
use serde_json::{json, Value};

mod common;

/// Create an RFQ with one line item and return (rfq_id, line_item_id).
async fn create_rfq_with_line_item(
    app: &common::TestApp,
    token: &str,
) -> (String, String) {
    let body = json!({
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "supplier_name": "Acme Supplies",
        "notes": "Please quote",
    });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap().to_string();

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

    (rfq_id, line_item_id)
}

#[tokio::test]
async fn test_generate_work_packets() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, line_item_id) = create_rfq_with_line_item(&app, &token).await;

    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets/generate", rfq_id),
        &token,
        json!({ "line_items": [line_item_id] }),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CREATED);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);

    // One operation per discipline from the estimation table.
    let ops = json["workpackets"].as_array().unwrap();
    assert_eq!(ops.len(), 6, "all six disciplines must be estimated");
    let total_hours: f64 = ops
        .iter()
        .map(|op| op["estimated_hours"].as_f64().unwrap())
        .sum();
    assert_eq!(total_hours, json["estimated_hours"].as_f64().unwrap());
}

#[tokio::test]
async fn test_generate_work_packets_unknown_rfq() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets/generate", uuid::Uuid::new_v4()),
        &token,
        json!({ "line_items": [] }),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_list_work_packets() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, line_item_id) = create_rfq_with_line_item(&app, &token).await;

    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets/generate", rfq_id),
        &token,
        json!({ "line_items": [line_item_id] }),
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets", rfq_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_update_work_packet() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, line_item_id) = create_rfq_with_line_item(&app, &token).await;

    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets/generate", rfq_id),
        &token,
        json!({ "line_items": [line_item_id] }),
    );
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let packet_id = created["id"].as_str().unwrap().to_string();

    let update = json!({"status": "approved", "notes": "Approved by engineering"});
    let req = app.patch_authenticated(
        &format!("/api/v1/quoting-helper/workpackets/{}", packet_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "approved");
    assert_eq!(json["notes"], "Approved by engineering");
}

#[tokio::test]
async fn test_ingest_rfq_documents() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, _) = create_rfq_with_line_item(&app, &token).await;

    // "hello world" in base64 (standard alphabet, padded).
    let body = json!({
        "documents": [
            {"filename": "spec.txt", "type": "txt", "content": "aGVsbG8gd29ybGQ="}
        ]
    });
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/ingest", rfq_id),
        &token,
        body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CREATED);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "completed");
    assert_eq!(json["documents_ingested"], 1);

    // The job must be persisted with real metadata.
    let job_id = json["id"].as_str().unwrap();
    let req = app.get_authenticated(
        &format!("/api/v1/smart-ingestion/{}/status", job_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let job: Value = app.json_body(&mut resp).await;
    assert_eq!(job["status"], "Completed");
    assert_eq!(job["file_size"], 11);
    assert_eq!(job["extracted_data"]["text_char_count"], 11);
    assert!(job["extracted_data"]["sha256"].as_str().unwrap_or("").len() == 64);
}

#[tokio::test]
async fn test_ingest_rfq_documents_invalid_base64() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, _) = create_rfq_with_line_item(&app, &token).await;

    let body = json!({
        "documents": [
            {"filename": "spec.pdf", "type": "pdf", "content": "%%%not-base64%%%"}
        ]
    });
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/ingest", rfq_id),
        &token,
        body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_build_quote_cost() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let quote_id = uuid::Uuid::new_v4().to_string();
    let body = json!({
        "material_costs": {"steel": 100.0},
        "labor_costs": {"machining": 50.0},
        "overhead_percentage": 20.0,
        "margin_percentage": 15.0,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/quotes/{}/cost/build", quote_id),
        &token,
        body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CREATED);
    let json: Value = app.json_body(&mut resp).await;
    // (100 + 50) * 1.2 = 180 cost; 180 * 1.15 = 207 selling price.
    assert_eq!(json["total_cost"], 180.0);
    assert_eq!(json["selling_price"], 207.0);
}

#[tokio::test]
async fn test_convert_quote_to_npi() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a real quote first.
    let quote_body = json!({
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "line_items": [
            {
                "product_id": uuid::Uuid::new_v4().to_string(),
                "product_name": "Widget",
                "quantity": 10,
                "unit_price": 100.0,
                "discount_percentage": 0.0,
                "net_price": 1000.0,
            }
        ],
        "total_amount": 1000.0,
        "currency": "USD",
        "valid_until": "2026-12-31T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/quotes", &token, quote_body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let quote_id = created["id"].as_str().unwrap().to_string();

    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/quotes/{}/convert-to-npi", quote_id),
        &token,
        json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CREATED);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["npi_project_id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["quote_id"], quote_id);

    // The NPI project must actually exist via the quality service.
    let npi_id = json["npi_project_id"].as_str().unwrap();
    let req = app.get_authenticated("/api/v1/quality/npi-projects", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let projects: Value = app.json_body(&mut resp).await;
    let found = projects["data"]
        .as_array()
        .unwrap()
        .iter()
        .any(|p| p["id"] == npi_id && p["quote_id"] == quote_id);
    assert!(found, "NPI project must be linked to the source quote");
}

#[tokio::test]
async fn test_convert_quote_to_npi_missing_quote() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let quote_id = uuid::Uuid::new_v4().to_string();
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/quotes/{}/convert-to-npi", quote_id),
        &token,
        json!({}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_suggest_clarifications_only_missing_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, _) = create_rfq_with_line_item(&app, &token).await;

    // The RFQ line item has a target_price and UoM, and the RFQ has notes:
    // only the RFQ-level missing fields (in empty notes) are asked.
    let req = app.get_authenticated(
        &format!("/api/v1/quoting-helper/ai/clarifications/suggest/{}", rfq_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let clarifications = json["clarifications"].as_array().unwrap();
    // notes is "Please quote" → non-empty → no RFQ-level questions either.
    assert_eq!(clarifications.len(), 0, "no missing fields, no questions");
}

#[tokio::test]
async fn test_suggest_clarifications_missing_target_price() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // RFQ with a line item that has NO target price.
    let body = json!({
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "supplier_name": "Acme Supplies",
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/rfqs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let rfq_id = created["id"].as_str().unwrap().to_string();

    let item = json!({
        "product_id": uuid::Uuid::new_v4().to_string(),
        "product_name": "Widget Y",
        "quantity": 5,
        "unit_of_measure": "pcs",
        "target_price": null,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/rfqs/{}/line-items", rfq_id),
        &token,
        item,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/quoting-helper/ai/clarifications/suggest/{}", rfq_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let clarifications = json["clarifications"].as_array().unwrap();
    assert!(clarifications.iter().any(|c| c["question"]
        .as_str()
        .unwrap()
        .contains("target unit price")));
    assert!(clarifications.iter().any(|c| c["context"]
        .as_str()
        .unwrap()
        .contains("RFQ General Requirements")));
}

#[tokio::test]
async fn test_retrieve_quote_memory() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let (rfq_id, _) = create_rfq_with_line_item(&app, &token).await;

    let req = app.get_authenticated(
        &format!("/api/v1/quoting-helper/ai/quote-memory/retrieve/{}", rfq_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["similar_quotes"].is_array());
    assert!(json["historical_pricing"]["avg_margin"].is_number());
}

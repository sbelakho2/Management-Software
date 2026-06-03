//! End-to-end tests for Quoting Helper endpoints.
//!
//! Covers: work packets generate/list/update, ingest RFQ documents,
//! build cost, convert to NPI.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_generate_work_packets() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let rfq_id = uuid::Uuid::new_v4().to_string();
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets/generate", rfq_id),
        &token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_array().is_some() || json.is_object());
}

#[tokio::test]
async fn test_list_work_packets() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let rfq_id = uuid::Uuid::new_v4().to_string();
    let req = app.get_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/workpackets", rfq_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_work_packet() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let packet_id = uuid::Uuid::new_v4().to_string();
    let update = serde_json::json!({"notes": "Updated notes"});
    let req = app.patch_authenticated(
        &format!("/api/v1/quoting-helper/workpackets/{}", packet_id),
        &token,
        update,
    );
    let resp = app.send_request(req).await;
    // May be 404 if no such packet, but endpoint should respond
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_ingest_rfq_documents() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let rfq_id = uuid::Uuid::new_v4().to_string();
    let body = serde_json::json!({
        "documents": [
            {"filename": "rfq.pdf", "content": "base64content"}
        ]
    });
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/rfqs/{}/ingest", rfq_id),
        &token,
        body,
    );
    let resp = app.send_request(req).await;
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::ACCEPTED);
}

#[tokio::test]
async fn test_build_quote_cost() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let quote_id = uuid::Uuid::new_v4().to_string();
    let body = serde_json::json!({
        "material_cost": 100.0,
        "labor_cost": 50.0,
        "overhead_cost": 20.0,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/quotes/{}/cost/build", quote_id),
        &token,
        body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("total_cost") || json.as_object().unwrap().contains_key("cost_breakdown"));
}

#[tokio::test]
async fn test_convert_quote_to_npi() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let quote_id = uuid::Uuid::new_v4().to_string();
    let req = app.post_authenticated(
        &format!("/api/v1/quoting-helper/quotes/{}/convert-to-npi", quote_id),
        &token,
        serde_json::json!({}),
    );
    let resp = app.send_request(req).await;
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

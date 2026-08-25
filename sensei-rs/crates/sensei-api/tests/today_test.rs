//! End-to-end tests for Today (daily snapshot) endpoint.
//!
//! Covers: get today snapshot with aggregated dashboard data.

use axum::http::StatusCode;
use serde_json::Value;

mod common;


/// Work order payload with all required `WorkOrder` fields (the shared
/// fixture omits id/tenant_id/wo_number/quantity_completed/assigned_to/
/// created_at/updated_at, which the entity requires).
fn work_order_payload(product_name: &str, quantity: i64) -> Value {
    let mut body = common::fixtures::work_order_payload(product_name, quantity);
    body["id"] = serde_json::json!(uuid::Uuid::new_v4().to_string());
    body["tenant_id"] = serde_json::json!(uuid::Uuid::new_v4().to_string());
    body["wo_number"] = serde_json::json!("WO-TEST");
    body["quantity_completed"] = serde_json::json!(0);
    body["assigned_to"] = serde_json::json!([]);
    body["created_at"] = serde_json::json!("2026-01-01T00:00:00Z");
    body["updated_at"] = serde_json::json!("2026-01-01T00:00:00Z");
    body
}

#[tokio::test]
async fn test_get_today_snapshot() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Seed some data so the snapshot has content
    let wo = work_order_payload("Today WO", 10);
    let req = app.post_authenticated("/api/v1/work-orders", &token, wo);
    let _ = app.send_request(req).await;

    let ncr = common::fixtures::ncr_payload("Today NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, ncr);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/today", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("date"));
    assert!(json.as_object().unwrap().contains_key("work_orders"));
    assert!(json.as_object().unwrap().contains_key("quality"));
    assert!(json.as_object().unwrap().contains_key("operations"));
    assert!(json["work_orders"].as_object().unwrap().contains_key("total_active"));
    assert!(json["quality"].as_object().unwrap().contains_key("active_andons"));
    assert!(json["operations"].as_object().unwrap().contains_key("open_risks"));
}

#[tokio::test]
async fn test_today_snapshot_counts_are_real() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // One active work order.
    let wo = work_order_payload("Counted WO", 10);
    let req = app.post_authenticated("/api/v1/work-orders", &token, wo);
    let _ = app.send_request(req).await;

    // One open NCR and one closed NCR — only the open one counts.
    let req = app.post_authenticated(
        "/api/v1/quality/ncrs",
        &token,
        common::fixtures::ncr_payload("Open NCR"),
    );
    let mut resp = app.send_request(req).await;
    let open_ncr: Value = app.json_body(&mut resp).await;
    let open_ncr_id = open_ncr["id"].as_str().unwrap().to_string();
    let _ = open_ncr_id;

    let req = app.post_authenticated(
        "/api/v1/quality/ncrs",
        &token,
        common::fixtures::ncr_payload("Closed NCR"),
    );
    let mut resp = app.send_request(req).await;
    let closed_ncr: Value = app.json_body(&mut resp).await;
    let closed_ncr_id = closed_ncr["id"].as_str().unwrap().to_string();

    // Close the second NCR via a full-entity PUT with status Closed.
    let mut closed_ncr_body = closed_ncr.clone();
    closed_ncr_body["status"] = serde_json::json!("Closed");
    let req = app.put_authenticated(
        &format!("/api/v1/quality/ncrs/{}", closed_ncr_id),
        &token,
        closed_ncr_body,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/today", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;

    assert_eq!(json["work_orders"]["total_active"], 1);
    assert_eq!(json["work_orders"]["in_progress"], 0);
    assert_eq!(json["quality"]["open_ncrs"], 1, "closed NCRs must not count as open");
    assert_eq!(json["quality"]["open_capas"], 0);
}

#[tokio::test]
async fn test_today_snapshot_unauthenticated() {
    let app = common::TestApp::new().await;
    let req = app.get("/api/v1/today");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

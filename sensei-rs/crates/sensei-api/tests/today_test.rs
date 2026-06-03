//! End-to-end tests for Today (daily snapshot) endpoint.
//!
//! Covers: get today snapshot with aggregated dashboard data.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_get_today_snapshot() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Seed some data so the snapshot has content
    let wo = common::fixtures::work_order_payload("Today WO", 10);
    let req = app.post_authenticated("/api/v1/work-orders", &token, wo);
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
async fn test_today_snapshot_unauthenticated() {
    let app = common::TestApp::new().await;
    let req = app.get("/api/v1/today");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

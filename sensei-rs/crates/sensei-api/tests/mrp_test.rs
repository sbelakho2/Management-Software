//! End-to-end tests for MRP (Material Requirements Planning) endpoints.
//!
//! Tests demand, supply, MRP runs, and related operations.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_demand() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::mrp_demand_payload("Widget A", 500.0);
    let req = app.post_authenticated("/api/v1/mrp/demand", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["product_name"], "Widget A");
}

#[tokio::test]
async fn test_list_demand() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::mrp_demand_payload("Widget B", 300.0);
    let req = app.post_authenticated("/api/v1/mrp/demand", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/mrp/demand", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["data"].as_array().unwrap_or(&vec![]).is_empty());
}

#[tokio::test]
async fn test_list_supply() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/mrp/supply", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some());
}

#[tokio::test]
async fn test_run_mrp() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "run_type": "full",
        "notes": "Test MRP run",
    });
    let req = app.post_authenticated("/api/v1/mrp/run", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["run"]["id"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_list_mrp_runs() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Run MRP first
    let run_body = serde_json::json!({ "run_type": "full" });
    let req = app.post_authenticated("/api/v1/mrp/run", &token, run_body);
    app.send_request(req).await;

    // List runs
    let req = app.get_authenticated("/api/v1/mrp/runs", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json.as_array().unwrap_or(&vec![]).is_empty());
}

#[tokio::test]
async fn test_get_mrp_run() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Run MRP first
    let run_body = serde_json::json!({ "run_type": "full" });
    let req = app.post_authenticated("/api/v1/mrp/run", &token, run_body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let run_id = created["run"]["id"].as_str().unwrap().to_string();

    // Get run
    let req = app.get_authenticated(&format!("/api/v1/mrp/runs/{}", run_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["run"]["id"].as_str().unwrap(), run_id);
}

#[tokio::test]
async fn test_get_mrp_run_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/mrp/runs/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

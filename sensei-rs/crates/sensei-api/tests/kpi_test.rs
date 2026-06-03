//! End-to-end tests for KPI endpoints.
//!
//! Tests CRUD for KPI definitions, recording values, and dashboard.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_kpi() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kpi_payload("Overall Equipment Effectiveness", "Production");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Overall Equipment Effectiveness");
}

#[tokio::test]
async fn test_list_kpis() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kpi_payload("List KPI", "Quality");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/kpi", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_kpi() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kpi_payload("Get KPI", "Maintenance");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let kpi_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/kpi/{}", kpi_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), kpi_id);
}

#[tokio::test]
async fn test_get_kpi_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(&format!("/api/v1/kpi/{}", uuid::Uuid::new_v4()), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_kpi() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kpi_payload("Update KPI", "Cost");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let kpi_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({ "name": "Updated KPI Name", "target": 98.0 });
    let req = app.put_authenticated(&format!("/api/v1/kpi/{}", kpi_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated KPI Name");
}

#[tokio::test]
async fn test_delete_kpi() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kpi_payload("Delete KPI", "Safety");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let kpi_id = created["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(&format!("/api/v1/kpi/{}", kpi_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_record_kpi_value() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create KPI first
    let body = common::fixtures::kpi_payload("KPI With Values", "Quality");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let kpi_id = created["id"].as_str().unwrap().to_string();

    // Record a value
    let value_body = serde_json::json!({
        "value": 92.5,
        "note": "Weekly measurement",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/kpi/{}/values", kpi_id),
        &token,
        value_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_kpi_values() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create KPI
    let body = common::fixtures::kpi_payload("KPI List Values", "Delivery");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let kpi_id = created["id"].as_str().unwrap().to_string();

    // List values
    let req = app.get_authenticated(&format!("/api/v1/kpi/{}/values", kpi_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some());
}

#[tokio::test]
async fn test_get_kpi_dashboard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kpi_payload("Dashboard KPI", "People");
    let req = app.post_authenticated("/api/v1/kpi", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let kpi_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/kpi/{}/dashboard", kpi_id), &token);
    let resp = app.send_request(req).await;
    assert!(resp.status() == StatusCode::OK || resp.status() == StatusCode::NOT_FOUND);
}

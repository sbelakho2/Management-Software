//! End-to-end tests for Risk management endpoints.
//!
//! Tests CRUD operations and risk mitigation for the risk registry.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::risk_payload("Supplier delay risk", "Supply Chain");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["title"], "Supplier delay risk");
}

#[tokio::test]
async fn test_list_risks() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::risk_payload("List Risk", "Operational");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/risk", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::risk_payload("Get Risk", "Financial");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/risk/{}", risk_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), risk_id);
}

#[tokio::test]
async fn test_get_risk_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(&format!("/api/v1/risk/{}", uuid::Uuid::new_v4()), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::risk_payload("Update Risk", "Strategic");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({
        "title": "Updated Risk Title",
        "probability": 2,
        "impact": 5,
    });
    let req = app.put_authenticated(&format!("/api/v1/risk/{}", risk_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Risk Title");
}

#[tokio::test]
async fn test_delete_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::risk_payload("Delete Risk", "Compliance");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(&format!("/api/v1/risk/{}", risk_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_mitigate_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::risk_payload("Mitigate Risk", "Operational");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    let mitigate_body = serde_json::json!({
        "mitigation": "Implement backup supplier",
        "residual_probability": 1,
        "residual_impact": 2,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/risk/{}/mitigate", risk_id),
        &token,
        mitigate_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

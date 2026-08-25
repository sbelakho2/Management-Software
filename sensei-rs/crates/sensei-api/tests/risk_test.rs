//! End-to-end tests for Risk management endpoints.
//!
//! Tests CRUD operations and risk mitigation for the risk registry.
//! `/api/v1/risk/*` is an alias of the `/api/v1/ops/risks/*` handlers, so
//! the payload contract is the ops `Risk` entity.

use axum::http::StatusCode;
use serde_json::{json, Value};

mod common;

/// Build a valid risk payload (full ops `Risk` entity).
fn risk_payload(title: &str, category: &str) -> Value {
    json!({
        "risk_number": format!("RISK-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "title": title,
        "description": format!("Risk: {}", title),
        "category": category,
        "likelihood": "possible",
        "impact": "moderate",
        "risk_score": 6,
        "mitigation": "Implement controls",
        "contingency": "Backup plan",
        "status": "identified",
        "owner_id": uuid::Uuid::new_v4().to_string(),
    })
}

#[tokio::test]
async fn test_create_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = risk_payload("Supplier delay risk", "Supply Chain");
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

    let body = risk_payload("List Risk", "Operational");
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

    let body = risk_payload("Get Risk", "Financial");
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

    let body = risk_payload("Update Risk", "Strategic");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    // The PUT handler takes the full entity; echo it back with the title
    // changed.
    let mut update_body = created.clone();
    update_body["title"] = json!("Updated Risk Title");
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

    let body = risk_payload("Delete Risk", "Compliance");
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

    let body = risk_payload("Mitigate Risk", "Operational");
    let req = app.post_authenticated("/api/v1/risk", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    let req = app.post_authenticated(
        &format!("/api/v1/risk/{}/mitigate", risk_id),
        &token,
        json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "mitigated");
    assert!(json["mitigated_at"].is_string());
}

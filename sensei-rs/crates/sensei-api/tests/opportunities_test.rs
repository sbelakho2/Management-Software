//! End-to-end tests for Opportunity endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_opportunity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "New Customer Lead",
        "description": "Potential large customer",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 30,
        "expected_value": 50000.0,
        "currency": "USD",
        "expected_close_date": "2026-09-01T00:00:00Z",
        "assigned_to": null,
        "notes": "Follow up soon",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["title"], "New Customer Lead");
}

#[tokio::test]
async fn test_list_opportunities() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Opp A",
        "description": "A sales opportunity",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 50,
        "expected_value": 10000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/opportunities", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_opportunity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Get Opp",
        "description": "Get this opportunity",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 50,
        "expected_value": 25000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let opp_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/opportunities/{}", opp_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], opp_id);
}

#[tokio::test]
async fn test_update_opportunity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Update Opp",
        "description": "Update this opportunity",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 50,
        "expected_value": 10000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let opp_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({
        "title": "Updated Opp",
        "description": "Updated description",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 50,
        "expected_value": 10000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.put_authenticated(&format!("/api/v1/opportunities/{}", opp_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Opp");
}

#[tokio::test]
async fn test_delete_opportunity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Delete Opp",
        "description": "Delete this opportunity",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 50,
        "expected_value": 5000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let opp_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/opportunities/{}", opp_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_create_opportunity_invalid_stage() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Bad Stage",
        "description": "Unknown pipeline stage",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "NotAStage",
        "probability": 50,
        "expected_value": 10000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_create_opportunity_invalid_probability() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Bad Probability",
        "description": "Probability out of range",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 150,
        "expected_value": 10000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_update_opportunity_stage_transition() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "title": "Stage Opp",
        "description": "Move through pipeline",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Prospecting",
        "probability": 50,
        "expected_value": 20000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/opportunities", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let opp_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({
        "title": "Stage Opp",
        "description": "Move through pipeline",
        "customer_id": uuid::Uuid::new_v4().to_string(),
        "customer_name": "Acme Corp",
        "stage": "Negotiation",
        "probability": 80,
        "expected_value": 20000.0,
        "currency": "USD",
        "expected_close_date": null,
        "assigned_to": null,
        "notes": "",
    });
    let req = app.put_authenticated(&format!("/api/v1/opportunities/{}", opp_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["stage"], "Negotiation");
    assert_eq!(json["probability"], 80.0);
}

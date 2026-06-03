//! End-to-end tests for State Machine endpoints.
//!
//! Covers: CRUD definitions, create/list/get instances, transitions.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Definition CRUD ────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_state_machine() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Order Workflow", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Order Workflow");
}

#[tokio::test]
async fn test_list_state_machines() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("SM A", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/state-machines", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_state_machine() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Get SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/state-machines/{}", sm_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], sm_id);
}

#[tokio::test]
async fn test_get_state_machine_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/state-machines/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_state_machine() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Update SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated SM"});
    let req = app.put_authenticated(
        &format!("/api/v1/state-machines/{}", sm_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated SM");
}

#[tokio::test]
async fn test_delete_state_machine() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Delete SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/state-machines/{}", sm_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Instances & Transitions ────────────────────────────────────────────────

#[tokio::test]
async fn test_create_instance() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Instance SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();

    let instance_body = serde_json::json!({
        "entity_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        instance_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_instances() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("List Inst SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();

    let instance_body = serde_json::json!({"entity_id": uuid::Uuid::new_v4().to_string()});
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        instance_body,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_transition_instance() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Transition SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();

    let instance_body = serde_json::json!({"entity_id": uuid::Uuid::new_v4().to_string()});
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        instance_body,
    );
    let mut resp = app.send_request(req).await;
    let instance: Value = app.json_body(&mut resp).await;
    let inst_id = instance["id"].as_str().unwrap();

    let trans = serde_json::json!({"event": "activate"});
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
        &token,
        trans,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("transition_applied"));
}

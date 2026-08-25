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
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
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
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
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
    let req = app.put_authenticated(&format!("/api/v1/state-machines/{}", sm_id), &token, update);
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
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
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
    let resp = app.send_request(req).await;
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

// ── Validation ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_state_machine_invalid_initial_state() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let mut body = common::fixtures::state_machine_payload("Bad Initial", "Order");
    body["initial_state"] = serde_json::json!("Nonexistent");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_create_state_machine_self_loop_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let mut body = common::fixtures::state_machine_payload("Self Loop", "Order");
    body["transitions"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!({
            "from_state": "Draft",
            "to_state": "Draft",
            "event": "stay",
            "conditions": null,
            "on_transition": null,
        }));
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_create_state_machine_unknown_condition_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let mut body = common::fixtures::state_machine_payload("Bad Condition", "Order");
    body["transitions"].as_array_mut().unwrap()[0]["conditions"] =
        serde_json::json!({"type": "not_a_real_condition"});
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_create_state_machine_undefined_transition_state_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let mut body = common::fixtures::state_machine_payload("Bad Transition", "Order");
    body["transitions"].as_array_mut().unwrap()[0]["to_state"] = serde_json::json!("GhostState");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

// ── Instances: history, uniqueness, terminal, roles ────────────────────────

#[tokio::test]
async fn test_create_instance_records_initial_state() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("History SM", "Order");
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
    assert_eq!(instance["current_state"], "Draft");
    let history = instance["state_history"].as_array().unwrap();
    assert_eq!(history.len(), 1);
    assert_eq!(history[0]["event"], "initialized");
    assert_eq!(history[0]["from_state"], "Draft");
    assert_eq!(history[0]["to_state"], "Draft");
}

#[tokio::test]
async fn test_instance_entity_uniqueness() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Unique SM", "Order");
    let req = app.post_authenticated("/api/v1/state-machines", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap();
    let entity_id = uuid::Uuid::new_v4().to_string();

    let instance_body = serde_json::json!({"entity_id": entity_id});
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        instance_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // Second instance for the same entity → conflict.
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        serde_json::json!({"entity_id": entity_id}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_transition_from_terminal_state_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("Terminal SM", "Order");
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

    // Draft -> Active -> Complete
    for event in ["activate", "complete"] {
        let req = app.post_authenticated(
            &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
            &token,
            serde_json::json!({"event": event}),
        );
        let resp = app.send_request(req).await;
        assert_eq!(resp.status(), StatusCode::OK);
    }

    // Complete is terminal — further transitions are conflicts.
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
        &token,
        serde_json::json!({"event": "complete"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_transition_role_required_returns_403() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Definition whose target state requires "admin"…
    let mut body = common::fixtures::state_machine_payload("Role SM", "Order");
    body["states"].as_array_mut().unwrap()[1]["allowed_roles"] = serde_json::json!(["admin"]);
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

    // …and a plain user without admin tries to transition → 403.
    let _user_id = app
        .create_user_with_roles("plain@sensei.test", "TestPass123!", &["user"])
        .await;
    let login = serde_json::json!({
        "email": "plain@sensei.test",
        "password": "TestPass123!",
    });
    let req = app.post("/api/v1/auth/login", login);
    let mut resp = app.send_request(req).await;
    let login_body: Value = app.json_body(&mut resp).await;
    let plain_token = login_body["access_token"].as_str().unwrap().to_string();

    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
        &plain_token,
        serde_json::json!({"event": "activate"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
}

#[tokio::test]
async fn test_transition_role_required_condition() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Transition guarded by {"type":"role_required","role":"admin"}.
    let mut body = common::fixtures::state_machine_payload("Cond SM", "Order");
    body["transitions"].as_array_mut().unwrap()[0]["conditions"] =
        serde_json::json!({"type": "role_required", "role": "admin"});
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

    // Admin passes the condition.
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
        &token,
        serde_json::json!({"event": "activate"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // A plain user fails the condition (conflict).
    let _ = app
        .create_user_with_roles("plain2@sensei.test", "TestPass123!", &["user"])
        .await;
    let login = serde_json::json!({
        "email": "plain2@sensei.test",
        "password": "TestPass123!",
    });
    let req = app.post("/api/v1/auth/login", login);
    let mut resp = app.send_request(req).await;
    let login_body: Value = app.json_body(&mut resp).await;
    let plain_token = login_body["access_token"].as_str().unwrap().to_string();

    let instance_body = serde_json::json!({"entity_id": uuid::Uuid::new_v4().to_string()});
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        instance_body,
    );
    let mut resp = app.send_request(req).await;
    let instance2: Value = app.json_body(&mut resp).await;
    let inst_id2 = instance2["id"].as_str().unwrap();

    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id2),
        &plain_token,
        serde_json::json!({"event": "activate"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_transition_send_notification_hook() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let mut body = common::fixtures::state_machine_payload("Hook SM", "Order");
    body["transitions"].as_array_mut().unwrap()[0]["on_transition"] = serde_json::json!({
        "action": "send_notification",
        "target_user_id": app.admin_user_id.to_string(),
        "title": "State machine hook notification",
        "body": "Transition executed the send_notification hook",
    });
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

    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
        &token,
        serde_json::json!({"event": "activate"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // The hook must have created a real notification.
    let req = app.get_authenticated("/api/v1/notifications", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let notifications: Value = app.json_body(&mut resp).await;
    assert!(
        notifications
            .as_array()
            .unwrap()
            .iter()
            .any(|n| n["title"] == "State machine hook notification"),
        "send_notification hook must create an in-app notification"
    );
}

#[tokio::test]
async fn test_transition_history_records_old_state() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::state_machine_payload("History2 SM", "Order");
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

    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/instances/{}/transition", inst_id),
        &token,
        serde_json::json!({"event": "activate"}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let result: Value = app.json_body(&mut resp).await;

    // The transition record must carry the OLD state, not the new one.
    let instance = &result["instance"];
    assert_eq!(instance["current_state"], "Active");
    let history = instance["state_history"].as_array().unwrap();
    let last = history.last().unwrap();
    assert_eq!(last["from_state"], "Draft");
    assert_eq!(last["to_state"], "Active");
}

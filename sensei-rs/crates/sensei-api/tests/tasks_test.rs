//! End-to-end tests for Task management endpoints.
//!
//! Tests CRUD, status updates, assignments, and statistics.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_task() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Review quality reports", "high");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["title"], "Review quality reports");
}

#[tokio::test]
async fn test_list_tasks() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("List Test Task", "medium");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/tasks", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_task() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Get Task", "low");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/tasks/{}", task_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), task_id);
}

#[tokio::test]
async fn test_get_task_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/tasks/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_task() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Update Task", "medium");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({
        "title": "Updated Task Title",
        "priority": "High",
    });
    let req = app.put_authenticated(&format!("/api/v1/tasks/{}", task_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Task Title");
}

#[tokio::test]
async fn test_delete_task() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Delete Task", "low");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(&format!("/api/v1/tasks/{}", task_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_task_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Status Task", "high");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let status_body = serde_json::json!({ "status": "in_progress" });
    let req = app.put_authenticated(
        &format!("/api/v1/tasks/{}/status", task_id),
        &token,
        status_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "in_progress");
}

#[tokio::test]
async fn test_assign_task() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Assign Task", "medium");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let assign_body = serde_json::json!({
        "assignee_id": app.admin_user_id.to_string(),
    });
    let req = app.put_authenticated(
        &format!("/api/v1/tasks/{}/assign", task_id),
        &token,
        assign_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    // We just check the response is OK; assignment field depends on service impl
    assert!(json["id"].as_str().is_some());
}

#[tokio::test]
async fn test_get_task_stats() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create some tasks
    for i in 0..3 {
        let body = common::fixtures::task_payload(&format!("Stats Task {}", i), "medium");
        let req = app.post_authenticated("/api/v1/tasks", &token, body);
        app.send_request(req).await;
    }

    let req = app.get_authenticated("/api/v1/tasks/stats", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["total"].as_u64().unwrap_or(0) >= 3);
}

#[tokio::test]
async fn test_update_task_all_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Update All", "low");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let update = serde_json::json!({
        "title": "Updated Title",
        "description": "Updated description",
        "priority": "high",
        "category": "Engineering",
        "tags": ["a", "b"],
        "estimated_hours": 4.0,
    });
    let req = app.put_authenticated(&format!("/api/v1/tasks/{}", task_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Title");
    assert_eq!(json["description"], "Updated description");
    assert_eq!(json["priority"], "high");
    assert_eq!(json["category"], "Engineering");
    assert_eq!(json["estimated_hours"], 4.0);
    assert_eq!(json["tags"].as_array().unwrap().len(), 2);
}

/// State machine governing a task: Draft -> InProgress -> Completed.
fn task_state_machine_payload() -> Value {
    serde_json::json!({
        "name": "Task Workflow",
        "description": "State machine for tasks",
        "entity_type": "task",
        "initial_state": "open",
        "states": [
            {"name": "open", "label": "Open", "is_terminal": false, "allowed_roles": []},
            {"name": "in_progress", "label": "In Progress", "is_terminal": false, "allowed_roles": ["admin"]},
            {"name": "completed", "label": "Completed", "is_terminal": true, "allowed_roles": ["admin"]},
        ],
        "transitions": [
            {"from_state": "open", "to_state": "in_progress", "event": "to_in_progress", "conditions": null, "on_transition": null},
            {"from_state": "in_progress", "to_state": "completed", "event": "to_completed", "conditions": null, "on_transition": null},
        ],
        "is_active": true,
    })
}

#[tokio::test]
async fn test_sm_linked_task_status_role_enforcement() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // State machine definition.
    let req = app.post_authenticated("/api/v1/state-machines", &token, task_state_machine_payload());
    let mut resp = app.send_request(req).await;
    let sm: Value = app.json_body(&mut resp).await;
    let sm_id = sm["id"].as_str().unwrap().to_string();

    // Task to govern.
    let body = common::fixtures::task_payload("Governed Task", "medium");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let task: Value = app.json_body(&mut resp).await;
    let task_id = task["id"].as_str().unwrap().to_string();

    // Instance for the task entity.
    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        serde_json::json!({"entity_id": task_id}),
    );
    let mut resp = app.send_request(req).await;
    let instance: Value = app.json_body(&mut resp).await;
    let instance_id = instance["id"].as_str().unwrap().to_string();

    // Link the task to the instance (no dedicated endpoint; set directly).
    {
        let mut store = app.state.tasks.write().await;
        store.get_mut(&task_id.parse().unwrap()).unwrap().state_machine_instance_id =
            Some(instance_id.parse().unwrap());
    }

    // A plain user cannot move to in_progress (allowed_roles: ["admin"]).
    let _ = app
        .create_user_with_roles("worker@sensei.test", "TestPass123!", &["user"])
        .await;
    let login = serde_json::json!({
        "email": "worker@sensei.test",
        "password": "TestPass123!",
    });
    let req = app.post("/api/v1/auth/login", login);
    let mut resp = app.send_request(req).await;
    let login_body: Value = app.json_body(&mut resp).await;
    let worker_token = login_body["access_token"].as_str().unwrap().to_string();

    let req = app.put_authenticated(
        &format!("/api/v1/tasks/{}/status", task_id),
        &worker_token,
        serde_json::json!({"status": "in_progress"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);

    // Admin can perform the transition.
    let req = app.put_authenticated(
        &format!("/api/v1/tasks/{}/status", task_id),
        &token,
        serde_json::json!({"status": "in_progress"}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "in_progress");
}

#[tokio::test]
async fn test_sm_linked_task_hook_creates_notification() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Definition whose transition fires a send_notification hook.
    let mut sm = task_state_machine_payload();
    sm["transitions"].as_array_mut().unwrap()[0]["on_transition"] = serde_json::json!({
        "action": "send_notification",
        "target_user_id": app.admin_user_id.to_string(),
        "title": "Task workflow notification",
        "body": "Task moved via state machine",
    });
    let req = app.post_authenticated("/api/v1/state-machines", &token, sm);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let sm_id = created["id"].as_str().unwrap().to_string();

    let body = common::fixtures::task_payload("Hook Task", "medium");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let task: Value = app.json_body(&mut resp).await;
    let task_id = task["id"].as_str().unwrap().to_string();

    let req = app.post_authenticated(
        &format!("/api/v1/state-machines/{}/instances", sm_id),
        &token,
        serde_json::json!({"entity_id": task_id}),
    );
    let mut resp = app.send_request(req).await;
    let instance: Value = app.json_body(&mut resp).await;
    let instance_id = instance["id"].as_str().unwrap().to_string();
    {
        let mut store = app.state.tasks.write().await;
        store.get_mut(&task_id.parse().unwrap()).unwrap().state_machine_instance_id =
            Some(instance_id.parse().unwrap());
    }

    let req = app.put_authenticated(
        &format!("/api/v1/tasks/{}/status", task_id),
        &token,
        serde_json::json!({"status": "in_progress"}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let req = app.get_authenticated("/api/v1/notifications", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let notifications: Value = app.json_body(&mut resp).await;
    assert!(
        notifications
            .as_array()
            .unwrap()
            .iter()
            .any(|n| n["title"] == "Task workflow notification"),
        "send_notification hook must create a notification"
    );
}

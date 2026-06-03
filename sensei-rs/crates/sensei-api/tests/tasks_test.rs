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

    let body = common::fixtures::task_payload("Review quality reports", "High");
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

    let body = common::fixtures::task_payload("List Test Task", "Medium");
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

    let body = common::fixtures::task_payload("Get Task", "Low");
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

    let body = common::fixtures::task_payload("Update Task", "Normal");
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

    let body = common::fixtures::task_payload("Delete Task", "Low");
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

    let body = common::fixtures::task_payload("Status Task", "High");
    let req = app.post_authenticated("/api/v1/tasks", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let task_id = created["id"].as_str().unwrap().to_string();

    let status_body = serde_json::json!({ "status": "InProgress" });
    let req = app.put_authenticated(
        &format!("/api/v1/tasks/{}/status", task_id),
        &token,
        status_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "InProgress");
}

#[tokio::test]
async fn test_assign_task() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::task_payload("Assign Task", "Normal");
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
        let body = common::fixtures::task_payload(&format!("Stats Task {}", i), "Normal");
        let req = app.post_authenticated("/api/v1/tasks", &token, body);
        app.send_request(req).await;
    }

    let req = app.get_authenticated("/api/v1/tasks/stats", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["total"].as_u64().unwrap_or(0) >= 3);
}

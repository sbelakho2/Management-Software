//! End-to-end tests for A3 problem-solving endpoints.
//!
//! Tests CRUD operations and closing A3 reports.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::a3_payload("Reduce Defect Rate", "High defect rate on Line 3");
    let req = app.post_authenticated("/api/v1/a3", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["title"], "Reduce Defect Rate");
}

#[tokio::test]
async fn test_list_a3s() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create an A3
    let body = common::fixtures::a3_payload("List A3", "Test problem");
    let req = app.post_authenticated("/api/v1/a3", &token, body);
    app.send_request(req).await;

    // List
    let req = app.get_authenticated("/api/v1/a3", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::a3_payload("Get A3", "Retrieve test");
    let req = app.post_authenticated("/api/v1/a3", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let a3_id = created["id"].as_str().unwrap().to_string();

    // Get
    let req = app.get_authenticated(&format!("/api/v1/a3/{}", a3_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), a3_id);
}

#[tokio::test]
async fn test_get_a3_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(&format!("/api/v1/a3/{}", uuid::Uuid::new_v4()), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::a3_payload("Update A3", "Initial problem");
    let req = app.post_authenticated("/api/v1/a3", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let a3_id = created["id"].as_str().unwrap().to_string();

    // Update
    let update_body = serde_json::json!({
        "id": a3_id,
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "a3_number": format!("A3-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "title": "Updated A3 Title",
        "background": "Updated problem",
        "current_state": "Current state description",
        "goal": "Reduce defects by 50%",
        "root_cause_analysis": "Root cause analysis findings",
        "countermeasures": "Implement standardized work instructions",
        "check_plan": "Weekly audits for 4 weeks",
        "follow_up": "Monthly review with team",
        "status": "draft",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    });
    let req = app.put_authenticated(&format!("/api/v1/a3/{}", a3_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated A3 Title");
}

#[tokio::test]
async fn test_close_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::a3_payload("Close A3", "Problem to close");
    let req = app.post_authenticated("/api/v1/a3", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let a3_id = created["id"].as_str().unwrap().to_string();

    // Close
    let close_body = serde_json::json!({});
    let req = app.post_authenticated(
        &format!("/api/v1/a3/{}/close", a3_id),
        &token,
        close_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_delete_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create
    let body = common::fixtures::a3_payload("Delete A3", "Problem to delete");
    let req = app.post_authenticated("/api/v1/a3", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let a3_id = created["id"].as_str().unwrap().to_string();

    // Delete
    let req = app.delete_authenticated(&format!("/api/v1/a3/{}", a3_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // The deleted A3 is gone.
    let req = app.get_authenticated(&format!("/api/v1/a3/{}", a3_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

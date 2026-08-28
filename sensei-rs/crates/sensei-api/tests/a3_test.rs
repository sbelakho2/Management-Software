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
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
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
    assert!(!json["data"].as_array().unwrap_or(&vec![]).is_empty());
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

    // Update: the editable text fields only (identity/actor/status are
    // server-owned; the UpdateA3Request DTO ignores them).
    let update_body = serde_json::json!({
        "background": "Updated problem",
        "goal": "Reduce defects by 50%",
        "countermeasures": "Implement standardized work instructions",
    });
    let req = app.put_authenticated(&format!("/api/v1/a3/{}", a3_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["background"], "Updated problem");
    assert_eq!(json["goal"], "Reduce defects by 50%");
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

    // Record verification evidence first (closing is evidence-driven).
    let upd = app.put_authenticated(
        &format!("/api/v1/a3/{}", a3_id),
        &token,
        serde_json::json!({
            "verifications": [{
                "metric": "defect_rate",
                "before": 5.2,
                "after": 1.8,
                "observed_at": "2026-08-01T08:00:00Z"
            }]
        }),
    );
    let resp = app.send_request(upd).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // Close
    let close_body = serde_json::json!({});
    let req = app.post_authenticated(&format!("/api/v1/a3/{}/close", a3_id), &token, close_body);
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

    // A3 learning history is append-only: the draft is VOIDED, not
    // physically deleted, and remains retrievable.
    let req = app.delete_authenticated(&format!("/api/v1/a3/{}", a3_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // The voided A3 is still readable with status 'voided' (history kept).
    let req = app.get_authenticated(&format!("/api/v1/a3/{}", a3_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "voided");
}

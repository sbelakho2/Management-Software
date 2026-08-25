//! End-to-end tests for Escalation Policy endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_escalation_policy() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::escalation_policy_payload("Escalate Andon", "andon.raised");
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Escalate Andon");
}

#[tokio::test]
async fn test_list_escalation_policies() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::escalation_policy_payload("Policy A", "andon.raised");
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/escalation-policies", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_escalation_policy() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::escalation_policy_payload("Get Policy", "andon.raised");
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let policy_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(
        &format!("/api/v1/escalation-policies/{}", policy_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], policy_id);
}

#[tokio::test]
async fn test_update_escalation_policy() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::escalation_policy_payload("Update Policy", "andon.raised");
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let policy_id = created["id"].as_str().unwrap();

    let update = common::fixtures::escalation_policy_payload("Updated Policy", "andon.raised");
    let req = app.put_authenticated(
        &format!("/api/v1/escalation-policies/{}", policy_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Policy");
}

#[tokio::test]
async fn test_delete_escalation_policy() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::escalation_policy_payload("Delete Policy", "andon.raised");
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let policy_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(
        &format!("/api/v1/escalation-policies/{}", policy_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_create_policy_rejects_invalid_rules() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // A rule must escalate after a positive delay.
    let bad_delay = serde_json::json!({
        "name": "Bad Delay",
        "description": "Invalid escalation delay",
        "event_type": "andon.raised",
        "is_active": true,
        "rules": [
            {
                "id": uuid::Uuid::new_v4().to_string(),
                "priority": 1,
                "condition": "unacknowledged",
                "notify_user_ids": [],
                "notify_role": "supervisor",
                "escalate_after_seconds": 0,
            }
        ],
    });
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, bad_delay);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // A rule must name at least one notification target.
    let no_target = serde_json::json!({
        "name": "No Target",
        "description": "Rule without targets",
        "event_type": "andon.raised",
        "is_active": true,
        "rules": [
            {
                "id": uuid::Uuid::new_v4().to_string(),
                "priority": 1,
                "condition": "unacknowledged",
                "notify_user_ids": [],
                "notify_role": null,
                "escalate_after_seconds": 300,
            }
        ],
    });
    let req = app.post_authenticated("/api/v1/escalation-policies", &token, no_target);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

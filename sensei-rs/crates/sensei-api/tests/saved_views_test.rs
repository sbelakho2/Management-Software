//! End-to-end tests for Saved View endpoints.
//!
//! Covers: CRUD.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_saved_view() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("My View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["name"], "My View");
}

#[tokio::test]
async fn test_list_saved_views() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("View A", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/saved-views", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_saved_view() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("Get View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let view_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/saved-views/{}", view_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], view_id);
}

#[tokio::test]
async fn test_get_saved_view_tracks_usage() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("Usage View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let view_id = created["id"].as_str().unwrap();
    assert_eq!(created["view_count"], 0);
    assert!(created["last_used_at"].is_null());

    // Every GET must increment view_count and set last_used_at.
    for expected in 1..=3 {
        let req = app.get_authenticated(&format!("/api/v1/saved-views/{}", view_id), &token);
        let mut resp = app.send_request(req).await;
        assert_eq!(resp.status(), StatusCode::OK);
        let json: Value = app.json_body(&mut resp).await;
        assert_eq!(json["view_count"], expected);
        assert!(json["last_used_at"].is_string());
    }
}

#[tokio::test]
async fn test_share_saved_view_with_invalid_user() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("Share View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let view_id = created["id"].as_str().unwrap();

    // A user that does not exist in the tenant → Validation.
    let share = serde_json::json!({
        "user_ids": [uuid::Uuid::new_v4().to_string()],
        "visibility": "team",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/saved-views/{}/share", view_id),
        &token,
        share,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_share_saved_view_with_valid_user() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // A real user in the same tenant.
    let other_id = app
        .create_user_with_roles("other@sensei.test", "TestPass123!", &["user"])
        .await;

    let body = common::fixtures::saved_view_payload("Shared View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let view_id = created["id"].as_str().unwrap();

    let share = serde_json::json!({
        "user_ids": [other_id.to_string()],
        "visibility": "private",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/saved-views/{}/share", view_id),
        &token,
        share,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let shared: Vec<String> = serde_json::from_value(json["shared_with"].clone()).unwrap();
    assert_eq!(shared, vec![other_id.to_string()]);
}

#[tokio::test]
async fn test_create_saved_view_with_invalid_shared_user() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let mut body = common::fixtures::saved_view_payload("Bad Share", "work_orders");
    body["shared_with"] = serde_json::json!([uuid::Uuid::new_v4().to_string()]);
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_visibility_rbac_listing() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Private view created by admin.
    let body = common::fixtures::saved_view_payload("Private View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let _ = app.send_request(req).await;

    // A second user in the same tenant cannot list the admin's private view.
    let other_id = app
        .create_user_with_roles("same-tenant@sensei.test", "TestPass123!", &["user"])
        .await;
    let login = serde_json::json!({
        "email": "same-tenant@sensei.test",
        "password": "TestPass123!",
    });
    let req = app.post("/api/v1/auth/login", login);
    let mut resp = app.send_request(req).await;
    let login_body: Value = app.json_body(&mut resp).await;
    let token2 = login_body["access_token"].as_str().unwrap().to_string();

    let req = app.get_authenticated("/api/v1/saved-views", &token2);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let views = json["data"].as_array().unwrap();
    assert!(
        !views.iter().any(|v| v["name"] == "Private View"),
        "other users must not see private views"
    );

    // Re-fetch the private view id from the admin listing to share it.
    let req = app.get_authenticated("/api/v1/saved-views", &token);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let view = json["data"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["name"] == "Private View")
        .cloned()
        .unwrap();
    let view_id = view["id"].as_str().unwrap().to_string();

    let share = serde_json::json!({
        "user_ids": [other_id.to_string()],
        "visibility": "private",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/saved-views/{}/share", view_id),
        &token,
        share,
    );
    let _ = app.send_request(req).await;

    // Once shared with that user, it becomes visible.
    let req = app.get_authenticated("/api/v1/saved-views", &token2);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let views = json["data"].as_array().unwrap();
    assert!(views.iter().any(|v| v["name"] == "Private View"));
}

#[tokio::test]
async fn test_get_saved_view_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/saved-views/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_saved_view() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("Update View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let view_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated View"});
    let req = app.put_authenticated(&format!("/api/v1/saved-views/{}", view_id), &token, update);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated View");
}

#[tokio::test]
async fn test_delete_saved_view() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::saved_view_payload("Delete View", "work_orders");
    let req = app.post_authenticated("/api/v1/saved-views", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let view_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/saved-views/{}", view_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

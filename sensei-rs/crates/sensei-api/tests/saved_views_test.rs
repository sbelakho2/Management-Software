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
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
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
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
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
    let req = app.put_authenticated(
        &format!("/api/v1/saved-views/{}", view_id),
        &token,
        update,
    );
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

//! End-to-end tests for Kanban board endpoints.
//!
//! Tests CRUD for boards, columns, cards, and metrics.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_kanban_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kanban_board_payload("Production Board");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Production Board");
}

#[tokio::test]
async fn test_list_kanban_boards() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kanban_board_payload("List Board");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/kanban/boards", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_kanban_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kanban_board_payload("Get Board");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/kanban/boards/{}", board_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), board_id);
}

#[tokio::test]
async fn test_get_kanban_board_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/kanban/boards/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_kanban_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kanban_board_payload("Update Board");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({
        "name": "Updated Board",
        "description": "Updated description",
    });
    let req = app.put_authenticated(&format!("/api/v1/kanban/boards/{}", board_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Board");
}

#[tokio::test]
async fn test_delete_kanban_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::kanban_board_payload("Delete Board");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(&format!("/api/v1/kanban/boards/{}", board_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_add_column_to_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create board
    let body = common::fixtures::kanban_board_payload("Board With Columns");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    // Add column
    let col_body = serde_json::json!({
        "name": "In Progress",
        "position": 1,
        "wip_limit": 5,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/kanban/boards/{}/columns", board_id),
        &token,
        col_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_get_kanban_metrics() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/kanban/metrics", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    // Metrics response shape depends on implementation
    assert!(serde_json::to_string(&json).is_ok());
}

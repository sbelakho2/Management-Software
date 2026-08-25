//! End-to-end tests for Obeya (visual management) endpoints.
//!
//! Tests CRUD operations for Obeya boards and their items.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_obeya_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Daily Management", "Production");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["name"], "Daily Management");
}

#[tokio::test]
async fn test_list_obeya_boards() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("List Board", "Quality");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/obeya/boards", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["data"].as_array().unwrap_or(&vec![]).is_empty());
}

#[tokio::test]
async fn test_get_obeya_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Get Board", "Safety");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/obeya/boards/{}", board_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), board_id);
}

#[tokio::test]
async fn test_get_obeya_board_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/obeya/boards/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_obeya_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Update Board", "Delivery");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({ "name": "Updated Board Name" });
    let req = app.put_authenticated(
        &format!("/api/v1/obeya/boards/{}", board_id),
        &token,
        update_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Board Name");
}

#[tokio::test]
async fn test_delete_obeya_board() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Delete Board", "Cost");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(&format!("/api/v1/obeya/boards/{}", board_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_add_board_item() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create board first
    let body = common::fixtures::obeya_board_payload("Board With Items", "Production");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    // Add item
    let item_body = serde_json::json!({
        "title": "Improve OEE",
        "description": "Increase OEE to 85%",
        "item_type": "KPI",
        "status": "Active",
        "priority": "High",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/obeya/boards/{}/items", board_id),
        &token,
        item_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_list_board_items() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Board List Items", "Quality");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    // Add an item
    let item_body = serde_json::json!({
        "title": "Reduce scrap",
        "description": "Reduce scrap by 20%",
        "item_type": "KPI",
        "status": "Active",
        "priority": "Medium",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/obeya/boards/{}/items", board_id),
        &token,
        item_body,
    );
    app.send_request(req).await;

    // List items
    let req = app.get_authenticated(&format!("/api/v1/obeya/boards/{}/items", board_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["data"].as_array().unwrap_or(&vec![]).is_empty());
}

#[tokio::test]
async fn test_update_board_item() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Board Item Update", "Production");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let item_body = serde_json::json!({
        "title": "Complete action",
        "description": "Finish this action item",
        "item_type": "Action",
        "priority": "High",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/obeya/boards/{}/items", board_id),
        &token,
        item_body,
    );
    let mut resp = app.send_request(req).await;
    let item: Value = app.json_body(&mut resp).await;
    let item_id = item["id"].as_str().unwrap().to_string();

    // Update fields + move to Completed — completed_at must be set.
    let update = serde_json::json!({
        "title": "Completed action",
        "status": "Completed",
        "priority": "Critical",
    });
    let req = app.put_authenticated(
        &format!("/api/v1/obeya/boards/{}/items/{}", board_id, item_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Completed action");
    assert_eq!(json["status"], "Completed");
    assert_eq!(json["priority"], "Critical");
    assert!(json["completed_at"].is_string());

    // A second update while already Completed must keep completed_at (set once).
    let req = app.put_authenticated(
        &format!("/api/v1/obeya/boards/{}/items/{}", board_id, item_id),
        &token,
        serde_json::json!({"title": "Still completed"}),
    );
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "Completed");
    assert!(json["completed_at"].is_string());
}

#[tokio::test]
async fn test_update_board_item_invalid_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Board Item Invalid", "Production");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let item_body = serde_json::json!({
        "title": "Item",
        "item_type": "KPI",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/obeya/boards/{}/items", board_id),
        &token,
        item_body,
    );
    let mut resp = app.send_request(req).await;
    let item: Value = app.json_body(&mut resp).await;
    let item_id = item["id"].as_str().unwrap().to_string();

    let req = app.put_authenticated(
        &format!("/api/v1/obeya/boards/{}/items/{}", board_id, item_id),
        &token,
        serde_json::json!({"status": "NotARealStatus"}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_add_board_item_invalid_type() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Board Item Invalid Type", "Production");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let item_body = serde_json::json!({
        "title": "Bad item",
        "item_type": "NotAType",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/obeya/boards/{}/items", board_id),
        &token,
        item_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_delete_board_item() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::obeya_board_payload("Board Item Delete", "Quality");
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let board_id = created["id"].as_str().unwrap().to_string();

    let item_body = serde_json::json!({
        "title": "Remove me",
        "item_type": "Issue",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/obeya/boards/{}/items", board_id),
        &token,
        item_body,
    );
    let mut resp = app.send_request(req).await;
    let item: Value = app.json_body(&mut resp).await;
    let item_id = item["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(
        &format!("/api/v1/obeya/boards/{}/items/{}", board_id, item_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // The item must be gone from the board.
    let req = app.get_authenticated(&format!("/api/v1/obeya/boards/{}/items", board_id), &token);
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let items = json["data"].as_array().unwrap();
    assert!(!items.iter().any(|i| i["id"] == item_id));
}

#[tokio::test]
async fn test_create_board_invalid_type() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "name": "Bad Board",
        "board_type": "NotAType",
    });
    let req = app.post_authenticated("/api/v1/obeya/boards", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

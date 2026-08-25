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

/// Helper: create a board with two columns ("To Do" with a WIP limit and
/// "Done") and return (board_id, todo_column_id, done_column_id).
async fn board_with_columns(
    app: &common::TestApp,
    token: &str,
    name: &str,
    wip_limit: i32,
) -> (String, String, String) {
    let body = common::fixtures::kanban_board_payload(name);
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, body);
    let mut resp = app.send_request(req).await;
    let board: Value = app.json_body(&mut resp).await;
    let board_id = board["id"].as_str().unwrap().to_string();

    let todo_body = serde_json::json!({
        "name": "To Do",
        "position": 0,
        "wip_limit": wip_limit,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/kanban/boards/{}/columns", board_id),
        &token,
        todo_body,
    );
    let mut resp = app.send_request(req).await;
    let todo_col: Value = app.json_body(&mut resp).await;
    let todo_col_id = todo_col["id"].as_str().unwrap().to_string();

    let done_body = serde_json::json!({
        "name": "Done",
        "position": 1,
        "wip_limit": null,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/kanban/boards/{}/columns", board_id),
        &token,
        done_body,
    );
    let mut resp = app.send_request(req).await;
    let done_col: Value = app.json_body(&mut resp).await;
    let done_col_id = done_col["id"].as_str().unwrap().to_string();

    (board_id, todo_col_id, done_col_id)
}

/// Helper: add a card to a column and return its id.
async fn add_card_to_column(
    app: &common::TestApp,
    token: &str,
    column_id: &str,
    title: &str,
) -> Value {
    let card_body = serde_json::json!({
        "title": title,
        "description": "Test card",
        "priority": "medium",
        "labels": [],
        "position": 0,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/kanban/columns/{}/cards", column_id),
        &token,
        card_body,
    );
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(resp.status(), StatusCode::OK, "adding card failed: {json}");
    json
}

#[tokio::test]
async fn test_wip_limit_blocks_new_card() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let (_, todo_col, _) = board_with_columns(&app, &token, "WIP Board", 1).await;

    // First card fits within the WIP limit.
    add_card_to_column(&app, &token, &todo_col, "Card 1").await;

    // A second card in the same column exceeds the limit.
    let card_body = serde_json::json!({
        "title": "Card 2",
        "description": "Test card",
        "priority": "medium",
        "labels": [],
        "position": 1,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/kanban/columns/{}/cards", todo_col),
        &token,
        card_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_wip_limit_blocks_move_card() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Board 1 has a WIP-limited "To Do"; the card starts in "Done".
    let (_, todo_col, done_col) = board_with_columns(&app, &token, "Move WIP Board", 1).await;
    let card = add_card_to_column(&app, &token, &done_col, "Mover").await;
    let card_id = card["id"].as_str().unwrap().to_string();

    // Fill the WIP-limited column.
    add_card_to_column(&app, &token, &todo_col, "Filler").await;

    // Moving another card into the full column is rejected.
    let move_body = serde_json::json!({
        "target_column_id": todo_col,
        "position": 0,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/kanban/cards/{}/move", card_id),
        &token,
        move_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_update_card_in_same_column_allowed_at_wip_limit() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let (_, todo_col, _) = board_with_columns(&app, &token, "Edit WIP Board", 1).await;
    let card = add_card_to_column(&app, &token, &todo_col, "Editable").await;
    let card_id = card["id"].as_str().unwrap().to_string();

    // Updating the card in place (same column, at the WIP limit) must be
    // allowed: the card itself is excluded from the count.
    let update_body = serde_json::json!({
        "title": "Edited Title",
        "description": "Edited",
        "priority": "high",
        "labels": [],
        "position": 0,
        "column_id": todo_col,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/kanban/cards/{}", card_id),
        &token,
        update_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Edited Title");
}

#[tokio::test]
async fn test_move_card_sets_completed_at_and_metrics() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let (board_id, todo_col, done_col) =
        board_with_columns(&app, &token, "Cycle Board", 10).await;
    let card = add_card_to_column(&app, &token, &todo_col, "Cycler").await;
    let card_id = card["id"].as_str().unwrap().to_string();

    // Move into "Done": completed_at must be stamped.
    let move_body = serde_json::json!({
        "target_column_id": done_col,
        "position": 0,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/kanban/cards/{}/move", card_id),
        &token,
        move_body.clone(),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(
        json["completed_at"].is_string(),
        "completed_at should be set when moving into a done column: {json}"
    );

    // Moving out of "Done" clears completed_at.
    let move_back = serde_json::json!({
        "target_column_id": todo_col,
        "position": 0,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/kanban/cards/{}/move", card_id),
        &token,
        move_back,
    );
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["completed_at"].is_null());

    // Move back into Done for the metrics assertion.
    let req = app.put_authenticated(
        &format!("/api/v1/kanban/cards/{}/move", card_id),
        &token,
        move_body.clone(),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // Board-scoped metrics: cycle time is computed from
    // completed_at - created_at, and throughput counts the completed card.
    let req = app.get_authenticated(
        &format!("/api/v1/kanban/metrics?board_id={}", board_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let metrics: Value = app.json_body(&mut resp).await;
    assert_eq!(metrics["total_boards"], 1);
    assert!(metrics["cycle_time_hours"].as_f64().unwrap_or(-1.0) >= 0.0);
    assert_eq!(metrics["throughput_last_30_days"], 1);
}

#[tokio::test]
async fn test_kanban_metrics_board_id_filter() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create a board with a card and a second empty board.
    let (board_id, todo_col, _) = board_with_columns(&app, &token, "Filter Board", 10).await;
    add_card_to_column(&app, &token, &todo_col, "Only Card").await;

    let second = common::fixtures::kanban_board_payload("Empty Board");
    let req = app.post_authenticated("/api/v1/kanban/boards", &token, second);
    let _ = app.send_request(req).await;

    // Metrics scoped to the first board only see its card.
    let req = app.get_authenticated(
        &format!("/api/v1/kanban/metrics?board_id={}", board_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    let metrics: Value = app.json_body(&mut resp).await;
    assert_eq!(metrics["total_boards"], 1);
    assert_eq!(metrics["total_cards"], 1);

    // Unscoped metrics see both boards.
    let req = app.get_authenticated("/api/v1/kanban/metrics", &token);
    let mut resp = app.send_request(req).await;
    let metrics: Value = app.json_body(&mut resp).await;
    assert_eq!(metrics["total_boards"], 2);
    assert_eq!(metrics["total_cards"], 1);
}

#[tokio::test]
async fn test_kanban_publishes_card_created_event() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Subscribe to the in-memory bus before the mutation.
    let received = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
    let received_clone = std::sync::Arc::clone(&received);
    app.state
        .event_bus
        .subscribe(
            "sensei.>",
            std::sync::Arc::new(move |envelope| {
                received_clone
                    .lock()
                    .unwrap()
                    .push(envelope.event_type.clone());
                Ok(())
            }),
        )
        .await
        .expect("subscribe should work");

    let (_, todo_col, _) = board_with_columns(&app, &token, "Event Board", 10).await;
    add_card_to_column(&app, &token, &todo_col, "Event Card").await;

    let events = received.lock().unwrap().clone();
    assert!(
        events.iter().any(|e| e == "operations.kanban.created"),
        "expected operations.kanban.created event, got {events:?}"
    );
}

#[tokio::test]
async fn test_move_card_missing_column_is_clear_error() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let (_, todo_col, _) = board_with_columns(&app, &token, "Missing Column Board", 10).await;
    let card = add_card_to_column(&app, &token, &todo_col, "Lonely").await;
    let card_id = card["id"].as_str().unwrap().to_string();

    // Moving to a column that does not exist must not be reported as a
    // generic card-not-found: it names the missing column.
    let move_body = serde_json::json!({
        "target_column_id": uuid::Uuid::new_v4().to_string(),
        "position": 0,
    });
    let req = app.put_authenticated(
        &format!("/api/v1/kanban/cards/{}/move", card_id),
        &token,
        move_body,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    let text = app.response_text(&mut resp).await;
    assert!(
        text.contains("Target column"),
        "error should name the missing column, got: {text}"
    );
}

//! End-to-end tests for chatbot route handlers.
//!
//! Covers:
//! - POST /api/v1/chat (single-turn chat)
//!
//! Note: The SSE streaming endpoint (POST /api/v1/chat/stream) is difficult
//! to test via tower::ServiceExt::oneshot because it returns an SSE stream
//! that consumes the connection. It is tested at the service layer.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Chat ──────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_chat_basic() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "message": "Hello, how can I help?",
    });

    let req = app.post_authenticated("/api/v1/chat", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["response"].is_string());
    assert!(json["conversation_id"].is_string());
    // response should not be empty
    assert!(!json["response"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_chat_with_conversation() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // First message
    let body1 = serde_json::json!({
        "message": "First message",
    });
    let req1 = app.post_authenticated("/api/v1/chat", &token, body1);
    let mut resp1 = app.send_request(req1).await;
    assert_eq!(resp1.status(), StatusCode::OK);
    let json1: Value = app.json_body(&mut resp1).await;
    let conv_id = json1["conversation_id"].as_str().unwrap().to_string();

    // Second message with same conversation_id
    let body2 = serde_json::json!({
        "message": "Second message in same conversation",
        "conversation_id": conv_id,
    });
    let req2 = app.post_authenticated("/api/v1/chat", &token, body2);
    let mut resp2 = app.send_request(req2).await;
    assert_eq!(resp2.status(), StatusCode::OK);
    let json2: Value = app.json_body(&mut resp2).await;
    assert!(json2["response"].is_string());
    assert_eq!(json2["conversation_id"], conv_id);
}

#[tokio::test]
async fn test_chat_unauthenticated() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({ "message": "test" });
    let req = app.post("/api/v1/chat", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_chat_empty_message() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({ "message": "" });
    let req = app.post_authenticated("/api/v1/chat", &token, body);
    let mut resp = app.send_request(req).await;
    // In-memory chatbot handles empty messages gracefully
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["response"].is_string());
}

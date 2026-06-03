//! End-to-end tests for WebSocket and SSE route handlers.
//!
//! Covers:
//! - GET /api/v1/ws?token=... (WebSocket upgrade)
//! - GET /api/v1/sse?token=... (SSE stream)
//! - Invalid token returns 401
//!
//! Note: WebSocket upgrade and SSE streaming are connection-oriented and
//! cannot be tested via tower::ServiceExt::oneshot. These tests verify
//! that auth rejection works properly for invalid tokens.

use axum::http::StatusCode;

mod common;

// ── WebSocket Auth ────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_ws_invalid_token_returns_401() {
    let app = common::TestApp::new().await;

    // WebSocket endpoint uses ?token= query parameter for auth
    let req = app.get("/api/v1/ws?token=invalid-token");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_ws_missing_token_returns_422_or_400() {
    let app = common::TestApp::new().await;

    // Missing token query parameter
    let req = app.get("/api/v1/ws");
    let resp = app.send_request(req).await;
    // Axum returns 422 Unprocessable Entity for missing query params
    let status = resp.status();
    assert!(
        status == StatusCode::UNPROCESSABLE_ENTITY || status == StatusCode::BAD_REQUEST,
        "Expected 422 or 400, got {}",
        status
    );
}

// ── SSE Auth ──────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_sse_invalid_token_returns_401() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/sse?token=invalid-token");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_sse_missing_token_returns_422_or_400() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/sse");
    let resp = app.send_request(req).await;
    let status = resp.status();
    assert!(
        status == StatusCode::UNPROCESSABLE_ENTITY || status == StatusCode::BAD_REQUEST,
        "Expected 422 or 400, got {}",
        status
    );
}

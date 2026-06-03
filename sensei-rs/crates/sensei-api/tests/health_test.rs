//! End-to-end tests for health check endpoints.
//!
//! Tests liveness, readiness, and detailed health probes.
//! These are public (unauthenticated) endpoints.

use axum::http::StatusCode;

mod common;

#[tokio::test]
async fn test_liveness_probe() {
    let app = common::TestApp::new().await;

    let req = app.get("/health/live");
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(body["status"], "alive");
}

#[tokio::test]
async fn test_readiness_probe() {
    let app = common::TestApp::new().await;

    let req = app.get("/health/ready");
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(body["status"], "ready");
    assert!(body["uptime_seconds"].as_u64().is_some());
    assert!(!body["version"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_detailed_health() {
    let app = common::TestApp::new().await;

    let req = app.get("/health/detailed");
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(body["status"], "ok");
    assert_eq!(body["service"], "sensei-api");
}

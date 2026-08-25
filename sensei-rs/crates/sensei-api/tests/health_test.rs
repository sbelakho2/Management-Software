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

    // The detailed probe reports real subsystem state: the in-memory bus
    // is connected, active sessions is a number, and memory/cpu are either
    // real numbers or null (platform-dependent).
    let checks = &body["checks"];
    assert_eq!(checks["event_bus_connected"], true);
    assert!(checks["active_sessions"].as_u64().is_some());
    assert!(checks["memory_usage_mb"].is_null() || checks["memory_usage_mb"].as_f64().is_some());
    assert!(checks["cpu_usage_pct"].is_null() || checks["cpu_usage_pct"].as_f64().is_some());
}

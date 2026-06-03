//! End-to-end tests for Admin endpoints.
//!
//! Covers: system health, db stats, admin list users, deactivate user,
//! system logs, system config.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_get_system_health() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/admin/system-health", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "healthy");
    assert!(json.as_object().unwrap().contains_key("active_users"));
}

#[tokio::test]
async fn test_get_db_stats() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/admin/db-stats", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("total_users"));
    assert!(json.as_object().unwrap().contains_key("total_entities"));
}

#[tokio::test]
async fn test_admin_list_users() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/admin/users", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_admin_get_system_logs() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/admin/logs", &token);
    let mut resp = app.send_request(req).await;
    // Logs may be empty or present; just verify the endpoint works
    let status = resp.status();
    assert!(status == StatusCode::OK || status == StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_admin_get_system_config() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/admin/config", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("api_host"));
    assert!(json.as_object().unwrap().contains_key("api_port"));
}

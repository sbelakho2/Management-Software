//! End-to-end tests for Smart Ingestion route handlers.
//!
//! Covers:
//! - POST /api/v1/smart-ingestion/upload (multipart)
//! - GET /api/v1/smart-ingestion/{id}/status
//! - GET /api/v1/smart-ingestion/history

use axum::{
    body::Body,
    http::Request,
};
use axum::http::StatusCode;
use serde_json::Value;
use std::time::Duration;
use uuid::Uuid;

mod common;

/// Build a multipart upload request with a single "file" part.
fn multipart_upload(
    app: &common::TestApp,
    token: &str,
    file_name: &str,
    content_type: &str,
    content: &[u8],
) -> Request<Body> {
    let boundary = "kilo-test-boundary";
    let mut body = Vec::new();
    body.extend_from_slice(
        format!(
            "--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file_name}\"\r\nContent-Type: {content_type}\r\n\r\n"
        )
        .as_bytes(),
    );
    body.extend_from_slice(content);
    body.extend_from_slice(format!("\r\n--{boundary}--\r\n").as_bytes());

    Request::builder()
        .uri("/api/v1/smart-ingestion/upload")
        .method("POST")
        .header("Content-Type", format!("multipart/form-data; boundary={boundary}"))
        .header("Authorization", format!("Bearer {token}"))
        .body(Body::from(body))
        .expect("Failed to build multipart request")
}

/// Poll the ingestion job until it completes (or the deadline passes).
async fn wait_for_completion(
    app: &common::TestApp,
    token: &str,
    job_id: &str,
) -> Value {
    let deadline = std::time::Instant::now() + Duration::from_secs(10);
    loop {
        let req = app.get_authenticated(
            &format!("/api/v1/smart-ingestion/{}/status", job_id),
            token,
        );
        let mut resp = app.send_request(req).await;
        assert_eq!(resp.status(), StatusCode::OK);
        let job: Value = app.json_body(&mut resp).await;
        let status = job["status"].as_str().unwrap_or("");
        if status == "Completed" || status == "Failed" {
            return job;
        }
        assert!(
            std::time::Instant::now() < deadline,
            "ingestion job did not finish in time (status={status})"
        );
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
}

// ── Ingestion Status ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_upload_and_process_document() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = multipart_upload(&app, &token, "notes.txt", "text/plain", b"hello world");
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let job_id = json["id"].as_str().unwrap();
    assert_eq!(json["status"], "processing");

    // The background task must complete the job with real metadata.
    let job = wait_for_completion(&app, &token, job_id).await;
    assert_eq!(job["status"], "Completed");
    assert_eq!(job["file_size"], 11);
    assert_eq!(job["extracted_data"]["text_char_count"], 11);
    let sha = job["extracted_data"]["sha256"].as_str().unwrap();
    assert_eq!(sha.len(), 64, "sha256 must be a real 64-char hex digest");
    assert!(job["completed_at"].is_string());
}

#[tokio::test]
async fn test_upload_rejects_unsupported_content_type() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = multipart_upload(
        &app,
        &token,
        "virus.exe",
        "application/x-msdownload",
        b"MZ...",
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_upload_sanitizes_file_name() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Path traversal attempt in the file name.
    let req = multipart_upload(
        &app,
        &token,
        "../../etc/passwd.txt",
        "text/plain",
        b"data",
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let job_id = json["id"].as_str().unwrap();
    let job = wait_for_completion(&app, &token, job_id).await;
    let name = job["file_name"].as_str().unwrap();
    assert!(!name.contains('/') && !name.contains(".."), "file name must be sanitized");
}

#[tokio::test]
async fn test_get_ingestion_status_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let id = Uuid::nil().to_string();
    let req = app.get_authenticated(
        &format!("/api/v1/smart-ingestion/{}/status", id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_list_ingestion_history() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/smart-ingestion/history", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
    // Should have data array and pagination fields
    assert!(json.get("data").is_some() || json.get("items").is_some() || json.is_array());
}

#[tokio::test]
async fn test_list_ingestion_history_after_upload() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = multipart_upload(&app, &token, "history.txt", "text/plain", b"history data");
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let job_id = json["id"].as_str().unwrap();
    let _ = wait_for_completion(&app, &token, job_id).await;

    let req = app.get_authenticated("/api/v1/smart-ingestion/history?status=completed", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let jobs = json["data"].as_array().unwrap();
    assert!(jobs.iter().any(|j| j["id"] == job_id));
}

#[tokio::test]
async fn test_smart_ingestion_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/smart-ingestion/history");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

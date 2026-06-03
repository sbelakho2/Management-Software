//! End-to-end tests for the export route handler.
//!
//! Covers:
//! - GET /api/v1/export/{entity_type}?format=...&tenant_id=...
//! - Supported formats: pdf, csv, xlsx
//! - Unsupported format returns validation error
//! - Unauthenticated access

use axum::http::StatusCode;
use uuid::Uuid;

mod common;

// ── Export NCR ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_export_ncr_csv() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/ncr?format=csv&tenant_id={}", tenant_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("csv"));
}

#[tokio::test]
async fn test_export_capa_pdf() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/capa?format=pdf&tenant_id={}", tenant_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("pdf"));
}

#[tokio::test]
async fn test_export_audit_xlsx() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/audit?format=xlsx&tenant_id={}", tenant_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("spreadsheetml"));
}

#[tokio::test]
async fn test_export_work_order_csv() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/work-order?format=csv&tenant_id={}", tenant_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_export_invalid_format() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/ncr?format=doc&tenant_id={}", tenant_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_export_unknown_entity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/unknown-entity?format=csv&tenant_id={}", tenant_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_export_unauthenticated() {
    let app = common::TestApp::new().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get(&format!("/api/v1/export/ncr?format=csv&tenant_id={}", tenant_id));
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

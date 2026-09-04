//! End-to-end tests for the export route handler.
//!
//! Covers:
//! - GET /api/v1/export/{entity_type}?format=...&tenant_id=...
//! - Supported formats: pdf, csv, xlsx
//! - Unsupported format returns validation error
//! - Unauthenticated access

use axum::http::StatusCode;
use serde_json::Value;
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
    let resp = app.send_request(req).await;
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
    let resp = app.send_request(req).await;
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
    let resp = app.send_request(req).await;
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
        &format!(
            "/api/v1/export/work-order?format=csv&tenant_id={}",
            tenant_id
        ),
        &token,
    );
    let resp = app.send_request(req).await;
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
        &format!(
            "/api/v1/export/unknown-entity?format=csv&tenant_id={}",
            tenant_id
        ),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_export_unauthenticated() {
    let app = common::TestApp::new().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get(&format!(
        "/api/v1/export/ncr?format=csv&tenant_id={}",
        tenant_id
    ));
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_export_ignores_query_tenant_id_and_uses_token_tenant() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create an NCR in the admin's tenant (inline payload: the fixture's
    // "Major" severity is not a valid NcSeverity variant).
    let ncr_body = serde_json::json!({
        "title": "Exportable NCR",
        "description": "An exportable NCR",
        "nc_type": "Product",
        "severity": "High",
        "is_recurrence": false,
    });
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, ncr_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let ncr: Value = app.json_body(&mut resp).await;
    let ncr_id = ncr["id"].as_str().unwrap().to_string();

    // The export handler must ignore the client-supplied tenant_id and use
    // the authenticated user's tenant: an arbitrary foreign tenant_id must
    // NOT change what data is returned (no cross-tenant leak).
    let foreign_tenant = Uuid::new_v4();
    let req = app.get_authenticated(
        &format!(
            "/api/v1/export/ncr?id={}&format=csv&tenant_id={}",
            ncr_id, foreign_tenant
        ),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let text = app.response_text(&mut resp).await;
    assert!(
        text.contains("Exportable NCR"),
        "export should return the token tenant's data, got: {text}"
    );
}

#[tokio::test]
async fn test_export_foreign_tenant_cannot_read_ncr_by_id() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Admin creates an NCR in their tenant (inline payload with a valid
    // NcSeverity variant).
    let ncr_body = serde_json::json!({
        "title": "Private NCR",
        "description": "A private NCR",
        "nc_type": "Product",
        "severity": "High",
        "is_recurrence": false,
    });
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, ncr_body);
    let mut resp = app.send_request(req).await;
    let ncr: Value = app.json_body(&mut resp).await;
    let ncr_id = ncr["id"].as_str().unwrap().to_string();

    // A user in a different tenant (registration provisions a fresh tenant)
    // must not be able to export the admin's NCR by id.
    let reg_body = serde_json::json!({
        "email": "outsider@sensei.test",
        "password": "StrongPass123!",
        "name": "Outsider",
    });
    let req = app.post("/api/v1/auth/register", reg_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let reg: Value = app.json_body(&mut resp).await;
    let outsider_token = reg["access_token"].as_str().unwrap().to_string();

    let req = app.get_authenticated(
        &format!("/api/v1/export/ncr?id={}&format=csv", ncr_id),
        &outsider_token,
    );
    let resp = app.send_request(req).await;
    assert!(
        matches!(resp.status(), StatusCode::NOT_FOUND | StatusCode::FORBIDDEN),
        "foreign tenant must not see another tenant's exported entity (404 or 403)"
    );
}

#[tokio::test]
async fn test_export_invalid_date_filter_is_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/export/ncr?format=csv&date_from=not-a-date", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

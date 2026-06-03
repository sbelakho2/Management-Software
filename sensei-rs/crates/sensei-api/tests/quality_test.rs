//! End-to-end tests for Quality management endpoints.
//!
//! Tests NCR, CAPA, audit, inspection, and other quality system endpoints.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── NCR Tests ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_ncr() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::ncr_payload("Surface defect on part A");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_ncrs() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::ncr_payload("List NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/quality/ncrs", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_ncr() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::ncr_payload("Get NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let ncr_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/quality/ncrs/{}", ncr_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), ncr_id);
}

#[tokio::test]
async fn test_update_ncr() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::ncr_payload("Update NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let ncr_id = created["id"].as_str().unwrap().to_string();

    let update_body = serde_json::json!({ "description": "Updated NCR description" });
    let req = app.put_authenticated(&format!("/api/v1/quality/ncrs/{}", ncr_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_delete_ncr() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::ncr_payload("Delete NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let ncr_id = created["id"].as_str().unwrap().to_string();

    let req = app.delete_authenticated(&format!("/api/v1/quality/ncrs/{}", ncr_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_investigate_ncr() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::ncr_payload("Investigate NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let ncr_id = created["id"].as_str().unwrap().to_string();

    let invest_body = serde_json::json!({
        "root_cause": "Material contamination",
        "investigation_notes": "Found impurity in raw material",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/quality/ncrs/{}/investigate", ncr_id),
        &token,
        invest_body,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── CAPA Tests ───────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_capa() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::capa_payload("Process FMEA CAPA");
    let req = app.post_authenticated("/api/v1/quality/capas", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_capas() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::capa_payload("List CAPA");
    let req = app.post_authenticated("/api/v1/quality/capas", &token, body);
    app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/quality/capas", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().unwrap_or(&vec![]).len() >= 1);
}

#[tokio::test]
async fn test_get_capa() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::capa_payload("Get CAPA");
    let req = app.post_authenticated("/api/v1/quality/capas", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let capa_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/quality/capas/{}", capa_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), capa_id);
}

#[tokio::test]
async fn test_get_ncr_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated(
        &format!("/api/v1/quality/ncrs/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

// ── Audit Tests ──────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_quality_audit() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "title": "ISO 9001 Internal Audit",
        "audit_type": "Internal",
        "scope": "Production area",
        "auditor": "John Doe",
        "status": "Planned",
    });
    let req = app.post_authenticated("/api/v1/quality/audits", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_quality_audits() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/quality/audits", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some());
}

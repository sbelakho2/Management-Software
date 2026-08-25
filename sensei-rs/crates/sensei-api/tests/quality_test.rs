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

    // The PUT handler takes the full NonConformance entity, not a partial
    // body: echo the created record back with the description changed.
    let mut update_body = created.clone();
    update_body["description"] = serde_json::json!("Updated NCR description");
    let req = app.put_authenticated(&format!("/api/v1/quality/ncrs/{}", ncr_id), &token, update_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["description"], "Updated NCR description");
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
        "id": uuid::Uuid::new_v4().to_string(),
        "capa_id": uuid::Uuid::new_v4().to_string(),
        "description": "Material contamination found in raw material",
        "root_cause_type": "Material",
        "analysis_method": "5 Whys",
        "contributors": ["Supplier"],
        "evidence": ["Lab report"],
        "verified_by": null,
        "verified_at": null,
        "created_at": "2026-01-01T00:00:00Z",
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
        "id": uuid::Uuid::new_v4().to_string(),
        "audit_number": "AUD-001",
        "audit_type": "Internal",
        "status": "Planned",
        "title": "ISO 9001 Internal Audit",
        "scope": "Production area",
        "area": "Production",
        "auditor": "John Doe",
        "checklist_items": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/quality/audits", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK, "audit create failed: {}", app.response_text(&mut resp).await);

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

// ── Getters for list-only entities ─────────────────────────────────────────

#[tokio::test]
async fn test_get_scar_roundtrip_and_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "scar_number": "SCAR-001",
        "supplier_id": uuid::Uuid::new_v4().to_string(),
        "title": "Supplier defect",
        "description": "Non-conforming batch received",
        "status": "Open",
        "severity": "Major",
    });
    let req = app.post_authenticated("/api/v1/quality/scars", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let created: Value = app.json_body(&mut resp).await;
    let scar_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/quality/scars/{}", scar_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), scar_id);
    assert_eq!(json["title"], "Supplier defect");

    // Unknown ID → 404
    let req = app.get_authenticated(
        &format!("/api/v1/quality/scars/{}", uuid::Uuid::new_v4()),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_get_gauge_roundtrip() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "gauge_number": "GAUGE-001",
        "name": "Digital Caliper",
        "gauge_type": "caliper",
        "status": "UnderCalibration",
        "calibration_frequency_days": 365,
    });
    let req = app.post_authenticated("/api/v1/quality/gauges", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let created: Value = app.json_body(&mut resp).await;
    let gauge_id = created["id"].as_str().unwrap().to_string();

    let req = app.get_authenticated(&format!("/api/v1/quality/gauges/{}", gauge_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"].as_str().unwrap(), gauge_id);
    assert_eq!(json["name"], "Digital Caliper");
}

#[tokio::test]
async fn test_list_only_getters_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let id = uuid::Uuid::new_v4().to_string();

    for path in [
        "documents",
        "first-article-inspections",
        "self-inspections",
        "msa-studies",
        "process-capability-studies",
        "control-plans",
        "pfmeas",
        "complaints",
        "eight-d-reports",
        "management-reviews",
    ] {
        let req = app.get_authenticated(
            &format!("/api/v1/quality/{}/{}", path, id),
            &token,
        );
        let resp = app.send_request(req).await;
        assert_eq!(
            resp.status(),
            StatusCode::NOT_FOUND,
            "GET /api/v1/quality/{path}/{id} should 404 for an unknown id"
        );
    }
}

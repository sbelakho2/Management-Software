//! End-to-end tests for LSW (Layer Standard Work) endpoints.
//!
//! Covers: create, list, get, update, delete standard; perform audit,
//! list audits, get audit, dashboard.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Standard CRUD ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_lsw_standard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Daily Checklist", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["title"], "Daily Checklist");
}

#[tokio::test]
async fn test_list_lsw_standards() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Std A", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/lsw/standards", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_lsw_standard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Get Std", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let std_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/lsw/standards/{}", std_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], std_id);
}

#[tokio::test]
async fn test_get_lsw_standard_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/lsw/standards/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_lsw_standard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Update Std", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let std_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"title": "Updated Standard"});
    let req = app.put_authenticated(
        &format!("/api/v1/lsw/standards/{}", std_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Standard");
}

#[tokio::test]
async fn test_delete_lsw_standard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Delete Std", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let std_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(&format!("/api/v1/lsw/standards/{}", std_id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Audits & Dashboard ─────────────────────────────────────────────────────

#[tokio::test]
async fn test_perform_audit() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Audit Std", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let std_id = created["id"].as_str().unwrap();

    let audit = serde_json::json!({
        "results": [
            {"item_id": uuid::Uuid::new_v4(), "passed": true, "notes": "OK"},
        ],
        "notes": "Audit completed",
    });
    let req = app.post_authenticated(
        &format!("/api/v1/lsw/standards/{}/audits", std_id),
        &token,
        audit,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_list_audits() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("List Audit Std", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let std_id = created["id"].as_str().unwrap();

    let audit = serde_json::json!({
        "results": [{"item_id": uuid::Uuid::new_v4(), "passed": true, "notes": ""}],
    });
    let req = app.post_authenticated(
        &format!("/api/v1/lsw/standards/{}/audits", std_id),
        &token,
        audit,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/lsw/standards/{}/audits", std_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_lsw_dashboard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/lsw/dashboard", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("total_standards"));
}

#[tokio::test]
async fn test_lsw_dashboard_reports_zero_without_audits() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // A dashboard over a tenant with no audits must report 0.0 compliance
    // (no evidence) instead of a fabricated 100%.
    let req = app.get_authenticated("/api/v1/lsw/dashboard", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total_audits"], 0);
    assert_eq!(json["overall_compliance_rate"], 0.0);
}

#[tokio::test]
async fn test_perform_audit_with_empty_results_reports_zero_compliance() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::lsw_standard_payload("Empty Audit Std", "Assembly");
    let req = app.post_authenticated("/api/v1/lsw/standards", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let std_id = created["id"].as_str().unwrap().to_string();

    // An audit with no results carries no compliance evidence.
    let audit = serde_json::json!({ "results": [] });
    let req = app.post_authenticated(
        &format!("/api/v1/lsw/standards/{}/audits", std_id),
        &token,
        audit,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["compliance_rate"], 0.0);
}

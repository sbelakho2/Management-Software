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
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
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
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
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
    let req = app.put_authenticated(&format!("/api/v1/lsw/standards/{}", std_id), &token, update);
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

    // Every REQUIRED checklist item must be observed: build the results
    // from the standard's actual checklist (a random item id is rejected).
    let req = app.get_authenticated(&format!("/api/v1/lsw/standards/{}", std_id), &token);
    let mut resp = app.send_request(req).await;
    let std: Value = app.json_body(&mut resp).await;
    let items = std["checklist_items"].as_array().unwrap();
    let results: Vec<Value> = items
        .iter()
        .map(|i| {
            serde_json::json!({
                "item_id": i["id"],
                "passed": true,
                "notes": "OK",
            })
        })
        .collect();

    // Audits execute a SCHEDULED occurrence (server-owned lifecycle).
    let occ_req = app.post_authenticated(
        &format!("/api/v1/lsw/standards/{}/occurrences", std_id),
        &token,
        serde_json::json!({
            "due_at": "2026-09-01T08:00:00Z",
            "assigned_leader": uuid::Uuid::new_v4().to_string(),
        }),
    );
    let mut occ_resp = app.send_request(occ_req).await;
    assert_eq!(occ_resp.status(), StatusCode::OK);
    let occ: Value = app.json_body(&mut occ_resp).await;
    let occurrence_id = occ["id"].as_str().unwrap().to_string();

    let audit = serde_json::json!({
        "results": results,
        "notes": "Audit completed",
        "occurrence_id": occurrence_id,
    });
    let req = app.post_authenticated(
        &format!("/api/v1/lsw/standards/{}/audits", std_id),
        &token,
        audit,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    // Compliance is computed against the FULL checklist.
    assert_eq!(json["compliance_rate"], 100.0);
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

    let req = app.get_authenticated(&format!("/api/v1/lsw/standards/{}/audits", std_id), &token);
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

    // An audit with no results is INVALID: the checklist must be completed
    // (every required item observed) — an empty submission cannot claim
    // anything, including zero compliance.
    let audit = serde_json::json!({ "results": [] });
    let req = app.post_authenticated(
        &format!("/api/v1/lsw/standards/{}/audits", std_id),
        &token,
        audit,
    );
    let resp = app.send_request(req).await;
    // Empty submissions are rejected: every required checklist item must be
    // observed, so a client can never fake compliance.
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

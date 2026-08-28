//! End-to-end tests for Operations (Ops) endpoints.
//!
//! Covers: Andon, Projects, A3s, Risks CRUD under /api/v1/ops/.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_ops_list_andons() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/andons", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_raise_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "andon_number": "ANDON-001",
        "work_center_id": uuid::Uuid::new_v4().to_string(),
        "issue_type": "quality",
        "severity": "high",
        "description": "Test andon via ops",
        "status": "active",
        "raised_by": uuid::Uuid::new_v4().to_string(),
        "acknowledged_by": null,
        "resolved_by": null,
        "resolution": null,
        "response_time_seconds": null,
        "resolution_time_seconds": null,
        "created_at": "2025-01-01T00:00:00Z",
        "acknowledged_at": null,
        "resolved_at": null,
    });
    let req = app.post_authenticated("/api/v1/ops/andons", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_create_project() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "project_code": "PROJ-001",
        "name": "Kaizen Event",
        "description": "Continuous improvement project",
        "category": "kaizen",
        "status": "active",
        "priority": "medium",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "team_members": [],
        "planned_start": null,
        "planned_end": null,
        "actual_start": null,
        "actual_end": null,
        "budget": null,
        "savings_realized": null,
        "created_at": "2025-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/ops/projects", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
}

#[tokio::test]
async fn test_ops_list_projects() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/projects", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_create_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "a3_number": "A3-001",
        "title": "Ops A3",
        "background": "Background",
        "current_state": "Current",
        "goal": "Target state",
        "root_cause_analysis": "RCA",
        "countermeasures": "Planned actions",
        "check_plan": "Check results",
        "follow_up": "Follow up actions",
        "status": "draft",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "created_at": "2025-01-01T00:00:00Z",
        "closed_at": null,
    });
    let req = app.post_authenticated("/api/v1/ops/a3s", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_list_a3s() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/a3s", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_create_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "risk_number": "RISK-001",
        "title": "Ops Risk",
        "description": "Risk via ops",
        "category": "operational",
        "likelihood": "possible",
        "impact": "moderate",
        "risk_score": 6,
        "mitigation": "Implement controls",
        "contingency": "Backup plan",
        "status": "identified",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "created_at": "2025-01-01T00:00:00Z",
        "mitigated_at": null,
    });
    let req = app.post_authenticated("/api/v1/ops/risks", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_list_risks() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/risks", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Lifecycle actions ───────────────────────────────────────────────────────

#[tokio::test]
async fn test_ops_acknowledge_and_resolve_andon() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::andon_payload("WC-1", "Machine down");
    let req = app.post_authenticated("/api/v1/ops/andons", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let andon_id = created["id"].as_str().unwrap().to_string();

    // Acknowledge: the actor comes from the token, not the body.
    let req = app.post_authenticated(
        &format!("/api/v1/ops/andons/{}/acknowledge", andon_id),
        &token,
        serde_json::json!({"acknowledged_by": uuid::Uuid::new_v4().to_string()}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "acknowledged");
    assert_eq!(json["acknowledged_by"], app.admin_user_id.to_string());
    assert!(json["acknowledged_at"].is_string());
    assert!(json["response_time_seconds"].is_number());

    // Resolve with resolution notes; the actor is still token-derived.
    let req = app.post_authenticated(
        &format!("/api/v1/ops/andons/{}/resolve", andon_id),
        &token,
        serde_json::json!({"resolution": "Restarted the machine"}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "resolved");
    assert_eq!(json["resolved_by"], app.admin_user_id.to_string());
    assert_eq!(json["resolution"], "Restarted the machine");
    assert!(json["resolution_time_seconds"].is_number());
}

#[tokio::test]
async fn test_ops_complete_project() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "project_code": "PROJ-002",
        "name": "Kaizen Event 2",
        "description": "Continuous improvement project",
        "category": "kaizen",
        "status": "active",
        "priority": "medium",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "team_members": [],
        "planned_start": null,
        "planned_end": null,
        "actual_start": null,
        "actual_end": null,
        "budget": null,
        "savings_realized": null,
        "created_at": "2025-01-01T00:00:00Z",
    });
    let req = app.post_authenticated("/api/v1/ops/projects", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let project_id = created["id"].as_str().unwrap().to_string();

    let req = app.post_authenticated(
        &format!("/api/v1/ops/projects/{}/complete", project_id),
        &token,
        serde_json::json!({"savings_realized": 12500.0}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "completed");
    assert_eq!(json["savings_realized"], 12500.0);
    assert!(json["actual_end"].is_string());
}

#[tokio::test]
async fn test_ops_close_a3() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = common::fixtures::a3_payload("Close A3", "Defect reduction");
    let req = app.post_authenticated("/api/v1/ops/a3s", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let a3_id = created["id"].as_str().unwrap().to_string();

    // Evidence-driven close: record verification evidence first (the
    // legacy update takes the full document).
    let get = app.get_authenticated(&format!("/api/v1/ops/a3s/{}", a3_id), &token);
    let mut get_resp = app.send_request(get).await;
    let mut doc: Value = app.json_body(&mut get_resp).await;
    doc["verifications"] = serde_json::json!([{"metric": "defect_rate", "after": 1.8}]);
    let upd = app.put_authenticated(&format!("/api/v1/ops/a3s/{}", a3_id), &token, doc);
    let resp = app.send_request(upd).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let req = app.post_authenticated(
        &format!("/api/v1/ops/a3s/{}/close", a3_id),
        &token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "closed");
    assert!(json["closed_at"].is_string());
}

#[tokio::test]
async fn test_ops_mitigate_risk() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "risk_number": format!("RISK-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "title": "Mitigate risk",
        "description": "Risk: Mitigate risk",
        "category": "Operational",
        "likelihood": "possible",
        "impact": "moderate",
        "risk_score": 6,
        "mitigation": "Implement controls",
        "contingency": "Backup plan",
        "status": "identified",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "created_at": "2025-01-01T00:00:00Z",
        "mitigated_at": null,
    });
    let req = app.post_authenticated("/api/v1/ops/risks", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "create risk failed: {}",
        app.response_text(&mut resp).await
    );
    let created: Value = app.json_body(&mut resp).await;
    let risk_id = created["id"].as_str().unwrap().to_string();

    let req = app.post_authenticated(
        &format!("/api/v1/ops/risks/{}/mitigate", risk_id),
        &token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "mitigated");
    assert!(json["mitigated_at"].is_string());
    assert_eq!(json["id"], risk_id);
}

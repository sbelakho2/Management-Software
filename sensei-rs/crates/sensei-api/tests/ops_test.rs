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
    let mut resp = app.send_request(req).await;
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
    let mut resp = app.send_request(req).await;
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
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
}

#[tokio::test]
async fn test_ops_list_projects() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/projects", &token);
    let mut resp = app.send_request(req).await;
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
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_list_a3s() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/a3s", &token);
    let mut resp = app.send_request(req).await;
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
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_list_risks() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/ops/risks", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

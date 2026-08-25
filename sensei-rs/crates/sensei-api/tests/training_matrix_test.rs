//! End-to-end tests for Training Matrix route handlers.
//!
//! Covers:
//! - GET/POST /api/v1/training-matrix
//! - PUT /api/v1/training-matrix/{id}
//! - GET /api/v1/training-matrix/skill-gaps
//! - Error cases (not_found, unauthenticated)

use axum::http::StatusCode;
use serde_json::Value;
use uuid::Uuid;

mod common;

// ── List & Create ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_list_matrix_entries() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let emp_id = Uuid::new_v4();

    let body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "employee_name": "Alice Johnson",
        "skill_name": "Welding",
        "skill_category": "Manufacturing",
        "proficiency_level": "competent",
        "notes": "Certified welder",
    });
    let req = app.post_authenticated("/api/v1/training-matrix", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let entry_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!entry_id.is_empty());
    assert_eq!(json["skill_name"], "Welding");

    // List entries
    let req_list = app.get_authenticated("/api/v1/training-matrix", &token);
    let mut resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
    let json_list: Value = app.json_body(&mut resp_list).await;
    assert!(json_list.is_object());
}

#[tokio::test]
async fn test_create_matrix_entry_with_all_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let emp_id = Uuid::new_v4();
    let assessor_id = Uuid::new_v4();

    let body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "employee_name": "Bob Smith",
        "skill_name": "CNC Operation",
        "skill_category": "Manufacturing",
        "proficiency_level": "expert",
        "certification_id": "CERT-001",
        "last_assessed_at": "2026-05-01T00:00:00Z",
        "valid_until": "2027-05-01T00:00:00Z",
        "notes": "Master CNC operator",
        "assessed_by": assessor_id.to_string(),
    });
    let req = app.post_authenticated("/api/v1/training-matrix", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["proficiency_level"], "expert");
    assert_eq!(json["certification_id"], "CERT-001");
}

// ── Update ────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_update_matrix_entry() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let emp_id = Uuid::new_v4();

    // Create entry
    let create_body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "employee_name": "Charlie Brown",
        "skill_name": "Quality Inspection",
        "skill_category": "Quality",
        "proficiency_level": "novice",
        "notes": "Needs training",
    });
    let req = app.post_authenticated("/api/v1/training-matrix", &token, create_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let entry_id = json["id"].as_str().unwrap().to_string();

    // Update proficiency level
    let update_body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "employee_name": "Charlie Brown",
        "skill_name": "Quality Inspection",
        "skill_category": "Quality",
        "proficiency_level": "competent",
        "notes": "Completed training",
    });
    let req_update = app.put_authenticated(
        &format!("/api/v1/training-matrix/{}", entry_id),
        &token,
        update_body,
    );
    let mut resp_update = app.send_request(req_update).await;
    assert_eq!(resp_update.status(), StatusCode::OK);
    let json_update: Value = app.json_body(&mut resp_update).await;
    assert_eq!(json_update["proficiency_level"], "competent");
}

#[tokio::test]
async fn test_update_matrix_entry_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let emp_id = Uuid::new_v4();
    let id = Uuid::nil().to_string();
    let body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "employee_name": "Unknown",
        "skill_name": "None",
        "skill_category": "Other",
        "proficiency_level": "novice",
        "notes": "",
    });
    let req = app.put_authenticated(&format!("/api/v1/training-matrix/{}", id), &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

// ── Skill Gaps ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_list_skill_gaps() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let emp_id = Uuid::new_v4();

    // Create a "novice" entry (should appear as a skill gap)
    let body = serde_json::json!({
        "employee_id": emp_id.to_string(),
        "employee_name": "David Lee",
        "skill_name": "Advanced Welding",
        "skill_category": "Manufacturing",
        "proficiency_level": "novice",
        "notes": "Beginner level",
    });
    let req = app.post_authenticated("/api/v1/training-matrix", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // List skill gaps
    let req_gaps = app.get_authenticated("/api/v1/training-matrix/skill-gaps", &token);
    let mut resp_gaps = app.send_request(req_gaps).await;
    assert_eq!(resp_gaps.status(), StatusCode::OK);
    let json_gaps: Value = app.json_body(&mut resp_gaps).await;
    assert!(json_gaps.is_array());
}

// ── Unauthenticated ───────────────────────────────────────────────────────────

#[tokio::test]
async fn test_training_matrix_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/training-matrix");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

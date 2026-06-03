//! End-to-end tests for Training Course endpoints.
//!
//! Covers: create, list, get, update, delete course; enroll users;
//! list enrollments; update enrollment status; my-courses; dashboard.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Course CRUD ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_course() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Safety Training", "Safety");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["title"], "Safety Training");
}

#[tokio::test]
async fn test_list_courses() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Course A", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/training/courses", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_course() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Get Course", "Quality");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(&format!("/api/v1/training/courses/{}", course_id), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], course_id);
}

#[tokio::test]
async fn test_get_course_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/training/courses/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_course() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Original", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"title": "Updated Title"});
    let req = app.put_authenticated(
        &format!("/api/v1/training/courses/{}", course_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["title"], "Updated Title");
}

#[tokio::test]
async fn test_delete_course() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Delete Me", "Safety");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(
        &format!("/api/v1/training/courses/{}", course_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

// ── Enrollments ────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_enroll_users() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Enroll Course", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let enroll = serde_json::json!({
        "user_ids": [app.admin_user_id.to_string()],
    });
    let req = app.post_authenticated(
        &format!("/api/v1/training/courses/{}/enroll", course_id),
        &token,
        enroll,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_list_enrollments() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Enroll List", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let enroll = serde_json::json!({"user_ids": [app.admin_user_id.to_string()]});
    let req = app.post_authenticated(
        &format!("/api/v1/training/courses/{}/enroll", course_id),
        &token,
        enroll,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/training/courses/{}/enrollments", course_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_update_enrollment_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Status Course", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let enroll = serde_json::json!({"user_ids": [app.admin_user_id.to_string()]});
    let req = app.post_authenticated(
        &format!("/api/v1/training/courses/{}/enroll", course_id),
        &token,
        enroll,
    );
    let mut resp = app.send_request(req).await;
    let enrollments: Value = app.json_body(&mut resp).await;
    let enrollment_id = enrollments[0]["id"].as_str().unwrap();

    let update = serde_json::json!({"status": "Completed", "score": 95.0});
    let req = app.patch_authenticated(
        &format!("/api/v1/training/enrollments/{}", enrollment_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["status"], "Completed");
}

#[tokio::test]
async fn test_my_courses() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("My Course", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let course_id = created["id"].as_str().unwrap();

    let enroll = serde_json::json!({"user_ids": [app.admin_user_id.to_string()]});
    let req = app.post_authenticated(
        &format!("/api/v1/training/courses/{}/enroll", course_id),
        &token,
        enroll,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/training/my-courses", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_training_dashboard() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::training_course_payload("Dash Course", "Technical");
    let req = app.post_authenticated("/api/v1/training/courses", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/training/dashboard", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["total_courses"].as_u64().unwrap_or(0) >= 1);
}

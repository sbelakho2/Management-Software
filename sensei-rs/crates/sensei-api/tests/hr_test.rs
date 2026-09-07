//! End-to-end tests for HR route handlers.
//!
//! Covers:
//! - CRUD /api/v1/hr/employees
//! - POST/GET /api/v1/hr/training
//! - Self-service leave + timecards (identity derived from the
//!   authenticated user, never from client-submitted employee ids)
//! - Manager read endpoints /api/v1/hr/employees/{id}/leave + /timecards
//! - Error cases (not_found, unauthenticated, forbidden)

use axum::http::StatusCode;
use chrono::Utc;
use serde_json::Value;
use uuid::Uuid;

mod common;

use common::setup::TestApp;

/// Log in with arbitrary credentials and return the access token.
async fn login_user(app: &TestApp, email: &str, password: &str) -> String {
    let body = serde_json::json!({ "email": email, "password": password });
    let req = app.post("/api/v1/auth/login", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "login for {email} should succeed"
    );
    let json: Value = app.json_body(&mut resp).await;
    json["access_token"]
        .as_str()
        .expect("No access_token in login response")
        .to_string()
}

/// Create an ACTIVE employee record bound to the given user id (as the
/// admin/hr_manager) and return the employee id.
async fn create_employee_for_user(app: &TestApp, token: &str, user_id: Uuid) -> String {
    let now = Utc::now().to_rfc3339();
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_code": "",
        "user_id": user_id.to_string(),
        "full_name": "Self Service User",
        "email": format!("self-{}@sensei.test", user_id.as_simple()),
        "department": "Engineering",
        "job_title": "Engineer",
        "employment_type": "full_time",
        "status": "active",
        "hire_date": now,
        "termination_date": null,
        "supervisor_id": null,
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/hr/employees", token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "employee creation should succeed"
    );
    let json: Value = app.json_body(&mut resp).await;
    json["id"]
        .as_str()
        .expect("created employee must have an id")
        .to_string()
}

/// Submit a leave request through the self-service endpoint with the NARROW
/// body (no identity fields) and return the created leave id.
async fn submit_self_leave(app: &TestApp, token: &str) -> String {
    let body = serde_json::json!({
        "leave_type": "annual",
        "start_date": Utc::now().to_rfc3339(),
        "end_date": (Utc::now() + chrono::Duration::days(5)).to_rfc3339(),
        "reason": "Annual vacation",
    });
    let req = app.post_authenticated("/api/v1/hr/leave", token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "self leave submit should succeed"
    );
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["employee_id"].as_str().is_some());
    json["id"]
        .as_str()
        .expect("created leave must have an id")
        .to_string()
}

// ── Employees ─────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_get_employee() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_code": "",
        "user_id": user_id.to_string(),
        "full_name": "John Doe",
        "email": "john.doe@sensei.test",
        "department": "Engineering",
        "job_title": "Software Engineer",
        "employment_type": "full_time",
        "status": "active",
        "hire_date": now,
        "termination_date": null,
        "supervisor_id": null,
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/hr/employees", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let emp_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!emp_id.is_empty());
    assert_eq!(json["full_name"], "John Doe");

    // Get the employee
    let req_get = app.get_authenticated(&format!("/api/v1/hr/employees/{}", emp_id), &token);
    let mut resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
    let json_get: Value = app.json_body(&mut resp_get).await;
    assert_eq!(json_get["full_name"], "John Doe");
}

#[tokio::test]
async fn test_list_employees() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/hr/employees", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
}

#[tokio::test]
async fn test_get_employee_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let id = Uuid::nil().to_string();
    let req = app.get_authenticated(&format!("/api/v1/hr/employees/{}", id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_employee_status() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    // Create employee
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_code": "",
        "user_id": user_id.to_string(),
        "full_name": "Jane Smith",
        "email": "jane.smith@sensei.test",
        "department": "Engineering",
        "job_title": "Senior Engineer",
        "employment_type": "full_time",
        "status": "active",
        "hire_date": now,
        "termination_date": null,
        "supervisor_id": null,
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/hr/employees", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let emp_id = json["id"].as_str().unwrap().to_string();

    // Update status
    let status_body = serde_json::json!({ "status": "on_leave" });
    let req_status = app.put_authenticated(
        &format!("/api/v1/hr/employees/{}/status", emp_id),
        &token,
        status_body,
    );
    let mut resp_status = app.send_request(req_status).await;
    assert_eq!(resp_status.status(), StatusCode::OK);
    let json_status: Value = app.json_body(&mut resp_status).await;
    assert_eq!(json_status["status"], "on_leave");
}

// ── Training Records ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_record_and_list_training() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let emp_id = Uuid::new_v4();
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_id": emp_id.to_string(),
        "course_name": "Safety Training",
        "provider": "OSHA",
        "credits": 8,
        "completed_at": now,
        "expires_at": null,
        "certificate_url": null,
    });
    let req = app.post_authenticated("/api/v1/hr/training", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let training_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!training_id.is_empty());

    // List training records
    let req_list = app.get_authenticated(
        &format!("/api/v1/hr/training?employee_id={}", emp_id),
        &token,
    );
    let resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
}

// ── Leave Requests (self-service) ─────────────────────────────────────────────

#[tokio::test]
async fn test_submit_update_and_list_my_leave() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Self-service identity: the admin's ACTIVE employee record.
    let emp_id = create_employee_for_user(&app, &token, app.admin_user_id).await;

    let leave_id = submit_self_leave(&app, &token).await;

    // "My leave": the self list derives the employee server-side.
    let req_list = app.get_authenticated("/api/v1/hr/leave", &token);
    let mut resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
    let json_list: Value = app.json_body(&mut resp_list).await;
    assert_eq!(
        json_list["total"], 1,
        "self list must return only own leave"
    );
    assert_eq!(
        json_list["data"][0]["id"].as_str().unwrap(),
        leave_id.as_str()
    );

    // The manager view of the SAME employee also sees it.
    let req_mgr = app.get_authenticated(&format!("/api/v1/hr/employees/{emp_id}/leave"), &token);
    let resp_mgr = app.send_request(req_mgr).await;
    assert_eq!(resp_mgr.status(), StatusCode::OK);

    // Update the pending request with the narrow body (no identity fields).
    let update_body = serde_json::json!({
        "leave_type": "sick",
        "start_date": (Utc::now() + chrono::Duration::days(1)).to_rfc3339(),
        "end_date": (Utc::now() + chrono::Duration::days(2)).to_rfc3339(),
        "reason": "Updated: medical",
    });
    let req_upd =
        app.put_authenticated(&format!("/api/v1/hr/leave/{leave_id}"), &token, update_body);
    let mut resp_upd = app.send_request(req_upd).await;
    assert_eq!(resp_upd.status(), StatusCode::OK);
    let json_upd: Value = app.json_body(&mut resp_upd).await;
    assert_eq!(json_upd["leave_type"], "sick");
    assert_eq!(json_upd["reason"], "Updated: medical");
    assert_eq!(json_upd["status"], "pending");

    // Approve leave (manager flow, approver = authenticated user).
    let approve_body = serde_json::json!({});
    let req_approve = app.post_authenticated(
        &format!("/api/v1/hr/leave/{leave_id}/approve"),
        &token,
        approve_body,
    );
    let resp_approve = app.send_request(req_approve).await;
    assert_eq!(resp_approve.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_self_leave_ownership_and_pending_only() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Self-service identity: the admin's ACTIVE employee record.
    create_employee_for_user(&app, &token, app.admin_user_id).await;

    // Once approved, the owner can no longer update or delete it.
    let approved_id = submit_self_leave(&app, &token).await;
    let approve_body = serde_json::json!({});
    let req_approve = app.post_authenticated(
        &format!("/api/v1/hr/leave/{approved_id}/approve"),
        &token,
        approve_body,
    );
    let resp_approve = app.send_request(req_approve).await;
    assert_eq!(resp_approve.status(), StatusCode::OK);

    let stale_update = serde_json::json!({
        "leave_type": "personal",
        "start_date": Utc::now().to_rfc3339(),
        "end_date": (Utc::now() + chrono::Duration::days(2)).to_rfc3339(),
        "reason": "must not apply",
    });
    let req_upd = app.put_authenticated(
        &format!("/api/v1/hr/leave/{approved_id}"),
        &token,
        stale_update,
    );
    let resp_upd = app.send_request(req_upd).await;
    assert_eq!(
        resp_upd.status(),
        StatusCode::NOT_FOUND,
        "approved leave is not editable"
    );
    let req_del = app.delete_authenticated(&format!("/api/v1/hr/leave/{approved_id}"), &token);
    let resp_del = app.send_request(req_del).await;
    assert_eq!(
        resp_del.status(),
        StatusCode::NOT_FOUND,
        "approved leave is not deletable"
    );

    // A pending OWN request can be updated once, deleted once, then 404s.
    let own_id = submit_self_leave(&app, &token).await;
    let update_body = serde_json::json!({
        "leave_type": "personal",
        "start_date": Utc::now().to_rfc3339(),
        "end_date": (Utc::now() + chrono::Duration::days(1)).to_rfc3339(),
        "reason": "Family matter",
    });
    let req_upd = app.put_authenticated(
        &format!("/api/v1/hr/leave/{own_id}"),
        &token,
        update_body.clone(),
    );
    let mut resp_upd = app.send_request(req_upd).await;
    assert_eq!(resp_upd.status(), StatusCode::OK);
    let json_upd: Value = app.json_body(&mut resp_upd).await;
    assert_eq!(json_upd["leave_type"], "personal");

    let req_del = app.delete_authenticated(&format!("/api/v1/hr/leave/{own_id}"), &token);
    let resp_del = app.send_request(req_del).await;
    assert_eq!(resp_del.status(), StatusCode::OK);

    let req_del2 = app.delete_authenticated(&format!("/api/v1/hr/leave/{own_id}"), &token);
    let resp_del2 = app.send_request(req_del2).await;
    assert_eq!(resp_del2.status(), StatusCode::NOT_FOUND);
    let req_upd2 =
        app.put_authenticated(&format!("/api/v1/hr/leave/{own_id}"), &token, update_body);
    let resp_upd2 = app.send_request(req_upd2).await;
    assert_eq!(resp_upd2.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_self_service_requires_active_employee_record() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // A supervisor WITH the self permission but WITHOUT any employee record
    // must be refused by the identity resolver (403), even though the
    // request itself is well-formed.
    let user_id = app
        .create_user_with_roles(
            "lonely-supervisor@sensei.test",
            "TestPass123!",
            &["supervisor"],
        )
        .await;
    let lonely_token = login_user(&app, "lonely-supervisor@sensei.test", "TestPass123!").await;

    let leave_body = serde_json::json!({
        "leave_type": "annual",
        "start_date": Utc::now().to_rfc3339(),
        "end_date": (Utc::now() + chrono::Duration::days(5)).to_rfc3339(),
        "reason": "Vacation",
    });
    let req = app.post_authenticated("/api/v1/hr/leave", &lonely_token, leave_body);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::FORBIDDEN,
        "self leave requires an active employee record"
    );

    let req = app.post_authenticated(
        "/api/v1/hr/timecards/clock-in",
        &lonely_token,
        serde_json::json!({}),
    );
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::FORBIDDEN,
        "clock-in requires an active employee record"
    );

    // A client-submitted employee id is NEVER trusted: even when the body
    // carries a foreign employee id, the server still resolves the caller.
    let foreign_emp = create_employee_for_user(&app, &token, Uuid::new_v4()).await;
    let spoof = serde_json::json!({
        "employee_id": foreign_emp,
        "leave_type": "annual",
        "start_date": Utc::now().to_rfc3339(),
        "end_date": (Utc::now() + chrono::Duration::days(5)).to_rfc3339(),
        "reason": "Spoofed",
    });
    let req = app.post_authenticated("/api/v1/hr/leave", &lonely_token, spoof);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::FORBIDDEN,
        "a client-submitted employee id must not satisfy the identity check"
    );

    // Once the same user HAS an active employee record the self endpoints
    // work — and the timecard is attributed to THAT derived employee.
    let lonely_emp = create_employee_for_user(&app, &token, user_id).await;
    let req = app.post_authenticated(
        "/api/v1/hr/timecards/clock-in",
        &lonely_token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(
        json["employee_id"].as_str().unwrap(),
        lonely_emp,
        "identity is derived server-side from the authenticated user"
    );
}

// ── Performance Reviews ────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_list_reviews() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let emp_id = Uuid::new_v4();
    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "employee_id": emp_id.to_string(),
        "reviewer_id": Uuid::new_v4().to_string(),
        "review_period": "Q1_2026",
        "overall_rating": 4.5,
        "strengths": "Strong technical skills",
        "areas_for_improvement": "Communication",
        "goals": "Lead a project",
        "status": "draft",
        "created_at": now,
        "completed_at": null,
    });
    let req = app.post_authenticated("/api/v1/hr/reviews", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let review_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!review_id.is_empty());

    // List reviews
    let req_list = app.get_authenticated(
        &format!("/api/v1/hr/reviews?employee_id={}", emp_id),
        &token,
    );
    let resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
}

// ── Timecards (self-service) ──────────────────────────────────────────────────

#[tokio::test]
async fn test_clock_in_and_out() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Self-service identity: the admin's ACTIVE employee record.
    let emp_id = create_employee_for_user(&app, &token, app.admin_user_id).await;

    // Clock in — the request body carries NO employee id.
    let clock_in_body = serde_json::json!({});
    let req_in = app.post_authenticated("/api/v1/hr/timecards/clock-in", &token, clock_in_body);
    let mut resp_in = app.send_request(req_in).await;
    assert_eq!(resp_in.status(), StatusCode::OK);
    let json_in: Value = app.json_body(&mut resp_in).await;
    let timecard_id = json_in["id"].as_str().unwrap_or("").to_string();
    assert!(!timecard_id.is_empty());
    assert_eq!(
        json_in["employee_id"], emp_id,
        "identity is derived server-side"
    );

    // "My timecards": the self list derives the employee server-side.
    let req_list = app.get_authenticated("/api/v1/hr/timecards", &token);
    let mut resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
    let json_list: Value = app.json_body(&mut resp_list).await;
    assert_eq!(
        json_list["total"], 1,
        "self list must return only own timecards"
    );

    // Clock out — body carries the timecard id only.
    let clock_out_body = serde_json::json!({ "timecard_id": timecard_id });
    let req_out = app.post_authenticated("/api/v1/hr/timecards/clock-out", &token, clock_out_body);
    let mut resp_out = app.send_request(req_out).await;
    assert_eq!(resp_out.status(), StatusCode::OK);
    let json_out: Value = app.json_body(&mut resp_out).await;
    assert!(json_out["clock_out"].as_str().is_some());
    assert_eq!(json_out["employee_id"], emp_id);

    // Clocking out an already-closed timecard fails (identity-scoped).
    let req_out2 = app.post_authenticated(
        "/api/v1/hr/timecards/clock-out",
        &token,
        serde_json::json!({ "timecard_id": timecard_id }),
    );
    let resp_out2 = app.send_request(req_out2).await;
    assert_ne!(resp_out2.status(), StatusCode::OK);
}

// ── Manager read endpoints ────────────────────────────────────────────────────

#[tokio::test]
async fn test_manager_list_employee_leave_and_timecards() {
    let app = common::TestApp::new().await;
    let admin_token = app.login_as_admin().await;

    // Target employee owned by a supervisor user.
    let target_user = app
        .create_user_with_roles(
            "target-employee@sensei.test",
            "TestPass123!",
            &["supervisor"],
        )
        .await;
    let target_token = login_user(&app, "target-employee@sensei.test", "TestPass123!").await;
    let target_emp = create_employee_for_user(&app, &admin_token, target_user).await;

    // The target exercises the SELF endpoints (identity derived).
    let req = app.post_authenticated(
        "/api/v1/hr/timecards/clock-in",
        &target_token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let timecard_id = json["id"].as_str().unwrap().to_string();
    let req = app.post_authenticated(
        "/api/v1/hr/timecards/clock-out",
        &target_token,
        serde_json::json!({ "timecard_id": timecard_id }),
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let leave_id = submit_self_leave(&app, &target_token).await;

    // The hr_manager (admin) reads the target employee's records through the
    // MANAGER endpoints — the employee id comes from the PATH, guarded by
    // manage/read permissions rather than *:self.
    let req = app.get_authenticated(
        &format!("/api/v1/hr/employees/{target_emp}/timecards"),
        &admin_token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"], 1, "manager sees the target's timecard");
    assert_eq!(
        json["data"][0]["id"].as_str().unwrap(),
        timecard_id.as_str()
    );

    let req = app.get_authenticated(
        &format!("/api/v1/hr/employees/{target_emp}/leave"),
        &admin_token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"], 1, "manager sees the target's leave");
    assert_eq!(json["data"][0]["id"].as_str().unwrap(), leave_id.as_str());

    // A user WITHOUT the manage/read permissions is refused on the manager
    // endpoints even though the same user may hold self permissions — plain
    // users hold neither, and the guard is NOT *:self.
    let _plain_user = app
        .create_user_with_roles("plain-hr@sensei.test", "TestPass123!", &["user"])
        .await;
    let plain_token = login_user(&app, "plain-hr@sensei.test", "TestPass123!").await;
    let req = app.get_authenticated(
        &format!("/api/v1/hr/employees/{target_emp}/leave"),
        &plain_token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
    let req = app.get_authenticated(
        &format!("/api/v1/hr/employees/{target_emp}/timecards"),
        &plain_token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
}

// ── Unauthenticated ───────────────────────────────────────────────────────────

#[tokio::test]
async fn test_hr_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/hr/employees");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

//! End-to-end tests for the API middleware stack.
//!
//! Covers:
//! - Rate limiting (429 after the limit is exhausted)
//! - Audit logging (entries recorded with the authenticated user)
//! - Session fingerprint mismatch → 401 (possible token theft)
//! - Idempotency keys (scoped per user, duplicate concurrent execution runs once)
//! - HSTS omitted on plain HTTP
//! - Unmatched `/api/*` paths return a structured JSON 404 (not static HTML)
//! - `GET /` serves the landing page

use axum::http::{HeaderValue, StatusCode};

mod common;

use common::TestApp;

// ── Helpers ──────────────────────────────────────────────────────────────────

/// Log in with email/password and return the access token.
async fn login(app: &TestApp, email: &str, password: &str) -> String {
    let body = serde_json::json!({ "email": email, "password": password });
    let req = app.post("/api/v1/auth/login", body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK, "login failed for {email}");
    let json: serde_json::Value = app.json_body(&mut resp).await;
    json["access_token"]
        .as_str()
        .expect("no access_token in login response")
        .to_string()
}

/// POST /api/v1/tasks with an optional Idempotency-Key, returning the response.
async fn create_task(
    _app: &TestApp,
    token: &str,
    title: &str,
    key: Option<&str>,
) -> axum::http::Request<axum::body::Body> {
    let body = serde_json::json!({
        "title": title,
        "description": "created by middleware test",
        "priority": "medium",
        "category": "general",
        "tags": ["test"],
    });
    let mut builder = axum::http::Request::builder()
        .uri("/api/v1/tasks")
        .method("POST")
        .header("Content-Type", "application/json")
        .header("Authorization", format!("Bearer {token}"));
    if let Some(key) = key {
        builder = builder.header("Idempotency-Key", key);
    }
    builder
        .body(axum::body::Body::from(serde_json::to_vec(&body).unwrap()))
        .unwrap()
}

async fn task_count(app: &TestApp, token: &str) -> usize {
    let req = app.get_authenticated("/api/v1/tasks", token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: serde_json::Value = app.json_body(&mut resp).await;
    json["data"].as_array().map(|a| a.len()).unwrap_or(0)
}

// ── Rate limiting ────────────────────────────────────────────────────────────

#[tokio::test]
async fn rate_limiter_returns_429_after_limit() {
    common::setup::pin_test_environment();
    let password = "TestAdmin123!";
    let hash = sensei_auth::password::hash_password(password).unwrap();
    let tenant = sensei_core::types::TenantId::new_v4();
    let users: std::sync::Arc<dyn sensei_services::users::UsersService> =
        std::sync::Arc::new(sensei_services::users::InMemoryUsersService::with_admin(
            "admin@sensei.test",
            "Admin User",
            &hash,
            tenant,
        ));
    let config = sensei_core::config::AppConfig::from_env().unwrap();
    let mut state = sensei_api::AppState::new(config, users);
    // Two requests per minute; all requests in this test share the
    // "unknown" client key (no ConnectInfo in oneshot mode).
    state.rate_limiter = sensei_api::middleware::rate_limiter::RateLimiter::new(2, 60);
    let app = TestApp::from_state(state);

    // Requests 1 and 2 pass; request 3 is rate-limited.
    let req = app.get("/health/live");
    assert_eq!(app.send_request(req).await.status(), StatusCode::OK);

    let req = app.get("/health/live");
    assert_eq!(app.send_request(req).await.status(), StatusCode::OK);

    let req = app.get("/health/live");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::TOO_MANY_REQUESTS);

    // The response carries a Retry-After header.
    let retry_after = resp
        .headers()
        .get(axum::http::header::RETRY_AFTER)
        .and_then(|v| v.to_str().ok());
    assert!(retry_after.is_some(), "429 must include Retry-After");
}

// ── Audit logging ────────────────────────────────────────────────────────────

#[tokio::test]
async fn audit_entries_are_recorded_with_user() {
    let app = TestApp::new().await;
    let token = login(&app, "admin@sensei.test", &app.admin_password).await;

    let req = create_task(&app, &token, "audited task", None).await;
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let entries = app.state.audit_log.get_entries().await;
    let entry = entries
        .iter()
        .find(|e| e.method == "POST" && e.path == "/api/v1/tasks")
        .expect("audit entry for the task creation must exist");

    assert_eq!(entry.status, 200);
    assert_eq!(
        entry.user_id.as_deref(),
        Some(app.admin_user_id.to_string().as_str()),
        "audit entry must record the authenticated user"
    );
}

#[tokio::test]
async fn audit_ignores_get_requests() {
    let app = TestApp::new().await;
    let token = login(&app, "admin@sensei.test", &app.admin_password).await;

    let req = app.get_authenticated("/api/v1/tasks", &token);
    app.send_request(req).await;

    let entries = app.state.audit_log.get_entries().await;
    assert!(
        entries.iter().all(|e| e.method != "GET"),
        "GET requests must not be audited"
    );
}

// ── Session binding ──────────────────────────────────────────────────────────

#[tokio::test]
async fn session_mismatch_returns_401_and_removes_binding() {
    let app = TestApp::new().await;
    let token = login(&app, "admin@sensei.test", &app.admin_password).await;

    // Plant a fingerprint under the TOKEN's sid that cannot match anything
    // the middleware computes (the binding is keyed by session id, not
    // user id — one user may hold many concurrent sessions).
    let claims = app.state.jwt_service.validate_access_token(&token).unwrap();
    let sid = claims.sid.to_string();
    app.state
        .session_store
        .register(
            &sid,
            &app.admin_user_id.to_string(),
            app.admin_tenant_id,
            "attacker-fingerprint".to_string(),
        )
        .await;

    let req = app.get_authenticated("/api/v1/tasks", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);

    // The stale binding must have been removed (forces re-login re-bind).
    assert_eq!(
        app.state
            .session_store
            .verify(&sid, "attacker-fingerprint")
            .await
            .unwrap(),
        sensei_api::middleware::session::SessionResult::Unknown,
        "mismatched binding must be removed"
    );
}

#[tokio::test]
async fn session_first_sight_auto_registers_and_passes() {
    let app = TestApp::new().await;
    let token = login(&app, "admin@sensei.test", &app.admin_password).await;

    // First authenticated request: no binding stored → auto-register + pass.
    let req = app.get_authenticated("/api/v1/tasks", &token);
    assert_eq!(app.send_request(req).await.status(), StatusCode::OK);

    // Second request with the same fingerprint still passes.
    let req = app.get_authenticated("/api/v1/tasks", &token);
    assert_eq!(app.send_request(req).await.status(), StatusCode::OK);
}

// ── Idempotency ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn idempotency_key_is_scoped_per_user() {
    let app = TestApp::new().await;
    let admin_token = login(&app, "admin@sensei.test", &app.admin_password).await;
    app.create_user_with_roles("other@sensei.test", "Other123!", &["user"])
        .await;
    let other_token = login(&app, "other@sensei.test", "Other123!").await;

    // Both users send the same Idempotency-Key on the same path.
    let resp = app
        .send_request(create_task(&app, &admin_token, "scoped-a", Some("shared-key")).await)
        .await;
    assert_eq!(resp.status(), StatusCode::OK);
    let resp = app
        .send_request(create_task(&app, &other_token, "scoped-b", Some("shared-key")).await)
        .await;
    assert_eq!(resp.status(), StatusCode::OK);

    // Two distinct tasks were created (keys did not collide across users).
    assert_eq!(task_count(&app, &admin_token).await, 2);

    // A retry with the same key + user + body replays the cached response:
    // the task count does not grow.
    let resp = app
        .send_request(create_task(&app, &admin_token, "scoped-a", Some("shared-key")).await)
        .await;
    assert_eq!(resp.status(), StatusCode::OK);
    assert_eq!(
        task_count(&app, &admin_token).await,
        2,
        "retry must not re-execute"
    );

    // Reusing the key with a DIFFERENT body is a replay attack: 422.
    let resp = app
        .send_request(
            create_task(
                &app,
                &admin_token,
                "scoped-a-different-body",
                Some("shared-key"),
            )
            .await,
        )
        .await;
    assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn duplicate_concurrent_key_executes_once() {
    let app = TestApp::new().await;
    let token = login(&app, "admin@sensei.test", &app.admin_password).await;

    // Fire two identical requests concurrently with the same key.
    let req_a = create_task(&app, &token, "concurrent", Some("concurrent-key")).await;
    let req_b = create_task(&app, &token, "concurrent", Some("concurrent-key")).await;
    let (resp_a, resp_b) = tokio::join!(app.send_request(req_a), app.send_request(req_b),);

    assert_eq!(resp_a.status(), StatusCode::OK);
    assert_eq!(resp_b.status(), StatusCode::OK);

    // Exactly one task was created — the per-key guard prevented the
    // duplicate from double-executing.
    assert_eq!(task_count(&app, &token).await, 1);

    // Both responses carry the same task id (the second one is a replay).
    let mut resp_a = resp_a;
    let mut resp_b = resp_b;
    let json_a: serde_json::Value = app.json_body(&mut resp_a).await;
    let json_b: serde_json::Value = app.json_body(&mut resp_b).await;
    assert_eq!(json_a["id"], json_b["id"]);
}

// ── Security headers ─────────────────────────────────────────────────────────

#[tokio::test]
async fn hsts_omitted_on_plain_http() {
    let app = TestApp::new().await;
    let req = app.get("/health/live");
    let resp = app.send_request(req).await;

    assert!(
        resp.headers().get("strict-transport-security").is_none(),
        "HSTS must be omitted on plain HTTP"
    );
    // Other security headers are still present.
    assert!(resp.headers().get("content-security-policy").is_some());
    assert_eq!(
        resp.headers().get("x-content-type-options").unwrap(),
        "nosniff"
    );
}

// ── Routing fallbacks ────────────────────────────────────────────────────────

#[tokio::test]
async fn unknown_api_path_returns_json_404() {
    let app = TestApp::new().await;

    let req = app.get("/api/v1/definitely/not/a/route");
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    let content_type = resp
        .headers()
        .get(axum::http::header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(
        content_type.contains("application/json"),
        "API 404 must be JSON, got {content_type:?}"
    );

    let body: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(body["error"], "not_found");
    assert_eq!(body["message"], "Unknown API endpoint");
}

#[tokio::test]
async fn root_serves_landing_page() {
    let app = TestApp::new().await;
    let req = app.get("/");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let content_type = resp
        .headers()
        .get(axum::http::header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("text/html"), "root must serve HTML");
    assert!(content_type.contains("charset=utf-8") || content_type.contains("utf-8"));
}

// ── Request ID validation ────────────────────────────────────────────────────

#[tokio::test]
async fn invalid_request_id_is_replaced_with_uuid() {
    let app = TestApp::new().await;

    let req = axum::http::Request::builder()
        .uri("/health/live")
        .header("x-request-id", "not a valid id !!!")
        .body(axum::body::Body::empty())
        .unwrap();
    let resp = app.send_request(req).await;

    let echoed = resp
        .headers()
        .get("x-request-id")
        .and_then(|v| v.to_str().ok())
        .expect("response must echo x-request-id");
    uuid::Uuid::parse_str(echoed).expect("invalid client request id must be replaced by a UUID");
}

#[tokio::test]
async fn valid_request_id_is_echoed() {
    let app = TestApp::new().await;

    let req = axum::http::Request::builder()
        .uri("/health/live")
        .header("x-request-id", HeaderValue::from_static("req_abc-123.456"))
        .body(axum::body::Body::empty())
        .unwrap();
    let resp = app.send_request(req).await;

    assert_eq!(
        resp.headers().get("x-request-id").unwrap(),
        "req_abc-123.456"
    );
}

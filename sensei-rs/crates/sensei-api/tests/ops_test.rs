//! End-to-end tests for Operations (Ops) endpoints.
//!
//! Covers: Andon aliases, Projects, A3s, Risks CRUD under /api/v1/ops/.
//!
//! # DB-gated lifecycle test
//!
//! `test_ops_acknowledge_and_resolve_andon` exercises the Andon
//! LIFECYCLE through the canonical scope-vector handlers that the legacy
//! `/ops/andons/{id}/acknowledge` + `/resolve` URLs alias (thirtieth-first
//! audit: the ops router no longer carries Andon handlers — the legacy
//! paths map DIRECTLY to `routes::andon`), whose commands are
//! scope-vector enforced: the repository UPDATEs embed the tripartite
//! scope predicate `(tenant_wide OR site_id = ANY(sites) OR
//! work_center_id = ANY(work_centers))` and deny a `NoOperationalScope`
//! caller (fail-closed, twenty-first audit). The in-memory test harness
//! has no site rows or role-slot scope authority, so the test connects to
//! the CI-provided database (`DATABASE_URL_TEST`), seeds an operator with
//! an ACTIVE site entitlement + assignment, and drives the real handlers
//! (DB-backed state). The Andon is raised through the canonical
//! `/api/v1/andon` path (the server-scoped raise). Without
//! the environment variable the test skips cleanly, mirroring
//! `attachments_test.rs` / `today_test.rs`.

use axum::http::StatusCode;
use axum::{
    extract::{Path, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_auth::rbac::RbacService;
use sensei_core::config::AppConfig;
use sensei_core::domain::entities::User;
use sensei_services::users::{InMemoryUsersService, UsersService};
use serde_json::Value;
use std::sync::Arc;
use uuid::Uuid;

mod common;

#[tokio::test]
async fn test_ops_list_andons() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    // Legacy alias: GET /api/v1/ops/andons IS the canonical
    // scope-vector list (routes::andon::list_andons). The in-memory
    // harness carries the explicit tenant-wide grant, so the listing
    // succeeds and is empty.
    let req = app.get_authenticated("/api/v1/ops/andons", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_ops_raise_andon_alias_requires_server_resolved_focus() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    // Legacy alias: POST /api/v1/ops/andons IS the canonical
    // server-scoped raise (routes::andon::raise_andon). The full-object
    // legacy shape is gone — the handler derives site + work center from
    // the caller's validated RequestContext focus, never from the body.
    // The in-memory harness has no operational assignment, so the raise
    // is FORBIDDEN (fail closed), exactly like the canonical endpoint.
    let body = serde_json::json!({
        "issue_type": "quality",
        "severity": "high",
        "description": "Test andon via ops alias",
    });
    let req = app.post_authenticated("/api/v1/ops/andons", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::FORBIDDEN,
        "raising an Andon requires an active site + work center (server-resolved)"
    );
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

// ── DB-gated helpers (see the module docs) ─────────────────────────────────

/// Connect to the CI-provided test database. Returns None when the env
/// var is absent so the local in-memory suite stays green.
async fn db_pool() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — ops lifecycle gate runs in CI");
        return None;
    };
    match sqlx::PgPool::connect(&url).await {
        Ok(pool) => Some(pool),
        Err(e) => {
            eprintln!("SKIP: cannot reach DATABASE_URL_TEST ({e})");
            None
        }
    }
}

/// The DB-gated tests share one database; migrations must apply before
/// any seed. A per-binary lock serializes the migration step (idempotent
/// once applied).
static DB_MIGRATE_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

/// Apply the migration chain when the database has none (no-op when
/// already migrated). Returns false (test skips) when the chain cannot
/// run.
async fn ensure_migrations(pool: &sqlx::PgPool) -> bool {
    let _guard = DB_MIGRATE_LOCK.lock().await;
    match sensei_db::migrations::run_migrations(pool).await {
        Ok(_) => true,
        Err(e) => {
            eprintln!("SKIP: migration chain unavailable for ops lifecycle gate ({e})");
            false
        }
    }
}

/// One fresh tenant world: a site + work center and an operator whose
/// ACTIVE role-slot entitlement + employee assignment scope them there.
struct OpsWorld {
    tenant_id: Uuid,
    site_a: Uuid,
    _work_center_a: Uuid,
    operator_id: Uuid,
    operator_email: String,
}

async fn seed_world(pool: &sqlx::PgPool) -> OpsWorld {
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let wc_a = Uuid::new_v4();
    let operator_id = Uuid::new_v4();
    let slot = Uuid::new_v4();
    let operator_email = format!("ops-operator-{operator_id}@sensei.test");

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
        .bind(tenant_id)
        .bind("Ops Gate Tenant")
        .bind(format!("ops-gate-{tenant_id}"))
        .execute(pool)
        .await
        .expect("tenant seed");
    sqlx::query("INSERT INTO sites (id, tenant_id, site_code, name) VALUES ($1, $2, $3, $4)")
        .bind(site_a)
        .bind(tenant_id)
        .bind("SITE_A")
        .bind("Site A")
        .execute(pool)
        .await
        .expect("site seed");
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, site_id) \
         VALUES ($1, $2, $3, 'Operator A', 'x', '{user,production_manager}', $4)",
    )
    .bind(operator_id)
    .bind(tenant_id)
    .bind(&operator_email)
    .bind(site_a)
    .execute(pool)
    .await
    .expect("user seed");
    sqlx::query(
        "INSERT INTO work_centers \
             (id, tenant_id, site_id, work_center_number, name, work_center_type) \
         VALUES ($1, $2, $3, $4, 'Ops Work Center', 'assembly')",
    )
    .bind(wc_a)
    .bind(tenant_id)
    .bind(site_a)
    .bind(format!("WC-{wc_a}"))
    .execute(pool)
    .await
    .expect("work center seed");
    sqlx::query(
        "INSERT INTO role_slots (id, tenant_id, role_name, slot_name, scope_kind, scope_site_id) \
         VALUES ($1, $2, 'production_manager', $3, 'site', $4)",
    )
    .bind(slot)
    .bind(tenant_id)
    .bind(format!("slot-{slot}"))
    .bind(site_a)
    .execute(pool)
    .await
    .expect("role slot seed");
    sqlx::query(
        "INSERT INTO principal_assignments (id, tenant_id, principal_id, slot_id) \
         VALUES ($1, $2, $3, $4)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(operator_id)
    .bind(slot)
    .execute(pool)
    .await
    .expect("principal assignment seed");
    sqlx::query(
        "INSERT INTO employee_assignments \
             (id, tenant_id, user_id, site_id, work_center_id, is_active) \
         VALUES ($1, $2, $3, $4, $5, TRUE)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(operator_id)
    .bind(site_a)
    .bind(wc_a)
    .execute(pool)
    .await
    .expect("employee assignment seed");

    OpsWorld {
        tenant_id,
        site_a,
        _work_center_a: wc_a,
        operator_id,
        operator_email,
    }
}

/// DB-backed application state with the in-memory `users_service` kept
/// authoritative for per-request user lookups (see `andon_test.rs`).
async fn gate_state(pool: &Arc<sqlx::PgPool>, world: &OpsWorld) -> sensei_api::AppState {
    common::setup::pin_test_environment();
    let config = AppConfig::from_env().expect("test configuration must load under pinned env");

    let mut operator = User::new(
        world.tenant_id,
        world.operator_email.clone(),
        "Operator A".to_string(),
        "x".to_string(),
    );
    operator.id = world.operator_id;
    operator.roles = vec!["user".to_string(), "production_manager".to_string()];
    operator.site_id = Some(world.site_a);
    let users_service: Arc<dyn UsersService> = Arc::new(InMemoryUsersService::new());
    let seeded = users_service
        .create_user(operator)
        .await
        .expect("seed operator");
    assert_eq!(seeded.id, world.operator_id);

    let mut state =
        sensei_api::AppState::new(config, users_service.clone()).with_db_pool(pool.clone());
    state.users_service = users_service;
    state
}

#[tokio::test]
async fn test_ops_acknowledge_and_resolve_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let roles = vec!["user".to_string(), "production_manager".to_string()];
    let permissions = RbacService::new().expand_static(&roles);
    let user = AuthenticatedUser {
        user_id: world.operator_id,
        tenant_id: world.tenant_id,
        roles,
        permissions,
        sid: None,
    };

    // Raise through the canonical server-scoped Andon path — the legacy
    // /ops/andons POST IS this handler (thirtieth-first audit), so the
    // lifecycle below covers the alias semantics end to end.
    let raised = sensei_api::routes::andon::raise_andon(
        user.clone(),
        State(state.clone()),
        axum::http::HeaderMap::new(),
        Json(sensei_api::routes::andon::RaiseAndonRequest {
            issue_type: "quality".to_string(),
            severity: "high".to_string(),
            description: "Machine down".to_string(),
            observed_at: None,
        }),
    )
    .await
    .expect("an assigned operator can raise an andon")
    .0;
    let andon_id = raised.id;

    // Acknowledge through the canonical scope-vector handler (the legacy
    // OPS URL aliases it): no body — the actor comes from the token.
    let acknowledged = sensei_api::routes::andon::acknowledge_andon(
        user.clone(),
        State(state.clone()),
        Path(andon_id),
        axum::body::Body::empty(),
    )
    .await
    .expect("an entitled operator can acknowledge through the ops alias")
    .0;
    assert_eq!(acknowledged.status, "acknowledged");
    assert_eq!(acknowledged.acknowledged_by, Some(world.operator_id));
    assert!(acknowledged.acknowledged_at.is_some());
    assert!(acknowledged.response_time_seconds.is_some());

    // Resolve with resolution notes; the actor is still token-derived.
    let resolved = sensei_api::routes::andon::resolve_andon(
        user.clone(),
        State(state),
        Path(andon_id),
        Json(sensei_api::routes::andon::ResolveAndonRequest {
            resolved_by: None,
            resolution: "Restarted the machine".to_string(),
        }),
    )
    .await
    .expect("an entitled operator can resolve through the ops alias")
    .0;
    assert_eq!(resolved.status, "resolved");
    assert_eq!(resolved.resolved_by, Some(world.operator_id));
    assert_eq!(
        resolved.resolution.as_deref(),
        Some("Restarted the machine")
    );
    assert!(resolved.resolution_time_seconds.is_some());
}

#[tokio::test]
async fn test_ops_acknowledge_alias_bodyless_route_reaches_handler() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let andon_id = uuid::Uuid::new_v4();
    // The canonical acknowledge is BODY-LESS (thirtieth-first audit).
    // Both the canonical URL and the legacy ops alias are the SAME
    // handler: a body-less POST is accepted and runs (an unknown andon id
    // is 404 NotFound — NOT a 415 body rejection).
    for path in [
        format!("/api/v1/ops/andons/{andon_id}/acknowledge"),
        format!("/api/v1/andon/{andon_id}/acknowledge"),
    ] {
        let req = axum::http::Request::builder()
            .uri(path)
            .method("POST")
            .header("Authorization", format!("Bearer {}", token))
            .body(axum::body::Body::empty())
            .expect("body-less acknowledge request builds");
        let resp = app.send_request(req).await;
        assert_eq!(
            resp.status(),
            StatusCode::NOT_FOUND,
            "a body-less acknowledge reaches the canonical handler on both URLs (unknown andon -> NotFound)"
        );
    }
}

#[tokio::test]
async fn test_ops_acknowledge_alias_rejects_legacy_payload() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let andon_id = uuid::Uuid::new_v4();
    // Legacy clients posted an acknowledged_by-style payload to the
    // acknowledge URL. The thirtieth-first audit made the canonical
    // acknowledge body-less (the actor is the token's user), so a request
    // carrying a body is rejected with 415 — on the canonical URL AND on
    // the legacy ops alias, which map to the same handler — instead of
    // silently dropping the payload.
    for path in [
        format!("/api/v1/ops/andons/{andon_id}/acknowledge"),
        format!("/api/v1/andon/{andon_id}/acknowledge"),
    ] {
        let req = app.post_authenticated(
            &path,
            &token,
            serde_json::json!({ "resolved_by": uuid::Uuid::new_v4() }),
        );
        let resp = app.send_request(req).await;
        assert_eq!(
            resp.status(),
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "an acknowledge with a body must be rejected on {path}"
        );
    }
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

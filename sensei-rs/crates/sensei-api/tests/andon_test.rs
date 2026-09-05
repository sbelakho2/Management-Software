//! End-to-end tests for Andon endpoints.
//!
//! Tests raising, acknowledging, resolving, and CRUD operations
//! for the Andon (visual alert) system.
//!
//! # DB-gated suite (twenty-third/thirtieth-audit scope contract)
//!
//! The Andon raise handler SERVER-RESOLVES the site + work center from the
//! caller's operational assignment and fails closed when there is none
//! (`routes/andon.rs`): "No work-center assignment — raising help requires
//! an active operational assignment". The in-memory test harness has no
//! site/work-center rows and no role-slot scope authority, so the whole
//! happy path (raise → list → get → ack → resolve → update → void) is
//! DB-gated: it connects to the CI-provided test database
//! (`DATABASE_URL_TEST`), applies the full migration chain and drives the
//! real handlers against DB-backed state with an operator whose role-slot
//! entitlement + active assignment scope them to a seeded site. Without
//! the environment variable each test skips cleanly (the local in-memory
//! suite stays green), mirroring the pre-existing DB-gated suites
//! (`attachments_test.rs`, `today_test.rs`).

use axum::{
    extract::{Path, Query, State},
    http::HeaderMap,
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_auth::rbac::RbacService;
use sensei_core::config::AppConfig;
use sensei_core::domain::entities::User;
use sensei_core::error::SenseiError;
use sensei_services::ops::Andon;
use sensei_services::users::{InMemoryUsersService, UsersService};
use std::sync::Arc;
use uuid::Uuid;

mod common;

/// Connect to the CI-provided test database. Returns None when the env
/// var is absent so the local suite stays green (the gate runs in CI,
/// mirroring `attachments_test.rs` / `today_test.rs`).
async fn db_pool() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — andon scope gate runs in CI");
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
/// any seed. A per-binary lock serializes the migration step (the schema
/// work is idempotent once applied, so later tests skip it instantly).
static DB_MIGRATE_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

/// Apply the migration chain when the database has none (no-op when
/// already migrated). Returns false (test skips) when the chain cannot
/// run.
async fn ensure_migrations(pool: &sqlx::PgPool) -> bool {
    let _guard = DB_MIGRATE_LOCK.lock().await;
    match sensei_db::migrations::run_migrations(pool).await {
        Ok(_) => true,
        Err(e) => {
            eprintln!("SKIP: migration chain unavailable for andon scope gate ({e})");
            false
        }
    }
}

/// One fresh tenant world: a site with a work center, and an operator
/// whose ACTIVE role-slot assignment entitles them to the site and whose
/// active `employee_assignments` row pins them to the work center — the
/// exact context the Andon raise resolves server-side.
struct AndonWorld {
    tenant_id: Uuid,
    site_a: Uuid,
    work_center_a: Uuid,
    operator_id: Uuid,
    operator_email: String,
}

async fn seed_world(pool: &sqlx::PgPool) -> AndonWorld {
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let wc_a = Uuid::new_v4();
    let operator_id = Uuid::new_v4();
    let slot = Uuid::new_v4();
    let assignment = Uuid::new_v4();
    let operator_email = format!("operator-{operator_id}@sensei.test");

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
        .bind(tenant_id)
        .bind("Andon Gate Tenant")
        .bind(format!("andon-gate-{tenant_id}"))
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
         VALUES ($1, $2, $3, $4, 'Andon Work Center', 'assembly')",
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
    .bind(assignment)
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

    AndonWorld {
        tenant_id,
        site_a,
        work_center_a: wc_a,
        operator_id,
        operator_email,
    }
}

/// The authenticated principal for the seeded operator. The permission
/// set is the static expansion of the DB roles (`production_manager`
/// grants the whole `tps:andon:*` family) — the middleware would resolve
/// exactly this set per request in production.
fn operator_principal(world: &AndonWorld) -> AuthenticatedUser {
    let roles = vec!["user".to_string(), "production_manager".to_string()];
    let permissions = RbacService::new().expand_static(&roles);
    AuthenticatedUser {
        user_id: world.operator_id,
        tenant_id: world.tenant_id,
        roles,
        permissions,
        sid: None,
    }
}

/// DB-backed application state. The `users_service` stays IN-MEMORY (with
/// the operator's row carrying the `site_id` hint) so the agent-context
/// builder's user lookup is deterministic; every OTHER service (ops,
/// production, …) is the DB-backed implementation attached by
/// [`AppState::with_db_pool`] — the raise/list/get/… handlers all hit the
/// relational tables.
async fn gate_state(pool: &Arc<sqlx::PgPool>, world: &AndonWorld) -> sensei_api::AppState {
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
    // Keep the in-memory users service authoritative for the per-request
    // user lookups (see the helper docs above).
    state.users_service = users_service;
    state
}

/// Raise one Andon through the real handler as the seeded operator.
async fn raise_andon(
    state: &sensei_api::AppState,
    user: &AuthenticatedUser,
    description: &str,
) -> Andon {
    let req = sensei_api::routes::andon::RaiseAndonRequest {
        issue_type: "quality".to_string(),
        severity: "high".to_string(),
        description: description.to_string(),
        observed_at: None,
    };
    sensei_api::routes::andon::raise_andon(
        user.clone(),
        State(state.clone()),
        HeaderMap::new(),
        Json(req),
    )
    .await
    .expect("an operator with an active site+work-center assignment can raise an andon")
    .0
}

#[tokio::test]
async fn test_raise_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let andon = raise_andon(&state, &user, "Quality issue detected").await;
    assert!(!andon.id.to_string().is_empty());
    assert_eq!(andon.tenant_id, world.tenant_id);
    // The site + work center are SERVER-RESOLVED from the operator's
    // active assignment — never client-supplied.
    assert_eq!(andon.site_id, Some(world.site_a));
    assert_eq!(andon.work_center_id, world.work_center_a);
    assert_eq!(andon.status, "active");
    assert_eq!(andon.raised_by, world.operator_id);
    assert!(!andon.andon_number.is_empty());
}

#[tokio::test]
async fn test_list_andons() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let raised = raise_andon(&state, &user, "Machine stopped").await;

    let resp = sensei_api::routes::andon::list_andons(
        user.clone(),
        State(state),
        Query(sensei_api::routes::andon::ListAndonsParams {
            status: None,
            work_center_id: None,
            page: None,
            per_page: None,
        }),
    )
    .await
    .expect("an entitled operator can list their site's andons");
    let listed = resp.0.data;
    assert!(!listed.is_empty(), "the raised andon must be listed");
    assert!(
        listed.iter().any(|a| a.id == raised.id),
        "the raised andon must appear in the listing"
    );
}

#[tokio::test]
async fn test_get_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let raised = raise_andon(&state, &user, "Material shortage").await;

    let resp = sensei_api::routes::andon::get_andon(user.clone(), State(state), Path(raised.id))
        .await
        .expect("an entitled operator can fetch their site's andon");
    assert_eq!(resp.0.id, raised.id);
}

#[tokio::test]
async fn test_get_andon_not_found() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let err = sensei_api::routes::andon::get_andon(user, State(state), Path(Uuid::new_v4()))
        .await
        .expect_err("an unknown andon id must be NotFound");
    assert!(
        matches!(err, SenseiError::NotFound(_)),
        "expected NotFound, got {err:?}"
    );
}

#[tokio::test]
async fn test_acknowledge_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let raised = raise_andon(&state, &user, "Safety issue").await;

    // The actor is taken from the token — the client-supplied field is
    // ignored (legacy clients may still send it).
    let resp = sensei_api::routes::andon::acknowledge_andon(
        user.clone(),
        State(state),
        Path(raised.id),
        Json(sensei_api::routes::andon::AcknowledgeAndonRequest {
            acknowledged_by: Some(Uuid::new_v4()),
        }),
    )
    .await
    .expect("an entitled operator can acknowledge their site's andon");
    let andon = resp.0;
    assert_eq!(andon.status, "acknowledged");
    assert_eq!(andon.acknowledged_by, Some(world.operator_id));
    assert!(andon.acknowledged_at.is_some());
    assert!(andon.response_time_seconds.is_some());
}

#[tokio::test]
async fn test_resolve_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let raised = raise_andon(&state, &user, "Tooling issue").await;

    // The actor is taken from the token; the client-supplied actor field
    // is ignored.
    let resp = sensei_api::routes::andon::resolve_andon(
        user.clone(),
        State(state),
        Path(raised.id),
        Json(sensei_api::routes::andon::ResolveAndonRequest {
            resolved_by: Some(Uuid::new_v4()),
            resolution: "Replaced faulty tool".to_string(),
        }),
    )
    .await
    .expect("an entitled operator can resolve their site's andon");
    let andon = resp.0;
    assert_eq!(andon.status, "resolved");
    assert_eq!(andon.resolved_by, Some(world.operator_id));
    assert_eq!(andon.resolution.as_deref(), Some("Replaced faulty tool"));
    assert!(andon.resolved_at.is_some());
    assert!(andon.resolution_time_seconds.is_some());
}

#[tokio::test]
async fn test_update_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let raised = raise_andon(&state, &user, "Initial problem").await;

    let resp = sensei_api::routes::andon::update_andon(
        user.clone(),
        State(state),
        Path(raised.id),
        Json(sensei_api::routes::andon::UpdateAndonCommand {
            issue_type: Some("quality".to_string()),
            severity: "high".to_string(),
            description: "Updated problem description".to_string(),
        }),
    )
    .await
    .expect("an entitled operator can update their site's andon");
    let andon = resp.0;
    assert_eq!(andon.description, "Updated problem description");
    assert_eq!(andon.id, raised.id);
}

#[tokio::test]
async fn test_delete_andon() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = operator_principal(&world);

    let raised = raise_andon(&state, &user, "To be deleted").await;

    // Append-only history: production Andon events are never physically
    // deleted — they are voided with a reason.
    let resp = sensei_api::routes::andon::void_andon(
        user.clone(),
        State(state),
        Path(raised.id),
        Json(sensei_api::routes::andon::VoidAndonRequest {
            reason: "false alarm".to_string(),
        }),
    )
    .await
    .expect("an entitled operator can void their site's andon");
    let andon = resp.0;
    assert_eq!(andon.status, "voided");
}

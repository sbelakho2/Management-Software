//! End-to-end tests for work center endpoints.
//!
//! Tests CRUD operations, capacity queries, and efficiency reports
//! for manufacturing work centers.
//!
//! # DB-gated suite (relational single-system-of-record contract)
//!
//! Every Work Center handler persists through the RELATIONAL
//! `work_centers` table (`tps::work_center_repository`) and requires a
//! database pool — the in-memory test harness has no relational tables,
//! sites or role-slot scope authority, so the suite connects to the
//! CI-provided test database (`DATABASE_URL_TEST`), applies the full
//! migration chain and drives the real handlers against DB-backed state
//! with a caller whose role-slot entitlement scopes them to a seeded
//! site. Response-shape expectations follow the relational contract:
//! rows carry `site_id` + `topology_state`; capacity/efficiency derive
//! from relational columns only (utilization is reported as 0 — never
//! fabricated); `work_center_type` must be one of the canonical
//! relational values. Without the environment variable each test skips
//! cleanly (the local in-memory suite stays green), mirroring the
//! pre-existing DB-gated suites (`attachments_test.rs`, `today_test.rs`).

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_auth::rbac::RbacService;
use sensei_core::config::AppConfig;
use sensei_core::domain::entities::User;
use sensei_core::error::SenseiError;
use sensei_services::tps::work_center_repository::RelationalWorkCenter;
use sensei_services::users::{InMemoryUsersService, UsersService};
use std::sync::Arc;
use uuid::Uuid;

mod common;

/// Connect to the CI-provided test database. Returns None when the env
/// var is absent so the local suite stays green (the gate runs in CI).
async fn db_pool() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — work center scope gate runs in CI");
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
            eprintln!("SKIP: migration chain unavailable for work center scope gate ({e})");
            false
        }
    }
}

/// One fresh tenant world: two sites and a manager whose ACTIVE role-slot
/// entitlement covers site A only (site B rows must never leak).
struct WorkCenterWorld {
    tenant_id: Uuid,
    site_a: Uuid,
    site_b: Uuid,
    manager_id: Uuid,
    manager_email: String,
}

async fn seed_world(pool: &sqlx::PgPool) -> WorkCenterWorld {
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let site_b = Uuid::new_v4();
    let manager_id = Uuid::new_v4();
    let slot = Uuid::new_v4();
    let manager_email = format!("manager-{manager_id}@sensei.test");

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
        .bind(tenant_id)
        .bind("Work Center Gate Tenant")
        .bind(format!("wc-gate-{tenant_id}"))
        .execute(pool)
        .await
        .expect("tenant seed");
    for (site, code) in [(site_a, "SITE_A"), (site_b, "SITE_B")] {
        sqlx::query("INSERT INTO sites (id, tenant_id, site_code, name) VALUES ($1, $2, $3, $4)")
            .bind(site)
            .bind(tenant_id)
            .bind(code)
            .bind(code)
            .execute(pool)
            .await
            .expect("site seed");
    }
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, site_id) \
         VALUES ($1, $2, $3, 'Gate Manager', 'x', '{user,production_manager}', $4)",
    )
    .bind(manager_id)
    .bind(tenant_id)
    .bind(&manager_email)
    .bind(site_a)
    .execute(pool)
    .await
    .expect("user seed");
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
    .bind(manager_id)
    .bind(slot)
    .execute(pool)
    .await
    .expect("principal assignment seed");

    WorkCenterWorld {
        tenant_id,
        site_a,
        site_b,
        manager_id,
        manager_email,
    }
}

/// The authenticated principal for the seeded manager (`production_manager`
/// grants `tps:work-center:read` + `tps:work-center:manage`).
fn manager_principal(world: &WorkCenterWorld) -> AuthenticatedUser {
    let roles = vec!["user".to_string(), "production_manager".to_string()];
    let permissions = RbacService::new().expand_static(&roles);
    AuthenticatedUser {
        user_id: world.manager_id,
        tenant_id: world.tenant_id,
        roles,
        permissions,
        sid: None,
    }
}

/// DB-backed application state with the in-memory `users_service` kept
/// authoritative for per-request user lookups (see `andon_test.rs`).
async fn gate_state(pool: &Arc<sqlx::PgPool>, world: &WorkCenterWorld) -> sensei_api::AppState {
    common::setup::pin_test_environment();
    let config = AppConfig::from_env()
        .expect("test configuration must load under pinned env");

    let mut manager = User::new(
        world.tenant_id,
        world.manager_email.clone(),
        "Gate Manager".to_string(),
        "x".to_string(),
    );
    manager.id = world.manager_id;
    manager.roles = vec!["user".to_string(), "production_manager".to_string()];
    manager.site_id = Some(world.site_a);
    let users_service: Arc<dyn UsersService> = Arc::new(InMemoryUsersService::new());
    let seeded = users_service.create_user(manager).await.expect("seed manager");
    assert_eq!(seeded.id, world.manager_id);

    let mut state = sensei_api::AppState::new(config, users_service.clone()).with_db_pool(pool.clone());
    state.users_service = users_service;
    state
}

/// Create one work center through the real handler as the seeded manager
/// (canonical relational type: the DB CHECK admits the lowercase values).
async fn create_work_center(
    state: &sensei_api::AppState,
    user: &AuthenticatedUser,
    world: &WorkCenterWorld,
    name: &str,
) -> RelationalWorkCenter {
    sensei_api::routes::work_centers::create_work_center(
        user.clone(),
        State(state.clone()),
        Json(sensei_api::routes::work_centers::CreateWorkCenterRequest {
            name: name.to_string(),
            work_center_type: "assembly".to_string(),
            site_id: Some(world.site_a),
        }),
    )
    .await
    .expect("a manager can create a work center at their entitled site")
    .0
}

/// Seed a relational work center row directly (for rows the API create
/// cannot express, e.g. capacity columns or foreign-site rows).
async fn seed_work_center_row(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Uuid,
    number: &str,
) {
    sqlx::query(
        "INSERT INTO work_centers \
             (id, tenant_id, site_id, work_center_number, name, work_center_type) \
         VALUES ($1, $2, $3, $4, 'Seeded Work Center', 'test')",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(site_id)
    .bind(number)
    .execute(pool)
    .await
    .expect("work center row seed");
}

#[tokio::test]
async fn test_create_work_center() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    let wc = create_work_center(&state, &user, &world, "Assembly Line 1").await;

    assert_eq!(wc.name, "Assembly Line 1");
    assert_eq!(wc.work_center_type, "assembly");
    assert_eq!(wc.tenant_id, world.tenant_id);
    assert_eq!(wc.site_id, Some(world.site_a), "the asserted site is echoed");
    // Per-tenant numbering: the first work center of this tenant is WC-00001.
    assert_eq!(wc.work_center_number, "WC-00001");
    // Assignment is not verification: the row is created
    // needs_reconciliation with no provenance.
    assert_eq!(wc.topology_state, "needs_reconciliation");
    assert_eq!(wc.topology_assignment_source, None);

    // The relational response shape carries no legacy entity fields: the
    // old EntityStore payload columns (capacity/efficiency/…) are not part
    // of the create contract and never echo back.
    let json = serde_json::to_value(&wc).expect("work center serializes");
    assert!(json.get("efficiency").is_none(), "efficiency is a relational column, not a create field");
    assert!(
        json.get("capacity_per_shift").is_none(),
        "capacity_per_shift is a relational column, not a create field"
    );
}

#[tokio::test]
async fn test_create_work_center_invalid_type_is_rejected() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    // The relational table admits only the canonical lowercase types; a
    // non-canonical value is a clean Validation error (the relational
    // successor of the legacy entity-field validations).
    let err = sensei_api::routes::work_centers::create_work_center(
        user.clone(),
        State(state),
        Json(sensei_api::routes::work_centers::CreateWorkCenterRequest {
            name: "Invalid Type WC".to_string(),
            work_center_type: "Assembly".to_string(),
            site_id: Some(world.site_a),
        }),
    )
    .await
    .expect_err("a non-canonical work_center_type must be rejected");
    assert!(
        matches!(err, SenseiError::Validation(_)),
        "expected Validation, got {err:?}"
    );
}

#[tokio::test]
async fn test_work_center_numbering_is_per_tenant_sequential() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    let mut numbers = Vec::new();
    for _ in 0..3 {
        let wc = create_work_center(&state, &user, &world, "Seq WC").await;
        numbers.push(wc.work_center_number);
    }
    // Numbers are unique and sequential within the tenant.
    let mut unique = numbers.clone();
    unique.sort();
    unique.dedup();
    assert_eq!(unique.len(), 3, "work center numbers must be unique per tenant");
    assert_eq!(unique, vec!["WC-00001", "WC-00002", "WC-00003"]);
}

#[tokio::test]
async fn test_list_work_centers() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    create_work_center(&state, &user, &world, "List WC").await;
    // A site-B row exists too — the site-A caller must never see it.
    seed_work_center_row(&pool, world.tenant_id, world.site_b, "WC-00042").await;

    let resp = sensei_api::routes::work_centers::list_work_centers(
        user.clone(),
        State(state),
        Query(sensei_api::routes::work_centers::ListWorkCentersParams {
            work_center_type: None,
            page: None,
            per_page: None,
        }),
    )
    .await
    .expect("a site-scoped caller can list their entitled rows");
    let listed = resp.0.data;
    assert!(!listed.is_empty(), "the created work center must be listed");
    assert_eq!(
        listed.len(),
        1,
        "the site-B row must not leak into the site-A listing"
    );
    assert_eq!(listed[0].name, "List WC");
}

#[tokio::test]
async fn test_get_work_center() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    let created = create_work_center(&state, &user, &world, "Get WC").await;

    let resp = sensei_api::routes::work_centers::get_work_center(
        user.clone(),
        State(state),
        Path(created.id),
    )
    .await
    .expect("a site-scoped caller can fetch their entitled work center");
    let wc = resp.0;
    assert_eq!(wc.id, created.id);
    assert_eq!(wc.site_id, Some(world.site_a));
}

#[tokio::test]
async fn test_get_work_center_not_found() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    let err = sensei_api::routes::work_centers::get_work_center(
        user.clone(),
        State(state),
        Path(Uuid::new_v4()),
    )
    .await
    .expect_err("an unknown work center id must be NotFound");
    assert!(
        matches!(err, SenseiError::NotFound(_)),
        "expected NotFound, got {err:?}"
    );
}

#[tokio::test]
async fn test_update_work_center() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    let created = create_work_center(&state, &user, &world, "Update WC").await;

    // Update the name (site untouched when site_id is absent).
    let resp = sensei_api::routes::work_centers::update_work_center(
        user.clone(),
        State(state.clone()),
        Path(created.id),
        Json(sensei_api::routes::work_centers::UpdateWorkCenterRequest {
            name: Some("Updated WC Name".to_string()),
            work_center_type: None,
            site_id: None,
        }),
    )
    .await
    .expect("a manager can update their site's work center");
    let wc = resp.0;
    assert_eq!(wc.name, "Updated WC Name");
    assert_eq!(wc.site_id, Some(world.site_a), "the site assignment is untouched");

    // A reassignment to site B is out of the caller's entitlement: 403 in
    // the ROUTE, before the repository runs.
    let err = sensei_api::routes::work_centers::update_work_center(
        user.clone(),
        State(state),
        Path(created.id),
        Json(sensei_api::routes::work_centers::UpdateWorkCenterRequest {
            name: None,
            work_center_type: None,
            site_id: Some(Some(world.site_b)),
        }),
    )
    .await
    .expect_err("reassigning to a foreign site must be forbidden");
    assert!(
        matches!(err, SenseiError::Forbidden(_)),
        "expected Forbidden, got {err:?}"
    );
}

#[tokio::test]
async fn test_deactivate_work_center() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    let created = create_work_center(&state, &user, &world, "Deactivate WC").await;

    let resp = sensei_api::routes::work_centers::deactivate_work_center(
        user.clone(),
        State(state),
        Path(created.id),
    )
    .await
    .expect("a manager can deactivate their site's work center");
    let wc = resp.0;
    assert_eq!(wc.id, created.id);

    // The relational response shape does not carry is_active; verify the
    // server-side flip directly on the row.
    let is_active: bool = sqlx::query_scalar(
        "SELECT is_active FROM work_centers WHERE id = $1 AND tenant_id = $2",
    )
    .bind(created.id)
    .bind(world.tenant_id)
    .fetch_one(&*pool)
    .await
    .expect("deactivated row read");
    assert!(!is_active, "deactivation must flip is_active in the relational table");
}

#[tokio::test]
async fn test_get_work_center_capacity() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    // Seed the relational capacity columns directly (they are not
    // client-writable through the create/update commands): 8 per shift,
    // 2 shifts, efficiency 0.85 (a fraction on the relational row).
    let wc_id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO work_centers \
             (id, tenant_id, site_id, work_center_number, name, work_center_type, \
              capacity_per_shift, shifts_per_day, efficiency) \
         VALUES ($1, $2, $3, $4, 'Capacity WC', 'assembly', 8.0, 2, 0.85)",
    )
    .bind(wc_id)
    .bind(world.tenant_id)
    .bind(world.site_a)
    .bind("WC-00001")
    .execute(&*pool)
    .await
    .expect("capacity row seed");

    let resp = sensei_api::routes::work_centers::get_work_center_capacity(
        user.clone(),
        State(state),
        Path(wc_id),
    )
    .await
    .expect("a site-scoped caller can read their site's capacity");
    let cap = resp.0;
    assert_eq!(cap.total_capacity_per_day, 16.0);
    assert_eq!(cap.effective_capacity_per_day, 13.6);
    // Utilization has no scheduled-hours input on the relational row: it
    // is reported as 0 — never fabricated.
    assert_eq!(cap.utilization_percentage, 0.0);
}

#[tokio::test]
async fn test_get_efficiency_report() {
    let Some(pool) = db_pool().await else { return };
    let pool = Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }
    let world = seed_world(&pool).await;
    let state = gate_state(&pool, &world).await;
    let user = manager_principal(&world);

    // Site-A row (defaults: capacity 0, efficiency fraction 1.0) and a
    // site-B row the site-A caller must not see in the report.
    seed_work_center_row(&pool, world.tenant_id, world.site_a, "WC-00001").await;
    seed_work_center_row(&pool, world.tenant_id, world.site_b, "WC-00002").await;

    let resp = sensei_api::routes::work_centers::get_efficiency_report(
        user.clone(),
        State(state),
    )
    .await
    .expect("a site-scoped caller can read the efficiency report");
    let report = resp.0;
    assert_eq!(
        report.len(),
        1,
        "the report is intersected with the caller's entitlement — site B must not leak"
    );
    assert_eq!(report[0].name, "Seeded Work Center");
    // The relational efficiency is a fraction (default 1.0); the report
    // converts it to a percentage.
    assert_eq!(report[0].efficiency, 100.0);
    // Utilization is never fabricated.
    assert_eq!(report[0].utilization, 0.0);
    assert!(!report[0].is_overloaded);
}

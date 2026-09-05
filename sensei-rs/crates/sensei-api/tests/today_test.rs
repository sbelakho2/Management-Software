//! End-to-end tests for Today (daily snapshot) endpoint.
//!
//! Covers: get today snapshot with aggregated dashboard data.

use axum::extract::State;
use axum::http::StatusCode;
use sensei_auth::middleware::AuthenticatedUser;
use serde_json::Value;
use std::collections::HashSet;
use std::sync::Arc;
use uuid::Uuid;

mod common;

/// Work order payload with all required `WorkOrder` fields (the shared
/// fixture omits id/tenant_id/wo_number/quantity_completed/assigned_to/
/// created_at/updated_at, which the entity requires).
fn work_order_payload(product_name: &str, quantity: i64) -> Value {
    let mut body = common::fixtures::work_order_payload(product_name, quantity);
    body["id"] = serde_json::json!(uuid::Uuid::new_v4().to_string());
    body["tenant_id"] = serde_json::json!(uuid::Uuid::new_v4().to_string());
    body["wo_number"] = serde_json::json!("WO-TEST");
    body["quantity_completed"] = serde_json::json!(0);
    body["assigned_to"] = serde_json::json!([]);
    body["created_at"] = serde_json::json!("2026-01-01T00:00:00Z");
    body["updated_at"] = serde_json::json!("2026-01-01T00:00:00Z");
    body
}

#[tokio::test]
async fn test_get_today_snapshot() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Seed some data so the snapshot has content
    let wo = work_order_payload("Today WO", 10);
    let req = app.post_authenticated("/api/v1/work-orders", &token, wo);
    let _ = app.send_request(req).await;

    let ncr = common::fixtures::ncr_payload("Today NCR");
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, ncr);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/today", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("date"));
    assert!(json.as_object().unwrap().contains_key("work_orders"));
    assert!(json.as_object().unwrap().contains_key("quality"));
    assert!(json.as_object().unwrap().contains_key("operations"));
    assert!(json["work_orders"]
        .as_object()
        .unwrap()
        .contains_key("total_active"));
    assert!(json["quality"]
        .as_object()
        .unwrap()
        .contains_key("active_andons"));
    assert!(json["operations"]
        .as_object()
        .unwrap()
        .contains_key("open_risks"));
}

#[tokio::test]
async fn test_today_snapshot_counts_are_real() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // One active work order.
    let wo = work_order_payload("Counted WO", 10);
    let req = app.post_authenticated("/api/v1/work-orders", &token, wo);
    let _ = app.send_request(req).await;

    // One open NCR and one closed NCR — only the open one counts.
    let req = app.post_authenticated(
        "/api/v1/quality/ncrs",
        &token,
        common::fixtures::ncr_payload("Open NCR"),
    );
    let mut resp = app.send_request(req).await;
    let open_ncr: Value = app.json_body(&mut resp).await;
    let open_ncr_id = open_ncr["id"].as_str().unwrap().to_string();
    let _ = open_ncr_id;

    let req = app.post_authenticated(
        "/api/v1/quality/ncrs",
        &token,
        common::fixtures::ncr_payload("Closed NCR"),
    );
    let mut resp = app.send_request(req).await;
    let closed_ncr: Value = app.json_body(&mut resp).await;
    let closed_ncr_id = closed_ncr["id"].as_str().unwrap().to_string();

    // Close the second NCR via a full-entity PUT with status Closed.
    let mut closed_ncr_body = closed_ncr.clone();
    closed_ncr_body["status"] = serde_json::json!("Closed");
    let req = app.put_authenticated(
        &format!("/api/v1/quality/ncrs/{}", closed_ncr_id),
        &token,
        closed_ncr_body,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/today", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;

    assert_eq!(json["work_orders"]["total_active"], 1);
    assert_eq!(json["work_orders"]["in_progress"], 0);
    assert_eq!(
        json["quality"]["open_ncrs"], 1,
        "closed NCRs must not count as open"
    );
    assert_eq!(json["quality"]["open_capas"], 0);
}

#[tokio::test]
async fn test_today_snapshot_unauthenticated() {
    let app = common::TestApp::new().await;
    let req = app.get("/api/v1/today");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

// ── DB-backed scope gate (twenty-ninth audit Wave B item 9) ─────────────────
//
// The Today dashboard must aggregate WITHIN the caller's effective display
// scope, never tenant-wide: a caller scoped to site A sees ONLY site A's
// numbers even when site B (same tenant) carries many more records.
//
// The API test harness runs DB-less by default, so this test connects to
// the same CI-provided empty database as the sensei-db db_contract gate
// (`DATABASE_URL_TEST`), applies the FULL migration chain (including
// migration 170's quality scope columns) and exercises the real handler
// against DB-backed state. Without the environment variable the test
// skips cleanly (local suite stays green).

/// DROP every table so the FULL migration chain applies to a truly empty
/// database (mirrors the db_contract gate).
async fn drop_all_tables(pool: &sqlx::PgPool) {
    sqlx::query(
        r#"DO $$ DECLARE r RECORD; BEGIN
             FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                 EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
             END LOOP;
         END $$"#,
    )
    .execute(pool)
    .await
    .expect("drop all tables");
}

/// Connect to the CI-provided empty test database. Returns None when the
/// env var is absent so the local suite stays green (the gate runs in CI).
async fn connect() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — today scope gate runs in CI");
        return None;
    };
    sqlx::PgPool::connect(&url).await.ok()
}

/// The DB-gated tests share one database and each DROPS every table
/// before re-applying the full chain — a per-binary lock serializes them.
static TODAY_DB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

#[tokio::test]
async fn test_today_site_scope_never_tenant_totals() {
    let _serial = TODAY_DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    drop_all_tables(&pool).await;
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");
    let pool = Arc::new(pool);

    // ── Fixture: tenant, sites A + B, work centers per site ───────────
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let site_b = Uuid::new_v4();
    let wc_a = Uuid::new_v4();
    let wc_b = Uuid::new_v4();
    let user_id = Uuid::new_v4();
    let slot_a = Uuid::new_v4();
    let assignment_a = Uuid::new_v4();

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'scope', 'scope')")
        .bind(tenant_id)
        .execute(&*pool)
        .await
        .expect("tenant insert");
    for (site, code) in [(site_a, "A"), (site_b, "B")] {
        sqlx::query(
            "INSERT INTO sites (id, tenant_id, name, site_code, timezone) \
             VALUES ($1, $2, $3, $3, 'UTC')",
        )
        .bind(site)
        .bind(tenant_id)
        .bind(code)
        .execute(&*pool)
        .await
        .expect("site insert");
    }
    for (wc, site, code) in [(wc_a, site_a, "WC-A"), (wc_b, site_b, "WC-B")] {
        sqlx::query(
            "INSERT INTO work_centers (id, tenant_id, name, work_center_number, site_id) \
             VALUES ($1, $2, $3, $3, $4)",
        )
        .bind(wc)
        .bind(tenant_id)
        .bind(code)
        .bind(site)
        .execute(&*pool)
        .await
        .expect("work center insert");
    }

    // ── The caller: a user whose ACTIVE role-slot assignment scopes them
    // to site A, with the legacy users.site_id hint pointing at A too.
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, site_id) \
         VALUES ($1, $2, 'user-a@sensei.test', 'User A', 'x', '{user}', $3)",
    )
    .bind(user_id)
    .bind(tenant_id)
    .bind(site_a)
    .execute(&*pool)
    .await
    .expect("user insert");
    sqlx::query(
        "INSERT INTO role_slots (id, tenant_id, role_name, slot_name, scope_site_id) \
         VALUES ($1, $2, 'operator', 'slot-a', $3)",
    )
    .bind(slot_a)
    .bind(tenant_id)
    .bind(site_a)
    .execute(&*pool)
    .await
    .expect("role slot insert");
    sqlx::query(
        "INSERT INTO principal_assignments (id, tenant_id, principal_id, slot_id) \
         VALUES ($1, $2, $3, $4)",
    )
    .bind(assignment_a)
    .bind(tenant_id)
    .bind(user_id)
    .bind(slot_a)
    .execute(&*pool)
    .await
    .expect("assignment insert");

    // ── Records: site A has 1 active WO + 1 open NCR; site B (same
    // tenant) has 7 active WOs + 9 open NCRs. A site-A caller must see
    // ONLY site A's numbers — never 8 WOs / 10 NCRs.
    sqlx::query(
        "INSERT INTO work_orders (id, tenant_id, wo_number, product_id, product_name, quantity, status, work_center_id) \
         VALUES ($1, $2, 'WO-A', $3, 'P-A', 1, 'in_progress', $4)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(Uuid::new_v4())
    .bind(wc_a)
    .execute(&*pool)
    .await
    .expect("site A work order insert");
    for i in 0..7 {
        sqlx::query(
            "INSERT INTO work_orders (id, tenant_id, wo_number, product_id, product_name, quantity, status, work_center_id) \
             VALUES ($1, $2, $3, $4, 'P-B', 1, 'in_progress', $5)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(format!("WO-B-{i}"))
        .bind(Uuid::new_v4())
        .bind(wc_b)
        .execute(&*pool)
        .await
        .expect("site B work order insert");
    }

    // Site A: 1 OPEN NCR stamped to site A.
    sqlx::query(
        "INSERT INTO ncr_reports (id, tenant_id, ncr_number, title, severity, status, reported_by, scope_site_id) \
         VALUES ($1, $2, 'NCR-A', 'A defect', 'minor', 'open', $3, $4)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(user_id)
    .bind(site_a)
    .execute(&*pool)
    .await
    .expect("site A NCR insert");
    // Site B: 9 OPEN NCRs stamped to site B.
    for i in 0..9 {
        sqlx::query(
            "INSERT INTO ncr_reports (id, tenant_id, ncr_number, title, severity, status, reported_by, scope_site_id) \
             VALUES ($1, $2, $3, 'B defect', 'minor', 'open', $4, $5)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(format!("NCR-B-{i}"))
        .bind(user_id)
        .bind(site_b)
        .execute(&*pool)
        .await
        .expect("site B NCR insert");
    }

    // ── DB-backed application state (full service swap) ────────────────
    let app = common::TestApp::new().await;
    let state = app.state.with_db_pool(pool.clone());

    // ── Call the real handler as the site-A user ────────────────────────
    let user = AuthenticatedUser {
        user_id,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["dashboard:read".to_string()]),
    };
    let resp = sensei_api::routes::today::get_today_snapshot(user, State(state))
        .await
        .expect("today snapshot must resolve for a site-scoped caller");
    let snap = resp.0;

    // The response is labeled with the caller's operating scope (site A)…
    assert_eq!(snap.scope.site_id, Some(site_a), "scope must echo site A");
    // …and the counters are site A's — NEVER the tenant totals.
    assert_eq!(
        snap.work_orders.total_active, 1,
        "site A has 1 active WO — site B's 7 must NOT leak in (never 8)"
    );
    assert_eq!(
        snap.work_orders.in_progress, 1,
        "site A's single active WO is in_progress"
    );
    assert_eq!(
        snap.quality.open_ncrs, 1,
        "site A has 1 open NCR — site B's 9 must NOT leak in (never 10)"
    );
    assert_eq!(
        snap.quality.open_capas, 0,
        "no CAPAs were seeded — zero is the honest count"
    );
}

// ── Site-local "today" boundaries (thirtieth-audit item 15) ─────────────────
//
// The date-bounded counters must use the SITE's local calendar day, never a
// UTC `date_naive()` comparison: near local midnight a UTC instant belongs
// to a different UTC date than its site-local date (2026-09-04 23:30 UTC is
// already 2026-09-05 00:30 at a UTC+1 site, and 2026-09-05 23:30 local is
// 2026-09-06 04:30 UTC at a UTC-5 site). A work order completed inside that
// window must count as "completed today" on its site, and the SAME
// implementation must give every site its own day in a multi-site union.

/// The UTC instant `local_time_of_day` into the site's CURRENT local day
/// (resolved from the DB with the same `AT TIME ZONE` arithmetic the
/// handler uses).
async fn local_day_offset_utc(
    pool: &sqlx::PgPool,
    tz: &str,
    offset: &str,
) -> chrono::DateTime<chrono::Utc> {
    sqlx::query_scalar(
        "SELECT (((NOW() AT TIME ZONE $1)::date)::timestamp + $2::interval) \
                AT TIME ZONE $1",
    )
    .bind(tz)
    .bind(offset)
    .fetch_one(pool)
    .await
    .expect("local-day offset must resolve")
}

/// The site's CURRENT local date (the label the handler computes).
async fn local_today(pool: &sqlx::PgPool, tz: &str) -> chrono::NaiveDate {
    sqlx::query_scalar("SELECT (NOW() AT TIME ZONE $1)::date")
        .bind(tz)
        .fetch_one(pool)
        .await
        .expect("local today must resolve")
}

/// Seed the tenant/sites/work centers/users/role-slot fixture shared by the
/// DB-gated today tests. Returns (tenant, site_a, site_b, wc_a, wc_b).
#[allow(clippy::type_complexity)]
async fn seed_scope_fixture(
    pool: &sqlx::PgPool,
    tz_a: &str,
    tz_b: &str,
) -> (Uuid, Uuid, Uuid, Uuid, Uuid) {
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let site_b = Uuid::new_v4();
    let wc_a = Uuid::new_v4();
    let wc_b = Uuid::new_v4();

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'scope', 'scope')")
        .bind(tenant_id)
        .execute(pool)
        .await
        .expect("tenant insert");
    for (site, code, tz) in [(site_a, "A", tz_a), (site_b, "B", tz_b)] {
        sqlx::query(
            "INSERT INTO sites (id, tenant_id, name, site_code, timezone) \
             VALUES ($1, $2, $3, $3, $4)",
        )
        .bind(site)
        .bind(tenant_id)
        .bind(code)
        .bind(tz)
        .execute(pool)
        .await
        .expect("site insert");
    }
    for (wc, site, code) in [(wc_a, site_a, "WC-A"), (wc_b, site_b, "WC-B")] {
        sqlx::query(
            "INSERT INTO work_centers (id, tenant_id, name, work_center_number, site_id) \
             VALUES ($1, $2, $3, $3, $4)",
        )
        .bind(wc)
        .bind(tenant_id)
        .bind(code)
        .bind(site)
        .execute(pool)
        .await
        .expect("work center insert");
    }
    (tenant_id, site_a, site_b, wc_a, wc_b)
}

/// Seed a work order with an explicit completion/update instant.
async fn seed_work_order(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    wc_id: Uuid,
    number: &str,
    status: &str,
    updated_at: chrono::DateTime<chrono::Utc>,
) {
    sqlx::query(
        "INSERT INTO work_orders \
             (id, tenant_id, wo_number, product_id, product_name, quantity, status, work_center_id, updated_at) \
         VALUES ($1, $2, $3, $4, 'P', 1, $5, $6, $7)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(number)
    .bind(Uuid::new_v4())
    .bind(status)
    .bind(wc_id)
    .bind(updated_at)
    .execute(pool)
    .await
    .expect("work order insert");
}

/// Seed a site-scoped user (site hint + active role-slot assignment).
async fn seed_site_user(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    user_id: Uuid,
    site_id: Uuid,
    email: &str,
) {
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, site_id) \
         VALUES ($1, $2, $3, 'User', 'x', '{user}', $4)",
    )
    .bind(user_id)
    .bind(tenant_id)
    .bind(email)
    .bind(site_id)
    .execute(pool)
    .await
    .expect("user insert");
    let slot_id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO role_slots (id, tenant_id, role_name, slot_name, scope_site_id) \
         VALUES ($1, $2, 'operator', $3, $4)",
    )
    .bind(slot_id)
    .bind(tenant_id)
    .bind(format!("slot-{user_id}"))
    .bind(site_id)
    .execute(pool)
    .await
    .expect("role slot insert");
    sqlx::query(
        "INSERT INTO principal_assignments (id, tenant_id, principal_id, slot_id) \
         VALUES ($1, $2, $3, $4)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(user_id)
    .bind(slot_id)
    .execute(pool)
    .await
    .expect("assignment insert");
}

/// Seed an unscoped user with one role-slot assignment per granted site
/// (used by the multi-site union test).
async fn seed_multi_site_user(pool: &sqlx::PgPool, tenant_id: Uuid, user_id: Uuid, sites: &[Uuid]) {
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash, roles) \
         VALUES ($1, $2, 'union@sensei.test', 'Union User', 'x', '{user}')",
    )
    .bind(user_id)
    .bind(tenant_id)
    .execute(pool)
    .await
    .expect("user insert");
    for (idx, site) in sites.iter().enumerate() {
        let slot_id = Uuid::new_v4();
        sqlx::query(
            "INSERT INTO role_slots (id, tenant_id, role_name, slot_name, scope_site_id) \
             VALUES ($1, $2, 'operator', $3, $4)",
        )
        .bind(slot_id)
        .bind(tenant_id)
        .bind(format!("slot-{user_id}-{idx}"))
        .bind(site)
        .execute(pool)
        .await
        .expect("role slot insert");
        sqlx::query(
            "INSERT INTO principal_assignments (id, tenant_id, principal_id, slot_id) \
             VALUES ($1, $2, $3, $4)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(user_id)
        .bind(slot_id)
        .execute(pool)
        .await
        .expect("assignment insert");
    }
}

#[tokio::test]
async fn test_today_completed_counts_the_site_local_day_across_the_utc_boundary() {
    let _serial = TODAY_DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    drop_all_tables(&pool).await;
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");
    let pool = Arc::new(pool);

    // A is UTC+1 (Etc/GMT-1), B is UTC-5 (Etc/GMT+5) — fixed offsets, no
    // DST, so the boundary mismatch directions never flip.
    let (tenant_id, site_a, site_b, wc_a, wc_b) =
        seed_scope_fixture(&pool, "Etc/GMT-1", "Etc/GMT+5").await;
    let user_a = Uuid::new_v4();
    seed_site_user(&pool, tenant_id, user_a, site_a, "user-a@sensei.test").await;
    let user_b = Uuid::new_v4();
    seed_site_user(&pool, tenant_id, user_b, site_b, "user-b@sensei.test").await;

    // ── Boundary-mismatch completions, derived from the LIVE local days
    // so the test is deterministic at any wall-clock instant:
    //  * A: local 00:30 today — its UTC date is ALWAYS the previous UTC
    //    day (local midnight of a UTC+1 site is 23:00 UTC the day
    //    before), so `updated_at.date_naive()` never equals the
    //    site-local date.
    //  * B: local 23:30 today — its UTC date is ALWAYS the NEXT UTC day
    //    (local midnight of a UTC-5 site is 05:00 UTC the same day).
    let a_local_today = local_today(&pool, "Etc/GMT-1").await;
    let b_local_today = local_today(&pool, "Etc/GMT+5").await;
    let completed_at_a = local_day_offset_utc(&pool, "Etc/GMT-1", "30 minutes").await;
    let completed_at_b = local_day_offset_utc(&pool, "Etc/GMT+5", "23 hours 30 minutes").await;
    // Yesterday locally at A (also 30 min before A's local midnight).
    let completed_yesterday_at_a =
        local_day_offset_utc(&pool, "Etc/GMT-1", "-12 hours 30 minutes").await;
    // The preconditions that make these the audit's midnight mismatch:
    assert_ne!(
        completed_at_a.date_naive(),
        a_local_today,
        "A's 00:30-local instant must sit on the PREVIOUS UTC date"
    );
    assert_ne!(
        completed_at_b.date_naive(),
        b_local_today,
        "B's 23:30-local instant must sit on the NEXT UTC date"
    );
    assert_ne!(
        completed_yesterday_at_a.date_naive(),
        a_local_today,
        "the yesterday-local completion must not be today's UTC date either"
    );

    seed_work_order(
        &pool,
        tenant_id,
        wc_a,
        "WO-A-TODAY",
        "completed",
        completed_at_a,
    )
    .await;
    seed_work_order(
        &pool,
        tenant_id,
        wc_a,
        "WO-A-YESTERDAY",
        "completed",
        completed_yesterday_at_a,
    )
    .await;
    seed_work_order(
        &pool,
        tenant_id,
        wc_b,
        "WO-B-TODAY",
        "completed",
        completed_at_b,
    )
    .await;

    let app = common::TestApp::new().await;
    let state = app.state.with_db_pool(pool.clone());

    let user = AuthenticatedUser {
        user_id: user_a,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["dashboard:read".to_string()]),
    };
    let resp = sensei_api::routes::today::get_today_snapshot(user, State(state.clone()))
        .await
        .expect("today snapshot must resolve for the site-A caller");
    let snap = resp.0;
    assert_eq!(snap.scope.site_id, Some(site_a));
    assert_eq!(
        snap.work_orders.completed_today, 1,
        "the WO completed at A's local 00:30 (UTC date = yesterday) is \
         TODAY at A; the yesterday-local completion is not, and B's WO is \
         invisible to A"
    );
    assert_eq!(snap.work_orders.total_active, 0);

    let user = AuthenticatedUser {
        user_id: user_b,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["dashboard:read".to_string()]),
    };
    let resp = sensei_api::routes::today::get_today_snapshot(user, State(state))
        .await
        .expect("today snapshot must resolve for the site-B caller");
    let snap = resp.0;
    assert_eq!(snap.scope.site_id, Some(site_b));
    assert_eq!(
        snap.work_orders.completed_today, 1,
        "the WO completed at B's local 23:30 (UTC date = tomorrow) is \
         TODAY at B — a UTC date_naive() comparison would count it for \
         the wrong day or not at all"
    );
    assert_eq!(snap.work_orders.total_active, 0);
}

#[tokio::test]
async fn test_today_multisite_union_counts_each_site_on_its_own_local_day() {
    let _serial = TODAY_DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    drop_all_tables(&pool).await;
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");
    let pool = Arc::new(pool);

    let (tenant_id, site_a, site_b, wc_a, wc_b) =
        seed_scope_fixture(&pool, "Etc/GMT-1", "Etc/GMT+5").await;
    let union_user = Uuid::new_v4();
    // The caller is granted BOTH sites but carries NO site hint, so no
    // operating focus exists: the display is the authorized union.
    seed_multi_site_user(&pool, tenant_id, union_user, &[site_a, site_b]).await;

    // Both sites complete a WO inside THEIR local day at instants whose
    // UTC dates are the other site's (or neither site's) date:
    //  * A's row: local 00:30 today  (= previous UTC day 23:30)
    //  * B's row: local 23:30 today  (= next UTC day 04:30)
    // With ONE shared (UTC) day boundary both rows fall outside; per-site
    // windows must count both.
    let completed_at_a = local_day_offset_utc(&pool, "Etc/GMT-1", "30 minutes").await;
    let completed_at_b = local_day_offset_utc(&pool, "Etc/GMT+5", "23 hours 30 minutes").await;
    seed_work_order(
        &pool,
        tenant_id,
        wc_a,
        "WO-A-UNION",
        "completed",
        completed_at_a,
    )
    .await;
    seed_work_order(
        &pool,
        tenant_id,
        wc_b,
        "WO-B-UNION",
        "completed",
        completed_at_b,
    )
    .await;

    let app = common::TestApp::new().await;
    let state = app.state.with_db_pool(pool.clone());

    let user = AuthenticatedUser {
        user_id: union_user,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["dashboard:read".to_string()]),
    };
    let resp = sensei_api::routes::today::get_today_snapshot(user, State(state))
        .await
        .expect("today snapshot must resolve for the union caller");
    let snap = resp.0;
    assert_eq!(snap.scope.site_id, None, "no focus — the union displays");
    assert_eq!(
        snap.work_orders.completed_today, 2,
        "each site's WO completed on ITS OWN local day — a single UTC/\
         shared boundary would count neither (their UTC dates differ from \
         every shared date)"
    );
}

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

#[tokio::test]
async fn test_today_site_scope_never_tenant_totals() {
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

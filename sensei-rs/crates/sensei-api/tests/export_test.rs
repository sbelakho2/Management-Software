//! End-to-end tests for the export route handler.
//!
//! Covers:
//! - GET /api/v1/export/{entity_type}?format=...&tenant_id=...
//! - Supported formats: pdf, csv, xlsx
//! - Unsupported format returns validation error
//! - Unauthenticated access

use axum::http::StatusCode;
use serde_json::Value;
use uuid::Uuid;

mod common;

// ── Export NCR ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_export_ncr_csv() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/ncr?format=csv&tenant_id={}", tenant_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("csv"));
}

#[tokio::test]
async fn test_export_capa_pdf() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/capa?format=pdf&tenant_id={}", tenant_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("pdf"));
}

#[tokio::test]
async fn test_export_audit_xlsx() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/audit?format=xlsx&tenant_id={}", tenant_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    assert!(content_type.contains("spreadsheetml"));
}

#[tokio::test]
async fn test_export_work_order_csv() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!(
            "/api/v1/export/work-order?format=csv&tenant_id={}",
            tenant_id
        ),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_export_invalid_format() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/export/ncr?format=doc&tenant_id={}", tenant_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_export_unknown_entity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!(
            "/api/v1/export/unknown-entity?format=csv&tenant_id={}",
            tenant_id
        ),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_export_unauthenticated() {
    let app = common::TestApp::new().await;
    let tenant_id = Uuid::new_v4();

    let req = app.get(&format!(
        "/api/v1/export/ncr?format=csv&tenant_id={}",
        tenant_id
    ));
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_export_ignores_query_tenant_id_and_uses_token_tenant() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create an NCR in the admin's tenant (inline payload: the fixture's
    // "Major" severity is not a valid NcSeverity variant).
    let ncr_body = serde_json::json!({
        "title": "Exportable NCR",
        "description": "An exportable NCR",
        "nc_type": "Product",
        "severity": "High",
        "is_recurrence": false,
    });
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, ncr_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let ncr: Value = app.json_body(&mut resp).await;
    let ncr_id = ncr["id"].as_str().unwrap().to_string();

    // The export handler must ignore the client-supplied tenant_id and use
    // the authenticated user's tenant: an arbitrary foreign tenant_id must
    // NOT change what data is returned (no cross-tenant leak).
    let foreign_tenant = Uuid::new_v4();
    let req = app.get_authenticated(
        &format!(
            "/api/v1/export/ncr?id={}&format=csv&tenant_id={}",
            ncr_id, foreign_tenant
        ),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let text = app.response_text(&mut resp).await;
    assert!(
        text.contains("Exportable NCR"),
        "export should return the token tenant's data, got: {text}"
    );
}

#[tokio::test]
async fn test_export_foreign_tenant_cannot_read_ncr_by_id() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Admin creates an NCR in their tenant (inline payload with a valid
    // NcSeverity variant).
    let ncr_body = serde_json::json!({
        "title": "Private NCR",
        "description": "A private NCR",
        "nc_type": "Product",
        "severity": "High",
        "is_recurrence": false,
    });
    let req = app.post_authenticated("/api/v1/quality/ncrs", &token, ncr_body);
    let mut resp = app.send_request(req).await;
    let ncr: Value = app.json_body(&mut resp).await;
    let ncr_id = ncr["id"].as_str().unwrap().to_string();

    // A user in a different tenant (registration provisions a fresh tenant)
    // must not be able to export the admin's NCR by id.
    let reg_body = serde_json::json!({
        "email": "outsider@sensei.test",
        "password": "StrongPass123!",
        "name": "Outsider",
    });
    let req = app.post("/api/v1/auth/register", reg_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let reg: Value = app.json_body(&mut resp).await;
    let outsider_token = reg["access_token"].as_str().unwrap().to_string();

    let req = app.get_authenticated(
        &format!("/api/v1/export/ncr?id={}&format=csv", ncr_id),
        &outsider_token,
    );
    let resp = app.send_request(req).await;
    assert!(
        matches!(resp.status(), StatusCode::NOT_FOUND | StatusCode::FORBIDDEN),
        "foreign tenant must not see another tenant's exported entity (404 or 403)"
    );
}

#[tokio::test]
async fn test_export_invalid_date_filter_is_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/export/ncr?format=csv&date_from=not-a-date", &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

// ── Inspection export scope + status (thirtieth-audit item 16) ─────────────
//
// The inspection export must apply the SAME scope discipline as the quality
// get/list surface (never a tenant-wide page) and the `status` argument
// must be MATERIAL: a mismatched status returns ZERO rows instead of every
// row.

use axum::extract::{Path, Query, State};
use sensei_auth::middleware::AuthenticatedUser;
use std::collections::HashSet;
use std::sync::Arc;

/// Read the response body of a direct route-handler call as text.
async fn response_text(response: axum::response::Response) -> String {
    let bytes = axum::body::to_bytes(response.into_body(), 10 * 1024 * 1024)
        .await
        .expect("read body");
    String::from_utf8(bytes.to_vec()).unwrap_or_default()
}

/// Dev / DB-less mode: the in-memory quality stores carry no site
/// dimension, but the status filter must still be applied to the fetched
/// rows (previously it was ignored entirely).
#[tokio::test]
async fn test_export_inspection_status_filter_is_applied_in_dev_mode() {
    let app = common::TestApp::new().await;

    // Seed one completed FAI + one planned self-inspection in the admin
    // tenant through the in-memory quality service.
    let now = chrono::Utc::now();
    let fai = sensei_services::quality::FirstArticleInspection {
        id: Uuid::new_v4(),
        fai_number: "FAI-STATUS-1".to_string(),
        part_number: "P-1".to_string(),
        part_name: "Part 1".to_string(),
        revision: "A".to_string(),
        customer: None,
        status: "Completed".to_string(),
        characteristics: Vec::new(),
        inspector_id: None,
        created_at: now,
        updated_at: now,
    };
    app.state
        .quality_service
        .create_first_article_inspection(app.admin_tenant_id, fai)
        .await
        .expect("seed FAI");
    let si = sensei_services::quality::SelfInspection {
        id: Uuid::new_v4(),
        inspection_number: "SI-STATUS-1".to_string(),
        product_id: None,
        work_order_id: None,
        station_id: None,
        operator_id: None,
        status: "Planned".to_string(),
        result: None,
        checks: Vec::new(),
        created_at: now,
        completed_at: None,
    };
    app.state
        .quality_service
        .create_self_inspection(app.admin_tenant_id, si)
        .await
        .expect("seed self-inspection");

    let token = app.login_as_admin().await;

    // The legacy dev-mode merge emits mixed-shape rows (FAI rows carry
    // `fai_number`, self rows `inspection_number`), and the CSV writer
    // uses the FIRST row's keys as headers — so presence is asserted by
    // data-row count (total non-empty lines minus the header line) and
    // by the status values, which every row shape carries.
    let csv_rows = |text: &str| -> usize {
        text.lines()
            .filter(|l| !l.trim().is_empty())
            .count()
            .saturating_sub(1)
    };

    // No filter: both rows are exported.
    let req = app.get_authenticated("/api/v1/export/inspection?format=csv", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let text = app.response_text(&mut resp).await;
    assert_eq!(
        csv_rows(&text),
        2,
        "unfiltered export must include both rows: {text}"
    );
    assert!(
        text.contains("Completed"),
        "unfiltered export must include the FAI: {text}"
    );
    assert!(
        text.contains("Planned"),
        "unfiltered export must include the self-inspection: {text}"
    );

    // status=planned: only the planned self-inspection remains.
    let req = app.get_authenticated(
        "/api/v1/export/inspection?format=csv&status=planned",
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let text = app.response_text(&mut resp).await;
    assert_eq!(
        csv_rows(&text),
        1,
        "planned filter must keep one row: {text}"
    );
    assert!(
        text.contains("Planned"),
        "planned filter must keep the planned row: {text}"
    );
    assert!(
        !text.contains("Completed"),
        "the completed FAI must not survive a planned filter: {text}"
    );

    // status=completed: only the completed FAI remains (the status
    // comparison is case-insensitive like the SQL LOWER equality).
    let req = app.get_authenticated(
        "/api/v1/export/inspection?format=csv&status=Completed",
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let text = app.response_text(&mut resp).await;
    assert_eq!(
        csv_rows(&text),
        1,
        "completed filter must keep one row: {text}"
    );
    assert!(
        text.contains("Completed"),
        "completed filter must keep the FAI: {text}"
    );
    assert!(
        !text.contains("Planned"),
        "the planned self-inspection must not survive a completed filter: {text}"
    );
}

// ── DB-backed gate: canonical scoped read (migration-170 stamp) ────────────

/// Connect to the CI-provided empty test database. Returns None when the
/// env var is absent so the local suite stays green (the gate runs in CI).
async fn connect() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — inspection export gate runs in CI");
        return None;
    };
    sqlx::PgPool::connect(&url).await.ok()
}

/// The DB-gated tests share one database; a per-binary lock serializes
/// the drop-everything migrations.
static EXPORT_DB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

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

#[tokio::test]
async fn test_export_inspection_never_leaks_other_sites_and_filters_status_in_sql() {
    let _serial = EXPORT_DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    drop_all_tables(&pool).await;
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");
    let pool = Arc::new(pool);

    // ── Fixture: tenant, sites A + B, users with site-A / site-B grants ──
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let site_b = Uuid::new_v4();
    let user_a = Uuid::new_v4();

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
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, site_id) \
         VALUES ($1, $2, 'user-a@sensei.test', 'User A', 'x', '{user}', $3)",
    )
    .bind(user_a)
    .bind(tenant_id)
    .bind(site_a)
    .execute(&*pool)
    .await
    .expect("user insert");
    let slot_a = Uuid::new_v4();
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
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(user_a)
    .bind(slot_a)
    .execute(&*pool)
    .await
    .expect("assignment insert");

    // ── Canonical `inspections` rows (migration 170 stamp): two at site
    // A (completed + planned) and one completed at site B.
    for (number, site, status) in [
        ("INS-A-1", site_a, "completed"),
        ("INS-A-2", site_a, "planned"),
        ("INS-B-1", site_b, "completed"),
    ] {
        sqlx::query(
            "INSERT INTO inspections \
                 (id, tenant_id, inspection_number, inspection_type, result, status, \
                  scope_site_id, scope_work_center_id) \
             VALUES ($1, $2, $3, 'incoming', 'pass', $4, $5, NULL)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(number)
        .bind(status)
        .bind(site)
        .execute(&*pool)
        .await
        .expect("inspection insert");
    }

    // ── DB-backed state + direct handler call as the site-A user ────────
    let app = common::TestApp::new().await;
    let state = app.state.with_db_pool(pool.clone());
    let user = AuthenticatedUser {
        user_id: user_a,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["quality:inspection:read".to_string()]),
    };

    let export_csv = |params: sensei_api::routes::export::ExportParams| async {
        let resp = sensei_api::routes::export::export_entity(
            user.clone(),
            State(state.clone()),
            Path("inspection".to_string()),
            Query(params),
        )
        .await
        .expect("inspection export must succeed for a site-scoped caller");
        response_text(resp).await
    };

    // Unfiltered: site A sees ONLY its own inspections.
    let text = export_csv(sensei_api::routes::export::ExportParams {
        format: "csv".to_string(),
        id: None,
        status: None,
        date_from: None,
        date_to: None,
    })
    .await;
    assert!(
        text.contains("INS-A-1"),
        "site A export must include its completed inspection"
    );
    assert!(
        text.contains("INS-A-2"),
        "site A export must include its planned inspection"
    );
    assert!(
        !text.contains("INS-B-1"),
        "a Site-B inspection must NEVER appear in a Site-A user's export: {text}"
    );

    // status=completed (both sites have one): site B's still never
    // appears; site A's planned row is filtered out at the SQL level.
    let text = export_csv(sensei_api::routes::export::ExportParams {
        format: "csv".to_string(),
        id: None,
        status: Some("completed".to_string()),
        date_from: None,
        date_to: None,
    })
    .await;
    assert!(
        text.contains("INS-A-1"),
        "completed filter must keep site A's completed row"
    );
    assert!(
        !text.contains("INS-A-2"),
        "the planned row must be filtered out: {text}"
    );
    assert!(
        !text.contains("INS-B-1"),
        "the status-matched Site-B row must still be scope-invisible: {text}"
    );

    // Mismatched status: NO rows at all — the filter is applied, not
    // fetched-broadly-and-ignored.
    let text = export_csv(sensei_api::routes::export::ExportParams {
        format: "csv".to_string(),
        id: None,
        status: Some("in_progress".to_string()),
        date_from: None,
        date_to: None,
    })
    .await;
    assert!(
        !text.contains("INS-A-1") && !text.contains("INS-A-2") && !text.contains("INS-B-1"),
        "a status with no matching rows must return NO rows rather than all rows: {text}"
    );
}

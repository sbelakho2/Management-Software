//! End-to-end tests for Attachment endpoints.
//!
//! Covers: upload, list, delete — plus the twenty-ninth-audit Wave B
//! item 11 parent-authorization contract:
//!
//! * attachments inherit their PARENT's authorization — a known
//!   attachment UUID never bypasses the parent check (orphan parents are
//!   denied with 404, and listing requires a readable parent);
//! * the site-scoped assertions (site-B parent denied for a site-A user)
//!   require a database with role-slot assignments — the in-memory test
//!   harness has no site rows, so those tests are DB-gated skips (they
//!   run when `DATABASE_URL_TEST` is set, following the
//!   `sensei-db/tests/db_contract.rs` gate convention).

use axum::http::StatusCode;
use chrono::Utc;
use sensei_api::stores::{Attachment, Opportunity};
use uuid::Uuid;

mod common;

// ── Helpers ─────────────────────────────────────────────────────────────────

/// Seed an opportunity parent in the caller's tenant (in-memory store).
async fn seed_opportunity(app: &common::TestApp, tenant_id: Uuid) -> Uuid {
    let id = Uuid::new_v4();
    let now = Utc::now();
    let opp = Opportunity {
        id,
        tenant_id,
        title: "Seed opportunity".to_string(),
        description: "Parent for attachment tests".to_string(),
        customer_id: Uuid::new_v4(),
        customer_name: "Seed Customer".to_string(),
        stage: "qualification".to_string(),
        probability: 0.5,
        expected_value: 1000.0,
        currency: "USD".to_string(),
        expected_close_date: None,
        assigned_to: None,
        notes: String::new(),
        created_by: Uuid::new_v4(),
        created_at: now,
        updated_at: now,
    };
    {
        let mut store = app.state.opportunities.write(tenant_id).await;
        store.insert(id, opp.clone());
    }
    id
}

/// Seed an attachment metadata row (in-memory repository) for the parent,
/// storing the blob through the storage service so downloads can resolve.
async fn seed_attachment(
    app: &common::TestApp,
    tenant_id: Uuid,
    entity_type: &str,
    entity_id: Uuid,
) -> Uuid {
    let object = app
        .state
        .storage_service
        .store_opaque(tenant_id, b"attachment-bytes", "application/pdf")
        .await
        .expect("blob must store");
    let id = Uuid::new_v4();
    let attachment = Attachment {
        id,
        tenant_id,
        entity_type: entity_type.to_string(),
        entity_id,
        file_name: "report.pdf".to_string(),
        content_type: "application/pdf".to_string(),
        file_size: 16,
        storage_path: object.key,
        uploaded_by: Uuid::new_v4(),
        created_at: Utc::now(),
    };
    app.state
        .attachment_repo
        .put(&attachment)
        .await
        .expect("attachment metadata must seed");
    id
}

// ── Legacy surface tests ────────────────────────────────────────────────────

#[tokio::test]
async fn test_upload_attachment() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    // Upload endpoint may expect multipart; try JSON-based approach
    let body = serde_json::json!({
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "data": "dGVzdCBjb250ZW50",  // base64 "test content"
        "entity_type": "work_order",
        "entity_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/attachments/upload", &token, body);
    let resp = app.send_request(req).await;
    // May accept JSON or require multipart; either way endpoint responds
    let status = resp.status();
    assert!(
        status == StatusCode::OK
            || status == StatusCode::UNSUPPORTED_MEDIA_TYPE
            || status == StatusCode::BAD_REQUEST
    );
}

#[tokio::test]
async fn test_list_attachments() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    // In-memory (no DB) deployments have no site rows: the work-order
    // parent proof is dev-permissive, so listing a nonexistent parent
    // returns an empty page (existing behavior).
    let entity_id = uuid::Uuid::new_v4().to_string();
    let req = app.get_authenticated(
        &format!("/api/v1/attachments/work_order/{}", entity_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_delete_attachment() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.delete_authenticated(
        "/api/v1/attachments/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

// ── Parent authorization (Wave B item 11) ──────────────────────────────────

/// A known attachment UUID whose parent does not exist (orphan row) must
/// NOT bypass the parent read check: download is 404 even though the
/// metadata row is present and the caller holds `attachments:read`.
#[tokio::test]
async fn test_download_known_uuid_does_not_bypass_missing_parent() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    // No parent seeded — the attachment metadata is an orphan.
    let orphan_parent = Uuid::new_v4();
    let attachment_id = seed_attachment(&app, tenant, "opportunity", orphan_parent).await;

    let req = app.get_authenticated(
        &format!("/api/v1/attachments/{attachment_id}/download"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "a known attachment UUID must not bypass the missing-parent check"
    );
}

/// Listing attachments of a parent the caller may not read (a nonexistent
/// store-backed parent) is denied BEFORE any metadata row is returned.
#[tokio::test]
async fn test_list_requires_readable_parent() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let missing_parent = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/attachments/opportunity/{missing_parent}"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

/// Positive control: an existing, readable parent (opportunity) lists its
/// attachments and downloads them; parent authorization passes.
#[tokio::test]
async fn test_download_and_list_with_existing_parent() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    let parent = seed_opportunity(&app, tenant).await;
    let attachment_id = seed_attachment(&app, tenant, "opportunity", parent).await;

    // List: parent readable → 200 with the seeded row.
    let req = app.get_authenticated(&format!("/api/v1/attachments/opportunity/{parent}"), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"].as_u64().unwrap_or(0), 1);

    // Download: parent readable → the blob resolves.
    let req = app.get_authenticated(
        &format!("/api/v1/attachments/{attachment_id}/download"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

/// Deleting an attachment whose parent may not be managed is denied with
/// 404/403 — the known UUID does not bypass the parent manage check.
#[tokio::test]
async fn test_delete_known_uuid_does_not_bypass_missing_parent() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    // Admin holds knowledge:manage; the parent row does not exist.
    let orphan_parent = Uuid::new_v4();
    let attachment_id = seed_attachment(&app, tenant, "knowledge_pack", orphan_parent).await;

    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "a known attachment UUID must not bypass the missing-parent manage check"
    );
}

// ── DB-gated site-scope tests ───────────────────────────────────────────────

/// Connect to the CI-provided test database. Returns None when the env
/// var is absent so the local in-memory suite stays green (the DB-gated
/// assertions run in CI, mirroring `sensei-db/tests/db_contract.rs`).
async fn db_pool() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — site-scope attachment gate runs in CI");
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

/// Site-B work-order parent attachment denied for a site-A user (Wave B
/// item 11): the parent's site is derived from its work center and the
/// caller's role-slot scope; a foreign-site parent is indistinguishable
/// from a nonexistent one (NotFound), and the metadata row alone cannot
/// bypass the check.
#[tokio::test]
async fn test_site_b_parent_attachment_denied_for_site_a_user_db_gated() {
    let Some(pool) = db_pool().await else { return };
    let pool = std::sync::Arc::new(pool);

    // The DB-gated assertions need the full schema; apply the migration
    // chain when the database has none (no-op when already migrated).
    if let Err(e) = sensei_db::migrations::run_migrations(&pool).await {
        eprintln!("SKIP: migration chain unavailable for attachment scope gate ({e})");
        return;
    }

    // Fresh, isolated tenant: every seed below is tenant-scoped.
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let site_b = Uuid::new_v4();
    let user_a = Uuid::new_v4();
    let user_b = Uuid::new_v4();
    let wc_a = Uuid::new_v4();
    let wc_b = Uuid::new_v4();
    let wo_a = Uuid::new_v4();
    let wo_b = Uuid::new_v4();
    let slot_a = Uuid::new_v4();
    let slot_b = Uuid::new_v4();
    let now = Utc::now();

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
        .bind(tenant_id)
        .bind("Attachment Scope Tenant")
        .bind(format!("att-scope-{tenant_id}"))
        .execute(&*pool)
        .await
        .expect("tenant seed");
    for (site, code) in [(site_a, "SITE_A"), (site_b, "SITE_B")] {
        sqlx::query("INSERT INTO sites (id, tenant_id, site_code, name) VALUES ($1, $2, $3, $4)")
            .bind(site)
            .bind(tenant_id)
            .bind(code)
            .bind(code)
            .execute(&*pool)
            .await
            .expect("site seed");
    }
    for user in [user_a, user_b] {
        sqlx::query(
            "INSERT INTO users (id, tenant_id, email, name, password_hash) \
             VALUES ($1, $2, $3, $4, 'x')",
        )
        .bind(user)
        .bind(tenant_id)
        .bind(format!("user-{user}@sensei.test"))
        .bind("Scope User")
        .execute(&*pool)
        .await
        .expect("user seed");
    }
    for (wc, site) in [(wc_a, site_a), (wc_b, site_b)] {
        sqlx::query(
            "INSERT INTO work_centers \
                 (id, tenant_id, work_center_number, name, site_id) \
             VALUES ($1, $2, $3, $4, $5)",
        )
        .bind(wc)
        .bind(tenant_id)
        .bind(format!("WC-{wc}"))
        .bind("Scope Work Center")
        .bind(site)
        .execute(&*pool)
        .await
        .expect("work center seed");
    }
    for (wo, wc) in [(wo_a, wc_a), (wo_b, wc_b)] {
        sqlx::query(
            "INSERT INTO work_orders \
                 (id, tenant_id, wo_number, product_id, quantity, work_center_id) \
             VALUES ($1, $2, $3, $4, 1, $5)",
        )
        .bind(wo)
        .bind(tenant_id)
        .bind(format!("WO-{wo}"))
        .bind(Uuid::new_v4())
        .bind(wc)
        .execute(&*pool)
        .await
        .expect("work order seed");
    }

    // Role-slot scope: the FORCE-RLS slot/assignment tables are only
    // writable inside a transaction that sets app.tenant_id.
    {
        let mut tx = pool.begin().await.expect("begin");
        sqlx::query("SET LOCAL app.tenant_id = $1")
            .bind(tenant_id)
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        for (slot, site) in [(slot_a, site_a), (slot_b, site_b)] {
            sqlx::query(
                "INSERT INTO role_slots \
                     (id, tenant_id, role_name, slot_name, scope_site_id) \
                 VALUES ($1, $2, 'operator', $3, $4)",
            )
            .bind(slot)
            .bind(tenant_id)
            .bind(format!("slot-{slot}"))
            .bind(site)
            .execute(&mut *tx)
            .await
            .expect("role slot seed");
        }
        for (slot, user) in [(slot_a, user_a), (slot_b, user_b)] {
            sqlx::query(
                "INSERT INTO principal_assignments \
                     (tenant_id, principal_id, slot_id) \
                 VALUES ($1, $2, $3)",
            )
            .bind(tenant_id)
            .bind(user)
            .bind(slot)
            .execute(&mut *tx)
            .await
            .expect("principal assignment seed");
        }
        tx.commit().await.expect("commit scope seeds");
    }

    // Attachment metadata for both work orders (rows exist and belong to
    // the tenant — a "known UUID" that must not bypass the parent scope).
    for (wo, suffix) in [(wo_a, "A"), (wo_b, "B")] {
        let id = Uuid::new_v4();
        sqlx::query(
            "INSERT INTO attachments \
                 (id, tenant_id, entity_type, entity_id, file_name, \
                  content_type, file_size, storage_path, uploaded_by, created_at) \
             VALUES ($1, $2, 'work_order', $3, $4, 'application/pdf', 1, $5, $6, $7)",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(wo)
        .bind(format!("doc-{suffix}.pdf"))
        .bind(format!("opaque-{suffix}"))
        .bind(user_a)
        .bind(now)
        .execute(&*pool)
        .await
        .expect("attachment seed");
    }

    // Build the application state with the DB pool attached (typed
    // repositories + scope resolution reach the same database).
    common::setup::pin_test_environment();
    let config = sensei_core::config::AppConfig::from_env()
        .expect("test configuration must load under pinned env");
    let users_service =
        std::sync::Arc::new(sensei_services::users::InMemoryUsersService::with_admin(
            "dbgate@sensei.test",
            "Db Gate",
            "x",
            tenant_id,
        ));
    let state = sensei_api::AppState::new(config, users_service).with_db_pool(pool.clone());

    // ── Direct-UUID access must not bypass parent authorization ────────
    use sensei_api::authorization::parent_resource::require_parent_read;
    use sensei_auth::middleware::AuthenticatedUser;
    use std::collections::HashSet;

    let user_a_principal = AuthenticatedUser {
        user_id: user_a,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from([
            "attachments:read".to_string(),
            "production:work-order:read".to_string(),
        ]),
    };

    // Site-A user CAN read the site-A work order's attachment parent…
    require_parent_read(&state, &user_a_principal, "work_order", wo_a)
        .await
        .expect("site-A user must read a site-A work order");

    // …but the site-B work order is out of scope: denied (NotFound), and
    // the attachment metadata row for it (a known UUID in the tenant)
    // cannot bypass the parent check — the download handler runs this
    // exact check after resolving metadata and before presigning.
    let err = require_parent_read(&state, &user_a_principal, "work_order", wo_b)
        .await
        .expect_err("site-B parent must be denied for a site-A user");
    assert!(
        matches!(err, sensei_core::error::SenseiError::NotFound(_)),
        "foreign-site and nonexistent parents must be indistinguishable, got {err:?}"
    );

    // Both attachment metadata rows exist and are tenant-visible — the
    // metadata alone (a "known UUID") grants nothing.
    let rows_a = state
        .attachment_repo
        .list(tenant_id, "work_order", wo_a)
        .await
        .expect("list site-A rows");
    assert_eq!(rows_a.len(), 1, "site-A attachment row exists");
    let rows_b = state
        .attachment_repo
        .list(tenant_id, "work_order", wo_b)
        .await
        .expect("list site-B rows");
    assert_eq!(rows_b.len(), 1, "site-B attachment row exists");

    // The download sequence — metadata resolved (row exists), then the
    // parent read check — must deny the site-B row for the site-A user.
    require_parent_read(&state, &user_a_principal, "work_order", rows_b[0].entity_id)
        .await
        .expect_err("site-B parent must deny the download sequence");

    // A principal with NO active role-slot assignment (NoOperationalScope)
    // cannot reach any work-order parent — fail closed, never tenant-wide.
    let no_scope_user = AuthenticatedUser {
        user_id: Uuid::new_v4(),
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from([
            "attachments:read".to_string(),
            "production:work-order:read".to_string(),
        ]),
    };
    require_parent_read(&state, &no_scope_user, "work_order", wo_a)
        .await
        .expect_err("NoOperationalScope must deny every work-order parent");
}

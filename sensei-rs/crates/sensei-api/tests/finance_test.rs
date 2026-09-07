//! End-to-end tests for finance route handlers.
//!
//! Covers:
//! - POST/GET /api/v1/finance/invoices (NARROW CreateInvoiceRequest —
//!   client-side totals are rejected, totals are server-derived)
//! - POST/GET /api/v1/finance/payments (NARROW RecordPaymentRequest)
//! - POST/GET /api/v1/finance/budgets
//! - POST/GET /api/v1/finance/journal-entries
//! - POST/GET /api/v1/finance/cost-rollup
//! - Error cases (not_found, unauthenticated)

use axum::http::StatusCode;
use chrono::Utc;
use serde_json::Value;
use uuid::Uuid;

mod common;

// ── Invoices ──────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_get_invoice() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "customer_id": Uuid::new_v4().to_string(),
        "customer_name": "Test Customer",
        "line_items": [
            {"description": "Service A", "quantity": 2, "unit_price": 1500.00},
            {"description": "Service B", "quantity": 1, "unit_price": 500.00}
        ],
        "tax_percentage": 10.0,
        "currency": "USD",
        "due_date": now,
        "notes": "net 30",
    });
    let req = app.post_authenticated("/api/v1/finance/invoices", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let invoice_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!invoice_id.is_empty());
    let inv_num = json["invoice_number"].as_str().unwrap_or("").to_string();
    assert!(
        inv_num.starts_with("INV-"),
        "invoice_number should start with INV-, got {inv_num}"
    );
    // Thirty-first audit: totals are SERVER-DERIVED from the narrow
    // request (2×1500 + 1×500 = 3500 subtotal; 10% tax = 350).
    assert_eq!(json["status"], "draft");
    assert_eq!(
        json["subtotal"].as_f64().unwrap_or(0.0),
        3500.0,
        "subtotal must be derived server-side"
    );
    assert_eq!(
        json["tax_amount"].as_f64().unwrap_or(0.0),
        350.0,
        "tax amount must be derived server-side"
    );
    assert_eq!(
        json["total_amount"].as_f64().unwrap_or(0.0),
        3850.0,
        "total must be derived server-side"
    );
    assert_eq!(json["line_items"][0]["total"], 3000.0);
    assert!(
        json["created_by"].as_str().is_some_and(|s| !s.is_empty()),
        "actor is server-set from the token"
    );

    // Get the invoice
    let req_get =
        app.get_authenticated(&format!("/api/v1/finance/invoices/{}", invoice_id), &token);
    let mut resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
    let json_get: Value = app.json_body(&mut resp_get).await;
    let inv_num_get = json_get["invoice_number"].as_str().unwrap_or("");
    assert!(
        inv_num_get.starts_with("INV-"),
        "invoice_number should start with INV-, got {inv_num_get}"
    );
}

/// Thirty-first audit: a request that smuggles CLIENT-SIDE totals /
/// identity is REJECTED (`deny_unknown_fields`) — never silently
/// trusted or ignored.
#[tokio::test]
async fn test_create_invoice_rejects_client_side_totals() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "invoice_number": "INV-FORGED",
        "customer_id": Uuid::new_v4().to_string(),
        "customer_name": "Sneaky Customer",
        "status": "paid",
        "line_items": [
            {"description": "Service A", "quantity": 1, "unit_price": 100.00, "total": 1.00}
        ],
        "subtotal": 1.00,
        "tax_percentage": 0.0,
        "tax_amount": 0.0,
        "total_amount": 1.00,
        "currency": "USD",
        "due_date": now,
        "paid_at": now,
        "notes": "",
        "created_by": Uuid::new_v4().to_string(),
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/finance/invoices", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::UNPROCESSABLE_ENTITY,
        "client-side totals must be rejected (deny_unknown_fields)"
    );
}

/// Thirty-first audit: a request with extra unknown fields is rejected
/// even when no totals are smuggled.
#[tokio::test]
async fn test_create_invoice_rejects_unknown_fields() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "customer_id": Uuid::new_v4().to_string(),
        "customer_name": "Test Customer",
        "line_items": [{"description": "A", "quantity": 1, "unit_price": 10.0}],
        "tax_percentage": 0.0,
        "currency": "USD",
        "due_date": Utc::now().to_rfc3339(),
        "notes": "",
        "work_center_id": Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/finance/invoices", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn test_list_invoices() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/finance/invoices", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
}

#[tokio::test]
async fn test_get_invoice_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let id = Uuid::nil().to_string();
    let req = app.get_authenticated(&format!("/api/v1/finance/invoices/{}", id), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

// ── Payments ──────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_record_and_list_payments() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "invoice_id": Uuid::new_v4().to_string(),
        "amount": 500.00,
        "currency": "USD",
        "payment_method": "bank_transfer",
        "reference": "REF-001",
    });
    let req = app.post_authenticated("/api/v1/finance/payments", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let payment_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!payment_id.is_empty());
    // Thirty-first audit: id/number/tenant/received_at/actor are
    // server-generated — the response carries the server's values.
    assert!(
        json["payment_number"]
            .as_str()
            .is_some_and(|n| n.starts_with("PAY-")),
        "payment_number should start with PAY-"
    );
    assert!(json["received_at"].is_string());
    assert!(
        json["created_by"].as_str().is_some_and(|s| !s.is_empty()),
        "actor is server-set from the token"
    );

    // List payments
    let req_list = app.get_authenticated("/api/v1/finance/payments", &token);
    let mut resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
    let json_list: Value = app.json_body(&mut resp_list).await;
    assert!(json_list.is_object());
}

/// Thirty-first audit: a client cannot fabricate the payment identity —
/// sending id/number/tenant/received time/actor is rejected.
#[tokio::test]
async fn test_record_payment_rejects_client_identity() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "payment_number": "PAY-FORGED",
        "invoice_id": Uuid::new_v4().to_string(),
        "amount": 500.00,
        "currency": "USD",
        "payment_method": "cash",
        "reference": "REF",
        "received_at": now,
        "created_by": Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/finance/payments", &token, body);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::UNPROCESSABLE_ENTITY,
        "client-supplied payment identity must be rejected"
    );
}

// ── Budgets ───────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_and_get_budget() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "fiscal_year": 2026,
        "department": "Engineering",
        "category": "R&D",
        "allocated_amount": 100000.0,
        "spent_amount": 0.0,
        "remaining_amount": 100000.0,
    });
    let req = app.post_authenticated("/api/v1/finance/budgets", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let budget_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!budget_id.is_empty());

    // Get the budget
    let req_get = app.get_authenticated(&format!("/api/v1/finance/budgets/{}", budget_id), &token);
    let mut resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
    let json_get: Value = app.json_body(&mut resp_get).await;
    assert_eq!(json_get["department"], "Engineering");
}

#[tokio::test]
async fn test_allocate_budget() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Create budget
    let create_body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "fiscal_year": 2026,
        "department": "Engineering",
        "category": "R&D",
        "allocated_amount": 50000.0,
        "spent_amount": 0.0,
        "remaining_amount": 50000.0,
    });
    let req = app.post_authenticated("/api/v1/finance/budgets", &token, create_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let budget_id = json["id"].as_str().unwrap().to_string();

    // Allocate
    let allocate_body = serde_json::json!({ "amount": 10000.0 });
    let req_alloc = app.post_authenticated(
        &format!("/api/v1/finance/budgets/{}/allocate", budget_id),
        &token,
        allocate_body,
    );
    let resp_alloc = app.send_request(req_alloc).await;
    assert_eq!(resp_alloc.status(), StatusCode::OK);
}

// ── Journal Entries ───────────────────────────────────────────────────────────

#[tokio::test]
async fn test_post_and_list_journal_entries() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "entry_number": "JE-001",
        "description": "Test journal entry",
        "debit_account": "1000",
        "credit_account": "2000",
        "amount": 1000.00,
        "currency": "USD",
        "entry_date": now,
        "posted_by": user_id.to_string(),
    });
    let req = app.post_authenticated("/api/v1/finance/journal-entries", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let entry_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!entry_id.is_empty());

    // List
    let req_list = app.get_authenticated("/api/v1/finance/journal-entries", &token);
    let resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
}

// ── Cost Rollup ───────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_run_cost_rollup() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let product_id = Uuid::new_v4();
    let body = serde_json::json!({
        "product_id": product_id.to_string(),
    });
    let req = app.post_authenticated("/api/v1/finance/cost-rollup", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.is_object());
}

// ── Unauthenticated ───────────────────────────────────────────────────────────

#[tokio::test]
async fn test_finance_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/finance/invoices");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

// ── AP 3-Way Matching ─────────────────────────────────────────────────────────

/// Build an app whose in-memory finance service is seeded with a PO and a
/// goods receipt, and return (app, po_id, receipt_id, product_id).
async fn seeded_three_way_app() -> (common::TestApp, Uuid, Uuid, Uuid) {
    use sensei_api::state::AppState;
    use sensei_core::config::AppConfig;
    use sensei_services::finance::InMemoryFinanceService;
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    common::setup::pin_test_environment();
    let password = "TestAdmin123!";
    let hash = sensei_auth::password::hash_password(password).unwrap();
    let tenant_id = Uuid::new_v4();
    let users_service =
        InMemoryUsersService::with_admin("admin@sensei.test", "Admin User", &hash, tenant_id);
    let users_service = Arc::new(users_service) as Arc<dyn UsersService>;
    let config = AppConfig::from_env().unwrap();
    let mut state = AppState::new(config, users_service);

    // Seed the PO and receipt before building the router.
    let po_id = Uuid::new_v4();
    let receipt_id = Uuid::new_v4();
    let product_id = Uuid::new_v4();
    let seeded = InMemoryFinanceService::default();
    seeded
        .seed_purchase_order(tenant_id, po_id, vec![(product_id, 100.0)])
        .await;
    seeded
        .seed_goods_receipt(tenant_id, receipt_id, po_id, vec![(product_id, 100.0)])
        .await;
    state.finance_service = Arc::new(seeded);

    let mut app = common::TestApp::from_state(state);
    app.admin_password = password.to_string();
    app.admin_tenant_id = tenant_id;
    (app, po_id, receipt_id, product_id)
}

#[tokio::test]
async fn test_three_way_match_endpoint() {
    let (app, po_id, receipt_id, product_id) = seeded_three_way_app().await;
    let token = app.login_as_admin().await;
    let now = Utc::now().to_rfc3339();

    // Create the invoice through the API (same service instance) — the
    // NARROW create contract (thirty-first audit): product_id rides on
    // the line items, totals are server-derived.
    let invoice_body = serde_json::json!({
        "customer_id": Uuid::new_v4().to_string(),
        "customer_name": "Supplier Co",
        "line_items": [
            {"description": "Part", "quantity": 100, "unit_price": 5.0, "product_id": product_id.to_string()}
        ],
        "tax_percentage": 0.0,
        "currency": "USD",
        "due_date": now,
        "notes": "",
    });
    let req = app.post_authenticated("/api/v1/finance/invoices", &token, invoice_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let invoice: Value = app.json_body(&mut resp).await;
    let invoice_id = invoice["id"].as_str().unwrap().to_string();

    // Match the PO, receipt, and invoice.
    let match_body = serde_json::json!({
        "po_id": po_id.to_string(),
        "receipt_ids": [receipt_id.to_string()],
        "invoice_id": invoice_id,
    });
    let req = app.post_authenticated("/api/v1/finance/three-way-match", &token, match_body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["verdict"], "Matched");
    let lines = json["lines"].as_array().expect("lines should be an array");
    assert_eq!(lines.len(), 1);
    assert_eq!(lines[0]["status"], "Matched");
    // Field names match the service's ThreeWayLineResult.
    assert_eq!(lines[0]["po_quantity"], 100.0);
    assert_eq!(lines[0]["received_quantity"], 100.0);
    assert_eq!(lines[0]["invoiced_quantity"], 100.0);
}

#[tokio::test]
async fn test_three_way_match_unknown_po() {
    let (app, _, receipt_id, _) = seeded_three_way_app().await;
    let token = app.login_as_admin().await;

    let match_body = serde_json::json!({
        "po_id": Uuid::new_v4().to_string(),
        "receipt_ids": [receipt_id.to_string()],
        "invoice_id": Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/finance/three-way-match", &token, match_body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

// ── DB-gated suite (thirty-first audit) ─────────────────────────────────────
//
// Drives the REAL route handlers against `DatabaseFinanceService` on a
// scratch database (`DATABASE_URL_TEST`), then asserts the persisted
// state: server-derived totals, the atomic business-audit + outbox rows,
// and idempotency replay protection. Without the environment variable
// each test skips cleanly (mirroring andon_test.rs / today_test.rs).

#[cfg(test)]
mod db_gate {
    use super::*;
    use axum::extract::{Path, Query, State};
    use axum::Json;
    use sensei_api::middleware::idempotency::OptionalIdempotencyKey;
    use sensei_api::routes::finance::{
        create_invoice, get_invoice, list_invoices, mark_invoice_paid, record_payment,
        ListInvoicesParams, ListPaymentsParams, MarkInvoicePaidRequest,
    };
    use sensei_auth::middleware::AuthenticatedUser;
    use sensei_auth::rbac::RbacService;
    use sensei_core::config::AppConfig;
    use sensei_core::db::TenantTx;
    use sensei_core::domain::entities::User;
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    /// Connect to the CI-provided test database. Returns None when the env
    /// var is absent so the local suite stays green.
    async fn db_pool() -> Option<sqlx::PgPool> {
        let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
            eprintln!("SKIP: DATABASE_URL_TEST not set — finance DB gate runs in CI");
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

    static DB_MIGRATE_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

    /// Apply the migration chain when the database has none (no-op when
    /// already migrated). Returns false (test skips) when it cannot run.
    async fn ensure_migrations(pool: &sqlx::PgPool) -> bool {
        let _guard = DB_MIGRATE_LOCK.lock().await;
        match sensei_db::migrations::run_migrations(pool).await {
            Ok(_) => true,
            Err(e) => {
                eprintln!("SKIP: migration chain unavailable for finance gate ({e})");
                false
            }
        }
    }

    struct FinanceWorld {
        tenant_id: Uuid,
        finance_user_id: Uuid,
        finance_email: String,
    }

    /// One fresh tenant world: a tenant + the users row every FK points
    /// at. Every test seeds its own tenant so the shared scratch DB stays
    /// isolated.
    async fn seed_world(pool: &sqlx::PgPool) -> FinanceWorld {
        let tenant_id = Uuid::new_v4();
        let finance_user_id = Uuid::new_v4();
        let finance_email = format!("finance-{finance_user_id}@sensei.test");

        sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
            .bind(tenant_id)
            .bind("Finance Gate Tenant")
            .bind(format!("finance-gate-{tenant_id}"))
            .execute(pool)
            .await
            .expect("tenant seed");
        sqlx::query(
            "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, site_id) \
             VALUES ($1, $2, $3, 'Finance Gate', 'x', '{user,finance_manager}', NULL)",
        )
        .bind(finance_user_id)
        .bind(tenant_id)
        .bind(&finance_email)
        .execute(pool)
        .await
        .expect("user seed");

        FinanceWorld {
            tenant_id,
            finance_user_id,
            finance_email,
        }
    }

    /// DB-backed application state: the users service stays IN-MEMORY
    /// (deterministic user lookups), every other service — including
    /// finance — is the DB-backed implementation attached by
    /// `AppState::with_db_pool`.
    async fn gate_state(pool: &Arc<sqlx::PgPool>, world: &FinanceWorld) -> sensei_api::AppState {
        common::setup::pin_test_environment();
        let config = AppConfig::from_env().expect("test configuration must load under pinned env");

        let mut finance_user = User::new(
            world.tenant_id,
            world.finance_email.clone(),
            "Finance Gate".to_string(),
            "x".to_string(),
        );
        finance_user.id = world.finance_user_id;
        finance_user.roles = vec!["user".to_string(), "finance_manager".to_string()];
        let users_service: Arc<dyn UsersService> = Arc::new(InMemoryUsersService::new());
        let seeded = users_service
            .create_user(finance_user)
            .await
            .expect("seed finance user");
        assert_eq!(seeded.id, world.finance_user_id);

        let mut state =
            sensei_api::AppState::new(config, users_service.clone()).with_db_pool(pool.clone());
        state.users_service = users_service;
        state
    }

    fn finance_principal(world: &FinanceWorld) -> AuthenticatedUser {
        let roles = vec!["user".to_string(), "finance_manager".to_string()];
        let permissions = RbacService::new().expand_static(&roles);
        AuthenticatedUser {
            user_id: world.finance_user_id,
            tenant_id: world.tenant_id,
            roles,
            permissions,
            sid: None,
        }
    }

    fn narrow_create_body() -> Value {
        serde_json::json!({
            "customer_id": Uuid::new_v4().to_string(),
            "customer_name": "Acme DB",
            "line_items": [
                {"description": "Widget A", "quantity": 10, "unit_price": 25.0},
                {"description": "Widget B", "quantity": 5, "unit_price": 50.0}
            ],
            "tax_percentage": 10.0,
            "currency": "USD",
            "due_date": (Utc::now() + chrono::Duration::days(30)).to_rfc3339(),
            "notes": "db gate",
        })
    }

    async fn claim_idempotency(pool: &sqlx::PgPool, key: &str) {
        sqlx::query(
            "INSERT INTO idempotency_records (key, request_hash, state, status, expires_at) \
             VALUES ($1, 'hash', 'started', NULL, NOW() + interval '1 hour')",
        )
        .bind(key)
        .execute(pool)
        .await
        .expect("idempotency claim seed");
    }

    async fn audit_count(pool: &sqlx::PgPool, tenant_id: Uuid, action: &str) -> i64 {
        let mut db = TenantTx::begin(pool, tenant_id)
            .await
            .expect("tenant tx begin");
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM business_audit_log WHERE tenant_id = $1 AND action = $2",
        )
        .bind(tenant_id)
        .bind(action)
        .fetch_one(&mut **db.tx())
        .await
        .expect("audit read");
        db.commit().await.expect("audit tx close");
        count
    }

    async fn outbox_count(pool: &sqlx::PgPool, tenant_id: Uuid, entity_type: &str) -> i64 {
        let mut db = TenantTx::begin(pool, tenant_id)
            .await
            .expect("tenant tx begin");
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM outbox_events              WHERE tenant_id = $1 AND event_type LIKE $2",
        )
        .bind(tenant_id)
        .bind(format!("sensei.{entity_type}.%"))
        .fetch_one(&mut **db.tx())
        .await
        .expect("outbox read");
        db.commit().await.expect("outbox tx close");
        count
    }

    async fn idempotency_state(pool: &sqlx::PgPool, key: &str) -> String {
        sqlx::query_scalar("SELECT state FROM idempotency_records WHERE key = $1")
            .bind(key)
            .fetch_one(pool)
            .await
            .expect("idempotency read")
    }

    /// Create one invoice through the REAL handler on the DB-backed
    /// service with an idempotency claim, and return its id.
    async fn create_invoice_via_handler(
        state: &sensei_api::AppState,
        user: &AuthenticatedUser,
        body: Value,
        idem_key: Option<String>,
    ) -> Uuid {
        // The JSON body must deserialize into the NARROW contract — the
        // same boundary a real HTTP client crosses (a smuggled total
        // would fail right here).
        let request: sensei_contracts::finance::CreateInvoiceRequest =
            serde_json::from_value(body).expect("narrow create body parses");
        let resp = create_invoice(
            user.clone(),
            OptionalIdempotencyKey(idem_key),
            State(state.clone()),
            Json(request),
        )
        .await
        .expect("finance manager can create an invoice");
        let invoice = resp.0;
        assert_eq!(invoice.tenant_id, user.tenant_id);
        assert_eq!(invoice.created_by, user.user_id);
        invoice.id
    }

    #[tokio::test]
    async fn db_create_invoice_derives_totals_and_audits_atomically() {
        let Some(pool) = db_pool().await else { return };
        let pool = Arc::new(pool);
        if !ensure_migrations(&pool).await {
            return;
        }
        let world = seed_world(&pool).await;
        let state = gate_state(&pool, &world).await;
        let user = finance_principal(&world);
        let key = format!("fin-gate-inv-{}-{}", world.tenant_id, uuid_v4_short());
        claim_idempotency(&pool, &key).await;

        let invoice_id =
            create_invoice_via_handler(&state, &user, narrow_create_body(), Some(key.clone()))
                .await;

        // Server-derived totals persisted in Postgres.
        let fetched = state
            .finance_service
            .get_invoice(world.tenant_id, invoice_id)
            .await
            .expect("invoice persisted");
        assert!(
            fetched.invoice_number.starts_with("INV-"),
            "invoice number is server-generated"
        );
        assert_eq!(fetched.status, "draft");
        // 10×25 + 5×50 = 500 subtotal; 10% tax = 50; total = 550.
        assert_eq!(fetched.subtotal, dec(500.0));
        assert_eq!(fetched.tax_amount, dec(50.0));
        assert_eq!(fetched.total_amount, dec(550.0));
        assert_eq!(fetched.line_items[0].total, dec(250.0));

        // Atomic business audit + outbox rows in the same tx.
        assert_eq!(
            audit_count(&pool, world.tenant_id, "invoice.created").await,
            1,
            "business audit row must be written atomically"
        );
        assert_eq!(
            outbox_count(&pool, world.tenant_id, "invoice").await,
            1,
            "outbox event must be written atomically"
        );
        // Idempotency completion committed in the SAME transaction.
        assert_eq!(idempotency_state(&pool, &key).await, "completed");

        // Replay with the same key is rejected instead of duplicating.
        let replay_body: sensei_contracts::finance::CreateInvoiceRequest =
            serde_json::from_value(narrow_create_body()).expect("narrow create body parses");
        let replay = create_invoice(
            user.clone(),
            OptionalIdempotencyKey(Some(key.clone())),
            State(state.clone()),
            Json(replay_body),
        )
        .await;
        assert!(
            matches!(replay, Err(sensei_core::error::SenseiError::Conflict(_))),
            "idempotency replay must be rejected as a conflict"
        );
    }

    #[tokio::test]
    async fn db_record_payment_and_mark_invoice_paid() {
        let Some(pool) = db_pool().await else { return };
        let pool = Arc::new(pool);
        if !ensure_migrations(&pool).await {
            return;
        }
        let world = seed_world(&pool).await;
        let state = gate_state(&pool, &world).await;
        let user = finance_principal(&world);

        // Invoice total: 2×10 + 3×20 = 80 (no tax).
        let body = serde_json::json!({
            "customer_id": Uuid::new_v4().to_string(),
            "customer_name": "Pay Co",
            "line_items": [
                {"description": "Part A", "quantity": 2, "unit_price": 10.0},
                {"description": "Part B", "quantity": 3, "unit_price": 20.0}
            ],
            "tax_percentage": 0.0,
            "currency": "USD",
            "due_date": (Utc::now() + chrono::Duration::days(30)).to_rfc3339(),
            "notes": "",
        });
        let invoice_id = create_invoice_via_handler(&state, &user, body, None).await;

        // Record ONE covering payment via the narrow contract.
        let pay_body: sensei_contracts::finance::RecordPaymentRequest =
            serde_json::from_value(serde_json::json!({
                "invoice_id": invoice_id.to_string(),
                "amount": 80.0,
                "currency": "USD",
                "payment_method": "bank_transfer",
                "reference": "DB-REF-001",
            }))
            .expect("narrow payment body parses");
        let pay_resp = record_payment(
            user.clone(),
            OptionalIdempotencyKey(None),
            State(state.clone()),
            Json(pay_body),
        )
        .await
        .expect("finance manager can record a payment");
        let payment = pay_resp.0;
        assert_eq!(payment.tenant_id, world.tenant_id);
        assert!(
            payment.payment_number.starts_with("PAY-"),
            "payment number is server-generated"
        );
        assert_eq!(payment.created_by, user.user_id);
        assert_eq!(
            audit_count(&pool, world.tenant_id, "payment.recorded").await,
            1,
            "payment audit row must be written atomically"
        );
        assert_eq!(
            outbox_count(&pool, world.tenant_id, "payment").await,
            1,
            "payment outbox event must be written atomically"
        );

        // List payments shows the persisted row.
        let list = list_invoices_payments(&state, &user, invoice_id).await;
        assert_eq!(list.len(), 1);
        assert_eq!(list[0]["amount"], 80.0);

        // Mark the invoice paid through the handler.
        let paid = mark_invoice_paid(
            user.clone(),
            State(state.clone()),
            Path(invoice_id),
            Json(MarkInvoicePaidRequest {
                payment_id: payment.id,
            }),
        )
        .await
        .expect("covering payment lets a finance manager mark the invoice paid");
        assert_eq!(paid.0.status, "paid");
        assert!(paid.0.paid_at.is_some());

        let fetched = state
            .finance_service
            .get_invoice(world.tenant_id, invoice_id)
            .await
            .expect("invoice still readable");
        assert_eq!(fetched.status, "paid");
    }

    #[tokio::test]
    async fn db_list_and_get_invoices_round_trip() {
        let Some(pool) = db_pool().await else { return };
        let pool = Arc::new(pool);
        if !ensure_migrations(&pool).await {
            return;
        }
        let world = seed_world(&pool).await;
        let state = gate_state(&pool, &world).await;
        let user = finance_principal(&world);

        let invoice_id =
            create_invoice_via_handler(&state, &user, narrow_create_body(), None).await;

        // get through the handler.
        let got = get_invoice(user.clone(), State(state.clone()), Path(invoice_id))
            .await
            .expect("invoice readable via handler");
        assert_eq!(got.0.id, invoice_id);

        // list through the handler: the pagination envelope contains the row.
        let page = list_invoices(
            user.clone(),
            State(state.clone()),
            Query(ListInvoicesParams {
                status: None,
                page: None,
                per_page: None,
            }),
        )
        .await
        .expect("finance manager can list invoices");
        assert!(
            page.0.data.iter().any(|i| i.id == invoice_id),
            "created invoice must appear in the tenant list"
        );

        // Unknown id → NotFound.
        let missing = get_invoice(user.clone(), State(state.clone()), Path(Uuid::nil())).await;
        assert!(
            matches!(missing, Err(sensei_core::error::SenseiError::NotFound(_))),
            "a foreign/nonexistent invoice is NotFound"
        );
    }

    /// Small helpers (mirror the finance module test helpers).
    fn dec(v: f64) -> rust_decimal::Decimal {
        rust_decimal::Decimal::from_f64_retain(v).unwrap_or(rust_decimal::Decimal::ZERO)
    }

    fn uuid_v4_short() -> String {
        Uuid::new_v4().as_simple().to_string()
    }

    /// List payments for an invoice through the handler and return the
    /// raw JSON items.
    async fn list_invoices_payments(
        state: &sensei_api::AppState,
        user: &AuthenticatedUser,
        invoice_id: Uuid,
    ) -> Vec<Value> {
        let resp = sensei_api::routes::finance::list_payments(
            user.clone(),
            State(state.clone()),
            Query(ListPaymentsParams {
                invoice_id: Some(invoice_id),
                page: None,
                per_page: None,
            }),
        )
        .await
        .expect("finance manager can list payments");
        serde_json::to_value(resp.0.data)
            .expect("payments serialize")
            .as_array()
            .cloned()
            .unwrap_or_default()
    }
}

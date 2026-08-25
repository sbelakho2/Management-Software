//! End-to-end tests for finance route handlers.
//!
//! Covers:
//! - POST/GET /api/v1/finance/invoices
//! - POST/GET /api/v1/finance/payments
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
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "invoice_number": "INV-001",
        "customer_id": Uuid::new_v4().to_string(),
        "customer_name": "Test Customer",
        "status": "draft",
        "line_items": [
            {"description": "Service A", "quantity": 1, "unit_price": 1500.00, "total": 1500.00}
        ],
        "subtotal": 1500.00,
        "tax_percentage": 0.0,
        "tax_amount": 0.0,
        "total_amount": 1500.00,
        "currency": "USD",
        "due_date": now,
        "paid_at": null,
        "notes": "",
        "created_by": user_id.to_string(),
        "created_at": now,
    });
    let req = app.post_authenticated("/api/v1/finance/invoices", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let invoice_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!invoice_id.is_empty());
    let inv_num = json["invoice_number"].as_str().unwrap_or("").to_string();
    assert!(inv_num.starts_with("INV-"), "invoice_number should start with INV-, got {inv_num}");

    // Get the invoice
    let req_get = app.get_authenticated(&format!("/api/v1/finance/invoices/{}", invoice_id), &token);
    let mut resp_get = app.send_request(req_get).await;
    assert_eq!(resp_get.status(), StatusCode::OK);
    let json_get: Value = app.json_body(&mut resp_get).await;
    let inv_num_get = json_get["invoice_number"].as_str().unwrap_or("");
    assert!(inv_num_get.starts_with("INV-"), "invoice_number should start with INV-, got {inv_num_get}");
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
    let user_id = Uuid::new_v4();
    let now = Utc::now().to_rfc3339();

    let body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": Uuid::new_v4().to_string(),
        "payment_number": "PAY-001",
        "invoice_id": Uuid::new_v4().to_string(),
        "amount": 500.00,
        "currency": "USD",
        "payment_method": "bank_transfer",
        "reference": "REF-001",
        "received_at": now,
        "created_by": user_id.to_string(),
    });
    let req = app.post_authenticated("/api/v1/finance/payments", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let payment_id = json["id"].as_str().unwrap_or("").to_string();
    assert!(!payment_id.is_empty());

    // List payments
    let req_list = app.get_authenticated("/api/v1/finance/payments", &token);
    let mut resp_list = app.send_request(req_list).await;
    assert_eq!(resp_list.status(), StatusCode::OK);
    let json_list: Value = app.json_body(&mut resp_list).await;
    assert!(json_list.is_object());
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
    let users_service = InMemoryUsersService::with_admin(
        "admin@sensei.test",
        "Admin User",
        &hash,
        tenant_id,
    );
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

    // Create the invoice through the API (same service instance).
    let invoice_body = serde_json::json!({
        "id": Uuid::new_v4().to_string(),
        "tenant_id": app.admin_tenant_id.to_string(),
        "invoice_number": "",
        "customer_id": Uuid::new_v4().to_string(),
        "customer_name": "Supplier Co",
        "status": "draft",
        "line_items": [
            {"description": "Part", "quantity": 100, "unit_price": 5.0, "total": 500.0, "product_id": product_id.to_string()}
        ],
        "subtotal": 500.0,
        "tax_percentage": 0.0,
        "tax_amount": 0.0,
        "total_amount": 500.0,
        "currency": "USD",
        "due_date": now,
        "paid_at": null,
        "notes": "",
        "created_by": app.admin_user_id.to_string(),
        "created_at": now,
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

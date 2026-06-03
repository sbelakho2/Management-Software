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
    let mut resp_alloc = app.send_request(req_alloc).await;
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
    let mut resp_list = app.send_request(req_list).await;
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

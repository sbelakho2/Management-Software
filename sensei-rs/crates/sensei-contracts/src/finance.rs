//! The canonical Finance HTTP contract (thirtieth-first audit).
//!
//! Two layers, deliberately separated:
//!
//! 1. **Narrow command requests** (`CreateInvoiceRequest`,
//!    `RecordPaymentRequest`, …). The API stops accepting whole `Invoice`
//!    / `Payment` domain objects. A client can never send
//!    subtotal/tax/total/status/invoice_number/tenant_id/created_by/
//!    created_at (invoice) or payment id/number/tenant/received time/
//!    actor (payment): the server derives every one of those fields, and
//!    `#[serde(deny_unknown_fields)]` turns any attempt to smuggle them
//!    into a loud rejection instead of a silent ignore.
//!
//! 2. **Response view models** (`Invoice`, `InvoiceLineItem`, `Payment`)
//!    — the exact shape the API serializes. The backend service domain
//!    re-exports these (`sensei_services::finance::Invoice` IS this
//!    type), so the frontend and the backend deserialize/serialize ONE
//!    definition and the response shape can never drift from the
//!    contract.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Narrow command requests
// ---------------------------------------------------------------------------

/// Create an invoice: only the commercial facts. The client NEVER sends
/// financial totals, status, identity, or timestamps — subtotal/tax/total
/// are derived server-side (`total = quantity × unit_price` per line) and
/// invoice_number/tenant/actor/dates are server-generated.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CreateInvoiceRequest {
    pub customer_id: Uuid,
    pub customer_name: String,
    pub line_items: Vec<CreateInvoiceLineItem>,
    pub tax_percentage: rust_decimal::Decimal,
    pub currency: String,
    pub due_date: DateTime<Utc>,
    pub notes: String,
}

/// One invoice line as the client sends it — no `total`, no status.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CreateInvoiceLineItem {
    pub description: String,
    pub quantity: i64,
    pub unit_price: rust_decimal::Decimal,
    /// Product this line refers to, when known (used by AP 3-way
    /// matching).
    #[serde(default)]
    pub product_id: Option<Uuid>,
}

/// Record a payment against an invoice. No payment id/number, no tenant,
/// no received time, no actor — all server-generated.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RecordPaymentRequest {
    pub invoice_id: Uuid,
    pub amount: rust_decimal::Decimal,
    pub currency: String,
    pub payment_method: String, // cash, card, bank_transfer, check
    pub reference: String,
}

// ---------------------------------------------------------------------------
// Response view models — the shared shape both sides (de)serialize
// ---------------------------------------------------------------------------

/// An invoice as the API returns it (receivables/payables document).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Invoice {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub invoice_number: String,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub status: String, // draft, sent, overdue, paid, cancelled, written_off
    pub line_items: Vec<InvoiceLineItem>,
    pub subtotal: rust_decimal::Decimal,
    pub tax_percentage: rust_decimal::Decimal,
    pub tax_amount: rust_decimal::Decimal,
    pub total_amount: rust_decimal::Decimal,
    pub currency: String,
    pub due_date: DateTime<Utc>,
    pub paid_at: Option<DateTime<Utc>>,
    pub notes: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// A single line item within an invoice (total server-derived).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvoiceLineItem {
    pub description: String,
    pub quantity: i64,
    pub unit_price: rust_decimal::Decimal,
    pub total: rust_decimal::Decimal,
    /// Product this line refers to, when known (used by AP 3-way matching).
    #[serde(default)]
    pub product_id: Option<Uuid>,
}

/// A payment as the API returns it (applied to an invoice).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Payment {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub payment_number: String,
    pub invoice_id: Uuid,
    pub amount: rust_decimal::Decimal,
    pub currency: String,
    pub payment_method: String, // cash, card, bank_transfer, check
    pub reference: String,
    pub received_at: DateTime<Utc>,
    pub created_by: Uuid,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_invoice_rejects_client_side_totals() {
        let json = serde_json::json!({
            "customer_id": "11111111-1111-1111-1111-111111111111",
            "customer_name": "Acme",
            "line_items": [
                {"description": "Widget", "quantity": 10, "unit_price": 25.0, "total": 250.0}
            ],
            "tax_percentage": 10.0,
            "currency": "USD",
            "due_date": "2026-10-01T00:00:00Z",
            "notes": "",
            "subtotal": 250.0,
            "total_amount": 275.0
        });
        let err = serde_json::from_value::<CreateInvoiceRequest>(json)
            .expect_err("client-side totals must be rejected");
        assert!(err.to_string().contains("total"));
    }

    #[test]
    fn record_payment_rejects_client_identity() {
        let json = serde_json::json!({
            "id": "11111111-1111-1111-1111-111111111111",
            "payment_number": "PAY-X",
            "invoice_id": "22222222-2222-2222-2222-222222222222",
            "amount": 500.0,
            "currency": "USD",
            "payment_method": "bank_transfer",
            "reference": "REF",
            "received_at": "2026-09-01T00:00:00Z"
        });
        let err = serde_json::from_value::<RecordPaymentRequest>(json)
            .expect_err("client-supplied payment id/number must be rejected");
        let msg = err.to_string();
        assert!(
            msg.contains("received_at")
                || msg.contains("payment_number")
                || msg.contains("unknown field"),
            "expected an unknown-field rejection, got: {msg}"
        );
    }

    #[test]
    fn narrow_requests_round_trip() {
        let json = serde_json::json!({
            "customer_id": "11111111-1111-1111-1111-111111111111",
            "customer_name": "Acme",
            "line_items": [
                {"description": "Widget", "quantity": 10, "unit_price": 25.0}
            ],
            "tax_percentage": 10.0,
            "currency": "USD",
            "due_date": "2026-10-01T00:00:00Z",
            "notes": "net 30"
        });
        let req: CreateInvoiceRequest =
            serde_json::from_value(json).expect("narrow create payload must parse");
        assert_eq!(req.line_items[0].quantity, 10);
        let out = serde_json::to_value(&req).unwrap();
        assert!(out.get("subtotal").is_none());
        assert!(out.get("created_by").is_none());
    }
}

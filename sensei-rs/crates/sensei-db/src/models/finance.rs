//! Financial management models for GL, accounting, invoices, and budgeting.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of a General Ledger account.
///
/// GL accounts form the chart of accounts for double-entry bookkeeping,
/// organized by type (asset, liability, equity, revenue, expense).
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct GlAccountModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Account number (unique within tenant).
    pub account_number: String,
    /// Account name.
    pub name: String,
    /// Account type (asset, liability, equity, revenue, expense).
    pub account_type: String,
    /// Current balance.
    pub balance: f64,
    /// Parent account (for hierarchical chart of accounts).
    pub parent_id: Option<Uuid>,
    /// Whether the account is active.
    pub is_active: bool,
    /// Description.
    pub description: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an accounting period.
///
/// Accounting periods define the fiscal calendar for financial reporting,
/// with open/closed/locked status for data integrity.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AccountingPeriodModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Period name (e.g., "2026-Q1", "2026-01").
    pub name: String,
    /// Period start date.
    pub start_date: chrono::NaiveDate,
    /// Period end date.
    pub end_date: chrono::NaiveDate,
    /// Status (open, closed, locked).
    pub status: String,
    /// Fiscal year.
    pub fiscal_year: i32,
    /// Period number within the fiscal year.
    pub period_number: i32,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a journal line.
///
/// Journal lines are individual debit/credit entries within a journal entry,
/// linked to GL accounts and optionally to source entities.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct JournalLineModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent journal entry.
    pub entry_id: Uuid,
    /// Line number within the entry.
    pub line_number: i32,
    /// GL account.
    pub account_id: Uuid,
    /// Debit amount.
    pub debit: f64,
    /// Credit amount.
    pub credit: f64,
    /// Description.
    pub description: Option<String>,
    /// Source entity type (e.g., "invoice", "po", "work_order").
    pub entity_type: Option<String>,
    /// Source entity ID.
    pub entity_id: Option<Uuid>,
    /// Cost center.
    pub cost_center: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a purchase order line item.
///
/// Extended PO line items with cost tracking, receiving, and invoicing status.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PoLineItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent purchase order.
    pub po_id: Uuid,
    /// Line number.
    pub line_number: i32,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Part number.
    pub part_number: Option<String>,
    /// Description.
    pub description: String,
    /// Quantity ordered.
    pub quantity: f64,
    /// Price per unit.
    pub unit_price: f64,
    /// Extended price (quantity * unit_price).
    pub extended_price: f64,
    /// Cost per unit.
    pub unit_cost: f64,
    /// Quantity received so far.
    pub received_quantity: f64,
    /// Quantity invoiced so far.
    pub invoiced_quantity: f64,
    /// Expected delivery date.
    pub expected_date: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a sales order line item.
///
/// Line items within a sales order with pricing, shipping, and invoicing status.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SoLineItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent sales order.
    pub so_id: Uuid,
    /// Line number.
    pub line_number: i32,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Part number.
    pub part_number: Option<String>,
    /// Description.
    pub description: String,
    /// Quantity ordered.
    pub quantity: f64,
    /// Price per unit.
    pub unit_price: f64,
    /// Extended price (quantity * unit_price).
    pub extended_price: f64,
    /// Cost per unit.
    pub unit_cost: f64,
    /// Quantity shipped so far.
    pub shipped_quantity: f64,
    /// Quantity invoiced so far.
    pub invoiced_quantity: f64,
    /// Customer requested date.
    pub requested_date: Option<DateTime<Utc>>,
    /// Promised delivery date.
    pub promised_date: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a customer invoice (accounts receivable).
///
/// Invoices sent to customers for goods or services, linked to
/// sales orders and tracked through payment lifecycle.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CustomerInvoiceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable invoice number.
    pub invoice_number: String,
    /// Sales order reference.
    pub sales_order_id: Option<Uuid>,
    /// Customer account.
    pub customer_id: Uuid,
    /// Status (draft, sent, approved, paid, overdue, cancelled).
    pub status: String,
    /// Subtotal before tax.
    pub subtotal: f64,
    /// Tax amount.
    pub tax: f64,
    /// Total including tax.
    pub total: f64,
    /// Currency code.
    pub currency: String,
    /// Payment due date.
    pub due_date: DateTime<Utc>,
    /// Payment received timestamp.
    pub paid_at: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// User who created the invoice.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier invoice (accounts payable).
///
/// Invoices received from suppliers for goods or services, linked to
/// purchase orders and tracked through approval and payment.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SupplierInvoiceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable invoice number.
    pub invoice_number: String,
    /// Purchase order reference.
    pub po_id: Option<Uuid>,
    /// Supplier.
    pub supplier_id: Uuid,
    /// Status (draft, received, approved, paid, disputed, cancelled).
    pub status: String,
    /// Subtotal before tax.
    pub subtotal: f64,
    /// Tax amount.
    pub tax: f64,
    /// Total including tax.
    pub total: f64,
    /// Currency code.
    pub currency: String,
    /// Invoice date.
    pub invoice_date: DateTime<Utc>,
    /// Payment due date.
    pub due_date: DateTime<Utc>,
    /// Payment made timestamp.
    pub paid_at: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// User who created the record.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier payment.
///
/// Payments made to suppliers against supplier invoices.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SupplierPaymentModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable payment number.
    pub payment_number: String,
    /// Supplier invoice reference.
    pub invoice_id: Option<Uuid>,
    /// Supplier being paid.
    pub supplier_id: Uuid,
    /// Payment amount.
    pub amount: f64,
    /// Currency code.
    pub currency: String,
    /// Payment method (bank_transfer, check, cash, credit_card, wire).
    pub payment_method: String,
    /// Payment reference (check number, transaction ID, etc.).
    pub reference: Option<String>,
    /// Status (pending, completed, failed, reversed).
    pub status: String,
    /// Payment timestamp.
    pub paid_at: DateTime<Utc>,
    /// Notes.
    pub notes: Option<String>,
    /// User who created the payment.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a foreign exchange rate.
///
/// FX rates support multi-currency operations with daily rate tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct FxRateModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Source currency code.
    pub from_currency: String,
    /// Target currency code.
    pub to_currency: String,
    /// Exchange rate.
    pub rate: f64,
    /// Rate effective date.
    pub date: chrono::NaiveDate,
    /// Rate source (manual, ECB, etc.).
    pub source: String,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of a tax jurisdiction.
///
/// Tax jurisdictions define tax rates by region and type for
/// automatic tax calculation on transactions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TaxJurisdictionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Jurisdiction name.
    pub name: String,
    /// Region (state, province, country).
    pub region: Option<String>,
    /// Tax rate (percentage as decimal, e.g., 0.20 for 20%).
    pub rate: f64,
    /// Tax type (sales, vat, gst, withholding, excise, other).
    pub tax_type: String,
    /// Whether the jurisdiction is active.
    pub is_active: bool,
    /// Description.
    pub description: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a budget allocation.
///
/// Budget allocations distribute budget amounts across GL accounts,
/// tracking committed and spent amounts.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct BudgetAllocationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent budget.
    pub budget_id: Uuid,
    /// GL account allocated to.
    pub gl_account_id: Uuid,
    /// Allocated amount.
    pub amount: f64,
    /// Amount spent.
    pub spent: f64,
    /// Amount committed.
    pub committed: f64,
    /// Description.
    pub description: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

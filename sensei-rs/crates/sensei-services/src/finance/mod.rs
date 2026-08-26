//! Finance domain services.
//!
//! Provides invoice management, payment processing, budgeting, journal entries,
//! and cost rollup with in-memory storage for development and testing.
//!
//! # Architecture
//!
//! The finance service layer abstracts financial operations behind a trait,
//! enabling the system to swap in real database-backed implementations
//! while keeping the in-memory implementation for unit tests and demos.

mod database;
pub use database::DatabaseFinanceService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::domain::events::{
    CostRollupCompleted, DomainEvent, InvoiceCreatedEvent, JournalEntryPosted,
    PaymentProcessedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_event_bus::bus::EventBus;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// An invoice representing a receivables or payables document.
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

/// A single line item within an invoice.
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

/// A payment applied to an invoice.
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

/// A budget allocation for a department and fiscal year.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Budget {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub fiscal_year: i32,
    pub department: String,
    pub category: String,
    pub allocated_amount: rust_decimal::Decimal,
    pub spent_amount: rust_decimal::Decimal,
    pub remaining_amount: rust_decimal::Decimal,
}

/// A journal entry in the general ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JournalEntry {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub entry_number: String,
    pub description: String,
    pub debit_account: String,
    pub credit_account: String,
    pub amount: rust_decimal::Decimal,
    pub currency: String,
    pub entry_date: DateTime<Utc>,
    pub posted_by: Uuid,
}

/// A cost rollup summarising the total cost of a product.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRollup {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    pub product_name: String,
    pub material_cost: f64,
    pub labor_cost: f64,
    pub overhead_cost: f64,
    pub total_cost: f64,
    pub rollup_date: DateTime<Utc>,
}

/// Per-line verdict of an AP 3-way match (PO vs receipts vs invoice).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ThreeWayLineStatus {
    /// Received quantity covers the invoiced quantity and does not exceed the PO.
    Matched,
    /// Received quantity is below the invoiced quantity.
    UnderDelivered,
    /// Received quantity exceeds the PO quantity or the invoiced quantity.
    OverDelivered,
    /// The invoice line cannot be tied to a product (no product reference).
    Unmatched,
}

/// Overall verdict of a 3-way match.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ThreeWayVerdict {
    /// Every invoice line matched and quantities are consistent.
    Matched,
    /// At least one line is under/over-delivered or unmatched.
    Mismatch,
}

/// Per-product comparison between PO quantity, received quantity, and
/// invoiced quantity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreeWayLineResult {
    pub product_id: Uuid,
    pub po_quantity: f64,
    pub received_quantity: f64,
    pub invoiced_quantity: f64,
    pub status: ThreeWayLineStatus,
}

/// Result of matching a purchase order against goods receipts and an invoice.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreeWayMatchResult {
    pub po_id: Uuid,
    pub invoice_id: Uuid,
    pub lines: Vec<ThreeWayLineResult>,
    pub verdict: ThreeWayVerdict,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Finance service trait covering invoices, payments, budgets, journal
/// entries, and cost rollups.
#[async_trait]
pub trait FinanceService: Send + Sync {
    // ── Invoices ────────────────────────────────────────────────────────
    /// Create a new invoice. When `idempotency_key` is present, the
    /// business mutation, the idempotency completion AND the business audit
    /// row commit in ONE transaction.
    async fn create_invoice(
        &self,
        tenant_id: Uuid,
        invoice: Invoice,
        idempotency_key: Option<&str>,
    ) -> Result<Invoice>;
    /// Get an invoice by ID.
    async fn get_invoice(&self, tenant_id: Uuid, id: Uuid) -> Result<Invoice>;
    /// List invoices with optional status filter and pagination.
    async fn list_invoices(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Invoice>>;
    /// Mark an invoice as paid.
    async fn mark_invoice_paid(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        payment_id: Uuid,
    ) -> Result<Invoice>;

    // ── Payments ────────────────────────────────────────────────────────
    /// Record a payment against an invoice.
    async fn record_payment(
        &self,
        tenant_id: Uuid,
        payment: Payment,
        idempotency_key: Option<&str>,
    ) -> Result<Payment>;
    /// List payments with optional invoice filter and pagination.
    async fn list_payments(
        &self,
        tenant_id: Uuid,
        invoice_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Payment>>;

    // ── Budget ──────────────────────────────────────────────────────────
    /// Create a new budget.
    async fn create_budget(&self, tenant_id: Uuid, budget: Budget) -> Result<Budget>;
    /// Get a budget by ID.
    async fn get_budget(&self, tenant_id: Uuid, id: Uuid) -> Result<Budget>;
    /// List budgets with optional fiscal year and department filters, with pagination.
    async fn list_budgets(
        &self,
        tenant_id: Uuid,
        fiscal_year: Option<i32>,
        department: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Budget>>;
    /// Allocate additional funds to a budget.
    async fn allocate_budget(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        amount: rust_decimal::Decimal,
    ) -> Result<Budget>;

    // ── Journal Entries ─────────────────────────────────────────────────
    /// Post a new journal entry.
    async fn post_journal_entry(
        &self,
        tenant_id: Uuid,
        entry: JournalEntry,
        idempotency_key: Option<&str>,
    ) -> Result<JournalEntry>;
    /// Get a journal entry by id.
    async fn get_journal_entry(&self, tenant_id: Uuid, id: Uuid) -> Result<JournalEntry>;

    /// List journal entries with optional account filter and pagination.
    async fn list_journal_entries(
        &self,
        tenant_id: Uuid,
        account: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<JournalEntry>>;

    // ── Invoice Mutations ──────────────────────────────────────────────
    /// Update an invoice.
    async fn update_invoice(&self, tenant_id: Uuid, id: Uuid, invoice: Invoice) -> Result<Invoice>;
    /// Delete an invoice.
    async fn delete_invoice(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Payment Mutations ──────────────────────────────────────────────
    /// Update a payment.
    async fn update_payment(&self, tenant_id: Uuid, id: Uuid, payment: Payment) -> Result<Payment>;
    /// Delete a payment.
    async fn delete_payment(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Budget Mutations ───────────────────────────────────────────────
    /// Update a budget.
    async fn update_budget(&self, tenant_id: Uuid, id: Uuid, budget: Budget) -> Result<Budget>;
    /// Delete a budget.
    async fn delete_budget(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Journal Entry Mutations ────────────────────────────────────────
    /// Update a journal entry.
    async fn update_journal_entry(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        entry: JournalEntry,
    ) -> Result<JournalEntry>;
    /// Delete a journal entry.
    async fn delete_journal_entry(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Reverse a posted journal entry: creates a mirror entry and marks the
    /// original `reversed`. Corrections are reversals + replacements, never
    /// edits of posted accounting history.
    async fn reverse_journal_entry(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        reversed_by: Uuid,
        idempotency_key: Option<&str>,
    ) -> Result<JournalEntry>;

    // ── Cost Rollup ─────────────────────────────────────────────────────
    /// Run a cost rollup for a product.
    async fn run_cost_rollup(&self, tenant_id: Uuid, product_id: Uuid) -> Result<CostRollup>;
    /// Get the latest cost rollup for a product.
    async fn get_cost_rollup(&self, tenant_id: Uuid, product_id: Uuid) -> Result<CostRollup>;

    // ── AP 3-Way Matching ───────────────────────────────────────────────
    /// Match a purchase order, its goods receipts, and a supplier invoice.
    ///
    /// Verifies the PO exists, that every receipt belongs to the PO, that
    /// received quantities per product cover the invoiced quantities, and
    /// that totals are consistent. Returns per-line and overall verdicts.
    async fn match_three_way(
        &self,
        tenant_id: Uuid,
        po_id: Uuid,
        receipt_ids: Vec<Uuid>,
        invoice_id: Uuid,
    ) -> Result<ThreeWayMatchResult>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`FinanceService`] trait.
///
/// Stores invoices, payments, budgets, journal entries, and cost rollups
/// in memory using `HashMap`s. Suitable for development, testing, and
/// demo environments.
pub struct InMemoryFinanceService {
    invoices: RwLock<HashMap<Uuid, Invoice>>,
    payments: RwLock<HashMap<Uuid, Payment>>,
    budgets: RwLock<HashMap<Uuid, Budget>>,
    journal_entries: RwLock<HashMap<Uuid, JournalEntry>>,
    /// Cost rollups keyed by product id (latest rollup per product).
    cost_rollups: RwLock<HashMap<Uuid, CostRollup>>,
    inv_counter: RwLock<u64>,
    pay_counter: RwLock<u64>,
    je_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
    // Costing inputs (seeded for tests/demos; the DB implementation reads
    // the real BOM / routing tables).
    bom: RwLock<HashMap<Uuid, Vec<BomEntry>>>,
    standard_costs: RwLock<HashMap<Uuid, f64>>,
    routings: RwLock<HashMap<Uuid, Vec<RoutingEntry>>>,
    product_names: RwLock<HashMap<Uuid, String>>,
    // AP 3-way match inputs (seeded for tests/demos).
    purchase_orders: RwLock<HashMap<Uuid, PoLite>>,
    receipts: RwLock<HashMap<Uuid, ReceiptLite>>,
}

/// A BOM line seeded into the in-memory finance service.
#[derive(Debug, Clone)]
pub struct BomEntry {
    /// The component product id (cost is looked up via `standard_cost`).
    pub component_product_id: Uuid,
    /// Quantity of the component per unit of the parent product.
    pub quantity: f64,
}

/// A routing step seeded into the in-memory finance service.
#[derive(Debug, Clone)]
pub struct RoutingEntry {
    /// Standard time in hours for the operation.
    pub standard_time_hours: f64,
    /// Hourly rate of the work center (currency units per hour).
    pub hourly_rate: f64,
}

/// A purchase order seeded into the in-memory finance service.
#[derive(Debug, Clone)]
pub struct PoLite {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub lines: Vec<(Uuid, f64)>,
}

/// A goods receipt seeded into the in-memory finance service.
#[derive(Debug, Clone)]
pub struct ReceiptLite {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub po_id: Uuid,
    pub lines: Vec<(Uuid, f64)>,
}

impl InMemoryFinanceService {
    /// Create a new empty [`InMemoryFinanceService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            invoices: RwLock::new(HashMap::new()),
            payments: RwLock::new(HashMap::new()),
            budgets: RwLock::new(HashMap::new()),
            journal_entries: RwLock::new(HashMap::new()),
            cost_rollups: RwLock::new(HashMap::new()),
            inv_counter: RwLock::new(0),
            pay_counter: RwLock::new(0),
            je_counter: RwLock::new(0),
            event_bus,
            bom: RwLock::new(HashMap::new()),
            standard_costs: RwLock::new(HashMap::new()),
            routings: RwLock::new(HashMap::new()),
            product_names: RwLock::new(HashMap::new()),
            purchase_orders: RwLock::new(HashMap::new()),
            receipts: RwLock::new(HashMap::new()),
        }
    }

    /// Seed a BOM line for cost rollups.
    pub async fn seed_bom(
        &self,
        parent_product_id: Uuid,
        component_product_id: Uuid,
        quantity: f64,
    ) {
        self.bom
            .write()
            .await
            .entry(parent_product_id)
            .or_default()
            .push(BomEntry {
                component_product_id,
                quantity,
            });
    }

    /// Seed a product's standard cost for cost rollups.
    pub async fn seed_standard_cost(&self, product_id: Uuid, cost: f64) {
        self.standard_costs.write().await.insert(product_id, cost);
    }

    /// Seed a routing step (standard time × hourly rate) for labor costing.
    pub async fn seed_routing(&self, product_id: Uuid, standard_time_hours: f64, hourly_rate: f64) {
        self.routings
            .write()
            .await
            .entry(product_id)
            .or_default()
            .push(RoutingEntry {
                standard_time_hours,
                hourly_rate,
            });
    }

    /// Seed a product display name for cost rollups.
    pub async fn seed_product_name(&self, product_id: Uuid, name: impl Into<String>) {
        self.product_names
            .write()
            .await
            .insert(product_id, name.into());
    }

    /// Seed a purchase order for AP 3-way matching.
    pub async fn seed_purchase_order(&self, tenant_id: Uuid, id: Uuid, lines: Vec<(Uuid, f64)>) {
        self.purchase_orders.write().await.insert(
            id,
            PoLite {
                id,
                tenant_id,
                lines,
            },
        );
    }

    /// Seed a goods receipt for AP 3-way matching.
    pub async fn seed_goods_receipt(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        po_id: Uuid,
        lines: Vec<(Uuid, f64)>,
    ) {
        self.receipts.write().await.insert(
            id,
            ReceiptLite {
                id,
                tenant_id,
                po_id,
                lines,
            },
        );
    }

    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!("Failed to publish event {}: {}", event.event_type(), e);
            }
        }
    }

    fn generate_invoice_number(counter: u64) -> String {
        format!("INV-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_payment_number(counter: u64) -> String {
        format!("PAY-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_entry_number(counter: u64) -> String {
        format!("JE-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }
}

/// Overhead percentage applied on top of (material + labor) cost.
///
/// Configurable via the `FINANCE_OVERHEAD_PCT` environment variable
/// (defaults to 15%). Invalid or non-finite values fall back to the default.
pub fn overhead_percentage() -> f64 {
    std::env::var("FINANCE_OVERHEAD_PCT")
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
        .filter(|v| v.is_finite() && *v >= 0.0)
        .unwrap_or(15.0)
}

impl Default for InMemoryFinanceService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl FinanceService for InMemoryFinanceService {
    async fn get_journal_entry(&self, tenant_id: Uuid, id: Uuid) -> Result<JournalEntry> {
        let entries = self.journal_entries.read().await;
        entries
            .get(&id)
            .filter(|e| e.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Journal entry {id} not found")))
    }

    // ── Invoices ────────────────────────────────────────────────────────

    async fn create_invoice(
        &self,
        tenant_id: Uuid,
        mut invoice: Invoice,
        _idempotency_key: Option<&str>,
    ) -> Result<Invoice> {
        let mut counter = self.inv_counter.write().await;
        *counter += 1;
        let inv_number = Self::generate_invoice_number(*counter);
        drop(counter);

        // Compute financial totals from line items
        let subtotal: rust_decimal::Decimal = invoice
            .line_items
            .iter()
            .map(|li| rust_decimal::Decimal::from(li.quantity) * li.unit_price)
            .sum();
        let tax_amount = subtotal * invoice.tax_percentage / rust_decimal::Decimal::from(100u32);
        let total_amount = subtotal + tax_amount;

        invoice.id = Uuid::new_v4();
        invoice.tenant_id = tenant_id;
        invoice.invoice_number = inv_number;
        invoice.subtotal = subtotal;
        invoice.tax_amount = tax_amount;
        invoice.total_amount = total_amount;
        invoice.status = "draft".to_string();
        invoice.created_at = Utc::now();

        // Update each line item's total
        for li in &mut invoice.line_items {
            li.total = rust_decimal::Decimal::from(li.quantity) * li.unit_price;
        }

        let id = invoice.id;
        self.invoices.write().await.insert(id, invoice.clone());
        self.publish_event(InvoiceCreatedEvent::new(
            tenant_id,
            id,
            "standard".to_string(),
            invoice
                .total_amount
                .to_string()
                .parse::<f64>()
                .unwrap_or_default(),
            invoice.currency.clone(),
            invoice.customer_name.clone(),
        ))
        .await;
        Ok(invoice)
    }

    async fn get_invoice(&self, _tenant_id: Uuid, id: Uuid) -> Result<Invoice> {
        let store = self.invoices.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))
    }

    async fn list_invoices(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Invoice>> {
        let store = self.invoices.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|inv| inv.tenant_id == tenant_id && status.is_none_or(|s| inv.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn mark_invoice_paid(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        payment_id: Uuid,
    ) -> Result<Invoice> {
        let mut store = self.invoices.write().await;
        let inv = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))?;

        if inv.tenant_id != tenant_id {
            return Err(SenseiError::NotFound(format!("Invoice {id} not found")));
        }
        if inv.status == "paid" {
            return Err(SenseiError::Validation(
                "Invoice is already paid".to_string(),
            ));
        }
        if inv.status == "cancelled" {
            return Err(SenseiError::Validation(
                "Cannot mark a cancelled invoice as paid".to_string(),
            ));
        }

        // Validate the payment being applied belongs to this invoice.
        let payments = self.payments.read().await;
        let payment = payments
            .get(&payment_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Payment {payment_id} not found")))?;
        if payment.invoice_id != id {
            return Err(SenseiError::Validation(format!(
                "Payment {payment_id} does not belong to invoice {id}"
            )));
        }

        // Cumulative payments must cover the invoice total (with a small
        // epsilon for floating-point rounding).
        let cumulative: rust_decimal::Decimal = payments
            .values()
            .filter(|p| p.invoice_id == id)
            .map(|p| p.amount)
            .sum();
        drop(payments);

        if cumulative + rust_decimal::Decimal::new(1, 2) < inv.total_amount {
            return Err(SenseiError::Validation(format!(
                "Cumulative payments ({cumulative:.2}) do not cover invoice total ({:.2})",
                inv.total_amount
            )));
        }

        inv.status = "paid".to_string();
        inv.paid_at = Some(Utc::now());
        Ok(inv.clone())
    }

    // ── Payments ────────────────────────────────────────────────────────

    async fn record_payment(
        &self,
        tenant_id: Uuid,
        mut payment: Payment,
        _idempotency_key: Option<&str>,
    ) -> Result<Payment> {
        let mut counter = self.pay_counter.write().await;
        *counter += 1;
        let pay_number = Self::generate_payment_number(*counter);
        drop(counter);

        // Preserve a caller-supplied id (callers reference it when marking
        // the invoice paid); only generate one when the caller left it nil.
        if payment.id.is_nil() {
            payment.id = Uuid::new_v4();
        }
        payment.tenant_id = tenant_id;
        payment.payment_number = pay_number;
        payment.received_at = Utc::now();

        let id = payment.id;
        self.payments.write().await.insert(id, payment.clone());
        self.publish_event(PaymentProcessedEvent::new(
            tenant_id,
            id,
            payment.payment_method.clone(),
            payment
                .amount
                .to_string()
                .parse::<f64>()
                .unwrap_or_default(),
            payment.currency.clone(),
            payment.created_by,
        ))
        .await;
        Ok(payment)
    }

    async fn list_payments(
        &self,
        tenant_id: Uuid,
        invoice_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Payment>> {
        let store = self.payments.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|p| {
                p.tenant_id == tenant_id && invoice_id.is_none_or(|inv_id| p.invoice_id == inv_id)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Budget ──────────────────────────────────────────────────────────

    async fn create_budget(&self, tenant_id: Uuid, mut budget: Budget) -> Result<Budget> {
        budget.id = Uuid::new_v4();
        budget.tenant_id = tenant_id;
        budget.spent_amount = rust_decimal::Decimal::ZERO;
        budget.remaining_amount = budget.allocated_amount;

        let id = budget.id;
        self.budgets.write().await.insert(id, budget.clone());
        Ok(budget)
    }

    async fn get_budget(&self, _tenant_id: Uuid, id: Uuid) -> Result<Budget> {
        let store = self.budgets.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))
    }

    async fn list_budgets(
        &self,
        tenant_id: Uuid,
        fiscal_year: Option<i32>,
        department: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Budget>> {
        let store = self.budgets.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|b| {
                b.tenant_id == tenant_id
                    && fiscal_year.is_none_or(|fy| b.fiscal_year == fy)
                    && department.is_none_or(|d| b.department == d)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn allocate_budget(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        amount: rust_decimal::Decimal,
    ) -> Result<Budget> {
        let mut store = self.budgets.write().await;
        let budget = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;

        if amount < rust_decimal::Decimal::ZERO {
            return Err(SenseiError::Validation(
                "Allocation amount must be non-negative".to_string(),
            ));
        }

        budget.allocated_amount += amount;
        budget.remaining_amount = budget.allocated_amount - budget.spent_amount;
        Ok(budget.clone())
    }

    // ── Journal Entries ─────────────────────────────────────────────────

    async fn post_journal_entry(
        &self,
        tenant_id: Uuid,
        mut entry: JournalEntry,
        _idempotency_key: Option<&str>,
    ) -> Result<JournalEntry> {
        let mut counter = self.je_counter.write().await;
        *counter += 1;
        let entry_number = Self::generate_entry_number(*counter);
        drop(counter);

        entry.id = Uuid::new_v4();
        entry.tenant_id = tenant_id;
        entry.entry_number = entry_number;
        entry.entry_date = Utc::now();

        let id = entry.id;
        self.journal_entries.write().await.insert(id, entry.clone());
        self.publish_event(JournalEntryPosted::new(
            tenant_id,
            id,
            entry.amount.to_string().parse::<f64>().unwrap_or_default(),
            entry.amount.to_string().parse::<f64>().unwrap_or_default(),
            entry.entry_date.format("%Y-%m").to_string(),
        ))
        .await;
        Ok(entry)
    }

    async fn list_journal_entries(
        &self,
        tenant_id: Uuid,
        account: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<JournalEntry>> {
        let store = self.journal_entries.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|e| {
                e.tenant_id == tenant_id
                    && account.is_none_or(|a| e.debit_account == a || e.credit_account == a)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Cost Rollup ─────────────────────────────────────────────────────

    async fn run_cost_rollup(&self, tenant_id: Uuid, product_id: Uuid) -> Result<CostRollup> {
        // Real rollup from seeded BOM/routing data, summed in integer cents.
        let bom = self.bom.read().await;
        let costs = self.standard_costs.read().await;
        let mut material_cents: i64 = 0;
        for entry in bom.get(&product_id).into_iter().flatten() {
            let unit_cost = costs
                .get(&entry.component_product_id)
                .copied()
                .unwrap_or(0.0);
            let line = sensei_core::domain::value_objects::Money::from_decimal(
                entry.quantity * unit_cost,
                sensei_core::domain::value_objects::CurrencyCode::USD,
            )
            .map_err(|e| SenseiError::Internal(format!("Invalid cost value in BOM: {e}")))?;
            material_cents += line.cents;
        }
        drop(bom);
        drop(costs);

        let routings = self.routings.read().await;
        let mut labor_cents: i64 = 0;
        for step in routings.get(&product_id).into_iter().flatten() {
            let labor = sensei_core::domain::value_objects::Money::from_decimal(
                step.standard_time_hours * step.hourly_rate,
                sensei_core::domain::value_objects::CurrencyCode::USD,
            )
            .map_err(|e| SenseiError::Internal(format!("Invalid labor rate: {e}")))?;
            labor_cents += labor.cents;
        }
        drop(routings);

        let overhead_pct = overhead_percentage();
        let overhead_cents =
            ((material_cents + labor_cents) as f64 * overhead_pct / 100.0).round() as i64;

        let material_cost = material_cents as f64 / 100.0;
        let labor_cost = labor_cents as f64 / 100.0;
        let overhead_cost = overhead_cents as f64 / 100.0;
        let total_cost = material_cost + labor_cost + overhead_cost;

        let product_names = self.product_names.read().await;
        let product_name = product_names
            .get(&product_id)
            .cloned()
            .unwrap_or_else(|| "Unknown Product".to_string());
        drop(product_names);

        let rollup = CostRollup {
            id: Uuid::new_v4(),
            tenant_id,
            product_id,
            product_name,
            material_cost,
            labor_cost,
            overhead_cost,
            total_cost,
            rollup_date: Utc::now(),
        };

        // Key by product so `get_cost_rollup` deterministically returns the
        // most recent rollup for the product.
        self.cost_rollups
            .write()
            .await
            .insert(product_id, rollup.clone());
        self.publish_event(CostRollupCompleted::new(
            tenant_id,
            product_id,
            rollup.total_cost,
            "USD".to_string(),
        ))
        .await;
        Ok(rollup)
    }

    async fn get_cost_rollup(&self, _tenant_id: Uuid, product_id: Uuid) -> Result<CostRollup> {
        let store = self.cost_rollups.read().await;
        store.get(&product_id).cloned().ok_or_else(|| {
            SenseiError::NotFound(format!("Cost rollup for product {product_id} not found"))
        })
    }

    // ── AP 3-Way Matching ───────────────────────────────────────────────

    async fn match_three_way(
        &self,
        tenant_id: Uuid,
        po_id: Uuid,
        receipt_ids: Vec<Uuid>,
        invoice_id: Uuid,
    ) -> Result<ThreeWayMatchResult> {
        let pos = self.purchase_orders.read().await;
        let po = pos
            .get(&po_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {po_id} not found")))?;
        if po.tenant_id != tenant_id {
            return Err(SenseiError::NotFound(format!(
                "Purchase order {po_id} not found"
            )));
        }

        let receipts = self.receipts.read().await;
        for rid in &receipt_ids {
            let r = receipts
                .get(rid)
                .ok_or_else(|| SenseiError::NotFound(format!("Goods receipt {rid} not found")))?;
            if r.tenant_id != tenant_id || r.po_id != po_id {
                return Err(SenseiError::Validation(format!(
                    "Goods receipt {rid} does not belong to purchase order {po_id}"
                )));
            }
        }

        // Received quantity per product across all provided receipts.
        let mut received: HashMap<Uuid, f64> = HashMap::new();
        for rid in &receipt_ids {
            if let Some(r) = receipts.get(rid) {
                for (product_id, qty) in &r.lines {
                    *received.entry(*product_id).or_default() += qty;
                }
            }
        }

        let invoices = self.invoices.read().await;
        let invoice = invoices
            .get(&invoice_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Invoice {invoice_id} not found")))?;
        if invoice.tenant_id != tenant_id {
            return Err(SenseiError::NotFound(format!(
                "Invoice {invoice_id} not found"
            )));
        }

        // Invoiced quantity per product.
        let mut invoiced: HashMap<Uuid, f64> = HashMap::new();
        let mut unmatched: Vec<Uuid> = Vec::new();
        for line in &invoice.line_items {
            match line.product_id {
                Some(pid) => *invoiced.entry(pid).or_default() += line.quantity as f64,
                None => unmatched.push(Uuid::nil()),
            }
        }

        // PO quantity per product.
        let mut po_qty: HashMap<Uuid, f64> = HashMap::new();
        for (product_id, qty) in &po.lines {
            *po_qty.entry(*product_id).or_default() += qty;
        }
        drop(pos);
        drop(receipts);
        drop(invoices);

        let mut products: Vec<Uuid> = po_qty
            .keys()
            .chain(invoiced.keys())
            .copied()
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        products.sort();

        let mut lines = Vec::new();
        for pid in products {
            let pq = po_qty.get(&pid).copied().unwrap_or(0.0);
            let rq = received.get(&pid).copied().unwrap_or(0.0);
            let iq = invoiced.get(&pid).copied().unwrap_or(0.0);
            let status = if rq + 1e-9 < iq {
                ThreeWayLineStatus::UnderDelivered
            } else if rq > pq + 1e-9 || rq > iq + 1e-9 {
                ThreeWayLineStatus::OverDelivered
            } else {
                ThreeWayLineStatus::Matched
            };
            lines.push(ThreeWayLineResult {
                product_id: pid,
                po_quantity: pq,
                received_quantity: rq,
                invoiced_quantity: iq,
                status,
            });
        }

        // Invoice lines without a product reference are reported as unmatched.
        if !unmatched.is_empty() {
            lines.push(ThreeWayLineResult {
                product_id: Uuid::nil(),
                po_quantity: 0.0,
                received_quantity: 0.0,
                invoiced_quantity: unmatched.len() as f64,
                status: ThreeWayLineStatus::Unmatched,
            });
        }

        let verdict = if lines.is_empty()
            || lines
                .iter()
                .any(|l| l.status != ThreeWayLineStatus::Matched)
        {
            ThreeWayVerdict::Mismatch
        } else {
            ThreeWayVerdict::Matched
        };

        Ok(ThreeWayMatchResult {
            po_id,
            invoice_id,
            lines,
            verdict,
        })
    }

    // ── Invoice Mutations ──────────────────────────────────────────────

    async fn update_invoice(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        invoice: Invoice,
    ) -> Result<Invoice> {
        let mut store = self.invoices.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))?;
        existing.customer_id = invoice.customer_id;
        existing.customer_name = invoice.customer_name;
        existing.line_items = invoice.line_items;
        existing.subtotal = invoice.subtotal;
        existing.tax_percentage = invoice.tax_percentage;
        existing.tax_amount = invoice.tax_amount;
        existing.total_amount = invoice.total_amount;
        existing.currency = invoice.currency;
        existing.due_date = invoice.due_date;
        existing.notes = invoice.notes;
        Ok(existing.clone())
    }

    async fn delete_invoice(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.invoices.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))?;
        Ok(())
    }

    // ── Payment Mutations ──────────────────────────────────────────────

    async fn update_payment(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        payment: Payment,
    ) -> Result<Payment> {
        let mut store = self.payments.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Payment {id} not found")))?;
        existing.amount = payment.amount;
        existing.currency = payment.currency;
        existing.payment_method = payment.payment_method;
        existing.reference = payment.reference;
        Ok(existing.clone())
    }

    async fn delete_payment(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.payments.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Payment {id} not found")))?;
        Ok(())
    }

    // ── Budget Mutations ───────────────────────────────────────────────

    async fn update_budget(&self, _tenant_id: Uuid, id: Uuid, budget: Budget) -> Result<Budget> {
        let mut store = self.budgets.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;
        existing.fiscal_year = budget.fiscal_year;
        existing.department = budget.department;
        existing.category = budget.category;
        existing.allocated_amount = budget.allocated_amount;
        existing.spent_amount = budget.spent_amount;
        existing.remaining_amount = budget.allocated_amount - budget.spent_amount;
        Ok(existing.clone())
    }

    async fn delete_budget(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.budgets.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;
        Ok(())
    }

    // ── Journal Entry Mutations ────────────────────────────────────────

    async fn update_journal_entry(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        entry: JournalEntry,
    ) -> Result<JournalEntry> {
        let mut store = self.journal_entries.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("JournalEntry {id} not found")))?;
        existing.description = entry.description;
        existing.debit_account = entry.debit_account;
        existing.credit_account = entry.credit_account;
        existing.amount = entry.amount;
        existing.currency = entry.currency;
        Ok(existing.clone())
    }

    async fn delete_journal_entry(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.journal_entries.write().await;
        let entry = store
            .get(&id)
            .filter(|e| e.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("JournalEntry {id} not found")))?;
        if entry.posted_by != Uuid::nil() {
            return Err(SenseiError::Conflict(
                "Posted accounting entries are immutable — reverse them instead of deleting"
                    .to_string(),
            ));
        }
        store.remove(&id);
        Ok(())
    }

    async fn reverse_journal_entry(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        reversed_by: Uuid,
        _idempotency_key: Option<&str>,
    ) -> Result<JournalEntry> {
        let mut store = self.journal_entries.write().await;
        let original = store
            .get(&id)
            .filter(|e| e.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("JournalEntry {id} not found")))?;
        if original.posted_by == Uuid::nil() {
            return Err(SenseiError::Conflict(
                "Only posted entries can be reversed".to_string(),
            ));
        }
        let reversal = JournalEntry {
            id: Uuid::new_v4(),
            tenant_id,
            entry_number: format!("REV-{}", original.entry_number),
            description: format!("Reversal of {}", original.description),
            debit_account: original.credit_account.clone(),
            credit_account: original.debit_account.clone(),
            amount: original.amount,
            currency: original.currency,
            entry_date: Utc::now(),
            posted_by: reversed_by,
        };
        store.insert(reversal.id, reversal.clone());
        Ok(reversal)
    }
}

#[cfg(test)]
mod tests {
    fn dec(v: f64) -> rust_decimal::Decimal {
        rust_decimal::Decimal::from_f64_retain(v).unwrap_or(rust_decimal::Decimal::ZERO)
    }
    use super::*;

    #[tokio::test]
    async fn test_create_and_get_invoice() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();
        let customer_id = Uuid::new_v4();

        let invoice = Invoice {
            id: Uuid::nil(),
            tenant_id,
            invoice_number: String::new(),
            customer_id,
            customer_name: "Acme Corp".to_string(),
            status: String::new(),
            line_items: vec![
                InvoiceLineItem {
                    description: "Widget A".to_string(),
                    quantity: 10,
                    unit_price: dec(25.0),
                    total: dec(0.0),
                    product_id: None,
                },
                InvoiceLineItem {
                    description: "Widget B".to_string(),
                    quantity: 5,
                    unit_price: dec(50.0),
                    total: dec(0.0),
                    product_id: None,
                },
            ],
            subtotal: dec(0.0),
            tax_percentage: dec(10.0),
            tax_amount: dec(0.0),
            total_amount: dec(0.0),
            currency: "USD".to_string(),
            due_date: Utc::now() + chrono::Duration::days(30),
            paid_at: None,
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created = service
            .create_invoice(tenant_id, invoice, None)
            .await
            .expect("should create invoice");
        assert!(created.invoice_number.starts_with("INV-"));
        assert_eq!(created.status, "draft");
        // 10*25 + 5*50 = 250 + 250 = 500 subtotal
        assert_eq!(created.subtotal, dec(500.0));
        // 10% tax = 50.0
        assert_eq!(created.tax_amount, dec(50.0));
        // total = 550.0
        assert_eq!(created.total_amount, dec(550.0));

        let fetched = service
            .get_invoice(tenant_id, created.id)
            .await
            .expect("should fetch invoice");
        assert_eq!(fetched.id, created.id);
    }

    #[tokio::test]
    async fn test_mark_invoice_paid() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();

        let invoice = Invoice {
            id: Uuid::nil(),
            tenant_id,
            invoice_number: String::new(),
            customer_id: Uuid::new_v4(),
            customer_name: "Test".to_string(),
            status: String::new(),
            // Totals are derived from line items by create_invoice.
            line_items: vec![InvoiceLineItem {
                description: "Widgets".to_string(),
                quantity: 2,
                unit_price: dec(50.0),
                total: dec(100.0),
                product_id: None,
            }],
            subtotal: dec(100.0),
            tax_percentage: dec(0.0),
            tax_amount: dec(0.0),
            total_amount: dec(100.0),
            currency: "USD".to_string(),
            due_date: Utc::now() + chrono::Duration::days(30),
            paid_at: None,
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created = service
            .create_invoice(tenant_id, invoice, None)
            .await
            .unwrap();

        // Insufficient payment must be rejected.
        let payment_id = Uuid::new_v4();
        let small = Payment {
            id: payment_id,
            tenant_id,
            payment_number: String::new(),
            invoice_id: created.id,
            amount: dec(50.0),
            currency: "USD".to_string(),
            payment_method: "bank_transfer".to_string(),
            reference: "PARTIAL".to_string(),
            received_at: Utc::now(),
            created_by: Uuid::new_v4(),
        };
        service
            .record_payment(tenant_id, small, None)
            .await
            .unwrap();
        let err = service
            .mark_invoice_paid(tenant_id, created.id, payment_id)
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));

        // Covering the balance lets the invoice be marked paid.
        let full = Payment {
            id: Uuid::new_v4(),
            tenant_id,
            payment_number: String::new(),
            invoice_id: created.id,
            amount: dec(50.0),
            currency: "USD".to_string(),
            payment_method: "bank_transfer".to_string(),
            reference: "BALANCE".to_string(),
            received_at: Utc::now(),
            created_by: Uuid::new_v4(),
        };
        let full_id = full.id;
        service.record_payment(tenant_id, full, None).await.unwrap();
        let paid = service
            .mark_invoice_paid(tenant_id, created.id, full_id)
            .await
            .unwrap();
        assert_eq!(paid.status, "paid");
        assert!(paid.paid_at.is_some());
    }

    #[tokio::test]
    async fn test_mark_invoice_paid_rejects_unrelated_payment() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();
        let invoice = Invoice {
            id: Uuid::nil(),
            tenant_id,
            invoice_number: String::new(),
            customer_id: Uuid::new_v4(),
            customer_name: "Test".to_string(),
            status: String::new(),
            line_items: vec![],
            subtotal: dec(0.0),
            tax_percentage: dec(0.0),
            tax_amount: dec(0.0),
            total_amount: dec(0.0),
            currency: "USD".to_string(),
            due_date: Utc::now() + chrono::Duration::days(30),
            paid_at: None,
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };
        let created = service
            .create_invoice(tenant_id, invoice, None)
            .await
            .unwrap();
        let other = Payment {
            id: Uuid::new_v4(),
            tenant_id,
            payment_number: String::new(),
            invoice_id: Uuid::new_v4(),
            amount: dec(100.0),
            currency: "USD".to_string(),
            payment_method: "cash".to_string(),
            reference: "WRONG-INVOICE".to_string(),
            received_at: Utc::now(),
            created_by: Uuid::new_v4(),
        };
        let other_id = other.id;
        service
            .record_payment(tenant_id, other, None)
            .await
            .unwrap();
        let err = service
            .mark_invoice_paid(tenant_id, created.id, other_id)
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));
    }

    #[tokio::test]
    async fn test_payment_lifecycle() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();

        let payment = Payment {
            id: Uuid::nil(),
            tenant_id,
            payment_number: String::new(),
            invoice_id: Uuid::new_v4(),
            amount: dec(550.0),
            currency: "USD".to_string(),
            payment_method: "bank_transfer".to_string(),
            reference: "TRX-001".to_string(),
            received_at: Utc::now(),
            created_by: Uuid::new_v4(),
        };

        let created = service
            .record_payment(tenant_id, payment, None)
            .await
            .expect("should record payment");
        assert!(created.payment_number.starts_with("PAY-"));
        assert_eq!(created.amount, dec(550.0));
    }

    #[tokio::test]
    async fn test_budget_allocation() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();

        let budget = Budget {
            id: Uuid::nil(),
            tenant_id,
            fiscal_year: 2026,
            department: "Engineering".to_string(),
            category: "Tools".to_string(),
            allocated_amount: dec(10000.0),
            spent_amount: dec(0.0),
            remaining_amount: dec(0.0),
        };

        let created = service
            .create_budget(tenant_id, budget)
            .await
            .expect("should create budget");
        assert_eq!(created.remaining_amount, dec(10000.0));

        let allocated = service
            .allocate_budget(tenant_id, created.id, dec(5000.0))
            .await
            .unwrap();
        assert_eq!(allocated.allocated_amount, dec(15000.0));
    }

    #[tokio::test]
    async fn test_journal_entry() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();

        let entry = JournalEntry {
            id: Uuid::nil(),
            tenant_id,
            entry_number: String::new(),
            description: "Office supplies".to_string(),
            debit_account: "6000".to_string(),
            credit_account: "1100".to_string(),
            amount: dec(250.0),
            currency: "USD".to_string(),
            entry_date: Utc::now(),
            posted_by: Uuid::new_v4(),
        };

        let posted = service
            .post_journal_entry(tenant_id, entry, None)
            .await
            .expect("should post journal entry");
        assert!(posted.entry_number.starts_with("JE-"));
        assert_eq!(posted.amount, dec(250.0));
    }

    #[tokio::test]
    async fn test_cost_rollup() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        // No cost data → honest zero-cost rollup (not hardcoded values).
        let zero = service
            .run_cost_rollup(tenant_id, product_id)
            .await
            .expect("should run cost rollup");
        assert_eq!(zero.product_id, product_id);
        assert_eq!(zero.material_cost, 0.0);
        assert_eq!(zero.labor_cost, 0.0);
        assert_eq!(zero.overhead_cost, 0.0);

        // Seed BOM: 2× component A @ $10.00, 1× component B @ $25.50.
        let comp_a = Uuid::new_v4();
        let comp_b = Uuid::new_v4();
        service.seed_bom(product_id, comp_a, 2.0).await;
        service.seed_bom(product_id, comp_b, 1.0).await;
        service.seed_standard_cost(comp_a, 10.0).await;
        service.seed_standard_cost(comp_b, 25.5).await;
        // Seed routing: 2h @ $40/h → $80 labor.
        service.seed_routing(product_id, 2.0, 40.0).await;
        service.seed_product_name(product_id, "Widget").await;

        let rollup = service
            .run_cost_rollup(tenant_id, product_id)
            .await
            .expect("should run cost rollup");
        assert_eq!(rollup.product_name, "Widget");
        // material = 2*10.00 + 1*25.50 = 45.50
        assert_eq!(rollup.material_cost, 45.50);
        // labor = 2h * 40 = 80.00
        assert_eq!(rollup.labor_cost, 80.00);
        // overhead = 15% of (45.50 + 80.00) = 18.825 → 18.83 (rounded to cents)
        assert_eq!(rollup.overhead_cost, 18.83);
        assert_eq!(
            rollup.total_cost,
            rollup.material_cost + rollup.labor_cost + rollup.overhead_cost
        );

        let fetched = service
            .get_cost_rollup(tenant_id, product_id)
            .await
            .unwrap();
        assert_eq!(fetched.id, rollup.id);
    }

    #[tokio::test]
    async fn test_three_way_match() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();
        let po_id = Uuid::new_v4();
        let receipt_id = Uuid::new_v4();
        let invoice_id = Uuid::new_v4();
        let p1 = Uuid::new_v4();
        let p2 = Uuid::new_v4();

        service
            .seed_purchase_order(tenant_id, po_id, vec![(p1, 100.0), (p2, 50.0)])
            .await;
        service
            .seed_goods_receipt(tenant_id, receipt_id, po_id, vec![(p1, 100.0), (p2, 50.0)])
            .await;

        let invoice = Invoice {
            id: invoice_id,
            tenant_id,
            invoice_number: "SUP-1".to_string(),
            customer_id: Uuid::new_v4(),
            customer_name: "Supplier".to_string(),
            status: "draft".to_string(),
            line_items: vec![
                InvoiceLineItem {
                    description: "Part 1".to_string(),
                    quantity: 100,
                    unit_price: dec(5.0),
                    total: dec(500.0),
                    product_id: Some(p1),
                },
                InvoiceLineItem {
                    description: "Part 2".to_string(),
                    quantity: 50,
                    unit_price: dec(2.0),
                    total: dec(100.0),
                    product_id: Some(p2),
                },
            ],
            subtotal: dec(600.0),
            tax_percentage: dec(0.0),
            tax_amount: dec(0.0),
            total_amount: dec(600.0),
            currency: "USD".to_string(),
            due_date: Utc::now() + chrono::Duration::days(30),
            paid_at: None,
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };
        service.invoices.write().await.insert(invoice_id, invoice);

        let result = service
            .match_three_way(tenant_id, po_id, vec![receipt_id], invoice_id)
            .await
            .unwrap();
        assert_eq!(result.verdict, ThreeWayVerdict::Matched);
        assert!(result
            .lines
            .iter()
            .all(|l| l.status == ThreeWayLineStatus::Matched));

        // Short delivery on p2 → UnderDelivered + overall Mismatch.
        let short_receipt = Uuid::new_v4();
        service
            .seed_goods_receipt(
                tenant_id,
                short_receipt,
                po_id,
                vec![(p1, 100.0), (p2, 40.0)],
            )
            .await;
        let result = service
            .match_three_way(tenant_id, po_id, vec![short_receipt], invoice_id)
            .await
            .unwrap();
        assert_eq!(result.verdict, ThreeWayVerdict::Mismatch);
        let p2_line = result.lines.iter().find(|l| l.product_id == p2).unwrap();
        assert_eq!(p2_line.status, ThreeWayLineStatus::UnderDelivered);

        // A receipt for a different PO must be rejected.
        let other_po = Uuid::new_v4();
        let foreign_receipt = Uuid::new_v4();
        service
            .seed_goods_receipt(tenant_id, foreign_receipt, other_po, vec![(p1, 1.0)])
            .await;
        let err = service
            .match_three_way(tenant_id, po_id, vec![foreign_receipt], invoice_id)
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));
    }
}

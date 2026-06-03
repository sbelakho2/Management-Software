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
use serde::{Deserialize, Serialize};
use sensei_core::domain::events::{
    CostRollupCompleted, DomainEvent, InvoiceCreatedEvent, JournalEntryPosted,
    PaymentProcessedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_event_bus::bus::EventBus;
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
    pub subtotal: f64,
    pub tax_percentage: f64,
    pub tax_amount: f64,
    pub total_amount: f64,
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
    pub unit_price: f64,
    pub total: f64,
}

/// A payment applied to an invoice.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Payment {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub payment_number: String,
    pub invoice_id: Uuid,
    pub amount: f64,
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
    pub allocated_amount: f64,
    pub spent_amount: f64,
    pub remaining_amount: f64,
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
    pub amount: f64,
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

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Finance service trait covering invoices, payments, budgets, journal
/// entries, and cost rollups.
#[async_trait]
pub trait FinanceService: Send + Sync {
    // ── Invoices ────────────────────────────────────────────────────────
    /// Create a new invoice.
    async fn create_invoice(&self, tenant_id: Uuid, invoice: Invoice) -> Result<Invoice>;
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
    async fn record_payment(&self, tenant_id: Uuid, payment: Payment) -> Result<Payment>;
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
        amount: f64,
    ) -> Result<Budget>;

    // ── Journal Entries ─────────────────────────────────────────────────
    /// Post a new journal entry.
    async fn post_journal_entry(
        &self,
        tenant_id: Uuid,
        entry: JournalEntry,
    ) -> Result<JournalEntry>;
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
    async fn update_invoice(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        invoice: Invoice,
    ) -> Result<Invoice>;
    /// Delete an invoice.
    async fn delete_invoice(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Payment Mutations ──────────────────────────────────────────────
    /// Update a payment.
    async fn update_payment(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        payment: Payment,
    ) -> Result<Payment>;
    /// Delete a payment.
    async fn delete_payment(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Budget Mutations ───────────────────────────────────────────────
    /// Update a budget.
    async fn update_budget(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        budget: Budget,
    ) -> Result<Budget>;
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

    // ── Cost Rollup ─────────────────────────────────────────────────────
    /// Run a cost rollup for a product.
    async fn run_cost_rollup(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<CostRollup>;
    /// Get the latest cost rollup for a product.
    async fn get_cost_rollup(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<CostRollup>;
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
    cost_rollups: RwLock<HashMap<Uuid, CostRollup>>,
    inv_counter: RwLock<u64>,
    pay_counter: RwLock<u64>,
    je_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
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
        }
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

impl Default for InMemoryFinanceService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl FinanceService for InMemoryFinanceService {
    // ── Invoices ────────────────────────────────────────────────────────

    async fn create_invoice(
        &self,
        tenant_id: Uuid,
        mut invoice: Invoice,
    ) -> Result<Invoice> {
        let mut counter = self.inv_counter.write().await;
        *counter += 1;
        let inv_number = Self::generate_invoice_number(*counter);
        drop(counter);

        // Compute financial totals from line items
        let subtotal: f64 = invoice
            .line_items
            .iter()
            .map(|li| li.quantity as f64 * li.unit_price)
            .sum();
        let tax_amount = subtotal * invoice.tax_percentage / 100.0;
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
            li.total = li.quantity as f64 * li.unit_price;
        }

        let id = invoice.id;
        self.invoices.write().await.insert(id, invoice.clone());
        self.publish_event(InvoiceCreatedEvent::new(
            tenant_id,
            id,
            "standard".to_string(),
            invoice.total_amount,
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
            .filter(|inv| {
                inv.tenant_id == tenant_id
                    && status.is_none_or(|s| inv.status == s)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn mark_invoice_paid(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        _payment_id: Uuid,
    ) -> Result<Invoice> {
        let mut store = self.invoices.write().await;
        let inv = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))?;

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

        inv.status = "paid".to_string();
        inv.paid_at = Some(Utc::now());
        Ok(inv.clone())
    }

    // ── Payments ────────────────────────────────────────────────────────

    async fn record_payment(
        &self,
        tenant_id: Uuid,
        mut payment: Payment,
    ) -> Result<Payment> {
        let mut counter = self.pay_counter.write().await;
        *counter += 1;
        let pay_number = Self::generate_payment_number(*counter);
        drop(counter);

        payment.id = Uuid::new_v4();
        payment.tenant_id = tenant_id;
        payment.payment_number = pay_number;
        payment.received_at = Utc::now();

        let id = payment.id;
        self.payments.write().await.insert(id, payment.clone());
        self.publish_event(PaymentProcessedEvent::new(
            tenant_id,
            id,
            payment.payment_method.clone(),
            payment.amount,
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
                p.tenant_id == tenant_id
                    && invoice_id.is_none_or(|inv_id| p.invoice_id == inv_id)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Budget ──────────────────────────────────────────────────────────

    async fn create_budget(
        &self,
        tenant_id: Uuid,
        mut budget: Budget,
    ) -> Result<Budget> {
        budget.id = Uuid::new_v4();
        budget.tenant_id = tenant_id;
        budget.spent_amount = 0.0;
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
        amount: f64,
    ) -> Result<Budget> {
        let mut store = self.budgets.write().await;
        let budget = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;

        if amount < 0.0 {
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
            entry.amount,
            entry.amount,
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
                    && account.is_none_or(|a| {
                        e.debit_account == a || e.credit_account == a
                    })
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Cost Rollup ─────────────────────────────────────────────────────

    async fn run_cost_rollup(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<CostRollup> {
        // Generate a realistic synthetic cost rollup
        let rollup = CostRollup {
            id: Uuid::new_v4(),
            tenant_id,
            product_id,
            product_name: format!("Product-{}", &product_id.to_string()[..8]),
            material_cost: 1250.75,
            labor_cost: 875.50,
            overhead_cost: 340.25,
            total_cost: 1250.75 + 875.50 + 340.25,
            rollup_date: Utc::now(),
        };

        self.cost_rollups
            .write()
            .await
            .insert(rollup.id, rollup.clone());
        self.publish_event(CostRollupCompleted::new(
            tenant_id,
            product_id,
            rollup.total_cost,
            "USD".to_string(),
        ))
        .await;
        Ok(rollup)
    }

    async fn get_cost_rollup(
        &self,
        _tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<CostRollup> {
        let store = self.cost_rollups.read().await;
        store
            .values()
            .find(|cr| cr.product_id == product_id)
            .cloned()
            .ok_or_else(|| {
                SenseiError::NotFound(format!(
                    "Cost rollup for product {product_id} not found"
                ))
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
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Invoice {id} not found"))
        })?;
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
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Payment {id} not found"))
        })?;
        Ok(())
    }

    // ── Budget Mutations ───────────────────────────────────────────────

    async fn update_budget(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        budget: Budget,
    ) -> Result<Budget> {
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
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Budget {id} not found"))
        })?;
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

    async fn delete_journal_entry(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.journal_entries.write().await;
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("JournalEntry {id} not found"))
        })?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
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
                    unit_price: 25.0,
                    total: 0.0,
                },
                InvoiceLineItem {
                    description: "Widget B".to_string(),
                    quantity: 5,
                    unit_price: 50.0,
                    total: 0.0,
                },
            ],
            subtotal: 0.0,
            tax_percentage: 10.0,
            tax_amount: 0.0,
            total_amount: 0.0,
            currency: "USD".to_string(),
            due_date: Utc::now() + chrono::Duration::days(30),
            paid_at: None,
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created = service
            .create_invoice(tenant_id, invoice)
            .await
            .expect("should create invoice");
        assert!(created.invoice_number.starts_with("INV-"));
        assert_eq!(created.status, "draft");
        // 10*25 + 5*50 = 250 + 250 = 500 subtotal
        assert_eq!(created.subtotal, 500.0);
        // 10% tax = 50.0
        assert_eq!(created.tax_amount, 50.0);
        // total = 550.0
        assert_eq!(created.total_amount, 550.0);

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
            line_items: vec![],
            subtotal: 100.0,
            tax_percentage: 0.0,
            tax_amount: 0.0,
            total_amount: 100.0,
            currency: "USD".to_string(),
            due_date: Utc::now() + chrono::Duration::days(30),
            paid_at: None,
            notes: String::new(),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
        };

        let created = service.create_invoice(tenant_id, invoice).await.unwrap();
        let paid = service
            .mark_invoice_paid(tenant_id, created.id, Uuid::new_v4())
            .await
            .unwrap();
        assert_eq!(paid.status, "paid");
        assert!(paid.paid_at.is_some());
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
            amount: 550.0,
            currency: "USD".to_string(),
            payment_method: "bank_transfer".to_string(),
            reference: "TRX-001".to_string(),
            received_at: Utc::now(),
            created_by: Uuid::new_v4(),
        };

        let created = service
            .record_payment(tenant_id, payment)
            .await
            .expect("should record payment");
        assert!(created.payment_number.starts_with("PAY-"));
        assert_eq!(created.amount, 550.0);
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
            allocated_amount: 10000.0,
            spent_amount: 0.0,
            remaining_amount: 0.0,
        };

        let created = service
            .create_budget(tenant_id, budget)
            .await
            .expect("should create budget");
        assert_eq!(created.remaining_amount, 10000.0);

        let allocated = service
            .allocate_budget(tenant_id, created.id, 5000.0)
            .await
            .unwrap();
        assert_eq!(allocated.allocated_amount, 15000.0);
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
            amount: 250.0,
            currency: "USD".to_string(),
            entry_date: Utc::now(),
            posted_by: Uuid::new_v4(),
        };

        let posted = service
            .post_journal_entry(tenant_id, entry)
            .await
            .expect("should post journal entry");
        assert!(posted.entry_number.starts_with("JE-"));
        assert_eq!(posted.amount, 250.0);
    }

    #[tokio::test]
    async fn test_cost_rollup() {
        let service = InMemoryFinanceService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        let rollup = service
            .run_cost_rollup(tenant_id, product_id)
            .await
            .expect("should run cost rollup");
        assert_eq!(rollup.product_id, product_id);
        assert!(rollup.total_cost > 0.0);
        assert_eq!(
            rollup.total_cost,
            rollup.material_cost + rollup.labor_cost + rollup.overhead_cost
        );
    }
}

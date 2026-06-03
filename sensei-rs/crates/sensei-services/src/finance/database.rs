//! PostgreSQL-backed finance service using sqlx.
//!
//! Provides invoice, payment, budget, journal entry, and cost rollup
//! management backed by PostgreSQL tables. Implements [`FinanceService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use serde_json;
use sqlx::PgPool;
use uuid::Uuid;

use super::{
    Budget, CostRollup, FinanceService, Invoice, InvoiceLineItem, JournalEntry, Payment,
};

// ---------------------------------------------------------------------------
// Row structs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct InvoiceRow {
    id: Uuid,
    tenant_id: Uuid,
    invoice_number: String,
    customer_id: Uuid,
    customer_name: String,
    status: String,
    line_items: serde_json::Value,
    subtotal: f64,
    tax_percentage: f64,
    tax_amount: f64,
    total_amount: f64,
    currency: String,
    due_date: chrono::DateTime<Utc>,
    paid_at: Option<chrono::DateTime<Utc>>,
    notes: String,
    created_by: Uuid,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct PaymentRow {
    id: Uuid,
    tenant_id: Uuid,
    payment_number: String,
    invoice_id: Uuid,
    amount: f64,
    currency: String,
    payment_method: String,
    reference: String,
    received_at: chrono::DateTime<Utc>,
    created_by: Uuid,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct BudgetRow {
    id: Uuid,
    tenant_id: Uuid,
    fiscal_year: i32,
    department: String,
    category: String,
    allocated_amount: f64,
    spent_amount: f64,
    remaining_amount: f64,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct JournalEntryRow {
    id: Uuid,
    tenant_id: Uuid,
    entry_number: String,
    description: String,
    debit_account: String,
    credit_account: String,
    amount: f64,
    currency: String,
    entry_date: chrono::DateTime<Utc>,
    posted_by: Uuid,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct CostRollupRow {
    id: Uuid,
    tenant_id: Uuid,
    product_id: Uuid,
    product_name: String,
    material_cost: f64,
    labor_cost: f64,
    overhead_cost: f64,
    total_cost: f64,
    rollup_date: chrono::DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn invoice_row_to_domain(r: InvoiceRow) -> Invoice {
    let line_items: Vec<InvoiceLineItem> = serde_json::from_value(r.line_items).unwrap_or_default();
    Invoice {
        id: r.id,
        tenant_id: r.tenant_id,
        invoice_number: r.invoice_number,
        customer_id: r.customer_id,
        customer_name: r.customer_name,
        status: r.status,
        line_items,
        subtotal: r.subtotal,
        tax_percentage: r.tax_percentage,
        tax_amount: r.tax_amount,
        total_amount: r.total_amount,
        currency: r.currency,
        due_date: r.due_date,
        paid_at: r.paid_at,
        notes: r.notes,
        created_by: r.created_by,
        created_at: r.created_at,
    }
}

fn payment_row_to_domain(r: PaymentRow) -> Payment {
    Payment {
        id: r.id,
        tenant_id: r.tenant_id,
        payment_number: r.payment_number,
        invoice_id: r.invoice_id,
        amount: r.amount,
        currency: r.currency,
        payment_method: r.payment_method,
        reference: r.reference,
        received_at: r.received_at,
        created_by: r.created_by,
    }
}

fn budget_row_to_domain(r: BudgetRow) -> Budget {
    Budget {
        id: r.id,
        tenant_id: r.tenant_id,
        fiscal_year: r.fiscal_year,
        department: r.department,
        category: r.category,
        allocated_amount: r.allocated_amount,
        spent_amount: r.spent_amount,
        remaining_amount: r.remaining_amount,
    }
}

fn journal_row_to_domain(r: JournalEntryRow) -> JournalEntry {
    JournalEntry {
        id: r.id,
        tenant_id: r.tenant_id,
        entry_number: r.entry_number,
        description: r.description,
        debit_account: r.debit_account,
        credit_account: r.credit_account,
        amount: r.amount,
        currency: r.currency,
        entry_date: r.entry_date,
        posted_by: r.posted_by,
    }
}

fn cost_rollup_row_to_domain(r: CostRollupRow) -> CostRollup {
    CostRollup {
        id: r.id,
        tenant_id: r.tenant_id,
        product_id: r.product_id,
        product_name: r.product_name,
        material_cost: r.material_cost,
        labor_cost: r.labor_cost,
        overhead_cost: r.overhead_cost,
        total_cost: r.total_cost,
        rollup_date: r.rollup_date,
    }
}

// ---------------------------------------------------------------------------
// Database service
// ---------------------------------------------------------------------------

/// PostgreSQL-backed implementation of [`FinanceService`].
pub struct DatabaseFinanceService {
    pool: PgPool,
}

impl DatabaseFinanceService {
    /// Create a new [`DatabaseFinanceService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl FinanceService for DatabaseFinanceService {
    // ── Invoices ────────────────────────────────────────────────────────

    async fn create_invoice(&self, tenant_id: Uuid, invoice: Invoice) -> Result<Invoice> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let invoice_number = format!("INV-{}-{}", now.format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

        let subtotal: f64 = invoice.line_items.iter().map(|li| li.quantity as f64 * li.unit_price).sum();
        let tax_amount = subtotal * invoice.tax_percentage / 100.0;
        let total_amount = subtotal + tax_amount;
        let line_items_json = serde_json::to_value(&invoice.line_items).unwrap_or(serde_json::Value::Array(vec![]));

        let row = sqlx::query_as::<_, InvoiceRow>(
            r#"
            INSERT INTO invoices (
                id, tenant_id, invoice_number, customer_id, customer_name,
                status, line_items, subtotal, tax_percentage, tax_amount,
                total_amount, currency, due_date, paid_at, notes, created_by, created_at
            ) VALUES ($1,$2,$3,$4,$5,'draft',$6,$7,$8,$9,$10,$11,$12,NULL,$13,$14,$15)
            RETURNING id, tenant_id, invoice_number, customer_id, customer_name,
                      status, line_items, subtotal, tax_percentage, tax_amount,
                      total_amount, currency, due_date, paid_at, notes, created_by, created_at
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&invoice_number)
        .bind(invoice.customer_id)
        .bind(&invoice.customer_name)
        .bind(&line_items_json)
        .bind(subtotal)
        .bind(invoice.tax_percentage)
        .bind(tax_amount)
        .bind(total_amount)
        .bind(&invoice.currency)
        .bind(invoice.due_date)
        .bind(&invoice.notes)
        .bind(invoice.created_by)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create invoice: {e}")))?;

        Ok(invoice_row_to_domain(row))
    }

    async fn get_invoice(&self, tenant_id: Uuid, id: Uuid) -> Result<Invoice> {
        let row = sqlx::query_as::<_, InvoiceRow>(
            r#"
            SELECT id, tenant_id, invoice_number, customer_id, customer_name,
                   status, line_items, subtotal, tax_percentage, tax_amount,
                   total_amount, currency, due_date, paid_at, notes, created_by, created_at
            FROM invoices WHERE id = $1 AND tenant_id = $2
            "#,
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get invoice: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))?;

        Ok(invoice_row_to_domain(row))
    }

    async fn list_invoices(
        &self, tenant_id: Uuid, status: Option<&str>, page: Option<usize>, per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Invoice>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<InvoiceRow> = sqlx::query_as(
            r#"
            SELECT id, tenant_id, invoice_number, customer_id, customer_name,
                   status, line_items, subtotal, tax_percentage, tax_amount,
                   total_amount, currency, due_date, paid_at, notes, created_by, created_at
            FROM invoices WHERE tenant_id = $1 AND ($2::text IS NULL OR status = $2)
            ORDER BY created_at DESC LIMIT $3 OFFSET $4
            "#,
        )
        .bind(tenant_id).bind(status).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list invoices: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM invoices WHERE tenant_id = $1 AND ($2::text IS NULL OR status = $2)",
        )
        .bind(tenant_id).bind(status)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count invoices: {e}")))?;

        let items = items.into_iter().map(invoice_row_to_domain).collect();
        Ok(PaginatedResponse { data: items, total: count as usize, page, per_page, total_pages: ((count as usize).max(1) + per_page - 1) / per_page })
    }

    async fn mark_invoice_paid(&self, tenant_id: Uuid, id: Uuid, _payment_id: Uuid) -> Result<Invoice> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, InvoiceRow>(
            r#"
            UPDATE invoices SET status = 'paid', paid_at = $1
            WHERE id = $2 AND tenant_id = $3 AND status != 'paid' AND status != 'cancelled'
            RETURNING id, tenant_id, invoice_number, customer_id, customer_name,
                      status, line_items, subtotal, tax_percentage, tax_amount,
                      total_amount, currency, due_date, paid_at, notes, created_by, created_at
            "#,
        )
        .bind(now).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to mark invoice paid: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found or cannot be marked paid")))?;

        Ok(invoice_row_to_domain(row))
    }

    // ── Payments ────────────────────────────────────────────────────────

    async fn record_payment(&self, tenant_id: Uuid, payment: Payment) -> Result<Payment> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let payment_number = format!("PAY-{}-{}", now.format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

        let row = sqlx::query_as::<_, PaymentRow>(
            r#"
            INSERT INTO payments (id, tenant_id, payment_number, invoice_id, amount, currency, payment_method, reference, received_at, created_by)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id, tenant_id, payment_number, invoice_id, amount, currency, payment_method, reference, received_at, created_by
            "#,
        )
        .bind(id).bind(tenant_id).bind(&payment_number)
        .bind(payment.invoice_id).bind(payment.amount).bind(&payment.currency)
        .bind(&payment.payment_method).bind(&payment.reference).bind(now).bind(payment.created_by)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to record payment: {e}")))?;

        Ok(payment_row_to_domain(row))
    }

    async fn list_payments(
        &self, tenant_id: Uuid, invoice_id: Option<Uuid>, page: Option<usize>, per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Payment>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<PaymentRow> = sqlx::query_as(
            r#"
            SELECT id, tenant_id, payment_number, invoice_id, amount, currency, payment_method, reference, received_at, created_by
            FROM payments WHERE tenant_id = $1 AND ($2::uuid IS NULL OR invoice_id = $2)
            ORDER BY received_at DESC LIMIT $3 OFFSET $4
            "#,
        )
        .bind(tenant_id).bind(invoice_id).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list payments: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM payments WHERE tenant_id = $1 AND ($2::uuid IS NULL OR invoice_id = $2)",
        )
        .bind(tenant_id).bind(invoice_id)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count payments: {e}")))?;

        let items = items.into_iter().map(payment_row_to_domain).collect();
        Ok(PaginatedResponse { data: items, total: count as usize, page, per_page, total_pages: ((count as usize).max(1) + per_page - 1) / per_page })
    }

    // ── Budget ──────────────────────────────────────────────────────────

    async fn create_budget(&self, tenant_id: Uuid, budget: Budget) -> Result<Budget> {
        let id = Uuid::new_v4();
        let row = sqlx::query_as::<_, BudgetRow>(
            r#"
            INSERT INTO budgets (id, tenant_id, fiscal_year, department, category, allocated_amount, spent_amount, remaining_amount)
            VALUES ($1,$2,$3,$4,$5,$6,0,$6)
            RETURNING id, tenant_id, fiscal_year, department, category, allocated_amount, spent_amount, remaining_amount
            "#,
        )
        .bind(id).bind(tenant_id).bind(budget.fiscal_year).bind(&budget.department)
        .bind(&budget.category).bind(budget.allocated_amount)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create budget: {e}")))?;

        Ok(budget_row_to_domain(row))
    }

    async fn get_budget(&self, tenant_id: Uuid, id: Uuid) -> Result<Budget> {
        let row = sqlx::query_as::<_, BudgetRow>(
            "SELECT id, tenant_id, fiscal_year, department, category, allocated_amount, spent_amount, remaining_amount FROM budgets WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get budget: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;

        Ok(budget_row_to_domain(row))
    }

    async fn list_budgets(
        &self, tenant_id: Uuid, fiscal_year: Option<i32>, department: Option<&str>, page: Option<usize>, per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Budget>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<BudgetRow> = sqlx::query_as(
            r#"
            SELECT id, tenant_id, fiscal_year, department, category, allocated_amount, spent_amount, remaining_amount
            FROM budgets WHERE tenant_id = $1 AND ($2::int IS NULL OR fiscal_year = $2) AND ($3::text IS NULL OR department = $3)
            ORDER BY fiscal_year DESC, department LIMIT $4 OFFSET $5
            "#,
        )
        .bind(tenant_id).bind(fiscal_year).bind(department).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list budgets: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM budgets WHERE tenant_id = $1 AND ($2::int IS NULL OR fiscal_year = $2) AND ($3::text IS NULL OR department = $3)",
        )
        .bind(tenant_id).bind(fiscal_year).bind(department)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count budgets: {e}")))?;

        let items = items.into_iter().map(budget_row_to_domain).collect();
        Ok(PaginatedResponse { data: items, total: count as usize, page, per_page, total_pages: ((count as usize).max(1) + per_page - 1) / per_page })
    }

    async fn allocate_budget(&self, tenant_id: Uuid, id: Uuid, amount: f64) -> Result<Budget> {
        let row = sqlx::query_as::<_, BudgetRow>(
            r#"
            UPDATE budgets SET allocated_amount = allocated_amount + $1, remaining_amount = remaining_amount + $1
            WHERE id = $2 AND tenant_id = $3
            RETURNING id, tenant_id, fiscal_year, department, category, allocated_amount, spent_amount, remaining_amount
            "#,
        )
        .bind(amount).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to allocate budget: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;

        Ok(budget_row_to_domain(row))
    }

    // ── Journal Entries ─────────────────────────────────────────────────

    async fn post_journal_entry(&self, tenant_id: Uuid, entry: JournalEntry) -> Result<JournalEntry> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let entry_number = format!("JE-{}-{}", now.format("%Y%m%d"), id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string());

        let row = sqlx::query_as::<_, JournalEntryRow>(
            r#"
            INSERT INTO journal_entries (id, tenant_id, entry_number, description, debit_account, credit_account, amount, currency, entry_date, posted_by)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id, tenant_id, entry_number, description, debit_account, credit_account, amount, currency, entry_date, posted_by
            "#,
        )
        .bind(id).bind(tenant_id).bind(&entry_number).bind(&entry.description)
        .bind(&entry.debit_account).bind(&entry.credit_account).bind(entry.amount)
        .bind(&entry.currency).bind(entry.entry_date).bind(entry.posted_by)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to post journal entry: {e}")))?;

        Ok(journal_row_to_domain(row))
    }

    async fn list_journal_entries(
        &self, tenant_id: Uuid, account: Option<&str>, page: Option<usize>, per_page: Option<usize>,
    ) -> Result<PaginatedResponse<JournalEntry>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<JournalEntryRow> = sqlx::query_as(
            r#"
            SELECT id, tenant_id, entry_number, description, debit_account, credit_account, amount, currency, entry_date, posted_by
            FROM journal_entries WHERE tenant_id = $1 AND ($2::text IS NULL OR debit_account = $2 OR credit_account = $2)
            ORDER BY entry_date DESC LIMIT $3 OFFSET $4
            "#,
        )
        .bind(tenant_id).bind(account).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list journal entries: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM journal_entries WHERE tenant_id = $1 AND ($2::text IS NULL OR debit_account = $2 OR credit_account = $2)",
        )
        .bind(tenant_id).bind(account)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count journal entries: {e}")))?;

        let items = items.into_iter().map(journal_row_to_domain).collect();
        Ok(PaginatedResponse { data: items, total: count as usize, page, per_page, total_pages: ((count as usize).max(1) + per_page - 1) / per_page })
    }

    // ── Invoice Mutations ──────────────────────────────────────────────

    async fn update_invoice(&self, tenant_id: Uuid, id: Uuid, invoice: Invoice) -> Result<Invoice> {
        let line_items_json = serde_json::to_value(&invoice.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let subtotal: f64 = invoice.line_items.iter().map(|li| li.quantity as f64 * li.unit_price).sum();
        let tax_amount = subtotal * invoice.tax_percentage / 100.0;
        let total_amount = subtotal + tax_amount;

        let row = sqlx::query_as::<_, InvoiceRow>(
            r#"
            UPDATE invoices SET customer_id=$1, customer_name=$2, line_items=$3,
                subtotal=$4, tax_percentage=$5, tax_amount=$6, total_amount=$7,
                currency=$8, due_date=$9, notes=$10
            WHERE id=$11 AND tenant_id=$12
            RETURNING id, tenant_id, invoice_number, customer_id, customer_name,
                      status, line_items, subtotal, tax_percentage, tax_amount,
                      total_amount, currency, due_date, paid_at, notes, created_by, created_at
            "#,
        )
        .bind(invoice.customer_id).bind(&invoice.customer_name).bind(&line_items_json)
        .bind(subtotal).bind(invoice.tax_percentage).bind(tax_amount).bind(total_amount)
        .bind(&invoice.currency).bind(invoice.due_date).bind(&invoice.notes)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update invoice: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Invoice {id} not found")))?;

        Ok(invoice_row_to_domain(row))
    }

    async fn delete_invoice(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM invoices WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete invoice: {e}")))?;

        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Invoice {id} not found")));
        }
        Ok(())
    }

    // ── Payment Mutations ──────────────────────────────────────────────

    async fn update_payment(&self, tenant_id: Uuid, id: Uuid, payment: Payment) -> Result<Payment> {
        let row = sqlx::query_as::<_, PaymentRow>(
            r#"
            UPDATE payments SET amount=$1, currency=$2, payment_method=$3, reference=$4
            WHERE id=$5 AND tenant_id=$6
            RETURNING id, tenant_id, payment_number, invoice_id, amount, currency, payment_method, reference, received_at, created_by
            "#,
        )
        .bind(payment.amount).bind(&payment.currency).bind(&payment.payment_method).bind(&payment.reference)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update payment: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Payment {id} not found")))?;

        Ok(payment_row_to_domain(row))
    }

    async fn delete_payment(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM payments WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete payment: {e}")))?;

        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Payment {id} not found")));
        }
        Ok(())
    }

    // ── Budget Mutations ───────────────────────────────────────────────

    async fn update_budget(&self, tenant_id: Uuid, id: Uuid, budget: Budget) -> Result<Budget> {
        let row = sqlx::query_as::<_, BudgetRow>(
            r#"
            UPDATE budgets SET fiscal_year=$1, department=$2, category=$3, allocated_amount=$4, remaining_amount=$4 - spent_amount
            WHERE id=$5 AND tenant_id=$6
            RETURNING id, tenant_id, fiscal_year, department, category, allocated_amount, spent_amount, remaining_amount
            "#,
        )
        .bind(budget.fiscal_year).bind(&budget.department).bind(&budget.category).bind(budget.allocated_amount)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update budget: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Budget {id} not found")))?;

        Ok(budget_row_to_domain(row))
    }

    async fn delete_budget(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM budgets WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete budget: {e}")))?;

        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Budget {id} not found")));
        }
        Ok(())
    }

    // ── Journal Entry Mutations ────────────────────────────────────────

    async fn update_journal_entry(&self, tenant_id: Uuid, id: Uuid, entry: JournalEntry) -> Result<JournalEntry> {
        let row = sqlx::query_as::<_, JournalEntryRow>(
            r#"
            UPDATE journal_entries SET description=$1, debit_account=$2, credit_account=$3, amount=$4, currency=$5, entry_date=$6
            WHERE id=$7 AND tenant_id=$8
            RETURNING id, tenant_id, entry_number, description, debit_account, credit_account, amount, currency, entry_date, posted_by
            "#,
        )
        .bind(&entry.description).bind(&entry.debit_account).bind(&entry.credit_account)
        .bind(entry.amount).bind(&entry.currency).bind(entry.entry_date)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update journal entry: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Journal entry {id} not found")))?;

        Ok(journal_row_to_domain(row))
    }

    async fn delete_journal_entry(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM journal_entries WHERE id = $1 AND tenant_id = $2")
            .bind(id).bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete journal entry: {e}")))?;

        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Journal entry {id} not found")));
        }
        Ok(())
    }

    // ── Cost Rollup ─────────────────────────────────────────────────────

    async fn run_cost_rollup(&self, tenant_id: Uuid, product_id: Uuid) -> Result<CostRollup> {
        let now = Utc::now();
        let id = Uuid::new_v4();

        let material_cost: f64 = sqlx::query_scalar(
            r#"SELECT COALESCE(SUM(bi.quantity_required * 10.0), 0.0) FROM bom_items bi WHERE bi.parent_product_id = $1 AND bi.tenant_id = $2"#,
        )
        .bind(product_id).bind(tenant_id)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to compute material cost: {e}")))?;

        let labor_cost = 0.0_f64;
        let overhead_cost = 0.0_f64;
        let total_cost = material_cost + labor_cost + overhead_cost;

        let product_name: String = sqlx::query_scalar(
            r#"SELECT name FROM products WHERE id = $1 AND tenant_id = $2"#,
        )
        .bind(product_id).bind(tenant_id)
        .fetch_optional(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to get product name: {e}")))?
        .unwrap_or_else(|| "Unknown Product".to_string());

        let row = sqlx::query_as::<_, CostRollupRow>(
            r#"
            INSERT INTO cost_rollups (id, tenant_id, product_id, product_name, material_cost, labor_cost, overhead_cost, total_cost, rollup_date)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            RETURNING id, tenant_id, product_id, product_name, material_cost, labor_cost, overhead_cost, total_cost, rollup_date
            "#,
        )
        .bind(id).bind(tenant_id).bind(product_id).bind(&product_name)
        .bind(material_cost).bind(labor_cost).bind(overhead_cost).bind(total_cost).bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create cost rollup: {e}")))?;

        Ok(cost_rollup_row_to_domain(row))
    }

    async fn get_cost_rollup(&self, tenant_id: Uuid, product_id: Uuid) -> Result<CostRollup> {
        let row = sqlx::query_as::<_, CostRollupRow>(
            r#"
            SELECT id, tenant_id, product_id, product_name, material_cost, labor_cost, overhead_cost, total_cost, rollup_date
            FROM cost_rollups WHERE product_id = $1 AND tenant_id = $2
            ORDER BY rollup_date DESC LIMIT 1
            "#,
        )
        .bind(product_id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get cost rollup: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Cost rollup for product {product_id} not found")))?;

        Ok(cost_rollup_row_to_domain(row))
    }
}

//! Finance store — accounts, journal entries, FX rates, standard costs,
//! cost rollups, tax jurisdictions/rules, currencies, payment terms,
//! bank accounts/transactions, and dashboard stats.
//!
//! Port of [`frontend/src/stores/finance.ts`](frontend/src/stores/finance.ts).

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Account {
    pub id: String,
    pub account_number: String,
    pub name: String,
    pub account_type: String, // "asset" | "liability" | "equity" | "revenue" | "expense"
    pub parent_id: Option<String>,
    pub currency: String,
    pub balance: f64,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct JournalEntry {
    pub id: String,
    pub entry_number: String,
    pub description: String,
    pub entry_date: String,
    pub debit_account_id: String,
    pub credit_account_id: String,
    pub amount: f64,
    pub currency: String,
    pub reference_type: Option<String>,
    pub reference_id: Option<String>,
    pub posted: bool,
    pub posted_at: Option<String>,
    pub created_by: String,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FxRate {
    pub from_currency: String,
    pub to_currency: String,
    pub rate: f64,
    pub as_of_date: String,
    pub source: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct StandardCost {
    pub id: String,
    pub sku: String,
    pub material_cost: f64,
    pub labor_cost: f64,
    pub overhead_cost: f64,
    pub total_cost: f64,
    pub effective_date: String,
    pub created_by: String,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CostRollup {
    pub id: String,
    pub work_order_id: String,
    pub actual_material: f64,
    pub actual_labor: f64,
    pub actual_overhead: f64,
    pub total_actual: f64,
    pub variance_from_standard: f64,
    pub rolled_up_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TaxJurisdiction {
    pub id: String,
    pub name: String,
    pub country: String,
    pub state_province: Option<String>,
    pub city: Option<String>,
    pub description: Option<String>,
    pub is_active: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TaxRate {
    pub id: String,
    pub jurisdiction_id: String,
    pub name: String,
    pub rate: f64,
    pub tax_type: String, // "sales" | "vat" | "withholding" | "customs"
    pub is_active: bool,
    pub effective_date: String,
    pub expiry_date: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TaxTransaction {
    pub id: String,
    pub reference_type: String,
    pub reference_id: String,
    pub tax_rate_id: String,
    pub taxable_amount: f64,
    pub tax_amount: f64,
    pub currency: String,
    pub transaction_date: String,
    pub posted: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CurrencyConfig {
    pub code: String,
    pub symbol: String,
    pub name: String,
    pub decimal_places: i32,
    pub is_base: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Currency {
    pub code: String,
    pub symbol: String,
    pub name: String,
    pub decimal_places: i32,
    pub is_active: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PaymentTerm {
    pub id: String,
    pub name: String,
    pub description: String,
    pub due_days: i32,
    pub discount_percentage: f64,
    pub discount_days: Option<i32>,
    pub is_active: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BankAccount {
    pub id: String,
    pub bank_name: String,
    pub account_number: String,
    pub account_name: String,
    pub currency: String,
    pub balance: f64,
    pub account_type: String,
    pub is_active: bool,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BankTransaction {
    pub id: String,
    pub bank_account_id: String,
    pub transaction_type: String, // "deposit" | "withdrawal" | "transfer" | "payment"
    pub amount: f64,
    pub currency: String,
    pub description: String,
    pub reference: Option<String>,
    pub transaction_date: String,
    pub reconciled: bool,
    pub reconciled_at: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FinanceDashboardStats {
    pub total_revenue: f64,
    pub total_expenses: f64,
    pub net_income: f64,
    pub cash_balance: f64,
    pub accounts_receivable: f64,
    pub accounts_payable: f64,
    pub pending_invoices: i32,
    pub overdue_payments: i32,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RevenueByProduct {
    pub product_id: String,
    pub product_name: String,
    pub revenue: f64,
    pub quantity: i32,
    pub period: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ExpenseBreakdown {
    pub category: String,
    pub amount: f64,
    pub percentage: f64,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PendingApproval {
    pub id: String,
    pub approval_type: String,
    pub reference_id: String,
    pub reference_description: String,
    pub amount: f64,
    pub currency: String,
    pub requested_by: String,
    pub requested_at: String,
    pub urgency: String,
}

// ---------------------------------------------------------------------------
// FinanceStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct FinanceStore {
    // Data signals
    pub accounts: RwSignal<Vec<Account>>,
    pub journal_entries: RwSignal<Vec<JournalEntry>>,
    pub fx_rates: RwSignal<Vec<FxRate>>,
    pub standard_costs: RwSignal<Vec<StandardCost>>,
    pub cost_rollups: RwSignal<Vec<CostRollup>>,
    pub tax_jurisdictions: RwSignal<Vec<TaxJurisdiction>>,
    pub tax_rates: RwSignal<Vec<TaxRate>>,
    pub tax_transactions: RwSignal<Vec<TaxTransaction>>,
    pub currencies: RwSignal<Vec<Currency>>,
    pub payment_terms: RwSignal<Vec<PaymentTerm>>,
    pub bank_accounts: RwSignal<Vec<BankAccount>>,
    pub bank_transactions: RwSignal<Vec<BankTransaction>>,

    // Dashboard
    pub dashboard_stats: RwSignal<Option<FinanceDashboardStats>>,
    pub revenue_by_product: RwSignal<Vec<RevenueByProduct>>,
    pub expense_breakdown: RwSignal<Vec<ExpenseBreakdown>>,
    pub pending_approvals: RwSignal<Vec<PendingApproval>>,

    // Currency settings
    pub currency_settings: RwSignal<Option<CurrencyConfig>>,

    // Loading & error
    pub loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
}

impl FinanceStore {
    pub fn new() -> Self {
        Self {
            accounts: RwSignal::new(Vec::new()),
            journal_entries: RwSignal::new(Vec::new()),
            fx_rates: RwSignal::new(Vec::new()),
            standard_costs: RwSignal::new(Vec::new()),
            cost_rollups: RwSignal::new(Vec::new()),
            tax_jurisdictions: RwSignal::new(Vec::new()),
            tax_rates: RwSignal::new(Vec::new()),
            tax_transactions: RwSignal::new(Vec::new()),
            currencies: RwSignal::new(Vec::new()),
            payment_terms: RwSignal::new(Vec::new()),
            bank_accounts: RwSignal::new(Vec::new()),
            bank_transactions: RwSignal::new(Vec::new()),
            dashboard_stats: RwSignal::new(None),
            revenue_by_product: RwSignal::new(Vec::new()),
            expense_breakdown: RwSignal::new(Vec::new()),
            pending_approvals: RwSignal::new(Vec::new()),
            currency_settings: RwSignal::new(None),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }

    // -----------------------------------------------------------------------
    // Accounts
    // -----------------------------------------------------------------------

    pub async fn fetch_accounts(&self, client: &ApiClient) {
        self.loading.set(true);
        match client.get::<Vec<Account>>("/finance/accounts").await {
            Ok(items) => self.accounts.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn create_account(
        &self,
        client: &ApiClient,
        account: serde_json::Value,
    ) -> Result<Account, ApiError> {
        match client
            .post::<Account, serde_json::Value>("/finance/accounts", &account)
            .await
        {
            Ok(created) => {
                self.accounts.update(|a| a.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Journal Entries
    // -----------------------------------------------------------------------

    pub async fn fetch_journal_entries(&self, client: &ApiClient) {
        self.loading.set(true);
        match client
            .get::<Vec<JournalEntry>>("/finance/journal-entries")
            .await
        {
            Ok(items) => self.journal_entries.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    // -----------------------------------------------------------------------
    // Currency Settings
    // -----------------------------------------------------------------------

    pub async fn fetch_currency_settings(&self, client: &ApiClient) {
        match client
            .get::<CurrencyConfig>("/finance/currency-settings")
            .await
        {
            Ok(settings) => self.currency_settings.set(Some(settings)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn update_currency_settings(
        &self,
        client: &ApiClient,
        settings: serde_json::Value,
    ) -> Result<CurrencyConfig, ApiError> {
        match client
            .put::<CurrencyConfig, serde_json::Value>("/finance/currency-settings", &settings)
            .await
        {
            Ok(updated) => {
                self.currency_settings.set(Some(updated.clone()));
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // FX Rates
    // -----------------------------------------------------------------------

    pub async fn fetch_fx_rates(&self, client: &ApiClient, as_of: Option<&str>) {
        let path = match as_of {
            Some(date) => format!("/finance/fx-rates?as_of={date}"),
            None => "/finance/fx-rates".to_string(),
        };
        match client.get::<Vec<FxRate>>(&path).await {
            Ok(items) => self.fx_rates.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn upsert_fx_rate(
        &self,
        client: &ApiClient,
        rate: serde_json::Value,
    ) -> Result<FxRate, ApiError> {
        match client
            .post::<FxRate, serde_json::Value>("/finance/fx-rates", &rate)
            .await
        {
            Ok(created) => {
                self.fx_rates.update(|r| r.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Standard Costs
    // -----------------------------------------------------------------------

    pub async fn fetch_standard_costs(&self, client: &ApiClient, sku: Option<&str>) {
        let path = match sku {
            Some(s) => format!("/finance/standard-costs?sku={s}"),
            None => "/finance/standard-costs".to_string(),
        };
        match client.get::<Vec<StandardCost>>(&path).await {
            Ok(items) => self.standard_costs.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn upsert_standard_cost(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<StandardCost, ApiError> {
        match client
            .post::<StandardCost, serde_json::Value>("/finance/standard-costs", &payload)
            .await
        {
            Ok(created) => {
                self.standard_costs.update(|c| c.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Cost Rollups
    // -----------------------------------------------------------------------

    pub async fn fetch_cost_rollups(&self, client: &ApiClient, work_order_id: Option<&str>) {
        let path = match work_order_id {
            Some(id) => format!("/finance/cost-rollups?work_order_id={id}"),
            None => "/finance/cost-rollups".to_string(),
        };
        match client.get::<Vec<CostRollup>>(&path).await {
            Ok(items) => self.cost_rollups.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_cost_rollup(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<CostRollup, ApiError> {
        match client
            .post::<CostRollup, serde_json::Value>("/finance/cost-rollups", &payload)
            .await
        {
            Ok(created) => {
                self.cost_rollups.update(|c| c.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Tax Jurisdictions
    // -----------------------------------------------------------------------

    pub async fn fetch_tax_jurisdictions(&self, client: &ApiClient) {
        match client
            .get::<Vec<TaxJurisdiction>>("/finance/tax-jurisdictions")
            .await
        {
            Ok(items) => self.tax_jurisdictions.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_tax_jurisdiction(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<TaxJurisdiction, ApiError> {
        match client
            .post::<TaxJurisdiction, serde_json::Value>("/finance/tax-jurisdictions", &payload)
            .await
        {
            Ok(created) => {
                self.tax_jurisdictions.update(|j| j.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Tax Rates
    // -----------------------------------------------------------------------

    pub async fn fetch_tax_rates(&self, client: &ApiClient, jurisdiction_id: &str) {
        match client
            .get::<Vec<TaxRate>>(&format!(
                "/finance/tax-jurisdictions/{jurisdiction_id}/rates"
            ))
            .await
        {
            Ok(items) => self.tax_rates.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_tax_rate(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<TaxRate, ApiError> {
        match client
            .post::<TaxRate, serde_json::Value>("/finance/tax-rates", &payload)
            .await
        {
            Ok(created) => {
                self.tax_rates.update(|r| r.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Tax Transactions
    // -----------------------------------------------------------------------

    pub async fn fetch_tax_transactions(&self, client: &ApiClient, reference_id: Option<&str>) {
        let path = match reference_id {
            Some(id) => format!("/finance/tax-transactions?reference_id={id}"),
            None => "/finance/tax-transactions".to_string(),
        };
        match client.get::<Vec<TaxTransaction>>(&path).await {
            Ok(items) => self.tax_transactions.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_tax_transaction(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<TaxTransaction, ApiError> {
        match client
            .post::<TaxTransaction, serde_json::Value>("/finance/tax-transactions", &payload)
            .await
        {
            Ok(created) => {
                self.tax_transactions.update(|t| t.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Dashboard
    // -----------------------------------------------------------------------

    pub async fn fetch_dashboard_stats(&self, client: &ApiClient) {
        match client
            .get::<FinanceDashboardStats>("/finance/dashboard/stats")
            .await
        {
            Ok(stats) => self.dashboard_stats.set(Some(stats)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn fetch_revenue_by_product(&self, client: &ApiClient) {
        match client
            .get::<Vec<RevenueByProduct>>("/finance/dashboard/revenue-by-product")
            .await
        {
            Ok(items) => self.revenue_by_product.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn fetch_expense_breakdown(&self, client: &ApiClient) {
        match client
            .get::<Vec<ExpenseBreakdown>>("/finance/dashboard/expense-breakdown")
            .await
        {
            Ok(items) => self.expense_breakdown.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn fetch_pending_approvals(&self, client: &ApiClient) {
        match client
            .get::<Vec<PendingApproval>>("/finance/dashboard/pending-approvals")
            .await
        {
            Ok(items) => self.pending_approvals.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn fetch_all(&self, client: &ApiClient) {
        self.loading.set(true);
        // Fetch all dashboard data in parallel-like fashion
        // In WASM, these will run sequentially but provide a convenient "load everything" method
        self.fetch_dashboard_stats(client).await;
        self.fetch_revenue_by_product(client).await;
        self.fetch_expense_breakdown(client).await;
        self.fetch_pending_approvals(client).await;
        self.loading.set(false);
    }

    // -----------------------------------------------------------------------
    // Currencies
    // -----------------------------------------------------------------------

    pub async fn fetch_currencies(&self, client: &ApiClient) {
        match client.get::<Vec<Currency>>("/finance/currencies").await {
            Ok(items) => self.currencies.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_currency(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<Currency, ApiError> {
        match client
            .post::<Currency, serde_json::Value>("/finance/currencies", &payload)
            .await
        {
            Ok(created) => {
                self.currencies.update(|c| c.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    pub async fn update_currency(
        &self,
        client: &ApiClient,
        id: &str,
        payload: serde_json::Value,
    ) -> Result<Currency, ApiError> {
        match client
            .put::<Currency, serde_json::Value>(&format!("/finance/currencies/{id}"), &payload)
            .await
        {
            Ok(updated) => {
                self.currencies.update(|c| {
                    if let Some(pos) = c.iter().position(|x| x.code == id) {
                        c[pos] = updated.clone();
                    }
                });
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Payment Terms
    // -----------------------------------------------------------------------

    pub async fn fetch_payment_terms(&self, client: &ApiClient) {
        match client
            .get::<Vec<PaymentTerm>>("/finance/payment-terms")
            .await
        {
            Ok(items) => self.payment_terms.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_payment_term(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<PaymentTerm, ApiError> {
        match client
            .post::<PaymentTerm, serde_json::Value>("/finance/payment-terms", &payload)
            .await
        {
            Ok(created) => {
                self.payment_terms.update(|p| p.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    pub async fn update_payment_term(
        &self,
        client: &ApiClient,
        id: &str,
        payload: serde_json::Value,
    ) -> Result<PaymentTerm, ApiError> {
        match client
            .put::<PaymentTerm, serde_json::Value>(
                &format!("/finance/payment-terms/{id}"),
                &payload,
            )
            .await
        {
            Ok(updated) => {
                self.payment_terms.update(|p| {
                    if let Some(pos) = p.iter().position(|x| x.id == id) {
                        p[pos] = updated.clone();
                    }
                });
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Bank Accounts
    // -----------------------------------------------------------------------

    pub async fn fetch_bank_accounts(&self, client: &ApiClient) {
        match client
            .get::<Vec<BankAccount>>("/finance/bank-accounts")
            .await
        {
            Ok(items) => self.bank_accounts.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_bank_account(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<BankAccount, ApiError> {
        match client
            .post::<BankAccount, serde_json::Value>("/finance/bank-accounts", &payload)
            .await
        {
            Ok(created) => {
                self.bank_accounts.update(|b| b.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    pub async fn update_bank_account(
        &self,
        client: &ApiClient,
        id: &str,
        payload: serde_json::Value,
    ) -> Result<BankAccount, ApiError> {
        match client
            .put::<BankAccount, serde_json::Value>(
                &format!("/finance/bank-accounts/{id}"),
                &payload,
            )
            .await
        {
            Ok(updated) => {
                self.bank_accounts.update(|b| {
                    if let Some(pos) = b.iter().position(|x| x.id == id) {
                        b[pos] = updated.clone();
                    }
                });
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Bank Transactions
    // -----------------------------------------------------------------------

    pub async fn fetch_bank_transactions(&self, client: &ApiClient, bank_account_id: &str) {
        match client
            .get::<Vec<BankTransaction>>(&format!(
                "/finance/bank-accounts/{bank_account_id}/transactions"
            ))
            .await
        {
            Ok(items) => self.bank_transactions.set(items),
            Err(e) => self.error.set(Some(e.to_string())),
        }
    }

    pub async fn create_bank_transaction(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<BankTransaction, ApiError> {
        match client
            .post::<BankTransaction, serde_json::Value>("/finance/bank-transactions", &payload)
            .await
        {
            Ok(created) => {
                self.bank_transactions.update(|t| t.push(created.clone()));
                Ok(created)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }

    pub async fn reconcile_bank_transaction(
        &self,
        client: &ApiClient,
        id: &str,
    ) -> Result<BankTransaction, ApiError> {
        match client
            .post::<BankTransaction, serde_json::Value>(
                &format!("/finance/bank-transactions/{id}/reconcile"),
                &serde_json::json!({}),
            )
            .await
        {
            Ok(updated) => {
                self.bank_transactions.update(|t| {
                    if let Some(pos) = t.iter().position(|x| x.id == id) {
                        t[pos] = updated.clone();
                    }
                });
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                Err(e)
            }
        }
    }
}

impl Default for FinanceStore {
    fn default() -> Self {
        Self::new()
    }
}

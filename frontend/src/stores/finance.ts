import { create } from 'zustand';
import { apiClient } from '@/api/client';

// ─── Domain Types ──────────────────────────────────────────────────────────────

interface Account {
  id: string;
  code: string;
  name: string;
  type: string;
  parent_id?: string | null;
  currency: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

interface JournalEntry {
  id: string;
  entry_number: string;
  description: string;
  entry_date: string;
  status: string;
  total_debit: number;
  total_credit: number;
  created_by: string;
  created_at: string;
}

interface FxRate {
  id: string;
  from_currency: string;
  to_currency: string;
  rate: number;
  effective_date: string;
}

interface StandardCost {
  id: string;
  sku: string;
  material_cost: number;
  labor_cost: number;
  overhead_cost: number;
  total_cost: number;
  effective_date: string;
}

interface CostRollup {
  id: string;
  work_order_id: string;
  material_cost: number;
  labor_cost: number;
  overhead_cost: number;
  total_cost: number;
  status: string;
}

interface TaxJurisdiction {
  id: string;
  name: string;
  code: string;
  country: string;
  active: boolean;
}

interface TaxRate {
  id: string;
  jurisdiction_id: string;
  name: string;
  rate: number;
  tax_type: string;
  effective_date: string;
}

interface TaxTransaction {
  id: string;
  reference_id: string;
  tax_amount: number;
  rate_applied: number;
  jurisdiction_id: string;
  created_at: string;
}

interface CurrencyConfig {
  base_currency: string;
  supported_currencies: string[];
  auto_update_rates: boolean;
}

interface Currency {
  id: string;
  code: string;
  name: string;
  symbol: string;
  active: boolean;
}

interface PaymentTerm {
  id: string;
  name: string;
  days: number;
  discount_percent: number;
  discount_days: number;
}

interface BankAccount {
  id: string;
  name: string;
  account_number: string;
  bank_name: string;
  currency: string;
  balance: number;
  active: boolean;
}

interface BankTransaction {
  id: string;
  bank_account_id: string;
  date: string;
  description: string;
  amount: number;
  type: string;
  reconciled: boolean;
}

interface DashboardStats {
  revenue_mtd: number;
  revenue_change: number;
  gross_margin: number;
  margin_change: number;
  opex: number;
  budget_utilization: number;
  liquidity_reserve: number;
  liquidity_status: string;
  total_accounts: number;
  active_accounts: number;
  total_journal_entries: number;
  pending_approvals: number;
  overdue_invoices: number;
  overdue_amount: number;
}

interface RevenueByProduct {
  name: string;
  revenue: number;
  percentage: number;
}

interface ExpenseBreakdown {
  category: string;
  amount: number;
  percentage: number;
  status: string;
}

interface PendingApproval {
  id: string;
  type: string;
  description: string;
  amount: number;
  requestor: string;
  submitted: string;
}

// ─── Error auto-clear timeout (ms) ────────────────────────────────────────────
const ERROR_CLEAR_DELAY = 8_000;
let _errorTimer: ReturnType<typeof setTimeout> | null = null;

function setErrorWithAutoClear(set: (partial: Partial<FinanceState>) => void, message: string) {
  if (_errorTimer) clearTimeout(_errorTimer);
  set({ error: message, loading: false });
  _errorTimer = setTimeout(() => set({ error: null }), ERROR_CLEAR_DELAY);
}

interface FinanceState {
  accounts: Account[];
  journalEntries: JournalEntry[];
  currencySettings: CurrencyConfig | null;
  fxRates: FxRate[];
  standardCosts: StandardCost[];
  costRollups: CostRollup[];
  taxJurisdictions: TaxJurisdiction[];
  taxRates: TaxRate[];
  taxTransactions: TaxTransaction[];
  dashboardStats: DashboardStats | null;
  revenueByProduct: RevenueByProduct[];
  expenseBreakdown: ExpenseBreakdown[];
  pendingApprovals: PendingApproval[];
  // Banking
  currencies: Currency[];
  paymentTerms: PaymentTerm[];
  bankAccounts: BankAccount[];
  bankTransactions: BankTransaction[];
  loading: boolean;
  error: string | null;

  fetchAccounts: () => Promise<void>;
  fetchJournalEntries: () => Promise<void>;
  createAccount: (account: Partial<Account>) => Promise<void>;
  fetchCurrencySettings: () => Promise<void>;
  updateCurrencySettings: (settings: Partial<CurrencyConfig>) => Promise<void>;
  fetchFxRates: (asOf?: string) => Promise<void>;
  upsertFxRate: (rate: Partial<FxRate>) => Promise<void>;
  fetchStandardCosts: (sku?: string) => Promise<void>;
  upsertStandardCost: (payload: Partial<StandardCost>) => Promise<void>;
  fetchCostRollups: (workOrderId?: string) => Promise<void>;
  createCostRollup: (payload: Partial<CostRollup>) => Promise<void>;
  fetchTaxJurisdictions: () => Promise<void>;
  createTaxJurisdiction: (payload: Partial<TaxJurisdiction>) => Promise<void>;
  fetchTaxRates: (jurisdictionId?: string) => Promise<void>;
  createTaxRate: (payload: Partial<TaxRate>) => Promise<void>;
  fetchTaxTransactions: (referenceId?: string) => Promise<void>;
  createTaxTransaction: (payload: Partial<TaxTransaction>) => Promise<void>;
  fetchDashboardStats: () => Promise<void>;
  fetchRevenueByProduct: () => Promise<void>;
  fetchExpenseBreakdown: () => Promise<void>;
  fetchPendingApprovals: () => Promise<void>;
  fetchAll: () => Promise<void>;
  // Banking methods
  fetchCurrencies: () => Promise<void>;
  createCurrency: (payload: Partial<Currency>) => Promise<void>;
  updateCurrency: (id: string, payload: Partial<Currency>) => Promise<void>;
  fetchPaymentTerms: () => Promise<void>;
  createPaymentTerm: (payload: Partial<PaymentTerm>) => Promise<void>;
  updatePaymentTerm: (id: string, payload: Partial<PaymentTerm>) => Promise<void>;
  fetchBankAccounts: () => Promise<void>;
  createBankAccount: (payload: Partial<BankAccount>) => Promise<void>;
  updateBankAccount: (id: string, payload: Partial<BankAccount>) => Promise<void>;
  fetchBankTransactions: (bankAccountId?: string) => Promise<void>;
  createBankTransaction: (payload: Partial<BankTransaction>) => Promise<void>;
  reconcileBankTransaction: (id: string) => Promise<void>;
}

export const useFinanceStore = create<FinanceState>((set, get) => ({
  accounts: [],
  journalEntries: [],
  currencySettings: null,
  fxRates: [],
  standardCosts: [],
  costRollups: [],
  taxJurisdictions: [],
  taxRates: [],
  taxTransactions: [],
  dashboardStats: null,
  revenueByProduct: [],
  expenseBreakdown: [],
  pendingApprovals: [],
  // Banking
  currencies: [],
  paymentTerms: [],
  bankAccounts: [],
  bankTransactions: [],
  loading: false,
  error: null,

  fetchAccounts: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/accounts');
      set({ accounts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchJournalEntries: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/journal-entries');
      set({ journalEntries: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createAccount: async (account) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/accounts', account);
      const response = await apiClient.get<any[]>('/finance/accounts');
      set({ accounts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchCurrencySettings: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any>('/finance/currency-settings');
      set({ currencySettings: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  updateCurrencySettings: async (settings) => {
    set({ loading: true });
    try {
      const response = await apiClient.post<any>('/finance/currency-settings', settings);
      set({ currencySettings: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchFxRates: async (asOf) => {
    set({ loading: true });
    try {
      const params = asOf ? { as_of: asOf } : undefined;
      const response = await apiClient.get<any[]>('/finance/fx-rates', { params });
      set({ fxRates: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  upsertFxRate: async (rate) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/fx-rates', rate);
      const response = await apiClient.get<any[]>('/finance/fx-rates');
      set({ fxRates: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchStandardCosts: async (sku) => {
    set({ loading: true });
    try {
      const params = sku ? { sku } : undefined;
      const response = await apiClient.get<any[]>('/finance/costing/standard-costs', { params });
      set({ standardCosts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  upsertStandardCost: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/costing/standard-costs', payload);
      const response = await apiClient.get<any[]>('/finance/costing/standard-costs');
      set({ standardCosts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchCostRollups: async (workOrderId) => {
    set({ loading: true });
    try {
      const params = workOrderId ? { work_order_id: workOrderId } : undefined;
      const response = await apiClient.get<any[]>('/finance/costing/rollups', { params });
      set({ costRollups: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createCostRollup: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/costing/rollups', payload);
      const response = await apiClient.get<any[]>('/finance/costing/rollups');
      set({ costRollups: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchTaxJurisdictions: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/tax/jurisdictions');
      set({ taxJurisdictions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createTaxJurisdiction: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/tax/jurisdictions', payload);
      const response = await apiClient.get<any[]>('/finance/tax/jurisdictions');
      set({ taxJurisdictions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchTaxRates: async (jurisdictionId) => {
    set({ loading: true });
    try {
      const params = jurisdictionId ? { jurisdiction_id: jurisdictionId } : undefined;
      const response = await apiClient.get<any[]>('/finance/tax/rates', { params });
      set({ taxRates: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createTaxRate: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/tax/rates', payload);
      const response = await apiClient.get<any[]>('/finance/tax/rates');
      set({ taxRates: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchTaxTransactions: async (referenceId) => {
    set({ loading: true });
    try {
      const params = referenceId ? { reference_id: referenceId } : undefined;
      const response = await apiClient.get<any[]>('/finance/tax/transactions', { params });
      set({ taxTransactions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createTaxTransaction: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/tax/transactions', payload);
      const response = await apiClient.get<any[]>('/finance/tax/transactions');
      set({ taxTransactions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchDashboardStats: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<DashboardStats>('/finance/dashboard-stats');
      set({ dashboardStats: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchRevenueByProduct: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<RevenueByProduct[]>('/finance/revenue-by-product');
      set({ revenueByProduct: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchExpenseBreakdown: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<ExpenseBreakdown[]>('/finance/expense-breakdown');
      set({ expenseBreakdown: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchPendingApprovals: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<PendingApproval[]>('/finance/pending-approvals');
      set({ pendingApprovals: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  fetchAll: async () => {
    const { fetchDashboardStats, fetchRevenueByProduct, fetchExpenseBreakdown, fetchPendingApprovals } = get();
    await Promise.all([
      fetchDashboardStats(),
      fetchRevenueByProduct(),
      fetchExpenseBreakdown(),
      fetchPendingApprovals(),
    ]);
  },

  // Banking - Currencies
  fetchCurrencies: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/currencies');
      set({ currencies: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createCurrency: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/currencies', payload);
      const response = await apiClient.get<any[]>('/finance/currencies');
      set({ currencies: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  updateCurrency: async (id, payload) => {
    set({ loading: true });
    try {
      await apiClient.patch(`/finance/currencies/${id}`, payload);
      const response = await apiClient.get<any[]>('/finance/currencies');
      set({ currencies: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  // Payment Terms
  fetchPaymentTerms: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/payment-terms');
      set({ paymentTerms: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createPaymentTerm: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/payment-terms', payload);
      const response = await apiClient.get<any[]>('/finance/payment-terms');
      set({ paymentTerms: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  updatePaymentTerm: async (id, payload) => {
    set({ loading: true });
    try {
      await apiClient.patch(`/finance/payment-terms/${id}`, payload);
      const response = await apiClient.get<any[]>('/finance/payment-terms');
      set({ paymentTerms: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  // Bank Accounts
  fetchBankAccounts: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/bank-accounts');
      set({ bankAccounts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createBankAccount: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/bank-accounts', payload);
      const response = await apiClient.get<any[]>('/finance/bank-accounts');
      set({ bankAccounts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  updateBankAccount: async (id, payload) => {
    set({ loading: true });
    try {
      await apiClient.patch(`/finance/bank-accounts/${id}`, payload);
      const response = await apiClient.get<any[]>('/finance/bank-accounts');
      set({ bankAccounts: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  // Bank Transactions
  fetchBankTransactions: async (bankAccountId) => {
    set({ loading: true });
    try {
      const params = bankAccountId ? { bank_account_id: bankAccountId } : undefined;
      const response = await apiClient.get<any[]>('/finance/bank-transactions', { params });
      set({ bankTransactions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  createBankTransaction: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/bank-transactions', payload);
      const response = await apiClient.get<any[]>('/finance/bank-transactions');
      set({ bankTransactions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },

  reconcileBankTransaction: async (id) => {
    set({ loading: true });
    try {
      await apiClient.post(`/finance/bank-transactions/${id}/reconcile`);
      const response = await apiClient.get<any[]>('/finance/bank-transactions');
      set({ bankTransactions: response, loading: false });
    } catch (error: any) {
      setErrorWithAutoClear(set, error.message);
    }
  },
}));

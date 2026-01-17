import { create } from 'zustand';
import { apiClient } from '@/api/client';

interface FinanceState {
  accounts: any[];
  journalEntries: any[];
  currencySettings: any | null;
  fxRates: any[];
  standardCosts: any[];
  costRollups: any[];
  taxJurisdictions: any[];
  taxRates: any[];
  taxTransactions: any[];
  loading: boolean;
  error: string | null;

  fetchAccounts: () => Promise<void>;
  fetchJournalEntries: () => Promise<void>;
  createAccount: (account: any) => Promise<void>;
  fetchCurrencySettings: () => Promise<void>;
  updateCurrencySettings: (settings: any) => Promise<void>;
  fetchFxRates: (asOf?: string) => Promise<void>;
  upsertFxRate: (rate: any) => Promise<void>;
  fetchStandardCosts: (sku?: string) => Promise<void>;
  upsertStandardCost: (payload: any) => Promise<void>;
  fetchCostRollups: (workOrderId?: string) => Promise<void>;
  createCostRollup: (payload: any) => Promise<void>;
  fetchTaxJurisdictions: () => Promise<void>;
  createTaxJurisdiction: (payload: any) => Promise<void>;
  fetchTaxRates: (jurisdictionId?: string) => Promise<void>;
  createTaxRate: (payload: any) => Promise<void>;
  fetchTaxTransactions: (referenceId?: string) => Promise<void>;
  createTaxTransaction: (payload: any) => Promise<void>;
}

export const useFinanceStore = create<FinanceState>((set) => ({
  accounts: [],
  journalEntries: [],
  currencySettings: null,
  fxRates: [],
  standardCosts: [],
  costRollups: [],
  taxJurisdictions: [],
  taxRates: [],
  taxTransactions: [],
  loading: false,
  error: null,

  fetchAccounts: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/accounts');
      set({ accounts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchJournalEntries: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/journal-entries');
      set({ journalEntries: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createAccount: async (account) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/accounts', account);
      const response = await apiClient.get<any[]>('/finance/accounts');
      set({ accounts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchCurrencySettings: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any>('/finance/currency-settings');
      set({ currencySettings: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  updateCurrencySettings: async (settings) => {
    set({ loading: true });
    try {
      const response = await apiClient.post<any>('/finance/currency-settings', settings);
      set({ currencySettings: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchFxRates: async (asOf) => {
    set({ loading: true });
    try {
      const params = asOf ? { as_of: asOf } : undefined;
      const response = await apiClient.get<any[]>('/finance/fx-rates', { params });
      set({ fxRates: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  upsertFxRate: async (rate) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/fx-rates', rate);
      const response = await apiClient.get<any[]>('/finance/fx-rates');
      set({ fxRates: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchStandardCosts: async (sku) => {
    set({ loading: true });
    try {
      const params = sku ? { sku } : undefined;
      const response = await apiClient.get<any[]>('/finance/costing/standard-costs', { params });
      set({ standardCosts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  upsertStandardCost: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/costing/standard-costs', payload);
      const response = await apiClient.get<any[]>('/finance/costing/standard-costs');
      set({ standardCosts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchCostRollups: async (workOrderId) => {
    set({ loading: true });
    try {
      const params = workOrderId ? { work_order_id: workOrderId } : undefined;
      const response = await apiClient.get<any[]>('/finance/costing/rollups', { params });
      set({ costRollups: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createCostRollup: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/costing/rollups', payload);
      const response = await apiClient.get<any[]>('/finance/costing/rollups');
      set({ costRollups: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchTaxJurisdictions: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<any[]>('/finance/tax/jurisdictions');
      set({ taxJurisdictions: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createTaxJurisdiction: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/tax/jurisdictions', payload);
      const response = await apiClient.get<any[]>('/finance/tax/jurisdictions');
      set({ taxJurisdictions: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchTaxRates: async (jurisdictionId) => {
    set({ loading: true });
    try {
      const params = jurisdictionId ? { jurisdiction_id: jurisdictionId } : undefined;
      const response = await apiClient.get<any[]>('/finance/tax/rates', { params });
      set({ taxRates: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createTaxRate: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/tax/rates', payload);
      const response = await apiClient.get<any[]>('/finance/tax/rates');
      set({ taxRates: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchTaxTransactions: async (referenceId) => {
    set({ loading: true });
    try {
      const params = referenceId ? { reference_id: referenceId } : undefined;
      const response = await apiClient.get<any[]>('/finance/tax/transactions', { params });
      set({ taxTransactions: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createTaxTransaction: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/tax/transactions', payload);
      const response = await apiClient.get<any[]>('/finance/tax/transactions');
      set({ taxTransactions: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

import { create } from 'zustand';
import { apiClient } from '@/api/client';

interface FinanceState {
  accounts: any[];
  journalEntries: any[];
  currencySettings: any | null;
  fxRates: any[];
  standardCosts: any[];
  costRollups: any[];
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
}

export const useFinanceStore = create<FinanceState>((set) => ({
  accounts: [],
  journalEntries: [],
  currencySettings: null,
  fxRates: [],
  standardCosts: [],
  costRollups: [],
  loading: false,
  error: null,

  fetchAccounts: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get('/finance/accounts');
      set({ accounts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchJournalEntries: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get('/finance/journal-entries');
      set({ journalEntries: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createAccount: async (account) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/accounts', account);
      const response = await apiClient.get('/finance/accounts');
      set({ accounts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchCurrencySettings: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get('/finance/currency-settings');
      set({ currencySettings: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  updateCurrencySettings: async (settings) => {
    set({ loading: true });
    try {
      const response = await apiClient.post('/finance/currency-settings', settings);
      set({ currencySettings: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchFxRates: async (asOf) => {
    set({ loading: true });
    try {
      const params = asOf ? { as_of: asOf } : undefined;
      const response = await apiClient.get('/finance/fx-rates', { params });
      set({ fxRates: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  upsertFxRate: async (rate) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/fx-rates', rate);
      const response = await apiClient.get('/finance/fx-rates');
      set({ fxRates: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchStandardCosts: async (sku) => {
    set({ loading: true });
    try {
      const params = sku ? { sku } : undefined;
      const response = await apiClient.get('/finance/costing/standard-costs', { params });
      set({ standardCosts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  upsertStandardCost: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/costing/standard-costs', payload);
      const response = await apiClient.get('/finance/costing/standard-costs');
      set({ standardCosts: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchCostRollups: async (workOrderId) => {
    set({ loading: true });
    try {
      const params = workOrderId ? { work_order_id: workOrderId } : undefined;
      const response = await apiClient.get('/finance/costing/rollups', { params });
      set({ costRollups: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createCostRollup: async (payload) => {
    set({ loading: true });
    try {
      await apiClient.post('/finance/costing/rollups', payload);
      const response = await apiClient.get('/finance/costing/rollups');
      set({ costRollups: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

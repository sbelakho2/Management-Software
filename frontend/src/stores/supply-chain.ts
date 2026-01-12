import { create } from 'zustand';
import { supplyChainApi, DisruptionScenario, SupplyChainStats } from '@/api/supply-chain';

interface SupplyChainState {
  scenarios: DisruptionScenario[];
  stats: SupplyChainStats | null;
  riskAnalysis: any | null;
  loading: boolean;
  error: string | null;

  fetchStats: () => Promise<void>;
  fetchScenarios: () => Promise<void>;
  fetchRiskAnalysis: () => Promise<void>;
}

export const useSupplyChainStore = create<SupplyChainState>((set) => ({
  scenarios: [],
  stats: null,
  riskAnalysis: null,
  loading: false,
  error: null,

  fetchStats: async () => {
    set({ loading: true, error: null });
    try {
      const stats = await supplyChainApi.getStats();
      set({ stats, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchScenarios: async () => {
    set({ loading: true, error: null });
    try {
      const scenarios = await supplyChainApi.listScenarios();
      set({ scenarios, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchRiskAnalysis: async () => {
    set({ loading: true, error: null });
    try {
      const riskAnalysis = await supplyChainApi.getRiskAnalysis();
      set({ riskAnalysis, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

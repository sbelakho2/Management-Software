import { create } from 'zustand';
import { analyticsApi, MLInsight, PerformanceTrend } from '@/api/analytics';

interface AnalyticsState {
  insights: MLInsight[];
  trends: PerformanceTrend[];
  health: any | null;
  loading: boolean;
  error: string | null;

  fetchInsights: () => Promise<void>;
  fetchTrends: () => Promise<void>;
  fetchHealth: () => Promise<void>;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  insights: [],
  trends: [],
  health: null,
  loading: false,
  error: null,

  fetchInsights: async () => {
    set({ loading: true, error: null });
    try {
      const insights = await analyticsApi.getInsights();
      set({ insights, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchTrends: async () => {
    set({ loading: true, error: null });
    try {
      const trends = await analyticsApi.getTrends();
      set({ trends, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchHealth: async () => {
    set({ loading: true, error: null });
    try {
      const health = await analyticsApi.getHealth();
      set({ health, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

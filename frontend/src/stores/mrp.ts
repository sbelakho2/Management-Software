import { create } from 'zustand';
import { apiClient } from '@/api/client';
import type { MPSPlan, MPSPlanLine } from '@/types';

interface MRPState {
  mpsPlans: MPSPlan[];
  mpsLines: MPSPlanLine[];
  loading: boolean;
  error: string | null;

  fetchMpsPlans: () => Promise<void>;
  createMpsPlan: (payload: Partial<MPSPlan> & { name: string; period_start: string; period_end: string }) => Promise<void>;
  fetchMpsLines: (planId: string) => Promise<void>;
  createMpsLine: (planId: string, payload: Partial<MPSPlanLine> & { product_id: number; bucket_date: string; quantity: number }) => Promise<void>;
}

export const useMrpStore = create<MRPState>((set, get) => ({
  mpsPlans: [],
  mpsLines: [],
  loading: false,
  error: null,

  fetchMpsPlans: async () => {
    set({ loading: true, error: null });
    try {
      const response = await apiClient.get<MPSPlan[]>('/mrp/mps/plans');
      set({ mpsPlans: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createMpsPlan: async (payload) => {
    set({ loading: true, error: null });
    try {
      await apiClient.post('/mrp/mps/plans', payload);
      await get().fetchMpsPlans();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchMpsLines: async (planId) => {
    set({ loading: true, error: null });
    try {
      const response = await apiClient.get<MPSPlanLine[]>(`/mrp/mps/plans/${planId}/lines`);
      set({ mpsLines: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createMpsLine: async (planId, payload) => {
    set({ loading: true, error: null });
    try {
      await apiClient.post(`/mrp/mps/plans/${planId}/lines`, payload);
      await get().fetchMpsLines(planId);
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

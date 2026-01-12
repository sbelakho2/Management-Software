import { create } from 'zustand';
import { maintenanceApi, Asset, MaintenanceWorkOrder, MaintenanceStats } from '@/api/maintenance';

interface MaintenanceState {
  assets: Asset[];
  workOrders: MaintenanceWorkOrder[];
  stats: MaintenanceStats | null;
  loading: boolean;
  error: string | null;

  fetchStats: () => Promise<void>;
  fetchAssets: () => Promise<void>;
  fetchWorkOrders: () => Promise<void>;
}

export const useMaintenanceStore = create<MaintenanceState>((set) => ({
  assets: [],
  workOrders: [],
  stats: null,
  loading: false,
  error: null,

  fetchStats: async () => {
    set({ loading: true, error: null });
    try {
      const stats = await maintenanceApi.getStats();
      set({ stats, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchAssets: async () => {
    set({ loading: true, error: null });
    try {
      const assets = await maintenanceApi.listAssets();
      set({ assets, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchWorkOrders: async () => {
    set({ loading: true, error: null });
    try {
      const workOrders = await maintenanceApi.listWorkOrders();
      set({ workOrders, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

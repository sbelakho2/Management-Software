import { create } from 'zustand';
import { productionApi, WorkOrder } from '@/api/production';

interface ProductionState {
  workOrders: WorkOrder[];
  totalWorkOrders: number;
  stats: any | null;
  loading: boolean;
  error: string | null;

  fetchWorkOrders: (params?: any) => Promise<void>;
  fetchStats: () => Promise<void>;
  updateWorkOrderStatus: (id: number, status: string) => Promise<void>;
}

export const useProductionStore = create<ProductionState>((set, get) => ({
  workOrders: [],
  totalWorkOrders: 0,
  stats: null,
  loading: false,
  error: null,

  fetchWorkOrders: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await productionApi.listWorkOrders(params);
      set({ 
        workOrders: response.items, 
        totalWorkOrders: response.total,
        loading: false 
      });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const stats = await productionApi.getStats();
      set({ stats });
    } catch (error) {
      console.error('Failed to fetch production stats:', error);
    }
  },

  updateWorkOrderStatus: async (id, status) => {
    try {
      await productionApi.updateWorkOrder(id, { status });
      await get().fetchWorkOrders();
    } catch (error: any) {
      set({ error: error.message });
    }
  },
}));

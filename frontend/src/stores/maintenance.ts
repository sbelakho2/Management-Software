import { create } from 'zustand';
import { maintenanceApi, Asset, MaintenanceWorkOrder, MaintenanceStats, LOTOProcedure, LOTOLock, ToolItem, ToolCheckout, AssetWarranty, MaintenanceBudget, FieldReturn } from '@/api/maintenance';

interface MaintenanceState {
  assets: Asset[];
  workOrders: MaintenanceWorkOrder[];
  stats: MaintenanceStats | null;
  lotoProcedures: LOTOProcedure[];
  activeLotoLocks: LOTOLock[];
  tools: ToolItem[];
  activeToolCheckouts: ToolCheckout[];
  warranties: AssetWarranty[];
  fieldReturns: FieldReturn[];
  pmSchedules: any[];
  pmRoute: any[];
  budgets: MaintenanceBudget[];
  loading: boolean;
  error: string | null;

  fetchStats: () => Promise<void>;
  fetchAssets: () => Promise<void>;
  fetchWorkOrders: () => Promise<void>;
  fetchLotoProcedures: () => Promise<void>;
  fetchActiveLotoLocks: () => Promise<void>;
  fetchTools: () => Promise<void>;
  fetchActiveToolCheckouts: () => Promise<void>;
  fetchWarranties: () => Promise<void>;
  fetchFieldReturns: () => Promise<void>;
  fetchPMSchedules: () => Promise<void>;
  fetchPMRoute: (daysAhead?: number) => Promise<void>;
  fetchBudgets: () => Promise<void>;
}

export const useMaintenanceStore = create<MaintenanceState>((set) => ({
  assets: [],
  workOrders: [],
  stats: null,
  lotoProcedures: [],
  activeLotoLocks: [],
  tools: [],
  activeToolCheckouts: [],
  warranties: [],
  fieldReturns: [],
  pmSchedules: [],
  pmRoute: [],
  budgets: [],
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

  fetchLotoProcedures: async () => {
    set({ loading: true, error: null });
    try {
      const lotoProcedures = await maintenanceApi.listLotoProcedures();
      set({ lotoProcedures, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchActiveLotoLocks: async () => {
    set({ loading: true, error: null });
    try {
      const activeLotoLocks = await maintenanceApi.listActiveLotoLocks();
      set({ activeLotoLocks, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchTools: async () => {
    set({ loading: true, error: null });
    try {
      const tools = await maintenanceApi.listTools();
      set({ tools, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchActiveToolCheckouts: async () => {
    set({ loading: true, error: null });
    try {
      const activeToolCheckouts = await maintenanceApi.listActiveToolCheckouts();
      set({ activeToolCheckouts, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchWarranties: async () => {
    set({ loading: true, error: null });
    try {
      const warranties = await maintenanceApi.listWarranties();
      set({ warranties, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchFieldReturns: async () => {
    set({ loading: true, error: null });
    try {
      const fieldReturns = await maintenanceApi.listFieldReturns();
      set({ fieldReturns, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchPMSchedules: async () => {
    set({ loading: true, error: null });
    try {
      const pmSchedules = await maintenanceApi.listPMSchedules();
      set({ pmSchedules, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchPMRoute: async (daysAhead: number = 7) => {
    set({ loading: true, error: null });
    try {
      const pmRoute = await maintenanceApi.getPMRoute(daysAhead);
      set({ pmRoute, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchBudgets: async () => {
    set({ loading: true, error: null });
    try {
      const budgets = await maintenanceApi.listMaintenanceBudgets();
      set({ budgets, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));

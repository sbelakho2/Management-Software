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
  /** @deprecated Use loadingOps for per-operation states */
  loading: boolean;
  /** Set of currently in-progress operation names */
  loadingOps: Set<string>;
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
  /** Check if a specific operation is in progress */
  isOpLoading: (op: string) => boolean;
}


/* ── Per-operation loading helpers ─────────────────────────────────── */
function startOp(set: (fn: (s: MaintenanceState) => Partial<MaintenanceState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.add(op);
    return { loadingOps: next, loading: true, error: null };
  });
}
function endOp(set: (fn: (s: MaintenanceState) => Partial<MaintenanceState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.delete(op);
    return { loadingOps: next, loading: next.size > 0 };
  });
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
  loadingOps: new Set<string>(),
  error: null,

  fetchStats: async () => {
    startOp(set, 'fetchStats');
    try {
      const stats = await maintenanceApi.getStats();
      set({ stats });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchStats');
      }
  },

  fetchAssets: async () => {
    startOp(set, 'fetchAssets');
    try {
      const assets = await maintenanceApi.listAssets();
      set({ assets });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchAssets');
      }
  },

  fetchWorkOrders: async () => {
    startOp(set, 'fetchWorkOrders');
    try {
      const workOrders = await maintenanceApi.listWorkOrders();
      set({ workOrders });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchWorkOrders');
      }
  },

  fetchLotoProcedures: async () => {
    startOp(set, 'fetchLotoProcedures');
    try {
      const lotoProcedures = await maintenanceApi.listLotoProcedures();
      set({ lotoProcedures });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchLotoProcedures');
      }
  },

  fetchActiveLotoLocks: async () => {
    startOp(set, 'fetchActiveLotoLocks');
    try {
      const activeLotoLocks = await maintenanceApi.listActiveLotoLocks();
      set({ activeLotoLocks });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchActiveLotoLocks');
      }
  },

  fetchTools: async () => {
    startOp(set, 'fetchTools');
    try {
      const tools = await maintenanceApi.listTools();
      set({ tools });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchTools');
      }
  },

  fetchActiveToolCheckouts: async () => {
    startOp(set, 'fetchActiveToolCheckouts');
    try {
      const activeToolCheckouts = await maintenanceApi.listActiveToolCheckouts();
      set({ activeToolCheckouts });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchActiveToolCheckouts');
      }
  },

  fetchWarranties: async () => {
    startOp(set, 'fetchWarranties');
    try {
      const warranties = await maintenanceApi.listWarranties();
      set({ warranties });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchWarranties');
      }
  },

  fetchFieldReturns: async () => {
    startOp(set, 'fetchFieldReturns');
    try {
      const fieldReturns = await maintenanceApi.listFieldReturns();
      set({ fieldReturns });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchFieldReturns');
      }
  },

  fetchPMSchedules: async () => {
    startOp(set, 'fetchPMSchedules');
    try {
      const pmSchedules = await maintenanceApi.listPMSchedules();
      set({ pmSchedules });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchPMSchedules');
      }
  },

  fetchPMRoute: async (daysAhead: number = 7) => {
    startOp(set, 'fetchPMRoute');
    try {
      const pmRoute = await maintenanceApi.getPMRoute(daysAhead);
      set({ pmRoute });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchPMRoute');
      }
  },

  fetchBudgets: async () => {
    startOp(set, 'fetchBudgets');
    try {
      const budgets = await maintenanceApi.listMaintenanceBudgets();
      set({ budgets });
    } catch (error: any) {
      set({ error: error.message });
    }
      finally {
        endOp(set, 'fetchBudgets');
      }
  },
}));

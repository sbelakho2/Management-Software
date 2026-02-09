/**
 * Production Store
 * 
 * Zustand store for managing production/manufacturing state including:
 * - Work orders CRUD operations
 * - Production statistics
 * - Real-time status updates
 * 
 * @module stores/production
 */

import { create } from 'zustand';
import { productionApi, WorkOrder, WorkOrderFilters, ProductionStats, UpdateWorkOrderData, CreateWorkOrderData } from '@/api/production';

/**
 * Production store state interface
 */
interface ProductionState {
  /** List of work orders */
  workOrders: WorkOrder[];
  /** Total count for pagination */
  totalWorkOrders: number;
  /** Production statistics */
  stats: ProductionStats | null;
  /** Loading state for async operations */
  /** @deprecated Use loadingOps for per-operation states */
  loading: boolean;
  /** Set of currently in-progress operation names */
  loadingOps: Set<string>;
  /** Error message if any operation fails */
  error: string | null;

  /** Fetch work orders with optional filters */
  fetchWorkOrders: (params?: WorkOrderFilters) => Promise<void>;
  /** Fetch production statistics */
  fetchStats: () => Promise<void>;
  /** Update a work order's status */
  updateWorkOrderStatus: (id: number, status: string) => Promise<void>;
  /** Create a new work order */
  createWorkOrder: (data: CreateWorkOrderData) => Promise<WorkOrder>;
  /** Check if a specific operation is in progress */
  isOpLoading: (op: string) => boolean;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'An unexpected error occurred';
}


/* ── Per-operation loading helpers ─────────────────────────────────── */
function startOp(set: (fn: (s: ProductionState) => Partial<ProductionState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.add(op);
    return { loadingOps: next, loading: true, error: null };
  });
}
function endOp(set: (fn: (s: ProductionState) => Partial<ProductionState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.delete(op);
    return { loadingOps: next, loading: next.size > 0 };
  });
}

export const useProductionStore = create<ProductionState>((set, get) => ({
  workOrders: [],
  totalWorkOrders: 0,
  stats: null,
  loading: false,
  loadingOps: new Set<string>(),
  error: null,

  fetchWorkOrders: async (params) => {
    startOp(set, 'fetchWorkOrders');
    try {
      const response = await productionApi.listWorkOrders(params);
      const items = Array.isArray(response.items) ? response.items : [];
      const total = typeof response.total === 'number' ? response.total : items.length;
      set({ 
        workOrders: items,
        totalWorkOrders: total,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
    finally {
      endOp(set, 'fetchWorkOrders');
    }
  },

  fetchStats: async () => {
    try {
      const stats = await productionApi.getStats();
      set({ stats });
    } catch (error: unknown) {
      // Stats fetch is non-critical, log but don't block UI
      console.warn('Failed to fetch production stats:', getErrorMessage(error));
    }
    finally {
      endOp(set, 'fetchStats');
    }
  },

  updateWorkOrderStatus: async (id, status) => {
    try {
      await productionApi.updateWorkOrder(id, { status } as UpdateWorkOrderData);
      await get().fetchWorkOrders();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
    finally {
      endOp(set, 'updateWorkOrderStatus');
    }
  },

  createWorkOrder: async (data) => {
    startOp(set, 'createWorkOrder');
    try {
      const workOrder = await productionApi.createWorkOrder(data);
      set((state) => ({ 
        workOrders: [workOrder, ...state.workOrders],
        totalWorkOrders: state.totalWorkOrders + 1,
      }));
      return workOrder;
    } catch (error: unknown) {
      const errorMsg = getErrorMessage(error);
      set({ error: errorMsg });
      throw new Error(errorMsg);
    }
      finally {
        endOp(set, 'createWorkOrder');
      }
  },

  isOpLoading: (op: string) => get().loadingOps.has(op),
}));

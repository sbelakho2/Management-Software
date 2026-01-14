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
import { productionApi, WorkOrder, WorkOrderFilters, ProductionStats, UpdateWorkOrderData } from '@/api/production';

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
  loading: boolean;
  /** Error message if any operation fails */
  error: string | null;

  /** Fetch work orders with optional filters */
  fetchWorkOrders: (params?: WorkOrderFilters) => Promise<void>;
  /** Fetch production statistics */
  fetchStats: () => Promise<void>;
  /** Update a work order's status */
  updateWorkOrderStatus: (id: number, status: string) => Promise<void>;
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
      const items = Array.isArray(response.items) ? response.items : [];
      const total = typeof response.total === 'number' ? response.total : items.length;
      set({ 
        workOrders: items,
        totalWorkOrders: total,
        loading: false 
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const stats = await productionApi.getStats();
      set({ stats });
    } catch {
      // Stats fetch is non-critical, silently fail
    }
  },

  updateWorkOrderStatus: async (id, status) => {
    try {
      await productionApi.updateWorkOrder(id, { status } as UpdateWorkOrderData);
      await get().fetchWorkOrders();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
  },
}));

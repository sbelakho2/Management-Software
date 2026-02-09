import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';
import type { Shipment, ShipmentLine, PickList, PickListLine } from '@/types';

export interface ShippingStats {
  pending_shipments: number;
  in_transit: number;
  delivered_today: number;
  pending_picks: number;
  picks_in_progress: number;
  completed_picks: number;
}

interface ShippingState {
  // Shipments
  shipments: Shipment[];
  selectedShipment: Shipment | null;
  // Pick Lists
  pickLists: PickList[];
  selectedPickList: PickList | null;
  // Stats
  stats: ShippingStats | null;
  // UI State
  /** @deprecated Use loadingOps for per-operation states */
  isLoading: boolean;
  /** Set of currently in-progress operation names */
  loadingOps: Set<string>;
  error: string | null;
  lastFetchedAt: number | null;

  // Shipment methods
  fetchShipments: (params?: { status?: string; account_id?: string }) => Promise<void>;
  fetchShipment: (id: string) => Promise<void>;
  createShipment: (payload: Partial<Shipment>) => Promise<void>;
  updateShipment: (id: string, payload: Partial<Shipment>) => Promise<void>;
  updateShipmentStatus: (id: string, status: string) => Promise<void>;
  addShipmentLine: (shipmentId: string, line: Partial<ShipmentLine>) => Promise<void>;
  
  // Pick List methods
  fetchPickLists: (params?: { status?: string; warehouse_id?: string }) => Promise<void>;
  fetchPickList: (id: string) => Promise<void>;
  createPickList: (payload: Partial<PickList>) => Promise<void>;
  updatePickList: (id: string, payload: Partial<PickList>) => Promise<void>;
  startPicking: (id: string) => Promise<void>;
  completePicking: (id: string) => Promise<void>;
  updatePickLine: (pickListId: string, lineId: string, quantityPicked: number) => Promise<void>;
  
  // Stats
  fetchStats: () => Promise<void>;
  clearError: () => void;
  /** Check if a specific operation is in progress */
  isOpLoading: (op: string) => boolean;
}


/* ── Per-operation loading helpers ─────────────────────────────────── */
function startOp(set: (fn: (s: ShippingState) => Partial<ShippingState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.add(op);
    return { loadingOps: next, isLoading: true, error: null };
  });
}
function endOp(set: (fn: (s: ShippingState) => Partial<ShippingState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.delete(op);
    return { loadingOps: next, isLoading: next.size > 0 };
  });
}

export const useShippingStore = create<ShippingState>()(
  devtools(
    persist(
      (set, get) => ({
        shipments: [],
        selectedShipment: null,
        pickLists: [],
        selectedPickList: null,
        stats: null,
        isLoading: false,
  loadingOps: new Set<string>(),
        error: null,
        lastFetchedAt: null,

        // Shipment methods
        fetchShipments: async (params) => {
          startOp(set, 'fetchShipments');
          try {
            let url = '/shipping/shipments';
            const queryParams = new URLSearchParams();
            if (params?.status) queryParams.append('status', params.status);
            if (params?.account_id) queryParams.append('account_id', params.account_id);
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: Shipment[] }>(url);
            set({ shipments: response.items || [], lastFetchedAt: Date.now() });
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'fetchShipments');
          }
        },

        fetchShipment: async (id) => {
          startOp(set, 'fetchShipment');
          try {
            const response = await apiClient.get<Shipment>(`/shipping/shipments/${id}`);
            set({ selectedShipment: response });
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'fetchShipment');
          }
        },

        createShipment: async (payload) => {
          startOp(set, 'createShipment');
          try {
            await apiClient.post('/shipping/shipments', payload);
            await get().fetchShipments();
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'createShipment');
          }
        },

        updateShipment: async (id, payload) => {
          startOp(set, 'updateShipment');
          try {
            await apiClient.patch(`/shipping/shipments/${id}`, payload);
            await get().fetchShipments();
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'updateShipment');
          }
        },

        updateShipmentStatus: async (id, status) => {
          startOp(set, 'updateShipmentStatus');
          try {
            await apiClient.post(`/shipping/shipments/${id}/status`, { status });
            await get().fetchShipments();
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'updateShipmentStatus');
          }
        },

        addShipmentLine: async (shipmentId, line) => {
          startOp(set, 'addShipmentLine');
          try {
            await apiClient.post(`/shipping/shipments/${shipmentId}/lines`, line);
            await get().fetchShipment(shipmentId);
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'addShipmentLine');
          }
        },

        // Pick List methods
        fetchPickLists: async (params) => {
          startOp(set, 'fetchPickLists');
          try {
            let url = '/wms/pick-lists';
            const queryParams = new URLSearchParams();
            if (params?.status) queryParams.append('status', params.status);
            if (params?.warehouse_id) queryParams.append('warehouse_id', params.warehouse_id);
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: PickList[] }>(url);
            set({ pickLists: response.items || [] });
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'fetchPickLists');
          }
        },

        fetchPickList: async (id) => {
          startOp(set, 'fetchPickList');
          try {
            const response = await apiClient.get<PickList>(`/wms/pick-lists/${id}`);
            set({ selectedPickList: response });
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'fetchPickList');
          }
        },

        createPickList: async (payload) => {
          startOp(set, 'createPickList');
          try {
            await apiClient.post('/wms/pick-lists', payload);
            await get().fetchPickLists();
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'createPickList');
          }
        },

        updatePickList: async (id, payload) => {
          startOp(set, 'updatePickList');
          try {
            await apiClient.patch(`/wms/pick-lists/${id}`, payload);
            await get().fetchPickLists();
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'updatePickList');
          }
        },

        startPicking: async (id) => {
          startOp(set, 'startPicking');
          try {
            await apiClient.post(`/wms/pick-lists/${id}/start`);
            await get().fetchPickList(id);
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'startPicking');
          }
        },

        completePicking: async (id) => {
          startOp(set, 'completePicking');
          try {
            await apiClient.post(`/wms/pick-lists/${id}/complete`);
            await get().fetchPickLists();
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'completePicking');
          }
        },

        updatePickLine: async (pickListId, lineId, quantityPicked) => {
          startOp(set, 'updatePickLine');
          try {
            await apiClient.patch(`/wms/pick-lists/${pickListId}/lines/${lineId}`, {
              quantity_picked: quantityPicked,
            });
            await get().fetchPickList(pickListId);
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'updatePickLine');
          }
        },

        // Stats
        fetchStats: async () => {
          const { lastFetchedAt, isLoading } = get();
          const now = Date.now();
          
          // Cache for 30 seconds
          if (lastFetchedAt && now - lastFetchedAt < 30000 && get().stats) {
            return;
          }
          
          if (isLoading) return;
          
          startOp(set, 'fetchStats');
          try {
            const data = await apiClient.get<ShippingStats>('/shipping/stats');
            set({ stats: data, lastFetchedAt: now });
          } catch (error) {
            set({ error: (error as Error).message });
          }
          finally {
            endOp(set, 'fetchStats');
          }
        },

        clearError: () => set({ error: null }),
        isOpLoading: (op: string) => get().loadingOps.has(op),
      }),
      {
        name: 'shipping-storage',
        partialize: (state) => ({
          lastFetchedAt: state.lastFetchedAt,
        }),
      }
    ),
    { name: 'shipping-store' }
  )
);

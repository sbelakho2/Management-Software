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
  isLoading: boolean;
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
        error: null,
        lastFetchedAt: null,

        // Shipment methods
        fetchShipments: async (params) => {
          set({ isLoading: true, error: null });
          try {
            let url = '/shipping/shipments';
            const queryParams = new URLSearchParams();
            if (params?.status) queryParams.append('status', params.status);
            if (params?.account_id) queryParams.append('account_id', params.account_id);
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: Shipment[] }>(url);
            set({ shipments: response.items || [], isLoading: false, lastFetchedAt: Date.now() });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchShipment: async (id) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.get<Shipment>(`/shipping/shipments/${id}`);
            set({ selectedShipment: response, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        createShipment: async (payload) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post('/shipping/shipments', payload);
            await get().fetchShipments();
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        updateShipment: async (id, payload) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.patch(`/shipping/shipments/${id}`, payload);
            await get().fetchShipments();
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        updateShipmentStatus: async (id, status) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/shipping/shipments/${id}/status`, { status });
            await get().fetchShipments();
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        addShipmentLine: async (shipmentId, line) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/shipping/shipments/${shipmentId}/lines`, line);
            await get().fetchShipment(shipmentId);
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        // Pick List methods
        fetchPickLists: async (params) => {
          set({ isLoading: true, error: null });
          try {
            let url = '/wms/pick-lists';
            const queryParams = new URLSearchParams();
            if (params?.status) queryParams.append('status', params.status);
            if (params?.warehouse_id) queryParams.append('warehouse_id', params.warehouse_id);
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: PickList[] }>(url);
            set({ pickLists: response.items || [], isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchPickList: async (id) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.get<PickList>(`/wms/pick-lists/${id}`);
            set({ selectedPickList: response, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        createPickList: async (payload) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post('/wms/pick-lists', payload);
            await get().fetchPickLists();
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        updatePickList: async (id, payload) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.patch(`/wms/pick-lists/${id}`, payload);
            await get().fetchPickLists();
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        startPicking: async (id) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/wms/pick-lists/${id}/start`);
            await get().fetchPickList(id);
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        completePicking: async (id) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/wms/pick-lists/${id}/complete`);
            await get().fetchPickLists();
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        updatePickLine: async (pickListId, lineId, quantityPicked) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.patch(`/wms/pick-lists/${pickListId}/lines/${lineId}`, {
              quantity_picked: quantityPicked,
            });
            await get().fetchPickList(pickListId);
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
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
          
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ShippingStats>('/shipping/stats');
            set({ stats: data, isLoading: false, lastFetchedAt: now });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        clearError: () => set({ error: null }),
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

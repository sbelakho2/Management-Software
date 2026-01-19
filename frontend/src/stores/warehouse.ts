import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

export interface WarehouseStats {
  total_items: number;
  low_stock: number;
  out_of_stock: number;
  pending_receipts: number;
  pending_shipments: number;
  inventory_value: number;
}

export interface StockMovement {
  id: string;
  type: 'in' | 'out';
  item: string;
  quantity: number;
  location: string;
  time: string;
}

export interface LowStockItem {
  id: string;
  name: string;
  current: number;
  reorder: number;
  unit: string;
}

export interface Warehouse {
  id: string;
  name: string;
  code: string;
  address?: string;
  location_count: number;
}

export interface InventoryLevel {
  id: string;
  product_id: number;
  product_name: string;
  location_id: string;
  location_name: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
}

interface WarehouseState {
  stats: WarehouseStats | null;
  movements: StockMovement[];
  lowStockItems: LowStockItem[];
  warehouses: Warehouse[];
  inventoryLevels: InventoryLevel[];
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  
  fetchStats: () => Promise<void>;
  fetchMovements: (limit?: number) => Promise<void>;
  fetchLowStock: (limit?: number) => Promise<void>;
  fetchWarehouses: () => Promise<void>;
  fetchInventoryLevels: (params?: { location_id?: string; product_id?: number }) => Promise<void>;
  syncInventory: () => Promise<void>;
  clearError: () => void;
}

export const useWarehouseStore = create<WarehouseState>()(
  devtools(
    persist(
      (set, get) => ({
        stats: null,
        movements: [],
        lowStockItems: [],
        warehouses: [],
        inventoryLevels: [],
        isLoading: false,
        error: null,
        lastFetchedAt: null,

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
            const data = await apiClient.get<WarehouseStats>('/warehouse/stats');
            set({ stats: data, isLoading: false, lastFetchedAt: now });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchMovements: async (limit = 10) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<StockMovement[]>(`/warehouse/movements?limit=${limit}`);
            set({ movements: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchLowStock: async (limit = 10) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<LowStockItem[]>(`/warehouse/low-stock?limit=${limit}`);
            set({ lowStockItems: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchWarehouses: async () => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.get<{ items: Warehouse[] }>('/warehouse/warehouses');
            set({ warehouses: response.items || [], isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchInventoryLevels: async (params) => {
          set({ isLoading: true, error: null });
          try {
            let url = '/warehouse/levels';
            const queryParams = new URLSearchParams();
            if (params?.location_id) queryParams.append('location_id', params.location_id);
            if (params?.product_id) queryParams.append('product_id', params.product_id.toString());
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: InventoryLevel[] }>(url);
            set({ inventoryLevels: response.items || [], isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        syncInventory: async () => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post('/warehouse/sync', {});
            // Refresh stats after sync
            await get().fetchStats();
            set({ isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        clearError: () => set({ error: null }),
      }),
      { name: 'warehouse-storage' }
    ),
    { name: 'WarehouseStore' }
  )
);

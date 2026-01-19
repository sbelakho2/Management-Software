import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

export interface SystemHealth {
  api_health: string;
  db_health: string;
  cache_health: string;
  queue_health: string;
  uptime: string;
  last_incident: string;
}

export interface ServerStats {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_connections: number;
}

export interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  latency: string;
}

export interface ITAlert {
  id: string;
  type: 'info' | 'warning' | 'error';
  message: string;
  time: string;
  resolved: boolean;
}

export interface ActiveUsersGroup {
  name: string;
  count: number;
  trend: 'up' | 'down' | 'stable';
}

interface ITState {
  systemHealth: SystemHealth | null;
  serverStats: ServerStats | null;
  services: ServiceStatus[];
  alerts: ITAlert[];
  activeUsers: ActiveUsersGroup[];
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  
  fetchSystemHealth: () => Promise<void>;
  fetchServerStats: () => Promise<void>;
  fetchServices: () => Promise<void>;
  fetchAlerts: (includeResolved?: boolean) => Promise<void>;
  fetchActiveUsers: () => Promise<void>;
  fetchAll: () => Promise<void>;
  clearCache: () => Promise<void>;
  restartService: (serviceName: string) => Promise<void>;
  clearError: () => void;
}

export const useITStore = create<ITState>()(
  devtools(
    persist(
      (set, get) => ({
        systemHealth: null,
        serverStats: null,
        services: [],
        alerts: [],
        activeUsers: [],
        isLoading: false,
        error: null,
        lastFetchedAt: null,

        fetchSystemHealth: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<SystemHealth>('/it/health');
            set({ systemHealth: data, isLoading: false, lastFetchedAt: Date.now() });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchServerStats: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ServerStats>('/it/server-stats');
            set({ serverStats: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchServices: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ServiceStatus[]>('/it/services');
            set({ services: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchAlerts: async (includeResolved = true) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ITAlert[]>(`/it/alerts?include_resolved=${includeResolved}`);
            set({ alerts: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchActiveUsers: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ActiveUsersGroup[]>('/it/active-users');
            set({ activeUsers: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchAll: async () => {
          const { lastFetchedAt, isLoading } = get();
          const now = Date.now();
          
          // Cache for 15 seconds for IT monitoring (more frequent updates needed)
          if (lastFetchedAt && now - lastFetchedAt < 15000) {
            return;
          }
          
          if (isLoading) return;
          
          set({ isLoading: true, error: null });
          try {
            await Promise.all([
              get().fetchSystemHealth(),
              get().fetchServerStats(),
              get().fetchServices(),
              get().fetchAlerts(),
              get().fetchActiveUsers(),
            ]);
            set({ isLoading: false, lastFetchedAt: now });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        clearCache: async () => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post('/it/clear-cache', {});
            set({ isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        restartService: async (serviceName: string) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/it/restart-service/${serviceName}`, {});
            // Refresh services status after restart
            await get().fetchServices();
            set({ isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        clearError: () => set({ error: null }),
      }),
      { name: 'it-monitoring-storage' }
    ),
    { name: 'ITStore' }
  )
);

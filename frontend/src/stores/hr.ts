import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

export interface HRStats {
  total_employees: number;
  open_positions: number;
  pending_time_off: number;
  expiring_certifications: number;
  new_hires_this_month: number;
  turnover_rate: number;
}

export interface DepartmentHeadcount {
  name: string;
  count: number;
  percentage: number;
}

export interface ExpiringCert {
  id: string;
  employee: string;
  cert: string;
  expires: string;
  priority: string;
}

interface HRState {
  stats: HRStats | null;
  headcount: DepartmentHeadcount[];
  expiringCerts: ExpiringCert[];
  isLoading: boolean;
  error: string | null;
  
  fetchStats: () => Promise<void>;
  fetchHeadcount: () => Promise<void>;
  fetchExpiringCerts: () => Promise<void>;
}

export const useHRStore = create<HRState>()(
  devtools(
    persist(
      (set) => ({
        stats: null,
        headcount: [],
        expiringCerts: [],
        isLoading: false,
        error: null,

        fetchStats: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<HRStats>('/hr/stats');
            set({ stats: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchHeadcount: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<DepartmentHeadcount[]>('/hr/headcount');
            set({ headcount: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchExpiringCerts: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ExpiringCert[]>('/hr/expiring-certs');
            set({ expiringCerts: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },
      }),
      { name: 'hr-storage' }
    )
  )
);

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

type CTQCategory = 'dimensional' | 'surface' | 'material' | 'mechanical' | 'electrical' | 'visual' | 'functional' | 'environmental' | 'other';
type CTQPriority = 'critical' | 'major' | 'minor';
type CTQStatus = 'draft' | 'active' | 'under_review' | 'approved' | 'obsolete';
type MeasurementResult = 'pass' | 'fail' | 'marginal' | 'not_measured';

interface CTQMeasurement {
  id: string;
  ctq_id: string;
  measured_value: number | null;
  measured_at: string;
  measured_by_id: string;
  measured_by_name: string;
  result: MeasurementResult;
  notes: string;
  attachment_ids: string[];
  created_at: string;
}

interface CTQ {
  id: string;
  ctq_number: string;
  category: CTQCategory;
  priority: CTQPriority;
  status: CTQStatus;
  rfq_id?: string;
  rfq_number?: string;
  part_number?: string;
  characteristic: string;
  description: string;
  specification: string;
  nominal_value: number | null;
  upper_tolerance: number | null;
  lower_tolerance: number | null;
  unit_of_measure: string;
  measurement_method: string;
  sampling_plan: string;
  check_stage: string;
  evidence_required: boolean;
  measurements: CTQMeasurement[];
  measurement_count: number;
  pass_rate: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  created_by_name: string;
}

interface CTQStats {
  total: number;
  active: number;
  approved: number;
  critical: number;
  average_pass_rate: number;
  measured_today: number;
}

interface CTQState {
  ctqs: CTQ[];
  stats: CTQStats;
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchCTQs: () => Promise<void>;
  fetchCTQById: (id: string) => Promise<CTQ | null>;
  createCTQ: (ctq: Partial<CTQ>) => Promise<CTQ>;
  updateCTQ: (id: string, updates: Partial<CTQ>) => Promise<CTQ>;
  deleteCTQ: (id: string) => Promise<void>;
  addMeasurement: (ctqId: string, measurement: Partial<CTQMeasurement>) => Promise<CTQMeasurement>;
  exportCTQs: (format: 'pdf' | 'excel') => Promise<void>;
  clearError: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useCTQStore = create<CTQState>()(
  devtools(
    persist(
      (set, get) => ({
        ctqs: [],
        stats: {
          total: 0,
          active: 0,
          approved: 0,
          critical: 0,
          average_pass_rate: 0,
          measured_today: 0,
        },
        isLoading: false,
        error: null,
        lastFetchedAt: null,

        fetchCTQs: async () => {
          const { lastFetchedAt } = get();
          const now = Date.now();

          // Cache for 30 seconds
          if (lastFetchedAt && now - lastFetchedAt < 30000) {
            return;
          }

          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/ctqs');
            const ctqs: CTQ[] = data.items || [];

            // Calculate stats
            const total = ctqs.length;
            const active = ctqs.filter(c => c.status === 'active').length;
            const approved = ctqs.filter(c => c.status === 'approved').length;
            const critical = ctqs.filter(c => c.priority === 'critical').length;
            const average_pass_rate = total > 0 
              ? ctqs.reduce((sum, c) => sum + c.pass_rate, 0) / total 
              : 0;
            
            // Count measurements today
            const today = new Date().toISOString().split('T')[0];
            const measured_today = ctqs.reduce((count, ctq) => {
              return count + ctq.measurements.filter(m => 
                m.measured_at.startsWith(today)
              ).length;
            }, 0);

            set({
              ctqs,
              stats: {
                total,
                active,
                approved,
                critical,
                average_pass_rate,
                measured_today,
              },
              lastFetchedAt: now,
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch CTQs',
              isLoading: false,
            });
          }
        },

        fetchCTQById: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const ctq = await apiClient.get<CTQ>(`/ctqs/${id}`);
            
            // Update store
            set(state => ({
              ctqs: state.ctqs.map(c => c.id === id ? ctq : c),
              isLoading: false,
            }));

            return ctq;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch CTQ',
              isLoading: false,
            });
            return null;
          }
        },

        createCTQ: async (ctqData: Partial<CTQ>) => {
          set({ isLoading: true, error: null });
          try {
            const ctq = await apiClient.post<CTQ>('/ctqs', ctqData);

            set(state => ({
              ctqs: [ctq, ...state.ctqs],
              stats: {
                ...state.stats,
                total: state.stats.total + 1,
                active: ctq.status === 'active' ? state.stats.active + 1 : state.stats.active,
                approved: ctq.status === 'approved' ? state.stats.approved + 1 : state.stats.approved,
                critical: ctq.priority === 'critical' ? state.stats.critical + 1 : state.stats.critical,
              },
              isLoading: false,
            }));

            return ctq;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create CTQ',
              isLoading: false,
            });
            throw error;
          }
        },

        updateCTQ: async (id: string, updates: Partial<CTQ>) => {
          set({ isLoading: true, error: null });
          try {
            const ctq = await apiClient.patch<CTQ>(`/ctqs/${id}`, updates, {
              headers: {
                'If-Match': get().ctqs.find(c => c.id === id)?.updated_at || '',
              },
            });

            set(state => ({
              ctqs: state.ctqs.map(c => c.id === id ? ctq : c),
              isLoading: false,
            }));

            return ctq;
          } catch (error: any) {
            if (error.code === '409' || error.message?.includes('409')) {
               set({ error: 'CTQ was modified by another user. Please refresh and try again.' });
            } else {
               set({ error: error.message || 'Failed to update CTQ' });
            }
            throw error;
          }
        },

        deleteCTQ: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.delete(`/ctqs/${id}`);

            const deletedCTQ = get().ctqs.find(c => c.id === id);

            set(state => ({
              ctqs: state.ctqs.filter(c => c.id !== id),
              stats: {
                ...state.stats,
                total: Math.max(0, state.stats.total - 1),
                active: deletedCTQ?.status === 'active' ? Math.max(0, state.stats.active - 1) : state.stats.active,
                approved: deletedCTQ?.status === 'approved' ? Math.max(0, state.stats.approved - 1) : state.stats.approved,
                critical: deletedCTQ?.priority === 'critical' ? Math.max(0, state.stats.critical - 1) : state.stats.critical,
              },
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete CTQ',
              isLoading: false,
            });
            throw error;
          }
        },

        addMeasurement: async (ctqId: string, measurementData: Partial<CTQMeasurement>) => {
          set({ isLoading: true, error: null });
          try {
            const measurement = await apiClient.post<CTQMeasurement>(`/ctqs/${ctqId}/measurements`, measurementData);

            // Fetch updated CTQ to get recalculated stats
            await get().fetchCTQById(ctqId);

            set({ isLoading: false });
            return measurement;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to add measurement',
              isLoading: false,
            });
            throw error;
          }
        },

        exportCTQs: async (format: 'pdf' | 'excel') => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/ctqs/export?format=${format}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to export CTQs: ${response.statusText}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ctqs_${new Date().toISOString().split('T')[0]}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            set({ isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to export CTQs',
              isLoading: false,
            });
            throw error;
          }
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'ctq-storage',
        partialize: (state) => ({
          ctqs: state.ctqs,
          stats: state.stats,
          lastFetchedAt: state.lastFetchedAt,
        }),
      }
    )
  )
);

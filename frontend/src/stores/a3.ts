import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

type A3Type = 'problem_solving' | 'proposal' | 'status_report' | 'strategy';
type A3Status = 'draft' | 'in_progress' | 'review' | 'approved' | 'implemented' | 'closed' | 'cancelled';
type A3Priority = 'critical' | 'high' | 'medium' | 'low';
type A3SectionType = 
  | 'background' | 'current_condition' | 'goal' | 'root_cause' 
  | 'countermeasures' | 'implementation_plan' | 'follow_up'
  | 'problem_statement' | 'analysis' | 'proposed_solution'
  | 'cost_benefit' | 'timeline' | 'risks' | 'custom';

interface A3Section {
  id: string;
  a3_id: string;
  section_type: A3SectionType;
  section_name: string;
  section_order: number;
  content?: string;
  structured_content?: any;
  is_complete: boolean;
  completed_at?: string;
  completed_by_id?: string;
  completed_by_name?: string;
  guidance?: string;
  attachments?: any[];
  comments?: any[];
  version: number;
  created_at: string;
  updated_at: string;
}

interface A3 {
  id: string;
  a3_number: string;
  title: string;
  a3_type: A3Type;
  status: A3Status;
  related_entity_type?: string;
  related_entity_id?: string;
  author_id: string;
  author_name: string;
  sponsor_id?: string;
  sponsor_name?: string;
  coach_id?: string;
  coach_name?: string;
  team_members?: string[];
  started_date?: string;
  target_completion_date?: string;
  actual_completion_date?: string;
  last_review_date?: string;
  review_notes?: string;
  approved_by_id?: string;
  approved_by_name?: string;
  approved_date?: string;
  progress_percentage: number;
  version: number;
  pdf_storage_key?: string;
  tags?: string[];
  department?: string;
  area?: string;
  priority: A3Priority;
  summary?: string;
  lessons_learned?: string;
  is_yokoten_candidate: boolean;
  yokoten_areas?: string[];
  custom_fields?: Record<string, any>;
  sections: A3Section[];
  created_at: string;
  updated_at: string;
  created_by_id: string;
  created_by_name: string;
}

interface A3Stats {
  total: number;
  by_status: Record<A3Status, number>;
  by_type: Record<A3Type, number>;
  by_priority: Record<A3Priority, number>;
  overdue_count: number;
  avg_completion_days: number;
  approval_pending: number;
}

interface A3State {
  a3s: A3[];
  stats: A3Stats;
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchA3s: () => Promise<void>;
  fetchA3ById: (id: string) => Promise<A3 | null>;
  createA3: (a3: Partial<A3>) => Promise<A3>;
  updateA3: (id: string, updates: Partial<A3>) => Promise<A3>;
  deleteA3: (id: string) => Promise<void>;
  updateSection: (a3Id: string, sectionId: string, updates: Partial<A3Section>) => Promise<A3Section>;
  completeSection: (a3Id: string, sectionId: string) => Promise<void>;
  submitForReview: (id: string) => Promise<void>;
  approve: (id: string, notes?: string) => Promise<void>;
  reject: (id: string, notes: string) => Promise<void>;
  exportPDF: (id: string) => Promise<void>;
  clearError: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const initialStats: A3Stats = {
  total: 0,
  by_status: {
    draft: 0,
    in_progress: 0,
    review: 0,
    approved: 0,
    implemented: 0,
    closed: 0,
    cancelled: 0,
  },
  by_type: {
    problem_solving: 0,
    proposal: 0,
    status_report: 0,
    strategy: 0,
  },
  by_priority: {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  },
  overdue_count: 0,
  avg_completion_days: 0,
  approval_pending: 0,
};

export const useA3Store = create<A3State>()(
  devtools(
    persist(
      (set, get) => ({
        a3s: [],
        stats: initialStats,
        isLoading: false,
        error: null,
        lastFetchedAt: null,

        fetchA3s: async () => {
          const { lastFetchedAt, isLoading } = get();
          const now = Date.now();

          if (isLoading) {
            return;
          }

          // Cache for 30 seconds
          if (lastFetchedAt && now - lastFetchedAt < 30000) {
            return;
          }

          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/a3s');
            const a3s: A3[] = data.items || [];

            // Calculate stats
            const stats: A3Stats = {
              total: a3s.length,
              by_status: a3s.reduce((acc, a3) => {
                acc[a3.status] = (acc[a3.status] || 0) + 1;
                return acc;
              }, {} as Record<A3Status, number>),
              by_type: a3s.reduce((acc, a3) => {
                acc[a3.a3_type] = (acc[a3.a3_type] || 0) + 1;
                return acc;
              }, {} as Record<A3Type, number>),
              by_priority: a3s.reduce((acc, a3) => {
                acc[a3.priority] = (acc[a3.priority] || 0) + 1;
                return acc;
              }, {} as Record<A3Priority, number>),
              overdue_count: a3s.filter(a3 => {
                if (!a3.target_completion_date) return false;
                if (['closed', 'cancelled'].includes(a3.status)) return false;
                return new Date(a3.target_completion_date) < new Date();
              }).length,
              avg_completion_days: 0, // Calculated on backend
              approval_pending: a3s.filter(a3 => a3.status === 'review').length,
            };

            set({
              a3s,
              stats,
              lastFetchedAt: now,
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch A3s',
              isLoading: false,
            });
          }
        },

        fetchA3ById: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const a3 = await apiClient.get<A3>(`/a3s/${id}`);

            set(state => ({
              a3s: state.a3s.map(a => a.id === id ? a3 : a),
              isLoading: false,
            }));

            return a3;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch A3',
              isLoading: false,
            });
            return null;
          }
        },

        createA3: async (a3Data: Partial<A3>) => {
          set({ isLoading: true, error: null });
          try {
            const a3 = await apiClient.post<A3>('/a3s', a3Data);

            set(state => ({
              a3s: [a3, ...state.a3s],
              stats: {
                ...state.stats,
                total: state.stats.total + 1,
              },
              isLoading: false,
            }));

            return a3;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create A3',
              isLoading: false,
            });
            throw error;
          }
        },

        updateA3: async (id: string, updates: Partial<A3>) => {
          set({ isLoading: true, error: null });
          try {
            const a3 = await apiClient.patch<A3>(`/a3s/${id}`, updates);

            set(state => ({
              a3s: state.a3s.map(a => a.id === id ? a3 : a),
              isLoading: false,
            }));

            return a3;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update A3',
              isLoading: false,
            });
            throw error;
          }
        },

        deleteA3: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.delete(`/a3s/${id}`);

            set(state => ({
              a3s: state.a3s.filter(a => a.id !== id),
              stats: {
                ...state.stats,
                total: Math.max(0, state.stats.total - 1),
              },
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete A3',
              isLoading: false,
            });
            throw error;
          }
        },

        updateSection: async (a3Id: string, sectionId: string, updates: Partial<A3Section>) => {
          set({ isLoading: true, error: null });
          try {
            const section = await apiClient.patch<A3Section>(`/a3s/${a3Id}/sections/${sectionId}`, updates);

            // Refresh A3 to get updated progress
            await get().fetchA3ById(a3Id);

            set({ isLoading: false });
            return section;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update section',
              isLoading: false,
            });
            throw error;
          }
        },

        completeSection: async (a3Id: string, sectionId: string) => {
          await get().updateSection(a3Id, sectionId, { is_complete: true });
        },

        submitForReview: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const a3 = await apiClient.post<A3>(`/a3s/${id}/submit`);

            set(state => ({
              a3s: state.a3s.map(a => a.id === id ? a3 : a),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to submit A3',
              isLoading: false,
            });
            throw error;
          }
        },

        approve: async (id: string, notes?: string) => {
          set({ isLoading: true, error: null });
          try {
            const a3 = await apiClient.post<A3>(`/a3s/${id}/approve`, { notes });

            set(state => ({
              a3s: state.a3s.map(a => a.id === id ? a3 : a),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to approve A3',
              isLoading: false,
            });
            throw error;
          }
        },

        reject: async (id: string, notes: string) => {
          set({ isLoading: true, error: null });
          try {
            const a3 = await apiClient.post<A3>(`/a3s/${id}/reject`, { notes });

            set(state => ({
              a3s: state.a3s.map(a => a.id === id ? a3 : a),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to reject A3',
              isLoading: false,
            });
            throw error;
          }
        },

        exportPDF: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/a3s/${id}/export`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to export A3: ${response.statusText}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `a3_${id}_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            set({ isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to export A3',
              isLoading: false,
            });
            throw error;
          }
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'a3-storage',
        partialize: (state) => ({
          a3s: state.a3s,
          stats: state.stats,
          lastFetchedAt: state.lastFetchedAt,
        }),
      }
    )
  )
);

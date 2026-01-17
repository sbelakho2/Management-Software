import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

// Types
export type ExceptionSeverity = 'critical' | 'high' | 'medium' | 'low';
export type ExceptionCategory = 'andon' | 'quote' | 'production' | 'quality' | 'a3' | 'obeya' | 'task' | 'training';
export type ExceptionStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'escalated';

export interface Exception {
  id: string;
  title: string;
  category: ExceptionCategory;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
  created_at: string;
  due_date: string;
  owner: string;
  owner_id: string;
  department: string;
  description: string;
  resolution_time?: number; // minutes
  resolved_at?: string;
  escalated_at?: string;
  escalated_to?: string;
  blocked_reason?: string;
  related_entity_id?: string;
  related_entity_type?: string;
  tags: string[];
  comments_count: number;
  attachments_count: number;
}

export interface ExceptionTrend {
  period: string;
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  resolved: number;
  created: number;
}

export interface ExceptionStats {
  total_open: number;
  critical_count: number;
  overdue_count: number;
  escalated_count: number;
  blocked_count: number;
  avg_resolution_time_minutes: number;
  resolved_today: number;
  created_today: number;
  by_category: Record<ExceptionCategory, number>;
  by_severity: Record<ExceptionSeverity, number>;
  by_status: Record<ExceptionStatus, number>;
}

interface ExceptionsState {
  // Data
  exceptions: Exception[];
  trends: ExceptionTrend[];
  stats: ExceptionStats | null;
  
  // Loading & Error States
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  
  // Actions
  fetchExceptions: (filters?: {
    category?: ExceptionCategory;
    severity?: ExceptionSeverity;
    status?: ExceptionStatus;
  }) => Promise<void>;
  fetchExceptionById: (id: string) => Promise<Exception>;
  acknowledgeException: (id: string) => Promise<void>;
  escalateException: (id: string, escalateTo: string, reason: string) => Promise<void>;
  resolveException: (id: string, resolutionNotes: string) => Promise<void>;
  assignException: (id: string, ownerId: string) => Promise<void>;
  addComment: (id: string, comment: string) => Promise<void>;
  
  // Trends & Stats
  fetchTrends: (days?: number) => Promise<void>;
  fetchStats: () => Promise<void>;
  
  // Utility
  clearError: () => void;
}

const CACHE_DURATION = 30000; // 30 seconds
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useExceptionsStore = create<ExceptionsState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        exceptions: [],
        trends: [],
        stats: null,
        isLoading: false,
        error: null,
        lastFetchedAt: null,
        
        // Actions
        fetchExceptions: async (filters = {}) => {
          const now = Date.now();
          const { lastFetchedAt, isLoading } = get();

          if (isLoading) {
            return;
          }
          
          // Use cache if fresh and no filters
          if (!Object.keys(filters).length && lastFetchedAt && now - lastFetchedAt < CACHE_DURATION) {
            return;
          }
          
          set({ isLoading: true, error: null });
          
          try {
            const params = new URLSearchParams(filters as any);
            const data = await apiClient.get<any>(`/exceptions?${params}`);

            const items = Array.isArray(data?.items)
              ? data.items
              : Array.isArray(data)
                ? data
                : [];
            
            set({
              exceptions: items,
              isLoading: false,
              lastFetchedAt: now,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch exceptions',
              isLoading: false,
            });
          }
        },
        
        fetchExceptionById: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            const exception = await apiClient.get<Exception>(`/exceptions/${id}`);
            set({ isLoading: false });
            return exception;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch exception',
              isLoading: false,
            });
            throw error;
          }
        },
        
        acknowledgeException: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.post(`/exceptions/${id}/acknowledge`);
            
            set((state) => ({
              exceptions: state.exceptions.map(exc =>
                exc.id === id ? { ...exc, status: 'acknowledged' as ExceptionStatus } : exc
              ),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to acknowledge exception',
              isLoading: false,
            });
            throw error;
          }
        },
        
        escalateException: async (id: string, escalateTo: string, reason: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.post(`/exceptions/${id}/escalate`, { escalate_to: escalateTo, reason });
            
            set((state) => ({
              exceptions: state.exceptions.map(exc =>
                exc.id === id
                  ? {
                      ...exc,
                      status: 'escalated' as ExceptionStatus,
                      escalated_at: new Date().toISOString(),
                      escalated_to: escalateTo,
                    }
                  : exc
              ),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to escalate exception',
              isLoading: false,
            });
            throw error;
          }
        },
        
        resolveException: async (id: string, resolutionNotes: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.post(`/exceptions/${id}/resolve`, { resolution_notes: resolutionNotes });
            
            const resolvedAt = new Date().toISOString();
            const exception = get().exceptions.find(e => e.id === id);
            const resolutionTime = exception
              ? Math.floor((new Date(resolvedAt).getTime() - new Date(exception.created_at).getTime()) / 60000)
              : 0;
            
            set((state) => ({
              exceptions: state.exceptions.map(exc =>
                exc.id === id
                  ? {
                      ...exc,
                      status: 'resolved' as ExceptionStatus,
                      resolved_at: resolvedAt,
                      resolution_time: resolutionTime,
                    }
                  : exc
              ),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to resolve exception',
              isLoading: false,
            });
            throw error;
          }
        },
        
        assignException: async (id: string, ownerId: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.post(`/exceptions/${id}/assign`, { owner_id: ownerId });
            
            set((state) => ({
              exceptions: state.exceptions.map(exc =>
                exc.id === id ? { ...exc, owner_id: ownerId } : exc
              ),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to assign exception',
              isLoading: false,
            });
            throw error;
          }
        },
        
        addComment: async (id: string, comment: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.post(`/exceptions/${id}/comments`, { comment });
            
            set((state) => ({
              exceptions: state.exceptions.map(exc =>
                exc.id === id
                  ? { ...exc, comments_count: exc.comments_count + 1 }
                  : exc
              ),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to add comment',
              isLoading: false,
            });
            throw error;
          }
        },
        
        fetchTrends: async (days = 7) => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>(`/exceptions/trends?days=${days}`);

            const trends = Array.isArray(data?.items)
              ? data.items
              : Array.isArray(data)
                ? data
                : [];

            set({ trends, isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch trends',
              isLoading: false,
            });
          }
        },
        
        fetchStats: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/exceptions/summary');
            set({ stats: data ?? null, isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch stats',
              isLoading: false,
            });
          }
        },
        
        // Utility
        clearError: () => set({ error: null }),
      }),
      {
        name: 'exceptions-storage',
        partialize: (state) => ({
          exceptions: state.exceptions,
          trends: state.trends,
        }),
      }
    )
  )
);

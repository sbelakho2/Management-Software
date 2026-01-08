import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

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
          const { lastFetchedAt } = get();
          
          // Use cache if fresh and no filters
          if (!Object.keys(filters).length && lastFetchedAt && now - lastFetchedAt < CACHE_DURATION) {
            return;
          }
          
          set({ isLoading: true, error: null });
          
          try {
            // TODO: Replace with actual API call
            // const params = new URLSearchParams(filters as any);
            // const response = await fetch(`/api/v1/exceptions?${params}`, {
            //   headers: { Authorization: `Bearer ${token}` }
            // });
            // const data = await response.json();
            
            // Mock data for now
            await new Promise(resolve => setTimeout(resolve, 500));
            
            set({
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
            // TODO: Replace with actual API call
            // const response = await fetch(`/api/v1/exceptions/${id}`, {
            //   headers: { Authorization: `Bearer ${token}` }
            // });
            // const exception = await response.json();
            
            const exception = get().exceptions.find(e => e.id === id);
            if (!exception) throw new Error('Exception not found');
            
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
            // TODO: Replace with actual API call
            // await fetch(`/api/v1/exceptions/${id}/acknowledge`, {
            //   method: 'POST',
            //   headers: {
            //     'Content-Type': 'application/json',
            //     Authorization: `Bearer ${token}`
            //   }
            // });
            
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
            // TODO: Replace with actual API call
            // await fetch(`/api/v1/exceptions/${id}/escalate`, {
            //   method: 'POST',
            //   headers: {
            //     'Content-Type': 'application/json',
            //     Authorization: `Bearer ${token}`
            //   },
            //   body: JSON.stringify({ escalate_to: escalateTo, reason })
            // });
            
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
            // TODO: Replace with actual API call
            // await fetch(`/api/v1/exceptions/${id}/resolve`, {
            //   method: 'POST',
            //   headers: {
            //     'Content-Type': 'application/json',
            //     Authorization: `Bearer ${token}`
            //   },
            //   body: JSON.stringify({ resolution_notes: resolutionNotes })
            // });
            
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
            // TODO: Replace with actual API call
            // await fetch(`/api/v1/exceptions/${id}/assign`, {
            //   method: 'POST',
            //   headers: {
            //     'Content-Type': 'application/json',
            //     Authorization: `Bearer ${token}`
            //   },
            //   body: JSON.stringify({ owner_id: ownerId })
            // });
            
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
            // TODO: Replace with actual API call
            // await fetch(`/api/v1/exceptions/${id}/comments`, {
            //   method: 'POST',
            //   headers: {
            //     'Content-Type': 'application/json',
            //     Authorization: `Bearer ${token}`
            //   },
            //   body: JSON.stringify({ comment })
            // });
            
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
            // TODO: Replace with actual API call
            // const response = await fetch(`/api/v1/exceptions/trends?days=${days}`, {
            //   headers: { Authorization: `Bearer ${token}` }
            // });
            // const trends = await response.json();
            
            // Mock data
            await new Promise(resolve => setTimeout(resolve, 500));
            
            set({ isLoading: false });
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
            // TODO: Replace with actual API call
            // const response = await fetch('/api/v1/exceptions/stats', {
            //   headers: { Authorization: `Bearer ${token}` }
            // });
            // const stats = await response.json();
            
            // Calculate stats from current exceptions
            const exceptions = get().exceptions;
            const now = new Date();
            const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            
            const stats: ExceptionStats = {
              total_open: exceptions.filter(e => e.status !== 'resolved').length,
              critical_count: exceptions.filter(e => e.severity === 'critical' && e.status !== 'resolved').length,
              overdue_count: exceptions.filter(e => new Date(e.due_date) < now && e.status !== 'resolved').length,
              escalated_count: exceptions.filter(e => e.status === 'escalated').length,
              blocked_count: exceptions.filter(e => e.blocked_reason !== undefined).length,
              avg_resolution_time_minutes: Math.floor(
                exceptions
                  .filter(e => e.resolution_time)
                  .reduce((sum, e) => sum + (e.resolution_time || 0), 0) /
                  Math.max(exceptions.filter(e => e.resolution_time).length, 1)
              ),
              resolved_today: exceptions.filter(
                e => e.resolved_at && new Date(e.resolved_at) >= todayStart
              ).length,
              created_today: exceptions.filter(
                e => new Date(e.created_at) >= todayStart
              ).length,
              by_category: {
                andon: exceptions.filter(e => e.category === 'andon' && e.status !== 'resolved').length,
                quote: exceptions.filter(e => e.category === 'quote' && e.status !== 'resolved').length,
                production: exceptions.filter(e => e.category === 'production' && e.status !== 'resolved').length,
                quality: exceptions.filter(e => e.category === 'quality' && e.status !== 'resolved').length,
                a3: exceptions.filter(e => e.category === 'a3' && e.status !== 'resolved').length,
                obeya: exceptions.filter(e => e.category === 'obeya' && e.status !== 'resolved').length,
                task: exceptions.filter(e => e.category === 'task' && e.status !== 'resolved').length,
                training: exceptions.filter(e => e.category === 'training' && e.status !== 'resolved').length,
              },
              by_severity: {
                critical: exceptions.filter(e => e.severity === 'critical' && e.status !== 'resolved').length,
                high: exceptions.filter(e => e.severity === 'high' && e.status !== 'resolved').length,
                medium: exceptions.filter(e => e.severity === 'medium' && e.status !== 'resolved').length,
                low: exceptions.filter(e => e.severity === 'low' && e.status !== 'resolved').length,
              },
              by_status: {
                open: exceptions.filter(e => e.status === 'open').length,
                acknowledged: exceptions.filter(e => e.status === 'acknowledged').length,
                in_progress: exceptions.filter(e => e.status === 'in_progress').length,
                escalated: exceptions.filter(e => e.status === 'escalated').length,
                resolved: exceptions.filter(e => e.status === 'resolved').length,
              },
            };
            
            set({ stats, isLoading: false });
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

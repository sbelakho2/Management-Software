import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';
import type { RFQStatus, Priority } from '@/types';

interface RFQItem {
  id: string;
  rfqNumber: string;
  customerName: string;
  customerId: string;
  title: string;
  description?: string;
  dueDate: string;
  receivedDate: string;
  estimatedValue?: number;
  priority: Priority;
  status: RFQStatus;
  account?: {
    name: string;
    id?: string;
  };
  assignee?: {
    id: string;
    name: string;
    avatar?: string;
  };
  tags: string[];
  version: number;
  attachmentCount: number;
  commentCount: number;
  lastActivityAt: string;
}

interface PipelineStats {
  totalRFQs: number;
  activeRFQs: number;
  totalValue: number;
  avgResponseTime: number;
  conversionRate: number;
  overdueCount: number;
}

interface PipelineState {
  // State
  rfqs: RFQItem[];
  stats: PipelineStats;
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  // Actions
  fetchRFQs: () => Promise<void>;
  fetchRFQById: (id: string) => Promise<RFQItem | null>;
  createRFQ: (rfq: Partial<RFQItem>) => Promise<RFQItem>;
  updateRFQ: (id: string, updates: Partial<RFQItem>) => Promise<RFQItem>;
  deleteRFQ: (id: string) => Promise<void>;
  bulkDeleteRFQs: (ids: string[]) => Promise<void>;
  exportRFQs: (ids?: string[]) => Promise<void>;
  setRFQStatus: (id: string, status: RFQStatus) => Promise<void>;
  assignRFQ: (id: string, assigneeId: string) => Promise<void>;
  clearError: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const usePipelineStore = create<PipelineState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        rfqs: [],
        stats: {
          totalRFQs: 0,
          activeRFQs: 0,
          totalValue: 0,
          avgResponseTime: 0,
          conversionRate: 0,
          overdueCount: 0,
        },
        isLoading: false,
        error: null,
        lastFetchedAt: null,

        // Fetch all RFQs
        fetchRFQs: async () => {
          const { lastFetchedAt } = get();
          const now = Date.now();

          // Cache for 30 seconds
          if (lastFetchedAt && now - lastFetchedAt < 30000) {
            return;
          }

          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/rfqs');
            
            // Calculate stats
            const rfqs: RFQItem[] = data.items || [];
            const activeStatuses: RFQStatus[] = ['new', 'reviewing', 'quoting', 'submitted'];
            const activeRFQs = rfqs.filter(rfq => activeStatuses.includes(rfq.status));
            const totalValue = rfqs.reduce((sum, rfq) => sum + (rfq.estimatedValue || 0), 0);
            const overdueCount = rfqs.filter(rfq => new Date(rfq.dueDate) < new Date()).length;
            const wonRFQs = rfqs.filter(rfq => rfq.status === 'won').length;
            const totalSubmitted = rfqs.filter(rfq => rfq.status === 'submitted').length;
            
            // Calculate avg response time (mock for now)
            const avgResponseTime = rfqs.reduce((sum, rfq) => {
              const received = new Date(rfq.receivedDate).getTime();
              const lastActivity = new Date(rfq.lastActivityAt).getTime();
              return sum + (lastActivity - received);
            }, 0) / (rfqs.length || 1) / (1000 * 60 * 60); // Convert to hours

            set({
              rfqs,
              stats: {
                totalRFQs: rfqs.length,
                activeRFQs: activeRFQs.length,
                totalValue,
                avgResponseTime: Math.round(avgResponseTime),
                conversionRate: totalSubmitted > 0 ? Math.round((wonRFQs / totalSubmitted) * 100) : 0,
                overdueCount,
              },
              isLoading: false,
              lastFetchedAt: now,
            });
          } catch (error) {
            console.error('Error fetching RFQs:', error);
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch RFQs',
              isLoading: false,
            });
          }
        },

        // Fetch single RFQ
        fetchRFQById: async (id: string) => {
          try {
            const rfq = await apiClient.get<RFQItem>(`/rfqs/${id}`);

            // Update in store
            set(state => ({
              rfqs: state.rfqs.map(r => r.id === id ? rfq : r),
            }));

            return rfq;
          } catch (error) {
            console.error('Error fetching RFQ:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to fetch RFQ' });
            return null;
          }
        },

        // Create RFQ
        createRFQ: async (rfqData: Partial<RFQItem>) => {
          try {
            const newRFQ = await apiClient.post<RFQItem>('/rfqs', rfqData);

            // Add to store
            set(state => ({
              rfqs: [newRFQ, ...state.rfqs],
              stats: {
                ...state.stats,
                totalRFQs: state.stats.totalRFQs + 1,
                activeRFQs: state.stats.activeRFQs + 1,
              },
            }));

            return newRFQ;
          } catch (error) {
            console.error('Error creating RFQ:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to create RFQ' });
            throw error;
          }
        },

        // Update RFQ
        updateRFQ: async (id: string, updates: Partial<RFQItem>) => {
          const currentRFQ = get().rfqs.find(r => r.id === id);
          if (!currentRFQ) {
            throw new Error('RFQ not found');
          }

          try {
            const updatedRFQ = await apiClient.put<RFQItem>(`/rfqs/${id}`, updates, {
              headers: {
                'If-Match': `"${currentRFQ.version}"`, // Optimistic locking
              },
            });

            // Update in store
            set(state => ({
              rfqs: state.rfqs.map(r => r.id === id ? updatedRFQ : r),
            }));

            return updatedRFQ;
          } catch (error: any) {
            console.error('Error updating RFQ:', error);
            if (error.code === '409' || error.message?.includes('409')) {
               set({ error: 'RFQ was modified by another user. Please refresh and try again.' });
            } else {
               set({ error: error.message || 'Failed to update RFQ' });
            }
            throw error;
          }
        },

        // Delete RFQ
        deleteRFQ: async (id: string) => {
          try {
            await apiClient.delete(`/rfqs/${id}`);

            // Remove from store
            set(state => ({
              rfqs: state.rfqs.filter(r => r.id !== id),
              stats: {
                ...state.stats,
                totalRFQs: state.stats.totalRFQs - 1,
              },
            }));
          } catch (error) {
            console.error('Error deleting RFQ:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to delete RFQ' });
            throw error;
          }
        },

        // Bulk delete RFQs
        bulkDeleteRFQs: async (ids: string[]) => {
          try {
            await apiClient.post('/rfqs/bulk-delete', { ids });

            // Remove from store
            set(state => ({
              rfqs: state.rfqs.filter(r => !ids.includes(r.id)),
              stats: {
                ...state.stats,
                totalRFQs: state.stats.totalRFQs - ids.length,
              },
            }));
          } catch (error) {
            console.error('Error bulk deleting RFQs:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to bulk delete RFQs' });
            throw error;
          }
        },

        // Export RFQs
        exportRFQs: async (ids?: string[]) => {
          try {
            const queryParams = ids && ids.length > 0 ? `?ids=${ids.join(',')}` : '';
            const response = await fetch(`${API_BASE_URL}/rfqs/export${queryParams}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to export RFQs: ${response.statusText}`);
            }

            // Download the file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `rfqs_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
          } catch (error) {
            console.error('Error exporting RFQs:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to export RFQs' });
            throw error;
          }
        },

        // Set RFQ status
        setRFQStatus: async (id: string, status: RFQStatus) => {
          await get().updateRFQ(id, { status });
        },

        // Assign RFQ
        assignRFQ: async (id: string, assigneeId: string) => {
          // Fetch assignee details (mock for now)
          const assignee = {
            id: assigneeId,
            name: 'User Name', // Would fetch from API
          };
          await get().updateRFQ(id, { assignee });
        },

        // Clear error
        clearError: () => set({ error: null }),
      }),
      {
        name: 'pipeline-storage',
        partialize: (state) => ({
          // Only persist RFQs and lastFetchedAt
          rfqs: state.rfqs,
          lastFetchedAt: state.lastFetchedAt,
        }),
      }
    ),
    { name: 'PipelineStore' }
  )
);

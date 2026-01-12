import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

interface QuoteLineItem {
  id: string;
  partNumber: string;
  description: string;
  quantity: number;
  unitOfMeasure: string;
  unitPrice: number;
  cost?: number;
  leadTimeDays?: number;
  notes?: string;
  materialCost?: number;
  laborCost?: number;
  overheadCost?: number;
}

interface QuoteAssumption {
  id: string;
  category: 'technical' | 'commercial' | 'delivery' | 'quality';
  description: string;
  impact: 'high' | 'medium' | 'low';
  verified: boolean;
}

interface QuoteFormData {
  rfqId?: string;
  quoteNumber?: string;
  version: number;
  validUntil: string;
  discountType: 'percentage' | 'amount';
  discountValue: number;
  taxRate: number;
  termsAndConditions: string;
  notes: string;
  internalNotes: string;
  lineItems: QuoteLineItem[];
  assumptions: QuoteAssumption[];
}

interface Quote extends QuoteFormData {
  id: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'sent' | 'accepted' | 'declined';
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  approvedBy?: string;
  approvedAt?: string;
}

interface QuoteState {
  quotes: Quote[];
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchQuotes: () => Promise<void>;
  fetchQuoteById: (id: string) => Promise<Quote | null>;
  saveQuote: (data: QuoteFormData) => Promise<Quote>;
  submitQuote: (data: QuoteFormData) => Promise<Quote>;
  updateQuote: (id: string, updates: Partial<QuoteFormData>) => Promise<Quote>;
  deleteQuote: (id: string) => Promise<void>;
  approveQuote: (id: string, rationale: string) => Promise<void>;
  rejectQuote: (id: string, reason: string) => Promise<void>;
  clearError: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useQuoteStore = create<QuoteState>()(
  devtools(
    persist(
      (set, get) => ({
        quotes: [],
        isLoading: false,
        error: null,

        fetchQuotes: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/quotes');
            set({ quotes: data.items || [], isLoading: false });
          } catch (error) {
            console.error('Error fetching quotes:', error);
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch quotes',
              isLoading: false,
            });
          }
        },

        fetchQuoteById: async (id: string) => {
          try {
            const quote = await apiClient.get<Quote>(`/quotes/${id}`);

            // Update in store
            set(state => ({
              quotes: state.quotes.map(q => q.id === id ? quote : q),
            }));

            return quote;
          } catch (error) {
            console.error('Error fetching quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to fetch quote' });
            return null;
          }
        },

        saveQuote: async (data: QuoteFormData) => {
          set({ isLoading: true, error: null });
          try {
            const newQuote = await apiClient.post<Quote>('/quotes', { ...data, status: 'draft' });

            set(state => ({
              quotes: [newQuote, ...state.quotes],
              isLoading: false,
            }));

            return newQuote;
          } catch (error) {
            console.error('Error saving quote:', error);
            set({
              error: error instanceof Error ? error.message : 'Failed to save quote',
              isLoading: false,
            });
            throw error;
          }
        },

        submitQuote: async (data: QuoteFormData) => {
          set({ isLoading: true, error: null });
          try {
            const newQuote = await apiClient.post<Quote>('/quotes', { ...data, status: 'pending_approval' });

            set(state => ({
              quotes: [newQuote, ...state.quotes],
              isLoading: false,
            }));

            return newQuote;
          } catch (error) {
            console.error('Error submitting quote:', error);
            set({
              error: error instanceof Error ? error.message : 'Failed to submit quote',
              isLoading: false,
            });
            throw error;
          }
        },

        updateQuote: async (id: string, updates: Partial<QuoteFormData>) => {
          const currentQuote = get().quotes.find(q => q.id === id);
          if (!currentQuote) {
            throw new Error('Quote not found');
          }

          try {
            const updatedQuote = await apiClient.put<Quote>(`/quotes/${id}`, updates, {
              headers: {
                // @ts-ignore
                'If-Match': `"${currentQuote.version}"`, // Optimistic locking
              },
            });

            set(state => ({
              quotes: state.quotes.map(q => q.id === id ? updatedQuote : q),
            }));

            return updatedQuote;
          } catch (error: any) {
            console.error('Error updating quote:', error);
            if (error.code === '409' || error.message?.includes('409')) {
               set({ error: 'Quote was modified by another user. Please refresh and try again.' });
            } else {
               set({ error: error.message || 'Failed to update quote' });
            }
            throw error;
          }
        },

        deleteQuote: async (id: string) => {
          try {
            await apiClient.delete(`/quotes/${id}`);

            set(state => ({
              quotes: state.quotes.filter(q => q.id !== id),
            }));
          } catch (error) {
            console.error('Error deleting quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to delete quote' });
            throw error;
          }
        },

        approveQuote: async (id: string, rationale: string) => {
          try {
            const approvedQuote = await apiClient.post<Quote>(`/quotes/${id}/approve`, { rationale });

            set(state => ({
              quotes: state.quotes.map(q => q.id === id ? approvedQuote : q),
            }));
          } catch (error) {
            console.error('Error approving quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to approve quote' });
            throw error;
          }
        },

        rejectQuote: async (id: string, reason: string) => {
          try {
            const rejectedQuote = await apiClient.post<Quote>(`/quotes/${id}/reject`, { reason });

            set(state => ({
              quotes: state.quotes.map(q => q.id === id ? rejectedQuote : q),
            }));
          } catch (error) {
            console.error('Error rejecting quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to reject quote' });
            throw error;
          }
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'quote-storage',
        partialize: (state) => ({
          quotes: state.quotes,
        }),
      }
    ),
    { name: 'QuoteStore' }
  )
);

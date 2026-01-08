import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

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
            const response = await fetch(`${API_BASE_URL}/quotes`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch quotes: ${response.statusText}`);
            }

            const data = await response.json();
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
            const response = await fetch(`${API_BASE_URL}/quotes/${id}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch quote: ${response.statusText}`);
            }

            const quote: Quote = await response.json();

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
            const response = await fetch(`${API_BASE_URL}/quotes`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ ...data, status: 'draft' }),
            });

            if (!response.ok) {
              throw new Error(`Failed to save quote: ${response.statusText}`);
            }

            const newQuote: Quote = await response.json();

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
            const response = await fetch(`${API_BASE_URL}/quotes`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ ...data, status: 'pending_approval' }),
            });

            if (!response.ok) {
              throw new Error(`Failed to submit quote: ${response.statusText}`);
            }

            const newQuote: Quote = await response.json();

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
            const response = await fetch(`${API_BASE_URL}/quotes/${id}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                'If-Match': `"${currentQuote.version}"`, // Optimistic locking
              },
              body: JSON.stringify(updates),
            });

            if (!response.ok) {
              if (response.status === 409) {
                throw new Error('Quote was modified by another user. Please refresh and try again.');
              }
              throw new Error(`Failed to update quote: ${response.statusText}`);
            }

            const updatedQuote: Quote = await response.json();

            set(state => ({
              quotes: state.quotes.map(q => q.id === id ? updatedQuote : q),
            }));

            return updatedQuote;
          } catch (error) {
            console.error('Error updating quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to update quote' });
            throw error;
          }
        },

        deleteQuote: async (id: string) => {
          try {
            const response = await fetch(`${API_BASE_URL}/quotes/${id}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to delete quote: ${response.statusText}`);
            }

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
            const response = await fetch(`${API_BASE_URL}/quotes/${id}/approve`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ rationale }),
            });

            if (!response.ok) {
              throw new Error(`Failed to approve quote: ${response.statusText}`);
            }

            const approvedQuote: Quote = await response.json();

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
            const response = await fetch(`${API_BASE_URL}/quotes/${id}/reject`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ reason }),
            });

            if (!response.ok) {
              throw new Error(`Failed to reject quote: ${response.statusText}`);
            }

            const rejectedQuote: Quote = await response.json();

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

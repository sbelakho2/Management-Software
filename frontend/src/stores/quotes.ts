import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

import { QuoteStatus } from '@/types';

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
}

interface Quote {
  id: string;
  quoteNumber: string;
  rfqId: string;
  customerId: string;
  customerName: string;
  status: QuoteStatus;
  validUntil: string;
  createdAt: string;
  updatedAt: string;
  lineItems: QuoteLineItem[];
  subtotal: number;
  discountType: 'percentage' | 'amount';
  discountValue: number;
  taxRate: number;
  total: number;
  termsAndConditions: string;
  notes: string;
  version: number;
}

interface QuoteStats {
  totalQuotes: number;
  pendingQuotes: number;
  totalValue: number;
  acceptanceRate: number;
}

interface QuoteState {
  quotes: Quote[];
  stats: QuoteStats;
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchQuotes: () => Promise<void>;
  fetchQuoteById: (id: string) => Promise<Quote | null>;
  createQuote: (quote: Partial<Quote>) => Promise<Quote>;
  updateQuote: (id: string, updates: Partial<Quote>) => Promise<Quote>;
  deleteQuote: (id: string) => Promise<void>;
  exportQuote: (id: string, format: 'pdf' | 'excel') => Promise<void>;
  sendQuote: (id: string) => Promise<void>;
  calculateQuoteTotals: (lineItems: QuoteLineItem[], discountType: 'percentage' | 'amount', discountValue: number, taxRate: number) => { subtotal: number; discount: number; tax: number; total: number };
  clearError: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useQuoteStore = create<QuoteState>()(
  devtools(
    persist(
      (set, get) => ({
        quotes: [],
        stats: {
          totalQuotes: 0,
          pendingQuotes: 0,
          totalValue: 0,
          acceptanceRate: 0,
        },
        isLoading: false,
        error: null,
        lastFetchedAt: null,

        fetchQuotes: async () => {
          const { lastFetchedAt } = get();
          const now = Date.now();

          if (lastFetchedAt && now - lastFetchedAt < 30000) {
            return;
          }

          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/quotes');
            const quotes: Quote[] = data.items || [];

            const totalValue = quotes.reduce((sum, q) => sum + q.total, 0);
            const pendingQuotes = quotes.filter(q => q.status === 'pending_approval' || q.status === 'sent');
            const sentQuotes = quotes.filter(q => q.status === 'sent');
            const acceptedQuotes = quotes.filter(q => q.status === 'accepted');

            set({
              quotes,
              stats: {
                totalQuotes: quotes.length,
                pendingQuotes: pendingQuotes.length,
                totalValue,
                acceptanceRate: sentQuotes.length > 0 ? Math.round((acceptedQuotes.length / sentQuotes.length) * 100) : 0,
              },
              isLoading: false,
              lastFetchedAt: now,
            });
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

        createQuote: async (quoteData: Partial[Quote]) => {
          try {
            const newQuote = await apiClient.post<Quote>('/quotes', quoteData);

            set(state => ({
              quotes: [newQuote, ...state.quotes],
              stats: {
                ...state.stats,
                totalQuotes: state.stats.totalQuotes + 1,
              },
            }));

            return newQuote;
          } catch (error) {
            console.error('Error creating quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to create quote' });
            throw error;
          }
        },

        updateQuote: async (id: string, updates: Partial[Quote]) => {
          const currentQuote = get().quotes.find(q => q.id === id);
          if (!currentQuote) {
            throw new Error('Quote not found');
          }

          try {
            const updatedQuote = await apiClient.put<Quote>(`/quotes/${id}`, updates, {
              headers: {
                'If-Match': `"${currentQuote.version}"`,
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
              stats: {
                ...state.stats,
                totalQuotes: state.stats.totalQuotes - 1,
              },
            }));
          } catch (error) {
            console.error('Error deleting quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to delete quote' });
            throw error;
          }
        },

        exportQuote: async (id: string, format: 'pdf' | 'excel') => {
          try {
            // Note: apiClient.get returns data, but for blob we might need to use axios directly or add a config
            // For now, let's keep fetch for blob/export as it requires special handling
            const response = await fetch(`${API_BASE_URL}/quotes/${id}/export?format=${format}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to export quote: ${response.statusText}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `quote_${id}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
          } catch (error) {
            console.error('Error exporting quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to export quote' });
            throw error;
          }
        },

        sendQuote: async (id: string) => {
          try {
            const updatedQuote = await apiClient.post<Quote>(`/quotes/${id}/send`);

            set(state => ({
              quotes: state.quotes.map(q => q.id === id ? updatedQuote : q),
            }));
          } catch (error) {
            console.error('Error sending quote:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to send quote' });
            throw error;
          }
        },

        calculateQuoteTotals: (lineItems, discountType, discountValue, taxRate) => {
          const subtotal = lineItems.reduce((sum, item) => sum + (item.quantity * item.unitPrice), 0);
          const discount = discountType === 'percentage'
            ? (subtotal * discountValue) / 100
            : discountValue;
          const afterDiscount = subtotal - discount;
          const tax = (afterDiscount * taxRate) / 100;
          const total = afterDiscount + tax;

          return { subtotal, discount, tax, total };
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'quote-storage',
        partialize: (state) => ({
          quotes: state.quotes,
          lastFetchedAt: state.lastFetchedAt,
        }),
      }
    ),
    { name: 'QuoteStore' }
  )
);

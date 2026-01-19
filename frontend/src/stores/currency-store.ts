/**
 * Currency Localization System with Live Exchange Rates
 * 
 * Features:
 * - Live exchange rates from European Central Bank (ECB)
 * - Fallback to cached rates
 * - Currency formatting based on user locale
 * - Real-time conversion between currencies
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Supported currencies with their metadata
export const CURRENCIES = {
  USD: { symbol: '$', name: 'US Dollar', locale: 'en-US' },
  EUR: { symbol: '€', name: 'Euro', locale: 'de-DE' },
  GBP: { symbol: '£', name: 'British Pound', locale: 'en-GB' },
  CAD: { symbol: 'CA$', name: 'Canadian Dollar', locale: 'en-CA' },
  CHF: { symbol: 'CHF', name: 'Swiss Franc', locale: 'de-CH' },
  JPY: { symbol: '¥', name: 'Japanese Yen', locale: 'ja-JP' },
  CNY: { symbol: '¥', name: 'Chinese Yuan', locale: 'zh-CN' },
  MAD: { symbol: 'د.م.', name: 'Moroccan Dirham', locale: 'ar-MA' },
  AED: { symbol: 'د.إ', name: 'UAE Dirham', locale: 'ar-AE' },
  SAR: { symbol: '﷼', name: 'Saudi Riyal', locale: 'ar-SA' },
} as const;

export type CurrencyCode = keyof typeof CURRENCIES;

// Exchange rates relative to EUR (ECB base currency)
export interface ExchangeRates {
  base: 'EUR';
  date: string;
  rates: Record<string, number>;
}

// Default fallback rates (approximate values for offline use)
const DEFAULT_RATES: ExchangeRates = {
  base: 'EUR',
  date: '2025-01-01',
  rates: {
    USD: 1.09,
    EUR: 1.00,
    GBP: 0.86,
    CAD: 1.49,
    CHF: 0.95,
    JPY: 163.5,
    CNY: 7.91,
    MAD: 10.85,
    AED: 4.01,
    SAR: 4.09,
  },
};

interface CurrencyState {
  // User's display currency
  displayCurrency: CurrencyCode;
  // Base currency for system (what values are stored in)
  baseCurrency: CurrencyCode;
  // Current exchange rates
  rates: ExchangeRates;
  // Loading state
  isLoading: boolean;
  // Last fetch timestamp
  lastFetched: number | null;
  // Error state
  error: string | null;
  
  // Actions
  setDisplayCurrency: (currency: CurrencyCode) => void;
  setBaseCurrency: (currency: CurrencyCode) => void;
  fetchRates: () => Promise<void>;
  
  // Conversion helpers
  convert: (amount: number, from: CurrencyCode, to: CurrencyCode) => number;
  format: (amount: number, currency?: CurrencyCode, options?: FormatOptions) => string;
  formatWithOriginal: (amount: number, originalCurrency: CurrencyCode) => string;
}

interface FormatOptions {
  maximumFractionDigits?: number;
  minimumFractionDigits?: number;
  notation?: 'standard' | 'compact';
}

// ECB provides XML, but we'll use the exchangerate-api.com free tier as it's JSON-based
// For production, consider using ECB's XML feed directly or a paid API
const ECB_API_URL = 'https://api.exchangerate-api.com/v4/latest/EUR';

export const useCurrencyStore = create<CurrencyState>()(
  persist(
    (set, get) => ({
      displayCurrency: 'USD',
      baseCurrency: 'USD',
      rates: DEFAULT_RATES,
      isLoading: false,
      lastFetched: null,
      error: null,

      setDisplayCurrency: (currency) => set({ displayCurrency: currency }),
      
      setBaseCurrency: (currency) => set({ baseCurrency: currency }),

      fetchRates: async () => {
        const state = get();
        
        // Don't fetch if we recently fetched (within 1 hour)
        const now = Date.now();
        if (state.lastFetched && now - state.lastFetched < 60 * 60 * 1000) {
          return;
        }

        set({ isLoading: true, error: null });

        try {
          const response = await fetch(ECB_API_URL);
          
          if (!response.ok) {
            throw new Error(`Failed to fetch exchange rates: ${response.status}`);
          }

          const data = await response.json();
          
          // Ensure EUR is in the rates (it's the base)
          const rates: Record<string, number> = { EUR: 1, ...data.rates };

          set({
            rates: {
              base: 'EUR',
              date: data.date || new Date().toISOString().split('T')[0],
              rates,
            },
            isLoading: false,
            lastFetched: now,
            error: null,
          });
        } catch (error) {
          console.error('Failed to fetch exchange rates:', error);
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to fetch rates',
          });
          // Keep using cached/default rates
        }
      },

      convert: (amount, from, to) => {
        if (from === to) return amount;
        
        const { rates } = get();
        
        // Convert to EUR first (base currency), then to target
        const fromRate = rates.rates[from] || 1;
        const toRate = rates.rates[to] || 1;
        
        // amount in FROM -> EUR -> TO
        const inEur = amount / fromRate;
        return inEur * toRate;
      },

      format: (amount, currency, options = {}) => {
        const { displayCurrency } = get();
        const targetCurrency = currency || displayCurrency;
        const currencyInfo = CURRENCIES[targetCurrency];
        
        const formatter = new Intl.NumberFormat(currencyInfo?.locale || 'en-US', {
          style: 'currency',
          currency: targetCurrency,
          maximumFractionDigits: options.maximumFractionDigits ?? 2,
          minimumFractionDigits: options.minimumFractionDigits ?? 0,
          notation: options.notation || 'standard',
        });

        return formatter.format(amount);
      },

      formatWithOriginal: (amount, originalCurrency) => {
        const { displayCurrency, convert, format } = get();
        
        if (originalCurrency === displayCurrency) {
          return format(amount, displayCurrency);
        }
        
        const converted = convert(amount, originalCurrency, displayCurrency);
        const formattedConverted = format(converted, displayCurrency);
        const formattedOriginal = format(amount, originalCurrency);
        
        return `${formattedConverted} (${formattedOriginal})`;
      },
    }),
    {
      name: 'currency-storage',
      partialize: (state) => ({
        displayCurrency: state.displayCurrency,
        baseCurrency: state.baseCurrency,
        rates: state.rates,
        lastFetched: state.lastFetched,
      }),
    }
  )
);

/**
 * React hook for currency formatting
 * Automatically uses the user's display currency
 */
export function useCurrency() {
  const {
    displayCurrency,
    baseCurrency,
    rates,
    isLoading,
    error,
    setDisplayCurrency,
    fetchRates,
    convert,
    format,
    formatWithOriginal,
  } = useCurrencyStore();

  return {
    displayCurrency,
    baseCurrency,
    rates,
    isLoading,
    error,
    setDisplayCurrency,
    fetchRates,
    
    /**
     * Convert amount from base currency to display currency and format
     */
    formatAmount: (amount: number, options?: FormatOptions) => {
      const converted = convert(amount, baseCurrency, displayCurrency);
      return format(converted, displayCurrency, options);
    },
    
    /**
     * Format amount in a specific currency
     */
    formatInCurrency: (amount: number, currency: CurrencyCode, options?: FormatOptions) => {
      return format(amount, currency, options);
    },
    
    /**
     * Convert and format, showing both converted and original amounts
     */
    formatWithConversion: (amount: number, originalCurrency: CurrencyCode) => {
      return formatWithOriginal(amount, originalCurrency);
    },
    
    /**
     * Convert amount between currencies
     */
    convertAmount: (amount: number, from: CurrencyCode, to: CurrencyCode) => {
      return convert(amount, from, to);
    },
  };
}

/**
 * Get locale-appropriate currency for a given locale string
 */
export function getCurrencyForLocale(locale: string): CurrencyCode {
  const localeMap: Record<string, CurrencyCode> = {
    'en': 'USD',
    'en-US': 'USD',
    'en-GB': 'GBP',
    'en-CA': 'CAD',
    'fr': 'EUR',
    'fr-FR': 'EUR',
    'fr-CA': 'CAD',
    'de': 'EUR',
    'de-DE': 'EUR',
    'de-CH': 'CHF',
    'es': 'EUR',
    'es-ES': 'EUR',
    'es-MX': 'USD',
    'ar': 'SAR',
    'ar-MA': 'MAD',
    'ar-AE': 'AED',
    'ar-SA': 'SAR',
    'ja': 'JPY',
    'zh': 'CNY',
  };
  
  return localeMap[locale] || localeMap[locale.split('-')[0]] || 'USD';
}

/**
 * Initialize currency system on app load
 * Call this in your root layout or _app.tsx
 */
export async function initializeCurrency() {
  const store = useCurrencyStore.getState();
  
  // Fetch rates on initialization
  await store.fetchRates();
  
  // Set up periodic refresh (every hour)
  setInterval(() => {
    store.fetchRates();
  }, 60 * 60 * 1000);
}

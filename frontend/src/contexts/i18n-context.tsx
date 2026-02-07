'use client';

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
  type ReactNode,
} from 'react';

// Import all locale files
import en from '@/locales/en.json';
import fr from '@/locales/fr.json';
import ar from '@/locales/ar.json';
import es from '@/locales/es.json';
import de from '@/locales/de.json';

// Import currency store for integrated formatting
import { useCurrencyStore, CURRENCIES, type CurrencyCode } from '@/stores/currency-store';

// =============================================================================
// TYPES
// =============================================================================

export type Locale = 'en' | 'fr' | 'ar' | 'es' | 'de';
export type Direction = 'ltr' | 'rtl';

export interface LocaleConfig {
  locale: Locale;
  name: string;
  nativeName: string;
  flag: string;
  direction: Direction;
}

export interface I18nContextValue {
  locale: Locale;
  direction: Direction;
  localeConfig: LocaleConfig;
  availableLocales: LocaleConfig[];
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
  formatCurrency: (value: number, currency?: string) => string;
  formatDate: (date: Date | string, options?: Intl.DateTimeFormatOptions) => string;
  formatRelativeTime: (date: Date | string) => string;
  isRTL: boolean;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const STORAGE_KEY = 'sensei-locale';

const TRANSLATIONS: Record<Locale, Record<string, unknown>> = {
  en,
  fr,
  ar,
  es,
  de,
};

const LOCALE_CONFIGS: Record<Locale, LocaleConfig> = {
  en: { locale: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸', direction: 'ltr' },
  fr: { locale: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷', direction: 'ltr' },
  ar: { locale: 'ar', name: 'Arabic', nativeName: 'العربية', flag: '🇹🇳', direction: 'rtl' },
  es: { locale: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸', direction: 'ltr' },
  de: { locale: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪', direction: 'ltr' },
};

// Map short locale to BCP 47 locale tags for Intl APIs
const LOCALE_BCP47: Record<Locale, string> = {
  en: 'en-US',
  fr: 'fr-FR',
  ar: 'ar-TN', // Tunisian Arabic
  es: 'es-ES',
  de: 'de-DE',
};

// Default currency per locale
const DEFAULT_CURRENCY: Record<Locale, string> = {
  en: 'USD',
  fr: 'EUR',
  ar: 'TND', // Tunisian Dinar
  es: 'EUR',
  de: 'EUR',
};

// =============================================================================
// CONTEXT
// =============================================================================

const I18nContext = createContext<I18nContextValue | null>(null);

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Get a nested value from an object by dot-notation key
 */
function getNestedValue(obj: Record<string, unknown>, path: string): string | undefined {
  const keys = path.split('.');
  let current: unknown = obj;

  for (const key of keys) {
    if (current === null || current === undefined || typeof current !== 'object') {
      return undefined;
    }
    current = (current as Record<string, unknown>)[key];
  }

  return typeof current === 'string' ? current : undefined;
}

/**
 * Convert a translation key to a human-readable fallback
 * e.g., "pages.pipeline.newOpportunity" -> "New Opportunity"
 */
function keyToReadableFallback(key: string): string {
  // Get the last part of the key (most specific)
  const lastPart = key.split('.').pop() || key;
  
  // Convert camelCase/PascalCase to words with spaces
  // "newOpportunity" -> "new Opportunity" -> "New Opportunity"
  const withSpaces = lastPart
    .replace(/([A-Z])/g, ' $1')
    .replace(/([0-9]+)/g, ' $1 ')
    .trim();
  
  // Capitalize first letter of each word
  return withSpaces
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Interpolate parameters into a translation string
 * Supports both {param} and {{param}} syntax
 */
function interpolate(text: string, params?: Record<string, string | number>): string {
  if (!params) return text;

  let result = text;
  Object.entries(params).forEach(([key, value]) => {
    // Support both {param} and {{param}} syntax
    result = result.replace(new RegExp(`\\{\\{?${key}\\}\\}?`, 'g'), String(value));
  });

  return result;
}

/**
 * Get saved locale from localStorage
 */
function getSavedLocale(): Locale | null {
  if (typeof window === 'undefined') return null;
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && saved in LOCALE_CONFIGS) {
    return saved as Locale;
  }
  return null;
}

/**
 * Detect browser locale
 */
function detectBrowserLocale(): Locale {
  if (typeof window === 'undefined') return 'en';
  
  const browserLang = navigator.language.split('-')[0];
  if (browserLang in LOCALE_CONFIGS) {
    return browserLang as Locale;
  }
  return 'en';
}

// =============================================================================
// PROVIDER
// =============================================================================

interface I18nProviderProps {
  children: ReactNode;
  defaultLocale?: Locale;
}

export function I18nProvider({
  children,
  defaultLocale = 'en',
}: I18nProviderProps): React.ReactElement {
  const [locale, setLocaleState] = useState<Locale>(() => {
    // Try to get from localStorage first, then browser, then default
    return getSavedLocale() || detectBrowserLocale() || defaultLocale;
  });

  const localeConfig = LOCALE_CONFIGS[locale];
  const direction = localeConfig.direction;
  const isRTL = direction === 'rtl';
  const bcp47Locale = LOCALE_BCP47[locale];

  // Apply direction and lang to document
  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = locale;
    
    // Add RTL class for Tailwind/CSS targeting
    if (isRTL) {
      document.documentElement.classList.add('rtl');
    } else {
      document.documentElement.classList.remove('rtl');
    }
  }, [direction, locale, isRTL]);

  // Set locale and persist
  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem(STORAGE_KEY, newLocale);
  }, []);

  // Translation function
  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      const translations = TRANSLATIONS[locale];
      let value = getNestedValue(translations as Record<string, unknown>, key);

      // Fallback to English if translation not found
      if (value === undefined && locale !== 'en') {
        value = getNestedValue(TRANSLATIONS.en as Record<string, unknown>, key);
      }

      // Return human-readable fallback if no translation found
      if (value === undefined) {
        // Only warn in development
        if (process.env.NODE_ENV === 'development') {
          console.warn(`Missing translation for key: ${key}`);
        }
        return keyToReadableFallback(key);
      }

      return interpolate(value, params);
    },
    [locale]
  );

  // Number formatting
  const formatNumber = useCallback(
    (value: number, options?: Intl.NumberFormatOptions): string => {
      return new Intl.NumberFormat(bcp47Locale, options).format(value);
    },
    [bcp47Locale]
  );

  // Currency formatting - integrates with currency store for user preferences
  const formatCurrency = useCallback(
    (value: number, currency?: string): string => {
      // Get the user's display currency from the store if no explicit currency provided
      const currencyStore = useCurrencyStore.getState();
      const targetCurrency = currency || currencyStore.displayCurrency || DEFAULT_CURRENCY[locale];
      
      // Use the currency's native locale for proper symbol placement
      const currencyInfo = CURRENCIES[targetCurrency as CurrencyCode];
      const formatLocale = currencyInfo?.locale || bcp47Locale;
      
      return new Intl.NumberFormat(formatLocale, {
        style: 'currency',
        currency: targetCurrency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }).format(value);
    },
    [bcp47Locale, locale]
  );

  // Date formatting
  const formatDate = useCallback(
    (date: Date | string, options?: Intl.DateTimeFormatOptions): string => {
      const d = typeof date === 'string' ? new Date(date) : date;
      return new Intl.DateTimeFormat(bcp47Locale, options).format(d);
    },
    [bcp47Locale]
  );

  // Relative time formatting
  const formatRelativeTime = useCallback(
    (date: Date | string): string => {
      const d = typeof date === 'string' ? new Date(date) : date;
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);
      const diffWeeks = Math.floor(diffDays / 7);
      const diffMonths = Math.floor(diffDays / 30);
      const diffYears = Math.floor(diffDays / 365);

      if (diffSecs < 60) return t('time.now');
      if (diffMins < 60) return t('time.minutes', { count: diffMins });
      if (diffHours < 24) return t('time.hours', { count: diffHours });
      if (diffDays < 7) return t('time.days', { count: diffDays });
      if (diffWeeks < 4) return t('time.weeks', { count: diffWeeks });
      if (diffMonths < 12) return t('time.months', { count: diffMonths });
      return t('time.years', { count: diffYears });
    },
    [t]
  );

  const availableLocales = useMemo(() => Object.values(LOCALE_CONFIGS), []);

  const value = useMemo(
    () => ({
      locale,
      direction,
      localeConfig,
      availableLocales,
      setLocale,
      t,
      formatNumber,
      formatCurrency,
      formatDate,
      formatRelativeTime,
      isRTL,
    }),
    [
      locale,
      direction,
      localeConfig,
      availableLocales,
      setLocale,
      t,
      formatNumber,
      formatCurrency,
      formatDate,
      formatRelativeTime,
      isRTL,
    ]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

// =============================================================================
// HOOK
// =============================================================================

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
}

// =============================================================================
// EXPORTS
// =============================================================================

export { LOCALE_CONFIGS, LOCALE_BCP47, DEFAULT_CURRENCY };
export type { LocaleConfig as I18nLocaleConfig };

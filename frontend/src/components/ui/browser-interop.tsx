/**
 * Browser, OS & Hardware Interoperability Components
 * 
 * Section 19.10: Browser, OS & Hardware Interoperability
 * 
 * Provides cross-browser compatibility, OS-specific interactions,
 * internationalization (i18n), and localization (l10n) support.
 */

'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Supported browsers for feature detection
 */
export const BROWSER = {
  CHROME: 'chrome',
  FIREFOX: 'firefox',
  SAFARI: 'safari',
  EDGE: 'edge',
  OPERA: 'opera',
  UNKNOWN: 'unknown',
} as const;

export type BrowserType = (typeof BROWSER)[keyof typeof BROWSER];

/**
 * Operating systems
 */
export const OS = {
  WINDOWS: 'windows',
  MACOS: 'macos',
  LINUX: 'linux',
  IOS: 'ios',
  ANDROID: 'android',
  UNKNOWN: 'unknown',
} as const;

export type OSType = (typeof OS)[keyof typeof OS];

/**
 * Supported locales
 */
export const LOCALE = {
  EN_US: 'en-US',
  EN_GB: 'en-GB',
  FR_FR: 'fr-FR',
  AR_SA: 'ar-SA',
} as const;

export type LocaleType = (typeof LOCALE)[keyof typeof LOCALE];

/**
 * Unit systems
 */
export const UNIT_SYSTEM = {
  METRIC: 'metric',
  IMPERIAL: 'imperial',
} as const;

export type UnitSystemType = (typeof UNIT_SYSTEM)[keyof typeof UNIT_SYSTEM];

/**
 * Theme modes
 */
export const THEME_MODE = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
} as const;

export type ThemeModeType = (typeof THEME_MODE)[keyof typeof THEME_MODE];

/**
 * Text direction
 */
export const TEXT_DIRECTION = {
  LTR: 'ltr',
  RTL: 'rtl',
} as const;

export type TextDirectionType = (typeof TEXT_DIRECTION)[keyof typeof TEXT_DIRECTION];

/**
 * CSS feature support flags
 */
export const CSS_FEATURE = {
  ASPECT_RATIO: 'aspectRatio',
  GRID: 'grid',
  FLEX: 'flex',
  GAP: 'gap',
  CONTAINER_QUERIES: 'containerQueries',
  SUBGRID: 'subgrid',
  SCROLL_SNAP: 'scrollSnap',
} as const;

export type CSSFeatureType = (typeof CSS_FEATURE)[keyof typeof CSS_FEATURE];

// =============================================================================
// BROWSER DETECTION
// =============================================================================

/**
 * Detect current browser
 */
export function detectBrowser(): BrowserType {
  if (typeof navigator === 'undefined' || !navigator.userAgent) return BROWSER.UNKNOWN;

  const userAgent = navigator.userAgent.toLowerCase();

  if (userAgent.includes('edg/')) return BROWSER.EDGE;
  if (userAgent.includes('chrome') && !userAgent.includes('edg')) return BROWSER.CHROME;
  if (userAgent.includes('firefox')) return BROWSER.FIREFOX;
  if (userAgent.includes('safari') && !userAgent.includes('chrome')) return BROWSER.SAFARI;
  if (userAgent.includes('opera') || userAgent.includes('opr')) return BROWSER.OPERA;

  return BROWSER.UNKNOWN;
}

/**
 * Detect current OS
 */
export function detectOS(): OSType {
  if (typeof navigator === 'undefined' || !navigator.userAgent) return OS.UNKNOWN;

  const userAgent = navigator.userAgent.toLowerCase();
  const platform = navigator.platform?.toLowerCase() || '';

  if (/iphone|ipad|ipod/.test(userAgent)) return OS.IOS;
  if (/android/.test(userAgent)) return OS.ANDROID;
  if (platform.includes('mac')) return OS.MACOS;
  if (platform.includes('win')) return OS.WINDOWS;
  if (platform.includes('linux')) return OS.LINUX;

  return OS.UNKNOWN;
}

/**
 * Check if device supports touch
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || (navigator?.maxTouchPoints ?? 0) > 0;
}

/**
 * Check if device is mobile
 */
export function isMobileDevice(): boolean {
  const os = detectOS();
  return os === OS.IOS || os === OS.ANDROID;
}

// =============================================================================
// CSS FEATURE DETECTION
// =============================================================================

/**
 * Check CSS feature support
 */
export function checkCSSFeature(feature: CSSFeatureType): boolean {
  if (typeof CSS === 'undefined' || typeof CSS.supports !== 'function') {
    return false;
  }

  switch (feature) {
    case CSS_FEATURE.ASPECT_RATIO:
      return CSS.supports('aspect-ratio', '1 / 1');
    case CSS_FEATURE.GRID:
      return CSS.supports('display', 'grid');
    case CSS_FEATURE.FLEX:
      return CSS.supports('display', 'flex');
    case CSS_FEATURE.GAP:
      return CSS.supports('gap', '1px');
    case CSS_FEATURE.CONTAINER_QUERIES:
      return CSS.supports('container-type', 'inline-size');
    case CSS_FEATURE.SUBGRID:
      return CSS.supports('grid-template-columns', 'subgrid');
    case CSS_FEATURE.SCROLL_SNAP:
      return CSS.supports('scroll-snap-type', 'x mandatory');
    default:
      return false;
  }
}

/**
 * Get all CSS feature support
 */
export function getCSSFeatureSupport(): Record<CSSFeatureType, boolean> {
  return {
    [CSS_FEATURE.ASPECT_RATIO]: checkCSSFeature(CSS_FEATURE.ASPECT_RATIO),
    [CSS_FEATURE.GRID]: checkCSSFeature(CSS_FEATURE.GRID),
    [CSS_FEATURE.FLEX]: checkCSSFeature(CSS_FEATURE.FLEX),
    [CSS_FEATURE.GAP]: checkCSSFeature(CSS_FEATURE.GAP),
    [CSS_FEATURE.CONTAINER_QUERIES]: checkCSSFeature(CSS_FEATURE.CONTAINER_QUERIES),
    [CSS_FEATURE.SUBGRID]: checkCSSFeature(CSS_FEATURE.SUBGRID),
    [CSS_FEATURE.SCROLL_SNAP]: checkCSSFeature(CSS_FEATURE.SCROLL_SNAP),
  };
}

// =============================================================================
// SHARE API
// =============================================================================

export interface ShareData {
  title?: string;
  text?: string;
  url?: string;
  files?: File[];
}

/**
 * Check if Web Share API is available
 */
export function canShare(): boolean {
  if (typeof navigator === 'undefined') return false;
  return 'share' in navigator;
}

/**
 * Check if sharing files is supported
 */
export function canShareFiles(): boolean {
  if (typeof navigator === 'undefined') return false;
  return 'canShare' in navigator;
}

/**
 * Share content using native Share API
 */
export async function nativeShare(data: ShareData): Promise<boolean> {
  if (!canShare()) {
    return false;
  }

  try {
    await navigator.share(data);
    return true;
  } catch (error) {
    // User cancelled or error
    if ((error as Error).name === 'AbortError') {
      return false;
    }
    console.error('Share failed:', error);
    return false;
  }
}

// =============================================================================
// THEME CONTEXT
// =============================================================================

interface ThemeContextValue {
  theme: ThemeModeType;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: ThemeModeType) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/**
 * Get system color scheme preference
 */
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: ThemeModeType;
  storageKey?: string;
}

/**
 * Theme provider with system preference support
 */
export function ThemeProvider({
  children,
  defaultTheme = THEME_MODE.SYSTEM,
  storageKey = 'theme-preference',
}: ThemeProviderProps): React.ReactElement {
  const [theme, setThemeState] = useState<ThemeModeType>(() => {
    if (typeof localStorage === 'undefined') return defaultTheme;
    const stored = localStorage.getItem(storageKey);
    return (stored as ThemeModeType) || defaultTheme;
  });

  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => getSystemTheme());

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light');
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const resolvedTheme = theme === THEME_MODE.SYSTEM ? systemTheme : (theme as 'light' | 'dark');

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);
  }, [resolvedTheme]);

  const setTheme = useCallback((newTheme: ThemeModeType) => {
    setThemeState(newTheme);
    localStorage.setItem(storageKey, newTheme);
  }, [storageKey]);

  const value = useMemo(() => ({
    theme,
    resolvedTheme,
    setTheme,
  }), [theme, resolvedTheme, setTheme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

// =============================================================================
// THEME TOGGLE
// =============================================================================

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

/**
 * Theme toggle component
 */
export function ThemeToggle({
  className = '',
  showLabel = false,
}: ThemeToggleProps): React.ReactElement {
  const { theme, setTheme } = useTheme();

  const cycleTheme = () => {
    const themes: ThemeModeType[] = [THEME_MODE.LIGHT, THEME_MODE.DARK, THEME_MODE.SYSTEM];
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  const icon = theme === THEME_MODE.LIGHT ? '☀️' : theme === THEME_MODE.DARK ? '🌙' : '💻';
  const label = theme === THEME_MODE.LIGHT ? 'Light' : theme === THEME_MODE.DARK ? 'Dark' : 'System';

  return (
    <button
      type="button"
      onClick={cycleTheme}
      aria-label={`Theme: ${label}. Click to change`}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${className}`}
    >
      <span aria-hidden="true">{icon}</span>
      {showLabel && <span>{label}</span>}
    </button>
  );
}

// =============================================================================
// SCROLLBAR STYLING
// =============================================================================

interface ScrollbarContainerProps {
  children: ReactNode;
  className?: string;
  hideScrollbar?: boolean;
  thinScrollbar?: boolean;
}

/**
 * Scrollbar-styled container with cross-browser support
 */
export function ScrollbarContainer({
  children,
  className = '',
  hideScrollbar = false,
  thinScrollbar = false,
}: ScrollbarContainerProps): React.ReactElement {
  const scrollbarClass = hideScrollbar
    ? 'scrollbar-hide'
    : thinScrollbar
    ? 'scrollbar-thin'
    : 'scrollbar-default';

  return (
    <>
      <style>{`
        .scrollbar-hide {
          scrollbar-width: none;
          -ms-overflow-style: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        
        .scrollbar-thin {
          scrollbar-width: thin;
          scrollbar-color: #cbd5e1 transparent;
        }
        .scrollbar-thin::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        .scrollbar-thin::-webkit-scrollbar-track {
          background: transparent;
        }
        .scrollbar-thin::-webkit-scrollbar-thumb {
          background-color: #cbd5e1;
          border-radius: 3px;
        }
        .scrollbar-thin::-webkit-scrollbar-thumb:hover {
          background-color: #94a3b8;
        }
        
        .scrollbar-default {
          scrollbar-width: auto;
          scrollbar-color: #94a3b8 #f1f5f9;
        }
        .scrollbar-default::-webkit-scrollbar {
          width: 12px;
          height: 12px;
        }
        .scrollbar-default::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 6px;
        }
        .scrollbar-default::-webkit-scrollbar-thumb {
          background-color: #94a3b8;
          border-radius: 6px;
          border: 2px solid #f1f5f9;
        }
        .scrollbar-default::-webkit-scrollbar-thumb:hover {
          background-color: #64748b;
        }
        
        /* Touch-friendly scrollbars */
        @media (pointer: coarse) {
          .scrollbar-thin::-webkit-scrollbar,
          .scrollbar-default::-webkit-scrollbar {
            width: 16px;
            height: 16px;
          }
        }
        
        /* Dark mode scrollbars */
        .dark .scrollbar-thin {
          scrollbar-color: #475569 transparent;
        }
        .dark .scrollbar-thin::-webkit-scrollbar-thumb {
          background-color: #475569;
        }
        .dark .scrollbar-thin::-webkit-scrollbar-thumb:hover {
          background-color: #64748b;
        }
        
        .dark .scrollbar-default {
          scrollbar-color: #475569 #1e293b;
        }
        .dark .scrollbar-default::-webkit-scrollbar-track {
          background: #1e293b;
        }
        .dark .scrollbar-default::-webkit-scrollbar-thumb {
          background-color: #475569;
          border-color: #1e293b;
        }
        .dark .scrollbar-default::-webkit-scrollbar-thumb:hover {
          background-color: #64748b;
        }
      `}</style>
      <div className={`overflow-auto ${scrollbarClass} ${className}`}>
        {children}
      </div>
    </>
  );
}

// =============================================================================
// I18N CONTEXT
// =============================================================================

interface Translations {
  [key: string]: string | Translations;
}

interface I18nContextValue {
  locale: LocaleType;
  direction: TextDirectionType;
  setLocale: (locale: LocaleType) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
  formatCurrency: (value: number, currency?: string) => string;
  formatDate: (date: Date | string, options?: Intl.DateTimeFormatOptions) => string;
  formatRelativeTime: (date: Date | string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

// Base translations
const translations: Record<LocaleType, Translations> = {
  'en-US': {
    common: {
      save: 'Save',
      cancel: 'Cancel',
      delete: 'Delete',
      edit: 'Edit',
      add: 'Add',
      search: 'Search',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      confirm: 'Confirm',
      close: 'Close',
    },
    time: {
      now: 'just now',
      seconds: '{count} seconds ago',
      minutes: '{count} minutes ago',
      hours: '{count} hours ago',
      days: '{count} days ago',
      weeks: '{count} weeks ago',
      months: '{count} months ago',
      years: '{count} years ago',
    },
  },
  'en-GB': {
    common: {
      save: 'Save',
      cancel: 'Cancel',
      delete: 'Delete',
      edit: 'Edit',
      add: 'Add',
      search: 'Search',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      confirm: 'Confirm',
      close: 'Close',
    },
    time: {
      now: 'just now',
      seconds: '{count} seconds ago',
      minutes: '{count} minutes ago',
      hours: '{count} hours ago',
      days: '{count} days ago',
      weeks: '{count} weeks ago',
      months: '{count} months ago',
      years: '{count} years ago',
    },
  },
  'fr-FR': {
    common: {
      save: 'Enregistrer',
      cancel: 'Annuler',
      delete: 'Supprimer',
      edit: 'Modifier',
      add: 'Ajouter',
      search: 'Rechercher',
      loading: 'Chargement...',
      error: 'Erreur',
      success: 'Succès',
      confirm: 'Confirmer',
      close: 'Fermer',
    },
    time: {
      now: "à l'instant",
      seconds: 'il y a {count} secondes',
      minutes: 'il y a {count} minutes',
      hours: 'il y a {count} heures',
      days: 'il y a {count} jours',
      weeks: 'il y a {count} semaines',
      months: 'il y a {count} mois',
      years: 'il y a {count} ans',
    },
  },
  'ar-SA': {
    common: {
      save: 'حفظ',
      cancel: 'إلغاء',
      delete: 'حذف',
      edit: 'تعديل',
      add: 'إضافة',
      search: 'بحث',
      loading: 'جار التحميل...',
      error: 'خطأ',
      success: 'نجاح',
      confirm: 'تأكيد',
      close: 'إغلاق',
    },
    time: {
      now: 'الآن',
      seconds: 'منذ {count} ثانية',
      minutes: 'منذ {count} دقيقة',
      hours: 'منذ {count} ساعة',
      days: 'منذ {count} يوم',
      weeks: 'منذ {count} أسبوع',
      months: 'منذ {count} شهر',
      years: 'منذ {count} سنة',
    },
  },
};

/**
 * Get text direction for locale
 */
export function getTextDirection(locale: LocaleType): TextDirectionType {
  return locale.startsWith('ar') ? TEXT_DIRECTION.RTL : TEXT_DIRECTION.LTR;
}

/**
 * Get nested translation value
 */
function getTranslation(obj: Translations, path: string): string | undefined {
  const keys = path.split('.');
  let current: Translations | string = obj;

  for (const key of keys) {
    if (typeof current !== 'object' || current === null) {
      return undefined;
    }
    current = current[key];
  }

  return typeof current === 'string' ? current : undefined;
}

interface I18nProviderProps {
  children: ReactNode;
  defaultLocale?: LocaleType;
  storageKey?: string;
  customTranslations?: Record<LocaleType, Translations>;
}

/**
 * Internationalization provider
 */
export function I18nProvider({
  children,
  defaultLocale = LOCALE.EN_US,
  storageKey = 'locale-preference',
  customTranslations,
}: I18nProviderProps): React.ReactElement {
  const [locale, setLocaleState] = useState<LocaleType>(() => {
    if (typeof localStorage === 'undefined') return defaultLocale;
    const stored = localStorage.getItem(storageKey);
    return (stored as LocaleType) || defaultLocale;
  });

  const direction = getTextDirection(locale);

  // Apply direction to document
  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = locale;
  }, [direction, locale]);

  const setLocale = useCallback((newLocale: LocaleType) => {
    setLocaleState(newLocale);
    localStorage.setItem(storageKey, newLocale);
  }, [storageKey]);

  // Merge custom translations
  const mergedTranslations = useMemo(() => {
    if (!customTranslations) return translations;
    const merged = { ...translations };
    Object.keys(customTranslations).forEach((loc) => {
      const key = loc as LocaleType;
      merged[key] = { ...merged[key], ...customTranslations[key] };
    });
    return merged;
  }, [customTranslations]);

  // Translation function
  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    const localeTranslations = mergedTranslations[locale] || mergedTranslations[LOCALE.EN_US];
    let value = getTranslation(localeTranslations, key) || key;

    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        value = value.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramValue));
      });
    }

    return value;
  }, [locale, mergedTranslations]);

  // Number formatting
  const formatNumber = useCallback((value: number, options?: Intl.NumberFormatOptions): string => {
    return new Intl.NumberFormat(locale, options).format(value);
  }, [locale]);

  // Currency formatting
  const formatCurrency = useCallback((value: number, currency: string = 'USD'): string => {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
    }).format(value);
  }, [locale]);

  // Date formatting
  const formatDate = useCallback((date: Date | string, options?: Intl.DateTimeFormatOptions): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat(locale, options).format(d);
  }, [locale]);

  // Relative time formatting
  const formatRelativeTime = useCallback((date: Date | string): string => {
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
  }, [t]);

  const value = useMemo(() => ({
    locale,
    direction,
    setLocale,
    t,
    formatNumber,
    formatCurrency,
    formatDate,
    formatRelativeTime,
  }), [locale, direction, setLocale, t, formatNumber, formatCurrency, formatDate, formatRelativeTime]);

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

/**
 * Hook to access i18n context
 */
export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
}

// =============================================================================
// LOCALE SELECTOR
// =============================================================================

interface LocaleSelectorProps {
  className?: string;
}

/**
 * Locale selector dropdown
 */
export function LocaleSelector({ className = '' }: LocaleSelectorProps): React.ReactElement {
  const { locale, setLocale } = useI18n();
  const [isOpen, setIsOpen] = useState(false);

  const locales: { value: LocaleType; label: string; flag: string }[] = [
    { value: LOCALE.EN_US, label: 'English (US)', flag: '🇺🇸' },
    { value: LOCALE.EN_GB, label: 'English (UK)', flag: '🇬🇧' },
    { value: LOCALE.FR_FR, label: 'Français', flag: '🇫🇷' },
    { value: LOCALE.AR_SA, label: 'العربية', flag: '🇸🇦' },
  ];

  const currentLocale = locales.find((l) => l.value === locale) || locales[0];

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600 transition-colors"
      >
        <span aria-hidden="true">{currentLocale.flag}</span>
        <span>{currentLocale.label}</span>
        <span aria-hidden="true" className="text-gray-400">▼</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <ul
            role="listbox"
            aria-label="Select language"
            className="absolute top-full left-0 mt-1 w-full min-w-[180px] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 py-1"
          >
            {locales.map((loc) => (
              <li
                key={loc.value}
                role="option"
                aria-selected={loc.value === locale}
                onClick={() => {
                  setLocale(loc.value);
                  setIsOpen(false);
                }}
                className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 ${
                  loc.value === locale ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                }`}
              >
                <span aria-hidden="true">{loc.flag}</span>
                <span>{loc.label}</span>
                {loc.value === locale && (
                  <span className="ml-auto text-blue-600 dark:text-blue-400">✓</span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// =============================================================================
// UNIT CONVERSION
// =============================================================================

interface UnitContextValue {
  system: UnitSystemType;
  setSystem: (system: UnitSystemType) => void;
  convertLength: (value: number, fromMetric?: boolean) => number;
  convertWeight: (value: number, fromMetric?: boolean) => number;
  convertTemperature: (value: number, fromCelsius?: boolean) => number;
  formatLength: (value: number, isMetric?: boolean) => string;
  formatWeight: (value: number, isMetric?: boolean) => string;
  formatTemperature: (value: number, isCelsius?: boolean) => string;
}

const UnitContext = createContext<UnitContextValue | null>(null);

interface UnitProviderProps {
  children: ReactNode;
  defaultSystem?: UnitSystemType;
  storageKey?: string;
}

/**
 * Unit conversion provider
 */
export function UnitProvider({
  children,
  defaultSystem = UNIT_SYSTEM.METRIC,
  storageKey = 'unit-system',
}: UnitProviderProps): React.ReactElement {
  const [system, setSystemState] = useState<UnitSystemType>(() => {
    if (typeof localStorage === 'undefined') return defaultSystem;
    const stored = localStorage.getItem(storageKey);
    return (stored as UnitSystemType) || defaultSystem;
  });

  const setSystem = useCallback((newSystem: UnitSystemType) => {
    setSystemState(newSystem);
    localStorage.setItem(storageKey, newSystem);
  }, [storageKey]);

  // Length conversion (mm to inches)
  const convertLength = useCallback((value: number, fromMetric: boolean = true): number => {
    const MM_TO_INCH = 0.0393701;
    const INCH_TO_MM = 25.4;
    return fromMetric ? value * MM_TO_INCH : value * INCH_TO_MM;
  }, []);

  // Weight conversion (kg to lbs)
  const convertWeight = useCallback((value: number, fromMetric: boolean = true): number => {
    const KG_TO_LB = 2.20462;
    const LB_TO_KG = 0.453592;
    return fromMetric ? value * KG_TO_LB : value * LB_TO_KG;
  }, []);

  // Temperature conversion
  const convertTemperature = useCallback((value: number, fromCelsius: boolean = true): number => {
    return fromCelsius ? (value * 9) / 5 + 32 : ((value - 32) * 5) / 9;
  }, []);

  // Format length with unit
  const formatLength = useCallback((value: number, isMetric: boolean = true): string => {
    if (system === UNIT_SYSTEM.METRIC) {
      const displayValue = isMetric ? value : convertLength(value, false);
      return `${displayValue.toFixed(2)} mm`;
    } else {
      const displayValue = isMetric ? convertLength(value, true) : value;
      return `${displayValue.toFixed(3)} in`;
    }
  }, [system, convertLength]);

  // Format weight with unit
  const formatWeight = useCallback((value: number, isMetric: boolean = true): string => {
    if (system === UNIT_SYSTEM.METRIC) {
      const displayValue = isMetric ? value : convertWeight(value, false);
      return `${displayValue.toFixed(2)} kg`;
    } else {
      const displayValue = isMetric ? convertWeight(value, true) : value;
      return `${displayValue.toFixed(2)} lb`;
    }
  }, [system, convertWeight]);

  // Format temperature with unit
  const formatTemperature = useCallback((value: number, isCelsius: boolean = true): string => {
    if (system === UNIT_SYSTEM.METRIC) {
      const displayValue = isCelsius ? value : convertTemperature(value, false);
      return `${displayValue.toFixed(1)} °C`;
    } else {
      const displayValue = isCelsius ? convertTemperature(value, true) : value;
      return `${displayValue.toFixed(1)} °F`;
    }
  }, [system, convertTemperature]);

  const value = useMemo(() => ({
    system,
    setSystem,
    convertLength,
    convertWeight,
    convertTemperature,
    formatLength,
    formatWeight,
    formatTemperature,
  }), [system, setSystem, convertLength, convertWeight, convertTemperature, formatLength, formatWeight, formatTemperature]);

  return (
    <UnitContext.Provider value={value}>
      {children}
    </UnitContext.Provider>
  );
}

/**
 * Hook to access unit context
 */
export function useUnits(): UnitContextValue {
  const context = useContext(UnitContext);
  if (!context) {
    throw new Error('useUnits must be used within UnitProvider');
  }
  return context;
}

// =============================================================================
// UNIT TOGGLE
// =============================================================================

interface UnitToggleProps {
  className?: string;
}

/**
 * Unit system toggle
 */
export function UnitToggle({ className = '' }: UnitToggleProps): React.ReactElement {
  const { system, setSystem } = useUnits();

  return (
    <div className={`flex items-center gap-1 ${className}`} role="radiogroup" aria-label="Unit system">
      <button
        type="button"
        role="radio"
        aria-checked={system === UNIT_SYSTEM.METRIC}
        onClick={() => setSystem(UNIT_SYSTEM.METRIC)}
        className={`px-3 py-1 rounded-l-lg border ${
          system === UNIT_SYSTEM.METRIC
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600'
        }`}
      >
        Metric
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={system === UNIT_SYSTEM.IMPERIAL}
        onClick={() => setSystem(UNIT_SYSTEM.IMPERIAL)}
        className={`px-3 py-1 rounded-r-lg border-t border-r border-b ${
          system === UNIT_SYSTEM.IMPERIAL
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600'
        }`}
      >
        Imperial
      </button>
    </div>
  );
}

// =============================================================================
// TIMEZONE CONTEXT
// =============================================================================

interface TimezoneContextValue {
  timezone: string;
  setTimezone: (tz: string) => void;
  formatInTimezone: (date: Date | string, options?: Intl.DateTimeFormatOptions) => string;
  toLocalTime: (date: Date | string) => Date;
  toTimezone: (date: Date | string) => Date;
}

const TimezoneContext = createContext<TimezoneContextValue | null>(null);

interface TimezoneProviderProps {
  children: ReactNode;
  defaultTimezone?: string;
  storageKey?: string;
}

/**
 * Get local timezone
 */
export function getLocalTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * Timezone-aware provider
 */
export function TimezoneProvider({
  children,
  defaultTimezone,
  storageKey = 'timezone-preference',
}: TimezoneProviderProps): React.ReactElement {
  const localTz = getLocalTimezone();

  const [timezone, setTimezoneState] = useState<string>(() => {
    if (typeof localStorage === 'undefined') return defaultTimezone || localTz;
    const stored = localStorage.getItem(storageKey);
    return stored || defaultTimezone || localTz;
  });

  const setTimezone = useCallback((tz: string) => {
    setTimezoneState(tz);
    localStorage.setItem(storageKey, tz);
  }, [storageKey]);

  // Format date in specified timezone
  const formatInTimezone = useCallback((date: Date | string, options?: Intl.DateTimeFormatOptions): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat('en-US', {
      ...options,
      timeZone: timezone,
    }).format(d);
  }, [timezone]);

  // Convert to local time
  const toLocalTime = useCallback((date: Date | string): Date => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return new Date(d.toLocaleString('en-US', { timeZone: localTz }));
  }, [localTz]);

  // Convert to selected timezone
  const toTimezone = useCallback((date: Date | string): Date => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return new Date(d.toLocaleString('en-US', { timeZone: timezone }));
  }, [timezone]);

  const value = useMemo(() => ({
    timezone,
    setTimezone,
    formatInTimezone,
    toLocalTime,
    toTimezone,
  }), [timezone, setTimezone, formatInTimezone, toLocalTime, toTimezone]);

  return (
    <TimezoneContext.Provider value={value}>
      {children}
    </TimezoneContext.Provider>
  );
}

/**
 * Hook to access timezone context
 */
export function useTimezone(): TimezoneContextValue {
  const context = useContext(TimezoneContext);
  if (!context) {
    throw new Error('useTimezone must be used within TimezoneProvider');
  }
  return context;
}

// =============================================================================
// TIMEZONE SELECTOR
// =============================================================================

const COMMON_TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern Time (ET)', offset: 'UTC-5' },
  { value: 'America/Chicago', label: 'Central Time (CT)', offset: 'UTC-6' },
  { value: 'America/Denver', label: 'Mountain Time (MT)', offset: 'UTC-7' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)', offset: 'UTC-8' },
  { value: 'Europe/London', label: 'London (GMT)', offset: 'UTC+0' },
  { value: 'Europe/Paris', label: 'Paris (CET)', offset: 'UTC+1' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)', offset: 'UTC+1' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)', offset: 'UTC+9' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)', offset: 'UTC+8' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)', offset: 'UTC+4' },
  { value: 'Asia/Riyadh', label: 'Riyadh (AST)', offset: 'UTC+3' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)', offset: 'UTC+11' },
];

interface TimezoneSelectorProps {
  className?: string;
}

/**
 * Timezone selector
 */
export function TimezoneSelector({ className = '' }: TimezoneSelectorProps): React.ReactElement {
  const { timezone, setTimezone } = useTimezone();

  return (
    <select
      value={timezone}
      onChange={(e) => setTimezone(e.target.value)}
      aria-label="Select timezone"
      className={`px-3 py-2 border border-gray-300 rounded-lg bg-white dark:bg-gray-800 dark:border-gray-600 ${className}`}
    >
      {COMMON_TIMEZONES.map((tz) => (
        <option key={tz.value} value={tz.value}>
          {tz.label} ({tz.offset})
        </option>
      ))}
    </select>
  );
}

// =============================================================================
// SHARE BUTTON
// =============================================================================

interface ShareButtonProps {
  title?: string;
  text?: string;
  url?: string;
  onFallback?: () => void;
  className?: string;
  children?: ReactNode;
}

/**
 * Native share button with fallback
 */
export function ShareButton({
  title,
  text,
  url,
  onFallback,
  className = '',
  children,
}: ShareButtonProps): React.ReactElement {
  const [canUseShare] = useState(() => canShare());

  const handleShare = async () => {
    if (canUseShare) {
      const success = await nativeShare({ title, text, url });
      if (!success && onFallback) {
        onFallback();
      }
    } else if (onFallback) {
      onFallback();
    } else if (url) {
      // Fallback: copy to clipboard
      await navigator.clipboard.writeText(url);
    }
  };

  return (
    <button
      type="button"
      onClick={handleShare}
      aria-label="Share"
      className={`flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors ${className}`}
    >
      <span aria-hidden="true">📤</span>
      {children || 'Share'}
    </button>
  );
}

// =============================================================================
// BROWSER INFO HOOK
// =============================================================================

interface BrowserInfo {
  browser: BrowserType;
  os: OSType;
  isTouch: boolean;
  isMobile: boolean;
  cssFeatures: Record<CSSFeatureType, boolean>;
}

/**
 * Hook to get browser information
 */
export function useBrowserInfo(): BrowserInfo {
  const [info, setInfo] = useState<BrowserInfo>(() => ({
    browser: BROWSER.UNKNOWN,
    os: OS.UNKNOWN,
    isTouch: false,
    isMobile: false,
    cssFeatures: {
      [CSS_FEATURE.ASPECT_RATIO]: false,
      [CSS_FEATURE.GRID]: false,
      [CSS_FEATURE.FLEX]: false,
      [CSS_FEATURE.GAP]: false,
      [CSS_FEATURE.CONTAINER_QUERIES]: false,
      [CSS_FEATURE.SUBGRID]: false,
      [CSS_FEATURE.SCROLL_SNAP]: false,
    },
  }));

  useEffect(() => {
    setInfo({
      browser: detectBrowser(),
      os: detectOS(),
      isTouch: isTouchDevice(),
      isMobile: isMobileDevice(),
      cssFeatures: getCSSFeatureSupport(),
    });
  }, []);

  return info;
}

// =============================================================================
// RTL WRAPPER
// =============================================================================

interface RTLWrapperProps {
  children: ReactNode;
  className?: string;
}

/**
 * RTL-aware wrapper component
 */
export function RTLWrapper({ children, className = '' }: RTLWrapperProps): React.ReactElement {
  const { direction } = useI18n();

  return (
    <div dir={direction} className={`${direction === 'rtl' ? 'rtl' : 'ltr'} ${className}`}>
      {children}
    </div>
  );
}

/**
 * Design Tokens Context and Hooks
 * 
 * React integration for the design token system.
 */
'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import {
  tokens,
  lightTheme,
  darkTheme,
  generateThemeCSSVars,
  type ThemeColors,
  type DensityMode,
  type ComponentSize,
  type StatusType,
  type BadgeVariant,
  type ElevationLevel,
  type ColorScale,
  densityModes,
  componentSizes,
  statusColors,
  badgeVariants,
  elevations,
  darkElevations,
  spacing,
  radii,
  shadows,
  type SpacingToken,
  type RadiusToken,
  type ShadowToken,
} from './design-tokens';

// =============================================================================
// Types
// =============================================================================

export type ThemeMode = 'light' | 'dark' | 'system';

export interface DesignTokensContextValue {
  // Theme
  theme: 'light' | 'dark';
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  colors: ThemeColors;
  
  // Density
  density: DensityMode;
  setDensity: (density: DensityMode) => void;
  
  // Token accessors
  getSpacing: (key: SpacingToken) => string;
  getRadius: (key: RadiusToken) => string;
  getShadow: (key: ShadowToken) => string;
  getColor: (scale: keyof typeof tokens.colors, shade: keyof ColorScale) => string;
  getComponentSize: (size: ComponentSize) => typeof componentSizes[ComponentSize];
  getStatusColors: (status: StatusType) => typeof statusColors[StatusType];
  getBadgeVariant: (variant: BadgeVariant) => typeof badgeVariants[BadgeVariant];
  getElevation: (level: ElevationLevel) => { shadow: string; zIndex: number };
  getDensity: () => typeof densityModes[DensityMode];
  
  // Utilities
  cssVar: (name: string) => string;
  applyThemeVars: () => Record<string, string>;
}

// =============================================================================
// Context
// =============================================================================

const DesignTokensContext = createContext<DesignTokensContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

export interface DesignTokensProviderProps {
  children: React.ReactNode;
  defaultTheme?: ThemeMode;
  defaultDensity?: DensityMode;
  storageKey?: string;
}

export function DesignTokensProvider({
  children,
  defaultTheme = 'system',
  defaultDensity = 'comfortable',
  storageKey = 'sensei-theme',
}: DesignTokensProviderProps) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(defaultTheme);
  const [density, setDensityState] = useState<DensityMode>(defaultDensity);
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');
  
  // Load theme from storage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey);
      if (stored && ['light', 'dark', 'system'].includes(stored)) {
        setThemeModeState(stored as ThemeMode);
      }
      
      const storedDensity = localStorage.getItem(`${storageKey}-density`);
      if (storedDensity && ['comfortable', 'compact'].includes(storedDensity)) {
        setDensityState(storedDensity as DensityMode);
      }
    }
  }, [storageKey]);
  
  // Resolve system theme preference
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const resolveTheme = () => {
      if (themeMode === 'system') {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        setResolvedTheme(isDark ? 'dark' : 'light');
      } else {
        setResolvedTheme(themeMode);
      }
    };
    
    resolveTheme();
    
    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (themeMode === 'system') {
        resolveTheme();
      }
    };
    
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [themeMode]);
  
  // Apply theme to document
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const root = document.documentElement;
    
    // Remove previous theme classes
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);
    
    // Apply CSS variables
    const vars = generateThemeCSSVars(resolvedTheme);
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
    
    // Apply density variables
    const densityTokens = densityModes[density];
    root.style.setProperty('--row-height', densityTokens.rowHeight);
    root.style.setProperty('--cell-padding', densityTokens.cellPadding);
    root.style.setProperty('--gap', densityTokens.gap);
  }, [resolvedTheme, density]);
  
  const setThemeMode = useCallback((mode: ThemeMode) => {
    setThemeModeState(mode);
    if (typeof window !== 'undefined') {
      localStorage.setItem(storageKey, mode);
    }
  }, [storageKey]);
  
  const toggleTheme = useCallback(() => {
    const newTheme = resolvedTheme === 'light' ? 'dark' : 'light';
    setThemeMode(newTheme);
  }, [resolvedTheme, setThemeMode]);
  
  const setDensity = useCallback((newDensity: DensityMode) => {
    setDensityState(newDensity);
    if (typeof window !== 'undefined') {
      localStorage.setItem(`${storageKey}-density`, newDensity);
    }
  }, [storageKey]);
  
  // Token accessors
  const getSpacing = useCallback((key: SpacingToken) => spacing[key], []);
  const getRadius = useCallback((key: RadiusToken) => radii[key], []);
  const getShadow = useCallback((key: ShadowToken) => shadows[key], []);
  
  const getColor = useCallback((scale: keyof typeof tokens.colors, shade: keyof ColorScale) => {
    return tokens.colors[scale][shade];
  }, []);
  
  const getComponentSize = useCallback((size: ComponentSize) => {
    return componentSizes[size];
  }, []);
  
  const getStatusColors = useCallback((status: StatusType) => {
    return statusColors[status];
  }, []);
  
  const getBadgeVariant = useCallback((variant: BadgeVariant) => {
    return badgeVariants[variant];
  }, []);
  
  const getElevation = useCallback((level: ElevationLevel) => {
    return resolvedTheme === 'light' ? elevations[level] : darkElevations[level];
  }, [resolvedTheme]);
  
  const getDensity = useCallback(() => {
    return densityModes[density];
  }, [density]);
  
  const cssVar = useCallback((name: string) => {
    return `var(--${name})`;
  }, []);
  
  const applyThemeVars = useCallback(() => {
    return generateThemeCSSVars(resolvedTheme);
  }, [resolvedTheme]);
  
  const colors = useMemo(() => {
    return resolvedTheme === 'light' ? lightTheme : darkTheme;
  }, [resolvedTheme]);
  
  const value: DesignTokensContextValue = useMemo(() => ({
    theme: resolvedTheme,
    themeMode,
    setThemeMode,
    toggleTheme,
    colors,
    density,
    setDensity,
    getSpacing,
    getRadius,
    getShadow,
    getColor,
    getComponentSize,
    getStatusColors,
    getBadgeVariant,
    getElevation,
    getDensity,
    cssVar,
    applyThemeVars,
  }), [
    resolvedTheme,
    themeMode,
    setThemeMode,
    toggleTheme,
    colors,
    density,
    setDensity,
    getSpacing,
    getRadius,
    getShadow,
    getColor,
    getComponentSize,
    getStatusColors,
    getBadgeVariant,
    getElevation,
    getDensity,
    cssVar,
    applyThemeVars,
  ]);
  
  return (
    <DesignTokensContext.Provider value={value}>
      {children}
    </DesignTokensContext.Provider>
  );
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Main hook to access the design tokens system
 */
export function useDesignTokens(): DesignTokensContextValue {
  const context = useContext(DesignTokensContext);
  if (!context) {
    throw new Error('useDesignTokens must be used within a DesignTokensProvider');
  }
  return context;
}

/**
 * Hook for theme management
 */
export function useTheme() {
  const { theme, themeMode, setThemeMode, toggleTheme, colors } = useDesignTokens();
  return { theme, themeMode, setThemeMode, toggleTheme, colors };
}

/**
 * Hook for density mode
 */
export function useDensity() {
  const { density, setDensity, getDensity } = useDesignTokens();
  return { density, setDensity, getDensity };
}

/**
 * Hook to get spacing values
 */
export function useSpacing() {
  const { getSpacing } = useDesignTokens();
  return getSpacing;
}

/**
 * Hook to get radius values
 */
export function useRadius() {
  const { getRadius } = useDesignTokens();
  return getRadius;
}

/**
 * Hook to get shadow values
 */
export function useShadow() {
  const { getShadow } = useDesignTokens();
  return getShadow;
}

/**
 * Hook to get color values
 */
export function useColors() {
  const { getColor, colors } = useDesignTokens();
  return { getColor, themeColors: colors };
}

/**
 * Hook for component sizes
 */
export function useComponentSizes() {
  const { getComponentSize } = useDesignTokens();
  return getComponentSize;
}

/**
 * Hook for status colors
 */
export function useStatusColors() {
  const { getStatusColors } = useDesignTokens();
  return getStatusColors;
}

/**
 * Hook for badge variants
 */
export function useBadgeVariants() {
  const { getBadgeVariant } = useDesignTokens();
  return getBadgeVariant;
}

/**
 * Hook for elevation
 */
export function useElevation() {
  const { getElevation } = useDesignTokens();
  return getElevation;
}

/**
 * Hook for CSS variable reference
 */
export function useCssVar() {
  const { cssVar } = useDesignTokens();
  return cssVar;
}

// =============================================================================
// Standalone theme detection (for SSR/initial load)
// =============================================================================

/**
 * Get initial theme from storage or system preference
 * Can be used in server components or initial HTML
 */
export function getInitialTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') {
    return 'light';
  }
  
  const stored = localStorage.getItem('sensei-theme');
  if (stored === 'light' || stored === 'dark') {
    return stored;
  }
  
  if (stored === 'system' || !stored) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  
  return 'light';
}

/**
 * Theme script to prevent flash of unstyled content (FOUC)
 * Include this in the HTML head
 */
export const themeScript = `
(function() {
  try {
    var stored = localStorage.getItem('sensei-theme');
    var theme = stored;
    if (stored === 'system' || !stored) {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.classList.add(theme);
  } catch (e) {}
})();
`;

// =============================================================================
// Utility Components
// =============================================================================

export interface ThemeToggleProps {
  className?: string;
}

/**
 * Simple theme toggle button component
 */
export function ThemeToggle({ className }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <button
      onClick={toggleTheme}
      className={className}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      )}
    </button>
  );
}

export interface DensityToggleProps {
  className?: string;
}

/**
 * Simple density toggle component
 */
export function DensityToggle({ className }: DensityToggleProps) {
  const { density, setDensity } = useDensity();
  
  return (
    <button
      onClick={() => setDensity(density === 'comfortable' ? 'compact' : 'comfortable')}
      className={className}
      aria-label={`Switch to ${density === 'comfortable' ? 'compact' : 'comfortable'} density`}
    >
      {density === 'comfortable' ? (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      )}
    </button>
  );
}

// =============================================================================
// Default Export
// =============================================================================

export default DesignTokensProvider;

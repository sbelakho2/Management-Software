'use client';

import React, { createContext, useContext, useMemo, useCallback, useEffect, useState } from 'react';
import { useI18n } from '@/contexts/i18n-context';

// =============================================================================
// DESIGN TOKEN CONSTANTS
// =============================================================================

/**
 * Core color tokens - must be defined in CSS variables
 */
export const COLOR_TOKENS = {
  // Semantic colors
  background: '--background',
  foreground: '--foreground',
  card: '--card',
  'card-foreground': '--card-foreground',
  popover: '--popover',
  'popover-foreground': '--popover-foreground',
  primary: '--primary',
  'primary-foreground': '--primary-foreground',
  secondary: '--secondary',
  'secondary-foreground': '--secondary-foreground',
  muted: '--muted',
  'muted-foreground': '--muted-foreground',
  accent: '--accent',
  'accent-foreground': '--accent-foreground',
  destructive: '--destructive',
  'destructive-foreground': '--destructive-foreground',
  border: '--border',
  input: '--input',
  ring: '--ring',
  // Status colors
  success: '--success',
  'success-foreground': '--success-foreground',
  warning: '--warning',
  'warning-foreground': '--warning-foreground',
  danger: '--danger',
  'danger-foreground': '--danger-foreground',
} as const;

export type ColorToken = keyof typeof COLOR_TOKENS;

/**
 * Spacing tokens - Tailwind-compatible scale
 */
export const SPACING_TOKENS = {
  px: '1px',
  0: '0px',
  0.5: '0.125rem',
  1: '0.25rem',
  1.5: '0.375rem',
  2: '0.5rem',
  2.5: '0.625rem',
  3: '0.75rem',
  3.5: '0.875rem',
  4: '1rem',
  4.5: '1.125rem',
  5: '1.25rem',
  5.5: '1.375rem',
  6: '1.5rem',
  7: '1.75rem',
  8: '2rem',
  9: '2.25rem',
  10: '2.5rem',
  11: '2.75rem',
  12: '3rem',
  14: '3.5rem',
  16: '4rem',
  18: '4.5rem',
  20: '5rem',
  22: '5.5rem',
  24: '6rem',
  28: '7rem',
  32: '8rem',
  36: '9rem',
  40: '10rem',
  44: '11rem',
  48: '12rem',
  52: '13rem',
  56: '14rem',
  60: '15rem',
  64: '16rem',
  72: '18rem',
  80: '20rem',
  96: '24rem',
} as const;

export type SpacingToken = keyof typeof SPACING_TOKENS;

/**
 * Typography tokens
 */
export const TYPOGRAPHY_TOKENS = {
  fontFamily: {
    sans: 'var(--font-sans), system-ui, sans-serif',
    mono: 'var(--font-mono), monospace',
  },
  fontSize: {
    '2xs': '0.625rem',
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
    '5xl': '3rem',
    '6xl': '3.75rem',
    '7xl': '4.5rem',
    '8xl': '6rem',
    '9xl': '8rem',
  },
  fontWeight: {
    thin: '100',
    extralight: '200',
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
    black: '900',
  },
  lineHeight: {
    none: '1',
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '2',
  },
} as const;

export type FontSizeToken = keyof typeof TYPOGRAPHY_TOKENS.fontSize;
export type FontWeightToken = keyof typeof TYPOGRAPHY_TOKENS.fontWeight;
export type LineHeightToken = keyof typeof TYPOGRAPHY_TOKENS.lineHeight;

/**
 * Border radius tokens
 */
export const RADIUS_TOKENS = {
  none: '0px',
  sm: 'calc(var(--radius) - 4px)',
  md: 'calc(var(--radius) - 2px)',
  lg: 'var(--radius)',
  xl: 'calc(var(--radius) + 4px)',
  '2xl': 'calc(var(--radius) + 8px)',
  '3xl': '1.5rem',
  full: '9999px',
} as const;

export type RadiusToken = keyof typeof RADIUS_TOKENS;

/**
 * Shadow tokens
 */
export const SHADOW_TOKENS = {
  'elevation-1': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  'elevation-2': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  'elevation-3': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  none: '0 0 #0000',
} as const;

export type ShadowToken = keyof typeof SHADOW_TOKENS;

/**
 * Animation tokens
 */
export const ANIMATION_TOKENS = {
  duration: {
    fast: '100ms',
    normal: '200ms',
    slow: '300ms',
    slower: '500ms',
  },
  easing: {
    linear: 'linear',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const;

export type DurationToken = keyof typeof ANIMATION_TOKENS.duration;
export type EasingToken = keyof typeof ANIMATION_TOKENS.easing;

/**
 * Breakpoint tokens
 */
export const BREAKPOINT_TOKENS = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

export type BreakpointToken = keyof typeof BREAKPOINT_TOKENS;

// =============================================================================
// TOKEN VALIDATION
// =============================================================================

export interface TokenValidationResult {
  token: string;
  cssVariable: string;
  isValid: boolean;
  value: string | null;
  error?: string;
}

export interface TokenAuditReport {
  timestamp: Date;
  totalTokens: number;
  validTokens: number;
  invalidTokens: number;
  missingTokens: string[];
  results: TokenValidationResult[];
}

/**
 * Validates that a CSS variable is defined and has a value
 */
export function validateCssVariable(variableName: string): TokenValidationResult {
  if (typeof window === 'undefined') {
    return {
      token: variableName,
      cssVariable: variableName,
      isValid: false,
      value: null,
      error: 'Cannot validate CSS variables on server',
    };
  }

  const computedStyle = getComputedStyle(document.documentElement);
  const value = computedStyle.getPropertyValue(variableName).trim();

  return {
    token: variableName,
    cssVariable: variableName,
    isValid: value !== '',
    value: value || null,
    error: value === '' ? `CSS variable ${variableName} is not defined` : undefined,
  };
}

/**
 * Validates all color tokens and returns an audit report
 */
export function auditColorTokens(): TokenAuditReport {
  const results: TokenValidationResult[] = [];
  const missingTokens: string[] = [];

  Object.entries(COLOR_TOKENS).forEach(([name, variable]) => {
    const result = validateCssVariable(variable);
    result.token = name;
    results.push(result);
    if (!result.isValid) {
      missingTokens.push(name);
    }
  });

  return {
    timestamp: new Date(),
    totalTokens: results.length,
    validTokens: results.filter((r) => r.isValid).length,
    invalidTokens: results.filter((r) => !r.isValid).length,
    missingTokens,
    results,
  };
}

/**
 * Gets the computed value of a design token
 */
export function getTokenValue(token: ColorToken): string | null {
  const variable = COLOR_TOKENS[token];
  if (typeof window === 'undefined') {
    return null;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  return value || null;
}

// =============================================================================
// DESIGN SYSTEM CONTEXT
// =============================================================================

export type ThemeMode = 'light' | 'dark' | 'system';

export interface DesignSystemContextValue {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  resolvedTheme: 'light' | 'dark';
  tokens: {
    colors: typeof COLOR_TOKENS;
    spacing: typeof SPACING_TOKENS;
    typography: typeof TYPOGRAPHY_TOKENS;
    radius: typeof RADIUS_TOKENS;
    shadows: typeof SHADOW_TOKENS;
    animations: typeof ANIMATION_TOKENS;
    breakpoints: typeof BREAKPOINT_TOKENS;
  };
  getTokenValue: (token: ColorToken) => string | null;
  auditTokens: () => TokenAuditReport;
}

const DesignSystemContext = createContext<DesignSystemContextValue | null>(null);

export interface DesignSystemProviderProps {
  children: React.ReactNode;
  defaultTheme?: ThemeMode;
  storageKey?: string;
}

export function DesignSystemProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'sensei-theme',
}: DesignSystemProviderProps) {
  const [theme, setThemeState] = useState<ThemeMode>(defaultTheme);
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');

  // Initialize theme from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey);
      if (stored && ['light', 'dark', 'system'].includes(stored)) {
        setThemeState(stored as ThemeMode);
      }
    }
  }, [storageKey]);

  // Resolve system theme
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const resolveTheme = () => {
      if (theme === 'system') {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        setResolvedTheme(mediaQuery.matches ? 'dark' : 'light');
      } else {
        setResolvedTheme(theme);
      }
    };

    resolveTheme();

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'system') {
        setResolvedTheme(mediaQuery.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme]);

  // Apply theme class to document
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);
  }, [resolvedTheme]);

  const setTheme = useCallback(
    (newTheme: ThemeMode) => {
      setThemeState(newTheme);
      if (typeof window !== 'undefined') {
        localStorage.setItem(storageKey, newTheme);
      }
    },
    [storageKey]
  );

  const value = useMemo<DesignSystemContextValue>(
    () => ({
      theme,
      setTheme,
      resolvedTheme,
      tokens: {
        colors: COLOR_TOKENS,
        spacing: SPACING_TOKENS,
        typography: TYPOGRAPHY_TOKENS,
        radius: RADIUS_TOKENS,
        shadows: SHADOW_TOKENS,
        animations: ANIMATION_TOKENS,
        breakpoints: BREAKPOINT_TOKENS,
      },
      getTokenValue,
      auditTokens: auditColorTokens,
    }),
    [theme, setTheme, resolvedTheme]
  );

  return <DesignSystemContext.Provider value={value}>{children}</DesignSystemContext.Provider>;
}

export function useDesignSystem(): DesignSystemContextValue {
  const context = useContext(DesignSystemContext);
  if (!context) {
    throw new Error('useDesignSystem must be used within a DesignSystemProvider');
  }
  return context;
}

// =============================================================================
// COMPONENT AUDIT UTILITIES
// =============================================================================

export interface ComponentAuditItem {
  name: string;
  path: string;
  category: 'primitive' | 'composite' | 'layout' | 'feedback' | 'navigation' | 'data-display' | 'form';
  hasTokens: boolean;
  hasAccessibility: boolean;
  hasResponsive: boolean;
  hasAnimation: boolean;
  issues: string[];
}

export interface ComponentAuditReport {
  timestamp: Date;
  totalComponents: number;
  passingComponents: number;
  failingComponents: number;
  components: ComponentAuditItem[];
}

/**
 * Creates a component audit item for tracking design system compliance
 */
export function createComponentAudit(config: Omit<ComponentAuditItem, 'issues'>): ComponentAuditItem {
  const issues: string[] = [];

  if (!config.hasTokens) {
    issues.push('Component does not use design tokens for styling');
  }
  if (!config.hasAccessibility) {
    issues.push('Component lacks proper accessibility attributes');
  }
  if (!config.hasResponsive) {
    issues.push('Component does not have responsive design');
  }

  return {
    ...config,
    issues,
  };
}

// =============================================================================
// TOKEN DISPLAY COMPONENTS
// =============================================================================

export interface ColorSwatchProps {
  token: ColorToken;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ColorSwatch({ token, showValue = false, size = 'md', className = '' }: ColorSwatchProps) {
  const [value, setValue] = useState<string | null>(null);
  const variable = COLOR_TOKENS[token];

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const computed = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
      setValue(computed || null);
    }
  }, [variable]);

  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className={`${sizeClasses[size]} rounded-md border border-border`}
        style={{ backgroundColor: `hsl(var(${variable}))` }}
        role="img"
        aria-label={`Color swatch for ${token}`}
      />
      <div className="flex flex-col">
        <span className="text-sm font-medium">{token}</span>
        {showValue && value && <span className="text-xs text-muted-foreground">{value}</span>}
      </div>
    </div>
  );
}

export interface SpacingScaleProps {
  tokens?: SpacingToken[];
  direction?: 'horizontal' | 'vertical';
  className?: string;
}

export function SpacingScale({
  tokens = [1, 2, 4, 8, 16, 32],
  direction = 'horizontal',
  className = '',
}: SpacingScaleProps) {
  const isHorizontal = direction === 'horizontal';

  return (
    <div className={`flex ${isHorizontal ? 'flex-row items-end' : 'flex-col'} gap-2 ${className}`}>
      {tokens.map((token) => (
        <div key={token} className="flex flex-col items-center gap-1">
          <div
            className={`bg-primary ${isHorizontal ? 'w-4' : 'h-4'}`}
            style={{
              [isHorizontal ? 'height' : 'width']: SPACING_TOKENS[token],
            }}
            role="img"
            aria-label={`Spacing ${token}: ${SPACING_TOKENS[token]}`}
          />
          <span className="text-xs text-muted-foreground">{token}</span>
        </div>
      ))}
    </div>
  );
}

export interface TypographyScaleProps {
  sizes?: FontSizeToken[];
  sampleText?: string;
  className?: string;
}

export function TypographyScale({
  sizes = ['2xs', 'xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl'],
  sampleText = 'Aa',
  className = '',
}: TypographyScaleProps) {
  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {sizes.map((size) => (
        <div key={size} className="flex items-baseline gap-4">
          <span className="w-12 text-sm text-muted-foreground">{size}</span>
          <span
            style={{ fontSize: TYPOGRAPHY_TOKENS.fontSize[size] }}
            className="font-medium"
          >
            {sampleText}
          </span>
          <span className="text-xs text-muted-foreground">{TYPOGRAPHY_TOKENS.fontSize[size]}</span>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// DESIGN SYSTEM DOCUMENTATION
// =============================================================================

export interface TokenDocumentationProps {
  category: 'colors' | 'spacing' | 'typography' | 'radius' | 'shadows' | 'animations';
  className?: string;
}

export function TokenDocumentation({ category, className = '' }: TokenDocumentationProps) {
  const { t } = useI18n();
  const renderColors = () => (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {(Object.keys(COLOR_TOKENS) as ColorToken[]).map((token) => (
        <ColorSwatch key={token} token={token} showValue size="md" />
      ))}
    </div>
  );

  const renderSpacing = () => (
    <div className="space-y-8">
      <div>
        <h4 className="text-sm font-medium mb-4">{t('components.designSystem.horizontalScale')}</h4>
        <SpacingScale direction="horizontal" />
      </div>
      <div>
        <h4 className="text-sm font-medium mb-4">{t('components.designSystem.verticalScale')}</h4>
        <SpacingScale direction="vertical" />
      </div>
    </div>
  );

  const renderTypography = () => (
    <div className="space-y-8">
      <div>
        <h4 className="text-sm font-medium mb-4">{t('components.designSystem.fontSizes')}</h4>
        <TypographyScale />
      </div>
      <div>
        <h4 className="text-sm font-medium mb-4">{t('components.designSystem.fontWeights')}</h4>
        <div className="flex flex-wrap gap-4">
          {(Object.entries(TYPOGRAPHY_TOKENS.fontWeight) as [FontWeightToken, string][]).map(
            ([weight, value]) => (
              <div key={weight} className="text-center">
                <span style={{ fontWeight: value }} className="text-lg">
                  Aa
                </span>
                <p className="text-xs text-muted-foreground">{weight}</p>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );

  const renderRadius = () => (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {(Object.entries(RADIUS_TOKENS) as [RadiusToken, string][]).map(([name, value]) => (
        <div key={name} className="flex flex-col items-center gap-2">
          <div
            className="w-16 h-16 bg-primary"
            style={{ borderRadius: value }}
            role="img"
            aria-label={`Border radius ${name}`}
          />
          <span className="text-sm font-medium">{name}</span>
          <span className="text-xs text-muted-foreground">{value}</span>
        </div>
      ))}
    </div>
  );

  const renderShadows = () => (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
      {(Object.entries(SHADOW_TOKENS) as [ShadowToken, string][]).map(([name, value]) => (
        <div key={name} className="flex flex-col items-center gap-2">
          <div
            className="w-20 h-20 bg-card rounded-lg"
            style={{ boxShadow: value }}
            role="img"
            aria-label={`Shadow ${name}`}
          />
          <span className="text-sm font-medium">{name}</span>
        </div>
      ))}
    </div>
  );

  const renderAnimations = () => (
    <div className="space-y-8">
      <div>
        <h4 className="text-sm font-medium mb-4">Durations</h4>
        <div className="flex flex-wrap gap-4">
          {(Object.entries(ANIMATION_TOKENS.duration) as [DurationToken, string][]).map(
            ([name, value]) => (
              <div key={name} className="text-center px-4 py-2 bg-muted rounded">
                <span className="text-sm font-medium">{name}</span>
                <p className="text-xs text-muted-foreground">{value}</p>
              </div>
            )
          )}
        </div>
      </div>
      <div>
        <h4 className="text-sm font-medium mb-4">Easings</h4>
        <div className="flex flex-wrap gap-4">
          {(Object.entries(ANIMATION_TOKENS.easing) as [EasingToken, string][]).map(([name, value]) => (
            <div key={name} className="text-center px-4 py-2 bg-muted rounded">
              <span className="text-sm font-medium">{name}</span>
              <p className="text-xs text-muted-foreground truncate max-w-32">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const content = {
    colors: renderColors,
    spacing: renderSpacing,
    typography: renderTypography,
    radius: renderRadius,
    shadows: renderShadows,
    animations: renderAnimations,
  };

  return (
    <div className={className}>
      <h3 className="text-lg font-semibold mb-4 capitalize">{category}</h3>
      {content[category]()}
    </div>
  );
}

// =============================================================================
// VISUAL CONSISTENCY UTILITIES
// =============================================================================

export interface VisualWeight {
  padding: SpacingToken;
  fontSize: FontSizeToken;
  fontWeight: FontWeightToken;
  borderRadius: RadiusToken;
  shadow: ShadowToken;
}

/**
 * Predefined visual weight configurations for consistent component styling
 */
export const VISUAL_WEIGHTS: Record<'small' | 'medium' | 'large', VisualWeight> = {
  small: {
    padding: 2,
    fontSize: 'sm',
    fontWeight: 'medium',
    borderRadius: 'sm',
    shadow: 'sm',
  },
  medium: {
    padding: 4,
    fontSize: 'base',
    fontWeight: 'medium',
    borderRadius: 'md',
    shadow: 'DEFAULT',
  },
  large: {
    padding: 6,
    fontSize: 'lg',
    fontWeight: 'semibold',
    borderRadius: 'lg',
    shadow: 'md',
  },
};

/**
 * Hook to get consistent visual weight styling
 */
export function useVisualWeight(size: 'small' | 'medium' | 'large'): VisualWeight {
  return VISUAL_WEIGHTS[size];
}

// =============================================================================
// INTERACTION PATTERNS
// =============================================================================

export const INTERACTION_PATTERNS = {
  button: {
    hover: 'hover:opacity-90',
    active: 'active:scale-[0.98]',
    focus: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    disabled: 'disabled:opacity-50 disabled:pointer-events-none',
    transition: 'transition-all duration-200',
  },
  input: {
    hover: 'hover:border-primary/50',
    focus: 'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
    disabled: 'disabled:opacity-50 disabled:cursor-not-allowed',
    error: 'border-destructive focus:ring-destructive',
    transition: 'transition-colors duration-200',
  },
  card: {
    hover: 'hover:shadow-elevation-2',
    active: 'active:shadow-elevation-1',
    focus: 'focus-within:ring-2 focus-within:ring-ring',
    transition: 'transition-shadow duration-200',
  },
  link: {
    hover: 'hover:underline',
    focus: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:rounded',
    active: 'active:opacity-80',
    transition: 'transition-opacity duration-100',
  },
} as const;

export type InteractionPattern = keyof typeof INTERACTION_PATTERNS;

/**
 * Builds a className string from interaction patterns
 */
export function buildInteractionClasses(
  pattern: InteractionPattern,
  options: { hover?: boolean; active?: boolean; focus?: boolean; disabled?: boolean; transition?: boolean } = {}
): string {
  const { hover = true, active = true, focus = true, disabled = true, transition = true } = options;
  const patternDef = INTERACTION_PATTERNS[pattern];
  const classes: string[] = [];

  if (hover && patternDef.hover) classes.push(patternDef.hover);
  if (active && 'active' in patternDef) classes.push((patternDef as any).active);
  if (focus && patternDef.focus) classes.push(patternDef.focus);
  if (disabled && 'disabled' in patternDef) classes.push(patternDef.disabled);
  if (transition && patternDef.transition) classes.push(patternDef.transition);

  return classes.join(' ');
}

// =============================================================================
// DESIGN AUDIT PANEL
// =============================================================================

export interface DesignAuditPanelProps {
  className?: string;
}

export function DesignAuditPanel({ className = '' }: DesignAuditPanelProps) {
  const { t } = useI18n();
  const [report, setReport] = useState<TokenAuditReport | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const runAudit = useCallback(() => {
    const auditReport = auditColorTokens();
    setReport(auditReport);
  }, []);

  useEffect(() => {
    if (isOpen && !report) {
      runAudit();
    }
  }, [isOpen, report, runAudit]);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-4 right-4 z-50 px-4 py-2 bg-primary text-primary-foreground rounded-lg shadow-lg hover:opacity-90 transition-opacity ${className}`}
        aria-label={t('components.designSystem.openAuditPanel')}
      >
        🎨 Audit
      </button>
    );
  }

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 w-96 max-h-[80vh] bg-card border border-border rounded-lg shadow-xl overflow-hidden ${className}`}
      role="dialog"
      aria-label={t('components.designSystem.auditPanelTitle')}
    >
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h2 className="text-lg font-semibold">{t('components.designSystem.designSystemAudit')}</h2>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1 hover:bg-muted rounded"
          aria-label={t('components.designSystem.closeAuditPanel')}
        >
          ✕
        </button>
      </div>

      <div className="p-4 overflow-y-auto max-h-[60vh]">
        {report ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-center">
              <div className="p-2 bg-muted rounded">
                <div className="text-2xl font-bold">{report.totalTokens}</div>
                <div className="text-xs text-muted-foreground">Total</div>
              </div>
              <div className="p-2 bg-success/10 rounded">
                <div className="text-2xl font-bold text-success">{report.validTokens}</div>
                <div className="text-xs text-muted-foreground">Valid</div>
              </div>
              <div className="p-2 bg-destructive/10 rounded">
                <div className="text-2xl font-bold text-destructive">{report.invalidTokens}</div>
                <div className="text-xs text-muted-foreground">Invalid</div>
              </div>
            </div>

            {report.missingTokens.length > 0 && (
              <div className="p-3 bg-destructive/10 rounded">
                <h4 className="text-sm font-medium text-destructive mb-2">{t('components.designSystem.missingTokens')}</h4>
                <ul className="text-xs space-y-1">
                  {report.missingTokens.map((token) => (
                    <li key={token} className="text-muted-foreground">
                      • {token}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <h4 className="text-sm font-medium mb-2">{t('components.designSystem.tokenStatus')}</h4>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {report.results.map((result) => (
                  <div
                    key={result.token}
                    className="flex items-center justify-between text-xs p-1 rounded hover:bg-muted"
                  >
                    <span>{result.token}</span>
                    <span className={result.isValid ? 'text-success' : 'text-destructive'}>
                      {result.isValid ? '✓' : '✗'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">{t('components.designSystem.loadingAudit')}</div>
        )}
      </div>

      <div className="p-4 border-t border-border">
        <button
          onClick={runAudit}
          className="w-full px-4 py-2 bg-primary text-primary-foreground rounded hover:opacity-90 transition-opacity"
        >
          {t('components.designSystem.reRunAudit')}
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// CLS (CUMULATIVE LAYOUT SHIFT) UTILITIES
// =============================================================================

export interface CLSEntry {
  value: number;
  timestamp: number;
  sources: Array<{
    node?: Node;
    previousRect?: DOMRect;
    currentRect?: DOMRect;
  }>;
}

export interface CLSReport {
  totalCLS: number;
  entries: CLSEntry[];
  isGood: boolean;
  isNeedsImprovement: boolean;
  isPoor: boolean;
  recommendation: string;
}

/**
 * CLS threshold values based on Web Vitals
 * Good: < 0.1
 * Needs Improvement: 0.1 - 0.25
 * Poor: > 0.25
 */
export const CLS_THRESHOLDS = {
  good: 0.1,
  needsImprovement: 0.25,
} as const;

/**
 * Observes and reports Cumulative Layout Shift
 */
export function observeCLS(callback: (report: CLSReport) => void): (() => void) | null {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return null;
  }

  const entries: CLSEntry[] = [];
  let totalCLS = 0;

  const generateReport = (): CLSReport => {
    const isGood = totalCLS < CLS_THRESHOLDS.good;
    const isPoor = totalCLS > CLS_THRESHOLDS.needsImprovement;
    const isNeedsImprovement = !isGood && !isPoor;

    let recommendation = '';
    if (isGood) {
      recommendation = 'CLS is excellent. No action needed.';
    } else if (isNeedsImprovement) {
      recommendation = 'CLS could be improved. Consider adding size attributes to images and embeds.';
    } else {
      recommendation = 'CLS is poor. Investigate layout-shifting elements and add explicit dimensions.';
    }

    return {
      totalCLS,
      entries,
      isGood,
      isNeedsImprovement,
      isPoor,
      recommendation,
    };
  };

  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        // Only count entries without recent user input
        const layoutShift = entry as PerformanceEntry & {
          hadRecentInput?: boolean;
          value?: number;
          sources?: Array<{ node?: Node; previousRect?: DOMRect; currentRect?: DOMRect }>;
        };
        
        if (!layoutShift.hadRecentInput && typeof layoutShift.value === 'number') {
          totalCLS += layoutShift.value;
          entries.push({
            value: layoutShift.value,
            timestamp: entry.startTime,
            sources: layoutShift.sources || [],
          });
          callback(generateReport());
        }
      }
    });

    observer.observe({ type: 'layout-shift', buffered: true });

    return () => {
      observer.disconnect();
    };
  } catch {
    // PerformanceObserver for layout-shift not supported
    return null;
  }
}

/**
 * Hook to monitor CLS in a component
 */
export function useCLSMonitor(): CLSReport | null {
  const [report, setReport] = useState<CLSReport | null>(null);

  useEffect(() => {
    const cleanup = observeCLS(setReport);
    return () => {
      cleanup?.();
    };
  }, []);

  return report;
}

// =============================================================================
// CLS INDICATOR COMPONENT
// =============================================================================

export interface CLSIndicatorProps {
  threshold?: number;
  showDetails?: boolean;
  className?: string;
}

export function CLSIndicator({
  threshold = CLS_THRESHOLDS.good,
  showDetails = false,
  className = '',
}: CLSIndicatorProps) {
  const report = useCLSMonitor();

  if (!report) {
    return null;
  }

  const statusColor = report.isGood
    ? 'bg-success text-success-foreground'
    : report.isNeedsImprovement
      ? 'bg-warning text-warning-foreground'
      : 'bg-destructive text-destructive-foreground';

  const statusIcon = report.isGood ? '✓' : report.isNeedsImprovement ? '!' : '✗';

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${statusColor}`}
        role="status"
        aria-label={`Cumulative Layout Shift: ${report.totalCLS.toFixed(4)}`}
      >
        <span>{statusIcon}</span>
        <span>CLS: {report.totalCLS.toFixed(4)}</span>
      </div>

      {showDetails && (
        <div className="text-xs text-muted-foreground">
          Threshold: {threshold} | Shifts: {report.entries.length}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// VISUAL REGRESSION UTILITIES
// =============================================================================

export interface VisualSnapshotConfig {
  name: string;
  selector?: string;
  viewport?: { width: number; height: number };
  theme?: 'light' | 'dark';
  animations?: 'disabled' | 'enabled';
}

export interface GoldStandardState {
  name: string;
  description: string;
  route: string;
  config: VisualSnapshotConfig;
}

/**
 * Predefined gold standard UI states for visual regression testing
 */
export const GOLD_STANDARD_STATES: GoldStandardState[] = [
  {
    name: 'dashboard-default',
    description: 'Main dashboard in default state',
    route: '/',
    config: { name: 'dashboard-default', viewport: { width: 1280, height: 720 } },
  },
  {
    name: 'dashboard-mobile',
    description: 'Main dashboard on mobile viewport',
    route: '/',
    config: { name: 'dashboard-mobile', viewport: { width: 375, height: 667 } },
  },
  {
    name: 'dashboard-dark',
    description: 'Main dashboard in dark mode',
    route: '/',
    config: { name: 'dashboard-dark', theme: 'dark', viewport: { width: 1280, height: 720 } },
  },
  {
    name: 'pipeline-view',
    description: 'Pipeline/Kanban view',
    route: '/pipeline',
    config: { name: 'pipeline-view', viewport: { width: 1280, height: 720 } },
  },
  {
    name: 'rfq-detail',
    description: 'RFQ detail page',
    route: '/rfq/1',
    config: { name: 'rfq-detail', viewport: { width: 1280, height: 720 } },
  },
];

/**
 * Generates Playwright visual snapshot test code for a gold standard state
 */
export function generateVisualSnapshotTest(state: GoldStandardState): string {
  const { name, route, config } = state;
  const { viewport, theme, animations } = config;

  let testCode = `test('${name} visual regression', async ({ page }) => {\n`;
  
  if (viewport) {
    testCode += `  await page.setViewportSize({ width: ${viewport.width}, height: ${viewport.height} });\n`;
  }
  
  if (theme) {
    testCode += `  await page.emulateMedia({ colorScheme: '${theme}' });\n`;
  }
  
  if (animations === 'disabled') {
    testCode += `  await page.addStyleTag({ content: '*, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }' });\n`;
  }
  
  testCode += `  await page.goto('${route}');\n`;
  testCode += `  await page.waitForLoadState('networkidle');\n`;
  
  if (config.selector) {
    testCode += `  const element = page.locator('${config.selector}');\n`;
    testCode += `  await expect(element).toHaveScreenshot('${name}.png');\n`;
  } else {
    testCode += `  await expect(page).toHaveScreenshot('${name}.png');\n`;
  }
  
  testCode += `});\n`;
  
  return testCode;
}

/**
 * Exports all gold standard states as Playwright test file content
 */
export function generateVisualRegressionTestFile(): string {
  let fileContent = `import { test, expect } from '@playwright/test';

/**
 * Visual Regression Tests for Gold Standard UI States
 * Auto-generated from design system configuration
 */

`;

  GOLD_STANDARD_STATES.forEach((state) => {
    fileContent += `// ${state.description}\n`;
    fileContent += generateVisualSnapshotTest(state);
    fileContent += '\n';
  });

  return fileContent;
}

// =============================================================================
// DESIGN CONSISTENCY CHECKER
// =============================================================================

export interface ConsistencyIssue {
  type: 'hardcoded-color' | 'non-token-spacing' | 'inline-style' | 'missing-semantic';
  element?: string;
  property?: string;
  value?: string;
  suggestion: string;
}

/**
 * Checks for design consistency issues in a DOM subtree (for development)
 */
export function checkDesignConsistency(element: HTMLElement): ConsistencyIssue[] {
  const issues: ConsistencyIssue[] = [];
  
  // Check for inline styles
  if (element.style.length > 0) {
    for (let i = 0; i < element.style.length; i++) {
      const prop = element.style[i];
      const value = element.style.getPropertyValue(prop);
      
      // Check for hardcoded colors
      if ((prop.includes('color') || prop.includes('background')) && 
          !value.includes('var(--') && !value.includes('hsl(var(')) {
        issues.push({
          type: 'hardcoded-color',
          element: element.tagName.toLowerCase(),
          property: prop,
          value,
          suggestion: `Use a design token like hsl(var(--primary)) instead of ${value}`,
        });
      }
      
      // Check for hardcoded spacing
      if ((prop.includes('margin') || prop.includes('padding') || prop.includes('gap')) &&
          !value.includes('var(--') && value !== '0' && value !== 'auto') {
        issues.push({
          type: 'non-token-spacing',
          element: element.tagName.toLowerCase(),
          property: prop,
          value,
          suggestion: `Use Tailwind spacing utilities (p-4, m-2, gap-3) instead of ${value}`,
        });
      }
    }
  }
  
  // Recursively check children
  Array.from(element.children).forEach((child) => {
    if (child instanceof HTMLElement) {
      issues.push(...checkDesignConsistency(child));
    }
  });
  
  return issues;
}

/**
 * Hook to check design consistency in development
 */
export function useDesignConsistencyCheck(ref: React.RefObject<HTMLElement>): ConsistencyIssue[] {
  const [issues, setIssues] = useState<ConsistencyIssue[]>([]);

  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;
    
    if (ref.current) {
      setIssues(checkDesignConsistency(ref.current));
    }
  }, [ref]);

  return issues;
}

// =============================================================================
// EXPORTS
// =============================================================================

export {
  DesignSystemContext,
};

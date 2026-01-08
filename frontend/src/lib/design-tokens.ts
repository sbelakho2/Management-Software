/**
 * Design Tokens System
 * 
 * Token-first styling for consistent design across the application.
 * All colors, radii, shadows, and spacing are defined here.
 */

// =============================================================================
// Color Token Types
// =============================================================================

export type ColorScale = {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
  950: string;
};

export type SemanticColor = {
  DEFAULT: string;
  foreground: string;
  muted: string;
  border: string;
  ring: string;
};

// =============================================================================
// Core Color Palette
// =============================================================================

/**
 * Neutral gray scale for backgrounds, borders, and text
 */
export const neutral: ColorScale = {
  50: '#fafafa',
  100: '#f4f4f5',
  200: '#e4e4e7',
  300: '#d4d4d8',
  400: '#a1a1aa',
  500: '#71717a',
  600: '#52525b',
  700: '#3f3f46',
  800: '#27272a',
  900: '#18181b',
  950: '#09090b',
};

/**
 * Primary brand color (blue-based)
 */
export const primary: ColorScale = {
  50: '#eff6ff',
  100: '#dbeafe',
  200: '#bfdbfe',
  300: '#93c5fd',
  400: '#60a5fa',
  500: '#3b82f6',
  600: '#2563eb',
  700: '#1d4ed8',
  800: '#1e40af',
  900: '#1e3a8a',
  950: '#172554',
};

/**
 * Success color (green-based)
 */
export const success: ColorScale = {
  50: '#f0fdf4',
  100: '#dcfce7',
  200: '#bbf7d0',
  300: '#86efac',
  400: '#4ade80',
  500: '#22c55e',
  600: '#16a34a',
  700: '#15803d',
  800: '#166534',
  900: '#14532d',
  950: '#052e16',
};

/**
 * Warning color (amber-based)
 */
export const warning: ColorScale = {
  50: '#fffbeb',
  100: '#fef3c7',
  200: '#fde68a',
  300: '#fcd34d',
  400: '#fbbf24',
  500: '#f59e0b',
  600: '#d97706',
  700: '#b45309',
  800: '#92400e',
  900: '#78350f',
  950: '#451a03',
};

/**
 * Danger/Error color (red-based)
 */
export const danger: ColorScale = {
  50: '#fef2f2',
  100: '#fee2e2',
  200: '#fecaca',
  300: '#fca5a5',
  400: '#f87171',
  500: '#ef4444',
  600: '#dc2626',
  700: '#b91c1c',
  800: '#991b1b',
  900: '#7f1d1d',
  950: '#450a0a',
};

/**
 * Info color (cyan-based)
 */
export const info: ColorScale = {
  50: '#ecfeff',
  100: '#cffafe',
  200: '#a5f3fc',
  300: '#67e8f9',
  400: '#22d3ee',
  500: '#06b6d4',
  600: '#0891b2',
  700: '#0e7490',
  800: '#155e75',
  900: '#164e63',
  950: '#083344',
};

// =============================================================================
// Semantic Colors
// =============================================================================

export interface ThemeColors {
  // Background colors
  background: string;
  foreground: string;
  
  // Card/Surface colors
  card: string;
  cardForeground: string;
  
  // Popover colors
  popover: string;
  popoverForeground: string;
  
  // Primary
  primary: string;
  primaryForeground: string;
  
  // Secondary
  secondary: string;
  secondaryForeground: string;
  
  // Muted
  muted: string;
  mutedForeground: string;
  
  // Accent
  accent: string;
  accentForeground: string;
  
  // Destructive
  destructive: string;
  destructiveForeground: string;
  
  // Border and input
  border: string;
  input: string;
  ring: string;
  
  // Status colors
  success: string;
  successForeground: string;
  warning: string;
  warningForeground: string;
  danger: string;
  dangerForeground: string;
  info: string;
  infoForeground: string;
}

export const lightTheme: ThemeColors = {
  background: neutral[50],
  foreground: neutral[950],
  
  card: '#ffffff',
  cardForeground: neutral[950],
  
  popover: '#ffffff',
  popoverForeground: neutral[950],
  
  primary: primary[600],
  primaryForeground: '#ffffff',
  
  secondary: neutral[100],
  secondaryForeground: neutral[900],
  
  muted: neutral[100],
  mutedForeground: neutral[500],
  
  accent: neutral[100],
  accentForeground: neutral[900],
  
  destructive: danger[600],
  destructiveForeground: '#ffffff',
  
  border: neutral[200],
  input: neutral[200],
  ring: primary[500],
  
  success: success[600],
  successForeground: '#ffffff',
  warning: warning[600],
  warningForeground: '#ffffff',
  danger: danger[600],
  dangerForeground: '#ffffff',
  info: info[600],
  infoForeground: '#ffffff',
};

export const darkTheme: ThemeColors = {
  background: neutral[950],
  foreground: neutral[50],
  
  card: neutral[900],
  cardForeground: neutral[50],
  
  popover: neutral[900],
  popoverForeground: neutral[50],
  
  primary: primary[500],
  primaryForeground: '#ffffff',
  
  secondary: neutral[800],
  secondaryForeground: neutral[50],
  
  muted: neutral[800],
  mutedForeground: neutral[400],
  
  accent: neutral[800],
  accentForeground: neutral[50],
  
  destructive: danger[500],
  destructiveForeground: '#ffffff',
  
  border: neutral[800],
  input: neutral[800],
  ring: primary[400],
  
  success: success[500],
  successForeground: '#ffffff',
  warning: warning[500],
  warningForeground: neutral[950],
  danger: danger[500],
  dangerForeground: '#ffffff',
  info: info[500],
  infoForeground: '#ffffff',
};

// =============================================================================
// Surface Elevations
// =============================================================================

export type ElevationLevel = 'flat' | 'raised' | 'overlay';

export interface ElevationTokens {
  shadow: string;
  zIndex: number;
}

export const elevations: Record<ElevationLevel, ElevationTokens> = {
  flat: {
    shadow: 'none',
    zIndex: 0,
  },
  raised: {
    shadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    zIndex: 10,
  },
  overlay: {
    shadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    zIndex: 50,
  },
};

// Dark mode elevations (slightly different shadows)
export const darkElevations: Record<ElevationLevel, ElevationTokens> = {
  flat: {
    shadow: 'none',
    zIndex: 0,
  },
  raised: {
    shadow: '0 1px 3px 0 rgb(0 0 0 / 0.3), 0 1px 2px -1px rgb(0 0 0 / 0.3)',
    zIndex: 10,
  },
  overlay: {
    shadow: '0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.4)',
    zIndex: 50,
  },
};

// =============================================================================
// Shadow Tokens
// =============================================================================

export const shadows = {
  none: 'none',
  xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  sm: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
} as const;

export type ShadowToken = keyof typeof shadows;

// =============================================================================
// Border Radius Tokens
// =============================================================================

export const radii = {
  none: '0px',
  sm: '0.125rem', // 2px
  DEFAULT: '0.25rem', // 4px
  md: '0.375rem', // 6px
  lg: '0.5rem', // 8px
  xl: '0.75rem', // 12px
  '2xl': '1rem', // 16px
  '3xl': '1.5rem', // 24px
  full: '9999px',
} as const;

export type RadiusToken = keyof typeof radii;

// =============================================================================
// Spacing Tokens
// =============================================================================

export const spacing = {
  0: '0px',
  px: '1px',
  0.5: '0.125rem', // 2px
  1: '0.25rem', // 4px
  1.5: '0.375rem', // 6px
  2: '0.5rem', // 8px
  2.5: '0.625rem', // 10px
  3: '0.75rem', // 12px
  3.5: '0.875rem', // 14px
  4: '1rem', // 16px
  5: '1.25rem', // 20px
  6: '1.5rem', // 24px
  7: '1.75rem', // 28px
  8: '2rem', // 32px
  9: '2.25rem', // 36px
  10: '2.5rem', // 40px
  11: '2.75rem', // 44px
  12: '3rem', // 48px
  14: '3.5rem', // 56px
  16: '4rem', // 64px
  20: '5rem', // 80px
  24: '6rem', // 96px
  28: '7rem', // 112px
  32: '8rem', // 128px
  36: '9rem', // 144px
  40: '10rem', // 160px
  44: '11rem', // 176px
  48: '12rem', // 192px
  52: '13rem', // 208px
  56: '14rem', // 224px
  60: '15rem', // 240px
  64: '16rem', // 256px
  72: '18rem', // 288px
  80: '20rem', // 320px
  96: '24rem', // 384px
} as const;

export type SpacingToken = keyof typeof spacing;

// =============================================================================
// Typography Tokens
// =============================================================================

export const fontFamily = {
  sans: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
  serif: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
  mono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',
} as const;

export const fontSize = {
  xs: ['0.75rem', { lineHeight: '1rem' }], // 12px
  sm: ['0.875rem', { lineHeight: '1.25rem' }], // 14px
  base: ['1rem', { lineHeight: '1.5rem' }], // 16px
  lg: ['1.125rem', { lineHeight: '1.75rem' }], // 18px
  xl: ['1.25rem', { lineHeight: '1.75rem' }], // 20px
  '2xl': ['1.5rem', { lineHeight: '2rem' }], // 24px
  '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
  '4xl': ['2.25rem', { lineHeight: '2.5rem' }], // 36px
  '5xl': ['3rem', { lineHeight: '1' }], // 48px
  '6xl': ['3.75rem', { lineHeight: '1' }], // 60px
  '7xl': ['4.5rem', { lineHeight: '1' }], // 72px
  '8xl': ['6rem', { lineHeight: '1' }], // 96px
  '9xl': ['8rem', { lineHeight: '1' }], // 128px
} as const;

export const fontWeight = {
  thin: '100',
  extralight: '200',
  light: '300',
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
  extrabold: '800',
  black: '900',
} as const;

export const letterSpacing = {
  tighter: '-0.05em',
  tight: '-0.025em',
  normal: '0em',
  wide: '0.025em',
  wider: '0.05em',
  widest: '0.1em',
} as const;

export const lineHeight = {
  none: '1',
  tight: '1.25',
  snug: '1.375',
  normal: '1.5',
  relaxed: '1.625',
  loose: '2',
  3: '.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  7: '1.75rem',
  8: '2rem',
  9: '2.25rem',
  10: '2.5rem',
} as const;

// =============================================================================
// Z-Index Tokens
// =============================================================================

export const zIndex = {
  auto: 'auto',
  0: '0',
  10: '10',
  20: '20',
  30: '30',
  40: '40',
  50: '50',
  dropdown: '100',
  sticky: '200',
  overlay: '300',
  modal: '400',
  popover: '500',
  tooltip: '600',
  toast: '700',
  max: '9999',
} as const;

export type ZIndexToken = keyof typeof zIndex;

// =============================================================================
// Transition Tokens
// =============================================================================

export const transitions = {
  none: 'none',
  all: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  default: 'color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  colors: 'color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  opacity: 'opacity 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  shadow: 'box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  transform: 'transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
} as const;

export const durations = {
  fast: '75ms',
  normal: '150ms',
  slow: '200ms',
  slower: '300ms',
  slowest: '500ms',
} as const;

export const easings = {
  linear: 'linear',
  in: 'cubic-bezier(0.4, 0, 1, 1)',
  out: 'cubic-bezier(0, 0, 0.2, 1)',
  inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
} as const;

// =============================================================================
// Breakpoint Tokens
// =============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

export type BreakpointToken = keyof typeof breakpoints;

// =============================================================================
// Component Size Tokens
// =============================================================================

export const componentSizes = {
  xs: {
    height: '1.5rem', // 24px
    padding: '0.25rem 0.5rem',
    fontSize: '0.75rem',
    iconSize: '0.875rem',
  },
  sm: {
    height: '2rem', // 32px
    padding: '0.375rem 0.75rem',
    fontSize: '0.875rem',
    iconSize: '1rem',
  },
  md: {
    height: '2.5rem', // 40px
    padding: '0.5rem 1rem',
    fontSize: '0.875rem',
    iconSize: '1.25rem',
  },
  lg: {
    height: '2.75rem', // 44px
    padding: '0.625rem 1.25rem',
    fontSize: '1rem',
    iconSize: '1.5rem',
  },
  xl: {
    height: '3rem', // 48px
    padding: '0.75rem 1.5rem',
    fontSize: '1rem',
    iconSize: '1.5rem',
  },
} as const;

export type ComponentSize = keyof typeof componentSizes;

// =============================================================================
// Density Mode Tokens
// =============================================================================

export type DensityMode = 'comfortable' | 'compact';

export const densityModes: Record<DensityMode, {
  rowHeight: string;
  cellPadding: string;
  gap: string;
}> = {
  comfortable: {
    rowHeight: '3rem', // 48px
    cellPadding: '0.75rem',
    gap: '1rem',
  },
  compact: {
    rowHeight: '2.25rem', // 36px
    cellPadding: '0.5rem',
    gap: '0.5rem',
  },
};

// =============================================================================
// Status Color Tokens
// =============================================================================

export type StatusType = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

export const statusColors: Record<StatusType, {
  background: string;
  foreground: string;
  border: string;
  backgroundSubtle: string;
}> = {
  success: {
    background: success[600],
    foreground: '#ffffff',
    border: success[600],
    backgroundSubtle: success[50],
  },
  warning: {
    background: warning[500],
    foreground: neutral[950],
    border: warning[500],
    backgroundSubtle: warning[50],
  },
  danger: {
    background: danger[600],
    foreground: '#ffffff',
    border: danger[600],
    backgroundSubtle: danger[50],
  },
  info: {
    background: info[600],
    foreground: '#ffffff',
    border: info[600],
    backgroundSubtle: info[50],
  },
  neutral: {
    background: neutral[500],
    foreground: '#ffffff',
    border: neutral[500],
    backgroundSubtle: neutral[100],
  },
};

// =============================================================================
// Badge/Chip Colors
// =============================================================================

export type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'outline';

export const badgeVariants: Record<BadgeVariant, {
  background: string;
  foreground: string;
  border?: string;
}> = {
  default: {
    background: neutral[100],
    foreground: neutral[800],
  },
  primary: {
    background: primary[100],
    foreground: primary[800],
  },
  success: {
    background: success[100],
    foreground: success[800],
  },
  warning: {
    background: warning[100],
    foreground: warning[800],
  },
  danger: {
    background: danger[100],
    foreground: danger[800],
  },
  info: {
    background: info[100],
    foreground: info[800],
  },
  outline: {
    background: 'transparent',
    foreground: neutral[600],
    border: neutral[300],
  },
};

// =============================================================================
// Focus Ring Tokens
// =============================================================================

export const focusRing = {
  width: '2px',
  offset: '2px',
  color: primary[500],
  style: `0 0 0 2px ${primary[500]}40`, // 40 = 25% opacity
};

// =============================================================================
// Animation Keyframes
// =============================================================================

export const keyframes = {
  fadeIn: {
    from: { opacity: '0' },
    to: { opacity: '1' },
  },
  fadeOut: {
    from: { opacity: '1' },
    to: { opacity: '0' },
  },
  slideInFromTop: {
    from: { transform: 'translateY(-100%)', opacity: '0' },
    to: { transform: 'translateY(0)', opacity: '1' },
  },
  slideInFromBottom: {
    from: { transform: 'translateY(100%)', opacity: '0' },
    to: { transform: 'translateY(0)', opacity: '1' },
  },
  slideInFromLeft: {
    from: { transform: 'translateX(-100%)', opacity: '0' },
    to: { transform: 'translateX(0)', opacity: '1' },
  },
  slideInFromRight: {
    from: { transform: 'translateX(100%)', opacity: '0' },
    to: { transform: 'translateX(0)', opacity: '1' },
  },
  scaleIn: {
    from: { transform: 'scale(0.95)', opacity: '0' },
    to: { transform: 'scale(1)', opacity: '1' },
  },
  spin: {
    from: { transform: 'rotate(0deg)' },
    to: { transform: 'rotate(360deg)' },
  },
  pulse: {
    '0%, 100%': { opacity: '1' },
    '50%': { opacity: '0.5' },
  },
  bounce: {
    '0%, 100%': { transform: 'translateY(-25%)', animationTimingFunction: 'cubic-bezier(0.8, 0, 1, 1)' },
    '50%': { transform: 'translateY(0)', animationTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)' },
  },
};

// =============================================================================
// CSS Variable Generation Utilities
// =============================================================================

/**
 * Convert a color scale to CSS variables
 */
export function colorScaleToCSSVars(name: string, scale: ColorScale): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const [key, value] of Object.entries(scale)) {
    vars[`--${name}-${key}`] = value;
  }
  return vars;
}

/**
 * Convert theme colors to CSS variables
 */
export function themeColorsToCSSVars(colors: ThemeColors): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const [key, value] of Object.entries(colors)) {
    // Convert camelCase to kebab-case
    const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
    vars[`--${cssKey}`] = value;
  }
  return vars;
}

/**
 * Generate all CSS variables for a theme
 */
export function generateThemeCSSVars(theme: 'light' | 'dark'): Record<string, string> {
  const colors = theme === 'light' ? lightTheme : darkTheme;
  const elev = theme === 'light' ? elevations : darkElevations;
  
  const vars: Record<string, string> = {
    // Theme colors
    ...themeColorsToCSSVars(colors),
    
    // Color scales
    ...colorScaleToCSSVars('neutral', neutral),
    ...colorScaleToCSSVars('primary', primary),
    ...colorScaleToCSSVars('success', success),
    ...colorScaleToCSSVars('warning', warning),
    ...colorScaleToCSSVars('danger', danger),
    ...colorScaleToCSSVars('info', info),
    
    // Shadows
    '--shadow-xs': shadows.xs,
    '--shadow-sm': shadows.sm,
    '--shadow-md': shadows.md,
    '--shadow-lg': shadows.lg,
    '--shadow-xl': shadows.xl,
    '--shadow-2xl': shadows['2xl'],
    '--shadow-inner': shadows.inner,
    
    // Elevations
    '--elevation-flat': elev.flat.shadow,
    '--elevation-raised': elev.raised.shadow,
    '--elevation-overlay': elev.overlay.shadow,
    
    // Radii
    '--radius-sm': radii.sm,
    '--radius': radii.DEFAULT,
    '--radius-md': radii.md,
    '--radius-lg': radii.lg,
    '--radius-xl': radii.xl,
    '--radius-2xl': radii['2xl'],
    '--radius-full': radii.full,
    
    // Focus ring
    '--focus-ring-width': focusRing.width,
    '--focus-ring-offset': focusRing.offset,
    '--focus-ring-color': focusRing.color,
    '--focus-ring-style': focusRing.style,
    
    // Transitions
    '--transition-fast': durations.fast,
    '--transition-normal': durations.normal,
    '--transition-slow': durations.slow,
    '--easing-in-out': easings.inOut,
  };
  
  return vars;
}

/**
 * Get CSS variables as a style object for inline use
 */
export function getThemeStyles(theme: 'light' | 'dark'): React.CSSProperties {
  const vars = generateThemeCSSVars(theme);
  return vars as React.CSSProperties;
}

// =============================================================================
// Token Access Utilities
// =============================================================================

/**
 * Get a spacing value
 */
export function getSpacing(key: SpacingToken): string {
  return spacing[key];
}

/**
 * Get a radius value
 */
export function getRadius(key: RadiusToken): string {
  return radii[key];
}

/**
 * Get a shadow value
 */
export function getShadow(key: ShadowToken): string {
  return shadows[key];
}

/**
 * Get a z-index value
 */
export function getZIndex(key: ZIndexToken): string | number {
  return zIndex[key];
}

/**
 * Get a color from a scale
 */
export function getColor(scale: 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info', shade: keyof ColorScale): string {
  const scales = { neutral, primary, success, warning, danger, info };
  return scales[scale][shade];
}

/**
 * Get component size tokens
 */
export function getComponentSize(size: ComponentSize) {
  return componentSizes[size];
}

/**
 * Get density mode tokens
 */
export function getDensityMode(mode: DensityMode) {
  return densityModes[mode];
}

/**
 * Get status colors
 */
export function getStatusColors(status: StatusType) {
  return statusColors[status];
}

/**
 * Get badge variant colors
 */
export function getBadgeVariant(variant: BadgeVariant) {
  return badgeVariants[variant];
}

// =============================================================================
// Default Export
// =============================================================================

export const tokens = {
  colors: {
    neutral,
    primary,
    success,
    warning,
    danger,
    info,
  },
  themes: {
    light: lightTheme,
    dark: darkTheme,
  },
  shadows,
  radii,
  spacing,
  typography: {
    fontFamily,
    fontSize,
    fontWeight,
    letterSpacing,
    lineHeight,
  },
  zIndex,
  transitions,
  durations,
  easings,
  breakpoints,
  componentSizes,
  densityModes,
  statusColors,
  badgeVariants,
  elevations,
  focusRing,
  keyframes,
} as const;

export default tokens;

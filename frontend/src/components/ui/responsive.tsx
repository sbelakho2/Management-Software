/**
 * Cross-Device Responsive System
 * 
 * Provides comprehensive responsive utilities for cross-device perfection:
 * - Breakpoint management with hooks
 * - Device detection utilities
 * - Responsive container components
 * - Safe area handling for mobile devices
 * - Orientation detection and handling
 * 
 * Section 19.1: Cross-Device & Responsive Perfection
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

// =============================================================================
// TYPES & INTERFACES
// =============================================================================

export type Breakpoint = 'mobile' | 'tablet' | 'desktop' | 'wide';

export interface BreakpointConfig {
  mobile: number;    // 320px - 479px
  tablet: number;    // 480px - 1023px
  desktop: number;   // 1024px - 1439px
  wide: number;      // 1440px+
}

export interface DeviceInfo {
  breakpoint: Breakpoint;
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isWide: boolean;
  isTouchDevice: boolean;
  isLandscape: boolean;
  isPortrait: boolean;
  hasNotch: boolean;
  safeAreaInsets: SafeAreaInsets;
  pixelRatio: number;
}

export interface SafeAreaInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface ResponsiveContainerProps {
  children: ReactNode;
  className?: string;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: boolean;
  centerContent?: boolean;
}

export interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
  cols?: {
    mobile?: number;
    tablet?: number;
    desktop?: number;
    wide?: number;
  };
  gap?: 'sm' | 'md' | 'lg';
}

export interface VisibleAtProps {
  children: ReactNode;
  breakpoints: Breakpoint[];
}

export interface HiddenAtProps {
  children: ReactNode;
  breakpoints: Breakpoint[];
}

// =============================================================================
// CONSTANTS
// =============================================================================

export const BREAKPOINTS: BreakpointConfig = {
  mobile: 320,
  tablet: 480,
  desktop: 1024,
  wide: 1440,
};

export const MAX_WIDTHS = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
  full: '100%',
};

// Industrial-grade touch targets (Section 19.1 & 19.6)
export const TOUCH_TARGETS = {
  minimum: 44,      // iOS HIG minimum
  comfortable: 48,  // Material Design recommendation
  industrial: 56,   // Glove-friendly factory floor
};

// =============================================================================
// CONTEXT
// =============================================================================

const ResponsiveContext = createContext<DeviceInfo | null>(null);

// =============================================================================
// UTILITIES
// =============================================================================

/**
 * Get current breakpoint from window width
 */
export function getBreakpoint(width: number): Breakpoint {
  if (width < BREAKPOINTS.tablet) return 'mobile';
  if (width < BREAKPOINTS.desktop) return 'tablet';
  if (width < BREAKPOINTS.wide) return 'desktop';
  return 'wide';
}

/**
 * Check if device supports touch
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

/**
 * Detect if device has a notch (iPhone X+)
 */
export function hasNotch(): boolean {
  if (typeof window === 'undefined') return false;
  
  // Check for CSS env() support and notch
  const style = getComputedStyle(document.documentElement);
  const safeTop = parseInt(style.getPropertyValue('--sat') || '0', 10);
  return safeTop > 20;
}

/**
 * Get safe area insets from CSS environment variables
 */
export function getSafeAreaInsets(): SafeAreaInsets {
  if (typeof window === 'undefined') {
    return { top: 0, right: 0, bottom: 0, left: 0 };
  }
  
  const style = getComputedStyle(document.documentElement);
  
  return {
    top: parseInt(style.getPropertyValue('--sat') || '0', 10),
    right: parseInt(style.getPropertyValue('--sar') || '0', 10),
    bottom: parseInt(style.getPropertyValue('--sab') || '0', 10),
    left: parseInt(style.getPropertyValue('--sal') || '0', 10),
  };
}

/**
 * Get device info from current window state
 */
export function getDeviceInfo(): DeviceInfo {
  if (typeof window === 'undefined') {
    return {
      breakpoint: 'desktop',
      width: 1024,
      height: 768,
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      isWide: false,
      isTouchDevice: false,
      isLandscape: true,
      isPortrait: false,
      hasNotch: false,
      safeAreaInsets: { top: 0, right: 0, bottom: 0, left: 0 },
      pixelRatio: 1,
    };
  }
  
  const width = window.innerWidth;
  const height = window.innerHeight;
  const breakpoint = getBreakpoint(width);
  
  return {
    breakpoint,
    width,
    height,
    isMobile: breakpoint === 'mobile',
    isTablet: breakpoint === 'tablet',
    isDesktop: breakpoint === 'desktop',
    isWide: breakpoint === 'wide',
    isTouchDevice: isTouchDevice(),
    isLandscape: width > height,
    isPortrait: height >= width,
    hasNotch: hasNotch(),
    safeAreaInsets: getSafeAreaInsets(),
    pixelRatio: window.devicePixelRatio || 1,
  };
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to get current device info with real-time updates
 */
export function useDeviceInfo(): DeviceInfo {
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo>(getDeviceInfo);
  
  useEffect(() => {
    const handleResize = () => {
      setDeviceInfo(getDeviceInfo());
    };
    
    const handleOrientationChange = () => {
      // Delay to allow orientation to settle
      setTimeout(handleResize, 100);
    };
    
    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleOrientationChange);
    
    // Set initial CSS custom properties for safe areas
    document.documentElement.style.setProperty('--sat', 'env(safe-area-inset-top, 0px)');
    document.documentElement.style.setProperty('--sar', 'env(safe-area-inset-right, 0px)');
    document.documentElement.style.setProperty('--sab', 'env(safe-area-inset-bottom, 0px)');
    document.documentElement.style.setProperty('--sal', 'env(safe-area-inset-left, 0px)');
    
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleOrientationChange);
    };
  }, []);
  
  return deviceInfo;
}

/**
 * Hook to use responsive context
 */
export function useResponsive(): DeviceInfo {
  const context = useContext(ResponsiveContext);
  
  if (!context) {
    // Fallback to direct hook if not in provider
    return useDeviceInfo();
  }
  
  return context;
}

/**
 * Hook for breakpoint-specific values
 */
export function useBreakpointValue<T>(values: Partial<Record<Breakpoint, T>>, defaultValue: T): T {
  const { breakpoint } = useResponsive();
  
  // Find value for current breakpoint, falling back through hierarchy
  const breakpointOrder: Breakpoint[] = ['mobile', 'tablet', 'desktop', 'wide'];
  const currentIndex = breakpointOrder.indexOf(breakpoint);
  
  for (let i = currentIndex; i >= 0; i--) {
    const bp = breakpointOrder[i];
    if (values[bp] !== undefined) {
      return values[bp] as T;
    }
  }
  
  return defaultValue;
}

/**
 * Hook for media query matching
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);
    
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mediaQuery.addEventListener('change', handler);
    
    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);
  
  return matches;
}

/**
 * Hook for preferred color scheme
 */
export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

/**
 * Hook for reduced motion preference
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

/**
 * Hook for high contrast mode
 */
export function usePrefersHighContrast(): boolean {
  return useMediaQuery('(prefers-contrast: more)');
}

// =============================================================================
// COMPONENTS
// =============================================================================

/**
 * Responsive Provider Component
 */
export function ResponsiveProvider({ children }: { children: ReactNode }) {
  const deviceInfo = useDeviceInfo();
  
  return (
    <ResponsiveContext.Provider value={deviceInfo}>
      {children}
    </ResponsiveContext.Provider>
  );
}

/**
 * Responsive Container Component
 * Constrains content width and adds padding based on breakpoint
 */
export function ResponsiveContainer({
  children,
  className = '',
  maxWidth = 'xl',
  padding = true,
  centerContent = false,
}: ResponsiveContainerProps) {
  const { isMobile, isTablet } = useResponsive();
  
  const paddingClass = padding
    ? isMobile
      ? 'px-4'
      : isTablet
        ? 'px-6'
        : 'px-8'
    : '';
  
  const centerClass = centerContent ? 'mx-auto' : '';
  
  return (
    <div
      className={`w-full ${paddingClass} ${centerClass} ${className}`}
      style={{ maxWidth: MAX_WIDTHS[maxWidth] }}
    >
      {children}
    </div>
  );
}

/**
 * Responsive Grid Component
 * Adaptive grid layout based on breakpoint
 */
export function ResponsiveGrid({
  children,
  className = '',
  cols = { mobile: 1, tablet: 2, desktop: 3, wide: 4 },
  gap = 'md',
}: ResponsiveGridProps) {
  const { breakpoint } = useResponsive();
  
  const columnCount = cols[breakpoint] || cols.desktop || 3;
  
  const gapClasses = {
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
  };
  
  return (
    <div
      className={`grid ${gapClasses[gap]} ${className}`}
      style={{
        gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`,
      }}
    >
      {children}
    </div>
  );
}

/**
 * Show content only at specified breakpoints
 */
export function VisibleAt({ children, breakpoints }: VisibleAtProps) {
  const { breakpoint } = useResponsive();
  
  if (!breakpoints.includes(breakpoint)) {
    return null;
  }
  
  return <>{children}</>;
}

/**
 * Hide content at specified breakpoints
 */
export function HiddenAt({ children, breakpoints }: HiddenAtProps) {
  const { breakpoint } = useResponsive();
  
  if (breakpoints.includes(breakpoint)) {
    return null;
  }
  
  return <>{children}</>;
}

/**
 * Safe Area View for mobile devices with notches
 */
export function SafeAreaView({
  children,
  className = '',
  edges = ['top', 'bottom'],
}: {
  children: ReactNode;
  className?: string;
  edges?: ('top' | 'right' | 'bottom' | 'left')[];
}) {
  const { safeAreaInsets } = useResponsive();
  
  const style: React.CSSProperties = {};
  
  // Handle NaN values gracefully
  const safeInset = (value: number) => (isNaN(value) ? 0 : value);
  
  if (edges.includes('top') && safeInset(safeAreaInsets.top) > 0) {
    style.paddingTop = safeInset(safeAreaInsets.top);
  }
  if (edges.includes('right') && safeInset(safeAreaInsets.right) > 0) {
    style.paddingRight = safeInset(safeAreaInsets.right);
  }
  if (edges.includes('bottom') && safeInset(safeAreaInsets.bottom) > 0) {
    style.paddingBottom = safeInset(safeAreaInsets.bottom);
  }
  if (edges.includes('left') && safeInset(safeAreaInsets.left) > 0) {
    style.paddingLeft = safeInset(safeAreaInsets.left);
  }
  
  return (
    <div className={className} style={style}>
      {children}
    </div>
  );
}

/**
 * Touch-friendly button wrapper
 * Ensures minimum touch target size for industrial use
 */
export function TouchTarget({
  children,
  className = '',
  size = 'comfortable',
  onClick,
}: {
  children: ReactNode;
  className?: string;
  size?: 'minimum' | 'comfortable' | 'industrial';
  onClick?: () => void;
}) {
  const minSize = TOUCH_TARGETS[size];
  
  return (
    <button
      className={`inline-flex items-center justify-center ${className}`}
      style={{
        minWidth: minSize,
        minHeight: minSize,
      }}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

/**
 * Responsive Text Component
 * Adjusts font size based on breakpoint
 */
export function ResponsiveText({
  children,
  as: Component = 'span',
  className = '',
  sizes = { mobile: 'text-sm', tablet: 'text-base', desktop: 'text-lg' },
}: {
  children: ReactNode;
  as?: keyof JSX.IntrinsicElements;
  className?: string;
  sizes?: Partial<Record<Breakpoint, string>>;
}) {
  const sizeClass = useBreakpointValue(sizes, 'text-base');
  
  return React.createElement(
    Component,
    { className: `${sizeClass} ${className}` },
    children
  );
}

/**
 * Responsive Card View
 * Converts table rows to cards on mobile
 */
export function ResponsiveCardView({
  children,
  className = '',
  cardClassName = '',
  tableClassName = '',
  renderAsCards,
}: {
  children: ReactNode;
  className?: string;
  cardClassName?: string;
  tableClassName?: string;
  renderAsCards?: boolean;
}) {
  const { isMobile } = useResponsive();
  const shouldRenderCards = renderAsCards ?? isMobile;
  
  return (
    <div className={`${className} ${shouldRenderCards ? cardClassName : tableClassName}`}>
      {children}
    </div>
  );
}

/**
 * Orientation Lock Component
 * Shows message when in wrong orientation
 */
export function OrientationLock({
  children,
  requiredOrientation = 'portrait',
  message = 'Please rotate your device',
}: {
  children: ReactNode;
  requiredOrientation?: 'portrait' | 'landscape';
  message?: string;
}) {
  const { isLandscape, isPortrait, isMobile, isTablet } = useResponsive();
  
  const isWrongOrientation = 
    (requiredOrientation === 'portrait' && isLandscape) ||
    (requiredOrientation === 'landscape' && isPortrait);
  
  // Only show on mobile/tablet
  if ((isMobile || isTablet) && isWrongOrientation) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center p-8">
          <div className="text-6xl mb-4">📱</div>
          <p className="text-xl">{message}</p>
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
}

// =============================================================================
// CSS UTILITIES (for Tailwind)
// =============================================================================

/**
 * Generate responsive Tailwind classes
 */
export function responsiveClasses(
  base: string,
  responsive: Partial<Record<Breakpoint, string>>
): string {
  const classes = [base];
  
  if (responsive.tablet) classes.push(`sm:${responsive.tablet}`);
  if (responsive.desktop) classes.push(`lg:${responsive.desktop}`);
  if (responsive.wide) classes.push(`xl:${responsive.wide}`);
  
  return classes.join(' ');
}

/**
 * Industrial-grade responsive utilities
 */
export const industrialResponsive = {
  // Thumb-zone friendly positioning
  thumbZone: 'fixed bottom-0 left-0 right-0 pb-safe',
  
  // High-contrast mode for bright environments
  highContrast: 'contrast-more:bg-white contrast-more:text-black contrast-more:border-black',
  
  // Glove-friendly touch targets
  gloveFriendly: 'min-h-[56px] min-w-[56px] touch-manipulation',
  
  // Safe area padding
  safeArea: 'pt-safe pr-safe pb-safe pl-safe',
  
  // Prevent text overflow on small screens
  preventOverflow: 'break-words overflow-wrap-anywhere hyphens-auto',
};

// =============================================================================
// EXPORTS
// =============================================================================

export default {
  ResponsiveProvider,
  ResponsiveContainer,
  ResponsiveGrid,
  VisibleAt,
  HiddenAt,
  SafeAreaView,
  TouchTarget,
  ResponsiveText,
  ResponsiveCardView,
  OrientationLock,
  useDeviceInfo,
  useResponsive,
  useBreakpointValue,
  useMediaQuery,
  usePrefersDarkMode,
  usePrefersReducedMotion,
  usePrefersHighContrast,
  getBreakpoint,
  getDeviceInfo,
  BREAKPOINTS,
  TOUCH_TARGETS,
  MAX_WIDTHS,
  responsiveClasses,
  industrialResponsive,
};

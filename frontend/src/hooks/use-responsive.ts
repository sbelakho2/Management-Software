/**
 * useResponsive - Cross-Device Responsive Hook
 * 
 * Section 19.1: Cross-Device & Responsive Perfection
 * 
 * Provides real-time device information, breakpoint detection,
 * and responsive utilities for cross-device perfection.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

// =============================================================================
// TYPES & INTERFACES
// =============================================================================

export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface BreakpointConfig {
  xs: number;    // 0 - 479px (mobile portrait)
  sm: number;    // 480 - 639px (mobile landscape)
  md: number;    // 640 - 767px (tablet portrait)
  lg: number;    // 768 - 1023px (tablet landscape)
  xl: number;    // 1024 - 1279px (desktop)
  '2xl': number; // 1280px+ (wide desktop)
}

export interface DeviceInfo {
  breakpoint: Breakpoint;
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isTouchDevice: boolean;
  isLandscape: boolean;
  isPortrait: boolean;
  hasNotch: boolean;
  pixelRatio: number;
  isSSR: boolean;
}

export interface SafeAreaInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface ResponsiveConfig {
  debounceMs?: number;
  ssr?: boolean;
}

// =============================================================================
// CONSTANTS
// =============================================================================

export const BREAKPOINTS: BreakpointConfig = {
  xs: 0,
  sm: 480,
  md: 640,
  lg: 768,
  xl: 1024,
  '2xl': 1280,
};

// Industrial-grade touch targets (Section 19.6)
export const TOUCH_TARGETS = {
  minimum: 44,      // iOS HIG minimum
  comfortable: 48,  // Material Design recommendation  
  industrial: 56,   // Glove-friendly factory floor
} as const;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get current breakpoint from window width
 */
export function getBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINTS['2xl']) return '2xl';
  if (width >= BREAKPOINTS.xl) return 'xl';
  if (width >= BREAKPOINTS.lg) return 'lg';
  if (width >= BREAKPOINTS.md) return 'md';
  if (width >= BREAKPOINTS.sm) return 'sm';
  return 'xs';
}

/**
 * Check if device supports touch
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

/**
 * Check for notch (iPhone X+ style)
 */
export function hasNotch(): boolean {
  if (typeof window === 'undefined') return false;
  
  // Check if CSS.supports exists (not available in jsdom)
  if (typeof CSS === 'undefined' || typeof CSS.supports !== 'function') return false;
  
  try {
    // Check if CSS env() is supported
    const supportsEnv = CSS.supports('padding-top', 'env(safe-area-inset-top)');
    if (!supportsEnv) return false;
    
    // Create a test element to check actual inset values
    const testDiv = document.createElement('div');
    testDiv.style.cssText = 'position:fixed;top:0;padding-top:env(safe-area-inset-top);';
    document.body.appendChild(testDiv);
    const paddingTop = parseInt(getComputedStyle(testDiv).paddingTop || '0', 10);
    document.body.removeChild(testDiv);
    
    return paddingTop > 20;
  } catch {
    return false;
  }
}

/**
 * Get safe area insets
 */
export function getSafeAreaInsets(): SafeAreaInsets {
  if (typeof window === 'undefined') {
    return { top: 0, right: 0, bottom: 0, left: 0 };
  }

  const testDiv = document.createElement('div');
  testDiv.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    padding-top: env(safe-area-inset-top, 0px);
    padding-right: env(safe-area-inset-right, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    padding-left: env(safe-area-inset-left, 0px);
  `;
  document.body.appendChild(testDiv);
  
  const style = getComputedStyle(testDiv);
  const insets: SafeAreaInsets = {
    top: parseInt(style.paddingTop || '0', 10),
    right: parseInt(style.paddingRight || '0', 10),
    bottom: parseInt(style.paddingBottom || '0', 10),
    left: parseInt(style.paddingLeft || '0', 10),
  };
  
  document.body.removeChild(testDiv);
  return insets;
}

/**
 * Get current device info
 */
export function getDeviceInfo(isSSR: boolean = false): DeviceInfo {
  if (typeof window === 'undefined' || isSSR) {
    return {
      breakpoint: 'xl',
      width: 1024,
      height: 768,
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      isTouchDevice: false,
      isLandscape: true,
      isPortrait: false,
      hasNotch: false,
      pixelRatio: 1,
      isSSR: true,
    };
  }
  
  const width = window.innerWidth;
  const height = window.innerHeight;
  const breakpoint = getBreakpoint(width);
  
  return {
    breakpoint,
    width,
    height,
    isMobile: breakpoint === 'xs' || breakpoint === 'sm',
    isTablet: breakpoint === 'md' || breakpoint === 'lg',
    isDesktop: breakpoint === 'xl' || breakpoint === '2xl',
    isTouchDevice: isTouchDevice(),
    isLandscape: width > height,
    isPortrait: height >= width,
    hasNotch: hasNotch(),
    pixelRatio: window.devicePixelRatio || 1,
    isSSR: false,
  };
}

/**
 * Debounce function
 */
function debounce<T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => func(...args), wait);
  };
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Main responsive hook - provides device info with real-time updates
 */
export function useResponsive(config: ResponsiveConfig = {}): DeviceInfo {
  const { debounceMs = 100, ssr = false } = config;
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo>(() => getDeviceInfo(ssr));
  
  useEffect(() => {
    // Skip on SSR
    if (typeof window === 'undefined') return;
    
    const handleResize = debounce(() => {
      setDeviceInfo(getDeviceInfo(false));
    }, debounceMs);
    
    const handleOrientationChange = () => {
      // Delay to allow orientation to settle
      setTimeout(() => setDeviceInfo(getDeviceInfo(false)), 150);
    };
    
    // Initial update on client
    setDeviceInfo(getDeviceInfo(false));
    
    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleOrientationChange);
    
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleOrientationChange);
    };
  }, [debounceMs]);
  
  return deviceInfo;
}

/**
 * Hook for breakpoint-specific values
 */
export function useBreakpointValue<T>(
  values: Partial<Record<Breakpoint, T>>,
  defaultValue: T
): T {
  const { breakpoint } = useResponsive();
  
  return useMemo(() => {
    // Find value for current breakpoint, falling back through hierarchy
    const breakpointOrder: Breakpoint[] = ['xs', 'sm', 'md', 'lg', 'xl', '2xl'];
    const currentIndex = breakpointOrder.indexOf(breakpoint);
    
    for (let i = currentIndex; i >= 0; i--) {
      const bp = breakpointOrder[i];
      if (values[bp] !== undefined) {
        return values[bp] as T;
      }
    }
    
    return defaultValue;
  }, [breakpoint, values, defaultValue]);
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
    
    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    }
    
    // Legacy support
    mediaQuery.addListener(handler);
    return () => mediaQuery.removeListener(handler);
  }, [query]);
  
  return matches;
}

/**
 * Hook for safe area insets
 */
export function useSafeArea(): SafeAreaInsets {
  const [insets, setInsets] = useState<SafeAreaInsets>({ top: 0, right: 0, bottom: 0, left: 0 });
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const updateInsets = () => {
      setInsets(getSafeAreaInsets());
    };
    
    updateInsets();
    
    // Update on orientation change
    window.addEventListener('orientationchange', updateInsets);
    window.addEventListener('resize', updateInsets);
    
    return () => {
      window.removeEventListener('orientationchange', updateInsets);
      window.removeEventListener('resize', updateInsets);
    };
  }, []);
  
  return insets;
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

/**
 * Hook for coarse pointer (touch) detection
 */
export function useCoarsePointer(): boolean {
  return useMediaQuery('(pointer: coarse)');
}

/**
 * Hook for hover capability
 */
export function useCanHover(): boolean {
  return useMediaQuery('(hover: hover)');
}

/**
 * Hook for orientation
 */
export function useOrientation(): 'portrait' | 'landscape' {
  const isLandscape = useMediaQuery('(orientation: landscape)');
  return isLandscape ? 'landscape' : 'portrait';
}

/**
 * Hook to check if at or above a breakpoint
 */
export function useBreakpointUp(breakpoint: Breakpoint): boolean {
  const { width } = useResponsive();
  return width >= BREAKPOINTS[breakpoint];
}

/**
 * Hook to check if below a breakpoint
 */
export function useBreakpointDown(breakpoint: Breakpoint): boolean {
  const { width } = useResponsive();
  return width < BREAKPOINTS[breakpoint];
}

/**
 * Hook to check if between two breakpoints
 */
export function useBreakpointBetween(lower: Breakpoint, upper: Breakpoint): boolean {
  const { width } = useResponsive();
  return width >= BREAKPOINTS[lower] && width < BREAKPOINTS[upper];
}

/**
 * Hook for responsive container queries (fallback for older browsers)
 */
export function useContainerQuery(
  containerRef: React.RefObject<HTMLElement>,
  breakpoints: { [key: string]: number }
): string | null {
  const [currentBreakpoint, setCurrentBreakpoint] = useState<string | null>(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    const container = containerRef.current;
    
    // Use ResizeObserver to track container size
    const observer = new ResizeObserver(entries => {
      const entry = entries[0];
      if (!entry) return;
      
      const width = entry.contentRect.width;
      
      // Find matching breakpoint
      let matched: string | null = null;
      let maxWidth = 0;
      
      Object.entries(breakpoints).forEach(([name, minWidth]) => {
        if (width >= minWidth && minWidth > maxWidth) {
          matched = name;
          maxWidth = minWidth;
        }
      });
      
      setCurrentBreakpoint(matched);
    });
    
    observer.observe(container);
    
    return () => observer.disconnect();
  }, [containerRef, breakpoints]);
  
  return currentBreakpoint;
}

/**
 * Hook for window dimensions with SSR support
 */
export function useWindowSize(): { width: number; height: number } {
  const [size, setSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
  });
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const handleResize = () => {
      setSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    
    window.addEventListener('resize', handleResize);
    handleResize(); // Initial call
    
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  return size;
}

/**
 * Hook for scroll position
 */
export function useScrollPosition(): { x: number; y: number } {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const handleScroll = () => {
      setPosition({
        x: window.scrollX,
        y: window.scrollY,
      });
    };
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial call
    
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);
  
  return position;
}

/**
 * Hook for viewport visibility (element in viewport)
 */
export function useInViewport(
  elementRef: React.RefObject<HTMLElement>,
  options: IntersectionObserverInit = {}
): boolean {
  const [isInViewport, setIsInViewport] = useState(false);
  
  useEffect(() => {
    if (!elementRef.current) return;
    
    const element = elementRef.current;
    
    const observer = new IntersectionObserver(
      entries => {
        setIsInViewport(entries[0]?.isIntersecting ?? false);
      },
      {
        threshold: 0.1,
        ...options,
      }
    );
    
    observer.observe(element);
    
    return () => observer.disconnect();
  }, [elementRef, options]);
  
  return isInViewport;
}

// =============================================================================
// RESPONSIVE UTILITIES
// =============================================================================

/**
 * Generate responsive Tailwind classes
 */
export function responsiveClasses(
  base: string,
  responsive: Partial<Record<Breakpoint, string>>
): string {
  const classes = [base];
  
  // Map to Tailwind breakpoint prefixes
  const tailwindMap: Record<Breakpoint, string> = {
    xs: '',      // Default (mobile-first)
    sm: 'sm:',
    md: 'md:',
    lg: 'lg:',
    xl: 'xl:',
    '2xl': '2xl:',
  };
  
  Object.entries(responsive).forEach(([bp, className]) => {
    if (className) {
      const prefix = tailwindMap[bp as Breakpoint];
      classes.push(`${prefix}${className}`);
    }
  });
  
  return classes.join(' ');
}

/**
 * Thumb-zone utilities for mobile ergonomics
 */
export const thumbZone = {
  // Bottom-positioned for easy thumb reach
  safeBottom: 'fixed bottom-0 left-0 right-0 pb-safe',
  
  // Primary action zone (bottom 30% of screen)
  primaryAction: 'fixed bottom-[10%] left-[10%] right-[10%]',
  
  // Natural thumb arc positioning
  thumbArc: 'fixed bottom-[15%] right-[10%]',
};

/**
 * Industrial-grade responsive utilities
 */
export const industrialResponsive = {
  // Glove-friendly touch targets
  gloveFriendly: 'min-h-[56px] min-w-[56px] touch-manipulation',
  
  // High-contrast mode for bright environments
  highContrast: 'contrast-more:bg-white contrast-more:text-black contrast-more:border-black',
  
  // Large text for distance reading
  distanceText: 'text-lg md:text-xl lg:text-2xl font-semibold',
  
  // Safe area padding for notched devices
  safeAreaPadding: 'pt-safe pr-safe pb-safe pl-safe',
};

export default useResponsive;

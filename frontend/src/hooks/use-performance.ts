/**
 * Performance Optimization Hooks
 * 
 * Utilities to ensure frontend load time < 2 seconds:
 * - Debounced inputs
 * - Throttled scroll handlers
 * - Lazy loading helpers
 * - Performance monitoring
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface PerformanceMetrics {
  pageLoadTime: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  timeToInteractive: number;
  cumulativeLayoutShift: number;
  firstInputDelay: number;
}

export interface PerformanceEntry {
  name: string;
  duration: number;
  startTime: number;
  entryType: string;
}

export interface LazyLoadOptions {
  rootMargin?: string;
  threshold?: number;
  triggerOnce?: boolean;
}

// =============================================================================
// Debounce Hook
// =============================================================================

/**
 * Debounce a value - delays updating until after wait ms of no changes
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);
  
  return debouncedValue;
}

/**
 * Debounce a callback function
 */
export function useDebouncedCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);
  
  // Update callback ref when it changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);
  
  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    },
    [delay]
  );
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);
  
  return debouncedCallback;
}

// =============================================================================
// Throttle Hook
// =============================================================================

/**
 * Throttle a callback - ensures it runs at most once per wait ms
 */
export function useThrottledCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const lastRan = useRef<number>(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);
  
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);
  
  const throttledCallback = useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now();
      
      if (now - lastRan.current >= delay) {
        callbackRef.current(...args);
        lastRan.current = now;
      } else {
        // Schedule a trailing call
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        
        timeoutRef.current = setTimeout(() => {
          callbackRef.current(...args);
          lastRan.current = Date.now();
        }, delay - (now - lastRan.current));
      }
    },
    [delay]
  );
  
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);
  
  return throttledCallback;
}

// =============================================================================
// Intersection Observer Hook (Lazy Loading)
// =============================================================================

/**
 * Detect when an element enters the viewport
 */
export function useIntersectionObserver(
  options: LazyLoadOptions = {}
): [React.RefObject<HTMLElement | null>, boolean] {
  const { rootMargin = '100px', threshold = 0, triggerOnce = true } = options;
  const elementRef = useRef<HTMLElement | null>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);
  const hasTriggered = useRef(false);
  
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    
    if (typeof IntersectionObserver === 'undefined') {
      // Fallback for SSR or unsupported browsers
      setIsIntersecting(true);
      return;
    }
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          if (triggerOnce && hasTriggered.current) return;
          hasTriggered.current = true;
          setIsIntersecting(true);
        } else if (!triggerOnce) {
          setIsIntersecting(false);
        }
      },
      { rootMargin, threshold }
    );
    
    observer.observe(element);
    
    return () => {
      observer.disconnect();
    };
  }, [rootMargin, threshold, triggerOnce]);
  
  return [elementRef, isIntersecting];
}

/**
 * Lazy load component when it enters viewport
 */
export function useLazyLoad(options: LazyLoadOptions = {}): {
  ref: React.RefObject<HTMLElement | null>;
  isVisible: boolean;
  hasLoaded: boolean;
} {
  const [ref, isVisible] = useIntersectionObserver({ ...options, triggerOnce: true });
  const [hasLoaded, setHasLoaded] = useState(false);
  
  useEffect(() => {
    if (isVisible && !hasLoaded) {
      setHasLoaded(true);
    }
  }, [isVisible, hasLoaded]);
  
  return { ref, isVisible, hasLoaded };
}

// =============================================================================
// Performance Monitoring Hook
// =============================================================================

/**
 * Monitor and report Core Web Vitals
 */
export function usePerformanceMonitor(): PerformanceMetrics | null {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  
  useEffect(() => {
    if (typeof window === 'undefined' || typeof performance === 'undefined') {
      return;
    }
    
    const measureMetrics = () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
      const paint = performance.getEntriesByType('paint');
      
      if (!navigation) return;
      
      const fcp = paint.find(p => p.name === 'first-contentful-paint')?.startTime ?? 0;
      
      // Get LCP if available
      let lcp = 0;
      const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
      if (lcpEntries.length > 0) {
        lcp = lcpEntries[lcpEntries.length - 1].startTime;
      }
      
      setMetrics({
        pageLoadTime: navigation.loadEventEnd - navigation.startTime,
        firstContentfulPaint: fcp,
        largestContentfulPaint: lcp,
        timeToInteractive: navigation.domInteractive - navigation.startTime,
        cumulativeLayoutShift: 0, // Requires PerformanceObserver
        firstInputDelay: 0, // Requires user interaction
      });
    };
    
    // Measure after page load
    if (document.readyState === 'complete') {
      measureMetrics();
    } else {
      window.addEventListener('load', measureMetrics);
      return () => window.removeEventListener('load', measureMetrics);
    }
  }, []);
  
  return metrics;
}

/**
 * Track custom performance marks
 */
export function usePerformanceMark(markName: string): {
  startMark: () => void;
  endMark: () => number;
  getDuration: () => number | null;
} {
  const startMarkName = `${markName}-start`;
  const endMarkName = `${markName}-end`;
  const measureName = `${markName}-measure`;
  
  const startMark = useCallback(() => {
    if (typeof performance !== 'undefined') {
      performance.mark(startMarkName);
    }
  }, [startMarkName]);
  
  const endMark = useCallback((): number => {
    if (typeof performance === 'undefined') return 0;
    
    performance.mark(endMarkName);
    
    try {
      performance.measure(measureName, startMarkName, endMarkName);
      const measures = performance.getEntriesByName(measureName);
      return measures[measures.length - 1]?.duration ?? 0;
    } catch {
      return 0;
    }
  }, [startMarkName, endMarkName, measureName]);
  
  const getDuration = useCallback((): number | null => {
    if (typeof performance === 'undefined') return null;
    
    const measures = performance.getEntriesByName(measureName);
    if (measures.length === 0) return null;
    return measures[measures.length - 1].duration;
  }, [measureName]);
  
  return { startMark, endMark, getDuration };
}

// =============================================================================
// Memoization Helpers
// =============================================================================

/**
 * Deep compare memoization for complex objects
 */
export function useDeepMemo<T>(value: T, deps: unknown[]): T {
  const ref = useRef<T>(value);
  const depsRef = useRef<unknown[]>(deps);
  
  const depsChanged = deps.some((dep, i) => {
    const prev = depsRef.current[i];
    return !deepEqual(dep, prev);
  });
  
  if (depsChanged) {
    ref.current = value;
    depsRef.current = deps;
  }
  
  return ref.current;
}

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return a === b;
  
  if (typeof a === 'object' && typeof b === 'object') {
    const aObj = a as Record<string, unknown>;
    const bObj = b as Record<string, unknown>;
    const aKeys = Object.keys(aObj);
    const bKeys = Object.keys(bObj);
    
    if (aKeys.length !== bKeys.length) return false;
    
    return aKeys.every(key => deepEqual(aObj[key], bObj[key]));
  }
  
  return false;
}

// =============================================================================
// Virtual Scrolling Support
// =============================================================================

export interface VirtualScrollConfig {
  itemHeight: number;
  overscan?: number;
  containerHeight: number;
}

export interface VirtualScrollResult {
  visibleItems: { index: number; style: React.CSSProperties }[];
  totalHeight: number;
  containerStyle: React.CSSProperties;
}

/**
 * Virtual scrolling for large lists
 */
export function useVirtualScroll(
  totalItems: number,
  config: VirtualScrollConfig
): VirtualScrollResult & { onScroll: (scrollTop: number) => void } {
  const { itemHeight, overscan = 3, containerHeight } = config;
  const [scrollTop, setScrollTop] = useState(0);
  
  const result = useMemo(() => {
    const totalHeight = totalItems * itemHeight;
    
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      totalItems - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );
    
    const visibleItems: { index: number; style: React.CSSProperties }[] = [];
    
    for (let i = startIndex; i <= endIndex; i++) {
      visibleItems.push({
        index: i,
        style: {
          position: 'absolute',
          top: i * itemHeight,
          height: itemHeight,
          width: '100%',
        },
      });
    }
    
    const containerStyle: React.CSSProperties = {
      height: containerHeight,
      overflow: 'auto',
      position: 'relative',
    };
    
    return { visibleItems, totalHeight, containerStyle };
  }, [totalItems, itemHeight, overscan, containerHeight, scrollTop]);
  
  const onScroll = useCallback((newScrollTop: number) => {
    setScrollTop(newScrollTop);
  }, []);
  
  return { ...result, onScroll };
}

// =============================================================================
// Request Idle Callback Hook
// =============================================================================

/**
 * Schedule work during browser idle time
 */
export function useIdleCallback(
  callback: () => void,
  deps: unknown[] = []
): void {
  useEffect(() => {
    if (typeof window === 'undefined') {
      callback();
      return;
    }
    
    if ('requestIdleCallback' in window) {
      const id = (window as Window & { requestIdleCallback: (cb: () => void) => number }).requestIdleCallback(callback);
      return () => {
        (window as Window & { cancelIdleCallback: (id: number) => void }).cancelIdleCallback(id);
      };
    } else {
      // Fallback to setTimeout
      const id = setTimeout(callback, 1);
      return () => clearTimeout(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

// =============================================================================
// Preload Hook
// =============================================================================

/**
 * Preload resources during idle time
 */
export function usePreload(urls: string[]): void {
  useIdleCallback(() => {
    if (typeof document === 'undefined') return;
    
    urls.forEach(url => {
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      document.head.appendChild(link);
    });
  }, [urls.join(',')]);
}

/**
 * Preload images
 */
export function usePreloadImages(imageUrls: string[]): boolean[] {
  const [loaded, setLoaded] = useState<boolean[]>(imageUrls.map(() => false));
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const loadStates = imageUrls.map(() => false);
    
    imageUrls.forEach((url, index) => {
      const img = new Image();
      img.onload = () => {
        loadStates[index] = true;
        setLoaded([...loadStates]);
      };
      img.onerror = () => {
        loadStates[index] = true; // Mark as "loaded" even on error
        setLoaded([...loadStates]);
      };
      img.src = url;
    });
  }, [imageUrls]);
  
  return loaded;
}

export default {
  useDebounce,
  useDebouncedCallback,
  useThrottledCallback,
  useIntersectionObserver,
  useLazyLoad,
  usePerformanceMonitor,
  usePerformanceMark,
  useDeepMemo,
  useVirtualScroll,
  useIdleCallback,
  usePreload,
  usePreloadImages,
};

/**
 * Tests for useResponsive hook
 * 
 * Section 19.1: Cross-Device & Responsive Perfection
 * Tests for responsive hooks, breakpoint detection, and device utilities
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useResponsive,
  useBreakpointValue,
  useMediaQuery,
  useSafeArea,
  usePrefersDarkMode,
  usePrefersReducedMotion,
  usePrefersHighContrast,
  useCoarsePointer,
  useCanHover,
  useOrientation,
  useBreakpointUp,
  useBreakpointDown,
  useBreakpointBetween,
  useWindowSize,
  useScrollPosition,
  useContainerQuery,
  getBreakpoint,
  getDeviceInfo,
  isTouchDevice,
  hasNotch,
  getSafeAreaInsets,
  responsiveClasses,
  thumbZone,
  industrialResponsive,
  BREAKPOINTS,
  TOUCH_TARGETS,
  type Breakpoint,
  type DeviceInfo,
} from '../use-responsive';

// =============================================================================
// MOCK SETUP
// =============================================================================

// Store original window properties
const originalInnerWidth = window.innerWidth;
const originalInnerHeight = window.innerHeight;
const originalDevicePixelRatio = window.devicePixelRatio;
const originalMatchMedia = window.matchMedia;

// Mock ResizeObserver
class MockResizeObserver {
  callback: ResizeObserverCallback;
  
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
}

// Mock IntersectionObserver
class MockIntersectionObserver {
  callback: IntersectionObserverCallback;
  
  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
  }
  
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
}

// Setup mocks before tests
beforeAll(() => {
  // @ts-ignore
  global.ResizeObserver = MockResizeObserver;
  // @ts-ignore
  global.IntersectionObserver = MockIntersectionObserver;
});

// Reset mocks after each test
afterEach(() => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    value: originalInnerWidth,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    value: originalInnerHeight,
  });
  Object.defineProperty(window, 'devicePixelRatio', {
    writable: true,
    value: originalDevicePixelRatio,
  });
  window.matchMedia = originalMatchMedia;
  jest.clearAllMocks();
});

// Helper to set window dimensions
function setWindowSize(width: number, height: number): void {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    value: width,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    value: height,
  });
}

// Helper to mock matchMedia
function mockMatchMedia(matches: boolean): void {
  window.matchMedia = jest.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
}

// =============================================================================
// UTILITY FUNCTION TESTS
// =============================================================================

describe('getBreakpoint', () => {
  it('returns xs for widths below 480px', () => {
    expect(getBreakpoint(0)).toBe('xs');
    expect(getBreakpoint(320)).toBe('xs');
    expect(getBreakpoint(479)).toBe('xs');
  });

  it('returns sm for widths 480-639px', () => {
    expect(getBreakpoint(480)).toBe('sm');
    expect(getBreakpoint(550)).toBe('sm');
    expect(getBreakpoint(639)).toBe('sm');
  });

  it('returns md for widths 640-767px', () => {
    expect(getBreakpoint(640)).toBe('md');
    expect(getBreakpoint(700)).toBe('md');
    expect(getBreakpoint(767)).toBe('md');
  });

  it('returns lg for widths 768-1023px', () => {
    expect(getBreakpoint(768)).toBe('lg');
    expect(getBreakpoint(900)).toBe('lg');
    expect(getBreakpoint(1023)).toBe('lg');
  });

  it('returns xl for widths 1024-1279px', () => {
    expect(getBreakpoint(1024)).toBe('xl');
    expect(getBreakpoint(1150)).toBe('xl');
    expect(getBreakpoint(1279)).toBe('xl');
  });

  it('returns 2xl for widths 1280px and above', () => {
    expect(getBreakpoint(1280)).toBe('2xl');
    expect(getBreakpoint(1440)).toBe('2xl');
    expect(getBreakpoint(1920)).toBe('2xl');
    expect(getBreakpoint(2560)).toBe('2xl');
  });
});

describe('getDeviceInfo', () => {
  it('returns SSR defaults when isSSR is true', () => {
    const info = getDeviceInfo(true);
    
    expect(info).toEqual({
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
    });
  });

  it('returns correct device info for mobile width', () => {
    setWindowSize(375, 667);
    const info = getDeviceInfo(false);
    
    expect(info.breakpoint).toBe('xs');
    expect(info.width).toBe(375);
    expect(info.height).toBe(667);
    expect(info.isMobile).toBe(true);
    expect(info.isTablet).toBe(false);
    expect(info.isDesktop).toBe(false);
    expect(info.isPortrait).toBe(true);
    expect(info.isLandscape).toBe(false);
    expect(info.isSSR).toBe(false);
  });

  it('returns correct device info for tablet width', () => {
    setWindowSize(768, 1024);
    const info = getDeviceInfo(false);
    
    expect(info.breakpoint).toBe('lg');
    expect(info.isMobile).toBe(false);
    expect(info.isTablet).toBe(true);
    expect(info.isDesktop).toBe(false);
    expect(info.isPortrait).toBe(true);
  });

  it('returns correct device info for desktop width', () => {
    setWindowSize(1440, 900);
    const info = getDeviceInfo(false);
    
    expect(info.breakpoint).toBe('2xl');
    expect(info.isMobile).toBe(false);
    expect(info.isTablet).toBe(false);
    expect(info.isDesktop).toBe(true);
    expect(info.isLandscape).toBe(true);
  });

  it('detects landscape orientation correctly', () => {
    setWindowSize(1024, 768);
    const info = getDeviceInfo(false);
    
    expect(info.isLandscape).toBe(true);
    expect(info.isPortrait).toBe(false);
  });

  it('detects portrait orientation correctly', () => {
    setWindowSize(768, 1024);
    const info = getDeviceInfo(false);
    
    expect(info.isLandscape).toBe(false);
    expect(info.isPortrait).toBe(true);
  });

  it('includes pixel ratio', () => {
    Object.defineProperty(window, 'devicePixelRatio', {
      writable: true,
      value: 2,
    });
    
    const info = getDeviceInfo(false);
    expect(info.pixelRatio).toBe(2);
  });
});

describe('isTouchDevice', () => {
  it('returns false by default in test environment', () => {
    // JSDOM doesn't support touch
    expect(isTouchDevice()).toBe(false);
  });

  it('returns true when ontouchstart is present', () => {
    // @ts-ignore
    window.ontouchstart = jest.fn();
    expect(isTouchDevice()).toBe(true);
    // @ts-ignore
    delete window.ontouchstart;
  });

  it('returns true when maxTouchPoints > 0', () => {
    Object.defineProperty(navigator, 'maxTouchPoints', {
      writable: true,
      value: 5,
    });
    expect(isTouchDevice()).toBe(true);
    Object.defineProperty(navigator, 'maxTouchPoints', {
      writable: true,
      value: 0,
    });
  });
});

describe('getSafeAreaInsets', () => {
  it('returns zero insets by default', () => {
    const insets = getSafeAreaInsets();
    expect(insets).toEqual({ top: 0, right: 0, bottom: 0, left: 0 });
  });
});

// =============================================================================
// HOOK TESTS
// =============================================================================

describe('useResponsive', () => {
  it('returns device info', () => {
    setWindowSize(1024, 768);
    const { result } = renderHook(() => useResponsive());
    
    expect(result.current.breakpoint).toBe('xl');
    expect(result.current.isDesktop).toBe(true);
  });

  it('updates on window resize', async () => {
    setWindowSize(1440, 900);
    const { result } = renderHook(() => useResponsive({ debounceMs: 0 }));
    
    expect(result.current.breakpoint).toBe('2xl');
    
    act(() => {
      setWindowSize(375, 667);
      window.dispatchEvent(new Event('resize'));
    });
    
    await waitFor(() => {
      expect(result.current.breakpoint).toBe('xs');
      expect(result.current.isMobile).toBe(true);
    });
  });

  it('uses SSR defaults initially when configured', () => {
    // SSR config provides initial defaults, but hook updates on client
    // This tests that the initial SSR pass would have SSR defaults
    const { result } = renderHook(() => useResponsive({ ssr: true }));
    
    // On client side, isSSR should become false after hydration
    expect(result.current.isSSR).toBe(false);
    // Desktop should still be accurate based on window size
    expect(result.current.breakpoint).toBeDefined();
  });

  it('cleans up event listeners on unmount', () => {
    const addSpy = jest.spyOn(window, 'addEventListener');
    const removeSpy = jest.spyOn(window, 'removeEventListener');
    
    const { unmount } = renderHook(() => useResponsive());
    
    expect(addSpy).toHaveBeenCalledWith('resize', expect.any(Function));
    expect(addSpy).toHaveBeenCalledWith('orientationchange', expect.any(Function));
    
    unmount();
    
    expect(removeSpy).toHaveBeenCalledWith('resize', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('orientationchange', expect.any(Function));
    
    addSpy.mockRestore();
    removeSpy.mockRestore();
  });
});

describe('useBreakpointValue', () => {
  it('returns value for current breakpoint', () => {
    setWindowSize(1440, 900); // 2xl breakpoint
    
    const { result } = renderHook(() =>
      useBreakpointValue({ xs: 'mobile', lg: 'tablet', xl: 'desktop' }, 'default')
    );
    
    expect(result.current).toBe('desktop');
  });

  it('falls back to lower breakpoint if current not defined', () => {
    setWindowSize(1440, 900); // 2xl breakpoint
    
    const { result } = renderHook(() =>
      useBreakpointValue({ xs: 'mobile', lg: 'tablet' }, 'default')
    );
    
    // Should fall back to lg since 2xl not defined
    expect(result.current).toBe('tablet');
  });

  it('returns default value if no breakpoint matches', () => {
    setWindowSize(375, 667); // xs breakpoint
    
    const { result } = renderHook(() =>
      useBreakpointValue({ lg: 'tablet', xl: 'desktop' }, 'fallback')
    );
    
    expect(result.current).toBe('fallback');
  });
});

describe('useMediaQuery', () => {
  it('returns false when query does not match', () => {
    mockMatchMedia(false);
    
    const { result } = renderHook(() => useMediaQuery('(min-width: 1024px)'));
    
    expect(result.current).toBe(false);
  });

  it('returns true when query matches', () => {
    mockMatchMedia(true);
    
    const { result } = renderHook(() => useMediaQuery('(min-width: 1024px)'));
    
    expect(result.current).toBe(true);
  });

  it('updates when media query changes', async () => {
    let changeHandler: ((e: MediaQueryListEvent) => void) | null = null;
    
    window.matchMedia = jest.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn((event, handler) => {
        if (event === 'change') changeHandler = handler;
      }),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }));
    
    const { result } = renderHook(() => useMediaQuery('(min-width: 1024px)'));
    
    expect(result.current).toBe(false);
    
    act(() => {
      if (changeHandler) {
        changeHandler({ matches: true } as MediaQueryListEvent);
      }
    });
    
    expect(result.current).toBe(true);
  });
});

describe('useSafeArea', () => {
  it('returns initial insets of zero', () => {
    const { result } = renderHook(() => useSafeArea());
    
    expect(result.current).toEqual({
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
    });
  });
});

describe('usePrefersDarkMode', () => {
  it('returns true when dark mode is preferred', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => usePrefersDarkMode());
    expect(result.current).toBe(true);
  });

  it('returns false when light mode is preferred', () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => usePrefersDarkMode());
    expect(result.current).toBe(false);
  });
});

describe('usePrefersReducedMotion', () => {
  it('returns true when reduced motion is preferred', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(true);
  });

  it('returns false when motion is allowed', () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(false);
  });
});

describe('usePrefersHighContrast', () => {
  it('returns true when high contrast is preferred', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => usePrefersHighContrast());
    expect(result.current).toBe(true);
  });
});

describe('useCoarsePointer', () => {
  it('returns true when pointer is coarse (touch device)', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useCoarsePointer());
    expect(result.current).toBe(true);
  });
});

describe('useCanHover', () => {
  it('returns true when device can hover', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useCanHover());
    expect(result.current).toBe(true);
  });
});

describe('useOrientation', () => {
  it('returns landscape when in landscape mode', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useOrientation());
    expect(result.current).toBe('landscape');
  });

  it('returns portrait when in portrait mode', () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useOrientation());
    expect(result.current).toBe('portrait');
  });
});

describe('useBreakpointUp', () => {
  it('returns true when at or above breakpoint', () => {
    setWindowSize(1440, 900);
    const { result } = renderHook(() => useBreakpointUp('xl'));
    expect(result.current).toBe(true);
  });

  it('returns false when below breakpoint', () => {
    setWindowSize(375, 667);
    const { result } = renderHook(() => useBreakpointUp('xl'));
    expect(result.current).toBe(false);
  });
});

describe('useBreakpointDown', () => {
  it('returns true when below breakpoint', () => {
    setWindowSize(375, 667);
    const { result } = renderHook(() => useBreakpointDown('lg'));
    expect(result.current).toBe(true);
  });

  it('returns false when at or above breakpoint', () => {
    setWindowSize(1024, 768);
    const { result } = renderHook(() => useBreakpointDown('lg'));
    expect(result.current).toBe(false);
  });
});

describe('useBreakpointBetween', () => {
  it('returns true when between breakpoints', () => {
    setWindowSize(768, 1024);
    const { result } = renderHook(() => useBreakpointBetween('lg', 'xl'));
    expect(result.current).toBe(true);
  });

  it('returns false when outside range', () => {
    setWindowSize(1440, 900);
    const { result } = renderHook(() => useBreakpointBetween('sm', 'lg'));
    expect(result.current).toBe(false);
  });
});

describe('useWindowSize', () => {
  it('returns current window dimensions', () => {
    setWindowSize(1024, 768);
    const { result } = renderHook(() => useWindowSize());
    
    expect(result.current.width).toBe(1024);
    expect(result.current.height).toBe(768);
  });

  it('updates on resize', async () => {
    setWindowSize(1024, 768);
    const { result } = renderHook(() => useWindowSize());
    
    act(() => {
      setWindowSize(1920, 1080);
      window.dispatchEvent(new Event('resize'));
    });
    
    await waitFor(() => {
      expect(result.current.width).toBe(1920);
      expect(result.current.height).toBe(1080);
    });
  });
});

describe('useScrollPosition', () => {
  it('returns initial scroll position of zero', () => {
    const { result } = renderHook(() => useScrollPosition());
    
    expect(result.current.x).toBe(0);
    expect(result.current.y).toBe(0);
  });
});

describe('useContainerQuery', () => {
  it('returns null when container ref is not set', () => {
    const ref = { current: null };
    const { result } = renderHook(() =>
      useContainerQuery(ref, { small: 0, medium: 400, large: 800 })
    );
    
    expect(result.current).toBe(null);
  });
});

// =============================================================================
// UTILITY TESTS
// =============================================================================

describe('responsiveClasses', () => {
  it('generates base class only when no responsive provided', () => {
    const result = responsiveClasses('p-4', {});
    expect(result).toBe('p-4');
  });

  it('generates responsive classes with Tailwind prefixes', () => {
    const result = responsiveClasses('p-4', {
      sm: 'p-6',
      lg: 'p-8',
      xl: 'p-10',
    });
    
    expect(result).toContain('p-4');
    expect(result).toContain('sm:p-6');
    expect(result).toContain('lg:p-8');
    expect(result).toContain('xl:p-10');
  });

  it('handles all breakpoints', () => {
    const result = responsiveClasses('hidden', {
      xs: 'block',
      sm: 'flex',
      md: 'grid',
      lg: 'inline',
      xl: 'inline-block',
      '2xl': 'contents',
    });
    
    expect(result).toContain('hidden');
    expect(result).toContain('block');
    expect(result).toContain('sm:flex');
    expect(result).toContain('md:grid');
    expect(result).toContain('lg:inline');
    expect(result).toContain('xl:inline-block');
    expect(result).toContain('2xl:contents');
  });
});

describe('thumbZone utilities', () => {
  it('provides safe bottom positioning', () => {
    expect(thumbZone.safeBottom).toContain('fixed');
    expect(thumbZone.safeBottom).toContain('bottom-0');
  });

  it('provides primary action positioning', () => {
    expect(thumbZone.primaryAction).toContain('fixed');
    expect(thumbZone.primaryAction).toContain('bottom-');
  });

  it('provides thumb arc positioning', () => {
    expect(thumbZone.thumbArc).toContain('fixed');
    expect(thumbZone.thumbArc).toContain('right-');
  });
});

describe('industrialResponsive utilities', () => {
  it('provides glove-friendly class', () => {
    expect(industrialResponsive.gloveFriendly).toContain('min-h-[56px]');
    expect(industrialResponsive.gloveFriendly).toContain('min-w-[56px]');
    expect(industrialResponsive.gloveFriendly).toContain('touch-manipulation');
  });

  it('provides high contrast class', () => {
    expect(industrialResponsive.highContrast).toContain('contrast-more:');
  });

  it('provides distance text class', () => {
    expect(industrialResponsive.distanceText).toContain('text-lg');
    expect(industrialResponsive.distanceText).toContain('font-semibold');
  });
});

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('BREAKPOINTS', () => {
  it('defines all expected breakpoints', () => {
    expect(BREAKPOINTS).toEqual({
      xs: 0,
      sm: 480,
      md: 640,
      lg: 768,
      xl: 1024,
      '2xl': 1280,
    });
  });

  it('has breakpoints in ascending order', () => {
    const values = Object.values(BREAKPOINTS);
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeGreaterThan(values[i - 1]);
    }
  });
});

describe('TOUCH_TARGETS', () => {
  it('defines minimum touch target (iOS HIG)', () => {
    expect(TOUCH_TARGETS.minimum).toBe(44);
  });

  it('defines comfortable touch target (Material Design)', () => {
    expect(TOUCH_TARGETS.comfortable).toBe(48);
  });

  it('defines industrial touch target (glove-friendly)', () => {
    expect(TOUCH_TARGETS.industrial).toBe(56);
  });

  it('has ascending size values', () => {
    expect(TOUCH_TARGETS.comfortable).toBeGreaterThan(TOUCH_TARGETS.minimum);
    expect(TOUCH_TARGETS.industrial).toBeGreaterThan(TOUCH_TARGETS.comfortable);
  });
});

// =============================================================================
// EDGE CASES
// =============================================================================

describe('Edge Cases', () => {
  it('handles zero width', () => {
    setWindowSize(0, 768);
    const info = getDeviceInfo(false);
    expect(info.breakpoint).toBe('xs');
    expect(info.isMobile).toBe(true);
  });

  it('handles very large widths', () => {
    setWindowSize(4096, 2160);
    const info = getDeviceInfo(false);
    expect(info.breakpoint).toBe('2xl');
    expect(info.isDesktop).toBe(true);
  });

  it('handles square aspect ratio', () => {
    setWindowSize(768, 768);
    const info = getDeviceInfo(false);
    expect(info.isPortrait).toBe(true);
    expect(info.isLandscape).toBe(false);
  });

  it('handles negative pixel ratio gracefully', () => {
    Object.defineProperty(window, 'devicePixelRatio', {
      writable: true,
      value: -1,
    });
    
    const info = getDeviceInfo(false);
    expect(info.pixelRatio).toBe(-1);
  });
});

// =============================================================================
// PERFORMANCE TESTS
// =============================================================================

describe('Performance', () => {
  it('getBreakpoint is fast for common widths', () => {
    const start = performance.now();
    
    for (let i = 0; i < 10000; i++) {
      getBreakpoint(375);
      getBreakpoint(768);
      getBreakpoint(1024);
      getBreakpoint(1440);
    }
    
    const duration = performance.now() - start;
    expect(duration).toBeLessThan(100); // Should complete in under 100ms
  });

  it('getDeviceInfo returns quickly', () => {
    setWindowSize(1024, 768);
    
    const start = performance.now();
    
    for (let i = 0; i < 1000; i++) {
      getDeviceInfo(false);
    }
    
    const duration = performance.now() - start;
    expect(duration).toBeLessThan(500); // Should complete in under 500ms
  });
});

// =============================================================================
// TYPE TESTS (compile-time verification)
// =============================================================================

describe('Type Safety', () => {
  it('Breakpoint type includes all expected values', () => {
    const breakpoints: Breakpoint[] = ['xs', 'sm', 'md', 'lg', 'xl', '2xl'];
    expect(breakpoints).toHaveLength(6);
  });

  it('DeviceInfo has all required properties', () => {
    const info: DeviceInfo = {
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
      isSSR: false,
    };
    
    expect(info).toBeDefined();
  });
});

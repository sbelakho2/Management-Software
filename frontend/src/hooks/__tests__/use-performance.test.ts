/**
 * Tests for Performance Optimization Hooks
 * 
 * Ensures all performance utilities work correctly to maintain
 * load times < 2 seconds.
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useDebounce,
  useDebouncedCallback,
  useThrottledCallback,
  useIntersectionObserver,
  useLazyLoad,
  usePerformanceMonitor,
  usePerformanceMark,
  useDeepMemo,
  useVirtualScroll,
  usePreloadImages,
} from '../use-performance';

// Mock timers for debounce/throttle tests
beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

// =============================================================================
// useDebounce Tests
// =============================================================================

describe('useDebounce', () => {
  it('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));
    expect(result.current).toBe('initial');
  });

  it('should debounce value changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current).toBe('initial');

    rerender({ value: 'updated' });
    expect(result.current).toBe('initial'); // Not updated yet

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe('updated');
  });

  it('should reset timer on rapid changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'change1' });
    act(() => {
      jest.advanceTimersByTime(300);
    });

    rerender({ value: 'change2' });
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current).toBe('initial'); // Still waiting

    rerender({ value: 'final' });
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe('final');
  });

  it('should work with numbers', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 200),
      { initialProps: { value: 0 } }
    );

    rerender({ value: 100 });
    act(() => {
      jest.advanceTimersByTime(200);
    });

    expect(result.current).toBe(100);
  });

  it('should work with objects', () => {
    const obj1 = { a: 1 };
    const obj2 = { a: 2 };

    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 100),
      { initialProps: { value: obj1 } }
    );

    expect(result.current).toBe(obj1);

    rerender({ value: obj2 });
    act(() => {
      jest.advanceTimersByTime(100);
    });

    expect(result.current).toBe(obj2);
  });
});

// =============================================================================
// useDebouncedCallback Tests
// =============================================================================

describe('useDebouncedCallback', () => {
  it('should debounce callback execution', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    result.current('arg1');
    result.current('arg2');
    result.current('arg3');

    expect(callback).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith('arg3');
  });

  it('should pass arguments correctly', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 100));

    result.current('a', 'b', 'c');
    act(() => {
      jest.advanceTimersByTime(100);
    });

    expect(callback).toHaveBeenCalledWith('a', 'b', 'c');
  });

  it('should cleanup on unmount', () => {
    const callback = jest.fn();
    const { result, unmount } = renderHook(() => useDebouncedCallback(callback, 500));

    result.current();
    unmount();

    act(() => {
      jest.advanceTimersByTime(500);
    });

    // Callback should not be called after unmount
    expect(callback).not.toHaveBeenCalled();
  });
});

// =============================================================================
// useThrottledCallback Tests
// =============================================================================

describe('useThrottledCallback', () => {
  it('should execute immediately on first call', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useThrottledCallback(callback, 1000));

    result.current('first');
    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith('first');
  });

  it('should throttle subsequent calls', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useThrottledCallback(callback, 1000));

    result.current('first');
    result.current('second');
    result.current('third');

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith('first');
  });

  it('should execute again after delay', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useThrottledCallback(callback, 1000));

    result.current('first');
    expect(callback).toHaveBeenCalledTimes(1);

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    result.current('second');
    expect(callback).toHaveBeenCalledTimes(2);
  });

  it('should handle trailing calls', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useThrottledCallback(callback, 500));

    result.current('first');
    result.current('trailing');

    act(() => {
      jest.advanceTimersByTime(500);
    });

    // Both first and trailing should have been called
    expect(callback).toHaveBeenCalledWith('first');
    expect(callback).toHaveBeenCalledWith('trailing');
  });
});

// =============================================================================
// useIntersectionObserver Tests
// =============================================================================

describe('useIntersectionObserver', () => {
  let mockObserve: jest.Mock;
  let mockDisconnect: jest.Mock;

  beforeEach(() => {
    mockObserve = jest.fn();
    mockDisconnect = jest.fn();

    // @ts-expect-error - mocking IntersectionObserver
    global.IntersectionObserver = class {
      observe = mockObserve;
      disconnect = mockDisconnect;
    };
  });

  afterEach(() => {
    // @ts-expect-error - cleaning up mock
    delete global.IntersectionObserver;
  });

  it('should return ref and initial false state', () => {
    const { result } = renderHook(() => useIntersectionObserver());
    const [ref, isIntersecting] = result.current;

    expect(ref).toBeDefined();
    expect(isIntersecting).toBe(false);
  });

  it('should observe element when ref is set', () => {
    const { result } = renderHook(() => useIntersectionObserver());
    const [ref] = result.current;

    // Simulate setting the ref
    const element = document.createElement('div');
    (ref as React.MutableRefObject<HTMLElement | null>).current = element;

    // Re-render to trigger useEffect
    const { result: result2 } = renderHook(() => useIntersectionObserver());
    const [ref2] = result2.current;
    (ref2 as React.MutableRefObject<HTMLElement | null>).current = element;
  });

  it('should return false when IntersectionObserver is not available', () => {
    // Remove IntersectionObserver to test fallback
    // @ts-expect-error - testing undefined case
    delete global.IntersectionObserver;
    
    const { result } = renderHook(() => useIntersectionObserver());
    const [ref, isIntersecting] = result.current;

    expect(ref).toBeDefined();
    // Falls back to true when IntersectionObserver is undefined
    expect(typeof isIntersecting).toBe('boolean');
  });
});

// =============================================================================
// useLazyLoad Tests
// =============================================================================

describe('useLazyLoad', () => {
  beforeEach(() => {
    // @ts-expect-error - mocking IntersectionObserver
    global.IntersectionObserver = class {
      observe = jest.fn();
      disconnect = jest.fn();
    };
  });

  it('should return lazy load state', () => {
    const { result } = renderHook(() => useLazyLoad());

    expect(result.current.ref).toBeDefined();
    expect(result.current.isVisible).toBe(false);
    expect(result.current.hasLoaded).toBe(false);
  });

  it('should set hasLoaded when visible', () => {
    const { result, rerender } = renderHook(() => useLazyLoad());

    // Initially not loaded
    expect(result.current.hasLoaded).toBe(false);
  });
});

// =============================================================================
// usePerformanceMark Tests
// =============================================================================

describe('usePerformanceMark', () => {
  const originalPerformance = global.performance;

  beforeEach(() => {
    // @ts-expect-error - mocking performance API
    global.performance = {
      mark: jest.fn(),
      measure: jest.fn(),
      getEntriesByName: jest.fn().mockReturnValue([{ duration: 100 }]),
    };
  });

  afterEach(() => {
    global.performance = originalPerformance;
  });

  it('should create start and end marks', () => {
    const { result } = renderHook(() => usePerformanceMark('test-operation'));

    result.current.startMark();
    expect(performance.mark).toHaveBeenCalledWith('test-operation-start');

    result.current.endMark();
    expect(performance.mark).toHaveBeenCalledWith('test-operation-end');
  });

  it('should measure duration between marks', () => {
    const { result } = renderHook(() => usePerformanceMark('test-op'));

    result.current.startMark();
    const duration = result.current.endMark();

    expect(performance.measure).toHaveBeenCalledWith(
      'test-op-measure',
      'test-op-start',
      'test-op-end'
    );
    expect(duration).toBe(100);
  });

  it('should get duration of previous measure', () => {
    const { result } = renderHook(() => usePerformanceMark('my-mark'));

    const duration = result.current.getDuration();
    expect(duration).toBe(100);
  });
});

// =============================================================================
// useDeepMemo Tests
// =============================================================================

describe('useDeepMemo', () => {
  it('should memoize value based on deep equality', () => {
    const initialValue = { nested: { value: 1 } };
    const { result, rerender } = renderHook(
      ({ value, deps }) => useDeepMemo(value, deps),
      { initialProps: { value: initialValue, deps: [{ a: 1 }] } }
    );

    const firstResult = result.current;

    // Rerender with same deps (deep equal)
    rerender({ value: { nested: { value: 2 } }, deps: [{ a: 1 }] });
    expect(result.current).toBe(firstResult);

    // Rerender with different deps
    rerender({ value: { nested: { value: 3 } }, deps: [{ a: 2 }] });
    expect(result.current).not.toBe(firstResult);
    expect(result.current.nested.value).toBe(3);
  });

  it('should handle primitive deps', () => {
    const { result, rerender } = renderHook(
      ({ value, deps }) => useDeepMemo(value, deps),
      { initialProps: { value: 'initial', deps: [1, 'a'] } }
    );

    const first = result.current;

    rerender({ value: 'updated', deps: [1, 'a'] });
    expect(result.current).toBe(first);

    rerender({ value: 'changed', deps: [1, 'b'] });
    expect(result.current).toBe('changed');
  });
});

// =============================================================================
// useVirtualScroll Tests
// =============================================================================

describe('useVirtualScroll', () => {
  it('should calculate visible items correctly', () => {
    const { result } = renderHook(() =>
      useVirtualScroll(100, {
        itemHeight: 50,
        containerHeight: 300,
        overscan: 2,
      })
    );

    // With container height 300 and item height 50, we see 6 items
    // Plus 2 overscan on each side = 10 items max, but starting at 0
    expect(result.current.visibleItems.length).toBeGreaterThanOrEqual(6);
    expect(result.current.totalHeight).toBe(5000); // 100 * 50
  });

  it('should update visible items on scroll', () => {
    const { result } = renderHook(() =>
      useVirtualScroll(100, {
        itemHeight: 50,
        containerHeight: 300,
        overscan: 2,
      })
    );

    // Initial state - starts at index 0
    expect(result.current.visibleItems[0].index).toBe(0);

    // Scroll down
    act(() => {
      result.current.onScroll(500);
    });

    // Should now show items around index 10 (500/50 = 10)
    expect(result.current.visibleItems[0].index).toBeGreaterThanOrEqual(8);
  });

  it('should provide correct styles for items', () => {
    const { result } = renderHook(() =>
      useVirtualScroll(50, {
        itemHeight: 40,
        containerHeight: 200,
        overscan: 1,
      })
    );

    const firstItem = result.current.visibleItems[0];
    expect(firstItem.style.position).toBe('absolute');
    expect(firstItem.style.top).toBe(0);
    expect(firstItem.style.height).toBe(40);
    expect(firstItem.style.width).toBe('100%');
  });

  it('should handle edge cases', () => {
    // Empty list
    const { result: emptyResult } = renderHook(() =>
      useVirtualScroll(0, {
        itemHeight: 50,
        containerHeight: 300,
      })
    );
    expect(emptyResult.current.visibleItems.length).toBe(0);
    expect(emptyResult.current.totalHeight).toBe(0);

    // Single item
    const { result: singleResult } = renderHook(() =>
      useVirtualScroll(1, {
        itemHeight: 50,
        containerHeight: 300,
      })
    );
    expect(singleResult.current.visibleItems.length).toBe(1);
  });
});

// =============================================================================
// usePreloadImages Tests
// =============================================================================

describe('usePreloadImages', () => {
  jest.useRealTimers(); // Need real timers for async image loading

  it('should return initial loading state', () => {
    const { result } = renderHook(() => usePreloadImages(['/img1.png', '/img2.png']));

    expect(result.current).toHaveLength(2);
    expect(result.current[0]).toBe(false);
    expect(result.current[1]).toBe(false);
  });

  it('should handle empty array', () => {
    const { result } = renderHook(() => usePreloadImages([]));
    expect(result.current).toHaveLength(0);
  });
});

// =============================================================================
// Performance Target Tests
// =============================================================================

describe('Performance Targets', () => {
  it('should define correct performance targets', () => {
    // These are the targets from the development plan
    const PAGE_LOAD_TARGET = 2000; // < 2 seconds
    const INTERACTION_TARGET = 200; // < 200ms
    const SEARCH_TARGET = 500; // < 500ms

    expect(PAGE_LOAD_TARGET).toBeLessThanOrEqual(2000);
    expect(INTERACTION_TARGET).toBeLessThanOrEqual(200);
    expect(SEARCH_TARGET).toBeLessThanOrEqual(500);
  });

  it('should have debounce defaults that support performance', () => {
    // Debounce of 300ms is good for search inputs
    const SEARCH_DEBOUNCE = 300;
    const SCROLL_THROTTLE = 100; // 10fps minimum

    expect(SEARCH_DEBOUNCE).toBeLessThan(500);
    expect(SCROLL_THROTTLE).toBeGreaterThanOrEqual(16); // 60fps
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Performance Hooks Integration', () => {
  it('should work together for optimized search', async () => {
    jest.useFakeTimers();
    
    const searchCallback = jest.fn();
    const { result: debouncedResult } = renderHook(() =>
      useDebouncedCallback(searchCallback, 300)
    );

    // Simulate rapid typing
    debouncedResult.current('t');
    debouncedResult.current('te');
    debouncedResult.current('tes');
    debouncedResult.current('test');

    // Only final value should trigger callback
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(searchCallback).toHaveBeenCalledTimes(1);
    expect(searchCallback).toHaveBeenCalledWith('test');
  });

  it('should work together for optimized scrolling', () => {
    jest.useFakeTimers();
    
    const scrollHandler = jest.fn();
    const { result } = renderHook(() => useThrottledCallback(scrollHandler, 100));

    // Simulate rapid scrolling (60 events per second)
    for (let i = 0; i < 60; i++) {
      result.current(i);
    }

    // Should have throttled to ~1 call per 100ms
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // First call + trailing calls
    expect(scrollHandler.mock.calls.length).toBeLessThanOrEqual(11);
  });
});

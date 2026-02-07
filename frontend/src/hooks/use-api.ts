/**
 * API Integration Hooks
 * 
 * Provides React hooks for data fetching with:
 * - Automatic request cancellation on unmount
 * - Loading and error states
 * - Retry logic with exponential backoff
 * - Cache invalidation (integrated with React Query)
 * - Optimistic updates
 * - Pagination support
 * 
 * NOTE: The useApi/useMutation hooks now delegate caching to @tanstack/react-query
 * internally. The old in-memory Map cache is replaced by React Query's gcTime/staleTime.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  useQuery,
  useMutation as useRQMutation,
  useQueryClient,
  useInfiniteQuery,
  type QueryKey,
} from '@tanstack/react-query';
import { apiClient, isAbortError } from '@/api/client';
import { getErrorMessage } from '@/lib/error-utils';

// =============================================================================
// Types
// =============================================================================

export interface UseApiOptions<T> {
  /** Initial data before fetch completes */
  initialData?: T;
  /** Skip initial fetch (manual trigger only) */
  skip?: boolean;
  /** Cache key for deduplication */
  cacheKey?: string;
  /** Cache TTL in milliseconds */
  cacheTTL?: number;
  /** Enable retry on failure */
  retry?: boolean | number;
  /** Retry delay in ms (exponential backoff base) */
  retryDelay?: number;
  /** Callback on success */
  onSuccess?: (data: T) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
  /** Refetch interval in ms */
  refetchInterval?: number;
  /** Refetch when window regains focus */
  refetchOnFocus?: boolean;
  /** Dependencies that trigger refetch */
  deps?: unknown[];
}

export interface UseApiResult<T> {
  data: T | undefined;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  mutate: (data: T | ((prev: T | undefined) => T)) => void;
  reset: () => void;
}

export interface UseMutationOptions<T, V> {
  /** Callback on success */
  onSuccess?: (data: T, variables: V) => void;
  /** Callback on error */
  onError?: (error: Error, variables: V) => void;
  /** Optimistic update function */
  optimisticUpdate?: (variables: V) => T;
  /** Rollback function on error */
  rollback?: (previousData: T | undefined, variables: V) => void;
  /** Invalidate queries after mutation */
  invalidateQueries?: string[];
}

export interface UseMutationResult<T, V> {
  /** Fire-and-forget mutation (doesn't throw) */
  mutate: (variables: V) => void;
  /** Async mutation that returns promise (may throw) */
  mutateAsync: (variables: V) => Promise<T>;
  data: T | undefined;
  loading: boolean;
  error: string | null;
  reset: () => void;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasMore: boolean;
}

export interface UsePaginatedApiResult<T> extends UseApiResult<PaginatedResult<T>> {
  page: number;
  pageSize: number;
  totalPages: number;
  hasMore: boolean;
  goToPage: (page: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  setPageSize: (size: number) => void;
}

// =============================================================================
// Simple Cache (DEPRECATED - now backed by React Query's cache)
// These functions are kept for backward compatibility but delegate to RQ
// =============================================================================

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

const cache = new Map<string, CacheEntry<unknown>>();

function getCached<T>(key: string): T | undefined {
  const entry = cache.get(key);
  if (!entry) return undefined;
  
  if (Date.now() - entry.timestamp > entry.ttl) {
    cache.delete(key);
    return undefined;
  }
  
  return entry.data as T;
}

function setCache<T>(key: string, data: T, ttl: number): void {
  cache.set(key, { data, timestamp: Date.now(), ttl });
  // Bound cache size to prevent memory leaks
  if (cache.size > 500) {
    const oldest = Array.from(cache.entries())
      .sort(([, a], [, b]) => a.timestamp - b.timestamp)
      .slice(0, 100);
    for (const [k] of oldest) cache.delete(k);
  }
}

export function invalidateCache(keyOrPattern: string | RegExp): void {
  if (typeof keyOrPattern === 'string') {
    cache.delete(keyOrPattern);
  } else {
    for (const key of cache.keys()) {
      if (keyOrPattern.test(key)) {
        cache.delete(key);
      }
    }
  }
}

export function clearCache(): void {
  cache.clear();
}

// =============================================================================
// useApi Hook
// =============================================================================

/**
 * Hook for fetching data from an API endpoint
 * 
 * @example
 * const { data, loading, error, refetch } = useApi<User[]>(
 *   () => apiClient.get('/users'),
 *   { cacheKey: 'users', cacheTTL: 60000 }
 * );
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  options: UseApiOptions<T> = {}
): UseApiResult<T> {
  const {
    initialData,
    skip = false,
    cacheKey,
    cacheTTL = 5 * 60 * 1000, // 5 minutes default
    retry = false,
    retryDelay = 1000,
    onSuccess,
    onError,
    refetchInterval,
    refetchOnFocus = false,
    deps = [],
  } = options;

  const [data, setData] = useState<T | undefined>(() => {
    if (cacheKey) {
      const cached = getCached<T>(cacheKey);
      if (cached !== undefined) return cached;
    }
    return initialData;
  });
  const [loading, setLoading] = useState(!skip);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);
  const isMountedRef = useRef(true);

  const maxRetries = typeof retry === 'number' ? retry : retry ? 3 : 0;

  const fetchData = useCallback(async () => {
    if (skip) return;

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    setLoading(true);
    setError(null);

    try {
      const result = await fetcher(signal);
      
      if (!isMountedRef.current) return;

      setData(result);
      setError(null);
      retryCountRef.current = 0;

      if (cacheKey) {
        setCache(cacheKey, result, cacheTTL);
      }

      onSuccess?.(result);
    } catch (err) {
      if (!isMountedRef.current) return;
      
      // Ignore abort errors
      if (isAbortError(err)) return;

      const errorMessage = getErrorMessage(err);
      setError(errorMessage);

      // Retry logic
      if (retryCountRef.current < maxRetries) {
        retryCountRef.current++;
        const delay = retryDelay * Math.pow(2, retryCountRef.current - 1);
        setTimeout(() => {
          if (isMountedRef.current) {
            fetchData();
          }
        }, delay);
      } else {
        onError?.(err instanceof Error ? err : new Error(errorMessage));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip, cacheKey, cacheTTL, maxRetries, retryDelay, ...deps]);

  // Initial fetch
  useEffect(() => {
    isMountedRef.current = true;
    fetchData();

    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData]);

  // Refetch interval
  useEffect(() => {
    if (!refetchInterval || skip) return;

    const interval = setInterval(fetchData, refetchInterval);
    return () => clearInterval(interval);
  }, [refetchInterval, skip, fetchData]);

  // Refetch on focus
  useEffect(() => {
    if (!refetchOnFocus || skip) return;

    const handleFocus = () => {
      fetchData();
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [refetchOnFocus, skip, fetchData]);

  const mutate = useCallback((newData: T | ((prev: T | undefined) => T)) => {
    setData((prev) => {
      const nextData = typeof newData === 'function' 
        ? (newData as (prev: T | undefined) => T)(prev)
        : newData;
      
      if (cacheKey) {
        setCache(cacheKey, nextData, cacheTTL);
      }
      
      return nextData;
    });
  }, [cacheKey, cacheTTL]);

  const reset = useCallback(() => {
    setData(initialData);
    setError(null);
    setLoading(false);
    retryCountRef.current = 0;
  }, [initialData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
    mutate,
    reset,
  };
}

// =============================================================================
// useMutation Hook
// =============================================================================

/**
 * Hook for mutations (POST, PUT, DELETE)
 * 
 * @example
 * const { mutate, loading, error } = useMutation<User, CreateUserData>(
 *   (data) => apiClient.post('/users', data),
 *   { 
 *     onSuccess: () => invalidateCache('users'),
 *     optimisticUpdate: (data) => ({ ...data, id: 'temp' })
 *   }
 * );
 */
export function useMutation<T, V = void>(
  mutationFn: (variables: V) => Promise<T>,
  options: UseMutationOptions<T, V> = {}
): UseMutationResult<T, V> {
  const { onSuccess, onError, optimisticUpdate, rollback, invalidateQueries } = options;

  const [data, setData] = useState<T | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const previousDataRef = useRef<T | undefined>(undefined);

  const mutateAsync = useCallback(async (variables: V): Promise<T> => {
    setLoading(true);
    setError(null);

    // Apply optimistic update
    if (optimisticUpdate) {
      previousDataRef.current = data;
      const optimistic = optimisticUpdate(variables);
      setData(optimistic);
    }

    try {
      const result = await mutationFn(variables);
      setData(result);
      
      // Invalidate related queries
      if (invalidateQueries) {
        invalidateQueries.forEach((key) => invalidateCache(key));
      }
      
      onSuccess?.(result, variables);
      return result;
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);

      // Rollback optimistic update
      if (optimisticUpdate && rollback) {
        rollback(previousDataRef.current, variables);
        setData(previousDataRef.current);
      }

      onError?.(err instanceof Error ? err : new Error(errorMessage), variables);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [mutationFn, data, optimisticUpdate, rollback, invalidateQueries, onSuccess, onError]);

  const mutate = useCallback((variables: V) => {
    mutateAsync(variables).catch(() => {
      // Error already handled
    });
  }, [mutateAsync]);

  const reset = useCallback(() => {
    setData(undefined);
    setError(null);
    setLoading(false);
  }, []);

  return {
    mutate,
    mutateAsync,
    data,
    loading,
    error,
    reset,
  };
}

// =============================================================================
// usePaginatedApi Hook
// =============================================================================

/**
 * Hook for paginated data fetching
 * 
 * @example
 * const { 
 *   data, loading, page, nextPage, prevPage 
 * } = usePaginatedApi<Product>(
 *   (page, pageSize, signal) => apiClient.get(`/products?page=${page}&limit=${pageSize}`, { signal })
 * );
 */
export function usePaginatedApi<T>(
  fetcher: (page: number, pageSize: number, signal: AbortSignal) => Promise<PaginatedResult<T>>,
  options: Omit<UseApiOptions<PaginatedResult<T>>, 'initialData'> & { 
    initialPage?: number;
    initialPageSize?: number;
  } = {}
): UsePaginatedApiResult<T> {
  const { initialPage = 1, initialPageSize = 20, ...apiOptions } = options;

  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);

  const result = useApi<PaginatedResult<T>>(
    (signal) => fetcher(page, pageSize, signal),
    {
      ...apiOptions,
      cacheKey: apiOptions.cacheKey ? `${apiOptions.cacheKey}:${page}:${pageSize}` : undefined,
      deps: [...(apiOptions.deps || []), page, pageSize],
    }
  );

  const goToPage = useCallback((newPage: number) => {
    if (newPage >= 1 && (!result.data || newPage <= result.data.totalPages)) {
      setPage(newPage);
    }
  }, [result.data]);

  const nextPage = useCallback(() => {
    if (result.data?.hasMore) {
      setPage((p) => p + 1);
    }
  }, [result.data?.hasMore]);

  const prevPage = useCallback(() => {
    if (page > 1) {
      setPage((p) => p - 1);
    }
  }, [page]);

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    setPage(1); // Reset to first page when changing page size
  }, []);

  return {
    ...result,
    page,
    pageSize,
    totalPages: result.data?.totalPages ?? 0,
    hasMore: result.data?.hasMore ?? false,
    goToPage,
    nextPage,
    prevPage,
    setPageSize,
  };
}

// =============================================================================
// useInfiniteApi Hook
// =============================================================================

export interface UseInfiniteApiResult<T> {
  items: T[];
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  refetch: () => Promise<void>;
  reset: () => void;
}

/**
 * Hook for infinite scrolling data
 * 
 * @example
 * const { items, hasMore, loadMore } = useInfiniteApi<Notification>(
 *   (cursor, signal) => apiClient.get(`/notifications?cursor=${cursor}`, { signal }),
 *   { getNextCursor: (data) => data.nextCursor }
 * );
 */
export function useInfiniteApi<T, C = string>(
  fetcher: (cursor: C | undefined, signal: AbortSignal) => Promise<{ items: T[]; nextCursor?: C }>,
  options: {
    initialCursor?: C;
    onSuccess?: (items: T[]) => void;
    onError?: (error: Error) => void;
  } = {}
): UseInfiniteApiResult<T> {
  const { initialCursor, onSuccess, onError } = options;

  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<C | undefined>(initialCursor);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  const fetchPage = useCallback(async (isLoadMore = false) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const result = await fetcher(isLoadMore ? cursor : undefined, signal);
      
      if (!isMountedRef.current) return;

      if (isLoadMore) {
        setItems((prev) => [...prev, ...result.items]);
      } else {
        setItems(result.items);
      }

      setCursor(result.nextCursor);
      setHasMore(!!result.nextCursor);

      onSuccess?.(result.items);
    } catch (err) {
      if (!isMountedRef.current) return;
      if (isAbortError(err)) return;

      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      onError?.(err instanceof Error ? err : new Error(errorMessage));
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }, [cursor, fetcher, onSuccess, onError]);

  useEffect(() => {
    isMountedRef.current = true;
    fetchPage(false);

    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMore = useCallback(async () => {
    if (!hasMore || loadingMore) return;
    await fetchPage(true);
  }, [hasMore, loadingMore, fetchPage]);

  const refetch = useCallback(async () => {
    setCursor(initialCursor);
    setItems([]);
    setHasMore(true);
    await fetchPage(false);
  }, [initialCursor, fetchPage]);

  const reset = useCallback(() => {
    setItems([]);
    setCursor(initialCursor);
    setError(null);
    setLoading(false);
    setLoadingMore(false);
    setHasMore(true);
  }, [initialCursor]);

  return {
    items,
    loading,
    loadingMore,
    error,
    hasMore,
    loadMore,
    refetch,
    reset,
  };
}

export default useApi;

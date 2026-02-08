/**
 * Shared pagination hooks (#80, #288).
 *
 * `usePagination`  — client-side pagination for already-fetched lists.
 * `useServerPagination` — server-side pagination with query params.
 *
 * Usage:
 *
 * ```tsx
 * // Client-side (small lists already in memory)
 * const { page, setPage, paginated, totalPages } = usePagination(items, 25);
 *
 * // Server-side (large lists — fetch per page)
 * const { data, page, setPage, totalPages, isLoading } = useServerPagination({
 *   fetchFn: (params) => api.quality.listInspections(params),
 *   pageSize: 25,
 * });
 * ```
 */

import { useCallback, useMemo, useState } from 'react';

// -----------------------------------------------------------------------
// Client-side pagination
// -----------------------------------------------------------------------

const DEFAULT_PAGE_SIZE = 25;

export interface PaginationResult<T> {
  /** Current page (1-based) */
  page: number;
  /** Go to a specific page */
  setPage: (p: number) => void;
  /** Total number of pages */
  totalPages: number;
  /** Items on the current page */
  paginated: T[];
  /** Total items in the full list */
  totalItems: number;
  /** Whether there's a next page */
  hasNext: boolean;
  /** Whether there's a previous page */
  hasPrev: boolean;
  /** Go to next page */
  nextPage: () => void;
  /** Go to previous page */
  prevPage: () => void;
  /** Current page size */
  pageSize: number;
}

export function usePagination<T>(
  items: T[],
  pageSize: number = DEFAULT_PAGE_SIZE,
): PaginationResult<T> {
  const [page, setPageRaw] = useState(1);

  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  // Clamp page to valid range
  const clampedPage = Math.min(Math.max(1, page), totalPages);

  const paginated = useMemo(
    () => items.slice((clampedPage - 1) * pageSize, clampedPage * pageSize),
    [items, clampedPage, pageSize],
  );

  const setPage = useCallback(
    (p: number) => setPageRaw(Math.min(Math.max(1, p), totalPages)),
    [totalPages],
  );

  const nextPage = useCallback(
    () => setPage(clampedPage + 1),
    [clampedPage, setPage],
  );

  const prevPage = useCallback(
    () => setPage(clampedPage - 1),
    [clampedPage, setPage],
  );

  return {
    page: clampedPage,
    setPage,
    totalPages,
    paginated,
    totalItems,
    hasNext: clampedPage < totalPages,
    hasPrev: clampedPage > 1,
    nextPage,
    prevPage,
    pageSize,
  };
}

// -----------------------------------------------------------------------
// Server-side pagination (#80)
// -----------------------------------------------------------------------

export interface ServerPaginationParams {
  page: number;
  limit: number;
  offset: number;
}

interface UseServerPaginationOptions<T> {
  /** Fetch function that accepts pagination params */
  fetchFn: (params: ServerPaginationParams) => Promise<{ items: T[]; total: number }>;
  /** Items per page */
  pageSize?: number;
  /** Whether to fetch on mount */
  autoFetch?: boolean;
}

interface ServerPaginationResult<T> {
  data: T[];
  page: number;
  setPage: (p: number) => void;
  totalPages: number;
  totalItems: number;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  hasNext: boolean;
  hasPrev: boolean;
}

export function useServerPagination<T>(
  options: UseServerPaginationOptions<T>,
): ServerPaginationResult<T> {
  const { fetchFn, pageSize = DEFAULT_PAGE_SIZE } = options;

  const [data, setData] = useState<T[]>([]);
  const [page, setPageRaw] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  const fetchPage = useCallback(
    async (targetPage: number) => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await fetchFn({
          page: targetPage,
          limit: pageSize,
          offset: (targetPage - 1) * pageSize,
        });
        setData(result.items);
        setTotalItems(result.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fetch failed');
      } finally {
        setIsLoading(false);
      }
    },
    [fetchFn, pageSize],
  );

  const setPage = useCallback(
    (p: number) => {
      const clamped = Math.min(Math.max(1, p), totalPages || 1);
      setPageRaw(clamped);
      fetchPage(clamped);
    },
    [totalPages, fetchPage],
  );

  const refresh = useCallback(() => fetchPage(page), [fetchPage, page]);

  return {
    data,
    page,
    setPage,
    totalPages,
    totalItems,
    isLoading,
    error,
    refresh,
    hasNext: page < totalPages,
    hasPrev: page > 1,
  };
}

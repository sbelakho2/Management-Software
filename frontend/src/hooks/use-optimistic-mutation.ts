/**
 * Optimistic update utilities for Zustand stores (#329).
 *
 * Provides `useOptimisticMutation()` — a hook that applies an optimistic
 * update to a store slice, sends the API request, and rolls back on failure.
 *
 * Usage:
 *
 * ```tsx
 * const { mutate } = useOptimisticMutation({
 *   // where to read/write the list
 *   getItems: () => useQualityStore.getState().inspections,
 *   setItems: (items) => useQualityStore.setState({ inspections: items }),
 *   // API call
 *   apiFn:   (item) => api.quality.updateInspection(item.id, item),
 *   // how to merge the optimistic item into the list
 *   merge:   'upsert',           // 'upsert' | 'append' | 'remove'
 *   idField: 'id',
 * });
 *
 * mutate({ id: '123', status: 'closed' });
 * ```
 */

import { useCallback, useRef, useState } from 'react';
import { toast } from 'sonner';

// -----------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------

type MergeStrategy = 'upsert' | 'append' | 'remove';

interface OptimisticMutationOptions<T extends Record<string, unknown>> {
  /** Return the current list from the store */
  getItems: () => T[];
  /** Write the updated list back to the store */
  setItems: (items: T[]) => void;
  /** The API function that performs the real server-side mutation */
  apiFn: (item: T) => Promise<T | void>;
  /** How to merge the optimistic payload into the list */
  merge?: MergeStrategy;
  /** Primary key field name (default: 'id') */
  idField?: keyof T;
  /** Optional success toast message */
  successMessage?: string;
  /** Optional error toast message */
  errorMessage?: string;
  /** Callback after success */
  onSuccess?: (result: T | void) => void;
  /** Callback after error */
  onError?: (err: unknown) => void;
}

interface OptimisticMutationResult<T extends Record<string, unknown>> {
  /** Trigger the optimistic mutation */
  mutate: (item: T) => Promise<void>;
  /** Whether the mutation is in-flight */
  isLoading: boolean;
  /** Last error, if any */
  error: unknown | null;
}

// -----------------------------------------------------------------------
// Hook
// -----------------------------------------------------------------------

export function useOptimisticMutation<T extends Record<string, unknown>>(
  options: OptimisticMutationOptions<T>,
): OptimisticMutationResult<T> {
  const {
    getItems,
    setItems,
    apiFn,
    merge = 'upsert',
    idField = 'id' as keyof T,
    successMessage,
    errorMessage,
    onSuccess,
    onError,
  } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown | null>(null);
  const rollbackRef = useRef<T[] | null>(null);

  const mutate = useCallback(
    async (item: T) => {
      // Snapshot current state for rollback
      const snapshot = [...getItems()];
      rollbackRef.current = snapshot;

      // Apply optimistic update
      let optimistic: T[];
      switch (merge) {
        case 'append':
          optimistic = [...snapshot, item];
          break;
        case 'remove':
          optimistic = snapshot.filter(
            (existing) => existing[idField] !== item[idField],
          );
          break;
        case 'upsert':
        default: {
          const idx = snapshot.findIndex(
            (existing) => existing[idField] === item[idField],
          );
          if (idx >= 0) {
            optimistic = [...snapshot];
            optimistic[idx] = { ...snapshot[idx], ...item };
          } else {
            optimistic = [...snapshot, item];
          }
        }
      }

      setItems(optimistic);
      setIsLoading(true);
      setError(null);

      try {
        const result = await apiFn(item);
        if (successMessage) toast.success(successMessage);
        onSuccess?.(result);
      } catch (err) {
        // Rollback to snapshot
        setItems(snapshot);
        setError(err);
        const msg =
          errorMessage ??
          (err instanceof Error ? err.message : 'Operation failed');
        toast.error(msg);
        onError?.(err);
      } finally {
        setIsLoading(false);
        rollbackRef.current = null;
      }
    },
    [getItems, setItems, apiFn, merge, idField, successMessage, errorMessage, onSuccess, onError],
  );

  return { mutate, isLoading, error };
}

// -----------------------------------------------------------------------
// Batch variant
// -----------------------------------------------------------------------

interface BatchOptimisticOptions<T extends Record<string, unknown>> {
  getItems: () => T[];
  setItems: (items: T[]) => void;
  apiFn: (items: T[]) => Promise<void>;
  merge?: MergeStrategy;
  idField?: keyof T;
}

export function useOptimisticBatchMutation<T extends Record<string, unknown>>(
  options: BatchOptimisticOptions<T>,
) {
  const { getItems, setItems, apiFn, merge = 'upsert', idField = 'id' as keyof T } = options;
  const [isLoading, setIsLoading] = useState(false);

  const mutate = useCallback(
    async (items: T[]) => {
      const snapshot = [...getItems()];
      let optimistic = [...snapshot];

      for (const item of items) {
        switch (merge) {
          case 'append':
            optimistic.push(item);
            break;
          case 'remove':
            optimistic = optimistic.filter(
              (e) => e[idField] !== item[idField],
            );
            break;
          case 'upsert':
          default: {
            const idx = optimistic.findIndex(
              (e) => e[idField] === item[idField],
            );
            if (idx >= 0) {
              optimistic[idx] = { ...optimistic[idx], ...item };
            } else {
              optimistic.push(item);
            }
          }
        }
      }

      setItems(optimistic);
      setIsLoading(true);

      try {
        await apiFn(items);
      } catch {
        setItems(snapshot);
      } finally {
        setIsLoading(false);
      }
    },
    [getItems, setItems, apiFn, merge, idField],
  );

  return { mutate, isLoading };
}

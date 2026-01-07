'use client';

import * as React from 'react';
import { useSyncStore, type PendingOperation } from '@/stores/sync-store';
import { apiClient } from '@/api/client';

interface SyncEngineOptions {
  /**
   * Auto-sync when coming back online
   */
  autoSync?: boolean;
  /**
   * Sync interval in milliseconds (0 = disabled)
   */
  syncInterval?: number;
  /**
   * Callback when sync completes
   */
  onSyncComplete?: (results: SyncResult[]) => void;
  /**
   * Callback when sync fails
   */
  onSyncError?: (error: Error) => void;
}

interface SyncResult {
  operationId: string;
  success: boolean;
  error?: string;
  serverData?: unknown;
}

interface UseSyncEngineReturn {
  /**
   * Current online status
   */
  isOnline: boolean;
  /**
   * Whether sync is in progress
   */
  isSyncing: boolean;
  /**
   * Number of pending operations
   */
  pendingCount: number;
  /**
   * Last sync timestamp
   */
  lastSyncAt: number | null;
  /**
   * Current sync error
   */
  syncError: string | null;
  /**
   * Manually trigger sync
   */
  sync: () => Promise<SyncResult[]>;
  /**
   * Queue an operation for sync
   */
  queueOperation: <T>(
    method: PendingOperation['method'],
    url: string,
    data?: unknown,
    options?: {
      entityType: string;
      entityId?: string;
      optimisticData?: Record<string, unknown>;
      maxRetries?: number;
    }
  ) => Promise<T>;
  /**
   * Retry all failed operations
   */
  retryFailed: () => Promise<void>;
  /**
   * Clear all pending operations
   */
  clearQueue: () => void;
}

/**
 * Sync engine hook for managing offline operations and background sync
 */
export function useSyncEngine(options: SyncEngineOptions = {}): UseSyncEngineReturn {
  const {
    autoSync = true,
    syncInterval = 0,
    onSyncComplete,
    onSyncError,
  } = options;

  const {
    pendingOperations,
    isSyncing,
    lastSyncAt,
    syncError,
    isOnline,
    addOperation,
    updateOperationStatus,
    incrementRetry,
    removeOperation,
    clearCompletedOperations,
    addOptimisticEntity,
    removeOptimisticEntity,
    setSyncing,
    setLastSyncAt,
    setSyncError,
    setOnline,
    getPendingCount,
    retryFailedOperations,
    clearAll,
  } = useSyncStore();

  // Listen for online/offline events
  React.useEffect(() => {
    const handleOnline = () => {
      setOnline(true);
      if (autoSync) {
        sync();
      }
    };

    const handleOffline = () => {
      setOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [autoSync]);

  // Periodic sync
  React.useEffect(() => {
    if (syncInterval <= 0) return;

    const intervalId = setInterval(() => {
      if (isOnline && getPendingCount() > 0) {
        sync();
      }
    }, syncInterval);

    return () => clearInterval(intervalId);
  }, [syncInterval, isOnline]);

  /**
   * Process a single pending operation
   */
  const processOperation = async (operation: PendingOperation): Promise<SyncResult> => {
    updateOperationStatus(operation.id, 'syncing');

    try {
      let serverData: unknown;

      switch (operation.method) {
        case 'POST':
          serverData = await apiClient.post(operation.url, operation.data);
          break;
        case 'PUT':
          serverData = await apiClient.put(operation.url, operation.data);
          break;
        case 'PATCH':
          serverData = await apiClient.patch(operation.url, operation.data);
          break;
        case 'DELETE':
          serverData = await apiClient.delete(operation.url);
          break;
      }

      updateOperationStatus(operation.id, 'completed');

      // Remove optimistic entity if exists
      if (operation.optimisticId) {
        removeOptimisticEntity(operation.optimisticId);
      }

      return {
        operationId: operation.id,
        success: true,
        serverData,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Check if we should retry
      if (operation.retryCount < operation.maxRetries) {
        incrementRetry(operation.id);
        updateOperationStatus(operation.id, 'pending', errorMessage);
      } else {
        updateOperationStatus(operation.id, 'failed', errorMessage);
      }

      return {
        operationId: operation.id,
        success: false,
        error: errorMessage,
      };
    }
  };

  /**
   * Sync all pending operations
   */
  const sync = async (): Promise<SyncResult[]> => {
    // Get fresh state from the store
    const currentState = useSyncStore.getState();
    
    if (!currentState.isOnline) {
      return [];
    }

    const pendingOps = currentState.pendingOperations.filter(
      (op) => op.status === 'pending'
    );

    if (pendingOps.length === 0) {
      return [];
    }

    setSyncing(true);
    setSyncError(null);

    const results: SyncResult[] = [];

    try {
      // Process operations sequentially to maintain order
      for (const operation of pendingOps) {
        const result = await processOperation(operation);
        results.push(result);
      }

      setLastSyncAt(Date.now());
      clearCompletedOperations();

      if (onSyncComplete) {
        onSyncComplete(results);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sync failed';
      setSyncError(errorMessage);

      if (onSyncError) {
        onSyncError(error instanceof Error ? error : new Error(errorMessage));
      }
    } finally {
      setSyncing(false);
    }

    return results;
  };

  /**
   * Queue an operation and optionally execute immediately if online
   */
  const queueOperation = async <T>(
    method: PendingOperation['method'],
    url: string,
    data?: unknown,
    operationOptions?: {
      entityType: string;
      entityId?: string;
      optimisticData?: Record<string, unknown>;
      maxRetries?: number;
    }
  ): Promise<T> => {
    const { entityType = 'unknown', entityId, optimisticData, maxRetries = 3 } = operationOptions || {};

    // Generate optimistic ID if creating
    const optimisticId = method === 'POST' && optimisticData
      ? `optimistic_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      : undefined;

    // Add optimistic entity
    if (optimisticId && optimisticData) {
      addOptimisticEntity({
        id: optimisticId,
        type: entityType,
        data: optimisticData,
        pendingOperationId: '', // Will be updated below
      });
    }

    // If online, try to execute immediately
    if (isOnline) {
      try {
        let serverData: T;

        switch (method) {
          case 'POST':
            serverData = await apiClient.post<T>(url, data);
            break;
          case 'PUT':
            serverData = await apiClient.put<T>(url, data);
            break;
          case 'PATCH':
            serverData = await apiClient.patch<T>(url, data);
            break;
          case 'DELETE':
            serverData = await apiClient.delete<T>(url);
            break;
        }

        // Remove optimistic entity on success
        if (optimisticId) {
          removeOptimisticEntity(optimisticId);
        }

        return serverData;
      } catch (error) {
        // If network error, queue for later
        if (!navigator.onLine) {
          const operationId = addOperation({
            method,
            url,
            data,
            maxRetries,
            entityType,
            entityId,
            optimisticId,
          });

          // Return optimistic data
          if (optimisticData) {
            return { id: optimisticId, ...optimisticData } as T;
          }
          throw error;
        }
        throw error;
      }
    }

    // Offline: queue operation
    const operationId = addOperation({
      method,
      url,
      data,
      maxRetries,
      entityType,
      entityId,
      optimisticId,
    });

    // Return optimistic data for creates
    if (method === 'POST' && optimisticData) {
      return { id: optimisticId, ...optimisticData, _isOptimistic: true } as T;
    }

    // For updates/deletes, just acknowledge
    return { success: true, _isPending: true } as T;
  };

  /**
   * Retry all failed operations
   */
  const retryFailed = async (): Promise<void> => {
    retryFailedOperations();
    await sync();
  };

  /**
   * Clear all pending operations
   */
  const clearQueue = (): void => {
    clearAll();
  };

  return {
    isOnline,
    isSyncing,
    pendingCount: getPendingCount(),
    lastSyncAt,
    syncError,
    sync,
    queueOperation,
    retryFailed,
    clearQueue,
  };
}

/**
 * Hook for optimistic mutations with automatic sync
 */
export function useOptimisticMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options?: {
    onSuccess?: (data: TData) => void;
    onError?: (error: Error) => void;
    onSettled?: () => void;
  }
) {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);
  const [data, setData] = React.useState<TData | null>(null);
  const { isOnline } = useSyncStore();

  const mutate = React.useCallback(
    async (variables: TVariables) => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await mutationFn(variables);
        setData(result);
        options?.onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Unknown error');
        setError(error);
        options?.onError?.(error);
        throw error;
      } finally {
        setIsLoading(false);
        options?.onSettled?.();
      }
    },
    [mutationFn, options]
  );

  return {
    mutate,
    isLoading,
    error,
    data,
    isOnline,
  };
}

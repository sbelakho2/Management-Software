'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * Represents a pending operation to be synced when online
 */
export interface PendingOperation {
  id: string;
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  url: string;
  data?: unknown;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
  entityType: string;
  entityId?: string;
  optimisticId?: string;
  status: 'pending' | 'syncing' | 'failed' | 'completed';
  error?: string;
}

/**
 * Represents an optimistic entity stored locally
 */
export interface OptimisticEntity {
  id: string;
  type: string;
  data: Record<string, unknown>;
  pendingOperationId: string;
  createdAt: number;
}

interface SyncState {
  // Pending operations queue
  pendingOperations: PendingOperation[];
  // Optimistic entities cache
  optimisticEntities: OptimisticEntity[];
  // Sync status
  isSyncing: boolean;
  lastSyncAt: number | null;
  syncError: string | null;
  // Online status
  isOnline: boolean;
}

interface SyncActions {
  // Queue operations
  addOperation: (operation: Omit<PendingOperation, 'id' | 'timestamp' | 'retryCount' | 'status'>) => string;
  removeOperation: (id: string) => void;
  updateOperationStatus: (id: string, status: PendingOperation['status'], error?: string) => void;
  incrementRetry: (id: string) => void;
  clearCompletedOperations: () => void;
  
  // Optimistic entities
  addOptimisticEntity: (entity: Omit<OptimisticEntity, 'createdAt'>) => void;
  updateOptimisticEntity: (id: string, data: Partial<OptimisticEntity['data']>) => void;
  removeOptimisticEntity: (id: string) => void;
  getOptimisticEntity: (id: string) => OptimisticEntity | undefined;
  
  // Sync status
  setSyncing: (isSyncing: boolean) => void;
  setLastSyncAt: (timestamp: number) => void;
  setSyncError: (error: string | null) => void;
  setOnline: (isOnline: boolean) => void;
  
  // Utilities
  getPendingCount: () => number;
  getFailedOperations: () => PendingOperation[];
  retryFailedOperations: () => void;
  clearAll: () => void;
}

function generateId(): string {
  return `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export const useSyncStore = create<SyncState & SyncActions>()(
  persist(
    (set, get) => ({
      // Initial state
      pendingOperations: [],
      optimisticEntities: [],
      isSyncing: false,
      lastSyncAt: null,
      syncError: null,
      isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,

      // Queue operations
      addOperation: (operation) => {
        const id = generateId();
        const newOperation: PendingOperation = {
          ...operation,
          id,
          timestamp: Date.now(),
          retryCount: 0,
          status: 'pending',
        };

        set((state) => ({
          pendingOperations: [...state.pendingOperations, newOperation],
        }));

        return id;
      },

      removeOperation: (id) => {
        set((state) => ({
          pendingOperations: state.pendingOperations.filter((op) => op.id !== id),
        }));
      },

      updateOperationStatus: (id, status, error) => {
        set((state) => ({
          pendingOperations: state.pendingOperations.map((op) =>
            op.id === id ? { ...op, status, error } : op
          ),
        }));
      },

      incrementRetry: (id) => {
        set((state) => ({
          pendingOperations: state.pendingOperations.map((op) =>
            op.id === id ? { ...op, retryCount: op.retryCount + 1 } : op
          ),
        }));
      },

      clearCompletedOperations: () => {
        set((state) => ({
          pendingOperations: state.pendingOperations.filter(
            (op) => op.status !== 'completed'
          ),
        }));
      },

      // Optimistic entities
      addOptimisticEntity: (entity) => {
        set((state) => ({
          optimisticEntities: [
            ...state.optimisticEntities,
            { ...entity, createdAt: Date.now() },
          ],
        }));
      },

      updateOptimisticEntity: (id, data) => {
        set((state) => ({
          optimisticEntities: state.optimisticEntities.map((entity) =>
            entity.id === id
              ? { ...entity, data: { ...entity.data, ...data } }
              : entity
          ),
        }));
      },

      removeOptimisticEntity: (id) => {
        set((state) => ({
          optimisticEntities: state.optimisticEntities.filter(
            (entity) => entity.id !== id
          ),
        }));
      },

      getOptimisticEntity: (id) => {
        return get().optimisticEntities.find((entity) => entity.id === id);
      },

      // Sync status
      setSyncing: (isSyncing) => set({ isSyncing }),
      setLastSyncAt: (timestamp) => set({ lastSyncAt: timestamp }),
      setSyncError: (error) => set({ syncError: error }),
      setOnline: (isOnline) => set({ isOnline }),

      // Utilities
      getPendingCount: () => {
        return get().pendingOperations.filter(
          (op) => op.status === 'pending' || op.status === 'syncing'
        ).length;
      },

      getFailedOperations: () => {
        return get().pendingOperations.filter((op) => op.status === 'failed');
      },

      retryFailedOperations: () => {
        set((state) => ({
          pendingOperations: state.pendingOperations.map((op) =>
            op.status === 'failed'
              ? { ...op, status: 'pending' as const, retryCount: 0, error: undefined }
              : op
          ),
        }));
      },

      clearAll: () => {
        set({
          pendingOperations: [],
          optimisticEntities: [],
          isSyncing: false,
          lastSyncAt: null,
          syncError: null,
        });
      },
    }),
    {
      name: 'sensei-sync-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        pendingOperations: state.pendingOperations,
        optimisticEntities: state.optimisticEntities,
        lastSyncAt: state.lastSyncAt,
      }),
    }
  )
);

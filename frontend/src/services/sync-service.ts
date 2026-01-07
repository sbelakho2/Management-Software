/**
 * Background Sync Service
 * 
 * Handles registration of background sync tasks with the service worker
 * and provides utilities for managing sync operations.
 */

import { useSyncStore, type PendingOperation } from '@/stores/sync-store';

export interface SyncRegistration {
  tag: string;
  registered: boolean;
}

export interface BackgroundSyncStatus {
  supported: boolean;
  registration: ServiceWorkerRegistration | null;
}

const SYNC_TAG = 'pending-operations-sync';
const PERIODIC_SYNC_TAG = 'periodic-sync';

/**
 * Check if Background Sync API is supported
 */
export function isBackgroundSyncSupported(): boolean {
  return 'serviceWorker' in navigator && 'sync' in window;
}

/**
 * Check if Periodic Background Sync API is supported
 */
export function isPeriodicSyncSupported(): boolean {
  return 'serviceWorker' in navigator && 'periodicSync' in ServiceWorkerRegistration.prototype;
}

/**
 * Get the current service worker registration
 */
export async function getServiceWorkerRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    return null;
  }

  try {
    return await navigator.serviceWorker.ready;
  } catch {
    return null;
  }
}

/**
 * Register a background sync task
 */
export async function registerBackgroundSync(tag: string = SYNC_TAG): Promise<SyncRegistration> {
  if (!isBackgroundSyncSupported()) {
    return { tag, registered: false };
  }

  try {
    const registration = await getServiceWorkerRegistration();
    if (!registration) {
      return { tag, registered: false };
    }

    // @ts-expect-error - sync API not fully typed
    await registration.sync.register(tag);
    return { tag, registered: true };
  } catch {
    return { tag, registered: false };
  }
}

/**
 * Register periodic background sync
 */
export async function registerPeriodicSync(
  minInterval: number = 60 * 60 * 1000 // 1 hour default
): Promise<SyncRegistration> {
  if (!isPeriodicSyncSupported()) {
    return { tag: PERIODIC_SYNC_TAG, registered: false };
  }

  try {
    const registration = await getServiceWorkerRegistration();
    if (!registration) {
      return { tag: PERIODIC_SYNC_TAG, registered: false };
    }

    // @ts-expect-error - periodicSync API not fully typed
    await registration.periodicSync.register(PERIODIC_SYNC_TAG, {
      minInterval,
    });

    return { tag: PERIODIC_SYNC_TAG, registered: true };
  } catch {
    return { tag: PERIODIC_SYNC_TAG, registered: false };
  }
}

/**
 * Unregister periodic background sync
 */
export async function unregisterPeriodicSync(): Promise<boolean> {
  if (!isPeriodicSyncSupported()) {
    return false;
  }

  try {
    const registration = await getServiceWorkerRegistration();
    if (!registration) {
      return false;
    }

    // @ts-expect-error - periodicSync API not fully typed
    await registration.periodicSync.unregister(PERIODIC_SYNC_TAG);
    return true;
  } catch {
    return false;
  }
}

/**
 * Post a message to the service worker
 */
export async function postMessageToServiceWorker(message: unknown): Promise<void> {
  const registration = await getServiceWorkerRegistration();
  if (!registration?.active) {
    return;
  }

  registration.active.postMessage(message);
}

/**
 * Get pending operations from the sync store and serialize for sync
 */
export function getSerializedPendingOperations(): string {
  const { pendingOperations } = useSyncStore.getState();
  const pending = pendingOperations.filter((op) => op.status === 'pending');
  return JSON.stringify(pending);
}

/**
 * Store operations in IndexedDB for service worker access
 */
export async function storePendingOperationsForSync(): Promise<void> {
  const operations = getSerializedPendingOperations();
  
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('sync-store', 1);

    request.onerror = () => reject(request.error);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('pending-operations')) {
        db.createObjectStore('pending-operations', { keyPath: 'id' });
      }
    };

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      const transaction = db.transaction(['pending-operations'], 'readwrite');
      const store = transaction.objectStore('pending-operations');

      // Clear existing operations
      store.clear();

      // Add current operations
      const parsedOps = JSON.parse(operations) as PendingOperation[];
      for (const op of parsedOps) {
        store.add(op);
      }

      transaction.oncomplete = () => {
        db.close();
        resolve();
      };

      transaction.onerror = () => {
        db.close();
        reject(transaction.error);
      };
    };
  });
}

/**
 * Get pending operations from IndexedDB
 */
export async function getPendingOperationsFromIndexedDB(): Promise<PendingOperation[]> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('sync-store', 1);

    request.onerror = () => reject(request.error);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('pending-operations')) {
        db.createObjectStore('pending-operations', { keyPath: 'id' });
      }
    };

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      const transaction = db.transaction(['pending-operations'], 'readonly');
      const store = transaction.objectStore('pending-operations');
      const getAllRequest = store.getAll();

      getAllRequest.onsuccess = () => {
        db.close();
        resolve(getAllRequest.result as PendingOperation[]);
      };

      getAllRequest.onerror = () => {
        db.close();
        reject(getAllRequest.error);
      };
    };
  });
}

/**
 * Clear pending operations from IndexedDB after successful sync
 */
export async function clearSyncedOperations(operationIds: string[]): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('sync-store', 1);

    request.onerror = () => reject(request.error);

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      const transaction = db.transaction(['pending-operations'], 'readwrite');
      const store = transaction.objectStore('pending-operations');

      for (const id of operationIds) {
        store.delete(id);
      }

      transaction.oncomplete = () => {
        db.close();
        resolve();
      };

      transaction.onerror = () => {
        db.close();
        reject(transaction.error);
      };
    };
  });
}

/**
 * Queue an operation and register background sync
 */
export async function queueOperationWithBackgroundSync(
  operation: Omit<PendingOperation, 'id' | 'timestamp' | 'retryCount' | 'status'>
): Promise<string> {
  const store = useSyncStore.getState();
  const operationId = store.addOperation(operation);

  // Store in IndexedDB for service worker access
  await storePendingOperationsForSync();

  // Register background sync
  await registerBackgroundSync();

  return operationId;
}

/**
 * Sync manager class for more complex sync scenarios
 */
export class SyncManager {
  private static instance: SyncManager;
  private messageHandler: ((event: MessageEvent) => void) | null = null;

  private constructor() {
    this.setupMessageListener();
  }

  static getInstance(): SyncManager {
    if (!SyncManager.instance) {
      SyncManager.instance = new SyncManager();
    }
    return SyncManager.instance;
  }

  private setupMessageListener(): void {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    this.messageHandler = (event: MessageEvent) => {
      const { type, payload } = event.data || {};

      switch (type) {
        case 'SYNC_COMPLETE':
          this.handleSyncComplete(payload);
          break;
        case 'SYNC_ERROR':
          this.handleSyncError(payload);
          break;
        case 'OPERATION_SYNCED':
          this.handleOperationSynced(payload);
          break;
      }
    };

    navigator.serviceWorker.addEventListener('message', this.messageHandler);
  }

  private handleSyncComplete(payload: { syncedCount: number; failedCount: number }): void {
    const store = useSyncStore.getState();
    store.setLastSyncAt(Date.now());
    store.setSyncing(false);
    store.clearCompletedOperations();

    // Dispatch custom event for UI updates
    window.dispatchEvent(
      new CustomEvent('sync-complete', { detail: payload })
    );
  }

  private handleSyncError(payload: { error: string }): void {
    const store = useSyncStore.getState();
    store.setSyncError(payload.error);
    store.setSyncing(false);

    // Dispatch custom event for UI updates
    window.dispatchEvent(
      new CustomEvent('sync-error', { detail: payload })
    );
  }

  private handleOperationSynced(payload: { operationId: string; success: boolean; serverData?: unknown }): void {
    const store = useSyncStore.getState();
    
    if (payload.success) {
      store.updateOperationStatus(payload.operationId, 'completed');
    } else {
      store.updateOperationStatus(payload.operationId, 'failed');
    }

    // Dispatch custom event for UI updates
    window.dispatchEvent(
      new CustomEvent('operation-synced', { detail: payload })
    );
  }

  async requestSync(): Promise<boolean> {
    const result = await registerBackgroundSync();
    return result.registered;
  }

  async requestPeriodicSync(minInterval?: number): Promise<boolean> {
    const result = await registerPeriodicSync(minInterval);
    return result.registered;
  }

  async cancelPeriodicSync(): Promise<boolean> {
    return unregisterPeriodicSync();
  }

  getBackgroundSyncStatus(): BackgroundSyncStatus {
    return {
      supported: isBackgroundSyncSupported(),
      registration: null, // Will be populated async
    };
  }

  destroy(): void {
    if (this.messageHandler && typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.removeEventListener('message', this.messageHandler);
    }
  }
}

/**
 * Get the sync manager instance
 */
export function getSyncManager(): SyncManager {
  return SyncManager.getInstance();
}

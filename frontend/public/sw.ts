/// <reference lib="webworker" />

/**
 * SENSEI Manufacturing PWA Service Worker
 * Provides offline caching, background sync, and push notifications
 */

declare const self: ServiceWorkerGlobalScope;

const CACHE_NAME = 'sensei-cache-v1';
const STATIC_CACHE_NAME = 'sensei-static-v1';
const DYNAMIC_CACHE_NAME = 'sensei-dynamic-v1';
const API_CACHE_NAME = 'sensei-api-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/offline',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// API routes to cache with network-first strategy
const API_ROUTES = [
  '/api/v1/users/me',
  '/api/v1/rfqs',
  '/api/v1/quotes',
  '/api/v1/customers',
  '/api/v1/products',
];

// Maximum age for cached API responses (in milliseconds)
const API_CACHE_MAX_AGE = 5 * 60 * 1000; // 5 minutes

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        // Force the waiting service worker to become active
        return self.skipWaiting();
      })
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old versions of our caches
              return name.startsWith('sensei-') && 
                     name !== STATIC_CACHE_NAME && 
                     name !== DYNAMIC_CACHE_NAME &&
                     name !== API_CACHE_NAME;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        // Take control of all pages immediately
        return self.clients.claim();
      })
  );
});

/**
 * Fetch event - implement caching strategies
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // API routes: Network first, fall back to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE_NAME));
    return;
  }

  // Static assets: Cache first, fall back to network
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE_NAME));
    return;
  }

  // Pages: Stale while revalidate
  event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE_NAME));
});

/**
 * Cache-first strategy
 * Good for static assets that rarely change
 */
async function cacheFirst(request: Request, cacheName: string): Promise<Response> {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const offlineResponse = await caches.match('/offline');
      if (offlineResponse) return offlineResponse;
    }
    
    throw error;
  }
}

/**
 * Network-first strategy
 * Good for API requests where fresh data is important
 */
async function networkFirst(request: Request, cacheName: string): Promise<Response> {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      console.log('[SW] Serving from cache (offline):', request.url);
      return cachedResponse;
    }
    
    // Return a JSON error response for API requests
    return new Response(
      JSON.stringify({ error: 'Network unavailable and no cached data' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Stale-while-revalidate strategy
 * Good for pages where stale content is acceptable but fresh is preferred
 */
async function staleWhileRevalidate(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  // Start fetching from network
  const fetchPromise = fetch(request)
    .then((networkResponse) => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch(() => {
      // Network failed, we'll rely on cache
      return null;
    });

  // Return cached response immediately, or wait for network
  if (cachedResponse) {
    // Don't await the fetch, let it update cache in background
    fetchPromise.catch(() => {});
    return cachedResponse;
  }

  const networkResponse = await fetchPromise;
  if (networkResponse) {
    return networkResponse;
  }

  // No cache, no network - return offline page
  const offlineResponse = await caches.match('/offline');
  if (offlineResponse) return offlineResponse;

  return new Response('Offline', { status: 503 });
}

/**
 * Check if a pathname is a static asset
 */
function isStaticAsset(pathname: string): boolean {
  const staticExtensions = [
    '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', 
    '.ico', '.woff', '.woff2', '.ttf', '.eot', '.json'
  ];
  
  return staticExtensions.some((ext) => pathname.endsWith(ext));
}

// Sync tags
const SYNC_TAG = 'pending-operations-sync';
const PERIODIC_SYNC_TAG = 'periodic-sync';

// IndexedDB database name and store
const SYNC_DB_NAME = 'sync-store';
const SYNC_STORE_NAME = 'pending-operations';

/**
 * Pending operation interface (matches sync-store.ts)
 */
interface PendingOperation {
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
  status: 'pending' | 'syncing' | 'completed' | 'failed';
  error?: string;
}

/**
 * Background sync for offline operations
 */
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);
  
  if (event.tag === SYNC_TAG) {
    event.waitUntil(syncPendingOperations());
  }
  
  if (event.tag === 'sync-forms') {
    event.waitUntil(syncPendingOperations());
  }
  
  if (event.tag === 'sync-offline-data') {
    event.waitUntil(syncPendingOperations());
  }
});

/**
 * Periodic background sync handler
 */
self.addEventListener('periodicsync', (event: Event) => {
  const periodicSyncEvent = event as unknown as { tag: string; waitUntil: (promise: Promise<unknown>) => void };
  console.log('[SW] Periodic sync event:', periodicSyncEvent.tag);
  
  if (periodicSyncEvent.tag === PERIODIC_SYNC_TAG) {
    periodicSyncEvent.waitUntil(syncPendingOperations());
  }
});

/**
 * Open IndexedDB and get pending operations
 */
async function getPendingOperationsFromDB(): Promise<PendingOperation[]> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SYNC_DB_NAME, 1);

    request.onerror = () => reject(request.error);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(SYNC_STORE_NAME)) {
        db.createObjectStore(SYNC_STORE_NAME, { keyPath: 'id' });
      }
    };

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains(SYNC_STORE_NAME)) {
        db.close();
        resolve([]);
        return;
      }
      
      const transaction = db.transaction([SYNC_STORE_NAME], 'readonly');
      const store = transaction.objectStore(SYNC_STORE_NAME);
      const getAllRequest = store.getAll();

      getAllRequest.onsuccess = () => {
        db.close();
        const operations = getAllRequest.result as PendingOperation[];
        resolve(operations.filter((op) => op.status === 'pending'));
      };

      getAllRequest.onerror = () => {
        db.close();
        reject(getAllRequest.error);
      };
    };
  });
}

/**
 * Delete a synced operation from IndexedDB
 */
async function deleteOperationFromDB(operationId: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SYNC_DB_NAME, 1);

    request.onerror = () => reject(request.error);

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains(SYNC_STORE_NAME)) {
        db.close();
        resolve();
        return;
      }
      
      const transaction = db.transaction([SYNC_STORE_NAME], 'readwrite');
      const store = transaction.objectStore(SYNC_STORE_NAME);
      store.delete(operationId);

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
 * Update operation status in IndexedDB
 */
async function updateOperationInDB(operation: PendingOperation): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SYNC_DB_NAME, 1);

    request.onerror = () => reject(request.error);

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains(SYNC_STORE_NAME)) {
        db.close();
        resolve();
        return;
      }
      
      const transaction = db.transaction([SYNC_STORE_NAME], 'readwrite');
      const store = transaction.objectStore(SYNC_STORE_NAME);
      store.put(operation);

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
 * Broadcast message to all clients
 */
async function broadcastToClients(message: unknown): Promise<void> {
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  for (const client of clients) {
    client.postMessage(message);
  }
}

/**
 * Execute a pending operation
 */
async function executeOperation(operation: PendingOperation): Promise<{ success: boolean; data?: unknown; error?: string }> {
  try {
    const options: RequestInit = {
      method: operation.method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (operation.data && ['POST', 'PUT', 'PATCH'].includes(operation.method)) {
      options.body = JSON.stringify(operation.data);
    }

    // Get auth token from cache or clients
    const tokenFromClients = await getAuthTokenFromClients();
    if (tokenFromClients) {
      options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${tokenFromClients}`,
      };
    }

    const response = await fetch(operation.url, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    let data: unknown = null;
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      data = await response.json();
    }

    return { success: true, data };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get auth token from active clients
 */
async function getAuthTokenFromClients(): Promise<string | null> {
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  
  for (const client of clients) {
    // Create a message channel to get response
    const messageChannel = new MessageChannel();
    
    return new Promise((resolve) => {
      const timeoutId = setTimeout(() => resolve(null), 1000);
      
      messageChannel.port1.onmessage = (event) => {
        clearTimeout(timeoutId);
        resolve(event.data?.token || null);
      };
      
      client.postMessage({ type: 'GET_AUTH_TOKEN' }, [messageChannel.port2]);
    });
  }
  
  return null;
}

/**
 * Sync all pending operations
 */
async function syncPendingOperations(): Promise<void> {
  console.log('[SW] Starting sync of pending operations...');
  
  let syncedCount = 0;
  let failedCount = 0;

  try {
    const operations = await getPendingOperationsFromDB();
    console.log(`[SW] Found ${operations.length} pending operations`);

    for (const operation of operations) {
      console.log(`[SW] Processing operation: ${operation.id} - ${operation.method} ${operation.url}`);
      
      const result = await executeOperation(operation);

      if (result.success) {
        // Delete from IndexedDB
        await deleteOperationFromDB(operation.id);
        syncedCount++;

        // Notify clients
        await broadcastToClients({
          type: 'OPERATION_SYNCED',
          payload: {
            operationId: operation.id,
            success: true,
            serverData: result.data,
          },
        });
      } else {
        failedCount++;
        
        // Update retry count
        operation.retryCount += 1;
        
        if (operation.retryCount >= operation.maxRetries) {
          operation.status = 'failed';
          operation.error = result.error;
        }
        
        await updateOperationInDB(operation);

        // Notify clients of failure
        await broadcastToClients({
          type: 'OPERATION_SYNCED',
          payload: {
            operationId: operation.id,
            success: false,
            error: result.error,
          },
        });
      }
    }

    // Notify sync complete
    await broadcastToClients({
      type: 'SYNC_COMPLETE',
      payload: { syncedCount, failedCount },
    });

    console.log(`[SW] Sync complete. Synced: ${syncedCount}, Failed: ${failedCount}`);
  } catch (error) {
    console.error('[SW] Sync error:', error);
    
    await broadcastToClients({
      type: 'SYNC_ERROR',
      payload: { error: error instanceof Error ? error.message : 'Unknown error' },
    });
  }
}

/**
 * Push notification handler
 */
self.addEventListener('push', (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    console.log('[SW] Push notification received:', data);

    const options: NotificationOptions = {
      body: data.body || 'New notification',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      tag: data.tag || 'default',
      data: data.data || {},
      actions: data.actions || [],
      vibrate: [100, 50, 100],
      renotify: true,
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'SENSEI', options)
    );
  } catch (error) {
    console.error('[SW] Error handling push notification:', error);
  }
});

/**
 * Notification click handler
 */
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification.tag);
  event.notification.close();

  const data = event.notification.data || {};
  const url = data.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Try to focus existing window
        for (const client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        return self.clients.openWindow(url);
      })
  );
});

/**
 * Message handler for communication with the app
 */
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }

  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('sensei-'))
            .map((name) => caches.delete(name))
        );
      })
    );
  }

  if (event.data.type === 'SYNC_NOW') {
    event.waitUntil(syncPendingOperations());
  }

  if (event.data.type === 'STORE_OPERATIONS') {
    event.waitUntil(
      storeOperationsInDB(event.data.operations)
        .then(() => {
          if (event.ports[0]) {
            event.ports[0].postMessage({ success: true });
          }
        })
        .catch((error) => {
          if (event.ports[0]) {
            event.ports[0].postMessage({ success: false, error: error.message });
          }
        })
    );
  }
});

/**
 * Store operations in IndexedDB from client
 */
async function storeOperationsInDB(operations: PendingOperation[]): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SYNC_DB_NAME, 1);

    request.onerror = () => reject(request.error);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(SYNC_STORE_NAME)) {
        db.createObjectStore(SYNC_STORE_NAME, { keyPath: 'id' });
      }
    };

    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      const transaction = db.transaction([SYNC_STORE_NAME], 'readwrite');
      const store = transaction.objectStore(SYNC_STORE_NAME);

      for (const operation of operations) {
        store.put(operation);
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

export {};

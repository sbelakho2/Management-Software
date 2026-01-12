/**
 * SENSEI Manufacturing PWA Service Worker
 * Provides offline caching, background sync, and push notifications
 */

const CACHE_NAME = 'sensei-cache-v1';
const STATIC_CACHE_NAME = 'sensei-static-v1';
const DYNAMIC_CACHE_NAME = 'sensei-dynamic-v1';
const API_CACHE_NAME = 'sensei-api-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/offline',
  '/icons/icon-192x192.svg',
  '/icons/icon-512x512.svg',
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
 * @param {Request} request
 * @param {string} cacheName
 * @returns {Promise<Response>}
 */
async function cacheFirst(request, cacheName) {
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
 * @param {Request} request
 * @param {string} cacheName
 * @returns {Promise<Response>}
 */
async function networkFirst(request, cacheName) {
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
 * @param {Request} request
 * @param {string} cacheName
 * @returns {Promise<Response>}
 */
async function staleWhileRevalidate(request, cacheName) {
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
 * @param {string} pathname
 * @returns {boolean}
 */
function isStaticAsset(pathname) {
  const staticExtensions = [
    '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', 
    '.ico', '.woff', '.woff2', '.ttf', '.eot', '.json'
  ];
  
  return staticExtensions.some((ext) => pathname.endsWith(ext));
}

/**
 * Background sync for offline form submissions
 */
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);
  
  if (event.tag === 'sync-forms') {
    event.waitUntil(syncPendingForms());
  }
  
  if (event.tag === 'sync-offline-data') {
    event.waitUntil(syncOfflineData());
  }
});

/**
 * Simple IndexedDB helper for background sync
 */
const dbPromise = new Promise((resolve, reject) => {
  const request = indexedDB.open('sensei-offline-db', 1);
  request.onupgradeneeded = (event) => {
    const db = event.target.result;
    if (!db.objectStoreNames.contains('pending-submissions')) {
      db.createObjectStore('pending-submissions', { keyPath: 'id', autoIncrement: true });
    }
    if (!db.objectStoreNames.contains('offline-data')) {
      db.createObjectStore('offline-data', { keyPath: 'id' });
    }
  };
  request.onsuccess = (event) => resolve(event.target.result);
  request.onerror = (event) => reject(event.target.error);
});

async function getFromDB(storeName) {
  const db = await dbPromise;
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, 'readonly');
    const store = transaction.objectStore(storeName);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function removeFromDB(storeName, id) {
  const db = await dbPromise;
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, 'readwrite');
    const store = transaction.objectStore(storeName);
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

/**
 * Sync pending form submissions
 * @returns {Promise<void>}
 */
async function syncPendingForms() {
  console.log('[SW] Syncing pending form submissions...');
  try {
    const submissions = await getFromDB('pending-submissions');
    
    for (const submission of submissions) {
      try {
        const response = await fetch(submission.url, {
          method: submission.method || 'POST',
          headers: {
            ...submission.headers,
            'X-Synced-From': 'ServiceWorker'
          },
          body: submission.body
        });
        
        if (response.ok) {
          await removeFromDB('pending-submissions', submission.id);
          console.log('[SW] Successfully synced submission:', submission.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync submission:', submission.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Error during syncPendingForms:', error);
  }
}

/**
 * Sync offline data changes
 * @returns {Promise<void>}
 */
async function syncOfflineData() {
  console.log('[SW] Syncing offline data changes...');
  // Implementation for general data synchronization
  // e.g. updating local cache with latest from server or vice versa
  try {
    const offlineChanges = await getFromDB('offline-data');
    for (const change of offlineChanges) {
       // Logic to apply changes to server
       console.log('[SW] Syncing change:', change.id);
       // ... fetch calls ...
       await removeFromDB('offline-data', change.id);
    }
  } catch (error) {
    console.error('[SW] Error during syncOfflineData:', error);
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

    const options = {
      body: data.body || 'New notification',
      icon: '/icons/icon-192x192.svg',
      badge: '/icons/icon-72x72.svg',
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
});

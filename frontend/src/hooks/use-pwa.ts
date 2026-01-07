'use client';

import * as React from 'react';

interface ServiceWorkerState {
  isSupported: boolean;
  isRegistered: boolean;
  isOnline: boolean;
  isUpdateAvailable: boolean;
  registration: ServiceWorkerRegistration | null;
}

interface UsePWAReturn extends ServiceWorkerState {
  register: () => Promise<void>;
  unregister: () => Promise<void>;
  update: () => Promise<void>;
  skipWaiting: () => void;
}

export function usePWA(): UsePWAReturn {
  const [state, setState] = React.useState<ServiceWorkerState>({
    isSupported: false,
    isRegistered: false,
    isOnline: true,
    isUpdateAvailable: false,
    registration: null,
  });

  // Check for service worker support
  React.useEffect(() => {
    const isSupported = 'serviceWorker' in navigator;
    const isOnline = navigator.onLine;
    
    setState(prev => ({ ...prev, isSupported, isOnline }));
  }, []);

  // Listen for online/offline events
  React.useEffect(() => {
    const handleOnline = () => setState(prev => ({ ...prev, isOnline: true }));
    const handleOffline = () => setState(prev => ({ ...prev, isOnline: false }));

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Check existing registration on mount
  React.useEffect(() => {
    if (!state.isSupported) return;

    navigator.serviceWorker.getRegistration().then((registration) => {
      if (registration) {
        setState(prev => ({ ...prev, isRegistered: true, registration }));
        setupUpdateListener(registration);
      }
    });
  }, [state.isSupported]);

  const setupUpdateListener = (registration: ServiceWorkerRegistration) => {
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      if (!newWorker) return;

      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          // New update available
          setState(prev => ({ ...prev, isUpdateAvailable: true }));
        }
      });
    });
  };

  const register = async (): Promise<void> => {
    if (!state.isSupported) {
      console.warn('[PWA] Service workers not supported');
      return;
    }

    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      });

      console.log('[PWA] Service worker registered:', registration);
      setState(prev => ({ ...prev, isRegistered: true, registration }));
      setupUpdateListener(registration);

      // Check for updates periodically
      setInterval(() => {
        registration.update();
      }, 60 * 60 * 1000); // Every hour
    } catch (error) {
      console.error('[PWA] Service worker registration failed:', error);
    }
  };

  const unregister = async (): Promise<void> => {
    if (!state.registration) return;

    try {
      await state.registration.unregister();
      setState(prev => ({ ...prev, isRegistered: false, registration: null }));
      console.log('[PWA] Service worker unregistered');
    } catch (error) {
      console.error('[PWA] Service worker unregistration failed:', error);
    }
  };

  const update = async (): Promise<void> => {
    if (!state.registration) return;

    try {
      await state.registration.update();
      console.log('[PWA] Service worker update checked');
    } catch (error) {
      console.error('[PWA] Service worker update check failed:', error);
    }
  };

  const skipWaiting = (): void => {
    if (!state.registration?.waiting) return;

    state.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    window.location.reload();
  };

  return {
    ...state,
    register,
    unregister,
    update,
    skipWaiting,
  };
}

/**
 * Hook to check if the app is running as a PWA (installed)
 */
export function useIsPWA(): boolean {
  const [isPWA, setIsPWA] = React.useState(false);

  React.useEffect(() => {
    // Check if running in standalone mode (installed PWA)
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    const isIOSStandalone = (window.navigator as any).standalone === true;
    
    setIsPWA(isStandalone || isIOSStandalone);
  }, []);

  return isPWA;
}

/**
 * Hook for requesting push notification permission
 */
export function usePushNotifications() {
  const [permission, setPermission] = React.useState<NotificationPermission>('default');
  const [subscription, setSubscription] = React.useState<PushSubscription | null>(null);

  React.useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission);
    }
  }, []);

  const requestPermission = async (): Promise<boolean> => {
    if (!('Notification' in window)) {
      console.warn('[Push] Notifications not supported');
      return false;
    }

    const result = await Notification.requestPermission();
    setPermission(result);
    return result === 'granted';
  };

  const subscribe = async (
    registration: ServiceWorkerRegistration,
    vapidPublicKey: string
  ): Promise<PushSubscription | null> => {
    if (permission !== 'granted') {
      const granted = await requestPermission();
      if (!granted) return null;
    }

    try {
      const sub = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });
      
      setSubscription(sub);
      return sub;
    } catch (error) {
      console.error('[Push] Subscription failed:', error);
      return null;
    }
  };

  const unsubscribe = async (): Promise<void> => {
    if (!subscription) return;

    try {
      await subscription.unsubscribe();
      setSubscription(null);
    } catch (error) {
      console.error('[Push] Unsubscribe failed:', error);
    }
  };

  return {
    permission,
    subscription,
    requestPermission,
    subscribe,
    unsubscribe,
  };
}

/**
 * Convert VAPID public key to Uint8Array
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  
  return outputArray;
}

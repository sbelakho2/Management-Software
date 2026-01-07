import { renderHook, act } from '@testing-library/react';
import { usePWA, useIsPWA, usePushNotifications } from '../use-pwa';

// Mock service worker
const mockServiceWorkerRegistration: Partial<ServiceWorkerRegistration> = {
  installing: null,
  waiting: null,
  active: null,
  scope: '/',
  update: jest.fn().mockResolvedValue(undefined),
  unregister: jest.fn().mockResolvedValue(true),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  showNotification: jest.fn(),
  getNotifications: jest.fn().mockResolvedValue([]),
  pushManager: {
    getSubscription: jest.fn().mockResolvedValue(null),
    subscribe: jest.fn(),
    permissionState: jest.fn().mockResolvedValue('default'),
  } as unknown as PushManager,
};

describe('usePWA', () => {
  let originalServiceWorker: ServiceWorkerContainer | undefined;
  let originalNavigator: Navigator;

  beforeEach(() => {
    // Store original values
    originalServiceWorker = navigator.serviceWorker;
    originalNavigator = navigator;

    // Mock navigator.serviceWorker
    Object.defineProperty(navigator, 'serviceWorker', {
      writable: true,
      configurable: true,
      value: {
        register: jest.fn().mockResolvedValue(mockServiceWorkerRegistration),
        getRegistration: jest.fn().mockResolvedValue(undefined),
        ready: Promise.resolve(mockServiceWorkerRegistration),
        controller: null,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      },
    });

    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      configurable: true,
      value: true,
    });
  });

  afterEach(() => {
    // Restore original values
    if (originalServiceWorker !== undefined) {
      Object.defineProperty(navigator, 'serviceWorker', {
        writable: true,
        configurable: true,
        value: originalServiceWorker,
      });
    }
  });

  it('should detect service worker support', () => {
    const { result } = renderHook(() => usePWA());
    expect(result.current.isSupported).toBe(true);
  });

  it('should track online status', () => {
    const { result } = renderHook(() => usePWA());
    expect(result.current.isOnline).toBe(true);
  });

  it('should provide register function', () => {
    const { result } = renderHook(() => usePWA());
    expect(typeof result.current.register).toBe('function');
  });

  it('should provide unregister function', () => {
    const { result } = renderHook(() => usePWA());
    expect(typeof result.current.unregister).toBe('function');
  });

  it('should provide update function', () => {
    const { result } = renderHook(() => usePWA());
    expect(typeof result.current.update).toBe('function');
  });

  it('should provide skipWaiting function', () => {
    const { result } = renderHook(() => usePWA());
    expect(typeof result.current.skipWaiting).toBe('function');
  });
});

describe('useIsPWA', () => {
  beforeEach(() => {
    // Mock window.matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation((query: string) => ({
        matches: query === '(display-mode: standalone)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  it('should detect standalone mode', () => {
    const { result } = renderHook(() => useIsPWA());
    expect(typeof result.current).toBe('boolean');
  });
});

describe('usePushNotifications', () => {
  let originalNotification: typeof Notification;

  beforeEach(() => {
    originalNotification = window.Notification;

    // Mock Notification API
    Object.defineProperty(window, 'Notification', {
      writable: true,
      configurable: true,
      value: {
        permission: 'default',
        requestPermission: jest.fn().mockResolvedValue('granted'),
      },
    });

    // Mock navigator.serviceWorker
    Object.defineProperty(navigator, 'serviceWorker', {
      writable: true,
      configurable: true,
      value: {
        ready: Promise.resolve(mockServiceWorkerRegistration),
        register: jest.fn(),
        getRegistration: jest.fn().mockResolvedValue(mockServiceWorkerRegistration),
        controller: null,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'Notification', {
      writable: true,
      configurable: true,
      value: originalNotification,
    });
  });

  it('should return permission status', () => {
    const { result } = renderHook(() => usePushNotifications());
    expect(result.current.permission).toBe('default');
  });

  it('should provide subscribe function', () => {
    const { result } = renderHook(() => usePushNotifications());
    expect(typeof result.current.subscribe).toBe('function');
  });

  it('should provide unsubscribe function', () => {
    const { result } = renderHook(() => usePushNotifications());
    expect(typeof result.current.unsubscribe).toBe('function');
  });
});

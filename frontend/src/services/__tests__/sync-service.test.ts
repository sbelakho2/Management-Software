/**
 * @jest-environment jsdom
 */
import {
  isBackgroundSyncSupported,
  isPeriodicSyncSupported,
  getServiceWorkerRegistration,
  registerBackgroundSync,
  getSerializedPendingOperations,
  SyncManager,
  getSyncManager,
} from '@/services/sync-service';
import { useSyncStore } from '@/stores/sync-store';
import { act } from '@testing-library/react';

// Mock service worker APIs
const mockSync = {
  register: jest.fn(),
};

const mockPeriodicSync = {
  register: jest.fn(),
  unregister: jest.fn(),
};

const mockServiceWorkerRegistration = {
  sync: mockSync,
  periodicSync: mockPeriodicSync,
  active: {
    postMessage: jest.fn(),
  },
};

describe('sync-service', () => {
  const originalNavigator = global.navigator;
  const originalWindow = global.window;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset the sync store
    act(() => {
      useSyncStore.getState().clearAll();
    });

    // Reset navigator mock
    Object.defineProperty(global, 'navigator', {
      value: {
        serviceWorker: {
          ready: Promise.resolve(mockServiceWorkerRegistration),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
        },
      },
      writable: true,
      configurable: true,
    });

    // Mock window.sync
    Object.defineProperty(global, 'window', {
      value: {
        ...originalWindow,
        sync: {},
      },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(global, 'navigator', {
      value: originalNavigator,
      writable: true,
      configurable: true,
    });
  });

  describe('isBackgroundSyncSupported', () => {
    it('should return true when service worker and sync are available', () => {
      expect(isBackgroundSyncSupported()).toBe(true);
    });

    it('should return false when service worker is not available', () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        writable: true,
        configurable: true,
      });

      expect(isBackgroundSyncSupported()).toBe(false);
    });
  });

  describe('isPeriodicSyncSupported', () => {
    it('should return false when service worker is not available', () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        writable: true,
        configurable: true,
      });

      expect(isPeriodicSyncSupported()).toBe(false);
    });
  });

  describe('getServiceWorkerRegistration', () => {
    it('should return service worker registration when available', async () => {
      const registration = await getServiceWorkerRegistration();
      expect(registration).toBe(mockServiceWorkerRegistration);
    });

    it('should return null when service worker is not available', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        writable: true,
        configurable: true,
      });

      const registration = await getServiceWorkerRegistration();
      expect(registration).toBeNull();
    });
  });

  describe('registerBackgroundSync', () => {
    it('should register sync with default tag', async () => {
      mockSync.register.mockResolvedValue(undefined);

      const result = await registerBackgroundSync();

      expect(result.registered).toBe(true);
      expect(result.tag).toBe('pending-operations-sync');
      expect(mockSync.register).toHaveBeenCalledWith('pending-operations-sync');
    });

    it('should register sync with custom tag', async () => {
      mockSync.register.mockResolvedValue(undefined);

      const result = await registerBackgroundSync('custom-tag');

      expect(result.registered).toBe(true);
      expect(result.tag).toBe('custom-tag');
      expect(mockSync.register).toHaveBeenCalledWith('custom-tag');
    });

    it('should return false when sync registration fails', async () => {
      mockSync.register.mockRejectedValue(new Error('Registration failed'));

      const result = await registerBackgroundSync();

      expect(result.registered).toBe(false);
    });

    it('should return false when background sync is not supported', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        writable: true,
        configurable: true,
      });
      Object.defineProperty(global, 'window', {
        value: {},
        writable: true,
        configurable: true,
      });

      const result = await registerBackgroundSync();

      expect(result.registered).toBe(false);
    });
  });

  describe('getSerializedPendingOperations', () => {
    it('should return empty array when no pending operations', () => {
      const result = getSerializedPendingOperations();
      const parsed = JSON.parse(result);

      expect(parsed).toEqual([]);
    });

    it('should return pending operations as JSON', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          data: { name: 'test' },
          maxRetries: 3,
          entityType: 'test',
        });
      });

      const result = getSerializedPendingOperations();
      const parsed = JSON.parse(result);

      expect(parsed).toHaveLength(1);
      expect(parsed[0]).toMatchObject({
        method: 'POST',
        url: '/api/test',
        data: { name: 'test' },
        status: 'pending',
      });
    });

    it('should only return pending operations', () => {
      act(() => {
        const id1 = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });

        // Mark first as completed
        useSyncStore.getState().updateOperationStatus(id1, 'completed');
      });

      const result = getSerializedPendingOperations();
      const parsed = JSON.parse(result);

      expect(parsed).toHaveLength(1);
      expect(parsed[0].url).toBe('/api/test2');
    });
  });

  describe('SyncManager', () => {
    let syncManager: SyncManager;

    beforeEach(() => {
      syncManager = getSyncManager();
    });

    it('should return singleton instance', () => {
      const instance1 = getSyncManager();
      const instance2 = getSyncManager();

      expect(instance1).toBe(instance2);
    });

    it('should get background sync status', () => {
      const status = syncManager.getBackgroundSyncStatus();

      expect(status).toHaveProperty('supported');
      expect(status).toHaveProperty('registration');
    });

    it('should request sync', async () => {
      mockSync.register.mockResolvedValue(undefined);

      const result = await syncManager.requestSync();

      expect(result).toBe(true);
    });
  });
});

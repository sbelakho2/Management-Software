/**
 * @jest-environment jsdom
 */
import { act, renderHook, waitFor } from '@testing-library/react';
import { useSyncEngine, useOptimisticMutation } from '@/hooks/use-sync-engine';
import { useSyncStore } from '@/stores/sync-store';
import { apiClient } from '@/api/client';

// Mock the API client
jest.mock('@/api/client', () => ({
  apiClient: {
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('use-sync-engine', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the sync store and ensure online
    act(() => {
      useSyncStore.getState().clearAll();
      useSyncStore.getState().setOnline(true);
    });
  });

  describe('useSyncEngine', () => {
    describe('initial state', () => {
      it('should return online status', () => {
        const { result } = renderHook(() => useSyncEngine());
        expect(result.current.isOnline).toBe(true);
      });

      it('should return syncing status as false initially', () => {
        const { result } = renderHook(() => useSyncEngine());
        expect(result.current.isSyncing).toBe(false);
      });

      it('should return pending count as 0 initially', () => {
        const { result } = renderHook(() => useSyncEngine());
        expect(result.current.pendingCount).toBe(0);
      });

      it('should return lastSyncAt as null initially', () => {
        const { result } = renderHook(() => useSyncEngine());
        expect(result.current.lastSyncAt).toBeNull();
      });

      it('should return syncError as null initially', () => {
        const { result } = renderHook(() => useSyncEngine());
        expect(result.current.syncError).toBeNull();
      });
    });

    describe('queueOperation', () => {
      it('should execute POST immediately when online', async () => {
        mockApiClient.post.mockResolvedValue({ id: '1', name: 'test' });

        const { result } = renderHook(() => useSyncEngine());

        let response: unknown;
        await act(async () => {
          response = await result.current.queueOperation(
            'POST',
            '/api/test',
            { name: 'test' },
            { entityType: 'test' }
          );
        });

        expect(mockApiClient.post).toHaveBeenCalledWith('/api/test', { name: 'test' });
        expect(response).toEqual({ id: '1', name: 'test' });
      });

      it('should execute PUT immediately when online', async () => {
        mockApiClient.put.mockResolvedValue({ id: '1', name: 'updated' });

        const { result } = renderHook(() => useSyncEngine());

        let response: unknown;
        await act(async () => {
          response = await result.current.queueOperation(
            'PUT',
            '/api/test/1',
            { name: 'updated' },
            { entityType: 'test', entityId: '1' }
          );
        });

        expect(mockApiClient.put).toHaveBeenCalledWith('/api/test/1', { name: 'updated' });
        expect(response).toEqual({ id: '1', name: 'updated' });
      });

      it('should execute PATCH immediately when online', async () => {
        mockApiClient.patch.mockResolvedValue({ id: '1', status: 'active' });

        const { result } = renderHook(() => useSyncEngine());

        let response: unknown;
        await act(async () => {
          response = await result.current.queueOperation(
            'PATCH',
            '/api/test/1',
            { status: 'active' },
            { entityType: 'test', entityId: '1' }
          );
        });

        expect(mockApiClient.patch).toHaveBeenCalledWith('/api/test/1', { status: 'active' });
        expect(response).toEqual({ id: '1', status: 'active' });
      });

      it('should execute DELETE immediately when online', async () => {
        mockApiClient.delete.mockResolvedValue({ success: true });

        const { result } = renderHook(() => useSyncEngine());

        let response: unknown;
        await act(async () => {
          response = await result.current.queueOperation(
            'DELETE',
            '/api/test/1',
            undefined,
            { entityType: 'test', entityId: '1' }
          );
        });

        expect(mockApiClient.delete).toHaveBeenCalledWith('/api/test/1');
        expect(response).toEqual({ success: true });
      });

      it('should throw error when online request fails', async () => {
        mockApiClient.post.mockRejectedValue(new Error('Server error'));

        const { result } = renderHook(() => useSyncEngine());

        await expect(
          act(async () => {
            await result.current.queueOperation(
              'POST',
              '/api/test',
              { name: 'test' },
              { entityType: 'test' }
            );
          })
        ).rejects.toThrow('Server error');
      });
    });

    describe('sync', () => {
      it('should process pending operations', async () => {
        mockApiClient.post.mockResolvedValue({ id: '1', name: 'test' });

        // Add a pending operation directly to the store
        act(() => {
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
        });

        const { result } = renderHook(() => useSyncEngine());

        expect(result.current.pendingCount).toBe(1);

        let syncResults: unknown[];
        await act(async () => {
          syncResults = await result.current.sync();
        });

        expect(mockApiClient.post).toHaveBeenCalledWith('/api/test', { name: 'test' });
        expect(syncResults!).toHaveLength(1);
        expect(syncResults![0]).toMatchObject({ success: true });
      });

      it('should handle failed operations during sync', async () => {
        mockApiClient.post.mockRejectedValue(new Error('Network error'));

        // Add a pending operation
        act(() => {
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
        });

        const { result } = renderHook(() => useSyncEngine());

        let syncResults: unknown[];
        await act(async () => {
          syncResults = await result.current.sync();
        });

        expect(syncResults!).toHaveLength(1);
        expect(syncResults![0]).toMatchObject({
          success: false,
          error: 'Network error',
        });
      });

      it('should not sync when offline', async () => {
        // Set offline
        act(() => {
          useSyncStore.getState().setOnline(false);
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
        });

        const { result } = renderHook(() => useSyncEngine());

        let syncResults: unknown[];
        await act(async () => {
          syncResults = await result.current.sync();
        });

        expect(syncResults!).toHaveLength(0);
        expect(mockApiClient.post).not.toHaveBeenCalled();
      });

      it('should call onSyncComplete callback', async () => {
        const onSyncComplete = jest.fn();
        mockApiClient.post.mockResolvedValue({ id: '1' });

        act(() => {
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
        });

        const { result } = renderHook(() => useSyncEngine({ onSyncComplete }));

        await act(async () => {
          await result.current.sync();
        });

        await waitFor(() => {
          expect(onSyncComplete).toHaveBeenCalled();
        });
      });

      it('should update lastSyncAt after successful sync', async () => {
        mockApiClient.post.mockResolvedValue({ id: '1' });

        act(() => {
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
        });

        const { result } = renderHook(() => useSyncEngine());

        expect(result.current.lastSyncAt).toBeNull();

        await act(async () => {
          await result.current.sync();
        });

        // Check the store directly since re-render might not have happened
        expect(useSyncStore.getState().lastSyncAt).not.toBeNull();
      });
    });

    describe('retryFailed', () => {
      it('should reset failed operations to pending and sync', async () => {
        mockApiClient.post.mockResolvedValue({ id: '1' });

        // Add a failed operation
        act(() => {
          const id = useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
          useSyncStore.getState().updateOperationStatus(id, 'failed', 'First fail');
        });

        // Verify it's failed
        expect(useSyncStore.getState().pendingOperations[0].status).toBe('failed');

        const { result } = renderHook(() => useSyncEngine());

        await act(async () => {
          await result.current.retryFailed();
        });

        // After retryFailed, the operation should be synced
        expect(mockApiClient.post).toHaveBeenCalledWith('/api/test', { name: 'test' });
      });
    });

    describe('clearQueue', () => {
      it('should clear all pending operations', () => {
        act(() => {
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: '/api/test',
            data: { name: 'test' },
            maxRetries: 3,
            entityType: 'test',
          });
        });

        const { result } = renderHook(() => useSyncEngine());

        expect(result.current.pendingCount).toBe(1);

        act(() => {
          result.current.clearQueue();
        });

        expect(result.current.pendingCount).toBe(0);
      });
    });
  });

  describe('useOptimisticMutation', () => {
    beforeEach(() => {
      // Ensure online status is true for these tests
      act(() => {
        useSyncStore.getState().setOnline(true);
      });
    });

    it('should handle successful mutation', async () => {
      const mutationFn = jest.fn().mockResolvedValue({ id: '1', name: 'test' });
      const onSuccess = jest.fn();

      const { result } = renderHook(() =>
        useOptimisticMutation(mutationFn, { onSuccess })
      );

      await act(async () => {
        await result.current.mutate({ name: 'test' });
      });

      expect(mutationFn).toHaveBeenCalledWith({ name: 'test' });
      expect(onSuccess).toHaveBeenCalledWith({ id: '1', name: 'test' });
      expect(result.current.data).toEqual({ id: '1', name: 'test' });
      expect(result.current.error).toBeNull();
      expect(result.current.isLoading).toBe(false);
    });

    it('should handle failed mutation', async () => {
      const mutationFn = jest.fn().mockRejectedValue(new Error('Failed'));
      const onError = jest.fn();

      const { result } = renderHook(() =>
        useOptimisticMutation(mutationFn, { onError })
      );

      try {
        await act(async () => {
          await result.current.mutate({ name: 'test' });
        });
      } catch {
        // Expected to throw
      }

      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });

      // The error should be captured
      expect(result.current.isLoading).toBe(false);
    });

    it('should call onSettled after mutation completes', async () => {
      const mutationFn = jest.fn().mockResolvedValue({ id: '1' });
      const onSettled = jest.fn();

      const { result } = renderHook(() =>
        useOptimisticMutation(mutationFn, { onSettled })
      );

      await act(async () => {
        await result.current.mutate({ name: 'test' });
      });

      expect(onSettled).toHaveBeenCalled();
    });

    it('should expose online status', () => {
      const mutationFn = jest.fn();

      // Ensure online is true
      act(() => {
        useSyncStore.getState().setOnline(true);
      });

      const { result } = renderHook(() => useOptimisticMutation(mutationFn));

      expect(result.current.isOnline).toBe(true);
    });

    it('should set loading state during mutation', async () => {
      let resolvePromise: (value: unknown) => void;
      const mutationFn = jest.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            resolvePromise = resolve;
          })
      );

      const { result } = renderHook(() => useOptimisticMutation(mutationFn));

      expect(result.current.isLoading).toBe(false);

      let mutationPromise: Promise<unknown>;
      act(() => {
        mutationPromise = result.current.mutate({ name: 'test' });
      });

      expect(result.current.isLoading).toBe(true);

      await act(async () => {
        resolvePromise!({ id: '1' });
        await mutationPromise;
      });

      expect(result.current.isLoading).toBe(false);
    });
  });
});

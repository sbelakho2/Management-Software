/**
 * @jest-environment jsdom
 */
import { act, renderHook } from '@testing-library/react';
import { useSyncStore, type PendingOperation } from '@/stores/sync-store';

describe('sync-store', () => {
  beforeEach(() => {
    // Reset the store before each test
    act(() => {
      useSyncStore.getState().clearAll();
    });
  });

  describe('initial state', () => {
    it('should have empty pending operations', () => {
      const { result } = renderHook(() => useSyncStore());
      expect(result.current.pendingOperations).toEqual([]);
    });

    it('should not be syncing initially', () => {
      const { result } = renderHook(() => useSyncStore());
      expect(result.current.isSyncing).toBe(false);
    });

    it('should have no lastSyncAt initially', () => {
      const { result } = renderHook(() => useSyncStore());
      expect(result.current.lastSyncAt).toBeNull();
    });

    it('should have no syncError initially', () => {
      const { result } = renderHook(() => useSyncStore());
      expect(result.current.syncError).toBeNull();
    });

    it('should be online initially', () => {
      const { result } = renderHook(() => useSyncStore());
      expect(result.current.isOnline).toBe(true);
    });

    it('should have empty optimistic entities', () => {
      const { result } = renderHook(() => useSyncStore());
      expect(result.current.optimisticEntities).toEqual([]);
    });
  });

  describe('addOperation', () => {
    it('should add a new operation with generated id', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          data: { name: 'test' },
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations).toHaveLength(1);
      expect(result.current.pendingOperations[0]).toMatchObject({
        method: 'POST',
        url: '/api/test',
        data: { name: 'test' },
        maxRetries: 3,
        entityType: 'test',
        status: 'pending',
        retryCount: 0,
      });
      expect(result.current.pendingOperations[0].id).toBeDefined();
      expect(result.current.pendingOperations[0].timestamp).toBeDefined();
    });

    it('should return the operation id', () => {
      const { result } = renderHook(() => useSyncStore());

      let operationId: string = '';
      act(() => {
        operationId = result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(operationId).toBe(result.current.pendingOperations[0].id);
    });

    it('should add multiple operations', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        result.current.addOperation({
          method: 'PUT',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations).toHaveLength(2);
    });
  });

  describe('removeOperation', () => {
    it('should remove an operation by id', () => {
      const { result } = renderHook(() => useSyncStore());

      let operationId: string = '';
      act(() => {
        operationId = result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations).toHaveLength(1);

      act(() => {
        result.current.removeOperation(operationId);
      });

      expect(result.current.pendingOperations).toHaveLength(0);
    });

    it('should not affect other operations', () => {
      const { result } = renderHook(() => useSyncStore());

      let id1: string = '';
      let id2: string = '';
      act(() => {
        id1 = result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        id2 = result.current.addOperation({
          method: 'POST',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      act(() => {
        result.current.removeOperation(id1);
      });

      expect(result.current.pendingOperations).toHaveLength(1);
      expect(result.current.pendingOperations[0].id).toBe(id2);
    });
  });

  describe('updateOperationStatus', () => {
    it('should update operation status', () => {
      const { result } = renderHook(() => useSyncStore());

      let operationId: string = '';
      act(() => {
        operationId = result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      act(() => {
        result.current.updateOperationStatus(operationId, 'syncing');
      });

      expect(result.current.pendingOperations[0].status).toBe('syncing');
    });

    it('should update operation status with error', () => {
      const { result } = renderHook(() => useSyncStore());

      let operationId: string = '';
      act(() => {
        operationId = result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      act(() => {
        result.current.updateOperationStatus(operationId, 'failed', 'Network error');
      });

      expect(result.current.pendingOperations[0].status).toBe('failed');
      expect(result.current.pendingOperations[0].error).toBe('Network error');
    });
  });

  describe('incrementRetry', () => {
    it('should increment retry count', () => {
      const { result } = renderHook(() => useSyncStore());

      let operationId: string = '';
      act(() => {
        operationId = result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations[0].retryCount).toBe(0);

      act(() => {
        result.current.incrementRetry(operationId);
      });

      expect(result.current.pendingOperations[0].retryCount).toBe(1);

      act(() => {
        result.current.incrementRetry(operationId);
      });

      expect(result.current.pendingOperations[0].retryCount).toBe(2);
    });
  });

  describe('clearCompletedOperations', () => {
    it('should remove only completed operations', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        const id1 = result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        result.current.addOperation({
          method: 'POST',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });
        result.current.updateOperationStatus(id1, 'completed');
      });

      expect(result.current.pendingOperations).toHaveLength(2);

      act(() => {
        result.current.clearCompletedOperations();
      });

      expect(result.current.pendingOperations).toHaveLength(1);
      expect(result.current.pendingOperations[0].url).toBe('/api/test2');
    });
  });

  describe('optimisticEntities', () => {
    it('should add an optimistic entity', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOptimisticEntity({
          id: 'opt-1',
          type: 'test',
          data: { name: 'test item' },
          pendingOperationId: 'op-1',
        });
      });

      expect(result.current.optimisticEntities).toHaveLength(1);
      expect(result.current.optimisticEntities[0]).toMatchObject({
        id: 'opt-1',
        type: 'test',
        data: { name: 'test item' },
        pendingOperationId: 'op-1',
      });
    });

    it('should update an optimistic entity', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOptimisticEntity({
          id: 'opt-1',
          type: 'test',
          data: { name: 'original' },
          pendingOperationId: 'op-1',
        });
      });

      act(() => {
        result.current.updateOptimisticEntity('opt-1', { name: 'updated' });
      });

      expect(result.current.optimisticEntities[0].data).toEqual({ name: 'updated' });
    });

    it('should remove an optimistic entity', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOptimisticEntity({
          id: 'opt-1',
          type: 'test',
          data: { name: 'test' },
          pendingOperationId: 'op-1',
        });
      });

      expect(result.current.optimisticEntities).toHaveLength(1);

      act(() => {
        result.current.removeOptimisticEntity('opt-1');
      });

      expect(result.current.optimisticEntities).toHaveLength(0);
    });

    it('should get an optimistic entity', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOptimisticEntity({
          id: 'opt-1',
          type: 'test',
          data: { name: 'test' },
          pendingOperationId: 'op-1',
        });
      });

      const entity = result.current.getOptimisticEntity('opt-1');
      expect(entity).toBeDefined();
      expect(entity?.data).toEqual({ name: 'test' });
    });

    it('should return undefined for non-existent entity', () => {
      const { result } = renderHook(() => useSyncStore());

      const entity = result.current.getOptimisticEntity('non-existent');
      expect(entity).toBeUndefined();
    });
  });

  describe('sync state setters', () => {
    it('should set syncing state', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.setSyncing(true);
      });

      expect(result.current.isSyncing).toBe(true);

      act(() => {
        result.current.setSyncing(false);
      });

      expect(result.current.isSyncing).toBe(false);
    });

    it('should set lastSyncAt', () => {
      const { result } = renderHook(() => useSyncStore());
      const timestamp = Date.now();

      act(() => {
        result.current.setLastSyncAt(timestamp);
      });

      expect(result.current.lastSyncAt).toBe(timestamp);
    });

    it('should set syncError', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.setSyncError('Test error');
      });

      expect(result.current.syncError).toBe('Test error');
    });

    it('should set online state', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.setOnline(false);
      });

      expect(result.current.isOnline).toBe(false);

      act(() => {
        result.current.setOnline(true);
      });

      expect(result.current.isOnline).toBe(true);
    });
  });

  describe('getPendingCount', () => {
    it('should return count of pending and syncing operations', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        const id1 = result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        const id2 = result.current.addOperation({
          method: 'POST',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });
        const id3 = result.current.addOperation({
          method: 'POST',
          url: '/api/test3',
          maxRetries: 3,
          entityType: 'test',
        });

        result.current.updateOperationStatus(id1, 'syncing');
        result.current.updateOperationStatus(id3, 'completed');
      });

      expect(result.current.getPendingCount()).toBe(2); // 1 pending + 1 syncing
    });
  });

  describe('getFailedOperations', () => {
    it('should return only failed operations', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        const id1 = result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        result.current.addOperation({
          method: 'POST',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });

        result.current.updateOperationStatus(id1, 'failed', 'Error');
      });

      const failed = result.current.getFailedOperations();
      expect(failed).toHaveLength(1);
      expect(failed[0].url).toBe('/api/test1');
    });
  });

  describe('retryFailedOperations', () => {
    it('should reset failed operations to pending', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        const id1 = result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });

        result.current.updateOperationStatus(id1, 'failed', 'Error');
      });

      expect(result.current.pendingOperations[0].status).toBe('failed');

      act(() => {
        result.current.retryFailedOperations();
      });

      expect(result.current.pendingOperations[0].status).toBe('pending');
      expect(result.current.pendingOperations[0].error).toBeUndefined();
    });

    it('should reset retry count for failed operations', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        const id1 = result.current.addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });

        result.current.incrementRetry(id1);
        result.current.incrementRetry(id1);
        result.current.updateOperationStatus(id1, 'failed', 'Error');
      });

      expect(result.current.pendingOperations[0].retryCount).toBe(2);

      act(() => {
        result.current.retryFailedOperations();
      });

      expect(result.current.pendingOperations[0].retryCount).toBe(0);
    });
  });

  describe('clearAll', () => {
    it('should clear all state', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        result.current.addOptimisticEntity({
          id: 'opt-1',
          type: 'test',
          data: {},
          pendingOperationId: 'op-1',
        });
        result.current.setSyncing(true);
        result.current.setLastSyncAt(Date.now());
        result.current.setSyncError('Error');
      });

      expect(result.current.pendingOperations.length).toBeGreaterThan(0);
      expect(result.current.optimisticEntities.length).toBeGreaterThan(0);

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.pendingOperations).toHaveLength(0);
      expect(result.current.optimisticEntities).toHaveLength(0);
      expect(result.current.isSyncing).toBe(false);
      expect(result.current.lastSyncAt).toBeNull();
      expect(result.current.syncError).toBeNull();
    });
  });

  describe('operation methods', () => {
    it('should support POST method', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          data: { name: 'new' },
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations[0].method).toBe('POST');
    });

    it('should support PUT method', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'PUT',
          url: '/api/test/1',
          data: { name: 'updated' },
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations[0].method).toBe('PUT');
    });

    it('should support PATCH method', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'PATCH',
          url: '/api/test/1',
          data: { status: 'active' },
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations[0].method).toBe('PATCH');
    });

    it('should support DELETE method', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'DELETE',
          url: '/api/test/1',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      expect(result.current.pendingOperations[0].method).toBe('DELETE');
    });
  });

  describe('entityId and optimisticId', () => {
    it('should store entityId for updates', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'PUT',
          url: '/api/test/123',
          data: { name: 'updated' },
          maxRetries: 3,
          entityType: 'test',
          entityId: '123',
        });
      });

      expect(result.current.pendingOperations[0].entityId).toBe('123');
    });

    it('should store optimisticId for creates', () => {
      const { result } = renderHook(() => useSyncStore());

      act(() => {
        result.current.addOperation({
          method: 'POST',
          url: '/api/test',
          data: { name: 'new' },
          maxRetries: 3,
          entityType: 'test',
          optimisticId: 'opt-123',
        });
      });

      expect(result.current.pendingOperations[0].optimisticId).toBe('opt-123');
    });
  });
});

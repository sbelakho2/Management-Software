/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { act } from '@testing-library/react';
import {
  SyncStatusIndicator,
  SyncStatusBanner,
  PendingOperationsList,
} from '@/components/sync/sync-status';
import { useSyncStore } from '@/stores/sync-store';

describe('sync-status components', () => {
  beforeEach(() => {
    // Reset the sync store
    act(() => {
      useSyncStore.getState().clearAll();
      useSyncStore.getState().setOnline(true);
    });
  });

  describe('SyncStatusIndicator', () => {
    it('should render online status indicator', () => {
      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText('Synced')).toBeInTheDocument();
    });

    it('should show offline status when offline', () => {
      act(() => {
        useSyncStore.getState().setOnline(false);
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText('Offline')).toBeInTheDocument();
    });

    it('should show pending count', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText('2 Pending')).toBeInTheDocument();
    });

    it('should show syncing status', () => {
      act(() => {
        useSyncStore.getState().setSyncing(true);
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText('Syncing...')).toBeInTheDocument();
    });

    it('should show failed count', () => {
      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().updateOperationStatus(id, 'failed', 'Error');
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText('1 Failed')).toBeInTheDocument();
    });

    it('should show sync error', () => {
      act(() => {
        useSyncStore.getState().setSyncError('Connection failed');
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText('Sync Error')).toBeInTheDocument();
    });

    it('should show last sync time', () => {
      act(() => {
        useSyncStore.getState().setLastSyncAt(Date.now() - 30000); // 30 seconds ago
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText(/Last:/)).toBeInTheDocument();
      expect(screen.getByText(/Just now/)).toBeInTheDocument();
    });

    it('should show minutes ago for recent sync', () => {
      act(() => {
        useSyncStore.getState().setLastSyncAt(Date.now() - 5 * 60 * 1000); // 5 minutes ago
      });

      render(<SyncStatusIndicator showDetails />);

      expect(screen.getByText(/5m ago/)).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = render(
        <SyncStatusIndicator className="custom-class" />
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('should not show details by default', () => {
      render(<SyncStatusIndicator />);

      expect(screen.queryByText('Synced')).not.toBeInTheDocument();
    });
  });

  describe('SyncStatusBanner', () => {
    it('should not render when online and no issues', () => {
      const { container } = render(<SyncStatusBanner />);

      expect(container.firstChild).toBeNull();
    });

    it('should show offline banner', () => {
      act(() => {
        useSyncStore.getState().setOnline(false);
      });

      render(<SyncStatusBanner />);

      expect(
        screen.getByText(/You're offline\. Changes will sync when you reconnect\./)
      ).toBeInTheDocument();
    });

    it('should show sync error banner', () => {
      act(() => {
        useSyncStore.getState().setSyncError('Server unavailable');
      });

      render(<SyncStatusBanner />);

      expect(screen.getByText(/Sync failed: Server unavailable/)).toBeInTheDocument();
    });

    it('should show failed operations banner', () => {
      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().updateOperationStatus(id, 'failed', 'Error');
      });

      render(<SyncStatusBanner />);

      expect(screen.getByText(/1 change couldn't be saved\./)).toBeInTheDocument();
    });

    it('should show pending operations banner', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<SyncStatusBanner />);

      expect(screen.getByText(/1 change waiting to sync\./)).toBeInTheDocument();
    });

    it('should show retry button for failed operations', () => {
      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().updateOperationStatus(id, 'failed', 'Error');
      });

      render(<SyncStatusBanner />);

      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', () => {
      const onRetry = jest.fn();

      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().updateOperationStatus(id, 'failed', 'Error');
      });

      render(<SyncStatusBanner onRetry={onRetry} />);

      fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

      expect(onRetry).toHaveBeenCalled();
    });

    it('should show discard button for failed operations', () => {
      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().updateOperationStatus(id, 'failed', 'Error');
      });

      render(<SyncStatusBanner />);

      expect(screen.getByRole('button', { name: 'Discard' })).toBeInTheDocument();
    });

    it('should call onDismiss when discard button is clicked', () => {
      const onDismiss = jest.fn();

      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().updateOperationStatus(id, 'failed', 'Error');
      });

      render(<SyncStatusBanner onDismiss={onDismiss} />);

      fireEvent.click(screen.getByRole('button', { name: 'Discard' }));

      expect(onDismiss).toHaveBeenCalled();
    });

    it('should pluralize correctly', () => {
      act(() => {
        useSyncStore.getState().addOperation({
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
      });

      render(<SyncStatusBanner />);

      expect(screen.getByText(/2 changes waiting to sync\./)).toBeInTheDocument();
    });
  });

  describe('PendingOperationsList', () => {
    it('should show empty message when no operations', () => {
      render(<PendingOperationsList />);

      expect(screen.getByText('No pending operations')).toBeInTheDocument();
    });

    it('should list pending operations', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<PendingOperationsList />);

      expect(screen.getByText('POST')).toBeInTheDocument();
      expect(screen.getByText(/\/api\/test/)).toBeInTheDocument();
      expect(screen.getByText('Pending')).toBeInTheDocument();
    });

    it('should show different status badges', () => {
      act(() => {
        const id1 = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        const id2 = useSyncStore.getState().addOperation({
          method: 'PUT',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });

        useSyncStore.getState().updateOperationStatus(id1, 'syncing');
        useSyncStore.getState().updateOperationStatus(id2, 'failed', 'Error');
      });

      render(<PendingOperationsList />);

      expect(screen.getByText('Syncing')).toBeInTheDocument();
      expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('should show different method badges', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test1',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().addOperation({
          method: 'PUT',
          url: '/api/test2',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().addOperation({
          method: 'DELETE',
          url: '/api/test3',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<PendingOperationsList />);

      expect(screen.getByText('POST')).toBeInTheDocument();
      expect(screen.getByText('PUT')).toBeInTheDocument();
      expect(screen.getByText('DELETE')).toBeInTheDocument();
    });

    it('should show retry count', () => {
      act(() => {
        const id = useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
        useSyncStore.getState().incrementRetry(id);
        useSyncStore.getState().incrementRetry(id);
      });

      render(<PendingOperationsList />);

      expect(screen.getByText('Retry 2/3')).toBeInTheDocument();
    });

    it('should remove operation when remove button is clicked', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/test',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<PendingOperationsList />);

      expect(screen.getByText(/\/api\/test/)).toBeInTheDocument();

      const removeButton = screen.getByTitle('Remove operation');
      fireEvent.click(removeButton);

      expect(screen.getByText('No pending operations')).toBeInTheDocument();
    });

    it('should limit displayed operations', () => {
      act(() => {
        for (let i = 0; i < 15; i++) {
          useSyncStore.getState().addOperation({
            method: 'POST',
            url: `/api/test${i}`,
            maxRetries: 3,
            entityType: 'test',
          });
        }
      });

      render(<PendingOperationsList maxItems={10} />);

      expect(screen.getByText('And 5 more...')).toBeInTheDocument();
    });

    it('should truncate long URLs', () => {
      act(() => {
        useSyncStore.getState().addOperation({
          method: 'POST',
          url: '/api/v1/very/long/path/that/exceeds/forty/characters/endpoint',
          maxRetries: 3,
          entityType: 'test',
        });
      });

      render(<PendingOperationsList />);

      expect(screen.getByText(/\.\.\..*endpoint/)).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = render(
        <PendingOperationsList className="custom-class" />
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});

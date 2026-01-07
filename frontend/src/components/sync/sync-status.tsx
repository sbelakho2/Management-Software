'use client';

import * as React from 'react';
import { useSyncStore } from '@/stores/sync-store';
import { cn } from '@/lib/utils';

interface SyncStatusIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

/**
 * A visual indicator showing the current sync status
 */
export function SyncStatusIndicator({
  className,
  showDetails = false,
}: SyncStatusIndicatorProps) {
  const { isOnline, isSyncing, pendingOperations, lastSyncAt, syncError } =
    useSyncStore();

  const pendingCount = pendingOperations.filter(
    (op) => op.status === 'pending' || op.status === 'syncing'
  ).length;

  const failedCount = pendingOperations.filter(
    (op) => op.status === 'failed'
  ).length;

  const getStatusColor = () => {
    if (!isOnline) return 'bg-gray-400';
    if (syncError || failedCount > 0) return 'bg-red-500';
    if (isSyncing) return 'bg-blue-500';
    if (pendingCount > 0) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusText = () => {
    if (!isOnline) return 'Offline';
    if (syncError) return 'Sync Error';
    if (failedCount > 0) return `${failedCount} Failed`;
    if (isSyncing) return 'Syncing...';
    if (pendingCount > 0) return `${pendingCount} Pending`;
    return 'Synced';
  };

  const formatLastSync = () => {
    if (!lastSyncAt) return 'Never';

    const now = Date.now();
    const diff = now - lastSyncAt;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return new Date(lastSyncAt).toLocaleDateString();
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="relative">
        <div
          className={cn(
            'h-2 w-2 rounded-full',
            getStatusColor(),
            isSyncing && 'animate-pulse'
          )}
        />
        {pendingCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-3 w-3 items-center justify-center rounded-full bg-blue-600 text-[8px] text-white">
            {pendingCount > 9 ? '9+' : pendingCount}
          </span>
        )}
      </div>

      {showDetails && (
        <div className="flex flex-col">
          <span className="text-xs font-medium">{getStatusText()}</span>
          {lastSyncAt && (
            <span className="text-[10px] text-muted-foreground">
              Last: {formatLastSync()}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface SyncStatusBannerProps {
  className?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

/**
 * A banner that shows when there are sync issues
 */
export function SyncStatusBanner({
  className,
  onRetry,
  onDismiss,
}: SyncStatusBannerProps) {
  const { isOnline, isSyncing, pendingOperations, syncError, retryFailedOperations, clearAll } =
    useSyncStore();

  const pendingCount = pendingOperations.filter(
    (op) => op.status === 'pending' || op.status === 'syncing'
  ).length;

  const failedCount = pendingOperations.filter(
    (op) => op.status === 'failed'
  ).length;

  // Don't show banner if everything is fine
  if (isOnline && !syncError && failedCount === 0 && pendingCount === 0) {
    return null;
  }

  const handleRetry = () => {
    retryFailedOperations();
    onRetry?.();
  };

  const handleDismiss = () => {
    clearAll();
    onDismiss?.();
  };

  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg border px-4 py-2',
        !isOnline && 'border-gray-300 bg-gray-50 text-gray-700',
        (syncError || failedCount > 0) &&
          isOnline &&
          'border-red-200 bg-red-50 text-red-800',
        isOnline &&
          !syncError &&
          failedCount === 0 &&
          pendingCount > 0 &&
          'border-yellow-200 bg-yellow-50 text-yellow-800',
        className
      )}
    >
      <div className="flex items-center gap-3">
        {/* Status Icon */}
        {!isOnline ? (
          <CloudOffIcon className="h-5 w-5" />
        ) : isSyncing ? (
          <LoadingIcon className="h-5 w-5 animate-spin" />
        ) : syncError || failedCount > 0 ? (
          <AlertIcon className="h-5 w-5" />
        ) : (
          <ClockIcon className="h-5 w-5" />
        )}

        {/* Status Message */}
        <div>
          {!isOnline ? (
            <p className="text-sm font-medium">
              You're offline. Changes will sync when you reconnect.
            </p>
          ) : syncError ? (
            <p className="text-sm font-medium">
              Sync failed: {syncError}
            </p>
          ) : failedCount > 0 ? (
            <p className="text-sm font-medium">
              {failedCount} {failedCount === 1 ? 'change' : 'changes'} couldn't
              be saved.
            </p>
          ) : (
            <p className="text-sm font-medium">
              {pendingCount} {pendingCount === 1 ? 'change' : 'changes'} waiting
              to sync.
            </p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {(syncError || failedCount > 0) && (
          <button
            onClick={handleRetry}
            disabled={isSyncing}
            className="rounded-md bg-red-100 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-200 disabled:opacity-50"
          >
            {isSyncing ? 'Retrying...' : 'Retry'}
          </button>
        )}

        {failedCount > 0 && (
          <button
            onClick={handleDismiss}
            className="rounded-md px-3 py-1 text-xs font-medium hover:bg-red-200"
          >
            Discard
          </button>
        )}
      </div>
    </div>
  );
}

interface PendingOperationsListProps {
  className?: string;
  maxItems?: number;
}

/**
 * A list of pending operations for debugging or user visibility
 */
export function PendingOperationsList({
  className,
  maxItems = 10,
}: PendingOperationsListProps) {
  const { pendingOperations, removeOperation } = useSyncStore();

  const displayOps = pendingOperations.slice(0, maxItems);
  const hasMore = pendingOperations.length > maxItems;

  if (pendingOperations.length === 0) {
    return (
      <div className={cn('text-center text-sm text-muted-foreground', className)}>
        No pending operations
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">
            Pending
          </span>
        );
      case 'syncing':
        return (
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
            Syncing
          </span>
        );
      case 'failed':
        return (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
            Failed
          </span>
        );
      case 'completed':
        return (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
            Completed
          </span>
        );
      default:
        return null;
    }
  };

  const getMethodBadge = (method: string) => {
    const colors: Record<string, string> = {
      POST: 'bg-green-100 text-green-700',
      PUT: 'bg-blue-100 text-blue-700',
      PATCH: 'bg-purple-100 text-purple-700',
      DELETE: 'bg-red-100 text-red-700',
    };

    return (
      <span
        className={cn(
          'rounded-full px-2 py-0.5 text-xs font-mono',
          colors[method] || 'bg-gray-100 text-gray-700'
        )}
      >
        {method}
      </span>
    );
  };

  return (
    <div className={cn('space-y-2', className)}>
      {displayOps.map((op) => (
        <div
          key={op.id}
          className="flex items-center justify-between rounded-lg border p-3"
        >
          <div className="flex items-center gap-2">
            {getMethodBadge(op.method)}
            <span className="font-mono text-xs text-muted-foreground">
              {op.url.length > 40 ? `...${op.url.slice(-40)}` : op.url}
            </span>
            {getStatusBadge(op.status)}
          </div>

          <div className="flex items-center gap-2">
            {op.retryCount > 0 && (
              <span className="text-xs text-muted-foreground">
                Retry {op.retryCount}/{op.maxRetries}
              </span>
            )}
            <button
              onClick={() => removeOperation(op.id)}
              className="rounded p-1 text-muted-foreground hover:bg-gray-100 hover:text-gray-700"
              title="Remove operation"
            >
              <XIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      ))}

      {hasMore && (
        <p className="text-center text-xs text-muted-foreground">
          And {pendingOperations.length - maxItems} more...
        </p>
      )}
    </div>
  );
}

// Simple icon components
function CloudOffIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="2" y1="2" x2="22" y2="22" />
      <path d="M9.69 4.09A7 7 0 0 1 19 9c0 1.21-.31 2.35-.86 3.34" />
      <path d="M16.5 19H6a5 5 0 0 1-4.5-7.09" />
      <path d="M22 15.5a5 5 0 0 0-5-5" />
    </svg>
  );
}

function LoadingIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

/**
 * Error & Edge Case Experience Components
 * 
 * Section 19.5: Error & Edge Case Experience
 * 
 * Features:
 * - Actionable error messages with context
 * - Empty state components with CTAs
 * - Offline resilience indicators
 * - Conflict resolution UI
 * - Error boundary with fallback
 */

'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { cn } from '@/lib/utils';

// =============================================================================
// CONSTANTS
// =============================================================================

/** Error severity levels */
export const ERROR_SEVERITY = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
} as const;

export type ErrorSeverity = typeof ERROR_SEVERITY[keyof typeof ERROR_SEVERITY];

/** Offline status */
export const OFFLINE_STATUS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  RECONNECTING: 'reconnecting',
} as const;

export type OfflineStatus = typeof OFFLINE_STATUS[keyof typeof OFFLINE_STATUS];

/** Conflict resolution strategies */
export const CONFLICT_STRATEGY = {
  KEEP_LOCAL: 'keep-local',
  KEEP_SERVER: 'keep-server',
  MERGE: 'merge',
  MANUAL: 'manual',
} as const;

export type ConflictStrategy = typeof CONFLICT_STRATEGY[keyof typeof CONFLICT_STRATEGY];

// =============================================================================
// ACTIONABLE ERROR COMPONENTS
// =============================================================================

interface ActionableErrorProps {
  /** Error title */
  title: string;
  /** Detailed error message */
  message: string;
  /** Field that caused the error (for form validation) */
  field?: string;
  /** Expected value or format hint */
  expectedFormat?: string;
  /** Reason for the validation */
  reason?: string;
  /** Error severity */
  severity?: ErrorSeverity;
  /** Retry action */
  onRetry?: () => void;
  /** Dismiss action */
  onDismiss?: () => void;
  /** Report issue action */
  onReport?: () => void;
  /** Custom actions */
  actions?: Array<{
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'ghost';
  }>;
  className?: string;
}

/**
 * Actionable error message with context and recovery options
 */
export function ActionableError({
  title,
  message,
  field,
  expectedFormat,
  reason,
  severity = 'error',
  onRetry,
  onDismiss,
  onReport,
  actions,
  className,
}: ActionableErrorProps) {
  const severityStyles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    critical: 'bg-red-100 border-red-300 text-red-900',
  };

  const severityIcons = {
    info: 'ℹ',
    warning: '⚠',
    error: '✕',
    critical: '⚠',
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        'rounded-lg border p-4 space-y-3',
        severityStyles[severity],
        className
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg flex-shrink-0" aria-hidden="true">
          {severityIcons[severity]}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold">{title}</h4>
          <p className="text-sm mt-1">{message}</p>
          
          {/* Field-specific guidance */}
          {field && (
            <p className="text-sm mt-2">
              <strong>Field:</strong> {field}
            </p>
          )}
          
          {expectedFormat && (
            <p className="text-sm mt-1">
              <strong>Expected:</strong> {expectedFormat}
            </p>
          )}
          
          {reason && (
            <p className="text-sm mt-1 opacity-80">
              <strong>Reason:</strong> {reason}
            </p>
          )}
        </div>
        
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 p-1 hover:bg-black/10 rounded"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        )}
      </div>
      
      {/* Actions */}
      {(onRetry || onReport || actions?.length) && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-current/20">
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-3 py-1.5 text-sm font-medium rounded bg-current/10 hover:bg-current/20 transition-colors"
            >
              Try Again
            </button>
          )}
          {onReport && (
            <button
              onClick={onReport}
              className="px-3 py-1.5 text-sm font-medium rounded hover:bg-current/10 transition-colors"
            >
              Report Issue
            </button>
          )}
          {actions?.map((action, index) => (
            <button
              key={index}
              onClick={action.onClick}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded transition-colors',
                action.variant === 'primary' && 'bg-current/20 hover:bg-current/30',
                action.variant === 'secondary' && 'bg-current/10 hover:bg-current/20',
                action.variant === 'ghost' && 'hover:bg-current/10'
              )}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Inline field error for form validation
 */
export function FieldError({
  message,
  expected,
  id,
  className,
}: {
  message: string;
  expected?: string;
  id?: string;
  className?: string;
}) {
  return (
    <div
      id={id}
      role="alert"
      className={cn('text-sm text-red-600 mt-1', className)}
    >
      <span>{message}</span>
      {expected && (
        <span className="block text-xs text-red-500 mt-0.5">
          Expected: {expected}
        </span>
      )}
    </div>
  );
}

/**
 * Error page for 500 errors with system health check
 */
export function ServerErrorPage({
  error,
  onCheckHealth,
  onReportIssue,
  onGoHome,
  className,
}: {
  error?: Error | string;
  onCheckHealth?: () => void;
  onReportIssue?: () => void;
  onGoHome?: () => void;
  className?: string;
}) {
  const errorMessage = error instanceof Error ? error.message : error;

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center min-h-[400px] text-center px-4',
        className
      )}
      role="alert"
    >
      <div className="text-6xl mb-4" aria-hidden="true">
        ⚙️
      </div>
      <h1 className="text-2xl font-bold mb-2">Something went wrong</h1>
      <p className="text-muted-foreground max-w-md mb-6">
        We're experiencing technical difficulties. Our team has been notified.
      </p>
      
      {errorMessage && (
        <div className="bg-muted rounded-lg p-3 mb-6 max-w-md text-sm font-mono text-left w-full">
          {errorMessage}
        </div>
      )}
      
      <div className="flex flex-wrap gap-3 justify-center">
        {onCheckHealth && (
          <button
            onClick={onCheckHealth}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 transition-colors"
          >
            Check System Health
          </button>
        )}
        {onReportIssue && (
          <button
            onClick={onReportIssue}
            className="px-4 py-2 border rounded-md font-medium hover:bg-muted transition-colors"
          >
            Report Issue
          </button>
        )}
        {onGoHome && (
          <button
            onClick={onGoHome}
            className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            Go to Home
          </button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// EMPTY STATE COMPONENTS
// =============================================================================

interface EmptyStateProps {
  /** Icon or illustration */
  icon?: React.ReactNode;
  /** Empty state title */
  title: string;
  /** Description of the empty state */
  description?: string;
  /** Explanation of why it's empty */
  reason?: string;
  /** Primary action CTA */
  primaryAction?: {
    label: string;
    onClick: () => void;
  };
  /** Secondary action */
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  /** Whether to show educational tooltip */
  showTip?: boolean;
  /** Educational tip content */
  tip?: string;
  className?: string;
}

/**
 * Empty state with illustration, CTAs, and educational content
 */
export function EmptyState({
  icon,
  title,
  description,
  reason,
  primaryAction,
  secondaryAction,
  showTip = false,
  tip,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
      role="status"
      aria-label={title}
    >
      {icon && (
        <div className="text-6xl mb-4 text-muted-foreground" aria-hidden="true">
          {icon}
        </div>
      )}
      
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      
      {description && (
        <p className="text-muted-foreground max-w-sm mb-2">{description}</p>
      )}
      
      {reason && (
        <p className="text-sm text-muted-foreground/80 max-w-sm mb-4">
          {reason}
        </p>
      )}
      
      {(primaryAction || secondaryAction) && (
        <div className="flex flex-wrap gap-3 justify-center mt-4">
          {primaryAction && (
            <button
              onClick={primaryAction.onClick}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 transition-colors"
            >
              {primaryAction.label}
            </button>
          )}
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="px-4 py-2 border rounded-md font-medium hover:bg-muted transition-colors"
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
      
      {showTip && tip && (
        <div className="mt-6 p-3 bg-blue-50 text-blue-800 rounded-lg max-w-sm text-sm">
          <span className="font-medium">💡 Tip:</span> {tip}
        </div>
      )}
    </div>
  );
}

/** Preset empty states for common scenarios */
export const EMPTY_STATE_PRESETS = {
  NO_RESULTS: {
    icon: '🔍',
    title: 'No results found',
    description: 'Try adjusting your search or filters',
    reason: 'Your current filters may be too restrictive',
  },
  NO_ITEMS: {
    icon: '📋',
    title: 'No items yet',
    description: 'Get started by creating your first item',
  },
  NO_RFQS: {
    icon: '📨',
    title: 'No RFQs in queue',
    description: 'When new RFQs arrive, they will appear here',
    tip: 'RFQs are automatically imported from your email inbox',
  },
  NO_QUOTES: {
    icon: '📝',
    title: 'No quotes created',
    description: 'Create a quote from an RFQ to get started',
  },
  NO_JOBS: {
    icon: '🏭',
    title: 'No active jobs',
    description: 'Jobs appear here once quotes are converted',
  },
} as const;

// =============================================================================
// OFFLINE RESILIENCE COMPONENTS
// =============================================================================

interface OfflineBannerProps {
  /** Current offline status */
  status: OfflineStatus;
  /** Number of pending sync items */
  pendingCount?: number;
  /** Last online timestamp */
  lastOnline?: Date;
  /** Dismiss action */
  onDismiss?: () => void;
  /** Retry connection action */
  onRetry?: () => void;
  className?: string;
}

/**
 * Persistent offline banner that doesn't obstruct content
 */
export function OfflineBanner({
  status,
  pendingCount = 0,
  lastOnline,
  onDismiss,
  onRetry,
  className,
}: OfflineBannerProps) {
  if (status === 'online') return null;

  const isReconnecting = status === 'reconnecting';

  const formatLastOnline = () => {
    if (!lastOnline) return 'Unknown';
    const diff = Date.now() - lastOnline.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
    return `${Math.floor(diff / 3600000)} hours ago`;
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-2 text-sm',
        isReconnecting
          ? 'bg-yellow-100 text-yellow-800'
          : 'bg-gray-100 text-gray-800',
        className
      )}
    >
      <div className="flex items-center gap-2">
        <span className={cn('w-2 h-2 rounded-full', isReconnecting ? 'animate-pulse bg-yellow-500' : 'bg-gray-500')} />
        <span>
          {isReconnecting ? 'Reconnecting...' : 'You are offline'}
        </span>
        {pendingCount > 0 && (
          <span className="px-2 py-0.5 bg-current/10 rounded-full text-xs">
            {pendingCount} pending
          </span>
        )}
        {lastOnline && (
          <span className="text-xs opacity-70">
            Last online: {formatLastOnline()}
          </span>
        )}
      </div>
      
      <div className="flex items-center gap-2">
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-2 py-1 text-xs font-medium hover:bg-current/10 rounded transition-colors"
          >
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 hover:bg-current/10 rounded"
            aria-label="Dismiss"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Read-only indicator for fields that can't be edited offline
 */
export function ReadOnlyIndicator({
  reason = 'Available when online',
  className,
}: {
  reason?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs',
        className
      )}
      role="status"
      aria-label="Read-only mode"
    >
      <span aria-hidden="true">🔒</span>
      <span>{reason}</span>
    </div>
  );
}

/**
 * Queue indicator showing pending offline sync items
 */
export function SyncQueueIndicator({
  count,
  onClick,
  className,
}: {
  count: number;
  onClick?: () => void;
  className?: string;
}) {
  if (count === 0) return null;

  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm font-medium hover:bg-blue-200 transition-colors',
        className
      )}
      aria-label={`${count} items pending sync`}
    >
      <span className="animate-spin" aria-hidden="true">↻</span>
      <span>{count} pending</span>
    </button>
  );
}

// =============================================================================
// CONFLICT RESOLUTION UI
// =============================================================================

interface ConflictData {
  field: string;
  localValue: string;
  serverValue: string;
  localTimestamp: Date;
  serverTimestamp: Date;
}

interface ConflictResolutionProps {
  /** Conflict data */
  conflicts: ConflictData[];
  /** Resolution callback */
  onResolve: (resolutions: Record<string, { strategy: ConflictStrategy; value: string }>) => void;
  /** Cancel callback */
  onCancel?: () => void;
  className?: string;
}

/**
 * Conflict resolution UI for handling offline sync conflicts
 */
export function ConflictResolution({
  conflicts,
  onResolve,
  onCancel,
  className,
}: ConflictResolutionProps) {
  const [resolutions, setResolutions] = useState<
    Record<string, { strategy: ConflictStrategy; value: string }>
  >({});

  const handleStrategyChange = (field: string, strategy: ConflictStrategy, value: string) => {
    setResolutions((prev) => ({
      ...prev,
      [field]: { strategy, value },
    }));
  };

  const handleResolveAll = (strategy: ConflictStrategy) => {
    const allResolutions: Record<string, { strategy: ConflictStrategy; value: string }> = {};
    conflicts.forEach((conflict) => {
      const value = strategy === 'keep-local' ? conflict.localValue : conflict.serverValue;
      allResolutions[conflict.field] = { strategy, value };
    });
    setResolutions(allResolutions);
  };

  const allResolved = conflicts.every((c) => resolutions[c.field]);

  return (
    <div className={cn('rounded-lg border bg-card p-4 space-y-4', className)}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Resolve Conflicts</h3>
        <div className="flex gap-2">
          <button
            onClick={() => handleResolveAll('keep-local')}
            className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800 hover:bg-blue-200"
          >
            Keep All Local
          </button>
          <button
            onClick={() => handleResolveAll('keep-server')}
            className="text-xs px-2 py-1 rounded bg-green-100 text-green-800 hover:bg-green-200"
          >
            Keep All Server
          </button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        Some changes made while offline conflict with server updates. Choose which version to keep.
      </p>

      <div className="space-y-3">
        {conflicts.map((conflict) => {
          const resolution = resolutions[conflict.field];
          
          return (
            <div key={conflict.field} className="border rounded-lg p-3 space-y-2">
              <div className="font-medium">{conflict.field}</div>
              
              <div className="grid grid-cols-2 gap-3 text-sm">
                <button
                  onClick={() => handleStrategyChange(conflict.field, 'keep-local', conflict.localValue)}
                  className={cn(
                    'p-2 rounded border text-left transition-colors',
                    resolution?.strategy === 'keep-local'
                      ? 'border-blue-500 bg-blue-50'
                      : 'hover:bg-muted'
                  )}
                >
                  <div className="text-xs text-muted-foreground mb-1">Your changes</div>
                  <div className="font-mono text-xs truncate">{conflict.localValue}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {conflict.localTimestamp.toLocaleString()}
                  </div>
                </button>
                
                <button
                  onClick={() => handleStrategyChange(conflict.field, 'keep-server', conflict.serverValue)}
                  className={cn(
                    'p-2 rounded border text-left transition-colors',
                    resolution?.strategy === 'keep-server'
                      ? 'border-green-500 bg-green-50'
                      : 'hover:bg-muted'
                  )}
                >
                  <div className="text-xs text-muted-foreground mb-1">Server version</div>
                  <div className="font-mono text-xs truncate">{conflict.serverValue}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {conflict.serverTimestamp.toLocaleString()}
                  </div>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-end gap-3 pt-2 border-t">
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium hover:bg-muted rounded transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          onClick={() => onResolve(resolutions)}
          disabled={!allResolved}
          className={cn(
            'px-4 py-2 text-sm font-medium rounded transition-colors',
            allResolved
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-muted text-muted-foreground cursor-not-allowed'
          )}
        >
          Apply Resolutions
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// NETWORK STATUS HOOK
// =============================================================================

interface NetworkStatus {
  isOnline: boolean;
  effectiveType?: string;
  downlink?: number;
  rtt?: number;
}

/**
 * Hook to track network status
 */
export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  });

  useEffect(() => {
    const updateStatus = () => {
      const connection = (navigator as any).connection;
      setStatus({
        isOnline: navigator.onLine,
        effectiveType: connection?.effectiveType,
        downlink: connection?.downlink,
        rtt: connection?.rtt,
      });
    };

    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);

    const connection = (navigator as any).connection;
    if (connection) {
      connection.addEventListener('change', updateStatus);
    }

    return () => {
      window.removeEventListener('online', updateStatus);
      window.removeEventListener('offline', updateStatus);
      if (connection) {
        connection.removeEventListener('change', updateStatus);
      }
    };
  }, []);

  return status;
}

// =============================================================================
// OFFLINE CONTEXT
// =============================================================================

interface OfflineContextValue {
  status: OfflineStatus;
  pendingQueue: Array<{ id: string; action: string; timestamp: number }>;
  addToQueue: (action: { id: string; action: string }) => void;
  removeFromQueue: (id: string) => void;
  clearQueue: () => void;
}

const OfflineContext = createContext<OfflineContextValue | null>(null);

/**
 * Provider for offline state management
 */
export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const networkStatus = useNetworkStatus();
  const [status, setStatus] = useState<OfflineStatus>(
    networkStatus.isOnline ? 'online' : 'offline'
  );
  const [pendingQueue, setPendingQueue] = useState<
    Array<{ id: string; action: string; timestamp: number }>
  >([]);

  useEffect(() => {
    if (networkStatus.isOnline) {
      if (status === 'offline') {
        setStatus('reconnecting');
        // Simulate reconnection delay
        const timer = setTimeout(() => setStatus('online'), 1000);
        return () => clearTimeout(timer);
      }
    } else {
      setStatus('offline');
    }
  }, [networkStatus.isOnline, status]);

  const addToQueue = useCallback((action: { id: string; action: string }) => {
    setPendingQueue((prev) => [...prev, { ...action, timestamp: Date.now() }]);
  }, []);

  const removeFromQueue = useCallback((id: string) => {
    setPendingQueue((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clearQueue = useCallback(() => {
    setPendingQueue([]);
  }, []);

  const value = useMemo(
    () => ({
      status,
      pendingQueue,
      addToQueue,
      removeFromQueue,
      clearQueue,
    }),
    [status, pendingQueue, addToQueue, removeFromQueue, clearQueue]
  );

  return (
    <OfflineContext.Provider value={value}>
      {children}
    </OfflineContext.Provider>
  );
}

/**
 * Hook to use offline context
 */
export function useOfflineStatus() {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error('useOfflineStatus must be used within OfflineProvider');
  }
  return context;
}

// =============================================================================
// ERROR BOUNDARY
// =============================================================================

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode | ((error: Error, reset: () => void) => React.ReactNode);
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component with fallback UI
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.props.onError?.(error, errorInfo);
  }

  resetError = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (typeof this.props.fallback === 'function' && this.state.error) {
        return this.props.fallback(this.state.error, this.resetError);
      }
      
      if (this.props.fallback) {
        if (typeof this.props.fallback === 'function') {
          return (this.props.fallback as any)(this.state.error, () => this.setState({ hasError: false, error: null }));
        }
        return this.props.fallback;
      }

      return (
        <ServerErrorPage
          error={this.state.error || undefined}
          onCheckHealth={this.resetError}
        />
      );
    }

    return this.props.children;
  }
}

// =============================================================================
// FORM VALIDATION HELPERS
// =============================================================================

interface ValidationError {
  field: string;
  message: string;
  expected?: string;
  code?: string;
}

/**
 * Format validation errors from API response
 */
export function formatValidationErrors(
  errors: ValidationError[]
): Record<string, { message: string; expected?: string }> {
  return errors.reduce(
    (acc, error) => ({
      ...acc,
      [error.field]: {
        message: error.message,
        expected: error.expected,
      },
    }),
    {}
  );
}

/**
 * Get field-level error message
 */
export function getFieldError(
  errors: Record<string, { message: string; expected?: string }>,
  field: string
): { message: string; expected?: string } | undefined {
  return errors[field];
}

/**
 * Create actionable error message from field and validation rule
 */
export function createActionableMessage(
  field: string,
  rule: string,
  context?: string
): string {
  const fieldName = field.replace(/([A-Z])/g, ' $1').toLowerCase().trim();
  
  const ruleMessages: Record<string, string> = {
    required: `${fieldName} is required`,
    email: `${fieldName} must be a valid email address`,
    minLength: `${fieldName} is too short`,
    maxLength: `${fieldName} is too long`,
    pattern: `${fieldName} format is invalid`,
    min: `${fieldName} value is too low`,
    max: `${fieldName} value is too high`,
  };

  const baseMessage = ruleMessages[rule] || `${fieldName} is invalid`;
  return context ? `${baseMessage}. ${context}` : baseMessage;
}

// =============================================================================
// 404 NOT FOUND COMPONENT
// =============================================================================

/**
 * 404 Not Found page with navigation options
 */
export function NotFoundPage({
  title = 'Page not found',
  message = "The page you're looking for doesn't exist or has been moved.",
  onGoBack,
  onGoHome,
  onSearch,
  className,
}: {
  title?: string;
  message?: string;
  onGoBack?: () => void;
  onGoHome?: () => void;
  onSearch?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center min-h-[400px] text-center px-4',
        className
      )}
    >
      <div className="text-8xl mb-4 text-muted-foreground" aria-hidden="true">
        404
      </div>
      <h1 className="text-2xl font-bold mb-2">{title}</h1>
      <p className="text-muted-foreground max-w-md mb-6">{message}</p>
      
      <div className="flex flex-wrap gap-3 justify-center">
        {onGoBack && (
          <button
            onClick={onGoBack}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 transition-colors"
          >
            Go Back
          </button>
        )}
        {onGoHome && (
          <button
            onClick={onGoHome}
            className="px-4 py-2 border rounded-md font-medium hover:bg-muted transition-colors"
          >
            Go to Home
          </button>
        )}
        {onSearch && (
          <button
            onClick={onSearch}
            className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            Search
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Tests for Error & Edge Case Experience Components
 * 
 * Section 19.5: Error & Edge Case Experience
 * 
 * Tests:
 * - Actionable error messages
 * - Empty state components
 * - Offline resilience
 * - Conflict resolution UI
 * - Error boundary
 * - Network status hook
 */

import React from 'react';
import { screen, fireEvent, act, waitFor } from '@testing-library/react';
import { renderWithI18n } from '@/test-utils';
import {
  ERROR_SEVERITY,
  OFFLINE_STATUS,
  CONFLICT_STRATEGY,
  ActionableError,
  FieldError,
  ServerErrorPage,
  EmptyState,
  EMPTY_STATE_PRESETS,
  OfflineBanner,
  ReadOnlyIndicator,
  SyncQueueIndicator,
  ConflictResolution,
  useNetworkStatus,
  OfflineProvider,
  useOfflineStatus,
  ErrorBoundary,
  formatValidationErrors,
  getFieldError,
  createActionableMessage,
  NotFoundPage,
} from '../error-experience';

const render = renderWithI18n;

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Error Experience Constants', () => {
  describe('ERROR_SEVERITY', () => {
    it('should have all severity levels', () => {
      expect(ERROR_SEVERITY.INFO).toBe('info');
      expect(ERROR_SEVERITY.WARNING).toBe('warning');
      expect(ERROR_SEVERITY.ERROR).toBe('error');
      expect(ERROR_SEVERITY.CRITICAL).toBe('critical');
    });
  });

  describe('OFFLINE_STATUS', () => {
    it('should have all offline statuses', () => {
      expect(OFFLINE_STATUS.ONLINE).toBe('online');
      expect(OFFLINE_STATUS.OFFLINE).toBe('offline');
      expect(OFFLINE_STATUS.RECONNECTING).toBe('reconnecting');
    });
  });

  describe('CONFLICT_STRATEGY', () => {
    it('should have all conflict strategies', () => {
      expect(CONFLICT_STRATEGY.KEEP_LOCAL).toBe('keep-local');
      expect(CONFLICT_STRATEGY.KEEP_SERVER).toBe('keep-server');
      expect(CONFLICT_STRATEGY.MERGE).toBe('merge');
      expect(CONFLICT_STRATEGY.MANUAL).toBe('manual');
    });
  });
});

// =============================================================================
// ACTIONABLE ERROR TESTS
// =============================================================================

describe('ActionableError', () => {
  it('renders with title and message', () => {
    render(
      <ActionableError
        title="Validation Failed"
        message="Please check your input"
      />
    );
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Validation Failed')).toBeInTheDocument();
    expect(screen.getByText('Please check your input')).toBeInTheDocument();
  });

  it('displays field information', () => {
    render(
      <ActionableError
        title="Error"
        message="Invalid value"
        field="Email Address"
      />
    );
    
    expect(screen.getByText(/Field:/)).toBeInTheDocument();
    expect(screen.getByText('Email Address')).toBeInTheDocument();
  });

  it('displays expected format hint', () => {
    render(
      <ActionableError
        title="Error"
        message="Invalid format"
        expectedFormat="name@example.com"
      />
    );
    
    expect(screen.getByText(/Expected:/)).toBeInTheDocument();
    expect(screen.getByText('name@example.com')).toBeInTheDocument();
  });

  it('displays reason for validation', () => {
    render(
      <ActionableError
        title="Error"
        message="Invalid"
        reason="Email is required for notifications"
      />
    );
    
    expect(screen.getByText(/Reason:/)).toBeInTheDocument();
    expect(screen.getByText('Email is required for notifications')).toBeInTheDocument();
  });

  it('calls onRetry when Try Again is clicked', () => {
    const onRetry = jest.fn();
    render(
      <ActionableError
        title="Error"
        message="Failed"
        onRetry={onRetry}
      />
    );
    
    fireEvent.click(screen.getByText('Try Again'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = jest.fn();
    render(
      <ActionableError
        title="Error"
        message="Failed"
        onDismiss={onDismiss}
      />
    );
    
    fireEvent.click(screen.getByLabelText('Dismiss error'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('calls onReport when Report Issue is clicked', () => {
    const onReport = jest.fn();
    render(
      <ActionableError
        title="Error"
        message="Failed"
        onReport={onReport}
      />
    );
    
    fireEvent.click(screen.getByText('Report Issue'));
    expect(onReport).toHaveBeenCalled();
  });

  it('renders custom actions', () => {
    const action = jest.fn();
    render(
      <ActionableError
        title="Error"
        message="Failed"
        actions={[{ label: 'Custom Action', onClick: action }]}
      />
    );
    
    fireEvent.click(screen.getByText('Custom Action'));
    expect(action).toHaveBeenCalled();
  });

  it('applies severity styles', () => {
    const { rerender } = render(
      <ActionableError title="Info" message="Info message" severity="info" />
    );
    expect(screen.getByRole('alert').className).toContain('bg-blue-50');

    rerender(
      <ActionableError title="Warning" message="Warning message" severity="warning" />
    );
    expect(screen.getByRole('alert').className).toContain('bg-yellow-50');
  });
});

describe('FieldError', () => {
  it('renders error message', () => {
    render(<FieldError message="This field is required" />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('This field is required')).toBeInTheDocument();
  });

  it('displays expected format', () => {
    render(<FieldError message="Invalid email" expected="name@example.com" />);
    
    expect(screen.getByText(/Expected:/)).toBeInTheDocument();
    expect(screen.getByText(/name@example\.com/)).toBeInTheDocument();
  });

  it('accepts id prop for aria-describedby', () => {
    render(<FieldError message="Error" id="email-error" />);
    
    expect(screen.getByRole('alert')).toHaveAttribute('id', 'email-error');
  });
});

describe('ServerErrorPage', () => {
  it('renders error page content', () => {
    render(<ServerErrorPage />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('displays error message when provided', () => {
    render(<ServerErrorPage error="Database connection failed" />);
    
    expect(screen.getByText('Database connection failed')).toBeInTheDocument();
  });

  it('displays Error object message', () => {
    render(<ServerErrorPage error={new Error('Connection timeout')} />);
    
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  it('calls onCheckHealth when button is clicked', () => {
    const onCheckHealth = jest.fn();
    render(<ServerErrorPage onCheckHealth={onCheckHealth} />);
    
    fireEvent.click(screen.getByText('Check System Health'));
    expect(onCheckHealth).toHaveBeenCalled();
  });

  it('calls onReportIssue when button is clicked', () => {
    const onReportIssue = jest.fn();
    render(<ServerErrorPage onReportIssue={onReportIssue} />);
    
    fireEvent.click(screen.getByText('Report Issue'));
    expect(onReportIssue).toHaveBeenCalled();
  });

  it('calls onGoHome when button is clicked', () => {
    const onGoHome = jest.fn();
    render(<ServerErrorPage onGoHome={onGoHome} />);
    
    fireEvent.click(screen.getByText('Go to Home'));
    expect(onGoHome).toHaveBeenCalled();
  });
});

// =============================================================================
// EMPTY STATE TESTS
// =============================================================================

describe('EmptyState', () => {
  it('renders with title', () => {
    render(<EmptyState title="No items" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('No items')).toBeInTheDocument();
  });

  it('renders icon', () => {
    render(<EmptyState title="No items" icon="📋" />);
    
    expect(screen.getByText('📋')).toBeInTheDocument();
  });

  it('renders description', () => {
    render(
      <EmptyState
        title="No items"
        description="Get started by creating your first item"
      />
    );
    
    expect(screen.getByText('Get started by creating your first item')).toBeInTheDocument();
  });

  it('renders reason', () => {
    render(
      <EmptyState
        title="No results"
        reason="Your filters may be too restrictive"
      />
    );
    
    expect(screen.getByText('Your filters may be too restrictive')).toBeInTheDocument();
  });

  it('calls primaryAction onClick', () => {
    const onClick = jest.fn();
    render(
      <EmptyState
        title="No items"
        primaryAction={{ label: 'Create Item', onClick }}
      />
    );
    
    fireEvent.click(screen.getByText('Create Item'));
    expect(onClick).toHaveBeenCalled();
  });

  it('calls secondaryAction onClick', () => {
    const onClick = jest.fn();
    render(
      <EmptyState
        title="No items"
        secondaryAction={{ label: 'Learn More', onClick }}
      />
    );
    
    fireEvent.click(screen.getByText('Learn More'));
    expect(onClick).toHaveBeenCalled();
  });

  it('renders educational tip when showTip is true', () => {
    render(
      <EmptyState
        title="No items"
        showTip
        tip="This is a helpful tip"
      />
    );
    
    expect(screen.getByText(/This is a helpful tip/)).toBeInTheDocument();
  });
});

describe('EMPTY_STATE_PRESETS', () => {
  it('has NO_RESULTS preset', () => {
    expect(EMPTY_STATE_PRESETS.NO_RESULTS.title).toBe('No results found');
  });

  it('has NO_ITEMS preset', () => {
    expect(EMPTY_STATE_PRESETS.NO_ITEMS.title).toBe('No items yet');
  });

  it('has NO_RFQS preset', () => {
    expect(EMPTY_STATE_PRESETS.NO_RFQS.title).toBe('No RFQs in queue');
  });

  it('has NO_QUOTES preset', () => {
    expect(EMPTY_STATE_PRESETS.NO_QUOTES.title).toBe('No quotes created');
  });

  it('has NO_JOBS preset', () => {
    expect(EMPTY_STATE_PRESETS.NO_JOBS.title).toBe('No active jobs');
  });
});

// =============================================================================
// OFFLINE RESILIENCE TESTS
// =============================================================================

describe('OfflineBanner', () => {
  it('returns null when online', () => {
    const { container } = render(<OfflineBanner status="online" />);
    
    expect(container.firstChild).toBeNull();
  });

  it('renders when offline', () => {
    render(<OfflineBanner status="offline" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('You are offline')).toBeInTheDocument();
  });

  it('shows reconnecting state', () => {
    render(<OfflineBanner status="reconnecting" />);
    
    expect(screen.getByText('Reconnecting...')).toBeInTheDocument();
  });

  it('displays pending count', () => {
    render(<OfflineBanner status="offline" pendingCount={5} />);
    
    expect(screen.getByText('5 pending')).toBeInTheDocument();
  });

  it('displays last online time', () => {
    const lastOnline = new Date(Date.now() - 2 * 60 * 1000); // 2 minutes ago
    render(<OfflineBanner status="offline" lastOnline={lastOnline} />);
    
    expect(screen.getByText(/Last online:/)).toBeInTheDocument();
    expect(screen.getByText(/2 minutes ago/)).toBeInTheDocument();
  });

  it('calls onRetry when clicked', () => {
    const onRetry = jest.fn();
    render(<OfflineBanner status="offline" onRetry={onRetry} />);
    
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('calls onDismiss when clicked', () => {
    const onDismiss = jest.fn();
    render(<OfflineBanner status="offline" onDismiss={onDismiss} />);
    
    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(onDismiss).toHaveBeenCalled();
  });
});

describe('ReadOnlyIndicator', () => {
  it('renders with default reason', () => {
    render(<ReadOnlyIndicator />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Available when online')).toBeInTheDocument();
  });

  it('renders with custom reason', () => {
    render(<ReadOnlyIndicator reason="Requires authentication" />);
    
    expect(screen.getByText('Requires authentication')).toBeInTheDocument();
  });

  it('has lock icon', () => {
    render(<ReadOnlyIndicator />);
    
    expect(screen.getByText('🔒')).toBeInTheDocument();
  });
});

describe('SyncQueueIndicator', () => {
  it('returns null when count is 0', () => {
    const { container } = render(<SyncQueueIndicator count={0} />);
    
    expect(container.firstChild).toBeNull();
  });

  it('renders when count > 0', () => {
    render(<SyncQueueIndicator count={3} />);
    
    expect(screen.getByLabelText('3 items pending sync')).toBeInTheDocument();
    expect(screen.getByText('3 pending')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = jest.fn();
    render(<SyncQueueIndicator count={5} onClick={onClick} />);
    
    fireEvent.click(screen.getByText('5 pending'));
    expect(onClick).toHaveBeenCalled();
  });
});

// =============================================================================
// CONFLICT RESOLUTION TESTS
// =============================================================================

describe('ConflictResolution', () => {
  const mockConflicts = [
    {
      field: 'Customer Name',
      localValue: 'Acme Corp',
      serverValue: 'ACME Corporation',
      localTimestamp: new Date('2024-01-15T10:00:00'),
      serverTimestamp: new Date('2024-01-15T11:00:00'),
    },
    {
      field: 'Email',
      localValue: 'old@email.com',
      serverValue: 'new@email.com',
      localTimestamp: new Date('2024-01-15T10:00:00'),
      serverTimestamp: new Date('2024-01-15T11:00:00'),
    },
  ];

  it('renders conflicts', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    expect(screen.getByText('Resolve Conflicts')).toBeInTheDocument();
    expect(screen.getByText('Customer Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('displays local and server values', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('ACME Corporation')).toBeInTheDocument();
  });

  it('allows selecting local value', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    // Click on local value option
    fireEvent.click(screen.getByText('Acme Corp'));
    
    // The button should now have the selected style
    expect(screen.getByText('Acme Corp').closest('button')).toHaveClass('border-blue-500');
  });

  it('allows selecting server value', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    // Click on server value option
    fireEvent.click(screen.getByText('ACME Corporation'));
    
    expect(screen.getByText('ACME Corporation').closest('button')).toHaveClass('border-green-500');
  });

  it('has Keep All Local button', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    expect(screen.getByText('Keep All Local')).toBeInTheDocument();
  });

  it('has Keep All Server button', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    expect(screen.getByText('Keep All Server')).toBeInTheDocument();
  });

  it('calls onResolve when Apply is clicked after all resolved', () => {
    const onResolve = jest.fn();
    render(<ConflictResolution conflicts={mockConflicts} onResolve={onResolve} />);
    
    // Click Keep All Local to resolve all
    fireEvent.click(screen.getByText('Keep All Local'));
    
    // Now Apply should be enabled
    fireEvent.click(screen.getByText('Apply Resolutions'));
    
    expect(onResolve).toHaveBeenCalledWith({
      'Customer Name': { strategy: 'keep-local', value: 'Acme Corp' },
      'Email': { strategy: 'keep-local', value: 'old@email.com' },
    });
  });

  it('calls onCancel when Cancel is clicked', () => {
    const onCancel = jest.fn();
    render(
      <ConflictResolution
        conflicts={mockConflicts}
        onResolve={jest.fn()}
        onCancel={onCancel}
      />
    );
    
    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('disables Apply button until all conflicts are resolved', () => {
    render(<ConflictResolution conflicts={mockConflicts} onResolve={jest.fn()} />);
    
    const applyButton = screen.getByText('Apply Resolutions');
    expect(applyButton).toBeDisabled();
  });
});

// =============================================================================
// NETWORK STATUS HOOK TESTS
// =============================================================================

describe('useNetworkStatus', () => {
  function TestComponent() {
    const status = useNetworkStatus();
    return (
      <div>
        <div data-testid="online">{status.isOnline ? 'online' : 'offline'}</div>
      </div>
    );
  }

  it('returns current online status', () => {
    render(<TestComponent />);
    
    // By default, navigator.onLine is true in jsdom
    expect(screen.getByTestId('online')).toHaveTextContent('online');
  });
});

// =============================================================================
// OFFLINE PROVIDER TESTS
// =============================================================================

describe('OfflineProvider', () => {
  function TestComponent() {
    const { status, pendingQueue, addToQueue, removeFromQueue, clearQueue } =
      useOfflineStatus();

    return (
      <div>
        <div data-testid="status">{status}</div>
        <div data-testid="queue">{pendingQueue.length}</div>
        <button onClick={() => addToQueue({ id: '1', action: 'test' })}>Add</button>
        <button onClick={() => removeFromQueue('1')}>Remove</button>
        <button onClick={clearQueue}>Clear</button>
      </div>
    );
  }

  it('throws error when used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => render(<TestComponent />)).toThrow(
      'useOfflineStatus must be used within OfflineProvider'
    );

    consoleError.mockRestore();
  });

  it('provides initial status', () => {
    render(
      <OfflineProvider>
        <TestComponent />
      </OfflineProvider>
    );
    
    expect(screen.getByTestId('status')).toHaveTextContent('online');
  });

  it('adds to pending queue', () => {
    render(
      <OfflineProvider>
        <TestComponent />
      </OfflineProvider>
    );

    expect(screen.getByTestId('queue')).toHaveTextContent('0');
    
    fireEvent.click(screen.getByText('Add'));
    
    expect(screen.getByTestId('queue')).toHaveTextContent('1');
  });

  it('removes from pending queue', () => {
    render(
      <OfflineProvider>
        <TestComponent />
      </OfflineProvider>
    );

    fireEvent.click(screen.getByText('Add'));
    expect(screen.getByTestId('queue')).toHaveTextContent('1');

    fireEvent.click(screen.getByText('Remove'));
    expect(screen.getByTestId('queue')).toHaveTextContent('0');
  });

  it('clears pending queue', () => {
    render(
      <OfflineProvider>
        <TestComponent />
      </OfflineProvider>
    );

    fireEvent.click(screen.getByText('Add'));
    fireEvent.click(screen.getByText('Add'));
    expect(screen.getByTestId('queue')).toHaveTextContent('2');

    fireEvent.click(screen.getByText('Clear'));
    expect(screen.getByTestId('queue')).toHaveTextContent('0');
  });
});

// =============================================================================
// ERROR BOUNDARY TESTS
// =============================================================================

describe('ErrorBoundary', () => {
  const ThrowingComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
    if (shouldThrow) {
      throw new Error('Test error');
    }
    return <div>Content</div>;
  };

  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Content</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('renders fallback when error occurs', () => {
    render(
      <ErrorBoundary fallback={<div>Error occurred</div>}>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Error occurred')).toBeInTheDocument();
  });

  it('renders default error page when no fallback provided', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('calls onError callback', () => {
    const onError = jest.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0][0].message).toBe('Test error');
  });

  it('supports function fallback with error and reset', () => {
    render(
      <ErrorBoundary
        fallback={(error, reset) => (
          <div>
            <span>Error: {error.message}</span>
            <button onClick={reset}>Reset</button>
          </div>
        )}
      >
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Error: Test error')).toBeInTheDocument();
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });
});

// =============================================================================
// VALIDATION HELPER TESTS
// =============================================================================

describe('Validation Helpers', () => {
  describe('formatValidationErrors', () => {
    it('formats array of errors to object', () => {
      const errors = [
        { field: 'email', message: 'Invalid email', expected: 'name@example.com' },
        { field: 'name', message: 'Name is required' },
      ];

      const result = formatValidationErrors(errors);

      expect(result.email).toEqual({ message: 'Invalid email', expected: 'name@example.com' });
      expect(result.name).toEqual({ message: 'Name is required', expected: undefined });
    });
  });

  describe('getFieldError', () => {
    it('returns error for existing field', () => {
      const errors = {
        email: { message: 'Invalid email', expected: 'name@example.com' },
      };

      const result = getFieldError(errors, 'email');
      expect(result).toEqual({ message: 'Invalid email', expected: 'name@example.com' });
    });

    it('returns undefined for non-existing field', () => {
      const errors = {};
      
      const result = getFieldError(errors, 'email');
      expect(result).toBeUndefined();
    });
  });

  describe('createActionableMessage', () => {
    it('creates message for required rule', () => {
      const result = createActionableMessage('email', 'required');
      expect(result).toBe('email is required');
    });

    it('creates message for email rule', () => {
      const result = createActionableMessage('userEmail', 'email');
      expect(result).toBe('user email must be a valid email address');
    });

    it('adds context when provided', () => {
      const result = createActionableMessage('email', 'required', 'Used for notifications');
      expect(result).toBe('email is required. Used for notifications');
    });

    it('handles unknown rules', () => {
      const result = createActionableMessage('field', 'unknownRule');
      expect(result).toBe('field is invalid');
    });
  });
});

// =============================================================================
// NOT FOUND PAGE TESTS
// =============================================================================

describe('NotFoundPage', () => {
  it('renders 404 content', () => {
    render(<NotFoundPage />);
    
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByText('Page Not Found')).toBeInTheDocument();
  });

  it('renders custom title and message', () => {
    render(
      <NotFoundPage
        title="Resource not found"
        message="The requested resource does not exist"
      />
    );
    
    expect(screen.getByText('Resource not found')).toBeInTheDocument();
    expect(screen.getByText('The requested resource does not exist')).toBeInTheDocument();
  });

  it('calls onGoBack when clicked', () => {
    const onGoBack = jest.fn();
    render(<NotFoundPage onGoBack={onGoBack} />);
    
    fireEvent.click(screen.getByText('Go Back'));
    expect(onGoBack).toHaveBeenCalled();
  });

  it('calls onGoHome when clicked', () => {
    const onGoHome = jest.fn();
    render(<NotFoundPage onGoHome={onGoHome} />);
    
    fireEvent.click(screen.getByText('Go to Home'));
    expect(onGoHome).toHaveBeenCalled();
  });

  it('calls onSearch when clicked', () => {
    const onSearch = jest.fn();
    render(<NotFoundPage onSearch={onSearch} />);
    
    fireEvent.click(screen.getByText('Search'));
    expect(onSearch).toHaveBeenCalled();
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Error Experience Integration', () => {
  it('error flow from boundary to actionable error', () => {
    const onRetry = jest.fn();
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    const ThrowingComponent = () => {
      throw new Error('API call failed');
    };

    render(
      <ErrorBoundary
        fallback={(error, reset) => (
          <ActionableError
            title="Operation Failed"
            message={error.message}
            onRetry={() => {
              reset();
              onRetry();
            }}
          />
        )}
      >
        <ThrowingComponent />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Operation Failed')).toBeInTheDocument();
    expect(screen.getByText('API call failed')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('Try Again'));
    expect(onRetry).toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
  });

  it('offline flow with queue and banner', () => {
    function OfflineApp() {
      const { status, pendingQueue, addToQueue } = useOfflineStatus();
      
      return (
        <div>
          <OfflineBanner status={status} pendingCount={pendingQueue.length} />
          <SyncQueueIndicator count={pendingQueue.length} />
          <button onClick={() => addToQueue({ id: Date.now().toString(), action: 'save' })}>
            Save
          </button>
        </div>
      );
    }

    render(
      <OfflineProvider>
        <OfflineApp />
      </OfflineProvider>
    );

    // Initially online, no banner
    expect(screen.queryByText('You are offline')).not.toBeInTheDocument();

    // Add to queue while online
    fireEvent.click(screen.getByText('Save'));
    
    // Queue indicator should show
    expect(screen.getByText('1 pending')).toBeInTheDocument();
  });
});

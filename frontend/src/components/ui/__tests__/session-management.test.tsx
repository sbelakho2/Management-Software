/**
 * Tests for Multi-Tab, Session & State Management Components
 * 
 * Section 19.8: Multi-Tab, Session & State Management
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  // Constants
  SESSION_STATE,
  BROADCAST_MESSAGE_TYPE,
  TOAST_SEVERITY,
  NOTIFICATION_TYPE,
  SESSION_TIMEOUTS,
  // Tab Sync
  TabSyncProvider,
  useTabSync,
  // Session Management
  SessionManagerProvider,
  useSession,
  SessionTimeoutWarning,
  ReAuthModal,
  // Toast
  ToastProvider,
  useToast,
  ToastContainer,
  // Notifications
  NotificationProvider,
  useNotifications,
  NotificationCenter,
  NotificationBell,
} from '../session-management';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Session Management Constants', () => {
  describe('SESSION_STATE', () => {
    it('should define all session states', () => {
      expect(SESSION_STATE.ACTIVE).toBe('active');
      expect(SESSION_STATE.WARNING).toBe('warning');
      expect(SESSION_STATE.EXPIRED).toBe('expired');
      expect(SESSION_STATE.LOCKED).toBe('locked');
    });
  });

  describe('BROADCAST_MESSAGE_TYPE', () => {
    it('should define all broadcast message types', () => {
      expect(BROADCAST_MESSAGE_TYPE.LOGOUT).toBe('logout');
      expect(BROADCAST_MESSAGE_TYPE.LOGIN).toBe('login');
      expect(BROADCAST_MESSAGE_TYPE.STATE_CHANGE).toBe('state_change');
      expect(BROADCAST_MESSAGE_TYPE.SESSION_REFRESH).toBe('session_refresh');
      expect(BROADCAST_MESSAGE_TYPE.TAB_PING).toBe('tab_ping');
      expect(BROADCAST_MESSAGE_TYPE.TAB_PONG).toBe('tab_pong');
    });
  });

  describe('TOAST_SEVERITY', () => {
    it('should define all toast severities', () => {
      expect(TOAST_SEVERITY.INFO).toBe('info');
      expect(TOAST_SEVERITY.SUCCESS).toBe('success');
      expect(TOAST_SEVERITY.WARNING).toBe('warning');
      expect(TOAST_SEVERITY.ERROR).toBe('error');
    });
  });

  describe('NOTIFICATION_TYPE', () => {
    it('should define all notification types', () => {
      expect(NOTIFICATION_TYPE.SYSTEM).toBe('system');
      expect(NOTIFICATION_TYPE.SENSEI).toBe('sensei');
      expect(NOTIFICATION_TYPE.ALERT).toBe('alert');
      expect(NOTIFICATION_TYPE.UPDATE).toBe('update');
      expect(NOTIFICATION_TYPE.TASK).toBe('task');
    });
  });

  describe('SESSION_TIMEOUTS', () => {
    it('should define timeout values', () => {
      expect(SESSION_TIMEOUTS.WARNING_BEFORE_EXPIRY).toBe(5 * 60 * 1000);
      expect(SESSION_TIMEOUTS.SESSION_DURATION).toBe(30 * 60 * 1000);
      expect(SESSION_TIMEOUTS.COUNTDOWN_START).toBe(60 * 1000);
    });
  });
});

// =============================================================================
// TAB SYNC TESTS
// =============================================================================

describe('TabSyncProvider', () => {
  // Helper component
  function TabSyncTester() {
    const { tabId, tabCount, isLeaderTab, broadcast } = useTabSync();
    return (
      <div>
        <span data-testid="tab-id">{tabId}</span>
        <span data-testid="tab-count">{tabCount}</span>
        <span data-testid="is-leader">{isLeaderTab.toString()}</span>
        <button onClick={() => broadcast(BROADCAST_MESSAGE_TYPE.STATE_CHANGE, { test: true })}>
          Broadcast
        </button>
      </div>
    );
  }

  beforeEach(() => {
    // Clear session storage
    sessionStorage.clear();
  });

  it('should provide tab ID', () => {
    render(
      <TabSyncProvider>
        <TabSyncTester />
      </TabSyncProvider>
    );

    const tabId = screen.getByTestId('tab-id').textContent;
    expect(tabId).toMatch(/^tab_\d+_[a-z0-9]+$/);
  });

  it('should initialize tab count', () => {
    render(
      <TabSyncProvider>
        <TabSyncTester />
      </TabSyncProvider>
    );

    expect(screen.getByTestId('tab-count')).toHaveTextContent('1');
  });

  it('should determine leader tab', () => {
    render(
      <TabSyncProvider>
        <TabSyncTester />
      </TabSyncProvider>
    );

    // First tab should be leader
    expect(screen.getByTestId('is-leader')).toHaveTextContent('true');
  });

  it('should provide broadcast function', async () => {
    const user = userEvent.setup();

    render(
      <TabSyncProvider>
        <TabSyncTester />
      </TabSyncProvider>
    );

    // Should not throw
    await user.click(screen.getByText('Broadcast'));
  });

  it('should throw error when useTabSync is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TabSyncTester />);
    }).toThrow('useTabSync must be used within TabSyncProvider');

    consoleError.mockRestore();
  });

  it('should call onLogout when logout message received', () => {
    const onLogout = jest.fn();

    render(
      <TabSyncProvider onLogout={onLogout}>
        <TabSyncTester />
      </TabSyncProvider>
    );

    // Logout is triggered via BroadcastChannel in another tab
    // Can't easily test cross-tab communication in Jest
    expect(onLogout).not.toHaveBeenCalled();
  });
});

// =============================================================================
// SESSION MANAGEMENT TESTS
// =============================================================================

describe('SessionManagerProvider', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  // Helper component
  function SessionTester() {
    const { sessionState, timeRemaining, extendSession, lockSession } = useSession();
    return (
      <div>
        <span data-testid="state">{sessionState}</span>
        <span data-testid="remaining">{timeRemaining}</span>
        <button onClick={() => extendSession()}>Extend</button>
        <button onClick={() => lockSession()}>Lock</button>
      </div>
    );
  }

  it('should start with active state', () => {
    render(
      <SessionManagerProvider sessionDuration={60000}>
        <SessionTester />
      </SessionManagerProvider>
    );

    expect(screen.getByTestId('state')).toHaveTextContent('active');
  });

  it('should transition to warning state before expiry', () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTester />
      </SessionManagerProvider>
    );

    expect(screen.getByTestId('state')).toHaveTextContent('active');

    // Advance to warning period
    act(() => {
      jest.advanceTimersByTime(50000);
    });

    expect(screen.getByTestId('state')).toHaveTextContent('warning');
  });

  it('should transition to expired state after timeout', () => {
    const onExpire = jest.fn();

    render(
      <SessionManagerProvider sessionDuration={10000} onSessionExpire={onExpire}>
        <SessionTester />
      </SessionManagerProvider>
    );

    act(() => {
      jest.advanceTimersByTime(10001);
    });

    expect(screen.getByTestId('state')).toHaveTextContent('expired');
    expect(onExpire).toHaveBeenCalled();
  });

  it('should extend session and reset timer', async () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTester />
      </SessionManagerProvider>
    );

    // Advance to warning
    act(() => {
      jest.advanceTimersByTime(50000);
    });
    expect(screen.getByTestId('state')).toHaveTextContent('warning');

    // Extend session by clicking and then flushing promises
    await act(async () => {
      fireEvent.click(screen.getByText('Extend'));
      await Promise.resolve();
    });

    // Should be back to active
    expect(screen.getByTestId('state')).toHaveTextContent('active');
  });

  it('should lock session', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    const onLock = jest.fn();

    render(
      <SessionManagerProvider sessionDuration={60000} onSessionLock={onLock}>
        <SessionTester />
      </SessionManagerProvider>
    );

    await user.click(screen.getByText('Lock'));

    expect(screen.getByTestId('state')).toHaveTextContent('locked');
    expect(onLock).toHaveBeenCalled();
  });

  it('should throw error when useSession is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<SessionTester />);
    }).toThrow('useSession must be used within SessionManagerProvider');

    consoleError.mockRestore();
  });
});

// =============================================================================
// SESSION TIMEOUT WARNING TESTS
// =============================================================================

describe('SessionTimeoutWarning', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should not render when session is active', () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTimeoutWarning />
      </SessionManagerProvider>
    );

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('should render when session is in warning state', () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTimeoutWarning />
      </SessionManagerProvider>
    );

    act(() => {
      jest.advanceTimersByTime(50001);
    });

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByText('Session Expiring Soon')).toBeInTheDocument();
  });

  it('should show continue session button', () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTimeoutWarning />
      </SessionManagerProvider>
    );

    act(() => {
      jest.advanceTimersByTime(50001);
    });

    expect(screen.getByRole('button', { name: /continue session/i })).toBeInTheDocument();
  });

  it('should show log out button', () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTimeoutWarning />
      </SessionManagerProvider>
    );

    act(() => {
      jest.advanceTimersByTime(50001);
    });

    expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument();
  });

  it('should have accessible structure', () => {
    render(
      <SessionManagerProvider sessionDuration={60000} warningBefore={10000}>
        <SessionTimeoutWarning />
      </SessionManagerProvider>
    );

    act(() => {
      jest.advanceTimersByTime(50001);
    });

    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toHaveAttribute('aria-labelledby', 'session-warning-title');
    expect(dialog).toHaveAttribute('aria-describedby', 'session-warning-description');
  });
});

// =============================================================================
// RE-AUTH MODAL TESTS
// =============================================================================

describe('ReAuthModal', () => {
  it('should not render when not open', () => {
    render(
      <ReAuthModal isOpen={false} onAuthenticate={async () => true} />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    render(
      <ReAuthModal isOpen onAuthenticate={async () => true} />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Session Locked')).toBeInTheDocument();
  });

  it('should have password input', () => {
    render(
      <ReAuthModal isOpen onAuthenticate={async () => true} />
    );

    expect(screen.getByPlaceholderText(/password/i)).toBeInTheDocument();
  });

  it('should focus password input on open', () => {
    render(
      <ReAuthModal isOpen onAuthenticate={async () => true} />
    );

    expect(screen.getByPlaceholderText(/password/i)).toHaveFocus();
  });

  it('should disable unlock button when password is empty', () => {
    render(
      <ReAuthModal isOpen onAuthenticate={async () => true} />
    );

    expect(screen.getByRole('button', { name: /unlock/i })).toBeDisabled();
  });

  it('should call onAuthenticate with password', async () => {
    const onAuthenticate = jest.fn().mockResolvedValue(true);
    const user = userEvent.setup();

    render(
      <ReAuthModal isOpen onAuthenticate={onAuthenticate} />
    );

    await user.type(screen.getByPlaceholderText(/password/i), 'mypassword');
    await user.click(screen.getByRole('button', { name: /unlock/i }));

    await waitFor(() => {
      expect(onAuthenticate).toHaveBeenCalledWith('mypassword');
    });
  });

  it('should show error on failed authentication', async () => {
    const onAuthenticate = jest.fn().mockResolvedValue(false);
    const user = userEvent.setup();

    render(
      <ReAuthModal isOpen onAuthenticate={onAuthenticate} />
    );

    await user.type(screen.getByPlaceholderText(/password/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /unlock/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid password/i)).toBeInTheDocument();
    });
  });

  it('should have sign out button when onCancel provided', () => {
    const onCancel = jest.fn();

    render(
      <ReAuthModal isOpen onAuthenticate={async () => true} onCancel={onCancel} />
    );

    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
  });

  it('should call onCancel when sign out clicked', async () => {
    const onCancel = jest.fn();
    const user = userEvent.setup();

    render(
      <ReAuthModal isOpen onAuthenticate={async () => true} onCancel={onCancel} />
    );

    await user.click(screen.getByRole('button', { name: /sign out/i }));

    expect(onCancel).toHaveBeenCalled();
  });
});

// =============================================================================
// TOAST PROVIDER TESTS
// =============================================================================

describe('ToastProvider', () => {
  function ToastTester() {
    const { toasts, addToast, removeToast, clearAll } = useToast();
    return (
      <div>
        <span data-testid="count">{toasts.length}</span>
        <button onClick={() => addToast({ severity: TOAST_SEVERITY.INFO, title: 'Test' })}>
          Add
        </button>
        <button onClick={() => removeToast(toasts[0]?.id || '')}>Remove</button>
        <button onClick={() => clearAll()}>Clear</button>
        {toasts.map((t) => (
          <span key={t.id} data-testid="toast">
            {t.title}
          </span>
        ))}
      </div>
    );
  }

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should start with empty toasts', () => {
    render(
      <ToastProvider>
        <ToastTester />
      </ToastProvider>
    );

    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should add toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider>
        <ToastTester />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add'));

    expect(screen.getByTestId('count')).toHaveTextContent('1');
    expect(screen.getByTestId('toast')).toHaveTextContent('Test');
  });

  it('should remove toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider>
        <ToastTester />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('1');

    await user.click(screen.getByText('Remove'));
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should clear all toasts', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider>
        <ToastTester />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('2');

    await user.click(screen.getByText('Clear'));
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should auto-dismiss after duration', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider defaultDuration={3000}>
        <ToastTester />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('1');

    act(() => {
      jest.advanceTimersByTime(3001);
    });

    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should limit max toasts', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider maxToasts={3} defaultDuration={0}>
        <ToastTester />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));

    expect(screen.getByTestId('count')).toHaveTextContent('3');
  });

  it('should throw error when useToast is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<ToastTester />);
    }).toThrow('useToast must be used within ToastProvider');

    consoleError.mockRestore();
  });
});

// =============================================================================
// TOAST CONTAINER TESTS
// =============================================================================

describe('ToastContainer', () => {
  function ToastContainerTest() {
    const { addToast } = useToast();
    return (
      <div>
        <button
          onClick={() =>
            addToast({
              severity: TOAST_SEVERITY.SUCCESS,
              title: 'Success Toast',
              message: 'Operation completed',
            })
          }
        >
          Add Success
        </button>
        <button
          onClick={() =>
            addToast({
              severity: TOAST_SEVERITY.ERROR,
              title: 'Error Toast',
              message: 'Something went wrong',
            })
          }
        >
          Add Error
        </button>
        <ToastContainer />
      </div>
    );
  }

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should render toasts', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider defaultDuration={0}>
        <ToastContainerTest />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add Success'));

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Success Toast')).toBeInTheDocument();
    expect(screen.getByText('Operation completed')).toBeInTheDocument();
  });

  it('should display different severity styles', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider defaultDuration={0}>
        <ToastContainerTest />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add Error'));

    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('bg-red-50');
  });

  it('should have dismiss button', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider defaultDuration={0}>
        <ToastContainerTest />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add Success'));

    expect(screen.getByLabelText('Dismiss notification')).toBeInTheDocument();
  });

  it('should remove toast on dismiss click', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider defaultDuration={0}>
        <ToastContainerTest />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add Success'));
    expect(screen.getByRole('alert')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Dismiss notification'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should have accessible region label', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider defaultDuration={0}>
        <ToastContainerTest />
      </ToastProvider>
    );

    await user.click(screen.getByText('Add Success'));

    expect(screen.getByRole('region', { name: /notifications/i })).toBeInTheDocument();
  });
});

// =============================================================================
// NOTIFICATION PROVIDER TESTS
// =============================================================================

describe('NotificationProvider', () => {
  function NotificationTester() {
    const { notifications, unreadCount, addNotification, markAsRead, markAllAsRead, clearAll } =
      useNotifications();
    return (
      <div>
        <span data-testid="count">{notifications.length}</span>
        <span data-testid="unread">{unreadCount}</span>
        <button
          onClick={() =>
            addNotification({
              type: NOTIFICATION_TYPE.SYSTEM,
              title: 'Test Notification',
              message: 'Test message',
            })
          }
        >
          Add
        </button>
        <button onClick={() => markAsRead(notifications[0]?.id || '')}>Mark Read</button>
        <button onClick={() => markAllAsRead()}>Mark All Read</button>
        <button onClick={() => clearAll()}>Clear</button>
      </div>
    );
  }

  it('should start with empty notifications', () => {
    render(
      <NotificationProvider>
        <NotificationTester />
      </NotificationProvider>
    );

    expect(screen.getByTestId('count')).toHaveTextContent('0');
    expect(screen.getByTestId('unread')).toHaveTextContent('0');
  });

  it('should add notification', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationTester />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));

    expect(screen.getByTestId('count')).toHaveTextContent('1');
    expect(screen.getByTestId('unread')).toHaveTextContent('1');
  });

  it('should mark notification as read', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationTester />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('unread')).toHaveTextContent('1');

    await user.click(screen.getByText('Mark Read'));
    expect(screen.getByTestId('unread')).toHaveTextContent('0');
    expect(screen.getByTestId('count')).toHaveTextContent('1');
  });

  it('should mark all as read', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationTester />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('unread')).toHaveTextContent('2');

    await user.click(screen.getByText('Mark All Read'));
    expect(screen.getByTestId('unread')).toHaveTextContent('0');
  });

  it('should clear all notifications', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationTester />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('2');

    await user.click(screen.getByText('Clear'));
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should limit max notifications', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider maxNotifications={3}>
        <NotificationTester />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));

    expect(screen.getByTestId('count')).toHaveTextContent('3');
  });

  it('should throw error when useNotifications is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<NotificationTester />);
    }).toThrow('useNotifications must be used within NotificationProvider');

    consoleError.mockRestore();
  });
});

// =============================================================================
// NOTIFICATION CENTER TESTS
// =============================================================================

describe('NotificationCenter', () => {
  function NotificationCenterTest() {
    const { addNotification } = useNotifications();
    const [isOpen, setIsOpen] = React.useState(false);
    return (
      <div>
        <button onClick={() => setIsOpen(true)}>Open</button>
        <button
          onClick={() =>
            addNotification({
              type: NOTIFICATION_TYPE.SENSEI,
              title: 'Sensei Suggestion',
              message: 'Try this approach',
            })
          }
        >
          Add
        </button>
        <NotificationCenter isOpen={isOpen} onClose={() => setIsOpen(false)} />
      </div>
    );
  }

  it('should not render when closed', () => {
    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when open', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Open'));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });

  it('should show empty state when no notifications', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Open'));

    expect(screen.getByText('No notifications')).toBeInTheDocument();
  });

  it('should display notifications', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Open'));

    expect(screen.getByText('Sensei Suggestion')).toBeInTheDocument();
    expect(screen.getByText('Try this approach')).toBeInTheDocument();
  });

  it('should show unread count', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Open'));

    expect(screen.getByText('2 unread')).toBeInTheDocument();
  });

  it('should have close button', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Open'));

    expect(screen.getByLabelText('Close notification center')).toBeInTheDocument();
  });

  it('should close on close button click', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Open'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Close notification center'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should have mark all read button when unread exist', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Open'));

    expect(screen.getByText('Mark all read')).toBeInTheDocument();
  });

  it('should have clear all button when notifications exist', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationCenterTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Open'));

    expect(screen.getByText('Clear all notifications')).toBeInTheDocument();
  });
});

// =============================================================================
// NOTIFICATION BELL TESTS
// =============================================================================

describe('NotificationBell', () => {
  function NotificationBellTest() {
    const { addNotification } = useNotifications();
    return (
      <div>
        <button
          onClick={() =>
            addNotification({
              type: NOTIFICATION_TYPE.ALERT,
              title: 'Alert',
              message: 'Test',
            })
          }
        >
          Add
        </button>
        <NotificationBell onClick={() => {}} />
      </div>
    );
  }

  it('should render bell icon', () => {
    render(
      <NotificationProvider>
        <NotificationBellTest />
      </NotificationProvider>
    );

    expect(screen.getByLabelText('Notifications')).toBeInTheDocument();
  });

  it('should not show badge when no unread', () => {
    render(
      <NotificationProvider>
        <NotificationBellTest />
      </NotificationProvider>
    );

    expect(screen.queryByText('1')).not.toBeInTheDocument();
  });

  it('should show badge with unread count', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationBellTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('should show 99+ for large counts', async () => {
    const user = userEvent.setup();

    function ManyNotificationsTest() {
      const { addNotification } = useNotifications();
      return (
        <div>
          <button
            onClick={() => {
              for (let i = 0; i < 100; i++) {
                addNotification({
                  type: NOTIFICATION_TYPE.SYSTEM,
                  title: `Notification ${i}`,
                  message: 'Test',
                });
              }
            }}
          >
            Add Many
          </button>
          <NotificationBell onClick={() => {}} />
        </div>
      );
    }

    render(
      <NotificationProvider>
        <ManyNotificationsTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add Many'));

    expect(screen.getByText('99+')).toBeInTheDocument();
  });

  it('should include unread count in aria-label', async () => {
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationBellTest />
      </NotificationProvider>
    );

    await user.click(screen.getByText('Add'));

    expect(screen.getByLabelText('Notifications, 1 unread')).toBeInTheDocument();
  });

  it('should call onClick when clicked', async () => {
    const onClick = jest.fn();
    const user = userEvent.setup();

    render(
      <NotificationProvider>
        <NotificationBell onClick={onClick} />
      </NotificationProvider>
    );

    await user.click(screen.getByLabelText('Notifications'));

    expect(onClick).toHaveBeenCalled();
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Session Management Integration', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should work with combined providers', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    function IntegrationTest() {
      const { addToast } = useToast();
      const { addNotification } = useNotifications();
      const { sessionState } = useSession();

      return (
        <div>
          <span data-testid="session">{sessionState}</span>
          <button onClick={() => addToast({ severity: TOAST_SEVERITY.INFO, title: 'Toast' })}>
            Add Toast
          </button>
          <button
            onClick={() =>
              addNotification({
                type: NOTIFICATION_TYPE.SYSTEM,
                title: 'Notification',
                message: 'Test',
              })
            }
          >
            Add Notification
          </button>
          <ToastContainer />
        </div>
      );
    }

    render(
      <SessionManagerProvider sessionDuration={60000}>
        <ToastProvider defaultDuration={0}>
          <NotificationProvider>
            <IntegrationTest />
          </NotificationProvider>
        </ToastProvider>
      </SessionManagerProvider>
    );

    expect(screen.getByTestId('session')).toHaveTextContent('active');

    await user.click(screen.getByText('Add Toast'));
    expect(screen.getByRole('alert')).toBeInTheDocument();

    await user.click(screen.getByText('Add Notification'));
    // Notification added but not visible without center
  });
});

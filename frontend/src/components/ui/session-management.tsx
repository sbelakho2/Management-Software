/**
 * Multi-Tab, Session & State Management Components
 * 
 * Section 19.8: Multi-Tab, Session & State Management
 * 
 * Provides components and utilities for:
 * - Cross-tab synchronization via BroadcastChannel
 * - Session timeout management with warnings
 * - Graceful re-authentication without data loss
 * - Toast stack management
 * - Notification center
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  ReactNode,
} from 'react';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Session states
 */
export const SESSION_STATE = {
  ACTIVE: 'active',
  WARNING: 'warning',
  EXPIRED: 'expired',
  LOCKED: 'locked',
} as const;

export type SessionState = (typeof SESSION_STATE)[keyof typeof SESSION_STATE];

/**
 * Broadcast message types for cross-tab sync
 */
export const BROADCAST_MESSAGE_TYPE = {
  LOGOUT: 'logout',
  LOGIN: 'login',
  STATE_CHANGE: 'state_change',
  SESSION_REFRESH: 'session_refresh',
  TAB_PING: 'tab_ping',
  TAB_PONG: 'tab_pong',
} as const;

export type BroadcastMessageType =
  (typeof BROADCAST_MESSAGE_TYPE)[keyof typeof BROADCAST_MESSAGE_TYPE];

/**
 * Toast severity levels
 */
export const TOAST_SEVERITY = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
} as const;

export type ToastSeverity = (typeof TOAST_SEVERITY)[keyof typeof TOAST_SEVERITY];

/**
 * Notification types
 */
export const NOTIFICATION_TYPE = {
  SYSTEM: 'system',
  SENSEI: 'sensei',
  ALERT: 'alert',
  UPDATE: 'update',
  TASK: 'task',
} as const;

export type NotificationType =
  (typeof NOTIFICATION_TYPE)[keyof typeof NOTIFICATION_TYPE];

/**
 * Default timeouts (in milliseconds)
 */
export const SESSION_TIMEOUTS = {
  WARNING_BEFORE_EXPIRY: 5 * 60 * 1000, // 5 minutes before expiry
  SESSION_DURATION: 30 * 60 * 1000, // 30 minutes
  COUNTDOWN_START: 60 * 1000, // Show countdown in last 60 seconds
} as const;

// =============================================================================
// TYPES
// =============================================================================

export interface BroadcastMessage<T = unknown> {
  type: BroadcastMessageType;
  payload: T;
  tabId: string;
  timestamp: number;
}

export interface ToastMessage {
  id: string;
  severity: ToastSeverity;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
  createdAt: number;
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  read: boolean;
  actionUrl?: string;
  createdAt: Date;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// CROSS-TAB SYNCHRONIZATION
// =============================================================================

const TAB_ID = `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

interface TabSyncContextValue {
  tabId: string;
  tabCount: number;
  isLeaderTab: boolean;
  broadcast: <T>(type: BroadcastMessageType, payload: T) => void;
  subscribe: <T>(
    type: BroadcastMessageType,
    callback: (payload: T) => void
  ) => () => void;
}

const TabSyncContext = createContext<TabSyncContextValue | null>(null);

export interface TabSyncProviderProps {
  children: ReactNode;
  channelName?: string;
  onLogout?: () => void;
  onLogin?: () => void;
}

/**
 * Provider for cross-tab synchronization
 */
export function TabSyncProvider({
  children,
  channelName = 'sensei_tab_sync',
  onLogout,
  onLogin,
}: TabSyncProviderProps) {
  const [tabCount, setTabCount] = useState(1);
  const [isLeaderTab, setIsLeaderTab] = useState(false);
  const channelRef = useRef<BroadcastChannel | null>(null);
  const subscribersRef = useRef<Map<BroadcastMessageType, Set<(payload: unknown) => void>>>(new Map());
  const tabsRef = useRef<Set<string>>(new Set([TAB_ID]));

  useEffect(() => {
    // Check if BroadcastChannel is supported
    if (typeof BroadcastChannel === 'undefined') {
      console.warn('BroadcastChannel not supported, cross-tab sync disabled');
      setIsLeaderTab(true);
      return;
    }

    const channel = new BroadcastChannel(channelName);
    channelRef.current = channel;

    channel.onmessage = (event: MessageEvent<BroadcastMessage>) => {
      const { type, payload, tabId } = event.data;

      // Track other tabs
      if (type === BROADCAST_MESSAGE_TYPE.TAB_PING) {
        tabsRef.current.add(tabId);
        setTabCount(tabsRef.current.size);
        // Respond with pong
        broadcast(BROADCAST_MESSAGE_TYPE.TAB_PONG, { tabId: TAB_ID });
      }

      if (type === BROADCAST_MESSAGE_TYPE.TAB_PONG) {
        tabsRef.current.add(tabId);
        setTabCount(tabsRef.current.size);
      }

      // Handle logout across tabs
      if (type === BROADCAST_MESSAGE_TYPE.LOGOUT) {
        onLogout?.();
      }

      // Handle login across tabs
      if (type === BROADCAST_MESSAGE_TYPE.LOGIN) {
        onLogin?.();
      }

      // Notify subscribers
      const callbacks = subscribersRef.current.get(type);
      if (callbacks) {
        callbacks.forEach((cb) => cb(payload));
      }
    };

    // Announce presence
    broadcast(BROADCAST_MESSAGE_TYPE.TAB_PING, { tabId: TAB_ID });

    // Determine leader (first tab with lowest ID wins)
    const storedLeader = sessionStorage.getItem('sensei_leader_tab');
    if (!storedLeader || storedLeader === TAB_ID) {
      sessionStorage.setItem('sensei_leader_tab', TAB_ID);
      setIsLeaderTab(true);
    }

    // Cleanup on unload
    const handleUnload = () => {
      if (sessionStorage.getItem('sensei_leader_tab') === TAB_ID) {
        sessionStorage.removeItem('sensei_leader_tab');
      }
    };

    window.addEventListener('beforeunload', handleUnload);

    return () => {
      window.removeEventListener('beforeunload', handleUnload);
      channel.close();
      channelRef.current = null;
    };
  }, [channelName, onLogout, onLogin]);

  const broadcast = useCallback(<T,>(type: BroadcastMessageType, payload: T) => {
    if (channelRef.current) {
      const message: BroadcastMessage<T> = {
        type,
        payload,
        tabId: TAB_ID,
        timestamp: Date.now(),
      };
      channelRef.current.postMessage(message);
    }
  }, []);

  const subscribe = useCallback(
    <T,>(type: BroadcastMessageType, callback: (payload: T) => void): (() => void) => {
      if (!subscribersRef.current.has(type)) {
        subscribersRef.current.set(type, new Set());
      }
      subscribersRef.current.get(type)!.add(callback as (payload: unknown) => void);

      return () => {
        subscribersRef.current.get(type)?.delete(callback as (payload: unknown) => void);
      };
    },
    []
  );

  const value: TabSyncContextValue = {
    tabId: TAB_ID,
    tabCount,
    isLeaderTab,
    broadcast,
    subscribe,
  };

  return (
    <TabSyncContext.Provider value={value}>{children}</TabSyncContext.Provider>
  );
}

/**
 * Hook to access tab sync functionality
 */
export function useTabSync(): TabSyncContextValue {
  const context = useContext(TabSyncContext);
  if (!context) {
    throw new Error('useTabSync must be used within TabSyncProvider');
  }
  return context;
}

// =============================================================================
// SESSION MANAGEMENT
// =============================================================================

interface SessionContextValue {
  sessionState: SessionState;
  expiresAt: Date | null;
  timeRemaining: number;
  extendSession: () => Promise<void>;
  lockSession: () => void;
  unlockSession: (credentials: { password: string }) => Promise<boolean>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export interface SessionManagerProviderProps {
  children: ReactNode;
  sessionDuration?: number;
  warningBefore?: number;
  onSessionExpire?: () => void;
  onSessionExtend?: () => Promise<void>;
  onSessionLock?: () => void;
  onUnlock?: (credentials: { password: string }) => Promise<boolean>;
}

/**
 * Provider for session management with timeout warnings
 */
export function SessionManagerProvider({
  children,
  sessionDuration = SESSION_TIMEOUTS.SESSION_DURATION,
  warningBefore = SESSION_TIMEOUTS.WARNING_BEFORE_EXPIRY,
  onSessionExpire,
  onSessionExtend,
  onSessionLock,
  onUnlock,
}: SessionManagerProviderProps) {
  const [sessionState, setSessionState] = useState<SessionState>(SESSION_STATE.ACTIVE);
  const [expiresAt, setExpiresAt] = useState<Date | null>(
    new Date(Date.now() + sessionDuration)
  );
  const [timeRemaining, setTimeRemaining] = useState(sessionDuration);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const warningTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Reset session timer
  const resetTimer = useCallback(() => {
    const newExpiry = new Date(Date.now() + sessionDuration);
    setExpiresAt(newExpiry);
    setTimeRemaining(sessionDuration);
    setSessionState(SESSION_STATE.ACTIVE);

    // Clear existing timers
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    if (warningTimerRef.current) {
      clearTimeout(warningTimerRef.current);
    }

    // Set warning timer
    warningTimerRef.current = setTimeout(() => {
      setSessionState(SESSION_STATE.WARNING);
    }, sessionDuration - warningBefore);

    // Set expiry timer
    timerRef.current = setTimeout(() => {
      setSessionState(SESSION_STATE.EXPIRED);
      onSessionExpire?.();
    }, sessionDuration);
  }, [sessionDuration, warningBefore, onSessionExpire]);

  // Initialize timer on mount
  useEffect(() => {
    resetTimer();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    };
  }, [resetTimer]);

  // Update remaining time
  useEffect(() => {
    const interval = setInterval(() => {
      if (expiresAt && sessionState !== SESSION_STATE.EXPIRED) {
        const remaining = Math.max(0, expiresAt.getTime() - Date.now());
        setTimeRemaining(remaining);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, sessionState]);

  const extendSession = useCallback(async () => {
    try {
      await onSessionExtend?.();
      resetTimer();
    } catch (error) {
      console.error('Failed to extend session:', error);
    }
  }, [onSessionExtend, resetTimer]);

  const lockSession = useCallback(() => {
    setSessionState(SESSION_STATE.LOCKED);
    onSessionLock?.();
  }, [onSessionLock]);

  const unlockSession = useCallback(
    async (credentials: { password: string }): Promise<boolean> => {
      try {
        const success = onUnlock ? await onUnlock(credentials) : true;
        if (success) {
          resetTimer();
          return true;
        }
        return false;
      } catch {
        return false;
      }
    },
    [onUnlock, resetTimer]
  );

  const value: SessionContextValue = {
    sessionState,
    expiresAt,
    timeRemaining,
    extendSession,
    lockSession,
    unlockSession,
  };

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

/**
 * Hook to access session management
 */
export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionManagerProvider');
  }
  return context;
}

// =============================================================================
// SESSION TIMEOUT WARNING
// =============================================================================

export interface SessionTimeoutWarningProps {
  className?: string;
}

/**
 * Session timeout warning with countdown
 */
export function SessionTimeoutWarning({ className = '' }: SessionTimeoutWarningProps) {
  const { sessionState, timeRemaining, extendSession } = useSession();
  const [isExtending, setIsExtending] = useState(false);

  if (sessionState !== SESSION_STATE.WARNING) {
    return null;
  }

  const minutes = Math.floor(timeRemaining / 60000);
  const seconds = Math.floor((timeRemaining % 60000) / 1000);
  const showCountdown = timeRemaining <= SESSION_TIMEOUTS.COUNTDOWN_START;

  const handleExtend = async () => {
    setIsExtending(true);
    try {
      await extendSession();
    } finally {
      setIsExtending(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/50 ${className}`}
      role="alertdialog"
      aria-labelledby="session-warning-title"
      aria-describedby="session-warning-description"
    >
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md mx-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl" aria-hidden="true">⏱️</span>
          <h2
            id="session-warning-title"
            className="text-xl font-bold text-gray-900"
          >
            Session Expiring Soon
          </h2>
        </div>
        <p id="session-warning-description" className="text-gray-600 mb-4">
          Your session will expire in{' '}
          {showCountdown ? (
            <span className="font-mono font-bold text-red-600">
              {seconds}s
            </span>
          ) : (
            <span className="font-bold">
              {minutes} minute{minutes !== 1 ? 's' : ''}
            </span>
          )}{' '}
          due to inactivity.
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleExtend}
            disabled={isExtending}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isExtending ? 'Extending...' : 'Continue Session'}
          </button>
          <button
            type="button"
            onClick={() => window.location.href = '/logout'}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
          >
            Log Out
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// RE-AUTHENTICATION MODAL
// =============================================================================

export interface ReAuthModalProps {
  isOpen: boolean;
  onAuthenticate: (password: string) => Promise<boolean>;
  onCancel?: () => void;
  className?: string;
}

/**
 * Re-authentication modal for graceful session recovery
 */
export function ReAuthModal({
  isOpen,
  onAuthenticate,
  onCancel,
  className = '',
}: ReAuthModalProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const success = await onAuthenticate(password);
      if (!success) {
        setError('Invalid password. Please try again.');
        setPassword('');
        inputRef.current?.focus();
      }
    } catch {
      setError('Authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/50 ${className}`}
      role="dialog"
      aria-labelledby="reauth-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4 w-full">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl" aria-hidden="true">🔒</span>
          <h2 id="reauth-title" className="text-xl font-bold text-gray-900">
            Session Locked
          </h2>
        </div>
        <p className="text-gray-600 mb-4">
          Your session has been locked for security. Enter your password to continue.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="reauth-password" className="sr-only">
              Password
            </label>
            <input
              ref={inputRef}
              id="reauth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              className={`
                w-full px-4 py-2 border rounded-lg
                ${error ? 'border-red-500' : 'border-gray-300'}
                focus:outline-none focus:ring-2 focus:ring-blue-500
              `}
              aria-invalid={!!error}
              aria-describedby={error ? 'reauth-error' : undefined}
            />
            {error && (
              <p id="reauth-error" className="mt-2 text-sm text-red-600">
                {error}
              </p>
            )}
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isLoading || !password}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? 'Verifying...' : 'Unlock'}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Sign Out
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// TOAST MANAGEMENT
// =============================================================================

interface ToastContextValue {
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export interface ToastProviderProps {
  children: ReactNode;
  maxToasts?: number;
  defaultDuration?: number;
}

/**
 * Provider for toast notifications with stack management
 */
export function ToastProvider({
  children,
  maxToasts = 5,
  defaultDuration = 5000,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback(
    (toast: Omit<ToastMessage, 'id' | 'createdAt'>): string => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const newToast: ToastMessage = {
        ...toast,
        id,
        duration: toast.duration ?? defaultDuration,
        dismissible: toast.dismissible ?? true,
        createdAt: Date.now(),
      };

      setToasts((prev) => {
        // Keep only max toasts, removing oldest
        const updated = [...prev, newToast];
        if (updated.length > maxToasts) {
          return updated.slice(-maxToasts);
        }
        return updated;
      });

      // Auto-dismiss after duration
      if (newToast.duration && newToast.duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, newToast.duration);
      }

      return id;
    },
    [defaultDuration, maxToasts]
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  const value: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    clearAll,
  };

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
}

/**
 * Hook to access toast functionality
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

// =============================================================================
// TOAST CONTAINER
// =============================================================================

export interface ToastContainerProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  className?: string;
}

/**
 * Container to render toast notifications
 */
export function ToastContainer({
  position = 'top-right',
  className = '',
}: ToastContainerProps) {
  const { toasts, removeToast } = useToast();

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  };

  const severityStyles = {
    [TOAST_SEVERITY.INFO]: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'ℹ️',
      text: 'text-blue-800',
    },
    [TOAST_SEVERITY.SUCCESS]: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: '✓',
      text: 'text-green-800',
    },
    [TOAST_SEVERITY.WARNING]: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      icon: '⚠️',
      text: 'text-amber-800',
    },
    [TOAST_SEVERITY.ERROR]: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: '✕',
      text: 'text-red-800',
    },
  };

  return (
    <div
      className={`fixed z-50 ${positionClasses[position]} flex flex-col gap-2 max-w-sm ${className}`}
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const styles = severityStyles[toast.severity];
        return (
          <div
            key={toast.id}
            className={`
              ${styles.bg} ${styles.border} ${styles.text}
              border rounded-lg shadow-lg p-4
              animate-slide-in
            `}
            role="alert"
          >
            <div className="flex items-start gap-3">
              <span className="text-lg flex-shrink-0" aria-hidden="true">
                {styles.icon}
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium">{toast.title}</h3>
                {toast.message && (
                  <p className="text-sm mt-1 opacity-80">{toast.message}</p>
                )}
                {toast.action && (
                  <button
                    type="button"
                    onClick={toast.action.onClick}
                    className="text-sm font-medium underline mt-2"
                  >
                    {toast.action.label}
                  </button>
                )}
              </div>
              {toast.dismissible && (
                <button
                  type="button"
                  onClick={() => removeToast(toast.id)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label="Dismiss notification"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// NOTIFICATION CENTER
// =============================================================================

interface NotificationContextValue {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (
    notification: Omit<Notification, 'id' | 'read' | 'createdAt'>
  ) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export interface NotificationProviderProps {
  children: ReactNode;
  maxNotifications?: number;
}

/**
 * Provider for notification center
 */
export function NotificationProvider({
  children,
  maxNotifications = 100,
}: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const addNotification = useCallback(
    (notification: Omit<Notification, 'id' | 'read' | 'createdAt'>) => {
      const id = `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const newNotification: Notification = {
        ...notification,
        id,
        read: false,
        createdAt: new Date(),
      };

      setNotifications((prev) => {
        const updated = [newNotification, ...prev];
        if (updated.length > maxNotifications) {
          return updated.slice(0, maxNotifications);
        }
        return updated;
      });
    },
    [maxNotifications]
  );

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const value: NotificationContextValue = {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

/**
 * Hook to access notification center
 */
export function useNotifications(): NotificationContextValue {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}

// =============================================================================
// NOTIFICATION CENTER UI
// =============================================================================

export interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

/**
 * Notification center panel
 */
export function NotificationCenter({
  isOpen,
  onClose,
  className = '',
}: NotificationCenterProps) {
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearAll } =
    useNotifications();

  if (!isOpen) {
    return null;
  }

  const typeIcons = {
    [NOTIFICATION_TYPE.SYSTEM]: '⚙️',
    [NOTIFICATION_TYPE.SENSEI]: '🧠',
    [NOTIFICATION_TYPE.ALERT]: '🔔',
    [NOTIFICATION_TYPE.UPDATE]: '📢',
    [NOTIFICATION_TYPE.TASK]: '✅',
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <div
      className={`fixed inset-y-0 right-0 w-96 bg-white shadow-2xl z-50 flex flex-col ${className}`}
      role="dialog"
      aria-labelledby="notification-center-title"
      aria-modal="true"
    >
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2
            id="notification-center-title"
            className="text-lg font-bold text-gray-900"
          >
            Notifications
          </h2>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-500">{unreadCount} unread</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={markAllAsRead}
              className="text-sm text-blue-600 hover:underline"
            >
              Mark all read
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close notification center"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <span className="text-4xl mb-2" aria-hidden="true">
              📭
            </span>
            <p>No notifications</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {notifications.map((notification) => (
              <li
                key={notification.id}
                className={`p-4 hover:bg-gray-50 cursor-pointer ${
                  !notification.read ? 'bg-blue-50' : ''
                }`}
                onClick={() => markAsRead(notification.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    markAsRead(notification.id);
                  }
                }}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl" aria-hidden="true">
                    {typeIcons[notification.type]}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h3
                        className={`font-medium truncate ${
                          !notification.read ? 'text-gray-900' : 'text-gray-600'
                        }`}
                      >
                        {notification.title}
                      </h3>
                      {!notification.read && (
                        <span
                          className="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0"
                          aria-label="Unread"
                        />
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {notification.message}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {formatTime(notification.createdAt)}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {notifications.length > 0 && (
        <div className="p-4 border-t border-gray-200">
          <button
            type="button"
            onClick={clearAll}
            className="w-full py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Clear all notifications
          </button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// NOTIFICATION BELL
// =============================================================================

export interface NotificationBellProps {
  onClick: () => void;
  className?: string;
}

/**
 * Notification bell button with unread count badge
 */
export function NotificationBell({ onClick, className = '' }: NotificationBellProps) {
  const { unreadCount } = useNotifications();

  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative p-2 text-gray-600 hover:text-gray-900 ${className}`}
      aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
    >
      <span className="text-xl" aria-hidden="true">
        🔔
      </span>
      {unreadCount > 0 && (
        <span
          className="absolute -top-1 -right-1 min-w-[20px] h-5 px-1 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center"
          aria-hidden="true"
        >
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </button>
  );
}

// =============================================================================
// EXPORTS
// =============================================================================

export type {
  BroadcastMessage,
  ToastMessage,
  Notification,
  TabSyncContextValue,
  SessionContextValue,
  ToastContextValue,
  NotificationContextValue,
};

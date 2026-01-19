/**
 * Security, Privacy & Compliance UI/UX Components
 * 
 * Section 19.12: Security, Privacy & Compliance UI/UX
 * Perfecting Section 1.3 RBAC and Section 9.4 PII
 * 
 * Features:
 * - Role-Based Visibility (RBAC) with permission gates
 * - Masked sensitive data with reveal toggle
 * - Privacy indicators for data sync/processing
 * - Document confidentiality labeling
 * - Audit trail/change history viewer
 */

'use client';

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
  ReactNode,
} from 'react';
import { useI18n } from '@/contexts/i18n-context';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * User permission levels
 */
export const PERMISSION = {
  READ: 'read',
  WRITE: 'write',
  DELETE: 'delete',
  ADMIN: 'admin',
  MANAGE_USERS: 'manage_users',
  VIEW_FINANCIALS: 'view_financials',
  VIEW_CONFIDENTIAL: 'view_confidential',
  EXPORT_DATA: 'export_data',
} as const;

export type Permission = (typeof PERMISSION)[keyof typeof PERMISSION];

/**
 * User roles with hierarchical permissions
 */
export const ROLE = {
  GUEST: 'guest',
  VIEWER: 'viewer',
  OPERATOR: 'operator',
  SUPERVISOR: 'supervisor',
  MANAGER: 'manager',
  ADMIN: 'admin',
  OWNER: 'owner',
} as const;

export type Role = (typeof ROLE)[keyof typeof ROLE];

/**
 * Role to permissions mapping
 */
export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [ROLE.GUEST]: [PERMISSION.READ],
  [ROLE.VIEWER]: [PERMISSION.READ],
  [ROLE.OPERATOR]: [PERMISSION.READ, PERMISSION.WRITE],
  [ROLE.SUPERVISOR]: [PERMISSION.READ, PERMISSION.WRITE, PERMISSION.VIEW_FINANCIALS],
  [ROLE.MANAGER]: [
    PERMISSION.READ,
    PERMISSION.WRITE,
    PERMISSION.DELETE,
    PERMISSION.VIEW_FINANCIALS,
    PERMISSION.EXPORT_DATA,
  ],
  [ROLE.ADMIN]: [
    PERMISSION.READ,
    PERMISSION.WRITE,
    PERMISSION.DELETE,
    PERMISSION.ADMIN,
    PERMISSION.MANAGE_USERS,
    PERMISSION.VIEW_FINANCIALS,
    PERMISSION.VIEW_CONFIDENTIAL,
    PERMISSION.EXPORT_DATA,
  ],
  [ROLE.OWNER]: [
    PERMISSION.READ,
    PERMISSION.WRITE,
    PERMISSION.DELETE,
    PERMISSION.ADMIN,
    PERMISSION.MANAGE_USERS,
    PERMISSION.VIEW_FINANCIALS,
    PERMISSION.VIEW_CONFIDENTIAL,
    PERMISSION.EXPORT_DATA,
  ],
};

/**
 * Document confidentiality levels
 */
export const CONFIDENTIALITY = {
  PUBLIC: 'public',
  INTERNAL: 'internal',
  CONFIDENTIAL: 'confidential',
  RESTRICTED: 'restricted',
} as const;

export type Confidentiality = (typeof CONFIDENTIALITY)[keyof typeof CONFIDENTIALITY];

/**
 * Sync status for privacy indicators
 */
export const SYNC_STATUS = {
  IDLE: 'idle',
  SYNCING: 'syncing',
  PROCESSING: 'processing',
  COMPLETE: 'complete',
  ERROR: 'error',
} as const;

export type SyncStatus = (typeof SYNC_STATUS)[keyof typeof SYNC_STATUS];

/**
 * Audit action types
 */
export const AUDIT_ACTION = {
  CREATE: 'create',
  UPDATE: 'update',
  DELETE: 'delete',
  VIEW: 'view',
  EXPORT: 'export',
  SHARE: 'share',
  PERMISSION_CHANGE: 'permission_change',
} as const;

export type AuditAction = (typeof AUDIT_ACTION)[keyof typeof AUDIT_ACTION];

// =============================================================================
// TYPES
// =============================================================================

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  permissions?: Permission[];
  avatar?: string;
}

export interface AuditEntry {
  id: string;
  timestamp: Date;
  action: AuditAction;
  userId: string;
  userName: string;
  entityType: string;
  entityId: string;
  description: string;
  changes?: {
    field: string;
    oldValue: string | number | boolean | null;
    newValue: string | number | boolean | null;
  }[];
  metadata?: Record<string, unknown>;
}

// =============================================================================
// RBAC CONTEXT & PROVIDER
// =============================================================================

interface RBACContextValue {
  user: User | null;
  setUser: (user: User | null) => void;
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
  hasRole: (role: Role) => boolean;
  hasMinimumRole: (role: Role) => boolean;
}

const RBACContext = createContext<RBACContextValue | null>(null);

const ROLE_HIERARCHY: Role[] = [
  ROLE.GUEST,
  ROLE.VIEWER,
  ROLE.OPERATOR,
  ROLE.SUPERVISOR,
  ROLE.MANAGER,
  ROLE.ADMIN,
  ROLE.OWNER,
];

export interface RBACProviderProps {
  children: ReactNode;
  initialUser?: User | null;
}

export function RBACProvider({ children, initialUser = null }: RBACProviderProps) {
  const [user, setUser] = useState<User | null>(initialUser);

  const getUserPermissions = useCallback((u: User | null): Permission[] => {
    if (!u) return [];
    const rolePermissions = ROLE_PERMISSIONS[u.role] || [];
    const additionalPermissions = u.permissions || [];
    return [...new Set([...rolePermissions, ...additionalPermissions])];
  }, []);

  const hasPermission = useCallback(
    (permission: Permission): boolean => {
      const permissions = getUserPermissions(user);
      return permissions.includes(permission);
    },
    [user, getUserPermissions]
  );

  const hasAnyPermission = useCallback(
    (permissions: Permission[]): boolean => {
      return permissions.some((p) => hasPermission(p));
    },
    [hasPermission]
  );

  const hasAllPermissions = useCallback(
    (permissions: Permission[]): boolean => {
      return permissions.every((p) => hasPermission(p));
    },
    [hasPermission]
  );

  const hasRole = useCallback(
    (role: Role): boolean => {
      return user?.role === role;
    },
    [user]
  );

  const hasMinimumRole = useCallback(
    (role: Role): boolean => {
      if (!user) return false;
      const userRoleIndex = ROLE_HIERARCHY.indexOf(user.role);
      const requiredRoleIndex = ROLE_HIERARCHY.indexOf(role);
      return userRoleIndex >= requiredRoleIndex;
    },
    [user]
  );

  const value = useMemo<RBACContextValue>(
    () => ({
      user,
      setUser,
      hasPermission,
      hasAnyPermission,
      hasAllPermissions,
      hasRole,
      hasMinimumRole,
    }),
    [user, hasPermission, hasAnyPermission, hasAllPermissions, hasRole, hasMinimumRole]
  );

  return <RBACContext.Provider value={value}>{children}</RBACContext.Provider>;
}

export function useRBAC(): RBACContextValue {
  const context = useContext(RBACContext);
  if (!context) {
    throw new Error('useRBAC must be used within RBACProvider');
  }
  return context;
}

// =============================================================================
// PERMISSION GATE COMPONENT
// =============================================================================

export interface PermissionGateProps {
  children: ReactNode;
  require?: Permission | Permission[];
  requireAll?: boolean;
  requireRole?: Role;
  requireMinimumRole?: Role;
  fallback?: ReactNode;
  hideOnly?: boolean;
}

/**
 * PermissionGate - Conditionally render children based on permissions
 * 
 * @example
 * <PermissionGate require={PERMISSION.VIEW_FINANCIALS}>
 *   <FinancialDashboard />
 * </PermissionGate>
 */
export function PermissionGate({
  children,
  require,
  requireAll = false,
  requireRole,
  requireMinimumRole,
  fallback = null,
  hideOnly = false,
}: PermissionGateProps) {
  const { hasPermission, hasAnyPermission, hasAllPermissions, hasRole, hasMinimumRole } = useRBAC();

  let hasAccess = true;

  // Check permissions
  if (require) {
    const permissions = Array.isArray(require) ? require : [require];
    hasAccess = requireAll ? hasAllPermissions(permissions) : hasAnyPermission(permissions);
  }

  // Check specific role
  if (hasAccess && requireRole) {
    hasAccess = hasRole(requireRole);
  }

  // Check minimum role
  if (hasAccess && requireMinimumRole) {
    hasAccess = hasMinimumRole(requireMinimumRole);
  }

  if (!hasAccess) {
    if (hideOnly) {
      return null;
    }
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// =============================================================================
// MASKED DATA COMPONENT
// =============================================================================

export interface MaskedDataProps {
  value: string | number;
  maskCharacter?: string;
  showLength?: number;
  showPrefix?: boolean;
  requirePermission?: Permission;
  className?: string;
  label?: string;
}

/**
 * MaskedData - Display sensitive data with blur/reveal toggle
 * 
 * @example
 * <MaskedData 
 *   value="$125,000.00" 
 *   requirePermission={PERMISSION.VIEW_FINANCIALS} 
 *   label="Annual Revenue"
 * />
 */
export function MaskedData({
  value,
  maskCharacter = '•',
  showLength = 0,
  showPrefix = false,
  requirePermission,
  className = '',
  label,
}: MaskedDataProps) {
  const [isRevealed, setIsRevealed] = useState(false);
  const { hasPermission } = useRBAC();

  const canReveal = !requirePermission || hasPermission(requirePermission);
  const valueStr = String(value);

  const maskedValue = useMemo(() => {
    if (showLength > 0) {
      if (showPrefix) {
        return valueStr.slice(0, showLength) + maskCharacter.repeat(valueStr.length - showLength);
      }
      return maskCharacter.repeat(valueStr.length - showLength) + valueStr.slice(-showLength);
    }
    return maskCharacter.repeat(Math.min(valueStr.length, 12));
  }, [valueStr, maskCharacter, showLength, showPrefix]);

  const displayValue = isRevealed && canReveal ? valueStr : maskedValue;

  return (
    <span
      className={`inline-flex items-center gap-2 ${className}`}
      data-testid="masked-data"
    >
      {label && (
        <span className="text-sm text-gray-500 dark:text-gray-400">{label}:</span>
      )}
      <span
        className={`font-mono ${!isRevealed || !canReveal ? 'select-none' : ''}`}
        aria-label={isRevealed && canReveal ? 'Revealed value' : 'Masked value'}
      >
        {displayValue}
      </span>
      {canReveal && (
        <button
          type="button"
          onClick={() => setIsRevealed(!isRevealed)}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          aria-label={isRevealed ? 'Hide sensitive data' : 'Reveal sensitive data'}
        >
          {isRevealed ? '👁️' : '👁️‍🗨️'}
        </button>
      )}
      {!canReveal && (
        <span
          className="text-xs text-gray-400 dark:text-gray-500"
          title="You don't have permission to view this data"
        >
          🔒
        </span>
      )}
    </span>
  );
}

// =============================================================================
// PRIVACY INDICATOR COMPONENT
// =============================================================================

export interface PrivacyIndicatorProps {
  status: SyncStatus;
  label?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const STATUS_CONFIG: Record<SyncStatus, { icon: string; color: string; labelKey: string; animate?: boolean }> = {
  [SYNC_STATUS.IDLE]: { icon: '⚪', color: 'text-gray-400', labelKey: 'common.status.idle' },
  [SYNC_STATUS.SYNCING]: { icon: '🔄', color: 'text-blue-500', labelKey: 'common.status.syncing', animate: true },
  [SYNC_STATUS.PROCESSING]: { icon: '⚙️', color: 'text-yellow-500', labelKey: 'common.status.processing', animate: true },
  [SYNC_STATUS.COMPLETE]: { icon: '✅', color: 'text-green-500', labelKey: 'common.status.complete' },
  [SYNC_STATUS.ERROR]: { icon: '❌', color: 'text-red-500', labelKey: 'common.status.error' },
};

const SIZE_CLASSES = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
};

/**
 * PrivacyIndicator - Visual cue for data sync/processing status
 * 
 * @example
 * <PrivacyIndicator status={SYNC_STATUS.SYNCING} label="Uploading to cloud" />
 */
export function PrivacyIndicator({
  status,
  label,
  showLabel = true,
  size = 'md',
  className = '',
}: PrivacyIndicatorProps) {
  const { t } = useI18n();
  const config = STATUS_CONFIG[status];

  return (
    <div
      className={`inline-flex items-center gap-1.5 ${SIZE_CLASSES[size]} ${className}`}
      role="status"
      aria-live="polite"
      data-testid="privacy-indicator"
    >
      <span className={`${config.animate ? 'animate-spin' : ''} ${config.color}`}>
        {config.icon}
      </span>
      {showLabel && (
        <span className={config.color}>
          {label || t(config.labelKey)}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// CONFIDENTIALITY LABEL COMPONENT
// =============================================================================

export interface ConfidentialityLabelProps {
  level: Confidentiality;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

const CONFIDENTIALITY_CONFIG: Record<Confidentiality, { icon: string; color: string; bg: string; label: string }> = {
  [CONFIDENTIALITY.PUBLIC]: {
    icon: '🌐',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 dark:bg-green-900/30',
    label: 'Public',
  },
  [CONFIDENTIALITY.INTERNAL]: {
    icon: '🏢',
    color: 'text-blue-700 dark:text-blue-300',
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    label: 'Internal',
  },
  [CONFIDENTIALITY.CONFIDENTIAL]: {
    icon: '🔐',
    color: 'text-orange-700 dark:text-orange-300',
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    label: 'Confidential',
  },
  [CONFIDENTIALITY.RESTRICTED]: {
    icon: '⛔',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 dark:bg-red-900/30',
    label: 'Restricted',
  },
};

const LABEL_SIZE_CLASSES = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-1',
  lg: 'text-base px-2.5 py-1.5',
};

/**
 * ConfidentialityLabel - Badge indicating document confidentiality level
 * 
 * @example
 * <ConfidentialityLabel level={CONFIDENTIALITY.CONFIDENTIAL} />
 */
export function ConfidentialityLabel({
  level,
  size = 'md',
  showIcon = true,
  className = '',
}: ConfidentialityLabelProps) {
  const config = CONFIDENTIALITY_CONFIG[level];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded font-medium ${config.color} ${config.bg} ${LABEL_SIZE_CLASSES[size]} ${className}`}
      data-testid="confidentiality-label"
      aria-label={`Confidentiality level: ${config.label}`}
    >
      {showIcon && <span>{config.icon}</span>}
      <span>{config.label}</span>
    </span>
  );
}

// =============================================================================
// SENSEI PROCESSING INDICATOR
// =============================================================================

export interface SenseiProcessingProps {
  isProcessing: boolean;
  modelName?: string;
  progress?: number;
  className?: string;
}

/**
 * SenseiProcessing - Indicator when local AI models are processing data
 * 
 * @example
 * <SenseiProcessing isProcessing={true} modelName="Quote Optimizer" progress={45} />
 */
export function SenseiProcessing({
  isProcessing,
  modelName = 'Sensei',
  progress,
  className = '',
}: SenseiProcessingProps) {
  if (!isProcessing) return null;

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 ${className}`}
      role="status"
      aria-live="polite"
      data-testid="sensei-processing"
    >
      <span className="animate-pulse">🧠</span>
      <div className="flex flex-col">
        <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
          {modelName} is analyzing...
        </span>
        {progress !== undefined && (
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 bg-purple-200 dark:bg-purple-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
            <span className="text-xs text-purple-600 dark:text-purple-400">{progress}%</span>
          </div>
        )}
      </div>
      <span className="text-xs text-purple-500 dark:text-purple-400 ml-2">
        (local processing - data stays on device)
      </span>
    </div>
  );
}

// =============================================================================
// AUDIT TRAIL / CHANGE HISTORY COMPONENTS
// =============================================================================

export interface AuditTrailProps {
  entries: AuditEntry[];
  title?: string;
  maxVisible?: number;
  showFilters?: boolean;
  className?: string;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

const ACTION_CONFIG: Record<AuditAction, { icon: string; color: string; label: string }> = {
  [AUDIT_ACTION.CREATE]: { icon: '➕', color: 'text-green-600', label: 'Created' },
  [AUDIT_ACTION.UPDATE]: { icon: '✏️', color: 'text-blue-600', label: 'Updated' },
  [AUDIT_ACTION.DELETE]: { icon: '🗑️', color: 'text-red-600', label: 'Deleted' },
  [AUDIT_ACTION.VIEW]: { icon: '👁️', color: 'text-gray-600', label: 'Viewed' },
  [AUDIT_ACTION.EXPORT]: { icon: '📤', color: 'text-purple-600', label: 'Exported' },
  [AUDIT_ACTION.SHARE]: { icon: '🔗', color: 'text-indigo-600', label: 'Shared' },
  [AUDIT_ACTION.PERMISSION_CHANGE]: { icon: '🔐', color: 'text-orange-600', label: 'Permission Changed' },
};

/**
 * AuditTrail - Display change history for an entity
 * 
 * @example
 * <AuditTrail entries={auditEntries} title="Quote History" />
 */
export function AuditTrail({
  entries,
  title = 'Change History',
  maxVisible = 10,
  showFilters = true,
  className = '',
  onLoadMore,
  hasMore = false,
}: AuditTrailProps) {
  const [filter, setFilter] = useState<AuditAction | 'all'>('all');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const filteredEntries = useMemo(() => {
    if (filter === 'all') return entries;
    return entries.filter((e) => e.action === filter);
  }, [entries, filter]);

  const visibleEntries = filteredEntries.slice(0, maxVisible);

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  };

  const formatRelativeTime = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(date);
  };

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`} data-testid="audit-trail">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
        {showFilters && (
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as AuditAction | 'all')}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            aria-label="Filter by action type"
          >
            <option value="all">All Actions</option>
            {Object.entries(AUDIT_ACTION).map(([key, value]) => (
              <option key={key} value={value}>
                {ACTION_CONFIG[value].label}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Entries */}
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {visibleEntries.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
            No history entries found
          </div>
        ) : (
          visibleEntries.map((entry) => {
            const config = ACTION_CONFIG[entry.action];
            const isExpanded = expandedIds.has(entry.id);

            return (
              <div
                key={entry.id}
                className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                data-testid="audit-entry"
              >
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 ${config.color}`}>{config.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {entry.userName}
                      </span>
                      <span className={`text-sm ${config.color}`}>{config.label.toLowerCase()}</span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {entry.entityType}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                      {entry.description}
                    </p>
                    
                    {/* Changes detail */}
                    {entry.changes && entry.changes.length > 0 && (
                      <div className="mt-2">
                        <button
                          onClick={() => toggleExpanded(entry.id)}
                          className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {isExpanded ? 'Hide details' : `Show ${entry.changes.length} change(s)`}
                        </button>
                        {isExpanded && (
                          <div className="mt-2 space-y-1 bg-gray-50 dark:bg-gray-800 rounded p-2">
                            {entry.changes.map((change) => (
                              <div key={change.field} className="text-xs">
                                <span className="font-medium text-gray-700 dark:text-gray-300">
                                  {change.field}:
                                </span>{' '}
                                <span className="text-red-600 dark:text-red-400 line-through">
                                  {String(change.oldValue ?? 'null')}
                                </span>{' '}
                                →{' '}
                                <span className="text-green-600 dark:text-green-400">
                                  {String(change.newValue ?? 'null')}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <time
                    className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap"
                    title={formatDate(entry.timestamp)}
                    dateTime={entry.timestamp.toISOString()}
                  >
                    {formatRelativeTime(entry.timestamp)}
                  </time>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Load More */}
      {hasMore && onLoadMore && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onLoadMore}
            className="w-full text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Load more history
          </button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// CHANGE HISTORY MODAL
// =============================================================================

export interface ChangeHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  entityType: string;
  entityId: string;
  entityName?: string;
  entries: AuditEntry[];
  onLoadMore?: () => void;
  hasMore?: boolean;
}

/**
 * ChangeHistoryModal - Modal for viewing full entity change history
 */
export function ChangeHistoryModal({
  isOpen,
  onClose,
  entityType,
  entityId,
  entityName,
  entries,
  onLoadMore,
  hasMore,
}: ChangeHistoryModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="change-history-title"
    >
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden m-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 id="change-history-title" className="text-xl font-semibold text-gray-900 dark:text-white">
              Change History
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {entityType}: {entityName || entityId}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[60vh]">
          <AuditTrail
            entries={entries}
            title=""
            showFilters={false}
            onLoadMore={onLoadMore}
            hasMore={hasMore}
            className="border-0 rounded-none"
          />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// DATA CLASSIFICATION BANNER
// =============================================================================

export interface DataClassificationBannerProps {
  level: Confidentiality;
  message?: string;
  dismissible?: boolean;
  className?: string;
}

/**
 * DataClassificationBanner - Top-of-page banner showing data classification
 */
export function DataClassificationBanner({
  level,
  message,
  dismissible = false,
  className = '',
}: DataClassificationBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);
  const config = CONFIDENTIALITY_CONFIG[level];

  if (isDismissed) return null;

  const defaultMessages: Record<Confidentiality, string> = {
    [CONFIDENTIALITY.PUBLIC]: 'This information is publicly accessible.',
    [CONFIDENTIALITY.INTERNAL]: 'This information is for internal use only.',
    [CONFIDENTIALITY.CONFIDENTIAL]: 'This information is confidential. Handle with care.',
    [CONFIDENTIALITY.RESTRICTED]: 'This information is restricted. Unauthorized access prohibited.',
  };

  return (
    <div
      className={`flex items-center justify-between px-4 py-2 ${config.bg} ${config.color} ${className}`}
      role="banner"
      data-testid="classification-banner"
    >
      <div className="flex items-center gap-2">
        <span>{config.icon}</span>
        <span className="font-medium">{config.label}:</span>
        <span>{message || defaultMessages[level]}</span>
      </div>
      {dismissible && (
        <button
          onClick={() => setIsDismissed(true)}
          className="p-1 hover:opacity-70"
          aria-label="Dismiss banner"
        >
          ✕
        </button>
      )}
    </div>
  );
}

// =============================================================================
// SECURE ACTION BUTTON
// =============================================================================

export interface SecureActionButtonProps {
  children: ReactNode;
  onClick: () => void;
  requirePermission?: Permission;
  requireConfirmation?: boolean;
  confirmationMessage?: string;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  className?: string;
}

/**
 * SecureActionButton - Button that can require permission and/or confirmation
 */
export function SecureActionButton({
  children,
  onClick,
  requirePermission,
  requireConfirmation = false,
  confirmationMessage = 'Are you sure you want to perform this action?',
  variant = 'primary',
  disabled = false,
  className = '',
}: SecureActionButtonProps) {
  const { hasPermission } = useRBAC();
  const [showConfirm, setShowConfirm] = useState(false);

  const canPerform = !requirePermission || hasPermission(requirePermission);
  const isDisabled = disabled || !canPerform;

  const variantClasses = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  };

  const handleClick = () => {
    if (requireConfirmation) {
      setShowConfirm(true);
    } else {
      onClick();
    }
  };

  const handleConfirm = () => {
    setShowConfirm(false);
    onClick();
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={isDisabled}
        className={`px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`}
        title={!canPerform ? 'You do not have permission to perform this action' : undefined}
      >
        {children}
      </button>

      {/* Confirmation Dialog */}
      {showConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl p-6 max-w-md m-4">
            <h3 id="confirm-title" className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Confirm Action
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">{confirmationMessage}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className={`px-4 py-2 rounded-lg font-medium ${variantClasses[variant]}`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// =============================================================================
// SESSION SECURITY INDICATOR
// =============================================================================

export interface SessionSecurityProps {
  isSecure: boolean;
  sessionExpiry?: Date;
  onExtendSession?: () => void;
  className?: string;
}

/**
 * SessionSecurity - Show session security status and expiry
 */
export function SessionSecurity({
  isSecure,
  sessionExpiry,
  onExtendSession,
  className = '',
}: SessionSecurityProps) {
  const [timeRemaining, setTimeRemaining] = useState<string>('');

  useEffect(() => {
    if (!sessionExpiry) return;

    const updateRemaining = () => {
      const now = new Date();
      const diffMs = sessionExpiry.getTime() - now.getTime();

      if (diffMs <= 0) {
        setTimeRemaining('Expired');
        return;
      }

      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);

      if (diffMins < 60) {
        setTimeRemaining(`${diffMins}m remaining`);
      } else {
        setTimeRemaining(`${diffHours}h remaining`);
      }
    };

    updateRemaining();
    const interval = setInterval(updateRemaining, 60000);

    return () => clearInterval(interval);
  }, [sessionExpiry]);

  return (
    <div
      className={`inline-flex items-center gap-2 text-sm ${className}`}
      data-testid="session-security"
    >
      <span className={isSecure ? 'text-green-600' : 'text-yellow-600'}>
        {isSecure ? '🔒' : '⚠️'}
      </span>
      <span className="text-gray-600 dark:text-gray-400">
        {isSecure ? 'Secure session' : 'Insecure connection'}
      </span>
      {sessionExpiry && (
        <>
          <span className="text-gray-300 dark:text-gray-600">•</span>
          <span className="text-gray-500 dark:text-gray-400">{timeRemaining}</span>
          {onExtendSession && timeRemaining !== 'Expired' && (
            <button
              onClick={onExtendSession}
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Extend
            </button>
          )}
        </>
      )}
    </div>
  );
}

// =============================================================================
// EXPORTS
// =============================================================================

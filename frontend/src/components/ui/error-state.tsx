/**
 * Error state components for replacing hardcoded fallback data.
 *
 * Instead of showing fake/hardcoded data when API calls fail,
 * display clear error states with retry actions.
 *
 * Checklist item: #444
 */

"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, RefreshCw, WifiOff, ServerCrash, FileWarning } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/contexts/i18n-context";

// ─── Types ───────────────────────────────────────────────────────

export type ErrorVariant = "network" | "server" | "empty" | "permission" | "not-found" | "generic";

interface ErrorStateProps {
  variant?: ErrorVariant;
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
  compact?: boolean;
  children?: React.ReactNode;
}

interface EmptyStateProps {
  icon?: React.ReactNode;
  title?: string;
  message?: string;
  action?: React.ReactNode;
  className?: string;
  compact?: boolean;
}

// ─── Error State ─────────────────────────────────────────────────

const VARIANT_CONFIG: Record<
  ErrorVariant,
  { icon: React.ReactNode; titleKey: string; messageKey: string }
> = {
  network: {
    icon: <WifiOff className="h-10 w-10 text-muted-foreground" />,
    titleKey: "components.errorState.connectionError",
    messageKey: "components.errorState.connectionErrorDesc",
  },
  server: {
    icon: <ServerCrash className="h-10 w-10 text-destructive/60" />,
    titleKey: "components.errorState.serverError",
    messageKey: "components.errorState.serverErrorDesc",
  },
  empty: {
    icon: <FileWarning className="h-10 w-10 text-muted-foreground" />,
    titleKey: "components.errorState.noData",
    messageKey: "components.errorState.noDataDesc",
  },
  permission: {
    icon: <AlertCircle className="h-10 w-10 text-amber-500/60" />,
    titleKey: "components.errorState.accessDenied",
    messageKey: "components.errorState.accessDeniedDesc",
  },
  "not-found": {
    icon: <FileWarning className="h-10 w-10 text-muted-foreground" />,
    titleKey: "components.errorState.notFound",
    messageKey: "components.errorState.notFoundDesc",
  },
  generic: {
    icon: <AlertCircle className="h-10 w-10 text-destructive/60" />,
    titleKey: "components.errorState.error",
    messageKey: "components.errorState.errorDesc",
  },
};

/**
 * Generic error state component. Use instead of hardcoded fallback data.
 *
 * @example
 * ```tsx
 * {error ? (
 *   <ErrorState
 *     variant="server"
 *     onRetry={() => fetchData()}
 *   />
 * ) : (
 *   <DataTable data={data} />
 * )}
 * ```
 */
export function ErrorState({
  variant = "generic",
  title,
  message,
  onRetry,
  retryLabel,
  className,
  compact = false,
  children,
}: ErrorStateProps) {
  const { t } = useI18n();
  const config = VARIANT_CONFIG[variant];
  const resolvedTitle = title || t(config.titleKey);
  const resolvedMessage = message || t(config.messageKey);
  const resolvedRetryLabel = retryLabel || t('components.errorState.tryAgain');

  if (compact) {
    return (
      <div
        className={cn(
          "flex items-center gap-3 p-4 rounded-lg border border-destructive/20 bg-destructive/5",
          className
        )}
        role="alert"
      >
        <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
        <p className="text-sm text-muted-foreground">
          {resolvedMessage}
        </p>
        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRetry}
            className="ml-auto shrink-0"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            {resolvedRetryLabel}
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-12 text-center",
        className
      )}
      role="alert"
    >
      {config.icon}
      <h3 className="mt-4 text-lg font-semibold">{resolvedTitle}</h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-md">
        {resolvedMessage}
      </p>
      {onRetry && (
        <Button
          variant="outline"
          onClick={onRetry}
          className="mt-4"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          {resolvedRetryLabel}
        </Button>
      )}
      {children}
    </div>
  );
}

/**
 * Empty state component for when data loads successfully but is empty.
 *
 * @example
 * ```tsx
 * {data.length === 0 ? (
 *   <EmptyState
 *     title="No inspections"
 *     message="Create your first inspection to get started."
 *     action={<Button onClick={openCreateDialog}>Create Inspection</Button>}
 *   />
 * ) : (
 *   <InspectionTable data={data} />
 * )}
 * ```
 */
export function EmptyState({
  icon,
  title,
  message,
  action,
  className,
  compact = false,
}: EmptyStateProps) {
  const { t } = useI18n();
  const resolvedTitle = title || t('components.errorState.noData');
  const resolvedMessage = message || t('components.errorState.noDataDesc');
  if (compact) {
    return (
      <div
        className={cn(
          "flex items-center gap-3 p-4 text-muted-foreground",
          className
        )}
      >
        {icon || <FileWarning className="h-5 w-5 shrink-0" />}
        <p className="text-sm">{resolvedMessage}</p>
        {action}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-12 text-center",
        className
      )}
    >
      {icon || <FileWarning className="h-10 w-10 text-muted-foreground" />}
      <h3 className="mt-4 text-lg font-semibold">{resolvedTitle}</h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-md">{resolvedMessage}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/**
 * Loading state component for consistent loading UX.
 */
export function LoadingState({
  message = "Loading…",
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-center p-12 text-muted-foreground",
        className
      )}
      role="status"
      aria-label={message}
    >
      <svg
        className="animate-spin h-5 w-5 mr-2"
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
          className="opacity-25"
        />
        <path
          fill="currentColor"
          d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
          className="opacity-75"
        />
      </svg>
      {message}
    </div>
  );
}

export default ErrorState;

'use client';

import * as React from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export type ConfirmationVariant = 'default' | 'danger' | 'warning' | 'info';

export interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmationVariant;
  loading?: boolean;
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
}

// =============================================================================
// Confirmation Dialog Component
// =============================================================================

const variantStyles: Record<ConfirmationVariant, string> = {
  default: 'bg-primary text-primary-foreground hover:bg-primary/90',
  danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
  warning: 'bg-yellow-600 text-white hover:bg-yellow-700',
  info: 'bg-blue-600 text-white hover:bg-blue-700',
};

const variantIcons: Record<ConfirmationVariant, React.ReactNode> = {
  default: null,
  danger: (
    <svg
      className="h-6 w-6 text-red-600"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  ),
  warning: (
    <svg
      className="h-6 w-6 text-yellow-600"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  ),
  info: (
    <svg
      className="h-6 w-6 text-blue-600"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  ),
};

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  const [isLoading, setIsLoading] = React.useState(false);

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    onCancel?.();
    onOpenChange(false);
  };

  const isActionLoading = loading || isLoading;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-start gap-4">
            {variantIcons[variant] && (
              <div className="flex-shrink-0">{variantIcons[variant]}</div>
            )}
            <div>
              <AlertDialogTitle>{title}</AlertDialogTitle>
              <AlertDialogDescription className="mt-2">
                {description}
              </AlertDialogDescription>
            </div>
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel} disabled={isActionLoading}>
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isActionLoading}
            className={cn(variantStyles[variant])}
          >
            {isActionLoading ? (
              <>
                <svg
                  className="mr-2 h-4 w-4 animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Processing...
              </>
            ) : (
              confirmLabel
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// =============================================================================
// Hook for programmatic confirmation dialogs
// =============================================================================

interface ConfirmationState {
  open: boolean;
  title: string;
  description: string;
  variant: ConfirmationVariant;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
}

const defaultState: ConfirmationState = {
  open: false,
  title: '',
  description: '',
  variant: 'default',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  onConfirm: () => {},
};

export function useConfirmation() {
  const [state, setState] = React.useState<ConfirmationState>(defaultState);

  const confirm = React.useCallback(
    (
      options: Omit<ConfirmationState, 'open'>
    ): Promise<boolean> => {
      return new Promise((resolve) => {
        setState({
          ...options,
          open: true,
          onConfirm: async () => {
            await options.onConfirm();
            resolve(true);
          },
          onCancel: () => {
            options.onCancel?.();
            resolve(false);
          },
        });
      });
    },
    []
  );

  const close = React.useCallback(() => {
    setState((prev) => ({ ...prev, open: false }));
  }, []);

  const dialog = React.useMemo(
    () => (
      <ConfirmationDialog
        open={state.open}
        onOpenChange={(open) => {
          if (!open) {
            state.onCancel?.();
          }
          setState((prev) => ({ ...prev, open }));
        }}
        title={state.title}
        description={state.description}
        variant={state.variant}
        confirmLabel={state.confirmLabel}
        cancelLabel={state.cancelLabel}
        onConfirm={state.onConfirm}
        onCancel={state.onCancel}
      />
    ),
    [state]
  );

  return {
    confirm,
    close,
    dialog,
  };
}

// =============================================================================
// Shorthand confirmation functions
// =============================================================================

export function useDeleteConfirmation(itemName: string = 'item') {
  const { confirm, dialog } = useConfirmation();

  const confirmDelete = React.useCallback(
    (onConfirm: () => void | Promise<void>) => {
      return confirm({
        title: `Delete ${itemName}?`,
        description: `This action cannot be undone. The ${itemName.toLowerCase()} will be permanently deleted.`,
        variant: 'danger',
        confirmLabel: 'Delete',
        cancelLabel: 'Cancel',
        onConfirm,
      });
    },
    [confirm, itemName]
  );

  return { confirmDelete, dialog };
}

export function useBulkDeleteConfirmation() {
  const { confirm, dialog } = useConfirmation();

  const confirmBulkDelete = React.useCallback(
    (count: number, itemType: string, onConfirm: () => void | Promise<void>) => {
      return confirm({
        title: `Delete ${count} ${itemType}${count > 1 ? 's' : ''}?`,
        description: `This action cannot be undone. ${count} ${itemType.toLowerCase()}${count > 1 ? 's' : ''} will be permanently deleted.`,
        variant: 'danger',
        confirmLabel: `Delete ${count}`,
        cancelLabel: 'Cancel',
        onConfirm,
      });
    },
    [confirm]
  );

  return { confirmBulkDelete, dialog };
}

export function useDiscardChangesConfirmation() {
  const { confirm, dialog } = useConfirmation();

  const confirmDiscard = React.useCallback(
    (onConfirm: () => void | Promise<void>) => {
      return confirm({
        title: 'Discard changes?',
        description: 'You have unsaved changes. Are you sure you want to discard them?',
        variant: 'warning',
        confirmLabel: 'Discard',
        cancelLabel: 'Keep editing',
        onConfirm,
      });
    },
    [confirm]
  );

  return { confirmDiscard, dialog };
}

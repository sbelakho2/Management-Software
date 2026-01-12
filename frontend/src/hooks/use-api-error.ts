'use client';

import { useCallback } from 'react';
import { useToast } from './use-toast';
import type { ApiError } from '@/api/client';

/**
 * Error codes that should show specific messages
 */
const ERROR_MESSAGES: Record<string, string> = {
  NETWORK_ERROR: 'Unable to connect to the server. Please check your connection.',
  UNAUTHORIZED: 'Your session has expired. Please log in again.',
  FORBIDDEN: 'You do not have permission to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  CONFLICT: 'This resource already exists or conflicts with another.',
  RATE_LIMITED: 'Too many requests. Please wait a moment and try again.',
  SERVER_ERROR: 'An unexpected server error occurred. Please try again later.',
  TIMEOUT: 'The request timed out. Please try again.',
};

/**
 * Get a user-friendly error message
 */
function getErrorMessage(error: unknown): string {
  if (!error) {
    return 'An unexpected error occurred';
  }

  // Handle ApiError type
  if (typeof error === 'object' && 'message' in error) {
    const apiError = error as ApiError;
    
    // Check for specific error code
    if (apiError.code && ERROR_MESSAGES[apiError.code]) {
      return ERROR_MESSAGES[apiError.code];
    }
    
    // Use the error message if available
    if (apiError.message) {
      return apiError.message;
    }
  }

  // Handle Error instances
  if (error instanceof Error) {
    if (error.message.includes('fetch')) {
      return ERROR_MESSAGES.NETWORK_ERROR;
    }
    return error.message;
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }

  return 'An unexpected error occurred';
}

/**
 * Get the appropriate toast variant for an error
 */
function getErrorVariant(error: unknown): 'destructive' | 'default' {
  if (typeof error === 'object' && error && 'code' in error) {
    const code = (error as ApiError).code;
    // Less severe errors can use default variant
    if (code === 'VALIDATION_ERROR' || code === 'CONFLICT') {
      return 'default';
    }
  }
  return 'destructive';
}

export interface UseApiErrorOptions {
  /** Custom title for error toasts */
  title?: string;
  /** Whether to show toast on error (default: true) */
  showToast?: boolean;
  /** Custom handler after showing toast */
  onError?: (error: unknown) => void;
}

/**
 * Hook for handling API errors with toast notifications
 * 
 * @example
 * ```tsx
 * const { handleError } = useApiError();
 * 
 * try {
 *   await mutation.mutateAsync(data);
 * } catch (error) {
 *   handleError(error, { title: 'Failed to save' });
 * }
 * ```
 */
export function useApiError(defaultOptions?: UseApiErrorOptions) {
  const { toast } = useToast();

  const handleError = useCallback(
    (error: unknown, options?: UseApiErrorOptions) => {
      const mergedOptions = { ...defaultOptions, ...options };
      const { title = 'Error', showToast = true, onError } = mergedOptions;

      if (showToast) {
        toast({
          title,
          description: getErrorMessage(error),
          variant: getErrorVariant(error),
        });
      }

      onError?.(error);
    },
    [toast, defaultOptions]
  );

  return { handleError, getErrorMessage };
}

/**
 * Create a React Query error handler that shows toasts
 * 
 * @example
 * ```tsx
 * const { toast } = useToast();
 * 
 * const mutation = useMutation({
 *   mutationFn: createCustomer,
 *   onError: createQueryErrorHandler(toast, 'Failed to create customer'),
 * });
 * ```
 */
export function createQueryErrorHandler(
  toast: ReturnType<typeof useToast>['toast'],
  title = 'Error'
) {
  return (error: unknown) => {
    toast({
      title,
      description: getErrorMessage(error),
      variant: getErrorVariant(error),
    });
  };
}

/**
 * Higher-order function for wrapping async functions with error handling
 * 
 * @example
 * ```tsx
 * const { handleError } = useApiError();
 * 
 * const safeSubmit = withErrorHandling(
 *   async (data: FormData) => {
 *     await api.post('/submit', data);
 *   },
 *   handleError
 * );
 * ```
 */
export function withErrorHandling<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  errorHandler: (error: unknown) => void
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args);
    } catch (error) {
      errorHandler(error);
      throw error;
    }
  }) as T;
}

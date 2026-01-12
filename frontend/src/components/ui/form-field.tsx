'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Input, type InputProps } from './input';
import { Textarea, type TextareaProps } from './textarea';
import { Label } from './label';
import { AlertCircle, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import type { ValidationSeverity } from '@/lib/validation';

// =============================================================================
// Types
// =============================================================================

interface FormFieldBaseProps {
  /** Field name (used for IDs and aria attributes) */
  name: string;
  /** Label text */
  label?: string;
  /** Helper text shown below the field */
  hint?: string;
  /** Error message */
  error?: string;
  /** Warning message */
  warning?: string;
  /** Success message (e.g., "Username available") */
  success?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Additional class for the wrapper */
  className?: string;
  /** Whether to hide the label visually (still accessible) */
  hideLabel?: boolean;
}

interface FormFieldInputProps extends FormFieldBaseProps, Omit<InputProps, 'name' | 'error'> {
  type?: 'text' | 'email' | 'password' | 'tel' | 'url' | 'number' | 'date' | 'time' | 'datetime-local' | 'search';
}

interface FormFieldTextareaProps extends FormFieldBaseProps, Omit<TextareaProps, 'name' | 'error'> {
  type: 'textarea';
}

export type FormFieldProps = FormFieldInputProps | FormFieldTextareaProps;

// =============================================================================
// Validation Message Component
// =============================================================================

interface ValidationMessageProps {
  message: string;
  severity: ValidationSeverity;
  id?: string;
}

function ValidationMessage({ message, severity, id }: ValidationMessageProps) {
  const icons = {
    error: <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />,
    warning: <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />,
    info: <Info className="h-3.5 w-3.5" aria-hidden="true" />,
    success: <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />,
  };

  const colors = {
    error: 'text-destructive',
    warning: 'text-amber-600 dark:text-amber-500',
    info: 'text-blue-600 dark:text-blue-400',
    success: 'text-emerald-600 dark:text-emerald-500',
  };

  return (
    <div
      id={id}
      className={cn('flex items-center gap-1.5 text-xs mt-1.5', colors[severity])}
      role={severity === 'error' ? 'alert' : undefined}
    >
      {icons[severity]}
      <span>{message}</span>
    </div>
  );
}

// =============================================================================
// FormField Component
// =============================================================================

/**
 * FormField - Accessible form field with integrated validation
 * 
 * @example
 * ```tsx
 * <FormField
 *   name="email"
 *   label="Email Address"
 *   type="email"
 *   placeholder="name@company.com"
 *   error={errors.email}
 *   required
 * />
 * 
 * <FormField
 *   name="description"
 *   label="Description"
 *   type="textarea"
 *   rows={4}
 *   hint="Describe the issue in detail"
 * />
 * ```
 */
export const FormField = React.forwardRef<
  HTMLInputElement | HTMLTextAreaElement,
  FormFieldProps
>(function FormField(props, ref) {
  const {
    name,
    label,
    hint,
    error,
    warning,
    success,
    required,
    disabled,
    className,
    hideLabel,
    type = 'text',
    ...inputProps
  } = props;

  // Generate IDs for accessibility
  const inputId = `field-${name}`;
  const hintId = hint ? `hint-${name}` : undefined;
  const errorId = error ? `error-${name}` : undefined;
  const warningId = warning ? `warning-${name}` : undefined;
  const successId = success ? `success-${name}` : undefined;

  // Build aria-describedby
  const describedBy = [hintId, errorId, warningId, successId]
    .filter(Boolean)
    .join(' ') || undefined;

  // Determine if field has error state
  const hasError = Boolean(error);
  const hasWarning = Boolean(warning) && !hasError;
  const hasSuccess = Boolean(success) && !hasError && !hasWarning;

  return (
    <div className={cn('space-y-1.5', className)}>
      {/* Label */}
      {label && (
        <Label
          htmlFor={inputId}
          className={cn(
            hideLabel && 'sr-only',
            hasError && 'text-destructive'
          )}
        >
          {label}
          {required && <span className="text-destructive ml-0.5" aria-hidden="true">*</span>}
          {required && <span className="sr-only">(required)</span>}
        </Label>
      )}

      {/* Input or Textarea */}
      {type === 'textarea' ? (
        <Textarea
          ref={ref as React.Ref<HTMLTextAreaElement>}
          id={inputId}
          name={name}
          disabled={disabled}
          required={required}
          error={hasError}
          errorId={errorId}
          aria-describedby={describedBy}
          {...(inputProps as Omit<TextareaProps, 'name' | 'error'>)}
        />
      ) : (
        <Input
          ref={ref as React.Ref<HTMLInputElement>}
          id={inputId}
          name={name}
          type={type}
          disabled={disabled}
          required={required}
          error={hasError}
          errorId={errorId}
          aria-describedby={describedBy}
          {...(inputProps as Omit<InputProps, 'name' | 'error' | 'type'>)}
        />
      )}

      {/* Hint text */}
      {hint && !error && !warning && !success && (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}

      {/* Validation messages - show only one at a time, in priority order */}
      {error && (
        <ValidationMessage id={errorId} message={error} severity="error" />
      )}
      {warning && !error && (
        <ValidationMessage id={warningId} message={warning} severity="warning" />
      )}
      {success && !error && !warning && (
        <ValidationMessage id={successId} message={success} severity="success" />
      )}
    </div>
  );
});

// =============================================================================
// FormFieldGroup - For grouping related fields
// =============================================================================

interface FormFieldGroupProps {
  /** Legend text for the fieldset */
  legend: string;
  /** Whether to hide the legend visually */
  hideLegend?: boolean;
  /** Child form fields */
  children: React.ReactNode;
  /** Additional class for the fieldset */
  className?: string;
  /** Error for the group (e.g., "At least one phone number required") */
  error?: string;
}

export function FormFieldGroup({
  legend,
  hideLegend,
  children,
  className,
  error,
}: FormFieldGroupProps) {
  const errorId = error ? `group-error-${legend.toLowerCase().replace(/\s+/g, '-')}` : undefined;

  return (
    <fieldset
      className={cn('space-y-4', className)}
      aria-describedby={errorId}
      aria-invalid={Boolean(error)}
    >
      <legend className={cn('text-sm font-medium', hideLegend && 'sr-only')}>
        {legend}
      </legend>
      {children}
      {error && (
        <ValidationMessage id={errorId} message={error} severity="error" />
      )}
    </fieldset>
  );
}

// =============================================================================
// FormActions - For form submit/cancel buttons
// =============================================================================

interface FormActionsProps {
  children: React.ReactNode;
  className?: string;
  /** Align buttons to start, end, or space between */
  align?: 'start' | 'end' | 'between' | 'center';
}

export function FormActions({
  children,
  className,
  align = 'end',
}: FormActionsProps) {
  const alignClass = {
    start: 'justify-start',
    end: 'justify-end',
    between: 'justify-between',
    center: 'justify-center',
  }[align];

  return (
    <div className={cn('flex items-center gap-3 pt-4', alignClass, className)}>
      {children}
    </div>
  );
}

export default FormField;

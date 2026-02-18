/**
 * Inline Validation Components
 * 
 * React components for displaying inline validation feedback.
 */
'use client';

import React, { forwardRef, useId, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  type ValidationResult,
  type ValidationSeverity,
  type FieldSchema,
  type GateValidationResult,
  getSeverityColorClass,
  getSeverityBackgroundClass,
  createRulesFromSchema,
} from '@/lib/validation';
import { useFormValidationStore, useField } from '@/stores/form-validation-store';

// =============================================================================
// Validation Message Component
// =============================================================================

export interface ValidationMessageProps {
  message: string;
  severity: ValidationSeverity;
  className?: string;
  showIcon?: boolean;
}

export function ValidationMessage({
  message,
  severity,
  className,
  showIcon = true,
}: ValidationMessageProps) {
  const colorClass = getSeverityColorClass(severity);
  
  const icon = {
    error: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    info: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    success: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };
  
  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        'flex items-start gap-1.5 text-sm mt-1',
        colorClass,
        className
      )}
    >
      {showIcon && (
        <span className="flex-shrink-0 mt-0.5">{icon[severity]}</span>
      )}
      <span>{message}</span>
    </div>
  );
}

// =============================================================================
// Validation Messages List Component
// =============================================================================

export interface ValidationMessagesProps {
  results: ValidationResult[];
  className?: string;
  showIcon?: boolean;
  maxMessages?: number;
}

export function ValidationMessages({
  results,
  className,
  showIcon = true,
  maxMessages = 3,
}: ValidationMessagesProps) {
  const visibleResults = results
    .filter(r => r.message)
    .slice(0, maxMessages);
  
  if (visibleResults.length === 0) {
    return null;
  }
  
  return (
    <div className={cn('space-y-1', className)}>
      {visibleResults.map((result, index) => (
        <ValidationMessage
          key={`${result.code ?? index}-${result.message}`}
          message={result.message!}
          severity={result.severity}
          showIcon={showIcon}
        />
      ))}
      {results.length > maxMessages && (
        <p className="text-sm text-muted-foreground">
          And {results.length - maxMessages} more...
        </p>
      )}
    </div>
  );
}

// =============================================================================
// Field Wrapper Component
// =============================================================================

export interface FieldWrapperProps {
  formId: string;
  name: string;
  inputId?: string;
  label?: string;
  helperText?: string;
  required?: boolean;
  showValidating?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function FieldWrapper({
  formId,
  name,
  inputId,
  label,
  helperText,
  required,
  showValidating = true,
  children,
  className,
}: FieldWrapperProps) {
  const generatedId = useId();
  const id = inputId ?? `${generatedId}-${name}`;
  const { touched, errors, warnings, status, isValid } = useField(formId, name);
  
  const showErrors = touched && errors.length > 0;
  const showWarnings = touched && warnings.length > 0 && !showErrors;
  const showHelper = helperText && !showErrors && !showWarnings;
  const isValidating = status === 'validating';
  
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-foreground"
        >
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
          {showValidating && isValidating && (
            <span className="ml-2 text-muted-foreground text-xs">Validating...</span>
          )}
        </label>
      )}
      
      <div className="relative">
        {children}
        
        {/* Validation status indicator */}
        {touched && !isValidating && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
            {isValid && errors.length === 0 && (
              <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
            {!isValid && errors.length > 0 && (
              <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </div>
        )}
      </div>
      
      {showErrors && <ValidationMessages results={errors} />}
      {showWarnings && <ValidationMessages results={warnings} />}
      {showHelper && (
        <p className="text-sm text-muted-foreground">{helperText}</p>
      )}
    </div>
  );
}

// =============================================================================
// Validated Input Component
// =============================================================================

export interface ValidatedInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'name'> {
  formId: string;
  name: string;
  label?: string;
  helperText?: string;
  wrapperClassName?: string;
}

export const ValidatedInput = forwardRef<HTMLInputElement, ValidatedInputProps>(
  function ValidatedInput(
    { formId, name, label, helperText, className, wrapperClassName, required, ...props },
    ref
  ) {
    const id = useId();
    const inputId = `${id}-${name}`;
    const { value, touched, errors, setValue, setTouched } = useField(formId, name);
    
    const hasError = touched && errors.length > 0;
    
    return (
      <FieldWrapper
        formId={formId}
        name={name}
        inputId={inputId}
        label={label}
        helperText={helperText}
        required={required}
        className={wrapperClassName}
      >
        <input
          ref={ref}
          id={inputId}
          name={name}
          value={String(value ?? '')}
          onChange={(e) => setValue(e.target.value)}
          onBlur={() => setTouched()}
          aria-invalid={hasError}
          aria-describedby={hasError ? `${id}-${name}-error` : undefined}
          className={cn(
            'w-full px-3 py-2 border rounded-md transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            'bg-background text-foreground',
            hasError
              ? 'border-red-500 focus:ring-red-500/20'
              : 'border-input focus:ring-primary/20 focus:border-primary',
            'pr-10', // Space for validation icon
            className
          )}
          {...props}
        />
      </FieldWrapper>
    );
  }
);

// =============================================================================
// Validated Textarea Component
// =============================================================================

export interface ValidatedTextareaProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'name'> {
  formId: string;
  name: string;
  label?: string;
  helperText?: string;
  wrapperClassName?: string;
}

export const ValidatedTextarea = forwardRef<HTMLTextAreaElement, ValidatedTextareaProps>(
  function ValidatedTextarea(
    { formId, name, label, helperText, className, wrapperClassName, required, ...props },
    ref
  ) {
    const id = useId();
    const inputId = `${id}-${name}`;
    const { value, touched, errors, setValue, setTouched } = useField(formId, name);
    
    const hasError = touched && errors.length > 0;
    
    return (
      <FieldWrapper
        formId={formId}
        name={name}
        inputId={inputId}
        label={label}
        helperText={helperText}
        required={required}
        className={wrapperClassName}
      >
        <textarea
          ref={ref}
          id={inputId}
          name={name}
          value={String(value ?? '')}
          onChange={(e) => setValue(e.target.value)}
          onBlur={() => setTouched()}
          aria-invalid={hasError}
          aria-describedby={hasError ? `${inputId}-error` : undefined}
          className={cn(
            'w-full px-3 py-2 border rounded-md transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            'bg-background text-foreground resize-y min-h-[80px]',
            hasError
              ? 'border-red-500 focus:ring-red-500/20'
              : 'border-input focus:ring-primary/20 focus:border-primary',
            className
          )}
          {...props}
        />
      </FieldWrapper>
    );
  }
);

// =============================================================================
// Validated Select Component
// =============================================================================

export interface ValidatedSelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'name'> {
  formId: string;
  name: string;
  label?: string;
  helperText?: string;
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  placeholder?: string;
  wrapperClassName?: string;
}

export const ValidatedSelect = forwardRef<HTMLSelectElement, ValidatedSelectProps>(
  function ValidatedSelect(
    { formId, name, label, helperText, options, placeholder, className, wrapperClassName, required, ...props },
    ref
  ) {
    const id = useId();
    const inputId = `${id}-${name}`;
    const { value, touched, errors, setValue, setTouched } = useField(formId, name);
    
    const hasError = touched && errors.length > 0;
    
    return (
      <FieldWrapper
        formId={formId}
        name={name}
        inputId={inputId}
        label={label}
        helperText={helperText}
        required={required}
        className={wrapperClassName}
      >
        <select
          ref={ref}
          id={inputId}
          name={name}
          value={String(value ?? '')}
          onChange={(e) => setValue(e.target.value)}
          onBlur={() => setTouched()}
          aria-invalid={hasError}
          aria-describedby={hasError ? `${inputId}-error` : undefined}
          className={cn(
            'w-full px-3 py-2 border rounded-md transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            'bg-background text-foreground appearance-none cursor-pointer',
            hasError
              ? 'border-red-500 focus:ring-red-500/20'
              : 'border-input focus:ring-primary/20 focus:border-primary',
            'pr-10',
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        {/* Select arrow */}
        <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-5 h-5 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </FieldWrapper>
    );
  }
);

// =============================================================================
// Validated Checkbox Component
// =============================================================================

export interface ValidatedCheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'name' | 'type'> {
  formId: string;
  name: string;
  label: string;
  helperText?: string;
  wrapperClassName?: string;
}

export const ValidatedCheckbox = forwardRef<HTMLInputElement, ValidatedCheckboxProps>(
  function ValidatedCheckbox(
    { formId, name, label, helperText, className, wrapperClassName, ...props },
    ref
  ) {
    const id = useId();
    const { value, touched, errors, setValue, setTouched } = useField(formId, name);
    
    const hasError = touched && errors.length > 0;
    const checked = Boolean(value);
    
    return (
      <div className={cn('space-y-1', wrapperClassName)}>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            ref={ref}
            type="checkbox"
            id={`${id}-${name}`}
            name={name}
            checked={checked}
            onChange={(e) => setValue(e.target.checked)}
            onBlur={() => setTouched()}
            aria-invalid={hasError}
            className={cn(
              'mt-1 w-4 h-4 rounded border transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-offset-0',
              hasError
                ? 'border-red-500 focus:ring-red-500/20'
                : 'border-input focus:ring-primary/20',
              className
            )}
            {...props}
          />
          <span className="text-sm text-foreground">{label}</span>
        </label>
        
        {touched && errors.length > 0 && <ValidationMessages results={errors} />}
        {helperText && !hasError && (
          <p className="text-sm text-muted-foreground ml-6">{helperText}</p>
        )}
      </div>
    );
  }
);

// =============================================================================
// Gate Check Display Component
// =============================================================================

export interface GateCheckDisplayProps {
  result: GateValidationResult;
  className?: string;
  title?: string;
  showAllChecks?: boolean;
}

export function GateCheckDisplay({
  result,
  className,
  title = 'Pre-submission Checks',
  showAllChecks = false,
}: GateCheckDisplayProps) {
  const checks = result.checks ?? [];
  const failedBlocking = checks.filter(c => c.blocking && !c.result?.passed);
  const failedWarnings = checks.filter(c => !c.blocking && !c.result?.passed);
  const passed = checks.filter(c => c.result?.passed);
  const canProceed = result.canProceed ?? result.passed ?? false;
  
  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">{title}</h3>
        {canProceed ? (
          <span className="inline-flex items-center gap-1 text-sm text-emerald-600 dark:text-emerald-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Ready to proceed
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-sm text-red-600 dark:text-red-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Blocking issues
          </span>
        )}
      </div>
      
      {/* Blocking issues */}
      {failedBlocking.length > 0 && (
        <div className={cn('p-4 rounded-lg border', getSeverityBackgroundClass('error'))}>
          <h4 className="font-medium text-red-700 dark:text-red-300 mb-2">
            Must be resolved before proceeding
          </h4>
          <ul className="space-y-2">
            {failedBlocking.map((check) => (
              <li key={check.id ?? check.key} className="text-sm">
                <div className="font-medium text-red-600 dark:text-red-400">
                  {check.name ?? check.label}: {check.result?.message}
                </div>
                {check.result?.details && check.result.details.length > 0 && (
                  <ul className="ml-4 mt-1 list-disc text-muted-foreground">
                    {check.result.details.map((detail: string, i: number) => (
                      <li key={i}>{detail}</li>
                    ))}
                  </ul>
                )}
                {check.result?.suggestions && (
                  <p className="mt-1 text-muted-foreground italic">
                    {check.result.suggestions[0]}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Warnings */}
      {failedWarnings.length > 0 && (
        <div className={cn('p-4 rounded-lg border', getSeverityBackgroundClass('warning'))}>
          <h4 className="font-medium text-amber-700 dark:text-amber-300 mb-2">
            Warnings (can still proceed)
          </h4>
          <ul className="space-y-2">
            {failedWarnings.map((check) => (
              <li key={check.id ?? check.key} className="text-sm">
                <div className="font-medium text-amber-600 dark:text-amber-400">
                  {check.name ?? check.label}: {check.result?.message}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Passed checks (optional) */}
      {showAllChecks && passed.length > 0 && (
        <div className={cn('p-4 rounded-lg border', getSeverityBackgroundClass('success'))}>
          <h4 className="font-medium text-emerald-700 dark:text-emerald-300 mb-2">
            Passed
          </h4>
          <ul className="space-y-1">
            {passed.map((check) => (
              <li key={check.id ?? check.key} className="text-sm flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>{check.name ?? check.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Form Summary Component
// =============================================================================

export interface FormSummaryProps {
  formId: string;
  className?: string;
  showWhenValid?: boolean;
}

export function FormSummary({
  formId,
  className,
  showWhenValid = false,
}: FormSummaryProps) {
  const form = useFormValidationStore((state) => state.forms[formId]);
  
  if (!form) return null;
  
  const { hasErrors, hasWarnings, errors = [], warnings = [], isValid } = form;
  
  if (isValid && !hasWarnings && !showWhenValid) {
    return null;
  }
  
  if (isValid && !hasWarnings && showWhenValid) {
    return (
      <div className={cn('p-4 rounded-lg border', getSeverityBackgroundClass('success'), className)}>
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-medium text-emerald-700 dark:text-emerald-300">
            All fields are valid
          </span>
        </div>
      </div>
    );
  }
  
  return (
    <div className={cn('space-y-3', className)}>
      {hasErrors && (
        <div className={cn('p-4 rounded-lg border', getSeverityBackgroundClass('error'))}>
          <h4 className="font-medium text-red-700 dark:text-red-300 mb-2">
            {errors.length} error{errors.length !== 1 ? 's' : ''} to fix
          </h4>
          <ul className="space-y-1 text-sm">
            {errors.slice(0, 5).map((error, i) => (
              <li key={i} className="text-red-600 dark:text-red-400">
                {error.field && <span className="font-medium">{error.field}: </span>}
                {error.message}
              </li>
            ))}
            {errors.length > 5 && (
              <li className="text-muted-foreground">
                And {errors.length - 5} more...
              </li>
            )}
          </ul>
        </div>
      )}
      
      {hasWarnings && (
        <div className={cn('p-4 rounded-lg border', getSeverityBackgroundClass('warning'))}>
          <h4 className="font-medium text-amber-700 dark:text-amber-300 mb-2">
            {warnings.length} warning{warnings.length !== 1 ? 's' : ''}
          </h4>
          <ul className="space-y-1 text-sm">
            {warnings.slice(0, 3).map((warning, i) => (
              <li key={i} className="text-amber-600 dark:text-amber-400">
                {warning.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Auto-register Field Component
// =============================================================================

export interface AutoFieldProps {
  formId: string;
  schema: FieldSchema;
  className?: string;
}

export function AutoField({ formId, schema, className }: AutoFieldProps) {
  const registerField = useFormValidationStore((state) => state.registerField);
  const unregisterField = useFormValidationStore((state) => state.unregisterField);
  
  // Derive the field name from schema.name or fallback to schema.field
  const fieldName = schema.name ?? schema.field;
  
  // Register field on mount
  useEffect(() => {
    const rules = createRulesFromSchema(schema);
    registerField(formId, {
      name: fieldName,
      rules,
    });
    
    return () => {
      unregisterField(formId, fieldName);
    };
  }, [formId, fieldName, registerField, unregisterField]);
  
  // Render appropriate component based on type
  switch (schema.type) {
    case 'textarea':
      return (
        <ValidatedTextarea
          formId={formId}
          name={fieldName}
          label={schema.label}
          helperText={schema.helperText}
          required={schema.required}
          placeholder={schema.placeholder}
          wrapperClassName={className}
        />
      );
    
    case 'select':
      return (
        <ValidatedSelect
          formId={formId}
          name={fieldName}
          label={schema.label}
          helperText={schema.helperText}
          required={schema.required}
          placeholder={schema.placeholder}
          options={schema.options ?? []}
          wrapperClassName={className}
        />
      );
    
    case 'checkbox':
      return (
        <ValidatedCheckbox
          formId={formId}
          name={fieldName}
          label={schema.label}
          helperText={schema.helperText}
          wrapperClassName={className}
        />
      );
    
    case 'number':
      return (
        <ValidatedInput
          formId={formId}
          name={fieldName}
          type="number"
          label={schema.label}
          helperText={schema.helperText}
          required={schema.required}
          placeholder={schema.placeholder}
          min={schema.min}
          max={schema.max}
          wrapperClassName={className}
        />
      );
    
    case 'email':
    case 'phone':
    case 'url':
    case 'date':
      return (
        <ValidatedInput
          formId={formId}
          name={fieldName}
          type={(schema.type ?? 'text') === 'phone' ? 'tel' : (schema.type ?? 'text')}
          label={schema.label}
          helperText={schema.helperText}
          required={schema.required}
          placeholder={schema.placeholder}
          wrapperClassName={className}
        />
      );
    
    default:
      return (
        <ValidatedInput
          formId={formId}
          name={fieldName}
          type="text"
          label={schema.label}
          helperText={schema.helperText}
          required={schema.required}
          placeholder={schema.placeholder}
          minLength={schema.minLength}
          maxLength={schema.maxLength}
          wrapperClassName={className}
        />
      );
  }
}

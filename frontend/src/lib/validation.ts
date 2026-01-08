/**
 * Inline Validation System
 * 
 * Real-time validation with clear guidance for form fields.
 * Features:
 * - Field-level validation with custom validators
 * - Schema-based validation (like Zod integration)
 * - Async validation support (e.g., checking uniqueness)
 * - Debounced validation to prevent excessive calls
 * - Cross-field validation (conditional rules)
 * - Validation message severity levels
 * - Pre-submission gate checks
 */

// =============================================================================
// Types
// =============================================================================

export type ValidationSeverity = 'error' | 'warning' | 'info' | 'success';

export type ValidationStatus = 'idle' | 'validating' | 'valid' | 'invalid';

export interface ValidationResult {
  valid: boolean;
  message?: string;
  severity: ValidationSeverity;
  field?: string;
  code?: string;
}

export interface FieldValidation {
  status: ValidationStatus;
  touched: boolean;
  dirty: boolean;
  results: ValidationResult[];
  lastValidatedValue?: unknown;
  validatedAt?: Date;
}

export interface ValidationRule<T = unknown> {
  id: string;
  validate: (value: T, context?: ValidationContext) => ValidationResult | Promise<ValidationResult>;
  message?: string;
  severity?: ValidationSeverity;
  async?: boolean;
  debounceMs?: number;
  condition?: (context: ValidationContext) => boolean;
}

export interface ValidationContext {
  fieldName: string;
  values: Record<string, unknown>;
  touched: Record<string, boolean>;
  dirty: Record<string, boolean>;
  metadata?: Record<string, unknown>;
}

export interface FieldConfig<T = unknown> {
  name: string;
  label?: string;
  required?: boolean;
  rules?: ValidationRule<T>[];
  dependsOn?: string[];
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
  debounceMs?: number;
}

export interface FormValidationState {
  fields: Record<string, FieldValidation>;
  values: Record<string, unknown>;
  isValid: boolean;
  isValidating: boolean;
  isDirty: boolean;
  hasErrors: boolean;
  hasWarnings: boolean;
  errors: ValidationResult[];
  warnings: ValidationResult[];
  submitCount: number;
}

export interface GateCheck {
  id: string;
  name: string;
  description: string;
  check: (state: FormValidationState) => GateCheckResult;
  severity: ValidationSeverity;
  blocking: boolean;
}

export interface GateCheckResult {
  passed: boolean;
  message: string;
  details?: string[];
  suggestions?: string[];
}

export interface GateValidationResult {
  canProceed: boolean;
  checks: Array<GateCheck & { result: GateCheckResult }>;
  blockers: string[];
  warnings: string[];
}

// =============================================================================
// Built-in Validation Rules
// =============================================================================

/**
 * Required field validator
 */
export const required = (message = 'This field is required'): ValidationRule => ({
  id: 'required',
  message,
  severity: 'error',
  validate: (value) => {
    const isEmpty = 
      value === undefined || 
      value === null || 
      value === '' ||
      (Array.isArray(value) && value.length === 0) ||
      (typeof value === 'object' && Object.keys(value).length === 0);
    
    return {
      valid: !isEmpty,
      message: isEmpty ? message : undefined,
      severity: 'error',
    };
  },
});

/**
 * Minimum length validator
 */
export const minLength = (min: number, message?: string): ValidationRule<string> => ({
  id: 'minLength',
  message: message ?? `Must be at least ${min} characters`,
  severity: 'error',
  validate: (value) => {
    const str = String(value ?? '');
    const valid = str.length >= min;
    return {
      valid,
      message: valid ? undefined : (message ?? `Must be at least ${min} characters`),
      severity: 'error',
    };
  },
});

/**
 * Maximum length validator
 */
export const maxLength = (max: number, message?: string): ValidationRule<string> => ({
  id: 'maxLength',
  message: message ?? `Must be no more than ${max} characters`,
  severity: 'error',
  validate: (value) => {
    const str = String(value ?? '');
    const valid = str.length <= max;
    return {
      valid,
      message: valid ? undefined : (message ?? `Must be no more than ${max} characters`),
      severity: 'error',
    };
  },
});

/**
 * Minimum value validator (numbers)
 */
export const min = (minVal: number, message?: string): ValidationRule<number> => ({
  id: 'min',
  message: message ?? `Must be at least ${minVal}`,
  severity: 'error',
  validate: (value) => {
    const num = Number(value);
    const valid = !isNaN(num) && num >= minVal;
    return {
      valid,
      message: valid ? undefined : (message ?? `Must be at least ${minVal}`),
      severity: 'error',
    };
  },
});

/**
 * Maximum value validator (numbers)
 */
export const max = (maxVal: number, message?: string): ValidationRule<number> => ({
  id: 'max',
  message: message ?? `Must be no more than ${maxVal}`,
  severity: 'error',
  validate: (value) => {
    const num = Number(value);
    const valid = !isNaN(num) && num <= maxVal;
    return {
      valid,
      message: valid ? undefined : (message ?? `Must be no more than ${maxVal}`),
      severity: 'error',
    };
  },
});

/**
 * Regex pattern validator
 */
export const pattern = (regex: RegExp, message = 'Invalid format'): ValidationRule<string> => ({
  id: 'pattern',
  message,
  severity: 'error',
  validate: (value) => {
    const str = String(value ?? '');
    const valid = str === '' || regex.test(str);
    return {
      valid,
      message: valid ? undefined : message,
      severity: 'error',
    };
  },
});

/**
 * Email validator
 */
export const email = (message = 'Invalid email address'): ValidationRule<string> => {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return {
    id: 'email',
    message,
    severity: 'error',
    validate: (value) => {
      const str = String(value ?? '');
      const valid = str === '' || emailRegex.test(str);
      return {
        valid,
        message: valid ? undefined : message,
        severity: 'error',
      };
    },
  };
};

/**
 * URL validator
 */
export const url = (message = 'Invalid URL'): ValidationRule<string> => ({
  id: 'url',
  message,
  severity: 'error',
  validate: (value) => {
    const str = String(value ?? '');
    if (str === '') {
      return { valid: true, severity: 'error' };
    }
    try {
      new URL(str);
      return { valid: true, severity: 'error' };
    } catch {
      return { valid: false, message, severity: 'error' };
    }
  },
});

/**
 * Phone number validator
 */
export const phone = (message = 'Invalid phone number'): ValidationRule<string> => {
  // Flexible international phone pattern - allows +, spaces, dashes, dots, parentheses, digits
  const phoneRegex = /^[+]?[0-9]?[-\s.()\/0-9]*$/;
  return {
    id: 'phone',
    message,
    severity: 'error',
    validate: (value) => {
      const str = String(value ?? '').trim();
      // Check the original string against regex (which allows formatting chars)
      // Also check minimum digits (at least 7 digits)
      const digitsOnly = str.replace(/\D/g, '');
      const valid = str === '' || (digitsOnly.length >= 7 && phoneRegex.test(str));
      return {
        valid,
        message: valid ? undefined : message,
        severity: 'error',
      };
    },
  };
};

/**
 * Date validator (must be valid date)
 */
export const validDate = (message = 'Invalid date'): ValidationRule<string | Date> => ({
  id: 'validDate',
  message,
  severity: 'error',
  validate: (value) => {
    if (value === null || value === undefined || value === '') {
      return { valid: true, severity: 'error' };
    }
    const date = value instanceof Date ? value : new Date(String(value));
    const valid = !isNaN(date.getTime());
    return {
      valid,
      message: valid ? undefined : message,
      severity: 'error',
    };
  },
});

/**
 * Date must be in the future
 */
export const futureDate = (message = 'Date must be in the future'): ValidationRule<string | Date> => ({
  id: 'futureDate',
  message,
  severity: 'error',
  validate: (value) => {
    if (value === null || value === undefined || value === '') {
      return { valid: true, severity: 'error' };
    }
    const date = value instanceof Date ? value : new Date(String(value));
    const valid = !isNaN(date.getTime()) && date > new Date();
    return {
      valid,
      message: valid ? undefined : message,
      severity: 'error',
    };
  },
});

/**
 * Date must be in the past
 */
export const pastDate = (message = 'Date must be in the past'): ValidationRule<string | Date> => ({
  id: 'pastDate',
  message,
  severity: 'error',
  validate: (value) => {
    if (value === null || value === undefined || value === '') {
      return { valid: true, severity: 'error' };
    }
    const date = value instanceof Date ? value : new Date(String(value));
    const valid = !isNaN(date.getTime()) && date < new Date();
    return {
      valid,
      message: valid ? undefined : message,
      severity: 'error',
    };
  },
});

/**
 * Custom validator factory
 */
export const custom = <T = unknown>(
  id: string,
  validateFn: (value: T, context?: ValidationContext) => boolean,
  message: string,
  severity: ValidationSeverity = 'error'
): ValidationRule<T> => ({
  id,
  message,
  severity,
  validate: (value, context) => {
    const valid = validateFn(value, context);
    return {
      valid,
      message: valid ? undefined : message,
      severity,
    };
  },
});

/**
 * Async validator factory
 */
export const asyncValidator = <T = unknown>(
  id: string,
  validateFn: (value: T, context?: ValidationContext) => Promise<boolean>,
  message: string,
  options: {
    severity?: ValidationSeverity;
    debounceMs?: number;
  } = {}
): ValidationRule<T> => ({
  id,
  message,
  severity: options.severity ?? 'error',
  async: true,
  debounceMs: options.debounceMs ?? 300,
  validate: async (value, context) => {
    const valid = await validateFn(value, context);
    return {
      valid,
      message: valid ? undefined : message,
      severity: options.severity ?? 'error',
    };
  },
});

/**
 * Conditional validator that only runs when condition is met
 */
export const when = <T = unknown>(
  condition: (context: ValidationContext) => boolean,
  rule: ValidationRule<T>
): ValidationRule<T> => ({
  ...rule,
  id: `conditional_${rule.id}`,
  condition,
});

/**
 * Warning validator (non-blocking)
 */
export const warning = <T = unknown>(
  id: string,
  validateFn: (value: T, context?: ValidationContext) => boolean,
  message: string
): ValidationRule<T> => ({
  id,
  message,
  severity: 'warning',
  validate: (value, context) => {
    const valid = validateFn(value, context);
    return {
      valid: true, // Warnings don't make the field invalid
      message: valid ? undefined : message,
      severity: 'warning',
    };
  },
});

/**
 * Info message (non-blocking)
 */
export const info = <T = unknown>(
  id: string,
  condition: (value: T, context?: ValidationContext) => boolean,
  message: string
): ValidationRule<T> => ({
  id,
  message,
  severity: 'info',
  validate: (value, context) => {
    const show = condition(value, context);
    return {
      valid: true,
      message: show ? message : undefined,
      severity: 'info',
    };
  },
});

// =============================================================================
// Validation Utilities
// =============================================================================

/**
 * Combine multiple validation results
 */
export function combineResults(results: ValidationResult[]): {
  valid: boolean;
  errors: ValidationResult[];
  warnings: ValidationResult[];
  infos: ValidationResult[];
} {
  const errors = results.filter(r => !r.valid && r.severity === 'error');
  const warnings = results.filter(r => r.message && r.severity === 'warning');
  const infos = results.filter(r => r.message && r.severity === 'info');
  
  return {
    valid: errors.length === 0,
    errors,
    warnings,
    infos,
  };
}

/**
 * Run all rules for a field
 */
export async function validateField<T>(
  value: T,
  rules: ValidationRule<T>[],
  context: ValidationContext
): Promise<ValidationResult[]> {
  const results: ValidationResult[] = [];
  
  for (const rule of rules) {
    // Check condition
    if (rule.condition && !rule.condition(context)) {
      continue;
    }
    
    // Run validation
    const result = await Promise.resolve(rule.validate(value, context));
    result.field = context.fieldName;
    result.code = rule.id;
    
    if (result.message) {
      results.push(result);
    }
    
    // Stop on first error for better UX
    if (!result.valid && result.severity === 'error') {
      break;
    }
  }
  
  return results;
}

/**
 * Debounce a validation function
 */
export function debounceValidation<T extends (...args: unknown[]) => Promise<ValidationResult[]>>(
  fn: T,
  ms: number
): T & { cancel: () => void } {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
  const debounced = ((...args: unknown[]) => {
    return new Promise<ValidationResult[]>((resolve) => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      
      timeoutId = setTimeout(async () => {
        const result = await fn(...args);
        resolve(result);
      }, ms);
    });
  }) as T & { cancel: () => void };
  
  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };
  
  return debounced;
}

/**
 * Create initial field validation state
 */
export function createFieldValidation(): FieldValidation {
  return {
    status: 'idle',
    touched: false,
    dirty: false,
    results: [],
  };
}

/**
 * Create initial form validation state
 */
export function createFormValidationState(
  initialValues: Record<string, unknown> = {}
): FormValidationState {
  return {
    fields: {},
    values: initialValues,
    isValid: true,
    isValidating: false,
    isDirty: false,
    hasErrors: false,
    hasWarnings: false,
    errors: [],
    warnings: [],
    submitCount: 0,
  };
}

/**
 * Get severity icon name
 */
export function getSeverityIcon(severity: ValidationSeverity): string {
  switch (severity) {
    case 'error':
      return 'alert-circle';
    case 'warning':
      return 'alert-triangle';
    case 'info':
      return 'info';
    case 'success':
      return 'check-circle';
    default:
      return 'info';
  }
}

/**
 * Get severity color class
 */
export function getSeverityColorClass(severity: ValidationSeverity): string {
  switch (severity) {
    case 'error':
      return 'text-red-600 dark:text-red-400';
    case 'warning':
      return 'text-amber-600 dark:text-amber-400';
    case 'info':
      return 'text-blue-600 dark:text-blue-400';
    case 'success':
      return 'text-emerald-600 dark:text-emerald-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

/**
 * Get severity background class
 */
export function getSeverityBackgroundClass(severity: ValidationSeverity): string {
  switch (severity) {
    case 'error':
      return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
    case 'warning':
      return 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800';
    case 'info':
      return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
    case 'success':
      return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800';
    default:
      return 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
  }
}

// =============================================================================
// Gate Checks (Pre-submission Validation)
// =============================================================================

/**
 * Common gate check: All required fields filled
 */
export const requiredFieldsGate = (
  requiredFields: string[],
  fieldLabels?: Record<string, string>
): GateCheck => ({
  id: 'required-fields',
  name: 'Required Fields',
  description: 'All required fields must be filled',
  severity: 'error',
  blocking: true,
  check: (state) => {
    const missing = requiredFields.filter(field => {
      const value = state.values[field];
      return value === undefined || value === null || value === '' ||
        (Array.isArray(value) && value.length === 0);
    });
    
    return {
      passed: missing.length === 0,
      message: missing.length === 0
        ? 'All required fields are filled'
        : `${missing.length} required field(s) missing`,
      details: missing.map(f => fieldLabels?.[f] ?? f),
      suggestions: missing.length > 0
        ? ['Please fill in all required fields before proceeding']
        : undefined,
    };
  },
});

/**
 * Common gate check: No validation errors
 */
export const noErrorsGate: GateCheck = {
  id: 'no-errors',
  name: 'Validation',
  description: 'All fields must pass validation',
  severity: 'error',
  blocking: true,
  check: (state) => {
    const errorCount = state.errors.length;
    
    return {
      passed: errorCount === 0,
      message: errorCount === 0
        ? 'All fields pass validation'
        : `${errorCount} validation error(s)`,
      details: state.errors.map(e => e.message ?? 'Unknown error'),
      suggestions: errorCount > 0
        ? ['Please fix all validation errors before proceeding']
        : undefined,
    };
  },
};

/**
 * Common gate check: Assumptions reviewed (for quote release)
 */
export const assumptionsReviewedGate = (
  assumptionField = 'assumptions',
  acknowledgedField = 'assumptionsReviewed'
): GateCheck => ({
  id: 'assumptions-reviewed',
  name: 'Assumptions',
  description: 'Assumptions must be reviewed before release',
  severity: 'error',
  blocking: true,
  check: (state) => {
    const assumptions = state.values[assumptionField];
    const reviewed = state.values[acknowledgedField];
    
    if (!assumptions || (Array.isArray(assumptions) && assumptions.length === 0)) {
      return {
        passed: true,
        message: 'No assumptions to review',
      };
    }
    
    return {
      passed: Boolean(reviewed),
      message: reviewed ? 'Assumptions have been reviewed' : 'Assumptions require review',
      suggestions: !reviewed
        ? ['Please review and acknowledge all assumptions before releasing']
        : undefined,
    };
  },
});

/**
 * Common gate check: Approvals obtained
 */
export const approvalsGate = (
  requiredApprovals: string[],
  approvalField = 'approvals'
): GateCheck => ({
  id: 'approvals',
  name: 'Approvals',
  description: 'Required approvals must be obtained',
  severity: 'error',
  blocking: true,
  check: (state) => {
    const approvals = (state.values[approvalField] as string[]) ?? [];
    const missing = requiredApprovals.filter(a => !approvals.includes(a));
    
    return {
      passed: missing.length === 0,
      message: missing.length === 0
        ? 'All required approvals obtained'
        : `${missing.length} approval(s) pending`,
      details: missing,
      suggestions: missing.length > 0
        ? ['Request missing approvals before proceeding']
        : undefined,
    };
  },
});

/**
 * Run gate checks
 */
export function runGateChecks(
  state: FormValidationState,
  gates: GateCheck[]
): GateValidationResult {
  const results = gates.map(gate => ({
    ...gate,
    result: gate.check(state),
  }));
  
  const blockers = results
    .filter(g => g.blocking && !g.result.passed)
    .map(g => g.result.message);
  
  const warnings = results
    .filter(g => !g.blocking && !g.result.passed)
    .map(g => g.result.message);
  
  return {
    canProceed: blockers.length === 0,
    checks: results,
    blockers,
    warnings,
  };
}

// =============================================================================
// Field Schemas (Quick Configuration)
// =============================================================================

export interface FieldSchema {
  name: string;
  label: string;
  type: 'text' | 'email' | 'phone' | 'url' | 'number' | 'date' | 'select' | 'textarea' | 'checkbox';
  required?: boolean;
  placeholder?: string;
  helperText?: string;
  rules?: ValidationRule[];
  options?: Array<{ value: string; label: string }>;
  min?: number;
  max?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
}

/**
 * Create validation rules from field schema
 */
export function createRulesFromSchema(schema: FieldSchema): ValidationRule<unknown>[] {
  const rules: ValidationRule<unknown>[] = [];
  
  if (schema.required) {
    rules.push(required(`${schema.label} is required`));
  }
  
  if (schema.minLength !== undefined) {
    rules.push(minLength(schema.minLength, `${schema.label} must be at least ${schema.minLength} characters`) as ValidationRule<unknown>);
  }
  
  if (schema.maxLength !== undefined) {
    rules.push(maxLength(schema.maxLength, `${schema.label} must be no more than ${schema.maxLength} characters`) as ValidationRule<unknown>);
  }
  
  if (schema.min !== undefined) {
    rules.push(min(schema.min, `${schema.label} must be at least ${schema.min}`) as ValidationRule<unknown>);
  }
  
  if (schema.max !== undefined) {
    rules.push(max(schema.max, `${schema.label} must be no more than ${schema.max}`) as ValidationRule<unknown>);
  }
  
  if (schema.type === 'email') {
    rules.push(email(`Please enter a valid email address`) as ValidationRule<unknown>);
  }
  
  if (schema.type === 'phone') {
    rules.push(phone(`Please enter a valid phone number`) as ValidationRule<unknown>);
  }
  
  if (schema.type === 'url') {
    rules.push(url(`Please enter a valid URL`) as ValidationRule<unknown>);
  }
  
  if (schema.type === 'date') {
    rules.push(validDate(`Please enter a valid date`) as ValidationRule<unknown>);
  }
  
  if (schema.pattern) {
    rules.push(pattern(schema.pattern, `${schema.label} format is invalid`) as ValidationRule<unknown>);
  }
  
  // Add any custom rules
  if (schema.rules) {
    rules.push(...schema.rules);
  }
  
  return rules;
}

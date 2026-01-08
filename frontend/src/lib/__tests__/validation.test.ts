/**
 * Tests for validation library
 */
import {
  // Types
  type ValidationResult,
  type ValidationContext,
  type FieldSchema,
  // Built-in Rules
  required,
  minLength,
  maxLength,
  min,
  max,
  pattern,
  email,
  url,
  phone,
  validDate,
  futureDate,
  pastDate,
  custom,
  asyncValidator,
  when,
  warning,
  info,
  // Utilities
  combineResults,
  validateField,
  debounceValidation,
  createFieldValidation,
  createFormValidationState,
  getSeverityIcon,
  getSeverityColorClass,
  getSeverityBackgroundClass,
  // Gate Checks
  requiredFieldsGate,
  noErrorsGate,
  assumptionsReviewedGate,
  approvalsGate,
  runGateChecks,
  // Schema
  createRulesFromSchema,
} from '@/lib/validation';

// =============================================================================
// Required Validator Tests
// =============================================================================

describe('required validator', () => {
  const rule = required();
  
  it('should fail for undefined', async () => {
    const result = await rule.validate(undefined);
    expect(result.valid).toBe(false);
    expect(result.message).toBeDefined();
  });
  
  it('should fail for null', async () => {
    const result = await rule.validate(null);
    expect(result.valid).toBe(false);
  });
  
  it('should fail for empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(false);
  });
  
  it('should fail for empty array', async () => {
    const result = await rule.validate([]);
    expect(result.valid).toBe(false);
  });
  
  it('should fail for empty object', async () => {
    const result = await rule.validate({});
    expect(result.valid).toBe(false);
  });
  
  it('should pass for non-empty string', async () => {
    const result = await rule.validate('hello');
    expect(result.valid).toBe(true);
    expect(result.message).toBeUndefined();
  });
  
  it('should pass for number', async () => {
    const result = await rule.validate(42);
    expect(result.valid).toBe(true);
  });
  
  it('should pass for zero', async () => {
    const result = await rule.validate(0);
    expect(result.valid).toBe(true);
  });
  
  it('should pass for false', async () => {
    const result = await rule.validate(false);
    expect(result.valid).toBe(true);
  });
  
  it('should use custom message', async () => {
    const customRule = required('Please fill this field');
    const result = await customRule.validate('');
    expect(result.message).toBe('Please fill this field');
  });
});

// =============================================================================
// Length Validator Tests
// =============================================================================

describe('minLength validator', () => {
  const rule = minLength(5);
  
  it('should fail for string shorter than min', async () => {
    const result = await rule.validate('abc');
    expect(result.valid).toBe(false);
  });
  
  it('should pass for string equal to min', async () => {
    const result = await rule.validate('abcde');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for string longer than min', async () => {
    const result = await rule.validate('abcdefgh');
    expect(result.valid).toBe(true);
  });
  
  it('should handle empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(false);
  });
  
  it('should use custom message', async () => {
    const customRule = minLength(3, 'Too short!');
    const result = await customRule.validate('ab');
    expect(result.message).toBe('Too short!');
  });
});

describe('maxLength validator', () => {
  const rule = maxLength(10);
  
  it('should fail for string longer than max', async () => {
    const result = await rule.validate('12345678901');
    expect(result.valid).toBe(false);
  });
  
  it('should pass for string equal to max', async () => {
    const result = await rule.validate('1234567890');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for string shorter than max', async () => {
    const result = await rule.validate('abc');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// Numeric Validator Tests
// =============================================================================

describe('min validator', () => {
  const rule = min(5);
  
  it('should fail for number less than min', async () => {
    const result = await rule.validate(3);
    expect(result.valid).toBe(false);
  });
  
  it('should pass for number equal to min', async () => {
    const result = await rule.validate(5);
    expect(result.valid).toBe(true);
  });
  
  it('should pass for number greater than min', async () => {
    const result = await rule.validate(10);
    expect(result.valid).toBe(true);
  });
  
  it('should fail for NaN', async () => {
    const result = await rule.validate(NaN);
    expect(result.valid).toBe(false);
  });
  
  it('should handle negative numbers', async () => {
    const negRule = min(-10);
    const result = await negRule.validate(-5);
    expect(result.valid).toBe(true);
  });
});

describe('max validator', () => {
  const rule = max(100);
  
  it('should fail for number greater than max', async () => {
    const result = await rule.validate(150);
    expect(result.valid).toBe(false);
  });
  
  it('should pass for number equal to max', async () => {
    const result = await rule.validate(100);
    expect(result.valid).toBe(true);
  });
  
  it('should pass for number less than max', async () => {
    const result = await rule.validate(50);
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// Pattern Validator Tests
// =============================================================================

describe('pattern validator', () => {
  const rule = pattern(/^[A-Z]{3}-\d{4}$/, 'Invalid format');
  
  it('should fail for non-matching string', async () => {
    const result = await rule.validate('invalid');
    expect(result.valid).toBe(false);
    expect(result.message).toBe('Invalid format');
  });
  
  it('should pass for matching string', async () => {
    const result = await rule.validate('ABC-1234');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty string (not required)', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// Email Validator Tests
// =============================================================================

describe('email validator', () => {
  const rule = email();
  
  it('should fail for invalid email', async () => {
    const result = await rule.validate('not-an-email');
    expect(result.valid).toBe(false);
  });
  
  it('should fail for email without domain', async () => {
    const result = await rule.validate('test@');
    expect(result.valid).toBe(false);
  });
  
  it('should fail for email without @', async () => {
    const result = await rule.validate('testexample.com');
    expect(result.valid).toBe(false);
  });
  
  it('should pass for valid email', async () => {
    const result = await rule.validate('test@example.com');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for email with subdomain', async () => {
    const result = await rule.validate('test@mail.example.com');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for email with plus sign', async () => {
    const result = await rule.validate('test+filter@example.com');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// URL Validator Tests
// =============================================================================

describe('url validator', () => {
  const rule = url();
  
  it('should fail for invalid URL', async () => {
    const result = await rule.validate('not-a-url');
    expect(result.valid).toBe(false);
  });
  
  it('should pass for valid http URL', async () => {
    const result = await rule.validate('http://example.com');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for valid https URL', async () => {
    const result = await rule.validate('https://example.com/path?query=1');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// Phone Validator Tests
// =============================================================================

describe('phone validator', () => {
  const rule = phone();
  
  it('should fail for too short number', async () => {
    const result = await rule.validate('123');
    expect(result.valid).toBe(false);
  });
  
  it('should pass for valid US phone', async () => {
    const result = await rule.validate('555-123-4567');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for international format', async () => {
    const result = await rule.validate('+1 (555) 123-4567');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for digits only', async () => {
    const result = await rule.validate('5551234567');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// Date Validator Tests
// =============================================================================

describe('validDate validator', () => {
  const rule = validDate();
  
  it('should fail for invalid date string', async () => {
    const result = await rule.validate('not-a-date');
    expect(result.valid).toBe(false);
  });
  
  it('should pass for valid date string', async () => {
    const result = await rule.validate('2024-01-15');
    expect(result.valid).toBe(true);
  });
  
  it('should pass for Date object', async () => {
    const result = await rule.validate(new Date());
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty string', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

describe('futureDate validator', () => {
  const rule = futureDate();
  
  it('should fail for past date', async () => {
    const past = new Date();
    past.setDate(past.getDate() - 1);
    const result = await rule.validate(past);
    expect(result.valid).toBe(false);
  });
  
  it('should pass for future date', async () => {
    const future = new Date();
    future.setDate(future.getDate() + 1);
    const result = await rule.validate(future);
    expect(result.valid).toBe(true);
  });
  
  it('should pass for empty value', async () => {
    const result = await rule.validate('');
    expect(result.valid).toBe(true);
  });
});

describe('pastDate validator', () => {
  const rule = pastDate();
  
  it('should fail for future date', async () => {
    const future = new Date();
    future.setDate(future.getDate() + 1);
    const result = await rule.validate(future);
    expect(result.valid).toBe(false);
  });
  
  it('should pass for past date', async () => {
    const past = new Date();
    past.setDate(past.getDate() - 1);
    const result = await rule.validate(past);
    expect(result.valid).toBe(true);
  });
});

// =============================================================================
// Custom Validator Tests
// =============================================================================

describe('custom validator', () => {
  it('should create working validator', async () => {
    const isEven = custom<number>(
      'even',
      (val) => val % 2 === 0,
      'Must be even'
    );
    
    expect((await isEven.validate(4)).valid).toBe(true);
    expect((await isEven.validate(3)).valid).toBe(false);
  });
  
  it('should support context', async () => {
    const context: ValidationContext = {
      fieldName: 'test',
      values: { other: 'value' },
      touched: {},
      dirty: {},
    };
    
    const hasOther = custom<string>(
      'hasOther',
      (_, ctx) => ctx?.values.other === 'value',
      'Other field must be set'
    );
    
    const result = await hasOther.validate('test', context);
    expect(result.valid).toBe(true);
  });
  
  it('should support custom severity', async () => {
    const warningValidator = custom<number>(
      'highValue',
      (val) => val < 1000,
      'Value is quite high',
      'warning'
    );
    
    const result = await warningValidator.validate(1500);
    expect(result.severity).toBe('warning');
  });
});

// =============================================================================
// Async Validator Tests
// =============================================================================

describe('asyncValidator', () => {
  it('should create async validator', async () => {
    const checkAsync = asyncValidator<string>(
      'asyncCheck',
      async (val) => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return val !== 'taken';
      },
      'Value is already taken'
    );
    
    expect(checkAsync.async).toBe(true);
    expect((await checkAsync.validate('available')).valid).toBe(true);
    expect((await checkAsync.validate('taken')).valid).toBe(false);
  });
});

// =============================================================================
// Conditional Validator Tests
// =============================================================================

describe('when (conditional) validator', () => {
  it('should only run when condition is true', async () => {
    const context: ValidationContext = {
      fieldName: 'email',
      values: { requireEmail: true },
      touched: {},
      dirty: {},
    };
    
    const conditionalRequired = when<string>(
      (ctx) => ctx.values.requireEmail === true,
      required('Email is required when enabled')
    );
    
    expect(conditionalRequired.condition?.(context)).toBe(true);
  });
  
  it('should skip when condition is false', async () => {
    const context: ValidationContext = {
      fieldName: 'email',
      values: { requireEmail: false },
      touched: {},
      dirty: {},
    };
    
    const conditionalRequired = when<string>(
      (ctx) => ctx.values.requireEmail === true,
      required('Email is required')
    );
    
    expect(conditionalRequired.condition?.(context)).toBe(false);
  });
});

// =============================================================================
// Warning Validator Tests
// =============================================================================

describe('warning validator', () => {
  it('should always return valid true', async () => {
    const warningRule = warning<number>(
      'highValue',
      (val) => val < 1000,
      'Consider using a lower value'
    );
    
    // Even when check fails, valid should be true
    const result = await warningRule.validate(1500);
    expect(result.valid).toBe(true);
    expect(result.message).toBe('Consider using a lower value');
    expect(result.severity).toBe('warning');
  });
  
  it('should not show message when condition passes', async () => {
    const warningRule = warning<number>(
      'highValue',
      (val) => val < 1000,
      'Consider using a lower value'
    );
    
    const result = await warningRule.validate(500);
    expect(result.valid).toBe(true);
    expect(result.message).toBeUndefined();
  });
});

// =============================================================================
// Info Validator Tests
// =============================================================================

describe('info validator', () => {
  it('should show info message when condition is true', async () => {
    const infoRule = info<string>(
      'suggestion',
      (val) => val.length > 50,
      'Consider adding more detail'
    );
    
    const result = await infoRule.validate('a'.repeat(60));
    expect(result.valid).toBe(true);
    expect(result.message).toBe('Consider adding more detail');
    expect(result.severity).toBe('info');
  });
});

// =============================================================================
// Utility Function Tests
// =============================================================================

describe('combineResults', () => {
  it('should separate errors, warnings, and infos', () => {
    const results: ValidationResult[] = [
      { valid: false, message: 'Error 1', severity: 'error' },
      { valid: true, message: 'Warning 1', severity: 'warning' },
      { valid: true, message: 'Info 1', severity: 'info' },
      { valid: false, message: 'Error 2', severity: 'error' },
    ];
    
    const combined = combineResults(results);
    
    expect(combined.valid).toBe(false);
    expect(combined.errors).toHaveLength(2);
    expect(combined.warnings).toHaveLength(1);
    expect(combined.infos).toHaveLength(1);
  });
  
  it('should be valid when no errors', () => {
    const results: ValidationResult[] = [
      { valid: true, message: 'Warning', severity: 'warning' },
    ];
    
    const combined = combineResults(results);
    expect(combined.valid).toBe(true);
  });
});

describe('validateField', () => {
  it('should run all rules and collect results', async () => {
    const context: ValidationContext = {
      fieldName: 'test',
      values: {},
      touched: {},
      dirty: {},
    };
    
    const rules = [
      required(),
      minLength(5),
    ];
    
    const results = await validateField('ab', rules, context);
    // Should stop at first error for UX
    expect(results.length).toBeGreaterThanOrEqual(1);
    expect(results[0].valid).toBe(false);
  });
  
  it('should include field name in results', async () => {
    const context: ValidationContext = {
      fieldName: 'username',
      values: {},
      touched: {},
      dirty: {},
    };
    
    const results = await validateField('', [required()], context);
    expect(results[0].field).toBe('username');
  });
});

describe('createFieldValidation', () => {
  it('should create initial field state', () => {
    const field = createFieldValidation();
    
    expect(field.status).toBe('idle');
    expect(field.touched).toBe(false);
    expect(field.dirty).toBe(false);
    expect(field.results).toEqual([]);
  });
});

describe('createFormValidationState', () => {
  it('should create initial form state', () => {
    const form = createFormValidationState();
    
    expect(form.isValid).toBe(true);
    expect(form.isValidating).toBe(false);
    expect(form.isDirty).toBe(false);
    expect(form.submitCount).toBe(0);
  });
  
  it('should accept initial values', () => {
    const form = createFormValidationState({ name: 'John' });
    expect(form.values.name).toBe('John');
  });
});

describe('getSeverityIcon', () => {
  it('should return correct icon names', () => {
    expect(getSeverityIcon('error')).toBe('alert-circle');
    expect(getSeverityIcon('warning')).toBe('alert-triangle');
    expect(getSeverityIcon('info')).toBe('info');
    expect(getSeverityIcon('success')).toBe('check-circle');
  });
});

describe('getSeverityColorClass', () => {
  it('should return color classes', () => {
    expect(getSeverityColorClass('error')).toContain('red');
    expect(getSeverityColorClass('warning')).toContain('amber');
    expect(getSeverityColorClass('info')).toContain('blue');
    expect(getSeverityColorClass('success')).toContain('emerald');
  });
});

describe('getSeverityBackgroundClass', () => {
  it('should return background classes', () => {
    expect(getSeverityBackgroundClass('error')).toContain('bg-red');
    expect(getSeverityBackgroundClass('warning')).toContain('bg-amber');
    expect(getSeverityBackgroundClass('info')).toContain('bg-blue');
    expect(getSeverityBackgroundClass('success')).toContain('bg-emerald');
  });
});

// =============================================================================
// Gate Check Tests
// =============================================================================

describe('requiredFieldsGate', () => {
  const gate = requiredFieldsGate(['name', 'email'], { name: 'Name', email: 'Email' });
  
  it('should pass when all required fields are filled', () => {
    const state = createFormValidationState({ name: 'John', email: 'john@example.com' });
    const result = gate.check(state);
    
    expect(result.passed).toBe(true);
  });
  
  it('should fail when required fields are missing', () => {
    const state = createFormValidationState({ name: 'John' });
    const result = gate.check(state);
    
    expect(result.passed).toBe(false);
    expect(result.details).toContain('Email');
  });
  
  it('should fail for empty strings', () => {
    const state = createFormValidationState({ name: '', email: '' });
    const result = gate.check(state);
    
    expect(result.passed).toBe(false);
    expect(result.details).toHaveLength(2);
  });
});

describe('noErrorsGate', () => {
  it('should pass when no errors', () => {
    const state = createFormValidationState();
    const result = noErrorsGate.check(state);
    
    expect(result.passed).toBe(true);
  });
  
  it('should fail when errors exist', () => {
    const state = createFormValidationState();
    state.errors = [{ valid: false, message: 'Error', severity: 'error' }];
    
    const result = noErrorsGate.check(state);
    expect(result.passed).toBe(false);
  });
});

describe('assumptionsReviewedGate', () => {
  const gate = assumptionsReviewedGate();
  
  it('should pass when no assumptions', () => {
    const state = createFormValidationState();
    const result = gate.check(state);
    
    expect(result.passed).toBe(true);
  });
  
  it('should fail when assumptions not reviewed', () => {
    const state = createFormValidationState({
      assumptions: ['Assumption 1'],
      assumptionsReviewed: false,
    });
    
    const result = gate.check(state);
    expect(result.passed).toBe(false);
  });
  
  it('should pass when assumptions are reviewed', () => {
    const state = createFormValidationState({
      assumptions: ['Assumption 1'],
      assumptionsReviewed: true,
    });
    
    const result = gate.check(state);
    expect(result.passed).toBe(true);
  });
});

describe('approvalsGate', () => {
  const gate = approvalsGate(['manager', 'finance']);
  
  it('should pass when all approvals obtained', () => {
    const state = createFormValidationState({
      approvals: ['manager', 'finance'],
    });
    
    const result = gate.check(state);
    expect(result.passed).toBe(true);
  });
  
  it('should fail when approvals missing', () => {
    const state = createFormValidationState({
      approvals: ['manager'],
    });
    
    const result = gate.check(state);
    expect(result.passed).toBe(false);
    expect(result.details).toContain('finance');
  });
});

describe('runGateChecks', () => {
  it('should run all gate checks', () => {
    const state = createFormValidationState({ name: 'John' });
    const gates = [
      requiredFieldsGate(['name']),
      noErrorsGate,
    ];
    
    const result = runGateChecks(state, gates);
    
    expect(result.canProceed).toBe(true);
    expect(result.checks).toHaveLength(2);
    expect(result.blockers).toHaveLength(0);
  });
  
  it('should identify blockers', () => {
    const state = createFormValidationState();
    const gates = [requiredFieldsGate(['name'])];
    
    const result = runGateChecks(state, gates);
    
    expect(result.canProceed).toBe(false);
    expect(result.blockers.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// Schema Tests
// =============================================================================

describe('createRulesFromSchema', () => {
  it('should create required rule for required field', () => {
    const schema: FieldSchema = {
      name: 'email',
      label: 'Email',
      type: 'email',
      required: true,
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'required')).toBe(true);
    expect(rules.some(r => r.id === 'email')).toBe(true);
  });
  
  it('should create length rules', () => {
    const schema: FieldSchema = {
      name: 'username',
      label: 'Username',
      type: 'text',
      minLength: 3,
      maxLength: 20,
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'minLength')).toBe(true);
    expect(rules.some(r => r.id === 'maxLength')).toBe(true);
  });
  
  it('should create min/max rules for numbers', () => {
    const schema: FieldSchema = {
      name: 'quantity',
      label: 'Quantity',
      type: 'number',
      min: 1,
      max: 100,
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'min')).toBe(true);
    expect(rules.some(r => r.id === 'max')).toBe(true);
  });
  
  it('should create phone rule for phone type', () => {
    const schema: FieldSchema = {
      name: 'phone',
      label: 'Phone',
      type: 'phone',
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'phone')).toBe(true);
  });
  
  it('should create url rule for url type', () => {
    const schema: FieldSchema = {
      name: 'website',
      label: 'Website',
      type: 'url',
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'url')).toBe(true);
  });
  
  it('should create date rule for date type', () => {
    const schema: FieldSchema = {
      name: 'dob',
      label: 'Date of Birth',
      type: 'date',
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'validDate')).toBe(true);
  });
  
  it('should create pattern rule', () => {
    const schema: FieldSchema = {
      name: 'code',
      label: 'Code',
      type: 'text',
      pattern: /^[A-Z]{3}$/,
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'pattern')).toBe(true);
  });
  
  it('should include custom rules', () => {
    const customRule = custom('custom', () => true, 'Custom');
    const schema: FieldSchema = {
      name: 'field',
      label: 'Field',
      type: 'text',
      rules: [customRule],
    };
    
    const rules = createRulesFromSchema(schema);
    expect(rules.some(r => r.id === 'custom')).toBe(true);
  });
});

// =============================================================================
// Debounce Tests
// =============================================================================

describe('debounceValidation', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  it('should debounce validation calls', async () => {
    const mockFn = jest.fn().mockResolvedValue([]);
    const debounced = debounceValidation(mockFn, 100);
    
    // Call multiple times
    debounced();
    debounced();
    debounced();
    
    // Function shouldn't be called yet
    expect(mockFn).not.toHaveBeenCalled();
    
    // Fast forward time
    jest.advanceTimersByTime(100);
    
    // Wait for promise resolution
    await Promise.resolve();
    
    // Should only be called once
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
  
  it('should be cancelable', () => {
    const mockFn = jest.fn().mockResolvedValue([]);
    const debounced = debounceValidation(mockFn, 100);
    
    debounced();
    debounced.cancel();
    
    jest.advanceTimersByTime(100);
    
    expect(mockFn).not.toHaveBeenCalled();
  });
});

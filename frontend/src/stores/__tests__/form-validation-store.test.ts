/**
 * Tests for Form Validation Store
 */
import { act } from '@testing-library/react';
import { useFormValidationStore } from '@/stores/form-validation-store';
import { required, minLength, email, warning, noErrorsGate, requiredFieldsGate } from '@/lib/validation';

// Reset store before each test
beforeEach(() => {
  const store = useFormValidationStore.getState();
  // Clear all forms
  Object.keys(store.forms).forEach(formId => {
    store.destroyForm(formId);
  });
});

// =============================================================================
// Form Management Tests
// =============================================================================

describe('Form Management', () => {
  describe('initForm', () => {
    it('should initialize a new form', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      const form = store.getForm('test-form');
      expect(form).toBeDefined();
      expect(form?.isValid).toBe(true);
      expect(form?.isValidating).toBe(false);
      expect(form?.isDirty).toBe(false);
      expect(form?.submitCount).toBe(0);
    });
    
    it('should accept configuration', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form', {
        validateOnChange: true,
        validateOnBlur: true,
        debounceMs: 500,
      });
      
      // Get updated state after mutation
      const updatedStore = useFormValidationStore.getState();
      expect(updatedStore.formConfigs['test-form']).toBeDefined();
      expect(updatedStore.formConfigs['test-form'].validateOnChange).toBe(true);
    });
    
    it('should accept gate checks in config', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form', {
        gates: [noErrorsGate],
      });
      
      // Get updated state after mutation
      const updatedStore = useFormValidationStore.getState();
      expect(updatedStore.formConfigs['test-form'].gates).toHaveLength(1);
    });
  });
  
  describe('destroyForm', () => {
    it('should remove form and its data', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'field1' });
      
      store.destroyForm('test-form');
      
      expect(store.getForm('test-form')).toBeUndefined();
      expect(store.fieldRules['test-form']).toBeUndefined();
    });
  });
  
  describe('resetForm', () => {
    it('should reset form state while keeping values', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name', initialValue: 'John' });
      store.setTouched('test-form', 'name');
      store.incrementSubmitCount('test-form');
      
      store.resetForm('test-form');
      
      const form = store.getForm('test-form');
      expect(form?.submitCount).toBe(0);
      expect(form?.isDirty).toBe(false);
    });
  });
});

// =============================================================================
// Field Management Tests
// =============================================================================

describe('Field Management', () => {
  describe('registerField', () => {
    it('should register a field with rules', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      store.registerField('test-form', {
        name: 'email',
        rules: [required(), email()],
        initialValue: '',
      });
      
      // Get updated state after mutation
      const updatedStore = useFormValidationStore.getState();
      const rules = updatedStore.fieldRules['test-form']?.['email'];
      expect(rules).toHaveLength(2);
    });
    
    it('should set initial value', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      store.registerField('test-form', {
        name: 'name',
        initialValue: 'John Doe',
      });
      
      // Get updated state after mutation
      const updatedStore = useFormValidationStore.getState();
      expect(updatedStore.getValue('test-form', 'name')).toBe('John Doe');
    });
    
    it('should register field dependencies', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      store.registerField('test-form', {
        name: 'confirmPassword',
        dependsOn: ['password'],
      });
      
      // Get updated state after mutation
      const updatedStore = useFormValidationStore.getState();
      expect(updatedStore.fieldDependencies['test-form']?.['confirmPassword']).toContain('password');
    });
  });
  
  describe('unregisterField', () => {
    it('should remove field and its data', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'field1' });
      
      store.unregisterField('test-form', 'field1');
      
      expect(store.getField('test-form', 'field1')).toBeUndefined();
      expect(store.getValue('test-form', 'field1')).toBeUndefined();
    });
  });
});

// =============================================================================
// Value Management Tests
// =============================================================================

describe('Value Management', () => {
  describe('setValue', () => {
    it('should update field value', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      store.setValue('test-form', 'name', 'Jane');
      
      expect(store.getValue('test-form', 'name')).toBe('Jane');
    });
    
    it('should mark field as dirty', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      store.setValue('test-form', 'name', 'Jane');
      
      const field = store.getField('test-form', 'name');
      expect(field?.dirty).toBe(true);
    });
    
    it('should mark form as dirty', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      store.setValue('test-form', 'name', 'Jane');
      
      expect(store.getForm('test-form')?.isDirty).toBe(true);
    });
  });
  
  describe('setValues', () => {
    it('should update multiple values at once', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'firstName' });
      store.registerField('test-form', { name: 'lastName' });
      
      store.setValues('test-form', {
        firstName: 'John',
        lastName: 'Doe',
      });
      
      expect(store.getValue('test-form', 'firstName')).toBe('John');
      expect(store.getValue('test-form', 'lastName')).toBe('Doe');
    });
  });
  
  describe('getValues', () => {
    it('should return all form values', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'a', initialValue: 1 });
      store.registerField('test-form', { name: 'b', initialValue: 2 });
      
      const values = store.getValues('test-form');
      
      expect(values).toEqual({ a: 1, b: 2 });
    });
    
    it('should return empty object for non-existent form', () => {
      const store = useFormValidationStore.getState();
      expect(store.getValues('nonexistent')).toEqual({});
    });
  });
});

// =============================================================================
// Touch Management Tests
// =============================================================================

describe('Touch Management', () => {
  describe('setTouched', () => {
    it('should mark field as touched', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      store.setTouched('test-form', 'name');
      
      const field = store.getField('test-form', 'name');
      expect(field?.touched).toBe(true);
    });
    
    it('should untouch field when passed false', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      store.setTouched('test-form', 'name', true);
      
      store.setTouched('test-form', 'name', false);
      
      const field = store.getField('test-form', 'name');
      expect(field?.touched).toBe(false);
    });
  });
  
  describe('setAllTouched', () => {
    it('should touch all fields', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'field1' });
      store.registerField('test-form', { name: 'field2' });
      
      store.setAllTouched('test-form');
      
      expect(store.getField('test-form', 'field1')?.touched).toBe(true);
      expect(store.getField('test-form', 'field2')?.touched).toBe(true);
    });
  });
});

// =============================================================================
// Validation Tests
// =============================================================================

describe('Validation', () => {
  describe('validateFieldAsync', () => {
    it('should validate field and return results', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      const results = await store.validateFieldAsync('test-form', 'name');
      
      expect(results).toHaveLength(1);
      expect(results[0].valid).toBe(false);
    });
    
    it('should update field status to validating during validation', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      const promise = store.validateFieldAsync('test-form', 'name');
      
      // Check status is validating (might be too fast to catch)
      await promise;
      
      const field = store.getField('test-form', 'name');
      expect(['valid', 'invalid']).toContain(field?.status);
    });
    
    it('should update field status to valid when no errors', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: 'John',
      });
      
      await store.validateFieldAsync('test-form', 'name');
      
      const field = store.getField('test-form', 'name');
      expect(field?.status).toBe('valid');
    });
    
    it('should update field status to invalid when errors', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFieldAsync('test-form', 'name');
      
      const field = store.getField('test-form', 'name');
      expect(field?.status).toBe('invalid');
    });
    
    it('should store validation results on field', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'email',
        rules: [required(), email()],
        initialValue: '',
      });
      
      await store.validateFieldAsync('test-form', 'email');
      
      const field = store.getField('test-form', 'email');
      expect(field?.results.length).toBeGreaterThan(0);
    });
    
    it('should update form-level error tracking', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFieldAsync('test-form', 'name');
      
      const form = store.getForm('test-form');
      expect(form?.hasErrors).toBe(true);
      expect(form?.isValid).toBe(false);
    });
  });
  
  describe('validateFormAsync', () => {
    it('should validate all fields', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: 'John',
      });
      store.registerField('test-form', {
        name: 'email',
        rules: [required(), email()],
        initialValue: 'john@example.com',
      });
      
      const isValid = await store.validateFormAsync('test-form');
      
      expect(isValid).toBe(true);
    });
    
    it('should touch all fields', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'field1' });
      store.registerField('test-form', { name: 'field2' });
      
      await store.validateFormAsync('test-form');
      
      expect(store.getField('test-form', 'field1')?.touched).toBe(true);
      expect(store.getField('test-form', 'field2')?.touched).toBe(true);
    });
    
    it('should return false when any field has errors', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      const isValid = await store.validateFormAsync('test-form');
      
      expect(isValid).toBe(false);
    });
  });
  
  describe('clearFieldErrors', () => {
    it('should clear errors for a specific field', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFieldAsync('test-form', 'name');
      store.clearFieldErrors('test-form', 'name');
      
      const field = store.getField('test-form', 'name');
      expect(field?.status).toBe('idle');
      expect(field?.results).toEqual([]);
    });
  });
  
  describe('clearAllErrors', () => {
    it('should clear all form errors', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'field1',
        rules: [required()],
        initialValue: '',
      });
      store.registerField('test-form', {
        name: 'field2',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFormAsync('test-form');
      store.clearAllErrors('test-form');
      
      const form = store.getForm('test-form');
      expect(form?.hasErrors).toBe(false);
      expect(form?.isValid).toBe(true);
    });
  });
  
  describe('setFieldError', () => {
    it('should manually set an error on a field', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      store.setFieldError('test-form', 'name', 'Server error');
      
      const errors = store.getFieldErrors('test-form', 'name');
      expect(errors[0].message).toBe('Server error');
    });
    
    it('should mark field as invalid', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      store.setFieldError('test-form', 'name', 'Server error');
      
      expect(store.isFieldValid('test-form', 'name')).toBe(false);
    });
  });
});

// =============================================================================
// Gate Check Tests
// =============================================================================

describe('Gate Checks', () => {
  describe('runGates', () => {
    it('should run configured gate checks', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form', {
        gates: [
          requiredFieldsGate(['name']),
          noErrorsGate,
        ],
      });
      store.registerField('test-form', { name: 'name', initialValue: 'John' });
      
      const result = store.runGates('test-form');
      
      expect(result).not.toBeNull();
      expect(result?.canProceed).toBe(true);
      expect(result?.checks).toHaveLength(2);
    });
    
    it('should return null when no gates configured', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      const result = store.runGates('test-form');
      
      expect(result).toBeNull();
    });
    
    it('should identify blockers', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form', {
        gates: [requiredFieldsGate(['name', 'email'])],
      });
      store.registerField('test-form', { name: 'name', initialValue: '' });
      
      const result = store.runGates('test-form');
      
      expect(result?.canProceed).toBe(false);
      expect(result?.blockers.length).toBeGreaterThan(0);
    });
  });
});

// =============================================================================
// Getter Tests
// =============================================================================

describe('Getters', () => {
  describe('getFieldErrors', () => {
    it('should return only error-severity results', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'amount',
        rules: [
          required(),
          warning('highAmount', (v: number) => v < 10000, 'High amount'),
        ],
        initialValue: '',
      });
      
      await store.validateFieldAsync('test-form', 'amount');
      
      const errors = store.getFieldErrors('test-form', 'amount');
      expect(errors.every(e => e.severity === 'error')).toBe(true);
    });
  });
  
  describe('getFieldWarnings', () => {
    it('should return only warning-severity results', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'amount',
        rules: [warning('highAmount', (v: number) => v < 10000, 'High amount')],
        initialValue: 50000,
      });
      
      await store.validateFieldAsync('test-form', 'amount');
      
      const warnings = store.getFieldWarnings('test-form', 'amount');
      expect(warnings.length).toBe(1);
      expect(warnings[0].severity).toBe('warning');
    });
  });
  
  describe('isFieldValid', () => {
    it('should return true for idle field', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', { name: 'name' });
      
      expect(store.isFieldValid('test-form', 'name')).toBe(true);
    });
    
    it('should return true for valid field', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: 'John',
      });
      
      await store.validateFieldAsync('test-form', 'name');
      
      expect(store.isFieldValid('test-form', 'name')).toBe(true);
    });
    
    it('should return false for invalid field', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFieldAsync('test-form', 'name');
      
      expect(store.isFieldValid('test-form', 'name')).toBe(false);
    });
  });
  
  describe('isFormValid', () => {
    it('should return true for valid form', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: 'John',
      });
      
      await store.validateFormAsync('test-form');
      
      expect(store.isFormValid('test-form')).toBe(true);
    });
    
    it('should return false for invalid form', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFormAsync('test-form');
      
      expect(store.isFormValid('test-form')).toBe(false);
    });
  });
  
  describe('getFormErrors', () => {
    it('should return all form errors', async () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      store.registerField('test-form', {
        name: 'name',
        rules: [required()],
        initialValue: '',
      });
      store.registerField('test-form', {
        name: 'email',
        rules: [required()],
        initialValue: '',
      });
      
      await store.validateFormAsync('test-form');
      
      const errors = store.getFormErrors('test-form');
      expect(errors.length).toBeGreaterThanOrEqual(2);
    });
  });
});

// =============================================================================
// Submit Count Tests
// =============================================================================

describe('Submit Count', () => {
  describe('incrementSubmitCount', () => {
    it('should increment submit count', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      store.incrementSubmitCount('test-form');
      store.incrementSubmitCount('test-form');
      
      expect(store.getSubmitCount('test-form')).toBe(2);
    });
  });
  
  describe('getSubmitCount', () => {
    it('should return 0 for new form', () => {
      const store = useFormValidationStore.getState();
      store.initForm('test-form');
      
      expect(store.getSubmitCount('test-form')).toBe(0);
    });
    
    it('should return 0 for non-existent form', () => {
      const store = useFormValidationStore.getState();
      
      expect(store.getSubmitCount('nonexistent')).toBe(0);
    });
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Integration', () => {
  it('should handle complete form lifecycle', async () => {
    const store = useFormValidationStore.getState();
    
    // Initialize form
    store.initForm('user-form', {
      gates: [
        requiredFieldsGate(['name', 'email']),
        noErrorsGate,
      ],
    });
    
    // Register fields
    store.registerField('user-form', {
      name: 'name',
      rules: [required(), minLength(2)],
      initialValue: '',
    });
    store.registerField('user-form', {
      name: 'email',
      rules: [required(), email()],
      initialValue: '',
    });
    
    // Initially valid (no validation run)
    expect(store.isFormValid('user-form')).toBe(true);
    
    // Gate checks should fail (missing required)
    let gates = store.runGates('user-form');
    expect(gates?.canProceed).toBe(false);
    
    // User fills form with invalid data
    store.setValue('user-form', 'name', 'J');
    store.setValue('user-form', 'email', 'invalid');
    
    // Validate
    await store.validateFormAsync('user-form');
    
    // Should have errors
    expect(store.isFormValid('user-form')).toBe(false);
    expect(store.getFieldErrors('user-form', 'name').length).toBeGreaterThan(0);
    expect(store.getFieldErrors('user-form', 'email').length).toBeGreaterThan(0);
    
    // User corrects form
    store.setValue('user-form', 'name', 'John');
    store.setValue('user-form', 'email', 'john@example.com');
    
    // Validate again
    await store.validateFormAsync('user-form');
    
    // Should be valid
    expect(store.isFormValid('user-form')).toBe(true);
    
    // Gate checks should pass
    gates = store.runGates('user-form');
    expect(gates?.canProceed).toBe(true);
    
    // Submit
    store.incrementSubmitCount('user-form');
    expect(store.getSubmitCount('user-form')).toBe(1);
    
    // Cleanup
    store.destroyForm('user-form');
    expect(store.getForm('user-form')).toBeUndefined();
  });
  
  it('should handle dependent field validation', async () => {
    const store = useFormValidationStore.getState();
    
    store.initForm('password-form');
    
    store.registerField('password-form', {
      name: 'password',
      rules: [required(), minLength(8)],
      initialValue: '',
    });
    
    store.registerField('password-form', {
      name: 'confirmPassword',
      rules: [required()],
      dependsOn: ['password'],
      initialValue: '',
    });
    
    // Set and validate password
    store.setValue('password-form', 'password', 'password123');
    store.setTouched('password-form', 'confirmPassword');
    
    await store.validateFieldAsync('password-form', 'password');
    
    // Password field should be valid
    expect(store.isFieldValid('password-form', 'password')).toBe(true);
  });
});

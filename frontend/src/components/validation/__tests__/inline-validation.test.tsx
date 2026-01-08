/**
 * Tests for Inline Validation Components
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  ValidationMessage,
  ValidationMessages,
  FieldWrapper,
  ValidatedInput,
  ValidatedTextarea,
  ValidatedSelect,
  ValidatedCheckbox,
  GateCheckDisplay,
  FormSummary,
  AutoField,
} from '@/components/validation/inline-validation';
import { useFormValidationStore } from '@/stores/form-validation-store';
import { required, email, minLength, noErrorsGate, requiredFieldsGate } from '@/lib/validation';
import type { GateValidationResult, FieldSchema } from '@/lib/validation';

// Reset store before each test
beforeEach(() => {
  const store = useFormValidationStore.getState();
  Object.keys(store.forms).forEach(formId => {
    store.destroyForm(formId);
  });
});

// =============================================================================
// ValidationMessage Tests
// =============================================================================

describe('ValidationMessage', () => {
  it('should render error message', () => {
    render(<ValidationMessage message="This is required" severity="error" />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('This is required')).toBeInTheDocument();
  });
  
  it('should render warning message', () => {
    render(<ValidationMessage message="Consider this" severity="warning" />);
    
    expect(screen.getByText('Consider this')).toBeInTheDocument();
  });
  
  it('should render info message', () => {
    render(<ValidationMessage message="Helpful tip" severity="info" />);
    
    expect(screen.getByText('Helpful tip')).toBeInTheDocument();
  });
  
  it('should render success message', () => {
    render(<ValidationMessage message="Looks good!" severity="success" />);
    
    expect(screen.getByText('Looks good!')).toBeInTheDocument();
  });
  
  it('should show icon by default', () => {
    render(<ValidationMessage message="Error" severity="error" />);
    
    // SVG icon should be present
    expect(screen.getByRole('alert').querySelector('svg')).toBeInTheDocument();
  });
  
  it('should hide icon when showIcon is false', () => {
    render(<ValidationMessage message="Error" severity="error" showIcon={false} />);
    
    expect(screen.getByRole('alert').querySelector('svg')).not.toBeInTheDocument();
  });
  
  it('should apply custom className', () => {
    render(<ValidationMessage message="Test" severity="error" className="custom-class" />);
    
    expect(screen.getByRole('alert')).toHaveClass('custom-class');
  });
});

// =============================================================================
// ValidationMessages Tests
// =============================================================================

describe('ValidationMessages', () => {
  it('should render multiple messages', () => {
    const results = [
      { valid: false, message: 'Error 1', severity: 'error' as const },
      { valid: false, message: 'Error 2', severity: 'error' as const },
    ];
    
    render(<ValidationMessages results={results} />);
    
    expect(screen.getByText('Error 1')).toBeInTheDocument();
    expect(screen.getByText('Error 2')).toBeInTheDocument();
  });
  
  it('should not render when no results', () => {
    const { container } = render(<ValidationMessages results={[]} />);
    
    expect(container.firstChild).toBeNull();
  });
  
  it('should filter out results without messages', () => {
    const results = [
      { valid: true, severity: 'error' as const },
      { valid: false, message: 'Has message', severity: 'error' as const },
    ];
    
    render(<ValidationMessages results={results} />);
    
    expect(screen.queryAllByRole('alert')).toHaveLength(1);
  });
  
  it('should respect maxMessages prop', () => {
    const results = [
      { valid: false, message: 'Error 1', severity: 'error' as const },
      { valid: false, message: 'Error 2', severity: 'error' as const },
      { valid: false, message: 'Error 3', severity: 'error' as const },
      { valid: false, message: 'Error 4', severity: 'error' as const },
    ];
    
    render(<ValidationMessages results={results} maxMessages={2} />);
    
    expect(screen.getByText('Error 1')).toBeInTheDocument();
    expect(screen.getByText('Error 2')).toBeInTheDocument();
    expect(screen.queryByText('Error 3')).not.toBeInTheDocument();
    expect(screen.getByText(/And 2 more/)).toBeInTheDocument();
  });
});

// =============================================================================
// FieldWrapper Tests
// =============================================================================

describe('FieldWrapper', () => {
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
    store.registerField('test-form', { name: 'testField' });
  });
  
  it('should render label when provided', () => {
    render(
      <FieldWrapper formId="test-form" name="testField" label="Test Label">
        <input />
      </FieldWrapper>
    );
    
    expect(screen.getByText('Test Label')).toBeInTheDocument();
  });
  
  it('should show required indicator', () => {
    render(
      <FieldWrapper formId="test-form" name="testField" label="Field" required>
        <input />
      </FieldWrapper>
    );
    
    expect(screen.getByText('*')).toBeInTheDocument();
  });
  
  it('should show helper text', () => {
    render(
      <FieldWrapper formId="test-form" name="testField" helperText="Help text">
        <input />
      </FieldWrapper>
    );
    
    expect(screen.getByText('Help text')).toBeInTheDocument();
  });
  
  it('should show errors when field is touched and has errors', async () => {
    const store = useFormValidationStore.getState();
    store.registerField('test-form', {
      name: 'errorField',
      rules: [required()],
      initialValue: '',
    });
    store.setTouched('test-form', 'errorField');
    await store.validateFieldAsync('test-form', 'errorField');
    
    render(
      <FieldWrapper formId="test-form" name="errorField">
        <input />
      </FieldWrapper>
    );
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
  
  it('should hide helper text when showing errors', async () => {
    const store = useFormValidationStore.getState();
    store.registerField('test-form', {
      name: 'field',
      rules: [required()],
      initialValue: '',
    });
    store.setTouched('test-form', 'field');
    await store.validateFieldAsync('test-form', 'field');
    
    render(
      <FieldWrapper formId="test-form" name="field" helperText="Help">
        <input />
      </FieldWrapper>
    );
    
    expect(screen.queryByText('Help')).not.toBeInTheDocument();
  });
});

// =============================================================================
// ValidatedInput Tests
// =============================================================================

describe('ValidatedInput', () => {
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
  });
  
  it('should render input with label', () => {
    const store = useFormValidationStore.getState();
    store.registerField('test-form', { name: 'username' });
    
    render(
      <ValidatedInput formId="test-form" name="username" label="Username" />
    );
    
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });
  
  it('should update value on change', async () => {
    const user = userEvent.setup();
    const store = useFormValidationStore.getState();
    store.registerField('test-form', { name: 'name', initialValue: '' });
    
    render(<ValidatedInput formId="test-form" name="name" />);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'John');
    
    expect(store.getValue('test-form', 'name')).toBe('John');
  });
  
  it('should set touched on blur', async () => {
    const user = userEvent.setup();
    const store = useFormValidationStore.getState();
    store.registerField('test-form', { name: 'name' });
    
    render(<ValidatedInput formId="test-form" name="name" />);
    
    const input = screen.getByRole('textbox');
    await user.click(input);
    await user.tab(); // Blur
    
    expect(store.getField('test-form', 'name')?.touched).toBe(true);
  });
  
  it('should show error styling when invalid', async () => {
    const store = useFormValidationStore.getState();
    store.registerField('test-form', {
      name: 'email',
      rules: [required()],
      initialValue: '',
    });
    store.setTouched('test-form', 'email');
    await store.validateFieldAsync('test-form', 'email');
    
    render(<ValidatedInput formId="test-form" name="email" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });
  
  it('should pass through additional props', () => {
    const store = useFormValidationStore.getState();
    store.registerField('test-form', { name: 'field' });
    
    render(
      <ValidatedInput
        formId="test-form"
        name="field"
        placeholder="Enter value"
        disabled
      />
    );
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('placeholder', 'Enter value');
    expect(input).toBeDisabled();
  });
});

// =============================================================================
// ValidatedTextarea Tests
// =============================================================================

describe('ValidatedTextarea', () => {
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
  });
  
  it('should render textarea', () => {
    const store = useFormValidationStore.getState();
    store.registerField('test-form', { name: 'description' });
    
    render(
      <ValidatedTextarea formId="test-form" name="description" label="Description" />
    );
    
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
  
  it('should update value on change', async () => {
    const user = userEvent.setup();
    const store = useFormValidationStore.getState();
    store.registerField('test-form', { name: 'notes', initialValue: '' });
    
    render(<ValidatedTextarea formId="test-form" name="notes" />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Some notes');
    
    expect(store.getValue('test-form', 'notes')).toBe('Some notes');
  });
});

// =============================================================================
// ValidatedSelect Tests
// =============================================================================

describe('ValidatedSelect', () => {
  const options = [
    { value: 'a', label: 'Option A' },
    { value: 'b', label: 'Option B' },
    { value: 'c', label: 'Option C', disabled: true },
  ];
  
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
    store.registerField('test-form', { name: 'choice', initialValue: '' });
  });
  
  it('should render select with options', () => {
    render(
      <ValidatedSelect
        formId="test-form"
        name="choice"
        options={options}
        label="Choice"
      />
    );
    
    expect(screen.getByLabelText('Choice')).toBeInTheDocument();
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('Option B')).toBeInTheDocument();
  });
  
  it('should render placeholder option', () => {
    render(
      <ValidatedSelect
        formId="test-form"
        name="choice"
        options={options}
        placeholder="Select an option"
      />
    );
    
    expect(screen.getByText('Select an option')).toBeInTheDocument();
  });
  
  it('should update value on change', async () => {
    const user = userEvent.setup();
    const store = useFormValidationStore.getState();
    
    render(
      <ValidatedSelect formId="test-form" name="choice" options={options} />
    );
    
    const select = screen.getByRole('combobox');
    await user.selectOptions(select, 'b');
    
    expect(store.getValue('test-form', 'choice')).toBe('b');
  });
  
  it('should render disabled options', () => {
    render(
      <ValidatedSelect formId="test-form" name="choice" options={options} />
    );
    
    const disabledOption = screen.getByText('Option C');
    expect(disabledOption).toBeDisabled();
  });
});

// =============================================================================
// ValidatedCheckbox Tests
// =============================================================================

describe('ValidatedCheckbox', () => {
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
    store.registerField('test-form', { name: 'agree', initialValue: false });
  });
  
  it('should render checkbox with label', () => {
    render(
      <ValidatedCheckbox formId="test-form" name="agree" label="I agree to terms" />
    );
    
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByText('I agree to terms')).toBeInTheDocument();
  });
  
  it('should toggle value on click', async () => {
    const user = userEvent.setup();
    const store = useFormValidationStore.getState();
    
    render(
      <ValidatedCheckbox formId="test-form" name="agree" label="Agree" />
    );
    
    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    
    expect(store.getValue('test-form', 'agree')).toBe(true);
    
    await user.click(checkbox);
    expect(store.getValue('test-form', 'agree')).toBe(false);
  });
  
  it('should show checked state from store', () => {
    const store = useFormValidationStore.getState();
    store.setValue('test-form', 'agree', true);
    
    render(
      <ValidatedCheckbox formId="test-form" name="agree" label="Agree" />
    );
    
    expect(screen.getByRole('checkbox')).toBeChecked();
  });
});

// =============================================================================
// GateCheckDisplay Tests
// =============================================================================

describe('GateCheckDisplay', () => {
  it('should show ready to proceed when can proceed', () => {
    const result: GateValidationResult = {
      canProceed: true,
      checks: [
        {
          id: 'test',
          name: 'Test',
          description: 'Test check',
          severity: 'error',
          blocking: true,
          check: () => ({ passed: true, message: 'Passed' }),
          result: { passed: true, message: 'Passed' },
        },
      ],
      blockers: [],
      warnings: [],
    };
    
    render(<GateCheckDisplay result={result} />);
    
    expect(screen.getByText('Ready to proceed')).toBeInTheDocument();
  });
  
  it('should show blocking issues when cannot proceed', () => {
    const result: GateValidationResult = {
      canProceed: false,
      checks: [
        {
          id: 'test',
          name: 'Required Fields',
          description: 'Test check',
          severity: 'error',
          blocking: true,
          check: () => ({ passed: false, message: 'Missing fields' }),
          result: { passed: false, message: 'Missing fields', details: ['Name', 'Email'] },
        },
      ],
      blockers: ['Missing fields'],
      warnings: [],
    };
    
    render(<GateCheckDisplay result={result} />);
    
    expect(screen.getByText('Blocking issues')).toBeInTheDocument();
    expect(screen.getByText(/Must be resolved/)).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });
  
  it('should show warnings when present', () => {
    const result: GateValidationResult = {
      canProceed: true,
      checks: [
        {
          id: 'warning',
          name: 'High Value',
          description: 'Check value',
          severity: 'warning',
          blocking: false,
          check: () => ({ passed: false, message: 'High value warning' }),
          result: { passed: false, message: 'High value warning' },
        },
      ],
      blockers: [],
      warnings: ['High value warning'],
    };
    
    render(<GateCheckDisplay result={result} />);
    
    expect(screen.getByText(/Warnings/)).toBeInTheDocument();
  });
  
  it('should show passed checks when showAllChecks is true', () => {
    const result: GateValidationResult = {
      canProceed: true,
      checks: [
        {
          id: 'passed',
          name: 'All Good',
          description: 'Check',
          severity: 'error',
          blocking: true,
          check: () => ({ passed: true, message: 'OK' }),
          result: { passed: true, message: 'OK' },
        },
      ],
      blockers: [],
      warnings: [],
    };
    
    render(<GateCheckDisplay result={result} showAllChecks />);
    
    expect(screen.getByText('Passed')).toBeInTheDocument();
    expect(screen.getByText('All Good')).toBeInTheDocument();
  });
  
  it('should accept custom title', () => {
    const result: GateValidationResult = {
      canProceed: true,
      checks: [],
      blockers: [],
      warnings: [],
    };
    
    render(<GateCheckDisplay result={result} title="Custom Title" />);
    
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });
});

// =============================================================================
// FormSummary Tests
// =============================================================================

describe('FormSummary', () => {
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
  });
  
  it('should not render when form is valid and no warnings', () => {
    const { container } = render(<FormSummary formId="test-form" />);
    
    expect(container.firstChild).toBeNull();
  });
  
  it('should render valid state when showWhenValid is true', () => {
    render(<FormSummary formId="test-form" showWhenValid />);
    
    expect(screen.getByText('All fields are valid')).toBeInTheDocument();
  });
  
  it('should show error count and messages', async () => {
    const store = useFormValidationStore.getState();
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
    
    render(<FormSummary formId="test-form" />);
    
    expect(screen.getByText(/2 errors? to fix/)).toBeInTheDocument();
  });
  
  it('should not render for non-existent form', () => {
    const { container } = render(<FormSummary formId="nonexistent" />);
    
    expect(container.firstChild).toBeNull();
  });
});

// =============================================================================
// AutoField Tests
// =============================================================================

describe('AutoField', () => {
  beforeEach(() => {
    const store = useFormValidationStore.getState();
    store.initForm('test-form');
  });
  
  it('should render text input for text type', () => {
    const schema: FieldSchema = {
      name: 'username',
      label: 'Username',
      type: 'text',
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveAttribute('type', 'text');
  });
  
  it('should render email input for email type', () => {
    const schema: FieldSchema = {
      name: 'email',
      label: 'Email',
      type: 'email',
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'email');
  });
  
  it('should render textarea for textarea type', () => {
    const schema: FieldSchema = {
      name: 'description',
      label: 'Description',
      type: 'textarea',
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    expect(screen.getByRole('textbox').tagName).toBe('TEXTAREA');
  });
  
  it('should render select for select type', () => {
    const schema: FieldSchema = {
      name: 'country',
      label: 'Country',
      type: 'select',
      options: [
        { value: 'us', label: 'United States' },
        { value: 'uk', label: 'United Kingdom' },
      ],
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
  });
  
  it('should render checkbox for checkbox type', () => {
    const schema: FieldSchema = {
      name: 'agree',
      label: 'I agree',
      type: 'checkbox',
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });
  
  it('should render number input for number type', () => {
    const schema: FieldSchema = {
      name: 'quantity',
      label: 'Quantity',
      type: 'number',
      min: 1,
      max: 100,
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    const input = screen.getByRole('spinbutton');
    expect(input).toHaveAttribute('type', 'number');
    expect(input).toHaveAttribute('min', '1');
    expect(input).toHaveAttribute('max', '100');
  });
  
  it('should render date input for date type', () => {
    const schema: FieldSchema = {
      name: 'dueDate',
      label: 'Due Date',
      type: 'date',
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    expect(screen.getByLabelText('Due Date')).toHaveAttribute('type', 'date');
  });
  
  it('should register field with rules from schema', async () => {
    const schema: FieldSchema = {
      name: 'testField',
      label: 'Test',
      type: 'text',
      required: true,
      minLength: 3,
    };
    
    render(<AutoField formId="test-form" schema={schema} />);
    
    // Wait for effect to run and re-check updated store
    await waitFor(() => {
      const updatedStore = useFormValidationStore.getState();
      const rules = updatedStore.fieldRules['test-form']?.['testField'];
      expect(rules).toBeDefined();
      expect(rules?.length).toBeGreaterThanOrEqual(2);
    });
  });
  
  it('should unregister field on unmount', async () => {
    const schema: FieldSchema = {
      name: 'tempField',
      label: 'Temp',
      type: 'text',
    };
    
    const { unmount } = render(<AutoField formId="test-form" schema={schema} />);
    
    await waitFor(() => {
      const updatedStore = useFormValidationStore.getState();
      expect(updatedStore.fieldRules['test-form']?.['tempField']).toBeDefined();
    });
    
    unmount();
    
    await waitFor(() => {
      const updatedStore = useFormValidationStore.getState();
      expect(updatedStore.fieldRules['test-form']?.['tempField']).toBeUndefined();
    });
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Integration', () => {
  it('should show validation errors in real-time', async () => {
    const user = userEvent.setup();
    const store = useFormValidationStore.getState();
    
    store.initForm('contact-form', { validateOnBlur: true });
    store.registerField('contact-form', {
      name: 'email',
      rules: [required('Email is required'), email('Invalid email')],
      initialValue: '',
    });
    
    render(
      <ValidatedInput
        formId="contact-form"
        name="email"
        label="Email"
        required
      />
    );
    
    const input = screen.getByRole('textbox');
    
    // Type invalid email
    await user.type(input, 'invalid');
    await user.tab(); // Blur to trigger validation
    
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    
    // Clear and type valid email
    await user.clear(input);
    await user.type(input, 'test@example.com');
    await user.tab();
    
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });
  
  it('should work with form-level validation', async () => {
    const store = useFormValidationStore.getState();
    
    store.initForm('signup-form', {
      gates: [
        requiredFieldsGate(['name', 'email']),
        noErrorsGate,
      ],
    });
    
    store.registerField('signup-form', {
      name: 'name',
      rules: [required()],
      initialValue: 'John',
    });
    
    store.registerField('signup-form', {
      name: 'email',
      rules: [required(), email()],
      initialValue: 'john@example.com',
    });
    
    // Validate form
    const isValid = await store.validateFormAsync('signup-form');
    expect(isValid).toBe(true);
    
    // Run gate checks
    const gateResult = store.runGates('signup-form');
    expect(gateResult?.canProceed).toBe(true);
    
    render(<GateCheckDisplay result={gateResult!} />);
    
    expect(screen.getByText('Ready to proceed')).toBeInTheDocument();
  });
});

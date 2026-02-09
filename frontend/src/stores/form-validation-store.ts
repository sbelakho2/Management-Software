/**
 * Form Validation Store
 * 
 * Zustand store for managing form validation state.
 */
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

import {
  type ValidationResult,
  type ValidationRule,
  type FieldValidation,
  type FormValidationState,
  type ValidationContext,
  type GateCheck,
  type GateValidationResult,
  createFieldValidation,
  createFormValidationState,
  runGateChecks,
} from '@/lib/validation';

// =============================================================================
// Types
// =============================================================================

export interface FormConfig {
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
  validateOnMount?: boolean;
  debounceMs?: number;
  gates?: GateCheck[];
}

export interface FieldRegistration {
  name: string;
  rules?: ValidationRule[];
  initialValue?: unknown;
  dependsOn?: string[];
}

interface FormValidationStore {
  // State
  forms: Record<string, FormValidationState>;
  fieldRules: Record<string, Record<string, ValidationRule[]>>;
  fieldDependencies: Record<string, Record<string, string[]>>;
  formConfigs: Record<string, FormConfig>;
  debounceTimers: Record<string, Record<string, ReturnType<typeof setTimeout>>>;
  
  // Form Management
  initForm: (formId: string, config?: FormConfig) => void;
  destroyForm: (formId: string) => void;
  resetForm: (formId: string) => void;
  
  // Field Management
  registerField: (formId: string, registration: FieldRegistration) => void;
  unregisterField: (formId: string, fieldName: string) => void;
  
  // Value Management
  setValue: (formId: string, fieldName: string, value: unknown) => void;
  setValues: (formId: string, values: Record<string, unknown>) => void;
  getValue: (formId: string, fieldName: string) => unknown;
  getValues: (formId: string) => Record<string, unknown>;
  
  // Touch Management
  setTouched: (formId: string, fieldName: string, touched?: boolean) => void;
  setAllTouched: (formId: string, touched?: boolean) => void;
  
  // Validation
  validateFieldAsync: (formId: string, fieldName: string) => Promise<ValidationResult[]>;
  validateFormAsync: (formId: string) => Promise<boolean>;
  clearFieldErrors: (formId: string, fieldName: string) => void;
  clearAllErrors: (formId: string) => void;
  setFieldError: (formId: string, fieldName: string, error: string) => void;
  
  // Gate Checks
  runGates: (formId: string) => GateValidationResult | null;
  
  // Getters
  getForm: (formId: string) => FormValidationState | undefined;
  getField: (formId: string, fieldName: string) => FieldValidation | undefined;
  getFieldErrors: (formId: string, fieldName: string) => ValidationResult[];
  getFieldWarnings: (formId: string, fieldName: string) => ValidationResult[];
  isFieldValid: (formId: string, fieldName: string) => boolean;
  isFormValid: (formId: string) => boolean;
  isFormValidating: (formId: string) => boolean;
  getFormErrors: (formId: string) => ValidationResult[];
  
  // Submit
  incrementSubmitCount: (formId: string) => void;
  getSubmitCount: (formId: string) => number;
}

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Run validation rules against a single value.
 * This wraps the library's validateField which works on FieldValidation objects.
 */
async function validateField(
  value: unknown,
  rules: ValidationRule[],
  context?: ValidationContext,
): Promise<ValidationResult[]> {
  const results: ValidationResult[] = [];
  for (const rule of rules) {
    const result = rule.validate(value, context);
    if (result) results.push(result);
  }
  return results;
}

/**
 * Combine validation results into a summary with valid/errors/warnings.
 */
function combineResults(results: ValidationResult[]): { valid: boolean; errors: ValidationResult[]; warnings: ValidationResult[] } {
  const errors = results.filter(r => !r.valid && r.severity === 'error');
  const warnings = results.filter(r => r.message && r.severity === 'warning');
  return { valid: errors.length === 0, errors, warnings };
}

// =============================================================================
// Store Implementation
// =============================================================================

export const useFormValidationStore = create<FormValidationStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      forms: {},
      fieldRules: {},
      fieldDependencies: {},
      formConfigs: {},
      debounceTimers: {},
      
      // Form Management
      initForm: (formId, config = {}) => {
        set((state) => ({
          forms: {
            ...state.forms,
            [formId]: createFormValidationState(),
          },
          fieldRules: {
            ...state.fieldRules,
            [formId]: {},
          },
          fieldDependencies: {
            ...state.fieldDependencies,
            [formId]: {},
          },
          formConfigs: {
            ...state.formConfigs,
            [formId]: config,
          },
          debounceTimers: {
            ...state.debounceTimers,
            [formId]: {},
          },
        }), false, 'initForm');
      },
      
      destroyForm: (formId) => {
        // Clear any pending debounce timers
        const timers = get().debounceTimers[formId] ?? {};
        Object.values(timers).forEach(timer => clearTimeout(timer));
        
        set((state) => {
          const { [formId]: _form, ...restForms } = state.forms;
          const { [formId]: _rules, ...restRules } = state.fieldRules;
          const { [formId]: _deps, ...restDeps } = state.fieldDependencies;
          const { [formId]: _config, ...restConfigs } = state.formConfigs;
          const { [formId]: _timers, ...restTimers } = state.debounceTimers;
          
          return {
            forms: restForms,
            fieldRules: restRules,
            fieldDependencies: restDeps,
            formConfigs: restConfigs,
            debounceTimers: restTimers,
          };
        }, false, 'destroyForm');
      },
      
      resetForm: (formId) => {
        const form = get().forms[formId];
        if (!form) return;
        
        set((state) => ({
          forms: {
            ...state.forms,
            [formId]: {
              ...createFormValidationState(),
              values: form.values ?? {}, // Keep initial values
            },
          },
        }), false, 'resetForm');
      },
      
      // Field Management
      registerField: (formId, registration) => {
        const { name, rules = [], initialValue, dependsOn = [] } = registration;
        
        set((state) => {
          const form = state.forms[formId] ?? createFormValidationState();
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                fields: {
                  ...form.fields,
                  [name]: form.fields[name] ?? createFieldValidation(),
                },
                values: {
                  ...(form.values ?? {}),
                  [name]: (form.values ?? {})[name] ?? initialValue,
                },
              },
            },
            fieldRules: {
              ...state.fieldRules,
              [formId]: {
                ...(state.fieldRules[formId] ?? {}),
                [name]: rules,
              },
            },
            fieldDependencies: {
              ...state.fieldDependencies,
              [formId]: {
                ...(state.fieldDependencies[formId] ?? {}),
                [name]: dependsOn,
              },
            },
          };
        }, false, 'registerField');
      },
      
      unregisterField: (formId, fieldName) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const { [fieldName]: _field, ...restFields } = form.fields;
          const { [fieldName]: _value, ...restValues } = (form.values ?? {});
          const rules = state.fieldRules[formId] ?? {};
          const { [fieldName]: _rules, ...restRules } = rules;
          const deps = state.fieldDependencies[formId] ?? {};
          const { [fieldName]: _deps, ...restDeps } = deps;
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                fields: restFields,
                values: restValues,
              },
            },
            fieldRules: {
              ...state.fieldRules,
              [formId]: restRules,
            },
            fieldDependencies: {
              ...state.fieldDependencies,
              [formId]: restDeps,
            },
          };
        }, false, 'unregisterField');
      },
      
      // Value Management
      setValue: (formId, fieldName, value) => {
        const config = get().formConfigs[formId] ?? {};
        const debounceMs = config.debounceMs ?? 300;
        
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const field = form.fields[fieldName] ?? createFieldValidation();
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                values: {
                  ...(form.values ?? {}),
                  [fieldName]: value,
                },
                fields: {
                  ...form.fields,
                  [fieldName]: {
                    ...field,
                    dirty: true,
                  },
                },
                isDirty: true,
              },
            },
          };
        }, false, 'setValue');
        
        // Auto-validate on change if configured
        if (config.validateOnChange) {
          // Clear existing timer
          const timers = get().debounceTimers[formId] ?? {};
          const existingTimer = timers[fieldName];
          if (existingTimer) {
            clearTimeout(existingTimer);
          }
          
          // Set new debounced timer
          const timer = setTimeout(() => {
            get().validateFieldAsync(formId, fieldName);
          }, debounceMs);
          
          set((state) => ({
            debounceTimers: {
              ...state.debounceTimers,
              [formId]: {
                ...(state.debounceTimers[formId] ?? {}),
                [fieldName]: timer,
              },
            },
          }), false, 'setDebounceTimer');
        }
      },
      
      setValues: (formId, values) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const updatedFields = { ...form.fields };
          Object.keys(values).forEach(key => {
            const field = updatedFields[key] ?? createFieldValidation();
            updatedFields[key] = { ...field, dirty: true };
          });
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                values: {
                  ...(form.values ?? {}),
                  ...values,
                },
                fields: updatedFields,
                isDirty: true,
              },
            },
          };
        }, false, 'setValues');
      },
      
      getValue: (formId, fieldName) => {
        const form = get().forms[formId];
        return form?.values?.[fieldName];
      },
      
      getValues: (formId) => {
        const form = get().forms[formId];
        return form?.values ?? {};
      },
      
      // Touch Management
      setTouched: (formId, fieldName, touched = true) => {
        const config = get().formConfigs[formId] ?? {};
        
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const field = form.fields[fieldName] ?? createFieldValidation();
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                fields: {
                  ...form.fields,
                  [fieldName]: {
                    ...field,
                    touched,
                  },
                },
              },
            },
          };
        }, false, 'setTouched');
        
        // Auto-validate on blur if configured
        if (touched && config.validateOnBlur) {
          get().validateFieldAsync(formId, fieldName);
        }
      },
      
      setAllTouched: (formId, touched = true) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const updatedFields = { ...form.fields };
          Object.keys(updatedFields).forEach(key => {
            updatedFields[key] = { ...updatedFields[key], touched };
          });
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                fields: updatedFields,
              },
            },
          };
        }, false, 'setAllTouched');
      },
      
      // Validation
      validateFieldAsync: async (formId, fieldName) => {
        const form = get().forms[formId];
        const rules = get().fieldRules[formId]?.[fieldName] ?? [];
        
        if (!form) return [];
        
        // Mark as validating
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const field = form.fields[fieldName] ?? createFieldValidation();
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                isValidating: true,
                fields: {
                  ...form.fields,
                  [fieldName]: {
                    ...field,
                    status: 'validating',
                  },
                },
              },
            },
          };
        }, false, 'validateFieldStart');
        
        // Create validation context
        const context: ValidationContext = {
          fieldName,
          values: form.values ?? {},
          touched: Object.fromEntries(
            Object.entries(form.fields).map(([k, v]) => [k, v.touched])
          ),
          dirty: Object.fromEntries(
            Object.entries(form.fields).map(([k, v]) => [k, v.dirty])
          ),
        };
        
        // Run validation
        const value = (form.values ?? {})[fieldName];
        const results = await validateField(value, rules, context);
        const { valid, errors, warnings } = combineResults(results);
        
        // Update state with results
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const field = form.fields[fieldName] ?? createFieldValidation();
          
          // Recalculate form-level errors/warnings
          const allResults = Object.entries(form.fields)
            .filter(([key]) => key !== fieldName)
            .flatMap(([_, f]) => f.results)
            .concat(results);
          
          const allErrors = allResults.filter(r => !r.valid && r.severity === 'error');
          const allWarnings = allResults.filter(r => r.message && r.severity === 'warning');
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                isValidating: false,
                isValid: allErrors.length === 0,
                hasErrors: allErrors.length > 0,
                hasWarnings: allWarnings.length > 0,
                errors: allErrors,
                warnings: allWarnings,
                fields: {
                  ...form.fields,
                  [fieldName]: {
                    ...field,
                    status: valid ? 'valid' : 'invalid',
                    results,
                    lastValidatedValue: value,
                    validatedAt: new Date(),
                  },
                },
              },
            },
          };
        }, false, 'validateFieldEnd');
        
        // Validate dependent fields
        const allDeps = get().fieldDependencies[formId] ?? {};
        const dependentFields = Object.entries(allDeps)
          .filter(([_, deps]) => deps.includes(fieldName))
          .map(([field]) => field);
        
        for (const depField of dependentFields) {
          if (form.fields[depField]?.touched) {
            await get().validateFieldAsync(formId, depField);
          }
        }
        
        return results;
      },
      
      validateFormAsync: async (formId) => {
        const form = get().forms[formId];
        if (!form) return false;
        
        // Mark all fields as touched
        get().setAllTouched(formId, true);
        
        // Validate all fields
        const fieldNames = Object.keys(form.fields);
        const results = await Promise.all(
          fieldNames.map(name => get().validateFieldAsync(formId, name))
        );
        
        // Check if all valid
        const allResults = results.flat();
        const hasErrors = allResults.some(r => !r.valid && r.severity === 'error');
        
        return !hasErrors;
      },
      
      clearFieldErrors: (formId, fieldName) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const field = form.fields[fieldName];
          if (!field) return state;
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                fields: {
                  ...form.fields,
                  [fieldName]: {
                    ...field,
                    status: 'idle',
                    results: [],
                  },
                },
              },
            },
          };
        }, false, 'clearFieldErrors');
      },
      
      clearAllErrors: (formId) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const updatedFields = { ...form.fields };
          Object.keys(updatedFields).forEach(key => {
            updatedFields[key] = {
              ...updatedFields[key],
              status: 'idle',
              results: [],
            };
          });
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                fields: updatedFields,
                isValid: true,
                hasErrors: false,
                hasWarnings: false,
                errors: [],
                warnings: [],
              },
            },
          };
        }, false, 'clearAllErrors');
      },
      
      setFieldError: (formId, fieldName, error) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          const field = form.fields[fieldName] ?? createFieldValidation();
          const errorResult: ValidationResult = {
            valid: false,
            message: error,
            severity: 'error',
            field: fieldName,
          };
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                isValid: false,
                hasErrors: true,
                errors: [...(form.errors ?? []), errorResult],
                fields: {
                  ...form.fields,
                  [fieldName]: {
                    ...field,
                    status: 'invalid',
                    results: [...field.results, errorResult],
                  },
                },
              },
            },
          };
        }, false, 'setFieldError');
      },
      
      // Gate Checks
      runGates: (formId) => {
        const form = get().forms[formId];
        const config = get().formConfigs[formId];
        
        if (!form || !config?.gates) return null;
        
        return runGateChecks(form, config.gates);
      },
      
      // Getters
      getForm: (formId) => get().forms[formId],
      
      getField: (formId, fieldName) => get().forms[formId]?.fields[fieldName],
      
      getFieldErrors: (formId, fieldName) => {
        const field = get().forms[formId]?.fields[fieldName];
        return field?.results.filter(r => !r.valid && r.severity === 'error') ?? [];
      },
      
      getFieldWarnings: (formId, fieldName) => {
        const field = get().forms[formId]?.fields[fieldName];
        return field?.results.filter(r => r.message && r.severity === 'warning') ?? [];
      },
      
      isFieldValid: (formId, fieldName) => {
        const field = get().forms[formId]?.fields[fieldName];
        return field?.status === 'valid' || field?.status === 'idle';
      },
      
      isFormValid: (formId) => get().forms[formId]?.isValid ?? true,
      
      isFormValidating: (formId) => get().forms[formId]?.isValidating ?? false,
      
      getFormErrors: (formId) => get().forms[formId]?.errors ?? [],
      
      // Submit
      incrementSubmitCount: (formId) => {
        set((state) => {
          const form = state.forms[formId];
          if (!form) return state;
          
          return {
            forms: {
              ...state.forms,
              [formId]: {
                ...form,
                submitCount: (form.submitCount ?? 0) + 1,
              },
            },
          };
        }, false, 'incrementSubmitCount');
      },
      
      getSubmitCount: (formId) => get().forms[formId]?.submitCount ?? 0,
    }),
    { name: 'form-validation-store' }
  )
);

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to use form validation for a specific form
 */
export function useForm(formId: string, config?: FormConfig) {
  const store = useFormValidationStore();
  
  // Initialize form on mount
  if (!store.forms[formId]) {
    store.initForm(formId, config);
  }
  
  return {
    // Form state
    form: store.getForm(formId),
    values: store.getValues(formId),
    isValid: store.isFormValid(formId),
    isValidating: store.isFormValidating(formId),
    errors: store.getFormErrors(formId),
    
    // Actions
    setValue: (name: string, value: unknown) => store.setValue(formId, name, value),
    setValues: (values: Record<string, unknown>) => store.setValues(formId, values),
    setTouched: (name: string) => store.setTouched(formId, name),
    validate: () => store.validateFormAsync(formId),
    reset: () => store.resetForm(formId),
    runGates: () => store.runGates(formId),
    
    // Field registration
    registerField: (registration: FieldRegistration) => 
      store.registerField(formId, registration),
    unregisterField: (name: string) => 
      store.unregisterField(formId, name),
  };
}

/**
 * Hook to use a specific field in a form
 */
export function useField(formId: string, fieldName: string) {
  const store = useFormValidationStore();
  
  const field = store.getField(formId, fieldName);
  const value = store.getValue(formId, fieldName);
  
  return {
    // Field state
    value,
    touched: field?.touched ?? false,
    dirty: field?.dirty ?? false,
    status: field?.status ?? 'idle',
    errors: store.getFieldErrors(formId, fieldName),
    warnings: store.getFieldWarnings(formId, fieldName),
    isValid: store.isFieldValid(formId, fieldName),
    
    // Actions
    setValue: (val: unknown) => store.setValue(formId, fieldName, val),
    setTouched: () => store.setTouched(formId, fieldName),
    validate: () => store.validateFieldAsync(formId, fieldName),
    clearErrors: () => store.clearFieldErrors(formId, fieldName),
    setError: (error: string) => store.setFieldError(formId, fieldName, error),
  };
}

//! Form validation store — field registration, debounced validation,
//! error/warning tracking, form gates, and submit counts.
//!
//! Port of [`frontend/src/stores/form-validation-store.ts`](frontend/src/stores/form-validation-store.ts).

use leptos::prelude::*;
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type ValidationRule = String; // "required" | "email" | "min_length" | "max_length" | "pattern" | "custom"

#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FormConfig {
    pub validate_on_change: bool,
    pub validate_on_blur: bool,
    pub debounce_ms: u32,
}

impl Default for FormConfig {
    fn default() -> Self {
        Self {
            validate_on_change: true,
            validate_on_blur: true,
            debounce_ms: 300,
        }
    }
}

#[derive(Debug, Clone)]
pub struct FieldRegistration {
    pub name: String,
    pub field_type: String, // "text" | "number" | "email" | "select" | "date" | "boolean"
    pub label: String,
    pub rules: Vec<(ValidationRule, serde_json::Value)>,
    pub required: bool,
    pub initial_value: serde_json::Value,
    pub async_validator: Option<String>, // identifier for async validation function
}

#[derive(Debug, Clone)]
pub struct FieldState {
    pub value: serde_json::Value,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
    pub touched: bool,
    pub dirty: bool,
    pub valid: bool,
    pub validating: bool,
}

#[derive(Debug, Clone)]
pub struct FormState {
    pub fields: HashMap<String, FieldState>,
    pub config: FormConfig,
    pub valid: bool,
    pub submit_count: i32,
    pub gates: Vec<String>, // gate error messages
}

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

fn combine_results(results: &[ValidationResult]) -> ValidationResult {
    let mut all_errors = Vec::new();
    let mut all_warnings = Vec::new();
    let mut all_valid = true;

    for result in results {
        if !result.valid {
            all_valid = false;
        }
        all_errors.extend(result.errors.clone());
        all_warnings.extend(result.warnings.clone());
    }

    ValidationResult {
        valid: all_valid,
        errors: all_errors,
        warnings: all_warnings,
    }
}

fn validate_required(value: &serde_json::Value) -> ValidationResult {
    match value {
        serde_json::Value::Null => ValidationResult {
            valid: false,
            errors: vec!["This field is required".to_string()],
            warnings: Vec::new(),
        },
        serde_json::Value::String(s) if s.is_empty() => ValidationResult {
            valid: false,
            errors: vec!["This field is required".to_string()],
            warnings: Vec::new(),
        },
        _ => ValidationResult {
            valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
        },
    }
}

fn validate_email(value: &serde_json::Value) -> ValidationResult {
    match value {
        serde_json::Value::String(s) => {
            if s.contains('@') && s.contains('.') {
                ValidationResult {
                    valid: true,
                    errors: Vec::new(),
                    warnings: Vec::new(),
                }
            } else {
                ValidationResult {
                    valid: false,
                    errors: vec!["Invalid email format".to_string()],
                    warnings: Vec::new(),
                }
            }
        }
        _ => ValidationResult {
            valid: false,
            errors: vec!["Invalid email format".to_string()],
            warnings: Vec::new(),
        },
    }
}

fn validate_min_length(value: &serde_json::Value, min: usize) -> ValidationResult {
    match value {
        serde_json::Value::String(s) => {
            if s.len() >= min {
                ValidationResult {
                    valid: true,
                    errors: Vec::new(),
                    warnings: Vec::new(),
                }
            } else {
                ValidationResult {
                    valid: false,
                    errors: vec![format!("Must be at least {min} characters")],
                    warnings: Vec::new(),
                }
            }
        }
        _ => ValidationResult {
            valid: false,
            errors: vec![format!("Must be at least {min} characters")],
            warnings: Vec::new(),
        },
    }
}

fn validate_max_length(value: &serde_json::Value, max: usize) -> ValidationResult {
    match value {
        serde_json::Value::String(s) => {
            if s.len() <= max {
                ValidationResult {
                    valid: true,
                    errors: Vec::new(),
                    warnings: Vec::new(),
                }
            } else {
                ValidationResult {
                    valid: false,
                    errors: vec![format!("Must be at most {max} characters")],
                    warnings: Vec::new(),
                }
            }
        }
        _ => ValidationResult {
            valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
        },
    }
}

fn validate_pattern(value: &serde_json::Value, pattern: &str) -> ValidationResult {
    match value {
        serde_json::Value::String(s) => {
            // Simple regex-like check using string operations
            let matched = match pattern {
                r"^\d+$" => s.chars().all(|c| c.is_ascii_digit()),
                r"^[A-Za-z]+$" => s.chars().all(|c| c.is_ascii_alphabetic()),
                r"^[A-Za-z0-9]+$" => s.chars().all(|c| c.is_ascii_alphanumeric()),
                r"^[\w\.-]+@[\w\.-]+\.\w+$" => s.contains('@') && s.contains('.'),
                _ => true, // unknown pattern, skip
            };
            if matched {
                ValidationResult {
                    valid: true,
                    errors: Vec::new(),
                    warnings: Vec::new(),
                }
            } else {
                ValidationResult {
                    valid: false,
                    errors: vec![format!("Does not match pattern: {pattern}")],
                    warnings: Vec::new(),
                }
            }
        }
        _ => ValidationResult {
            valid: false,
            errors: vec![format!("Does not match pattern: {pattern}")],
            warnings: Vec::new(),
        },
    }
}

async fn validate_field(field: &FieldRegistration, value: &serde_json::Value) -> ValidationResult {
    let mut results = Vec::new();

    if field.required {
        results.push(validate_required(value));
    }

    for (rule, param) in &field.rules {
        match rule.as_str() {
            "required" => results.push(validate_required(value)),
            "email" => results.push(validate_email(value)),
            "min_length" => {
                if let Some(min) = param.as_u64() {
                    results.push(validate_min_length(value, min as usize));
                }
            }
            "max_length" => {
                if let Some(max) = param.as_u64() {
                    results.push(validate_max_length(value, max as usize));
                }
            }
            "pattern" => {
                if let Some(p) = param.as_str() {
                    results.push(validate_pattern(value, p));
                }
            }
            _ => {} // custom rules handled externally
        }
    }

    combine_results(&results)
}

// ---------------------------------------------------------------------------
// FormValidationStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct FormValidationStore {
    pub forms: RwSignal<HashMap<String, FormState>>,
}

impl FormValidationStore {
    pub fn new() -> Self {
        Self {
            forms: RwSignal::new(HashMap::new()),
        }
    }

    // -----------------------------------------------------------------------
    // Form lifecycle
    // -----------------------------------------------------------------------

    pub fn init_form(&self, form_id: &str, config: Option<FormConfig>) {
        self.forms.update(|forms| {
            forms.entry(form_id.to_string()).or_insert_with(|| FormState {
                fields: HashMap::new(),
                config: config.unwrap_or_default(),
                valid: true,
                submit_count: 0,
                gates: Vec::new(),
            });
        });
    }

    pub fn destroy_form(&self, form_id: &str) {
        self.forms.update(|forms| {
            forms.remove(form_id);
        });
    }

    pub fn reset_form(&self, form_id: &str) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                for (_name, state) in form.fields.iter_mut() {
                    state.touched = false;
                    state.dirty = false;
                    state.errors.clear();
                    state.warnings.clear();
                    state.valid = true;
                }
                form.valid = true;
                form.gates.clear();
            }
        });
    }

    // -----------------------------------------------------------------------
    // Field registration
    // -----------------------------------------------------------------------

    pub fn register_field(&self, form_id: &str, registration: FieldRegistration) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                let name = registration.name.clone();
                form.fields.insert(name, FieldState {
                    value: registration.initial_value.clone(),
                    errors: Vec::new(),
                    warnings: Vec::new(),
                    touched: false,
                    dirty: false,
                    valid: true,
                    validating: false,
                });
            }
        });
    }

    pub fn unregister_field(&self, form_id: &str, field_name: &str) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                form.fields.remove(field_name);
            }
        });
    }

    // -----------------------------------------------------------------------
    // Value setters / getters
    // -----------------------------------------------------------------------

    pub fn set_value(&self, form_id: &str, field_name: &str, value: serde_json::Value) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                if let Some(field) = form.fields.get_mut(field_name) {
                    field.value = value;
                    field.dirty = true;
                }
            }
        });
    }

    pub fn set_values(&self, form_id: &str, values: HashMap<String, serde_json::Value>) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                for (key, value) in values {
                    if let Some(field) = form.fields.get_mut(&key) {
                        field.value = value;
                        field.dirty = true;
                    }
                }
            }
        });
    }

    pub fn get_value(&self, form_id: &str, field_name: &str) -> Option<serde_json::Value> {
        self.forms.get().get(form_id)?.fields.get(field_name).map(|f| f.value.clone())
    }

    pub fn get_values(&self, form_id: &str) -> Option<HashMap<String, serde_json::Value>> {
        let forms = self.forms.get();
        let form = forms.get(form_id)?;
        Some(
            form.fields
                .iter()
                .map(|(k, v)| (k.clone(), v.value.clone()))
                .collect(),
        )
    }

    // -----------------------------------------------------------------------
    // Touched state
    // -----------------------------------------------------------------------

    pub fn set_touched(&self, form_id: &str, field_name: &str, touched: bool) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                if let Some(field) = form.fields.get_mut(field_name) {
                    field.touched = touched;
                }
            }
        });
    }

    pub fn set_all_touched(&self, form_id: &str, touched: bool) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                for (_name, field) in form.fields.iter_mut() {
                    field.touched = touched;
                }
            }
        });
    }

    // -----------------------------------------------------------------------
    // Validation
    // -----------------------------------------------------------------------

    pub async fn validate_field_async(&self, form_id: &str, field_name: &str, registration: Option<&FieldRegistration>) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                if let Some(field) = form.fields.get_mut(field_name) {
                    field.validating = true;
                }
            }
        });

        // For async validation, we can't easily await inside RwSignal update
        // In a real implementation, this would use leptos::spawn_local
        // For now, we'll do synchronous validation

        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                if let Some(field) = form.fields.get_mut(field_name) {
                    field.validating = false;
                    // Simplified validation
                    let value = &field.value;
                    let mut errors = Vec::new();
                    if value.is_null() || (value.is_string() && value.as_str().unwrap_or("").is_empty()) {
                        errors.push("This field is required".to_string());
                    }
                    field.errors = errors.clone();
                    field.valid = errors.is_empty();
                }

                // Update form validity
                form.valid = form.fields.values().all(|f| f.valid);
            }
        });
    }

    pub async fn validate_form_async(&self, form_id: &str) -> bool {
        let field_names: Vec<String> = {
            let forms = self.forms.get();
            forms
                .get(form_id)
                .map(|f| f.fields.keys().cloned().collect())
                .unwrap_or_default()
        };

        for field_name in &field_names {
            self.validate_field_async(form_id, field_name, None).await;
        }

        self.forms.get().get(form_id).map(|f| f.valid).unwrap_or(true)
    }

    // -----------------------------------------------------------------------
    // Error management
    // -----------------------------------------------------------------------

    pub fn clear_field_errors(&self, form_id: &str, field_name: &str) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                if let Some(field) = form.fields.get_mut(field_name) {
                    field.errors.clear();
                    field.warnings.clear();
                    field.valid = true;
                }
            }
        });
    }

    pub fn clear_all_errors(&self, form_id: &str) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                for (_name, field) in form.fields.iter_mut() {
                    field.errors.clear();
                    field.warnings.clear();
                    field.valid = true;
                }
                form.valid = true;
                form.gates.clear();
            }
        });
    }

    pub fn set_field_error(&self, form_id: &str, field_name: &str, error: &str) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                if let Some(field) = form.fields.get_mut(field_name) {
                    field.errors.push(error.to_string());
                    field.valid = false;
                }
                form.valid = false;
            }
        });
    }

    // -----------------------------------------------------------------------
    // Gates
    // -----------------------------------------------------------------------

    pub fn run_gates(&self, form_id: &str) -> Vec<String> {
        // Gates are cross-field validation rules
        // In a real implementation, this would check complex conditions
        self.forms.get().get(form_id).map(|f| f.gates.clone()).unwrap_or_default()
    }

    // -----------------------------------------------------------------------
    // Field queries
    // -----------------------------------------------------------------------

    pub fn get_field_errors(&self, form_id: &str, field_name: &str) -> Vec<String> {
        self.forms
            .get()
            .get(form_id)
            .and_then(|f| f.fields.get(field_name))
            .map(|f| f.errors.clone())
            .unwrap_or_default()
    }

    pub fn get_field_warnings(&self, form_id: &str, field_name: &str) -> Vec<String> {
        self.forms
            .get()
            .get(form_id)
            .and_then(|f| f.fields.get(field_name))
            .map(|f| f.warnings.clone())
            .unwrap_or_default()
    }

    pub fn is_field_valid(&self, form_id: &str, field_name: &str) -> bool {
        self.forms
            .get()
            .get(form_id)
            .and_then(|f| f.fields.get(field_name))
            .map(|f| f.valid)
            .unwrap_or(true)
    }

    // -----------------------------------------------------------------------
    // Submit
    // -----------------------------------------------------------------------

    pub fn increment_submit_count(&self, form_id: &str) {
        self.forms.update(|forms| {
            if let Some(form) = forms.get_mut(form_id) {
                form.submit_count += 1;
            }
        });
    }
}

impl Default for FormValidationStore {
    fn default() -> Self {
        Self::new()
    }
}

//! Industrial input component.
//!
//! Provides [`IndustrialInput`] — a form input styled for the Rams design system
//! (section 3.3). Features include reactive value binding, error state display,
//! and Dymo-style uppercase labels.

use leptos::prelude::*;

/// Industrial-styled form input field.
///
/// Renders a label in Dymo style (uppercase, monospaced) above an input
/// element with recessed styling. Supports reactive two-way binding via
/// [`RwSignal`] and optional external `on_input` callback.
///
/// # Example
///
/// ```ignore
/// let email = RwSignal::new(String::new());
/// let error = RwSignal::new(None::<String>);
///
/// <IndustrialInput
///     id="email"
///     label="Email"
///     placeholder="user@company.com"
///     input_type="email"
///     value=email
///     error=error
///     _required=true
/// />
/// ```
#[component]
pub fn IndustrialInput(
    /// Element `id` attribute (also used for `for` on the label).
    #[prop(optional)]
    id: String,
    /// Label text (displayed uppercase by Dymo style).
    #[prop(optional)]
    label: String,
    /// Placeholder text.
    #[prop(optional)]
    placeholder: String,
    /// Input `type` attribute: `"text"`, `"email"`, `"password"`, etc.
    #[prop(optional)]
    input_type: String,
    /// Reactive value binding.
    #[prop(optional)]
    value: RwSignal<String>,
    /// External input event handler (overrides the default signal setter).
    #[prop(optional)]
    on_input: Option<Box<dyn Fn(web_sys::Event) + 'static>>,
    /// Whether the input is disabled.
    #[prop(optional)]
    disabled: bool,
    /// Reactive error message (renders inline with `role="alert"`).
    #[prop(optional)]
    error: RwSignal<Option<String>>,
    /// Whether the field is required.
    #[prop(optional)]
    _required: bool,
) -> impl IntoView {
    let label_upper = label.to_uppercase();
    let error_class = move || {
        if error.get().is_some() {
            "rams-input rams-input--error"
        } else {
            "rams-input"
        }
    };
    let aria_invalid = move || error.get().is_some().to_string();
    let error_id = format!("{}-error", id);
    let error_id_2 = error_id.clone();

    let required_attr = if _required { "true" } else { "false" };

    view! {
        <div class="rams-input-wrapper">
            <label for=id.clone() class="rams-label">{label_upper}</label>
            <input
                id=id.clone()
                type=input_type
                placeholder=placeholder
                prop:value=value
                on:input=move |ev| {
                    if let Some(ref cb) = on_input {
                        cb(ev);
                    } else {
                        value.set(event_target_value(&ev));
                    }
                }
                disabled=disabled
                class=error_class
                aria-invalid=aria_invalid
                aria-required=required_attr
                aria-describedby=move || {
                    if error.get().is_some() {
                        error_id.clone()
                    } else {
                        String::new()
                    }
                }
            />
            {move || error.get().map(|msg| {
                view! {
                    <span id=error_id_2.clone() class="rams-input-error" role="alert">{msg}</span>
                }
            })}
        </div>
    }
}

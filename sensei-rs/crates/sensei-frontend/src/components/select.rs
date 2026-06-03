//! Industrial select dropdown component.
//!
//! Provides [`Select`] — a styled `<select>` element using the `.rams-input` CSS
//! classes from [`styles/rams.css`](../../styles/rams.css) section 7, matching the
//! look and feel of [`IndustrialInput`](super::input::IndustrialInput).

use leptos::prelude::*;

/// Industrial-styled select dropdown.
///
/// Renders a Dymo-style uppercase label above a `<select>` element styled with
/// the same `.rams-input` class used by [`IndustrialInput`](super::input::IndustrialInput).
///
/// # Example
///
/// ```ignore
/// let status = RwSignal::new(String::from("active"));
/// let options = vec![
///     ("active".to_string(), "Active".to_string()),
///     ("inactive".to_string(), "Inactive".to_string()),
/// ];
///
/// <Select name="status" value=status options=options />
/// ```
#[component]
pub fn Select(
    /// `name` attribute for the select element.
    #[prop(into)]
    name: String,
    /// Reactive value binding.
    #[prop(into)]
    value: RwSignal<String>,
    /// List of `(value, label)` tuples.
    #[prop(into)]
    options: Vec<(String, String)>,
    /// Optional placeholder text when no option is selected.
    #[prop(optional)]
    placeholder: Option<String>,
    /// Whether the field is required.
    #[prop(optional)]
    required: bool,
    /// Whether the select is disabled.
    #[prop(optional)]
    disabled: bool,
) -> impl IntoView {
    let name_upper = name.to_uppercase();

    view! {
        <div class="rams-input-wrapper">
            <label for=name.clone() class="rams-label">{name_upper.clone()}</label>
            <select
                id=name.clone()
                name=name.clone()
                class="rams-input"
                prop:value=value
                on:change=move |ev| {
                    value.set(event_target_value(&ev));
                }
                disabled=disabled
                required=required
                aria-label=name_upper.clone()
            >
                {placeholder.as_ref().map(|p| {
                    view! {
                        <option value="" disabled=required>
                            {p.clone()}
                        </option>
                    }
                })}
                {options.iter().map(|(opt_val, opt_label)| {
                    let opt_val = opt_val.clone();
                    let opt_label = opt_label.clone();
                    view! {
                        <option value=opt_val.clone()>
                            {opt_label}
                        </option>
                    }
                }).collect::<Vec<_>>()}
            </select>
        </div>
    }
}

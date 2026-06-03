//! Mechanical-toggle-style checkbox component.
//!
//! Provides [`Checkbox`] — an industrial-styled checkbox that follows the
//! Rams design system's mechanical toggle metaphor. Renders as a compact
//! square toggle with an uppercase Dymo label.

use leptos::prelude::*;

/// Mechanical-toggle-style checkbox with label.
///
/// Renders a square toggle indicator (not a rounded pill) with an uppercase
/// monospaced label. Uses border-based styling with inset shadow when active.
///
/// # Example
///
/// ```ignore
/// let checked = RwSignal::new(false);
/// <Checkbox label="Enable Notifications" checked=checked />
/// ```
#[component]
pub fn Checkbox(
    /// Label text displayed next to the checkbox (uppercase).
    #[prop(into)]
    label: String,
    /// Reactive checked state.
    #[prop(into)]
    checked: RwSignal<bool>,
    /// Whether the checkbox is disabled.
    #[prop(optional)]
    disabled: bool,
) -> impl IntoView {
    let label_upper = label.to_uppercase();
    let input_id = format!("checkbox-{}", label.to_lowercase().replace(' ', "-"));

    view! {
        <label
            for=input_id.clone()
            class="rams-flex rams-flex--center rams-gap-2"
            style="cursor: pointer; user-select: none;"
        >
            <input
                id=input_id.clone()
                type="checkbox"
                prop:checked=checked
                on:change=move |_| {
                    checked.update(|v| *v = !*v);
                }
                disabled=disabled
                class="rams-input"
                style="width: 16px; height: 16px; padding: 0; cursor: pointer; accent-color: var(--rams-orange);"
                aria-label=label_upper.clone()
            />
            <span class="rams-label" style="cursor: pointer;">{label_upper}</span>
        </label>
    }
}

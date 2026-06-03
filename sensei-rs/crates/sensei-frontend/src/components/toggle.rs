//! Mechanical toggle switch component.
//!
//! Provides [`ToggleSwitch`] — an industrial toggle following the Rams design
//! system's "rotary knob metaphor". Uses the `.rams-toggle` CSS classes from
//! [`styles/rams.css`](../../styles/rams.css) section 21.

use leptos::prelude::*;

/// Mechanical toggle switch with label.
///
/// Renders a switch track with a circular knob using `.rams-toggle` CSS classes.
/// Active state uses orange accent border and background tint.
///
/// # Example
///
/// ```ignore
/// let enabled = RwSignal::new(false);
/// <ToggleSwitch label="Enable Alarm" enabled=enabled />
/// ```
#[component]
pub fn ToggleSwitch(
    /// Label text displayed next to the toggle (uppercase).
    #[prop(into)]
    label: String,
    /// Reactive enabled state.
    #[prop(into)]
    enabled: RwSignal<bool>,
    /// Whether the toggle is disabled.
    #[prop(optional)]
    disabled: bool,
) -> impl IntoView {
    let label_upper = label.to_uppercase();
    let label_upper_clone = label_upper.clone();
    let toggle_id = format!("toggle-{}", label.to_lowercase().replace(' ', "-"));
    let is_active = move || enabled.get();

    view! {
        <label
            for=toggle_id.clone()
            class="rams-flex rams-flex--center rams-gap-2"
            style="cursor: pointer; user-select: none;"
        >
            <span class="rams-label" style="cursor: pointer;">{label_upper}</span>
            <div
                id=toggle_id.clone()
                role="switch"
                aria-checked=move || is_active().to_string()
                aria-label=label_upper_clone
                tabindex="0"
                class=move || {
                    if is_active() {
                        "rams-toggle rams-toggle--active"
                    } else {
                        "rams-toggle"
                    }
                }
                style=if disabled { "opacity: 0.5; cursor: not-allowed;" } else { "" }
                on:click=move |_| {
                    if !disabled {
                        enabled.update(|v| *v = !*v);
                    }
                }
                on:keydown=move |ev| {
                    if !disabled && (ev.key() == " " || ev.key() == "Enter") {
                        ev.prevent_default();
                        enabled.update(|v| *v = !*v);
                    }
                }
            >
                <div class="rams-toggle-knob"></div>
                <div class="rams-toggle-track-indicators" aria-hidden="true">
                    <span>"I"</span>
                    <span>"O"</span>
                </div>
            </div>
        </label>
    }
}

//! Andon status indicator component.
//!
//! Provides a visual three-light stack (Red / Yellow / Green) following the
//! Rams design system section 3.4. Each light can be independently enabled
//! to signal the current operational status.

use leptos::prelude::*;

/// Andon status indicator — a three-light stack (Red / Yellow / Green).
///
/// Mimics the factory-floor Andon towers. Inactive lights are dimmed; active
/// lights shine at full intensity. An optional [`DymoLabel`][super::dymo_label::DymoLabel]
/// can be displayed below the lights.
///
/// # Example
///
/// ```ignore
/// <AndonStack green=true label="SYSTEM OK" />
/// ```
#[component]
pub fn AndonStack(
    /// Whether the Red (Stop / Error) light is active.
    #[prop(optional)]
    red: bool,
    /// Whether the Yellow (Caution) light is active.
    #[prop(optional)]
    yellow: bool,
    /// Whether the Green (Normal) light is active.
    #[prop(optional)]
    green: bool,
    /// Optional label shown below the lights.
    #[prop(optional)]
    label: String,
) -> impl IntoView {
    view! {
        <div class="andon-stack" role="status" aria-label=format!("Andon status: {}", if green { "normal" } else if yellow { "caution" } else if red { "stop" } else { "inactive" })>
            <div
                class=format!(
                    "andon-light {}",
                    if red { "andon-light--red" } else { "andon-light--inactive" },
                )
                title="Stop / Error"
            ></div>
            <div
                class=format!(
                    "andon-light {}",
                    if yellow { "andon-light--yellow" } else { "andon-light--inactive" },
                )
                title="Caution"
            ></div>
            <div
                class=format!(
                    "andon-light {}",
                    if green { "andon-light--green" } else { "andon-light--inactive" },
                )
                title="Normal"
            ></div>
            {if !label.is_empty() {
                view! { <span class="dymo-label">{label.clone()}</span> }.into_any()
            } else {
                ().into_any()
            }}
        </div>
    }
}

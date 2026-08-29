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
    // Item 56: severity precedence is red > yellow > green — when multiple
    // conditions are active, the MOST severe one defines the status (the
    // old green-wins-if-first chain reported NORMAL for a stopped line).
    let condition = if red {
        "STOP"
    } else if yellow {
        "CAUTION"
    } else if green {
        "NORMAL"
    } else {
        "INACTIVE"
    };
    // The condition is EXPLICIT VISIBLE TEXT, not color alone (item 56) —
    // color-vision deficiency and rapid floor scanning both rely on it.
    let status_line = if condition == "INACTIVE" {
        label.clone()
    } else {
        format!("{condition} — {}", label.clone())
    };
    view! {
        <div class="andon-stack" role="status" aria-label=format!("Andon status: {condition}")>
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
            {if !status_line.is_empty() {
                view! { <span class="dymo-label">{status_line}</span> }.into_any()
            } else {
                ().into_any()
            }}
        </div>
    }
}

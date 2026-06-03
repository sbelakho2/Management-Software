//! Dymo label component.
//!
//! A small, monospaced label evoking the adhesive labels produced by a Dymo
//! embossing label maker. Used for status indicators, station IDs, and
//! instrument readout captions. See [`styles/rams.css`](../../styles/rams.css) section 3.5.

use leptos::prelude::*;

/// Dymo-style embossed label.
///
/// Renders uppercase, monospaced text that resembles a physical Dymo label
/// strip. Supports `"default"`, `"warning"`, and `"critical"` variants.
///
/// # Example
///
/// ```ignore
/// <DymoLabel text="STATION-01" />
/// <DymoLabel text="OVERHEAT" variant="critical" />
/// ```
#[component]
pub fn DymoLabel(
    /// The label text (will be displayed uppercase by CSS).
    text: String,
    /// Visual variant: `"default"`, `"warning"`, or `"critical"`.
    #[prop(optional)]
    variant: String,
    /// Additional CSS classes to append.
    #[prop(optional)]
    class: String,
) -> impl IntoView {
    let variant_class = match variant.as_str() {
        "warning" => "dymo-label--warning",
        "critical" => "dymo-label--critical",
        _ => "dymo-label--default",
    };
    view! {
        <span class=format!("dymo-label {} {}", variant_class, class)>{text}</span>
    }
}

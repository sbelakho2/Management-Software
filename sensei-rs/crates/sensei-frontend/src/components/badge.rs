//! Industrial status/priority/severity badge component.
//!
//! Provides [`Badge`] — a compact inline indicator for status, priority, or severity
//! using the `.rams-badge` CSS classes defined in [`styles/rams.css`](../../styles/rams.css).
//!
//! The variant string maps directly to CSS class names such as `status-open`,
//! `priority-high`, `severity-critical`, etc.

use leptos::prelude::*;

/// Compact inline badge for status, priority, or severity display.
///
/// Maps to the `.rams-badge` CSS classes. The `variant` string is appended as a
/// CSS class so that any status/priority/severity token defined in
/// [`rams.css`](../../styles/rams.css) sections 24 can be used.
///
/// # Example
///
/// ```ignore
/// <Badge label="Open" variant=Some("status-open".to_string()) />
/// <Badge label="High" variant=Some("priority-high".to_string()) />
/// <Badge label="Critical" variant=Some("severity-critical".to_string()) />
/// ```
#[component]
pub fn Badge(
    /// Badge label text (displayed uppercase).
    #[prop(into)]
    label: String,
    /// Optional variant class — maps to CSS status/priority/severity tokens
    /// (e.g., `"status-open"`, `"priority-high"`, `"severity-critical"`).
    #[prop(optional, into)]
    variant: Option<String>,
    /// Additional CSS classes to append.
    #[prop(optional)]
    class: Option<String>,
) -> impl IntoView {
    let label_upper = label.to_uppercase();
    let variant_class = move || {
        variant.clone().map(|v| format!(" {}", v)).unwrap_or_default()
    };
    let extra_class = move || {
        class.clone().map(|c| format!(" {}", c)).unwrap_or_default()
    };

    view! {
        <span
            class=move || format!("rams-badge{}{}", variant_class(), extra_class())
            aria-label=label.clone()
        >
            {label_upper}
        </span>
    }
}

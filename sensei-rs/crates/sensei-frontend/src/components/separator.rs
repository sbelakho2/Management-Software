//! Thin horizontal rule / separator component.
//!
//! Provides [`Separator`] — a thin horizontal rule using the Rams `--rams-line`
//! border color. Optionally includes a centered label.

use leptos::prelude::*;

/// Thin horizontal rule with optional label.
///
/// Uses the Rams `--rams-line` border color for the rule. When a label is
/// provided, it is displayed centered in uppercase monospaced text.
///
/// # Example
///
/// ```ignore
/// <Separator />
/// <Separator label="Section Break" />
/// ```
#[component]
pub fn Separator(
    /// Optional label displayed in the center of the separator.
    #[prop(optional)]
    label: Option<String>,
) -> impl IntoView {
    let label_upper = label.as_ref().map(|l| l.to_uppercase());

    view! {
        <div
            role="separator"
            aria-orientation="horizontal"
            style="width: 100%; height: 1px; background-color: var(--rams-line); \
                 margin: var(--rams-space-4) 0; position: relative;"
                .to_string()
        >
            {label_upper.map(|l| {
                view! {
                    <span
                        style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); \
                             background-color: var(--rams-chassis); \
                             padding: 0 var(--rams-space-3); \
                             font-family: var(--rams-font-mono); \
                             font-size: var(--rams-text-2xs); \
                             font-weight: var(--rams-weight-bold); \
                             text-transform: uppercase; \
                             letter-spacing: 0.1em; \
                             color: var(--rams-muted); \
                             white-space: nowrap;"
                            .to_string()
                    >
                        {l}
                    </span>
                }
            })}
        </div>
    }
}

//! Simple CSS-based tooltip component.
//!
//! Provides [`Tooltip`] — a lightweight tooltip that uses CSS positioning and
//! transitions. Follows the Rams design system with sharp corners, border styling,
//! and instant appearance.

use leptos::prelude::*;

/// CSS-based tooltip wrapping child content.
///
/// The tooltip appears on hover using CSS transitions. Supports four positions:
/// `"top"`, `"bottom"`, `"left"`, `"right"` (default: `"top"`).
///
/// # Example
///
/// ```ignore
/// <Tooltip text="Click to submit" position=Some("top".to_string())>
///     <button>"SUBMIT"</button>
/// </Tooltip>
/// ```
#[component]
pub fn Tooltip(
    /// Tooltip text content (displayed uppercase).
    #[prop(into)]
    text: String,
    /// Tooltip position: `"top"`, `"bottom"`, `"left"`, `"right"` (default: `"top"`).
    #[prop(optional)]
    position: Option<String>,
    /// Child elements the tooltip wraps around.
    children: Children,
) -> impl IntoView {
    let tooltip_text = text.to_uppercase();
    let pos = move || position.clone().unwrap_or_else(|| "top".to_string());
    let pos_for_container = pos.clone();
    let get_arrow_style = move || {
        let p = pos();
        match p.as_str() {
            "bottom" => "top: -4px; left: 50%; transform: translateX(-50%) rotate(45deg);",
            "left" => "top: 50%; right: -4px; transform: translateY(-50%) rotate(45deg);",
            "right" => "top: 50%; left: -4px; transform: translateY(-50%) rotate(45deg);",
            _ => "bottom: -4px; left: 50%; transform: translateX(-50%) rotate(45deg);",
        }
    };
    let get_container_style = move || {
        let p = pos_for_container();
        match p.as_str() {
            "bottom" => "top: calc(100% + 8px); left: 50%; transform: translateX(-50%);",
            "left" => "right: calc(100% + 8px); top: 50%; transform: translateY(-50%);",
            "right" => "left: calc(100% + 8px); top: 50%; transform: translateY(-50%);",
            _ => "bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%);",
        }
    };

    view! {
        <div
            style="position: relative; display: inline-flex;"
            aria-describedby="tooltip-text"
        >
            {children()}
            <div
                role="tooltip"
                style=move || {
                    format!(
                        "position: absolute; {} \
                         pointer-events: none; z-index: 100; \
                         background-color: var(--rams-foreground); \
                         color: var(--rams-chassis); \
                         font-family: var(--rams-font-mono); \
                         font-size: var(--rams-text-2xs); \
                         font-weight: var(--rams-weight-bold); \
                         text-transform: uppercase; \
                         letter-spacing: 0.05em; \
                         padding: var(--rams-space-1) var(--rams-space-2); \
                         border-radius: var(--rams-radius-sm); \
                         white-space: nowrap; \
                         opacity: 0; \
                         transition: opacity var(--rams-fast);",
                        get_container_style()
                    )
                }
            >
                {tooltip_text.clone()}
                <div
                    aria-hidden="true"
                    style=move || {
                        format!(
                            "position: absolute; width: 6px; height: 6px; \
                             background-color: var(--rams-foreground); {}",
                            get_arrow_style()
                        )
                    }
                ></div>
            </div>
            <style>
                {"[aria-describedby=\"tooltip-text\"]:hover [role=\"tooltip\"], \
                  [aria-describedby=\"tooltip-text\"]:focus-within [role=\"tooltip\"] { opacity: 1 !important; }".to_string()}
            </style>
        </div>
    }
}

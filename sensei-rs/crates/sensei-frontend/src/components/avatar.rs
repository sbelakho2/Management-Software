//! User avatar/initials display component.
//!
//! Provides [`Avatar`] — a compact display for user initials or profile images
//! following the Rams design system's industrial aesthetic. No rounded corners
//! beyond 2px, no shadows, no gradients.

use leptos::prelude::*;

/// User avatar/initials display.
///
/// Renders a square panel with user initials (derived from the name) or an
/// optional image. Supports three sizes: `"sm"`, `"md"`, `"lg"`.
///
/// # Example
///
/// ```ignore
/// <Avatar name="John Doe" size=Some("md".to_string()) />
/// <Avatar name="Jane Smith" src=Some("/avatars/jane.jpg".to_string()) />
/// ```
#[component]
pub fn Avatar(
    /// Full name used to derive initials.
    #[prop(into)]
    name: String,
    /// Optional image source URL.
    #[prop(optional)]
    src: Option<String>,
    /// Size variant: `"sm"`, `"md"`, `"lg"` (default: `"md"`).
    #[prop(optional)]
    size: Option<String>,
) -> impl IntoView {
    let initials = name
        .split_whitespace()
        .filter_map(|part| part.chars().next())
        .take(2)
        .collect::<String>()
        .to_uppercase();

    let size_for_font = size.clone();
    let size_class = move || {
        match size.as_deref() {
            Some("sm") => "24px",
            Some("lg") => "40px",
            _ => "32px", // md default
        }
    };
    let font_size = move || match size_for_font.as_deref() {
        Some("sm") => "10px",
        Some("lg") => "16px",
        _ => "14px",
    };

    let has_src = src.is_some();
    let name_clone = name.clone();

    view! {
        <div
            class="rams-flex rams-flex--center"
            role="img"
            aria-label=name.clone()
            style=move || {
                let s = size_class();
                format!(
                    "width: {}; height: {}; \
                     background-color: var(--rams-panel); \
                     border: 1px solid var(--rams-line); \
                     border-radius: var(--rams-radius-sm); \
                     overflow: hidden; \
                     flex-shrink: 0;",
                    s, s
                )
            }
        >
            {if has_src {
                let src_val = src.clone().unwrap_or_default();
                view! {
                    <img
                        src=src_val
                        alt=name_clone.clone()
                        style=move || "width: 100%; height: 100%; object-fit: cover; display: block;".to_string()
                    />
                }.into_any()
            } else {
                view! {
                    <span
                        style=move || format!(
                            "font-family: var(--rams-font-mono); \
                             font-size: {}; font-weight: var(--rams-weight-bold); \
                             color: var(--rams-muted); text-transform: uppercase; \
                             line-height: 1;",
                            font_size()
                        )
                    >
                        {initials.clone()}
                    </span>
                }.into_any()
            }}
        </div>
    }
}

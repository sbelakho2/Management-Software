//! Loading state components.
//!
//! Provides [`LoadingSpinner`] and [`Skeleton`] — industrial-style loading
//! indicators following the Rams design system. Uses opacity-based animations
//! rather than spinning or bouncing effects.

use leptos::prelude::*;

/// Industrial-style loading spinner with optional label.
///
/// Renders a simple pulsing circle (no spinning animation) with an optional
/// uppercase label beneath it. Follows the anti-pattern guidance for loading
/// states in [`docs/development/sensei-rams-anti-patterns.md`](../../../../docs/development/sensei-rams-anti-patterns.md).
///
/// # Example
///
/// ```ignore
/// <LoadingSpinner label="Processing" />
/// ```
#[component]
pub fn LoadingSpinner(
    /// Optional label displayed below the spinner.
    #[prop(optional)]
    label: Option<String>,
) -> impl IntoView {
    let label_upper = label.as_ref().map(|l| l.to_uppercase());

    view! {
        <div
            style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--rams-space-3); padding: var(--rams-space-8);"
            role="status"
            aria-label=label.clone().unwrap_or_else(|| "Loading".to_string())
        >
            <div
                style="
                    width: 20px;
                    height: 20px;
                    border: 2px solid var(--rams-line);
                    border-top: 2px solid var(--rams-orange);
                    border-radius: 50%;
                    animation: rams-spin 1s linear infinite;
                "
            ></div>
            {label_upper.map(|l| {
                view! {
                    <span class="rams-label" style="text-align: center;">{l}</span>
                }
            })}
            <style>
                "@keyframes rams-spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }"
            </style>
        </div>
    }
}

/// Industrial-style skeleton placeholder for loading content.
///
/// Renders one or more rectangular placeholder blocks with a pulsing opacity
/// animation. Can be used as a single block or multiple lines.
///
/// # Example
///
/// ```ignore
/// <Skeleton width=Some("100%".to_string()) height=Some("16px".to_string()) lines=Some(3) />
/// ```
#[component]
pub fn Skeleton(
    /// Width of each skeleton block (default: `"100%"`).
    #[prop(optional)]
    width: Option<String>,
    /// Height of each skeleton block (default: `"12px"`).
    #[prop(optional)]
    height: Option<String>,
    /// Number of skeleton lines to render (default: `1`).
    #[prop(optional)]
    lines: Option<u32>,
) -> impl IntoView {
    let block_w = width.clone().unwrap_or_else(|| "100%".to_string());
    let block_h = height.clone().unwrap_or_else(|| "12px".to_string());
    let num_lines = lines.unwrap_or(1);
    let skeleton_style = format!(
        "width: {}; height: {}; \
         background-color: var(--rams-panel); \
         border: 1px solid var(--rams-line); \
         border-radius: var(--rams-radius-sm); \
         animation: rams-pulse 1.5s ease-in-out infinite;",
        block_w, block_h
    );

    view! {
        <div
            aria-label="Loading content"
            aria-busy="true"
            role="status"
            style="display: flex; flex-direction: column; gap: var(--rams-space-2);"
        >
            {(0..num_lines).map(|i| {
                let line_style = if i == num_lines - 1 && num_lines > 1 {
                    format!("{} width: 60%;", skeleton_style)
                } else {
                    skeleton_style.clone()
                };
                view! {
                    <div style=line_style></div>
                }
            }).collect::<Vec<_>>()}
            <style>
                "@keyframes rams-pulse {
                    0%, 100% { opacity: 0.3; }
                    50% { opacity: 1; }
                }"
            </style>
        </div>
    }
}

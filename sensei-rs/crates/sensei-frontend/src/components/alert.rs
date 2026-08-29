//! Alert/notification banner component.
//!
//! Provides [`Alert`] — status banners for success, warning, error, and info
//! messages. Follows the Rams design system's industrial notification pattern:
//! solid background, border accent, no shadows.

use leptos::prelude::*;
use std::sync::Arc;

/// Status banner for success/warning/error/info notifications.
///
/// Renders a horizontal banner with a status indicator dot, message text,
/// and optional dismiss button. Uses Rams `--rams-status` CSS classes.
///
/// # Example
///
/// ```ignore
/// <Alert
///     message="Operation completed successfully"
///     level=Some("success".to_string())
///     dismissible=true
/// />
/// ```
#[component]
pub fn Alert(
    /// Alert message text.
    #[prop(into)]
    message: String,
    /// Alert severity level: `"success"`, `"warning"`, `"error"`, `"info"` (default: `"info"`).
    #[prop(optional)]
    level: Option<String>,
    /// Whether the alert can be dismissed.
    #[prop(optional)]
    dismissible: bool,
    /// Optional callback invoked when the alert is dismissed.
    #[prop(optional)]
    on_dismiss: Option<Arc<dyn Fn() + Send + Sync + 'static>>,
) -> impl IntoView {
    // Each colour helper captures its own clone of `level` to avoid
    // moving a shared closure into two places.
    let level_accent = level.clone();
    let level_dot = level.clone();
    let level_role = level.clone();
    let get_accent = move || match level_accent.unwrap_or_else(|| "info".to_string()).as_str() {
        "success" => "var(--rams-green)",
        "warning" => "var(--rams-orange)",
        "error" => "var(--rams-red)",
        _ => "var(--rams-steel)",
    };
    let get_dot = move || match level_dot.unwrap_or_else(|| "info".to_string()).as_str() {
        "success" => "var(--rams-green)",
        "warning" => "var(--rams-orange)",
        "error" => "var(--rams-red)",
        _ => "var(--rams-steel)",
    };

    let visible = RwSignal::new(true);

    // Define handler at function scope — no nested move closures.
    let on_dismiss = on_dismiss.map(|cb| Arc::clone(&cb));
    let handle_dismiss = move |_| {
        visible.set(false);
        if let Some(ref cb) = on_dismiss {
            cb();
        }
    };

    let accent = move || get_accent();
    let dot = move || get_dot();
    // Item 57: assertive `alert` is reserved for errors that truly require
    // immediate attention; success/info/warning are polite `status` so
    // screen-reader users are not interrupted by routine messages.
    let level_str = level_role.unwrap_or_else(|| "info".to_string());
    let is_error = level_str.eq("error");
    let role = if is_error { "alert" } else { "status" };

    view! {
        <div
            role=role
            hidden=move || !visible.get()
            style=format!(
                "display: flex; align-items: center; gap: var(--rams-space-3); \
                 padding: var(--rams-space-3) var(--rams-space-4); \
                 background-color: var(--rams-module); \
                 border: 1px solid {}; \
                 border-radius: var(--rams-radius-sm);",
                accent()
            )
        >
            <div
                aria-hidden="true"
                style=format!(
                    "width: 8px; height: 8px; border-radius: 50%; \
                     background-color: {}; flex-shrink: 0;",
                    dot()
                )
            ></div>

            <span style="flex: 1; font-size: var(--rams-text-sm); color: var(--rams-foreground);">
                {message.clone()}
            </span>

            {if dismissible {
                Some(view! {
                    <button
                        type="button"
                        class="rams-btn rams-btn--ghost rams-btn--sm"
                        aria-label="Dismiss alert"
                        style="font-size: 14px; line-height: 1; padding: 2px 6px; min-width: 0;"
                        on:click=handle_dismiss
                    >
                        "✕"
                    </button>
                })
            } else {
                None
            }}
        </div>
    }
}

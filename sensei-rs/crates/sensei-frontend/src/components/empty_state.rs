//! Empty state component for when no data is available.
//!
//! Provides [`EmptyState`] — a centered placeholder display with optional
//! title, description, and action button. Follows the Rams design system's
//! industrial aesthetic.

use leptos::prelude::*;

/// Empty state placeholder display.
///
/// Shown when a list, table, or panel has no data to display.
/// Includes an optional action button for primary call-to-action.
///
/// # Example
///
/// ```ignore
/// <EmptyState
///     title="No Records Found"
///     description=Some("There are no work orders matching the current filters.".to_string())
///     action_label=Some("Create Work Order".to_string())
///     on_action=Some(Box::new(|| { /* navigate to create */ }))
/// />
/// ```
#[component]
pub fn EmptyState(
    /// Primary title text (displayed uppercase).
    #[prop(into)]
    title: String,
    /// Optional description text.
    #[prop(optional)]
    description: Option<String>,
    /// Optional label for the action button.
    #[prop(optional)]
    action_label: Option<String>,
    /// Optional callback invoked when the action button is clicked.
    #[prop(optional)]
    on_action: Option<Box<dyn Fn() + 'static>>,
) -> impl IntoView {
    let title_upper = title.to_uppercase();

    view! {
        <div
            style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: var(--rams-space-12) var(--rams-space-8); text-align: center; gap: var(--rams-space-3);"
            role="status"
        >
            {/* Empty state icon - simple grille pattern */}
            <div
                class="rams-grille--fine"
                style="width: 48px; height: 48px; margin-bottom: var(--rams-space-2);"
                aria-hidden="true"
            ></div>

            <h3
                style="font-family: var(--rams-font-mono); font-size: var(--rams-text-sm); font-weight: var(--rams-weight-bold); text-transform: uppercase; letter-spacing: 0.1em; color: var(--rams-muted); margin: 0;"
            >
                {title_upper}
            </h3>

            {description.map(|desc| {
                view! {
                    <p style="font-size: var(--rams-text-sm); color: var(--rams-muted); max-width: 320px; margin: 0;">
                        {desc}
                    </p>
                }
            })}

            {action_label.zip(on_action).map(|(label, callback)| {
                let label_upper = label.to_uppercase();
                view! {
                    <button
                        type="button"
                        class="rams-btn rams-btn--default rams-btn--md"
                        style="margin-top: var(--rams-space-2);"
                        on:click=move |_| { callback() }
                    >
                        {label_upper}
                    </button>
                }
            })}
        </div>
    }
}

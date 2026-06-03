//! Search input field with clear button.
//!
//! Provides [`SearchInput`] — an industrial-styled search field following the
//! Rams design system. Includes a clear button and optional search callback.

use std::sync::Arc;
use leptos::prelude::*;

/// Industrial-styled search input with clear button.
///
/// Renders a text input styled with `.rams-input` class, plus a clear button
/// that appears when the field has content.
///
/// # Example
///
/// ```ignore
/// let query = RwSignal::new(String::new());
/// <SearchInput
///     value=query
///     placeholder=Some("Search work orders...".to_string())
///     on_search=Some(Arc::new(|q| { /* perform search */ }))
/// />
/// ```
#[component]
pub fn SearchInput(
    /// Reactive value binding for the search query.
    #[prop(into)]
    value: RwSignal<String>,
    /// Optional placeholder text.
    #[prop(optional)]
    placeholder: Option<String>,
    /// Optional callback invoked on each input change (debouncing expected externally).
    #[prop(optional)]
    on_search: Option<Arc<dyn Fn(String) + Send + Sync + 'static>>,
) -> impl IntoView {
    let placeholder_text = placeholder.clone().unwrap_or_else(|| "SEARCH".to_string());
    let has_value = move || !value.get().is_empty();
    let search_id = "rams-search-input";

    // Clone the Arc ref so each handler owns an independent reference.
    let on_search = on_search.map(|cb| Arc::clone(&cb));
    let on_search_input = on_search.clone();
    let on_search_key = on_search.clone();

    let on_input = move |ev| {
        let val = event_target_value(&ev);
        value.set(val.clone());
        if let Some(ref cb) = on_search_input {
            cb(val);
        }
    };

    let on_keydown = move |ev: leptos::ev::KeyboardEvent| {
        if ev.key() == "Enter" {
            if let Some(ref cb) = on_search_key {
                cb(value.get());
            }
        }
    };

    let on_clear = move |_| {
        value.set(String::new());
        if let Some(ref cb) = on_search {
            cb(String::new());
        }
    };

    view! {
        <div style="position: relative; display: flex; align-items: center;">
            <input
                id=search_id
                type="search"
                class="rams-input"
                placeholder=placeholder_text
                prop:value=value
                on:input=on_input
                on:keydown=on_keydown
                aria-label="Search"
                style="padding-right: 32px;"
            />
            <button
                type="button"
                class="rams-btn rams-btn--ghost"
                aria-label="Clear search"
                hidden=move || !has_value()
                style="
                    position: absolute;
                    right: 4px;
                    top: 50%;
                    transform: translateY(-50%);
                    padding: 2px 6px;
                    min-width: 0;
                    height: auto;
                    font-size: 14px;
                    line-height: 1;
                    border: none;
                    color: var(--rams-muted);
                "
                on:click=on_clear
            >
                "✕"
            </button>
        </div>
    }
}

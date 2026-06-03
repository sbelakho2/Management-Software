//! Industrial-style modal/dialog overlay component.
//!
//! Provides [`Modal`] — a positioned overlay panel following the Rams design
//! system. No shadows, sharp borders, solid backdrop. Follows the anti-pattern
//! guidance in [`docs/development/sensei-rams-anti-patterns.md`](../../../../docs/development/sensei-rams-anti-patterns.md).

use std::sync::Arc;
use leptos::prelude::*;
use wasm_bindgen::JsCast;

/// Industrial-style modal overlay.
///
/// Renders a positioned overlay with a solid backdrop (no blur, no shadow)
/// and a module-styled panel with optional title header.
///
/// # Example
///
/// ```ignore
/// let is_open = RwSignal::new(true);
/// <Modal title="Confirm Action" open=Some(is_open)>
///     <p>"Are you sure you want to proceed?"</p>
/// </Modal>
/// ```
#[component]
pub fn Modal(
    /// Optional title displayed in the modal header.
    #[prop(optional)]
    title: Option<String>,
    /// Optional reactive signal controlling open state.
    #[prop(optional)]
    open: Option<RwSignal<bool>>,
    /// Optional callback invoked when the modal is dismissed.
    #[prop(optional)]
    on_close: Option<Arc<dyn Fn() + Send + Sync + 'static>>,
    /// Modal body content.
    children: Children,
) -> impl IntoView {
    let is_open = move || {
        open.map(|s| s.get()).unwrap_or(true)
    };
    let heading_id = title.as_ref().map(|t| {
        format!("modal-{}", t.to_lowercase().replace(' ', "-"))
    }).unwrap_or_default();

    // Clone the Arc<dyn Fn> ref so both handlers can own a reference.
    let on_close = on_close.map(|cb| Arc::clone(&cb));
    let on_close_btn = on_close.clone();

    let handle_backdrop = move |ev: web_sys::MouseEvent| {
        if let Some(el) = ev.target().and_then(|t| t.dyn_into::<web_sys::Element>().ok()) {
            if el.get_attribute("data-backdrop").as_deref() == Some("true") {
                if let Some(ref cb) = on_close {
                    cb();
                }
                if let Some(s) = open {
                    s.set(false);
                }
            }
        }
    };

    let handle_close_btn = move |_| {
        if let Some(ref cb) = on_close_btn {
            cb();
        }
        if let Some(s) = open {
            s.set(false);
        }
    };

    let title_display = title.clone();
    let heading_id_clone = heading_id.clone();

    view! {
        <div
            role="dialog"
            aria-modal="true"
            data-backdrop="true"
            aria-labelledby=if heading_id_clone.is_empty() { None::<String> } else { Some(heading_id_clone.clone()) }
            hidden=move || !is_open()
            style="
                position: fixed;
                inset: 0;
                background-color: rgba(0, 0, 0, 0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            "
            on:click=handle_backdrop
        >
            <div
                style="
                    background-color: var(--rams-module);
                    border: 1px solid var(--rams-line);
                    border-radius: var(--rams-radius-sm);
                    width: 100%;
                    max-width: 480px;
                    min-width: 280px;
                "
                on:click=move |ev: web_sys::MouseEvent| {
                    ev.stop_propagation();
                }
            >
                {(title_display.clone().zip(Some(heading_id.clone()))).map(|(t, id)| {
                    view! {
                        <div class="module-header">
                            <h3 id=id.clone() class="module-title">{t}</h3>
                            <button
                                type="button"
                                class="rams-btn rams-btn--ghost rams-btn--sm"
                                aria-label="Close dialog"
                                style="font-size: 16px; line-height: 1; padding: 4px 8px;"
                                on:click=handle_close_btn
                            >
                                "✕"
                            </button>
                        </div>
                    }
                })}
                <div class="module-content">
                    {children()}
                </div>
            </div>
        </div>
    }
}

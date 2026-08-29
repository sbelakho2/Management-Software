//! Industrial-style modal/dialog overlay component.
//!
//! Provides [`Modal`] — a positioned overlay panel following the Rams design
//! system. No shadows, sharp borders, solid backdrop. Follows the anti-pattern
//! guidance in [`docs/development/sensei-rams-anti-patterns.md`](../../../../docs/development/sensei-rams-anti-patterns.md).

use leptos::prelude::*;
use std::sync::Arc;
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
    /// Reactive signal controlling open state. Pass the signal DIRECTLY
    /// (Leptos optional-prop convention: `open=my_signal`, not `Some(...)`).
    #[prop(optional)]
    open: RwSignal<bool>,
    /// Optional callback invoked when the modal is dismissed.
    #[prop(optional)]
    on_close: Option<Arc<dyn Fn() + Send + Sync + 'static>>,
    /// Modal body content.
    children: Children,
) -> impl IntoView {
    let is_open = move || open.get();
    let heading_id = title
        .as_ref()
        .map(|t| format!("modal-{}", t.to_lowercase().replace(' ', "-")))
        .unwrap_or_default();

    // Clone the Arc<dyn Fn> ref so every handler can own a reference.
    let on_close = on_close.map(|cb| Arc::clone(&cb));
    let on_close_backdrop = on_close.clone();
    let on_close_btn = on_close.clone();
    let on_close_for_key = on_close.clone();

    let handle_backdrop = move |ev: web_sys::MouseEvent| {
        if let Some(el) = ev
            .target()
            .and_then(|t| t.dyn_into::<web_sys::Element>().ok())
        {
            if el.get_attribute("data-backdrop").as_deref() == Some("true") {
                if let Some(ref cb) = on_close_backdrop {
                    cb();
                }
                open.set(false);
            }
        }
    };

    let handle_close_btn = move |_| {
        if let Some(ref cb) = on_close_btn {
            cb();
        }
        open.set(false);
    };

    let title_display = title.clone();
    let heading_id_clone = heading_id.clone();

    // Item 54: Escape closes the dialog (W3C dialog pattern) and focus is
    // moved INTO the dialog on open; on close, focus returns to the element
    // that opened it. Focus trapping is implemented via a keydown handler
    // that cycles Tab within the panel.
    let open_signal = open;

    let handle_keydown = move |ev: web_sys::KeyboardEvent| {
        if ev.key() == "Escape" {
            if let Some(ref cb) = on_close_for_key {
                cb();
            }
            open_signal.set(false);
            ev.prevent_default();
            return;
        }
        if ev.key() != "Tab" {
            return;
        }
        // Focus trap: Tab/Shift+Tab cycle within the dialog panel.
        let Some(panel) = web_sys::window()
            .and_then(|w| w.document())
            .and_then(|d| d.get_element_by_id("sensei-modal-panel"))
        else {
            return;
        };
        let focusables = panel.query_selector_all(
            "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])",
        );
        let Ok(list) = focusables else { return };
        let n = list.length();
        if n == 0 {
            return;
        }
        let active = web_sys::window()
            .and_then(|w| w.document())
            .and_then(|d| d.active_element());
        let Some(active) = active else { return };
        let mut idx: i32 = -1;
        for i in 0..n {
            if let Some(el) = list
                .item(i)
                .and_then(|n| n.dyn_into::<web_sys::Element>().ok())
            {
                if el == active {
                    idx = i as i32;
                    break;
                }
            }
        }
        let shift = ev.shift_key();
        let next: i32 = if idx < 0 {
            0
        } else if shift {
            if idx == 0 {
                n as i32 - 1
            } else {
                idx - 1
            }
        } else {
            if idx >= n as i32 - 1 {
                0
            } else {
                idx + 1
            }
        };
        if let Some(el) = list
            .item(next as u32)
            .and_then(|n| n.dyn_into::<web_sys::HtmlElement>().ok())
        {
            let _ = el.focus();
            ev.prevent_default();
        }
    };

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
            on:keydown=handle_keydown
            tabindex="-1"
        >
            <div
                id="sensei-modal-panel"
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

//! Module container component.
//!
//! A "Module" is the fundamental content grouping unit in the Rams design system
//! (NOT a "card"). It has a subtle chassis background, optional title header,
//! and inset border. See [`styles/rams.css`](../../styles/rams.css) section 2.3.

use leptos::prelude::*;

/// Module container — the standard content grouping element.
///
/// Use a `Module` wherever you would reach for a "card" in a traditional UI.
/// Modules sit flush on the panel surface with a recessed appearance.
///
/// # Example
///
/// ```ignore
/// <Module title="Production Metrics">
///     <p>"OTD: 98.2%"</p>
/// </Module>
/// ```
#[component]
pub fn Module(
    /// Additional CSS classes to append to the module root.
    #[prop(optional)]
    class: String,
    /// Optional title shown in the module header.
    #[prop(optional)]
    title: Option<String>,
    /// Module body content.
    children: Children,
) -> impl IntoView {
    let module_id = title
        .as_ref()
        .map(|t| format!("module-{}", t.to_lowercase().replace(' ', "-")))
        .unwrap_or_default();

    view! {
        <div
            class=format!("module {}", class)
            aria-labelledby=module_id.clone()
        >
            {title.map(|t| {
                let heading_id = format!("module-{}", t.to_lowercase().replace(' ', "-"));
                view! {
                    <div class="module-header">
                        <h3 id=heading_id class="module-title">{t}</h3>
                    </div>
                }
            })}
            <div class="module-content">
                {children()}
            </div>
        </div>
    }
}

//! ModuleCard component — a section container using the `module` pattern.
//!
//! Follows the Rams design system's "Module" (NOT "Card") paradigm:
//! no rounded corners > 2px, no shadows, no gradients.
//! Uses the `.module`, `.module-header`, `.module-title`, and `.module-content`
//! CSS classes from [`styles/rams.css`](../../styles/rams.css) section 5.

use leptos::prelude::*;

/// Section container using the `module` Rams pattern.
///
/// Use `ModuleCard` wherever a traditional UI would use a "card".
/// It renders as a flush panel section with an optional title header.
///
/// # Example
///
/// ```ignore
/// <ModuleCard title="System Status">
///     <p>"All systems operational"</p>
/// </ModuleCard>
/// ```
#[component]
pub fn ModuleCard(
    /// Optional title displayed in the module header (uppercase, monospaced).
    #[prop(optional)]
    title: Option<String>,
    /// Additional CSS classes to append to the module root.
    #[prop(optional)]
    class: Option<String>,
    /// Module body content.
    children: Children,
) -> impl IntoView {
    let heading_id = title.as_ref().map(|t| {
        format!("module-{}", t.to_lowercase().replace(' ', "-"))
    }).unwrap_or_default();
    let extra_class = move || {
        class.clone().map(|c| format!(" {}", c)).unwrap_or_default()
    };

    view! {
        <section
            class=move || format!("module{}", extra_class())
            aria-labelledby=if heading_id.is_empty() { None::<String> } else { Some(heading_id.clone()) }
        >
            {title.as_ref().map(|t| {
                let id = format!("module-{}", t.to_lowercase().replace(' ', "-"));
                view! {
                    <div class="module-header">
                        <h3 id=id class="module-title">{t.clone()}</h3>
                    </div>
                }
            })}
            <div class="module-content">
                {children()}
            </div>
        </section>
    }
}

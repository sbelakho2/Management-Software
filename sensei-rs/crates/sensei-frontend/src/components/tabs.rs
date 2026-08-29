//! Horizontal tab navigation component.
//!
//! Provides [`Tabs`] and [`TabDefinition`] — an industrial-style horizontal tab
//! bar following the Rams design system. Active tabs are indicated with a border
//! accent rather than background color or shadow.

use leptos::prelude::*;

/// Definition for a single tab item.
#[derive(Debug, Clone)]
pub struct TabDefinition {
    /// Unique identifier for the tab.
    pub id: String,
    /// Display label.
    pub label: String,
    /// Optional icon identifier.
    pub icon: Option<String>,
}

/// Industrial-style horizontal tab navigation.
///
/// Renders a tab bar with an underline/border accent on the active tab.
/// Uses Rams CSS tokens exclusively — no rounded corners, shadows, or gradients.
///
/// # Example
///
/// ```ignore
/// let active = RwSignal::new(String::from("overview"));
/// let tabs = vec![
///     TabDefinition { id: "overview".into(), label: "Overview".into(), icon: None },
///     TabDefinition { id: "details".into(), label: "Details".into(), icon: None },
/// ];
///
/// <Tabs tabs=tabs active_tab=active />
/// ```
#[component]
pub fn Tabs(
    /// List of tab definitions.
    #[prop(into)]
    tabs: Vec<TabDefinition>,
    /// Reactive binding for the active tab ID.
    #[prop(into)]
    active_tab: RwSignal<String>,
) -> impl IntoView {
    // Item 55: roving tabindex + Arrow/Home/End keyboard navigation
    // (W3C tabs pattern) — the tablist is focusable and the handlers
    // move the active tab with the arrow keys.
    let tab_ids: Vec<String> = tabs.iter().map(|t| t.id.clone()).collect();
    let handle_keydown = move |ev: web_sys::KeyboardEvent| {
        let current = active_tab.get_untracked();
        let Some(pos) = tab_ids.iter().position(|id| id == &current) else {
            return;
        };
        let next = match ev.key().as_str() {
            "ArrowRight" => Some((pos + 1) % tab_ids.len()),
            "ArrowLeft" => Some((pos + tab_ids.len() - 1) % tab_ids.len()),
            "Home" => Some(0),
            "End" => Some(tab_ids.len() - 1),
            _ => None,
        };
        if let Some(idx) = next {
            if let Some(id) = tab_ids.get(idx) {
                active_tab.set(id.clone());
                ev.prevent_default();
            }
        }
    };
    view! {
        <nav
            class="rams-flex"
            style="border-bottom: 1px solid var(--rams-line);"
            role="tablist"
            aria-label="Tab navigation"
            on:keydown=handle_keydown
        >
            {tabs.iter().map(|tab| {
                let tab_id = tab.id.clone();
                let tab_label = tab.label.clone();
                let tab_id_for_active = tab_id.clone();
                let tab_id_for_controls = tab_id.clone();
                let tab_id_for_id = tab_id.clone();
                let tab_id_for_click = tab_id.clone();
                let is_active = move || active_tab.get() == tab_id_for_active;
                let is_active_for_tabindex = is_active.clone();
                let is_active_for_style = is_active.clone();
                let tab_label_upper = tab_label.to_uppercase();

                view! {
                    <button
                        role="tab"
                        aria-selected=move || is_active().to_string()
                        aria-controls=format!("tabpanel-{}", tab_id_for_controls)
                        id=format!("tab-{}", tab_id_for_id)
                        class="rams-btn rams-btn--ghost"
                        style=move || {
                            let mut styles = String::from(
                                "border: none; border-radius: 0; padding: var(--rams-space-2) var(--rams-space-4); \
                                 font-family: var(--rams-font-mono); font-size: var(--rams-text-2xs); \
                                 font-weight: var(--rams-weight-bold); text-transform: uppercase; \
                                 letter-spacing: 0.1em; transition: border-color var(--rams-fast), color var(--rams-fast);"
                            );
                            if is_active_for_style() {
                                styles.push_str(
                                    " border-bottom: 2px solid var(--rams-orange); color: var(--rams-foreground);"
                                );
                            } else {
                                styles.push_str(
                                    " border-bottom: 2px solid transparent; color: var(--rams-muted);"
                                );
                            }
                            styles
                        }
                        tabindex=move || {
                            if is_active_for_tabindex() { "0".to_string() } else { "-1".to_string() }
                        }
                        on:click=move |_| {
                            active_tab.set(tab_id_for_click.clone());
                        }
                    >
                        {tab_label_upper}
                    </button>
                }
            }).collect::<Vec<_>>()}
        </nav>
    }
}

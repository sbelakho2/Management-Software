//! Rack sidebar navigation component.
//!
//! Provides [`RackSidebar`] — a vertical navigation rail inspired by industrial
//! equipment racks. Displays the station identifier, navigation links with
//! active-state highlighting, an Andon status indicator, and a logout button.
//!
//! See [`styles/rams.css`](../../styles/rams.css) section 2.2.

use leptos::prelude::*;
use leptos_router::hooks::use_location;

/// Describes a single navigation item in the sidebar.
#[derive(Debug, Clone)]
pub struct NavItem {
    /// Display label (typically uppercase).
    pub label: &'static str,
    /// Route path (e.g. `"/dashboard"`).
    pub path: &'static str,
    /// Simple text icon/indicator character.
    pub icon: &'static str,
}

/// Rack-style sidebar navigation.
///
/// Renders the full navigation tree for the Sensei application. Active route
/// detection is performed via [`use_location`].
///
/// # Example
///
/// ```ignore
/// <RackSidebar username="Operator" on_logout=Some(Box::new(|| state.clear_tokens())) />
/// ```
#[component]
pub fn RackSidebar(
    /// Current user display name.
    #[prop(optional)]
    username: String,
    /// Optional logout click callback — pass `Some(Arc::new(...))` or `None`.
    on_logout: Option<std::sync::Arc<dyn Fn() + Send + Sync + 'static>>,
) -> impl IntoView {
    let location = use_location();
    let pathname = move || location.pathname.get();

    // Item 67: the shell leads with WORK, not departments — Today first,
    // then the TPS work surfaces; departments remain secondary filters.
    // Item 69: operator-facing surfaces (TODAY, WORK, ABNORMALITIES) are
    // visible to everyone; finance/master-data items are role-gated.
    let nav_items = vec![
        NavItem {
            label: "TODAY",
            path: "/today",
            icon: "◉",
        },
        NavItem {
            label: "WORK",
            path: "/tps/standard-work",
            icon: "▣",
        },
        NavItem {
            label: "LSW",
            path: "/tps/lsw",
            icon: "✓",
        },
        NavItem {
            label: "ABNORMALITIES",
            path: "/ops/andons",
            icon: "▲",
        },
        NavItem {
            label: "TIER MEETINGS",
            path: "/tps/tier-meetings",
            icon: "▤",
        },
        NavItem {
            label: "OBEYA",
            path: "/tps/obeya",
            icon: "▦",
        },
        NavItem {
            label: "KANBAN",
            path: "/tps/kanban",
            icon: "▤",
        },
        NavItem {
            label: "WORK CENTERS",
            path: "/tps/work-centers",
            icon: "◆",
        },
        NavItem {
            label: "TOPOLOGY",
            path: "/tps/topology",
            icon: "⬢",
        },
        NavItem {
            label: "TRAINING",
            path: "/tps/training",
            icon: "✦",
        },
        NavItem {
            label: "CTQ",
            path: "/tps/ctq",
            icon: "◆",
        },
        NavItem {
            label: "STATION",
            path: "/station",
            icon: "◈",
        },
        NavItem {
            label: "TEAM LEAD",
            path: "/team-lead",
            icon: "▥",
        },
        NavItem {
            label: "LEARNING",
            path: "/tps/learning",
            icon: "◭",
        },
        NavItem {
            label: "FLOW ECONOMICS",
            path: "/tps/flow-economics",
            icon: "€",
        },
        NavItem {
            label: "AGENT",
            path: "/agent",
            icon: "◆",
        },
        NavItem {
            label: "INTEGRATION",
            path: "/integration",
            icon: "⇄",
        },
        NavItem {
            label: "QUALITY",
            path: "/quality",
            icon: "■",
        },
        NavItem {
            label: "PRODUCTION",
            path: "/production",
            icon: "◆",
        },
        NavItem {
            label: "MAINTENANCE",
            path: "/maintenance",
            icon: "▲",
        },
        NavItem {
            label: "FINANCE",
            path: "/finance",
            icon: "⬡",
        },
        NavItem {
            label: "HR",
            path: "/hr",
            icon: "✦",
        },
        NavItem {
            label: "SUPPLY CHAIN",
            path: "/supply-chain",
            icon: "⬥",
        },
        NavItem {
            label: "OPS",
            path: "/ops",
            icon: "●",
        },
    ];

    view! {
        <aside class="racksidebar">
            <div class="racksidebar-station">
                <span class="dymo-label">"SENSEI-OS"</span>
                <span class="racksidebar-station-id">"STATION-01"</span>
            </div>

            <nav class="racksidebar-nav" aria-label="Main navigation">
                {nav_items
                    .into_iter()
                    .map(|item| {
                        let item_path = item.path.to_string();
                        let item_path_2 = item_path.clone();
                        view! {
                            <a
                                href=item.path
                                class=move || {
                                    if pathname().starts_with(&item_path) {
                                        "racksidebar-item racksidebar-item--active"
                                    } else {
                                        "racksidebar-item"
                                    }
                                }
                                aria-current=move || {
                                    if pathname().starts_with(&item_path_2) { "page" } else { "" }
                                }
                            >
                                <span class="racksidebar-item-icon">{item.icon}</span>
                                <span class="racksidebar-item-label">{item.label}</span>
                            </a>
                        }
                    })
                    .collect::<Vec<_>>()}
            </nav>

            <div class="racksidebar-footer">
                <div class="racksidebar-user">
                    <span class="racksidebar-user-name">{username}</span>
                </div>
                <div class="andon-stack" title="Application connectivity — NOT process health">
                    <div class="andon-light andon-light--green"></div>
                    <span class="rams-text-xs" style="color: var(--rams-muted)">"CONNECTED"</span>
                </div>
                <button
                    class="rams-btn rams-btn--ghost rams-btn--sm"
                    on:click=move |_| { if let Some(ref cb) = on_logout { cb() } }
                >
                    "LOGOUT"
                </button>
            </div>
        </aside>
    }
}

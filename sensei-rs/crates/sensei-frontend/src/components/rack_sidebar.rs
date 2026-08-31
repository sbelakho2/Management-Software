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
    /// Roles that may see this item (item 71/72: operators must NOT see
    /// Integration/Finance/HR — the interface reduces choices by role).
    pub roles: Option<&'static [&'static str]>,
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
    /// The authenticated user's roles — navigation is role-gated
    /// (item 71/72): an operator sees TODAY/WORK/ABNORMALITIES, never
    /// Integration/Finance/HR.
    #[prop(optional)]
    roles: Vec<String>,
    /// Optional logout click callback — pass `Some(Arc::new(...))` or `None`.
    on_logout: Option<std::sync::Arc<dyn Fn() + Send + Sync + 'static>>,
) -> impl IntoView {
    let location = use_location();
    let pathname = move || location.pathname.get();

    // Item 67: the shell leads with WORK, not departments — Today first,
    // then the TPS work surfaces; departments remain secondary filters.
    // Item 69: operator-facing surfaces (TODAY, WORK, ABNORMALITIES) are
    // visible to everyone; finance/master-data items are role-gated.
    // Item 71/72: filter by the caller's roles — an operator sees
    // TODAY/WORK/ABNORMALITIES, never Integration/Finance/HR.
    let is_admin = roles
        .iter()
        .any(|r| r == "admin" || r == "platform_superadmin" || r == "ceo");
    let is_operator = roles.iter().any(|r| r == "operator");
    let is_manager = roles
        .iter()
        .any(|r| r == "manager" || r == "team_lead" || r == "supervisor");
    let can_see = move |item: &NavItem| -> bool {
        match item.roles {
            Some(required) => {
                // Privileged surfaces require an explicit role match.
                required.iter().any(|r| roles.iter().any(|u| u == r))
                    || (is_admin && required.contains(&"admin"))
            }
            // Unrestricted items are visible to everyone — but an operator
            // with NO admin/manager role sees only the operator set (the
            // items themselves carry roles: None for universal ones).
            None => {
                if required_roles_empty() {
                    true
                } else {
                    is_operator || is_manager
                }
            }
        }
    };
    fn required_roles_empty() -> bool {
        false
    }
    let _ = &is_operator;
    let _ = &is_manager;
    let nav_items = vec![
        NavItem {
            label: "TODAY",
            path: "/today",
            icon: "◉",
            roles: None,
        },
        NavItem {
            label: "SEARCH",
            path: "/search",
            icon: "⌕",
            roles: None,
        },
        NavItem {
            label: "WORK",
            path: "/tps/standard-work",
            icon: "▣",
            roles: None,
        },
        NavItem {
            label: "LSW",
            path: "/tps/lsw",
            icon: "✓",
            roles: None,
        },
        NavItem {
            label: "ABNORMALITIES",
            path: "/ops/andons",
            icon: "▲",
            roles: None,
        },
        NavItem {
            label: "TIER MEETINGS",
            path: "/tps/tier-meetings",
            icon: "▤",
            roles: None,
        },
        NavItem {
            label: "OBEYA",
            path: "/tps/obeya",
            icon: "▦",
            roles: None,
        },
        NavItem {
            label: "KANBAN",
            path: "/tps/kanban",
            icon: "▤",
            roles: None,
        },
        NavItem {
            label: "WORK CENTERS",
            path: "/tps/work-centers",
            icon: "◆",
            roles: None,
        },
        NavItem {
            label: "TOPOLOGY",
            path: "/tps/topology",
            icon: "⬢",
            roles: Some(&["admin", "ceo", "manager"]),
        },
        NavItem {
            label: "TRAINING",
            path: "/tps/training",
            icon: "✦",
            roles: None,
        },
        NavItem {
            label: "CTQ",
            path: "/tps/ctq",
            icon: "◆",
            roles: None,
        },
        NavItem {
            label: "STATION",
            path: "/station",
            icon: "◈",
            roles: None,
        },
        NavItem {
            label: "TEAM LEAD",
            path: "/team-lead",
            icon: "▥",
            roles: None,
        },
        NavItem {
            label: "LEARNING",
            path: "/tps/learning",
            icon: "◭",
            roles: Some(&["admin", "ceo", "manager"]),
        },
        NavItem {
            label: "FLOW ECONOMICS",
            path: "/tps/flow-economics",
            icon: "€",
            roles: Some(&["admin", "ceo", "finance"]),
        },
        NavItem {
            label: "AGENT",
            path: "/agent",
            icon: "◆",
            roles: Some(&["admin", "ceo"]),
        },
        NavItem {
            label: "INTEGRATION",
            path: "/integration",
            icon: "⇄",
            roles: Some(&["admin"]),
        },
        NavItem {
            label: "DOC INGESTION",
            path: "/documents/ingestion",
            icon: "◫",
            roles: Some(&["admin"]),
        },
        NavItem {
            label: "QUALITY",
            path: "/quality",
            icon: "■",
            roles: None,
        },
        NavItem {
            label: "PRODUCTION",
            path: "/production",
            icon: "◆",
            roles: None,
        },
        NavItem {
            label: "MAINTENANCE",
            path: "/maintenance",
            icon: "▲",
            roles: None,
        },
        NavItem {
            label: "FINANCE",
            path: "/finance",
            icon: "⬡",
            roles: Some(&["admin", "ceo", "finance"]),
        },
        NavItem {
            label: "HR",
            path: "/hr",
            icon: "✦",
            roles: Some(&["admin", "ceo", "hr"]),
        },
        NavItem {
            label: "SUPPLY CHAIN",
            path: "/supply-chain",
            icon: "⬥",
            roles: None,
        },
        NavItem {
            label: "OPS",
            path: "/ops",
            icon: "●",
            roles: None,
        },
    ];

    view! {
        <aside class="racksidebar">
            <div class="racksidebar-station">
                <span class="dymo-label">"STARZ FORGE"</span>
                // Item 78: the station identity is REAL operational context
                // (site/work-center assignment), never static chrome.
                <StationIdentity />
            </div>

            <nav class="racksidebar-nav" aria-label="Main navigation">
                {nav_items
                    .iter()
                    .filter(|item| can_see(item))
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

/// Item 78: the station identity is REAL operational context — derived
/// from the authenticated principal's profile (its stable id), never
/// static "STATION-01" chrome. The Station page itself shows the
/// operator's assigned work center; this sidebar badge identifies the
/// device/principal the UI is running as.
#[component]
fn StationIdentity() -> impl IntoView {
    let app_state = use_context::<crate::state::AppState>();
    let Some(app_state) = app_state else {
        return view! { <span class="racksidebar-station-id">"UNASSIGNED"</span> }.into_any();
    };
    let user = app_state.user;
    let display = move || match user.get() {
        Some(profile) if profile.id.len() >= 8 => {
            format!("PRINCIPAL {}", &profile.id[..8])
        }
        Some(_) | None => "UNASSIGNED".to_string(),
    };
    view! {
        <span
            class="racksidebar-station-id"
            title="Resolved from the authenticated principal — the Station page shows the assigned work center"
        >
            {display}
        </span>
    }
    .into_any()
}

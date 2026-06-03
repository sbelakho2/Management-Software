//! Root layout and route guard components.
//!
//! Provides the top-level application chrome:
//! - [`RootLayout`] — the outer industrial bezel with status bar, sidebar, and main content area.
//! - [`ProtectedRoute`] — wraps a page in [`RootLayout`] with auth state from [`AppState`].
//! - [`ProtectedShell`] — route-group guard using [`Outlet`] for [`ParentRoute`] nesting.

use leptos::prelude::*;
use leptos_router::components::Outlet;

use crate::components::rack_sidebar::RackSidebar;
use crate::state::AppState;

/// Root industrial bezel layout.
///
/// Wraps child content in the full Rams chassis including:
/// - Top status bar with SENSEI-OS label and user name
/// - Left rack sidebar with navigation
/// - Main content area
/// - Corner screw decorations
///
/// # Example
///
/// ```ignore
/// <RootLayout username="Operator" on_logout=Some(Box::new(|| state.clear_tokens()))>
///     <p>"Content goes here"</p>
/// </RootLayout>
/// ```
#[component]
pub fn RootLayout(
    /// Child content rendered in the main area.
    children: Children,
    /// Current user display name shown in the status bar.
    #[prop(optional)]
    username: String,
    /// Optional logout callback — pass `Some(Box::new(...))` or `None`.
    on_logout: Option<Box<dyn Fn() + 'static>>,
) -> impl IntoView {
    let username_footer = username.clone();

    view! {
        <a class="skip-link" href="#main-content">"SKIP TO MAIN CONTENT"</a>
        <div class="rams-bezel">
            <div class="rams-bezel-inner">
                <RackSidebar username=username on_logout=on_logout />
                <main id="main-content" class="rams-main">
                    {children()}
                </main>
            </div>
            <footer class="rams-status-bar" role="contentinfo">
                <div class="rams-status-bar-left">
                    <span class="dymo-label">"SENSEI-OS"</span>
                    <span class="rams-status-bar-separator">"|"</span>
                    <span class="rams-status-text">"OPERATIONAL"</span>
                </div>
                <div class="rams-status-bar-right">
                    <span class="rams-status-text">{username_footer}</span>
                </div>
            </footer>
            // Corner screws
            <div class="rams-screw rams-screw--tl"></div>
            <div class="rams-screw rams-screw--tr"></div>
            <div class="rams-screw rams-screw--bl"></div>
            <div class="rams-screw rams-screw--br"></div>
        </div>
    }
}

/// Route-level guard that wraps a page in the industrial [`RootLayout`].
///
/// Reads [`AppState`] from the Leptos context to derive the current username
/// and logout handler automatically. Use this as the `view` for protected
/// routes in [`crate::app::App`].
///
/// # Example
///
/// ```ignore
/// <Route path=path!("/dashboard") view=|| view! {
///     <ProtectedRoute><DashboardPage/></ProtectedRoute>
/// } />
/// ```
#[component]
pub fn ProtectedRoute(
    /// Child page content to render inside the layout.
    children: Children,
) -> impl IntoView {
    let app_state =
        use_context::<AppState>().expect("AppState not provided — did you forget provide_context?");

    let username = app_state
        .user
        .get()
        .map(|u| u.name)
        .unwrap_or_else(|| "Operator".into());

    let on_logout = {
        let state = app_state.clone();
        Some(Box::new(move || state.clear_tokens()) as Box<dyn Fn() + 'static>)
    };

    view! {
        <RootLayout username=username on_logout=on_logout>
            {children()}
        </RootLayout>
    }
}

/// Route-group guard that nests all child routes inside the industrial [`RootLayout`].
///
/// Uses [`Outlet`] so it can be used as the `view` of a [`ParentRoute`] that
/// groups multiple authenticated routes under a single layout shell. This is
/// the recommended approach for keeping the route tree concise.
///
/// # Example
///
/// ```ignore
/// <ParentRoute path=path!("/") view=ProtectedShell>
///     <Route path=path!("/dashboard") view=DashboardPage />
///     <ParentRoute path=path!("/quality") view=QualityPage>
///         <Route path=path!("/") view=NcrListPage />
///     </ParentRoute>
/// </ParentRoute>
/// ```
#[component]
pub fn ProtectedShell() -> impl IntoView {
    let app_state =
        use_context::<AppState>().expect("AppState not provided — did you forget provide_context?");

    let username = app_state
        .user
        .get()
        .map(|u| u.name)
        .unwrap_or_else(|| "Operator".into());

    let on_logout = {
        let state = app_state.clone();
        Some(Box::new(move || state.clear_tokens()) as Box<dyn Fn() + 'static>)
    };

    view! {
        <RootLayout username=username on_logout=on_logout>
            <Outlet/>
        </RootLayout>
    }
}

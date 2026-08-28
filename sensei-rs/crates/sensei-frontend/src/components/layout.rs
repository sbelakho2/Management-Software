//! Root layout and route guard components.
//!
//! Provides the top-level application chrome:
//! - [`RootLayout`] — the outer industrial bezel with status bar, sidebar, and main content area.
//! - [`ProtectedRoute`] — guards a page with the [`AuthState`] machine.
//! - [`ProtectedShell`] — route-group guard using [`Outlet`] for [`ParentRoute`] nesting.

use leptos::prelude::*;
use leptos::task::spawn_local;
use leptos_router::components::Outlet;
use leptos_router::hooks::use_navigate;

use crate::components::rack_sidebar::RackSidebar;
use crate::state::{AppState, AuthState};

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
                    <span class="rams-status-text" title="Application infrastructure only — process status comes from live data">"CONNECTED"</span>
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
/// Guards against unauthenticated access:
/// - [`AuthState::Loading`] — renders a loading shell while auth resolves.
/// - [`AuthState::Anonymous`] — redirects to `/login`.
/// - [`AuthState::Authenticated`] — renders the page inside [`RootLayout`]
///   with the profile-derived username (never a hard-coded "Operator").
///
/// Use this as the `view` for individual protected routes.
#[component]
pub fn ProtectedRoute() -> impl IntoView {
    let app_state =
        use_context::<AppState>().expect("AppState not provided — did you forget provide_context?");
    let navigate = use_navigate();

    // Redirect to /login whenever the session becomes anonymous.
    Effect::new(move |_| {
        if matches!(app_state.auth_state.get(), AuthState::Anonymous) {
            navigate("/login", Default::default());
        }
    });

    let username = move || match app_state.auth_state.get() {
        AuthState::Authenticated(profile) => profile.display_name(),
        _ => String::new(),
    };

    let on_logout = {
        let state = app_state.clone();
        move || {
            let state = state.clone();
            spawn_local(async move {
                let _ = state.logout().await;
            });
        }
    };

    // The router renders the matched child route through the Outlet.
    view! {
        {move || {
            // Re-evaluated per render: fresh values keep the outer closure
            // re-callable (leptos requires Fn for reactive re-renders).
            let uname = username();
            let logout = Some(Box::new(on_logout.clone()) as Box<dyn Fn() + 'static>);
            match app_state.auth_state.get() {
                AuthState::Loading => view! {
                    <div
                        role="status"
                        aria-live="polite"
                        style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; gap: 12px; background: #1A1A1A;"
                    >
                        <span
                            aria-hidden="true"
                            style="width: 24px; height: 24px; border: 2px solid transparent; border-top-color: #FFBE00; border-radius: 50%; animation: spin 0.6s linear infinite;"
                        ></span>
                        <p style="font-family: 'JetBrains Mono', monospace; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #666666;">
                            "AUTHENTICATING..."
                        </p>
                    </div>
                }.into_any(),
                AuthState::Anonymous => view! { <div style="min-height: 100vh; background: #1A1A1A;"></div> }.into_any(),
                AuthState::Authenticated(_) => view! {
                    <RootLayout
                        username=uname
                        on_logout=logout
                    >
                        <Outlet/>
                    </RootLayout>
                }.into_any(),
            }
        }}
    }
}

/// Route-group guard that nests all child routes inside the industrial [`RootLayout`].
///
/// Guards every nested route with the [`AuthState`] machine:
/// - [`AuthState::Loading`] — renders a loading shell while auth resolves.
/// - [`AuthState::Anonymous`] — redirects to `/login`.
/// - [`AuthState::Authenticated`] — renders [`RootLayout`] with `<Outlet/>`.
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
    let navigate = use_navigate();

    // Redirect to /login whenever the session becomes anonymous.
    Effect::new(move |_| {
        if matches!(app_state.auth_state.get(), AuthState::Anonymous) {
            navigate("/login", Default::default());
        }
    });

    let username = move || match app_state.auth_state.get() {
        AuthState::Authenticated(profile) => profile.display_name(),
        _ => String::new(),
    };

    let on_logout = {
        let state = app_state.clone();
        move || {
            let state = state.clone();
            spawn_local(async move {
                let _ = state.logout().await;
            });
        }
    };

    view! {
        {move || match app_state.auth_state.get() {
            AuthState::Loading => view! {
                <div
                    role="status"
                    aria-live="polite"
                    style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; gap: 12px; background: #1A1A1A;"
                >
                    <span
                        aria-hidden="true"
                        style="width: 24px; height: 24px; border: 2px solid transparent; border-top-color: #FFBE00; border-radius: 50%; animation: spin 0.6s linear infinite;"
                    ></span>
                    <p style="font-family: 'JetBrains Mono', monospace; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #666666;">
                        "AUTHENTICATING..."
                    </p>
                </div>
            }.into_any(),
            AuthState::Anonymous => view! { <div style="min-height: 100vh; background: #1A1A1A;"></div> }.into_any(),
            AuthState::Authenticated(_) => view! {
                <RootLayout
                    username=username()
                    on_logout=Some(Box::new(on_logout.clone()) as Box<dyn Fn() + 'static>)
                >
                    <Outlet/>
                </RootLayout>
            }.into_any(),
        }}
    }
}

//! Error boundary component that catches rendering errors and displays a
//! Rams-styled fallback UI.

use leptos::error::{ErrorBoundary as LeptosErrorBoundary, Errors};
use leptos::prelude::*;

/// An error boundary component that catches errors in child components
/// and displays a Rams-styled error fallback.
///
/// # Usage
/// ```ignore
/// <ErrorBoundary>
///     <MyFallibleComponent />
/// </ErrorBoundary>
/// ```
#[component]
pub fn ErrorBoundary(
    /// Child components to wrap with error handling.
    children: Children,
) -> impl IntoView {
    // Define the fallback outside the view! macro.
    // Leptos 0.7.8 ErrorBoundary expects FnMut(ArcRwSignal<Errors>) -> impl IntoView.
    let fallback = |_errors: ArcRwSignal<Errors>| {
        view! {
            <div class="rams-error-boundary">
                <div class="rams-error-boundary__container">
                    <div class="rams-error-boundary__icon">"⚠"</div>
                    <h2 class="rams-error-boundary__title">"SYSTEM MALFUNCTION"</h2>
                    <p class="rams-error-boundary__message">
                        "An unexpected error occurred in this section."
                    </p>
                    <p class="rams-error-boundary__sub">
                        "Please contact your system administrator if the problem persists."
                    </p>
                </div>
            </div>
        }
    };

    view! {
        <LeptosErrorBoundary fallback=fallback>
            {children()}
        </LeptosErrorBoundary>
    }
}

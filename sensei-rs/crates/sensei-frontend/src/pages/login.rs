//! Login page component with real API integration.
//!
//! Rams design system — centered module with IndustrialInput fields,
//! DymoLabel branding, and Primary IndustrialButton.
//!
//! # Auth flow
//!
//! 1. `POST /api/v1/auth/login` (via [`AppState::login`]) stores the tokens
//!    in memory and immediately fetches `GET /api/v1/auth/me` so the user
//!    profile is available **before** navigating to the dashboard — the UI
//!    never falls back to a hard-coded "Operator" name.
//! 2. If the profile fetch fails the session is still established (the login
//!    response carries a provisional identity) and a warning with a retry
//!    action is shown.
//! 3. Errors surface the backend `request_id` when present, so failures can
//!    be correlated with server logs.

use crate::state::AppState;
use leptos::prelude::*;
use leptos::task::spawn_local;
use leptos_router::hooks::use_navigate;

use crate::components::button::{ButtonVariant, IndustrialButton};
use crate::components::dymo_label::DymoLabel;
use crate::components::input::IndustrialInput;
use crate::components::module::Module;

/// Login page with email/password form.
#[component]
pub fn LoginPage() -> impl IntoView {
    let email = RwSignal::new(String::new());
    let password = RwSignal::new(String::new());
    let error_msg = RwSignal::new(None::<String>);
    let (submitting, set_submitting) = signal(false);
    // Set when login succeeded but the /auth/me profile fetch failed.
    let (profile_retry, set_profile_retry) = signal(false);

    // Access app state provided at root level
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let navigate = use_navigate();

    let state_submit = app_state.clone();
    let nav_submit = navigate.clone();
    let on_submit = move |ev: leptos::ev::SubmitEvent| {
        ev.prevent_default();
        error_msg.set(None);
        set_profile_retry.set(false);

        let email_val = email.get();
        let password_val = password.get();

        if email_val.is_empty() || password_val.is_empty() {
            error_msg.set(Some("CREDENTIALS REQUIRED".into()));
            return;
        }

        set_submitting.set(true);

        // Clone values for the async block
        let email_clone = email_val.clone();
        let password_clone = password_val.clone();
        let state = state_submit.clone();
        let nav = nav_submit.clone();

        spawn_local(async move {
            // `login` stores the tokens in memory and fetches /auth/me before
            // returning, so the profile is always available on entry.
            match state.login(&email_clone, &password_clone).await {
                Ok(outcome) => {
                    if outcome.profile_fetch_failed {
                        // Session established, but the profile could not be
                        // loaded: surface a warning with a retry action.
                        set_profile_retry.set(true);
                    } else {
                        nav("/dashboard", Default::default());
                    }
                }
                Err(e) => {
                    let msg = match e.status {
                        Some(401) => "INVALID CREDENTIALS".to_string(),
                        Some(429) => "RATE LIMITED - RETRY LATER".to_string(),
                        _ => format!("LOGIN FAILED: {}", e.user_message()),
                    };
                    error_msg.set(Some(msg));
                }
            }
            set_submitting.set(false);
        });
    };

    // Retry the /auth/me profile fetch after a failed initial load.
    let state_retry = app_state.clone();
    let nav_retry = navigate.clone();
    let on_retry_profile = move |ev: leptos::ev::MouseEvent| {
        ev.prevent_default();
        error_msg.set(None);
        set_profile_retry.set(false);
        set_submitting.set(true);

        let state = state_retry.clone();
        let nav = nav_retry.clone();
        spawn_local(async move {
            match state.fetch_profile().await {
                Ok(_) => {
                    nav("/dashboard", Default::default());
                }
                Err(e) => {
                    set_profile_retry.set(true);
                    error_msg.set(Some(format!("PROFILE LOAD FAILED: {}", e.user_message())));
                }
            }
            set_submitting.set(false);
        });
    };

    // Enter the dashboard with the provisional identity from the login
    // response; the profile can be retried from the UI later.
    let nav_continue = navigate.clone();
    let on_continue = move |ev: leptos::ev::MouseEvent| {
        ev.prevent_default();
        nav_continue("/dashboard", Default::default());
    };

    view! {
        <div class="rams-flex rams-flex-center rams-min-h-screen rams-w-full">
            <Module title="AUTHENTICATE".to_string()>
                <div class="rams-p-4">
                    <DymoLabel text="SENSEI-ERP".to_string() variant="default".to_string() />
                </div>
                <form on:submit=on_submit class="rams-flex rams-flex--col rams-gap-4">
                    {move || {
                        // Fresh clones per render keep the outer closure
                        // re-callable (leptos requires Fn).
                        let retry = on_retry_profile.clone();
                        let cont = on_continue.clone();
                        if profile_retry.get() {
                            view! {
                                <div
                                    role="alert"
                                    aria-live="polite"
                                    style="border: 1px solid #FFBE00; background: rgba(255,190,0,0.08); padding: 12px; border-radius: 2px;"
                                >
                                    <p style="font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: #FFBE00; margin-bottom: 8px;">
                                        "SESSION ESTABLISHED - PROFILE LOAD FAILED"
                                    </p>
                                    <div style="display: flex; gap: 8px;">
                                        <button
                                            type="button"
                                            class="rams-btn rams-btn--ghost rams-btn--sm"
                                            on:click=retry
                                        >
                                            "RETRY PROFILE"
                                        </button>
                                        <button
                                            type="button"
                                            class="rams-btn rams-btn--ghost rams-btn--sm"
                                            on:click=cont
                                        >
                                            "CONTINUE"
                                        </button>
                                    </div>
                                </div>
                            }.into_any()
                        } else {
                            ().into_any()
                        }
                    }}

                    <IndustrialInput
                        id="email".to_string()
                        label="Email".to_string()
                        placeholder="user@company.com".to_string()
                        input_type="email".to_string()
                        value=email
                        disabled=submitting.get()
                        error=error_msg
                        _required=true
                    />
                    <IndustrialInput
                        id="password".to_string()
                        label="Password".to_string()
                        placeholder="••••••••".to_string()
                        input_type="password".to_string()
                        value=password
                        disabled=submitting.get()
                        _required=true
                    />
                    <div class="rams-mt-4">
                        <IndustrialButton variant=ButtonVariant::Primary disabled=submitting.get()>
                            {move || if submitting.get() { "AUTHENTICATING..." } else { "AUTHENTICATE" }}
                        </IndustrialButton>
                    </div>
                </form>
            </Module>
        </div>
    }
}

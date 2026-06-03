//! Login page component with real API integration.
//!
//! Rams design system — centered module with IndustrialInput fields,
//! DymoLabel branding, and Primary IndustrialButton.

use crate::api::auth;
use crate::state::{AppState, AuthTokens};
use crate::components::button::{ButtonVariant, IndustrialButton};
use crate::components::dymo_label::DymoLabel;
use crate::components::input::IndustrialInput;
use crate::components::module::Module;
use leptos::prelude::*;
use leptos::task::spawn_local;
use leptos_router::hooks::use_navigate;

/// Login page with email/password form.
#[component]
pub fn LoginPage() -> impl IntoView {
    let email = RwSignal::new(String::new());
    let password = RwSignal::new(String::new());
    let error_msg = RwSignal::new(None::<String>);
    let (submitting, set_submitting) = signal(false);

    // Access app state provided at root level
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let navigate = use_navigate();

    let on_submit = move |ev: leptos::ev::SubmitEvent| {
        ev.prevent_default();
        error_msg.set(None);

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
        let state = app_state.clone();
        let nav = navigate.clone();

        spawn_local(async move {
            let client = state.api_client();
            match auth::login(&client, &email_clone, &password_clone).await {
                Ok(resp) => {
                    // Store tokens in reactive memory only (not localStorage)
                    let tokens = AuthTokens {
                        access_token: resp.access_token.clone(),
                        refresh_token: resp.refresh_token.clone(),
                        token_type: resp.token_type.clone(),
                        expires_in: resp.expires_in,
                    };
                    state.tokens.set(Some(tokens));
                    state.is_authenticated.set(true);

                    // Navigate to dashboard
                    nav("/dashboard", Default::default());
                }
                Err(e) => {
                    let msg = match &e {
                        crate::api::client::ApiError::Status(401) => "INVALID CREDENTIALS".into(),
                        crate::api::client::ApiError::Status(429) => "RATE LIMITED - RETRY LATER".into(),
                        _ => format!("LOGIN FAILED: {}", e),
                    };
                    error_msg.set(Some(msg));
                }
            }
            set_submitting.set(false);
        });
    };

    view! {
        <div class="rams-flex rams-flex-center rams-min-h-screen rams-w-full">
            <Module title="AUTHENTICATE".to_string()>
                <div class="rams-p-4">
                    <DymoLabel text="SENSEI-ERP".to_string() variant="default".to_string() />
                </div>
                <form on:submit=on_submit class="rams-flex rams-flex--col rams-gap-4">
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

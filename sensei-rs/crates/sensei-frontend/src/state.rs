//! Global reactive application state.
//!
//! Provides reactive signals for authentication status, current user,
//! API client configuration, and auth methods shared across all pages.
//!
//! # Security
//! Auth tokens are stored **only in memory** (inside the shared
//! [`ApiClient`], plus the `tokens` signal) and are never persisted to
//! `localStorage`/`sessionStorage`. This eliminates the XSS vector that
//! would otherwise expose credentials to malicious scripts. On page reload
//! the session is RESTORED through the backend's HttpOnly refresh cookie
//! (`refresh_from_cookie`); only when the cookie session is absent/expired
//! does the state become `Anonymous`.

use std::sync::Arc;

use crate::api::auth;
use crate::api::client::{ApiClient, ApiError, AuthTokens};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// Lifecycle state of the application's authentication.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuthState {
    /// Authentication status is being resolved (initial load / refresh).
    Loading,
    /// An authenticated session is active, with the user profile loaded.
    Authenticated(UserProfile),
    /// No session — the user must log in.
    Anonymous,
}

/// User profile as returned by `GET /api/v1/auth/me`.
///
/// Matches the backend `UserProfileResponse` exactly; optional fields carry
/// `#[serde(default)]` so a minimal profile (id/email) still deserialises.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UserProfile {
    pub id: String,
    pub email: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub roles: Vec<String>,
    #[serde(default)]
    pub is_active: bool,
}

impl UserProfile {
    /// Name shown in the status bar. Never falls back to a hard-coded
    /// "Operator": when the profile is incomplete, the email (or an explicit
    /// "UNKNOWN OPERATOR" marker) is shown instead.
    pub fn display_name(&self) -> String {
        if !self.name.is_empty() {
            self.name.clone()
        } else if !self.email.is_empty() {
            self.email.clone()
        } else {
            "UNKNOWN OPERATOR".to_string()
        }
    }
}

/// Outcome of a successful login.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LoginOutcome {
    /// `true` when the session was established but the `/auth/me` profile
    /// fetch failed. The caller should surface a warning and offer a retry.
    pub profile_fetch_failed: bool,
}

/// Top-level app state held in a reactive context.
#[derive(Clone)]
pub struct AppState {
    /// Current authentication state (drives the route guards).
    pub auth_state: RwSignal<AuthState>,
    /// Stored auth tokens (in-memory only — never persisted).
    pub tokens: RwSignal<Option<AuthTokens>>,
    /// Cached user profile.
    pub user: RwSignal<Option<UserProfile>>,
    /// Base URL of the backend API.
    pub api_base: RwSignal<String>,
    /// Derived memo of user roles from profile.
    pub user_roles: Memo<Vec<String>>,
    /// `true` when the last `/auth/me` fetch after login failed (warning +
    /// retry UI).
    pub profile_fetch_failed: RwSignal<bool>,
    /// The single shared API client. All clones share connection pool,
    /// tokens, and the single-flight refresh gate.
    client: ApiClient,
}

impl AppState {
    /// Initialise app state with no persisted tokens (in-memory only).
    pub fn new() -> Self {
        let api_base = std::option_env!("SENSEI_API_BASE")
            .unwrap_or("http://localhost:3000")
            .to_string();
        let api_base_signal = RwSignal::new(api_base.clone());

        let auth_state = RwSignal::new(AuthState::Loading);
        let tokens = RwSignal::new(None);
        let user = RwSignal::new(None);
        let user_roles = Memo::new(move |_| {
            user.get()
                .map(|u: UserProfile| u.roles.clone())
                .unwrap_or_default()
        });

        // One shared client for the whole application.
        let client = ApiClient::new(&api_base);
        // Keep the reactive signal and the client in lockstep: changing
        // api_base reconfigures the client immediately.
        let base_client = client.clone();
        let base_client_hook = base_client.clone();
        let base_hook = api_base_signal;
        base_client.set_auth_hooks(
            Some(Arc::new(move |_| {
                let base = base_hook.get();
                base_client_hook.set_base_url(&base);
            })),
            None,
        );

        // Wire the client's refresh/session-expiry hooks back into reactive
        // state. The hooks capture only signals (Arc-backed), never
        // `AppState` itself, so no reference cycles are created.
        let tokens_hook = tokens;
        let auth_hook = auth_state;
        let user_hook = user;
        client.set_auth_hooks(
            Some(Arc::new(move |updated: AuthTokens| {
                tokens_hook.set(Some(updated));
            })),
            Some(Arc::new(move || {
                user_hook.set(None);
                auth_hook.set(AuthState::Anonymous);
            })),
        );

        Self {
            auth_state,
            tokens,
            user,
            api_base: api_base_signal,
            user_roles,
            profile_fetch_failed: RwSignal::new(false),
            client,
        }
    }

    /// The shared API client. Clones share the same connection pool, bearer
    /// token, refresh token, and single-flight refresh gate, so any clone is
    /// effectively the same instance.
    pub fn api_client(&self) -> ApiClient {
        self.client.clone()
    }

    /// Resolve the initial authentication state.
    ///
    /// Tokens are in-memory only and cannot survive a reload, so on a fresh
    /// page load the state FIRST attempts to restore the session through the
    /// backend's HttpOnly refresh cookie (`POST /auth/refresh` with an empty
    /// body — the cookie carries the credential, JavaScript never sees it).
    /// Only when the cookie session is absent/expired does the state become
    /// `Anonymous`.
    pub async fn resolve_initial_auth(&self) {
        if !matches!(self.auth_state.get(), AuthState::Loading) {
            return;
        }
        if self.tokens.get().is_some() {
            // SSR handoff with tokens in memory: normal single-flight refresh.
            if self.refresh_token().await.is_err() {
                self.clear_tokens();
                self.auth_state.set(AuthState::Anonymous);
            }
            return;
        }

        // Cookie-backed restore: the refresh request carries no body token;
        // the backend reads the HttpOnly cookie instead.
        match self.client.refresh_from_cookie().await {
            Ok(tokens) => {
                self.apply_tokens(tokens);
                match self.fetch_profile().await {
                    Ok(_) => {
                        self.auth_state
                            .set(AuthState::Authenticated(self.user.get().unwrap_or(
                                UserProfile {
                                    id: String::new(),
                                    email: String::new(),
                                    name: String::new(),
                                    roles: Vec::new(),
                                    is_active: true,
                                },
                            )))
                    }
                    Err(_) => {
                        // Session restored but profile fetch failed: enter a
                        // DISTINCT "authenticated but profile unavailable"
                        // state (blank provisional + profile_fetch_failed)
                        // so the UI offers retry instead of pretending the
                        // blank identity is the real profile.
                        self.profile_fetch_failed.set(true);
                        self.auth_state
                            .set(AuthState::Authenticated(self.user.get().unwrap_or(
                                UserProfile {
                                    id: String::new(),
                                    email: String::new(),
                                    name: String::new(),
                                    roles: Vec::new(),
                                    is_active: true,
                                },
                            )));
                    }
                }
            }
            Err(_) => {
                self.clear_tokens();
                self.auth_state.set(AuthState::Anonymous);
            }
        }
    }

    /// Authenticate with email/password via the API.
    ///
    /// On success the tokens are stored in memory **and the user profile is
    /// fetched from `/api/v1/auth/me` before returning** so the UI never has
    /// to fall back to a hard-coded name. If the profile fetch fails the
    /// session is still established (a server-provided provisional identity
    /// from the login response is used) and [`LoginOutcome::profile_fetch_failed`]
    /// is set for the caller to surface a warning + retry.
    pub async fn login(&self, email: &str, password: &str) -> Result<LoginOutcome, ApiError> {
        let resp = auth::login(&self.client, email, password).await?;
        self.apply_tokens(AuthTokens {
            access_token: resp.access_token.clone(),
            refresh_token: resp.refresh_token.clone(),
            token_type: resp.token_type.clone(),
            expires_in: resp.expires_in,
        });

        // Provisional identity derived from the server's login response —
        // only used if /auth/me is unavailable.
        let provisional = UserProfile {
            id: resp.user_id.clone(),
            email: email.to_string(),
            name: String::new(),
            roles: resp.roles.clone(),
            is_active: true,
        };

        self.profile_fetch_failed.set(false);
        match self.fetch_profile_inner().await {
            Ok(profile) => {
                self.user.set(Some(profile.clone()));
                self.auth_state.set(AuthState::Authenticated(profile));
                Ok(LoginOutcome {
                    profile_fetch_failed: false,
                })
            }
            Err(_) => {
                // The session is valid; keep the user authenticated with the
                // provisional identity and flag the failed profile load so
                // the login page can offer a retry.
                self.user.set(Some(provisional.clone()));
                self.auth_state.set(AuthState::Authenticated(provisional));
                self.profile_fetch_failed.set(true);
                Ok(LoginOutcome {
                    profile_fetch_failed: true,
                })
            }
        }
    }

    /// Refresh the access token using the stored refresh token
    /// (single-flight — safe to call concurrently).
    pub async fn refresh_token(&self) -> Result<AuthTokens, ApiError> {
        self.client.refresh_once().await
    }

    /// Fetch the current user's profile from the API and publish it.
    pub async fn fetch_profile(&self) -> Result<UserProfile, ApiError> {
        let profile = self.fetch_profile_inner().await?;
        self.user.set(Some(profile.clone()));
        self.auth_state
            .set(AuthState::Authenticated(profile.clone()));
        self.profile_fetch_failed.set(false);
        Ok(profile)
    }

    async fn fetch_profile_inner(&self) -> Result<UserProfile, ApiError> {
        self.client.get("/api/v1/auth/me").await
    }

    /// Store tokens in the shared client and the reactive signal.
    fn apply_tokens(&self, tokens: AuthTokens) {
        self.client.set_token(&tokens.access_token);
        self.client.set_refresh_token(&tokens.refresh_token);
        self.tokens.set(Some(tokens));
    }

    /// Logout — calls the API to invalidate the session and clears local state.
    pub async fn logout(&self) -> Result<(), ApiError> {
        // Best-effort API call; clear local state regardless of result.
        let _ = auth::logout(&self.client).await;
        self.clear_tokens();
        Ok(())
    }

    /// Clear all auth state (logout / session expiry).
    pub fn clear_tokens(&self) {
        self.client.clear_token();
        self.client.clear_refresh_token();
        self.tokens.set(None);
        self.user.set(None);
        self.auth_state.set(AuthState::Anonymous);
    }

    /// Check whether the current user has a specific role.
    pub fn has_role(&self, role: &str) -> bool {
        self.user
            .get()
            .map(|u| u.roles.iter().any(|r| r == role))
            .unwrap_or(false)
    }

    /// Set the user profile (e.g. after fetching from `/me`).
    pub fn set_user_profile(&self, profile: UserProfile) {
        self.user.set(Some(profile));
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}

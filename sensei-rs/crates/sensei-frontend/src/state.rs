//! Global reactive application state.
//!
//! Provides reactive signals for authentication status, current user,
//! API client configuration, and auth methods shared across all pages.
//!
//! # Security
//! Auth tokens are stored **only in reactive memory** (RwSignal) and are
//! never persisted to localStorage. This eliminates the XSS vector that
//! would otherwise expose credentials to malicious scripts. On page reload,
//! the user must re-authenticate. httpOnly cookie support should be added
//! on the backend for a fully seamless experience.

use crate::api::auth;
use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// Authentication token bundle held in reactive memory only.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthTokens {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: u64,
}

/// Minimal user profile derived from JWT claims or a `/me` endpoint.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserProfile {
    pub id: String,
    pub email: String,
    pub name: String,
    pub tenant_id: String,
    pub roles: Vec<String>,
}

/// Top-level app state held in a reactive context.
#[derive(Debug, Clone)]
pub struct AppState {
    /// Whether the user is authenticated.
    pub is_authenticated: RwSignal<bool>,
    /// Stored auth tokens (in-memory only — never persisted).
    pub tokens: RwSignal<Option<AuthTokens>>,
    /// Cached user profile.
    pub user: RwSignal<Option<UserProfile>>,
    /// Base URL of the backend API.
    pub api_base: RwSignal<String>,
    /// Derived memo of user roles from profile.
    pub user_roles: Memo<Vec<String>>,
}

impl AppState {
    /// Initialise app state with no persisted tokens (in-memory only).
    pub fn new() -> Self {
        let api_base = std::option_env!("SENSEI_API_BASE")
            .unwrap_or("http://localhost:3000")
            .to_string();

        let user = RwSignal::new(None);
        let user_roles = Memo::new(move |_| {
            user.get()
                .map(|u: UserProfile| u.roles.clone())
                .unwrap_or_default()
        });

        Self {
            is_authenticated: RwSignal::new(false),
            tokens: RwSignal::new(None),
            user,
            api_base: RwSignal::new(api_base),
            user_roles,
        }
    }

    /// Clear all auth state (logout).
    pub fn clear_tokens(&self) {
        self.tokens.set(None);
        self.user.set(None);
        self.is_authenticated.set(false);
    }

    /// Build an `ApiClient` configured with the current auth token.
    pub fn api_client(&self) -> ApiClient {
        let base = self.api_base.get();
        let mut client = ApiClient::new(&base);
        if let Some(ref tokens) = self.tokens.get() {
            client.set_token(&tokens.access_token);
        }
        client
    }

    /// Authenticate with email/password via the API.
    ///
    /// On success, stores tokens and marks the user as authenticated.
    /// The caller is responsible for fetching the user profile separately
    /// via [`AppState::set_user_profile`] or [`AppState::fetch_profile`].
    pub async fn login(
        &self,
        email: &str,
        password: &str,
    ) -> Result<auth::LoginResponse, ApiError> {
        let client = self.api_client();
        let resp = auth::login(&client, email, password).await?;
        let tokens = AuthTokens {
            access_token: resp.access_token.clone(),
            refresh_token: resp.refresh_token.clone(),
            token_type: resp.token_type.clone(),
            expires_in: resp.expires_in,
        };
        self.tokens.set(Some(tokens));
        self.is_authenticated.set(true);
        Ok(resp)
    }

    /// Refresh the access token using the stored refresh token.
    pub async fn refresh_token(&self) -> Result<auth::RefreshResponse, ApiError> {
        let refresh_tok = self
            .tokens
            .get()
            .map(|t| t.refresh_token.clone())
            .ok_or_else(|| ApiError::Auth("No refresh token available".into()))?;
        let client = self.api_client();
        let resp = auth::refresh_token(&client, &refresh_tok).await?;
        let tokens = AuthTokens {
            access_token: resp.access_token.clone(),
            refresh_token: resp.refresh_token.clone(),
            token_type: resp.token_type.clone(),
            expires_in: resp.expires_in,
        };
        self.tokens.set(Some(tokens));
        Ok(resp)
    }

    /// Logout — calls the API to invalidate the session and clears local state.
    pub async fn logout(&self) -> Result<(), ApiError> {
        let client = self.api_client();
        // Best-effort API call; clear local state regardless of result.
        let _ = auth::logout(&client).await;
        self.clear_tokens();
        Ok(())
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

    /// Fetch the current user's profile from the API.
    pub async fn fetch_profile(&self) -> Result<UserProfile, ApiError> {
        let client = self.api_client();
        let profile: UserProfile = client.get("/api/v1/auth/me").await?;
        self.user.set(Some(profile.clone()));
        Ok(profile)
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}

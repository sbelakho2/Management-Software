//! Authentication route handlers.
//!
//! Provides login, token refresh, logout, registration, password management,
//! profile management, and email verification endpoints.

use axum::{
    Json,
    extract::{ConnectInfo, FromRequestParts, State},
    http::{HeaderMap, header},
    http::request::Parts,
};
use dashmap::DashMap;
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use sensei_auth::jwt::{AccessTokenClaims, RefreshTokenClaims};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_auth::password::{PasswordCheck, hash_password, validate_password_strength, verify_password};
use sensei_auth::refresh_tokens::TokenReuseDetected;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, now, new_id};
use std::collections::VecDeque;
use std::net::SocketAddr;
use std::time::{Duration as StdDuration, Instant};
use uuid::Uuid;

use crate::middleware::session::session_fingerprint;
use crate::state::{AppState, PasswordResetToken, EmailVerificationToken};
use chrono::{Duration, Utc};

/// Login request body.
#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    /// User email.
    pub email: String,
    /// User password.
    pub password: String,
}

/// Login response body.
#[derive(Debug, Serialize)]
pub struct LoginResponse {
    /// JWT access token.
    pub access_token: String,
    /// Token type (always "Bearer").
    pub token_type: String,
    /// JWT refresh token.
    pub refresh_token: String,
    /// User ID.
    pub user_id: Uuid,
    /// User roles.
    pub roles: Vec<String>,
}

/// Token refresh request body.
#[derive(Debug, Deserialize)]
pub struct RefreshRequest {
    /// Refresh token.
    pub refresh_token: String,
}

/// Registration request body.
#[derive(Debug, Deserialize)]
pub struct RegisterRequest {
    /// User email.
    pub email: String,
    /// User password.
    pub password: String,
    /// User display name.
    pub name: String,
}

/// Profile update request body.
#[derive(Debug, Deserialize)]
pub struct UpdateProfileRequest {
    /// New display name.
    pub name: Option<String>,
    /// New email address.
    pub email: Option<String>,
}

/// Password change request body.
#[derive(Debug, Deserialize)]
pub struct ChangePasswordRequest {
    /// Current password for verification.
    pub old_password: String,
    /// New password.
    pub new_password: String,
}

/// Password reset request body (step 1: request).
#[derive(Debug, Deserialize)]
pub struct PasswordResetRequest {
    /// Email address of the account.
    pub email: String,
}

/// Password reset confirm body (step 2: confirm with token).
#[derive(Debug, Deserialize)]
pub struct PasswordResetConfirmRequest {
    /// The reset token received via email.
    pub token: String,
    /// The new password to set.
    pub new_password: String,
}

/// Email verification request body (step 1: request).
#[derive(Debug, Deserialize)]
pub struct VerifyEmailRequest {
    /// Email address to verify.
    pub email: String,
}

/// Email verification confirm body (step 2: confirm with token).
#[derive(Debug, Deserialize)]
pub struct VerifyEmailConfirmRequest {
    /// The verification token.
    pub token: String,
}

/// Generic message response.
#[derive(Debug, Serialize)]
pub struct MessageResponse {
    pub message: String,
}

/// User profile response.
#[derive(Debug, Serialize)]
pub struct UserProfileResponse {
    pub id: EntityId,
    pub email: String,
    pub name: String,
    pub roles: Vec<String>,
    pub is_active: bool,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

impl From<User> for UserProfileResponse {
    fn from(u: User) -> Self {
        Self {
            id: u.id,
            email: u.email,
            name: u.name,
            roles: u.roles,
            is_active: u.is_active,
            created_at: u.created_at,
            updated_at: u.updated_at,
        }
    }
}

/// Extractor yielding the peer socket address when the router provides
/// connect-info (absent in tests and for servers without
/// `into_make_service_with_connect_info`).
#[derive(Debug, Clone, Copy)]
pub struct OptionalPeer(pub Option<SocketAddr>);

impl<S> FromRequestParts<S> for OptionalPeer
where
    S: Send + Sync,
{
    type Rejection = std::convert::Infallible;

    async fn from_request_parts(
        parts: &mut Parts,
        _state: &S,
    ) -> std::result::Result<Self, Self::Rejection> {
        let peer = parts
            .extensions
            .get::<ConnectInfo<SocketAddr>>()
            .map(|ci| ci.0);
        Ok(Self(peer))
    }
}

/// Max password-reset / email-verification requests per email per hour.
const EMAIL_REQUEST_RATE_LIMIT_PER_HOUR: usize = 3;
/// How long a rate-limit bucket retains timestamps.
const EMAIL_RATE_WINDOW: StdDuration = StdDuration::from_secs(3600);

/// Per-email request timestamps for the auth request endpoints.
static EMAIL_REQUEST_RATE_LIMITS: Lazy<DashMap<String, VecDeque<Instant>>> =
    Lazy::new(DashMap::new);

/// Clear the per-email rate-limit buckets (tests only).
#[cfg(test)]
fn reset_email_rate_limits() {
    EMAIL_REQUEST_RATE_LIMITS.clear();
}

/// Enforce a per-email rate limit for auth request endpoints.
///
/// Returns `true` when the request is allowed. The bucket is pruned of
/// timestamps older than the sliding window before counting.
fn allow_email_request(email: &str) -> bool {
    let now = Instant::now();
    let key = email.trim().to_lowercase();
    let mut bucket = EMAIL_REQUEST_RATE_LIMITS.entry(key).or_default();

    while bucket
        .front()
        .is_some_and(|t| now.duration_since(*t) >= EMAIL_RATE_WINDOW)
    {
        bucket.pop_front();
    }

    if bucket.len() >= EMAIL_REQUEST_RATE_LIMIT_PER_HOUR {
        return false;
    }
    bucket.push_back(now);
    true
}

/// Compute the session fingerprint for the current client, reusing the same
/// logic as the session-binding middleware so login/refresh register the
/// exact fingerprint later requests are verified against.
fn fingerprint_for_request(
    peer: Option<SocketAddr>,
    headers: &HeaderMap,
    state: &AppState,
) -> String {
    let user_agent = headers
        .get(header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string());
    let xff = headers
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok());
    session_fingerprint(
        peer.map(|p| p.ip()),
        xff,
        user_agent.as_deref(),
        &state.config.security.trusted_proxies,
    )
}

/// Issue a fresh token pair for a user, storing the refresh token in the
/// refresh-token store so rotation and reuse detection can be enforced.
async fn issue_token_pair(
    state: &AppState,
    user: &User,
    family_id: Uuid,
) -> Result<LoginResponse> {
    let user_id = user.id;
    let tenant_id = user.tenant_id;
    let roles = user.roles.clone();

    let access_token = state
        .jwt_service
        .issue_access_token(user_id, tenant_id, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let refresh_token = state
        .jwt_service
        .issue_refresh_token(user_id, tenant_id, family_id)
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let expires_at = Utc::now() + Duration::days(state.config.auth.refresh_token_expiry_days);
    state
        .refresh_token_store
        .store(&refresh_token, family_id, user_id, expires_at)
        .await
        .map_err(|e| SenseiError::Internal(format!("Failed to store refresh token: {e}")))?;

    Ok(LoginResponse {
        access_token,
        token_type: "Bearer".to_string(),
        refresh_token,
        user_id,
        roles,
    })
}

/// Extract the bearer access token from the request headers.
fn bearer_access_token(headers: &HeaderMap) -> Option<&str> {
    headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
}

/// Decode an access token from the request headers (returns the claims).
fn access_token_claims(state: &AppState, headers: &HeaderMap) -> Option<AccessTokenClaims> {
    let token = bearer_access_token(headers)?;
    state.jwt_service.validate_access_token(token).ok()
}

/// Handle user login.
///
/// Unknown emails and wrong passwords both produce the same `401` so the
/// endpoint cannot be used to enumerate registered accounts.
pub async fn login(
    State(state): State<AppState>,
    OptionalPeer(peer): OptionalPeer,
    headers: HeaderMap,
    Json(req): Json<LoginRequest>,
) -> Result<Json<LoginResponse>> {
    // Unknown emails surface as NotFound from the users service; both that
    // and a wrong password must produce the same 401 so the endpoint cannot
    // be used to enumerate registered accounts.
    let user = state
        .users_service
        .verify_password(&req.email, &req.password)
        .await
        .map_err(|e| match e {
            SenseiError::NotFound(_) | SenseiError::Unauthorized(_) => {
                SenseiError::Unauthorized("Invalid email or password".to_string())
            }
            other => other,
        })?;

    let family_id = new_id();
    let response = issue_token_pair(&state, &user, family_id).await?;

    // Bind the session to this client's fingerprint.
    let fingerprint = fingerprint_for_request(peer, &headers, &state);
    state
        .session_store
        .register(&user.id.to_string(), fingerprint);

    Ok(Json(response))
}

/// Handle token refresh.
///
/// Rotates the refresh token within its family, revoking the whole family on
/// reuse (a stolen/replayed token). A user lookup failure rejects the
/// request instead of silently downgrading to a default role set.
pub async fn refresh(
    State(state): State<AppState>,
    OptionalPeer(peer): OptionalPeer,
    headers: HeaderMap,
    Json(req): Json<RefreshRequest>,
) -> Result<Json<LoginResponse>> {
    let claims: RefreshTokenClaims = state
        .jwt_service
        .validate_refresh_token(&req.refresh_token)
        .map_err(|_| SenseiError::Unauthorized("Invalid or expired refresh token".to_string()))?;

    let family_id = claims.family_id;
    let new_expires = Utc::now() + Duration::days(state.config.auth.refresh_token_expiry_days);
    let new_refresh_token = state
        .jwt_service
        .issue_refresh_token(claims.sub, claims.tenant_id, family_id)
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    match state
        .refresh_token_store
        .validate_and_rotate(&req.refresh_token, &new_refresh_token, new_expires)
        .await
    {
        Ok((_family, _user)) => {}
        Err(TokenReuseDetected::ReuseDetected) => {
            // A rotated token presented again means it was stolen: kill the
            // whole family so neither the thief nor the victim can continue.
            let _ = state.refresh_token_store.revoke_family(family_id).await;
            return Err(SenseiError::Unauthorized("Token reuse detected".to_string()));
        }
        Err(TokenReuseDetected::Invalid) | Err(TokenReuseDetected::Database(_)) => {
            return Err(SenseiError::Unauthorized(
                "Invalid or expired refresh token".to_string(),
            ));
        }
    }

    // Reload the user from the service; a missing user rejects the request
    // (the token must not silently grant a default role set).
    let user = state
        .users_service
        .find_by_id(claims.sub)
        .await
        .map_err(|_| SenseiError::Unauthorized("Invalid or expired refresh token".to_string()))?;

    let roles = user.roles;
    let access_token = state
        .jwt_service
        .issue_access_token(claims.sub, claims.tenant_id, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    // Re-bind the session to the current client fingerprint.
    let fingerprint = fingerprint_for_request(peer, &headers, &state);
    state
        .session_store
        .register(&claims.sub.to_string(), fingerprint);

    Ok(Json(LoginResponse {
        access_token,
        token_type: "Bearer".to_string(),
        refresh_token: new_refresh_token,
        user_id: claims.sub,
        roles,
    }))
}

/// Register a new user account.
pub async fn register(
    State(state): State<AppState>,
    OptionalPeer(peer): OptionalPeer,
    headers: HeaderMap,
    Json(req): Json<RegisterRequest>,
) -> Result<Json<LoginResponse>> {
    // Validate password strength
    validate_password_strength(&req.password)?;

    // Hash the password
    let password_hash = hash_password(&req.password)?;

    // Check if user already exists
    if state.users_service.find_by_email(&req.email).await.is_ok() {
        return Err(SenseiError::AlreadyExists(format!(
            "User with email '{}' already exists",
            req.email
        )));
    }

    // Create the user — default tenant is a new UUID for self-registration
    let tenant_id = new_id();
    let user = User::new(tenant_id, req.email.clone(), req.name, password_hash);
    let user = state.users_service.create_user(user).await?;

    let family_id = new_id();
    let response = issue_token_pair(&state, &user, family_id).await?;

    // Bind the session to this client's fingerprint.
    let fingerprint = fingerprint_for_request(peer, &headers, &state);
    state
        .session_store
        .register(&user.id.to_string(), fingerprint);

    Ok(Json(response))
}

/// Logout — blacklist the presented access token's `jti`.
///
/// The token's `jti` (plus its expiry timestamp) is stored in the
/// blacklist; the auth middleware rejects any later request presenting the
/// same token. The session binding is removed so the client must
/// re-authenticate.
pub async fn logout(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<MessageResponse>> {
    if let Some(claims) = access_token_claims(&state, &headers) {
        let entry = format!("{}:{}", claims.jti, claims.exp);
        state.blacklisted_tokens.write().await.insert(entry);
    }

    // Drop the session binding: the client must log in again.
    state.session_store.remove(&user.user_id.to_string());

    Ok(Json(MessageResponse {
        message: "Logged out successfully".to_string(),
    }))
}

/// Get the current authenticated user's profile.
pub async fn get_me(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<UserProfileResponse>> {
    let profile = state.users_service.find_by_id(user.user_id).await?;
    Ok(Json(UserProfileResponse::from(profile)))
}

/// Update the current user's profile (name, email).
pub async fn update_me(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<UpdateProfileRequest>,
) -> Result<Json<UserProfileResponse>> {
    let mut profile = state.users_service.find_by_id(user.user_id).await?;

    if let Some(name) = req.name {
        profile.name = name;
    }
    if let Some(email) = req.email {
        // Check if new email is taken
        if email != profile.email
            && state.users_service.find_by_email(&email).await.is_ok()
        {
            return Err(SenseiError::AlreadyExists(format!(
                "Email '{}' is already in use",
                email
            )));
        }
        profile.email = email;
    }

    profile.updated_at = now();
    let updated = state.users_service.update_user(user.user_id, profile).await?;
    Ok(Json(UserProfileResponse::from(updated)))
}

/// Change the current user's password.
pub async fn change_password(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ChangePasswordRequest>,
) -> Result<Json<MessageResponse>> {
    // Verify old password
    let profile = state.users_service.find_by_id(user.user_id).await?;
    match verify_password(&req.old_password, &profile.password_hash)
        .map_err(|e| SenseiError::Internal(format!("Password verification failed: {e}")))?
    {
        PasswordCheck::Valid => {}
        PasswordCheck::Invalid => {
            return Err(SenseiError::Unauthorized(
                "Current password is incorrect".to_string(),
            ));
        }
        PasswordCheck::Malformed => {
            return Err(SenseiError::Internal(
                "Stored password hash is malformed".to_string(),
            ));
        }
    }

    // Validate and hash new password
    validate_password_strength(&req.new_password)?;
    let new_hash = hash_password(&req.new_password)?;

    let mut updated = profile.clone();
    updated.password_hash = new_hash;
    updated.updated_at = now();
    state.users_service.update_user(user.user_id, updated).await?;

    Ok(Json(MessageResponse {
        message: "Password changed successfully".to_string(),
    }))
}

/// Request a password reset (generates a token and sends email).
///
/// Rate-limited per email (max 3/hour) to prevent mailbox flooding.
pub async fn request_password_reset(
    State(state): State<AppState>,
    Json(req): Json<PasswordResetRequest>,
) -> Result<Json<MessageResponse>> {
    if !allow_email_request(&req.email) {
        return Err(SenseiError::HttpError {
            status: 429,
            message: "Too many password reset requests for this email. Try again later.".to_string(),
        });
    }

    // Check if the email exists (don't reveal to caller)
    if let Ok(user) = state.users_service.find_by_email(&req.email).await {
        let tenant_id = user.tenant_id;
        let token = Uuid::new_v4().to_string();
        let reset_token = PasswordResetToken {
            user_id: user.id,
            expires_at: now() + Duration::hours(1),
        };
        {
            let mut tokens = state.password_reset_tokens.write().await;
            // Lazily sweep expired tokens so the map cannot grow unbounded.
            tokens.retain(|_, t| t.expires_at > now());
            tokens.insert(token.clone(), reset_token);
        }

        // Send the password reset email
        if let Err(e) = state
            .email_service
            .send_password_reset(&req.email, &token, tenant_id)
            .await
        {
            tracing::error!(
                email = %req.email,
                error = %e,
                "Failed to send password reset email"
            );
        }
    }

    // Always return success to avoid email enumeration
    Ok(Json(MessageResponse {
        message: "If the email exists, a password reset link has been sent".to_string(),
    }))
}

/// Confirm a password reset with a token.
pub async fn confirm_password_reset(
    State(state): State<AppState>,
    Json(req): Json<PasswordResetConfirmRequest>,
) -> Result<Json<MessageResponse>> {
    let mut tokens = state.password_reset_tokens.write().await;
    let stored = tokens
        .remove(&req.token)
        .ok_or_else(|| SenseiError::Unauthorized("Invalid or expired reset token".to_string()))?;

    if stored.expires_at < now() {
        return Err(SenseiError::Unauthorized("Reset token has expired".to_string()));
    }

    // Validate and hash new password
    validate_password_strength(&req.new_password)?;
    let new_hash = hash_password(&req.new_password)?;

    // Update user's password
    let mut user = state.users_service.find_by_id(stored.user_id).await?;
    user.password_hash = new_hash;
    user.updated_at = now();
    state.users_service.update_user(stored.user_id, user).await?;

    Ok(Json(MessageResponse {
        message: "Password has been reset successfully".to_string(),
    }))
}

/// Request email verification (generates a token and sends email).
///
/// Rate-limited per email (max 3/hour) to prevent mailbox flooding.
pub async fn request_email_verification(
    State(state): State<AppState>,
    Json(req): Json<VerifyEmailRequest>,
) -> Result<Json<MessageResponse>> {
    if !allow_email_request(&req.email) {
        return Err(SenseiError::HttpError {
            status: 429,
            message: "Too many verification requests for this email. Try again later.".to_string(),
        });
    }

    if let Ok(user) = state.users_service.find_by_email(&req.email).await {
        // Already verified users get no new token.
        if !state
            .users_service
            .is_email_verified(user.id)
            .await
            .unwrap_or(false)
        {
            let tenant_id = user.tenant_id;
            let token = Uuid::new_v4().to_string();
            let verification_token = EmailVerificationToken {
                user_id: user.id,
                expires_at: now() + Duration::hours(24),
            };
            {
                let mut tokens = state.email_verification_tokens.write().await;
                // Lazily sweep expired tokens so the map cannot grow unbounded.
                tokens.retain(|_, t| t.expires_at > now());
                tokens.insert(token.clone(), verification_token);
            }

            // Send the email verification link
            if let Err(e) = state
                .email_service
                .send_email_verification(&req.email, &token, tenant_id)
                .await
            {
                tracing::error!(
                    email = %req.email,
                    error = %e,
                    "Failed to send email verification"
                );
            }
        }
    }

    Ok(Json(MessageResponse {
        message: "If the email exists, a verification link has been sent".to_string(),
    }))
}

/// Confirm email verification with a token.
///
/// Marks the user's email as verified in the users service (no more
/// acknowledge-only behavior).
pub async fn confirm_email_verification(
    State(state): State<AppState>,
    Json(req): Json<VerifyEmailConfirmRequest>,
) -> Result<Json<MessageResponse>> {
    let mut tokens = state.email_verification_tokens.write().await;
    let stored = tokens
        .remove(&req.token)
        .ok_or_else(|| SenseiError::Unauthorized("Invalid or expired verification token".to_string()))?;

    if stored.expires_at < now() {
        return Err(SenseiError::Unauthorized("Verification token has expired".to_string()));
    }

    state
        .users_service
        .set_email_verified(stored.user_id, true)
        .await?;

    Ok(Json(MessageResponse {
        message: "Email verified successfully".to_string(),
    }))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use axum::Json;
    use sensei_auth::password::hash_password;
    use sensei_core::config::AppConfig;
    use sensei_core::types::{EntityId, TenantId};
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    /// Helper to build an AppState seeded with a test user.
    async fn test_state() -> (AppState, String, TenantId, EntityId) {
        let password = "Test@1234".to_string();
        let hash = hash_password(&password).unwrap();
        let tenant_id = TenantId::new_v4();
        let users_service = InMemoryUsersService::with_admin(
            "admin@test.com",
            "Admin User",
            &hash,
            tenant_id,
        );
        let users_service = Arc::new(users_service) as Arc<dyn UsersService>;
        let config = AppConfig::from_env().unwrap();
        let state = AppState::new(config, users_service);

        // Get the admin user's ID from the service
        let admin = state.users_service.find_by_email("admin@test.com").await.unwrap();
        let admin_id = admin.id;

        (state, password, tenant_id, admin_id)
    }

    /// Helper to build an AuthenticatedUser for the admin.
    fn admin_user(tenant_id: TenantId, user_id: EntityId) -> AuthenticatedUser {
        AuthenticatedUser {
            user_id,
            tenant_id,
            roles: vec!["admin".to_string()],
        }
    }

    /// Client extractors for a default "client" (no UA, no XFF).
    fn empty_client() -> (OptionalPeer, HeaderMap) {
        // A fixed loopback peer keeps fingerprints deterministic.
        (OptionalPeer(Some(SocketAddr::from(([127, 0, 0, 1], 9999)))), HeaderMap::new())
    }

    #[tokio::test]
    async fn test_login_success() {
        let (state, password, _, _) = test_state().await;
        let req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: password.clone(),
        };
        let (peer, headers) = empty_client();
        let resp = login(State(state.clone()), peer, headers, Json(req)).await.unwrap();
        assert_eq!(resp.token_type, "Bearer");
        assert!(!resp.access_token.is_empty());
        assert!(!resp.refresh_token.is_empty());
        assert!(resp.roles.contains(&"user".to_string()));

        // The refresh token must be registered for rotation.
        let user = state.users_service.find_by_email("admin@test.com").await.unwrap();
        let fp = state.session_store.verify(
            &user.id.to_string(),
            &session_fingerprint(
                Some(SocketAddr::from(([127, 0, 0, 1], 9999)).ip()),
                None,
                None,
                &state.config.security.trusted_proxies,
            ),
        );
        assert_eq!(fp, crate::middleware::session::SessionResult::Matches);
    }

    #[tokio::test]
    async fn test_login_invalid_password() {
        let (state, _, _, _) = test_state().await;
        let req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: "WrongPassword1!".to_string(),
        };
        let (peer, headers) = empty_client();
        let result = login(State(state.clone()), peer, headers, Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_login_user_not_found() {
        let (state, _, _, _) = test_state().await;
        let req = LoginRequest {
            email: "nonexistent@test.com".to_string(),
            password: "SomePass1!".to_string(),
        };
        let (peer, headers) = empty_client();
        let result = login(State(state.clone()), peer, headers, Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_login_unknown_email_and_wrong_password_are_indistinguishable() {
        let (state, _, _, _) = test_state().await;
        let (peer, headers) = empty_client();

        let unknown = LoginRequest {
            email: "nobody@test.com".to_string(),
            password: "SomePass1!".to_string(),
        };
        let wrong = LoginRequest {
            email: "admin@test.com".to_string(),
            password: "SomePass1!".to_string(),
        };

        let unknown_err = login(State(state.clone()), peer, headers.clone(), Json(unknown)).await.unwrap_err();
        let wrong_err = login(State(state.clone()), peer, headers, Json(wrong)).await.unwrap_err();

        // Both must produce the same 401 class with the same message so the
        // endpoint cannot be used to enumerate accounts.
        assert_eq!(unknown_err.http_status(), 401);
        assert_eq!(wrong_err.http_status(), 401);
        assert_eq!(unknown_err.to_string(), wrong_err.to_string());
    }

    #[tokio::test]
    async fn test_register_success() {
        let (state, _, _, _) = test_state().await;
        let req = RegisterRequest {
            email: "newuser@test.com".to_string(),
            password: "StrongPass1!".to_string(),
            name: "New User".to_string(),
        };
        let (peer, headers) = empty_client();
        let resp = register(State(state.clone()), peer, headers, Json(req)).await.unwrap();
        assert_eq!(resp.token_type, "Bearer");
        assert!(!resp.access_token.is_empty());
    }

    #[tokio::test]
    async fn test_register_duplicate_email() {
        let (state, _, _, _) = test_state().await;
        let req = RegisterRequest {
            email: "admin@test.com".to_string(),
            password: "StrongPass1!".to_string(),
            name: "Duplicate".to_string(),
        };
        let (peer, headers) = empty_client();
        let result = register(State(state.clone()), peer, headers, Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_register_weak_password() {
        let (state, _, _, _) = test_state().await;
        let req = RegisterRequest {
            email: "weak@test.com".to_string(),
            password: "short".to_string(),
            name: "Weak".to_string(),
        };
        let (peer, headers) = empty_client();
        let result = register(State(state.clone()), peer, headers, Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_refresh_token() {
        let (state, password, _, _) = test_state().await;
        // First login to get tokens
        let login_req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: password.clone(),
        };
        let (peer, headers) = empty_client();
        let login_resp = login(State(state.clone()), peer.clone(), headers.clone(), Json(login_req)).await.unwrap();

        // Refresh the token
        let refresh_req = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let resp = refresh(State(state.clone()), peer, headers, Json(refresh_req)).await.unwrap();
        assert_eq!(resp.token_type, "Bearer");
        assert!(!resp.access_token.is_empty());
    }

    #[tokio::test]
    async fn test_refresh_token_rotates_and_rejects_reuse() {
        let (state, password, _, _) = test_state().await;
        let login_req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: password.clone(),
        };
        let (peer, headers) = empty_client();
        let login_resp = login(State(state.clone()), peer.clone(), headers.clone(), Json(login_req)).await.unwrap();

        let refresh_req = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let first = refresh(State(state.clone()), peer.clone(), headers.clone(), Json(refresh_req)).await.unwrap();

        // The old token has been rotated: presenting it again is reuse.
        let reuse = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let err = refresh(State(state.clone()), peer.clone(), headers.clone(), Json(reuse)).await.unwrap_err();
        assert!(err.to_string().contains("reuse"), "got: {err}");

        // Reuse detection revokes the WHOLE family, so the rotated-in token
        // must also be dead (neither the thief nor the victim can continue).
        let second = RefreshRequest {
            refresh_token: first.refresh_token.clone(),
        };
        let err2 = refresh(State(state.clone()), peer, headers, Json(second)).await.unwrap_err();
        assert!(
            err2.to_string().contains("Invalid or expired"),
            "family was not revoked after reuse detection: got: {err2}"
        );
    }

    #[tokio::test]
    async fn test_refresh_token_invalid() {
        let (state, _, _, _) = test_state().await;
        let req = RefreshRequest {
            refresh_token: "totally-invalid-token".to_string(),
        };
        let (peer, headers) = empty_client();
        let result = refresh(State(state.clone()), peer, headers, Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_logout_blacklists_token() {
        let (state, password, tenant_id, user_id) = test_state().await;
        let login_req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: password.clone(),
        };
        let (peer, headers) = empty_client();
        let login_resp = login(State(state.clone()), peer, headers.clone(), Json(login_req)).await.unwrap();

        // The access token must be presented on logout to extract its jti.
        let mut logout_headers = HeaderMap::new();
        logout_headers.insert(
            header::AUTHORIZATION,
            format!("Bearer {}", login_resp.access_token).parse().unwrap(),
        );
        let user = admin_user(tenant_id, user_id);
        let _ = logout(user, State(state.clone()), logout_headers).await.unwrap();

        assert!(!state.blacklisted_tokens.read().await.is_empty());

        // The blacklisted token must be rejected by the middleware.
        let req = axum::http::Request::builder()
            .uri("/api/v1/auth/me")
            .header("Authorization", format!("Bearer {}", login_resp.access_token))
            .body(axum::body::Body::empty())
            .unwrap();
        let router = crate::router::build_router(state.clone());
        let resp = tower::ServiceExt::oneshot(router, req).await.unwrap();
        assert_eq!(resp.status(), axum::http::StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn test_get_me() {
        let (state, _, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let resp = get_me(user, State(state.clone())).await.unwrap();
        assert_eq!(resp.email, "admin@test.com");
        assert_eq!(resp.name, "Admin User");
    }

    #[tokio::test]
    async fn test_update_me_name_only() {
        let (state, _, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let req = UpdateProfileRequest {
            name: Some("Updated Name".to_string()),
            email: None,
        };
        let resp = update_me(user, State(state.clone()), Json(req)).await.unwrap();
        assert_eq!(resp.name, "Updated Name");
        assert_eq!(resp.email, "admin@test.com");
    }

    #[tokio::test]
    async fn test_update_me_email_taken() {
        let (state, _, tenant_id, user_id) = test_state().await;
        // Register a second user
        let reg_req = RegisterRequest {
            email: "other@test.com".to_string(),
            password: "StrongPass1!".to_string(),
            name: "Other".to_string(),
        };
        let (peer, headers) = empty_client();
        let _ = register(State(state.clone()), peer, headers, Json(reg_req)).await.unwrap();

        // Try to update admin's email to the other user's email
        let user = admin_user(tenant_id, user_id);
        let req = UpdateProfileRequest {
            name: None,
            email: Some("other@test.com".to_string()),
        };
        let result = update_me(user, State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_change_password_success() {
        let (state, password, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let req = ChangePasswordRequest {
            old_password: password.clone(),
            new_password: "NewStrong1!".to_string(),
        };
        let resp = change_password(user, State(state.clone()), Json(req)).await.unwrap();
        assert_eq!(resp.message, "Password changed successfully");
    }

    #[tokio::test]
    async fn test_change_password_wrong_old() {
        let (state, _, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let req = ChangePasswordRequest {
            old_password: "WrongOld1!".to_string(),
            new_password: "NewStrong1!".to_string(),
        };
        let result = change_password(user, State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_request_password_reset() {
        reset_email_rate_limits();
        let (state, _, _, _) = test_state().await;
        let req = PasswordResetRequest {
            email: "admin@test.com".to_string(),
        };
        let resp = request_password_reset(State(state.clone()), Json(req)).await.unwrap();
        assert!(resp.message.contains("If the email exists"));
    }

    #[tokio::test]
    async fn test_request_password_reset_nonexistent() {
        let (state, _, _, _) = test_state().await;
        // Should still succeed to avoid email enumeration
        let req = PasswordResetRequest {
            email: "doesnotexist@test.com".to_string(),
        };
        let resp = request_password_reset(State(state.clone()), Json(req)).await.unwrap();
        assert!(resp.message.contains("If the email exists"));
    }

    #[tokio::test]
    async fn test_password_reset_rate_limited_per_email() {
        reset_email_rate_limits();
        let (state, _, _, _) = test_state().await;
        for _ in 0..3 {
            let req = PasswordResetRequest {
                email: "rate@test.com".to_string(),
            };
            let _ = request_password_reset(State(state.clone()), Json(req)).await.unwrap();
        }
        let req = PasswordResetRequest {
            email: "rate@test.com".to_string(),
        };
        let err = request_password_reset(State(state.clone()), Json(req)).await.unwrap_err();
        assert_eq!(err.http_status(), 429);
    }

    #[tokio::test]
    async fn test_confirm_password_reset() {
        reset_email_rate_limits();
        let (state, _, _, _) = test_state().await;
        // Request reset first to generate a token for an existing email.
        let req = PasswordResetRequest {
            email: "admin@test.com".to_string(),
        };
        let _ = request_password_reset(State(state.clone()), Json(req)).await.unwrap();

        // Get the token from state
        let token_map = state.password_reset_tokens.read().await;
        let token = token_map.keys().next().unwrap().clone();
        drop(token_map);

        let confirm_req = PasswordResetConfirmRequest {
            token,
            new_password: "ResetPass1!".to_string(),
        };
        let resp = confirm_password_reset(State(state.clone()), Json(confirm_req)).await.unwrap();
        assert_eq!(resp.message, "Password has been reset successfully");
    }

    #[tokio::test]
    async fn test_confirm_password_reset_invalid_token() {
        let (state, _, _, _) = test_state().await;
        let req = PasswordResetConfirmRequest {
            token: "invalid-token".to_string(),
            new_password: "NewPass1!".to_string(),
        };
        let result = confirm_password_reset(State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_request_email_verification() {
        reset_email_rate_limits();
        let (state, _, _, _) = test_state().await;
        let req = VerifyEmailRequest {
            email: "admin@test.com".to_string(),
        };
        let resp = request_email_verification(State(state.clone()), Json(req)).await.unwrap();
        assert!(resp.message.contains("If the email exists"));
    }

    #[tokio::test]
    async fn test_confirm_email_verification() {
        reset_email_rate_limits();
        let (state, _, _, _) = test_state().await;
        // Request verification first for an existing email.
        let req = VerifyEmailRequest {
            email: "admin@test.com".to_string(),
        };
        let _ = request_email_verification(State(state.clone()), Json(req)).await.unwrap();

        // Get the token from state
        let token_map = state.email_verification_tokens.read().await;
        let token = token_map.keys().next().unwrap().clone();
        drop(token_map);

        let confirm_req = VerifyEmailConfirmRequest { token };
        let resp = confirm_email_verification(State(state.clone()), Json(confirm_req)).await.unwrap();
        assert_eq!(resp.message, "Email verified successfully");

        // The user must now actually be marked verified.
        let user = state.users_service.find_by_email("admin@test.com").await.unwrap();
        assert!(state.users_service.is_email_verified(user.id).await.unwrap());
    }

    #[tokio::test]
    async fn test_confirm_email_verification_invalid_token() {
        let (state, _, _, _) = test_state().await;
        let req = VerifyEmailConfirmRequest {
            token: "invalid-token".to_string(),
        };
        let result = confirm_email_verification(State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }
}

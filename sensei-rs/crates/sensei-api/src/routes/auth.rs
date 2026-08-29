//! Authentication route handlers.
//!
//! Provides login, token refresh, logout, registration, password management,
//! profile management, and email verification endpoints.

use axum::response::IntoResponse as _;
use axum::{
    extract::{ConnectInfo, FromRequestParts, State},
    http::request::Parts,
    http::{header, HeaderMap},
    Json,
};
use dashmap::DashMap;
use once_cell::sync::Lazy;
use sensei_auth::jwt::{AccessTokenClaims, RefreshTokenClaims};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_auth::password::{
    hash_password, validate_password_strength, verify_password, PasswordCheck,
};
use sensei_auth::refresh_tokens::TokenReuseDetected;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::net::SocketAddr;
use std::time::{Duration as StdDuration, Instant};
use uuid::Uuid;

use crate::middleware::session::session_fingerprint;
use crate::state::AppState;
use chrono::{Duration, Utc};
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{new_id, now, EntityId};

/// Login request body.
#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    /// User email.
    pub email: String,
    /// User password.
    pub password: String,
}

/// Login response body.
#[derive(Debug, Serialize, Deserialize)]
pub struct LoginResponse {
    /// JWT access token.
    pub access_token: String,
    /// Token type (always "Bearer").
    pub token_type: String,
    /// JWT refresh token. Present in the default (JSON) mode only — in
    /// cookie mode the refresh token travels exclusively in the HttpOnly
    /// cookie and is NEVER serialized into JavaScript-readable JSON.
    #[serde(skip_serializing_if = "String::is_empty")]
    pub refresh_token: String,
    /// Access-token lifetime in seconds.
    pub expires_in: i64,
    /// User ID.
    pub user_id: Uuid,
    /// User roles.
    pub roles: Vec<String>,
}

/// Cookie-mode login/refresh response body.
///
/// The refresh token is NOT included — it exists only in the HttpOnly
/// cookie, so an XSS cannot exfiltrate it from JavaScript.
#[derive(Debug, Serialize)]
pub struct CookieLoginResponse {
    pub access_token: String,
    pub token_type: String,
    pub expires_in: i64,
    pub user_id: Uuid,
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
    /// Optional tenant/workspace name (defaults to the user's display name).
    #[serde(default)]
    pub tenant_name: Option<String>,
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
    /// The tenant scope (item 63): the client needs it to join its own
    /// tenant realtime room.
    pub tenant_id: EntityId,
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
            tenant_id: u.tenant_id,
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
///
/// Item 27: when a shared PostgreSQL pool is attached the counter lives in
/// the `rate_limits` table (atomic UPSERT) so the limit is GLOBAL across
/// API replicas; the in-memory DashMap remains the dev-mode fallback.
async fn allow_email_request(pool: Option<&sqlx::PgPool>, email: &str) -> bool {
    let key = format!("email:{}", email.trim().to_lowercase());
    if let Some(pool) = pool {
        let row = sqlx::query_as::<_, (i64,)>(
            "INSERT INTO rate_limits (key, window_start, count, expires_at) \
             VALUES ($1, NOW(), 1, NOW() + make_interval(secs => $3)) \
             ON CONFLICT (key) DO UPDATE SET \
                 count = CASE \
                     WHEN rate_limits.window_start <= NOW() - make_interval(secs => $2) \
                         THEN 1 \
                     ELSE rate_limits.count + 1 \
                 END, \
                 window_start = CASE \
                     WHEN rate_limits.window_start <= NOW() - make_interval(secs => $2) \
                         THEN NOW() \
                     ELSE rate_limits.window_start \
                 END, \
                 expires_at = NOW() + make_interval(secs => $3) \
             RETURNING count",
        )
        .bind(&key)
        .bind(EMAIL_RATE_WINDOW.as_secs() as i64)
        .bind(EMAIL_RATE_WINDOW.as_secs() as i64 * 5)
        .fetch_one(pool)
        .await;
        match row {
            Ok((count,)) => count as usize <= EMAIL_REQUEST_RATE_LIMIT_PER_HOUR,
            // Store failure: fail OPEN for the safety-net limiter — it is
            // not an authorization boundary (same policy as the primary
            // rate limiter), but the error is logged by the caller path.
            Err(e) => {
                tracing::error!(error = %e, "Shared email rate-limit counter failed");
                true
            }
        }
    } else {
        let now = Instant::now();
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
}

/// Compute the session fingerprint for the current client, reusing the same
/// logic as the session-binding middleware so login/refresh register the
/// exact fingerprint later requests are verified against.
///
/// Name of the HttpOnly refresh-token cookie.
pub const REFRESH_COOKIE_NAME: &str = "sensei_refresh";
/// Lifetime of the refresh cookie (matches the refresh token expiry).
pub const REFRESH_COOKIE_MAX_AGE_SECS: i64 = 30 * 24 * 60 * 60;

/// The user's current credential version (bumped on password change/reset).
///
/// The users service maps `credential_version` onto the `User` entity; the
/// integration agent wires this through once the field lands.
fn credential_version_of(user: &User) -> u64 {
    user.credential_version
}

/// Whether the client asked for cookie-based refresh persistence.
///
/// The legacy HTML frontend sends `X-Use-Cookie: true` on login; the
/// response then carries the refresh token in an HttpOnly cookie instead of
/// exposing it to JavaScript.
fn wants_cookie(headers: &HeaderMap) -> bool {
    headers
        .get("x-use-cookie")
        .and_then(|v| v.to_str().ok())
        .map(|v| v.eq_ignore_ascii_case("true") || v == "1")
        .unwrap_or(false)
}

/// Build the refresh-cookie header value from the config.
///
/// One builder for create AND delete so the path attributes always match:
/// `Path=/api/v1/auth`, `HttpOnly`, `SameSite=Strict`, `Secure` exactly
/// when the environment is production (the parser accepts both `prod` and
/// `production`), and `Max-Age` derived from the configured refresh-token
/// lifetime.
fn refresh_cookie_header(state: &AppState, token: &str) -> String {
    let secure = if state.config.environment.is_prod() {
        "; Secure"
    } else {
        ""
    };
    let max_age = state.config.auth.refresh_token_expiry_days * 24 * 60 * 60;
    format!(
        "{name}={token}; Path=/api/v1/auth; HttpOnly; SameSite=Strict; Max-Age={max_age}{secure}",
        name = REFRESH_COOKIE_NAME,
        token = token,
        max_age = max_age,
        secure = secure,
    )
}

/// Set the HttpOnly refresh cookie on the response.
fn set_refresh_cookie(response: &mut axum::response::Response, state: &AppState, token: &str) {
    use axum::http::header::{HeaderValue, SET_COOKIE};
    let cookie = refresh_cookie_header(state, token);
    if let Ok(value) = HeaderValue::from_str(&cookie) {
        response.headers_mut().append(SET_COOKIE, value);
    }
}

/// Clear the refresh cookie (logout).
fn clear_refresh_cookie(response: &mut axum::response::Response, state: &AppState) {
    use axum::http::header::{HeaderValue, SET_COOKIE};
    // The deletion cookie MUST carry the same Path as creation or the
    // browser keeps the original refresh cookie.
    let secure = if state.config.environment.is_prod() {
        "; Secure"
    } else {
        ""
    };
    let cookie = format!(
        "{name}=; Path=/api/v1/auth; HttpOnly; SameSite=Strict; Max-Age=0{secure}",
        name = REFRESH_COOKIE_NAME,
        secure = secure,
    );
    if let Ok(value) = HeaderValue::from_str(&cookie) {
        response.headers_mut().append(SET_COOKIE, value);
    }
}

/// Extract the refresh token from the cookie header, if present.
fn refresh_token_from_cookie(headers: &HeaderMap) -> Option<String> {
    let cookie_header = headers.get(axum::http::header::COOKIE)?;
    let raw = cookie_header.to_str().ok()?;
    for part in raw.split(';') {
        let part = part.trim();
        if let Some((name, value)) = part.split_once('=') {
            if name.trim() == REFRESH_COOKIE_NAME && !value.is_empty() {
                return Some(value.to_string());
            }
        }
    }
    None
}

fn fingerprint_for_request(
    peer: Option<SocketAddr>,
    headers: &HeaderMap,
    state: &AppState,
) -> String {
    let user_agent = headers
        .get(header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string());
    let xff = headers.get("x-forwarded-for").and_then(|v| v.to_str().ok());
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
    sid: Uuid,
) -> Result<LoginResponse> {
    let user_id = user.id;
    let tenant_id = user.tenant_id;
    let roles = user.roles.clone();

    let access_token = state
        .jwt_service
        .issue_access_token(user_id, tenant_id, sid, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let credential_version = credential_version_of(user);
    let refresh_token = state
        .jwt_service
        .issue_refresh_token(user_id, tenant_id, family_id, credential_version, sid)
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let expires_at = Utc::now() + Duration::days(state.config.auth.refresh_token_expiry_days);
    state
        .refresh_token_store
        .store(
            &refresh_token,
            family_id,
            user_id,
            credential_version,
            expires_at,
        )
        .await
        .map_err(|e| SenseiError::Internal(format!("Failed to store refresh token: {e}")))?;

    Ok(LoginResponse {
        access_token,
        token_type: "Bearer".to_string(),
        refresh_token,
        expires_in: state.config.auth.access_token_expiry_minutes * 60,
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
) -> Result<axum::response::Response> {
    // authenticate() is the single invariant: normalized email, active
    // account, Argon2 hash. Unknown email and wrong password produce the
    // same 401 so the endpoint cannot enumerate accounts.
    let user = state
        .users_service
        .authenticate(&req.email, &req.password)
        .await?;

    let family_id = new_id();
    let sid = new_id();
    let response = issue_token_pair(&state, &user, family_id, sid).await?;

    // Bind this session (sid) to the client's fingerprint.
    let fingerprint = fingerprint_for_request(peer, &headers, &state);
    state
        .session_store
        .register(
            &sid.to_string(),
            &user.id.to_string(),
            user.tenant_id,
            fingerprint,
        )
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to persist session binding");
            SenseiError::Internal("Unable to establish the session. Please retry.".to_string())
        })?;

    // Optional HttpOnly cookie persistence: the refresh token NEVER
    // touches localStorage or JavaScript — it is not even present in the
    // JSON response body in cookie mode.
    if wants_cookie(&headers) {
        let refresh_token = response.refresh_token.clone();
        let cookie_body = CookieLoginResponse {
            access_token: response.access_token.clone(),
            token_type: response.token_type.clone(),
            expires_in: response.expires_in,
            user_id: response.user_id,
            roles: response.roles.clone(),
        };
        let mut resp = Json(cookie_body).into_response();
        set_refresh_cookie(&mut resp, &state, &refresh_token);
        return Ok(resp);
    }

    Ok(Json(response).into_response())
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
) -> Result<axum::response::Response> {
    // The refresh token comes from the body (Leptos) or the HttpOnly cookie
    // (legacy frontend) — never from localStorage.
    let token = if req.refresh_token.is_empty() {
        refresh_token_from_cookie(&headers)
            .ok_or_else(|| SenseiError::Unauthorized("Missing refresh token".to_string()))?
    } else {
        req.refresh_token.clone()
    };

    let claims: RefreshTokenClaims = state
        .jwt_service
        .validate_refresh_token(&token)
        .map_err(|_| SenseiError::Unauthorized("Invalid or expired refresh token".to_string()))?;

    let family_id = claims.family_id;
    // Every refresh starts a NEW session (the old sid is retired when the
    // old access token expires); one user may hold many concurrent sessions.
    let sid = new_id();
    let new_expires = Utc::now() + Duration::days(state.config.auth.refresh_token_expiry_days);
    let new_refresh_token = state
        .jwt_service
        .issue_refresh_token(
            claims.sub,
            claims.tenant_id,
            family_id,
            claims.credential_version,
            sid,
        )
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let credential_version = claims.credential_version;
    match state
        .refresh_token_store
        .validate_and_rotate(&token, &new_refresh_token, credential_version, new_expires)
        .await
    {
        Ok((_family, _user)) => {}
        Err(TokenReuseDetected::ReuseDetected) => {
            // A rotated token presented again means it was stolen: kill the
            // whole family so neither the thief nor the victim can continue.
            // A revocation write failure is NOT swallowed: the response must
            // not imply the family was secured when it was not.
            state
                .refresh_token_store
                .revoke_family(family_id)
                .await
                .map_err(|e| {
                    tracing::error!(
                        error = %e,
                        family_id = %family_id,
                        "Failed to revoke refresh-token family after reuse — ALERT: \
                         the family may still be usable"
                    );
                    SenseiError::Internal(
                        "Token reuse detected but family revocation could not be persisted. \
                         Please retry and alert your administrator."
                            .to_string(),
                    )
                })?;
            return Err(SenseiError::Unauthorized(
                "Token reuse detected".to_string(),
            ));
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
        .issue_access_token(claims.sub, claims.tenant_id, sid, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    // Bind the NEW session to the current client fingerprint.
    let fingerprint = fingerprint_for_request(peer, &headers, &state);
    state
        .session_store
        .register(
            &sid.to_string(),
            &claims.sub.to_string(),
            claims.tenant_id,
            fingerprint,
        )
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to persist refreshed session binding");
            SenseiError::Internal("Unable to establish the session. Please retry.".to_string())
        })?;

    let response = LoginResponse {
        access_token,
        token_type: "Bearer".to_string(),
        refresh_token: new_refresh_token,
        expires_in: state.config.auth.access_token_expiry_minutes * 60,
        user_id: claims.sub,
        roles,
    };
    if wants_cookie(&headers) {
        let refresh_token = response.refresh_token.clone();
        let cookie_body = CookieLoginResponse {
            access_token: response.access_token.clone(),
            token_type: response.token_type.clone(),
            expires_in: response.expires_in,
            user_id: response.user_id,
            roles: response.roles.clone(),
        };
        let mut resp = Json(cookie_body).into_response();
        set_refresh_cookie(&mut resp, &state, &refresh_token);
        return Ok(resp);
    }
    Ok(Json(response).into_response())
}

/// Register a new user account.
pub async fn register(
    State(state): State<AppState>,
    OptionalPeer(peer): OptionalPeer,
    headers: HeaderMap,
    Json(req): Json<RegisterRequest>,
) -> Result<axum::response::Response> {
    // Explicit product decision (SELF_REGISTRATION_ENABLED): Sensei is an
    // enterprise manufacturing platform — public self-registration defaults
    // OFF in production (platform admins create tenants and invite users).
    let self_registration = std::env::var("SELF_REGISTRATION_ENABLED")
        .map(|v| v == "true" || v == "1")
        .unwrap_or_else(|_| {
            // Default: allowed in development, disabled in production.
            !state.config.environment.is_prod()
        });
    if !self_registration {
        return Err(SenseiError::Forbidden(
            "Self-registration is disabled. Contact a platform administrator to create your tenant.".to_string(),
        ));
    }

    // Validate password strength
    validate_password_strength(&req.password)?;

    // Hash the password
    let password_hash = hash_password(&req.password)?;

    // Registration is atomic: the tenant and its initial user are created
    // in a single transaction (users.tenant_id is a FK to tenants).
    let tenant_id = new_id();
    let tenant = sensei_core::domain::entities::Tenant {
        id: tenant_id,
        name: req.tenant_name.clone().unwrap_or_else(|| req.name.clone()),
        slug: format!("tenant-{}", tenant_id.as_simple()),
        is_active: true,
        features: Vec::new(),
        created_at: sensei_core::types::now(),
        updated_at: sensei_core::types::now(),
    };
    let user = User::new(tenant_id, req.email.clone(), req.name, password_hash);
    let user = state
        .users_service
        .create_tenant_with_initial_user(tenant, user)
        .await?;

    let family_id = new_id();
    let sid = new_id();
    let response = issue_token_pair(&state, &user, family_id, sid).await?;

    // Bind this session (sid) to the client's fingerprint.
    let fingerprint = fingerprint_for_request(peer, &headers, &state);
    state
        .session_store
        .register(
            &sid.to_string(),
            &user.id.to_string(),
            user.tenant_id,
            fingerprint,
        )
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to persist session binding");
            SenseiError::Internal("Unable to establish the session. Please retry.".to_string())
        })?;

    // Optional HttpOnly cookie persistence: the refresh token NEVER
    // touches localStorage or JavaScript — it is not even present in the
    // JSON response body in cookie mode.
    if wants_cookie(&headers) {
        let refresh_token = response.refresh_token.clone();
        let cookie_body = CookieLoginResponse {
            access_token: response.access_token.clone(),
            token_type: response.token_type.clone(),
            expires_in: response.expires_in,
            user_id: response.user_id,
            roles: response.roles.clone(),
        };
        let mut resp = Json(cookie_body).into_response();
        set_refresh_cookie(&mut resp, &state, &refresh_token);
        return Ok(resp);
    }

    Ok(Json(response).into_response())
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
) -> Result<axum::response::Response> {
    if let Some(claims) = access_token_claims(&state, &headers) {
        let entry = format!("{}:{}", claims.jti, claims.exp);
        if let Err(e) = state.token_blacklist.insert(entry).await {
            // Revocation persistence failed: do NOT report success.
            tracing::error!(error = %e, "Access-token revocation could not be persisted");
            return Err(SenseiError::Internal(
                "Unable to complete logout — revocation could not be persisted. Please retry."
                    .to_string(),
            ));
        }
    }

    // Revoke the current session binding (this device).
    if let Some(sid) = user.sid {
        if let Err(e) = state.session_store.revoke_session(&sid.to_string()).await {
            tracing::error!(error = %e, "Failed to revoke server-side session");
            return Err(SenseiError::Internal(
                "Unable to complete logout — session revocation could not be persisted. Please retry.".to_string(),
            ));
        }
    }
    // `X-Logout-All: true` revokes every device.
    if headers
        .get("x-logout-all")
        .and_then(|v| v.to_str().ok())
        .is_some_and(|v| v.eq_ignore_ascii_case("true"))
    {
        if let Err(e) = state
            .session_store
            .revoke_all_for_user(&user.user_id.to_string())
            .await
        {
            tracing::error!(error = %e, "Failed to revoke all user sessions");
            return Err(SenseiError::Internal(
                "Unable to complete logout — session revocation could not be persisted. Please retry.".to_string(),
            ));
        }
    }

    // Revoke the user's refresh families: a logged-out refresh token must
    // not be able to mint new access tokens. FAIL CLOSED: if the
    // revocation could not be persisted, the logout must not claim success
    // (a stolen refresh token may still mint credentials).
    if let Err(e) = state
        .refresh_token_store
        .revoke_user_sessions(user.user_id)
        .await
    {
        tracing::error!(error = ?e, user_id = %user.user_id, "Failed to revoke refresh sessions on logout — failing closed");
        return Err(SenseiError::Internal(
            "Unable to complete logout — refresh revocation could not be persisted. Please retry."
                .to_string(),
        ));
    }

    // Clear the HttpOnly refresh cookie when the legacy frontend used it.
    let mut response = Json(MessageResponse {
        message: "Logged out successfully".to_string(),
    })
    .into_response();
    clear_refresh_cookie(&mut response, &state);

    Ok(response)
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
        if email != profile.email && state.users_service.find_by_email(&email).await.is_ok() {
            return Err(SenseiError::AlreadyExists(format!(
                "Email '{}' is already in use",
                email
            )));
        }
        profile.email = email;
    }

    profile.updated_at = now();
    let updated = state
        .users_service
        .update_user(user.tenant_id, user.user_id, profile)
        .await?;
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
    // A password change invalidates every outstanding refresh token and
    // session: bump the credential version so old tokens fail validation.
    updated.credential_version = updated.credential_version.saturating_add(1);
    updated.updated_at = now();
    state
        .users_service
        .update_user(user.tenant_id, user.user_id, updated)
        .await?;

    if let Err(e) = state
        .refresh_token_store
        .revoke_user_sessions(user.user_id)
        .await
    {
        tracing::warn!(error = ?e, user_id = %user.user_id, "Failed to revoke sessions after password change");
    }
    // Revoke every session binding (all devices) — the old password must
    // not keep any session alive.
    state
        .session_store
        .revoke_all_for_user(&user.user_id.to_string())
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to revoke all user sessions");
            SenseiError::Internal("Unable to revoke sessions. Please retry.".to_string())
        })?;

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
    if !allow_email_request(state.db_pool.as_ref().map(|p| p.as_ref()), &req.email).await {
        return Err(SenseiError::HttpError {
            status: 429,
            message: "Too many password reset requests for this email. Try again later."
                .to_string(),
        });
    }

    // Check if the email exists (don't reveal to caller). A lookup failure
    // (e.g. database outage) is NOT the same as "email unknown" — surface
    // it so the user is not silently told the request succeeded.
    let user = match state.users_service.find_by_email(&req.email).await {
        Ok(user) => Some(user),
        Err(SenseiError::NotFound(_)) => None,
        Err(e) => {
            tracing::error!(error = %e, email = %req.email, "Failed to look up email for password reset");
            return Err(SenseiError::Database(
                "Unable to process the password reset request right now. Please try again later."
                    .to_string(),
            ));
        }
    };
    if let Some(user) = user {
        let tenant_id = user.tenant_id;
        let token = Uuid::new_v4().to_string();
        if let Err(e) = state
            .password_reset_store
            .insert(&token, user.id, tenant_id, now() + Duration::hours(1))
            .await
        {
            tracing::error!(error = %e, "Reset-token persistence failed");
            return Err(SenseiError::Internal(
                "Unable to issue a reset token right now. Please retry.".to_string(),
            ));
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
    let stored = match state.password_reset_store.consume(&req.token).await {
        Ok(Some(record)) => record,
        Ok(None) => {
            return Err(SenseiError::Unauthorized(
                "Invalid or expired reset token".to_string(),
            ));
        }
        Err(e) => {
            tracing::error!(error = %e, "Reset-token consume failed");
            return Err(SenseiError::Internal(
                "Unable to validate the reset token right now".to_string(),
            ));
        }
    };

    if stored.expires_at < now() {
        return Err(SenseiError::Unauthorized(
            "Reset token has expired".to_string(),
        ));
    }

    // Validate and hash new password
    validate_password_strength(&req.new_password)?;
    let new_hash = hash_password(&req.new_password)?;

    // Update user's password and bump the credential version: every
    // outstanding refresh token and session must die with the old password.
    let mut user = state.users_service.find_by_id(stored.user_id).await?;
    let caller_tenant = user.tenant_id;
    user.password_hash = new_hash;
    user.credential_version = user.credential_version.saturating_add(1);
    user.updated_at = now();
    state
        .users_service
        .update_user(caller_tenant, stored.user_id, user)
        .await?;

    if let Err(e) = state
        .refresh_token_store
        .revoke_user_sessions(stored.user_id)
        .await
    {
        tracing::warn!(error = ?e, user_id = %stored.user_id, "Failed to revoke sessions after password reset");
    }
    // Revoke every session binding (all devices).
    state
        .session_store
        .revoke_all_for_user(&stored.user_id.to_string())
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to revoke all user sessions");
            SenseiError::Internal("Unable to revoke sessions. Please retry.".to_string())
        })?;

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
    if !allow_email_request(state.db_pool.as_ref().map(|p| p.as_ref()), &req.email).await {
        return Err(SenseiError::HttpError {
            status: 429,
            message: "Too many verification requests for this email. Try again later.".to_string(),
        });
    }

    // Look up the email without revealing existence to the caller. Only a
    // genuine lookup failure (database outage, ...) differs from "unknown
    // email" and must be surfaced.
    let user = match state.users_service.find_by_email(&req.email).await {
        Ok(user) => Some(user),
        Err(SenseiError::NotFound(_)) => None,
        Err(e) => {
            tracing::error!(error = %e, email = %req.email, "Failed to look up email for verification request");
            return Err(SenseiError::Database(
                "Unable to process the verification request right now. Please try again later."
                    .to_string(),
            ));
        }
    };
    if let Some(user) = user {
        // Already verified users get no new token.
        let verified = state
            .users_service
            .is_email_verified(user.id)
            .await
            .map_err(|e| {
                tracing::error!(error = %e, user_id = %user.id, "Failed to check email verification state");
                SenseiError::Database(
                    "Unable to process the verification request right now. Please try again later."
                        .to_string(),
                )
            })?;
        if !verified {
            let tenant_id = user.tenant_id;
            let token = Uuid::new_v4().to_string();
            if let Err(e) = state
                .email_verification_store
                .insert(&token, user.id, user.tenant_id, now() + Duration::hours(24))
                .await
            {
                tracing::error!(error = %e, "Verification-token persistence failed");
                return Err(SenseiError::Internal(
                    "Unable to issue a verification token right now. Please retry.".to_string(),
                ));
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
    let stored = match state.email_verification_store.consume(&req.token).await {
        Ok(Some(record)) => record,
        Ok(None) => {
            return Err(SenseiError::Unauthorized(
                "Invalid or expired verification token".to_string(),
            ));
        }
        Err(e) => {
            tracing::error!(error = %e, "Verification-token consume failed");
            return Err(SenseiError::Internal(
                "Unable to validate the verification token right now".to_string(),
            ));
        }
    };

    if stored.expires_at < now() {
        return Err(SenseiError::Unauthorized(
            "Verification token has expired".to_string(),
        ));
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
    use axum::body::to_bytes;
    use axum::Json;
    use sensei_auth::password::hash_password;
    use sensei_core::config::AppConfig;
    use sensei_core::types::TenantId;
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    /// Parse a handler `Response` body back into a [`LoginResponse`] (the
    /// login/refresh/register handlers return `Response` so they can attach
    /// the HttpOnly refresh cookie).
    async fn unwrap_auth(resp: axum::response::Response) -> LoginResponse {
        let bytes = to_bytes(resp.into_body(), 1024 * 64).await.unwrap();
        serde_json::from_slice(&bytes).unwrap()
    }

    /// Helper to build an AppState seeded with a test user.
    async fn test_state() -> (AppState, String, TenantId, EntityId) {
        let password = "Test@1234".to_string();
        let hash = hash_password(&password).unwrap();
        let tenant_id = TenantId::new_v4();
        let users_service =
            InMemoryUsersService::with_admin("admin@test.com", "Admin User", &hash, tenant_id);
        let users_service = Arc::new(users_service) as Arc<dyn UsersService>;
        let config = AppConfig::from_env().unwrap();
        let state = AppState::new(config, users_service);

        // Get the admin user's ID from the service
        let admin = state
            .users_service
            .find_by_email("admin@test.com")
            .await
            .unwrap();
        let admin_id = admin.id;

        (state, password, tenant_id, admin_id)
    }

    /// Helper to build an AuthenticatedUser for the admin.
    fn admin_user(tenant_id: TenantId, user_id: EntityId) -> AuthenticatedUser {
        AuthenticatedUser {
            user_id,
            tenant_id,
            roles: vec![
                "user".to_string(),
                "tenant_admin".to_string(),
                "production_manager".to_string(),
                "quality_manager".to_string(),
                "purchasing_manager".to_string(),
                "sales_manager".to_string(),
                "finance_manager".to_string(),
                "inventory_manager".to_string(),
                "operator".to_string(),
            ],
            sid: None,
        }
    }

    /// Client extractors for a default "client" (no UA, no XFF).
    fn empty_client() -> (OptionalPeer, HeaderMap) {
        // A fixed loopback peer keeps fingerprints deterministic.
        (
            OptionalPeer(Some(SocketAddr::from(([127, 0, 0, 1], 9999)))),
            HeaderMap::new(),
        )
    }

    #[tokio::test]
    async fn test_login_success() {
        let (state, password, _, _) = test_state().await;
        let req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: password.clone(),
        };
        let (peer, headers) = empty_client();
        let resp = unwrap_auth(
            login(State(state.clone()), peer, headers, Json(req))
                .await
                .unwrap(),
        )
        .await;
        assert_eq!(resp.token_type, "Bearer");
        assert!(!resp.access_token.is_empty());
        assert!(!resp.refresh_token.is_empty());
        assert!(resp.roles.contains(&"user".to_string()));

        // The refresh token must be registered for rotation, and the
        // session binding must exist under the access token's sid.
        let claims = state
            .jwt_service
            .validate_access_token(&resp.access_token)
            .unwrap();
        let user = state
            .users_service
            .find_by_email("admin@test.com")
            .await
            .unwrap();
        let fp = state
            .session_store
            .verify(
                &claims.sid.to_string(),
                &session_fingerprint(
                    Some(SocketAddr::from(([127, 0, 0, 1], 9999)).ip()),
                    None,
                    None,
                    &state.config.security.trusted_proxies,
                ),
            )
            .await
            .unwrap();
        assert_eq!(fp, crate::middleware::session::SessionResult::Matches);
        let _ = user;
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

        let unknown_err = login(State(state.clone()), peer, headers.clone(), Json(unknown))
            .await
            .unwrap_err();
        let wrong_err = login(State(state.clone()), peer, headers, Json(wrong))
            .await
            .unwrap_err();

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
            tenant_name: None,
        };
        let (peer, headers) = empty_client();
        let resp = unwrap_auth(
            register(State(state.clone()), peer, headers, Json(req))
                .await
                .unwrap(),
        )
        .await;
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
            tenant_name: None,
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
            tenant_name: None,
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
        let login_resp = unwrap_auth(
            login(State(state.clone()), peer, headers.clone(), Json(login_req))
                .await
                .unwrap(),
        )
        .await;

        // Refresh the token
        let refresh_req = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let resp = unwrap_auth(
            refresh(State(state.clone()), peer, headers, Json(refresh_req))
                .await
                .unwrap(),
        )
        .await;
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
        let login_resp = unwrap_auth(
            login(State(state.clone()), peer, headers.clone(), Json(login_req))
                .await
                .unwrap(),
        )
        .await;

        let refresh_req = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let first = unwrap_auth(
            refresh(
                State(state.clone()),
                peer,
                headers.clone(),
                Json(refresh_req),
            )
            .await
            .unwrap(),
        )
        .await;

        // The old token has been rotated: presenting it again is reuse.
        let reuse = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let err = refresh(State(state.clone()), peer, headers.clone(), Json(reuse))
            .await
            .unwrap_err();
        assert!(err.to_string().contains("reuse"), "got: {err}");

        // Reuse detection revokes the WHOLE family, so the rotated-in token
        // must also be dead (neither the thief nor the victim can continue).
        let second = RefreshRequest {
            refresh_token: first.refresh_token.clone(),
        };
        let err2 = refresh(State(state.clone()), peer, headers, Json(second))
            .await
            .unwrap_err();
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
        let login_resp = unwrap_auth(
            login(State(state.clone()), peer, headers, Json(login_req))
                .await
                .unwrap(),
        )
        .await;

        // The access token must be presented on logout to extract its jti.
        let mut logout_headers = HeaderMap::new();
        logout_headers.insert(
            header::AUTHORIZATION,
            format!("Bearer {}", login_resp.access_token)
                .parse()
                .unwrap(),
        );
        let user = admin_user(tenant_id, user_id);
        let _ = logout(user, State(state.clone()), logout_headers)
            .await
            .unwrap();

        assert!(!state.token_blacklist.is_empty().await);

        // The blacklisted token must be rejected by the middleware.
        let req = axum::http::Request::builder()
            .uri("/api/v1/auth/me")
            .header(
                "Authorization",
                format!("Bearer {}", login_resp.access_token),
            )
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
        let resp = update_me(user, State(state.clone()), Json(req))
            .await
            .unwrap();
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
            tenant_name: None,
        };
        let (peer, headers) = empty_client();
        let _ = unwrap_auth(
            register(State(state.clone()), peer, headers, Json(reg_req))
                .await
                .unwrap(),
        )
        .await;

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
        let resp = change_password(user, State(state.clone()), Json(req))
            .await
            .unwrap();
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
        let resp = request_password_reset(State(state.clone()), Json(req))
            .await
            .unwrap();
        assert!(resp.message.contains("If the email exists"));
    }

    #[tokio::test]
    async fn test_request_password_reset_nonexistent() {
        let (state, _, _, _) = test_state().await;
        // Should still succeed to avoid email enumeration
        let req = PasswordResetRequest {
            email: "doesnotexist@test.com".to_string(),
        };
        let resp = request_password_reset(State(state.clone()), Json(req))
            .await
            .unwrap();
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
            let _ = request_password_reset(State(state.clone()), Json(req))
                .await
                .unwrap();
        }
        let req = PasswordResetRequest {
            email: "rate@test.com".to_string(),
        };
        let err = request_password_reset(State(state.clone()), Json(req))
            .await
            .unwrap_err();
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
        let _ = request_password_reset(State(state.clone()), Json(req))
            .await
            .unwrap();

        // The token travels in the reset email (the store keeps hashes).
        let token = token_from_sent_email(&state, "admin@test.com").await;

        let confirm_req = PasswordResetConfirmRequest {
            token,
            new_password: "ResetPass1!".to_string(),
        };
        let resp = confirm_password_reset(State(state.clone()), Json(confirm_req))
            .await
            .unwrap();
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
        let resp = request_email_verification(State(state.clone()), Json(req))
            .await
            .unwrap();
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
        let _ = request_email_verification(State(state.clone()), Json(req))
            .await
            .unwrap();

        // The token travels in the verification email (the store keeps
        // hashes).
        let token = token_from_sent_email(&state, "admin@test.com").await;

        let confirm_req = VerifyEmailConfirmRequest { token };
        let resp = confirm_email_verification(State(state.clone()), Json(confirm_req))
            .await
            .unwrap();
        assert_eq!(resp.message, "Email verified successfully");

        // The user must now actually be marked verified.
        let user = state
            .users_service
            .find_by_email("admin@test.com")
            .await
            .unwrap();
        assert!(state
            .users_service
            .is_email_verified(user.id)
            .await
            .unwrap());
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

    /// Extract the one-time token from the captured in-memory email.
    async fn token_from_sent_email(state: &AppState, to: &str) -> String {
        let service = state
            .email_service
            .as_any()
            .downcast_ref::<sensei_services::notifications::InMemoryEmailService>()
            .expect("tests use the in-memory email service");
        let emails = service.get_sent_emails().await;
        let email = emails
            .iter()
            .find(|e| e.to == to)
            .expect("expected a captured email");
        email
            .body
            .split("token=")
            .nth(1)
            .and_then(|s| s.split(|c: char| !c.is_ascii_hexdigit() && c != '-').next())
            .map(|s| s.to_string())
            .expect("expected a token in the email body")
    }
}

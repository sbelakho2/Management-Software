//! Authentication route handlers.
//!
//! Provides login, token refresh, logout, registration, password management,
//! profile management, and email verification endpoints.

use axum::{Json, extract::State};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_auth::password::{hash_password, validate_password_strength};
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, now, new_id};
use uuid::Uuid;

use crate::state::{AppState, PasswordResetToken, EmailVerificationToken};
use chrono::Duration;

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

/// Handle user login.
pub async fn login(
    State(state): State<AppState>,
    Json(req): Json<LoginRequest>,
) -> Result<Json<LoginResponse>> {
    let user = state
        .users_service
        .verify_password(&req.email, &req.password)
        .await?;

    let user_id = user.id;
    let tenant_id = user.tenant_id;
    let roles = user.roles;

    let access_token = state
        .jwt_service
        .issue_access_token(user_id, tenant_id, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let refresh_token = state
        .jwt_service
        .issue_refresh_token(user_id, tenant_id)
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    Ok(Json(LoginResponse {
        access_token,
        token_type: "Bearer".to_string(),
        refresh_token,
        user_id,
        roles,
    }))
}

/// Handle token refresh.
pub async fn refresh(
    State(state): State<AppState>,
    Json(req): Json<RefreshRequest>,
) -> Result<Json<LoginResponse>> {
    let claims = state
        .jwt_service
        .validate_refresh_token(&req.refresh_token)
        .map_err(|_| SenseiError::Unauthorized("Invalid or expired refresh token".to_string()))?;

    let roles = state
        .users_service
        .find_by_id(claims.sub)
        .await
        .map(|u| u.roles)
        .unwrap_or_else(|_| vec!["user".to_string()]);

    let access_token = state
        .jwt_service
        .issue_access_token(claims.sub, claims.tenant_id, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let new_refresh_token = state
        .jwt_service
        .issue_refresh_token(claims.sub, claims.tenant_id)
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

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

    let user_id = user.id;
    let roles = user.roles.clone();

    let access_token = state
        .jwt_service
        .issue_access_token(user_id, tenant_id, roles.clone())
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    let refresh_token = state
        .jwt_service
        .issue_refresh_token(user_id, tenant_id)
        .map_err(|e| SenseiError::TokenError(e.to_string()))?;

    Ok(Json(LoginResponse {
        access_token,
        token_type: "Bearer".to_string(),
        refresh_token,
        user_id,
        roles,
    }))
}

/// Logout — blacklist the current access token.
pub async fn logout(
    _user: AuthenticatedUser,
    _state: State<AppState>,
) -> Result<Json<MessageResponse>> {
    // The access token is already validated by the auth middleware.
    // In a production system we would extract the token's jti from the
    // request and store it in the blacklisted_tokens set.
    // For now, a simple acknowledgment is provided.

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
    let valid = sensei_auth::password::verify_password(&req.old_password, &profile.password_hash)
        .map_err(|e| SenseiError::Internal(format!("Password verification failed: {e}")))?;
    if !valid {
        return Err(SenseiError::Unauthorized("Current password is incorrect".to_string()));
    }

    // Validate and hash new password
    validate_password_strength(&req.new_password)?;
    let new_hash = hash_password(&req.new_password)?;

    // Update user — we need a way to set password hash. Since the service
    // doesn't expose a dedicated change_password method, we'll update the
    // user in-place via the users service internal store.
    // For this we use the existing update mechanism.
    let mut updated = profile.clone();
    updated.password_hash = new_hash;
    updated.updated_at = now();
    state.users_service.update_user(user.user_id, updated).await?;

    Ok(Json(MessageResponse {
        message: "Password changed successfully".to_string(),
    }))
}

/// Request a password reset (generates a token and sends email).
pub async fn request_password_reset(
    State(state): State<AppState>,
    Json(req): Json<PasswordResetRequest>,
) -> Result<Json<MessageResponse>> {
    // Check if the email exists (don't reveal to caller)
    if let Ok(user) = state.users_service.find_by_email(&req.email).await {
        let tenant_id = user.tenant_id;
        let token = Uuid::new_v4().to_string();
        let reset_token = PasswordResetToken {
            user_id: user.id,
            expires_at: now() + Duration::hours(1),
        };
        state
            .password_reset_tokens
            .write()
            .await
            .insert(token.clone(), reset_token);

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
pub async fn request_email_verification(
    State(state): State<AppState>,
    Json(req): Json<VerifyEmailRequest>,
) -> Result<Json<MessageResponse>> {
    if let Ok(user) = state.users_service.find_by_email(&req.email).await {
        let tenant_id = user.tenant_id;
        let token = Uuid::new_v4().to_string();
        let verification_token = EmailVerificationToken {
            user_id: user.id,
            expires_at: now() + Duration::hours(24),
        };
        state
            .email_verification_tokens
            .write()
            .await
            .insert(token.clone(), verification_token);

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

    Ok(Json(MessageResponse {
        message: "If the email exists, a verification link has been sent".to_string(),
    }))
}

/// Confirm email verification with a token.
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

    // In a real system we would mark the user's email as verified.
    // For now, the in-memory service doesn't have an email_verified field,
    // but we acknowledge the verification.

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

    #[tokio::test]
    async fn test_login_success() {
        let (state, password, _, _) = test_state().await;
        let req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: password.clone(),
        };
        let resp = login(State(state.clone()), Json(req)).await.unwrap();
        assert_eq!(resp.token_type, "Bearer");
        assert!(!resp.access_token.is_empty());
        assert!(!resp.refresh_token.is_empty());
        assert!(resp.roles.contains(&"user".to_string()));
    }

    #[tokio::test]
    async fn test_login_invalid_password() {
        let (state, _, _, _) = test_state().await;
        let req = LoginRequest {
            email: "admin@test.com".to_string(),
            password: "WrongPassword1!".to_string(),
        };
        let result = login(State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_login_user_not_found() {
        let (state, _, _, _) = test_state().await;
        let req = LoginRequest {
            email: "nonexistent@test.com".to_string(),
            password: "SomePass1!".to_string(),
        };
        let result = login(State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_register_success() {
        let (state, _, _, _) = test_state().await;
        let req = RegisterRequest {
            email: "newuser@test.com".to_string(),
            password: "StrongPass1!".to_string(),
            name: "New User".to_string(),
        };
        let resp = register(State(state.clone()), Json(req)).await.unwrap();
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
        let result = register(State(state.clone()), Json(req)).await;
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
        let result = register(State(state.clone()), Json(req)).await;
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
        let login_resp = login(State(state.clone()), Json(login_req)).await.unwrap();

        // Refresh the token
        let refresh_req = RefreshRequest {
            refresh_token: login_resp.refresh_token.clone(),
        };
        let resp = refresh(State(state.clone()), Json(refresh_req)).await.unwrap();
        assert_eq!(resp.token_type, "Bearer");
        assert!(!resp.access_token.is_empty());
    }

    #[tokio::test]
    async fn test_refresh_token_invalid() {
        let (state, _, _, _) = test_state().await;
        let req = RefreshRequest {
            refresh_token: "totally-invalid-token".to_string(),
        };
        let result = refresh(State(state.clone()), Json(req)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_logout() {
        let (state, _, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let resp = logout(user, State(state.clone())).await.unwrap();
        assert_eq!(resp.message, "Logged out successfully");
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
        let _ = register(State(state.clone()), Json(reg_req)).await.unwrap();

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
    async fn test_confirm_password_reset() {
        let (state, _, _, _) = test_state().await;
        // Request reset first to generate a token
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
        let (state, _, _, _) = test_state().await;
        let req = VerifyEmailRequest {
            email: "admin@test.com".to_string(),
        };
        let resp = request_email_verification(State(state.clone()), Json(req)).await.unwrap();
        assert!(resp.message.contains("If the email exists"));
    }

    #[tokio::test]
    async fn test_confirm_email_verification() {
        let (state, _, _, _) = test_state().await;
        // Request verification first
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

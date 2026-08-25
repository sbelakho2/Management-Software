//! Authentication API helpers: login, logout, token refresh.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

/// Request body for the login endpoint.
#[derive(Debug, Serialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

/// Response body from a successful login.
#[derive(Debug, Deserialize)]
pub struct LoginResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: u64,
}

/// Response body from a successful token refresh.
#[derive(Debug, Deserialize)]
pub struct RefreshResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: u64,
}

/// Authenticate with email and password.
pub async fn login(
    client: &ApiClient,
    email: &str,
    password: &str,
) -> Result<LoginResponse, ApiError> {
    let request = LoginRequest {
        email: email.to_string(),
        password: password.to_string(),
    };

    client.post("/api/v1/auth/login", &request).await
}

/// Refresh an access token using a valid refresh token.
pub async fn refresh_token(
    client: &ApiClient,
    refresh_token: &str,
) -> Result<RefreshResponse, ApiError> {
    #[derive(Debug, Serialize)]
    struct RefreshRequest {
        refresh_token: String,
    }

    let request = RefreshRequest {
        refresh_token: refresh_token.to_string(),
    };

    client.post("/api/v1/auth/refresh", &request).await
}

/// Logout (invalidate the current session).
pub async fn logout(client: &ApiClient) -> Result<serde_json::Value, ApiError> {
    client
        .post("/api/v1/auth/logout", &serde_json::json!({}))
        .await
}

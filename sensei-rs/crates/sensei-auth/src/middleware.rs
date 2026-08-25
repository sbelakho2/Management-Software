//! Axum authentication middleware.
//!
//! Provides a Tower layer that extracts and validates JWT tokens from
//! incoming requests, attaching user identity information to the request
//! extensions for downstream handlers to use.

use axum::{
    extract::{FromRequestParts, Request},
    http::{header, request::Parts, StatusCode},
    middleware::Next,
    response::Response,
    Json,
};
use sensei_core::error::SenseiError;
use serde::Serialize;
use uuid::Uuid;

use crate::jwt::JwtService;

/// Authenticated user identity extracted from a valid JWT.
#[derive(Debug, Clone)]
pub struct AuthenticatedUser {
    /// The user's unique identifier.
    pub user_id: Uuid,
    /// The tenant this user belongs to.
    pub tenant_id: Uuid,
    /// The user's assigned roles.
    pub roles: Vec<String>,
}

impl AuthenticatedUser {
    /// Returns `true` if the user has the given role.
    pub fn has_role(&self, role: &str) -> bool {
        self.roles.iter().any(|r| r == role)
    }

    /// Returns `true` if the user has any of the given roles.
    pub fn has_any_role(&self, roles: &[&str]) -> bool {
        roles.iter().any(|role| self.has_role(role))
    }
}

/// Error response for auth failures.
#[derive(Debug, Serialize)]
pub struct AuthErrorResponse {
    pub error: String,
    pub message: String,
}

/// Axum middleware for JWT authentication.
///
/// Extracts the `Authorization: Bearer <token>` header, validates the JWT,
/// and inserts [`AuthenticatedUser`] into the request extensions.
pub async fn auth_middleware(
    mut req: Request,
    next: Next,
) -> Result<Response, (StatusCode, Json<AuthErrorResponse>)> {
    let jwt_service = req
        .extensions()
        .get::<JwtService>()
        .cloned()
        .ok_or_else(|| {
            tracing::error!(
                "Auth middleware: JwtService not registered in request extensions; \
                 the application failed to configure JWT authentication"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(AuthErrorResponse {
                    error: "configuration_error".to_string(),
                    message: "JWT service not configured".to_string(),
                }),
            )
        })?;

    // Extract Bearer token from Authorization header
    let token = req
        .headers()
        .get(header::AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
        .ok_or_else(|| {
            (
                StatusCode::UNAUTHORIZED,
                Json(AuthErrorResponse {
                    error: "missing_token".to_string(),
                    message: "Missing or invalid Authorization header".to_string(),
                }),
            )
        })?;

    // Validate the token
    match jwt_service.validate_access_token(token) {
        Ok(claims) => {
            let user = AuthenticatedUser {
                user_id: claims.sub,
                tenant_id: claims.tenant_id,
                roles: claims.roles,
            };
            req.extensions_mut().insert(user);
            Ok(next.run(req).await)
        }
        Err(e) => {
            let message = match &e {
                // A dedicated variant, mapped by the JWT layer from
                // `ErrorKind::ExpiredSignature` — never string matching.
                SenseiError::TokenExpired => "Token has expired",
                _ => "Invalid token",
            };

            Err((
                StatusCode::UNAUTHORIZED,
                Json(AuthErrorResponse {
                    error: "invalid_token".to_string(),
                    message: message.to_string(),
                }),
            ))
        }
    }
}

/// Axum extractor for retrieving the authenticated user from request extensions.
///
/// # Example
///
/// ```ignore
/// async fn protected_handler(user: AuthenticatedUser) -> impl IntoResponse {
///     format!("Hello, user {}!", user.user_id)
/// }
/// ```
impl<S> FromRequestParts<S> for AuthenticatedUser
where
    S: Send + Sync,
{
    type Rejection = (StatusCode, Json<AuthErrorResponse>);

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        parts
            .extensions
            .get::<AuthenticatedUser>()
            .cloned()
            .ok_or_else(|| {
                (
                    StatusCode::UNAUTHORIZED,
                    Json(AuthErrorResponse {
                        error: "not_authenticated".to_string(),
                        message: "Not authenticated".to_string(),
                    }),
                )
            })
    }
}

/// Optional auth extractor (does not reject if no token).
///
/// Allows endpoints to work for both authenticated and unauthenticated users.
pub struct OptionalUser(pub Option<AuthenticatedUser>);

impl<S> FromRequestParts<S> for OptionalUser
where
    S: Send + Sync,
{
    type Rejection = (StatusCode, Json<AuthErrorResponse>);

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        Ok(OptionalUser(
            parts.extensions.get::<AuthenticatedUser>().cloned(),
        ))
    }
}

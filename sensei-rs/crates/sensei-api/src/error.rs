//! API error handling and response formatting.
//!
//! Converts domain errors into structured JSON error responses with
//! appropriate HTTP status codes.

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::{Deserialize, Serialize};
use sensei_core::error::SenseiError;

/// Standard API error response body.
#[derive(Debug, Serialize, Deserialize)]
pub struct ApiErrorResponse {
    /// Error code for programmatic handling.
    pub error: String,
    /// Human-readable error message.
    pub message: String,
    /// Additional details about the error (optional).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
}

/// Unified API error type that can be converted into HTTP responses.
#[derive(Debug)]
pub enum ApiError {
    /// Bad request (400).
    BadRequest(String),
    /// Unauthorized (401).
    Unauthorized(String),
    /// Forbidden (403).
    Forbidden(String),
    /// Not found (404).
    NotFound(String),
    /// Conflict (409).
    Conflict(String),
    /// Unprocessable entity (422).
    Unprocessable(String),
    /// Internal server error (500).
    Internal(String),
    /// Domain error converted from SenseiError.
    Domain(SenseiError),
}

impl ApiError {
    /// Get the HTTP status code for this error.
    pub fn status_code(&self) -> StatusCode {
        match self {
            ApiError::BadRequest(_) => StatusCode::BAD_REQUEST,
            ApiError::Unauthorized(_) => StatusCode::UNAUTHORIZED,
            ApiError::Forbidden(_) => StatusCode::FORBIDDEN,
            ApiError::NotFound(_) => StatusCode::NOT_FOUND,
            ApiError::Conflict(_) => StatusCode::CONFLICT,
            ApiError::Unprocessable(_) => StatusCode::UNPROCESSABLE_ENTITY,
            ApiError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ApiError::Domain(err) => StatusCode::from_u16(err.http_status()).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR),
        }
    }

    /// Get the error code string.
    pub fn error_code(&self) -> String {
        match self {
            ApiError::BadRequest(_) => "bad_request",
            ApiError::Unauthorized(_) => "unauthorized",
            ApiError::Forbidden(_) => "forbidden",
            ApiError::NotFound(_) => "not_found",
            ApiError::Conflict(_) => "conflict",
            ApiError::Unprocessable(_) => "unprocessable",
            ApiError::Internal(_) => "internal_error",
            ApiError::Domain(err) => match err {
                SenseiError::Validation(_) | SenseiError::MissingField(_) | SenseiError::InvalidValue { .. } => "validation_error",
                SenseiError::Unauthorized(_) => "unauthorized",
                SenseiError::TokenError(_) => "token_error",
                SenseiError::TokenExpired => "token_expired",
                SenseiError::Forbidden(_) => "forbidden",
                SenseiError::NotFound(_) => "not_found",
                SenseiError::AlreadyExists(_) => "already_exists",
                _ => "internal_error",
            },
        }
        .to_string()
    }

    fn message(&self) -> String {
        match self {
            ApiError::BadRequest(msg)
            | ApiError::Unauthorized(msg)
            | ApiError::Forbidden(msg)
            | ApiError::NotFound(msg)
            | ApiError::Conflict(msg)
            | ApiError::Unprocessable(msg)
            | ApiError::Internal(msg) => msg.clone(),
            ApiError::Domain(err) => err.to_string(),
        }
    }

    /// Structured `details` payload for the error body.
    ///
    /// Populated when the underlying error carries structured information:
    /// `InvalidValue` exposes the offending field, and `Validation` messages
    /// that mention a quoted field name expose it as best-effort.
    fn details(&self) -> Option<serde_json::Value> {
        match self {
            ApiError::Domain(SenseiError::InvalidValue { field, detail }) => {
                Some(serde_json::json!({ "field": field, "detail": detail }))
            }
            ApiError::Domain(SenseiError::Validation(msg)) => {
                Some(serde_json::json!({ "field": quoted_field(msg) }))
            }
            ApiError::Domain(SenseiError::MissingField(msg)) => {
                Some(serde_json::json!({ "field": quoted_field(msg) }))
            }
            _ => None,
        }
    }
}

/// Best-effort extraction of a quoted field name from a validation message,
/// e.g. `"Field 'name' is required"` → `Some("name")`.
fn quoted_field(msg: &str) -> Option<String> {
    msg.split('\'')
        .nth(1)
        .map(str::trim)
        .filter(|f| !f.is_empty())
        .map(str::to_string)
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = self.status_code();
        let body = ApiErrorResponse {
            error: self.error_code(),
            message: self.message(),
            details: self.details(),
        };

        (status, Json(body)).into_response()
    }
}

impl From<SenseiError> for ApiError {
    fn from(err: SenseiError) -> Self {
        ApiError::Domain(err)
    }
}

/// Convenience function to create a 500 error from any error type.
pub fn internal_error<E: std::fmt::Display>(err: E) -> ApiError {
    ApiError::Internal(err.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn token_expired_maps_to_401_token_expired() {
        let err = ApiError::Domain(SenseiError::TokenExpired);
        assert_eq!(err.status_code(), StatusCode::UNAUTHORIZED);
        assert_eq!(err.error_code(), "token_expired");
        let response = err.into_response();
        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[test]
    fn token_error_maps_to_token_error_code() {
        let err = ApiError::Domain(SenseiError::TokenError("bad token".to_string()));
        assert_eq!(err.status_code(), StatusCode::UNAUTHORIZED);
        assert_eq!(err.error_code(), "token_error");
    }

    #[tokio::test]
    async fn invalid_value_exposes_field_in_details() {
        let err = ApiError::Domain(SenseiError::InvalidValue {
            field: "quantity".to_string(),
            detail: "must be positive".to_string(),
        });
        let response = err.into_response();
        let bytes = axum::body::to_bytes(response.into_body(), 1024)
            .await
            .expect("body readable");
        let body: ApiErrorResponse = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(body.error, "validation_error");
        let details = body.details.expect("details populated");
        assert_eq!(details["field"], "quantity");
        assert_eq!(details["detail"], "must be positive");
    }

    #[test]
    fn validation_message_field_is_extracted() {
        assert_eq!(quoted_field("Field 'name' is required"), Some("name".to_string()));
        assert_eq!(quoted_field("Invalid email format"), None);
        assert_eq!(quoted_field(""), None);
    }
}

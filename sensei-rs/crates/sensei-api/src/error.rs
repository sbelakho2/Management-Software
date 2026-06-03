//! API error handling and response formatting.
//!
//! Converts domain errors into structured JSON error responses with
//! appropriate HTTP status codes.

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Serialize;
use sensei_core::error::SenseiError;

/// Standard API error response body.
#[derive(Debug, Serialize)]
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
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = self.status_code();
        let body = ApiErrorResponse {
            error: self.error_code(),
            message: self.message(),
            details: None,
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

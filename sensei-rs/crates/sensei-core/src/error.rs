//! Unified error types for the Sensei ERP system.
//!
//! Provides a comprehensive error hierarchy that can be used across all crates.
//! Uses [`thiserror`] for derive-based error implementations.
//!
//! # Axum Integration
//!
//! [`SenseiError`] implements [`IntoResponse`](axum::response::IntoResponse) via the
//! `axum` feature flag, enabling its use as the error type in Axum handlers.

use thiserror::Error;

/// Unified error type for the entire Sensei system.
///
/// This enum captures all possible error categories that can occur
/// across backend services, from database failures to authentication issues.
#[derive(Error, Debug)]
pub enum SenseiError {
    // ── Database Errors ──────────────────────────────────────────────
    /// A database operation failed.
    #[error("Database error: {0}")]
    Database(String),

    /// A database connection could not be established.
    #[error("Database connection failed: {0}")]
    DatabaseConnection(String),

    /// A query returned no results when results were expected.
    #[error("Entity not found: {0}")]
    NotFound(String),

    /// An entity with the given key already exists.
    #[error("Entity already exists: {0}")]
    AlreadyExists(String),

    // ── Validation Errors ────────────────────────────────────────────
    /// Input validation failed.
    #[error("Validation error: {0}")]
    Validation(String),

    /// A required field was missing.
    #[error("Missing required field: {0}")]
    MissingField(String),

    /// An invalid value was provided.
    #[error("Invalid value for {field}: {detail}")]
    InvalidValue {
        /// The field name.
        field: String,
        /// A description of the validation failure.
        detail: String,
    },

    // ── Authentication / Authorization ───────────────────────────────
    /// Authentication failed (invalid credentials, expired token, etc.).
    #[error("Authentication failed: {0}")]
    Unauthorized(String),

    /// The user does not have permission to perform the action.
    #[error("Forbidden: {0}")]
    Forbidden(String),

    /// A token operation failed.
    #[error("Token error: {0}")]
    TokenError(String),

    /// A token has expired.
    #[error("Token has expired")]
    TokenExpired,

    // ── Event Bus Errors ─────────────────────────────────────────────
    /// An event bus operation failed.
    #[error("Event bus error: {0}")]
    EventBus(String),

    /// Publishing an event failed.
    #[error("Failed to publish event: {0}")]
    PublishError(String),

    /// Subscribing to an event failed.
    #[error("Failed to subscribe to event: {0}")]
    SubscribeError(String),

    // ── External Service Errors ──────────────────────────────────────
    /// An external API call failed.
    #[error("External service error: {0}")]
    ExternalService(String),

    /// An HTTP request failed.
    #[error("HTTP error: {status} - {message}")]
    HttpError {
        /// The HTTP status code.
        status: u16,
        /// The error message.
        message: String,
    },

    /// A request timed out.
    #[error("Request timed out: {0}")]
    Timeout(String),

    // ── Conflict / Constraint Errors ─────────────────────────────────
    /// A conflict occurred (e.g., WIP limit exceeded, resource contention).
    #[error("Conflict: {0}")]
    Conflict(String),

    // ── Configuration Errors ─────────────────────────────────────────
    /// A configuration error occurred.
    #[error("Configuration error: {0}")]
    Configuration(String),

    /// A required environment variable is missing.
    #[error("Missing environment variable: {0}")]
    MissingEnvVar(String),

    // ── Internal Errors ──────────────────────────────────────────────
    /// An unexpected internal error occurred.
    #[error("Internal error: {0}")]
    Internal(String),

    /// A serialization/deserialization error occurred.
    #[error("Serialization error: {0}")]
    Serialization(String),

    /// An I/O error occurred.
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    // ── Concurrency Errors ───────────────────────────────────────────
    /// A lock acquisition failed (timeout/poison).
    #[error("Lock error: {0}")]
    LockError(String),

    /// A channel send/receive operation failed.
    #[error("Channel error: {0}")]
    ChannelError(String),
}

/// Convenience result alias using [`SenseiError`].
pub type Result<T> = std::result::Result<T, SenseiError>;

/// Axum [`IntoResponse`] implementation for [`SenseiError`].
///
/// Maps each error variant to an appropriate HTTP status code and JSON body.
#[cfg(feature = "axum")]
impl axum::response::IntoResponse for SenseiError {
    fn into_response(self) -> axum::response::Response {
        use axum::http::StatusCode;
        use axum::Json;

        let (status, message) = match &self {
            // 4xx Client Errors
            SenseiError::Validation(msg) | SenseiError::MissingField(msg) => {
                (StatusCode::BAD_REQUEST, msg.clone())
            }
            SenseiError::InvalidValue { field, detail } => {
                (StatusCode::BAD_REQUEST, format!("{field}: {detail}"))
            }
            SenseiError::Unauthorized(msg) | SenseiError::TokenError(msg) => {
                (StatusCode::UNAUTHORIZED, msg.clone())
            }
            SenseiError::TokenExpired => {
                (StatusCode::UNAUTHORIZED, "Token has expired".to_string())
            }
            SenseiError::Forbidden(msg) => (StatusCode::FORBIDDEN, msg.clone()),
            SenseiError::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            SenseiError::AlreadyExists(msg) | SenseiError::Conflict(msg) => {
                (StatusCode::CONFLICT, msg.clone())
            }
            SenseiError::Timeout(msg) => (StatusCode::REQUEST_TIMEOUT, msg.clone()),

            // 5xx Server Errors
            SenseiError::Database(msg)
            | SenseiError::DatabaseConnection(msg)
            | SenseiError::EventBus(msg)
            | SenseiError::PublishError(msg)
            | SenseiError::SubscribeError(msg)
            | SenseiError::ExternalService(msg)
            | SenseiError::Configuration(msg)
            | SenseiError::MissingEnvVar(msg)
            | SenseiError::Internal(msg)
            | SenseiError::Serialization(msg)
            | SenseiError::LockError(msg)
            | SenseiError::ChannelError(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
            SenseiError::HttpError { status, message } => (
                StatusCode::from_u16(*status).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR),
                message.clone(),
            ),
            SenseiError::Io(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
        };

        let body = serde_json::json!({
            "error": status.as_u16(),
            "message": message,
        });

        (status, Json(body)).into_response()
    }
}

impl SenseiError {
    /// Returns `true` if the error is a client-side error (4xx).
    pub fn is_client_error(&self) -> bool {
        matches!(
            self,
            SenseiError::Validation(_)
                | SenseiError::MissingField(_)
                | SenseiError::InvalidValue { .. }
                | SenseiError::Unauthorized(_)
                | SenseiError::Forbidden(_)
                | SenseiError::TokenError(_)
                | SenseiError::TokenExpired
                | SenseiError::NotFound(_)
                | SenseiError::AlreadyExists(_)
                | SenseiError::Conflict(_)
        )
    }

    /// Returns `true` if the error is a server-side error (5xx).
    pub fn is_server_error(&self) -> bool {
        !self.is_client_error()
    }

    /// Convert to an HTTP status code number.
    pub fn http_status(&self) -> u16 {
        match self {
            SenseiError::Validation(_)
            | SenseiError::MissingField(_)
            | SenseiError::InvalidValue { .. } => 400,
            SenseiError::Unauthorized(_)
            | SenseiError::TokenError(_)
            | SenseiError::TokenExpired => 401,
            SenseiError::Forbidden(_) => 403,
            SenseiError::NotFound(_) => 404,
            SenseiError::AlreadyExists(_) | SenseiError::Conflict(_) => 409,
            SenseiError::Timeout(_) => 408,
            SenseiError::HttpError { status, .. } => *status,
            SenseiError::Database(_)
            | SenseiError::DatabaseConnection(_)
            | SenseiError::EventBus(_)
            | SenseiError::PublishError(_)
            | SenseiError::SubscribeError(_)
            | SenseiError::ExternalService(_)
            | SenseiError::Configuration(_)
            | SenseiError::MissingEnvVar(_)
            | SenseiError::Internal(_)
            | SenseiError::Serialization(_)
            | SenseiError::Io(_)
            | SenseiError::LockError(_)
            | SenseiError::ChannelError(_) => 500,
        }
    }
}

// Allow conversion from Box<dyn std::error::Error>
impl From<Box<dyn std::error::Error + Send + Sync>> for SenseiError {
    fn from(err: Box<dyn std::error::Error + Send + Sync>) -> Self {
        SenseiError::Internal(err.to_string())
    }
}

impl From<serde_json::Error> for SenseiError {
    fn from(err: serde_json::Error) -> Self {
        SenseiError::Serialization(err.to_string())
    }
}

impl From<uuid::Error> for SenseiError {
    fn from(err: uuid::Error) -> Self {
        SenseiError::Internal(err.to_string())
    }
}

//! Request validation guard middleware.
//!
//! Validates incoming requests against configurable constraints:
//!
//! 1. **Body size** — rejects requests whose `Content-Length` exceeds a
//!    configurable maximum.
//! 2. **Method restriction** — blocks specific HTTP methods on matching
//!    path prefixes (e.g., forbid `DELETE` on `/api/admin/readonly`).
//! 3. **Request timeout** — returns `408 Request Timeout` if the inner
//!    handler takes longer than the configured limit.

use axum::{
    extract::Request,
    http::{Method, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use serde::Serialize;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::time::timeout;
use tracing::warn;

/// Internal error body for guard rejections.
#[derive(Serialize)]
struct GuardError {
    error: String,
    message: String,
}

/// Configuration for the request guard middleware.
#[derive(Clone, Debug)]
pub struct RequestGuardConfig {
    /// Maximum allowed request body size in bytes (default: 10 MB).
    pub max_body_size: u64,
    /// Per-path-prefix method restrictions.
    pub method_restrictions: Arc<HashMap<String, Vec<String>>>,
    /// Maximum time (seconds) allowed for the inner handler to complete.
    pub request_timeout_secs: u64,
}

impl Default for RequestGuardConfig {
    fn default() -> Self {
        Self {
            max_body_size: 10 * 1024 * 1024, // 10 MB
            method_restrictions: Arc::new(HashMap::new()),
            request_timeout_secs: 60,
        }
    }
}

/// Check whether the request body exceeds the configured maximum size.
///
/// Returns `Ok(())` if the body is within limits (or the `Content-Length`
/// header is absent), and `Err(Response)` with a `413 Payload Too Large`
/// error otherwise.
#[allow(clippy::result_large_err)]
fn check_body_size(req: &Request, max: u64) -> Result<(), Response> {
    if let Some(content_length) = req
        .headers()
        .get(axum::http::header::CONTENT_LENGTH)
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.parse::<u64>().ok())
    {
        if content_length > max {
            let body = GuardError {
                error: "payload_too_large".to_string(),
                message: format!(
                    "Request body of {} bytes exceeds the maximum of {} bytes",
                    content_length, max
                ),
            };
            return Err((StatusCode::PAYLOAD_TOO_LARGE, Json(body)).into_response());
        }
    }
    Ok(())
}

/// Check whether the request method is allowed for the given path.
///
/// Returns `Err(Response)` with `405 Method Not Allowed` if the method is
/// restricted.
#[allow(clippy::result_large_err)]
fn check_method_restriction(
    method: &Method,
    path: &str,
    restrictions: &HashMap<String, Vec<String>>,
) -> Result<(), Response> {
    for (prefix, allowed_methods) in restrictions.iter() {
        if path.starts_with(prefix) {
            let method_str = method.to_string().to_uppercase();
            let allowed = allowed_methods
                .iter()
                .any(|m| m.to_uppercase() == method_str);
            if !allowed {
                let body = GuardError {
                    error: "method_not_allowed".to_string(),
                    message: format!(
                        "Method {} is not allowed on path matching '{}'",
                        method, prefix
                    ),
                };
                return Err((StatusCode::METHOD_NOT_ALLOWED, Json(body)).into_response());
            }
        }
    }
    Ok(())
}

/// Axum middleware that validates incoming requests against the
/// [`RequestGuardConfig`].
///
/// The [`RequestGuardConfig`] must be injected into request extensions
/// before this middleware runs.
pub async fn request_guard_middleware(req: Request, next: Next) -> Response {
    // ── 1. Body size check ──────────────────────────────────────────
    let config = req
        .extensions()
        .get::<RequestGuardConfig>()
        .cloned()
        .unwrap_or_default();

    if let Err(response) = check_body_size(&req, config.max_body_size) {
        return response;
    }

    // ── 2. Method restriction check ─────────────────────────────────
    let path = req.uri().path().to_string();
    if let Err(response) = check_method_restriction(
        req.method(),
        &path,
        &config.method_restrictions,
    ) {
        return response;
    }

    // ── 3. Request timeout ──────────────────────────────────────────
    let timeout_dur = Duration::from_secs(config.request_timeout_secs);

    match timeout(timeout_dur, next.run(req)).await {
        Ok(response) => response,
        Err(_elapsed) => {
            warn!(
                path = %path,
                timeout_secs = config.request_timeout_secs,
                "Request timed out"
            );
            let body = GuardError {
                error: "request_timeout".to_string(),
                message: format!(
                    "Request timed out after {} seconds",
                    config.request_timeout_secs
                ),
            };
            (StatusCode::REQUEST_TIMEOUT, Json(body)).into_response()
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::Method;
    use std::collections::HashMap;

    #[test]
    fn test_check_body_size_within_limit() {
        let req = Request::builder()
            .header("content-length", "100")
            .body(axum::body::Body::empty())
            .unwrap();
        assert!(check_body_size(&req, 200).is_ok());
    }

    #[test]
    fn test_check_body_size_exceeds_limit() {
        let req = Request::builder()
            .header("content-length", "300")
            .body(axum::body::Body::empty())
            .unwrap();
        let result = check_body_size(&req, 200);
        assert!(result.is_err());
    }

    #[test]
    fn test_check_body_size_no_content_length() {
        let req = Request::builder()
            .body(axum::body::Body::empty())
            .unwrap();
        // No content-length header → skip check → Ok.
        assert!(check_body_size(&req, 200).is_ok());
    }

    #[test]
    fn test_check_body_size_zero_limit() {
        let req = Request::builder()
            .header("content-length", "1")
            .body(axum::body::Body::empty())
            .unwrap();
        // Max body size of 0 → any body exceeds it.
        let result = check_body_size(&req, 0);
        assert!(result.is_err());
    }

    #[test]
    fn test_check_method_restriction_allowed() {
        let mut restrictions = HashMap::new();
        restrictions.insert("/api/admin".to_string(), vec!["GET".into(), "POST".into()]);

        let req = Request::builder()
            .method(Method::GET)
            .uri("/api/admin/users")
            .body(axum::body::Body::empty())
            .unwrap();
        assert!(check_method_restriction(req.method(), "/api/admin/users", &restrictions).is_ok());
    }

    #[test]
    fn test_check_method_restriction_blocked() {
        let mut restrictions = HashMap::new();
        restrictions.insert("/api/admin".to_string(), vec!["GET".into()]);

        let req = Request::builder()
            .method(Method::DELETE)
            .uri("/api/admin/users")
            .body(axum::body::Body::empty())
            .unwrap();
        let result = check_method_restriction(req.method(), "/api/admin/users", &restrictions);
        assert!(result.is_err());
    }

    #[test]
    fn test_check_method_restriction_no_match() {
        let mut restrictions = HashMap::new();
        restrictions.insert("/api/admin".to_string(), vec!["GET".into()]);

        // Path doesn't match any restricted prefix → allowed.
        assert!(
            check_method_restriction(&Method::DELETE, "/api/public", &restrictions).is_ok()
        );
    }

    #[test]
    fn test_check_method_restriction_case_insensitive() {
        let mut restrictions = HashMap::new();
        restrictions.insert("/api".to_string(), vec!["get".into()]);

        assert!(
            check_method_restriction(&Method::GET, "/api/test", &restrictions).is_ok()
        );
    }

    #[test]
    fn test_request_guard_config_default() {
        let config = RequestGuardConfig::default();
        assert_eq!(config.max_body_size, 10 * 1024 * 1024); // 10 MB
        assert_eq!(config.request_timeout_secs, 60);
        assert!(config.method_restrictions.is_empty());
    }

    #[test]
    fn test_request_guard_config_custom() {
        let mut restrictions = HashMap::new();
        restrictions.insert("/api/readonly".to_string(), vec!["GET".into()]);

        let config = RequestGuardConfig {
            max_body_size: 1024,
            request_timeout_secs: 30,
            method_restrictions: Arc::new(restrictions),
        };
        assert_eq!(config.max_body_size, 1024);
        assert_eq!(config.request_timeout_secs, 30);
        assert_eq!(config.method_restrictions.len(), 1);
    }

    #[test]
    fn test_guard_error_serialization() {
        let err = GuardError {
            error: "test_error".into(),
            message: "Test message".into(),
        };
        let json = serde_json::to_string(&err).unwrap();
        assert!(json.contains("test_error"));
        assert!(json.contains("Test message"));
    }
}

//! Request validation guard middleware.
//!
//! Validates incoming requests against configurable constraints:
//!
//! 1. **Method restriction** — blocks specific HTTP methods on matching
//!    path prefixes (e.g., forbid `DELETE` on `/api/admin/readonly`).
//!
//! Request body limits are enforced by the router-level
//! [`RequestBodyLimitLayer`](tower_http::limit::RequestBodyLimitLayer)
//! (which also covers chunked bodies, unlike a `Content-Length` check), and
//! request timeouts are enforced by the single global
//! [`TimeoutLayer`](tower_http::timeout::TimeoutLayer).

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

/// Internal error body for guard rejections.
#[derive(Serialize)]
struct GuardError {
    error: String,
    message: String,
}

/// Configuration for the request guard middleware.
#[derive(Clone, Debug)]
pub struct RequestGuardConfig {
    /// Per-path-prefix method restrictions.
    pub method_restrictions: Arc<HashMap<String, Vec<String>>>,
    /// Maximum allowed request body size in bytes (used to configure the
    /// router-level `RequestBodyLimitLayer`).
    pub max_body_size: usize,
    /// Maximum time (seconds) allowed for the inner handler to complete
    /// (used to configure the router-level `TimeoutLayer`).
    pub request_timeout_secs: u64,
}

impl Default for RequestGuardConfig {
    fn default() -> Self {
        Self {
            method_restrictions: Arc::new(HashMap::new()),
            max_body_size: 10 * 1024 * 1024, // 10 MB
            request_timeout_secs: 30,
        }
    }
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
/// Enforces per-prefix method restrictions only. Body-size and timeout
/// enforcement live in dedicated router-level layers (see the module docs).
///
/// The [`RequestGuardConfig`] must be injected into request extensions
/// before this middleware runs.
pub async fn request_guard_middleware(req: Request, next: Next) -> Response {
    let config = req
        .extensions()
        .get::<RequestGuardConfig>()
        .cloned()
        .unwrap_or_default();

    // ── Method restriction check ─────────────────────────────────────
    let path = req.uri().path().to_string();
    if let Err(response) =
        check_method_restriction(req.method(), &path, &config.method_restrictions)
    {
        return response;
    }

    next.run(req).await
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
        assert!(check_method_restriction(&Method::DELETE, "/api/public", &restrictions).is_ok());
    }

    #[test]
    fn test_check_method_restriction_case_insensitive() {
        let mut restrictions = HashMap::new();
        restrictions.insert("/api".to_string(), vec!["get".into()]);

        assert!(check_method_restriction(&Method::GET, "/api/test", &restrictions).is_ok());
    }

    #[test]
    fn test_request_guard_config_default() {
        let config = RequestGuardConfig::default();
        assert_eq!(config.max_body_size, 10 * 1024 * 1024); // 10 MB
        assert_eq!(config.request_timeout_secs, 30);
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

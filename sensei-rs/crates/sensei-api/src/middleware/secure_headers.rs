//! Secure headers middleware.
//!
//! Adds security-related HTTP headers to all responses to harden the
//! application against common web vulnerabilities.

use axum::{
    extract::Request,
    http::HeaderValue,
    middleware::Next,
    response::Response,
};
use tracing::warn;

/// Headers inserted by this middleware.
const HSTS_HEADER: &str = "max-age=31536000; includeSubDomains";
const CSP_HEADER: &str = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' ws: wss:; frame-ancestors 'none'";

/// Middleware that adds security headers to every HTTP response.
pub async fn secure_headers_middleware(req: Request, next: Next) -> Response {
    let mut response = next.run(req).await;
    let headers = response.headers_mut();

    insert_header(headers, "x-content-type-options", "nosniff");
    insert_header(headers, "x-frame-options", "DENY");
    insert_header(headers, "x-xss-protection", "0");
    insert_header(headers, "referrer-policy", "strict-origin-when-cross-origin");
    insert_header(headers, "permissions-policy", "camera=(), microphone=(), geolocation=()");
    insert_header(headers, "strict-transport-security", HSTS_HEADER);
    insert_header(headers, "content-security-policy", CSP_HEADER);

    response
}

/// Insert a header value, logging a warning if parsing fails.
fn insert_header(headers: &mut axum::http::HeaderMap, name: &'static str, value: &str) {
    match HeaderValue::from_str(value) {
        Ok(val) => {
            headers.insert(
                axum::http::HeaderName::from_static(name),
                val,
            );
        }
        Err(e) => {
            warn!(
                header = name,
                value = %value,
                error = %e,
                "Failed to insert security header"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::Request,
        middleware,
        routing::get,
        Router,
    };
    use tower::util::ServiceExt;

    /// Helper: build a Router with the secure headers middleware and a simple handler.
    fn test_app() -> Router {
        Router::new()
            .route("/", get(|| async { "Hello, World!" }))
            .layer(middleware::from_fn(secure_headers_middleware))
    }

    #[tokio::test]
    async fn test_secure_headers_middleware_adds_headers() {
        let app = test_app();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        let headers = response.headers();

        assert_eq!(
            headers.get("x-content-type-options").unwrap(),
            "nosniff"
        );
        assert_eq!(headers.get("x-frame-options").unwrap(), "DENY");
        assert_eq!(headers.get("x-xss-protection").unwrap(), "0");
        assert_eq!(
            headers.get("referrer-policy").unwrap(),
            "strict-origin-when-cross-origin"
        );
        assert_eq!(
            headers.get("permissions-policy").unwrap(),
            "camera=(), microphone=(), geolocation=()"
        );
        assert!(headers.get("strict-transport-security").is_some());
        assert!(headers.get("content-security-policy").is_some());
    }

    #[tokio::test]
    async fn test_secure_headers_hsts_value() {
        let app = test_app();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        let hsts = response
            .headers()
            .get("strict-transport-security")
            .unwrap()
            .to_str()
            .unwrap();
        assert!(hsts.contains("max-age=31536000"));
        assert!(hsts.contains("includeSubDomains"));
    }

    #[tokio::test]
    async fn test_secure_headers_csp_value() {
        let app = test_app();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        let csp = response
            .headers()
            .get("content-security-policy")
            .unwrap()
            .to_str()
            .unwrap();
        assert!(csp.contains("default-src 'self'"));
        assert!(csp.contains("frame-ancestors 'none'"));
    }

    #[tokio::test]
    async fn test_secure_headers_preserves_body() {
        let app = Router::new()
            .route("/", get(|| async { "response body" }))
            .layer(middleware::from_fn(secure_headers_middleware));

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        assert_eq!(&body[..], b"response body");
    }

    #[test]
    fn test_insert_header_valid() {
        let mut headers = axum::http::HeaderMap::new();
        insert_header(&mut headers, "x-custom", "valid-value");
        assert_eq!(
            headers.get("x-custom").unwrap(),
            "valid-value"
        );
    }

    #[test]
    fn test_insert_header_invalid_value_does_not_panic() {
        let mut headers = axum::http::HeaderMap::new();
        // A value with null bytes is invalid for HeaderValue.
        insert_header(&mut headers, "x-bad", "valid\x00value");
        // The invalid header should not be inserted.
        assert!(headers.get("X-Bad").is_none());
    }

    #[tokio::test]
    async fn test_secure_headers_do_not_remove_existing_headers() {
        // Create a router that adds a custom content-type header in the response.
        let app = Router::new()
            .route(
                "/",
                get(|| async {
                    (
                        [(axum::http::header::CONTENT_TYPE.as_str(), "application/json")],
                        "body",
                    )
                }),
            )
            .layer(middleware::from_fn(secure_headers_middleware));

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        let headers = response.headers();
        // Original header should still be present.
        assert_eq!(
            headers.get(axum::http::header::CONTENT_TYPE).unwrap(),
            "application/json"
        );
        // Security headers should be added.
        assert_eq!(headers.get("x-content-type-options").unwrap(), "nosniff");
    }
}

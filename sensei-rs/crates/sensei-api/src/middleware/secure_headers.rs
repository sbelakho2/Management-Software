//! Secure headers middleware.
//!
//! Adds security-related HTTP headers to all responses to harden the
//! application against common web vulnerabilities.
//!
//! # TLS-awareness
//!
//! `Strict-Transport-Security` is only emitted when the request was made
//! over HTTPS. The scheme is taken from the request URI, or from the
//! `X-Forwarded-Proto` header when the immediate peer is a trusted proxy
//! (see [`SecurityConfig::trusted_proxies`](sensei_core::config::SecurityConfig)).
//!
//! # CSP
//!
//! The `Content-Security-Policy` value is taken from
//! `config.security.csp`; when unset (or empty) the built-in default is
//! used. `config.security.hsts` can disable the HSTS header entirely.

use axum::{
    extract::{Request, State},
    http::HeaderValue,
    middleware::Next,
    response::Response,
};
use tracing::warn;

use crate::state::AppState;

/// Default HSTS policy.
const HSTS_HEADER: &str = "max-age=31536000; includeSubDomains";
/// Default Content-Security-Policy, used when `config.security.csp` is unset.
const DEFAULT_CSP_HEADER: &str = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' ws: wss:; frame-ancestors 'none'";

/// Determine whether the request was made over HTTPS.
///
/// Trusts `X-Forwarded-Proto` only when the immediate peer is a configured
/// trusted proxy; otherwise the request URI scheme decides.
fn request_is_https(req: &Request, trusted_proxies: &[std::net::IpAddr]) -> bool {
    if req.uri().scheme_str() == Some("https") {
        return true;
    }

    let peer_is_trusted = req
        .extensions()
        .get::<axum::extract::ConnectInfo<std::net::SocketAddr>>()
        .map(|ci| trusted_proxies.contains(&ci.0.ip()))
        .unwrap_or(false);

    if peer_is_trusted {
        if let Some(value) = req
            .headers()
            .get("x-forwarded-proto")
            .and_then(|v| v.to_str().ok())
        {
            if value.split(',').next().map(str::trim) == Some("https") {
                return true;
            }
        }
    }

    false
}

/// Middleware that adds security headers to every HTTP response.
pub async fn secure_headers_middleware(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Response {
    // Scheme checks must run before the request is moved into the handler.
    let is_https = request_is_https(&req, &state.config.security.trusted_proxies);

    let mut response = next.run(req).await;
    let headers = response.headers_mut();

    insert_header(headers, "x-content-type-options", "nosniff");
    insert_header(headers, "x-frame-options", "DENY");
    insert_header(headers, "x-xss-protection", "0");
    insert_header(
        headers,
        "referrer-policy",
        "strict-origin-when-cross-origin",
    );
    insert_header(
        headers,
        "permissions-policy",
        "camera=(), microphone=(), geolocation=()",
    );

    if state.config.security.hsts && is_https {
        insert_header(headers, "strict-transport-security", HSTS_HEADER);
    }

    let csp = state
        .config
        .security
        .csp
        .as_deref()
        .filter(|csp| !csp.is_empty())
        .unwrap_or(DEFAULT_CSP_HEADER);
    insert_header(headers, "content-security-policy", csp);

    response
}

/// Insert a header value, logging a warning if parsing fails.
fn insert_header(headers: &mut axum::http::HeaderMap, name: &'static str, value: &str) {
    match HeaderValue::from_str(value) {
        Ok(val) => {
            headers.insert(axum::http::HeaderName::from_static(name), val);
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

/// Test-only helper to attach a `ConnectInfo` extension to a request.
#[cfg(test)]
trait WithConnectInfo {
    fn with_connect_info(self, addr: &str) -> Self;
}

#[cfg(test)]
impl WithConnectInfo for Request<axum::body::Body> {
    fn with_connect_info(self, addr: &str) -> Self {
        let mut req = self;
        let socket: std::net::SocketAddr = addr.parse().unwrap();
        req.extensions_mut()
            .insert(axum::extract::ConnectInfo(socket));
        req
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request, routing::get, Router};
    use tower::util::ServiceExt;

    /// Build a deterministic test configuration regardless of the ambient
    /// environment (parallel tests share the process, so every test pins the
    /// same safe values).
    fn test_config() -> sensei_core::config::AppConfig {
        std::env::set_var("SENSEI_ENV", "development");
        std::env::set_var("JWT_SECRET", "sensei-api-test-secret");
        std::env::set_var("DATABASE_URL", "");
        std::env::remove_var("NATS_URL");
        sensei_core::config::AppConfig::from_env().expect("test config")
    }

    /// Build a state with the given security configuration and wrap a simple
    /// handler with the secure-headers middleware.
    async fn app_with_security(security: sensei_core::config::SecurityConfig) -> Router {
        let config = test_config();
        let config = sensei_core::config::AppConfig { security, ..config };
        let users_service: std::sync::Arc<dyn sensei_services::users::UsersService> =
            std::sync::Arc::new(sensei_services::users::InMemoryUsersService::new());
        let state = crate::state::AppState::new(config, users_service);
        Router::new()
            .route("/", get(|| async { "Hello, World!" }))
            .layer(axum::middleware::from_fn_with_state(
                state,
                secure_headers_middleware,
            ))
    }

    #[tokio::test]
    async fn test_secure_headers_middleware_adds_headers() {
        let app = app_with_security(sensei_core::config::SecurityConfig::default()).await;
        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let headers = response.headers();

        assert_eq!(headers.get("x-content-type-options").unwrap(), "nosniff");
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
        assert!(headers.get("content-security-policy").is_some());
    }

    #[tokio::test]
    async fn test_secure_headers_hsts_value() {
        let app = app_with_security(sensei_core::config::SecurityConfig::default()).await;
        let response = app
            .oneshot(
                Request::builder()
                    .uri("https://sensei.example/")
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
    async fn test_hsts_omitted_on_plain_http() {
        let app = app_with_security(sensei_core::config::SecurityConfig::default()).await;
        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        // Plain (non-TLS) requests must not receive the HSTS header, since
        // HSTS on http is both useless and actively harmful (the header is
        // ignored by browsers, and mirrors the broken practice of sending it
        // unencrypted).
        assert!(
            response
                .headers()
                .get("strict-transport-security")
                .is_none(),
            "HSTS must be omitted on plain HTTP"
        );
    }

    #[tokio::test]
    async fn test_hsts_respects_config_flag() {
        let security = sensei_core::config::SecurityConfig {
            hsts: false,
            ..Default::default()
        };
        let app = app_with_security(security).await;
        let response = app
            .oneshot(
                Request::builder()
                    .uri("https://sensei.example/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert!(response
            .headers()
            .get("strict-transport-security")
            .is_none());
    }

    #[tokio::test]
    async fn test_secure_headers_csp_value() {
        let app = app_with_security(sensei_core::config::SecurityConfig::default()).await;
        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
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
    async fn test_csp_is_configurable() {
        let security = sensei_core::config::SecurityConfig {
            csp: Some("default-src 'none'".to_string()),
            ..Default::default()
        };
        let app = app_with_security(security).await;
        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let csp = response
            .headers()
            .get("content-security-policy")
            .unwrap()
            .to_str()
            .unwrap();
        assert_eq!(csp, "default-src 'none'");
    }

    #[tokio::test]
    async fn test_secure_headers_preserves_body() {
        let app = app_with_security(sensei_core::config::SecurityConfig::default()).await;
        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        assert_eq!(&body[..], b"Hello, World!");
    }

    #[test]
    fn test_insert_header_valid() {
        let mut headers = axum::http::HeaderMap::new();
        insert_header(&mut headers, "x-custom", "valid-value");
        assert_eq!(headers.get("x-custom").unwrap(), "valid-value");
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
        let config = test_config();
        let users_service: std::sync::Arc<dyn sensei_services::users::UsersService> =
            std::sync::Arc::new(sensei_services::users::InMemoryUsersService::new());
        let state = crate::state::AppState::new(config, users_service);
        // A handler that sets its own content-type header.
        let app = Router::new()
            .route(
                "/",
                get(|| async {
                    (
                        [(
                            axum::http::header::CONTENT_TYPE.as_str(),
                            "application/json",
                        )],
                        "body",
                    )
                }),
            )
            .layer(axum::middleware::from_fn_with_state(
                state,
                secure_headers_middleware,
            ));

        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
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

    #[tokio::test]
    async fn test_https_detection_trusted_proxy_x_forwarded_proto() {
        use std::net::IpAddr;
        let trusted: Vec<IpAddr> = vec!["10.0.0.1".parse().unwrap()];

        let req = Request::builder()
            .uri("/")
            .header("x-forwarded-proto", "https")
            .body(Body::empty())
            .unwrap()
            .with_connect_info("10.0.0.1:443");
        assert!(request_is_https(&req, &trusted));

        // An untrusted peer cannot spoof the proto header.
        let req = Request::builder()
            .uri("/")
            .header("x-forwarded-proto", "https")
            .body(Body::empty())
            .unwrap()
            .with_connect_info("198.51.100.9:443");
        assert!(!request_is_https(&req, &trusted));

        // No proxy header, no scheme → http.
        let req = Request::builder().uri("/").body(Body::empty()).unwrap();
        assert!(!request_is_https(&req, &trusted));
    }
}

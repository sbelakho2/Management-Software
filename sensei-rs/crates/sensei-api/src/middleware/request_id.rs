//! Request ID middleware.
//!
//! Assigns a unique UUID to each incoming request for distributed tracing.
//! If the client sends an `X-Request-Id` header it is used only when it is
//! well-formed (`^[A-Za-z0-9._-]{1,128}$`); otherwise a new UUID is
//! generated so that downstream systems can rely on the header shape.

use axum::{
    extract::Request,
    http::header::HeaderName,
    middleware::Next,
    response::Response,
};
use tracing::warn;
use uuid::Uuid;

/// The header name used for request IDs.
pub const REQUEST_ID_HEADER: HeaderName = HeaderName::from_static("x-request-id");

/// Maximum accepted length of a client-supplied request ID.
const MAX_REQUEST_ID_LEN: usize = 128;

/// Validate a client-supplied request ID against `^[A-Za-z0-9._-]{1,128}$`.
///
/// Rejects empty, oversized, and otherwise malformed values.
pub fn is_valid_request_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_REQUEST_ID_LEN
        && value.bytes().all(|b| {
            b.is_ascii_alphanumeric() || b == b'.' || b == b'_' || b == b'-'
        })
}

/// Middleware that attaches a unique request ID to each request.
pub async fn request_id_middleware(mut req: Request, next: Next) -> Response {
    let request_id = req
        .headers()
        .get(&REQUEST_ID_HEADER)
        .and_then(|v| v.to_str().ok())
        .filter(|s| is_valid_request_id(s))
        .map(|s| s.to_string())
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    req.extensions_mut()
        .insert(RequestId(request_id.clone()));

    let mut response = next.run(req).await;
    // The request ID is always a valid header value: either a validated
    // client string (ASCII alphanumerics + `._-`) or a UUID.
    if let Ok(header_value) = axum::http::HeaderValue::try_from(&request_id[..]) {
        response.headers_mut().insert(&REQUEST_ID_HEADER, header_value);
    } else {
        warn!(
            request_id = %request_id,
            "Failed to parse request_id as HeaderValue"
        );
    }

    response
}

/// A request ID extracted from the middleware.
#[derive(Debug, Clone)]
pub struct RequestId(pub String);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_well_formed_ids() {
        assert!(is_valid_request_id("abc123"));
        assert!(is_valid_request_id("A-Z_0-9.-"));
        assert!(is_valid_request_id("a"));
        assert!(is_valid_request_id(&"x".repeat(128)));
        assert!(is_valid_request_id("req_abc.def-123"));
    }

    #[test]
    fn rejects_malformed_ids() {
        assert!(!is_valid_request_id(""));
        assert!(!is_valid_request_id(&"x".repeat(129)));
        assert!(!is_valid_request_id("has spaces"));
        assert!(!is_valid_request_id("has/slash"));
        assert!(!is_valid_request_id("has?query"));
        assert!(!is_valid_request_id("has\nnewline"));
        assert!(!is_valid_request_id("emoji-😀"));
    }

    #[tokio::test]
    async fn middleware_replaces_invalid_header_with_uuid() {
        use axum::{body::Body, routing::get, Router};
        use tower::ServiceExt;

        let app = Router::new()
            .route(
                "/",
                get(|req: Request| async move {
                    let id = req
                        .extensions()
                        .get::<RequestId>()
                        .expect("RequestId must be injected")
                        .0
                        .clone();
                    ([(REQUEST_ID_HEADER.clone(), id)], "ok")
                }),
            )
            .layer(axum::middleware::from_fn(request_id_middleware));

        let response = app
            .oneshot(
                Request::builder()
                    .header("x-request-id", "bad id with spaces!!!")
                    .uri("/")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        let echoed = response
            .headers()
            .get("x-request-id")
            .and_then(|v| v.to_str().ok())
            .expect("response must carry x-request-id");
        // The malformed client header must have been replaced by a UUID.
        uuid::Uuid::parse_str(echoed).expect("invalid header must be replaced by a UUID");
    }
}

//! Request ID middleware.
//!
//! Assigns a unique UUID to each incoming request for distributed tracing.
//! If the client sends an `X-Request-Id` header, it is used as-is;
//! otherwise, a new UUID is generated.

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

/// Middleware that attaches a unique request ID to each request.
pub async fn request_id_middleware(mut req: Request, next: Next) -> Response {
    let request_id = req
        .headers()
        .get(&REQUEST_ID_HEADER)
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string())
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    req.extensions_mut()
        .insert(RequestId(request_id.clone()));

    let mut response = next.run(req).await;
    // Parse the request_id back into a HeaderValue
    // Since request_id is always a UUID string (valid ASCII), this should never fail
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

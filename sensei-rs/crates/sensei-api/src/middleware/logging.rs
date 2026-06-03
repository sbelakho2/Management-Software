//! Request logging middleware.
//!
//! Logs incoming HTTP requests and their responses with timing,
//! status codes, and metadata for observability. Enriches tracing
//! spans with request/response attributes for distributed tracing.
//!
//! Prometheus metric recording is handled by the dedicated
//! [`metrics_middleware`](super::metrics::metrics_middleware).

use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
};
use std::time::Instant;
use tracing::{info, Span};

/// Middleware that logs HTTP requests and responses.
///
/// Logs request start and completion with method, path, status, and
/// timing information. Enriches the current tracing span with HTTP
/// attributes so they appear in structured (JSON) logs and OpenTelemetry
/// spans if tracing-opentelemetry is configured.
pub async fn logging_middleware(request: Request, next: Next) -> Response {
    let start = Instant::now();
    let method = request.method().to_string();
    let path = request.uri().path().to_string();

    // Enrich current span with request attributes
    Span::current().record("http.method", &method);
    Span::current().record("http.path", &path);

    info!(
        method = %method,
        path = %path,
        "request started"
    );

    let response = next.run(request).await;

    let duration = start.elapsed();
    let status = response.status().as_u16();

    Span::current().record("http.status_code", status);
    Span::current().record("http.duration_ms", duration.as_millis() as i64);

    info!(
        method = %method,
        path = %path,
        status = status,
        duration_ms = duration.as_millis(),
        "request completed"
    );

    response
}

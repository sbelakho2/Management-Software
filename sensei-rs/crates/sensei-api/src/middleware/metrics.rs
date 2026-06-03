//! Metrics collection middleware.
//!
//! Records Prometheus metrics for every HTTP request: total count (by method,
//! path, status), duration histogram, and in-flight gauge. This middleware is
//! intentionally lightweight and focused solely on metric collection, separate
//! from the logging middleware.
//!
//! Metrics are exported via the `/metrics` endpoint (see [`routes::metrics::metrics_handler`]).

use std::time::Instant;

use axum::{extract::Request, middleware::Next, response::Response};

use crate::routes::metrics::{
    HTTP_REQUESTS_IN_FLIGHT, HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION,
};

/// Middleware that records Prometheus HTTP metrics.
///
/// Measures and records:
/// - `http_requests_total` – counter by `method`, `path`, `status`
/// - `http_request_duration_seconds` – histogram by `method`, `path`
/// - `http_requests_in_flight` – gauge (current count of concurrent requests)
pub async fn metrics_middleware(request: Request, next: Next) -> Response {
    HTTP_REQUESTS_IN_FLIGHT.inc();

    let start = Instant::now();
    let method = request.method().to_string();
    let path = request.uri().path().to_string();

    let response = next.run(request).await;

    let duration = start.elapsed().as_secs_f64();
    let status = response.status().as_u16().to_string();

    HTTP_REQUESTS_TOTAL
        .with_label_values(&[&method, &path, &status])
        .inc();
    HTTP_REQUEST_DURATION
        .with_label_values(&[&method, &path])
        .observe(duration);
    HTTP_REQUESTS_IN_FLIGHT.dec();

    response
}

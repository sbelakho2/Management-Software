//! Metrics collection middleware.
//!
//! Records Prometheus metrics for every HTTP request: total count (by method,
//! path, status), duration histogram, and in-flight gauge. This middleware is
//! intentionally lightweight and focused solely on metric collection, separate
//! from the logging middleware.
//!
//! # Path normalization
//!
//! Label cardinality is kept bounded by replacing UUID-shaped and long
//! numeric path segments with `{id}`, so e.g. `/api/v1/tasks/<uuid>` and
//! `/api/v1/employees/<9-digit-id>` collapse to `/api/v1/tasks/{id}` and
//! `/api/v1/employees/{id}` for the `http_requests_total` and
//! `http_request_duration_seconds` labels.
//!
//! Metrics are exported via the `/metrics` endpoint (see [`routes::metrics::metrics_handler`]).

use std::time::Instant;

use axum::{extract::Request, middleware::Next, response::Response};

use crate::routes::metrics::{HTTP_REQUESTS_IN_FLIGHT, HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION};

/// Minimum length for a numeric segment to be normalized to `{id}`.
const MIN_NUMERIC_ID_LEN: usize = 8;

/// Returns `true` when `segment` looks like a UUID (canonical hyphenated form
/// or the 32-char raw hex form).
fn looks_like_uuid(segment: &str) -> bool {
    if segment.len() == 36 {
        let bytes = segment.as_bytes();
        return bytes[8] == b'-'
            && bytes[13] == b'-'
            && bytes[18] == b'-'
            && bytes[23] == b'-'
            && segment
                .bytes()
                .filter(|b| *b != b'-')
                .all(|b| b.is_ascii_hexdigit());
    }
    if segment.len() == 32 {
        return segment.bytes().all(|b| b.is_ascii_hexdigit());
    }
    false
}

/// Normalize a request path for metric labels.
///
/// UUID segments and long numeric segments (e.g. numeric primary keys) are
/// replaced with `{id}`.
pub fn normalize_path(path: &str) -> String {
    path.split('/')
        .map(|segment| {
            if looks_like_uuid(segment)
                || (segment.len() >= MIN_NUMERIC_ID_LEN
                    && segment.bytes().all(|b| b.is_ascii_digit()))
            {
                "{id}"
            } else {
                segment
            }
        })
        .collect::<Vec<_>>()
        .join("/")
}

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
    let path = normalize_path(request.uri().path());

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_uuid_segments() {
        let uuid = "123e4567-e89b-12d3-a456-426614174000";
        assert_eq!(
            normalize_path(&format!("/api/v1/tasks/{uuid}/status")),
            "/api/v1/tasks/{id}/status"
        );
    }

    #[test]
    fn normalizes_raw_hex_uuid_segments() {
        assert_eq!(
            normalize_path("/api/v1/tasks/123e4567e89b12d3a456426614174000"),
            "/api/v1/tasks/{id}"
        );
    }

    #[test]
    fn normalizes_long_numeric_segments() {
        assert_eq!(
            normalize_path("/api/v1/employees/123456789"),
            "/api/v1/employees/{id}"
        );
    }

    #[test]
    fn leaves_short_segments_alone() {
        assert_eq!(normalize_path("/api/v1/health/live"), "/api/v1/health/live");
        assert_eq!(normalize_path("/api/v1/tasks/42"), "/api/v1/tasks/42");
        assert_eq!(normalize_path("/api/v1/orders/2024"), "/api/v1/orders/2024");
    }

    #[test]
    fn normalizes_mixed_paths() {
        assert_eq!(
            normalize_path("/api/v1/kanban/boards/9a2f1c6e-3b7d-4e5f-8a0b-1c2d3e4f5a6b/columns/7"),
            "/api/v1/kanban/boards/{id}/columns/7"
        );
    }

    #[test]
    fn root_path_unchanged() {
        assert_eq!(normalize_path("/"), "/");
    }
}

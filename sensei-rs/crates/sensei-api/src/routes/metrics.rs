//! Prometheus metrics endpoint.
//!
//! Exposes application metrics in Prometheus text format for scraping.
//! Uses the `prometheus` crate directly with labeled CounterVec, HistogramVec,
//! and Gauge metrics for production-grade observability.
//!
//! Registration and encoding failures are logged and skipped; they never
//! panic the server.

use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use once_cell::sync::Lazy;
use prometheus::{CounterVec, Gauge, HistogramVec, Opts, Registry, TextEncoder};

/// Global Prometheus registry.
pub static METRICS_REGISTRY: Lazy<Registry> = Lazy::new(Registry::new);

/// Total HTTP requests by method, path, and status code.
pub static HTTP_REQUESTS_TOTAL: Lazy<CounterVec> = Lazy::new(|| {
    let opts = Opts::new("http_requests_total", "Total number of HTTP requests");
    let cv = match CounterVec::new(opts, &["method", "path", "status"]) {
        Ok(cv) => cv,
        Err(e) => {
            tracing::error!(
                error = %e,
                metric = "http_requests_total",
                "Failed to create counter metric"
            );
            // The name is a compile-time constant with valid label names,
            // so this fallback path cannot fail at runtime; the log above
            // is the actual signal for a developer error.
            CounterVec::new(
                Opts::new("http_requests_total", "Total number of HTTP requests"),
                &["method", "path", "status"],
            )
            .expect("metric name is a compile-time constant")
        }
    };
    if let Err(e) = METRICS_REGISTRY.register(Box::new(cv.clone())) {
        tracing::warn!(
            error = %e,
            metric = "http_requests_total",
            "Failed to register counter metric (continuing without it)"
        );
    }
    cv
});

/// HTTP request duration in seconds by method and path.
pub static HTTP_REQUEST_DURATION: Lazy<HistogramVec> = Lazy::new(|| {
    let opts = prometheus::HistogramOpts::new(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
    )
    .buckets(vec![
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
    ]);
    let hv = match HistogramVec::new(opts, &["method", "path"]) {
        Ok(hv) => hv,
        Err(e) => {
            tracing::error!(
                error = %e,
                metric = "http_request_duration_seconds",
                "Failed to create histogram metric"
            );
            // Compile-time constant name/labels: cannot fail at runtime.
            prometheus::HistogramVec::new(
                prometheus::HistogramOpts::new(
                    "http_request_duration_seconds",
                    "HTTP request duration in seconds",
                )
                .buckets(vec![
                    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
                ]),
                &["method", "path"],
            )
            .expect("metric name is a compile-time constant")
        }
    };
    if let Err(e) = METRICS_REGISTRY.register(Box::new(hv.clone())) {
        tracing::warn!(
            error = %e,
            metric = "http_request_duration_seconds",
            "Failed to register histogram metric (continuing without it)"
        );
    }
    hv
});

/// Current number of in-flight HTTP requests.
pub static HTTP_REQUESTS_IN_FLIGHT: Lazy<Gauge> = Lazy::new(|| {
    let opts = Opts::new(
        "http_requests_in_flight",
        "Current number of HTTP requests in flight",
    );
    let gauge = match Gauge::with_opts(opts) {
        Ok(gauge) => gauge,
        Err(e) => {
            tracing::error!(
                error = %e,
                metric = "http_requests_in_flight",
                "Failed to create gauge metric"
            );
            // Compile-time constant name: cannot fail at runtime.
            Gauge::with_opts(Opts::new(
                "http_requests_in_flight",
                "Current number of HTTP requests in flight",
            ))
            .expect("metric name is a compile-time constant")
        }
    };
    if let Err(e) = METRICS_REGISTRY.register(Box::new(gauge.clone())) {
        tracing::warn!(
            error = %e,
            metric = "http_requests_in_flight",
            "Failed to register gauge metric (continuing without it)"
        );
    }
    gauge
});

/// Initialize the Prometheus metrics recorder.
///
/// Called once at application startup to force evaluation of all `Lazy` statics.
pub fn init_metrics() {
    // Force evaluation of lazy statics to register them
    let _ = &*METRICS_REGISTRY;
    let _ = &*HTTP_REQUESTS_TOTAL;
    let _ = &*HTTP_REQUEST_DURATION;
    let _ = &*HTTP_REQUESTS_IN_FLIGHT;

    tracing::info!("Prometheus metrics initialized");
}

/// Handle for the `/metrics` endpoint.
///
/// Returns all registered metrics in Prometheus text format. Encoding
/// failures are logged and surfaced as a 500 rather than panicking.
pub async fn metrics_handler(
    headers: HeaderMap,
    crate::routes::health::OptionalPeer(peer): crate::routes::health::OptionalPeer,
    axum::extract::State(state): axum::extract::State<crate::state::AppState>,
) -> Response {
    use crate::routes::health::internal_access_allowed;
    if !internal_access_allowed(&headers, peer, state.config.environment.is_prod()) {
        return (
            StatusCode::FORBIDDEN,
            axum::Json(serde_json::json!({
                "error": "forbidden",
                "message": "Metrics require the internal monitoring token",
            })),
        )
            .into_response();
    }
    let encoder = TextEncoder::new();
    let metric_families = METRICS_REGISTRY.gather();
    let mut buffer = String::new();
    match encoder.encode_utf8(&metric_families, &mut buffer) {
        Ok(()) => (
            [(header::CONTENT_TYPE, "text/plain; charset=utf-8")],
            buffer,
        )
            .into_response(),
        Err(e) => {
            tracing::error!(error = %e, "Failed to encode Prometheus metrics");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Metrics encoding failed: {e}"),
            )
                .into_response()
        }
    }
}

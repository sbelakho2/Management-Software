//! Prometheus metrics endpoint.
//!
//! Exposes application metrics in Prometheus text format for scraping.
//! Uses the `prometheus` crate directly with labeled CounterVec, HistogramVec,
//! and Gauge metrics for production-grade observability.

use axum::http::header;
use axum::response::IntoResponse;
use once_cell::sync::Lazy;
use prometheus::{
    CounterVec, Gauge, HistogramVec, Opts,
    Registry, TextEncoder,
};

/// Global Prometheus registry.
pub static METRICS_REGISTRY: Lazy<Registry> = Lazy::new(|| Registry::new());

/// Total HTTP requests by method, path, and status code.
pub static HTTP_REQUESTS_TOTAL: Lazy<CounterVec> = Lazy::new(|| {
    let cv = CounterVec::new(
        Opts::new("http_requests_total", "Total number of HTTP requests"),
        &["method", "path", "status"],
    )
    .expect("Failed to create http_requests_total counter");
    METRICS_REGISTRY
        .register(Box::new(cv.clone()))
        .expect("Failed to register http_requests_total");
    cv
});

/// HTTP request duration in seconds by method and path.
pub static HTTP_REQUEST_DURATION: Lazy<HistogramVec> = Lazy::new(|| {
    let hv = HistogramVec::new(
        prometheus::HistogramOpts::new(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
        )
        .buckets(vec![
            0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
        ]),
        &["method", "path"],
    )
    .expect("Failed to create http_request_duration_seconds histogram");
    METRICS_REGISTRY
        .register(Box::new(hv.clone()))
        .expect("Failed to register http_request_duration_seconds");
    hv
});

/// Current number of in-flight HTTP requests.
pub static HTTP_REQUESTS_IN_FLIGHT: Lazy<Gauge> = Lazy::new(|| {
    let gauge = Gauge::with_opts(Opts::new(
        "http_requests_in_flight",
        "Current number of HTTP requests in flight",
    ))
    .expect("Failed to create http_requests_in_flight gauge");
    METRICS_REGISTRY
        .register(Box::new(gauge.clone()))
        .expect("Failed to register http_requests_in_flight");
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
/// Returns all registered metrics in Prometheus text format.
pub async fn metrics_handler() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = METRICS_REGISTRY.gather();
    let mut buffer = String::new();
    encoder
        .encode_utf8(&metric_families, &mut buffer)
        .expect("Failed to encode metrics");
    ([(header::CONTENT_TYPE, "text/plain; charset=utf-8")], buffer)
}

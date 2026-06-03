//! Rate limiting middleware using a token-bucket algorithm.
//!
//! Each distinct client (by IP) has its own token bucket.  Requests
//! within the same sliding window consume from the bucket.  When the
//! bucket is empty the client receives a `429 Too Many Requests` response.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use dashmap::DashMap;
use serde::Serialize;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::error;

/// Internal state for a single client's rate limit bucket.
struct RateLimitState {
    /// Number of requests already seen in the current window.
    count: u32,
    /// When the current window started.
    window_start: Instant,
}

/// A concurrent, key-based rate limiter.
///
/// Each key (typically a client IP) gets its own counter that resets
/// after `window_duration` elapses.
#[derive(Clone)]
pub struct RateLimiter {
    max_requests: u32,
    window_duration: Duration,
    buckets: Arc<DashMap<String, RateLimitState>>,
}

#[derive(Serialize)]
struct RateLimitError {
    error: String,
    message: String,
    retry_after_secs: u64,
}

impl RateLimiter {
    /// Create a new rate limiter.
    ///
    /// * `max_requests` – maximum number of requests allowed per window.
    /// * `window_secs`   – length of the window in seconds.
    pub fn new(max_requests: u32, window_secs: u64) -> Self {
        let buckets: Arc<DashMap<String, RateLimitState>> = Arc::new(DashMap::new());

        // Spawn a background cleanup task that periodically evicts stale entries.
        let window = Duration::from_secs(window_secs);
        let cleanup_buckets = buckets.clone();
        if window_secs > 0 {
            tokio::spawn(async move {
                cleanup_task(cleanup_buckets, window).await;
            });
        }

        Self {
            max_requests,
            window_duration: window,
            buckets,
        }
    }

    /// Check whether a request for the given `key` is allowed.
    ///
    /// Returns `Ok(())` if the request is within the limit, `Err(())` if
    /// the client has been rate-limited.
    #[allow(clippy::result_unit_err)]
    pub fn check(&self, key: &str) -> Result<(), ()> {
        let now = Instant::now();
        let mut entry = self.buckets.entry(key.to_string()).or_insert(RateLimitState {
            count: 0,
            window_start: now,
        });

        // If the window has elapsed, reset the counter.
        if now.duration_since(entry.window_start) >= self.window_duration {
            entry.count = 0;
            entry.window_start = now;
        }

        if entry.count >= self.max_requests {
            Err(())
        } else {
            entry.count += 1;
            Ok(())
        }
    }

    /// Return the number of keys currently tracked.
    pub fn tracked_keys(&self) -> usize {
        self.buckets.len()
    }
}

/// Background task that periodically removes stale entries from the bucket map.
async fn cleanup_task(buckets: Arc<DashMap<String, RateLimitState>>, window: Duration) {
    let mut interval = tokio::time::interval(window * 2);
    loop {
        interval.tick().await;
        let cutoff = Instant::now() - window;
        buckets.retain(|_, state| state.window_start > cutoff);
    }
}

/// Extract the client IP from the `X-Forwarded-For` header or fall back
/// to the socket address.
fn extract_client_ip(req: &Request) -> String {
    // Try X-Forwarded-For header first.
    if let Some(value) = req
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
    {
        if let Some(ip) = value.split(',').next() {
            return ip.trim().to_string();
        }
    }

    // Fall back to the connection's remote address.
    if let Some(connect_info) = req.extensions().get::<axum::extract::connect_info::ConnectInfo<std::net::SocketAddr>>() {
        return connect_info.0.ip().to_string();
    }

    "unknown".to_string()
}

/// Axum middleware that enforces rate limits per client IP.
///
/// Expects a [`RateLimiter`] instance in request extensions (injected by
/// the application state).  Reads the client IP from the
/// `X-Forwarded-For` header or falls back to the socket address.
pub async fn rate_limit_middleware(mut req: Request, next: Next) -> Response {
    // Retrieve the shared rate limiter from extensions.
    let rate_limiter = match req.extensions().get::<RateLimiter>() {
        Some(rl) => rl.clone(),
        None => {
            error!("RateLimiter not found in request extensions");
            return next.run(req).await;
        }
    };

    // Determine the client key (IP address).
    let client_ip = extract_client_ip(&req);

    match rate_limiter.check(&client_ip) {
        Ok(()) => {
            // Inject the limiter back so downstream layers can reuse it.
            req.extensions_mut().insert(rate_limiter);
            next.run(req).await
        }
        Err(()) => {
            let retry_after = rate_limiter.window_duration.as_secs();
            let body = RateLimitError {
                error: "rate_limited".to_string(),
                message: format!("Too many requests. Try again in {} seconds.", retry_after),
                retry_after_secs: retry_after,
            };
            let mut response = (StatusCode::TOO_MANY_REQUESTS, Json(body)).into_response();
            if let Ok(val) = axum::http::HeaderValue::from_str(&retry_after.to_string()) {
                response.headers_mut().insert(
                    axum::http::header::RETRY_AFTER,
                    val,
                );
            }
            response
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    #[tokio::test]
    async fn test_rate_limiter_allows_first_request() {
        let limiter = RateLimiter::new(10, 60);
        assert!(limiter.check("127.0.0.1").is_ok());
    }

    #[tokio::test]
    async fn test_rate_limiter_allows_within_limit() {
        let limiter = RateLimiter::new(3, 60);
        assert!(limiter.check("client-1").is_ok());
        assert!(limiter.check("client-1").is_ok());
        assert!(limiter.check("client-1").is_ok());
    }

    #[tokio::test]
    async fn test_rate_limiter_blocks_excess() {
        let limiter = RateLimiter::new(2, 60);
        assert!(limiter.check("client-1").is_ok());
        assert!(limiter.check("client-1").is_ok());
        assert!(limiter.check("client-1").is_err());
    }

    #[tokio::test]
    async fn test_rate_limiter_per_key_independence() {
        let limiter = RateLimiter::new(1, 60);
        assert!(limiter.check("client-a").is_ok());
        assert!(limiter.check("client-a").is_err()); // client-a blocked
        assert!(limiter.check("client-b").is_ok()); // client-b still allowed
    }

    #[tokio::test]
    async fn test_rate_limiter_window_resets() {
        let limiter = RateLimiter::new(1, 0); // 0-second window = instant expiry
        // On a 0-second window, each request starts a new window, so the
        // first request is always allowed, but the second within the same
        // reset might also pass because the window expired.
        // Actually: window_duration = 0 means the window checks `now - start >= 0`
        // which is always true, so the window resets on every request.
        assert!(limiter.check("client-1").is_ok());
        assert!(limiter.check("client-1").is_ok()); // Window resets, so OK again
    }

    #[tokio::test]
    async fn test_rate_limiter_tracks_keys() {
        let limiter = RateLimiter::new(5, 60);
        limiter.check("ip-1").ok();
        limiter.check("ip-2").ok();
        limiter.check("ip-3").ok();
        assert_eq!(limiter.tracked_keys(), 3);
    }

    #[test]
    fn test_extract_client_ip_from_header() {
        let req = Request::builder()
            .header("x-forwarded-for", "203.0.113.42, 10.0.0.1")
            .body(axum::body::Body::empty())
            .unwrap();
        assert_eq!(extract_client_ip(&req), "203.0.113.42");
    }

    #[test]
    fn test_extract_client_ip_fallback() {
        let req = Request::builder()
            .body(axum::body::Body::empty())
            .unwrap();
        // No connect info, no x-forwarded-for → "unknown"
        assert_eq!(extract_client_ip(&req), "unknown");
    }

    #[tokio::test]
    async fn test_rate_limiter_high_volume() {
        let limiter = RateLimiter::new(100, 60);
        for i in 0..100 {
            assert!(limiter.check(&format!("bulk-{}", i)).is_ok());
        }
        // 101st unique key should also be allowed (100 requests each, different keys)
        assert!(limiter.check("bulk-100").is_ok());
    }
}

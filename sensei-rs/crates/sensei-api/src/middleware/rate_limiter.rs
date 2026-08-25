//! Rate limiting middleware using a sliding-window log algorithm.
//!
//! Each distinct client (by IP) has its own sliding window: the timestamps
//! of the requests seen in the last `window_duration` are kept in a
//! `VecDeque` and pruned on access. A request is allowed only if the number
//! of timestamps still inside the window is below the configured limit.
//!
//! Unlike a fixed-window counter, the sliding-window log does not suffer
//! from double-bursts at window boundaries: the limit is enforced against
//! *any* contiguous `window_duration` span of time.
//!
//! Stale entries are periodically evicted by a background task so that
//! abandoned keys do not accumulate.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use dashmap::DashMap;
use serde::Serialize;
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::error;

/// Internal state for a single client's sliding window.
///
/// The deque holds the `Instant` of each request still inside the window;
/// entries are ordered oldest-first.
struct RateLimitState {
    /// Timestamps of requests inside the current sliding window.
    timestamps: VecDeque<Instant>,
}

/// A concurrent, key-based rate limiter.
///
/// Each key (typically a client IP) gets its own sliding-window log that
/// allows at most `max_requests` requests in any `window_duration` span.
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
    /// * `window_secs`   – length of the sliding window in seconds.
    pub fn new(max_requests: u32, window_secs: u64) -> Self {
        Self::with_window(max_requests, Duration::from_secs(window_secs))
    }

    /// Create a rate limiter with an explicit window duration.
    ///
    /// `window` may be sub-second (unit tests exercise sliding-window
    /// boundaries with millisecond windows).
    fn with_window(max_requests: u32, window: Duration) -> Self {
        let buckets: Arc<DashMap<String, RateLimitState>> = Arc::new(DashMap::new());

        // Spawn a background cleanup task that periodically evicts stale entries.
        let cleanup_buckets = buckets.clone();
        tokio::spawn(async move {
            cleanup_task(cleanup_buckets, window).await;
        });

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
        let mut entry = self
            .buckets
            .entry(key.to_string())
            .or_insert_with(|| RateLimitState {
                timestamps: VecDeque::new(),
            });

        // Prune timestamps that have fallen out of the sliding window.
        // `window_duration = 0` means "instant expiry": every request starts
        // a fresh window and is therefore allowed.
        if self.window_duration.is_zero() {
            entry.timestamps.clear();
        } else {
            let cutoff = now.checked_sub(self.window_duration).unwrap_or(now);
            while let Some(front) = entry.timestamps.front() {
                if *front < cutoff {
                    entry.timestamps.pop_front();
                } else {
                    break;
                }
            }
        }

        if entry.timestamps.len() >= self.max_requests as usize {
            return Err(());
        }

        entry.timestamps.push_back(now);
        Ok(())
    }

    /// Return the number of keys currently tracked.
    pub fn tracked_keys(&self) -> usize {
        self.buckets.len()
    }
}

/// Background task that periodically removes stale entries from the bucket map.
async fn cleanup_task(buckets: Arc<DashMap<String, RateLimitState>>, window: Duration) {
    // tokio intervals must be non-zero; a zero-length window is pruned on
    // every access anyway, so a 1s sweep is sufficient for cleanup.
    let sweep = window.max(Duration::from_secs(1)) * 2;
    let mut interval = tokio::time::interval(sweep);
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    loop {
        interval.tick().await;
        let cutoff = Instant::now().checked_sub(window.max(Duration::from_secs(1))).unwrap_or(Instant::now());
        buckets.retain(|_, state| {
            state
                .timestamps
                .back()
                .is_some_and(|newest| *newest >= cutoff)
        });
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
    if let Some(connect_info) =
        req.extensions()
            .get::<axum::extract::connect_info::ConnectInfo<std::net::SocketAddr>>()
    {
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
            let retry_after = rate_limiter.window_duration.as_secs().max(1);
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
    use std::time::Duration;

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
        // A zero-length window is pruned on every access, so every request
        // starts a fresh window and is always allowed.
        assert!(limiter.check("client-1").is_ok());
        assert!(limiter.check("client-1").is_ok());
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

    /// Sliding window: once the oldest timestamp falls out of the window the
    /// request is allowed again, even though the wall-clock "window start"
    /// has not reset (the property a fixed-window counter would enforce).
    #[tokio::test]
    async fn test_sliding_window_releases_slot_after_entry_expires() {
        let limiter = RateLimiter::with_window(2, Duration::from_millis(400)); // 2 req / 400ms
        assert!(limiter.check("burst").is_ok());
        assert!(limiter.check("burst").is_ok());
        assert!(limiter.check("burst").is_err());

        // After >400ms the first timestamp has slid out of the window, so a
        // third request is allowed again.
        tokio::time::sleep(Duration::from_millis(500)).await;
        assert!(limiter.check("burst").is_ok());
    }

    /// Boundary behavior: requests spread across the boundary of a fixed
    /// window would double-count; the sliding-window log never does.
    #[tokio::test]
    async fn test_sliding_window_boundary_no_double_burst() {
        let limiter = RateLimiter::with_window(2, Duration::from_millis(200)); // 2 req / 200ms
        assert!(limiter.check("boundary").is_ok());

        // 100ms later the second slot is taken; a third immediate request is
        // rejected.
        tokio::time::sleep(Duration::from_millis(100)).await;
        assert!(limiter.check("boundary").is_ok());
        assert!(limiter.check("boundary").is_err());

        // 150ms later (250ms after the first request) the first entry has
        // expired: exactly one entry remains in the window, so a new
        // request is allowed — a fixed-window counter resetting at t=200
        // would have allowed *two* here.
        tokio::time::sleep(Duration::from_millis(150)).await;
        assert!(limiter.check("boundary").is_ok());
        assert!(limiter.check("boundary").is_err());
    }
}

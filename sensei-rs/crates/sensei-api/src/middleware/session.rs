//! Session binding (fingerprinting) middleware.
//!
//! Prevents token theft by binding authenticated sessions to the original
//! client's `User-Agent` and IP address.  If a request carrying a valid JWT
//! arrives from a different fingerprint, the middleware returns `401
//! Unauthorized`.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use dashmap::DashMap;
use serde::Serialize;
use sensei_auth::middleware::AuthenticatedUser;
use sha2::{Digest, Sha256};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, warn};

/// A stored session fingerprint for a user.
#[derive(Debug, Clone)]
struct SessionFingerprint {
    /// SHA-256 hash of the combined User-Agent + IP.
    fingerprint: String,
    /// When the fingerprint was last verified (for expiry).
    last_seen: Instant,
}

/// Thread-safe store that maps user IDs to their session fingerprints.
#[derive(Clone)]
pub struct SessionStore {
    /// Map of user_id (as string) → fingerprint.
    store: Arc<DashMap<String, SessionFingerprint>>,
    /// How long a fingerprint is considered valid without re-verification.
    ttl: Duration,
}

impl SessionStore {
    /// Create a new [`SessionStore`] with the given TTL (in seconds).
    pub fn new(ttl_secs: u64) -> Self {
        let store = Self {
            store: Arc::new(DashMap::new()),
            ttl: Duration::from_secs(ttl_secs),
        };

        // Background cleanup of stale fingerprints.
        let inner = Arc::clone(&store.store);
        let ttl = store.ttl;
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(300));
            loop {
                interval.tick().await;
                let before = inner.len();
                inner.retain(|_, fp| fp.last_seen.elapsed() < ttl);
                let removed = before - inner.len();
                if removed > 0 {
                    debug!(removed, remaining = inner.len(), "Session-store cleanup");
                }
            }
        });

        store
    }

    /// Register or update a fingerprint for the given user.
    pub fn register(&self, user_id: &str, fingerprint: String) {
        self.store.insert(
            user_id.to_string(),
            SessionFingerprint {
                fingerprint,
                last_seen: Instant::now(),
            },
        );
    }

    /// Verify that the given fingerprint matches the stored one for `user_id`.
    ///
    /// Returns `true` if the fingerprint matches, `false` otherwise.
    /// If no fingerprint is stored yet, the check is treated as a match
    /// (first request) and the fingerprint is registered.
    pub fn verify(&self, user_id: &str, fingerprint: &str) -> bool {
        match self.store.get(user_id) {
            Some(stored) => {
                let matched = stored.fingerprint == fingerprint;
                if matched {
                    // Update last_seen.
                    drop(stored); // Release the ref before modifying.
                    if let Some(mut entry) = self.store.get_mut(user_id) {
                        entry.last_seen = Instant::now();
                    }
                }
                matched
            }
            None => {
                // First time seeing this user – register fingerprint.
                self.register(user_id, fingerprint.to_string());
                true
            }
        }
    }

    /// Remove a session fingerprint (e.g. on logout).
    pub fn remove(&self, user_id: &str) {
        self.store.remove(user_id);
    }
}

/// Compute a SHA-256 fingerprint from `user_agent` and `ip`.
fn compute_fingerprint(user_agent: &str, ip: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(user_agent.as_bytes());
    hasher.update(b"|");
    hasher.update(ip.as_bytes());
    hex::encode(hasher.finalize())
}

/// Error response for fingerprint mismatch.
#[derive(Debug, Serialize)]
struct SessionError {
    error: String,
    message: String,
}

/// Extract the client IP address from the request.
fn extract_client_ip(req: &Request) -> String {
    // Check X-Forwarded-For header first.
    if let Some(val) = req
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
    {
        if let Some(ip) = val.split(',').next().map(|s| s.trim()) {
            if !ip.is_empty() {
                return ip.to_string();
            }
        }
    }

    // Fall back to connect info.
    if let Some(ci) = req
        .extensions()
        .get::<axum::extract::ConnectInfo<std::net::SocketAddr>>()
    {
        return ci.0.ip().to_string();
    }

    "unknown".to_string()
}

/// Axum middleware that enforces session binding.
///
/// For authenticated requests, the middleware computes a fingerprint from
/// the `User-Agent` header and client IP, then compares it against the
/// stored fingerprint for the user.  A mismatch results in `401
/// Unauthorized`.
///
/// The [`SessionStore`] must be injected into request extensions before
/// this middleware runs.
pub async fn session_binding_middleware(mut req: Request, next: Next) -> Response {
    // Only enforce for authenticated requests.
    let user = match req.extensions().get::<AuthenticatedUser>() {
        Some(u) => u.clone(),
        None => return next.run(req).await,
    };

    let session_store = match req.extensions().get::<SessionStore>() {
        Some(s) => s.clone(),
        None => {
            warn!("SessionStore not found in request extensions – session binding disabled");
            return next.run(req).await;
        }
    };

    let user_agent = req
        .headers()
        .get(axum::http::header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("unknown")
        .to_string();

    let client_ip = extract_client_ip(&req);

    let fingerprint = compute_fingerprint(&user_agent, &client_ip);
    let user_id_str = user.user_id.to_string();

    if !session_store.verify(&user_id_str, &fingerprint) {
        warn!(
            user_id = %user_id_str,
            "Session fingerprint mismatch – possible token theft"
        );
        let body = SessionError {
            error: "session_mismatch".to_string(),
            message: "Session fingerprint mismatch. Please re-authenticate.".to_string(),
        };
        return (StatusCode::UNAUTHORIZED, Json(body)).into_response();
    }

    // Re-inject the store (it may have been consumed).
    req.extensions_mut().insert(session_store);

    next.run(req).await
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_fingerprint_deterministic() {
        let fp1 = compute_fingerprint("Mozilla/5.0", "192.168.1.1");
        let fp2 = compute_fingerprint("Mozilla/5.0", "192.168.1.1");
        assert_eq!(fp1, fp2);
    }

    #[test]
    fn test_compute_fingerprint_different_agents() {
        let fp1 = compute_fingerprint("Chrome/120", "10.0.0.1");
        let fp2 = compute_fingerprint("Firefox/121", "10.0.0.1");
        assert_ne!(fp1, fp2);
    }

    #[test]
    fn test_compute_fingerprint_different_ips() {
        let fp1 = compute_fingerprint("Mozilla/5.0", "10.0.0.1");
        let fp2 = compute_fingerprint("Mozilla/5.0", "10.0.0.2");
        assert_ne!(fp1, fp2);
    }

    #[test]
    fn test_compute_fingerprint_not_empty() {
        let fp = compute_fingerprint("", "");
        assert!(!fp.is_empty());
        // SHA-256 hex is always 64 characters.
        assert_eq!(fp.len(), 64);
    }

    #[tokio::test]
    async fn test_session_store_register_and_verify() {
        let store = SessionStore::new(3600);
        let user_id = "user-abc-123";
        let fp = "my-fingerprint-hash";

        // First verify should register and return true.
        assert!(store.verify(user_id, fp));

        // Second verify with matching fingerprint should return true.
        assert!(store.verify(user_id, fp));
    }

    #[tokio::test]
    async fn test_session_store_mismatch() {
        let store = SessionStore::new(3600);
        let user_id = "user-abc-123";

        // Register with first fingerprint.
        assert!(store.verify(user_id, "first-fingerprint"));

        // Verify with different fingerprint should fail.
        assert!(!store.verify(user_id, "second-fingerprint"));
    }

    #[tokio::test]
    async fn test_session_store_remove() {
        let store = SessionStore::new(3600);
        let user_id = "user-to-remove";
        let fp = "some-fingerprint";

        assert!(store.verify(user_id, fp));
        store.remove(user_id);

        // After removal, verify should act as first-time (register) → true.
        assert!(store.verify(user_id, fp));
    }

    #[tokio::test]
    async fn test_session_store_multiple_users() {
        let store = SessionStore::new(3600);

        assert!(store.verify("user-a", "fp-a"));
        assert!(store.verify("user-b", "fp-b"));

        // Mismatch should still fail for each independently.
        assert!(!store.verify("user-a", "fp-b"));
        assert!(!store.verify("user-b", "fp-a"));

        // Correct match still works.
        assert!(store.verify("user-a", "fp-a"));
        assert!(store.verify("user-b", "fp-b"));
    }

    #[test]
    fn test_extract_client_ip_from_x_forwarded_for() {
        let req = Request::builder()
            .header("x-forwarded-for", "203.0.113.42, 10.0.0.1")
            .body(axum::body::Body::empty())
            .unwrap();
        assert_eq!(extract_client_ip(&req), "203.0.113.42");
    }

    #[test]
    fn test_extract_client_ip_no_headers() {
        let req = Request::builder()
            .body(axum::body::Body::empty())
            .unwrap();
        assert_eq!(extract_client_ip(&req), "unknown");
    }

    #[tokio::test]
    async fn test_session_store_ttl_updates_on_verify() {
        let store = SessionStore::new(3600);
        let user_id = "ttl-test";
        store.verify(user_id, "fp");

        // After verify, last_seen should be updated.
        // We can't directly check the internal time, but we can verify
        // the entry still exists by verifying again.
        assert!(store.verify(user_id, "fp"));
    }

    #[test]
    fn test_fingerprint_includes_both_agent_and_ip() {
        // Same agent, different IP = different fingerprint.
        let fp1 = compute_fingerprint("Agent", "10.0.0.1");
        let fp2 = compute_fingerprint("Agent", "10.0.0.2");
        assert_ne!(fp1, fp2);

        // Different agent, same IP = different fingerprint.
        let fp3 = compute_fingerprint("Agent-A", "10.0.0.1");
        let fp4 = compute_fingerprint("Agent-B", "10.0.0.1");
        assert_ne!(fp3, fp4);
    }
}

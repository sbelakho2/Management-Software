//! Session binding (fingerprinting) middleware.
//!
//! Prevents token theft by binding authenticated sessions to the original
//! client's `User-Agent` and IP address.  If a request carrying a valid JWT
//! arrives from a different fingerprint, the stored binding is removed and
//! the middleware returns `401 Unauthorized` (`session_mismatch`), forcing
//! the client to re-authenticate (which re-binds the session).
//!
//! # Client IP resolution
//!
//! The `X-Forwarded-For` header is only trusted when the immediate peer
//! (the `ConnectInfo` socket address) is listed in
//! [`SecurityConfig::trusted_proxies`](sensei_core::config::SecurityConfig).
//! In that case the rightmost non-trusted entry of the XFF chain is used;
//! otherwise the peer address itself is authoritative.

use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use dashmap::DashMap;
use sensei_auth::middleware::AuthenticatedUser;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::net::IpAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, warn};

use crate::state::AppState;

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

/// Outcome of a fingerprint verification.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionResult {
    /// The presented fingerprint matches the stored binding.
    Matches,
    /// The presented fingerprint differs from the stored binding
    /// (possible token theft).
    Mismatch,
    /// No binding is stored for this user yet (first sight).
    Unknown,
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
            interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
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
    ///
    /// Called by the auth routes on login and refresh so that a successful
    /// authentication always re-binds the session to the current client.
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
    /// * [`SessionResult::Matches`] – the fingerprint matches (and its
    ///   `last_seen` is refreshed).
    /// * [`SessionResult::Mismatch`] – the fingerprint differs from the
    ///   stored binding.
    /// * [`SessionResult::Unknown`] – no binding is stored yet; the caller
    ///   decides whether to auto-register.
    pub fn verify(&self, user_id: &str, fingerprint: &str) -> SessionResult {
        match self.store.get(user_id) {
            Some(stored) => {
                if stored.fingerprint == fingerprint {
                    // Update last_seen.
                    drop(stored); // Release the ref before modifying.
                    if let Some(mut entry) = self.store.get_mut(user_id) {
                        entry.last_seen = Instant::now();
                    }
                    SessionResult::Matches
                } else {
                    SessionResult::Mismatch
                }
            }
            None => SessionResult::Unknown,
        }
    }

    /// Remove a session fingerprint (e.g. on logout or on mismatch).
    pub fn remove(&self, user_id: &str) {
        self.store.remove(user_id);
    }

    /// Number of active session bindings currently tracked.
    pub fn len(&self) -> usize {
        self.store.len()
    }

    /// Whether the store holds no session bindings.
    pub fn is_empty(&self) -> bool {
        self.store.is_empty()
    }
}

/// Compute a SHA-256 fingerprint from `user_agent` and `ip`.
///
/// Public so auth routes (login/refresh) can register the same fingerprint
/// the middleware computes on subsequent requests.
pub fn compute_fingerprint(user_agent: &str, ip: &str) -> String {
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

/// Resolve the effective client IP for session fingerprinting.
///
/// * If the immediate peer (`ConnectInfo`) is in `trusted_proxies`, the
///   `X-Forwarded-For` chain is trusted: the rightmost entry that is not
///   itself a trusted proxy is used.
/// * Otherwise the peer address is authoritative.
/// * If no peer address is available, `"unknown"` is returned.
fn extract_client_ip(req: &Request, trusted_proxies: &[IpAddr]) -> String {
    let peer_ip = req
        .extensions()
        .get::<axum::extract::ConnectInfo<std::net::SocketAddr>>()
        .map(|ci| ci.0.ip());

    let xff = req
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok());

    resolve_client_ip(peer_ip, xff, trusted_proxies)
}

/// Resolve the effective client IP from the peer address and (optionally
/// trusted) `X-Forwarded-For` chain.
///
/// Shared by the middleware and the auth routes so login/refresh register
/// the exact same fingerprint the middleware verifies.
pub fn resolve_client_ip(
    peer_ip: Option<IpAddr>,
    xff: Option<&str>,
    trusted_proxies: &[IpAddr],
) -> String {
    let peer_is_trusted = peer_ip
        .map(|ip| trusted_proxies.contains(&ip))
        .unwrap_or(false);

    if peer_is_trusted {
        // Trusted proxy: walk the XFF chain right-to-left and pick the
        // rightmost entry that is not itself a trusted proxy.
        if let Some(value) = xff {
            for candidate in value.split(',').rev() {
                let candidate = candidate.trim();
                if candidate.is_empty() {
                    continue;
                }
                let is_trusted = candidate
                    .parse::<IpAddr>()
                    .is_ok_and(|ip| trusted_proxies.contains(&ip));
                if !is_trusted {
                    return candidate.to_string();
                }
            }
        }
        // Every XFF entry is trusted (or the header is absent): the request
        // is indistinguishable from the proxy itself.
        return peer_ip
            .map(|ip| ip.to_string())
            .unwrap_or_else(|| "unknown".to_string());
    }

    match peer_ip {
        Some(ip) => ip.to_string(),
        None => "unknown".to_string(),
    }
}

/// Compute the session fingerprint for a request without a full `Request`
/// (used by the auth routes, which only have extractor parts).
pub fn session_fingerprint(
    peer_ip: Option<IpAddr>,
    xff: Option<&str>,
    user_agent: Option<&str>,
    trusted_proxies: &[IpAddr],
) -> String {
    let ip = resolve_client_ip(peer_ip, xff, trusted_proxies);
    compute_fingerprint(user_agent.unwrap_or("unknown"), &ip)
}

/// Axum middleware that enforces session binding.
///
/// Runs after authentication, so [`AuthenticatedUser`] is present in the
/// request extensions.  For authenticated requests, the middleware computes
/// a fingerprint from the `User-Agent` header and the effective client IP,
/// then compares it against the stored fingerprint for the user.
///
/// * First sight (no stored binding) – the fingerprint is auto-registered.
/// * Mismatch – the stored binding is removed, `possible token theft` is
///   logged, and `401 session_mismatch` is returned (forces re-login).
pub async fn session_binding_middleware(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Response {
    // Only enforce for authenticated requests.
    let user = match req.extensions().get::<AuthenticatedUser>() {
        Some(u) => u.clone(),
        None => return next.run(req).await,
    };

    let session_store = state.session_store.clone();

    let user_agent = req
        .headers()
        .get(axum::http::header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("unknown")
        .to_string();

    let client_ip = extract_client_ip(&req, &state.config.security.trusted_proxies);
    let fingerprint = compute_fingerprint(&user_agent, &client_ip);
    let user_id_str = user.user_id.to_string();

    match session_store.verify(&user_id_str, &fingerprint) {
        SessionResult::Matches => {}
        SessionResult::Unknown => {
            // First time seeing this user on this client – register.
            debug!(user_id = %user_id_str, "Registering session fingerprint (first sight)");
            session_store.register(&user_id_str, fingerprint);
        }
        SessionResult::Mismatch => {
            // Remove the stale binding so the next login re-binds cleanly.
            session_store.remove(&user_id_str);
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
    }

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

        // First verify is Unknown (no binding yet).
        assert_eq!(store.verify(user_id, fp), SessionResult::Unknown);

        // Explicit registration, then verification matches.
        store.register(user_id, fp.to_string());
        assert_eq!(store.verify(user_id, fp), SessionResult::Matches);
    }

    #[tokio::test]
    async fn test_session_store_mismatch() {
        let store = SessionStore::new(3600);
        let user_id = "user-abc-123";

        store.register(user_id, "first-fingerprint".to_string());

        // Verify with different fingerprint should fail.
        assert_eq!(
            store.verify(user_id, "second-fingerprint"),
            SessionResult::Mismatch
        );

        // The stored binding is untouched by verify; the middleware removes
        // it explicitly on mismatch.
        assert_eq!(
            store.verify(user_id, "first-fingerprint"),
            SessionResult::Matches
        );
    }

    #[tokio::test]
    async fn test_session_store_remove() {
        let store = SessionStore::new(3600);
        let user_id = "user-to-remove";
        let fp = "some-fingerprint";

        store.register(user_id, fp.to_string());
        assert_eq!(store.verify(user_id, fp), SessionResult::Matches);
        store.remove(user_id);

        // After removal, verify reports Unknown (no binding stored).
        assert_eq!(store.verify(user_id, fp), SessionResult::Unknown);
    }

    #[tokio::test]
    async fn test_session_store_multiple_users() {
        let store = SessionStore::new(3600);

        store.register("user-a", "fp-a".to_string());
        store.register("user-b", "fp-b".to_string());

        // Mismatch should still fail for each independently.
        assert_eq!(store.verify("user-a", "fp-b"), SessionResult::Mismatch);
        assert_eq!(store.verify("user-b", "fp-a"), SessionResult::Mismatch);

        // Correct match still works.
        assert_eq!(store.verify("user-a", "fp-a"), SessionResult::Matches);
        assert_eq!(store.verify("user-b", "fp-b"), SessionResult::Matches);
    }

    fn req_with_peer(peer: Option<IpAddr>, xff: Option<&str>) -> Request {
        let mut builder = Request::builder().uri("/");
        if let Some(xff) = xff {
            builder = builder.header("x-forwarded-for", xff);
        }
        let mut req = builder.body(axum::body::Body::empty()).unwrap();
        if let Some(ip) = peer {
            let ci = axum::extract::ConnectInfo(std::net::SocketAddr::new(ip, 12345));
            req.extensions_mut().insert(ci);
        }
        req
    }

    fn ip(s: &str) -> IpAddr {
        s.parse().unwrap()
    }

    #[test]
    fn test_extract_client_ip_untrusted_peer_ignores_xff() {
        // Peer 203.0.113.10 is NOT a trusted proxy: X-Forwarded-For must be
        // ignored and the peer address used.
        let trusted = vec![ip("10.0.0.1"), ip("10.0.0.2")];
        let req = req_with_peer(Some(ip("203.0.113.10")), Some("198.51.100.7, 10.0.0.2"));
        assert_eq!(extract_client_ip(&req, &trusted), "203.0.113.10");
    }

    #[test]
    fn test_extract_client_ip_trusted_proxy_uses_rightmost_foreign_xff() {
        // Peer 10.0.0.1 IS trusted: use the rightmost non-trusted XFF entry.
        let trusted = vec![ip("10.0.0.1"), ip("10.0.0.2")];
        let req = req_with_peer(
            Some(ip("10.0.0.1")),
            Some("198.51.100.7, 10.0.0.2, 203.0.113.99"),
        );
        assert_eq!(extract_client_ip(&req, &trusted), "203.0.113.99");
    }

    #[test]
    fn test_extract_client_ip_trusted_proxy_all_entries_trusted_falls_back_to_peer() {
        let trusted = vec![ip("10.0.0.1"), ip("10.0.0.2")];
        let req = req_with_peer(Some(ip("10.0.0.1")), Some("10.0.0.2, 10.0.0.1"));
        assert_eq!(extract_client_ip(&req, &trusted), "10.0.0.1");
    }

    #[test]
    fn test_extract_client_ip_no_peer_unknown() {
        let req = req_with_peer(None, Some("198.51.100.7"));
        assert_eq!(extract_client_ip(&req, &[]), "unknown");
    }

    #[test]
    fn test_extract_client_ip_plain_peer() {
        let req = req_with_peer(Some(ip("192.168.1.5")), None);
        assert_eq!(extract_client_ip(&req, &[]), "192.168.1.5");
    }

    #[tokio::test]
    async fn test_session_store_ttl_updates_on_verify() {
        let store = SessionStore::new(3600);
        let user_id = "ttl-test";
        store.register(user_id, "fp".to_string());

        // After verify, last_seen should be updated. We can't check the
        // internal time, but the entry must still exist afterwards.
        assert_eq!(store.verify(user_id, "fp"), SessionResult::Matches);
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

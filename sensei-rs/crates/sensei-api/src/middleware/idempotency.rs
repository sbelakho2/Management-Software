//! Idempotency middleware.
//!
//! Allows clients to safely retry POST, PUT, and PATCH requests by providing
//! an `Idempotency-Key` header.  When a request with a known key arrives,
//! the previously stored response is returned without re-executing the
//! handler.
//!
//! # Cache-key scoping
//!
//! The cache key is `sha256("{user_id}|{path}|{idempotency_key}")`, so the
//! same key used by different users (or on different paths) never collides.
//! This middleware runs after authentication and reads the
//! [`AuthenticatedUser`] from the request extensions.
//!
//! # Safety properties
//!
//! * 5xx responses are never cached, so a transient server failure does not
//!   poison the retry.
//! * Responses larger than 1 MiB are not cached.
//! * A per-key mutex serializes concurrent requests carrying the same key,
//!   so a duplicate is not double-executed: the second request waits for the
//!   first and then replays its cached response.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
};
use dashmap::DashMap;
use sensei_auth::middleware::AuthenticatedUser;
use sha2::{Digest, Sha256};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;
use tracing::{debug, trace, warn};

/// Upper bound for cached response bodies (1 MiB). Larger responses are
/// passed through without being cached.
const MAX_CACHED_BODY_BYTES: usize = 1024 * 1024;

/// A cached response for a given idempotency key.
#[derive(Debug, Clone)]
pub struct StoredResponse {
    /// HTTP status code.
    pub status_code: u16,
    /// Response headers (name → value pairs).
    pub headers: Vec<(String, String)>,
    /// Raw response body bytes.
    pub body: Vec<u8>,
    /// When this entry was created (for TTL-based eviction).
    pub created_at: Instant,
}

/// Thread-safe store for idempotent request responses.
///
/// Entries are automatically evicted after a configurable TTL. A companion
/// per-key lock map serializes concurrent execution for the same key.
#[derive(Clone)]
pub struct IdempotencyStore {
    responses: Arc<DashMap<String, StoredResponse>>,
    /// Per-key concurrency guards: one `Mutex` per cache key, held for the
    /// duration of handler execution so duplicate concurrent requests with
    /// the same key do not double-execute.
    locks: Arc<DashMap<String, Arc<Mutex<()>>>>,
    /// Time-to-live for each cached response.
    ttl: Duration,
}

impl IdempotencyStore {
    /// Create a new [`IdempotencyStore`].
    ///
    /// # Arguments
    /// * `ttl_secs` – number of seconds before a cached response expires.
    pub fn new(ttl_secs: u64) -> Self {
        let store = Self {
            responses: Arc::new(DashMap::new()),
            locks: Arc::new(DashMap::new()),
            ttl: Duration::from_secs(ttl_secs),
        };

        // Spawn a background eviction task.
        let inner = Arc::clone(&store.responses);
        let locks = Arc::clone(&store.locks);
        let ttl = store.ttl;
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(300));
            interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
            loop {
                interval.tick().await;
                let before = inner.len();
                inner.retain(|_, stored| stored.created_at.elapsed() < ttl);
                let removed = before - inner.len();
                // Drop locks for keys whose response is gone. A lock that is
                // currently held stays alive via its `Arc` until the holder
                // finishes; the holder's post-lock cache check keeps
                // correctness.
                locks.retain(|key, _| inner.contains_key(key));
                if removed > 0 {
                    debug!(
                        removed,
                        remaining = inner.len(),
                        "Idempotency-store cleanup"
                    );
                }
            }
        });

        store
    }

    /// Retrieve a cached response by key.
    pub fn get(&self, key: &str) -> Option<StoredResponse> {
        self.responses.get(key).and_then(|r| {
            let stored = r.value();
            // Don't return expired entries.
            if stored.created_at.elapsed() >= self.ttl {
                None
            } else {
                Some(stored.clone())
            }
        })
    }

    /// Store a response for the given key.
    pub fn store(&self, key: String, response: StoredResponse) {
        self.responses.insert(key, response);
    }

    /// Remove a key (e.g. after a failed request so the client can retry).
    pub fn remove(&self, key: &str) {
        self.responses.remove(key);
    }

    /// Acquire the per-key concurrency guard.
    ///
    /// Returns an owned guard, so the mutex stays alive (via its `Arc`) for
    /// as long as the guard is held.
    pub async fn lock_for(&self, key: &str) -> tokio::sync::OwnedMutexGuard<()> {
        let lock = self
            .locks
            .entry(key.to_string())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone();
        lock.lock_owned().await
    }

    /// Return the number of cached responses.
    pub fn len(&self) -> usize {
        self.responses.len()
    }

    /// Return `true` if there are no cached responses.
    pub fn is_empty(&self) -> bool {
        self.responses.is_empty()
    }
}

/// Compute the scoped cache key: `sha256("{user_id}|{path}|{key}")`.
fn compute_cache_key(user_id: &str, path: &str, idempotency_key: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(user_id.as_bytes());
    hasher.update(b"|");
    hasher.update(path.as_bytes());
    hasher.update(b"|");
    hasher.update(idempotency_key.as_bytes());
    hex::encode(hasher.finalize())
}

/// Axum middleware that handles idempotency keys.
///
/// Reads the `Idempotency-Key` header from POST, PUT, and PATCH requests.
/// If a cached response exists for the key (scoped to the authenticated
/// user and path) it is returned immediately. Otherwise the request passes
/// through under a per-key mutex and the response is cached for future
/// retries.
///
/// The [`IdempotencyStore`] must be injected into request extensions before
/// this middleware runs.
pub async fn idempotency_middleware(req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let is_idempotent_method = matches!(method.as_str(), "POST" | "PUT" | "PATCH");

    if !is_idempotent_method {
        return next.run(req).await;
    }

    let idempotency_key = req
        .headers()
        .get("Idempotency-Key")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty());

    let store_option = req.extensions().get::<IdempotencyStore>().cloned();

    // Determine if we have both a key and a store.
    let (key, store) = match (idempotency_key, store_option) {
        (Some(k), Some(s)) => (k, s),
        (Some(_), None) => {
            warn!("IdempotencyStore not in request extensions – idempotency disabled for this request");
            return next.run(req).await;
        }
        // No idempotency key supplied – pass through.
        (None, _) => return next.run(req).await,
    };

    // Runs after authentication: the cache key is scoped to the user.
    let user_id = req
        .extensions()
        .get::<AuthenticatedUser>()
        .map(|u| u.user_id.to_string())
        .unwrap_or_else(|| "anonymous".to_string());
    let path = req.uri().path().to_string();
    let cache_key = compute_cache_key(&user_id, &path, &key);

    // Check for a cached response.
    if let Some(cached) = store.get(&cache_key) {
        trace!(key = %key, "Returning cached idempotent response");
        return stored_response_into_response(cached);
    }

    // Serialize concurrent duplicates of the same key: the first request
    // executes; later ones wait and then replay the cached response.
    let _guard = store.lock_for(&cache_key).await;

    // Double-check under the lock – another request may have executed and
    // cached the response while we were waiting.
    if let Some(cached) = store.get(&cache_key) {
        trace!(key = %key, "Returning cached idempotent response (after waiting for duplicate)");
        return stored_response_into_response(cached);
    }

    // No cached response – run the handler and cache the result.
    let response = next.run(req).await;

    // Never cache 5xx responses: a transient failure must be retryable.
    let status = response.status();
    if status.is_server_error() {
        store.remove(&cache_key);
        return response;
    }

    let (parts, body) = response.into_parts();

    // Collect the response body bytes.
    let body_bytes = match collect_body(body).await {
        Ok(bytes) => bytes,
        Err(e) => {
            warn!(error = %e, "Failed to read response body for idempotency caching");
            return (parts, axum::body::Body::empty()).into_response();
        }
    };

    // Do not cache oversized bodies.
    if body_bytes.len() > MAX_CACHED_BODY_BYTES {
        debug!(
            bytes = body_bytes.len(),
            "Response body exceeds idempotency cache limit; not caching"
        );
        return (
            parts,
            axum::body::Body::from(axum::body::Bytes::from(body_bytes)),
        )
            .into_response();
    }

    // Collect response headers.
    let headers: Vec<(String, String)> = parts
        .headers
        .iter()
        .map(|(name, value)| (name.to_string(), value.to_str().unwrap_or("").to_string()))
        .collect();

    let stored = StoredResponse {
        status_code: status.as_u16(),
        headers,
        body: body_bytes.clone(),
        created_at: Instant::now(),
    };
    store.store(cache_key, stored);

    // Reconstruct the response.
    (
        parts,
        axum::body::Body::from(axum::body::Bytes::from(body_bytes)),
    )
        .into_response()
}

/// Rebuild an HTTP response from a [`StoredResponse`].
fn stored_response_into_response(cached: StoredResponse) -> Response {
    let mut response = Response::new(axum::body::Body::from(axum::body::Bytes::from(cached.body)));
    *response.status_mut() =
        StatusCode::from_u16(cached.status_code).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR);
    for (name, value) in &cached.headers {
        if let (Ok(header_name), Ok(header_value)) = (
            axum::http::HeaderName::from_bytes(name.as_bytes()),
            axum::http::HeaderValue::from_str(value),
        ) {
            response.headers_mut().insert(header_name, header_value);
        }
    }
    response
}

/// Collect all body bytes from an [`axum::body::Body`] using the
/// stream-based API (no external trait dependency needed).
async fn collect_body(body: axum::body::Body) -> Result<Vec<u8>, String> {
    use futures::StreamExt;
    let mut stream = body.into_data_stream();
    let mut all_bytes = Vec::new();
    while let Some(chunk) = stream.next().await {
        match chunk {
            Ok(data) => all_bytes.extend_from_slice(&data),
            Err(e) => return Err(e.to_string()),
        }
    }
    Ok(all_bytes)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_idempotency_store_store_and_get() {
        let store = IdempotencyStore::new(3600);
        assert!(store.is_empty());
        assert_eq!(store.len(), 0);

        let response = StoredResponse {
            status_code: 201,
            headers: vec![("content-type".into(), "application/json".into())],
            body: b"{\"id\":\"abc\"}".to_vec(),
            created_at: Instant::now(),
        };

        store.store("key-1".into(), response.clone());
        assert_eq!(store.len(), 1);
        assert!(!store.is_empty());

        let cached = store.get("key-1").unwrap();
        assert_eq!(cached.status_code, 201);
        assert_eq!(cached.body, b"{\"id\":\"abc\"}".to_vec());
    }

    #[tokio::test]
    async fn test_idempotency_store_missing_key() {
        let store = IdempotencyStore::new(3600);
        assert!(store.get("nonexistent").is_none());
    }

    #[tokio::test]
    async fn test_idempotency_store_remove() {
        let store = IdempotencyStore::new(3600);
        let response = StoredResponse {
            status_code: 200,
            headers: vec![],
            body: vec![],
            created_at: Instant::now(),
        };
        store.store("key-1".into(), response);
        assert_eq!(store.len(), 1);

        store.remove("key-1");
        assert!(store.is_empty());
    }

    #[tokio::test]
    async fn test_idempotency_store_overwrite() {
        let store = IdempotencyStore::new(3600);

        let r1 = StoredResponse {
            status_code: 200,
            headers: vec![],
            body: b"first".to_vec(),
            created_at: Instant::now(),
        };
        let r2 = StoredResponse {
            status_code: 200,
            headers: vec![],
            body: b"second".to_vec(),
            created_at: Instant::now(),
        };

        store.store("key-1".into(), r1);
        store.store("key-1".into(), r2);

        let cached = store.get("key-1").unwrap();
        assert_eq!(cached.body, b"second".to_vec());
    }

    #[tokio::test]
    async fn test_idempotency_store_ttl_expiry() {
        // TTL of 0 seconds = immediate expiry.
        let store = IdempotencyStore::new(0);
        let response = StoredResponse {
            status_code: 200,
            headers: vec![],
            body: vec![],
            created_at: Instant::now(),
        };
        store.store("key-1".into(), response);

        // The TTL is 0, so the entry is already expired.
        tokio::time::sleep(Duration::from_millis(10)).await;

        let cached = store.get("key-1");
        assert!(cached.is_none());
    }

    #[tokio::test]
    async fn test_idempotency_store_multiple_keys() {
        let store = IdempotencyStore::new(3600);
        for i in 0..10 {
            let response = StoredResponse {
                status_code: 200,
                headers: vec![],
                body: format!("body-{}", i).into_bytes(),
                created_at: Instant::now(),
            };
            store.store(format!("key-{}", i), response);
        }
        assert_eq!(store.len(), 10);

        for i in 0..10 {
            let cached = store.get(&format!("key-{}", i));
            assert!(cached.is_some());
            assert_eq!(cached.unwrap().body, format!("body-{}", i).into_bytes());
        }
    }

    #[test]
    fn test_cache_key_is_scoped_to_user_and_path() {
        let k1 = compute_cache_key("user-a", "/api/v1/tasks", "key-1");
        let k2 = compute_cache_key("user-b", "/api/v1/tasks", "key-1");
        let k3 = compute_cache_key("user-a", "/api/v1/other", "key-1");
        let k4 = compute_cache_key("user-a", "/api/v1/tasks", "key-2");
        let k5 = compute_cache_key("user-a", "/api/v1/tasks", "key-1");

        assert_ne!(k1, k2, "same key must be scoped per user");
        assert_ne!(k1, k3, "same key must be scoped per path");
        assert_ne!(k1, k4, "different keys differ");
        assert_eq!(k1, k5, "deterministic");
    }

    #[tokio::test]
    async fn test_per_key_lock_serializes_concurrent_execution() {
        let store = IdempotencyStore::new(3600);
        let key = "same-key";

        // Two concurrent holders of the same key must be mutually exclusive.
        let guard1 = store.lock_for(key).await;
        let attempts = Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let attempts_clone = Arc::clone(&attempts);

        let store2 = store.clone();
        let key2 = key.to_string();
        let handle = tokio::spawn(async move {
            attempts_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            let _guard = store2.lock_for(&key2).await;
            // Only reachable after guard1 is released.
            attempts_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        });

        // Give the spawned task a chance to block on the lock.
        tokio::time::sleep(Duration::from_millis(50)).await;
        assert_eq!(
            attempts.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "second holder must still be waiting for the first"
        );

        drop(guard1);
        handle.await.unwrap();
        assert_eq!(attempts.load(std::sync::atomic::Ordering::SeqCst), 2);
    }

    #[test]
    fn test_collect_body_empty() {
        // Unit-style test for the collect_body helper.
        let body = axum::body::Body::empty();
        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(collect_body(body));
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }
}

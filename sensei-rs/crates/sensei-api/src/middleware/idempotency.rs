//! Idempotency middleware.
//!
//! Allows clients to safely retry POST, PUT, and PATCH requests by providing
//! an `Idempotency-Key` header.  When a request with a known key arrives,
//! the previously stored response is returned without re-executing the
//! handler.
//!
//! # Cache-key scoping
//!
//! The cache key is
//! `sha256(tenant_id|user_id|method|normalized_path|Idempotency-Key)`, so
//! the same key used by different users (or on different paths, or with
//! different methods) never collides. This middleware runs after
//! authentication and reads the [`AuthenticatedUser`] from the request
//! extensions.
//!
//! # Claim semantics
//!
//! * The claim is **atomic**: in PostgreSQL mode it is an
//!   `INSERT ... ON CONFLICT DO NOTHING` in state `in_progress`, so two
//!   replicas can never execute the same key concurrently.
//! * On conflict, an existing record is inspected:
//!   * `completed` + matching request hash → the cached response is replayed;
//!   * `completed` + different request hash → `422` `idempotency_key_reuse`;
//!   * `in_progress` → `409` with `Retry-After` (another replica is
//!     executing).
//! * On handler success the record is flipped to `completed` with the
//!   status and response body; **5xx responses are never cached** (the
//!   claim is aborted so a retry can re-execute).
//! * A per-key in-process mutex additionally serializes concurrent
//!   duplicates within one replica: the second request waits for the first
//!   and then replays its cached response.
//!
//! # Storage
//!
//! PostgreSQL (`idempotency_records`, migration 051) when a pool is
//! configured; a [`DashMap`] with identical semantics in development mode.
//! In both modes the request body is buffered once (bounded by
//! [`MAX_CACHED_BODY_BYTES`]; oversized bodies bypass idempotency) so the
//! request hash can be computed, and responses larger than 1 MiB are never
//! cached.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use dashmap::DashMap;
use sensei_auth::middleware::AuthenticatedUser;
use serde::Serialize;
use sha2::{Digest, Sha256};
use sqlx::PgPool;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;
use tracing::{debug, trace, warn};

/// Upper bound for cached request/response bodies (1 MiB). Larger
/// requests/responses bypass idempotency caching.
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
    /// SHA-256 of the request body this response answers.
    pub request_hash: String,
    /// Whether the handler is still executing for this key.
    pub in_progress: bool,
}

/// Outcome of claiming an idempotency key.
#[derive(Debug)]
enum Claim {
    /// The claim was acquired; the handler must run.
    New,
    /// A completed record with a matching request hash exists; replay it.
    Replay(StoredResponse),
    /// A completed record with a different request hash exists (422).
    ReuseConflict,
    /// Another worker is executing this key right now (409).
    InProgress,
}

/// Error body for idempotency conflicts.
#[derive(Serialize)]
struct IdempotencyError {
    error: String,
    message: String,
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
    /// PostgreSQL pool when the store is DB-backed.
    pool: Option<Arc<PgPool>>,
}

impl IdempotencyStore {
    /// Create a new in-memory [`IdempotencyStore`].
    ///
    /// # Arguments
    /// * `ttl_secs` – number of seconds before a cached response expires.
    pub fn new(ttl_secs: u64) -> Self {
        Self::with_pool(ttl_secs, None)
    }

    /// Create an [`IdempotencyStore`], optionally backed by a PostgreSQL
    /// pool (dev fallback is in-memory).
    pub fn with_pool(ttl_secs: u64, pool: Option<Arc<PgPool>>) -> Self {
        let store = Self {
            responses: Arc::new(DashMap::new()),
            locks: Arc::new(DashMap::new()),
            ttl: Duration::from_secs(ttl_secs),
            pool,
        };

        // Spawn a background eviction task (in-memory entries) and, when a
        // pool is present, sweep expired DB records.
        let inner = Arc::clone(&store.responses);
        let locks = Arc::clone(&store.locks);
        let ttl = store.ttl;
        let db_pool = store.pool.clone();
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
                if let Some(pool) = &db_pool {
                    if let Err(e) =
                        sqlx::query("DELETE FROM idempotency_records WHERE expires_at < NOW()")
                            .execute(&**pool)
                            .await
                    {
                        debug!(error = %e, "Idempotency DB cleanup failed");
                    }
                }
            }
        });

        store
    }

    /// Retrieve a completed cached response by key (in-memory mode).
    pub fn get(&self, key: &str) -> Option<StoredResponse> {
        self.responses.get(key).and_then(|r| {
            let stored = r.value();
            // Don't return expired or in-flight entries.
            if stored.in_progress || stored.created_at.elapsed() >= self.ttl {
                None
            } else {
                Some(stored.clone())
            }
        })
    }

    /// Store a response for the given key (in-memory mode).
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

    /// Atomically claim a key for execution.
    ///
    /// See the module docs for the state machine.
    async fn claim(&self, key: &str, request_hash: &str) -> Result<Claim, String> {
        match &self.pool {
            None => {
                if let Some(existing) = self.responses.get(key) {
                    let existing = existing.value().clone();
                    if existing.in_progress {
                        return Ok(Claim::InProgress);
                    }
                    if existing.request_hash != request_hash {
                        return Ok(Claim::ReuseConflict);
                    }
                    return Ok(Claim::Replay(existing));
                }
                self.responses.insert(
                    key.to_string(),
                    StoredResponse {
                        status_code: 0,
                        headers: Vec::new(),
                        body: Vec::new(),
                        created_at: Instant::now(),
                        request_hash: request_hash.to_string(),
                        in_progress: true,
                    },
                );
                Ok(Claim::New)
            }
            Some(pool) => {
                let expires_at =
                    chrono::Utc::now() + chrono::Duration::from_std(self.ttl).unwrap_or_default();
                let inserted = sqlx::query(
                    "INSERT INTO idempotency_records \
                     (key, request_hash, state, status, response_body, expires_at) \
                     VALUES ($1, $2, 'in_progress', NULL, NULL, $3) \
                     ON CONFLICT (key) DO NOTHING",
                )
                .bind(key)
                .bind(request_hash)
                .bind(expires_at)
                .execute(&**pool)
                .await
                .map_err(|e| format!("Idempotency claim failed: {e}"))?;

                if inserted.rows_affected() == 1 {
                    return Ok(Claim::New);
                }

                // The key already exists: inspect the current record.
                let row = sqlx::query_as::<_, (String, String, Option<i32>, Option<Vec<u8>>)>(
                    "SELECT request_hash, state, status, response_body \
                     FROM idempotency_records WHERE key = $1 AND expires_at > NOW()",
                )
                .bind(key)
                .fetch_optional(&**pool)
                .await
                .map_err(|e| format!("Idempotency lookup failed: {e}"))?;

                match row {
                    Some((stored_hash, state, status, body)) => match state.as_str() {
                        "completed" => {
                            if stored_hash != request_hash {
                                Ok(Claim::ReuseConflict)
                            } else {
                                Ok(Claim::Replay(StoredResponse {
                                    status_code: status.unwrap_or(200) as u16,
                                    headers: Vec::new(),
                                    body: body.unwrap_or_default(),
                                    created_at: Instant::now(),
                                    request_hash: stored_hash,
                                    in_progress: false,
                                }))
                            }
                        }
                        _ => Ok(Claim::InProgress),
                    },
                    // The existing row is expired: reclaim it atomically.
                    None => {
                        let reclaimed = sqlx::query(
                            "UPDATE idempotency_records \
                             SET request_hash = $2, state = 'in_progress', status = NULL, \
                                 response_body = NULL, expires_at = $3 \
                             WHERE key = $1 AND expires_at <= NOW()",
                        )
                        .bind(key)
                        .bind(request_hash)
                        .bind(expires_at)
                        .execute(&**pool)
                        .await
                        .map_err(|e| format!("Idempotency reclaim failed: {e}"))?;

                        if reclaimed.rows_affected() == 1 {
                            Ok(Claim::New)
                        } else {
                            // Lost the race to another worker.
                            Ok(Claim::InProgress)
                        }
                    }
                }
            }
        }
    }

    /// Flip a claimed key to `completed` with the cached response.
    async fn complete(&self, key: &str, response: StoredResponse) {
        match &self.pool {
            Some(pool) => {
                if let Err(e) = sqlx::query(
                    "UPDATE idempotency_records \
                     SET state = 'completed', status = $2, response_body = $3 \
                     WHERE key = $1",
                )
                .bind(key)
                .bind(response.status_code as i32)
                .bind(response.body)
                .execute(&**pool)
                .await
                {
                    warn!(error = %e, key, "Failed to store idempotency response");
                }
            }
            None => {
                self.responses.insert(key.to_string(), response);
            }
        }
    }

    /// Abort a claim (used for 5xx responses so a retry can re-execute).
    async fn abort(&self, key: &str) {
        match &self.pool {
            Some(pool) => {
                if let Err(e) = sqlx::query("DELETE FROM idempotency_records WHERE key = $1")
                    .bind(key)
                    .execute(&**pool)
                    .await
                {
                    warn!(error = %e, key, "Failed to abort idempotency claim");
                }
            }
            None => {
                self.responses.remove(key);
            }
        }
    }

    /// Return the number of cached responses (in-memory mode).
    pub fn len(&self) -> usize {
        self.responses.len()
    }

    /// Return `true` if there are no cached responses.
    pub fn is_empty(&self) -> bool {
        self.responses.is_empty()
    }
}

/// Compute the scoped cache key:
/// `sha256(tenant_id|user_id|method|normalized_path|idempotency_key)`.
fn compute_cache_key(
    tenant_id: &str,
    user_id: &str,
    method: &str,
    path: &str,
    idempotency_key: &str,
) -> String {
    let mut hasher = Sha256::new();
    hasher.update(tenant_id.as_bytes());
    hasher.update(b"|");
    hasher.update(user_id.as_bytes());
    hasher.update(b"|");
    hasher.update(method.as_bytes());
    hasher.update(b"|");
    hasher.update(path.as_bytes());
    hasher.update(b"|");
    hasher.update(idempotency_key.as_bytes());
    hex::encode(hasher.finalize())
}

/// Normalize a request path for cache-key scoping: strip trailing slashes.
fn normalize_path(path: &str) -> String {
    let trimmed = path.trim_end_matches('/');
    if trimmed.is_empty() {
        "/".to_string()
    } else {
        trimmed.to_string()
    }
}

/// SHA-256 hex digest of a byte slice (the request body).
fn hash_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

/// Axum middleware that handles idempotency keys.
///
/// Reads the `Idempotency-Key` header from POST, PUT, and PATCH requests.
/// If a completed record exists for the key (scoped to the authenticated
/// user, tenant, method and normalized path) it is returned immediately —
/// provided the request body hash matches; otherwise the request passes
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

    // Runs after authentication: the cache key is scoped to user + tenant.
    let (user_id, tenant_id) = req
        .extensions()
        .get::<AuthenticatedUser>()
        .map(|u| (u.user_id.to_string(), u.tenant_id.to_string()))
        .unwrap_or_else(|| ("anonymous".to_string(), "anonymous".to_string()));
    let path = normalize_path(req.uri().path());
    let cache_key = compute_cache_key(&tenant_id, &user_id, method.as_str(), &path, &key);

    // Capture the request body once so its hash can be compared on retries,
    // then reconstruct the request from the buffered bytes.
    let (parts, body) = req.into_parts();
    let body_bytes = match collect_body(body).await {
        Ok(bytes) => bytes,
        Err(e) => {
            warn!(
                error = %e,
                "Failed to capture request body for idempotency; skipping idempotency"
            );
            return next
                .run(Request::from_parts(parts, axum::body::Body::empty()))
                .await;
        }
    };
    let req = Request::from_parts(parts, axum::body::Body::from(body_bytes.clone()));

    if body_bytes.len() > MAX_CACHED_BODY_BYTES {
        debug!(
            bytes = body_bytes.len(),
            "Request body exceeds idempotency limit; skipping idempotency for this request"
        );
        return next.run(req).await;
    }
    let request_hash = hash_hex(&body_bytes);

    // Fast path (in-memory store only): a completed response may already be
    // cached for this key.
    if store.pool.is_none() {
        if let Some(cached) = store.get(&cache_key) {
            if cached.request_hash == request_hash {
                trace!(key = %key, "Returning cached idempotent response");
                return stored_response_into_response(cached);
            }
        }
    }

    // Serialize concurrent duplicates of the same key: the first request
    // executes; later ones wait and then replay the cached response.
    let _guard = store.lock_for(&cache_key).await;

    // Claim the key (double-check under the lock — another request may have
    // executed and cached the response while we were waiting).
    match store.claim(&cache_key, &request_hash).await {
        Ok(Claim::Replay(cached)) => {
            trace!(key = %key, "Returning cached idempotent response (after waiting for duplicate)");
            return stored_response_into_response(cached);
        }
        Ok(Claim::ReuseConflict) => {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(IdempotencyError {
                    error: "idempotency_key_reuse".to_string(),
                    message: "Idempotency-Key was already used with a different request"
                        .to_string(),
                }),
            )
                .into_response();
        }
        Ok(Claim::InProgress) => {
            let mut response = (
                StatusCode::CONFLICT,
                Json(IdempotencyError {
                    error: "idempotency_key_in_progress".to_string(),
                    message: "A request with this Idempotency-Key is already being processed"
                        .to_string(),
                }),
            )
                .into_response();
            response.headers_mut().insert(
                axum::http::header::RETRY_AFTER,
                axum::http::HeaderValue::from_static("1"),
            );
            return response;
        }
        Err(e) => {
            // FAIL CLOSED: idempotency exists to prevent duplicate side
            // effects. If the store cannot answer, the mutation must not
            // run unprotected.
            tracing::error!(
                error = %e,
                "Idempotency store unavailable — refusing to execute the request"
            );
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                Json(IdempotencyError {
                    error: "idempotency_store_unavailable".to_string(),
                    message: "The idempotency store is temporarily unavailable. Please retry."
                        .to_string(),
                }),
            )
                .into_response();
        }
        Ok(Claim::New) => {}
    }

    // Claimed – run the handler and cache the result.
    let response = next.run(req).await;

    // Never cache 5xx responses: a transient failure must be retryable.
    let status = response.status();
    if status.is_server_error() {
        store.abort(&cache_key).await;
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
        request_hash,
        in_progress: false,
    };
    store.complete(&cache_key, stored).await;

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
///
/// On stream errors the bytes collected so far are returned (callers log
/// and proceed); the request path must never fail because of body capture.
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
            request_hash: "hash-1".into(),
            in_progress: false,
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
            request_hash: "hash".into(),
            in_progress: false,
        };
        store.store("key-1".into(), response);
        assert_eq!(store.len(), 1);

        store.remove("key-1");
        assert!(store.is_empty());
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
            request_hash: "hash".into(),
            in_progress: false,
        };
        store.store("key-1".into(), response);

        // The TTL is 0, so the entry is already expired.
        tokio::time::sleep(Duration::from_millis(10)).await;

        let cached = store.get("key-1");
        assert!(cached.is_none());
    }

    #[tokio::test]
    async fn test_in_memory_claim_new_then_replay() {
        let store = IdempotencyStore::new(3600);
        let key = "k1";
        let hash = "body-hash";

        // First claim is New (nothing stored).
        assert!(matches!(store.claim(key, hash).await.unwrap(), Claim::New));

        // In-flight claim → InProgress.
        assert!(matches!(
            store.claim(key, hash).await.unwrap(),
            Claim::InProgress
        ));

        // Complete with a matching hash → Replay.
        store
            .complete(
                key,
                StoredResponse {
                    status_code: 200,
                    headers: vec![],
                    body: b"cached".to_vec(),
                    created_at: Instant::now(),
                    request_hash: hash.into(),
                    in_progress: false,
                },
            )
            .await;
        match store.claim(key, hash).await.unwrap() {
            Claim::Replay(cached) => assert_eq!(cached.body, b"cached".to_vec()),
            other => panic!("expected Replay, got {other:?}"),
        }

        // Different hash on the same key → reuse conflict.
        assert!(matches!(
            store.claim(key, "different-hash").await.unwrap(),
            Claim::ReuseConflict
        ));

        // Abort removes the record; a fresh claim is New again.
        store.abort(key).await;
        assert!(matches!(store.claim(key, hash).await.unwrap(), Claim::New));
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
    fn test_cache_key_is_scoped_to_tenant_user_method_and_path() {
        let k1 = compute_cache_key("tenant-a", "user-a", "POST", "/api/v1/tasks", "key-1");
        let k2 = compute_cache_key("tenant-b", "user-a", "POST", "/api/v1/tasks", "key-1");
        let k3 = compute_cache_key("tenant-a", "user-b", "POST", "/api/v1/tasks", "key-1");
        let k4 = compute_cache_key("tenant-a", "user-a", "PUT", "/api/v1/tasks", "key-1");
        let k5 = compute_cache_key("tenant-a", "user-a", "POST", "/api/v1/other", "key-1");
        let k6 = compute_cache_key("tenant-a", "user-a", "POST", "/api/v1/tasks", "key-2");
        let k7 = compute_cache_key("tenant-a", "user-a", "POST", "/api/v1/tasks", "key-1");

        assert_ne!(k1, k2, "same key must be scoped per tenant");
        assert_ne!(k1, k3, "same key must be scoped per user");
        assert_ne!(k1, k4, "same key must be scoped per method");
        assert_ne!(k1, k5, "same key must be scoped per path");
        assert_ne!(k1, k6, "different keys differ");
        assert_eq!(k1, k7, "deterministic");
    }

    #[test]
    fn test_normalize_path_strips_trailing_slashes() {
        assert_eq!(normalize_path("/api/v1/tasks"), "/api/v1/tasks");
        assert_eq!(normalize_path("/api/v1/tasks/"), "/api/v1/tasks");
        assert_eq!(normalize_path("/api/v1/tasks///"), "/api/v1/tasks");
        assert_eq!(normalize_path("/"), "/");
        assert_eq!(normalize_path("//"), "/");
    }

    #[test]
    fn test_hash_hex_is_stable_and_distinct() {
        assert_eq!(hash_hex(b"abc"), hash_hex(b"abc"));
        assert_ne!(hash_hex(b"abc"), hash_hex(b"abd"));
        assert_eq!(hash_hex(b"").len(), 64);
    }

    #[tokio::test]
    async fn test_collect_body_empty() {
        let body = axum::body::Body::empty();
        let result = collect_body(body).await;
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }
}

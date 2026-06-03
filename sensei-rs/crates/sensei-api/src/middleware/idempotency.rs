//! Idempotency middleware.
//!
//! Allows clients to safely retry POST, PUT, and PATCH requests by providing
//! an `Idempotency-Key` header.  When a request with a known key arrives,
//! the previously stored response is returned without re-executing the
//! handler.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
};
use dashmap::DashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, trace, warn};

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
/// Entries are automatically evicted after a configurable TTL.
#[derive(Clone)]
pub struct IdempotencyStore {
    responses: Arc<DashMap<String, StoredResponse>>,
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
            ttl: Duration::from_secs(ttl_secs),
        };

        // Spawn a background eviction task.
        let inner = Arc::clone(&store.responses);
        let ttl = store.ttl;
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(300));
            loop {
                interval.tick().await;
                let before = inner.len();
                inner.retain(|_, stored| stored.created_at.elapsed() < ttl);
                let removed = before - inner.len();
                if removed > 0 {
                    debug!(removed, remaining = inner.len(), "Idempotency-store cleanup");
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

    /// Return the number of cached responses.
    pub fn len(&self) -> usize {
        self.responses.len()
    }

    /// Return `true` if there are no cached responses.
    pub fn is_empty(&self) -> bool {
        self.responses.is_empty()
    }
}

/// Axum middleware that handles idempotency keys.
///
/// Reads the `Idempotency-Key` header from POST, PUT, and PATCH requests.
/// If a cached response exists for that key it is returned immediately.
/// Otherwise the request passes through and the response is cached for
/// future retries.
///
/// The [`IdempotencyStore`] must be injected into request extensions before
/// this middleware runs.
pub async fn idempotency_middleware(req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let is_idempotent_method = matches!(
        method.as_str(),
        "POST" | "PUT" | "PATCH"
    );

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

    // Check for a cached response.
    if let Some(cached) = store.get(&key) {
        trace!(key = %key, "Returning cached idempotent response");
        let mut response = Response::new(axum::body::Body::from(
            axum::body::Bytes::from(cached.body),
        ));
        *response.status_mut() = StatusCode::from_u16(cached.status_code)
            .unwrap_or(StatusCode::INTERNAL_SERVER_ERROR);
        for (name, value) in &cached.headers {
            if let (Ok(header_name), Ok(header_value)) = (
                axum::http::HeaderName::from_bytes(name.as_bytes()),
                axum::http::HeaderValue::from_str(value),
            ) {
                response.headers_mut().insert(header_name, header_value);
            }
        }
        return response;
    }

    // No cached response – run the handler and cache the result.
    let response = next.run(req).await;

    // Cache the response for future idempotent retries.
    let status = response.status();
    let (parts, body) = response.into_parts();

    // Collect the response body bytes.
    let body_bytes = match collect_body(body).await {
        Ok(bytes) => bytes,
        Err(e) => {
            warn!(error = %e, "Failed to read response body for idempotency caching");
            return (parts, axum::body::Body::empty()).into_response();
        }
    };

    // Collect response headers.
    let headers: Vec<(String, String)> = parts
        .headers
        .iter()
        .map(|(name, value)| {
            (
                name.to_string(),
                value.to_str().unwrap_or("").to_string(),
            )
        })
        .collect();

    let stored = StoredResponse {
        status_code: status.as_u16(),
        headers,
        body: body_bytes.clone(),
        created_at: Instant::now(),
    };
    store.store(key, stored);

    // Reconstruct the response.
    (parts, axum::body::Body::from(axum::body::Bytes::from(body_bytes))).into_response()
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
    use std::time::Duration;

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
        // But we allow a tiny bit of time to pass.
        tokio::time::sleep(Duration::from_millis(10)).await;

        // With TTL=0, the entry should be considered expired.
        // The `get` method checks `created_at.elapsed() >= self.ttl`.
        // Since ttl=0, and some time has passed, it should return None.
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
            assert_eq!(
                cached.unwrap().body,
                format!("body-{}", i).into_bytes()
            );
        }
    }

    #[test]
    fn test_collect_body_empty() {
        // This is a unit-style test for the collect_body helper.
        // Integration tests for the middleware would require a test server.
        let body = axum::body::Body::empty();
        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(collect_body(body));
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }
}

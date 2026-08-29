//! Generic HTTP API client wrapper.
//!
//! # Security model
//!
//! A single [`ApiClient`] is created per application and shared everywhere
//! (stored in [`crate::state::AppState`]). All clones share the same
//! connection pool, the in-memory bearer token, the refresh token, and the
//! single-flight refresh gate, so there is exactly one in-flight token
//! refresh at any time no matter how many concurrent requests hit a `401`.
//!
//! Tokens live **only in memory** (a `std::sync::RwLock` inside the client);
//! they are never persisted to `localStorage`/`sessionStorage`, eliminating
//! the XSS credential-exfiltration vector.

use crate::api::auth::RefreshResponse;
use serde::{de::DeserializeOwned, Serialize};
use serde_json::Value;
use std::fmt;
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Mutex, RwLock};
use std::task::{Context, Poll, Waker};
use std::time::Duration;

/// Connection timeout for the shared HTTP client. Ignored by the browser
/// `fetch` API on WASM, where the platform enforces its own limits.
const CONNECT_TIMEOUT_SECS: u64 = 10;
/// Overall request timeout for the shared HTTP client.
const REQUEST_TIMEOUT_SECS: u64 = 30;

/// Auth endpoints that must never trigger the automatic single-flight refresh:
/// a `401` from these means the presented credentials are invalid (or the
/// session is truly dead), not that the access token is stale.
const AUTO_REFRESH_SKIP_PATHS: [&str; 3] = [
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
];

/// Authentication token bundle held in reactive memory only.
#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct AuthTokens {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: u64,
}

/// Shared, cloneable HTTP client for the Sensei backend API.
///
/// Cloning is cheap and shares every mutable piece of state (bearer token,
/// refresh token, refresh gate, auth hooks), so any clone behaves as the
/// single application-wide client.
#[derive(Clone)]
pub struct ApiClient {
    base_url: std::sync::Arc<std::sync::RwLock<String>>,
    http: reqwest::Client,
    token: Arc<RwLock<Option<String>>>,
    refresh_token: Arc<RwLock<Option<String>>>,
    gate: Arc<RefreshGate>,
    hooks: Arc<AuthHooks>,
}

/// Hooks wired by [`crate::state::AppState`] to keep reactive state in sync
/// with the shared client.
/// Callback invoked after a successful token refresh.
type TokensRefreshedHook = Arc<dyn Fn(AuthTokens) + Send + Sync>;
/// Callback invoked when the session expires and cannot be refreshed.
type SessionExpiredHook = Arc<dyn Fn() + Send + Sync>;

#[derive(Default)]
struct AuthHooks {
    on_tokens_refreshed: Mutex<Option<TokensRefreshedHook>>,
    on_session_expired: Mutex<Option<SessionExpiredHook>>,
}

impl ApiClient {
    /// Create a new `ApiClient` pointing at the given base URL.
    ///
    /// The `reqwest::Client` inside is built once with explicit connect and
    /// request timeouts; no per-call construction happens anywhere.
    pub fn new(base_url: &str) -> Self {
        // The browser's fetch API ignores connect timeouts; reqwest's
        // wasm backend does not expose the builder methods.
        #[cfg(not(target_arch = "wasm32"))]
        let http = {
            reqwest::Client::builder()
                .connect_timeout(Duration::from_secs(CONNECT_TIMEOUT_SECS))
                .timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS))
                .build()
                .unwrap_or_default()
        };
        #[cfg(target_arch = "wasm32")]
        let http = reqwest::Client::builder().build().unwrap_or_default();
        Self {
            base_url: std::sync::Arc::new(std::sync::RwLock::new(
                base_url.trim_end_matches('/').to_string(),
            )),
            http,
            token: Arc::new(RwLock::new(None)),
            refresh_token: Arc::new(RwLock::new(None)),
            gate: Arc::new(RefreshGate::new()),
            hooks: Arc::new(AuthHooks::default()),
        }
    }

    /// Set the bearer token for subsequent requests (shared by all clones).
    pub fn set_token(&self, token: &str) {
        *self.token.write().unwrap() = Some(token.to_string());
    }

    /// Clear the current bearer token.
    pub fn clear_token(&self) {
        *self.token.write().unwrap() = None;
    }

    /// Return the current bearer token, if set.
    pub fn token(&self) -> Option<String> {
        self.token.read().unwrap().clone()
    }

    /// Set the refresh token used by the automatic `401` refresh path.
    pub fn set_refresh_token(&self, token: &str) {
        *self.refresh_token.write().unwrap() = Some(token.to_string());
    }

    /// Clear the stored refresh token.
    pub fn clear_refresh_token(&self) {
        *self.refresh_token.write().unwrap() = None;
    }

    /// Whether a refresh token is available for the automatic `401` path.
    pub fn has_refresh_token(&self) -> bool {
        self.refresh_token.read().unwrap().is_some()
    }

    /// Wire reactive hooks for token rotation and session expiry.
    ///
    /// The hooks are invoked after a successful refresh (with the rotated
    /// tokens) and after a failed refresh / invalid post-refresh `401` (so the
    /// UI can return to the login screen). Callbacks should capture signals,
    /// not `AppState`, to avoid reference cycles.
    pub fn set_auth_hooks(
        &self,
        on_tokens_refreshed: Option<Arc<dyn Fn(AuthTokens) + Send + Sync>>,
        on_session_expired: Option<Arc<dyn Fn() + Send + Sync>>,
    ) {
        *self.hooks.on_tokens_refreshed.lock().unwrap() = on_tokens_refreshed;
        *self.hooks.on_session_expired.lock().unwrap() = on_session_expired;
    }

    /// Build the full URL for a path relative to the API base.
    pub fn url(&self, path: &str) -> String {
        format!(
            "{}{}",
            self.base_url.read().unwrap_or_else(|p| p.into_inner()),
            path
        )
    }

    /// Reconfigure the API base URL at runtime (kept in sync with the
    /// reactive `api_base` signal).
    pub fn set_base_url(&self, base_url: &str) {
        if let Ok(mut guard) = self.base_url.write() {
            *guard = base_url.trim_end_matches('/').to_string();
        }
    }

    /// Perform a GET request.
    pub async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T, ApiError> {
        self.execute(reqwest::Method::GET, path, None).await
    }

    /// Perform a POST request with a JSON body.
    pub async fn post<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, ApiError> {
        let body = serde_json::to_value(body).map_err(|e| ApiError::json(e.to_string()))?;
        self.execute(reqwest::Method::POST, path, Some(body)).await
    }

    /// Perform a POST request with extra headers (e.g. the HttpOnly
    /// cookie-mode opt-in on login).
    pub async fn post_with_headers<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
        headers: &[(&str, &str)],
    ) -> Result<T, ApiError> {
        let body = serde_json::to_value(body).map_err(|e| ApiError::json(e.to_string()))?;
        let mut req = self.http.request(reqwest::Method::POST, self.url(path));
        if let Some(token) = self.token() {
            req = req.bearer_auth(token);
        }
        for (name, value) in headers {
            req = req.header(*name, *value);
        }
        req = req.json(&body);
        let resp = req
            .send()
            .await
            .map_err(|e| ApiError::http(e.to_string()))?;
        resp.json().await.map_err(|e| ApiError::json(e.to_string()))
    }

    /// Perform a PUT request with a JSON body.
    pub async fn put<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, ApiError> {
        let body = serde_json::to_value(body).map_err(|e| ApiError::json(e.to_string()))?;
        self.execute(reqwest::Method::PUT, path, Some(body)).await
    }

    /// POST with an Idempotency-Key (item 62): the offline replay can
    /// retry safely — a crash after the server committed cannot double
    /// create.
    pub async fn post_with_idempotency<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
        idempotency_key: &str,
    ) -> Result<T, ApiError> {
        let body = serde_json::to_value(body).map_err(|e| ApiError::json(e.to_string()))?;
        let mut req = self.http.request(reqwest::Method::POST, self.url(path));
        if let Some(token) = self.token() {
            req = req.bearer_auth(token);
        }
        req = req.header("Idempotency-Key", idempotency_key).json(&body);
        let resp = req
            .send()
            .await
            .map_err(|e| ApiError::http(e.to_string()))?;
        resp.json().await.map_err(|e| ApiError::json(e.to_string()))
    }

    /// PUT with an Idempotency-Key (item 62).
    pub async fn put_with_idempotency<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
        idempotency_key: &str,
    ) -> Result<T, ApiError> {
        let body = serde_json::to_value(body).map_err(|e| ApiError::json(e.to_string()))?;
        let mut req = self.http.request(reqwest::Method::PUT, self.url(path));
        if let Some(token) = self.token() {
            req = req.bearer_auth(token);
        }
        req = req.header("Idempotency-Key", idempotency_key).json(&body);
        let resp = req
            .send()
            .await
            .map_err(|e| ApiError::http(e.to_string()))?;
        resp.json().await.map_err(|e| ApiError::json(e.to_string()))
    }

    /// Perform a DELETE request.
    pub async fn delete<T: DeserializeOwned>(&self, path: &str) -> Result<T, ApiError> {
        self.execute(reqwest::Method::DELETE, path, None).await
    }

    /// Perform a GET request and return the raw response bytes (file
    /// downloads). Uses the same shared connection and auth pipeline.
    pub async fn get_bytes(&self, path: &str) -> Result<Vec<u8>, ApiError> {
        let resp = self.execute_raw(reqwest::Method::GET, path, None).await?;
        resp.bytes()
            .await
            .map(|b| b.to_vec())
            .map_err(|e| ApiError::json(format!("Failed to read response body: {e}")))
    }

    /// Refresh the access token, single-flight.
    ///
    /// Any number of concurrent callers collapse into exactly one network
    /// call; every caller receives the same rotated tokens (or the same
    /// error). Stored tokens are rotated on success and cleared on failure.
    pub async fn refresh_once(&self) -> Result<AuthTokens, ApiError> {
        if !self.gate.begin() {
            return self.gate.wait().await;
        }
        let result = self.do_refresh().await;
        self.gate.complete(result.clone());
        match &result {
            Ok(_) => {}
            Err(err) => {
                // A failed refresh invalidates the stored credentials; clear
                // them so subsequent requests fail fast instead of looping.
                self.clear_token();
                self.clear_refresh_token();
                if err.is_auth() {
                    self.notify_session_expired();
                }
            }
        }
        result
    }

    /// Restore a cookie-backed session: POST /auth/refresh with an empty
    /// body — the backend reads the HttpOnly refresh cookie. Used on app
    /// bootstrap after a reload (memory tokens are gone, the cookie is not).
    pub async fn refresh_from_cookie(&self) -> Result<AuthTokens, ApiError> {
        let resp = self
            .send(
                reqwest::Method::POST,
                "/api/v1/auth/refresh",
                Some(serde_json::json!({ "refresh_token": "" })),
            )
            .await?;
        if !resp.status().is_success() {
            return Err(ApiError::from_response(resp).await);
        }
        let body: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| ApiError::json(e.to_string()))?;
        // Cookie mode omits the refresh token from the body.
        let tokens = AuthTokens {
            access_token: body["access_token"]
                .as_str()
                .unwrap_or_default()
                .to_string(),
            refresh_token: body["refresh_token"]
                .as_str()
                .unwrap_or_default()
                .to_string(),
            token_type: body["token_type"].as_str().unwrap_or("Bearer").to_string(),
            expires_in: body["expires_in"].as_u64().unwrap_or(900),
        };
        if tokens.access_token.is_empty() {
            return Err(ApiError::auth("No access token in refresh response"));
        }
        *self.token.write().unwrap() = Some(tokens.access_token.clone());
        if !tokens.refresh_token.is_empty() {
            *self.refresh_token.write().unwrap() = Some(tokens.refresh_token.clone());
        }
        if let Some(cb) = self.hooks.on_tokens_refreshed.lock().unwrap().clone() {
            cb(tokens.clone());
        }
        Ok(tokens)
    }

    /// Perform the actual refresh request and rotate stored tokens.
    async fn do_refresh(&self) -> Result<AuthTokens, ApiError> {
        let refresh_tok = self
            .refresh_token
            .read()
            .unwrap()
            .clone()
            .ok_or_else(|| ApiError::auth("No refresh token available"))?;

        let request = RefreshRequest {
            refresh_token: refresh_tok,
        };
        // Direct send WITHOUT the auto-refresh loop: refreshing must never
        // recurse into itself (execute -> refresh_once -> do_refresh).
        let resp = self
            .send(
                reqwest::Method::POST,
                "/api/v1/auth/refresh",
                Some(serde_json::json!(request)),
            )
            .await?;
        if !resp.status().is_success() {
            return Err(ApiError::from_response(resp).await);
        }
        let resp: RefreshResponse = resp
            .json()
            .await
            .map_err(|e| ApiError::json(e.to_string()))?;

        let tokens = AuthTokens {
            access_token: resp.access_token.clone(),
            refresh_token: resp.refresh_token.clone(),
            token_type: resp.token_type.clone(),
            expires_in: resp.expires_in,
        };
        *self.token.write().unwrap() = Some(tokens.access_token.clone());
        *self.refresh_token.write().unwrap() = Some(tokens.refresh_token.clone());
        if let Some(cb) = self.hooks.on_tokens_refreshed.lock().unwrap().clone() {
            cb(tokens.clone());
        }
        Ok(tokens)
    }

    /// Execute a request, transparently handling `401` via the single-flight
    /// refresh path: the request is retried exactly once after a successful
    /// refresh.
    ///
    /// Item 3 (frontend/backend contract): the backend returns lists as
    /// `Json<PaginatedResponse<T>>` (`{"data": [...], "total": ...}`) while
    /// the frontend API modules declared `Result<Vec<T>, ApiError>`. The
    /// client now unwraps the envelope TRANSPARENTLY: when the response is a
    /// paginated envelope and the caller asks for a `Vec<T>`, only `.data`
    /// is deserialized. The type-system mismatch is eliminated at the
    /// boundary, not at every call site.
    async fn execute<T: DeserializeOwned>(
        &self,
        method: reqwest::Method,
        path: &str,
        body: Option<Value>,
    ) -> Result<T, ApiError> {
        let resp = self.execute_raw(method, path, body).await?;
        let bytes = resp
            .bytes()
            .await
            .map_err(|e| ApiError::http(e.to_string()))?;
        // First try the ENVELOPE for Vec targets: `{"data": [...], ...}`.
        // Deserialize the whole body as Value (cheap, local), detect the
        // pagination shape, and unwrap `.data`.
        if let Ok(value) = serde_json::from_slice::<Value>(&bytes) {
            if value.get("data").is_some() && value.get("total").is_some() {
                let data = value.get("data").cloned().unwrap_or(Value::Null);
                if let Ok(inner) = serde_json::from_value::<T>(data) {
                    return Ok(inner);
                }
            }
            // Non-envelope responses (single objects, plain arrays from
            // non-paginated endpoints) deserialize as-is.
            if let Ok(inner) = serde_json::from_value::<T>(value) {
                return Ok(inner);
            }
        }
        serde_json::from_slice(&bytes).map_err(|e| ApiError::json(e.to_string()))
    }

    /// Execute a request and return the raw response, retrying once after a
    /// successful single-flight refresh.
    async fn execute_raw(
        &self,
        method: reqwest::Method,
        path: &str,
        body: Option<Value>,
    ) -> Result<reqwest::Response, ApiError> {
        let mut attempts = 0u8;
        loop {
            let resp = self.send(method.clone(), path, body.clone()).await?;
            if resp.status() == reqwest::StatusCode::UNAUTHORIZED
                && attempts == 0
                && !is_auto_refresh_skipped(path)
                && self.has_refresh_token()
            {
                match self.refresh_once().await {
                    Ok(_) => {
                        attempts += 1;
                        continue;
                    }
                    Err(e) => return Err(e),
                }
            }
            if !resp.status().is_success() {
                let err = ApiError::from_response(resp).await;
                // A `401` after a successful refresh means the refreshed token
                // is still rejected — the session is genuinely dead.
                if err.is_auth() && attempts > 0 {
                    self.notify_session_expired();
                }
                return Err(err);
            }
            return Ok(resp);
        }
    }

    /// Build and send a single request with the current bearer token.
    async fn send(
        &self,
        method: reqwest::Method,
        path: &str,
        body: Option<Value>,
    ) -> Result<reqwest::Response, ApiError> {
        let mut req = self.http.request(method, self.url(path));
        if let Some(token) = self.token() {
            req = req.bearer_auth(token);
        }
        if let Some(body) = body {
            req = req.json(&body);
        }
        req.send().await.map_err(|e| ApiError::http(e.to_string()))
    }

    fn notify_session_expired(&self) {
        if let Some(cb) = self.hooks.on_session_expired.lock().unwrap().clone() {
            cb();
        }
    }
}

fn is_auto_refresh_skipped(path: &str) -> bool {
    AUTO_REFRESH_SKIP_PATHS.iter().any(|p| path.starts_with(p))
}

/// Body of the `POST /api/v1/auth/refresh` request.
#[derive(Debug, Serialize)]
struct RefreshRequest {
    refresh_token: String,
}

/// Classification of the failure that produced an [`ApiError`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, serde::Deserialize)]
pub enum ErrorKind {
    /// Transport-level failure (DNS, connection, timeout).
    Http,
    /// The server answered with a non-success status code.
    Status,
    /// The response body could not be deserialised.
    Json,
    /// Authentication failed (invalid credentials or failed refresh).
    Auth,
}

/// Structured API error.
///
/// Carries the HTTP status, the backend error code, a human-readable message,
/// and — when the backend supplies one — the `request_id` so failures can be
/// correlated with server logs and surfaced to the user.
#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct ApiError {
    pub kind: ErrorKind,
    pub status: Option<u16>,
    pub error_code: Option<String>,
    pub message: String,
    pub request_id: Option<String>,
}

impl ApiError {
    /// A transport-level error.
    pub fn http(message: impl Into<String>) -> Self {
        Self {
            kind: ErrorKind::Http,
            status: None,
            error_code: None,
            message: message.into(),
            request_id: None,
        }
    }

    /// A non-success status with no parseable body.
    pub fn status(status: u16) -> Self {
        Self {
            kind: ErrorKind::Status,
            status: Some(status),
            error_code: None,
            message: format!("HTTP status {status}"),
            request_id: None,
        }
    }

    /// A body deserialisation error.
    pub fn json(message: impl Into<String>) -> Self {
        Self {
            kind: ErrorKind::Json,
            status: None,
            error_code: None,
            message: message.into(),
            request_id: None,
        }
    }

    /// An authentication error.
    pub fn auth(message: impl Into<String>) -> Self {
        Self {
            kind: ErrorKind::Auth,
            status: None,
            error_code: None,
            message: message.into(),
            request_id: None,
        }
    }

    /// Whether this error represents an authentication failure.
    pub fn is_auth(&self) -> bool {
        self.kind == ErrorKind::Auth || self.status == Some(401)
    }

    /// Parse a non-success response into a structured error.
    ///
    /// The backend error envelope is either the legacy
    /// `{ "error": <code>, "message": <text>, "details": ... }` or the
    /// hardened `{ "error": <code>, "request_id": <id> }` shape.
    pub async fn from_response(resp: reqwest::Response) -> Self {
        let status = resp.status().as_u16();
        let body: Value = resp.json().await.unwrap_or(Value::Null);
        let (error_code, message, request_id) = extract_error_parts(&body, status);
        Self {
            kind: if status == 401 {
                ErrorKind::Auth
            } else {
                ErrorKind::Status
            },
            status: Some(status),
            error_code,
            message,
            request_id,
        }
    }

    /// A message suitable for display to an end user, including the
    /// `request_id` when the backend supplied one.
    pub fn user_message(&self) -> String {
        let mut msg = if self.message.is_empty() {
            match self.kind {
                ErrorKind::Http => "Network error — check your connection and retry.".to_string(),
                ErrorKind::Status => {
                    format!("Request failed with HTTP {}.", self.status.unwrap_or(0))
                }
                ErrorKind::Json => "Received an unexpected response from the server.".to_string(),
                ErrorKind::Auth => "Authentication failed.".to_string(),
            }
        } else {
            self.message.clone()
        };
        if let Some(rid) = &self.request_id {
            msg.push_str(&format!(" [Request ID: {rid}]"));
        }
        msg
    }
}

/// Extract `(error_code, message, request_id)` from an error body.
fn extract_error_parts(body: &Value, status: u16) -> (Option<String>, String, Option<String>) {
    let error_code = body
        .get("error")
        .and_then(Value::as_str)
        .map(str::to_string);
    let request_id = body
        .get("request_id")
        .and_then(Value::as_str)
        .map(str::to_string);
    let message = body
        .get("message")
        .or_else(|| body.get("detail"))
        .and_then(Value::as_str)
        .map(str::to_string)
        .or_else(|| error_code.clone())
        .unwrap_or_else(|| format!("Request failed (HTTP {status})"));
    (error_code, message, request_id)
}

impl fmt::Display for ApiError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.kind {
            ErrorKind::Http => write!(f, "Network error: {}", self.message),
            ErrorKind::Status => write!(f, "HTTP {}: {}", self.status.unwrap_or(0), self.message),
            ErrorKind::Json => write!(f, "Parse error: {}", self.message),
            ErrorKind::Auth => write!(f, "Auth error: {}", self.message),
        }
    }
}

impl std::error::Error for ApiError {}

// ---------------------------------------------------------------------------
// Single-flight refresh gate
// ---------------------------------------------------------------------------

/// Gate state shared by all clones of the client.
struct GateState {
    in_flight: bool,
    result: Option<Result<AuthTokens, ApiError>>,
    waiters: Vec<Waker>,
}

/// Single-flight gate: any number of concurrent callers collapse into exactly
/// one in-flight refresh, and every waiter receives the same result.
///
/// A completed result is retained until the next refresh begins, so callers
/// that arrive after completion reuse the fresh tokens instead of refreshing
/// again.
struct RefreshGate {
    inner: Mutex<GateState>,
}

impl RefreshGate {
    fn new() -> Self {
        Self {
            inner: Mutex::new(GateState {
                in_flight: false,
                result: None,
                waiters: Vec::new(),
            }),
        }
    }

    /// Claim leadership of the refresh.
    ///
    /// Returns `true` when this caller is the leader and must perform the
    /// refresh and call [`RefreshGate::complete`]; `false` when a refresh is
    /// in flight (or has just completed) and the caller should await
    /// [`RefreshGate::wait`] for the shared result instead.
    fn begin(&self) -> bool {
        let mut inner = self.inner.lock().unwrap();
        if inner.in_flight || inner.result.is_some() {
            false
        } else {
            inner.in_flight = true;
            true
        }
    }

    fn wait(&self) -> AwaitRefresh<'_> {
        AwaitRefresh { gate: self }
    }

    /// Complete the in-flight refresh and wake every waiter.
    fn complete(&self, result: Result<AuthTokens, ApiError>) {
        let waiters;
        {
            let mut inner = self.inner.lock().unwrap();
            inner.result = Some(result);
            inner.in_flight = false;
            waiters = std::mem::take(&mut inner.waiters);
        }
        for waker in waiters {
            waker.wake();
        }
    }
}

/// Future returned by [`RefreshGate::wait`]; resolves when the in-flight
/// refresh completes.
struct AwaitRefresh<'a> {
    gate: &'a RefreshGate,
}

impl Future for AwaitRefresh<'_> {
    type Output = Result<AuthTokens, ApiError>;

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        let mut inner = self.gate.inner.lock().unwrap();
        if let Some(result) = &inner.result {
            return Poll::Ready(result.clone());
        }
        if !inner.in_flight {
            // The leader never completed (aborted); surface an error instead
            // of blocking forever.
            return Poll::Ready(Err(ApiError::auth("Token refresh aborted")));
        }
        inner.waiters.push(cx.waker().clone());
        Poll::Pending
    }
}

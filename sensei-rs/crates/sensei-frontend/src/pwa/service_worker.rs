//! Service Worker registration and lifecycle management.
//!
//! Maps `navigator.serviceWorker.register()` from
//! [`frontend/src/services/service-worker.ts`](frontend/src/services/service-worker.ts)
//! to `web_sys::ServiceWorkerRegistration` methods.
//!
//! # Cache Strategies
//!
//! This module implements three cache strategies that can be used by the service
//! worker script:
//!
//! - **Cache First** — Return cached response if available, otherwise fetch from
//!   network and cache the result.
//! - **Network First** — Try network first, fall back to cache on failure.
//! - **Stale While Revalidate** — Return cached response immediately, then fetch
//!   from network to update the cache for next time.

use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::JsFuture;
use web_sys::{Cache, CacheStorage, ServiceWorkerRegistration};

// ── Constants ───────────────────────────────────────────────────────────────

/// Name of the cache storage used by the application service worker.
pub const CACHE_NAME: &str = "sensei-cache-v1";
/// Default service worker script URL relative to the app origin.
pub const SERVICE_WORKER_URL: &str = "/sw.js";
/// Scope for the service worker — the entire origin.
pub const SERVICE_WORKER_SCOPE: &str = "/";

// ── Error Type ──────────────────────────────────────────────────────────────

/// Errors that can occur during service worker registration.
#[derive(Debug, Clone)]
pub enum ServiceWorkerError {
    /// Service Workers are not supported in this browser.
    NotSupported,
    /// Registration failed.
    RegistrationFailed(String),
    /// Could not get the active registration.
    NoRegistration,
    /// Cache API not available.
    CacheNotAvailable,
    /// Cache operation failed.
    CacheOperationFailed(String),
}

impl std::fmt::Display for ServiceWorkerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotSupported => write!(f, "Service Workers are not supported in this browser"),
            Self::RegistrationFailed(msg) => write!(f, "Service worker registration failed: {msg}"),
            Self::NoRegistration => write!(f, "No active service worker registration"),
            Self::CacheNotAvailable => write!(f, "Cache API is not available"),
            Self::CacheOperationFailed(msg) => write!(f, "Cache operation failed: {msg}"),
        }
    }
}

impl std::error::Error for ServiceWorkerError {}

impl From<wasm_bindgen::JsValue> for ServiceWorkerError {
    fn from(value: wasm_bindgen::JsValue) -> Self {
        Self::RegistrationFailed(format!("{value:?}"))
    }
}

/// Specialised `Result` for service worker operations.
pub type Result<T> = std::result::Result<T, ServiceWorkerError>;

// ── Registration State ──────────────────────────────────────────────────────

/// Describes the current state of the service worker registration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegistrationState {
    /// Not yet registered.
    Unregistered,
    /// Registration is in progress.
    Registering,
    /// Successfully registered.
    Registered,
    /// Registration failed.
    Failed(String),
}

// ── Public API ──────────────────────────────────────────────────────────────

/// Check whether the browser supports Service Workers.
pub fn is_service_worker_supported() -> bool {
    web_sys::window()
        .map(|w| w.navigator().service_worker())
        .is_some()
}

/// Register the service worker at the given URL.
///
/// Returns a [`ServiceWorkerRegistration`] on success.
pub async fn register_service_worker() -> Result<ServiceWorkerRegistration> {
    let window = web_sys::window().ok_or(ServiceWorkerError::NotSupported)?;
    let navigator = window.navigator();
    let service_worker = navigator.service_worker();

    let registration = JsFuture::from(service_worker.register(SERVICE_WORKER_URL))
        .await
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("{e:?}")))?;

    registration
        .dyn_into::<ServiceWorkerRegistration>()
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("Cannot cast registration: {e:?}")))
}

/// Get the current service worker registration (waits for it to be ready).
pub async fn get_registration() -> Result<ServiceWorkerRegistration> {
    let window = web_sys::window().ok_or(ServiceWorkerError::NotSupported)?;
    let navigator = window.navigator();
    let service_worker = navigator.service_worker();

    let promise = service_worker
        .ready()
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("{e:?}")))?;

    let registration = JsFuture::from(promise)
        .await
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("{e:?}")))?;

    registration
        .dyn_into::<ServiceWorkerRegistration>()
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("Cannot cast registration: {e:?}")))
}

/// Unregister the service worker.
pub async fn unregister_service_worker() -> Result<bool> {
    let registration = get_registration().await?;
    let promise = registration
        .unregister()
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("{e:?}")))?;
    let result = JsFuture::from(promise)
        .await
        .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("{e:?}")))?;
    result.as_bool().ok_or(ServiceWorkerError::RegistrationFailed(
        "unregister returned non-boolean".into(),
    ))
}

/// Post a message to the active service worker.
pub fn post_message_to_service_worker(message: &JsValue) -> Result<()> {
    let window = web_sys::window().ok_or(ServiceWorkerError::NotSupported)?;
    let navigator = window.navigator();
    let service_worker = navigator.service_worker();

    // Get the active registration's service worker (via ready promise would be async,
    // so for synchronous access we try to get the controller)
    if let Some(controller) = service_worker.controller() {
        controller
            .post_message(message)
            .map_err(|e| ServiceWorkerError::RegistrationFailed(format!("postMessage failed: {e:?}")))?;
        Ok(())
    } else {
        Err(ServiceWorkerError::NoRegistration)
    }
}

// ── Cache Strategies ────────────────────────────────────────────────────────

/// Open a named cache.
pub async fn open_cache(name: &str) -> Result<Cache> {
    let window = web_sys::window().ok_or(ServiceWorkerError::NotSupported)?;
    let cache_storage: CacheStorage = window
        .caches()
        .map_err(|_| ServiceWorkerError::CacheNotAvailable)?;

    let result = JsFuture::from(cache_storage.open(name))
        .await
        .map_err(|e| ServiceWorkerError::CacheOperationFailed(format!("{e:?}")))?;

    result
        .dyn_into::<Cache>()
        .map_err(|e| ServiceWorkerError::CacheOperationFailed(format!("Cannot cast cache: {e:?}")))
}

/// Cache First strategy: return the cached response if available, otherwise
/// fetch from network and cache the result.
///
/// This is ideal for static assets that rarely change (CSS, JS, fonts, images).
pub async fn cache_first(request: &web_sys::Request) -> std::result::Result<web_sys::Response, JsValue> {
    let cache = open_cache(CACHE_NAME).await.map_err(|e| JsValue::from_str(&e.to_string()))?;

    // Try cache
    let cache_result = JsFuture::from(cache.match_with_request(request))
        .await
        .map_err(|e| JsValue::from_str(&format!("Cache match failed: {e:?}")))?;

    if !cache_result.is_null() && !cache_result.is_undefined() {
        let response: web_sys::Response = cache_result
            .dyn_into()
            .map_err(|_| JsValue::from_str("Expected Response from cache"))?;
        return Ok(response);
    }

    // Not in cache — fetch from network
    let response = web_sys::window()
        .ok_or(JsValue::from_str("No window"))?
        .fetch_with_request(request);

    let response_future = JsFuture::from(response).await?;
    let response: web_sys::Response = response_future
        .dyn_into()
        .map_err(|_| JsValue::from_str("Expected Response"))?;

    // Cache the fetched response (clone because response can only be consumed once)
    if response.ok() {
        let cloned = response
            .clone()
            .map_err(|_| JsValue::from_str("Cannot clone response"))?;
        let _ = cache.put_with_request(request, &cloned);
    }

    Ok(response)
}

/// Network First strategy: try the network first, fall back to cache on failure.
///
/// This is ideal for API responses where freshness is preferred but offline
/// access is still important.
pub async fn network_first(request: &web_sys::Request) -> std::result::Result<web_sys::Response, JsValue> {
    // Try network
    let fetch_promise = web_sys::window()
        .ok_or(JsValue::from_str("No window"))?
        .fetch_with_request(request);

    match JsFuture::from(fetch_promise).await {
        Ok(js_value) => {
            let response: web_sys::Response = js_value
                .dyn_into()
                .map_err(|_| JsValue::from_str("Expected Response"))?;

            // Cache the successful response
            if response.ok() {
                let cache = open_cache(CACHE_NAME).await;
                if let Ok(cache) = cache {
                    let cloned = response.clone().map_err(|_| JsValue::from_str("Cannot clone"))?;
                    let _ = cache.put_with_request(request, &cloned);
                }
            }

            Ok(response)
        }
        Err(_) => {
            // Network failed — fall back to cache
            let cache = open_cache(CACHE_NAME).await.map_err(|e| JsValue::from_str(&e.to_string()))?;
            let cache_result = JsFuture::from(cache.match_with_request(request))
                .await
                .map_err(|e| JsValue::from_str(&format!("Cache match failed: {e:?}")))?;

            if cache_result.is_null() || cache_result.is_undefined() {
                Err(JsValue::from_str("Network unavailable and no cached response"))
            } else {
                cache_result
                    .dyn_into()
                    .map_err(|_| JsValue::from_str("Expected Response from cache"))
            }
        }
    }
}

/// Stale While Revalidate strategy: return cached response immediately, then
/// fetch from network to update the cache for next time.
///
/// This is ideal for resources that update frequently but don't need to be
/// instantly fresh (e.g., user avatar, dashboard widgets).
pub async fn stale_while_revalidate(request: &web_sys::Request) -> std::result::Result<web_sys::Response, JsValue> {
    let cache = open_cache(CACHE_NAME).await.map_err(|e| JsValue::from_str(&e.to_string()))?;

    // Return cached response immediately (if available)
    let cached_result = JsFuture::from(cache.match_with_request(request))
        .await
        .map_err(|e| JsValue::from_str(&format!("Cache match failed: {e:?}")))?;

    let cached_response: Option<web_sys::Response> = if cached_result.is_null() || cached_result.is_undefined() {
        None
    } else {
        Some(cached_result.dyn_into().map_err(|_| JsValue::from_str("Expected Response"))?)
    };

    // Revalidate: fetch from network in background
    let request_clone = match request.clone() {
        Ok(r) => r,
        Err(_) => return Err(JsValue::from_str("Cannot clone request")),
    };
    let cache_clone = cache.clone();
    wasm_bindgen_futures::spawn_local(async move {
        if let Some(window) = web_sys::window() {
            let fetch_promise = window.fetch_with_request(&request_clone);
            if let Ok(js_value) = JsFuture::from(fetch_promise).await {
                if let Ok(response) = js_value.dyn_into::<web_sys::Response>() {
                    if response.ok() {
                        let _ = cache_clone.put_with_request(&request_clone, &response);
                    }
                }
            }
        }
    });

    if let Some(response) = cached_response {
        Ok(response)
    } else {
        // No cached response — fetch synchronously
        let fetch_promise = web_sys::window()
            .ok_or(JsValue::from_str("No window"))?
            .fetch_with_request(request);

        let js_value = JsFuture::from(fetch_promise).await?;
        js_value
            .dyn_into()
            .map_err(|_| JsValue::from_str("Expected Response"))
    }
}

// ── Lifecycle helpers ───────────────────────────────────────────────────────

/// Add a listener for the `install` event in the service worker global scope.
///
/// This should be called from within a service worker context (i.e. from `sw.rs`
/// or similar), not from the main thread.
///
/// Uses [`ExtendableEvent`] since `InstallEvent` is not a separate type in web-sys.
pub fn add_install_listener<F>(handler: F)
where
    F: FnMut(web_sys::ExtendableEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::ExtendableEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("install", cb.as_ref().unchecked_ref())
        .expect("addEventListener(install) failed");
    cb.forget();
}

/// Add a listener for the `activate` event in the service worker global scope.
///
/// Uses [`ExtendableEvent`] since `ActivateEvent` is not a separate type in web-sys.
pub fn add_activate_listener<F>(handler: F)
where
    F: FnMut(web_sys::ExtendableEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::ExtendableEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("activate", cb.as_ref().unchecked_ref())
        .expect("addEventListener(activate) failed");
    cb.forget();
}

/// Add a listener for the `fetch` event in the service worker global scope.
pub fn add_fetch_listener<F>(handler: F)
where
    F: FnMut(web_sys::FetchEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::FetchEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("fetch", cb.as_ref().unchecked_ref())
        .expect("addEventListener(fetch) failed");
    cb.forget();
}

/// Add a listener for the `message` event in the service worker global scope.
pub fn add_message_listener<F>(handler: F)
where
    F: FnMut(web_sys::ExtendableMessageEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::ExtendableMessageEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("message", cb.as_ref().unchecked_ref())
        .expect("addEventListener(message) failed");
    cb.forget();
}

/// Add a listener for the `push` event in the service worker global scope.
pub fn add_push_listener<F>(handler: F)
where
    F: FnMut(web_sys::PushEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::PushEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("push", cb.as_ref().unchecked_ref())
        .expect("addEventListener(push) failed");
    cb.forget();
}

/// Add a listener for the `sync` event in the service worker global scope.
///
/// Uses [`ExtendableEvent`] since `SyncEvent` is not a separate type in web-sys.
pub fn add_sync_listener<F>(handler: F)
where
    F: FnMut(web_sys::ExtendableEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::ExtendableEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("sync", cb.as_ref().unchecked_ref())
        .expect("addEventListener(sync) failed");
    cb.forget();
}

/// Add a listener for the `periodicsync` event in the service worker global scope.
///
/// Uses [`ExtendableEvent`] since `PeriodicSyncEvent` is not a separate type in web-sys.
pub fn add_periodic_sync_listener<F>(handler: F)
where
    F: FnMut(web_sys::ExtendableEvent) + 'static,
{
    let cb = Closure::<dyn FnMut(web_sys::ExtendableEvent)>::new(handler);
    let scope = js_sys::global()
        .dyn_into::<web_sys::ServiceWorkerGlobalScope>()
        .expect("Expected ServiceWorkerGlobalScope");

    scope
        .add_event_listener_with_callback("periodicsync", cb.as_ref().unchecked_ref())
        .expect("addEventListener(periodicsync) failed");
    cb.forget();
}

// ─── Online/offline detection ──────────────────────────────────────────────

/// Add a listener for the `online` event on the window.
pub fn add_online_listener<F>(handler: F)
where
    F: FnMut() + 'static,
{
    let cb = Closure::<dyn FnMut()>::new(handler);
    let window = web_sys::window().expect("Expected window");
    window
        .add_event_listener_with_callback("online", cb.as_ref().unchecked_ref())
        .expect("addEventListener(online) failed");
    cb.forget();
}

/// Add a listener for the `offline` event on the window.
pub fn add_offline_listener<F>(handler: F)
where
    F: FnMut() + 'static,
{
    let cb = Closure::<dyn FnMut()>::new(handler);
    let window = web_sys::window().expect("Expected window");
    window
        .add_event_listener_with_callback("offline", cb.as_ref().unchecked_ref())
        .expect("addEventListener(offline) failed");
    cb.forget();
}

/// Check whether the browser is currently online.
pub fn is_online() -> bool {
    web_sys::window()
        .map(|w| w.navigator().on_line())
        .unwrap_or(false)
}

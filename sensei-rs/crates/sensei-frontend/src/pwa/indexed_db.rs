//! IndexedDB storage layer for offline persistence.
//!
//! Maps TypeScript IndexedDB operations from [`frontend/src/services/sync-service.ts`](frontend/src/services/sync-service.ts)
//! to `web_sys::IdbDatabase` bindings with async wrappers via `wasm_bindgen_futures::JsFuture`.
//!
//! # Schema
//!
//! The sync store database (`sensei-sync-store`, version 1) uses object stores:
//!
//! | Store Name            | Key Path | Purpose                        |
//! |-----------------------|----------|--------------------------------|
//! | `pending-operations`  | `id`     | Queued offline operations      |
//! | `sync-meta`           | `key`    | Sync metadata (last sync time) |
//! | `cache`               | `url`    | Cached API responses           |

use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::JsFuture;
use web_sys::{
    DomException, IdbDatabase, IdbFactory, IdbObjectStore, IdbOpenDbRequest, IdbRequest,
    IdbTransaction, IdbTransactionMode, IdbVersionChangeEvent,
};

// ── Constants ───────────────────────────────────────────────────────────────

/// Name of the IndexedDB database used for offline sync storage.
const DB_NAME: &str = "sensei-sync-store";
/// Current schema version. Increment when making breaking changes to object stores.
const DB_VERSION: u32 = 1;

/// Names of object stores in the sync database.
pub struct StoreNames;
impl StoreNames {
    pub const PENDING_OPERATIONS: &'static str = "pending-operations";
    pub const SYNC_META: &'static str = "sync-meta";
    pub const CACHE: &'static str = "cache";
}

// ── Error Type ──────────────────────────────────────────────────────────────

/// Errors that can occur during IndexedDB operations.
#[derive(Debug, Clone)]
pub enum IndexedDbError {
    /// The browser does not support IndexedDB.
    NotSupported,
    /// Opening the database failed.
    OpenFailed(String),
    /// A transaction failed.
    TransactionFailed(String),
    /// A request returned an error.
    RequestFailed(String),
    /// The object store was not found.
    StoreNotFound(String),
    /// Serialization / deserialization failed.
    Serde(String),
    /// DomException wrapped.
    DomException(String),
}

impl std::fmt::Display for IndexedDbError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotSupported => write!(f, "IndexedDB is not supported in this browser"),
            Self::OpenFailed(msg) => write!(f, "IndexedDB open failed: {msg}"),
            Self::TransactionFailed(msg) => write!(f, "IndexedDB transaction failed: {msg}"),
            Self::RequestFailed(msg) => write!(f, "IndexedDB request failed: {msg}"),
            Self::StoreNotFound(name) => write!(f, "Object store not found: {name}"),
            Self::Serde(msg) => write!(f, "Serialization error: {msg}"),
            Self::DomException(msg) => write!(f, "DOM exception: {msg}"),
        }
    }
}

impl std::error::Error for IndexedDbError {}

impl From<wasm_bindgen::JsValue> for IndexedDbError {
    fn from(value: wasm_bindgen::JsValue) -> Self {
        if let Some(dom_ex) = value.dyn_ref::<DomException>() {
            Self::DomException(dom_ex.message())
        } else {
            Self::RequestFailed(format!("{value:?}"))
        }
    }
}

impl From<serde_json::Error> for IndexedDbError {
    fn from(e: serde_json::Error) -> Self {
        Self::Serde(e.to_string())
    }
}

/// Specialised `Result` for IndexedDB operations.
pub type Result<T> = std::result::Result<T, IndexedDbError>;

// ── Helpers ─────────────────────────────────────────────────────────────────

/// Convert an [`IdbRequest`] into a [`js_sys::Promise`] by wiring up its
/// `onsuccess` / `onerror` event handlers.
///
/// The returned Promise resolves with the request's `result` on success, or
/// rejects with the error value on failure.
fn idb_request_to_promise(request: &IdbRequest) -> js_sys::Promise {
    let req = request.clone();
    js_sys::Promise::new(&mut |resolve, reject| {
        // onsuccess handler
        let req_success = req.clone();
        let onsuccess = Closure::<dyn FnMut()>::new(move || {
            if let Ok(result) = req_success.result() {
                resolve.call1(&JsValue::null(), &result).ok();
            }
        });
        req.set_onsuccess(Some(onsuccess.as_ref().unchecked_ref()));
        onsuccess.forget();

        // onerror handler
        let req_error = req.clone();
        let onerror = Closure::<dyn FnMut()>::new(move || {
            let err_val: JsValue = match req_error.error() {
                Ok(Some(dom_ex)) => dom_ex.into(),
                Ok(None) => JsValue::from_str("request error"),
                Err(js_val) => js_val,
            };
            reject.call1(&JsValue::null(), &err_val).ok();
        });
        req.set_onerror(Some(onerror.as_ref().unchecked_ref()));
        onerror.forget();
    })
}

// ── Database Handle ─────────────────────────────────────────────────────────

/// A handle to an opened IndexedDB database with its store names known.
///
/// Drop this to close the underlying connection. All operations are
/// asynchronous using `wasm_bindgen_futures::JsFuture`.
#[derive(Clone)]
pub struct IndexedDb {
    db: IdbDatabase,
}

impl IndexedDb {
    /// Open (or create / upgrade) the sync database.
    ///
    /// This runs the schema migration callback which creates the required
    /// object stores if they don't exist.
    pub async fn open() -> Result<Self> {
        let factory = Self::factory()?;
        let open_request: IdbOpenDbRequest = factory
            .open_with_f64(DB_NAME, DB_VERSION.into())
            .map_err(|e| IndexedDbError::OpenFailed(format!("{e:?}")))?;

        // Handle onupgradeneeded — create object stores
        let open_req_clone = open_request.clone();
        let cb = Closure::<dyn FnMut(IdbVersionChangeEvent)>::new(
            move |_event: IdbVersionChangeEvent| {
                if let Ok(val) = open_req_clone.result() {
                    if let Ok(db) = val.dyn_into::<IdbDatabase>() {
                        Self::run_migrations(&db);
                    }
                }
            },
        );
        open_request.set_onupgradeneeded(Some(cb.as_ref().unchecked_ref()));
        cb.forget(); // Leak intentionally - lives for the lifetime of the open request

        // Wait for the open request to complete
        let _ = JsFuture::from(idb_request_to_promise(&open_request))
            .await
            .map_err(|e| IndexedDbError::OpenFailed(format!("{e:?}")))?;

        // Extract the IdbDatabase from the completed request
        let db: IdbDatabase = open_request
            .result()
            .map_err(|e| IndexedDbError::OpenFailed(format!("Cannot get result: {e:?}")))?
            .dyn_into::<IdbDatabase>()
            .map_err(|e| IndexedDbError::OpenFailed(format!("Cannot get database: {e:?}")))?;

        Ok(Self { db })
    }

    /// Get the [`IdbFactory`] from the global `window.indexedDB`.
    fn factory() -> Result<IdbFactory> {
        let window = web_sys::window().ok_or(IndexedDbError::NotSupported)?;
        let factory = window
            .indexed_db()
            .map_err(|_| IndexedDbError::NotSupported)?
            .ok_or(IndexedDbError::NotSupported)?;
        Ok(factory)
    }

    /// Create all required object stores during schema upgrade.
    ///
    /// In IndexedDB, `create_object_store` throws a `ConstraintError` if the
    /// store already exists. We simply ignore that case because it means the
    /// migration has already been applied.
    fn run_migrations(db: &IdbDatabase) {
        // pending-operations — no key-path params needed (uses default key generator)
        let _ = db.create_object_store(StoreNames::PENDING_OPERATIONS);

        // sync-meta — keyPath is "key"
        let params = web_sys::IdbObjectStoreParameters::new();
        params.set_key_path(&JsValue::from_str("key"));
        let _ = db.create_object_store_with_optional_parameters(StoreNames::SYNC_META, &params);

        // cache — keyPath is "url"
        let params = web_sys::IdbObjectStoreParameters::new();
        params.set_key_path(&JsValue::from_str("url"));
        let _ = db.create_object_store_with_optional_parameters(StoreNames::CACHE, &params);
    }

    /// Start a readwrite transaction and get a store reference.
    fn transaction_store(
        &self,
        store_name: &str,
        mode: IdbTransactionMode,
    ) -> Result<(IdbTransaction, IdbObjectStore)> {
        let transaction = self
            .db
            .transaction_with_str_and_mode(store_name, mode)
            .map_err(|e| IndexedDbError::TransactionFailed(format!("{e:?}")))?;

        let store = transaction
            .object_store(store_name)
            .map_err(|_| IndexedDbError::StoreNotFound(store_name.to_string()))?;

        Ok((transaction, store))
    }

    /// Await an [`IdbRequest`] and return the result.
    async fn await_request(&self, request: &IdbRequest) -> Result<JsValue> {
        let promise = idb_request_to_promise(request);
        JsFuture::from(promise)
            .await
            .map_err(|e| IndexedDbError::RequestFailed(format!("{e:?}")))
    }

    /// Await transaction completion.
    async fn await_transaction(&self, transaction: &IdbTransaction) -> Result<()> {
        let tx = transaction.clone();
        let promise = js_sys::Promise::new(&mut |resolve, reject| {
            let oncomplete = Closure::<dyn FnMut()>::new(move || {
                resolve.call0(&JsValue::null()).ok();
            });
            tx.set_oncomplete(Some(oncomplete.as_ref().unchecked_ref()));
            oncomplete.forget();

            let onerror_tx = tx.clone();
            let onerror = Closure::<dyn FnMut()>::new(move || {
                let err_val: JsValue = match onerror_tx.error() {
                    Some(dom_ex) => dom_ex.into(),
                    None => JsValue::from_str("transaction error"),
                };
                reject.call1(&JsValue::null(), &err_val).ok();
            });
            tx.set_onerror(Some(onerror.as_ref().unchecked_ref()));
            onerror.forget();
        });
        JsFuture::from(promise)
            .await
            .map_err(|e| IndexedDbError::TransactionFailed(format!("{e:?}")))?;
        Ok(())
    }

    /// Perform a `get_all` operation and return the results as a `Vec<JsValue>`.
    fn request_get_all(&self, store: &IdbObjectStore) -> Result<IdbRequest> {
        store
            .get_all()
            .map_err(|e| IndexedDbError::RequestFailed(format!("get_all failed: {e:?}")))
    }

    /// Perform a `get` operation.
    fn request_get(&self, store: &IdbObjectStore, key: &JsValue) -> Result<IdbRequest> {
        store
            .get(key)
            .map_err(|e| IndexedDbError::RequestFailed(format!("get failed: {e:?}")))
    }

    /// Perform a `put` operation.
    fn request_put(&self, store: &IdbObjectStore, value: &JsValue) -> Result<IdbRequest> {
        store
            .put(value)
            .map_err(|e| IndexedDbError::RequestFailed(format!("put failed: {e:?}")))
    }

    /// Perform a `put` with key operation.
    fn request_put_with_key(
        &self,
        store: &IdbObjectStore,
        value: &JsValue,
        key: &JsValue,
    ) -> Result<IdbRequest> {
        store
            .put_with_key(value, key)
            .map_err(|e| IndexedDbError::RequestFailed(format!("put_with_key failed: {e:?}")))
    }

    /// Perform a `delete` operation.
    fn request_delete(&self, store: &IdbObjectStore, key: &JsValue) -> Result<IdbRequest> {
        store
            .delete(key)
            .map_err(|e| IndexedDbError::RequestFailed(format!("delete failed: {e:?}")))
    }

    /// Perform a `clear` operation.
    fn request_clear(&self, store: &IdbObjectStore) -> Result<IdbRequest> {
        store
            .clear()
            .map_err(|e| IndexedDbError::RequestFailed(format!("clear failed: {e:?}")))
    }

    /// Perform a `count` operation.
    fn request_count(&self, store: &IdbObjectStore) -> Result<IdbRequest> {
        store
            .count()
            .map_err(|e| IndexedDbError::RequestFailed(format!("count failed: {e:?}")))
    }

    // ── Pending Operations CRUD ─────────────────────────────────────────────

    /// Store a pending operation (insert or update by ID).
    pub async fn put_pending_operation(&self, value: &JsValue) -> Result<()> {
        let (tx, store) = self.transaction_store(
            StoreNames::PENDING_OPERATIONS,
            IdbTransactionMode::Readwrite,
        )?;
        let request = self.request_put(&store, value)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Store a pending operation with an explicit key.
    pub async fn put_pending_operation_with_key(
        &self,
        value: &JsValue,
        key: &JsValue,
    ) -> Result<()> {
        let (tx, store) = self.transaction_store(
            StoreNames::PENDING_OPERATIONS,
            IdbTransactionMode::Readwrite,
        )?;
        let request = self.request_put_with_key(&store, value, key)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Get a pending operation by its ID.
    pub async fn get_pending_operation(&self, id: &JsValue) -> Result<Option<JsValue>> {
        let (tx, store) =
            self.transaction_store(StoreNames::PENDING_OPERATIONS, IdbTransactionMode::Readonly)?;
        let request = self.request_get(&store, id)?;
        let result = self.await_request(&request).await?;
        self.await_transaction(&tx).await?;
        if result.is_null() || result.is_undefined() {
            Ok(None)
        } else {
            Ok(Some(result))
        }
    }

    /// Get all pending operations.
    pub async fn get_all_pending_operations(&self) -> Result<Vec<JsValue>> {
        let (tx, store) =
            self.transaction_store(StoreNames::PENDING_OPERATIONS, IdbTransactionMode::Readonly)?;
        let request = self.request_get_all(&store)?;
        let result = self.await_request(&request).await?;
        self.await_transaction(&tx).await?;
        Ok(js_sys_array_to_vec(result))
    }

    /// Delete a pending operation by ID.
    pub async fn delete_pending_operation(&self, id: &JsValue) -> Result<()> {
        let (tx, store) = self.transaction_store(
            StoreNames::PENDING_OPERATIONS,
            IdbTransactionMode::Readwrite,
        )?;
        let request = self.request_delete(&store, id)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Clear all pending operations.
    pub async fn clear_pending_operations(&self) -> Result<()> {
        let (tx, store) = self.transaction_store(
            StoreNames::PENDING_OPERATIONS,
            IdbTransactionMode::Readwrite,
        )?;
        let request = self.request_clear(&store)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Count pending operations.
    pub async fn count_pending_operations(&self) -> Result<u32> {
        let (tx, store) =
            self.transaction_store(StoreNames::PENDING_OPERATIONS, IdbTransactionMode::Readonly)?;
        let request = self.request_count(&store)?;
        let result = self.await_request(&request).await?;
        self.await_transaction(&tx).await?;
        result
            .as_f64()
            .map(|n| n as u32)
            .ok_or(IndexedDbError::RequestFailed(
                "count returned non-number".into(),
            ))
    }

    // ── Sync Meta CRUD ──────────────────────────────────────────────────────

    /// Store a sync metadata key-value pair.
    ///
    /// The value is stored as an object `{ key: string, value: any }` so it
    /// matches the `key` key-path of the `sync-meta` object store.
    pub async fn put_sync_meta(&self, key: &str, value: &JsValue) -> Result<()> {
        let entry = js_sys::Object::new();
        js_sys::Reflect::set(&entry, &JsValue::from_str("key"), &JsValue::from_str(key))
            .map_err(|_| IndexedDbError::RequestFailed("Cannot set key".into()))?;
        js_sys::Reflect::set(&entry, &JsValue::from_str("value"), value)
            .map_err(|_| IndexedDbError::RequestFailed("Cannot set value".into()))?;

        let (tx, store) =
            self.transaction_store(StoreNames::SYNC_META, IdbTransactionMode::Readwrite)?;
        let request = self.request_put(&store, &entry)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Get a sync metadata value by key.
    pub async fn get_sync_meta(&self, key: &str) -> Result<Option<JsValue>> {
        let (tx, store) =
            self.transaction_store(StoreNames::SYNC_META, IdbTransactionMode::Readonly)?;
        let request = self.request_get(&store, &JsValue::from_str(key))?;
        let result = self.await_request(&request).await?;
        self.await_transaction(&tx).await?;
        if result.is_null() || result.is_undefined() {
            Ok(None)
        } else {
            // The result is the full object { key, value } — extract the "value" field
            let val = js_sys::Reflect::get(&result, &JsValue::from_str("value")).ok();
            Ok(val)
        }
    }

    // ── Cache CRUD ──────────────────────────────────────────────────────────

    /// Store a cached API response.
    pub async fn put_cache_entry(&self, url: &str, data: &JsValue) -> Result<()> {
        let entry = js_sys::Object::new();
        js_sys::Reflect::set(&entry, &JsValue::from_str("url"), &JsValue::from_str(url))
            .map_err(|_| IndexedDbError::RequestFailed("Cannot set url".into()))?;
        js_sys::Reflect::set(&entry, &JsValue::from_str("data"), data)
            .map_err(|_| IndexedDbError::RequestFailed("Cannot set data".into()))?;
        js_sys::Reflect::set(
            &entry,
            &JsValue::from_str("cached_at"),
            &JsValue::from_f64(js_sys::Date::now()),
        )
        .map_err(|_| IndexedDbError::RequestFailed("Cannot set cached_at".into()))?;

        let (tx, store) =
            self.transaction_store(StoreNames::CACHE, IdbTransactionMode::Readwrite)?;
        let request = self.request_put(&store, &entry)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Get a cached API response by URL.
    pub async fn get_cache_entry(&self, url: &str) -> Result<Option<JsValue>> {
        let (tx, store) =
            self.transaction_store(StoreNames::CACHE, IdbTransactionMode::Readonly)?;
        let request = self.request_get(&store, &JsValue::from_str(url))?;
        let result = self.await_request(&request).await?;
        self.await_transaction(&tx).await?;
        if result.is_null() || result.is_undefined() {
            Ok(None)
        } else {
            let data = js_sys::Reflect::get(&result, &JsValue::from_str("data")).ok();
            Ok(data)
        }
    }

    /// Delete a cache entry by URL.
    pub async fn delete_cache_entry(&self, url: &str) -> Result<()> {
        let (tx, store) =
            self.transaction_store(StoreNames::CACHE, IdbTransactionMode::Readwrite)?;
        let request = self.request_delete(&store, &JsValue::from_str(url))?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }

    /// Clear all cache entries.
    pub async fn clear_cache(&self) -> Result<()> {
        let (tx, store) =
            self.transaction_store(StoreNames::CACHE, IdbTransactionMode::Readwrite)?;
        let request = self.request_clear(&store)?;
        self.await_request(&request).await?;
        self.await_transaction(&tx).await
    }
}

impl Drop for IndexedDb {
    fn drop(&mut self) {
        self.db.close();
    }
}

// ── Utilities ───────────────────────────────────────────────────────────────

/// Convert a [`JsValue`] that is a [`js_sys::Array`] into a `Vec<JsValue>`.
fn js_sys_array_to_vec(value: JsValue) -> Vec<JsValue> {
    let array: js_sys::Array = value.into();
    let mut items = Vec::with_capacity(array.length() as usize);
    for i in 0..array.length() {
        items.push(array.get(i));
    }
    items
}

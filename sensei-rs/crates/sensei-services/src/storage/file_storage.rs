//! File storage service trait and implementations.
//!
//! Defines the [`FileStorageService`] trait that provides a uniform interface
//! for storing, retrieving, and deleting file content. Three backends are provided:
//!
//! * [`LocalStorageService`] — async filesystem I/O via `tokio::fs`
//! * [`S3StorageService`] — S3/MinIO via the `rust-s3` crate
//! * [`InMemoryStorageService`] — concurrent `HashMap` for development/testing

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::EntityId;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;

// ── Trait ──────────────────────────────────────────────────────────────────────

/// Unified file storage interface backed by local disk, S3, or in-memory storage.
///
/// Every method is async and returns [`sensei_core::error::Result`] so that callers
/// can use `?` uniformly regardless of the backend.
#[async_trait]
pub trait FileStorageService: Send + Sync {
    /// Store a blob at the given logical path under a tenant's namespace.
    ///
    /// Returns the storage path that can later be passed to [`retrieve`] or [`delete`].
    async fn store(
        &self,
        tenant_id: EntityId,
        path: &str,
        data: &[u8],
        content_type: &str,
    ) -> Result<String>;

    /// Retrieve the raw bytes previously stored at `storage_path`.
    async fn retrieve(&self, tenant_id: EntityId, storage_path: &str) -> Result<Vec<u8>>;

    /// Delete the blob at `storage_path`.
    async fn delete(&self, tenant_id: EntityId, storage_path: &str) -> Result<()>;

    /// Return a time-limited presigned GET URL, if the backend supports it.
    ///
    /// Local and in-memory backends return `Ok(None)`.
    async fn get_presigned_url(
        &self,
        tenant_id: EntityId,
        storage_path: &str,
        expires_in_secs: u64,
    ) -> Result<Option<String>>;

    /// Clone the trait object into a new `Box`.
    fn clone_box(&self) -> Box<dyn FileStorageService>;
}

// Allow cloning a `Box<dyn FileStorageService>` via `clone_box`.
impl Clone for Box<dyn FileStorageService> {
    fn clone(&self) -> Self {
        self.clone_box()
    }
}

// ── Local filesystem backend ───────────────────────────────────────────────────

/// Stores files on the local filesystem under a configurable base directory.
///
/// Files are written to `{base_path}/{tenant_id}/{relative_path}`.  The relative
/// path is returned as the storage path so it can be reconstructed later.
///
/// ## Concurrency
///
/// Directory creation is handled by [`tokio::fs::create_dir_all`], which is safe
/// to call concurrently from multiple tasks.
#[derive(Clone, Debug)]
pub struct LocalStorageService {
    /// Base directory for all uploaded files (e.g. `./data/uploads`).
    base_path: PathBuf,
}

impl LocalStorageService {
    /// Create a new local storage service rooted at `base_path`.
    ///
    /// The directory is **not** created eagerly; it will be created on the first
    /// call to [`store`](FileStorageService::store).
    pub fn new(base_path: impl Into<PathBuf>) -> Self {
        Self {
            base_path: base_path.into(),
        }
    }

    /// Resolve the absolute filesystem path for a tenant+relative storage path.
    fn resolve_path(&self, tenant_id: EntityId, storage_path: &str) -> PathBuf {
        self.base_path
            .join(tenant_id.to_string())
            .join(storage_path)
    }
}

#[async_trait]
impl FileStorageService for LocalStorageService {
    async fn store(
        &self,
        tenant_id: EntityId,
        path: &str,
        data: &[u8],
        _content_type: &str,
    ) -> Result<String> {
        let full_path = self.resolve_path(tenant_id, path);

        // Create parent directories atomically (safe under concurrent calls).
        if let Some(parent) = full_path.parent() {
            tokio::fs::create_dir_all(parent)
                .await
                .map_err(|e| SenseiError::Io(e))?;
        }

        tokio::fs::write(&full_path, data)
            .await
            .map_err(|e| SenseiError::Io(e))?;

        // Return the relative path as the storage key.
        Ok(path.to_string())
    }

    async fn retrieve(&self, tenant_id: EntityId, storage_path: &str) -> Result<Vec<u8>> {
        let full_path = self.resolve_path(tenant_id, storage_path);
        tokio::fs::read(&full_path)
            .await
            .map_err(|e| {
                if e.kind() == std::io::ErrorKind::NotFound {
                    SenseiError::NotFound(format!(
                        "File not found at storage path: {storage_path}"
                    ))
                } else {
                    SenseiError::Io(e)
                }
            })
    }

    async fn delete(&self, tenant_id: EntityId, storage_path: &str) -> Result<()> {
        let full_path = self.resolve_path(tenant_id, storage_path);
        tokio::fs::remove_file(&full_path)
            .await
            .map_err(|e| {
                if e.kind() == std::io::ErrorKind::NotFound {
                    SenseiError::NotFound(format!(
                        "File not found at storage path: {storage_path}"
                    ))
                } else {
                    SenseiError::Io(e)
                }
            })
    }

    async fn get_presigned_url(
        &self,
        _tenant_id: EntityId,
        _storage_path: &str,
        _expires_in_secs: u64,
    ) -> Result<Option<String>> {
        // Presigned URLs are not supported for local filesystem storage.
        Ok(None)
    }

    fn clone_box(&self) -> Box<dyn FileStorageService> {
        Box::new(self.clone())
    }
}

// ── In-memory backend (dev/test) ───────────────────────────────────────────────

/// Stores files in a concurrent in-memory `HashMap` keyed by the storage path.
///
/// The key is a combination of `{tenant_id}/{storage_path}` to keep tenant data
/// isolated.  This backend is intended for development and testing only.
#[derive(Clone, Debug)]
pub struct InMemoryStorageService {
    /// Key: `"{tenant_id}/{storage_path}"`, Value: raw blob.
    data: Arc<RwLock<HashMap<String, Vec<u8>>>>,
}

impl InMemoryStorageService {
    /// Create a new empty in-memory store.
    pub fn new() -> Self {
        Self {
            data: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Build the internal key from a tenant ID and storage path.
    fn key(tenant_id: EntityId, storage_path: &str) -> String {
        format!("{}/{}", tenant_id, storage_path)
    }
}

impl Default for InMemoryStorageService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl FileStorageService for InMemoryStorageService {
    async fn store(
        &self,
        tenant_id: EntityId,
        path: &str,
        data: &[u8],
        _content_type: &str,
    ) -> Result<String> {
        let key = Self::key(tenant_id, path);
        let mut map = self.data.write().await;
        map.insert(key, data.to_vec());
        Ok(path.to_string())
    }

    async fn retrieve(&self, tenant_id: EntityId, storage_path: &str) -> Result<Vec<u8>> {
        let key = Self::key(tenant_id, storage_path);
        let map = self.data.read().await;
        map.get(&key)
            .cloned()
            .ok_or_else(|| {
                SenseiError::NotFound(format!(
                    "File not found at storage path: {storage_path}"
                ))
            })
    }

    async fn delete(&self, tenant_id: EntityId, storage_path: &str) -> Result<()> {
        let key = Self::key(tenant_id, storage_path);
        let mut map = self.data.write().await;
        map.remove(&key).ok_or_else(|| {
            SenseiError::NotFound(format!(
                "File not found at storage path: {storage_path}"
            ))
        })?;
        Ok(())
    }

    async fn get_presigned_url(
        &self,
        _tenant_id: EntityId,
        _storage_path: &str,
        _expires_in_secs: u64,
    ) -> Result<Option<String>> {
        // Presigned URLs are not supported for in-memory storage.
        Ok(None)
    }

    fn clone_box(&self) -> Box<dyn FileStorageService> {
        Box::new(self.clone())
    }
}

// ── S3 / MinIO backend ─────────────────────────────────────────────────────────

/// Stores files in an S3-compatible object store such as AWS S3 or MinIO.
///
/// Supports configurable bucket, region, optional custom endpoint (for MinIO),
/// and presigned GET URLs for direct browser downloads.
pub struct S3StorageService {
    bucket: Arc<s3::Bucket>,
}

impl S3StorageService {
    /// Create a new S3 storage client from raw configuration values.
    ///
    /// # Errors
    ///
    /// Returns [`SenseiError::Configuration`] if the credentials, region, or
    /// bucket configuration are invalid.
    pub fn new(
        bucket_name: &str,
        region: &str,
        endpoint: Option<&str>,
        access_key: &str,
        secret_key: &str,
    ) -> Result<Self> {
        let region: s3::Region = match endpoint {
            Some(ep) if !ep.is_empty() => s3::Region::Custom {
                region: region.to_string(),
                endpoint: ep.to_string(),
            },
            _ => region
                .parse()
                .map_err(|e| SenseiError::Configuration(format!("Invalid S3 region '{region}': {e}")))?,
        };

        let credentials = s3::creds::Credentials::new(
            Some(access_key),
            Some(secret_key),
            None, // token
            None, // session token
            None, // profile
        )
        .map_err(|e| SenseiError::Configuration(format!("Invalid S3 credentials: {e}")))?;

        let bucket = s3::Bucket::new(bucket_name, region, credentials)
            .map_err(|e| SenseiError::Configuration(format!("Failed to create S3 bucket: {e}")))?;

        Ok(Self {
            bucket: Arc::new(*bucket),
        })
    }

    /// Internal: prefix the storage path with the tenant ID for isolation.
    fn tenant_path(tenant_id: EntityId, storage_path: &str) -> String {
        format!("{}/{}", tenant_id, storage_path)
    }
}

/// Map a rust-s3 error onto a [`SenseiError`].
///
/// 404 responses (which S3 reports as `NoSuchKey`) are mapped to
/// [`SenseiError::NotFound`] based on the HTTP status code rather than by
/// string-matching the error message.
fn map_s3_error(context: &str, e: &s3::error::S3Error, storage_path: &str) -> SenseiError {
    match e {
        s3::error::S3Error::HttpFailWithBody(404, _) => {
            SenseiError::NotFound(format!("File not found at storage path: {storage_path}"))
        }
        _ => SenseiError::ExternalService(format!("{context}: {e}")),
    }
}

impl std::fmt::Debug for S3StorageService {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("S3StorageService")
            .field("bucket", &self.bucket.name)
            .finish()
    }
}

impl Clone for S3StorageService {
    fn clone(&self) -> Self {
        Self {
            bucket: Arc::clone(&self.bucket),
        }
    }
}

#[async_trait]
impl FileStorageService for S3StorageService {
    async fn store(
        &self,
        tenant_id: EntityId,
        path: &str,
        data: &[u8],
        content_type: &str,
    ) -> Result<String> {
        let s3_path = Self::tenant_path(tenant_id, path);

        let content_type = if content_type.is_empty() {
            "application/octet-stream"
        } else {
            content_type
        };

        self.bucket
            .put_object_with_content_type(&s3_path, data, content_type)
            .await
            .map_err(|e| SenseiError::ExternalService(format!("S3 upload failed: {e}")))?;

        Ok(path.to_string())
    }

    async fn retrieve(&self, tenant_id: EntityId, storage_path: &str) -> Result<Vec<u8>> {
        let s3_path = Self::tenant_path(tenant_id, storage_path);

        let response = self
            .bucket
            .get_object(&s3_path)
            .await
            .map_err(|e| map_s3_error("S3 download failed", &e, storage_path))?;

        Ok(response.bytes().to_vec())
    }

    async fn delete(&self, tenant_id: EntityId, storage_path: &str) -> Result<()> {
        let s3_path = Self::tenant_path(tenant_id, storage_path);

        self.bucket
            .delete_object(&s3_path)
            .await
            .map_err(|e| map_s3_error("S3 delete failed", &e, storage_path))?;

        Ok(())
    }

    async fn get_presigned_url(
        &self,
        tenant_id: EntityId,
        storage_path: &str,
        expires_in_secs: u64,
    ) -> Result<Option<String>> {
        let s3_path = Self::tenant_path(tenant_id, storage_path);

        let url = self
            .bucket
            .presign_get(&s3_path, expires_in_secs as u32, None)
            .await
            .map_err(|e| SenseiError::ExternalService(format!("S3 presign failed: {e}")))?;

        Ok(Some(url))
    }

    fn clone_box(&self) -> Box<dyn FileStorageService> {
        Box::new(self.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Helpers ──────────────────────────────────────────────────────────────────

    fn test_tenant() -> EntityId {
        EntityId::parse_str("11111111-1111-1111-1111-111111111111").unwrap()
    }

    async fn test_roundtrip(service: &dyn FileStorageService) {
        let tenant = test_tenant();
        let data = b"hello, storage world!";
        let path = "test/hello.txt";

        let storage_path = service
            .store(tenant, path, data, "text/plain")
            .await
            .expect("store should succeed");
        assert_eq!(storage_path, path);

        let retrieved = service
            .retrieve(tenant, &storage_path)
            .await
            .expect("retrieve should succeed");
        assert_eq!(retrieved, data);

        let _presigned = service
            .get_presigned_url(tenant, &storage_path, 3600)
            .await
            .expect("get_presigned_url should not error");

        service
            .delete(tenant, &storage_path)
            .await
            .expect("delete should succeed");

        // After deletion, retrieve should fail.
        let err = service
            .retrieve(tenant, &storage_path)
            .await
            .expect_err("retrieve after delete should fail");
        assert!(matches!(err, SenseiError::NotFound(_)));
    }

    // ── InMemoryStorageService tests ────────────────────────────────────────────

    #[tokio::test]
    async fn test_in_memory_roundtrip() {
        let service = InMemoryStorageService::new();
        test_roundtrip(&service).await;
    }

    #[tokio::test]
    async fn test_in_memory_presigned_url_is_none() {
        let service = InMemoryStorageService::new();
        let tenant = test_tenant();
        let path = "test/file.txt";
        service
            .store(tenant, path, &[1, 2, 3], "application/octet-stream")
            .await
            .unwrap();

        let url = service
            .get_presigned_url(tenant, path, 3600)
            .await
            .unwrap();
        assert!(url.is_none());
    }

    #[tokio::test]
    async fn test_in_memory_delete_not_found() {
        let service = InMemoryStorageService::new();
        let tenant = test_tenant();
        let err = service
            .delete(tenant, "nonexistent")
            .await
            .expect_err("delete of nonexistent should fail");
        assert!(matches!(err, SenseiError::NotFound(_)));
    }

    // ── LocalStorageService tests ───────────────────────────────────────────────

    #[tokio::test]
    async fn test_local_storage_roundtrip() {
        let dir = tempfile::tempdir().expect("create temp dir");
        let service = LocalStorageService::new(dir.path().join("uploads"));
        test_roundtrip(&service).await;
    }

    #[tokio::test]
    async fn test_local_storage_concurrent_write() {
        let dir = tempfile::tempdir().expect("create temp dir");
        let service = Arc::new(LocalStorageService::new(dir.path().join("uploads")));
        let tenant = test_tenant();

        let mut handles = Vec::new();
        for i in 0..10 {
            let svc = Arc::clone(&service);
            let tenant = tenant;
            handles.push(tokio::spawn(async move {
                let data = vec![i as u8; 1024];
                svc.store(tenant, &format!("concurrent/file_{i}.bin"), &data, "application/octet-stream")
                    .await
                    .expect("concurrent store should succeed");
            }));
        }

        for h in handles {
            h.await.expect("task joined");
        }

        // Verify all files exist
        for i in 0..10 {
            let data = service
                .retrieve(tenant, &format!("concurrent/file_{i}.bin"))
                .await
                .expect("retrieve after concurrent write should succeed");
            assert_eq!(data.len(), 1024);
            assert_eq!(data[0], i as u8);
        }
    }

    #[tokio::test]
    async fn test_local_storage_presigned_url_is_none() {
        let dir = tempfile::tempdir().expect("create temp dir");
        let service = LocalStorageService::new(dir.path().join("uploads"));
        let tenant = test_tenant();
        service
            .store(tenant, "test.txt", b"content", "text/plain")
            .await
            .unwrap();

        let url = service
            .get_presigned_url(tenant, "test.txt", 3600)
            .await
            .unwrap();
        assert!(url.is_none());
    }

    #[tokio::test]
    async fn test_local_storage_not_found() {
        let dir = tempfile::tempdir().expect("create temp dir");
        let service = LocalStorageService::new(dir.path().join("uploads"));
        let tenant = test_tenant();

        let err = service
            .retrieve(tenant, "does_not_exist.txt")
            .await
            .expect_err("retrieve of nonexistent should fail");
        assert!(matches!(err, SenseiError::NotFound(_)));
    }

    // ── S3StorageService tests ──────────────────────────────────────────────────
    //
    // These tests are ignored by default because they require a running S3/MinIO
    // instance.  Run with:
    //   cargo test -- --ignored test_s3
    //
    // Or set environment variables to configure the connection:
    //   S3_ENDPOINT=http://localhost:9000
    //   S3_ACCESS_KEY=minioadmin
    //   S3_SECRET_KEY=minioadmin

    /// Helper: create an S3 service from environment variables (or skip).
    async fn s3_service_from_env() -> Option<S3StorageService> {
        let endpoint = std::env::var("S3_ENDPOINT").ok();
        let access_key = std::env::var("S3_ACCESS_KEY").unwrap_or_else(|_| "minioadmin".into());
        let secret_key = std::env::var("S3_SECRET_KEY").unwrap_or_else(|_| "minioadmin".into());
        let bucket = std::env::var("S3_BUCKET").unwrap_or_else(|_| "sensei-test".into());
        let region = std::env::var("S3_REGION").unwrap_or_else(|_| "us-east-1".into());

        match S3StorageService::new(&bucket, &region, endpoint.as_deref(), &access_key, &secret_key)
        {
            Ok(svc) => Some(svc),
            Err(e) => {
                eprintln!("Skipping S3 test — cannot connect: {e}");
                None
            }
        }
    }

    #[tokio::test]
    #[ignore]
    async fn test_s3_roundtrip() {
        if let Some(svc) = s3_service_from_env().await {
            test_roundtrip(&svc).await;
        }
    }

    #[tokio::test]
    #[ignore]
    async fn test_s3_presigned_url() {
        if let Some(svc) = s3_service_from_env().await {
            let tenant = test_tenant();
            let data = b"presigned content";
            let path = "presigned/test.txt";

            let storage_path = svc
                .store(tenant, path, data, "text/plain")
                .await
                .expect("store should succeed");

            let url = svc
                .get_presigned_url(tenant, &storage_path, 3600)
                .await
                .expect("get_presigned_url should succeed")
                .expect("presigned URL should be Some for S3");

            assert!(
                url.starts_with("http"),
                "Presigned URL should start with http, got: {url}"
            );

            // Clean up
            svc.delete(tenant, &storage_path)
                .await
                .expect("delete should succeed");
        }
    }

    // ── Trait object cloning ────────────────────────────────────────────────────

    #[tokio::test]
    async fn test_trait_object_clone() {
        let service: Box<dyn FileStorageService> =
            Box::new(InMemoryStorageService::new());
        let cloned = service.clone(); // uses clone_box()
        let tenant = test_tenant();

        service
            .store(tenant, "original.txt", b"data", "text/plain")
            .await
            .unwrap();

        let data = cloned
            .retrieve(tenant, "original.txt")
            .await
            .expect("cloned service should see stored data");
        assert_eq!(data, b"data");
    }
}

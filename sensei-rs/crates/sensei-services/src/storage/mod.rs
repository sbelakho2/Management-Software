//! File storage backends for attachment and document management.
//!
//! Provides a [`FileStorageService`] trait with three implementations:
//! - [`LocalStorageService`] — stores files on the local filesystem
//! - [`S3StorageService`] — stores files in S3/MinIO
//! - [`InMemoryStorageService`] — stores files in memory (dev/test)

pub mod file_storage;

pub use file_storage::{
    FileStorageService,
    InMemoryStorageService,
    LocalStorageService,
    S3StorageService,
};

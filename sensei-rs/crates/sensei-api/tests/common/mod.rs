//! Common test utilities for end-to-end API tests.
//!
//! Provides shared setup, authentication helpers, and test data factories
//! used by all integration test files.

pub mod auth;
pub mod fixtures;
pub mod setup;

pub use setup::TestApp;

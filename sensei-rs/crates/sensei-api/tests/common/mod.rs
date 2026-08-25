//! Common test utilities for end-to-end API tests.
//!
//! Provides shared setup, authentication helpers, and test data factories
//! used by all integration test files.
//!
//! Each integration test file compiles this module as its own crate, so any
//! helper unused by a given test binary would trip `dead_code`. The helpers
//! are shared by design; suppress the per-binary lint for the module.

#![allow(dead_code)]

pub mod auth;
pub mod fixtures;
pub mod setup;

pub use setup::TestApp;

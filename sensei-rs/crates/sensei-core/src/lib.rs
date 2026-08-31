//! # Sensei Core
//!
//! Core types, traits, and domain models for the Sensei ERP system.
//!
//! This crate provides the foundational building blocks used by all other
//! Sensei crates, including:
//! - Domain entity definitions
//! - Domain event traits and types
//! - Value objects
//! - Unified error types
//! - Shared type aliases
//! - Configuration types

pub mod config;
#[cfg(not(target_arch = "wasm32"))]
pub mod db;
pub mod domain;
pub mod error;
pub mod pagination;
pub mod types;

/// Re-export commonly used types at the crate root.
pub use config::*;
pub use domain::*;
pub use error::*;
pub use types::*;

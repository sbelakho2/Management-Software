//! # Sensei Database Layer
//!
//! Provides PostgreSQL database connectivity using [`sqlx`] with compile-time
//! checked queries, connection pooling, and migration management.
//!
//! ## Features
//! - Connection pool management with configurable sizing
//! - SQL migration runner (embedding migrations from the `migrations/` directory)
//! - Database model definitions for all entities
//! - Transaction support

pub mod migrations;
pub mod models;
pub mod pg_pool;

pub use migrations::*;
pub use models::*;
pub use pg_pool::*;

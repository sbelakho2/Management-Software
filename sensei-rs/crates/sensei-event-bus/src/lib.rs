//! # Sensei Event Bus
//!
//! Event bus abstraction using NATS JetStream for reliable, at-least-once
//! event delivery. Supports publishing domain events and subscribing to
//! event streams with consumer groups.
//!
//! ## Features
//! - NATS JetStream backed for persistence and replay
//! - At-least-once delivery guarantees
//! - Consumer group support for competing consumers
//! - Event serialization/deserialization via serde

pub mod bus;
pub mod error;
pub mod types;

pub use bus::*;
pub use error::*;
pub use types::*;

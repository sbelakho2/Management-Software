//! API middleware components.
//!
//! Provides middleware layers for authentication, request ID generation,
//! structured logging, metrics collection, CORS handling, security headers,
//! rate limiting, audit logging, idempotency, request validation, and
//! session binding.

pub mod audit;
pub mod auth;
pub mod cors;
pub mod idempotency;
pub mod logging;
pub mod metrics;
pub mod rate_limiter;
pub mod request_guard;
pub mod request_id;
pub mod secure_headers;
pub mod session;

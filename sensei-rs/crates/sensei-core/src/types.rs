//! Shared type aliases for the Sensei ERP system.
//!
//! This module provides standardized type aliases used across all crates
//! to ensure consistency in UUID, DateTime, and other common type usage.

use chrono::{DateTime, Utc};
use uuid::Uuid;

/// A unique identifier for an entity in the system.
pub type EntityId = Uuid;

/// A timestamp type representing UTC datetime.
pub type Timestamp = DateTime<Utc>;

/// A unique identifier for a user session.
pub type SessionId = Uuid;

/// A unique identifier for a tenant/organization.
pub type TenantId = Uuid;

/// A unique identifier for a domain event.
pub type EventId = Uuid;

/// A unique identifier for a correlation chain (tracing).
pub type CorrelationId = Uuid;

/// A phone number string.
pub type PhoneNumber = String;

/// An email address string.
pub type EmailAddress = String;

/// A URL string.
pub type Url = String;

/// A monetary amount represented as a 64-bit float.
///
/// Kept for backward compatibility with existing API contracts.
/// New code should prefer [`crate::domain::value_objects::Money`],
/// which stores amounts as integer cents to avoid floating-point
/// precision issues and rejects non-finite values.
pub type Amount = f64;

/// A percentage value (0.0 to 100.0).
pub type Percentage = f64;

/// A quantity value.
pub type Quantity = i64;

/// Generates a new [`EntityId`] (UUID v4).
#[inline]
pub fn new_id() -> EntityId {
    Uuid::new_v4()
}

/// Returns the current UTC timestamp.
#[inline]
pub fn now() -> Timestamp {
    Utc::now()
}

/// Generates a new [`CorrelationId`].
#[inline]
pub fn new_correlation_id() -> CorrelationId {
    Uuid::new_v4()
}

//! Route-layer authorization helpers (twenty-ninth audit Wave B).
//!
//! This module hosts the canonical per-surface authorization policies that
//! the API route handlers enforce:
//!
//! * [`request_context`] — the ONE server-created [`RequestContext`]
//!   builder every context-aware route/helper uses (DB-resolved scope +
//!   focus; explicit tenant-wide grant in in-memory/dev mode).
//! * [`search_policy`] — the registry mapping every searchable result type
//!   to its canonical read permission and scope mode (Tenant vs
//!   Operational), plus the caller-derived [`AllowedSearchProjection`]
//!   that is pushed into the database search BEFORE ranking.
//! * [`parent_resource`] — the registry mapping attachment parent entity
//!   types to their canonical read/manage permissions, with the
//!   scope-aware parent authorization checks (attachments inherit their
//!   parent's authorization).

pub mod parent_resource;
pub mod request_context;
pub mod search_policy;

pub use request_context::build_request_context;

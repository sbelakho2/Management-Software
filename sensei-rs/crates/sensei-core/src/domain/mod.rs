//! Domain models for Sensei ERP.
//!
//! This module contains the core domain entity definitions, domain event
//! types and traits, and value objects used throughout the system.
//!
//! Authorization and the operating context (twenty-ninth audit Wave A
//! items 3/6): [`RequestContext`] pairs an [`AuthorizedScope`] (what the
//! principal MAY access — resolved from active role-slot assignments)
//! with an [`OperationalFocus`] (where the session acts), and resources
//! are enforced through [`AuthorizedScope::enforce_resource`] against an
//! explicit [`ResourceScope`].

pub mod entities;
pub mod events;
pub mod request_context;
pub mod scope;
pub mod value_objects;

pub use request_context::{OperationalFocus, RequestContext};
pub use scope::{AuthorizedScope, ResourceScope, SiteScope, WorkCenterScope};

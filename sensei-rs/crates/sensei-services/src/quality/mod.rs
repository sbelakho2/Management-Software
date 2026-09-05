//! Quality management domain services.
//!
//! This module provides a comprehensive set of quality management services
//! covering the full manufacturing quality lifecycle:
//!
//! - **models**: Domain models, enums, and DTOs for all quality services
//! - **service**: Quality service trait + in-memory implementation
//! - **ncr**: Non-conformance reports and CAPA workflow
//! - **inspection**: AQL sampling, First Article Inspection, self-inspection
//! - **audit**: Audit evidence packaging, audit trail timeline, certification gating
//! - **supplier**: Supplier quality scorecards and SCAR management
//! - **npi_risk**: NPI risk register (FMEA) and change control
//! - **msa_spc**: Measurement systems analysis (GRR), process capability (Cp/Cpk), SPC
//! - **stage_gates**: NPI stage-gate workflow and traceability
//!
//! # Resource scope (twenty-ninth audit Wave B items 6-8; thirtieth-audit
//! P0 items 6-8)
//!
//! The NCR / CAPA / audit methods of [`QualityService`] take the
//! server-created [`RequestContext`](sensei_core::domain::RequestContext)
//! — never a naked `tenant_id` — and quality records carry an
//! authoritative, SERVER-STAMPED site / work-center anchor
//! ([`QualityScopeStamp`]; migration 170 adds `scope_site_id` /
//! `scope_work_center_id` columns to the real relational quality tables).
//! The database implementation operates on the canonical tables only
//! (`ncr_reports`, `capas`, `audits` / `audit_findings` — migration 173
//! reconciles their columns to the service models; see
//! [`database::DatabaseQualityService`]) and embeds the caller's scope as
//! a SQL predicate in the same statement as the read or mutation
//! ([`scope::quality_scope_predicate`]): site grants match stamped rows
//! of their sites; EXACT work-center grants match only the records
//! stamped at that work center — never the whole site; a corporate
//! record with a NULL scope pair is tenant-wide-only; a caller with no
//! operational scope matches zero rows. Creation scope is derived by the
//! single [`scope::derive_creation_scope`] helper — missing focus never
//! widens a scoped caller into a corporate record.

mod database;
pub use database::DatabaseQualityService;

pub mod audit;
pub mod inspection;
pub mod models;
pub mod msa_spc;
pub mod ncr;
pub mod npi_risk;
pub mod scope;
pub mod service;
pub mod stage_gates;
pub mod supplier;

// Re-export key types for convenience
pub use models::*;
pub use scope::{derive_creation_scope, CanonicalParent};
pub use sensei_core::pagination::PaginatedResponse;
pub use service::{InMemoryQualityService, QualityService};

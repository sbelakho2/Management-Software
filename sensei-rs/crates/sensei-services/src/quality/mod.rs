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
//! # Resource scope (twenty-ninth audit Wave B items 6-8)
//!
//! The NCR / CAPA / audit methods of [`QualityService`] take the
//! server-created [`RequestContext`](sensei_core::domain::RequestContext)
//! — never a naked `tenant_id` — and quality records carry an
//! authoritative, SERVER-STAMPED site / work-center anchor
//! ([`QualityScopeStamp`]; migration 170 adds `scope_site_id` /
//! `scope_work_center_id` columns to the relational quality tables). The
//! database implementation embeds the caller's scope as a SQL predicate
//! in the same statement as the read or mutation (site-scoped callers
//! match `scope_site_id = ANY(authorized sites)`; a corporate record
//! with a NULL scope is tenant-wide-only; a caller with no operational
//! scope matches zero rows).

mod database;
pub use database::DatabaseQualityService;

pub mod audit;
pub mod inspection;
pub mod models;
pub mod msa_spc;
pub mod ncr;
pub mod npi_risk;
pub mod service;
pub mod stage_gates;
pub mod supplier;

// Re-export key types for convenience
pub use models::*;
pub use sensei_core::pagination::PaginatedResponse;
pub use service::{InMemoryQualityService, QualityService};

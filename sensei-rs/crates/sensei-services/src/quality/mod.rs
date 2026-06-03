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

mod database;
pub use database::DatabaseQualityService;

pub mod models;
pub mod ncr;
pub mod inspection;
pub mod audit;
pub mod supplier;
pub mod npi_risk;
pub mod msa_spc;
pub mod stage_gates;
pub mod service;

// Re-export key types for convenience
pub use models::*;
pub use service::{InMemoryQualityService, QualityService};
pub use sensei_core::pagination::PaginatedResponse;

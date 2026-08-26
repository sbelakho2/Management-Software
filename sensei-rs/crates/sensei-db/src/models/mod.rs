//! Database model definitions.
//!
//! These models map directly to database tables and are used by sqlx
//! for compile-time checked queries. They differ from domain entities
//! in that they closely mirror the database schema rather than the domain.
//!
//! Every model derives `Debug, Clone, sqlx::FromRow, Serialize, Deserialize`
//! so that it can be used with sqlx query macros and serialized over the API.
//!
//! # Module Organization
//!
//! - Core models (tenants, users, roles, etc.) are defined inline below.
//! - Domain-specific models are organized in separate module files:
//!   - [`account`] — CRM accounts, contacts, opportunities
//!   - [`rfq`] — RFQ line items, quotes, qualifications
//!   - [`product`] — Routings, stations, work order operations, production cells
//!   - [`quality`] — Non-conformances, inspections, gauges, CAPA actions, QMS
//!   - [`finance`] — GL accounts, invoices, journal lines, tax, FX rates
//!   - [`maintenance`] — Assets, maintenance work orders, spare parts, downtime
//!   - [`hr`] — Compensation, training programs, enrollments
//!   - [`ops`] — Kanban, obeya, KPIs, tasks, standard work
//!   - [`system`] — Notifications, service state, knowledge, sites

pub mod account;
pub mod finance;
pub mod hr;
pub mod maintenance;
pub mod ops;
pub mod product;
pub mod quality;
pub mod rfq;
pub mod system;

// Re-export all domain models for convenient access
pub use account::*;
pub use finance::*;
pub use hr::*;
pub use maintenance::*;
pub use ops::*;
pub use product::*;
pub use quality::*;
pub use rfq::*;
pub use system::*;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// ── Core / Multi-Tenant Models ─────────────────────────────────────────────

/// Database representation of a tenant organization.
///
/// Each tenant is an isolated organization within the multi-tenant system.
/// All business data is scoped to a tenant.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TenantModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Organization name.
    pub name: String,
    /// Unique subdomain slug for tenant identification.
    pub slug: String,
    /// Whether the tenant is active.
    pub is_active: bool,
    /// Feature flags (JSON array of strings).
    pub features: serde_json::Value,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a user.
///
/// Users are scoped to a tenant and identified by email within that tenant.
/// Passwords are hashed using Argon2. Roles are stored as a PostgreSQL text
/// array and map directly to `Vec<String>`.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct UserModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Email address (unique within tenant).
    pub email: String,
    /// Display name.
    pub name: String,
    /// Password hash (Argon2).
    pub password_hash: String,
    /// Role names (PostgreSQL `TEXT[]`).
    pub roles: Vec<String>,
    /// Whether the account is active.
    pub is_active: bool,
    /// Whether the account's email address has been verified.
    pub email_verified: bool,
    /// Incremented on every password change/reset; older refresh tokens
    /// become invalid.
    pub credential_version: i64,
    /// Last login timestamp.
    pub last_login_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a role definition.
///
/// Roles define permission sets that can be assigned to users within a tenant.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct RoleModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Role name (unique within tenant).
    pub name: String,
    /// Description of the role's purpose.
    pub description: String,
    /// Permission identifiers assigned to this role.
    pub permissions: serde_json::Value,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Quality Models ─────────────────────────────────────────────────────────

/// Database representation of a non-conformance report (NCR).
///
/// NCRs document instances where products, processes, or systems
/// fail to meet specified requirements. They can be linked to CAPAs.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NcrModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable NCR number.
    pub ncr_number: String,
    /// Title/summary of the non-conformance.
    pub title: String,
    /// Detailed description.
    pub description: String,
    /// Severity: minor, major, critical.
    pub severity: String,
    /// Status: open, under_investigation, action_defined, in_progress, closed, rejected.
    pub status: String,
    /// Foreign key to CAPA (nullable).
    pub capa_id: Option<Uuid>,
    /// User who reported the NCR.
    pub reported_by: Uuid,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Corrective and Preventive Action (CAPA).
///
/// CAPAs are used to investigate and correct non-conformances,
/// and to implement preventive measures to avoid recurrence.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CapaModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable CAPA number.
    pub capa_number: String,
    /// Title of the CAPA.
    pub title: String,
    /// Root cause analysis text.
    pub root_cause: Option<String>,
    /// Action plan description.
    pub action_plan: String,
    /// Status: open, analysis_in_progress, approved, implementation_in_progress, verification_in_progress, closed.
    pub status: String,
    /// User who owns this CAPA.
    pub owner_id: Uuid,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
    /// Deadline for completion.
    pub due_date: Option<DateTime<Utc>>,
}

/// Database representation of an inspection record.
///
/// Inspections are quality checks performed on products, processes,
/// or incoming materials. They track results and inspector assignments.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InspectionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable inspection number.
    pub inspection_number: String,
    /// Type of inspection (e.g., incoming, in-process, final, FAI).
    pub inspection_type: String,
    /// Product or item being inspected.
    pub product_id: Option<Uuid>,
    /// Work order associated with this inspection.
    pub work_order_id: Option<Uuid>,
    /// Result: pass, fail, conditional.
    pub result: String,
    /// Inspector user ID.
    pub inspector_id: Option<Uuid>,
    /// Status of the inspection.
    pub status: String,
    /// Notes or observations from the inspection.
    pub notes: Option<String>,
    /// Timestamp when the inspection was performed.
    pub inspected_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a quality audit.
///
/// Audits assess compliance with quality management system requirements,
/// standards, and procedures. They can be internal, external, or supplier audits.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AuditModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable audit number.
    pub audit_number: String,
    /// Type of audit (internal, external, supplier, regulatory, certification).
    pub audit_type: String,
    /// Status (planned, scheduled, in_progress, completed, closed, cancelled).
    pub status: String,
    /// Title of the audit.
    pub title: String,
    /// Scope of the audit.
    pub scope: String,
    /// Area or department being audited.
    pub area: String,
    /// Lead auditor user ID.
    pub lead_auditor_id: Option<Uuid>,
    /// Scheduled date for the audit.
    pub scheduled_date: Option<DateTime<Utc>>,
    /// Actual start date.
    pub start_date: Option<DateTime<Utc>>,
    /// Actual completion date.
    pub completion_date: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an audit finding.
///
/// Findings are non-conformances, observations, or opportunities for
/// improvement identified during an audit.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AuditFindingModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent audit ID.
    pub audit_id: Uuid,
    /// Human-readable finding number.
    pub finding_number: String,
    /// Severity (observation, minor, major, critical).
    pub severity: String,
    /// Status (open, accepted, in_progress, implemented, verified, closed, waived).
    pub status: String,
    /// Description of the finding.
    pub description: String,
    /// Applicable clause or standard reference.
    pub clause: Option<String>,
    /// Area where the finding was identified.
    pub area: Option<String>,
    /// Implementation notes for corrective actions.
    pub implementation_notes: Option<String>,
    /// User who verified the finding closure.
    pub verified_by: Option<Uuid>,
    /// Verification notes.
    pub verification_notes: Option<String>,
    /// Deadline for resolution.
    pub due_date: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier.
///
/// Suppliers provide materials, components, or services to the organization.
/// They are evaluated and scored based on quality, delivery, and cost.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SupplierModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable supplier code/number.
    pub supplier_number: String,
    /// Supplier company name.
    pub name: String,
    /// Supplier tier (1, 2, 3, etc.).
    pub tier: Option<String>,
    /// Status (active, inactive, on_hold, disqualified).
    pub status: String,
    /// Contact email.
    pub email: Option<String>,
    /// Contact phone.
    pub phone: Option<String>,
    /// Physical address.
    pub address: Option<String>,
    /// Supplier website.
    pub website: Option<String>,
    /// ISO or quality certifications held.
    pub certifications: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier scorecard.
///
/// Scorecards provide periodic evaluation of supplier performance
/// across quality, delivery, cost, and responsiveness metrics.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SupplierScorecardModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Supplier being evaluated.
    pub supplier_id: Uuid,
    /// Evaluation period identifier (e.g., "2026-Q1").
    pub period_key: String,
    /// Quality score (0-100).
    pub quality_score: f64,
    /// Delivery/on-time performance score (0-100).
    pub delivery_score: f64,
    /// Cost/competitiveness score (0-100).
    pub cost_score: f64,
    /// Responsiveness score (0-100).
    pub responsiveness_score: f64,
    /// Overall weighted score (0-100).
    pub overall_score: f64,
    /// Supplier tier assigned based on score.
    pub tier: String,
    /// Defects per million (PPM) rate.
    pub ppm_rate: Option<f64>,
    /// On-time delivery percentage.
    pub otd_percentage: Option<f64>,
    /// Timestamp when the scorecard was computed.
    pub computed_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Supplier Corrective Action Request (SCAR).
///
/// SCARs are issued to suppliers when quality or delivery issues are
/// identified, requiring corrective action from the supplier.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ScarModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable SCAR number.
    pub scar_number: String,
    /// Supplier against whom the SCAR is raised.
    pub supplier_id: Uuid,
    /// Title of the SCAR.
    pub title: String,
    /// Detailed description of the issue.
    pub description: String,
    /// Status (open, sent_to_supplier, containment_in_progress, root_cause_analysis, corrective_action_defined, verification_in_progress, closed, rejected).
    pub status: String,
    /// Severity of the issue.
    pub severity: String,
    /// Containment actions taken.
    pub containment_action: Option<String>,
    /// Root cause identified by supplier.
    pub root_cause: Option<String>,
    /// Corrective action proposed by supplier.
    pub corrective_action: Option<String>,
    /// Verification notes after action implementation.
    pub verification_notes: Option<String>,
    /// Owner of the SCAR within the organization.
    pub owner_id: Option<Uuid>,
    /// Deadline for resolution.
    pub due_date: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an NPI (New Product Introduction) risk item.
///
/// Risks are identified during the NPI process and tracked through
/// various phases (intake, DFM, prototype, pilot, SOP).
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NpiRiskModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable risk number.
    pub risk_number: String,
    /// Title of the risk.
    pub title: String,
    /// Detailed description.
    pub description: String,
    /// Risk category (design_complexity, process_capability, supplier_capability, etc.).
    pub category: String,
    /// NPI phase when this risk was identified.
    pub phase: String,
    /// Related project, if applicable.
    pub project_id: Option<Uuid>,
    /// Initial severity score (1-10).
    pub initial_severity: i32,
    /// Initial occurrence score (1-10).
    pub initial_occurrence: i32,
    /// Initial detection score (1-10).
    pub initial_detection: i32,
    /// Current severity score (1-10).
    pub current_severity: i32,
    /// Current occurrence score (1-10).
    pub current_occurrence: i32,
    /// Current detection score (1-10).
    pub current_detection: i32,
    /// Target severity score (1-10).
    pub target_severity: i32,
    /// Target occurrence score (1-10).
    pub target_occurrence: i32,
    /// Target detection score (1-10).
    pub target_detection: i32,
    /// Whether the risk has been closed.
    pub is_closed: bool,
    /// Whether the risk has materialized.
    pub has_occurred: bool,
    /// Timestamp when the risk occurred.
    pub occurred_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Measurement Systems Analysis (MSA) study.
///
/// MSA studies evaluate the capability of measurement systems including
/// Gauge R&R, linearity, bias, stability, and attribute agreement studies.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct MsaModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Type of MSA study (grr, linearity, bias, stability, attribute_agreement).
    pub study_type: String,
    /// Title of the study.
    pub title: String,
    /// Gauge/equipment being evaluated.
    pub gauge_id: Option<Uuid>,
    /// Number of operators involved.
    pub operators_count: i32,
    /// Number of parts measured.
    pub parts_count: i32,
    /// Number of trials per operator/part.
    pub trials_count: i32,
    /// Status (planned, in_progress, completed).
    pub status: String,
    /// Repeatability (Equipment Variation) as % of total.
    pub repeatability_ev: Option<f64>,
    /// Reproducibility (Appraiser Variation) as % of total.
    pub reproducibility_av: Option<f64>,
    /// Gauge R&R as % of total variation.
    pub grr_percent: Option<f64>,
    /// Number of distinct categories (ndc).
    pub ndc: Option<i32>,
    /// Timestamp when the study was completed.
    pub completed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of SPC (Statistical Process Control) data point.
///
/// SPC data tracks process measurements over time for statistical
/// process control analysis and capability studies.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SpcDataModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product or characteristic being measured.
    pub product_id: Option<Uuid>,
    /// Process step or station.
    pub process_step: Option<String>,
    /// Characteristic being measured.
    pub characteristic: String,
    /// Measured value.
    pub measured_value: f64,
    /// Upper specification limit.
    pub usl: Option<f64>,
    /// Lower specification limit.
    pub lsl: Option<f64>,
    /// Target value.
    pub target: Option<f64>,
    /// Unit of measurement.
    pub unit: Option<String>,
    /// Sample subgroup identifier.
    pub subgroup_id: Option<String>,
    /// Sample size for this subgroup.
    pub sample_size: Option<i32>,
    /// Operator who took the measurement.
    pub operator_id: Option<Uuid>,
    /// Gauge/equipment used.
    pub gauge_id: Option<Uuid>,
    /// Timestamp when the measurement was taken.
    pub measured_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of an NPI stage gate.
///
/// Stage gates control the progression of new product introduction
/// projects through defined phases with required artifacts and reviews.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct StageGateModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// NPI project associated with this gate.
    pub project_id: Uuid,
    /// Current NPI stage (intake, dfm, prototype, pilot, sop).
    pub stage: String,
    /// Gate decision (go, no_go, conditional_go, hold).
    pub decision: Option<String>,
    /// Rationale for the decision.
    pub decision_rationale: Option<String>,
    /// User who conducted the gate review.
    pub reviewed_by: Option<Uuid>,
    /// Timestamp when the gate review was conducted.
    pub conducted_at: Option<DateTime<Utc>>,
    /// Whether this stage has been completed.
    pub is_completed: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Production / Manufacturing Models ──────────────────────────────────────

/// Database representation of a product.
///
/// Products are the items manufactured or assembled by the organization.
/// They are the central entity linking BOMs, work orders, and inventory.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ProductModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable product code/part number.
    pub product_number: String,
    /// Product name.
    pub name: String,
    /// Product description.
    pub description: Option<String>,
    /// Product category or family.
    pub category: Option<String>,
    /// Unit of measure (e.g., pcs, kg, m).
    pub unit_of_measure: String,
    /// Standard cost per unit.
    pub standard_cost: Option<f64>,
    /// List price per unit.
    pub list_price: Option<f64>,
    /// Current inventory quantity on hand.
    pub quantity_on_hand: f64,
    /// Minimum stock level before reorder.
    pub reorder_point: Option<f64>,
    /// Whether the product is active for production.
    pub is_active: bool,
    /// Product type (raw_material, component, subassembly, finished_good, supply).
    pub product_type: String,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Bill of Materials (BOM) item.
///
/// BOM items define the component quantities required to produce
/// a parent product. They form the product structure tree.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct BomItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent product (the assembled product).
    pub parent_product_id: Uuid,
    /// Child component product.
    pub component_product_id: Uuid,
    /// Quantity of component required per parent unit.
    pub quantity: f64,
    /// Unit of measure for the quantity.
    pub unit_of_measure: String,
    /// Scrap percentage allowance.
    pub scrap_percent: Option<f64>,
    /// Routing sequence/operation number.
    pub operation_sequence: Option<i32>,
    /// Effective date for this BOM revision.
    pub effective_date: Option<DateTime<Utc>>,
    /// Whether this BOM item is active.
    pub is_active: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a production order.
///
/// Production orders authorize the manufacturing of a specific quantity
/// of a product. They track the production lifecycle from release to completion.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ProductionOrderModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable production order number.
    pub order_number: String,
    /// Product to be produced.
    pub product_id: Uuid,
    /// Quantity planned for production.
    pub quantity_planned: f64,
    /// Quantity actually produced.
    pub quantity_produced: f64,
    /// Quantity scrapped during production.
    pub quantity_scrapped: f64,
    /// Status (created, released, in_progress, completed, cancelled, on_hold).
    pub status: String,
    /// Assigned work center.
    pub work_center_id: Option<Uuid>,
    /// Scheduled start date.
    pub scheduled_start: Option<DateTime<Utc>>,
    /// Scheduled end date.
    pub scheduled_end: Option<DateTime<Utc>>,
    /// Actual start date.
    pub actual_start: Option<DateTime<Utc>>,
    /// Actual completion date.
    pub actual_completion: Option<DateTime<Utc>>,
    /// Priority level.
    pub priority: Option<String>,
    /// Related work order, if any.
    pub work_order_id: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an MRP (Material Requirements Planning) record.
///
/// MRP records capture the results of material requirement planning runs,
/// including planned orders, shortages, and recommendations.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct MrpRecordModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// MRP run identifier.
    pub run_id: Option<Uuid>,
    /// Product being planned.
    pub product_id: Uuid,
    /// Gross requirement quantity.
    pub gross_requirement: f64,
    /// Scheduled receipts quantity.
    pub scheduled_receipts: f64,
    /// Projected on-hand quantity.
    pub projected_on_hand: f64,
    /// Net requirement quantity.
    pub net_requirement: f64,
    /// Planned order receipt quantity.
    pub planned_order_receipt: f64,
    /// Planned order release quantity.
    pub planned_order_release: f64,
    /// Planned order release date.
    pub planned_order_date: Option<DateTime<Utc>>,
    /// Whether this record indicates a shortage.
    pub is_shortage: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a work center.
///
/// Work centers are production resources (machines, cells, or workstations)
/// where manufacturing operations are performed.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct WorkCenterModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable work center code.
    pub work_center_number: String,
    /// Work center name.
    pub name: String,
    /// Description of the work center's capabilities.
    pub description: Option<String>,
    /// Type of work center (manual, semi_automated, automated, assembly, test).
    pub work_center_type: String,
    /// Whether the work center is active.
    pub is_active: bool,
    /// Capacity per shift in units.
    pub capacity_per_shift: Option<f64>,
    /// Number of shifts per day.
    pub shifts_per_day: Option<i32>,
    /// Efficiency factor (0.0 - 1.0).
    pub efficiency: Option<f64>,
    /// Associated department.
    pub department: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Work Order Model ───────────────────────────────────────────────────────

/// Database representation of a work order.
///
/// Work orders represent tasks assigned to work centers for production
/// or maintenance activities. They track progress through defined states.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct WorkOrderModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable work order number.
    pub wo_number: String,
    /// Product/part being produced.
    pub product_id: Uuid,
    /// Quantity to produce.
    pub quantity: i64,
    /// Status (created, released, in_progress, completed, cancelled, on_hold).
    pub status: String,
    /// Assigned work center.
    pub work_center_id: Option<Uuid>,
    /// Scheduled start date.
    pub scheduled_start: Option<DateTime<Utc>>,
    /// Scheduled end date.
    pub scheduled_end: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Maintenance Models ─────────────────────────────────────────────────────

/// Database representation of a maintenance work request.
///
/// Work requests are submitted when equipment issues or maintenance
/// needs are identified. They may be converted to work orders.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct MaintenanceWorkRequestModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable request number.
    pub request_number: String,
    /// Equipment requiring maintenance.
    pub equipment_id: Uuid,
    /// Title of the work request.
    pub title: String,
    /// Detailed description of the issue.
    pub description: String,
    /// Priority (low, medium, high, emergency).
    pub priority: String,
    /// Status (open, assigned, in_progress, completed, cancelled).
    pub status: String,
    /// Type of maintenance (corrective, preventive, predictive).
    pub work_type: String,
    /// User who submitted the request.
    pub requested_by: Uuid,
    /// User assigned to perform the work.
    pub assigned_to: Option<Uuid>,
    /// Related work order, once created.
    pub work_order_id: Option<Uuid>,
    /// Target completion date.
    pub target_date: Option<DateTime<Utc>>,
    /// Actual completion date.
    pub completed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Preventive Maintenance (PM) schedule.
///
/// PM schedules define recurring maintenance tasks for equipment
/// based on calendar intervals, meter readings, or usage counts.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PmScheduledModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Equipment subject to PM.
    pub equipment_id: Uuid,
    /// PM schedule identifier/number.
    pub schedule_number: String,
    /// Title of the PM task.
    pub title: String,
    /// Description of the PM procedure.
    pub description: Option<String>,
    /// Frequency type (calendar, meter, usage).
    pub frequency_type: String,
    /// Frequency value (e.g., 30 for days, 5000 for km/miles).
    pub frequency_value: i32,
    /// Unit for frequency (days, hours, cycles, km).
    pub frequency_unit: String,
    /// Last performed date.
    pub last_performed_at: Option<DateTime<Utc>>,
    /// Next due date.
    pub next_due_at: Option<DateTime<Utc>>,
    /// Whether the schedule is active.
    pub is_active: bool,
    /// Assigned maintenance team or user.
    pub assigned_to: Option<Uuid>,
    /// Estimated duration in minutes.
    pub estimated_duration_minutes: Option<i32>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of equipment/machine.
///
/// Equipment records track all machines, tools, and assets
/// used in production and maintenance operations.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct EquipmentModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable equipment code/number.
    pub equipment_number: String,
    /// Equipment name.
    pub name: String,
    /// Description of the equipment.
    pub description: Option<String>,
    /// Equipment type (machine, tool, vehicle, facility, instrument).
    pub equipment_type: String,
    /// Manufacturer name.
    pub manufacturer: Option<String>,
    /// Model number.
    pub model: Option<String>,
    /// Serial number.
    pub serial_number: Option<String>,
    /// Location within the facility.
    pub location: Option<String>,
    /// Department responsible for the equipment.
    pub department: Option<String>,
    /// Status (operational, under_maintenance, out_of_service, retired).
    pub status: String,
    /// Installation/commissioning date.
    pub install_date: Option<DateTime<Utc>>,
    /// Expected useful life in months.
    pub useful_life_months: Option<i32>,
    /// Meter unit type (hours, cycles, km, etc.).
    pub meter_unit: Option<String>,
    /// Current meter reading value.
    pub current_meter_value: Option<f64>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Finance Models ─────────────────────────────────────────────────────────

/// Database representation of an invoice.
///
/// Invoices represent accounts payable (received from suppliers) or
/// accounts receivable (sent to customers) transactions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InvoiceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable invoice number.
    pub invoice_number: String,
    /// Type of invoice (payable, receivable).
    pub invoice_type: String,
    /// Status (draft, sent, approved, paid, overdue, cancelled).
    pub status: String,
    /// ID of the supplier (AP) or customer (AR).
    pub counterparty_id: Uuid,
    /// Name of the counterparty.
    pub counterparty_name: String,
    /// Invoice date.
    pub invoice_date: DateTime<Utc>,
    /// Due date for payment.
    pub due_date: DateTime<Utc>,
    /// Total amount before tax.
    pub subtotal: f64,
    /// Tax amount.
    pub tax_amount: f64,
    /// Total amount including tax.
    pub total_amount: f64,
    /// Currency code (e.g., USD, EUR, MAD).
    pub currency: String,
    /// Related purchase order or sales order.
    pub order_id: Option<Uuid>,
    /// User who created/manages the invoice.
    pub created_by: Option<Uuid>,
    /// Notes or memo.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a payment.
///
/// Payments track money received from customers (AR) or
/// sent to suppliers (AP).
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PaymentModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable payment reference/number.
    pub payment_number: String,
    /// Type of payment (received, issued).
    pub payment_type: String,
    /// Payment method (bank_transfer, check, cash, credit_card, wire).
    pub payment_method: String,
    /// Status (pending, completed, failed, refunded).
    pub status: String,
    /// Amount paid.
    pub amount: f64,
    /// Currency code.
    pub currency: String,
    /// ID of the counterparty.
    pub counterparty_id: Uuid,
    /// Related invoice, if applicable.
    pub invoice_id: Option<Uuid>,
    /// Payment date.
    pub payment_date: DateTime<Utc>,
    /// Bank account or reference details.
    pub reference: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a budget.
///
/// Budgets define financial plans for departments, projects,
/// or cost centers over specific fiscal periods.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct BudgetModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Budget identifier/code.
    pub budget_code: String,
    /// Budget name/title.
    pub name: String,
    /// Budget type (departmental, project, capital, operational).
    pub budget_type: String,
    /// Fiscal year or period.
    pub fiscal_period: String,
    /// Department or cost center.
    pub department: Option<String>,
    /// Total budgeted amount.
    pub budgeted_amount: f64,
    /// Amount spent so far.
    pub spent_amount: f64,
    /// Amount committed but not yet spent.
    pub committed_amount: f64,
    /// Status (draft, active, closed, cancelled).
    pub status: String,
    /// User who owns/manages this budget.
    pub owner_id: Option<Uuid>,
    /// Notes or description.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a journal entry.
///
/// Journal entries are accounting transactions that record debits
/// and credits to the general ledger.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct JournalEntryModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable journal entry number.
    pub entry_number: String,
    /// Description of the transaction.
    pub description: String,
    /// Entry type (standard, adjusting, closing, reversing).
    pub entry_type: String,
    /// Status (draft, posted, reversed).
    pub status: String,
    /// Total debit amount.
    pub debit_total: f64,
    /// Total credit amount.
    pub credit_total: f64,
    /// Currency code.
    pub currency: String,
    /// Accounting period (e.g., "2026-05").
    pub period: String,
    /// Date of the transaction.
    pub entry_date: DateTime<Utc>,
    /// User who posted the entry.
    pub posted_by: Option<Uuid>,
    /// Timestamp when the entry was posted.
    pub posted_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a cost rollup.
///
/// Cost rollups calculate the total cost of a product by aggregating
/// material, labor, and overhead costs from the BOM structure.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CostRollupModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product being costed.
    pub product_id: Uuid,
    /// Version identifier for this rollup.
    pub version: String,
    /// Total calculated cost.
    pub total_cost: f64,
    /// Material cost component.
    pub material_cost: f64,
    /// Labor cost component.
    pub labor_cost: f64,
    /// Overhead cost component.
    pub overhead_cost: f64,
    /// Currency code.
    pub currency: String,
    /// Status (draft, finalized).
    pub status: String,
    /// Timestamp when the rollup was computed.
    pub computed_at: DateTime<Utc>,
    /// User who triggered the rollup.
    pub computed_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

// ── Human Resources Models ─────────────────────────────────────────────────

/// Database representation of an employee.
///
/// Employees are the organization's workforce. Each employee record
/// tracks personal, job, and employment information.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct EmployeeModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable employee number/ID.
    pub employee_number: String,
    /// Legal first name.
    pub first_name: String,
    /// Legal last name.
    pub last_name: String,
    /// Work email address.
    pub email: String,
    /// Contact phone number.
    pub phone: Option<String>,
    /// Job title or position.
    pub job_title: Option<String>,
    /// Department.
    pub department: Option<String>,
    /// Employment type (full_time, part_time, contractor, intern, temporary).
    pub employment_type: String,
    /// Status (active, on_leave, terminated, suspended).
    pub status: String,
    /// Date of hire.
    pub hire_date: DateTime<Utc>,
    /// Date of termination, if applicable.
    pub termination_date: Option<DateTime<Utc>>,
    /// Supervisor/manager user ID.
    pub manager_id: Option<Uuid>,
    /// User account ID linked to this employee.
    pub user_id: Option<Uuid>,
    /// Physical or work location.
    pub location: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a training record.
///
/// Training records track employee participation in training courses,
/// including completion status, scores, and expiration.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TrainingRecordModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee who received the training.
    pub employee_id: Uuid,
    /// Training course name or identifier.
    pub training_name: String,
    /// Training type (internal, external, online, on_the_job, certification).
    pub training_type: String,
    /// Description of the training.
    pub description: Option<String>,
    /// Status (enrolled, in_progress, completed, failed, expired).
    pub status: String,
    /// Score achieved (if applicable).
    pub score: Option<f64>,
    /// Whether the employee passed.
    pub passed: bool,
    /// Date the training was completed.
    pub completed_at: Option<DateTime<Utc>>,
    /// Expiration date for the training (if time-limited).
    pub expires_at: Option<DateTime<Utc>>,
    /// User who provided or verified the training.
    pub trainer_id: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a certification.
///
/// Certifications are formal qualifications that employees hold,
/// often with expiration dates and renewal requirements.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CertificationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee holding the certification.
    pub employee_id: Uuid,
    /// Certification name.
    pub certification_name: String,
    /// Issuing body or organization.
    pub issuing_body: Option<String>,
    /// Certification ID or license number.
    pub certification_number: Option<String>,
    /// Status (active, expired, revoked, pending).
    pub status: String,
    /// Date when the certification was issued.
    pub issued_at: DateTime<Utc>,
    /// Date when the certification expires.
    pub expires_at: Option<DateTime<Utc>>,
    /// Date when the certification was renewed.
    pub renewed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an attendance record.
///
/// Attendance records track employee presence, absences, and
/// attendance status for each work day.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AttendanceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee associated with this record.
    pub employee_id: Uuid,
    /// Date of attendance.
    pub attendance_date: DateTime<Utc>,
    /// Status (present, absent, late, half_day, holiday, excused).
    pub status: String,
    /// Check-in time.
    pub check_in: Option<DateTime<Utc>>,
    /// Check-out time.
    pub check_out: Option<DateTime<Utc>>,
    /// Total hours worked.
    pub hours_worked: Option<f64>,
    /// Notes or reason for absence.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a performance review.
///
/// Performance reviews are periodic evaluations of an employee's
/// job performance, competencies, and development goals.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PerformanceReviewModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee being reviewed.
    pub employee_id: Uuid,
    /// User conducting the review.
    pub reviewer_id: Uuid,
    /// Review period identifier (e.g., "2026-Q1").
    pub review_period: String,
    /// Type of review (annual, quarterly, probation, project, 360).
    pub review_type: String,
    /// Status (draft, in_progress, completed, acknowledged).
    pub status: String,
    /// Overall rating (1-5 or similar scale).
    pub rating: Option<String>,
    /// Overall summary score.
    pub overall_score: Option<f64>,
    /// Strengths identified.
    pub strengths: Option<String>,
    /// Areas for improvement.
    pub improvements: Option<String>,
    /// Goals and objectives for next period.
    pub goals: Option<String>,
    /// Employee comments.
    pub employee_comments: Option<String>,
    /// Date the review was completed.
    pub completed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a timecard entry.
///
/// Timecards track employee clock-in/clock-out events for
/// attendance, payroll, and labor cost tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TimecardModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee associated with this timecard.
    pub employee_id: Uuid,
    /// Type of event (clock_in, clock_out, break_start, break_end).
    pub event_type: String,
    /// Timestamp of the event.
    pub event_time: DateTime<Utc>,
    /// Work order or project associated with the time.
    pub work_order_id: Option<Uuid>,
    /// Notes or reason for the entry.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of a leave request.
///
/// Leave requests track employee time-off requests including
/// vacation, sick leave, personal days, and other absences.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct LeaveRequestModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee requesting leave.
    pub employee_id: Uuid,
    /// Type of leave (vacation, sick, personal, maternity, paternity, bereavement, unpaid).
    pub leave_type: String,
    /// Status (pending, approved, rejected, cancelled, in_progress).
    pub status: String,
    /// Start date of leave.
    pub start_date: DateTime<Utc>,
    /// End date of leave.
    pub end_date: DateTime<Utc>,
    /// Total days requested.
    pub total_days: f64,
    /// Reason for the leave request.
    pub reason: Option<String>,
    /// User who approved the request.
    pub approved_by: Option<Uuid>,
    /// Manager notes or comments.
    pub manager_notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Supply Chain Models ────────────────────────────────────────────────────

/// Database representation of a purchase order.
///
/// Purchase orders are issued to suppliers to procure materials,
/// components, or services at agreed terms and prices.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PurchaseOrderModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable purchase order number.
    pub po_number: String,
    /// Supplier being ordered from.
    pub supplier_id: Uuid,
    /// Status (draft, sent, confirmed, received, cancelled, closed).
    pub status: String,
    /// Order date.
    pub order_date: DateTime<Utc>,
    /// Expected delivery date.
    pub expected_date: Option<DateTime<Utc>>,
    /// Total amount of the order.
    pub total_amount: f64,
    /// Currency code.
    pub currency: String,
    /// Payment terms (e.g., "Net 30").
    pub payment_terms: Option<String>,
    /// Shipping terms (e.g., "FOB", "CIF").
    pub shipping_terms: Option<String>,
    /// Shipping address or instructions.
    pub shipping_address: Option<String>,
    /// User who created the order.
    pub created_by: Option<Uuid>,
    /// Notes for the supplier.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a purchase order line item.
///
/// Each line item specifies a product, quantity, and price within
/// a purchase order.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PurchaseOrderItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent purchase order.
    pub purchase_order_id: Uuid,
    /// Line number.
    pub line_number: i32,
    /// Product being ordered.
    pub product_id: Uuid,
    /// Quantity ordered.
    pub quantity: f64,
    /// Quantity received so far.
    pub quantity_received: f64,
    /// Unit price.
    pub unit_price: f64,
    /// Total line amount.
    pub total_amount: f64,
    /// Unit of measure.
    pub unit_of_measure: String,
    /// Expected delivery date for this line.
    pub expected_date: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an inventory item.
///
/// Inventory items track the quantity and location of products
/// stored in warehouses, bins, or storage locations.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InventoryItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product in inventory.
    pub product_id: Uuid,
    /// Warehouse or storage location.
    pub location: String,
    /// Bin or shelf location within the warehouse.
    pub bin_location: Option<String>,
    /// Current quantity on hand.
    pub quantity_on_hand: f64,
    /// Quantity reserved for orders.
    pub quantity_reserved: f64,
    /// Quantity available (on_hand - reserved).
    pub quantity_available: f64,
    /// Lot or batch number.
    pub lot_number: Option<String>,
    /// Serial number (for serialized items).
    pub serial_number: Option<String>,
    /// Expiration date (for perishable items).
    pub expiry_date: Option<DateTime<Utc>>,
    /// Unit of measure.
    pub unit_of_measure: String,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a stock move.
///
/// Stock moves record the transfer of inventory between locations,
/// including receipts, issues, and internal transfers.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct StockMoveModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product being moved.
    pub product_id: Uuid,
    /// Source location.
    pub from_location: Option<String>,
    /// Destination location.
    pub to_location: String,
    /// Quantity moved.
    pub quantity: f64,
    /// Type of move (receipt, issue, transfer, adjustment).
    pub move_type: String,
    /// Reference document (PO, SO, work order, etc.).
    pub reference_type: Option<String>,
    /// Reference document ID.
    pub reference_id: Option<Uuid>,
    /// Lot or batch number.
    pub lot_number: Option<String>,
    /// Unit of measure.
    pub unit_of_measure: String,
    /// User who performed the move.
    pub moved_by: Option<Uuid>,
    /// Timestamp of the move.
    pub moved_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of a goods receipt.
///
/// Goods receipts document the physical receipt of materials
/// against a purchase order, updating inventory and triggering
/// quality inspection if needed.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct GoodsReceiptModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable receipt number.
    pub receipt_number: String,
    /// Purchase order being received against.
    pub purchase_order_id: Uuid,
    /// Supplier delivering the goods.
    pub supplier_id: Uuid,
    /// Status (expected, partially_received, fully_received, cancelled).
    pub status: String,
    /// Date of receipt.
    pub receipt_date: DateTime<Utc>,
    /// Delivery note reference from supplier.
    pub delivery_note: Option<String>,
    /// Whether the receipt passed quality inspection.
    pub is_quality_approved: Option<bool>,
    /// User who received the goods.
    pub received_by: Option<Uuid>,
    /// Notes about the receipt.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Request for Quote (RFQ).
///
/// RFQs are sent to suppliers to request pricing and availability
/// for specific products or services.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct RfqModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable RFQ number.
    pub rfq_number: String,
    /// Supplier being asked to quote.
    pub supplier_id: Uuid,
    /// Status (draft, sent, quoted, expired, cancelled, awarded).
    pub status: String,
    /// RFQ issue date.
    pub issue_date: DateTime<Utc>,
    /// Deadline for quote submission.
    pub deadline: Option<DateTime<Utc>>,
    /// User who created the RFQ.
    pub created_by: Option<Uuid>,
    /// Notes or special instructions.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier quote.
///
/// Quotes are supplier responses to RFQs, providing pricing,
/// delivery terms, and other commercial conditions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct QuoteModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable quote number.
    pub quote_number: String,
    /// Related RFQ.
    pub rfq_id: Option<Uuid>,
    /// Supplier providing the quote.
    pub supplier_id: Uuid,
    /// Status (draft, submitted, under_review, approved, rejected, expired).
    pub status: String,
    /// Quote date.
    pub quote_date: DateTime<Utc>,
    /// Valid until date.
    pub valid_until: Option<DateTime<Utc>>,
    /// Total amount.
    pub total_amount: f64,
    /// Currency code.
    pub currency: String,
    /// Payment terms offered.
    pub payment_terms: Option<String>,
    /// Delivery lead time in days.
    pub lead_time_days: Option<i32>,
    /// User who reviewed the quote.
    pub reviewed_by: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a sales order.
///
/// Sales orders record customer orders for products or services,
/// tracking the order from placement through fulfillment and delivery.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SalesOrderModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable sales order number.
    pub so_number: String,
    /// Customer (represented as a supplier/customer record).
    pub customer_id: Uuid,
    /// Status (draft, confirmed, in_production, shipped, delivered, invoiced, cancelled).
    pub status: String,
    /// Order date.
    pub order_date: DateTime<Utc>,
    /// Requested delivery date.
    pub requested_date: Option<DateTime<Utc>>,
    /// Actual delivery date.
    pub delivered_date: Option<DateTime<Utc>>,
    /// Total amount of the order.
    pub total_amount: f64,
    /// Currency code.
    pub currency: String,
    /// Payment terms.
    pub payment_terms: Option<String>,
    /// Shipping address.
    pub shipping_address: Option<String>,
    /// User who created/manages the order.
    pub sales_rep_id: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── Operations / Continuous Improvement Models ─────────────────────────────

/// Database representation of a project.
///
/// Projects are structured initiatives with defined scope, timeline,
/// and resources. They can be NPI, continuous improvement, or other types.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ProjectModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable project number/code.
    pub project_number: String,
    /// Project name.
    pub name: String,
    /// Project description.
    pub description: Option<String>,
    /// Project type (npi, continuous_improvement, kaizen, capital, other).
    pub project_type: String,
    /// Status (idea, planned, in_progress, completed, on_hold, cancelled).
    pub status: String,
    /// Priority (low, medium, high, critical).
    pub priority: Option<String>,
    /// Project start date.
    pub start_date: Option<DateTime<Utc>>,
    /// Target completion date.
    pub target_date: Option<DateTime<Utc>>,
    /// Actual completion date.
    pub completed_at: Option<DateTime<Utc>>,
    /// Project manager user ID.
    pub project_manager_id: Option<Uuid>,
    /// Budget allocated to the project.
    pub budget_amount: Option<f64>,
    /// Currency for budget.
    pub currency: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a Kanban card.
///
/// Kanban cards visualize work items on boards, tracking their
/// progress through workflow columns/stages.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct KanbanCardModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Board identifier.
    pub board_id: Uuid,
    /// Card title.
    pub title: String,
    /// Card description.
    pub description: Option<String>,
    /// Current column/status.
    pub column: String,
    /// Position within the column.
    pub position: i32,
    /// Type of card (task, issue, improvement, standard_work).
    pub card_type: String,
    /// Priority (low, medium, high, critical).
    pub priority: Option<String>,
    /// Size or story points.
    pub size: Option<i32>,
    /// User assigned to the card.
    pub assignee_id: Option<Uuid>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Whether the card is blocked.
    pub is_blocked: bool,
    /// Reason for blocking.
    pub block_reason: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an issue.
///
/// Issues track problems, bugs, tasks, and action items across
/// projects, work orders, and continuous improvement activities.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct IssueModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable issue number.
    pub issue_number: String,
    /// Issue title.
    pub title: String,
    /// Detailed description.
    pub description: Option<String>,
    /// Type of issue (bug, task, improvement, question, risk, action_item).
    pub issue_type: String,
    /// Severity (minor, major, critical, blocker).
    pub severity: String,
    /// Status (open, assigned, in_progress, resolved, closed, rejected).
    pub status: String,
    /// Priority (low, medium, high, critical).
    pub priority: Option<String>,
    /// User who reported the issue.
    pub reporter_id: Uuid,
    /// User assigned to resolve the issue.
    pub assignee_id: Option<Uuid>,
    /// Related project, if applicable.
    pub project_id: Option<Uuid>,
    /// Related entity type (work_order, ncr, capa, etc.).
    pub source_type: Option<String>,
    /// Related entity ID.
    pub source_id: Option<Uuid>,
    /// Due date for resolution.
    pub due_date: Option<DateTime<Utc>>,
    /// Date when the issue was resolved.
    pub resolved_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an A3 problem-solving report.
///
/// A3 reports follow the Plan-Do-Check-Act (PDCA) cycle to
/// document and solve problems using a structured approach.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct A3Model {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable A3 number.
    pub a3_number: String,
    /// A3 report title.
    pub title: String,
    /// Type of A3 (problem_solving, proposal, status, kaizen).
    pub a3_type: String,
    /// Status (draft, in_progress, under_review, approved, implemented, closed).
    pub status: String,
    /// Priority (low, medium, high, critical).
    pub priority: Option<String>,
    /// Background / problem statement.
    pub background: Option<String>,
    /// Current condition description.
    pub current_condition: Option<String>,
    /// Root cause analysis.
    pub root_cause: Option<String>,
    /// Target condition / goal.
    pub target_condition: Option<String>,
    /// Action plan (serialized as JSON).
    pub action_plan: Option<serde_json::Value>,
    /// Follow-up / check results.
    pub follow_up: Option<String>,
    /// Outcome (effective, ineffective, inconclusive).
    pub outcome: Option<String>,
    /// User who owns the A3.
    pub owner_id: Option<Uuid>,
    /// Related NCR or issue, if applicable.
    pub source_id: Option<Uuid>,
    /// Source type (ncr, capa, issue, risk).
    pub source_type: Option<String>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Date closed.
    pub closed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a risk register entry.
///
/// Risk records capture identified risks, their assessment scores,
/// mitigation actions, and current status.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct RiskModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable risk number.
    pub risk_number: String,
    /// Title of the risk.
    pub title: String,
    /// Detailed description.
    pub description: Option<String>,
    /// Risk category (quality, safety, schedule, cost, compliance, operational, strategic).
    pub category: String,
    /// Severity (1-5 scale).
    pub severity: i32,
    /// Likelihood (1-5 scale).
    pub likelihood: i32,
    /// Risk score (severity * likelihood).
    pub risk_score: i32,
    /// Status (open, mitigating, closed, accepted).
    pub status: String,
    /// Type of entity this risk is associated with.
    pub entity_type: Option<String>,
    /// Entity ID this risk is associated with.
    pub entity_id: Option<Uuid>,
    /// Owner of this risk.
    pub owner_id: Option<Uuid>,
    /// Mitigation plan description.
    pub mitigation_plan: Option<String>,
    /// Date when risk was closed or realized.
    pub resolved_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an Andon event.
///
/// Andon is a visual notification system that signals issues
/// on the production line, including quality, safety, and maintenance alerts.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AndonModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable event number.
    pub event_number: String,
    /// Type of Andon (safety, quality, production, maintenance, material).
    pub andon_type: String,
    /// Severity (low, medium, high, critical).
    pub severity: String,
    /// Status (active, acknowledged, resolved, cancelled).
    pub status: String,
    /// Description of the issue.
    pub description: String,
    /// Station or work center where the event occurred.
    pub station_id: Option<Uuid>,
    /// Work order associated with the event.
    pub work_order_id: Option<Uuid>,
    /// User who triggered the Andon.
    pub triggered_by: Option<Uuid>,
    /// User who acknowledged the event.
    pub acknowledged_by: Option<Uuid>,
    /// Timestamp when acknowledged.
    pub acknowledged_at: Option<DateTime<Utc>>,
    /// User who resolved the event.
    pub resolved_by: Option<Uuid>,
    /// Resolution description.
    pub resolution: Option<String>,
    /// Downtime caused (minutes).
    pub downtime_minutes: Option<f64>,
    /// Timestamp when resolved.
    pub resolved_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

// ── AI / ML Models ─────────────────────────────────────────────────────────

/// Database representation of an anomaly detection event.
///
/// Anomaly detection records capture potential anomalies identified
/// by AI/ML models across different domains (quality, maintenance, etc.).
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AnomalyDetectionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Type of entity where anomaly was detected.
    pub entity_type: String,
    /// ID of the entity with the anomaly.
    pub entity_id: Uuid,
    /// Type of anomaly detected.
    pub anomaly_type: String,
    /// Confidence score (0.0 - 1.0).
    pub confidence: f64,
    /// Description of the anomaly.
    pub description: String,
    /// Status (new, reviewed, escalated, dismissed).
    pub status: String,
    /// Features or metrics that triggered the alert.
    pub features: Option<serde_json::Value>,
    /// User who reviewed the anomaly.
    pub reviewed_by: Option<Uuid>,
    /// Timestamp when reviewed.
    pub reviewed_at: Option<DateTime<Utc>>,
    /// Detected timestamp.
    pub detected_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of an ML model registry entry.
///
/// The model registry tracks ML model versions, their performance
/// metrics, and deployment status across the organization.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ModelRegistryModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Model name.
    pub model_name: String,
    /// Model version string.
    pub version: String,
    /// Model type (anomaly_detection, prediction, classification, recommendation).
    pub model_type: String,
    /// Status (development, testing, deployed, archived, deprecated).
    pub status: String,
    /// Model accuracy metric (0.0 - 1.0).
    pub accuracy: Option<f64>,
    /// Model precision metric (0.0 - 1.0).
    pub precision: Option<f64>,
    /// Model recall metric (0.0 - 1.0).
    pub recall: Option<f64>,
    /// F1 score (0.0 - 1.0).
    pub f1_score: Option<f64>,
    /// Size of the training dataset.
    pub dataset_size: Option<i64>,
    /// Path to the model artifact.
    pub artifact_path: Option<String>,
    /// Model configuration/hyperparameters (JSON).
    pub config: Option<serde_json::Value>,
    /// User who registered the model.
    pub created_by: Option<Uuid>,
    /// Timestamp when the model was deployed.
    pub deployed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a prediction record.
///
/// Predictions store the output of ML model inferences along
/// with the input context and confidence levels.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PredictionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Model that generated the prediction.
    pub model_id: Uuid,
    /// Type of prediction (quality, maintenance, demand, risk).
    pub prediction_type: String,
    /// Target entity type.
    pub entity_type: String,
    /// Target entity ID.
    pub entity_id: Uuid,
    /// Predicted value or category.
    pub predicted_value: String,
    /// Actual value (once known, for model evaluation).
    pub actual_value: Option<String>,
    /// Prediction confidence (0.0 - 1.0).
    pub confidence: f64,
    /// Input features used for prediction (JSON).
    pub input_features: Option<serde_json::Value>,
    /// Whether the prediction was accurate.
    pub is_accurate: Option<bool>,
    /// Timestamp when the prediction was made.
    pub predicted_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

// ── Common / Cross-Cutting Models ──────────────────────────────────────────

/// Database representation of an audit log entry.
///
/// Audit logs record all significant actions performed by users,
/// providing an immutable trail for compliance and security.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AuditLogModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// User who performed the action.
    pub user_id: Option<Uuid>,
    /// Action performed (e.g., "create", "update", "delete", "status_change").
    pub action: String,
    /// Type of resource affected.
    pub resource_type: String,
    /// ID of the resource affected.
    pub resource_id: Option<Uuid>,
    /// JSON details about the change.
    pub details: serde_json::Value,
    /// IP address of the user.
    pub ip_address: Option<String>,
    /// User agent string.
    pub user_agent: Option<String>,
    /// Timestamp of the action.
    pub created_at: DateTime<Utc>,
}

/// Database representation of the transactional outbox.
///
/// The outbox implements the transactional outbox pattern for reliable
/// event publishing. Events are written to the outbox in the same
/// transaction as the business data, then published asynchronously.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct EventOutboxModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Event type name.
    pub event_type: String,
    /// Event key for deduplication and routing.
    pub event_key: Option<String>,
    /// Event payload (JSON).
    pub payload: serde_json::Value,
    /// Event headers/metadata (JSON).
    pub headers: serde_json::Value,
    /// Correlation ID for tracing.
    pub correlation_id: Option<Uuid>,
    /// Tenant associated with this event.
    pub tenant_id: Option<Uuid>,
    /// Status (pending, published, failed).
    pub status: String,
    /// Number of publish attempts.
    pub retry_count: i32,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Timestamp when the event was published.
    pub published_at: Option<DateTime<Utc>>,
}

/// Database representation of a notification.
///
/// Notifications are messages sent to users about events,
/// alerts, or actions requiring their attention.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NotificationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// User who should receive the notification.
    pub user_id: Uuid,
    /// Notification type (alert, reminder, approval_request, mention, system).
    pub notification_type: String,
    /// Title of the notification.
    pub title: String,
    /// Body/content of the notification.
    pub body: String,
    /// Whether the notification has been read.
    pub is_read: bool,
    /// Timestamp when the notification was read.
    pub read_at: Option<DateTime<Utc>>,
    /// Link or action associated with the notification.
    pub action_url: Option<String>,
    /// Reference entity type.
    pub entity_type: Option<String>,
    /// Reference entity ID.
    pub entity_id: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of an attachment.
///
/// Attachments store file metadata for documents, images, and
/// other files linked to various domain entities.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AttachmentModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Original file name.
    pub file_name: String,
    /// File size in bytes.
    pub file_size: i64,
    /// MIME content type.
    pub content_type: String,
    /// Storage path or URL.
    pub storage_path: String,
    /// Type of entity this attachment is linked to.
    pub entity_type: String,
    /// ID of the entity this attachment is linked to.
    pub entity_id: Uuid,
    /// User who uploaded the attachment.
    pub uploaded_by: Option<Uuid>,
    /// Description or notes about the attachment.
    pub description: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

// ── Chat / Conversational AI Models ───────────────────────────────────────

/// Database representation of a chat conversation.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ChatConversationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// User who owns this conversation.
    pub user_id: Uuid,
    /// Optional title for the conversation.
    pub title: String,
    /// Whether the conversation is still active.
    pub is_active: bool,
    /// Additional metadata (JSON).
    pub metadata: serde_json::Value,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a single chat message.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ChatMessageModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Conversation this message belongs to.
    pub conversation_id: Uuid,
    /// Role of the sender (user, assistant, system).
    pub role: String,
    /// Message content.
    pub content: String,
    /// Additional metadata (JSON).
    pub metadata: serde_json::Value,
    /// Timestamp when the message was created.
    pub created_at: DateTime<Utc>,
}

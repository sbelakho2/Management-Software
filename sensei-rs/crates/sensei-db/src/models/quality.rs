//! Quality management models for non-conformances, inspections, gauges, and QMS.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of a non-conformance.
///
/// Non-conformances track instances where products, processes, or systems
/// fail to meet specified requirements, with full disposition tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NonConformanceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable NC number.
    pub nc_number: String,
    /// Type of non-conformance (internal, external, supplier, customer, process).
    pub nc_type: String,
    /// Severity (minor, major, critical).
    pub severity: String,
    /// Status (open, under_investigation, dispositioned, in_progress, closed, rejected).
    pub status: String,
    /// Disposition decision (use_as_is, rework, repair, scrap, return).
    pub disposition: Option<String>,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Work order reference.
    pub work_order_id: Option<Uuid>,
    /// User who detected the NC.
    pub detected_by: Option<Uuid>,
    /// Detection timestamp.
    pub detected_at: Option<DateTime<Utc>>,
    /// Description of the non-conformance.
    pub description: String,
    /// Root cause analysis.
    pub root_cause: Option<String>,
    /// Corrective action taken.
    pub corrective_action: Option<String>,
    /// Resolution timestamp.
    pub resolved_at: Option<DateTime<Utc>>,
    /// User who closed the NC.
    pub closed_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a CAPA action.
///
/// Individual corrective, preventive, or containment actions within a CAPA.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CapaActionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent CAPA.
    pub capa_id: Uuid,
    /// Action type (corrective, preventive, containment).
    pub action_type: String,
    /// Status (pending, in_progress, completed, verified, overdue).
    pub status: String,
    /// Description of the action.
    pub description: String,
    /// User assigned to execute the action.
    pub assigned_to: Option<Uuid>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Completion timestamp.
    pub completed_at: Option<DateTime<Utc>>,
    /// User who verified the action.
    pub verified_by: Option<Uuid>,
    /// Verification timestamp.
    pub verified_at: Option<DateTime<Utc>>,
    /// Verification notes.
    pub verification_notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an inspection plan.
///
/// Plans define the inspection requirements for products, including
/// type, frequency, and sample size.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InspectionPlanModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product being inspected.
    pub product_id: Uuid,
    /// Human-readable plan number.
    pub plan_number: String,
    /// Plan type (incoming, in_process, final, fai, aql).
    pub plan_type: String,
    /// Plan name.
    pub name: String,
    /// Inspection frequency.
    pub frequency: Option<String>,
    /// Sample size per inspection.
    pub sample_size: i32,
    /// Status (draft, active, inactive).
    pub status: String,
    /// Description.
    pub description: Option<String>,
    /// User who created the plan.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an inspection characteristic.
///
/// Characteristics define measurable attributes within an inspection plan,
/// including specification limits and criticality.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InspectionCharacteristicModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent inspection plan.
    pub plan_id: Uuid,
    /// Sequence within the plan.
    pub sequence: i32,
    /// Characteristic name.
    pub name: String,
    /// Type (variable, attribute, visual).
    pub characteristic_type: String,
    /// Nominal/target value.
    pub nominal: Option<f64>,
    /// Upper specification limit.
    pub upper_spec: Option<f64>,
    /// Lower specification limit.
    pub lower_spec: Option<f64>,
    /// Unit of measurement.
    pub unit: Option<String>,
    /// Criticality (critical, major, minor).
    pub criticality: String,
    /// Inspection method.
    pub inspection_method: Option<String>,
    /// Gauge ID.
    pub gauge_id: Option<Uuid>,
    /// Whether this characteristic is required.
    pub required: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an inspection record.
///
/// Records capture individual inspections performed against plans,
/// tracking results and inspector information.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InspectionRecordModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Inspection plan used.
    pub plan_id: Uuid,
    /// Work order reference.
    pub work_order_id: Option<Uuid>,
    /// Lot number.
    pub lot_number: Option<String>,
    /// Sample size inspected.
    pub sample_size: i32,
    /// Result (pending, pass, fail, conditional).
    pub result: String,
    /// Inspector user ID.
    pub inspector_id: Option<Uuid>,
    /// Inspection timestamp.
    pub inspected_at: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an inspection measurement.
///
/// Individual measurements taken during an inspection, linked to
/// specific characteristics within the plan.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct InspectionMeasurementModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent inspection record.
    pub record_id: Uuid,
    /// Characteristic being measured.
    pub characteristic_id: Uuid,
    /// Measured value.
    pub measured_value: f64,
    /// Pass/fail result.
    pub pass_fail: bool,
    /// Deviation from nominal.
    pub deviation: Option<f64>,
    /// Notes.
    pub notes: Option<String>,
    /// Measurement timestamp.
    pub measured_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of a gauge/measurement instrument.
///
/// Gauges track measurement instruments including calibration
/// status, location, and specifications.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct GaugeModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable gauge ID.
    pub gauge_id: String,
    /// Gauge name.
    pub name: String,
    /// Gauge type (caliper, micrometer, height_gauge, cmm, etc.).
    pub gauge_type: String,
    /// Status (active, out_of_calibration, retired, lost).
    pub status: String,
    /// Physical location.
    pub location: Option<String>,
    /// Manufacturer.
    pub manufacturer: Option<String>,
    /// Model number.
    pub model: Option<String>,
    /// Serial number.
    pub serial_number: Option<String>,
    /// Measurement resolution.
    pub resolution: Option<f64>,
    /// Calibration interval in days.
    pub calibration_interval: i32,
    /// Calibration interval unit (days, weeks, months).
    pub calibration_interval_unit: String,
    /// Last calibration date.
    pub last_calibration_date: Option<DateTime<Utc>>,
    /// Next calibration due date.
    pub next_calibration_due: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a calibration event.
///
/// Calibration events record individual calibration activities
/// for gauges, including results and certificates.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CalibrationEventModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Gauge being calibrated.
    pub gauge_id: Uuid,
    /// Calibration date.
    pub calibration_date: DateTime<Utc>,
    /// Next calibration due date.
    pub next_due: DateTime<Utc>,
    /// Result (pass, fail, conditional, as_found_pass, as_found_fail).
    pub result: String,
    /// User who performed the calibration.
    pub performed_by: Option<Uuid>,
    /// Calibration vendor.
    pub vendor: Option<String>,
    /// Certificate number.
    pub certificate_number: Option<String>,
    /// Measurement uncertainty.
    pub uncertainty: Option<f64>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of an MSA measurement.
///
/// Individual measurements within a Measurement Systems Analysis study,
/// capturing operator, part, trial, and measured value.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct MsaMeasurementModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent MSA study.
    pub study_id: Uuid,
    /// Operator user ID.
    pub operator_id: Option<Uuid>,
    /// Part number in the study.
    pub part_number: i32,
    /// Trial number.
    pub trial_number: i32,
    /// Measured value.
    pub measured_value: f64,
    /// Notes.
    pub notes: Option<String>,
    /// Measurement timestamp.
    pub measured_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of MSA study results.
///
/// Computed results from a Measurement Systems Analysis, including
/// GRR percentage, distinct categories, and variation components.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct MsaResultModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent MSA study.
    pub study_id: Uuid,
    /// Gauge R&R as percentage of total variation.
    pub grr_percent: f64,
    /// GRR as percentage of contribution.
    pub grr_contribution: f64,
    /// Number of distinct categories.
    pub ndc: i32,
    /// Repeatability (equipment variation).
    pub repeatability: f64,
    /// Reproducibility (appraiser variation).
    pub reproducibility: f64,
    /// Part variation.
    pub part_variation: f64,
    /// Total variation.
    pub total_variation: f64,
    /// Computation timestamp.
    pub computed_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of a QMS document.
///
/// Controlled documents within the Quality Management System,
/// including policies, procedures, work instructions, and forms.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct QmsDocumentModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Document number.
    pub document_number: String,
    /// Document title.
    pub title: String,
    /// Status (draft, under_review, approved, published, obsolete).
    pub status: String,
    /// Category (policy, procedure, work_instruction, form, standard, manual, record, other).
    pub category: String,
    /// Version string.
    pub version: String,
    /// Effective date.
    pub effective_date: Option<DateTime<Utc>>,
    /// Next review date.
    pub review_date: Option<DateTime<Utc>>,
    /// Document owner.
    pub owner_id: Option<Uuid>,
    /// Approving user.
    pub approved_by: Option<Uuid>,
    /// Description.
    pub description: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a quality audit.
///
/// Quality audits assess compliance with QMS requirements, standards,
/// and procedures across the organization.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct QualityAuditModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable audit number.
    pub audit_number: String,
    /// Audit type (internal, external, supplier, regulatory, process, product).
    pub audit_type: String,
    /// Status (planned, scheduled, in_progress, completed, closed, cancelled).
    pub status: String,
    /// Scheduled date.
    pub scheduled_date: Option<DateTime<Utc>>,
    /// Completion date.
    pub completed_date: Option<DateTime<Utc>>,
    /// Lead auditor user ID.
    pub auditor_id: Option<Uuid>,
    /// Audit scope description.
    pub scope: String,
    /// Summary of findings.
    pub findings_summary: Option<String>,
    /// Audit score.
    pub score: Option<f64>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a first article inspection.
///
/// FAI records document the inspection of first production articles
/// for new or changed products.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct FirstArticleInspectionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable FAI number.
    pub fai_number: String,
    /// Product being inspected.
    pub product_id: Uuid,
    /// Work order reference.
    pub work_order_id: Option<Uuid>,
    /// Status (planned, in_progress, completed, failed).
    pub status: String,
    /// Inspector user ID.
    pub performed_by: Option<Uuid>,
    /// Inspection timestamp.
    pub performed_at: Option<DateTime<Utc>>,
    /// Result (pending, pass, fail, conditional).
    pub result: String,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a self-inspection.
///
/// Self-inspections are performed by operators during production,
/// recording characteristics and results.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SelfInspectionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product being inspected.
    pub product_id: Uuid,
    /// Work order reference.
    pub work_order_id: Option<Uuid>,
    /// Operator user ID.
    pub operator_id: Option<Uuid>,
    /// Inspection timestamp.
    pub inspected_at: DateTime<Utc>,
    /// Result (pending, pass, fail, conditional).
    pub result: String,
    /// Characteristics data (JSON array).
    pub characteristics: serde_json::Value,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a customer complaint.
///
/// Customer complaints track issues reported by customers,
/// from receipt through resolution.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct CustomerComplaintModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable complaint number.
    pub complaint_number: String,
    /// Customer account reference.
    pub account_id: Option<Uuid>,
    /// Contact person reference.
    pub contact_id: Option<Uuid>,
    /// Status (open, acknowledged, investigating, action_defined, in_progress, resolved, closed).
    pub status: String,
    /// Severity (minor, major, critical).
    pub severity: String,
    /// Complaint type (quality, delivery, service, documentation, packaging, other).
    pub complaint_type: String,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Description of the complaint.
    pub description: String,
    /// Resolution description.
    pub resolution: Option<String>,
    /// Receipt timestamp.
    pub received_at: DateTime<Utc>,
    /// Resolution timestamp.
    pub resolved_at: Option<DateTime<Utc>>,
    /// User who resolved the complaint.
    pub resolved_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an 8D report.
///
/// Eight Disciplines reports provide structured problem-solving
/// linked to customer complaints.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct EightDReportModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable report number.
    pub report_number: String,
    /// Parent customer complaint.
    pub complaint_id: Uuid,
    /// Status (open, in_progress, completed, closed).
    pub status: String,
    /// D1 - Team composition (JSON).
    pub d1_team: serde_json::Value,
    /// D2 - Problem description.
    pub d2_problem: Option<String>,
    /// D3 - Interim containment actions.
    pub d3_interim: Option<String>,
    /// D4 - Root cause analysis.
    pub d4_root_cause: Option<String>,
    /// D5 - Corrective actions.
    pub d5_corrective: Option<String>,
    /// D6 - Implementation actions.
    pub d6_implement: Option<String>,
    /// D7 - Preventive actions.
    pub d7_preventive: Option<String>,
    /// D8 - Closure data (JSON).
    pub d8_closure: serde_json::Value,
    /// Report owner.
    pub owner_id: Option<Uuid>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Closure timestamp.
    pub closed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a management review.
///
/// Management reviews are periodic QMS reviews assessing system
/// performance, findings, and improvement actions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ManagementReviewModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable review number.
    pub review_number: String,
    /// Review date.
    pub review_date: DateTime<Utc>,
    /// Status (planned, in_progress, completed).
    pub status: String,
    /// Review scope.
    pub scope: String,
    /// Findings from the review.
    pub findings: Option<String>,
    /// Actions decided.
    pub actions: Option<String>,
    /// Next scheduled review date.
    pub next_review_date: Option<DateTime<Utc>>,
    /// Chairperson user ID.
    pub chairperson_id: Option<Uuid>,
    /// Participant user IDs.
    pub participants: Option<Vec<Uuid>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a process capability study.
///
/// Statistical process capability studies calculate Cp, Cpk, Pp, Ppk
/// indices for manufacturing process characterization.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ProcessCapabilityStudyModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product being studied.
    pub product_id: Uuid,
    /// Characteristic being measured.
    pub characteristic: String,
    /// Process capability index.
    pub cp: f64,
    /// Process capability index (adjusted for mean shift).
    pub cpk: f64,
    /// Process performance index.
    pub pp: f64,
    /// Process performance index (adjusted for mean shift).
    pub ppk: f64,
    /// Sample size.
    pub sample_size: i32,
    /// Sample mean.
    pub mean: f64,
    /// Sample standard deviation.
    pub stddev: f64,
    /// Upper specification limit.
    pub usl: Option<f64>,
    /// Lower specification limit.
    pub lsl: Option<f64>,
    /// Target value.
    pub target: Option<f64>,
    /// User who performed the study.
    pub performed_by: Option<Uuid>,
    /// Study timestamp.
    pub performed_at: DateTime<Utc>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a control plan.
///
/// Control plans define inspection and monitoring requirements
/// for production processes.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ControlPlanModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product reference.
    pub product_id: Uuid,
    /// Plan name.
    pub name: String,
    /// Human-readable plan number.
    pub plan_number: String,
    /// Status (draft, active, inactive).
    pub status: String,
    /// Version string.
    pub version: String,
    /// Characteristics data (JSON array).
    pub characteristics: serde_json::Value,
    /// User who created the plan.
    pub created_by: Option<Uuid>,
    /// User who approved the plan.
    pub approved_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a PFMEA (Process Failure Mode and Effects Analysis) entry.
///
/// PFMEA entries identify potential failure modes in manufacturing processes
/// and assess risk using severity, occurrence, and detection ratings.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PfmeaLiteModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product reference.
    pub product_id: Uuid,
    /// Process step name.
    pub process_step: String,
    /// Potential failure mode.
    pub failure_mode: String,
    /// Effect of failure.
    pub effect: String,
    /// Severity rating (1-10).
    pub severity: i32,
    /// Occurrence rating (1-10).
    pub occurrence: i32,
    /// Detection rating (1-10).
    pub detection: i32,
    /// Risk Priority Number (severity * occurrence * detection).
    pub rpn: i32,
    /// Recommended action.
    pub recommended_action: Option<String>,
    /// Responsible user.
    pub responsible: Option<Uuid>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Status (open, in_progress, completed, closed).
    pub status: String,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an NPI (New Product Introduction) project.
///
/// NPI projects track new products through stage-gate phases
/// from intake through start of production.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NpiProjectModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable project number.
    pub project_number: String,
    /// Project name.
    pub name: String,
    /// Status (intake, dfm, prototype, pilot, sop, completed, cancelled).
    pub status: String,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Current stage.
    pub stage: String,
    /// Target launch date.
    pub target_launch: Option<DateTime<Utc>>,
    /// Project owner.
    pub owner_id: Option<Uuid>,
    /// Description.
    pub description: Option<String>,
    /// Budget amount.
    pub budget: Option<f64>,
    /// Actual cost.
    pub actual_cost: Option<f64>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

//! Quality domain models, enums, and DTOs.
//!
//! Ported from the Python `sensei.services.quality` module hierarchy,
//! covering: CAPA workflow, QMS, NPI risk register, audit evidence,
//! audit trail timeline, change control, inspections, MSA, SPC, etc.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// CAPA Workflow Enums & Models
// ---------------------------------------------------------------------------

/// Types of non-conformance.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NcType {
    Product,
    Process,
    System,
    Documentation,
    Supplier,
    Safety,
    Environmental,
    Regulatory,
    Service,
    CustomerComplaint,
    Other,
}

/// Severity levels for non-conformance.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NcSeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// Types of CAPA.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapaType {
    Corrective,
    Preventive,
    Improvement,
}

/// Extended CAPA status matching the Python workflow.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapaStatusEx {
    Draft,
    PendingApproval,
    Open,
    RootCauseAnalysis,
    ActionPlanning,
    Implementing,
    Verification,
    EffectivenessCheck,
    PendingClosure,
    Closed,
    Rejected,
    Cancelled,
}

/// CAPA priority levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapaPriority {
    Low,
    Medium,
    High,
    Emergency,
}

/// Status of a corrective/preventive action item.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActionStatus {
    Open,
    InProgress,
    Completed,
    Verified,
    Closed,
    Cancelled,
}

/// Types of closure gates in the CAPA workflow.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClosureGateType {
    NcConfirmed,
    RootCauseIdentified,
    RootCauseVerified,
    ActionPlanned,
    ActionsImplemented,
    ActionsVerified,
    EffectivenessCheck,
    DocumentationComplete,
    TrainingCompleted,
    RegulatoryCompliance,
    ManagementApproval,
}

/// Types of entity links for CAPA linking.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LinkType {
    A3Report,
    StandardWork,
    TrainingRecord,
    Ncr,
    AuditFinding,
    Complaint,
    Risk,
    ChangeRequest,
    SupplierScar,
}

/// Lifecycle status of a non-conformance report.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum NcrStatus {
    /// NCR created, investigation not started.
    #[default]
    Open,
    /// Root cause analysis in progress or completed.
    UnderInvestigation,
    /// Disposition decided; corrective/preventive actions defined.
    ActionDefined,
    /// Corrective actions are being implemented.
    InProgress,
    /// NCR closed after disposition and completeness validation.
    Closed,
    /// NCR cancelled / withdrawn.
    Cancelled,
}

impl NcrStatus {
    /// Snake-case name used by API filters and JSON payloads.
    pub fn as_str(&self) -> &'static str {
        match self {
            NcrStatus::Open => "open",
            NcrStatus::UnderInvestigation => "under_investigation",
            NcrStatus::ActionDefined => "action_defined",
            NcrStatus::InProgress => "in_progress",
            NcrStatus::Closed => "closed",
            NcrStatus::Cancelled => "cancelled",
        }
    }
}

/// Case- and separator-insensitive comparison between an API filter value and
/// an enum's canonical name (accepts `under_investigation`, `UnderInvestigation`,
/// `UNDERINVESTIGATION`, ...).
pub fn enum_name_matches(filter: &str, canonical: &str) -> bool {
    fn normalize(s: &str) -> String {
        s.chars()
            .filter(|c| *c != '_' && !c.is_whitespace())
            .flat_map(char::to_lowercase)
            .collect()
    }
    normalize(filter) == normalize(canonical)
}

/// A non-conformance record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NonConformance {
    pub id: Uuid,
    pub nc_number: String,
    pub title: String,
    pub description: String,
    pub nc_type: NcType,
    pub severity: NcSeverity,
    pub product_id: Option<Uuid>,
    pub process_id: Option<Uuid>,
    pub defect_code: Option<String>,
    pub detected_by: Option<Uuid>,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_recurrence: bool,
    /// Lifecycle status (defaults to `Open` for rows written before this
    /// field existed).
    #[serde(default)]
    pub status: NcrStatus,
    /// Originating source (e.g. inspection, audit, customer complaint).
    #[serde(default)]
    pub source: Option<String>,
    /// Root cause determined during investigation.
    #[serde(default)]
    pub root_cause: Option<String>,
    /// Root cause category (e.g. machine, method, material).
    #[serde(default)]
    pub root_cause_type: Option<String>,
    /// Analysis method used (5-Why, Fishbone, etc.).
    #[serde(default)]
    pub analysis_method: Option<String>,
    /// Disposition decided for the non-conforming material.
    #[serde(default)]
    pub disposition: Option<String>,
    /// When the NCR was closed.
    #[serde(default)]
    pub closed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Root cause analysis record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RootCauseAnalysis {
    pub id: Uuid,
    pub capa_id: Uuid,
    pub description: String,
    pub root_cause_type: String,
    pub analysis_method: String,
    pub contributors: Vec<String>,
    pub evidence: Vec<String>,
    pub verified_by: Option<Uuid>,
    pub verified_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// A corrective or preventive action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorrectiveAction {
    pub id: Uuid,
    pub capa_id: Uuid,
    pub description: String,
    pub action_type: String,
    pub owner_id: Option<Uuid>,
    pub status: ActionStatus,
    pub due_date: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub verified_by: Option<Uuid>,
    pub verified_at: Option<DateTime<Utc>>,
    pub verification_notes: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A closure gate in the CAPA workflow.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClosureGate {
    pub id: Uuid,
    pub capa_id: Uuid,
    pub gate_type: ClosureGateType,
    pub description: String,
    pub is_mandatory: bool,
    pub passed: bool,
    pub passed_by: Option<Uuid>,
    pub passed_at: Option<DateTime<Utc>>,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// An entity linked to a CAPA.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntityLink {
    pub id: Uuid,
    pub capa_id: Uuid,
    pub link_type: LinkType,
    pub entity_id: Uuid,
    pub entity_type: String,
    pub description: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// An effectiveness check record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectivenessCheck {
    pub id: Uuid,
    pub capa_id: Uuid,
    pub check_method: String,
    pub results: String,
    pub is_effective: bool,
    pub checked_by: Option<Uuid>,
    pub checked_at: Option<DateTime<Utc>>,
    pub follow_up_needed: bool,
    pub follow_up_actions: Vec<String>,
    pub created_at: DateTime<Utc>,
}

/// Extended CAPA info beyond the core entity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapaExtended {
    pub id: Uuid,
    pub capa_number: String,
    pub title: String,
    pub description: String,
    pub nc_ids: Vec<Uuid>,
    pub capa_type: CapaType,
    pub priority: CapaPriority,
    pub status: CapaStatusEx,
    pub root_cause_analyses: Vec<RootCauseAnalysis>,
    pub actions: Vec<CorrectiveAction>,
    pub closure_gates: Vec<ClosureGate>,
    pub effectiveness_checks: Vec<EffectivenessCheck>,
    pub entity_links: Vec<EntityLink>,
    pub owner_id: Option<Uuid>,
    pub due_date: Option<DateTime<Utc>>,
    pub closed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Configuration for CAPA workflow behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapaConfig {
    pub auto_create_capa: bool,
    pub recurrence_threshold: u32,
    pub recurrence_period_days: u32,
    pub require_effectiveness_check: bool,
    pub require_closure_gates: bool,
    pub default_priority: CapaPriority,
    pub auto_escalation_days: Option<u32>,
}

impl Default for CapaConfig {
    fn default() -> Self {
        Self {
            auto_create_capa: true,
            recurrence_threshold: 2,
            recurrence_period_days: 90,
            require_effectiveness_check: true,
            require_closure_gates: true,
            default_priority: CapaPriority::Medium,
            auto_escalation_days: Some(30),
        }
    }
}

/// Result of a closure readiness check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClosureCheckResult {
    pub is_ready: bool,
    pub passed_gates: Vec<ClosureGateType>,
    pub failed_gates: Vec<ClosureGateType>,
    pub pending_gates: Vec<ClosureGateType>,
    pub missing_items: Vec<String>,
    pub warnings: Vec<String>,
}

/// Result of a recurrence check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurrenceCheckResult {
    pub is_recurrence: bool,
    pub previous_nc_count: u32,
    pub previous_nc_ids: Vec<Uuid>,
    pub period_days: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapaCreationResult {
    pub capa: CapaExtended,
    pub auto_created: bool,
    pub creation_reason: String,
}

/// Default closure gates for CAPA workflow.
pub const DEFAULT_CLOSURE_GATES: &[(ClosureGateType, &str, bool)] = &[
    (
        ClosureGateType::NcConfirmed,
        "Non-conformance confirmed",
        true,
    ),
    (
        ClosureGateType::RootCauseIdentified,
        "Root cause identified",
        true,
    ),
    (
        ClosureGateType::RootCauseVerified,
        "Root cause verified",
        true,
    ),
    (
        ClosureGateType::ActionPlanned,
        "Corrective action planned",
        true,
    ),
    (
        ClosureGateType::ActionsImplemented,
        "Actions implemented",
        true,
    ),
    (ClosureGateType::ActionsVerified, "Actions verified", true),
    (
        ClosureGateType::EffectivenessCheck,
        "Effectiveness verified",
        true,
    ),
    (
        ClosureGateType::DocumentationComplete,
        "Documentation complete",
        false,
    ),
    (
        ClosureGateType::TrainingCompleted,
        "Training completed",
        false,
    ),
    (
        ClosureGateType::RegulatoryCompliance,
        "Regulatory compliance",
        true,
    ),
    (
        ClosureGateType::ManagementApproval,
        "Management approval",
        true,
    ),
];

// ---------------------------------------------------------------------------
// QMS / Supplier / Audit Models
// ---------------------------------------------------------------------------

/// QMS document types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum QmsDocumentType {
    QualityPolicy,
    Procedure,
    WorkInstruction,
    Form,
    Template,
    Specification,
    Standard,
    Manual,
    Record,
    Other,
}

/// QMS document status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum QmsDocumentStatus {
    Draft,
    UnderReview,
    Approved,
    Published,
    Superseded,
    Archived,
}

/// Roles for electronic signatures.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignatureRole {
    Author,
    Reviewer,
    Approver,
    QualityManager,
    DocumentControl,
}

/// SCAR workflow status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ScarStatus {
    Open,
    SentToSupplier,
    ContainmentInProgress,
    RootCauseAnalysis,
    CorrectiveActionDefined,
    VerificationInProgress,
    Closed,
    Rejected,
}

/// Audit types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditType {
    Internal,
    External,
    Supplier,
    Regulatory,
    Certification,
    Layered,
    Process,
    Product,
    System,
}

/// Audit status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditStatus {
    Planned,
    Scheduled,
    InProgress,
    Completed,
    Closed,
    Cancelled,
}

/// Finding severity levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FindingSeverity {
    Observation,
    MinorNc,
    MajorNc,
    CriticalNc,
}

/// Finding status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FindingStatus {
    Open,
    Accepted,
    InProgress,
    Implemented,
    Verified,
    Closed,
    Waived,
}

/// Risk status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskStatus {
    Open,
    Mitigating,
    Closed,
    Accepted,
}

/// Mitigation status for QMS risks.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MitigationStatus {
    Planned,
    InProgress,
    Completed,
    Overdue,
    Cancelled,
}

/// Gauge/equipment status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GaugeStatus {
    Active,
    Inactive,
    UnderCalibration,
    OutOfService,
    Retired,
}

/// Calibration status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CalibrationStatus {
    Scheduled,
    InProgress,
    Completed,
    Overdue,
    Failed,
}

/// Complaint status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ComplaintStatus {
    Open,
    UnderInvestigation,
    ContainmentInProgress,
    RootCauseAnalysis,
    CorrectiveAction,
    Verified,
    Closed,
    Rejected,
}

/// KPI trend direction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum KpiTrend {
    Improving,
    Stable,
    Declining,
    NotAvailable,
}

/// An electronic signature record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ElectronicSignature {
    pub user_id: Uuid,
    pub role: SignatureRole,
    pub signed_at: DateTime<Utc>,
    pub signature: String,
    pub comments: Option<String>,
}

/// A QMS document revision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QmsDocumentRevision {
    pub id: Uuid,
    pub document_id: Uuid,
    pub version: String,
    pub title: String,
    pub content: String,
    pub change_summary: String,
    pub status: QmsDocumentStatus,
    pub effective_date: Option<DateTime<Utc>>,
    pub signatures: Vec<ElectronicSignature>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A QMS document.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QmsDocument {
    pub id: Uuid,
    pub document_number: String,
    pub document_type: QmsDocumentType,
    pub current_revision: Option<QmsDocumentRevision>,
    pub revisions: Vec<QmsDocumentRevision>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// An external document reference.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalDocument {
    pub id: Uuid,
    pub title: String,
    pub document_number: String,
    pub version: String,
    pub source: String,
    pub review_by: Option<DateTime<Utc>>,
    pub superseded_by: Option<Uuid>,
    pub created_at: DateTime<Utc>,
}

/// A KPI value record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiValue {
    pub id: Uuid,
    pub kpi_key: String,
    pub value: f64,
    pub unit: Option<String>,
    pub recorded_at: DateTime<Utc>,
    pub notes: Option<String>,
}

/// A quality objective.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityObjective {
    pub id: Uuid,
    pub title: String,
    pub description: String,
    pub target_value: f64,
    pub target_date: Option<DateTime<Utc>>,
    pub is_achieved: bool,
    pub created_at: DateTime<Utc>,
}

/// Supplier profile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupplierProfile {
    pub id: Uuid,
    pub supplier_id: String,
    pub name: String,
    pub tier: String,
    pub status: String,
    pub created_at: DateTime<Utc>,
}

/// Supplier periodic statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupplierPeriodStats {
    pub period_key: String,
    pub units_received: u64,
    pub defects_found: u64,
    pub lots_received: u64,
    pub lots_rejected: u64,
    pub on_time_deliveries: u64,
    pub late_deliveries: u64,
    pub total_copq: f64,
}

impl SupplierPeriodStats {
    /// Calculate parts per million defect rate.
    pub fn ppm(&self) -> f64 {
        if self.units_received == 0 {
            return 0.0;
        }
        (self.defects_found as f64 / self.units_received as f64) * 1_000_000.0
    }

    /// Calculate on-time delivery percentage.
    pub fn otd_percent(&self) -> f64 {
        let total = self.on_time_deliveries + self.late_deliveries;
        if total == 0 {
            return 100.0;
        }
        (self.on_time_deliveries as f64 / total as f64) * 100.0
    }
}

/// Supplier scorecard.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupplierScorecard {
    pub supplier_id: String,
    pub period_key: String,
    pub ppm_score: f64,
    pub otd_score: f64,
    pub quality_score: f64,
    pub delivery_score: f64,
    pub copq_score: f64,
    pub overall_score: f64,
    pub tier: String,
    pub computed_at: DateTime<Utc>,
}

/// Supplier Corrective Action Request (SCAR).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scar {
    pub id: Uuid,
    pub scar_number: String,
    pub supplier_id: String,
    pub title: String,
    pub description: String,
    pub status: ScarStatus,
    pub severity: FindingSeverity,
    pub containment_action: Option<String>,
    pub root_cause: Option<String>,
    pub corrective_action: Option<String>,
    pub verification_notes: Option<String>,
    pub due_date: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Audit checklist item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditChecklistItem {
    pub id: Uuid,
    pub audit_id: Uuid,
    pub question: String,
    pub expected_evidence: String,
    pub is_conforming: Option<bool>,
    pub observations: Option<String>,
}

/// An audit record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Audit {
    pub id: Uuid,
    pub audit_number: String,
    pub audit_type: AuditType,
    pub status: AuditStatus,
    pub title: String,
    pub scope: String,
    pub area: String,
    pub auditor_id: Option<Uuid>,
    pub lead_auditor_id: Option<Uuid>,
    pub scheduled_date: Option<DateTime<Utc>>,
    pub start_date: Option<DateTime<Utc>>,
    pub completion_date: Option<DateTime<Utc>>,
    pub checklist_items: Vec<AuditChecklistItem>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// An audit finding.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditFinding {
    pub id: Uuid,
    pub audit_id: Uuid,
    pub finding_number: String,
    pub severity: FindingSeverity,
    pub status: FindingStatus,
    pub description: String,
    pub clause: Option<String>,
    pub area: Option<String>,
    pub implementation_notes: Option<String>,
    pub verified_by: Option<Uuid>,
    pub verification_notes: Option<String>,
    pub due_date: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Risk and opportunity record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskOpportunity {
    pub id: Uuid,
    pub title: String,
    pub description: String,
    pub risk_type: String,
    pub likelihood: u32,
    pub impact: u32,
    pub risk_score: u32,
    pub status: RiskStatus,
    pub created_at: DateTime<Utc>,
}

/// QMS mitigation action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MitigationActionQms {
    pub id: Uuid,
    pub risk_id: Uuid,
    pub description: String,
    pub owner: String,
    pub status: MitigationStatus,
    pub due_by: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// Gauge/measurement equipment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gauge {
    pub id: Uuid,
    pub gauge_number: String,
    pub name: String,
    pub gauge_type: String,
    pub range: Option<String>,
    pub accuracy: Option<String>,
    pub location: Option<String>,
    pub status: GaugeStatus,
    pub calibration_frequency_days: u32,
    pub last_calibrated: Option<DateTime<Utc>>,
    pub next_calibration_due: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// A calibration event for a gauge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationEvent {
    pub id: Uuid,
    pub gauge_id: Uuid,
    pub status: CalibrationStatus,
    pub scheduled_for: Option<DateTime<Utc>>,
    pub calibrated_at: Option<DateTime<Utc>>,
    pub calibrated_by: Option<Uuid>,
    pub result: Option<String>,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// A measurement record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeasurementRecord {
    pub id: Uuid,
    pub gauge_id: Uuid,
    pub lot_id: String,
    pub characteristic: String,
    pub value: f64,
    pub measured_at: DateTime<Utc>,
}

/// A control plan checkpoint.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlPlanCheckpoint {
    pub id: Uuid,
    pub control_plan_id: Uuid,
    pub process_step: String,
    pub characteristic: String,
    pub specification: String,
    pub method: String,
    pub frequency: String,
    pub sample_size: u32,
    pub reaction_plan: Option<String>,
    pub pfmea_link: Option<Uuid>,
    pub created_at: DateTime<Utc>,
}

/// A control plan.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlPlan {
    pub id: Uuid,
    pub name: String,
    pub product_id: Option<Uuid>,
    pub process_id: Option<Uuid>,
    pub checkpoints: Vec<ControlPlanCheckpoint>,
    pub revision: String,
    pub created_at: DateTime<Utc>,
}

/// A PFMEA step/row.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PfmeaStep {
    pub id: Uuid,
    pub pfmea_id: Uuid,
    pub process_step: String,
    pub potential_failure_mode: String,
    pub potential_effects: String,
    pub severity: u32,
    pub potential_causes: String,
    pub occurrence: u32,
    pub current_controls: String,
    pub detection: u32,
    pub rpn: u32,
    pub recommended_actions: Option<String>,
    pub created_at: DateTime<Utc>,
}

impl PfmeaStep {
    /// Calculate RPN (Risk Priority Number) = Severity × Occurrence × Detection.
    pub fn calculate_rpn(severity: u32, occurrence: u32, detection: u32) -> u32 {
        severity * occurrence * detection
    }
}

/// A lightweight PFMEA.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PfmeaLite {
    pub id: Uuid,
    pub name: String,
    pub product_id: Option<Uuid>,
    pub process_id: Option<Uuid>,
    pub steps: Vec<PfmeaStep>,
    pub created_at: DateTime<Utc>,
}

/// Customer complaint.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerComplaint {
    pub id: Uuid,
    pub complaint_number: String,
    pub customer_id: Uuid,
    pub product_id: Option<Uuid>,
    pub description: String,
    pub status: ComplaintStatus,
    pub severity: FindingSeverity,
    pub containment_action: Option<String>,
    pub root_cause: Option<String>,
    pub corrective_action: Option<String>,
    pub closed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// 8D Report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EightDReport {
    pub id: Uuid,
    pub complaint_id: Uuid,
    pub d1_team: Vec<String>,
    pub d2_problem_description: String,
    pub d3_containment: String,
    pub d4_root_cause: String,
    pub d5_corrective_action: String,
    pub d6_implementation: String,
    pub d7_preventive_action: String,
    pub d8_celebration: String,
    pub created_at: DateTime<Utc>,
}

/// Management review pack.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManagementReviewPack {
    pub id: Uuid,
    pub period_start: DateTime<Utc>,
    pub period_end: DateTime<Utc>,
    pub prepared_by: String,
    pub notes: String,
    pub sections: Vec<String>,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// NPI Risk Register Models
// ---------------------------------------------------------------------------

/// NPI risk categories.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NpiRiskCategory {
    DesignComplexity,
    ProcessCapability,
    SupplierCapability,
    TechnologyMaturity,
    ResourceAvailability,
    RegulatoryCompliance,
    ScheduleRisk,
    CostRisk,
    QualityRisk,
    SafetyRisk,
    EnvironmentalRisk,
    MarketRisk,
    TechnicalRisk,
    Other,
}

/// NPI risk phases.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskPhase {
    Intake,
    Dfm,
    Prototype,
    Pilot,
    Sop,
}

/// NPI risk priority.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskPriority {
    Critical,
    High,
    Medium,
    Low,
}

/// NPI mitigation status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NpiMitigationStatus {
    Identified,
    InProgress,
    Completed,
    Verified,
    Overdue,
    Cancelled,
}

/// NPI review status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReviewStatus {
    Scheduled,
    Completed,
    Overdue,
    Cancelled,
}

/// NPI mitigation action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiMitigationAction {
    pub id: Uuid,
    pub risk_id: Uuid,
    pub description: String,
    pub owner: String,
    pub status: NpiMitigationStatus,
    pub due_date: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub effectiveness: Option<u32>,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// NPI risk review.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiRiskReview {
    pub id: Uuid,
    pub risk_id: Uuid,
    pub phase: RiskPhase,
    pub reviewed_by: Uuid,
    pub reviewed_at: DateTime<Utc>,
    pub severity_score: u32,
    pub occurrence_score: u32,
    pub detection_score: u32,
    pub rpn: u32,
    pub comments: Option<String>,
    pub created_at: DateTime<Utc>,
}

impl NpiRiskReview {
    /// Calculate RPN from severity, occurrence, and detection scores.
    pub fn calculate_rpn(severity: u32, occurrence: u32, detection: u32) -> u32 {
        severity * occurrence * detection
    }
}

/// An NPI risk entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiRisk {
    pub id: Uuid,
    pub risk_number: String,
    pub title: String,
    pub description: String,
    pub category: NpiRiskCategory,
    pub phase: RiskPhase,
    pub project_id: Option<Uuid>,
    pub initial_severity: u32,
    pub initial_occurrence: u32,
    pub initial_detection: u32,
    pub current_severity: u32,
    pub current_occurrence: u32,
    pub current_detection: u32,
    pub target_severity: u32,
    pub target_occurrence: u32,
    pub target_detection: u32,
    pub is_closed: bool,
    pub has_occurred: bool,
    pub occurred_at: Option<DateTime<Utc>>,
    pub mitigations: Vec<NpiMitigationAction>,
    pub reviews: Vec<NpiRiskReview>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl NpiRisk {
    /// Calculate current RPN.
    pub fn current_rpn(&self) -> u32 {
        self.current_severity * self.current_occurrence * self.current_detection
    }

    /// Calculate target RPN.
    pub fn target_rpn(&self) -> u32 {
        self.target_severity * self.target_occurrence * self.target_detection
    }

    /// Calculate initial RPN.
    pub fn initial_rpn(&self) -> u32 {
        self.initial_severity * self.initial_occurrence * self.initial_detection
    }

    /// Determine risk priority based on current RPN.
    pub fn priority(&self) -> RiskPriority {
        let rpn = self.current_rpn();
        match rpn {
            0..=50 => RiskPriority::Low,
            51..=150 => RiskPriority::Medium,
            151..=500 => RiskPriority::High,
            _ => RiskPriority::Critical,
        }
    }
}

/// A risk template for NPI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskTemplate {
    pub id: Uuid,
    pub name: String,
    pub description: String,
    pub category: NpiRiskCategory,
    pub phase: RiskPhase,
    pub default_severity: u32,
    pub default_occurrence: u32,
    pub default_detection: u32,
    pub suggested_mitigations: Vec<String>,
}

/// A heat map cell for NPI risk visualization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeatMapCell {
    pub severity: u32,
    pub occurrence: u32,
    pub count: u32,
    pub rpn: u32,
    pub risk_ids: Vec<Uuid>,
}

impl HeatMapCell {
    /// Determine the heat map cell level based on RPN.
    pub fn level(&self) -> &'static str {
        match self.rpn {
            0..=50 => "low",
            51..=150 => "medium",
            151..=500 => "high",
            _ => "critical",
        }
    }
}

// ---------------------------------------------------------------------------
// Audit Evidence Models
// ---------------------------------------------------------------------------

/// Types of audit evidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EvidenceType {
    Document,
    Photo,
    Video,
    Audio,
    Recording,
    TestResult,
    Certificate,
    Email,
    Report,
    Other,
}

/// Status of an audit evidence package.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PackageStatus {
    Draft,
    Sealed,
    Exported,
}

/// An evidence record (immutable after creation).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceRecord {
    pub id: Uuid,
    pub audit_id: Uuid,
    pub evidence_type: EvidenceType,
    pub title: String,
    pub description: String,
    pub content_hash: String,
    pub file_path: Option<String>,
    pub created_by: Option<Uuid>,
    pub created_at: DateTime<Utc>,
}

/// An audit evidence package.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditPackage {
    pub id: Uuid,
    pub audit_id: Uuid,
    pub title: String,
    pub status: PackageStatus,
    pub evidence_ids: Vec<Uuid>,
    pub package_hash: Option<String>,
    pub signature: Option<String>,
    pub sealed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Audit Trail Timeline Models
// ---------------------------------------------------------------------------

/// Types of changes tracked in audit trail.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditChangeType {
    Create,
    Update,
    Delete,
    StatusChange,
    OwnerChange,
    LinkAdd,
    LinkRemove,
    AttachmentAdd,
    AttachmentRemove,
    Comment,
    Approval,
    Rejection,
    Escalation,
    Custom,
}

/// Types of entities tracked.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditEntityType {
    Ncr,
    Capa,
    Audit,
    Finding,
    Document,
    Supplier,
    Gauge,
    Risk,
    Complaint,
    ChangeRequest,
    Project,
    WorkOrder,
    Invoice,
    User,
    Other,
}

/// Types of fields that can change.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditFieldType {
    Text,
    Number,
    Boolean,
    Date,
    Enum,
    Currency,
    Percentage,
    UserRef,
    EntityRef,
    RichText,
    Attachment,
}

/// Relationship types for linked entities.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditRelationshipType {
    Parent,
    Child,
    Reference,
    Associated,
    Causes,
    Corrects,
    Prevents,
    Duplicate,
}

/// Access levels for audit entries.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditAccessLevel {
    Public,
    Internal,
    Confidential,
    Restricted,
}

/// A single field change in an audit entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldChange {
    pub field_name: String,
    pub old_value: Option<String>,
    pub new_value: Option<String>,
    pub field_type: AuditFieldType,
}

/// A related entity reference.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RelatedEntity {
    pub entity_id: Uuid,
    pub entity_type: AuditEntityType,
    pub relationship: AuditRelationshipType,
    pub summary: Option<String>,
}

/// An audit trail entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub id: Uuid,
    pub entity_id: Uuid,
    pub entity_type: AuditEntityType,
    pub change_type: AuditChangeType,
    pub summary: String,
    pub field_changes: Vec<FieldChange>,
    pub related_entities: Vec<RelatedEntity>,
    pub changed_by: Option<Uuid>,
    pub access_level: AuditAccessLevel,
    pub metadata: Option<serde_json::Value>,
    pub occurred_at: DateTime<Utc>,
}

/// A group of audit entries for a time period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelineGroup {
    pub label: String,
    pub date: DateTime<Utc>,
    pub entries: Vec<AuditEntry>,
}

/// A full timeline response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Timeline {
    pub groups: Vec<TimelineGroup>,
    pub total_count: u64,
    pub has_more: bool,
}

/// Filter for audit trail queries.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelineFilter {
    pub entity_ids: Option<Vec<Uuid>>,
    pub entity_types: Option<Vec<AuditEntityType>>,
    pub change_types: Option<Vec<AuditChangeType>>,
    pub user_id: Option<Uuid>,
    pub date_from: Option<DateTime<Utc>>,
    pub date_to: Option<DateTime<Utc>>,
    pub search_text: Option<String>,
    pub access_level_min: Option<AuditAccessLevel>,
}

/// Configuration for audit trail behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelineConfig {
    pub retention_days: u32,
    pub max_entries_per_entity: u32,
    pub enable_field_diff: bool,
    pub enable_relation_tracking: bool,
    pub enable_access_control: bool,
}

impl Default for TimelineConfig {
    fn default() -> Self {
        Self {
            retention_days: 365,
            max_entries_per_entity: 10000,
            enable_field_diff: true,
            enable_relation_tracking: true,
            enable_access_control: true,
        }
    }
}

/// Result of a field diff calculation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiffResult {
    pub field_changes: Vec<FieldChange>,
    pub has_changes: bool,
    pub change_count: usize,
}

// ---------------------------------------------------------------------------
// Change Control Models
// ---------------------------------------------------------------------------

/// Types of change in change control.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChangeType {
    Threshold,
    MarginFloor,
    PipelineStage,
    Template,
    Rule,
    Configuration,
    Parameter,
    Workflow,
    Permission,
    Integration,
    Other,
}

/// Status of a change request.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChangeStatus {
    Draft,
    PendingReview,
    PendingApproval,
    Approved,
    Rejected,
    Scheduled,
    InProgress,
    Completed,
    RolledBack,
    Cancelled,
}

/// Risk level of a change.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChangeRisk {
    Low,
    Medium,
    High,
    Critical,
}

/// Impact level of a change.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChangeImpact {
    None,
    Low,
    Medium,
    High,
    Critical,
}

/// Approval decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ApprovalDecision {
    Approved,
    Rejected,
    ConditionallyApproved,
    MoreInfoNeeded,
}

/// A configuration value (before/after snapshot).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigValue {
    pub key: String,
    pub old_value: Option<serde_json::Value>,
    pub new_value: Option<serde_json::Value>,
    pub value_type: String,
}

/// A change approval record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangeApproval {
    pub id: Uuid,
    pub change_request_id: Uuid,
    pub approver_id: Uuid,
    pub decision: ApprovalDecision,
    pub comments: Option<String>,
    pub decided_at: DateTime<Utc>,
}

/// An impact assessment for a change.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImpactAssessment {
    pub id: Uuid,
    pub change_request_id: Uuid,
    pub impact_type: String,
    pub description: String,
    pub impact_level: ChangeImpact,
    pub affected_areas: Vec<String>,
    pub mitigation: Option<String>,
}

/// An audit entry for a change.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangeAuditEntry {
    pub id: Uuid,
    pub change_request_id: Uuid,
    pub action: String,
    pub details: String,
    pub performed_by: Option<Uuid>,
    pub performed_at: DateTime<Utc>,
}

/// A change request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangeRequest {
    pub id: Uuid,
    pub change_number: String,
    pub title: String,
    pub description: String,
    pub change_type: ChangeType,
    pub status: ChangeStatus,
    pub risk: ChangeRisk,
    pub config_changes: Vec<ConfigValue>,
    pub approvals: Vec<ChangeApproval>,
    pub impact_assessments: Vec<ImpactAssessment>,
    pub audit_trail: Vec<ChangeAuditEntry>,
    pub requested_by: Option<Uuid>,
    pub scheduled_for: Option<DateTime<Utc>>,
    pub applied_at: Option<DateTime<Utc>>,
    pub rolled_back_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// An approval policy for change types.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApprovalPolicy {
    pub id: Uuid,
    pub change_type: ChangeType,
    pub required_approvers: u32,
    pub required_roles: Vec<String>,
    pub auto_approve_threshold: Option<ChangeRisk>,
    pub escalation_delay_hours: u32,
}

/// A config snapshot for rollback.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigSnapshot {
    pub id: Uuid,
    pub change_request_id: Uuid,
    pub config_data: serde_json::Value,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Inspection Models (AQL, FAI, Self-Inspection)
// ---------------------------------------------------------------------------

/// An AQL sampling plan.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AqlSamplingPlan {
    pub id: Uuid,
    pub plan_number: String,
    pub aql_percent: f64,
    pub inspection_level: String,
    pub lot_size_from: u64,
    pub lot_size_to: u64,
    pub sample_size: u64,
    pub accept_number: u64,
    pub reject_number: u64,
    pub created_at: DateTime<Utc>,
}

/// An AQL lot inspection record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AqlLotInspection {
    pub id: Uuid,
    pub plan_id: Uuid,
    pub lot_number: String,
    pub lot_size: u64,
    pub sample_size: u64,
    pub defects_found: u64,
    pub accept_number: u64,
    pub reject_number: u64,
    pub result: String,
    pub inspector_id: Option<Uuid>,
    pub inspected_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// A First Article Inspection (AS9102).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirstArticleInspection {
    pub id: Uuid,
    pub fai_number: String,
    pub part_number: String,
    pub part_name: String,
    pub revision: String,
    pub customer: Option<String>,
    pub status: String,
    pub characteristics: Vec<FirstArticleCharacteristic>,
    pub inspector_id: Option<Uuid>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A characteristic in a First Article Inspection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirstArticleCharacteristic {
    pub id: Uuid,
    pub inspection_id: Uuid,
    pub characteristic_number: String,
    pub requirement: String,
    pub specification: String,
    pub result: String,
    pub is_conforming: Option<bool>,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// Self-inspection record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelfInspection {
    pub id: Uuid,
    pub inspection_number: String,
    pub product_id: Option<Uuid>,
    pub work_order_id: Option<Uuid>,
    pub station_id: Option<Uuid>,
    pub operator_id: Option<Uuid>,
    pub status: String,
    pub result: Option<String>,
    pub checks: Vec<SelfInspectionCheck>,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

/// A check within a self-inspection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelfInspectionCheck {
    pub id: Uuid,
    pub inspection_id: Uuid,
    pub characteristic: String,
    pub specification: Option<String>,
    pub actual_value: Option<String>,
    pub result: String,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// MSA (Measurement Systems Analysis) Models
// ---------------------------------------------------------------------------

/// MSA study type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MsaStudyType {
    Grr,
    Linearity,
    Bias,
    Stability,
    AttributeAgreement,
}

/// MSA study.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MsaStudy {
    pub id: Uuid,
    pub study_type: MsaStudyType,
    pub title: String,
    pub gauge_id: Option<Uuid>,
    pub operators_count: u32,
    pub parts_count: u32,
    pub trials_count: u32,
    pub status: String,
    pub measurements: Vec<MsaMeasurement>,
    pub result: Option<MsaResult>,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

/// A single measurement in an MSA study.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MsaMeasurement {
    pub id: Uuid,
    pub study_id: Uuid,
    pub operator_id: Uuid,
    pub part_id: String,
    pub trial_number: u32,
    pub measured_value: f64,
    pub measured_at: DateTime<Utc>,
}

/// Result of an MSA study (GRR, ndc, etc.).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MsaResult {
    pub id: Uuid,
    pub study_id: Uuid,
    pub repeatability_ev: f64,
    pub reproducibility_av: f64,
    pub grr: f64,
    pub part_variation_pv: f64,
    pub total_variation_tv: f64,
    pub grr_percent: f64,
    pub ndc: u32,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Process Capability Models
// ---------------------------------------------------------------------------

/// Process capability study.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessCapabilityStudy {
    pub id: Uuid,
    pub title: String,
    pub characteristic: String,
    pub lsl: f64,
    pub usl: f64,
    pub target: Option<f64>,
    pub status: String,
    pub measurements: Vec<ProcessCapabilityMeasurement>,
    pub result: Option<ProcessCapabilityResult>,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

/// A single measurement in a capability study.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessCapabilityMeasurement {
    pub id: Uuid,
    pub study_id: Uuid,
    pub measured_value: f64,
    pub sample_label: Option<String>,
    pub measured_at: DateTime<Utc>,
}

/// Result of a capability study (Cp, Cpk, etc.).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessCapabilityResult {
    pub id: Uuid,
    pub study_id: Uuid,
    pub mean: f64,
    pub std_dev: f64,
    pub cp: f64,
    pub cpk: f64,
    pub cpu: f64,
    pub cpl: f64,
    pub pp: Option<f64>,
    pub ppk: Option<f64>,
    pub sample_size: u32,
    pub is_capable: bool,
    pub created_at: DateTime<Utc>,
}

impl ProcessCapabilityResult {
    /// Determine if the process is capable (Cpk >= 1.33).
    pub fn determine_capability(cpk: f64) -> bool {
        cpk >= 1.33
    }
}

// ---------------------------------------------------------------------------
// SPC / Change Point Detection Models
// ---------------------------------------------------------------------------

/// A change point study.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangePointStudy {
    pub id: Uuid,
    pub title: String,
    pub parameter: String,
    pub sensitivity: f64,
    pub algorithm: String,
    pub observations: Vec<ChangePointObservation>,
    pub events: Vec<ChangePointEvent>,
    pub created_at: DateTime<Utc>,
}

/// A single observation in a change point study.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangePointObservation {
    pub id: Uuid,
    pub study_id: Uuid,
    pub value: f64,
    pub label: Option<String>,
    pub observed_at: DateTime<Utc>,
}

/// A detected change point event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangePointEvent {
    pub id: Uuid,
    pub study_id: Uuid,
    pub index_position: usize,
    pub change_magnitude: f64,
    pub confidence: f64,
    pub notes: Option<String>,
    pub detected_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// NPI Stage Gates Models
// ---------------------------------------------------------------------------

/// NPI workflow stages.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NpiStage {
    Intake,
    Dfm,
    Prototype,
    Pilot,
    Sop,
    Completed,
    Cancelled,
}

/// Artifact types required at various NPI stages.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ArtifactType {
    CustomerRequirements,
    InitialSpecs,
    VolumeForecast,
    TargetPricing,
    CtqDefinition,
    ProcessCapabilityStudy,
    DfmReview,
    ToolingPlan,
    PrototypeBuild,
    PrototypeTestResults,
    DesignValidation,
    SupplierQuotes,
    PilotBuild,
    ProcessValidation,
    SupplierReadiness,
    PpapSubmission,
    OperatorTraining,
    ProductionApproval,
    StandardWorkApproved,
    ControlPlan,
    CustomerApproval,
}

/// Status of an NPI artifact.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ArtifactStatus {
    NotStarted,
    InProgress,
    PendingReview,
    Approved,
    Rejected,
    Waived,
}

/// Gate review decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GateDecision {
    Go,
    NoGo,
    ConditionalGo,
    Hold,
}

/// Reason for blocking a stage transition.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransitionBlockReason {
    MissingRequiredArtifact,
    ArtifactNotApproved,
    PendingApproval,
    FailedGateReview,
    InsufficientPermissions,
}

/// An NPI project artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiArtifact {
    pub id: Uuid,
    pub npi_project_id: Uuid,
    pub artifact_type: ArtifactType,
    pub name: String,
    pub description: String,
    pub status: ArtifactStatus,
    pub is_required: bool,
    pub required_for_stage: NpiStage,
    pub attachment_ids: Vec<Uuid>,
    pub evidence_notes: String,
    pub reviewed_by: Option<Uuid>,
    pub reviewed_at: Option<DateTime<Utc>>,
    pub review_notes: String,
    pub waived_by: Option<Uuid>,
    pub waived_at: Option<DateTime<Utc>>,
    pub waiver_reason: String,
    pub waiver_expiration: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Uuid,
}

impl NpiArtifact {
    /// Check if artifact is complete (approved or waived).
    pub fn is_complete(&self) -> bool {
        matches!(
            self.status,
            ArtifactStatus::Approved | ArtifactStatus::Waived
        )
    }

    /// Check if waiver is still valid.
    pub fn is_waiver_valid(&self) -> bool {
        if self.status != ArtifactStatus::Waived {
            return false;
        }
        match self.waiver_expiration {
            None => true,
            Some(exp) => chrono::Utc::now() < exp,
        }
    }
}

/// A gate review event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateReview {
    pub id: Uuid,
    pub npi_project_id: Uuid,
    pub from_stage: NpiStage,
    pub to_stage: NpiStage,
    pub decision: GateDecision,
    pub decision_rationale: String,
    pub conditions: Vec<String>,
    pub reviewed_by: Uuid,
    pub review_team: Vec<Uuid>,
    pub scheduled_at: Option<DateTime<Utc>>,
    pub conducted_at: DateTime<Utc>,
    pub action_items: Vec<serde_json::Value>,
    pub follow_up_date: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// Result of attempting a stage transition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitionResult {
    pub success: bool,
    pub from_stage: NpiStage,
    pub to_stage: NpiStage,
    pub blocked_reasons: Vec<TransitionBlockReason>,
    pub missing_artifacts: Vec<ArtifactType>,
    pub pending_artifacts: Vec<ArtifactType>,
    pub message: String,
    pub gate_review_id: Option<Uuid>,
}

/// An NPI project.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiProject {
    pub id: Uuid,
    pub name: String,
    pub description: String,
    pub product_id: Option<Uuid>,
    pub customer_id: Option<Uuid>,
    pub rfq_id: Option<Uuid>,
    pub quote_id: Option<Uuid>,
    pub current_stage: NpiStage,
    pub stage_entered_at: DateTime<Utc>,
    pub target_sop_date: Option<DateTime<Utc>>,
    pub actual_sop_date: Option<DateTime<Utc>>,
    pub project_manager_id: Option<Uuid>,
    pub engineering_lead_id: Option<Uuid>,
    pub quality_lead_id: Option<Uuid>,
    pub manufacturing_lead_id: Option<Uuid>,
    pub estimated_annual_volume: u64,
    pub estimated_unit_cost: f64,
    pub estimated_investment: f64,
    pub is_active: bool,
    pub priority: u32,
    pub health_status: String,
    pub health_notes: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Uuid,
}

/// Requirements for entering a specific stage.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StageRequirements {
    pub stage: NpiStage,
    pub required_artifacts: Vec<ArtifactType>,
    pub optional_artifacts: Vec<ArtifactType>,
    pub required_approvers: Vec<String>,
    pub minimum_approval_count: u32,
}

// ---------------------------------------------------------------------------
// Customer Satisfaction Models
// ---------------------------------------------------------------------------

/// A customer satisfaction survey.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerSurvey {
    pub id: Uuid,
    pub title: String,
    pub survey_type: String,
    pub responses: Vec<CustomerSurveyResponse>,
    pub created_at: DateTime<Utc>,
}

/// A response to a customer survey.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerSurveyResponse {
    pub id: Uuid,
    pub survey_id: Uuid,
    pub customer_id: Uuid,
    pub nps_score: u32,
    pub feedback: Option<String>,
    pub response_date: DateTime<Utc>,
}

/// NPS statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpsStats {
    pub total_responses: u32,
    pub promoters: u32,
    pub passives: u32,
    pub detractors: u32,
    pub nps_score: f64,
    pub promoter_percent: f64,
    pub passive_percent: f64,
    pub detractor_percent: f64,
}

// ---------------------------------------------------------------------------
// Lab Management Models
// ---------------------------------------------------------------------------

/// A lab sample.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LabSample {
    pub id: Uuid,
    pub sample_number: String,
    pub product_id: Option<Uuid>,
    pub lot_id: Option<String>,
    pub sample_type: String,
    pub status: String,
    pub created_at: DateTime<Utc>,
}

/// A lab test method.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LabTestMethod {
    pub id: Uuid,
    pub method_number: String,
    pub name: String,
    pub description: String,
    pub standard: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// A lab test run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LabTestRun {
    pub id: Uuid,
    pub sample_id: Uuid,
    pub method_id: Uuid,
    pub result: String,
    pub value: Option<f64>,
    pub unit: Option<String>,
    pub technician_id: Option<Uuid>,
    pub tested_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Management Review Models
// ---------------------------------------------------------------------------

/// A management review.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManagementReview {
    pub id: Uuid,
    pub title: String,
    pub period_start: DateTime<Utc>,
    pub period_end: DateTime<Utc>,
    pub status: String,
    pub notes: String,
    pub actions: Vec<ManagementReviewAction>,
    pub created_at: DateTime<Utc>,
}

/// An action item from a management review.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManagementReviewAction {
    pub id: Uuid,
    pub review_id: Uuid,
    pub description: String,
    pub owner_id: Option<Uuid>,
    pub due_date: Option<DateTime<Utc>>,
    pub status: String,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Traceability Models
// ---------------------------------------------------------------------------

/// A traceability matrix.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceabilityMatrix {
    pub id: Uuid,
    pub name: String,
    pub product_id: Option<Uuid>,
    pub description: String,
    pub created_at: DateTime<Utc>,
}

/// A link within a traceability matrix.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceabilityLink {
    pub id: Uuid,
    pub matrix_id: Uuid,
    pub source_type: String,
    pub source_id: Uuid,
    pub target_type: String,
    pub target_id: Uuid,
    pub relationship: String,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Quality Certification Gate Models
// ---------------------------------------------------------------------------

/// Result of a certification check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CertificationCheckResult {
    pub is_allowed: bool,
    pub required_skill_ids: Vec<u32>,
    pub missing_skill_ids: Vec<u32>,
    pub message: Option<String>,
}

// ---------------------------------------------------------------------------
// Additional domain events DTOs
// ---------------------------------------------------------------------------

/// Event data for NCR created events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NcrCreatedEventData {
    pub ncr_id: Uuid,
    pub ncr_number: String,
    pub severity: String,
    pub nc_type: String,
    pub product_id: Option<Uuid>,
    pub process_id: Option<Uuid>,
    pub defect_code: Option<String>,
    pub detected_by: Option<Uuid>,
}

/// Event data for CAPA created events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapaCreatedEventData {
    pub capa_id: Uuid,
    pub nc_id: Option<Uuid>,
    pub capa_number: String,
    pub priority: String,
    pub auto_created: bool,
    pub creation_reason: String,
}

/// Event data for inspection completed events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InspectionCompletedEventData {
    pub inspection_id: Uuid,
    pub result: String,
    pub product_id: Option<Uuid>,
    pub inspector_id: Option<Uuid>,
}

/// Event data for audit finding events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditFindingEventData {
    pub finding_id: Uuid,
    pub audit_id: Uuid,
    pub severity: String,
    pub area: Option<String>,
}

/// Event data for supplier evaluation events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupplierEvaluatedEventData {
    pub supplier_id: String,
    pub score: f64,
    pub tier: String,
}

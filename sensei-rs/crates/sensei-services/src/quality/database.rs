//! PostgreSQL-backed quality service using sqlx.
//!
//! Provides comprehensive quality management backed by PostgreSQL tables.
//!
//! Implements [`QualityService`].
//!
//! # Canonical storage (thirtieth-audit P0 items 6-8)
//!
//! The NCR / CAPA / audit / audit-finding methods operate on the REAL
//! relational quality tables — the fabricated JSONB-style `quality_*`
//! tables never existed anywhere in the migration chain and are gone
//! from this implementation:
//!
//! * NCR → `ncr_reports` (001; reconciled to the `NonConformance` model
//!   by migration 173);
//! * CAPA → `capas` (001; reconciled to `CapaExtended` by migration
//!   173 — the workflow sub-state vectors live in the canonical row's
//!   `details` JSONB column, the same JSONB-on-relational-table pattern
//!   the chain already uses for `self_inspections.characteristics` etc.;
//!   the SECURITY scope columns stay real relational columns);
//! * Audit → `audits` (002; `audit_findings` for findings — the extended
//!   `quality_audits` table is a legacy summary outside this family);
//! * every statement filters through the caller's scope on the
//!   SERVER-STAMPED relational columns (`scope_site_id` /
//!   `scope_work_center_id`, migration 170) via the single
//!   [`quality_scope_predicate`](super::scope::quality_scope_predicate):
//!   site grants match stamped rows of their sites, EXACT work-center
//!   grants match only records stamped at that work center (never the
//!   whole site, never a site-level record), corporate NULL-scope rows
//!   are tenant-wide-only, and a caller with no operational scope
//!   matches zero rows.
//!
//! Creation stamps the row from [`derive_creation_scope`](super::scope::derive_creation_scope)
//! — client payloads can never set the scope columns, and a scoped
//! caller without an operating site is rejected instead of silently
//! producing a corporate record (P0 item 8).
//!
//! The remaining tenant-only families of the trait (FAI / self
//! inspections, supplier scorecards / SCARs, documents, MSA, capability
//! studies, control plans, PFMEA, NPI projects/risks, gauges,
//! complaints, 8D reports, management reviews) return an explicit
//! `unsupported` error in DB mode: their domain models have no faithful
//! canonical relational home in the 001..172 chain, and this service no
//! longer fabricates JSONB tables for them (the in-memory service keeps
//! serving them in dev mode).

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::db::TenantTx;
use sensei_core::domain::RequestContext;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use uuid::Uuid;

use super::models::*;
use super::scope::{quality_scope_predicate, QualityScopeBind};
use super::service::QualityService;

/// PostgreSQL-backed implementation of [`QualityService`].
pub struct DatabaseQualityService {
    pool: PgPool,
}

impl DatabaseQualityService {
    /// Create a new [`DatabaseQualityService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items,
        total: count as usize,
        page,
        per_page,
        total_pages: (count as usize).max(1).div_ceil(per_page),
    }
}

fn gen_number(prefix: &str) -> (Uuid, String) {
    let id = Uuid::new_v4();
    let suffix = id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string();
    let number = format!("{}-{}-{}", prefix, Utc::now().format("%Y%m%d"), suffix);
    (id, number)
}

fn db_err(ctx: &str, e: sqlx::Error) -> SenseiError {
    SenseiError::Database(format!("{}: {e}", ctx))
}

fn not_found(entity: &str, id: Uuid) -> SenseiError {
    SenseiError::NotFound(format!("{} {id} not found", entity))
}

/// An explicit DB-mode gap: the family has no faithful canonical
/// relational home in the 001..172 chain and the service no longer
/// fabricates JSONB `quality_*` tables for it (thirtieth-audit P0
/// item 6 — no fabricated storage, ever).
fn unsupported(family: &str) -> SenseiError {
    SenseiError::Internal(format!(
        "{family} is not available in DB deployments: the {family} domain model has no \
         canonical relational table in the schema, and DatabaseQualityService does not \
         fabricate JSONB tables — the in-memory service serves this family in dev mode"
    ))
}

fn normalize(s: &str) -> String {
    s.chars()
        .filter(|c| *c != '_' && !c.is_whitespace())
        .flat_map(char::to_lowercase)
        .collect()
}

/// Map a case/separator-insensitive API filter value onto a canonical DB
/// string, or `None` when it matches nothing (the filter then matches
/// zero rows, mirroring the old post-filter semantics).
fn canonical_db_value<'a>(filter: &str, candidates: &[&'a str]) -> Option<&'a str> {
    let needle = normalize(filter);
    candidates.iter().find(|c| normalize(c) == needle).copied()
}

// ── Enum ↔ canonical DB string (lowercase snake) mappings ───────────────

const NC_TYPE_DB: &[&str] = &[
    "product",
    "process",
    "system",
    "documentation",
    "supplier",
    "safety",
    "environmental",
    "regulatory",
    "service",
    "customer_complaint",
    "other",
];

fn nc_type_db(t: NcType) -> &'static str {
    match t {
        NcType::Product => "product",
        NcType::Process => "process",
        NcType::System => "system",
        NcType::Documentation => "documentation",
        NcType::Supplier => "supplier",
        NcType::Safety => "safety",
        NcType::Environmental => "environmental",
        NcType::Regulatory => "regulatory",
        NcType::Service => "service",
        NcType::CustomerComplaint => "customer_complaint",
        NcType::Other => "other",
    }
}

fn nc_type_from_db(s: &str) -> Result<NcType> {
    Ok(match s {
        "product" => NcType::Product,
        "process" => NcType::Process,
        "system" => NcType::System,
        "documentation" => NcType::Documentation,
        "supplier" => NcType::Supplier,
        "safety" => NcType::Safety,
        "environmental" => NcType::Environmental,
        "regulatory" => NcType::Regulatory,
        "service" => NcType::Service,
        "customer_complaint" => NcType::CustomerComplaint,
        "other" => NcType::Other,
        other => {
            return Err(SenseiError::Database(format!(
                "stored NCR type {other:?} is not a canonical value"
            )))
        }
    })
}

/// The model's own severity vocabulary (migration 173 widened the CHECK;
/// the legacy 'minor'/'major' values remain writable by legacy code but
/// are not model values).
fn nc_severity_db(s: NcSeverity) -> &'static str {
    match s {
        NcSeverity::Low => "low",
        NcSeverity::Medium => "medium",
        NcSeverity::High => "high",
        NcSeverity::Critical => "critical",
    }
}

fn nc_severity_from_db(s: &str) -> Result<NcSeverity> {
    Ok(match s {
        "low" => NcSeverity::Low,
        "medium" => NcSeverity::Medium,
        "high" => NcSeverity::High,
        "critical" => NcSeverity::Critical,
        other => {
            return Err(SenseiError::Database(format!(
                "stored NCR severity {other:?} is not a model value"
            )))
        }
    })
}

const NCR_STATUS_DB: &[&str] = &[
    "open",
    "under_investigation",
    "action_defined",
    "in_progress",
    "closed",
    "cancelled",
];

fn ncr_status_from_db(s: &str) -> Result<NcrStatus> {
    Ok(match s {
        "open" => NcrStatus::Open,
        "under_investigation" => NcrStatus::UnderInvestigation,
        "action_defined" => NcrStatus::ActionDefined,
        "in_progress" => NcrStatus::InProgress,
        "closed" => NcrStatus::Closed,
        "cancelled" => NcrStatus::Cancelled,
        other => {
            return Err(SenseiError::Database(format!(
                "stored NCR status {other:?} is not a model value"
            )))
        }
    })
}

fn capa_type_db(t: CapaType) -> &'static str {
    match t {
        CapaType::Corrective => "corrective",
        CapaType::Preventive => "preventive",
        CapaType::Improvement => "improvement",
    }
}

fn capa_type_from_db(s: &str) -> Result<CapaType> {
    Ok(match s {
        "corrective" => CapaType::Corrective,
        "preventive" => CapaType::Preventive,
        "improvement" => CapaType::Improvement,
        other => {
            return Err(SenseiError::Database(format!(
                "stored CAPA type {other:?} is not a model value"
            )))
        }
    })
}

fn capa_priority_db(p: CapaPriority) -> &'static str {
    match p {
        CapaPriority::Low => "low",
        CapaPriority::Medium => "medium",
        CapaPriority::High => "high",
        CapaPriority::Emergency => "emergency",
    }
}

fn capa_priority_from_db(s: &str) -> Result<CapaPriority> {
    Ok(match s {
        "low" => CapaPriority::Low,
        "medium" => CapaPriority::Medium,
        "high" => CapaPriority::High,
        "emergency" => CapaPriority::Emergency,
        other => {
            return Err(SenseiError::Database(format!(
                "stored CAPA priority {other:?} is not a model value"
            )))
        }
    })
}

const CAPA_STATUS_DB: &[&str] = &[
    "draft",
    "pending_approval",
    "open",
    "root_cause_analysis",
    "action_planning",
    "implementing",
    "verification",
    "effectiveness_check",
    "pending_closure",
    "closed",
    "rejected",
    "cancelled",
];

fn capa_status_db(s: CapaStatusEx) -> &'static str {
    match s {
        CapaStatusEx::Draft => "draft",
        CapaStatusEx::PendingApproval => "pending_approval",
        CapaStatusEx::Open => "open",
        CapaStatusEx::RootCauseAnalysis => "root_cause_analysis",
        CapaStatusEx::ActionPlanning => "action_planning",
        CapaStatusEx::Implementing => "implementing",
        CapaStatusEx::Verification => "verification",
        CapaStatusEx::EffectivenessCheck => "effectiveness_check",
        CapaStatusEx::PendingClosure => "pending_closure",
        CapaStatusEx::Closed => "closed",
        CapaStatusEx::Rejected => "rejected",
        CapaStatusEx::Cancelled => "cancelled",
    }
}

fn capa_status_from_db(s: &str) -> Result<CapaStatusEx> {
    Ok(match s {
        "draft" => CapaStatusEx::Draft,
        "pending_approval" => CapaStatusEx::PendingApproval,
        "open" => CapaStatusEx::Open,
        "root_cause_analysis" => CapaStatusEx::RootCauseAnalysis,
        "action_planning" => CapaStatusEx::ActionPlanning,
        "implementing" => CapaStatusEx::Implementing,
        "verification" => CapaStatusEx::Verification,
        "effectiveness_check" => CapaStatusEx::EffectivenessCheck,
        "pending_closure" => CapaStatusEx::PendingClosure,
        "closed" => CapaStatusEx::Closed,
        "rejected" => CapaStatusEx::Rejected,
        "cancelled" => CapaStatusEx::Cancelled,
        other => {
            return Err(SenseiError::Database(format!(
                "stored CAPA status {other:?} is not a model value"
            )))
        }
    })
}

fn audit_type_db(t: AuditType) -> &'static str {
    match t {
        AuditType::Internal => "internal",
        AuditType::External => "external",
        AuditType::Supplier => "supplier",
        AuditType::Regulatory => "regulatory",
        AuditType::Certification => "certification",
        AuditType::Layered => "layered",
        AuditType::Process => "process",
        AuditType::Product => "product",
        AuditType::System => "system",
    }
}

fn audit_type_from_db(s: &str) -> Result<AuditType> {
    Ok(match s {
        "internal" => AuditType::Internal,
        "external" => AuditType::External,
        "supplier" => AuditType::Supplier,
        "regulatory" => AuditType::Regulatory,
        "certification" => AuditType::Certification,
        "layered" => AuditType::Layered,
        "process" => AuditType::Process,
        "product" => AuditType::Product,
        "system" => AuditType::System,
        other => {
            return Err(SenseiError::Database(format!(
                "stored audit type {other:?} is not a model value"
            )))
        }
    })
}

fn audit_status_db(s: AuditStatus) -> &'static str {
    match s {
        AuditStatus::Planned => "planned",
        AuditStatus::Scheduled => "scheduled",
        AuditStatus::InProgress => "in_progress",
        AuditStatus::Completed => "completed",
        AuditStatus::Closed => "closed",
        AuditStatus::Cancelled => "cancelled",
    }
}

fn audit_status_from_db(s: &str) -> Result<AuditStatus> {
    Ok(match s {
        "planned" => AuditStatus::Planned,
        "scheduled" => AuditStatus::Scheduled,
        "in_progress" => AuditStatus::InProgress,
        "completed" => AuditStatus::Completed,
        "closed" => AuditStatus::Closed,
        "cancelled" => AuditStatus::Cancelled,
        other => {
            return Err(SenseiError::Database(format!(
                "stored audit status {other:?} is not a model value"
            )))
        }
    })
}

fn finding_severity_from_db(s: &str) -> Result<FindingSeverity> {
    Ok(match s {
        "observation" => FindingSeverity::Observation,
        "minor" => FindingSeverity::MinorNc,
        "major" => FindingSeverity::MajorNc,
        "critical" => FindingSeverity::CriticalNc,
        other => {
            return Err(SenseiError::Database(format!(
                "stored finding severity {other:?} is not a model value"
            )))
        }
    })
}

fn finding_status_from_db(s: &str) -> Result<FindingStatus> {
    Ok(match s {
        "open" => FindingStatus::Open,
        "accepted" => FindingStatus::Accepted,
        "in_progress" => FindingStatus::InProgress,
        "implemented" => FindingStatus::Implemented,
        "verified" => FindingStatus::Verified,
        "closed" => FindingStatus::Closed,
        "waived" => FindingStatus::Waived,
        other => {
            return Err(SenseiError::Database(format!(
                "stored finding status {other:?} is not a model value"
            )))
        }
    })
}

/// Bind a [`QualityScopeBind`] to a query built by
/// [`quality_scope_predicate`]: the site set as ONE `uuid[]` value,
/// then one scalar `(site, work_center)` pair per exact grant.
macro_rules! bind_scope {
    ($q:expr, $bind:expr) => {
        if let Some(bind) = $bind {
            let QualityScopeBind {
                sites,
                work_centers,
            } = bind;
            let mut bound = if sites.is_empty() { $q } else { $q.bind(sites) };
            for (site, work_center) in work_centers {
                bound = bound.bind(site).bind(work_center);
            }
            bound
        } else {
            $q
        }
    };
}

/// The number of placeholders a scope predicate occupies: one `uuid[]`
/// site-set value when the caller holds site grants, plus two scalar
/// values per exact work-center grant.
fn scope_slots_used(bind: &Option<QualityScopeBind>) -> usize {
    match bind {
        None => 0,
        Some(b) => {
            let site_slots = usize::from(!b.sites.is_empty());
            site_slots + 2 * b.work_centers.len()
        }
    }
}

// ---------------------------------------------------------------------------
// Canonical relational rows (migration 170 scope columns + 173 storage)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct NcrRow {
    id: Uuid,
    ncr_number: String,
    title: String,
    description: String,
    nc_type: String,
    severity: String,
    status: String,
    product_id: Option<Uuid>,
    process_id: Option<Uuid>,
    defect_code: Option<String>,
    reported_by: Option<Uuid>,
    department: Option<String>,
    location: Option<String>,
    is_recurrence: bool,
    source: Option<String>,
    root_cause: Option<String>,
    root_cause_type: Option<String>,
    analysis_method: Option<String>,
    disposition: Option<String>,
    closed_at: Option<DateTime<Utc>>,
    scope_site_id: Option<Uuid>,
    scope_work_center_id: Option<Uuid>,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

impl NcrRow {
    fn to_entity(&self) -> Result<NonConformance> {
        Ok(NonConformance {
            id: self.id,
            nc_number: self.ncr_number.clone(),
            title: self.title.clone(),
            description: self.description.clone(),
            nc_type: nc_type_from_db(&self.nc_type)?,
            severity: nc_severity_from_db(&self.severity)?,
            product_id: self.product_id,
            process_id: self.process_id,
            defect_code: self.defect_code.clone(),
            detected_by: self.reported_by,
            department: self.department.clone(),
            location: self.location.clone(),
            is_recurrence: self.is_recurrence,
            status: ncr_status_from_db(&self.status)?,
            source: self.source.clone(),
            root_cause: self.root_cause.clone(),
            root_cause_type: self.root_cause_type.clone(),
            analysis_method: self.analysis_method.clone(),
            disposition: self.disposition.clone(),
            closed_at: self.closed_at,
            created_at: self.created_at,
            updated_at: self.updated_at,
        })
    }

    fn from_entity(ncr: &NonConformance) -> Self {
        Self {
            id: ncr.id,
            ncr_number: ncr.nc_number.clone(),
            title: ncr.title.clone(),
            description: ncr.description.clone(),
            nc_type: nc_type_db(ncr.nc_type).to_string(),
            severity: nc_severity_db(ncr.severity).to_string(),
            status: ncr.status.as_str().to_string(),
            product_id: ncr.product_id,
            process_id: ncr.process_id,
            defect_code: ncr.defect_code.clone(),
            reported_by: ncr.detected_by,
            department: ncr.department.clone(),
            location: ncr.location.clone(),
            is_recurrence: ncr.is_recurrence,
            source: ncr.source.clone(),
            root_cause: ncr.root_cause.clone(),
            root_cause_type: ncr.root_cause_type.clone(),
            analysis_method: ncr.analysis_method.clone(),
            disposition: ncr.disposition.clone(),
            closed_at: ncr.closed_at,
            scope_site_id: None,
            scope_work_center_id: None,
            created_at: ncr.created_at,
            updated_at: ncr.updated_at,
        }
    }
}

const NCR_COLUMNS: &str = "q.id, q.ncr_number, q.title, q.description, q.nc_type, \
     q.severity, q.status, q.product_id, q.process_id, q.defect_code, q.reported_by, \
     q.department, q.location, q.is_recurrence, q.source, q.root_cause, \
     q.root_cause_type, q.analysis_method, q.disposition, q.closed_at, \
     q.scope_site_id, q.scope_work_center_id, q.created_at, q.updated_at";

#[derive(Debug, Clone, sqlx::FromRow)]
struct CapaRow {
    id: Uuid,
    capa_number: String,
    title: String,
    description: String,
    capa_type: String,
    priority: String,
    status: String,
    nc_ids: Vec<Uuid>,
    owner_id: Option<Uuid>,
    due_date: Option<DateTime<Utc>>,
    closed_at: Option<DateTime<Utc>>,
    details: serde_json::Value,
    scope_site_id: Option<Uuid>,
    scope_work_center_id: Option<Uuid>,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

/// The workflow sub-state persisted in `capas.details` (JSONB on the
/// canonical relational row — the chain's own pattern; never the scope).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
struct CapaDetails {
    #[serde(default)]
    root_cause_analyses: Vec<RootCauseAnalysis>,
    #[serde(default)]
    actions: Vec<CorrectiveAction>,
    #[serde(default)]
    closure_gates: Vec<ClosureGate>,
    #[serde(default)]
    effectiveness_checks: Vec<EffectivenessCheck>,
    #[serde(default)]
    entity_links: Vec<EntityLink>,
}

impl CapaRow {
    fn to_entity(&self) -> Result<CapaExtended> {
        let details: CapaDetails = serde_json::from_value(self.details.clone()).unwrap_or_default();
        Ok(CapaExtended {
            id: self.id,
            capa_number: self.capa_number.clone(),
            title: self.title.clone(),
            description: self.description.clone(),
            nc_ids: self.nc_ids.clone(),
            capa_type: capa_type_from_db(&self.capa_type)?,
            priority: capa_priority_from_db(&self.priority)?,
            status: capa_status_from_db(&self.status)?,
            root_cause_analyses: details.root_cause_analyses,
            actions: details.actions,
            closure_gates: details.closure_gates,
            effectiveness_checks: details.effectiveness_checks,
            entity_links: details.entity_links,
            owner_id: self.owner_id,
            due_date: self.due_date,
            closed_at: self.closed_at,
            created_at: self.created_at,
            updated_at: self.updated_at,
        })
    }

    fn from_entity(capa: &CapaExtended) -> Self {
        let details = CapaDetails {
            root_cause_analyses: capa.root_cause_analyses.clone(),
            actions: capa.actions.clone(),
            closure_gates: capa.closure_gates.clone(),
            effectiveness_checks: capa.effectiveness_checks.clone(),
            entity_links: capa.entity_links.clone(),
        };
        Self {
            id: capa.id,
            capa_number: capa.capa_number.clone(),
            title: capa.title.clone(),
            description: capa.description.clone(),
            capa_type: capa_type_db(capa.capa_type).to_string(),
            priority: capa_priority_db(capa.priority).to_string(),
            status: capa_status_db(capa.status).to_string(),
            nc_ids: capa.nc_ids.clone(),
            owner_id: capa.owner_id,
            due_date: capa.due_date,
            closed_at: capa.closed_at,
            details: serde_json::to_value(&details).unwrap_or_else(|_| serde_json::json!({})),
            scope_site_id: None,
            scope_work_center_id: None,
            created_at: capa.created_at,
            updated_at: capa.updated_at,
        }
    }
}

const CAPA_COLUMNS: &str = "c.id, c.capa_number, c.title, c.description, c.capa_type, \
     c.priority, c.status, c.nc_ids, c.owner_id, c.due_date, c.closed_at, c.details, \
     c.scope_site_id, c.scope_work_center_id, c.created_at, c.updated_at";

#[derive(Debug, Clone, sqlx::FromRow)]
struct AuditRow {
    id: Uuid,
    audit_number: String,
    audit_type: String,
    status: String,
    title: String,
    scope: String,
    area: String,
    auditor_id: Option<Uuid>,
    lead_auditor_id: Option<Uuid>,
    scheduled_date: Option<DateTime<Utc>>,
    start_date: Option<DateTime<Utc>>,
    completion_date: Option<DateTime<Utc>>,
    details: serde_json::Value,
    scope_site_id: Option<Uuid>,
    scope_work_center_id: Option<Uuid>,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

impl AuditRow {
    fn to_entity(&self) -> Result<Audit> {
        let checklist_items: Vec<AuditChecklistItem> =
            serde_json::from_value(self.details.clone()).unwrap_or_default();
        Ok(Audit {
            id: self.id,
            audit_number: self.audit_number.clone(),
            audit_type: audit_type_from_db(&self.audit_type)?,
            status: audit_status_from_db(&self.status)?,
            title: self.title.clone(),
            scope: self.scope.clone(),
            area: self.area.clone(),
            auditor_id: self.auditor_id,
            lead_auditor_id: self.lead_auditor_id,
            scheduled_date: self.scheduled_date,
            start_date: self.start_date,
            completion_date: self.completion_date,
            checklist_items,
            created_at: self.created_at,
            updated_at: self.updated_at,
        })
    }

    fn from_entity(audit: &Audit) -> Self {
        Self {
            id: audit.id,
            audit_number: audit.audit_number.clone(),
            audit_type: audit_type_db(audit.audit_type).to_string(),
            status: audit_status_db(audit.status).to_string(),
            title: audit.title.clone(),
            scope: audit.scope.clone(),
            area: audit.area.clone(),
            auditor_id: audit.auditor_id,
            lead_auditor_id: audit.lead_auditor_id,
            scheduled_date: audit.scheduled_date,
            start_date: audit.start_date,
            completion_date: audit.completion_date,
            details: serde_json::to_value(&audit.checklist_items)
                .unwrap_or_else(|_| serde_json::json!([])),
            scope_site_id: None,
            scope_work_center_id: None,
            created_at: audit.created_at,
            updated_at: audit.updated_at,
        }
    }
}

const AUDIT_COLUMNS: &str = "a.id, a.audit_number, a.audit_type, a.status, a.title, a.scope, \
     a.area, a.auditor_id, a.lead_auditor_id, a.scheduled_date, a.start_date, \
     a.completion_date, a.details, a.scope_site_id, a.scope_work_center_id, \
     a.created_at, a.updated_at";

#[derive(Debug, Clone, sqlx::FromRow)]
struct FindingRow {
    id: Uuid,
    audit_id: Uuid,
    finding_number: String,
    severity: String,
    status: String,
    description: String,
    clause: Option<String>,
    area: Option<String>,
    implementation_notes: Option<String>,
    verified_by: Option<Uuid>,
    verification_notes: Option<String>,
    due_date: Option<DateTime<Utc>>,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

impl FindingRow {
    fn to_entity(&self) -> Result<AuditFinding> {
        Ok(AuditFinding {
            id: self.id,
            audit_id: self.audit_id,
            finding_number: self.finding_number.clone(),
            severity: finding_severity_from_db(&self.severity)?,
            status: finding_status_from_db(&self.status)?,
            description: self.description.clone(),
            clause: self.clause.clone(),
            area: self.area.clone(),
            implementation_notes: self.implementation_notes.clone(),
            verified_by: self.verified_by,
            verification_notes: self.verification_notes.clone(),
            due_date: self.due_date,
            created_at: self.created_at,
            updated_at: self.updated_at,
        })
    }
}

// ---------------------------------------------------------------------------
// Scoped fetch helpers (single-record paths; out-of-scope == missing)
// ---------------------------------------------------------------------------

/// Fetch ONE scoped NCR row in a TenantTx of `ctx.tenant`; `Ok(None)`
/// when the id is missing OR outside the caller's scope (item 3:
/// out-of-scope and nonexistent are indistinguishable).
async fn fetch_ncr_row(pool: &PgPool, ctx: &RequestContext, id: Uuid) -> Result<Option<NcrRow>> {
    let mut db = TenantTx::begin(pool, ctx.tenant)
        .await
        .map_err(|e| SenseiError::Database(format!("get_ncr: begin tx: {e}")))?;
    let (pred, bind) = quality_scope_predicate(ctx, "q", 3);
    let sql = format!(
        "SELECT {NCR_COLUMNS} FROM ncr_reports q \
         WHERE q.id=$1 AND q.tenant_id=$2 {pred}"
    );
    let mut q = sqlx::query_as::<_, NcrRow>(&sql).bind(id).bind(ctx.tenant);
    q = bind_scope!(q, bind);
    let row = q
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| db_err("get_ncr", e))?;
    db.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("get_ncr: commit: {e}")))?;
    Ok(row)
}

/// Fetch ONE scoped CAPA row; `Ok(None)` when missing or out of scope.
async fn fetch_capa_row(pool: &PgPool, ctx: &RequestContext, id: Uuid) -> Result<Option<CapaRow>> {
    let mut db = TenantTx::begin(pool, ctx.tenant)
        .await
        .map_err(|e| SenseiError::Database(format!("get_capa: begin tx: {e}")))?;
    let (pred, bind) = quality_scope_predicate(ctx, "c", 3);
    let sql = format!(
        "SELECT {CAPA_COLUMNS} FROM capas c \
         WHERE c.id=$1 AND c.tenant_id=$2 {pred}"
    );
    let mut q = sqlx::query_as::<_, CapaRow>(&sql).bind(id).bind(ctx.tenant);
    q = bind_scope!(q, bind);
    let row = q
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| db_err("get_capa", e))?;
    db.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("get_capa: commit: {e}")))?;
    Ok(row)
}

/// Fetch ONE scoped audit row; `Ok(None)` when missing or out of scope.
async fn fetch_audit_row(
    pool: &PgPool,
    ctx: &RequestContext,
    id: Uuid,
) -> Result<Option<AuditRow>> {
    let mut db = TenantTx::begin(pool, ctx.tenant)
        .await
        .map_err(|e| SenseiError::Database(format!("get_audit: begin tx: {e}")))?;
    let (pred, bind) = quality_scope_predicate(ctx, "a", 3);
    let sql = format!(
        "SELECT {AUDIT_COLUMNS} FROM audits a \
         WHERE a.id=$1 AND a.tenant_id=$2 {pred}"
    );
    let mut q = sqlx::query_as::<_, AuditRow>(&sql)
        .bind(id)
        .bind(ctx.tenant);
    q = bind_scope!(q, bind);
    let row = q
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| db_err("get_audit", e))?;
    db.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("get_audit: commit: {e}")))?;
    Ok(row)
}

// ---------------------------------------------------------------------------
// QualityService implementation
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_arguments)]
#[async_trait]
impl QualityService for DatabaseQualityService {
    // ── NCRs ──────────────────────────────────────────────────────────────

    async fn list_ncrs(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        severity: Option<&str>,
        source: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NonConformance>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;

        // Filters canonicalize to exact DB strings; a filter that matches
        // no canonical value matches zero rows.
        let status_db = status.and_then(|s| canonical_db_value(s, NCR_STATUS_DB));
        let severity_candidates = ["low", "medium", "high", "critical"];
        let severity_db = severity.and_then(|s| canonical_db_value(s, &severity_candidates));
        let source_ok = source.is_some();
        // A filter that matches no canonical DB value matches ZERO rows
        // (mirrors the old post-filter semantics) — short-circuit.
        if (status.is_some() && status_db.is_none())
            || (severity.is_some() && severity_db.is_none())
        {
            return Ok(paginate(Vec::new(), 0, page, pp));
        }

        let mut db = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("list_ncrs: begin tx: {e}")))?;

        // WHERE tenant_id=$1, then one DENSE optional placeholder per
        // filter, then the scope predicate, then LIMIT/OFFSET after
        // every scope placeholder (Postgres binds positionally — the
        // placeholder numbers must never skip).
        let mut filter_sql = String::new();
        let mut next = 2;
        if status_db.is_some() {
            filter_sql.push_str(&format!(" AND q.status = ${next}"));
            next += 1;
        }
        if severity_db.is_some() {
            filter_sql.push_str(&format!(" AND q.severity = ${next}"));
            next += 1;
        }
        if source_ok {
            filter_sql.push_str(&format!(" AND LOWER(q.source) = LOWER(${next})"));
            next += 1;
        }
        let (pred, bind) = quality_scope_predicate(ctx, "q", next);
        let limit_slot = next + scope_slots_used(&bind);
        let rows_sql = format!(
            "SELECT {NCR_COLUMNS} FROM ncr_reports q \
             WHERE q.tenant_id=$1{filter_sql} {pred} \
             ORDER BY q.created_at DESC LIMIT ${limit_slot} OFFSET ${}",
            limit_slot + 1
        );
        let mut rows_q = sqlx::query_as::<_, NcrRow>(&rows_sql).bind(ctx.tenant);
        if let Some(s) = status_db {
            rows_q = rows_q.bind(s);
        }
        if let Some(s) = severity_db {
            rows_q = rows_q.bind(s);
        }
        if let Some(s) = source {
            rows_q = rows_q.bind(s);
        }
        rows_q = bind_scope!(rows_q, bind.clone());
        rows_q = rows_q.bind(pp as i64).bind(off as i64);
        let rows: Vec<NcrRow> = rows_q
            .fetch_all(&mut **db.tx())
            .await
            .map_err(|e| db_err("list_ncrs", e))?;

        let count_sql = format!(
            "SELECT COUNT(*) FROM ncr_reports q \
             WHERE q.tenant_id=$1{filter_sql} {pred}"
        );
        let mut count_q = sqlx::query_scalar::<_, i64>(&count_sql).bind(ctx.tenant);
        if let Some(s) = status_db {
            count_q = count_q.bind(s);
        }
        if let Some(s) = severity_db {
            count_q = count_q.bind(s);
        }
        if let Some(s) = source {
            count_q = count_q.bind(s);
        }
        count_q = bind_scope!(count_q, bind);
        let count: i64 = count_q
            .fetch_one(&mut **db.tx())
            .await
            .map_err(|e| db_err("count_ncrs", e))?;

        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("list_ncrs: commit: {e}")))?;
        let items: Result<Vec<NonConformance>> = rows.iter().map(|r| r.to_entity()).collect();
        Ok(paginate(items?, count, page, pp))
    }

    async fn create_ncr(
        &self,
        ctx: &RequestContext,
        title: String,
        description: String,
        nc_type: NcType,
        severity: NcSeverity,
        product_id: Option<Uuid>,
        process_id: Option<Uuid>,
        defect_code: Option<String>,
        detected_by: Option<Uuid>,
        department: Option<String>,
        location: Option<String>,
        is_recurrence: bool,
    ) -> Result<NonConformance> {
        // Server-stamped scope from the SINGLE creation-scope helper (P0
        // item 8): scoped callers without an operating site are rejected
        // — never silently widened into a corporate record.
        let stamp = super::scope::stamp_from_scope(super::scope::derive_creation_scope(ctx, None)?);
        let now = Utc::now();
        let (id, nc_number) = gen_number("NCR");
        let ncr = NonConformance {
            id,
            nc_number,
            title,
            description,
            nc_type,
            severity,
            product_id,
            process_id,
            defect_code,
            detected_by,
            department,
            location,
            is_recurrence,
            status: NcrStatus::Open,
            source: None,
            root_cause: None,
            root_cause_type: None,
            analysis_method: None,
            disposition: None,
            closed_at: None,
            created_at: now,
            updated_at: now,
        };
        let mut row = NcrRow::from_entity(&ncr);
        row.scope_site_id = stamp.site_id;
        row.scope_work_center_id = stamp.work_center_id;
        // Item 28: the NCR state mutation and its workflow-driving event
        // are ONE transaction — a committed NCR can never lose its event
        // to a post-commit publish failure.
        let mut tx = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("create_ncr: begin tx: {e}")))?;
        sqlx::query(
            "INSERT INTO ncr_reports (id, tenant_id, ncr_number, title, description, nc_type, \
             severity, status, product_id, process_id, defect_code, reported_by, department, \
             location, is_recurrence, source, root_cause, root_cause_type, analysis_method, \
             disposition, closed_at, scope_site_id, scope_work_center_id, created_at, updated_at) \
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25)",
        )
        .bind(row.id)
        .bind(ctx.tenant)
        .bind(&row.ncr_number)
        .bind(&row.title)
        .bind(&row.description)
        .bind(&row.nc_type)
        .bind(&row.severity)
        .bind(&row.status)
        .bind(row.product_id)
        .bind(row.process_id)
        .bind(&row.defect_code)
        .bind(row.reported_by)
        .bind(&row.department)
        .bind(&row.location)
        .bind(row.is_recurrence)
        .bind(&row.source)
        .bind(&row.root_cause)
        .bind(&row.root_cause_type)
        .bind(&row.analysis_method)
        .bind(&row.disposition)
        .bind(row.closed_at)
        .bind(row.scope_site_id)
        .bind(row.scope_work_center_id)
        .bind(row.created_at)
        .bind(row.updated_at)
        .execute(&mut **tx.tx())
        .await
        .map_err(|e| db_err("create_ncr", e))?;
        sensei_db::outbox::enqueue_outbox(
            tx.tx(),
            ctx.tenant,
            "quality_ncr",
            id,
            "sensei.quality.ncr.created",
            serde_json::json!({
                "nc_number": ncr.nc_number,
                "severity": format!("{:?}", ncr.severity),
                "scope_site_id": stamp.site_id.map(|s| s.to_string()),
            }),
        )
        .await?;
        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("create_ncr: commit: {e}")))?;
        // POST echoes the PERSISTED entity (storage resolution: PG keeps
        // microseconds), so create and get always agree.
        let row = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        row.to_entity()
    }

    async fn get_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<NonConformance> {
        let row = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        row.to_entity()
    }

    async fn update_ncr_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        severity: NcSeverity,
    ) -> Result<NonConformance> {
        // Read-then-write inside the caller's scope: an out-of-scope (or
        // missing) NCR is NotFound before anything is mutated.
        let mut row = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        row.severity = nc_severity_db(severity).to_string();
        row.updated_at = Utc::now();
        update_ncr_columns(&self.pool, ctx.tenant, id, &row).await?;
        row.to_entity()
    }

    async fn update_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        ncr: NonConformance,
    ) -> Result<NonConformance> {
        // Read the stored record inside the caller's scope first: the
        // scope stamp is server-owned, so the whole-entity echo can never
        // move the record between sites (item 5).
        let stored = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        let mut row = NcrRow::from_entity(&ncr);
        row.scope_site_id = stored.scope_site_id;
        row.scope_work_center_id = stored.scope_work_center_id;
        row.updated_at = Utc::now();
        let mut echo = ncr;
        echo.updated_at = row.updated_at;
        update_ncr_columns(&self.pool, ctx.tenant, id, &row).await?;
        Ok(echo)
    }

    async fn delete_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<()> {
        // Out-of-scope deletes are indistinguishable from missing ones.
        let mut db = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("delete_ncr: begin tx: {e}")))?;
        let (pred, bind) = quality_scope_predicate(ctx, "q", 3);
        let sql = format!("DELETE FROM ncr_reports q WHERE q.id=$1 AND q.tenant_id=$2 {pred}");
        let mut q = sqlx::query(&sql).bind(id).bind(ctx.tenant);
        q = bind_scope!(q, bind);
        let r = q
            .execute(&mut **db.tx())
            .await
            .map_err(|e| db_err("delete_ncr", e))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("delete_ncr: commit: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(not_found("NCR", id));
        }
        Ok(())
    }

    async fn investigate_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        rca: RootCauseAnalysis,
    ) -> Result<NonConformance> {
        // Read-then-write inside the caller's scope.
        let row = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        let mut ncr = row.to_entity()?;
        if ncr.status == NcrStatus::Closed {
            return Err(SenseiError::Validation(
                "Cannot investigate a closed NCR".to_string(),
            ));
        }
        if ncr.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot investigate a cancelled NCR".to_string(),
            ));
        }
        ncr.root_cause = Some(rca.description);
        ncr.root_cause_type = Some(rca.root_cause_type);
        ncr.analysis_method = Some(rca.analysis_method);
        ncr.status = NcrStatus::UnderInvestigation;
        ncr.updated_at = Utc::now();
        let stamp_site = row.scope_site_id;
        let stamp_wc = row.scope_work_center_id;
        let mut updated = NcrRow::from_entity(&ncr);
        updated.scope_site_id = stamp_site;
        updated.scope_work_center_id = stamp_wc;
        update_ncr_columns(&self.pool, ctx.tenant, id, &updated).await?;
        Ok(ncr)
    }

    async fn disposition_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        disposition: String,
    ) -> Result<NonConformance> {
        if disposition.trim().is_empty() {
            return Err(SenseiError::Validation(
                "Disposition cannot be empty".to_string(),
            ));
        }
        let row = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        let mut ncr = row.to_entity()?;
        if ncr.status == NcrStatus::Closed {
            return Err(SenseiError::Validation(
                "Cannot dispose a closed NCR".to_string(),
            ));
        }
        if ncr.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot dispose a cancelled NCR".to_string(),
            ));
        }
        // Hard rule: a disposition that releases material from a quality
        // hold requires an explicit release decision — the rule engine is
        // the gate, not a text field.
        let releasing_hold = ncr
            .disposition
            .as_deref()
            .is_some_and(|d| d.to_lowercase().contains("release"));
        if releasing_hold {
            crate::tps::rules::check_lot_release(true, true)
                .map_err(|v| SenseiError::Conflict(v.message().to_string()))?;
        }
        ncr.disposition = Some(disposition);
        ncr.status = NcrStatus::ActionDefined;
        ncr.updated_at = Utc::now();
        let stamp_site = row.scope_site_id;
        let stamp_wc = row.scope_work_center_id;
        let mut updated = NcrRow::from_entity(&ncr);
        updated.scope_site_id = stamp_site;
        updated.scope_work_center_id = stamp_wc;
        update_ncr_columns(&self.pool, ctx.tenant, id, &updated).await?;
        Ok(ncr)
    }

    async fn close_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<NonConformance> {
        let row = fetch_ncr_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("NCR", id))?;
        let mut ncr = row.to_entity()?;
        if ncr.status == NcrStatus::Closed {
            return Err(SenseiError::Validation("NCR is already closed".to_string()));
        }
        if ncr.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot close a cancelled NCR".to_string(),
            ));
        }
        let mut missing = Vec::new();
        if ncr.root_cause.is_none() {
            missing.push("root cause analysis");
        }
        if ncr.disposition.is_none() {
            missing.push("disposition");
        }
        if !missing.is_empty() {
            return Err(SenseiError::Validation(format!(
                "Cannot close NCR {id}: missing {}",
                missing.join(", ")
            )));
        }
        ncr.status = NcrStatus::Closed;
        ncr.closed_at = Some(Utc::now());
        ncr.updated_at = Utc::now();
        let stamp_site = row.scope_site_id;
        let stamp_wc = row.scope_work_center_id;
        let mut updated = NcrRow::from_entity(&ncr);
        updated.scope_site_id = stamp_site;
        updated.scope_work_center_id = stamp_wc;
        update_ncr_columns(&self.pool, ctx.tenant, id, &updated).await?;
        Ok(ncr)
    }

    // ── CAPAs ─────────────────────────────────────────────────────────────

    async fn list_capas(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        nc_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CapaExtended>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;

        let status_db = status.and_then(|s| canonical_db_value(s, CAPA_STATUS_DB));
        // The API exposes `nc_type` but the model uses `capa_type`.
        let type_db = nc_type.and_then(|t| {
            canonical_db_value(t, NC_TYPE_DB)
                .or_else(|| canonical_db_value(t, &["corrective", "preventive", "improvement"]))
        });
        if (status.is_some() && status_db.is_none()) || (nc_type.is_some() && type_db.is_none()) {
            return Ok(paginate(Vec::new(), 0, page, pp));
        }

        let mut db = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("list_capas: begin tx: {e}")))?;
        let mut filter_sql = String::new();
        let mut next = 2;
        if status_db.is_some() {
            filter_sql.push_str(&format!(" AND c.status = ${next}"));
            next += 1;
        }
        if type_db.is_some() {
            filter_sql.push_str(&format!(" AND c.capa_type = ${next}"));
            next += 1;
        }
        let (pred, bind) = quality_scope_predicate(ctx, "c", next);
        let limit_slot = next + scope_slots_used(&bind);
        let rows_sql = format!(
            "SELECT {CAPA_COLUMNS} FROM capas c \
             WHERE c.tenant_id=$1{filter_sql} {pred} \
             ORDER BY c.created_at DESC LIMIT ${limit_slot} OFFSET ${}",
            limit_slot + 1
        );
        let mut rows_q = sqlx::query_as::<_, CapaRow>(&rows_sql).bind(ctx.tenant);
        if let Some(s) = status_db {
            rows_q = rows_q.bind(s);
        }
        if let Some(t) = type_db {
            rows_q = rows_q.bind(t);
        }
        rows_q = bind_scope!(rows_q, bind.clone());
        rows_q = rows_q.bind(pp as i64).bind(off as i64);
        let rows: Vec<CapaRow> = rows_q
            .fetch_all(&mut **db.tx())
            .await
            .map_err(|e| db_err("list_capas", e))?;

        let count_sql = format!(
            "SELECT COUNT(*) FROM capas c \
             WHERE c.tenant_id=$1{filter_sql} {pred}"
        );
        let mut count_q = sqlx::query_scalar::<_, i64>(&count_sql).bind(ctx.tenant);
        if let Some(s) = status_db {
            count_q = count_q.bind(s);
        }
        if let Some(t) = type_db {
            count_q = count_q.bind(t);
        }
        count_q = bind_scope!(count_q, bind);
        let count: i64 = count_q
            .fetch_one(&mut **db.tx())
            .await
            .map_err(|e| db_err("count_capas", e))?;

        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("list_capas: commit: {e}")))?;
        let items: Result<Vec<CapaExtended>> = rows.iter().map(|r| r.to_entity()).collect();
        Ok(paginate(items?, count, page, pp))
    }

    async fn create_capa(
        &self,
        ctx: &RequestContext,
        title: String,
        description: String,
        nc_ids: Vec<Uuid>,
        capa_type: CapaType,
        priority: CapaPriority,
        owner_id: Option<Uuid>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<CapaExtended> {
        let stamp = super::scope::stamp_from_scope(super::scope::derive_creation_scope(ctx, None)?);
        let now = Utc::now();
        let (id, capa_number) = gen_number("CAPA");
        let capa = CapaExtended {
            id,
            capa_number,
            title,
            description,
            nc_ids,
            capa_type,
            priority,
            status: CapaStatusEx::Draft,
            root_cause_analyses: vec![],
            actions: vec![],
            closure_gates: vec![],
            effectiveness_checks: vec![],
            entity_links: vec![],
            owner_id,
            due_date,
            closed_at: None,
            created_at: now,
            updated_at: now,
        };
        let mut row = CapaRow::from_entity(&capa);
        row.scope_site_id = stamp.site_id;
        row.scope_work_center_id = stamp.work_center_id;
        // Item 28: CAPA creation + its workflow-driving event are atomic.
        let mut tx = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("create_capa: begin tx: {e}")))?;
        sqlx::query(
            "INSERT INTO capas (id, tenant_id, capa_number, title, description, capa_type, \
             priority, status, nc_ids, owner_id, due_date, closed_at, details, \
             scope_site_id, scope_work_center_id, created_at, updated_at) \
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)",
        )
        .bind(row.id)
        .bind(ctx.tenant)
        .bind(&row.capa_number)
        .bind(&row.title)
        .bind(&row.description)
        .bind(&row.capa_type)
        .bind(&row.priority)
        .bind(&row.status)
        .bind(&row.nc_ids)
        .bind(row.owner_id)
        .bind(row.due_date)
        .bind(row.closed_at)
        .bind(&row.details)
        .bind(row.scope_site_id)
        .bind(row.scope_work_center_id)
        .bind(row.created_at)
        .bind(row.updated_at)
        .execute(&mut **tx.tx())
        .await
        .map_err(|e| db_err("create_capa", e))?;
        sensei_db::outbox::enqueue_outbox(
            tx.tx(),
            ctx.tenant,
            "quality_capa",
            id,
            "sensei.quality.capa.created",
            serde_json::json!({
                "capa_number": capa.capa_number,
                "priority": format!("{:?}", capa.priority),
                "scope_site_id": stamp.site_id.map(|s| s.to_string()),
            }),
        )
        .await?;
        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("create_capa: commit: {e}")))?;
        // POST echoes the PERSISTED entity (storage resolution: PG keeps
        // microseconds), so create and get always agree.
        let row = fetch_capa_row(&self.pool, ctx, capa.id)
            .await?
            .ok_or_else(|| not_found("CAPA", capa.id))?;
        row.to_entity()
    }

    async fn get_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended> {
        let row = fetch_capa_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("CAPA", id))?;
        row.to_entity()
    }

    async fn update_capa_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        status: CapaStatusEx,
    ) -> Result<CapaExtended> {
        // Read-then-write inside the caller's scope.
        let mut row = fetch_capa_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("CAPA", id))?;
        row.status = capa_status_db(status).to_string();
        if status == CapaStatusEx::Closed {
            row.closed_at = Some(Utc::now());
        }
        row.updated_at = Utc::now();
        update_capa_columns(&self.pool, ctx.tenant, id, &row).await?;
        row.to_entity()
    }

    async fn update_capa(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        capa: CapaExtended,
    ) -> Result<CapaExtended> {
        // Read the stored record inside the caller's scope first: the
        // scope stamp is server-owned (item 5).
        let stored = fetch_capa_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("CAPA", id))?;
        let mut row = CapaRow::from_entity(&capa);
        row.scope_site_id = stored.scope_site_id;
        row.scope_work_center_id = stored.scope_work_center_id;
        row.updated_at = Utc::now();
        let mut echo = capa;
        echo.updated_at = row.updated_at;
        update_capa_columns(&self.pool, ctx.tenant, id, &row).await?;
        Ok(echo)
    }

    async fn delete_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<()> {
        let mut db = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("delete_capa: begin tx: {e}")))?;
        let (pred, bind) = quality_scope_predicate(ctx, "c", 3);
        let sql = format!("DELETE FROM capas c WHERE c.id=$1 AND c.tenant_id=$2 {pred}");
        let mut q = sqlx::query(&sql).bind(id).bind(ctx.tenant);
        q = bind_scope!(q, bind);
        let r = q
            .execute(&mut **db.tx())
            .await
            .map_err(|e| db_err("delete_capa", e))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("delete_capa: commit: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(not_found("CAPA", id));
        }
        Ok(())
    }

    async fn verify_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended> {
        let row = fetch_capa_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("CAPA", id))?;
        let mut capa = row.to_entity()?;
        if capa.status == CapaStatusEx::Closed {
            return Err(SenseiError::Validation(
                "Cannot verify a closed CAPA".to_string(),
            ));
        }
        if capa.status == CapaStatusEx::Cancelled || capa.status == CapaStatusEx::Rejected {
            return Err(SenseiError::Validation(
                "Cannot verify a cancelled/rejected CAPA".to_string(),
            ));
        }
        if capa.root_cause_analyses.is_empty() {
            return Err(SenseiError::Validation(
                "Cannot verify CAPA without a root cause analysis".to_string(),
            ));
        }
        if capa.actions.is_empty() {
            return Err(SenseiError::Validation(
                "Cannot verify CAPA without corrective actions".to_string(),
            ));
        }
        capa.status = CapaStatusEx::Verification;
        // Record the verification as an effectiveness check so the result is
        // traceable, mirroring the in-memory implementation.
        capa.effectiveness_checks.push(EffectivenessCheck {
            id: Uuid::new_v4(),
            capa_id: id,
            check_method: "verification_review".to_string(),
            results: "Corrective actions verified against the defined plan".to_string(),
            is_effective: true,
            checked_by: None,
            checked_at: Some(Utc::now()),
            follow_up_needed: false,
            follow_up_actions: Vec::new(),
            created_at: Utc::now(),
        });
        capa.updated_at = Utc::now();
        let stamp_site = row.scope_site_id;
        let stamp_wc = row.scope_work_center_id;
        let mut updated = CapaRow::from_entity(&capa);
        updated.scope_site_id = stamp_site;
        updated.scope_work_center_id = stamp_wc;
        update_capa_columns(&self.pool, ctx.tenant, id, &updated).await?;
        Ok(capa)
    }

    async fn close_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended> {
        self.update_capa_status(ctx, id, CapaStatusEx::Closed).await
    }

    // ── Audits ────────────────────────────────────────────────────────────

    async fn list_audits(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        audit_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Audit>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;

        let status_candidates = [
            "planned",
            "scheduled",
            "in_progress",
            "completed",
            "closed",
            "cancelled",
        ];
        let type_candidates = [
            "internal",
            "external",
            "supplier",
            "regulatory",
            "certification",
            "layered",
            "process",
            "product",
            "system",
        ];
        let status_db = status.and_then(|s| canonical_db_value(s, &status_candidates));
        let type_db = audit_type.and_then(|t| canonical_db_value(t, &type_candidates));
        if (status.is_some() && status_db.is_none()) || (audit_type.is_some() && type_db.is_none())
        {
            return Ok(paginate(Vec::new(), 0, page, pp));
        }

        let mut db = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("list_audits: begin tx: {e}")))?;
        let mut filter_sql = String::new();
        let mut next = 2;
        if status_db.is_some() {
            filter_sql.push_str(&format!(" AND a.status = ${next}"));
            next += 1;
        }
        if type_db.is_some() {
            filter_sql.push_str(&format!(" AND a.audit_type = ${next}"));
            next += 1;
        }
        let (pred, bind) = quality_scope_predicate(ctx, "a", next);
        let limit_slot = next + scope_slots_used(&bind);
        let rows_sql = format!(
            "SELECT {AUDIT_COLUMNS} FROM audits a \
             WHERE a.tenant_id=$1{filter_sql} {pred} \
             ORDER BY a.created_at DESC LIMIT ${limit_slot} OFFSET ${}",
            limit_slot + 1
        );
        let mut rows_q = sqlx::query_as::<_, AuditRow>(&rows_sql).bind(ctx.tenant);
        if let Some(s) = status_db {
            rows_q = rows_q.bind(s);
        }
        if let Some(t) = type_db {
            rows_q = rows_q.bind(t);
        }
        rows_q = bind_scope!(rows_q, bind.clone());
        rows_q = rows_q.bind(pp as i64).bind(off as i64);
        let rows: Vec<AuditRow> = rows_q
            .fetch_all(&mut **db.tx())
            .await
            .map_err(|e| db_err("list_audits", e))?;

        let count_sql = format!(
            "SELECT COUNT(*) FROM audits a \
             WHERE a.tenant_id=$1{filter_sql} {pred}"
        );
        let mut count_q = sqlx::query_scalar::<_, i64>(&count_sql).bind(ctx.tenant);
        if let Some(s) = status_db {
            count_q = count_q.bind(s);
        }
        if let Some(t) = type_db {
            count_q = count_q.bind(t);
        }
        count_q = bind_scope!(count_q, bind);
        let count: i64 = count_q
            .fetch_one(&mut **db.tx())
            .await
            .map_err(|e| db_err("count_audits", e))?;

        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("list_audits: commit: {e}")))?;
        let items: Result<Vec<Audit>> = rows.iter().map(|r| r.to_entity()).collect();
        Ok(paginate(items?, count, page, pp))
    }

    async fn create_audit(&self, ctx: &RequestContext, mut audit: Audit) -> Result<Audit> {
        let stamp = super::scope::stamp_from_scope(super::scope::derive_creation_scope(ctx, None)?);
        let now = Utc::now();
        audit.id = Uuid::new_v4();
        audit.created_at = now;
        audit.updated_at = now;
        // Server-stamped resource scope: any scope keys in the
        // client-supplied body are OVERRIDDEN here — client input never
        // sets the scope.
        let mut row = AuditRow::from_entity(&audit);
        row.scope_site_id = stamp.site_id;
        row.scope_work_center_id = stamp.work_center_id;
        let mut tx = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("create_audit: begin tx: {e}")))?;
        sqlx::query(
            "INSERT INTO audits (id, tenant_id, audit_number, audit_type, status, title, \
             scope, area, auditor_id, lead_auditor_id, scheduled_date, start_date, \
             completion_date, details, scope_site_id, scope_work_center_id, created_at, \
             updated_at) \
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)",
        )
        .bind(row.id)
        .bind(ctx.tenant)
        .bind(&row.audit_number)
        .bind(&row.audit_type)
        .bind(&row.status)
        .bind(&row.title)
        .bind(&row.scope)
        .bind(&row.area)
        .bind(row.auditor_id)
        .bind(row.lead_auditor_id)
        .bind(row.scheduled_date)
        .bind(row.start_date)
        .bind(row.completion_date)
        .bind(&row.details)
        .bind(row.scope_site_id)
        .bind(row.scope_work_center_id)
        .bind(row.created_at)
        .bind(row.updated_at)
        .execute(&mut **tx.tx())
        .await
        .map_err(|e| db_err("create_audit", e))?;
        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("create_audit: commit: {e}")))?;
        // POST echoes the PERSISTED entity (storage resolution: PG keeps
        // microseconds), so create and get always agree.
        let row = fetch_audit_row(&self.pool, ctx, audit.id)
            .await?
            .ok_or_else(|| not_found("Audit", audit.id))?;
        row.to_entity()
    }

    async fn get_audit(&self, ctx: &RequestContext, id: Uuid) -> Result<Audit> {
        let row = fetch_audit_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("Audit", id))?;
        row.to_entity()
    }

    async fn update_audit(&self, ctx: &RequestContext, id: Uuid, audit: Audit) -> Result<Audit> {
        // Read the stored record inside the caller's scope first: the
        // scope stamp is server-owned (item 5).
        let stored = fetch_audit_row(&self.pool, ctx, id)
            .await?
            .ok_or_else(|| not_found("Audit", id))?;
        let mut row = AuditRow::from_entity(&audit);
        row.scope_site_id = stored.scope_site_id;
        row.scope_work_center_id = stored.scope_work_center_id;
        row.updated_at = Utc::now();
        let mut echo = audit;
        echo.updated_at = row.updated_at;
        update_audit_columns(&self.pool, ctx.tenant, id, &row).await?;
        Ok(echo)
    }

    async fn delete_audit(&self, ctx: &RequestContext, id: Uuid) -> Result<()> {
        let mut db = TenantTx::begin(&self.pool, ctx.tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("delete_audit: begin tx: {e}")))?;
        let (pred, bind) = quality_scope_predicate(ctx, "a", 3);
        let sql = format!("DELETE FROM audits a WHERE a.id=$1 AND a.tenant_id=$2 {pred}");
        let mut q = sqlx::query(&sql).bind(id).bind(ctx.tenant);
        q = bind_scope!(q, bind);
        let r = q
            .execute(&mut **db.tx())
            .await
            .map_err(|e| db_err("delete_audit", e))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("delete_audit: commit: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Audit", id));
        }
        Ok(())
    }

    async fn list_audit_findings(
        &self,
        ctx: &RequestContext,
        audit_id: Uuid,
    ) -> Result<Vec<AuditFinding>> {
        // The parent audit is scope-checked first (item 3): findings of
        // an out-of-scope audit are indistinguishable from a missing one.
        let _ = self.get_audit(ctx, audit_id).await?;
        let rows: Vec<FindingRow> = sqlx::query_as(
            "SELECT f.id, f.audit_id, f.finding_number, f.severity, f.status, f.description, \
             f.clause, f.area, f.implementation_notes, f.verified_by, f.verification_notes, \
             f.due_date, f.created_at, f.updated_at \
             FROM audit_findings f WHERE f.audit_id=$1 AND f.tenant_id=$2 \
             ORDER BY f.created_at ASC",
        )
        .bind(audit_id)
        .bind(ctx.tenant)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| db_err("list_findings", e))?;
        let items: Result<Vec<AuditFinding>> = rows.iter().map(|r| r.to_entity()).collect();
        items
    }

    // ── Unsupported-in-DB-mode families ───────────────────────────────────
    // The trait families below have no faithful canonical relational home
    // in the 001..172 chain; the DB implementation refuses them explicitly
    // instead of fabricating JSONB `quality_*` tables (see the module
    // docs). The in-memory service serves them in dev mode.

    async fn list_first_article_inspections(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<FirstArticleInspection>> {
        Err(unsupported("first-article inspections"))
    }

    async fn create_first_article_inspection(
        &self,
        _tenant_id: Uuid,
        _fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection> {
        Err(unsupported("first-article inspections"))
    }

    async fn list_self_inspections(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SelfInspection>> {
        Err(unsupported("self-inspections"))
    }

    async fn create_self_inspection(
        &self,
        _tenant_id: Uuid,
        _inspection: SelfInspection,
    ) -> Result<SelfInspection> {
        Err(unsupported("self-inspections"))
    }

    async fn list_supplier_scorecards(
        &self,
        _tenant_id: Uuid,
        _supplier_id: Option<Uuid>,
        _period: Option<&str>,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SupplierScorecard>> {
        Err(unsupported("supplier scorecards"))
    }

    async fn create_supplier_evaluation(
        &self,
        _tenant_id: Uuid,
        _scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard> {
        Err(unsupported("supplier scorecards"))
    }

    async fn list_scars(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Scar>> {
        Err(unsupported("SCARs"))
    }

    async fn list_documents(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<QmsDocument>> {
        Err(unsupported("QMS documents"))
    }

    async fn list_msa_studies(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MsaStudy>> {
        Err(unsupported("MSA studies"))
    }

    async fn list_process_capability_studies(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProcessCapabilityStudy>> {
        Err(unsupported("process capability studies"))
    }

    async fn list_control_plans(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ControlPlan>> {
        Err(unsupported("control plans"))
    }

    async fn list_pfmeas(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PfmeaLite>> {
        Err(unsupported("PFMEAs"))
    }

    async fn list_npi_projects(
        &self,
        _tenant_id: Uuid,
        _stage: Option<&str>,
        _status: Option<&str>,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiProject>> {
        Err(unsupported("NPI projects"))
    }

    async fn list_npi_risks(
        &self,
        _tenant_id: Uuid,
        _project_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiRisk>> {
        Err(unsupported("NPI risks"))
    }

    async fn list_gauges(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Gauge>> {
        Err(unsupported("gauges"))
    }

    async fn list_complaints(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CustomerComplaint>> {
        Err(unsupported("customer complaints"))
    }

    async fn list_eight_d_reports(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EightDReport>> {
        Err(unsupported("8D reports"))
    }

    async fn list_management_reviews(
        &self,
        _tenant_id: Uuid,
        _page: Option<usize>,
        _per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ManagementReview>> {
        Err(unsupported("management reviews"))
    }

    async fn update_first_article_inspection(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection> {
        Err(unsupported("first-article inspections"))
    }

    async fn delete_first_article_inspection(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("first-article inspections"))
    }

    async fn update_self_inspection(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _inspection: SelfInspection,
    ) -> Result<SelfInspection> {
        Err(unsupported("self-inspections"))
    }

    async fn delete_self_inspection(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("self-inspections"))
    }

    async fn update_supplier_scorecard(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard> {
        Err(unsupported("supplier scorecards"))
    }

    async fn delete_supplier_scorecard(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("supplier scorecards"))
    }

    async fn create_scar(&self, _tenant_id: Uuid, _scar: Scar) -> Result<Scar> {
        Err(unsupported("SCARs"))
    }

    async fn update_scar(&self, _tenant_id: Uuid, _id: Uuid, _scar: Scar) -> Result<Scar> {
        Err(unsupported("SCARs"))
    }

    async fn delete_scar(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("SCARs"))
    }

    async fn create_document(&self, _tenant_id: Uuid, _doc: QmsDocument) -> Result<QmsDocument> {
        Err(unsupported("QMS documents"))
    }

    async fn update_document(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _doc: QmsDocument,
    ) -> Result<QmsDocument> {
        Err(unsupported("QMS documents"))
    }

    async fn delete_document(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("QMS documents"))
    }

    async fn create_msa_study(&self, _tenant_id: Uuid, _study: MsaStudy) -> Result<MsaStudy> {
        Err(unsupported("MSA studies"))
    }

    async fn delete_msa_study(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("MSA studies"))
    }

    async fn create_process_capability_study(
        &self,
        _tenant_id: Uuid,
        _study: ProcessCapabilityStudy,
    ) -> Result<ProcessCapabilityStudy> {
        Err(unsupported("process capability studies"))
    }

    async fn delete_process_capability_study(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("process capability studies"))
    }

    async fn create_control_plan(&self, _tenant_id: Uuid, _cp: ControlPlan) -> Result<ControlPlan> {
        Err(unsupported("control plans"))
    }

    async fn update_control_plan(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _cp: ControlPlan,
    ) -> Result<ControlPlan> {
        Err(unsupported("control plans"))
    }

    async fn delete_control_plan(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("control plans"))
    }

    async fn create_pfmea(&self, _tenant_id: Uuid, _pfmea: PfmeaLite) -> Result<PfmeaLite> {
        Err(unsupported("PFMEAs"))
    }

    async fn delete_pfmea(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("PFMEAs"))
    }

    async fn create_npi_project(
        &self,
        _tenant_id: Uuid,
        _project: NpiProject,
    ) -> Result<NpiProject> {
        Err(unsupported("NPI projects"))
    }

    async fn update_npi_project(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _project: NpiProject,
    ) -> Result<NpiProject> {
        Err(unsupported("NPI projects"))
    }

    async fn delete_npi_project(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("NPI projects"))
    }

    async fn create_gauge(&self, _tenant_id: Uuid, _gauge: Gauge) -> Result<Gauge> {
        Err(unsupported("gauges"))
    }

    async fn update_gauge(&self, _tenant_id: Uuid, _id: Uuid, _gauge: Gauge) -> Result<Gauge> {
        Err(unsupported("gauges"))
    }

    async fn delete_gauge(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("gauges"))
    }

    async fn create_complaint(
        &self,
        _tenant_id: Uuid,
        _complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint> {
        Err(unsupported("customer complaints"))
    }

    async fn update_complaint(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint> {
        Err(unsupported("customer complaints"))
    }

    async fn delete_complaint(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("customer complaints"))
    }

    async fn create_eight_d_report(
        &self,
        _tenant_id: Uuid,
        _report: EightDReport,
    ) -> Result<EightDReport> {
        Err(unsupported("8D reports"))
    }

    async fn update_eight_d_report(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _report: EightDReport,
    ) -> Result<EightDReport> {
        Err(unsupported("8D reports"))
    }

    async fn delete_eight_d_report(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("8D reports"))
    }

    async fn create_management_review(
        &self,
        _tenant_id: Uuid,
        _review: ManagementReview,
    ) -> Result<ManagementReview> {
        Err(unsupported("management reviews"))
    }

    async fn update_management_review(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
        _review: ManagementReview,
    ) -> Result<ManagementReview> {
        Err(unsupported("management reviews"))
    }

    async fn delete_management_review(&self, _tenant_id: Uuid, _id: Uuid) -> Result<()> {
        Err(unsupported("management reviews"))
    }

    async fn get_scar(&self, _tenant_id: Uuid, _id: Uuid) -> Result<Scar> {
        Err(unsupported("SCARs"))
    }

    async fn get_document(&self, _tenant_id: Uuid, _id: Uuid) -> Result<QmsDocument> {
        Err(unsupported("QMS documents"))
    }

    async fn get_first_article_inspection(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
    ) -> Result<FirstArticleInspection> {
        Err(unsupported("first-article inspections"))
    }

    async fn get_self_inspection(&self, _tenant_id: Uuid, _id: Uuid) -> Result<SelfInspection> {
        Err(unsupported("self-inspections"))
    }

    async fn get_msa_study(&self, _tenant_id: Uuid, _id: Uuid) -> Result<MsaStudy> {
        Err(unsupported("MSA studies"))
    }

    async fn get_process_capability_study(
        &self,
        _tenant_id: Uuid,
        _id: Uuid,
    ) -> Result<ProcessCapabilityStudy> {
        Err(unsupported("process capability studies"))
    }

    async fn get_control_plan(&self, _tenant_id: Uuid, _id: Uuid) -> Result<ControlPlan> {
        Err(unsupported("control plans"))
    }

    async fn get_pfmea(&self, _tenant_id: Uuid, _id: Uuid) -> Result<PfmeaLite> {
        Err(unsupported("PFMEAs"))
    }

    async fn get_gauge(&self, _tenant_id: Uuid, _id: Uuid) -> Result<Gauge> {
        Err(unsupported("gauges"))
    }

    async fn get_complaint(&self, _tenant_id: Uuid, _id: Uuid) -> Result<CustomerComplaint> {
        Err(unsupported("customer complaints"))
    }

    async fn get_eight_d_report(&self, _tenant_id: Uuid, _id: Uuid) -> Result<EightDReport> {
        Err(unsupported("8D reports"))
    }

    async fn get_management_review(&self, _tenant_id: Uuid, _id: Uuid) -> Result<ManagementReview> {
        Err(unsupported("management reviews"))
    }
}

// ---------------------------------------------------------------------------
// Column writers (whole-row UPDATE; the caller already proved scope on
// the read side of the read-then-write path)
// ---------------------------------------------------------------------------

const NCR_UPDATE_SET: &str = "ncr_number=$2, title=$3, description=$4, nc_type=$5, \
     severity=$6, status=$7, product_id=$8, process_id=$9, defect_code=$10, \
     reported_by=$11, department=$12, location=$13, is_recurrence=$14, source=$15, \
     root_cause=$16, root_cause_type=$17, analysis_method=$18, disposition=$19, \
     closed_at=$20, scope_site_id=$21, scope_work_center_id=$22, updated_at=$23";

async fn update_ncr_columns(pool: &PgPool, tenant_id: Uuid, id: Uuid, row: &NcrRow) -> Result<()> {
    sqlx::query(&format!(
        "UPDATE ncr_reports SET {NCR_UPDATE_SET} WHERE id=$1 AND tenant_id=$24"
    ))
    .bind(id)
    .bind(&row.ncr_number)
    .bind(&row.title)
    .bind(&row.description)
    .bind(&row.nc_type)
    .bind(&row.severity)
    .bind(&row.status)
    .bind(row.product_id)
    .bind(row.process_id)
    .bind(&row.defect_code)
    .bind(row.reported_by)
    .bind(&row.department)
    .bind(&row.location)
    .bind(row.is_recurrence)
    .bind(&row.source)
    .bind(&row.root_cause)
    .bind(&row.root_cause_type)
    .bind(&row.analysis_method)
    .bind(&row.disposition)
    .bind(row.closed_at)
    .bind(row.scope_site_id)
    .bind(row.scope_work_center_id)
    .bind(row.updated_at)
    .bind(tenant_id)
    .execute(pool)
    .await
    .map_err(|e| db_err("update_ncr", e))?;
    Ok(())
}

const CAPA_UPDATE_SET: &str = "capa_number=$2, title=$3, description=$4, capa_type=$5, \
     priority=$6, status=$7, nc_ids=$8, owner_id=$9, due_date=$10, closed_at=$11, \
     details=$12, scope_site_id=$13, scope_work_center_id=$14, updated_at=$15";

async fn update_capa_columns(
    pool: &PgPool,
    tenant_id: Uuid,
    id: Uuid,
    row: &CapaRow,
) -> Result<()> {
    sqlx::query(&format!(
        "UPDATE capas SET {CAPA_UPDATE_SET} WHERE id=$1 AND tenant_id=$16"
    ))
    .bind(id)
    .bind(&row.capa_number)
    .bind(&row.title)
    .bind(&row.description)
    .bind(&row.capa_type)
    .bind(&row.priority)
    .bind(&row.status)
    .bind(&row.nc_ids)
    .bind(row.owner_id)
    .bind(row.due_date)
    .bind(row.closed_at)
    .bind(&row.details)
    .bind(row.scope_site_id)
    .bind(row.scope_work_center_id)
    .bind(row.updated_at)
    .bind(tenant_id)
    .execute(pool)
    .await
    .map_err(|e| db_err("update_capa", e))?;
    Ok(())
}

const AUDIT_UPDATE_SET: &str = "audit_number=$2, audit_type=$3, status=$4, title=$5, \
     scope=$6, area=$7, auditor_id=$8, lead_auditor_id=$9, scheduled_date=$10, \
     start_date=$11, completion_date=$12, details=$13, scope_site_id=$14, \
     scope_work_center_id=$15, updated_at=$16";

async fn update_audit_columns(
    pool: &PgPool,
    tenant_id: Uuid,
    id: Uuid,
    row: &AuditRow,
) -> Result<()> {
    sqlx::query(&format!(
        "UPDATE audits SET {AUDIT_UPDATE_SET} WHERE id=$1 AND tenant_id=$17"
    ))
    .bind(id)
    .bind(&row.audit_number)
    .bind(&row.audit_type)
    .bind(&row.status)
    .bind(&row.title)
    .bind(&row.scope)
    .bind(&row.area)
    .bind(row.auditor_id)
    .bind(row.lead_auditor_id)
    .bind(row.scheduled_date)
    .bind(row.start_date)
    .bind(row.completion_date)
    .bind(&row.details)
    .bind(row.scope_site_id)
    .bind(row.scope_work_center_id)
    .bind(row.updated_at)
    .bind(tenant_id)
    .execute(pool)
    .await
    .map_err(|e| db_err("update_audit", e))?;
    Ok(())
}

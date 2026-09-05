//! Quality domain service trait and in-memory implementation.
//!
//! Provides a comprehensive set of methods for managing quality processes:
//! NCRs, CAPAs, inspections, audits, supplier evaluations, and more.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::domain::events::{
    CAPACreatedEvent, DomainEvent, NcrCreatedEvent, SupplierEvaluatedEvent,
};
use sensei_core::domain::{AuthorizedScope, RequestContext};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_event_bus::bus::EventBus;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

use super::models::*;

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Quality service trait covering NCR, CAPA, inspection, audit, supplier,
/// NPI risk, MSA/SPC, gauge, complaint, 8D, and management review workflows.
///
/// # Request contexts (twenty-ninth audit Wave B items 6-8)
///
/// The NCR / CAPA / audit operational methods take the server-created
/// [`RequestContext`] instead of a naked `tenant_id`: `ctx.tenant` is the
/// tenant, and `ctx.scope` is the caller's DB-resolved authorization
/// boundary. List/get/update/close surface semantics:
///
/// - `Operational` (site grants) — the caller sees ONLY records whose
///   SERVER-STAMPED `scope_site_id` is among the granted sites; a
///   record with no site stamp (`NULL` — a corporate/tenant-level
///   record) is invisible to a site-scoped caller;
/// - `TenantWide` — no scope predicate: every record of the tenant,
///   corporate records included;
/// - `NoOperationalScope` — zero rows on lists, `NotFound` on gets
///   (FAIL-CLOSED: no entitlement → no data).
///
/// Creation stamps the record server-side from the caller's validated
/// operating focus (see [`QualityScopeStamp`]); client input can never
/// set the scope columns — on whole-entity updates the stored stamp is
/// preserved.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait QualityService: Send + Sync {
    // ── NCRs ──────────────────────────────────────────────────────────────
    /// List NCRs with optional filters, intersected with the caller's
    /// scope at the record level.
    async fn list_ncrs(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        severity: Option<&str>,
        source: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NonConformance>>;

    /// Create a new NCR, server-stamped with the caller's operating scope.
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
    ) -> Result<NonConformance>;

    /// Get a specific NCR by ID — out-of-scope and nonexistent ids are
    /// indistinguishable: both `NotFound`.
    async fn get_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<NonConformance>;

    /// Update NCR status (severity, etc.).
    async fn update_ncr_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        severity: NcSeverity,
    ) -> Result<NonConformance>;

    // ── CAPAs ─────────────────────────────────────────────────────────────
    /// List CAPAs with optional filters, intersected with the caller's
    /// scope at the record level.
    async fn list_capas(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        nc_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CapaExtended>>;

    /// Create a new CAPA, server-stamped with the caller's operating scope.
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
    ) -> Result<CapaExtended>;

    /// Get a specific CAPA by ID — out-of-scope and nonexistent ids are
    /// indistinguishable: both `NotFound`.
    async fn get_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended>;

    /// Update CAPA status.
    async fn update_capa_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        status: CapaStatusEx,
    ) -> Result<CapaExtended>;

    // ── Inspections ───────────────────────────────────────────────────────
    /// List first article inspections with pagination.
    async fn list_first_article_inspections(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<FirstArticleInspection>>;

    /// Create a first article inspection.
    async fn create_first_article_inspection(
        &self,
        tenant_id: Uuid,
        fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection>;

    /// List self-inspections with pagination.
    async fn list_self_inspections(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SelfInspection>>;

    /// Create a self-inspection.
    async fn create_self_inspection(
        &self,
        tenant_id: Uuid,
        inspection: SelfInspection,
    ) -> Result<SelfInspection>;

    // ── Audits ────────────────────────────────────────────────────────────
    /// List audits with optional filters, intersected with the caller's
    /// scope at the record level.
    async fn list_audits(
        &self,
        ctx: &RequestContext,
        status: Option<&str>,
        audit_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Audit>>;

    /// Create a new audit, server-stamped with the caller's operating
    /// scope — any scope fields in the client body are overridden.
    async fn create_audit(&self, ctx: &RequestContext, audit: Audit) -> Result<Audit>;

    /// Get a specific audit by ID — out-of-scope and nonexistent ids are
    /// indistinguishable: both `NotFound`.
    async fn get_audit(&self, ctx: &RequestContext, id: Uuid) -> Result<Audit>;

    /// List audit findings for a specific audit (the parent audit is
    /// scope-checked first).
    async fn list_audit_findings(
        &self,
        ctx: &RequestContext,
        audit_id: Uuid,
    ) -> Result<Vec<AuditFinding>>;

    // ── Supplier Quality ──────────────────────────────────────────────────
    /// List supplier scorecards with pagination.
    async fn list_supplier_scorecards(
        &self,
        tenant_id: Uuid,
        supplier_id: Option<Uuid>,
        period: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SupplierScorecard>>;

    /// Create a supplier evaluation (scorecard).
    async fn create_supplier_evaluation(
        &self,
        tenant_id: Uuid,
        scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard>;

    /// List SCARs with pagination.
    async fn list_scars(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Scar>>;

    // ── Documents ─────────────────────────────────────────────────────────
    /// List QMS documents with pagination.
    async fn list_documents(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<QmsDocument>>;

    // ── MSA / SPC / Process Capability ────────────────────────────────────
    /// List MSA studies with pagination.
    async fn list_msa_studies(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MsaStudy>>;

    /// List process capability studies with pagination.
    async fn list_process_capability_studies(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProcessCapabilityStudy>>;

    /// List control plans with pagination.
    async fn list_control_plans(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ControlPlan>>;

    /// List PFMEAs with pagination.
    async fn list_pfmeas(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PfmeaLite>>;

    // ── NPI ───────────────────────────────────────────────────────────────
    /// List NPI projects with pagination.
    async fn list_npi_projects(
        &self,
        tenant_id: Uuid,
        stage: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiProject>>;

    /// List NPI risks for a specific project with pagination.
    async fn list_npi_risks(
        &self,
        tenant_id: Uuid,
        project_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiRisk>>;

    // ── Gauges / Equipment ────────────────────────────────────────────────
    /// List gauges with pagination.
    async fn list_gauges(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Gauge>>;

    // ── Complaints / 8D / Reviews ─────────────────────────────────────────
    /// List customer complaints with pagination.
    async fn list_complaints(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CustomerComplaint>>;

    /// List 8D reports with pagination.
    async fn list_eight_d_reports(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EightDReport>>;

    /// List management reviews with pagination.
    async fn list_management_reviews(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ManagementReview>>;

    // ── New: NCR Update/Delete/Lifecycle ─────────────────────────────────
    /// Update an NCR (whole-entity echo). The server-owned scope stamp of
    /// the stored record is preserved — the client body can never move a
    /// record between sites.
    async fn update_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        ncr: NonConformance,
    ) -> Result<NonConformance>;
    /// Delete an NCR — out-of-scope ids are `NotFound`.
    async fn delete_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<()>;
    /// Investigate an NCR (add root cause analysis).
    async fn investigate_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        rca: RootCauseAnalysis,
    ) -> Result<NonConformance>;
    /// Add disposition to an NCR.
    async fn disposition_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        disposition: String,
    ) -> Result<NonConformance>;
    /// Close an NCR.
    async fn close_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<NonConformance>;

    // ── New: CAPA Update/Delete/Lifecycle ────────────────────────────────
    /// Update a CAPA (whole-entity echo). The server-owned scope stamp of
    /// the stored record is preserved.
    async fn update_capa(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        capa: CapaExtended,
    ) -> Result<CapaExtended>;
    /// Delete a CAPA — out-of-scope ids are `NotFound`.
    async fn delete_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<()>;
    /// Verify a CAPA's effectiveness.
    async fn verify_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended>;
    /// Close a CAPA.
    async fn close_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended>;

    // ── New: Inspection Update/Delete ────────────────────────────────────
    /// Update a first article inspection.
    async fn update_first_article_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection>;
    /// Delete a first article inspection.
    async fn delete_first_article_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Update a self-inspection.
    async fn update_self_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        inspection: SelfInspection,
    ) -> Result<SelfInspection>;
    /// Delete a self-inspection.
    async fn delete_self_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Audit Update/Delete ─────────────────────────────────────────
    /// Update an audit (whole-entity echo). The server-owned scope stamp
    /// of the stored record is preserved.
    async fn update_audit(&self, ctx: &RequestContext, id: Uuid, audit: Audit) -> Result<Audit>;
    /// Delete an audit — out-of-scope ids are `NotFound`.
    async fn delete_audit(&self, ctx: &RequestContext, id: Uuid) -> Result<()>;

    // ── New: Supplier Scorecard/SCAR Update/Delete ───────────────────────
    /// Update a supplier scorecard.
    async fn update_supplier_scorecard(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard>;
    /// Delete a supplier scorecard.
    async fn delete_supplier_scorecard(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Create a SCAR.
    async fn create_scar(&self, tenant_id: Uuid, scar: Scar) -> Result<Scar>;
    /// Update a SCAR.
    async fn update_scar(&self, tenant_id: Uuid, id: Uuid, scar: Scar) -> Result<Scar>;
    /// Delete a SCAR.
    async fn delete_scar(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Document Create/Update/Delete ───────────────────────────────
    /// Create a QMS document.
    async fn create_document(&self, tenant_id: Uuid, doc: QmsDocument) -> Result<QmsDocument>;
    /// Update a QMS document.
    async fn update_document(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        doc: QmsDocument,
    ) -> Result<QmsDocument>;
    /// Delete a QMS document.
    async fn delete_document(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: MSA Study Create/Delete ─────────────────────────────────────
    /// Create an MSA study.
    async fn create_msa_study(&self, tenant_id: Uuid, study: MsaStudy) -> Result<MsaStudy>;
    /// Delete an MSA study.
    async fn delete_msa_study(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Process Capability Study Create/Delete ──────────────────────
    /// Create a process capability study.
    async fn create_process_capability_study(
        &self,
        tenant_id: Uuid,
        study: ProcessCapabilityStudy,
    ) -> Result<ProcessCapabilityStudy>;
    /// Delete a process capability study.
    async fn delete_process_capability_study(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Control Plan Create/Update/Delete ───────────────────────────
    /// Create a control plan.
    async fn create_control_plan(&self, tenant_id: Uuid, cp: ControlPlan) -> Result<ControlPlan>;
    /// Update a control plan.
    async fn update_control_plan(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        cp: ControlPlan,
    ) -> Result<ControlPlan>;
    /// Delete a control plan.
    async fn delete_control_plan(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: PFMEA Create/Delete ─────────────────────────────────────────
    /// Create a PFMEA.
    async fn create_pfmea(&self, tenant_id: Uuid, pfmea: PfmeaLite) -> Result<PfmeaLite>;
    /// Delete a PFMEA.
    async fn delete_pfmea(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: NPI Project Create/Update/Delete ────────────────────────────
    /// Create an NPI project.
    async fn create_npi_project(&self, tenant_id: Uuid, project: NpiProject) -> Result<NpiProject>;
    /// Update an NPI project.
    async fn update_npi_project(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        project: NpiProject,
    ) -> Result<NpiProject>;
    /// Delete an NPI project.
    async fn delete_npi_project(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Gauge Create/Update/Delete ──────────────────────────────────
    /// Create a gauge.
    async fn create_gauge(&self, tenant_id: Uuid, gauge: Gauge) -> Result<Gauge>;
    /// Update a gauge.
    async fn update_gauge(&self, tenant_id: Uuid, id: Uuid, gauge: Gauge) -> Result<Gauge>;
    /// Delete a gauge.
    async fn delete_gauge(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Complaint Create/Update/Delete ──────────────────────────────
    /// Create a customer complaint.
    async fn create_complaint(
        &self,
        tenant_id: Uuid,
        complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint>;
    /// Update a customer complaint.
    async fn update_complaint(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint>;
    /// Delete a customer complaint.
    async fn delete_complaint(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: 8D Report Create/Update/Delete ──────────────────────────────
    /// Create an 8D report.
    async fn create_eight_d_report(
        &self,
        tenant_id: Uuid,
        report: EightDReport,
    ) -> Result<EightDReport>;
    /// Update an 8D report.
    async fn update_eight_d_report(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        report: EightDReport,
    ) -> Result<EightDReport>;
    /// Delete an 8D report.
    async fn delete_eight_d_report(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── New: Management Review Create/Update/Delete ──────────────────────
    /// Create a management review.
    async fn create_management_review(
        &self,
        tenant_id: Uuid,
        review: ManagementReview,
    ) -> Result<ManagementReview>;
    /// Update a management review.
    async fn update_management_review(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        review: ManagementReview,
    ) -> Result<ManagementReview>;
    /// Delete a management review.
    async fn delete_management_review(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;

    // ── Getters for list-only entities (tenant-scoped, 404 on missing/foreign) ──
    /// Get a SCAR by ID.
    async fn get_scar(&self, tenant_id: Uuid, id: Uuid) -> Result<Scar>;
    /// Get a QMS document by ID.
    async fn get_document(&self, tenant_id: Uuid, id: Uuid) -> Result<QmsDocument>;
    /// Get a first article inspection by ID.
    async fn get_first_article_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<FirstArticleInspection>;
    /// Get a self-inspection by ID.
    async fn get_self_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<SelfInspection>;
    /// Get an MSA study by ID.
    async fn get_msa_study(&self, tenant_id: Uuid, id: Uuid) -> Result<MsaStudy>;
    /// Get a process capability study by ID.
    async fn get_process_capability_study(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<ProcessCapabilityStudy>;
    /// Get a control plan by ID.
    async fn get_control_plan(&self, tenant_id: Uuid, id: Uuid) -> Result<ControlPlan>;
    /// Get a PFMEA by ID.
    async fn get_pfmea(&self, tenant_id: Uuid, id: Uuid) -> Result<PfmeaLite>;
    /// Get a gauge by ID.
    async fn get_gauge(&self, tenant_id: Uuid, id: Uuid) -> Result<Gauge>;
    /// Get a customer complaint by ID.
    async fn get_complaint(&self, tenant_id: Uuid, id: Uuid) -> Result<CustomerComplaint>;
    /// Get an 8D report by ID.
    async fn get_eight_d_report(&self, tenant_id: Uuid, id: Uuid) -> Result<EightDReport>;
    /// Get a management review by ID.
    async fn get_management_review(&self, tenant_id: Uuid, id: Uuid) -> Result<ManagementReview>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`QualityService`] trait.
///
/// Stores all quality domain data in memory using `HashMap`s. A separate
/// `tenant_index` maps entity IDs to tenant IDs so that list/get operations
/// can enforce tenant isolation even though the model structs themselves do
/// not carry a `tenant_id` field.
///
/// The NCR / CAPA / audit records additionally keep their SERVER-STAMPED
/// resource scope in a `scope_index` (twenty-ninth audit Wave B items
/// 6-8) so the same scope semantics as the SQL implementation hold: a
/// site-scoped caller sees only records stamped with one of their
/// authorized sites, corporate (unstamped) records are visible to the
/// explicit tenant-wide grant only, and a caller with no operational
/// scope sees nothing.
///
/// Suitable for development, testing, and demo environments.
pub struct InMemoryQualityService {
    ncrs: RwLock<HashMap<Uuid, NonConformance>>,
    capas: RwLock<HashMap<Uuid, CapaExtended>>,
    first_article_inspections: RwLock<HashMap<Uuid, FirstArticleInspection>>,
    self_inspections: RwLock<HashMap<Uuid, SelfInspection>>,
    audits: RwLock<HashMap<Uuid, Audit>>,
    audit_findings: RwLock<HashMap<Uuid, AuditFinding>>,
    supplier_scorecards: RwLock<HashMap<Uuid, SupplierScorecard>>,
    scars: RwLock<HashMap<Uuid, Scar>>,
    documents: RwLock<HashMap<Uuid, QmsDocument>>,
    msa_studies: RwLock<HashMap<Uuid, MsaStudy>>,
    process_capability_studies: RwLock<HashMap<Uuid, ProcessCapabilityStudy>>,
    control_plans: RwLock<HashMap<Uuid, ControlPlan>>,
    pfmeas: RwLock<HashMap<Uuid, PfmeaLite>>,
    npi_projects: RwLock<HashMap<Uuid, NpiProject>>,
    npi_risks: RwLock<HashMap<Uuid, NpiRisk>>,
    gauges: RwLock<HashMap<Uuid, Gauge>>,
    complaints: RwLock<HashMap<Uuid, CustomerComplaint>>,
    eight_d_reports: RwLock<HashMap<Uuid, EightDReport>>,
    management_reviews: RwLock<HashMap<Uuid, ManagementReview>>,
    ncr_counter: RwLock<u64>,
    capa_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
    /// Maps entity ID → tenant ID for tenant isolation.
    tenant_index: RwLock<HashMap<Uuid, Uuid>>,
    /// Maps entity ID → the server-stamped quality resource scope
    /// (NCR / CAPA / audit records only).
    scope_index: RwLock<HashMap<Uuid, QualityScopeStamp>>,
}

impl InMemoryQualityService {
    /// Create a new empty [`InMemoryQualityService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            ncrs: RwLock::new(HashMap::new()),
            capas: RwLock::new(HashMap::new()),
            first_article_inspections: RwLock::new(HashMap::new()),
            self_inspections: RwLock::new(HashMap::new()),
            audits: RwLock::new(HashMap::new()),
            audit_findings: RwLock::new(HashMap::new()),
            supplier_scorecards: RwLock::new(HashMap::new()),
            scars: RwLock::new(HashMap::new()),
            documents: RwLock::new(HashMap::new()),
            msa_studies: RwLock::new(HashMap::new()),
            process_capability_studies: RwLock::new(HashMap::new()),
            control_plans: RwLock::new(HashMap::new()),
            pfmeas: RwLock::new(HashMap::new()),
            npi_projects: RwLock::new(HashMap::new()),
            npi_risks: RwLock::new(HashMap::new()),
            gauges: RwLock::new(HashMap::new()),
            complaints: RwLock::new(HashMap::new()),
            eight_d_reports: RwLock::new(HashMap::new()),
            management_reviews: RwLock::new(HashMap::new()),
            ncr_counter: RwLock::new(0),
            capa_counter: RwLock::new(0),
            event_bus,
            tenant_index: RwLock::new(HashMap::new()),
            scope_index: RwLock::new(HashMap::new()),
        }
    }

    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!("Failed to publish event {}: {}", event.event_type(), e);
            }
        }
    }

    fn generate_ncr_number(counter: u64) -> String {
        format!("NCR-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_capa_number(counter: u64) -> String {
        format!("CAPA-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    /// Record the tenant ownership of an entity in the tenant index.
    async fn record_tenant(&self, entity_id: Uuid, tenant_id: Uuid) {
        self.tenant_index.write().await.insert(entity_id, tenant_id);
    }

    /// Check whether an entity belongs to the given tenant.
    ///
    /// Returns `true` when the entity is owned by `tenant_id`, or when the
    /// entity is not present in the index (backward-compatible fallback).
    async fn tenant_matches(&self, entity_id: Uuid, tenant_id: Uuid) -> bool {
        let idx = self.tenant_index.read().await;
        match idx.get(&entity_id) {
            Some(&tid) => tid == tenant_id,
            None => true, // not indexed yet — allow through
        }
    }

    /// Record the server-stamped quality resource scope of an entity
    /// (twenty-ninth audit Wave B item 2).
    async fn record_scope(&self, entity_id: Uuid, stamp: QualityScopeStamp) {
        self.scope_index.write().await.insert(entity_id, stamp);
    }

    /// The stored scope stamp of an entity; entities without a recorded
    /// stamp are treated as corporate (both ids `None`) — the honest
    /// legacy encoding.
    async fn stored_scope(&self, entity_id: Uuid) -> QualityScopeStamp {
        let idx = self.scope_index.read().await;
        idx.get(&entity_id).copied().unwrap_or_default()
    }

    /// The caller's scope as a SQL-equivalent visibility decision over a
    /// record's SERVER-STAMPED site (twenty-ninth audit Wave B item 3;
    /// thirtieth-audit P0 item 1):
    ///
    /// - `NoOperationalScope` ⇒ false (no rows anywhere);
    /// - `TenantWide` ⇒ true (corporate records included);
    /// - `Operational` with site grants ⇒ the record's site, when
    ///   stamped, is one of the authorized sites — an unstamped
    ///   (corporate) record is NOT visible to a site-scoped caller;
    /// - `Operational` with ONLY work-center grants ⇒ the record's stamp
    ///   must match an exact granted (site, work center) — a WC grant
    ///   never widens into its whole site.
    fn site_visible(ctx: &RequestContext, stamp: QualityScopeStamp) -> bool {
        match &ctx.scope {
            AuthorizedScope::NoOperationalScope => false,
            AuthorizedScope::TenantWide => true,
            AuthorizedScope::Operational {
                sites,
                work_centers,
            } => {
                if stamp.site_id.is_some_and(|site| sites.contains(&site)) {
                    return true;
                }
                match (stamp.site_id, stamp.work_center_id) {
                    (Some(site), Some(wc)) => work_centers
                        .iter()
                        .any(|s| s.site == site && s.work_center == wc),
                    _ => false,
                }
            }
        }
    }

    /// Scope gate used by the mutating single-record paths: a record
    /// outside the caller's scope is indistinguishable from a missing
    /// one — `NotFound`.
    async fn scope_gate(&self, ctx: &RequestContext, entity_id: Uuid) -> Result<QualityScopeStamp> {
        let stamp = self.stored_scope(entity_id).await;
        if !Self::site_visible(ctx, stamp) {
            return Err(SenseiError::NotFound(format!(
                "record {entity_id} not found"
            )));
        }
        Ok(stamp)
    }
}

impl Default for InMemoryQualityService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl QualityService for InMemoryQualityService {
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
        let idx = self.tenant_index.read().await;
        let scopes = self.scope_index.read().await;
        let store = self.ncrs.read().await;
        let tenant_id = ctx.tenant;
        let items: Vec<_> = store
            .values()
            .filter(|ncr| {
                // Tenant isolation
                let belongs_to_tenant = idx.get(&ncr.id).is_none_or(|&tid| tid == tenant_id);
                if !belongs_to_tenant {
                    return false;
                }
                // Scope intersection (site-scoped callers see only their
                // stamped records; corporate rows are tenant-wide only).
                let stamp = scopes.get(&ncr.id).copied().unwrap_or_default();
                if !Self::site_visible(ctx, stamp) {
                    return false;
                }
                status.is_none_or(|s| enum_name_matches(s, ncr.status.as_str()))
                    && severity.is_none_or(|s| enum_name_matches(s, &format!("{:?}", ncr.severity)))
                    && source.is_none_or(|s| {
                        ncr.source
                            .as_deref()
                            .is_some_and(|src| src.eq_ignore_ascii_case(s))
                    })
            })
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
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
        let tenant_id = ctx.tenant;
        // Server-stamped scope (thirtieth-audit P0 item 8): the SINGLE
        // creation-scope helper derives the stamp from the validated
        // operating focus — a scoped caller without an operating site is
        // rejected instead of silently producing a corporate record.
        let stamp = super::scope::stamp_from_scope(super::scope::derive_creation_scope(ctx, None)?);
        let mut counter = self.ncr_counter.write().await;
        *counter += 1;
        let nc_number = Self::generate_ncr_number(*counter);
        drop(counter);

        let now = Utc::now();
        let ncr = NonConformance {
            id: Uuid::new_v4(),
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

        let id = ncr.id;
        self.record_tenant(id, tenant_id).await;
        self.record_scope(id, stamp).await;
        self.ncrs.write().await.insert(id, ncr.clone());
        self.publish_event(NcrCreatedEvent::new(
            tenant_id,
            id,
            ncr.nc_number.clone(),
            ncr.title.clone(),
            format!("{:?}", ncr.severity),
            ncr.detected_by.unwrap_or_default(),
        ))
        .await;
        Ok(ncr)
    }

    async fn get_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<NonConformance> {
        let store = self.ncrs.read().await;
        let ncr = store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        if self.scope_gate(ctx, id).await.is_err() {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        Ok(ncr)
    }

    async fn update_ncr_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        severity: NcSeverity,
    ) -> Result<NonConformance> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        self.scope_gate(ctx, id).await?;
        let mut store = self.ncrs.write().await;
        let ncr = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        ncr.severity = severity;
        ncr.updated_at = Utc::now();
        Ok(ncr.clone())
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
        let idx = self.tenant_index.read().await;
        let scopes = self.scope_index.read().await;
        let store = self.capas.read().await;
        let tenant_id = ctx.tenant;
        let items: Vec<_> = store
            .values()
            .filter(|capa| {
                // Tenant isolation
                let belongs_to_tenant = idx.get(&capa.id).is_none_or(|&tid| tid == tenant_id);
                if !belongs_to_tenant {
                    return false;
                }
                let stamp = scopes.get(&capa.id).copied().unwrap_or_default();
                if !Self::site_visible(ctx, stamp) {
                    return false;
                }
                let status_match =
                    status.is_none_or(|s| enum_name_matches(s, &format!("{:?}", capa.status)));
                // The API exposes `nc_type` but the model uses `capa_type`.
                // Filter by capa_type when nc_type is provided.
                let type_match =
                    nc_type.is_none_or(|t| enum_name_matches(t, &format!("{:?}", capa.capa_type)));
                status_match && type_match
            })
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
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
        let tenant_id = ctx.tenant;
        // Server-stamped scope (thirtieth-audit P0 item 8): the SINGLE
        // creation-scope helper derives the stamp from the validated
        // operating focus — a scoped caller without an operating site is
        // rejected instead of silently producing a corporate record.
        let stamp = super::scope::stamp_from_scope(super::scope::derive_creation_scope(ctx, None)?);
        let mut counter = self.capa_counter.write().await;
        *counter += 1;
        let capa_number = Self::generate_capa_number(*counter);
        drop(counter);

        let now = Utc::now();
        let capa = CapaExtended {
            id: Uuid::new_v4(),
            capa_number,
            title,
            description,
            nc_ids,
            capa_type,
            priority,
            status: CapaStatusEx::Draft,
            root_cause_analyses: Vec::new(),
            actions: Vec::new(),
            closure_gates: Vec::new(),
            effectiveness_checks: Vec::new(),
            entity_links: Vec::new(),
            owner_id,
            due_date,
            closed_at: None,
            created_at: now,
            updated_at: now,
        };

        let id = capa.id;
        self.record_tenant(id, tenant_id).await;
        self.record_scope(id, stamp).await;
        self.capas.write().await.insert(id, capa.clone());
        self.publish_event(CAPACreatedEvent::new(
            tenant_id,
            id,
            capa.nc_ids.first().copied(),
            format!("{:?}", capa.priority),
            false,
            "CAPA created manually".to_string(),
        ))
        .await;
        Ok(capa)
    }

    async fn get_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "CAPA with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let store = self.capas.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA with id {id} not found")))
    }

    async fn update_capa_status(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        status: CapaStatusEx,
    ) -> Result<CapaExtended> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "CAPA with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let mut store = self.capas.write().await;
        let capa = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA with id {id} not found")))?;
        capa.status = status;
        capa.updated_at = Utc::now();
        if matches!(status, CapaStatusEx::Closed) {
            capa.closed_at = Some(Utc::now());
        }
        Ok(capa.clone())
    }

    // ── Inspections ───────────────────────────────────────────────────────

    async fn list_first_article_inspections(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<FirstArticleInspection>> {
        let idx = self.tenant_index.read().await;
        let store = self.first_article_inspections.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|fai| idx.get(&fai.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn create_first_article_inspection(
        &self,
        tenant_id: Uuid,
        mut fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection> {
        let now = Utc::now();
        fai.id = Uuid::new_v4();
        fai.created_at = now;
        fai.updated_at = now;
        let id = fai.id;
        self.record_tenant(id, tenant_id).await;
        self.first_article_inspections
            .write()
            .await
            .insert(id, fai.clone());
        Ok(fai)
    }

    async fn list_self_inspections(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SelfInspection>> {
        let idx = self.tenant_index.read().await;
        let store = self.self_inspections.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|si| idx.get(&si.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn create_self_inspection(
        &self,
        tenant_id: Uuid,
        mut inspection: SelfInspection,
    ) -> Result<SelfInspection> {
        let now = Utc::now();
        inspection.id = Uuid::new_v4();
        inspection.created_at = now;
        let id = inspection.id;
        self.record_tenant(id, tenant_id).await;
        self.self_inspections
            .write()
            .await
            .insert(id, inspection.clone());
        Ok(inspection)
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
        let idx = self.tenant_index.read().await;
        let scopes = self.scope_index.read().await;
        let store = self.audits.read().await;
        let tenant_id = ctx.tenant;
        let items: Vec<_> = store
            .values()
            .filter(|audit| {
                // Tenant isolation
                let belongs_to_tenant = idx.get(&audit.id).is_none_or(|&tid| tid == tenant_id);
                if !belongs_to_tenant {
                    return false;
                }
                let stamp = scopes.get(&audit.id).copied().unwrap_or_default();
                if !Self::site_visible(ctx, stamp) {
                    return false;
                }
                status.is_none_or(|s| enum_name_matches(s, &format!("{:?}", audit.status)))
                    && audit_type
                        .is_none_or(|t| enum_name_matches(t, &format!("{:?}", audit.audit_type)))
            })
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn create_audit(&self, ctx: &RequestContext, mut audit: Audit) -> Result<Audit> {
        let tenant_id = ctx.tenant;
        // Server-stamped scope (thirtieth-audit P0 item 8): the SINGLE
        // creation-scope helper derives the stamp from the validated
        // operating focus — a scoped caller without an operating site is
        // rejected instead of silently producing a corporate record.
        let stamp = super::scope::stamp_from_scope(super::scope::derive_creation_scope(ctx, None)?);
        let now = Utc::now();
        audit.id = Uuid::new_v4();
        audit.created_at = now;
        audit.updated_at = now;
        let id = audit.id;
        self.record_tenant(id, tenant_id).await;
        self.record_scope(id, stamp).await;
        self.audits.write().await.insert(id, audit.clone());
        Ok(audit)
    }

    async fn get_audit(&self, ctx: &RequestContext, id: Uuid) -> Result<Audit> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "Audit with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let store = self.audits.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Audit with id {id} not found")))
    }

    async fn list_audit_findings(
        &self,
        ctx: &RequestContext,
        audit_id: Uuid,
    ) -> Result<Vec<AuditFinding>> {
        // Verify the audit belongs to the requesting tenant and scope.
        if !self.tenant_matches(audit_id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "Audit with id {audit_id} not found"
            )));
        }
        self.scope_gate(ctx, audit_id).await?;
        let store = self.audit_findings.read().await;
        Ok(store
            .values()
            .filter(|f| f.audit_id == audit_id)
            .cloned()
            .collect())
    }

    // ── Supplier Quality ──────────────────────────────────────────────────

    async fn list_supplier_scorecards(
        &self,
        tenant_id: Uuid,
        supplier_id: Option<Uuid>,
        period: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SupplierScorecard>> {
        let idx = self.tenant_index.read().await;
        let store = self.supplier_scorecards.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|sc| {
                let belongs_to_tenant = idx
                    .get(&sc.supplier_id.parse().unwrap_or(Uuid::nil()))
                    .is_none_or(|&tid| tid == tenant_id);
                if !belongs_to_tenant {
                    return false;
                }
                // Filter by supplier_id if provided
                let supplier_match =
                    supplier_id.is_none_or(|sid| sc.supplier_id == sid.to_string());
                // Filter by period if provided
                let period_match = period.is_none_or(|p| sc.period_key == p);
                supplier_match && period_match
            })
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn create_supplier_evaluation(
        &self,
        tenant_id: Uuid,
        mut scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard> {
        scorecard.computed_at = Utc::now();
        let id = Uuid::new_v4();
        self.record_tenant(id, tenant_id).await;
        self.supplier_scorecards
            .write()
            .await
            .insert(id, scorecard.clone());
        let supplier_id = Uuid::parse_str(&scorecard.supplier_id).unwrap_or_default();
        self.publish_event(SupplierEvaluatedEvent::new(
            tenant_id,
            supplier_id,
            scorecard.overall_score,
            scorecard.tier.clone(),
        ))
        .await;
        Ok(scorecard)
    }

    async fn list_scars(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Scar>> {
        let idx = self.tenant_index.read().await;
        let store = self.scars.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|scar| idx.get(&scar.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Documents ─────────────────────────────────────────────────────────

    async fn list_documents(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<QmsDocument>> {
        let idx = self.tenant_index.read().await;
        let store = self.documents.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|doc| idx.get(&doc.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── MSA / SPC / Process Capability ────────────────────────────────────

    async fn list_msa_studies(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MsaStudy>> {
        let idx = self.tenant_index.read().await;
        let store = self.msa_studies.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|study| idx.get(&study.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_process_capability_studies(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProcessCapabilityStudy>> {
        let idx = self.tenant_index.read().await;
        let store = self.process_capability_studies.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|study| idx.get(&study.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_control_plans(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ControlPlan>> {
        let idx = self.tenant_index.read().await;
        let store = self.control_plans.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|cp| idx.get(&cp.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_pfmeas(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PfmeaLite>> {
        let idx = self.tenant_index.read().await;
        let store = self.pfmeas.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|pf| idx.get(&pf.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── NPI ───────────────────────────────────────────────────────────────

    async fn list_npi_projects(
        &self,
        tenant_id: Uuid,
        stage: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiProject>> {
        let idx = self.tenant_index.read().await;
        let store = self.npi_projects.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|proj| {
                let belongs_to_tenant = idx.get(&proj.id).is_none_or(|&tid| tid == tenant_id);
                if !belongs_to_tenant {
                    return false;
                }
                // Filter by stage if provided
                let stage_match = stage
                    .is_none_or(|s| enum_name_matches(s, &format!("{:?}", proj.current_stage)));
                // Filter by health_status when status is provided
                let status_match =
                    status.is_none_or(|s| proj.health_status.to_lowercase() == s.to_lowercase());
                stage_match && status_match
            })
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_npi_risks(
        &self,
        tenant_id: Uuid,
        project_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiRisk>> {
        let idx = self.tenant_index.read().await;
        let store = self.npi_risks.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|r| {
                // Tenant isolation
                let belongs_to_tenant = idx.get(&r.id).is_none_or(|&tid| tid == tenant_id);
                if !belongs_to_tenant {
                    return false;
                }
                r.project_id == Some(project_id)
            })
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Gauges ────────────────────────────────────────────────────────────

    async fn list_gauges(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Gauge>> {
        let idx = self.tenant_index.read().await;
        let store = self.gauges.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|g| idx.get(&g.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Complaints / 8D / Reviews ─────────────────────────────────────────

    async fn list_complaints(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CustomerComplaint>> {
        let idx = self.tenant_index.read().await;
        let store = self.complaints.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|c| idx.get(&c.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_eight_d_reports(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EightDReport>> {
        let idx = self.tenant_index.read().await;
        let store = self.eight_d_reports.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|r| idx.get(&r.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_management_reviews(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ManagementReview>> {
        let idx = self.tenant_index.read().await;
        let store = self.management_reviews.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|mr| idx.get(&mr.id).is_none_or(|&tid| tid == tenant_id))
            .cloned()
            .collect();
        drop(idx);
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── New: NCR Update/Delete/Investigate/Disposition/Close ──────────────

    async fn update_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        ncr: NonConformance,
    ) -> Result<NonConformance> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        // The stored scope stamp is server-owned and preserved — the
        // client body (a whole-entity echo) can never move the record
        // between sites.
        let stored_scope = self.scope_gate(ctx, id).await?;
        let mut store = self.ncrs.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        existing.title = ncr.title;
        existing.description = ncr.description;
        existing.nc_type = ncr.nc_type;
        existing.severity = ncr.severity;
        existing.product_id = ncr.product_id;
        existing.process_id = ncr.process_id;
        existing.defect_code = ncr.defect_code;
        existing.detected_by = ncr.detected_by;
        existing.department = ncr.department;
        existing.location = ncr.location;
        existing.is_recurrence = ncr.is_recurrence;
        existing.status = ncr.status;
        existing.source = ncr.source;
        existing.root_cause = ncr.root_cause;
        existing.root_cause_type = ncr.root_cause_type;
        existing.analysis_method = ncr.analysis_method;
        existing.disposition = ncr.disposition;
        existing.closed_at = ncr.closed_at;
        existing.updated_at = Utc::now();
        let updated = existing.clone();
        drop(store);
        self.record_scope(id, stored_scope).await;
        Ok(updated)
    }

    async fn delete_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        self.scope_gate(ctx, id).await?;
        // Canonical lock order (tenant -> scope -> store) so concurrent
        // list/get/delete paths can never interleave into a deadlock.
        let mut ti = self.tenant_index.write().await;
        let mut si = self.scope_index.write().await;
        let mut store = self.ncrs.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        ti.remove(&id);
        si.remove(&id);
        Ok(())
    }

    async fn investigate_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        rca: RootCauseAnalysis,
    ) -> Result<NonConformance> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        self.scope_gate(ctx, id).await?;
        let mut store = self.ncrs.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        if existing.status == NcrStatus::Closed {
            return Err(SenseiError::Validation(
                "Cannot investigate a closed NCR".to_string(),
            ));
        }
        if existing.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot investigate a cancelled NCR".to_string(),
            ));
        }
        existing.root_cause = Some(rca.description);
        existing.root_cause_type = Some(rca.root_cause_type);
        existing.analysis_method = Some(rca.analysis_method);
        existing.status = NcrStatus::UnderInvestigation;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn disposition_ncr(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        disposition: String,
    ) -> Result<NonConformance> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        self.scope_gate(ctx, id).await?;
        if disposition.trim().is_empty() {
            return Err(SenseiError::Validation(
                "Disposition cannot be empty".to_string(),
            ));
        }
        let mut store = self.ncrs.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        if existing.status == NcrStatus::Closed {
            return Err(SenseiError::Validation(
                "Cannot dispose a closed NCR".to_string(),
            ));
        }
        if existing.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot dispose a cancelled NCR".to_string(),
            ));
        }
        existing.disposition = Some(disposition);
        // Disposition defines the action path for the non-conforming material.
        existing.status = NcrStatus::ActionDefined;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn close_ncr(&self, ctx: &RequestContext, id: Uuid) -> Result<NonConformance> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!("NCR with id {id} not found")));
        }
        self.scope_gate(ctx, id).await?;
        let mut store = self.ncrs.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NCR with id {id} not found")))?;
        if existing.status == NcrStatus::Closed {
            return Err(SenseiError::Validation("NCR is already closed".to_string()));
        }
        if existing.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot close a cancelled NCR".to_string(),
            ));
        }
        // Closing requires the investigation and disposition to be complete.
        let mut missing = Vec::new();
        if existing.root_cause.is_none() {
            missing.push("root cause analysis");
        }
        if existing.disposition.is_none() {
            missing.push("disposition");
        }
        if !missing.is_empty() {
            return Err(SenseiError::Validation(format!(
                "Cannot close NCR {id}: missing {}",
                missing.join(", ")
            )));
        }
        existing.status = NcrStatus::Closed;
        existing.closed_at = Some(Utc::now());
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    // ── New: CAPA Update/Delete/Verify/Close ──────────────────────────────

    async fn update_capa(
        &self,
        ctx: &RequestContext,
        id: Uuid,
        capa: CapaExtended,
    ) -> Result<CapaExtended> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "CAPA with id {id} not found"
            )));
        }
        // The stored scope stamp is server-owned and preserved.
        let stored_scope = self.scope_gate(ctx, id).await?;
        let mut store = self.capas.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA with id {id} not found")))?;
        // Full-entity update: the database backend persists the whole CAPA
        // (JSONB), so the in-memory backend must apply every editable field
        // (workflow data included) to stay behaviorally identical.
        existing.capa_number = capa.capa_number;
        existing.title = capa.title;
        existing.description = capa.description;
        existing.nc_ids = capa.nc_ids;
        existing.capa_type = capa.capa_type;
        existing.priority = capa.priority;
        existing.status = capa.status;
        existing.root_cause_analyses = capa.root_cause_analyses;
        existing.actions = capa.actions;
        existing.closure_gates = capa.closure_gates;
        existing.effectiveness_checks = capa.effectiveness_checks;
        existing.entity_links = capa.entity_links;
        existing.owner_id = capa.owner_id;
        existing.due_date = capa.due_date;
        existing.closed_at = capa.closed_at;
        existing.updated_at = Utc::now();
        let updated = existing.clone();
        drop(store);
        self.record_scope(id, stored_scope).await;
        Ok(updated)
    }

    async fn delete_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "CAPA with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let mut ti = self.tenant_index.write().await;
        let mut si = self.scope_index.write().await;
        let mut store = self.capas.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA with id {id} not found")))?;
        ti.remove(&id);
        si.remove(&id);
        Ok(())
    }

    async fn verify_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "CAPA with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let mut store = self.capas.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA with id {id} not found")))?;
        if existing.status == CapaStatusEx::Closed {
            return Err(SenseiError::Validation(
                "Cannot verify a closed CAPA".to_string(),
            ));
        }
        if existing.status == CapaStatusEx::Cancelled || existing.status == CapaStatusEx::Rejected {
            return Err(SenseiError::Validation(
                "Cannot verify a cancelled/rejected CAPA".to_string(),
            ));
        }
        // Verification requires at least one defined action and an RCA.
        if existing.root_cause_analyses.is_empty() {
            return Err(SenseiError::Validation(
                "Cannot verify CAPA without a root cause analysis".to_string(),
            ));
        }
        if existing.actions.is_empty() {
            return Err(SenseiError::Validation(
                "Cannot verify CAPA without corrective actions".to_string(),
            ));
        }
        existing.status = CapaStatusEx::Verification;
        // Record the verification as an effectiveness check so the result is
        // traceable (who/when verified is captured by checked_by/checked_at
        // when the caller provides it).
        existing.effectiveness_checks.push(EffectivenessCheck {
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
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn close_capa(&self, ctx: &RequestContext, id: Uuid) -> Result<CapaExtended> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "CAPA with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let mut store = self.capas.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA with id {id} not found")))?;
        existing.status = CapaStatusEx::Closed;
        existing.closed_at = Some(Utc::now());
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    // ── New: Inspection Update/Delete ────────────────────────────────────

    async fn update_first_article_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "First article inspection with id {id} not found"
            )));
        }
        let mut store = self.first_article_inspections.write().await;
        let existing = store.get_mut(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("First article inspection with id {id} not found"))
        })?;
        existing.part_number = fai.part_number;
        existing.part_name = fai.part_name;
        existing.revision = fai.revision;
        existing.status = fai.status;
        existing.customer = fai.customer;
        existing.characteristics = fai.characteristics;
        existing.inspector_id = fai.inspector_id;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn delete_first_article_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "First article inspection with id {id} not found"
            )));
        }
        let mut store = self.first_article_inspections.write().await;
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("First article inspection with id {id} not found"))
        })?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    async fn update_self_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        inspection: SelfInspection,
    ) -> Result<SelfInspection> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Self inspection with id {id} not found"
            )));
        }
        let mut store = self.self_inspections.write().await;
        let existing = store.get_mut(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Self inspection with id {id} not found"))
        })?;
        existing.status = inspection.status;
        existing.result = inspection.result;
        existing.checks = inspection.checks;
        Ok(existing.clone())
    }

    async fn delete_self_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Self inspection with id {id} not found"
            )));
        }
        let mut store = self.self_inspections.write().await;
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Self inspection with id {id} not found"))
        })?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Audit Update/Delete ─────────────────────────────────────────

    async fn update_audit(&self, ctx: &RequestContext, id: Uuid, audit: Audit) -> Result<Audit> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "Audit with id {id} not found"
            )));
        }
        // The stored scope stamp is server-owned and preserved.
        let stored_scope = self.scope_gate(ctx, id).await?;
        let mut store = self.audits.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Audit with id {id} not found")))?;
        existing.audit_type = audit.audit_type;
        existing.title = audit.title;
        existing.status = audit.status;
        existing.scheduled_date = audit.scheduled_date;
        existing.auditor_id = audit.auditor_id;
        existing.scope = audit.scope;
        existing.updated_at = Utc::now();
        let updated = existing.clone();
        drop(store);
        self.record_scope(id, stored_scope).await;
        Ok(updated)
    }

    async fn delete_audit(&self, ctx: &RequestContext, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, ctx.tenant).await {
            return Err(SenseiError::NotFound(format!(
                "Audit with id {id} not found"
            )));
        }
        self.scope_gate(ctx, id).await?;
        let mut ti = self.tenant_index.write().await;
        let mut si = self.scope_index.write().await;
        let mut store = self.audits.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Audit with id {id} not found")))?;
        ti.remove(&id);
        si.remove(&id);
        Ok(())
    }

    // ── New: Supplier Scorecard/SCAR Update/Delete ───────────────────────

    async fn update_supplier_scorecard(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Supplier scorecard with id {id} not found"
            )));
        }
        let mut store = self.supplier_scorecards.write().await;
        let existing = store.get_mut(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Supplier scorecard with id {id} not found"))
        })?;
        existing.period_key = scorecard.period_key;
        existing.ppm_score = scorecard.ppm_score;
        existing.otd_score = scorecard.otd_score;
        existing.quality_score = scorecard.quality_score;
        existing.delivery_score = scorecard.delivery_score;
        existing.copq_score = scorecard.copq_score;
        existing.overall_score = scorecard.overall_score;
        existing.tier = scorecard.tier;
        existing.computed_at = Utc::now();
        Ok(existing.clone())
    }

    async fn delete_supplier_scorecard(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Supplier scorecard with id {id} not found"
            )));
        }
        let mut store = self.supplier_scorecards.write().await;
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Supplier scorecard with id {id} not found"))
        })?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    async fn create_scar(&self, tenant_id: Uuid, mut scar: Scar) -> Result<Scar> {
        scar.id = Uuid::new_v4();
        let now = Utc::now();
        scar.created_at = now;
        scar.updated_at = now;
        let id = scar.id;
        self.record_tenant(id, tenant_id).await;
        self.scars.write().await.insert(id, scar.clone());
        Ok(scar)
    }

    async fn update_scar(&self, tenant_id: Uuid, id: Uuid, scar: Scar) -> Result<Scar> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "SCAR with id {id} not found"
            )));
        }
        let mut store = self.scars.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR with id {id} not found")))?;
        existing.supplier_id = scar.supplier_id;
        existing.title = scar.title;
        existing.description = scar.description;
        existing.status = scar.status;
        existing.severity = scar.severity;
        existing.containment_action = scar.containment_action;
        existing.root_cause = scar.root_cause;
        existing.corrective_action = scar.corrective_action;
        existing.verification_notes = scar.verification_notes;
        existing.due_date = scar.due_date;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn delete_scar(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "SCAR with id {id} not found"
            )));
        }
        let mut store = self.scars.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Document Create/Update/Delete ───────────────────────────────

    async fn create_document(&self, tenant_id: Uuid, mut doc: QmsDocument) -> Result<QmsDocument> {
        doc.id = Uuid::new_v4();
        let now = Utc::now();
        doc.created_at = now;
        doc.updated_at = now;
        let id = doc.id;
        self.record_tenant(id, tenant_id).await;
        self.documents.write().await.insert(id, doc.clone());
        Ok(doc)
    }

    async fn update_document(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        doc: QmsDocument,
    ) -> Result<QmsDocument> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Document with id {id} not found"
            )));
        }
        let mut store = self.documents.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Document with id {id} not found")))?;
        existing.document_type = doc.document_type;
        existing.current_revision = doc.current_revision;
        existing.revisions = doc.revisions;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn delete_document(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Document with id {id} not found"
            )));
        }
        let mut store = self.documents.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Document with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: MSA Study Create/Delete ─────────────────────────────────────

    async fn create_msa_study(&self, tenant_id: Uuid, mut study: MsaStudy) -> Result<MsaStudy> {
        study.id = Uuid::new_v4();
        let now = Utc::now();
        study.created_at = now;
        let id = study.id;
        self.record_tenant(id, tenant_id).await;
        self.msa_studies.write().await.insert(id, study.clone());
        Ok(study)
    }

    async fn delete_msa_study(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "MSA study with id {id} not found"
            )));
        }
        let mut store = self.msa_studies.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("MSA study with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Process Capability Study Create/Delete ──────────────────────

    async fn create_process_capability_study(
        &self,
        tenant_id: Uuid,
        mut study: ProcessCapabilityStudy,
    ) -> Result<ProcessCapabilityStudy> {
        study.id = Uuid::new_v4();
        let now = Utc::now();
        study.created_at = now;
        let id = study.id;
        self.record_tenant(id, tenant_id).await;
        self.process_capability_studies
            .write()
            .await
            .insert(id, study.clone());
        Ok(study)
    }

    async fn delete_process_capability_study(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Process capability study with id {id} not found"
            )));
        }
        let mut store = self.process_capability_studies.write().await;
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Process capability study with id {id} not found"))
        })?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Control Plan Create/Update/Delete ───────────────────────────

    async fn create_control_plan(
        &self,
        tenant_id: Uuid,
        mut cp: ControlPlan,
    ) -> Result<ControlPlan> {
        cp.id = Uuid::new_v4();
        let now = Utc::now();
        cp.created_at = now;
        let id = cp.id;
        self.record_tenant(id, tenant_id).await;
        self.control_plans.write().await.insert(id, cp.clone());
        Ok(cp)
    }

    async fn update_control_plan(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        cp: ControlPlan,
    ) -> Result<ControlPlan> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Control plan with id {id} not found"
            )));
        }
        let mut store = self.control_plans.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Control plan with id {id} not found")))?;
        existing.name = cp.name;
        existing.checkpoints = cp.checkpoints;
        existing.revision = cp.revision;
        Ok(existing.clone())
    }

    async fn delete_control_plan(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Control plan with id {id} not found"
            )));
        }
        let mut store = self.control_plans.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Control plan with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: PFMEA Create/Delete ─────────────────────────────────────────

    async fn create_pfmea(&self, tenant_id: Uuid, mut pfmea: PfmeaLite) -> Result<PfmeaLite> {
        pfmea.id = Uuid::new_v4();
        let now = Utc::now();
        pfmea.created_at = now;
        let id = pfmea.id;
        self.record_tenant(id, tenant_id).await;
        self.pfmeas.write().await.insert(id, pfmea.clone());
        Ok(pfmea)
    }

    async fn delete_pfmea(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "PFMEA with id {id} not found"
            )));
        }
        let mut store = self.pfmeas.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PFMEA with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: NPI Project Create/Update/Delete ────────────────────────────

    async fn create_npi_project(
        &self,
        tenant_id: Uuid,
        mut project: NpiProject,
    ) -> Result<NpiProject> {
        project.id = Uuid::new_v4();
        let now = Utc::now();
        project.created_at = now;
        project.updated_at = now;
        let id = project.id;
        self.record_tenant(id, tenant_id).await;
        self.npi_projects.write().await.insert(id, project.clone());
        Ok(project)
    }

    async fn update_npi_project(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        project: NpiProject,
    ) -> Result<NpiProject> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "NPI project with id {id} not found"
            )));
        }
        let mut store = self.npi_projects.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NPI project with id {id} not found")))?;
        existing.name = project.name;
        existing.description = project.description;
        existing.current_stage = project.current_stage;
        existing.health_status = project.health_status;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn delete_npi_project(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "NPI project with id {id} not found"
            )));
        }
        let mut store = self.npi_projects.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("NPI project with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Gauge Create/Update/Delete ──────────────────────────────────

    async fn create_gauge(&self, tenant_id: Uuid, mut gauge: Gauge) -> Result<Gauge> {
        gauge.id = Uuid::new_v4();
        let now = Utc::now();
        gauge.created_at = now;
        let id = gauge.id;
        self.record_tenant(id, tenant_id).await;
        self.gauges.write().await.insert(id, gauge.clone());
        Ok(gauge)
    }

    async fn update_gauge(&self, tenant_id: Uuid, id: Uuid, gauge: Gauge) -> Result<Gauge> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Gauge with id {id} not found"
            )));
        }
        let mut store = self.gauges.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Gauge with id {id} not found")))?;
        existing.name = gauge.name;
        existing.gauge_type = gauge.gauge_type;
        existing.status = gauge.status;
        existing.next_calibration_due = gauge.next_calibration_due;
        existing.calibration_frequency_days = gauge.calibration_frequency_days;
        Ok(existing.clone())
    }

    async fn delete_gauge(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Gauge with id {id} not found"
            )));
        }
        let mut store = self.gauges.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Gauge with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Complaint Create/Update/Delete ──────────────────────────────

    async fn create_complaint(
        &self,
        tenant_id: Uuid,
        mut complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint> {
        complaint.id = Uuid::new_v4();
        let now = Utc::now();
        complaint.created_at = now;
        complaint.updated_at = now;
        let id = complaint.id;
        self.record_tenant(id, tenant_id).await;
        self.complaints.write().await.insert(id, complaint.clone());
        Ok(complaint)
    }

    async fn update_complaint(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Complaint with id {id} not found"
            )));
        }
        let mut store = self.complaints.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint with id {id} not found")))?;
        existing.description = complaint.description;
        existing.status = complaint.status;
        existing.customer_id = complaint.customer_id;
        existing.product_id = complaint.product_id;
        existing.updated_at = Utc::now();
        Ok(existing.clone())
    }

    async fn delete_complaint(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Complaint with id {id} not found"
            )));
        }
        let mut store = self.complaints.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: 8D Report Create/Update/Delete ──────────────────────────────

    async fn create_eight_d_report(
        &self,
        tenant_id: Uuid,
        mut report: EightDReport,
    ) -> Result<EightDReport> {
        report.id = Uuid::new_v4();
        let now = Utc::now();
        report.created_at = now;
        let id = report.id;
        self.record_tenant(id, tenant_id).await;
        self.eight_d_reports
            .write()
            .await
            .insert(id, report.clone());
        Ok(report)
    }

    async fn update_eight_d_report(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        report: EightDReport,
    ) -> Result<EightDReport> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "8D report with id {id} not found"
            )));
        }
        let mut store = self.eight_d_reports.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("8D report with id {id} not found")))?;
        existing.complaint_id = report.complaint_id;
        existing.d1_team = report.d1_team;
        existing.d2_problem_description = report.d2_problem_description;
        existing.d3_containment = report.d3_containment;
        existing.d4_root_cause = report.d4_root_cause;
        existing.d5_corrective_action = report.d5_corrective_action;
        existing.d6_implementation = report.d6_implementation;
        existing.d7_preventive_action = report.d7_preventive_action;
        existing.d8_celebration = report.d8_celebration;
        Ok(existing.clone())
    }

    async fn delete_eight_d_report(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "8D report with id {id} not found"
            )));
        }
        let mut store = self.eight_d_reports.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("8D report with id {id} not found")))?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── New: Management Review Create/Update/Delete ──────────────────────

    async fn create_management_review(
        &self,
        tenant_id: Uuid,
        mut review: ManagementReview,
    ) -> Result<ManagementReview> {
        review.id = Uuid::new_v4();
        let now = Utc::now();
        review.created_at = now;
        let id = review.id;
        self.record_tenant(id, tenant_id).await;
        self.management_reviews
            .write()
            .await
            .insert(id, review.clone());
        Ok(review)
    }

    async fn update_management_review(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        review: ManagementReview,
    ) -> Result<ManagementReview> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Management review with id {id} not found"
            )));
        }
        let mut store = self.management_reviews.write().await;
        let existing = store.get_mut(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Management review with id {id} not found"))
        })?;
        existing.title = review.title;
        existing.notes = review.notes;
        existing.status = review.status;
        existing.actions = review.actions;
        Ok(existing.clone())
    }

    async fn delete_management_review(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Management review with id {id} not found"
            )));
        }
        let mut store = self.management_reviews.write().await;
        store.remove(&id).ok_or_else(|| {
            SenseiError::NotFound(format!("Management review with id {id} not found"))
        })?;
        self.tenant_index.write().await.remove(&id);
        Ok(())
    }

    // ── Getters for list-only entities ──────────────────────────────────

    async fn get_scar(&self, tenant_id: Uuid, id: Uuid) -> Result<Scar> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "SCAR with id {id} not found"
            )));
        }
        let store = self.scars.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR with id {id} not found")))
    }

    async fn get_document(&self, tenant_id: Uuid, id: Uuid) -> Result<QmsDocument> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Document with id {id} not found"
            )));
        }
        let store = self.documents.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Document with id {id} not found")))
    }

    async fn get_first_article_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<FirstArticleInspection> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "First article inspection with id {id} not found"
            )));
        }
        let store = self.first_article_inspections.read().await;
        store.get(&id).cloned().ok_or_else(|| {
            SenseiError::NotFound(format!("First article inspection with id {id} not found"))
        })
    }

    async fn get_self_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<SelfInspection> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Self-inspection with id {id} not found"
            )));
        }
        let store = self.self_inspections.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Self-inspection with id {id} not found")))
    }

    async fn get_msa_study(&self, tenant_id: Uuid, id: Uuid) -> Result<MsaStudy> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "MSA study with id {id} not found"
            )));
        }
        let store = self.msa_studies.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("MSA study with id {id} not found")))
    }

    async fn get_process_capability_study(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<ProcessCapabilityStudy> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Process capability study with id {id} not found"
            )));
        }
        let store = self.process_capability_studies.read().await;
        store.get(&id).cloned().ok_or_else(|| {
            SenseiError::NotFound(format!("Process capability study with id {id} not found"))
        })
    }

    async fn get_control_plan(&self, tenant_id: Uuid, id: Uuid) -> Result<ControlPlan> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Control plan with id {id} not found"
            )));
        }
        let store = self.control_plans.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Control plan with id {id} not found")))
    }

    async fn get_pfmea(&self, tenant_id: Uuid, id: Uuid) -> Result<PfmeaLite> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "PFMEA with id {id} not found"
            )));
        }
        let store = self.pfmeas.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("PFMEA with id {id} not found")))
    }

    async fn get_gauge(&self, tenant_id: Uuid, id: Uuid) -> Result<Gauge> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Gauge with id {id} not found"
            )));
        }
        let store = self.gauges.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Gauge with id {id} not found")))
    }

    async fn get_complaint(&self, tenant_id: Uuid, id: Uuid) -> Result<CustomerComplaint> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Complaint with id {id} not found"
            )));
        }
        let store = self.complaints.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint with id {id} not found")))
    }

    async fn get_eight_d_report(&self, tenant_id: Uuid, id: Uuid) -> Result<EightDReport> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "8D report with id {id} not found"
            )));
        }
        let store = self.eight_d_reports.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("8D report with id {id} not found")))
    }

    async fn get_management_review(&self, tenant_id: Uuid, id: Uuid) -> Result<ManagementReview> {
        if !self.tenant_matches(id, tenant_id).await {
            return Err(SenseiError::NotFound(format!(
                "Management review with id {id} not found"
            )));
        }
        let store = self.management_reviews.read().await;
        store.get(&id).cloned().ok_or_else(|| {
            SenseiError::NotFound(format!("Management review with id {id} not found"))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Test-only request-context constructor (twenty-ninth audit Wave B
    /// items 6-8): pure unit tests have no database, so the context is
    /// assembled directly with an EXPLICIT tenant-wide grant (bootstrap
    /// semantics — `RequestContext::build` never returns TenantWide; the
    /// DB-backed fixtures use the real builder). Tenant-wide keeps every
    /// record visible, exactly like the in-memory/dev mode.
    fn test_ctx(tenant_id: Uuid) -> RequestContext {
        RequestContext {
            tenant: tenant_id,
            principal: Uuid::new_v4(),
            scope: AuthorizedScope::tenant_wide(),
            focus: sensei_core::domain::OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }
    }

    #[tokio::test]
    async fn test_ncr_workflow_investigate_disposition_close() {
        let service = InMemoryQualityService::default();
        let tenant_id = Uuid::new_v4();
        let ctx = test_ctx(tenant_id);

        let ncr = service
            .create_ncr(
                &ctx,
                "Defect rate too high".to_string(),
                "PPM rose on line 3".to_string(),
                NcType::Product,
                NcSeverity::High,
                None,
                None,
                Some("PPM-01".to_string()),
                None,
                Some("Quality".to_string()),
                Some("Line 3".to_string()),
                false,
            )
            .await
            .unwrap();
        assert_eq!(ncr.status, NcrStatus::Open);

        // Investigate: RCA fields + Open → UnderInvestigation.
        let rca = RootCauseAnalysis {
            id: Uuid::new_v4(),
            capa_id: Uuid::nil(),
            description: "Misaligned fixture".to_string(),
            root_cause_type: "Machine".to_string(),
            analysis_method: "5-Why".to_string(),
            contributors: vec![],
            evidence: vec![],
            verified_by: None,
            verified_at: None,
            created_at: Utc::now(),
        };
        let investigated = service.investigate_ncr(&ctx, ncr.id, rca).await.unwrap();
        assert_eq!(investigated.status, NcrStatus::UnderInvestigation);
        assert_eq!(
            investigated.root_cause.as_deref(),
            Some("Misaligned fixture")
        );
        assert_eq!(investigated.root_cause_type.as_deref(), Some("Machine"));
        assert_eq!(investigated.analysis_method.as_deref(), Some("5-Why"));

        // Disposition: ActionDefined.
        let disposed = service
            .disposition_ncr(&ctx, ncr.id, "Rework and verify".to_string())
            .await
            .unwrap();
        assert_eq!(disposed.status, NcrStatus::ActionDefined);
        assert_eq!(disposed.disposition.as_deref(), Some("Rework and verify"));

        // Closing without completeness is rejected.
        let fresh = service
            .create_ncr(
                &ctx,
                "Incomplete".to_string(),
                "no data".to_string(),
                NcType::Process,
                NcSeverity::Low,
                None,
                None,
                None,
                None,
                None,
                None,
                false,
            )
            .await
            .unwrap();
        let err = service.close_ncr(&ctx, fresh.id).await.unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));

        // Complete lifecycle closes with closed_at set.
        let closed = service.close_ncr(&ctx, ncr.id).await.unwrap();
        assert_eq!(closed.status, NcrStatus::Closed);
        assert!(closed.closed_at.is_some());

        // Closed NCRs reject further investigation.
        let err = service
            .investigate_ncr(
                &ctx,
                ncr.id,
                RootCauseAnalysis {
                    id: Uuid::new_v4(),
                    capa_id: Uuid::nil(),
                    description: "x".to_string(),
                    root_cause_type: "y".to_string(),
                    analysis_method: "z".to_string(),
                    contributors: vec![],
                    evidence: vec![],
                    verified_by: None,
                    verified_at: None,
                    created_at: Utc::now(),
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));
    }

    #[tokio::test]
    async fn test_list_ncrs_filters_by_status_and_source() {
        let service = InMemoryQualityService::default();
        let tenant_id = Uuid::new_v4();
        let ctx = test_ctx(tenant_id);

        let first = service
            .create_ncr(
                &ctx,
                "A".to_string(),
                "d".to_string(),
                NcType::Product,
                NcSeverity::Medium,
                None,
                None,
                None,
                None,
                None,
                None,
                false,
            )
            .await
            .unwrap();
        service
            .create_ncr(
                &ctx,
                "B".to_string(),
                "d".to_string(),
                NcType::Process,
                NcSeverity::Low,
                None,
                None,
                None,
                None,
                None,
                None,
                false,
            )
            .await
            .unwrap();

        // Set the source on one NCR via update.
        let mut updated = first.clone();
        updated.source = Some("inspection".to_string());
        service.update_ncr(&ctx, first.id, updated).await.unwrap();

        let page = service
            .list_ncrs(&ctx, Some("open"), None, None, None, None)
            .await
            .unwrap();
        assert_eq!(page.data.len(), 2);

        let page = service
            .list_ncrs(&ctx, Some("open"), None, Some("inspection"), None, None)
            .await
            .unwrap();
        assert_eq!(page.data.len(), 1);
        assert_eq!(page.data[0].id, first.id);

        let page = service
            .list_ncrs(&ctx, None, Some("critical"), None, None, None)
            .await
            .unwrap();
        assert!(page.data.is_empty());
    }

    #[tokio::test]
    async fn test_verify_capa_records_effectiveness() {
        let service = InMemoryQualityService::default();
        let tenant_id = Uuid::new_v4();
        let ctx = test_ctx(tenant_id);

        // Verification without RCA/actions is rejected.
        let capa = service
            .create_capa(
                &ctx,
                "Fix calibration".to_string(),
                "desc".to_string(),
                vec![],
                CapaType::Corrective,
                CapaPriority::High,
                None,
                None,
            )
            .await
            .unwrap();
        let err = service.verify_capa(&ctx, capa.id).await.unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));

        // Seed an RCA and an action, then verify.
        let mut with_rca = capa.clone();
        with_rca.root_cause_analyses.push(RootCauseAnalysis {
            id: Uuid::new_v4(),
            capa_id: capa.id,
            description: "Calibration drift".to_string(),
            root_cause_type: "Machine".to_string(),
            analysis_method: "Fishbone".to_string(),
            contributors: vec![],
            evidence: vec![],
            verified_by: None,
            verified_at: None,
            created_at: Utc::now(),
        });
        with_rca.actions.push(CorrectiveAction {
            id: Uuid::new_v4(),
            capa_id: capa.id,
            description: "Recalibrate".to_string(),
            action_type: "corrective".to_string(),
            owner_id: None,
            status: ActionStatus::Verified,
            due_date: None,
            completed_at: None,
            verified_by: None,
            verified_at: None,
            verification_notes: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        });
        service.update_capa(&ctx, capa.id, with_rca).await.unwrap();

        let verified = service.verify_capa(&ctx, capa.id).await.unwrap();
        assert_eq!(verified.status, CapaStatusEx::Verification);
        assert!(
            verified
                .effectiveness_checks
                .iter()
                .any(|ec| ec.is_effective),
            "verification must record an effectiveness check"
        );
    }

    #[tokio::test]
    async fn test_site_scoped_caller_only_sees_stamped_records() {
        let service = InMemoryQualityService::default();
        let tenant_a = Uuid::new_v4();
        let tenant_b = Uuid::new_v4();
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let corporate_ctx = test_ctx(tenant_a);

        // Server-side stamping (item 2): a caller acting in site A gets a
        // record stamped with site A; a corporate caller (no operating
        // focus, tenant-wide grant) gets an UNSTAMPED (corporate) record.
        let site_a_ctx = RequestContext {
            focus: sensei_core::domain::OperationalFocus {
                site: Some(site_a),
                value_stream: None,
                work_center: None,
                shift: None,
            },
            ..test_ctx(tenant_a)
        };
        let stamped = service
            .create_ncr(
                &site_a_ctx,
                "Site A defect".to_string(),
                "d".to_string(),
                NcType::Product,
                NcSeverity::Medium,
                None,
                None,
                None,
                None,
                None,
                None,
                false,
            )
            .await
            .unwrap();
        let corporate = service
            .create_ncr(
                &corporate_ctx,
                "Corporate finding".to_string(),
                "d".to_string(),
                NcType::System,
                NcSeverity::High,
                None,
                None,
                None,
                None,
                None,
                None,
                false,
            )
            .await
            .unwrap();

        // A SITE-A-scoped caller (Operational { sites: {site_a} }) sees
        // the site-A record but NOT the corporate one.
        let site_a_scope_ctx = RequestContext {
            scope: AuthorizedScope::Operational {
                sites: std::collections::HashSet::from([site_a]),
                work_centers: std::collections::HashSet::new(),
            },
            focus: sensei_core::domain::OperationalFocus {
                site: Some(site_a),
                value_stream: None,
                work_center: None,
                shift: None,
            },
            ..test_ctx(tenant_a)
        };
        let listed = service
            .list_ncrs(&site_a_scope_ctx, None, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(listed.data.len(), 1, "site-scoped list sees its site only");
        assert_eq!(listed.data[0].id, stamped.id);
        assert!(
            service
                .get_ncr(&site_a_scope_ctx, corporate.id)
                .await
                .is_err(),
            "corporate record is invisible to a site-scoped caller (NotFound)"
        );
        assert!(
            service.get_ncr(&site_a_scope_ctx, stamped.id).await.is_ok(),
            "stamped record resolves for its site"
        );

        // A SITE-B-scoped caller sees neither record.
        let site_b_scope_ctx = RequestContext {
            scope: AuthorizedScope::Operational {
                sites: std::collections::HashSet::from([site_b]),
                work_centers: std::collections::HashSet::new(),
            },
            focus: sensei_core::domain::OperationalFocus {
                site: Some(site_b),
                value_stream: None,
                work_center: None,
                shift: None,
            },
            ..test_ctx(tenant_a)
        };
        let listed_b = service
            .list_ncrs(&site_b_scope_ctx, None, None, None, None, None)
            .await
            .unwrap();
        assert!(listed_b.data.is_empty(), "foreign site sees nothing");
        assert!(
            service
                .get_ncr(&site_b_scope_ctx, stamped.id)
                .await
                .is_err(),
            "out-of-scope get is NotFound"
        );

        // NoOperationalScope sees nothing, even for a stamped record.
        let no_scope_ctx = RequestContext {
            scope: AuthorizedScope::NoOperationalScope,
            focus: sensei_core::domain::OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            ..test_ctx(tenant_a)
        };
        let listed_none = service
            .list_ncrs(&no_scope_ctx, None, None, None, None, None)
            .await
            .unwrap();
        assert!(listed_none.data.is_empty(), "no scope → no rows");
        assert!(
            service.get_ncr(&no_scope_ctx, stamped.id).await.is_err(),
            "no scope → NotFound"
        );

        // The tenant-wide caller sees everything (corporate included),
        // and a foreign TENANT never sees the records at all.
        let all = service
            .list_ncrs(&corporate_ctx, None, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(all.data.len(), 2);
        let foreign = service
            .list_ncrs(&test_ctx(tenant_b), None, None, None, None, None)
            .await
            .unwrap();
        assert!(foreign.data.is_empty(), "tenant isolation holds");
    }
}

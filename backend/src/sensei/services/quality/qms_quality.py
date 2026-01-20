"""
Advanced Quality System (QMS) Service.

Implements Section 21.5 of the Development Plan:
- QMS governance (document control, external document list, quality objectives/KPIs)
- Supplier quality (scorecards, SCAR workflow, supplier audits)
- Audit management (calendar, execution checklists, finding lifecycle)
- Risk-based thinking (risk/opportunity registry, mitigation tracking)
- Gauge & calibration management (registry, alerts, out-of-cal impact assessment)
- Control plans & PFMEA-lite (dynamic control plans, risk markers)
- Customer feedback & review (complaints/RMA, 8D automation, management review packs)

This module follows the repo convention of in-memory, test-friendly services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Iterable
from uuid import UUID, uuid4

from sensei.services.ai.reasoning_engine import SenseiReasoningEngine, A3Phase, MentorPersona


# =============================================================================
# ENUMS
# =============================================================================


class QMSDocumentType(str, Enum):
    QUALITY_MANUAL = "quality_manual"
    PROCEDURE = "procedure"
    WORK_INSTRUCTION = "work_instruction"
    FORM_TEMPLATE = "form_template"
    RECORD_TEMPLATE = "record_template"


class QMSDocumentStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    OBSOLETE = "obsolete"


class SignatureRole(str, Enum):
    AUTHOR = "author"
    REVIEWER = "reviewer"
    APPROVER = "approver"


class ExternalDocStatus(str, Enum):
    ACTIVE = "active"
    OBSOLETE = "obsolete"


class KPITrend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"
    UNKNOWN = "unknown"


class SCARStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    CONTAINMENT = "containment"
    ROOT_CAUSE = "root_cause"
    CORRECTIVE_ACTION = "corrective_action"
    VERIFICATION = "verification"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class AuditType(str, Enum):
    INTERNAL_PROCESS = "internal_process"
    INTERNAL_PRODUCT = "internal_product"
    INTERNAL_SYSTEM = "internal_system"
    SUPPLIER = "supplier"
    THIRD_PARTY = "third_party"
    CUSTOMER = "customer"


class AuditStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FindingSeverity(str, Enum):
    OBSERVATION = "observation"
    MINOR_NC = "minor_nc"
    MAJOR_NC = "major_nc"
    CRITICAL_NC = "critical_nc"


class FindingStatus(str, Enum):
    OPEN = "open"
    ACTION_PLANNED = "action_planned"
    ACTION_IMPLEMENTED = "action_implemented"
    VERIFIED_CLOSED = "verified_closed"
    CANCELLED = "cancelled"


class RiskType(str, Enum):
    RISK = "risk"
    OPPORTUNITY = "opportunity"


class RiskStatus(str, Enum):
    OPEN = "open"
    MITIGATING = "mitigating"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class MitigationStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class GaugeStatus(str, Enum):
    ACTIVE = "active"
    OUT_OF_SERVICE = "out_of_service"
    SCRAPPED = "scrapped"


class CalibrationStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComplaintStatus(str, Enum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    INVESTIGATION = "investigation"
    CONTAINMENT = "containment"
    CAPA = "capa"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass(frozen=True)
class ElectronicSignature:
    signer_id: str
    signer_name: str
    role: SignatureRole
    meaning: str  # e.g., "I approve this document"
    signed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class QMSDocumentRevision:
    id: UUID = field(default_factory=uuid4)
    document_id: UUID = field(default_factory=uuid4)
    revision_code: str = "A"
    status: QMSDocumentStatus = QMSDocumentStatus.DRAFT
    title: str = ""
    content_hash: str = ""  # treat as opaque (hash of file or text)
    change_summary: str = ""
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    effective_date: Optional[date] = None
    signatures: list[ElectronicSignature] = field(default_factory=list)
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    obsolete_at: Optional[datetime] = None


@dataclass
class QMSDocument:
    id: UUID = field(default_factory=uuid4)
    doc_type: QMSDocumentType = QMSDocumentType.PROCEDURE
    doc_number: str = ""  # e.g., "QP-001"
    title: str = ""
    owner: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_revision_id: Optional[UUID] = None
    revision_ids: list[UUID] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ExternalDocument:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    publisher: str = ""  # customer/standard body
    identifier: str = ""  # e.g., "AS9100D", "Customer-Spec-123"
    version: str = ""
    status: ExternalDocStatus = ExternalDocStatus.ACTIVE
    owner: str = ""
    last_reviewed_at: Optional[datetime] = None
    review_interval_days: int = 365
    superseded_by_id: Optional[UUID] = None
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class KPIValue:
    id: UUID = field(default_factory=uuid4)
    kpi_key: str = ""  # e.g., "fpy"
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    value: Decimal = Decimal("0")
    target: Optional[Decimal] = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


@dataclass
class QualityObjective:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    owner: str = ""
    kpi_keys: list[str] = field(default_factory=list)
    targets: dict[str, Decimal] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SupplierProfile:
    supplier_id: str = ""
    supplier_name: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SupplierPeriodStats:
    supplier_id: str
    period_key: str  # e.g., "2026-01"
    units_received: int = 0
    defects_found: int = 0
    deliveries_total: int = 0
    deliveries_on_time: int = 0
    copq_scrap_cost: Decimal = Decimal("0")
    copq_rework_cost: Decimal = Decimal("0")
    copq_warranty_cost: Decimal = Decimal("0")
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SupplierScorecard:
    supplier_id: str
    period_key: str
    ppm: Decimal
    otd: Decimal
    copq: Decimal


@dataclass
class SCAR:
    id: UUID = field(default_factory=uuid4)
    supplier_id: str = ""
    title: str = ""
    description: str = ""
    status: SCARStatus = SCARStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""

    # Links
    related_nc_id: Optional[UUID] = None
    related_capa_id: Optional[UUID] = None
    related_lot_id: Optional[str] = None

    # Workflow data
    containment_actions: list[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    corrective_actions: list[str] = field(default_factory=list)
    verification_notes: Optional[str] = None
    closed_at: Optional[datetime] = None
    portal_access_token: Optional[str] = None


@dataclass
class AuditChecklistItem:
    id: UUID = field(default_factory=uuid4)
    prompt: str = ""
    requirement_ref: str = ""  # clause/spec reference
    is_conformant: Optional[bool] = None
    notes: str = ""
    evidence_links: list[str] = field(default_factory=list)


@dataclass
class Audit:
    id: UUID = field(default_factory=uuid4)
    audit_type: AuditType = AuditType.INTERNAL_PROCESS
    title: str = ""
    scheduled_for: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_minutes: int = 60
    scope: str = ""
    auditor_ids: list[str] = field(default_factory=list)
    auditee_ids: list[str] = field(default_factory=list)
    supplier_id: Optional[str] = None
    status: AuditStatus = AuditStatus.PLANNED
    checklist: list[AuditChecklistItem] = field(default_factory=list)
    finding_ids: list[UUID] = field(default_factory=list)
    completed_at: Optional[datetime] = None


@dataclass
class AuditFinding:
    id: UUID = field(default_factory=uuid4)
    audit_id: UUID = field(default_factory=uuid4)
    severity: FindingSeverity = FindingSeverity.MINOR_NC
    title: str = ""
    description: str = ""
    requirement_ref: str = ""
    status: FindingStatus = FindingStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_by: Optional[date] = None
    assigned_to: Optional[str] = None
    corrective_action_plan: Optional[str] = None
    implementation_notes: Optional[str] = None
    verification_notes: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    linked_nc_id: Optional[UUID] = None
    linked_capa_id: Optional[UUID] = None


@dataclass
class RiskOpportunity:
    id: UUID = field(default_factory=uuid4)
    risk_type: RiskType = RiskType.RISK
    title: str = ""
    description: str = ""
    objective_id: Optional[UUID] = None
    owner: str = ""
    likelihood: int = 1  # 1-5
    impact: int = 1  # 1-5
    status: RiskStatus = RiskStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    linked_a3_id: Optional[UUID] = None
    linked_capa_id: Optional[UUID] = None
    mitigation_ids: list[UUID] = field(default_factory=list)


@dataclass
class MitigationAction:
    id: UUID = field(default_factory=uuid4)
    risk_id: UUID = field(default_factory=uuid4)
    description: str = ""
    owner: str = ""
    due_by: Optional[date] = None
    status: MitigationStatus = MitigationStatus.PLANNED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


@dataclass
class Gauge:
    id: UUID = field(default_factory=uuid4)
    gauge_number: str = ""  # shop identifier
    description: str = ""
    location: str = ""
    owner: str = ""
    status: GaugeStatus = GaugeStatus.ACTIVE
    calibration_interval_days: int = 180
    last_calibrated_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CalibrationEvent:
    id: UUID = field(default_factory=uuid4)
    gauge_id: UUID = field(default_factory=uuid4)
    scheduled_for: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    performed_at: Optional[datetime] = None
    performed_by: Optional[str] = None
    status: CalibrationStatus = CalibrationStatus.SCHEDULED
    result_notes: str = ""
    out_of_cal: bool = False
    out_of_cal_since: Optional[datetime] = None
    out_of_cal_until: Optional[datetime] = None


@dataclass(frozen=True)
class MeasurementRecord:
    gauge_id: UUID
    lot_id: str
    measured_at: datetime
    characteristic: str
    value: Decimal


@dataclass
class ControlPlanCheckpoint:
    id: UUID = field(default_factory=uuid4)
    characteristic: str = ""  # CTQ/feature
    method: str = ""  # how measured
    frequency: str = ""  # e.g., "first_article", "hourly", "every_10"
    sample_size: int = 1
    reaction_plan: str = ""
    pfmea_rpn: Optional[int] = None


@dataclass
class ControlPlan:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    product_id: Optional[UUID] = None
    process_id: Optional[UUID] = None
    revision: str = "A"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checkpoints: list[ControlPlanCheckpoint] = field(default_factory=list)


@dataclass
class PFMEAStep:
    id: UUID = field(default_factory=uuid4)
    process_step: str = ""
    failure_mode: str = ""
    effects: str = ""
    causes: str = ""
    current_controls: str = ""
    severity: int = 1  # 1-10
    occurrence: int = 1  # 1-10
    detection: int = 1  # 1-10

    def rpn(self) -> int:
        return int(self.severity) * int(self.occurrence) * int(self.detection)


@dataclass
class PFMEALite:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    process_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    steps: list[PFMEAStep] = field(default_factory=list)


@dataclass
class CustomerComplaint:
    id: UUID = field(default_factory=uuid4)
    customer_id: Optional[str] = None
    title: str = ""
    description: str = ""
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ComplaintStatus = ComplaintStatus.RECEIVED

    lot_id: Optional[str] = None
    related_nc_id: Optional[UUID] = None
    related_capa_id: Optional[UUID] = None
    rma_number: Optional[str] = None
    attachments: list[str] = field(default_factory=list)

    containment_actions: list[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    corrective_actions: list[str] = field(default_factory=list)
    closed_at: Optional[datetime] = None


@dataclass
class EightDReport:
    id: UUID = field(default_factory=uuid4)
    complaint_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    d1_team: list[str] = field(default_factory=list)
    d2_problem: str = ""
    d3_containment: list[str] = field(default_factory=list)
    d4_root_cause: str = ""
    d5_corrective_actions: list[str] = field(default_factory=list)
    d6_validate: str = ""
    d7_prevent_recurrence: list[str] = field(default_factory=list)
    d8_congratulate: str = ""


@dataclass
class ManagementReviewPack:
    id: UUID = field(default_factory=uuid4)
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prepared_by: str = ""

    kpi_summary: dict[str, Decimal] = field(default_factory=dict)
    open_findings: int = 0
    open_scars: int = 0
    open_risks: int = 0
    overdue_calibrations: int = 0
    document_changes: int = 0
    notes: str = ""


# =============================================================================
# SERVICE
# =============================================================================


class QMSQualityService:
    """In-memory Advanced QMS service."""

    def __init__(self, reasoning_engine: Optional[SenseiReasoningEngine] = None) -> None:
        self.reasoning_engine = reasoning_engine
        self.documents: dict[UUID, QMSDocument] = {}
        self.revisions: dict[UUID, QMSDocumentRevision] = {}
        self.external_documents: dict[UUID, ExternalDocument] = {}
        self.objectives: dict[UUID, QualityObjective] = {}
        self.kpi_values: list[KPIValue] = []

        self.suppliers: dict[str, SupplierProfile] = {}
        self.supplier_stats: dict[tuple[str, str], SupplierPeriodStats] = {}
        self.scars: dict[UUID, SCAR] = {}

        self.audits: dict[UUID, Audit] = {}
        self.findings: dict[UUID, AuditFinding] = {}

        self.risks: dict[UUID, RiskOpportunity] = {}
        self.mitigations: dict[UUID, MitigationAction] = {}

        self.gauges: dict[UUID, Gauge] = {}
        self.calibrations: dict[UUID, CalibrationEvent] = {}
        self.measurements: list[MeasurementRecord] = []

        self.control_plans: dict[UUID, ControlPlan] = {}
        self.pfmeas: dict[UUID, PFMEALite] = {}

        self.complaints: dict[UUID, CustomerComplaint] = {}
        self.eightd_reports: dict[UUID, EightDReport] = {}
        self.management_reviews: dict[UUID, ManagementReviewPack] = {}

    # -----------------------------
    # Helpers
    # -----------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    @staticmethod
    def _period_key(d: date) -> str:
        return f"{d.year:04d}-{d.month:02d}"

    # -----------------------------
    # Document control
    # -----------------------------

    def create_document(
        self,
        doc_type: QMSDocumentType,
        doc_number: str,
        title: str,
        owner: str,
        created_by: str,
        initial_revision_code: str = "A",
        content_hash: str = "",
        change_summary: str = "Initial release",
        tags: Optional[list[str]] = None,
    ) -> QMSDocument:
        self._require(bool(doc_number.strip()), "doc_number is required")
        self._require(bool(title.strip()), "title is required")

        doc = QMSDocument(doc_type=doc_type, doc_number=doc_number, title=title, owner=owner)
        if tags:
            doc.tags = list(tags)

        rev = QMSDocumentRevision(
            document_id=doc.id,
            revision_code=initial_revision_code,
            status=QMSDocumentStatus.DRAFT,
            title=title,
            content_hash=content_hash,
            change_summary=change_summary,
            created_by=created_by,
        )

        doc.revision_ids.append(rev.id)
        doc.current_revision_id = rev.id

        self.documents[doc.id] = doc
        self.revisions[rev.id] = rev
        return doc

    def start_revision(
        self,
        document_id: UUID,
        revision_code: str,
        created_by: str,
        content_hash: str,
        change_summary: str,
        title: Optional[str] = None,
    ) -> QMSDocumentRevision:
        self._require(document_id in self.documents, "document not found")
        doc = self.documents[document_id]

        for rev_id in doc.revision_ids:
            if self.revisions[rev_id].revision_code == revision_code:
                raise ValueError("revision_code already exists")

        rev = QMSDocumentRevision(
            document_id=document_id,
            revision_code=revision_code,
            status=QMSDocumentStatus.DRAFT,
            title=title or doc.title,
            content_hash=content_hash,
            change_summary=change_summary,
            created_by=created_by,
        )
        self.revisions[rev.id] = rev
        doc.revision_ids.append(rev.id)
        doc.current_revision_id = rev.id
        return rev

    def submit_revision_for_review(self, revision_id: UUID) -> QMSDocumentRevision:
        self._require(revision_id in self.revisions, "revision not found")
        rev = self.revisions[revision_id]
        self._require(rev.status in {QMSDocumentStatus.DRAFT}, "revision not in draft")
        rev.status = QMSDocumentStatus.IN_REVIEW
        return rev

    def sign_revision(
        self,
        revision_id: UUID,
        signer_id: str,
        signer_name: str,
        role: SignatureRole,
        meaning: str,
    ) -> QMSDocumentRevision:
        self._require(revision_id in self.revisions, "revision not found")
        rev = self.revisions[revision_id]
        self._require(rev.status in {QMSDocumentStatus.IN_REVIEW, QMSDocumentStatus.DRAFT}, "cannot sign in current status")

        # prevent duplicate signatures for same role+person
        for sig in rev.signatures:
            if sig.signer_id == signer_id and sig.role == role:
                raise ValueError("duplicate signature")

        rev.signatures.append(
            ElectronicSignature(
                signer_id=signer_id,
                signer_name=signer_name,
                role=role,
                meaning=meaning,
            )
        )
        return rev

    def approve_revision(self, revision_id: UUID, require_roles: Iterable[SignatureRole] = (SignatureRole.AUTHOR, SignatureRole.APPROVER)) -> QMSDocumentRevision:
        self._require(revision_id in self.revisions, "revision not found")
        rev = self.revisions[revision_id]
        self._require(rev.status in {QMSDocumentStatus.IN_REVIEW}, "revision must be in review")

        roles_present = {sig.role for sig in rev.signatures}
        required = set(require_roles)
        missing = required.difference(roles_present)
        self._require(not missing, f"missing required signatures: {sorted(r.value for r in missing)}")

        rev.status = QMSDocumentStatus.APPROVED
        rev.approved_at = self._now()
        return rev

    def publish_revision(self, revision_id: UUID, effective_date: Optional[date] = None) -> QMSDocumentRevision:
        self._require(revision_id in self.revisions, "revision not found")
        rev = self.revisions[revision_id]
        self._require(rev.status == QMSDocumentStatus.APPROVED, "revision must be approved")
        rev.status = QMSDocumentStatus.PUBLISHED
        rev.published_at = self._now()
        rev.effective_date = effective_date or date.today()

        # mark previous published revisions obsolete
        doc = self.documents[rev.document_id]
        for rid in doc.revision_ids:
            other = self.revisions[rid]
            if other.id != rev.id and other.status == QMSDocumentStatus.PUBLISHED:
                other.status = QMSDocumentStatus.OBSOLETE
                other.obsolete_at = self._now()
        doc.current_revision_id = rev.id
        return rev

    def get_document_history(self, document_id: UUID) -> list[QMSDocumentRevision]:
        self._require(document_id in self.documents, "document not found")
        doc = self.documents[document_id]
        return [self.revisions[rid] for rid in doc.revision_ids]

    # -----------------------------
    # External docs
    # -----------------------------

    def add_external_document(
        self,
        name: str,
        publisher: str,
        identifier: str,
        version: str,
        owner: str,
        review_interval_days: int = 365,
        notes: str = "",
    ) -> ExternalDocument:
        self._require(bool(identifier.strip()), "identifier is required")
        self._require(review_interval_days > 0, "review_interval_days must be positive")

        doc = ExternalDocument(
            name=name,
            publisher=publisher,
            identifier=identifier,
            version=version,
            owner=owner,
            review_interval_days=review_interval_days,
            notes=notes,
        )
        self.external_documents[doc.id] = doc
        return doc

    def supersede_external_document(self, old_doc_id: UUID, new_version: str, superseded_by_id: Optional[UUID] = None) -> ExternalDocument:
        self._require(old_doc_id in self.external_documents, "external doc not found")
        old = self.external_documents[old_doc_id]
        old.status = ExternalDocStatus.OBSOLETE
        old.superseded_by_id = superseded_by_id
        old.last_reviewed_at = self._now()

        # Optionally create a new entry for the new version.
        if superseded_by_id is None:
            new = ExternalDocument(
                name=old.name,
                publisher=old.publisher,
                identifier=old.identifier,
                version=new_version,
                owner=old.owner,
                status=ExternalDocStatus.ACTIVE,
                review_interval_days=old.review_interval_days,
                notes=f"Supersedes {old.version}",
            )
            self.external_documents[new.id] = new
            old.superseded_by_id = new.id
            return new

        return old

    def get_external_docs_due_for_review(self, as_of: Optional[datetime] = None) -> list[ExternalDocument]:
        now = as_of or self._now()
        due: list[ExternalDocument] = []
        for doc in self.external_documents.values():
            if doc.status != ExternalDocStatus.ACTIVE:
                continue
            last = doc.last_reviewed_at or doc.created_at
            next_due = last + timedelta(days=int(doc.review_interval_days))
            if next_due <= now:
                due.append(doc)
        return sorted(due, key=lambda d: d.created_at)

    # -----------------------------
    # Quality objectives & KPIs
    # -----------------------------

    def create_quality_objective(
        self,
        name: str,
        description: str,
        owner: str,
        kpi_keys: list[str],
        targets: Optional[dict[str, Decimal]] = None,
    ) -> QualityObjective:
        self._require(bool(name.strip()), "name is required")
        obj = QualityObjective(name=name, description=description, owner=owner, kpi_keys=list(kpi_keys), targets=targets or {})
        self.objectives[obj.id] = obj
        return obj

    def record_kpi_value(
        self,
        kpi_key: str,
        period_start: date,
        period_end: date,
        value: Decimal,
        target: Optional[Decimal] = None,
        notes: str = "",
    ) -> KPIValue:
        self._require(bool(kpi_key.strip()), "kpi_key is required")
        self._require(period_end >= period_start, "period_end must be >= period_start")
        kv = KPIValue(kpi_key=kpi_key, period_start=period_start, period_end=period_end, value=value, target=target, notes=notes)
        self.kpi_values.append(kv)
        return kv

    def get_latest_kpi(self, kpi_key: str) -> Optional[KPIValue]:
        items = [k for k in self.kpi_values if k.kpi_key == kpi_key]
        if not items:
            return None
        items.sort(key=lambda x: (x.period_end, x.recorded_at))
        return items[-1]

    def compute_kpi_trend(self, kpi_key: str) -> KPITrend:
        items = [k for k in self.kpi_values if k.kpi_key == kpi_key]
        items.sort(key=lambda x: (x.period_end, x.recorded_at))
        if len(items) < 2:
            return KPITrend.UNKNOWN
        a, b = items[-2], items[-1]
        if b.value == a.value:
            return KPITrend.STABLE
        # Assume higher is better for most KPIs unless target indicates otherwise.
        if b.target is not None:
            # If target is an upper bound (defect rate), we can't infer direction reliably.
            return KPITrend.UNKNOWN
        return KPITrend.IMPROVING if b.value > a.value else KPITrend.DETERIORATING

    # -----------------------------
    # Supplier scorecards
    # -----------------------------

    def upsert_supplier(self, supplier_id: str, supplier_name: str) -> SupplierProfile:
        self._require(bool(supplier_id.strip()), "supplier_id is required")
        if supplier_id in self.suppliers:
            profile = self.suppliers[supplier_id]
            profile.supplier_name = supplier_name or profile.supplier_name
            return profile
        profile = SupplierProfile(supplier_id=supplier_id, supplier_name=supplier_name)
        self.suppliers[supplier_id] = profile
        return profile

    def _get_supplier_stats(self, supplier_id: str, period_key: str) -> SupplierPeriodStats:
        key = (supplier_id, period_key)
        if key not in self.supplier_stats:
            self.supplier_stats[key] = SupplierPeriodStats(supplier_id=supplier_id, period_key=period_key)
        return self.supplier_stats[key]

    def record_supplier_receipt(self, supplier_id: str, receipt_date: date, units_received: int) -> SupplierPeriodStats:
        self._require(units_received >= 0, "units_received must be >= 0")
        pk = self._period_key(receipt_date)
        stats = self._get_supplier_stats(supplier_id, pk)
        stats.units_received += int(units_received)
        stats.updated_at = self._now()
        return stats

    def record_supplier_defects(self, supplier_id: str, defect_date: date, defects_found: int) -> SupplierPeriodStats:
        self._require(defects_found >= 0, "defects_found must be >= 0")
        pk = self._period_key(defect_date)
        stats = self._get_supplier_stats(supplier_id, pk)
        stats.defects_found += int(defects_found)
        stats.updated_at = self._now()
        return stats

    def record_supplier_delivery(self, supplier_id: str, delivery_date: date, on_time: bool) -> SupplierPeriodStats:
        pk = self._period_key(delivery_date)
        stats = self._get_supplier_stats(supplier_id, pk)
        stats.deliveries_total += 1
        stats.deliveries_on_time += 1 if on_time else 0
        stats.updated_at = self._now()
        return stats

    def record_supplier_copq(
        self,
        supplier_id: str,
        cost_date: date,
        scrap_cost: Decimal = Decimal("0"),
        rework_cost: Decimal = Decimal("0"),
        warranty_cost: Decimal = Decimal("0"),
    ) -> SupplierPeriodStats:
        pk = self._period_key(cost_date)
        stats = self._get_supplier_stats(supplier_id, pk)
        stats.copq_scrap_cost += scrap_cost
        stats.copq_rework_cost += rework_cost
        stats.copq_warranty_cost += warranty_cost
        stats.updated_at = self._now()
        return stats

    def compute_supplier_scorecard(self, supplier_id: str, period_key: str) -> SupplierScorecard:
        stats = self._get_supplier_stats(supplier_id, period_key)
        units = max(0, stats.units_received)
        defects = max(0, stats.defects_found)
        ppm = Decimal("0")
        if units > 0:
            ppm = (Decimal(defects) / Decimal(units)) * Decimal("1000000")

        otd = Decimal("0")
        if stats.deliveries_total > 0:
            otd = Decimal(stats.deliveries_on_time) / Decimal(stats.deliveries_total)

        copq = stats.copq_scrap_cost + stats.copq_rework_cost + stats.copq_warranty_cost
        return SupplierScorecard(supplier_id=supplier_id, period_key=period_key, ppm=ppm, otd=otd, copq=copq)

    # -----------------------------
    # SCAR workflow
    # -----------------------------

    def create_scar(
        self,
        supplier_id: str,
        title: str,
        description: str,
        created_by: str,
        related_nc_id: Optional[UUID] = None,
        related_capa_id: Optional[UUID] = None,
        related_lot_id: Optional[str] = None,
    ) -> SCAR:
        self._require(bool(supplier_id.strip()), "supplier_id is required")
        self._require(bool(title.strip()), "title is required")
        scar = SCAR(
            supplier_id=supplier_id,
            title=title,
            description=description,
            created_by=created_by,
            related_nc_id=related_nc_id,
            related_capa_id=related_capa_id,
            related_lot_id=related_lot_id,
        )
        self.scars[scar.id] = scar
        return scar

    def send_scar(self, scar_id: UUID, portal_access_token: str) -> SCAR:
        self._require(scar_id in self.scars, "scar not found")
        scar = self.scars[scar_id]
        self._require(scar.status == SCARStatus.DRAFT, "scar must be draft")
        self._require(bool(portal_access_token.strip()), "portal_access_token is required")
        scar.status = SCARStatus.SENT
        scar.portal_access_token = portal_access_token
        return scar

    def add_scar_containment(self, scar_id: UUID, action: str) -> SCAR:
        self._require(scar_id in self.scars, "scar not found")
        scar = self.scars[scar_id]
        self._require(scar.status in {SCARStatus.SENT, SCARStatus.CONTAINMENT}, "scar not in containment")
        scar.status = SCARStatus.CONTAINMENT
        scar.containment_actions.append(action)
        return scar

    def set_scar_root_cause(self, scar_id: UUID, root_cause: str) -> SCAR:
        self._require(scar_id in self.scars, "scar not found")
        scar = self.scars[scar_id]
        self._require(scar.status in {SCARStatus.CONTAINMENT, SCARStatus.ROOT_CAUSE}, "scar not in root cause")
        self._require(bool(root_cause.strip()), "root_cause is required")
        scar.status = SCARStatus.ROOT_CAUSE
        scar.root_cause = root_cause
        return scar

    def add_scar_corrective_action(self, scar_id: UUID, action: str) -> SCAR:
        self._require(scar_id in self.scars, "scar not found")
        scar = self.scars[scar_id]
        self._require(scar.status in {SCARStatus.ROOT_CAUSE, SCARStatus.CORRECTIVE_ACTION}, "scar not in corrective action")
        self._require(bool(action.strip()), "action is required")
        scar.status = SCARStatus.CORRECTIVE_ACTION
        scar.corrective_actions.append(action)
        return scar

    def verify_and_close_scar(self, scar_id: UUID, verification_notes: str) -> SCAR:
        self._require(scar_id in self.scars, "scar not found")
        scar = self.scars[scar_id]
        # Allow callers to attempt closure from earlier states; gate with explicit requirements.
        self._require(
            scar.status
            in {
                SCARStatus.SENT,
                SCARStatus.CONTAINMENT,
                SCARStatus.ROOT_CAUSE,
                SCARStatus.CORRECTIVE_ACTION,
                SCARStatus.VERIFICATION,
            },
            "scar not ready for verification",
        )
        self._require(bool(scar.root_cause), "root cause not set")
        self._require(bool(scar.corrective_actions), "no corrective actions")
        scar.status = SCARStatus.CLOSED
        scar.verification_notes = verification_notes
        scar.closed_at = self._now()
        return scar

    def list_open_scars(self) -> list[SCAR]:
        return [s for s in self.scars.values() if s.status not in {SCARStatus.CLOSED, SCARStatus.CANCELLED}]

    # -----------------------------
    # Audit management
    # -----------------------------

    def schedule_audit(
        self,
        audit_type: AuditType,
        title: str,
        scheduled_for: datetime,
        auditor_ids: list[str],
        scope: str,
        duration_minutes: int = 60,
        auditee_ids: Optional[list[str]] = None,
        supplier_id: Optional[str] = None,
        checklist_prompts: Optional[list[tuple[str, str]]] = None,
    ) -> Audit:
        self._require(bool(title.strip()), "title is required")
        self._require(duration_minutes > 0, "duration_minutes must be positive")
        audit = Audit(
            audit_type=audit_type,
            title=title,
            scheduled_for=scheduled_for,
            duration_minutes=duration_minutes,
            scope=scope,
            auditor_ids=list(auditor_ids),
            auditee_ids=list(auditee_ids or []),
            supplier_id=supplier_id,
        )
        if checklist_prompts:
            audit.checklist = [AuditChecklistItem(prompt=p, requirement_ref=r) for (p, r) in checklist_prompts]
        self.audits[audit.id] = audit
        return audit

    def start_audit(self, audit_id: UUID) -> Audit:
        self._require(audit_id in self.audits, "audit not found")
        audit = self.audits[audit_id]
        self._require(audit.status == AuditStatus.PLANNED, "audit must be planned")
        audit.status = AuditStatus.IN_PROGRESS
        return audit

    def complete_audit(self, audit_id: UUID) -> Audit:
        self._require(audit_id in self.audits, "audit not found")
        audit = self.audits[audit_id]
        self._require(audit.status in {AuditStatus.IN_PROGRESS, AuditStatus.PLANNED}, "audit not in progress")
        audit.status = AuditStatus.COMPLETED
        audit.completed_at = self._now()
        return audit

    def answer_checklist_item(
        self,
        audit_id: UUID,
        item_id: UUID,
        is_conformant: bool,
        notes: str = "",
        evidence_links: Optional[list[str]] = None,
    ) -> AuditChecklistItem:
        self._require(audit_id in self.audits, "audit not found")
        audit = self.audits[audit_id]
        for item in audit.checklist:
            if item.id == item_id:
                item.is_conformant = bool(is_conformant)
                item.notes = notes
                if evidence_links:
                    item.evidence_links.extend(list(evidence_links))
                return item
        raise ValueError("checklist item not found")

    def add_finding(
        self,
        audit_id: UUID,
        severity: FindingSeverity,
        title: str,
        description: str,
        requirement_ref: str,
        due_by: Optional[date] = None,
        assigned_to: Optional[str] = None,
        linked_nc_id: Optional[UUID] = None,
        linked_capa_id: Optional[UUID] = None,
    ) -> AuditFinding:
        self._require(audit_id in self.audits, "audit not found")
        self._require(bool(title.strip()), "title is required")
        finding = AuditFinding(
            audit_id=audit_id,
            severity=severity,
            title=title,
            description=description,
            requirement_ref=requirement_ref,
            due_by=due_by,
            assigned_to=assigned_to,
            linked_nc_id=linked_nc_id,
            linked_capa_id=linked_capa_id,
        )
        self.findings[finding.id] = finding
        self.audits[audit_id].finding_ids.append(finding.id)
        return finding

    def plan_finding_action(self, finding_id: UUID, corrective_action_plan: str) -> AuditFinding:
        self._require(finding_id in self.findings, "finding not found")
        f = self.findings[finding_id]
        self._require(f.status == FindingStatus.OPEN, "finding must be open")
        self._require(bool(corrective_action_plan.strip()), "corrective_action_plan is required")
        f.status = FindingStatus.ACTION_PLANNED
        f.corrective_action_plan = corrective_action_plan
        return f

    def implement_finding_action(self, finding_id: UUID, implementation_notes: str) -> AuditFinding:
        self._require(finding_id in self.findings, "finding not found")
        f = self.findings[finding_id]
        self._require(f.status in {FindingStatus.ACTION_PLANNED, FindingStatus.ACTION_IMPLEMENTED}, "finding action not planned")
        self._require(bool(implementation_notes.strip()), "implementation_notes is required")
        f.status = FindingStatus.ACTION_IMPLEMENTED
        f.implementation_notes = implementation_notes
        return f

    def verify_close_finding(self, finding_id: UUID, verified_by: str, verification_notes: str) -> AuditFinding:
        self._require(finding_id in self.findings, "finding not found")
        f = self.findings[finding_id]
        self._require(f.status == FindingStatus.ACTION_IMPLEMENTED, "finding not ready for verification")
        self._require(bool(verified_by.strip()), "verified_by is required")
        f.status = FindingStatus.VERIFIED_CLOSED
        f.verified_by = verified_by
        f.verification_notes = verification_notes
        f.verified_at = self._now()
        return f

    def list_audits_due(self, as_of: Optional[datetime] = None) -> list[Audit]:
        now = as_of or self._now()
        # Due if planned and scheduled_for <= now.
        due = [a for a in self.audits.values() if a.status == AuditStatus.PLANNED and a.scheduled_for <= now]
        return sorted(due, key=lambda a: a.scheduled_for)

    # -----------------------------
    # Risk-based thinking
    # -----------------------------

    def create_risk(
        self,
        risk_type: RiskType,
        title: str,
        description: str,
        owner: str,
        likelihood: int,
        impact: int,
        objective_id: Optional[UUID] = None,
        linked_a3_id: Optional[UUID] = None,
        linked_capa_id: Optional[UUID] = None,
    ) -> RiskOpportunity:
        self._require(bool(title.strip()), "title is required")
        self._require(1 <= likelihood <= 5, "likelihood must be 1-5")
        self._require(1 <= impact <= 5, "impact must be 1-5")
        r = RiskOpportunity(
            risk_type=risk_type,
            title=title,
            description=description,
            owner=owner,
            likelihood=likelihood,
            impact=impact,
            objective_id=objective_id,
            linked_a3_id=linked_a3_id,
            linked_capa_id=linked_capa_id,
        )
        self.risks[r.id] = r
        return r

    def add_mitigation(self, risk_id: UUID, description: str, owner: str, due_by: Optional[date] = None) -> MitigationAction:
        self._require(risk_id in self.risks, "risk not found")
        self._require(bool(description.strip()), "description is required")
        m = MitigationAction(risk_id=risk_id, description=description, owner=owner, due_by=due_by)
        self.mitigations[m.id] = m
        self.risks[risk_id].mitigation_ids.append(m.id)
        self.risks[risk_id].status = RiskStatus.MITIGATING
        return m

    def complete_mitigation(self, mitigation_id: UUID) -> MitigationAction:
        self._require(mitigation_id in self.mitigations, "mitigation not found")
        m = self.mitigations[mitigation_id]
        self._require(m.status in {MitigationStatus.PLANNED, MitigationStatus.IN_PROGRESS}, "mitigation not active")
        m.status = MitigationStatus.COMPLETE
        m.completed_at = self._now()

        # close risk if all mitigations complete
        risk = self.risks[m.risk_id]
        all_complete = all(self.mitigations[mid].status == MitigationStatus.COMPLETE for mid in risk.mitigation_ids)
        if all_complete and risk.status in {RiskStatus.OPEN, RiskStatus.MITIGATING}:
            risk.status = RiskStatus.CLOSED
        return m

    # -----------------------------
    # Gauge & calibration management
    # -----------------------------

    def register_gauge(
        self,
        gauge_number: str,
        description: str,
        location: str,
        owner: str,
        calibration_interval_days: int = 180,
        last_calibrated_at: Optional[datetime] = None,
    ) -> Gauge:
        self._require(bool(gauge_number.strip()), "gauge_number is required")
        self._require(calibration_interval_days > 0, "calibration_interval_days must be positive")
        g = Gauge(
            gauge_number=gauge_number,
            description=description,
            location=location,
            owner=owner,
            calibration_interval_days=calibration_interval_days,
            last_calibrated_at=last_calibrated_at,
        )
        if last_calibrated_at:
            g.next_due_at = last_calibrated_at + timedelta(days=int(calibration_interval_days))
        else:
            g.next_due_at = self._now() + timedelta(days=int(calibration_interval_days))
        self.gauges[g.id] = g
        return g

    def schedule_calibration(self, gauge_id: UUID, scheduled_for: datetime) -> CalibrationEvent:
        self._require(gauge_id in self.gauges, "gauge not found")
        ev = CalibrationEvent(gauge_id=gauge_id, scheduled_for=scheduled_for)
        self.calibrations[ev.id] = ev
        return ev

    def complete_calibration(
        self,
        calibration_id: UUID,
        performed_by: str,
        passed: bool,
        result_notes: str = "",
        out_of_cal_since: Optional[datetime] = None,
        out_of_cal_until: Optional[datetime] = None,
    ) -> CalibrationEvent:
        self._require(calibration_id in self.calibrations, "calibration not found")
        ev = self.calibrations[calibration_id]
        self._require(ev.status == CalibrationStatus.SCHEDULED, "calibration not scheduled")

        ev.performed_at = self._now()
        ev.performed_by = performed_by
        ev.result_notes = result_notes

        if passed:
            ev.status = CalibrationStatus.COMPLETED
            ev.out_of_cal = False
        else:
            ev.status = CalibrationStatus.FAILED
            ev.out_of_cal = True
            ev.out_of_cal_since = out_of_cal_since
            ev.out_of_cal_until = out_of_cal_until

        gauge = self.gauges[ev.gauge_id]
        gauge.last_calibrated_at = ev.performed_at
        gauge.next_due_at = ev.performed_at + timedelta(days=int(gauge.calibration_interval_days))
        return ev

    def list_overdue_calibrations(self, as_of: Optional[datetime] = None) -> list[Gauge]:
        now = as_of or self._now()
        overdue = [g for g in self.gauges.values() if g.status == GaugeStatus.ACTIVE and g.next_due_at and g.next_due_at <= now]
        return sorted(overdue, key=lambda g: g.next_due_at or self._now())

    def record_measurement(self, gauge_id: UUID, lot_id: str, characteristic: str, value: Decimal, measured_at: Optional[datetime] = None) -> MeasurementRecord:
        self._require(gauge_id in self.gauges, "gauge not found")
        self._require(bool(lot_id.strip()), "lot_id is required")
        mr = MeasurementRecord(
            gauge_id=gauge_id,
            lot_id=lot_id,
            measured_at=measured_at or self._now(),
            characteristic=characteristic,
            value=value,
        )
        self.measurements.append(mr)
        return mr

    def out_of_cal_impact_assessment(self, gauge_id: UUID, start: datetime, end: datetime) -> set[str]:
        self._require(gauge_id in self.gauges, "gauge not found")
        self._require(end >= start, "end must be >= start")
        impacted: set[str] = set()
        for mr in self.measurements:
            if mr.gauge_id != gauge_id:
                continue
            if start <= mr.measured_at <= end:
                impacted.add(mr.lot_id)
        return impacted

    # -----------------------------
    # Control plans & PFMEA-lite
    # -----------------------------

    def create_control_plan(
        self,
        name: str,
        product_id: Optional[UUID] = None,
        process_id: Optional[UUID] = None,
        revision: str = "A",
    ) -> ControlPlan:
        self._require(bool(name.strip()), "name is required")
        cp = ControlPlan(name=name, product_id=product_id, process_id=process_id, revision=revision)
        self.control_plans[cp.id] = cp
        return cp

    def add_control_plan_checkpoint(
        self,
        control_plan_id: UUID,
        characteristic: str,
        method: str,
        frequency: str,
        sample_size: int = 1,
        reaction_plan: str = "",
        pfmea_rpn: Optional[int] = None,
    ) -> ControlPlanCheckpoint:
        self._require(control_plan_id in self.control_plans, "control plan not found")
        self._require(sample_size > 0, "sample_size must be positive")
        cp = self.control_plans[control_plan_id]
        c = ControlPlanCheckpoint(
            characteristic=characteristic,
            method=method,
            frequency=frequency,
            sample_size=sample_size,
            reaction_plan=reaction_plan,
            pfmea_rpn=pfmea_rpn,
        )
        cp.checkpoints.append(c)
        return c

    def create_pfmea_lite(self, name: str, process_id: Optional[UUID] = None, product_id: Optional[UUID] = None) -> PFMEALite:
        self._require(bool(name.strip()), "name is required")
        f = PFMEALite(name=name, process_id=process_id, product_id=product_id)
        self.pfmeas[f.id] = f
        return f

    def add_pfmea_step(
        self,
        pfmea_id: UUID,
        process_step: str,
        failure_mode: str,
        effects: str,
        causes: str,
        current_controls: str,
        severity: int,
        occurrence: int,
        detection: int,
    ) -> PFMEAStep:
        self._require(pfmea_id in self.pfmeas, "pfmea not found")
        for v, name in ((severity, "severity"), (occurrence, "occurrence"), (detection, "detection")):
            self._require(1 <= int(v) <= 10, f"{name} must be 1-10")
        s = PFMEAStep(
            process_step=process_step,
            failure_mode=failure_mode,
            effects=effects,
            causes=causes,
            current_controls=current_controls,
            severity=severity,
            occurrence=occurrence,
            detection=detection,
        )
        self.pfmeas[pfmea_id].steps.append(s)
        return s

    def link_pfmea_rpn_to_checkpoint(self, control_plan_id: UUID, checkpoint_id: UUID, pfmea_step_id: UUID, pfmea_id: UUID) -> ControlPlanCheckpoint:
        self._require(control_plan_id in self.control_plans, "control plan not found")
        self._require(pfmea_id in self.pfmeas, "pfmea not found")
        steps = {s.id: s for s in self.pfmeas[pfmea_id].steps}
        self._require(pfmea_step_id in steps, "pfmea step not found")
        rpn = steps[pfmea_step_id].rpn()
        cp = self.control_plans[control_plan_id]
        for chk in cp.checkpoints:
            if chk.id == checkpoint_id:
                chk.pfmea_rpn = rpn
                return chk
        raise ValueError("checkpoint not found")

    # -----------------------------
    # Customer feedback & review
    # -----------------------------

    def create_complaint(
        self,
        customer_id: Optional[str],
        title: str,
        description: str,
        lot_id: Optional[str] = None,
        related_nc_id: Optional[UUID] = None,
        related_capa_id: Optional[UUID] = None,
        rma_number: Optional[str] = None,
        attachments: Optional[list[str]] = None,
    ) -> CustomerComplaint:
        self._require(bool(title.strip()), "title is required")
        c = CustomerComplaint(
            customer_id=customer_id,
            title=title,
            description=description,
            lot_id=lot_id,
            related_nc_id=related_nc_id,
            related_capa_id=related_capa_id,
            rma_number=rma_number,
            attachments=list(attachments or []),
        )
        self.complaints[c.id] = c
        return c

    def add_complaint_containment(self, complaint_id: UUID, action: str) -> CustomerComplaint:
        self._require(complaint_id in self.complaints, "complaint not found")
        c = self.complaints[complaint_id]
        self._require(c.status in {ComplaintStatus.RECEIVED, ComplaintStatus.UNDER_REVIEW, ComplaintStatus.CONTAINMENT}, "complaint not in containment")
        c.status = ComplaintStatus.CONTAINMENT
        c.containment_actions.append(action)
        return c

    def set_complaint_root_cause(self, complaint_id: UUID, root_cause: str) -> CustomerComplaint:
        self._require(complaint_id in self.complaints, "complaint not found")
        c = self.complaints[complaint_id]
        self._require(bool(root_cause.strip()), "root_cause is required")
        c.status = ComplaintStatus.INVESTIGATION
        c.root_cause = root_cause
        return c

    def add_complaint_corrective_action(self, complaint_id: UUID, action: str) -> CustomerComplaint:
        self._require(complaint_id in self.complaints, "complaint not found")
        c = self.complaints[complaint_id]
        self._require(c.status in {ComplaintStatus.INVESTIGATION, ComplaintStatus.CAPA}, "complaint not in corrective actions")
        c.status = ComplaintStatus.CAPA
        c.corrective_actions.append(action)
        return c

    def close_complaint(self, complaint_id: UUID) -> CustomerComplaint:
        self._require(complaint_id in self.complaints, "complaint not found")
        c = self.complaints[complaint_id]
        self._require(bool(c.root_cause), "root cause not set")
        self._require(bool(c.corrective_actions), "no corrective actions")
        c.status = ComplaintStatus.CLOSED
        c.closed_at = self._now()
        return c

    def generate_8d_report(self, complaint_id: UUID, team: Optional[list[str]] = None) -> EightDReport:
        self._require(complaint_id in self.complaints, "complaint not found")
        c = self.complaints[complaint_id]
        report = EightDReport(
            complaint_id=complaint_id,
            d1_team=list(team or []),
            d2_problem=f"{c.title}: {c.description}",
            d3_containment=list(c.containment_actions),
            d4_root_cause=c.root_cause or "",
            d5_corrective_actions=list(c.corrective_actions),
            d6_validate="Verification pending" if c.status != ComplaintStatus.CLOSED else "Verified during closure",
            d7_prevent_recurrence=["Update control plan" if c.related_capa_id else "Update procedure"],
            d8_congratulate="Team recognized in management review",
        )
        self.eightd_reports[report.id] = report
        return report

    async def suggest_8d_insights(self, complaint_id: UUID) -> dict[str, Any]:
        """
        Use Seeded Reasoning Engine to suggest root causes and corrective actions.
        """
        self._require(complaint_id in self.complaints, "complaint not found")
        c = self.complaints[complaint_id]

        if not self.reasoning_engine:
            return {"suggestions": [], "message": "Reasoning engine not available"}

        # Use reasoning engine for analysis
        problem_statement = f"{c.title}: {c.description}"
        suggestions = self.reasoning_engine.analyze_root_cause(problem_statement)

        return {
            "complaint_id": complaint_id,
            "suggestions": [
                {
                    "content": s.suggested_cause,
                    "confidence": s.confidence,
                    "waste_category": s.waste_category.value,
                    "evidence_needed": s.evidence_needed
                } for s in suggestions
            ],
            "suggested_root_cause": suggestions[0].suggested_cause if suggestions else "No expert patterns matched",
            "suggested_actions": [s.suggested_cause for s in suggestions[:3]],
        }

    def generate_management_review_pack(self, period_start: date, period_end: date, prepared_by: str, notes: str = "") -> ManagementReviewPack:
        self._require(period_end >= period_start, "period_end must be >= period_start")

        # KPI summary: take latest KPI in window per key.
        kpis_in_window = [k for k in self.kpi_values if not (k.period_end < period_start or k.period_start > period_end)]
        latest_by_key: dict[str, KPIValue] = {}
        for kv in sorted(kpis_in_window, key=lambda x: (x.period_end, x.recorded_at)):
            latest_by_key[kv.kpi_key] = kv

        open_findings = sum(1 for f in self.findings.values() if f.status not in {FindingStatus.VERIFIED_CLOSED, FindingStatus.CANCELLED})
        open_scars = sum(1 for s in self.scars.values() if s.status not in {SCARStatus.CLOSED, SCARStatus.CANCELLED})
        open_risks = sum(1 for r in self.risks.values() if r.status not in {RiskStatus.CLOSED})
        overdue_calibrations = len(self.list_overdue_calibrations(as_of=self._now()))

        # Document changes = revisions created in window
        changes = 0
        start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, datetime.max.time(), tzinfo=timezone.utc)
        for rev in self.revisions.values():
            if start_dt <= rev.created_at <= end_dt:
                changes += 1

        pack = ManagementReviewPack(
            period_start=period_start,
            period_end=period_end,
            prepared_by=prepared_by,
            kpi_summary={k: v.value for k, v in latest_by_key.items()},
            open_findings=open_findings,
            open_scars=open_scars,
            open_risks=open_risks,
            overdue_calibrations=overdue_calibrations,
            document_changes=changes,
            notes=notes,
        )
        self.management_reviews[pack.id] = pack
        return pack


def create_qms_quality_service() -> QMSQualityService:
    return QMSQualityService()

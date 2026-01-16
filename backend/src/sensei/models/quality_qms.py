from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
    UniqueConstraint,
    Integer,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.user import User
    from sensei.models.account import Account
    from sensei.models.product import Product
    from sensei.models.work_order import WorkOrder
    from sensei.models.quality import NonConformance, CAPA


class QMSDocument(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Quality Management System document.
    """
    __tablename__ = "qms_documents"

    doc_type: Mapped[str] = mapped_column(String(50), nullable=False) # manual, procedure, work_instruction, etc.
    doc_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    current_revision_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("qms_document_revisions.id", use_alter=True, name="fk_qms_documents_current_rev"), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    revisions: Mapped[list["QMSDocumentRevision"]] = relationship("QMSDocumentRevision", back_populates="document", foreign_keys="QMSDocumentRevision.document_id", cascade="all, delete-orphan")
    current_revision: Mapped[Optional["QMSDocumentRevision"]] = relationship("QMSDocumentRevision", foreign_keys=[current_revision_id], post_update=True)


class QMSDocumentRevision(Base, TimestampMixin):
    """
    Revision of a QMS document.
    """
    __tablename__ = "qms_document_revisions"

    document_id: Mapped[UUID] = mapped_column(ForeignKey("qms_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_code: Mapped[str] = mapped_column(String(10), default="A", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, in_review, approved, published, obsolete
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    obsolete_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    signatures: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    document: Mapped["QMSDocument"] = relationship("QMSDocument", back_populates="revisions", foreign_keys=[document_id])
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])


class ExternalDocument(Base, TimestampMixin, AuditMixin):
    """
    External reference document (standards, customer specs).
    """
    __tablename__ = "qms_external_documents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False) # customer, standard body
    identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, obsolete
    
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_interval_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    
    superseded_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("qms_external_documents.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])


class SupplierScorecard(Base, TimestampMixin, AuditMixin):
    """
    Supplier performance metrics.
    """
    __tablename__ = "qms_supplier_scorecards"

    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    ppm: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False) # parts per million defects
    otd: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False) # on-time delivery %
    copq: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False) # cost of poor quality
    
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    supplier: Mapped["Account"] = relationship("Account")
    __table_args__ = (UniqueConstraint("supplier_id", "period_key", name="uq_supplier_period"),)


class SCAR(Base, TimestampMixin, AuditMixin):
    """
    Supplier Corrective Action Request.
    """
    __tablename__ = "qms_scars"

    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, sent, containment, root_cause, corrective_action, verification, closed, cancelled
    
    related_nc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("non_conformances.id"), nullable=True)
    related_capa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("capas.id"), nullable=True)
    
    containment_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrective_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    portal_access_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    supplier: Mapped["Account"] = relationship("Account")
    nc: Mapped["NonConformance"] = relationship("NonConformance")
    capa: Mapped["CAPA"] = relationship("CAPA")


class QualityAudit(Base, TimestampMixin, AuditMixin):
    """
    Quality audit record.
    """
    __tablename__ = "qms_audits"

    audit_type: Mapped[str] = mapped_column(String(50), nullable=False) # internal_process, internal_product, internal_system, supplier, third_party, customer
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="planned", nullable=False) # planned, in_progress, completed, cancelled
    supplier_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    checklist_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    supplier: Mapped[Optional["Account"]] = relationship("Account")
    findings: Mapped[list["AuditFinding"]] = relationship("AuditFinding", back_populates="audit", cascade="all, delete-orphan")


class AuditFinding(Base, TimestampMixin, AuditMixin):
    """
    Finding from a quality audit.
    """
    __tablename__ = "qms_audit_findings"

    audit_id: Mapped[UUID] = mapped_column(ForeignKey("qms_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False) # observation, minor_nc, major_nc, critical_nc
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False) # open, action_planned, action_implemented, verified_closed, cancelled
    
    due_by: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    corrective_action_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    linked_nc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("non_conformances.id"), nullable=True)
    linked_capa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("capas.id"), nullable=True)

    audit: Mapped["QualityAudit"] = relationship("QualityAudit", back_populates="findings")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])


class Gauge(Base, TimestampMixin, AuditMixin):
    """
    Measurement equipment (gauge) registry.
    """
    __tablename__ = "qms_gauges"

    gauge_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, out_of_service, scrapped
    
    calibration_interval_days: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    last_calibrated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    calibration_events: Mapped[list["CalibrationEvent"]] = relationship("CalibrationEvent", back_populates="gauge", cascade="all, delete-orphan")


class CalibrationEvent(Base, TimestampMixin, AuditMixin):
    """
    Record of a calibration event for a gauge.
    """
    __tablename__ = "qms_calibration_events"

    gauge_id: Mapped[UUID] = mapped_column(ForeignKey("qms_gauges.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    performed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    performed_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False) # scheduled, completed, failed, cancelled
    
    result_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    out_of_cal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    gauge: Mapped["Gauge"] = relationship("Gauge", back_populates="calibration_events")
    performed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[performed_by_id])


class MSAStudy(Base, TimestampMixin, AuditMixin):
    """
    Measurement System Analysis (MSA) study for a gauge.
    """
    __tablename__ = "qms_msa_studies"

    gauge_id: Mapped[UUID] = mapped_column(ForeignKey("qms_gauges.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    study_type: Mapped[str] = mapped_column(String(50), default="grr", nullable=False) # grr, bias, linearity, stability
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False) # in_progress, completed, cancelled
    parts_count: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    operators_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    trials_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    gauge: Mapped["Gauge"] = relationship("Gauge")
    measurements: Mapped[list["MSAMeasurement"]] = relationship(
        "MSAMeasurement", back_populates="study", cascade="all, delete-orphan"
    )
    result: Mapped[Optional["MSAResult"]] = relationship(
        "MSAResult", back_populates="study", uselist=False, cascade="all, delete-orphan"
    )


class MSAMeasurement(Base, TimestampMixin, AuditMixin):
    """
    Individual measurement for an MSA study.
    """
    __tablename__ = "qms_msa_measurements"

    study_id: Mapped[UUID] = mapped_column(ForeignKey("qms_msa_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    operator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    part_id: Mapped[str] = mapped_column(String(100), nullable=False)
    trial_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    measured_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    study: Mapped["MSAStudy"] = relationship("MSAStudy", back_populates="measurements")
    operator: Mapped["User"] = relationship("User")


class MSAResult(Base, TimestampMixin, AuditMixin):
    """
    Calculated MSA results (GRR metrics).
    """
    __tablename__ = "qms_msa_results"

    study_id: Mapped[UUID] = mapped_column(ForeignKey("qms_msa_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    repeatability_ev: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reproducibility_av: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    grr: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    part_variation_pv: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_variation_tv: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    grr_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    ndc: Mapped[int] = mapped_column(Integer, nullable=False)

    study: Mapped["MSAStudy"] = relationship("MSAStudy", back_populates="result")


class ProcessCapabilityStudy(Base, TimestampMixin, AuditMixin):
    """
    Process capability study for Cp/Cpk analysis.
    """
    __tablename__ = "qms_process_capability_studies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    characteristic: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    lsl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    usl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    target: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    measurements: Mapped[list["ProcessCapabilityMeasurement"]] = relationship(
        "ProcessCapabilityMeasurement", back_populates="study", cascade="all, delete-orphan"
    )
    result: Mapped[Optional["ProcessCapabilityResult"]] = relationship(
        "ProcessCapabilityResult", back_populates="study", uselist=False, cascade="all, delete-orphan"
    )


class ProcessCapabilityMeasurement(Base, TimestampMixin, AuditMixin):
    """
    Measurement data point for process capability study.
    """
    __tablename__ = "qms_process_capability_measurements"

    study_id: Mapped[UUID] = mapped_column(ForeignKey("qms_process_capability_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    measured_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    study: Mapped["ProcessCapabilityStudy"] = relationship("ProcessCapabilityStudy", back_populates="measurements")


class ProcessCapabilityResult(Base, TimestampMixin, AuditMixin):
    """
    Calculated Cp/Cpk results.
    """
    __tablename__ = "qms_process_capability_results"

    study_id: Mapped[UUID] = mapped_column(ForeignKey("qms_process_capability_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    mean: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    std_dev: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cp: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cpk: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cpu: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cpl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)

    study: Mapped["ProcessCapabilityStudy"] = relationship("ProcessCapabilityStudy", back_populates="result")


class FirstArticleInspection(Base, TimestampMixin, AuditMixin):
    """
    First Article Inspection (FAI) / AS9102 report header.
    """
    __tablename__ = "qms_first_article_inspections"

    inspection_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    product_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("work_orders.id"), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    revision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    drawing_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    inspector_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    product: Mapped[Optional["Product"]] = relationship("Product")
    work_order: Mapped[Optional["WorkOrder"]] = relationship("WorkOrder")
    inspector: Mapped[Optional["User"]] = relationship("User", foreign_keys=[inspector_id])
    characteristics: Mapped[list["FAICharacteristic"]] = relationship(
        "FAICharacteristic", back_populates="inspection", cascade="all, delete-orphan"
    )


class FAICharacteristic(Base, TimestampMixin, AuditMixin):
    """
    FAI characteristic line item (AS9102 form 3 style).
    """
    __tablename__ = "qms_fai_characteristics"

    inspection_id: Mapped[UUID] = mapped_column(ForeignKey("qms_first_article_inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    characteristic_number: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement: Mapped[str] = mapped_column(String(255), nullable=False)
    nominal: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    tolerance: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pass/fail/pending
    method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("qms_gauges.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    inspection: Mapped["FirstArticleInspection"] = relationship("FirstArticleInspection", back_populates="characteristics")
    tool: Mapped[Optional["Gauge"]] = relationship("Gauge")


class SelfInspection(Base, TimestampMixin, AuditMixin):
    """
    Operator self-inspection record.
    """
    __tablename__ = "qms_self_inspections"

    inspection_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("work_orders.id"), nullable=True, index=True)
    product_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    operator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    work_order: Mapped[Optional["WorkOrder"]] = relationship("WorkOrder")
    product: Mapped[Optional["Product"]] = relationship("Product")
    operator: Mapped["User"] = relationship("User", foreign_keys=[operator_id])
    checks: Mapped[list["SelfInspectionCheck"]] = relationship(
        "SelfInspectionCheck", back_populates="inspection", cascade="all, delete-orphan"
    )


class SelfInspectionCheck(Base, TimestampMixin, AuditMixin):
    """
    Self-inspection check item.
    """
    __tablename__ = "qms_self_inspection_checks"

    inspection_id: Mapped[UUID] = mapped_column(ForeignKey("qms_self_inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    characteristic: Mapped[str] = mapped_column(String(255), nullable=False)
    specification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actual_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    inspection: Mapped["SelfInspection"] = relationship("SelfInspection", back_populates="checks")


class LabTestMethod(Base, TimestampMixin, AuditMixin):
    """
    Laboratory test method (ASTM/ISO).
    """
    __tablename__ = "qms_lab_test_methods"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    standard: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    lower_spec: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    upper_spec: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    tests: Mapped[list["LabTestRun"]] = relationship("LabTestRun", back_populates="method")


class LabSample(Base, TimestampMixin, AuditMixin):
    """
    Laboratory sample record.
    """
    __tablename__ = "qms_lab_samples"

    sample_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    product_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("work_orders.id"), nullable=True, index=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    product: Mapped[Optional["Product"]] = relationship("Product")
    work_order: Mapped[Optional["WorkOrder"]] = relationship("WorkOrder")
    collected_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[collected_by_id])
    tests: Mapped[list["LabTestRun"]] = relationship("LabTestRun", back_populates="sample", cascade="all, delete-orphan")


class LabTestRun(Base, TimestampMixin, AuditMixin):
    """
    Laboratory test execution/result.
    """
    __tablename__ = "qms_lab_test_runs"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("qms_lab_samples.id", ondelete="CASCADE"), nullable=False, index=True)
    method_id: Mapped[UUID] = mapped_column(ForeignKey("qms_lab_test_methods.id"), nullable=False, index=True)
    result_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    result_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tester_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sample: Mapped["LabSample"] = relationship("LabSample", back_populates="tests")
    method: Mapped["LabTestMethod"] = relationship("LabTestMethod", back_populates="tests")
    tester: Mapped[Optional["User"]] = relationship("User", foreign_keys=[tester_id])


class AQLSamplingPlan(Base, TimestampMixin, AuditMixin):
    """
    AQL sampling plan (e.g., ANSI/ASQ Z1.4).
    """
    __tablename__ = "qms_aql_sampling_plans"

    plan_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    standard: Mapped[str] = mapped_column(String(50), default="ANSI/ASQ Z1.4", nullable=False)
    inspection_level: Mapped[str] = mapped_column(String(10), default="II", nullable=False)
    aql_level: Mapped[str] = mapped_column(String(10), default="1.0", nullable=False)
    lot_size_min: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_size_max: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    accept_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    reject_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    inspections: Mapped[list["AQLLotInspection"]] = relationship(
        "AQLLotInspection", back_populates="plan", cascade="all, delete-orphan"
    )


class AQLLotInspection(Base, TimestampMixin, AuditMixin):
    """
    AQL lot inspection record.
    """
    __tablename__ = "qms_aql_lot_inspections"

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("qms_aql_sampling_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    defect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accept_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    reject_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(20), default="pending", nullable=False) # accept, reject, pending
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inspector_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    inspection_level: Mapped[str] = mapped_column(String(10), nullable=False)
    aql_level: Mapped[str] = mapped_column(String(10), nullable=False)
    defects_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["AQLSamplingPlan"] = relationship("AQLSamplingPlan", back_populates="inspections")
    inspector: Mapped[Optional["User"]] = relationship("User", foreign_keys=[inspector_id])


class TraceabilityMatrix(Base, TimestampMixin, AuditMixin):
    """
    Traceability matrix for product/work order/lot.
    """
    __tablename__ = "qms_traceability_matrices"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    product_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    work_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("work_orders.id"), nullable=True, index=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    external_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    product: Mapped[Optional["Product"]] = relationship("Product")
    work_order: Mapped[Optional["WorkOrder"]] = relationship("WorkOrder")
    links: Mapped[list["TraceabilityLink"]] = relationship(
        "TraceabilityLink", back_populates="matrix", cascade="all, delete-orphan"
    )


class TraceabilityLink(Base, TimestampMixin, AuditMixin):
    """
    Link to related record for traceability.
    """
    __tablename__ = "qms_traceability_links"

    matrix_id: Mapped[UUID] = mapped_column(ForeignKey("qms_traceability_matrices.id", ondelete="CASCADE"), nullable=False, index=True)
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reference_table: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    matrix: Mapped["TraceabilityMatrix"] = relationship("TraceabilityMatrix", back_populates="links")


class ChangePointStudy(Base, TimestampMixin, AuditMixin):
    """
    Change point control study for a process characteristic.
    """
    __tablename__ = "qms_change_point_studies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    characteristic: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(50), default="mean_shift", nullable=False)
    sensitivity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    observations: Mapped[list["ChangePointObservation"]] = relationship(
        "ChangePointObservation", back_populates="study", cascade="all, delete-orphan"
    )
    events: Mapped[list["ChangePointEvent"]] = relationship(
        "ChangePointEvent", back_populates="study", cascade="all, delete-orphan"
    )


class ChangePointObservation(Base, TimestampMixin, AuditMixin):
    """
    Observation for change point study.
    """
    __tablename__ = "qms_change_point_observations"

    study_id: Mapped[UUID] = mapped_column(ForeignKey("qms_change_point_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sample_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    study: Mapped["ChangePointStudy"] = relationship("ChangePointStudy", back_populates="observations")


class ChangePointEvent(Base, TimestampMixin, AuditMixin):
    """
    Detected change point event.
    """
    __tablename__ = "qms_change_point_events"

    study_id: Mapped[UUID] = mapped_column(ForeignKey("qms_change_point_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    index_position: Mapped[int] = mapped_column(Integer, nullable=False)
    change_magnitude: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    study: Mapped["ChangePointStudy"] = relationship("ChangePointStudy", back_populates="events")


class ManagementReview(Base, TimestampMixin, AuditMixin):
    """
    Management review record for QMS.
    """
    __tablename__ = "qms_management_reviews"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    held_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attendees: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    metrics_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    actions: Mapped[list["ManagementReviewAction"]] = relationship(
        "ManagementReviewAction", back_populates="review", cascade="all, delete-orphan"
    )


class ManagementReviewAction(Base, TimestampMixin, AuditMixin):
    """
    Action item from management review.
    """
    __tablename__ = "qms_management_review_actions"

    review_id: Mapped[UUID] = mapped_column(ForeignKey("qms_management_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assignee_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    review: Mapped["ManagementReview"] = relationship("ManagementReview", back_populates="actions")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])


class CustomerComplaint(Base, TimestampMixin, AuditMixin):
    """
    Customer complaint record.
    """
    __tablename__ = "qms_customer_complaints"

    customer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False) # received, under_review, investigation, containment, capa, closed, cancelled
    
    lot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    related_nc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("non_conformances.id"), nullable=True)
    related_capa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("capas.id"), nullable=True)
    rma_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    containment_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    corrective_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Optional["Account"]] = relationship("Account")
    nc: Mapped[Optional["NonConformance"]] = relationship("NonConformance")
    capa: Mapped[Optional["CAPA"]] = relationship("CAPA")


class CustomerSurvey(Base, TimestampMixin, AuditMixin):
    """
    Customer satisfaction survey (e.g., NPS).
    """
    __tablename__ = "qms_customer_surveys"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_responses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    responses: Mapped[list["CustomerSurveyResponse"]] = relationship(
        "CustomerSurveyResponse", back_populates="survey", cascade="all, delete-orphan"
    )


class CustomerSurveyResponse(Base, TimestampMixin, AuditMixin):
    """
    Individual survey response.
    """
    __tablename__ = "qms_customer_survey_responses"

    survey_id: Mapped[UUID] = mapped_column(ForeignKey("qms_customer_surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    respondent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    respondent_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nps_score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    survey: Mapped["CustomerSurvey"] = relationship("CustomerSurvey", back_populates="responses")
    customer: Mapped[Optional["Account"]] = relationship("Account")

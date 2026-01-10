"""Tests for Advanced Quality System (QMS) Service."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.qms_quality import (
    # Enums
    QMSDocumentType,
    QMSDocumentStatus,
    SignatureRole,
    ExternalDocStatus,
    KPITrend,
    SCARStatus,
    AuditType,
    AuditStatus,
    FindingSeverity,
    FindingStatus,
    RiskType,
    RiskStatus,
    MitigationStatus,
    GaugeStatus,
    CalibrationStatus,
    ComplaintStatus,
    # Models
    QMSDocument,
    QMSDocumentRevision,
    ElectronicSignature,
    ExternalDocument,
    QualityObjective,
    KPIValue,
    SupplierProfile,
    SupplierPeriodStats,
    SupplierScorecard,
    SCAR,
    Audit,
    AuditChecklistItem,
    AuditFinding,
    RiskOpportunity,
    MitigationAction,
    Gauge,
    CalibrationEvent,
    MeasurementRecord,
    ControlPlan,
    ControlPlanCheckpoint,
    PFMEALite,
    PFMEAStep,
    CustomerComplaint,
    EightDReport,
    ManagementReviewPack,
    # Service
    QMSQualityService,
    create_qms_quality_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def service() -> QMSQualityService:
    return QMSQualityService()


@pytest.fixture
def published_document(service: QMSQualityService) -> tuple[QMSDocument, QMSDocumentRevision]:
    doc = service.create_document(
        doc_type=QMSDocumentType.PROCEDURE,
        doc_number="QP-001",
        title="Nonconformance Control",
        owner="quality",
        created_by="u-001",
        content_hash="hash-a",
    )
    rev = service.revisions[doc.current_revision_id]
    service.submit_revision_for_review(rev.id)
    service.sign_revision(rev.id, signer_id="u-001", signer_name="Author", role=SignatureRole.AUTHOR, meaning="I authored this")
    service.sign_revision(rev.id, signer_id="u-002", signer_name="Approver", role=SignatureRole.APPROVER, meaning="I approve")
    service.approve_revision(rev.id)
    service.publish_revision(rev.id, effective_date=date(2026, 1, 1))
    return doc, service.revisions[rev.id]


@pytest.fixture
def supplier_with_stats(service: QMSQualityService) -> tuple[SupplierProfile, SupplierScorecard]:
    service.upsert_supplier("sup-001", "Acme Metals")
    service.record_supplier_receipt("sup-001", date(2026, 1, 4), units_received=10_000)
    service.record_supplier_defects("sup-001", date(2026, 1, 4), defects_found=12)
    service.record_supplier_delivery("sup-001", date(2026, 1, 2), on_time=True)
    service.record_supplier_delivery("sup-001", date(2026, 1, 8), on_time=False)
    service.record_supplier_copq("sup-001", date(2026, 1, 6), scrap_cost=Decimal("120"), rework_cost=Decimal("30"))
    score = service.compute_supplier_scorecard("sup-001", "2026-01")
    return service.suppliers["sup-001"], score


@pytest.fixture
def gauge_with_measurements(service: QMSQualityService) -> Gauge:
    g = service.register_gauge(
        gauge_number="G-001",
        description="Micrometer",
        location="QC",
        owner="metrology",
        calibration_interval_days=30,
        last_calibrated_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
    )
    # measurements around a suspected out-of-cal window
    service.record_measurement(
        g.id,
        lot_id="LOT-001",
        characteristic="diameter",
        value=Decimal("10.01"),
        measured_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
    )
    service.record_measurement(
        g.id,
        lot_id="LOT-002",
        characteristic="diameter",
        value=Decimal("9.98"),
        measured_at=datetime(2025, 12, 20, tzinfo=timezone.utc),
    )
    service.record_measurement(
        g.id,
        lot_id="LOT-003",
        characteristic="diameter",
        value=Decimal("10.00"),
        measured_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
    )
    return g


# =============================================================================
# TESTS: ENUMS
# =============================================================================


class TestEnums:
    def test_document_status_values(self):
        assert QMSDocumentStatus.DRAFT == "draft"
        assert QMSDocumentStatus.PUBLISHED == "published"
        assert QMSDocumentStatus.OBSOLETE == "obsolete"

    def test_scar_status_values(self):
        assert SCARStatus.DRAFT == "draft"
        assert SCARStatus.CLOSED == "closed"

    def test_audit_type_values(self):
        assert AuditType.SUPPLIER == "supplier"
        assert AuditType.THIRD_PARTY == "third_party"

    def test_risk_type_values(self):
        assert RiskType.RISK == "risk"
        assert RiskType.OPPORTUNITY == "opportunity"


# =============================================================================
# TESTS: DOCUMENT CONTROL
# =============================================================================


class TestDocumentControl:
    def test_create_document_creates_initial_revision(self, service: QMSQualityService):
        doc = service.create_document(
            doc_type=QMSDocumentType.QUALITY_MANUAL,
            doc_number="QM-001",
            title="Quality Manual",
            owner="quality",
            created_by="u-001",
            content_hash="h1",
        )
        assert doc.current_revision_id is not None
        rev = service.revisions[doc.current_revision_id]
        assert rev.revision_code == "A"
        assert rev.status == QMSDocumentStatus.DRAFT

    def test_submit_sign_approve_publish_flow(self, service: QMSQualityService):
        doc = service.create_document(
            doc_type=QMSDocumentType.PROCEDURE,
            doc_number="QP-002",
            title="Document Control",
            owner="quality",
            created_by="u-001",
            content_hash="h2",
        )
        rev = service.revisions[doc.current_revision_id]
        service.submit_revision_for_review(rev.id)
        service.sign_revision(rev.id, "u-001", "Author", SignatureRole.AUTHOR, "Authored")
        service.sign_revision(rev.id, "u-010", "Approver", SignatureRole.APPROVER, "Approved")
        service.approve_revision(rev.id)
        service.publish_revision(rev.id)
        assert rev.status == QMSDocumentStatus.PUBLISHED
        assert rev.published_at is not None
        assert rev.effective_date is not None

    def test_approve_requires_signatures(self, service: QMSQualityService):
        doc = service.create_document(
            doc_type=QMSDocumentType.PROCEDURE,
            doc_number="QP-003",
            title="Training",
            owner="quality",
            created_by="u-001",
            content_hash="h3",
        )
        rev = service.revisions[doc.current_revision_id]
        service.submit_revision_for_review(rev.id)
        service.sign_revision(rev.id, "u-001", "Author", SignatureRole.AUTHOR, "Authored")
        with pytest.raises(ValueError, match="missing required signatures"):
            service.approve_revision(rev.id)

    def test_publish_requires_approved(self, service: QMSQualityService):
        doc = service.create_document(
            doc_type=QMSDocumentType.WORK_INSTRUCTION,
            doc_number="WI-001",
            title="Torque Procedure",
            owner="prod",
            created_by="u-002",
            content_hash="h4",
        )
        rev = service.revisions[doc.current_revision_id]
        with pytest.raises(ValueError, match="must be approved"):
            service.publish_revision(rev.id)

    def test_new_published_revision_obsoletes_previous(self, service: QMSQualityService, published_document):
        doc, rev_a = published_document
        rev_b = service.start_revision(doc.id, revision_code="B", created_by="u-001", content_hash="hash-b", change_summary="Update")
        service.submit_revision_for_review(rev_b.id)
        service.sign_revision(rev_b.id, "u-001", "Author", SignatureRole.AUTHOR, "Authored")
        service.sign_revision(rev_b.id, "u-002", "Approver", SignatureRole.APPROVER, "Approved")
        service.approve_revision(rev_b.id)
        service.publish_revision(rev_b.id)
        assert service.revisions[rev_a.id].status == QMSDocumentStatus.OBSOLETE
        assert service.revisions[rev_b.id].status == QMSDocumentStatus.PUBLISHED

    def test_get_document_history_order_and_contents(self, service: QMSQualityService, published_document):
        doc, _ = published_document
        history = service.get_document_history(doc.id)
        assert len(history) == 1
        assert history[0].document_id == doc.id


# =============================================================================
# TESTS: EXTERNAL DOCUMENT LIST
# =============================================================================


class TestExternalDocs:
    def test_add_external_document(self, service: QMSQualityService):
        doc = service.add_external_document(
            name="AS9100",
            publisher="IAQG",
            identifier="AS9100D",
            version="D",
            owner="quality",
            review_interval_days=180,
        )
        assert doc.status == ExternalDocStatus.ACTIVE
        assert doc.review_interval_days == 180

    def test_external_docs_due_for_review(self, service: QMSQualityService):
        doc = service.add_external_document(
            name="Customer Spec",
            publisher="Customer",
            identifier="CUST-123",
            version="1",
            owner="quality",
            review_interval_days=1,
        )
        # force review due
        doc.last_reviewed_at = datetime.now(timezone.utc) - timedelta(days=2)
        due = service.get_external_docs_due_for_review(as_of=datetime.now(timezone.utc))
        assert doc in due

    def test_supersede_external_document_creates_new_active_version(self, service: QMSQualityService):
        old = service.add_external_document(
            name="Customer Spec",
            publisher="Customer",
            identifier="CUST-999",
            version="1",
            owner="quality",
        )
        new = service.supersede_external_document(old.id, new_version="2")
        assert service.external_documents[old.id].status == ExternalDocStatus.OBSOLETE
        assert new.status == ExternalDocStatus.ACTIVE
        assert service.external_documents[old.id].superseded_by_id == new.id


# =============================================================================
# TESTS: KPI OBJECTIVES
# =============================================================================


class TestKPIs:
    def test_create_quality_objective(self, service: QMSQualityService):
        obj = service.create_quality_objective(
            name="Improve FPY",
            description="Reduce rework",
            owner="quality",
            kpi_keys=["fpy", "dppm"],
            targets={"fpy": Decimal("0.95")},
        )
        assert obj.name == "Improve FPY"
        assert obj.targets["fpy"] == Decimal("0.95")

    def test_record_and_get_latest_kpi(self, service: QMSQualityService):
        service.record_kpi_value("fpy", date(2026, 1, 1), date(2026, 1, 7), Decimal("0.92"))
        service.record_kpi_value("fpy", date(2026, 1, 8), date(2026, 1, 14), Decimal("0.93"))
        latest = service.get_latest_kpi("fpy")
        assert latest is not None
        assert latest.value == Decimal("0.93")

    def test_kpi_trend_unknown_with_single_point(self, service: QMSQualityService):
        service.record_kpi_value("fpy", date(2026, 1, 1), date(2026, 1, 7), Decimal("0.92"))
        assert service.compute_kpi_trend("fpy") == KPITrend.UNKNOWN

    def test_kpi_trend_improving(self, service: QMSQualityService):
        service.record_kpi_value("fpy", date(2026, 1, 1), date(2026, 1, 7), Decimal("0.90"))
        service.record_kpi_value("fpy", date(2026, 1, 8), date(2026, 1, 14), Decimal("0.93"))
        assert service.compute_kpi_trend("fpy") == KPITrend.IMPROVING


# =============================================================================
# TESTS: SUPPLIER QUALITY
# =============================================================================


class TestSupplierQuality:
    def test_compute_supplier_scorecard(self, service: QMSQualityService, supplier_with_stats):
        _profile, score = supplier_with_stats
        assert score.supplier_id == "sup-001"
        assert score.period_key == "2026-01"
        assert score.ppm > 0
        assert score.otd == Decimal("0.5")
        assert score.copq == Decimal("150")

    def test_scar_workflow(self, service: QMSQualityService):
        scar = service.create_scar("sup-001", "Bad plating", "Rust observed", created_by="quality")
        assert scar.status == SCARStatus.DRAFT
        service.send_scar(scar.id, portal_access_token="tok-123")
        service.add_scar_containment(scar.id, "Sort stock")
        service.set_scar_root_cause(scar.id, "Improper bath chemistry")
        service.add_scar_corrective_action(scar.id, "Update chemistry control")
        service.verify_and_close_scar(scar.id, "Verified improved")
        assert service.scars[scar.id].status == SCARStatus.CLOSED

    def test_scar_close_requires_root_cause_and_actions(self, service: QMSQualityService):
        scar = service.create_scar("sup-001", "Issue", "Desc", created_by="quality")
        service.send_scar(scar.id, portal_access_token="tok")
        service.add_scar_containment(scar.id, "Contain")
        with pytest.raises(ValueError, match="root cause not set"):
            service.verify_and_close_scar(scar.id, "No root cause")


# =============================================================================
# TESTS: AUDITS & FINDINGS
# =============================================================================


class TestAudits:
    def test_schedule_due_start_complete_audit(self, service: QMSQualityService):
        scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)
        audit = service.schedule_audit(
            audit_type=AuditType.INTERNAL_PROCESS,
            title="Process audit",
            scheduled_for=scheduled_for,
            auditor_ids=["aud-1"],
            scope="Receiving",
            checklist_prompts=[("Are procedures followed?", "ISO9001 8.5")],
        )
        due = service.list_audits_due(as_of=datetime.now(timezone.utc))
        assert audit in due
        service.start_audit(audit.id)
        assert audit.status == AuditStatus.IN_PROGRESS
        item = audit.checklist[0]
        service.answer_checklist_item(audit.id, item.id, is_conformant=False, notes="No evidence", evidence_links=["photo.jpg"])
        assert item.is_conformant is False
        assert "photo.jpg" in item.evidence_links
        service.complete_audit(audit.id)
        assert audit.status == AuditStatus.COMPLETED
        assert audit.completed_at is not None

    def test_finding_lifecycle(self, service: QMSQualityService):
        audit = service.schedule_audit(
            audit_type=AuditType.INTERNAL_SYSTEM,
            title="System audit",
            scheduled_for=datetime.now(timezone.utc),
            auditor_ids=["aud"],
            scope="QMS",
        )
        finding = service.add_finding(
            audit_id=audit.id,
            severity=FindingSeverity.MAJOR_NC,
            title="Missing training records",
            description="No training evidence",
            requirement_ref="AS9100 7.2",
            due_by=date(2026, 1, 31),
            assigned_to="quality",
        )
        assert finding.status == FindingStatus.OPEN
        service.plan_finding_action(finding.id, "Train and record")
        assert finding.status == FindingStatus.ACTION_PLANNED
        service.implement_finding_action(finding.id, "Completed training")
        assert finding.status == FindingStatus.ACTION_IMPLEMENTED
        service.verify_close_finding(finding.id, verified_by="lead", verification_notes="Verified")
        assert finding.status == FindingStatus.VERIFIED_CLOSED
        assert finding.verified_at is not None


# =============================================================================
# TESTS: RISK REGISTRY
# =============================================================================


class TestRiskRegistry:
    def test_create_risk_and_mitigations(self, service: QMSQualityService):
        r = service.create_risk(
            risk_type=RiskType.RISK,
            title="Single source supplier",
            description="No alternate source",
            owner="supply",
            likelihood=4,
            impact=5,
        )
        assert r.status == RiskStatus.OPEN
        m1 = service.add_mitigation(r.id, "Qualify backup", owner="supply")
        m2 = service.add_mitigation(r.id, "Hold safety stock", owner="supply")
        assert service.risks[r.id].status == RiskStatus.MITIGATING
        service.complete_mitigation(m1.id)
        assert service.risks[r.id].status == RiskStatus.MITIGATING
        service.complete_mitigation(m2.id)
        assert service.risks[r.id].status == RiskStatus.CLOSED

    def test_create_risk_validates_ranges(self, service: QMSQualityService):
        with pytest.raises(ValueError, match="likelihood must be 1-5"):
            service.create_risk(RiskType.RISK, "Bad", "", owner="o", likelihood=0, impact=3)


# =============================================================================
# TESTS: GAUGE & CALIBRATION
# =============================================================================


class TestCalibration:
    def test_register_gauge_sets_next_due(self, service: QMSQualityService):
        last = datetime(2025, 12, 1, tzinfo=timezone.utc)
        g = service.register_gauge("G-100", "Caliper", "QC", "metrology", calibration_interval_days=10, last_calibrated_at=last)
        assert g.next_due_at == last + timedelta(days=10)

    def test_overdue_calibrations_list(self, service: QMSQualityService):
        last = datetime.now(timezone.utc) - timedelta(days=40)
        g = service.register_gauge("G-200", "Caliper", "QC", "metrology", calibration_interval_days=30, last_calibrated_at=last)
        overdue = service.list_overdue_calibrations(as_of=datetime.now(timezone.utc))
        assert g in overdue

    def test_out_of_cal_impact_assessment(self, service: QMSQualityService, gauge_with_measurements: Gauge):
        impacted = service.out_of_cal_impact_assessment(
            gauge_with_measurements.id,
            start=datetime(2025, 12, 12, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        assert impacted == {"LOT-002"}

    def test_complete_failed_calibration_sets_out_of_cal(self, service: QMSQualityService):
        g = service.register_gauge("G-300", "CMM", "QC", "metrology", calibration_interval_days=90)
        ev = service.schedule_calibration(g.id, scheduled_for=datetime.now(timezone.utc))
        service.complete_calibration(
            ev.id,
            performed_by="tech",
            passed=False,
            result_notes="Failed",
            out_of_cal_since=datetime(2025, 12, 1, tzinfo=timezone.utc),
            out_of_cal_until=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert service.calibrations[ev.id].status == CalibrationStatus.FAILED
        assert service.calibrations[ev.id].out_of_cal is True


# =============================================================================
# TESTS: CONTROL PLANS & PFMEA
# =============================================================================


class TestControlPlans:
    def test_create_control_plan_and_checkpoint(self, service: QMSQualityService):
        cp = service.create_control_plan("CP-001")
        chk = service.add_control_plan_checkpoint(cp.id, "diameter", "mic", "hourly", sample_size=2, reaction_plan="Stop and sort")
        assert chk.sample_size == 2
        assert chk.reaction_plan == "Stop and sort"

    def test_pfmea_rpn_and_link_to_checkpoint(self, service: QMSQualityService):
        cp = service.create_control_plan("CP-002")
        chk = service.add_control_plan_checkpoint(cp.id, "torque", "wrench", "every_10")
        f = service.create_pfmea_lite("PFMEA-001")
        step = service.add_pfmea_step(
            f.id,
            process_step="Assembly",
            failure_mode="Under-torque",
            effects="Loose joint",
            causes="Tool drift",
            current_controls="Torque check",
            severity=8,
            occurrence=4,
            detection=3,
        )
        assert step.rpn() == 96
        updated = service.link_pfmea_rpn_to_checkpoint(cp.id, chk.id, step.id, pfmea_id=f.id)
        assert updated.pfmea_rpn == 96


# =============================================================================
# TESTS: CUSTOMER COMPLAINTS, 8D, MANAGEMENT REVIEW
# =============================================================================


class TestCustomerFeedback:
    def test_complaint_workflow_and_8d(self, service: QMSQualityService):
        comp = service.create_complaint(
            customer_id="cust-1",
            title="Scratch on part",
            description="Surface scratch found",
            lot_id="LOT-777",
            related_capa_id=uuid4(),
            rma_number="RMA-001",
        )
        service.add_complaint_containment(comp.id, "Quarantine affected lot")
        service.set_complaint_root_cause(comp.id, "Handling damage")
        service.add_complaint_corrective_action(comp.id, "Add protective packaging")
        service.close_complaint(comp.id)
        assert service.complaints[comp.id].status == ComplaintStatus.CLOSED

        report = service.generate_8d_report(comp.id, team=["quality", "ops"])
        assert report.complaint_id == comp.id
        assert "Scratch on part" in report.d2_problem
        assert report.d5_corrective_actions == ["Add protective packaging"]

    def test_close_complaint_requires_root_cause_and_actions(self, service: QMSQualityService):
        comp = service.create_complaint(customer_id="cust", title="Issue", description="Desc")
        service.add_complaint_containment(comp.id, "Contain")
        with pytest.raises(ValueError, match="root cause not set"):
            service.close_complaint(comp.id)

    def test_management_review_pack_aggregates_counts(self, service: QMSQualityService):
        # KPI values
        service.record_kpi_value("fpy", date(2026, 1, 1), date(2026, 1, 31), Decimal("0.94"))

        # Open SCAR
        scar = service.create_scar("sup-9", "Issue", "Desc", created_by="q")
        service.send_scar(scar.id, portal_access_token="tok")

        # Open audit finding
        audit = service.schedule_audit(
            audit_type=AuditType.INTERNAL_SYSTEM,
            title="Audit",
            scheduled_for=datetime.now(timezone.utc),
            auditor_ids=["aud"],
            scope="QMS",
        )
        service.add_finding(audit.id, FindingSeverity.MINOR_NC, "Finding", "Desc", "ISO")

        # Open risk
        service.create_risk(RiskType.RISK, "Risk", "Desc", owner="o", likelihood=3, impact=3)

        # Overdue calibration
        last = datetime.now(timezone.utc) - timedelta(days=40)
        service.register_gauge("G-400", "Gauge", "QC", "met", calibration_interval_days=30, last_calibrated_at=last)

        pack = service.generate_management_review_pack(date(2026, 1, 1), date(2026, 1, 31), prepared_by="gm")
        assert pack.kpi_summary["fpy"] == Decimal("0.94")
        assert pack.open_scars == 1
        assert pack.open_findings == 1
        assert pack.open_risks == 1
        assert pack.overdue_calibrations == 1


# =============================================================================
# TESTS: FACTORY FUNCTION
# =============================================================================


class TestFactory:
    def test_create_service_factory(self):
        svc = create_qms_quality_service()
        assert isinstance(svc, QMSQualityService)

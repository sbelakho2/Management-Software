"""
Tests for Quality Management models (NC/CAPA).
"""

from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from sensei.core.time import utcnow_naive

from sensei.models.quality import (
    NonConformance,
    NCType,
    NCSource,
    NCSeverity,
    NCStatus,
    NCDisposition,
    RootCauseCategory,
    CAPA,
    CAPAType,
    CAPASourceType,
    CAPAStatus,
    CAPAPriority,
    CAPAAction,
    CAPAActionType,
    CAPAActionStatus,
    VerificationStatus,
    EffectivenessStatus,
    InspectionPlan,
    InspectionType,
    InspectionRecord,
    InspectionResult,
)


class TestNonConformanceModel:
    """Test cases for NonConformance model."""

    def test_nc_creation_basic(self):
        """Test basic NC creation."""
        nc = NonConformance(
            nc_number="NC-001",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Dimension out of spec",
            description="Part width is 10.2mm instead of 10.0mm",
            detected_by_id=1,
            severity=NCSeverity.MINOR,
            status=NCStatus.OPEN,
        )

        assert nc.nc_number == "NC-001"
        assert nc.nc_type == NCType.PRODUCT
        assert nc.source == NCSource.IN_PROCESS
        assert nc.severity == NCSeverity.MINOR
        assert nc.status == NCStatus.OPEN

    def test_nc_creation_full(self):
        """Test NC with all fields."""
        nc = NonConformance(
            nc_number="NC-002",
            nc_type=NCType.SUPPLIER,
            source=NCSource.INCOMING_INSPECTION,
            severity=NCSeverity.MAJOR,
            product_id=10,
            work_order_id=100,
            station_id=5,
            lot_number="LOT-2024-001",
            quantity_affected=50,
            quantity_inspected=100,
            title="Supplier material defect",
            description="Surface finish not meeting spec",
            specification_requirement="Ra 0.8 max",
            actual_condition="Ra 1.6 measured",
            root_cause_category=RootCauseCategory.MATERIAL,
            detected_by_id=1,
            cost_impact=Decimal("5000.00"),
            scrap_cost=Decimal("2000.00"),
            rework_cost=Decimal("1000.00"),
            supplier_name="ACME Corp",
            supplier_po_number="PO-2024-1234",
        )

        assert nc.severity == NCSeverity.MAJOR
        assert nc.quantity_affected == 50
        assert nc.lot_number == "LOT-2024-001"
        assert nc.supplier_name == "ACME Corp"

    def test_nc_type_values(self):
        """Test all NC type values."""
        for nc_type in NCType:
            nc = NonConformance(
                nc_number=f"NC-{nc_type.value}",
                nc_type=nc_type,
                source=NCSource.IN_PROCESS,
                title=f"Test {nc_type.value}",
                description="Test",
                detected_by_id=1,
            )
            assert nc.nc_type == nc_type

    def test_nc_source_values(self):
        """Test all NC source values."""
        for source in NCSource:
            nc = NonConformance(
                nc_number=f"NC-{source.value}",
                nc_type=NCType.PRODUCT,
                source=source,
                title=f"Test {source.value}",
                description="Test",
                detected_by_id=1,
            )
            assert nc.source == source

    def test_nc_severity_values(self):
        """Test all severity values."""
        for severity in NCSeverity:
            nc = NonConformance(
                nc_number=f"NC-{severity.value}",
                nc_type=NCType.PRODUCT,
                source=NCSource.IN_PROCESS,
                severity=severity,
                title=f"Test {severity.value}",
                description="Test",
                detected_by_id=1,
            )
            assert nc.severity == severity

    def test_nc_status_values(self):
        """Test all status values."""
        for status in NCStatus:
            nc = NonConformance(
                nc_number=f"NC-{status.value}",
                nc_type=NCType.PRODUCT,
                source=NCSource.IN_PROCESS,
                title=f"Test {status.value}",
                description="Test",
                detected_by_id=1,
                status=status,
            )
            assert nc.status == status

    def test_nc_disposition_values(self):
        """Test all disposition values."""
        for disposition in NCDisposition:
            nc = NonConformance(
                nc_number=f"NC-{disposition.value}",
                nc_type=NCType.PRODUCT,
                source=NCSource.IN_PROCESS,
                title=f"Test {disposition.value}",
                description="Test",
                detected_by_id=1,
                disposition=disposition,
            )
            assert nc.disposition == disposition

    def test_nc_is_open(self):
        """Test is_open property."""
        open_nc = NonConformance(
            nc_number="NC-OPEN",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Open",
            description="Test",
            detected_by_id=1,
            status=NCStatus.OPEN,
        )

        closed_nc = NonConformance(
            nc_number="NC-CLOSED",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Closed",
            description="Test",
            detected_by_id=1,
            status=NCStatus.CLOSED,
        )

        escalated_nc = NonConformance(
            nc_number="NC-ESCALATED",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Escalated",
            description="Test",
            detected_by_id=1,
            status=NCStatus.ESCALATED_TO_CAPA,
        )

        assert open_nc.is_open is True
        assert closed_nc.is_open is False
        assert escalated_nc.is_open is False

    def test_nc_requires_capa(self):
        """Test requires_capa property."""
        critical = NonConformance(
            nc_number="NC-CRITICAL",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            severity=NCSeverity.CRITICAL,
            title="Critical",
            description="Test",
            detected_by_id=1,
        )

        minor = NonConformance(
            nc_number="NC-MINOR",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            severity=NCSeverity.MINOR,
            title="Minor",
            description="Test",
            detected_by_id=1,
        )

        assert critical.requires_capa is True
        assert minor.requires_capa is False

    def test_nc_total_cost(self):
        """Test total_cost property."""
        nc = NonConformance(
            nc_number="NC-COST",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Cost test",
            description="Test",
            detected_by_id=1,
            cost_impact=Decimal("1000.00"),
            scrap_cost=Decimal("500.00"),
            rework_cost=Decimal("250.00"),
        )

        assert nc.total_cost == Decimal("1750.00")

    def test_nc_total_cost_partial(self):
        """Test total_cost with partial costs."""
        nc = NonConformance(
            nc_number="NC-PARTIAL",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Partial cost",
            description="Test",
            detected_by_id=1,
            scrap_cost=Decimal("500.00"),
        )

        assert nc.total_cost == Decimal("500.00")

    def test_nc_age_days(self):
        """Test age_days property."""
        nc = NonConformance(
            nc_number="NC-AGE",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Age test",
            description="Test",
            detected_by_id=1,
            detected_at=utcnow_naive() - timedelta(days=10),
        )

        assert nc.age_days == 10

    def test_nc_repr(self):
        """Test string representation."""
        nc = NonConformance(
            nc_number="NC-TEST",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Test",
            description="Test",
            detected_by_id=1,
            severity=NCSeverity.MINOR,
        )
        nc.id = 1

        assert "NonConformance" in repr(nc)
        assert "NC-TEST" in repr(nc)


class TestCAPAModel:
    """Test cases for CAPA model."""

    def test_capa_creation_basic(self):
        """Test basic CAPA creation."""
        capa = CAPA(
            capa_number="CAPA-001",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Root cause investigation",
            description="Investigate recurring defect",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            capa_type=CAPAType.CORRECTIVE,
            status=CAPAStatus.OPEN,
            priority=CAPAPriority.MEDIUM,
        )

        assert capa.capa_number == "CAPA-001"
        assert capa.capa_type == CAPAType.CORRECTIVE
        assert capa.source_type == CAPASourceType.NON_CONFORMANCE
        assert capa.status == CAPAStatus.OPEN
        assert capa.priority == CAPAPriority.MEDIUM

    def test_capa_creation_full(self):
        """Test CAPA with all fields."""
        five_why = {
            "problem": "Parts failing inspection",
            "whys": [
                {"why": "Why did they fail?", "answer": "Dimension wrong"},
                {"why": "Why wrong?", "answer": "Tool worn"},
                {"why": "Why worn?", "answer": "No replacement schedule"},
            ],
            "root_cause": "Lack of tool maintenance schedule",
        }

        capa = CAPA(
            capa_number="CAPA-002",
            capa_type=CAPAType.BOTH,
            source_type=CAPASourceType.AUDIT_FINDING,
            priority=CAPAPriority.HIGH,
            title="Audit finding resolution",
            description="Address audit non-conformity",
            status=CAPAStatus.INVESTIGATING,
            owner_id=5,
            due_date=date.today() + timedelta(days=14),
            root_cause_category=RootCauseCategory.METHOD,
            root_cause_analysis="Process control inadequate",
            five_why_analysis=five_why,
            containment_actions="Quarantine suspect material",
            corrective_actions="Implement tool change schedule",
            preventive_actions="Add to TPM checklist",
        )

        assert capa.capa_type == CAPAType.BOTH
        assert capa.priority == CAPAPriority.HIGH
        assert capa.root_cause_category == RootCauseCategory.METHOD
        assert len(capa.five_why_analysis["whys"]) == 3

    def test_capa_type_values(self):
        """Test all CAPA type values."""
        for capa_type in CAPAType:
            capa = CAPA(
                capa_number=f"CAPA-{capa_type.value}",
                capa_type=capa_type,
                source_type=CAPASourceType.NON_CONFORMANCE,
                title=f"Test {capa_type.value}",
                description="Test",
                owner_id=1,
                due_date=date.today() + timedelta(days=30),
            )
            assert capa.capa_type == capa_type

    def test_capa_source_type_values(self):
        """Test all source type values."""
        for source_type in CAPASourceType:
            capa = CAPA(
                capa_number=f"CAPA-{source_type.value}",
                source_type=source_type,
                title=f"Test {source_type.value}",
                description="Test",
                owner_id=1,
                due_date=date.today() + timedelta(days=30),
            )
            assert capa.source_type == source_type

    def test_capa_status_values(self):
        """Test all status values."""
        for status in CAPAStatus:
            capa = CAPA(
                capa_number=f"CAPA-{status.value}",
                source_type=CAPASourceType.NON_CONFORMANCE,
                title=f"Test {status.value}",
                description="Test",
                owner_id=1,
                due_date=date.today() + timedelta(days=30),
                status=status,
            )
            assert capa.status == status

    def test_capa_priority_values(self):
        """Test all priority values."""
        for priority in CAPAPriority:
            capa = CAPA(
                capa_number=f"CAPA-{priority.value}",
                source_type=CAPASourceType.NON_CONFORMANCE,
                priority=priority,
                title=f"Test {priority.value}",
                description="Test",
                owner_id=1,
                due_date=date.today() + timedelta(days=30),
            )
            assert capa.priority == priority

    def test_capa_is_open(self):
        """Test is_open property."""
        open_capa = CAPA(
            capa_number="CAPA-OPEN",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Open",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            status=CAPAStatus.OPEN,
        )

        closed_capa = CAPA(
            capa_number="CAPA-CLOSED",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Closed",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            status=CAPAStatus.CLOSED,
        )

        assert open_capa.is_open is True
        assert closed_capa.is_open is False

    def test_capa_is_overdue(self):
        """Test is_overdue property."""
        overdue = CAPA(
            capa_number="CAPA-OVERDUE",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Overdue",
            description="Test",
            owner_id=1,
            due_date=date.today() - timedelta(days=5),
            status=CAPAStatus.OPEN,
        )

        on_time = CAPA(
            capa_number="CAPA-ONTIME",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="On time",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=10),
            status=CAPAStatus.OPEN,
        )

        assert overdue.is_overdue is True
        assert on_time.is_overdue is False

    def test_capa_age_days(self):
        """Test age_days property."""
        capa = CAPA(
            capa_number="CAPA-AGE",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Age test",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            opened_at=utcnow_naive() - timedelta(days=15),
        )

        assert capa.age_days == 15

    def test_capa_repr(self):
        """Test string representation."""
        capa = CAPA(
            capa_number="CAPA-TEST",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Test",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            priority=CAPAPriority.MEDIUM,
            status=CAPAStatus.OPEN,
        )
        capa.id = 1

        assert "CAPA" in repr(capa)
        assert "CAPA-TEST" in repr(capa)


class TestCAPAActionModel:
    """Test cases for CAPAAction model."""

    def test_action_creation_basic(self):
        """Test basic action creation."""
        action = CAPAAction(
            capa_id=1,
            action_type=CAPAActionType.CORRECTIVE,
            description="Implement process change and update work instruction",
            owner_id=5,
            due_date=date.today() + timedelta(days=7),
            status=CAPAActionStatus.OPEN,
        )

        assert action.capa_id == 1
        assert action.action_type == CAPAActionType.CORRECTIVE
        assert action.status == CAPAActionStatus.OPEN

    def test_action_creation_full(self):
        """Test action with all fields."""
        action = CAPAAction(
            capa_id=1,
            action_type=CAPAActionType.CONTAINMENT,
            description="Quarantine suspect material - isolate all material from LOT-123",
            expected_result="All suspect material isolated",
            owner_id=5,
            due_date=date.today() + timedelta(days=1),
            status=CAPAActionStatus.COMPLETED,
            completed_at=utcnow_naive(),
            completion_evidence="All material quarantined in area Q1",
            verified=True,
            verified_by_id=10,
            verified_at=utcnow_naive(),
        )

        assert action.action_type == CAPAActionType.CONTAINMENT
        assert action.status == CAPAActionStatus.COMPLETED
        assert action.verified is True

    def test_action_type_values(self):
        """Test all action type values."""
        for action_type in CAPAActionType:
            action = CAPAAction(
                capa_id=1,
                action_type=action_type,
                description=f"Test {action_type.value}",
                owner_id=1,
                due_date=date.today() + timedelta(days=7),
            )
            assert action.action_type == action_type

    def test_action_status_values(self):
        """Test all action status values."""
        for status in CAPAActionStatus:
            action = CAPAAction(
                capa_id=1,
                action_type=CAPAActionType.CORRECTIVE,
                description=f"Test {status.value}",
                owner_id=1,
                due_date=date.today() + timedelta(days=7),
                status=status,
            )
            assert action.status == status

    def test_action_is_overdue(self):
        """Test is_overdue property."""
        overdue = CAPAAction(
            capa_id=1,
            action_type=CAPAActionType.CORRECTIVE,
            description="Overdue action",
            owner_id=1,
            due_date=date.today() - timedelta(days=3),
            status=CAPAActionStatus.OPEN,
        )

        completed = CAPAAction(
            capa_id=1,
            action_type=CAPAActionType.CORRECTIVE,
            description="Completed action",
            owner_id=1,
            due_date=date.today() - timedelta(days=3),
            status=CAPAActionStatus.COMPLETED,
        )

        assert overdue.is_overdue is True
        assert completed.is_overdue is False

    def test_action_days_until_due(self):
        """Test days_until_due property."""
        action = CAPAAction(
            capa_id=1,
            action_type=CAPAActionType.CORRECTIVE,
            description="Test action",
            owner_id=1,
            due_date=date.today() + timedelta(days=10),
        )

        assert action.days_until_due == 10

    def test_action_repr(self):
        """Test string representation."""
        action = CAPAAction(
            capa_id=1,
            action_type=CAPAActionType.CORRECTIVE,
            description="Test action",
            owner_id=1,
            due_date=date.today() + timedelta(days=7),
        )

        assert "CAPAAction" in repr(action)


class TestInspectionPlanModel:
    """Test cases for InspectionPlan model."""

    def test_inspection_plan_creation_basic(self):
        """Test basic inspection plan creation."""
        plan = InspectionPlan(
            name="Incoming Inspection",
            inspection_type=InspectionType.INCOMING,
            is_active=True,
        )

        assert plan.name == "Incoming Inspection"
        assert plan.inspection_type == InspectionType.INCOMING
        assert plan.is_active is True

    def test_inspection_plan_creation_full(self):
        """Test inspection plan with all fields."""
        checkpoints = [
            {
                "sequence": 1,
                "characteristic": "Dimension A",
                "specification": "10.0 ± 0.1 mm",
                "nominal": 10.0,
                "tolerance_plus": 0.1,
                "tolerance_minus": 0.1,
                "measurement_method": "Caliper",
                "is_critical": True,
            },
            {
                "sequence": 2,
                "characteristic": "Surface Finish",
                "specification": "Ra 0.8 max",
                "is_critical": False,
            },
        ]

        plan = InspectionPlan(
            name="Final Inspection",
            code="INS-FINAL-001",
            description="Final product inspection",
            product_id=10,
            station_id=5,
            inspection_type=InspectionType.FINAL,
            frequency="Every lot",
            checkpoints_json=checkpoints,
            is_active=True,
            revision=2,
        )

        assert plan.code == "INS-FINAL-001"
        assert plan.inspection_type == InspectionType.FINAL
        assert len(plan.checkpoints_json) == 2

    def test_inspection_type_values(self):
        """Test all inspection type values."""
        for insp_type in InspectionType:
            plan = InspectionPlan(
                name=f"Test {insp_type.value}",
                inspection_type=insp_type,
            )
            assert plan.inspection_type == insp_type

    def test_inspection_plan_checkpoint_count(self):
        """Test checkpoint_count property."""
        plan = InspectionPlan(
            name="Test",
            inspection_type=InspectionType.IN_PROCESS,
            checkpoints_json=[
                {"sequence": 1, "characteristic": "A"},
                {"sequence": 2, "characteristic": "B"},
                {"sequence": 3, "characteristic": "C"},
            ],
        )

        assert plan.checkpoint_count == 3

    def test_inspection_plan_critical_checkpoint_count(self):
        """Test critical_checkpoint_count property."""
        plan = InspectionPlan(
            name="Test",
            inspection_type=InspectionType.IN_PROCESS,
            checkpoints_json=[
                {"sequence": 1, "characteristic": "A", "is_critical": True},
                {"sequence": 2, "characteristic": "B", "is_critical": False},
                {"sequence": 3, "characteristic": "C", "is_critical": True},
            ],
        )

        assert plan.critical_checkpoint_count == 2

    def test_inspection_plan_repr(self):
        """Test string representation."""
        plan = InspectionPlan(
            name="Test Plan",
            inspection_type=InspectionType.INCOMING,
        )
        plan.id = 1

        assert "InspectionPlan" in repr(plan)


class TestInspectionRecordModel:
    """Test cases for InspectionRecord model."""

    def test_inspection_record_creation_basic(self):
        """Test basic inspection record creation."""
        record = InspectionRecord(
            inspection_plan_id=1,
            sample_size=5,
            inspected_by_id=10,
            overall_result=InspectionResult.PASS,
        )

        assert record.inspection_plan_id == 1
        assert record.sample_size == 5
        assert record.overall_result == InspectionResult.PASS

    def test_inspection_record_creation_full(self):
        """Test inspection record with all fields."""
        measurements = [
            {
                "checkpoint_sequence": 1,
                "values": [10.05, 9.98, 10.02],
                "pass_count": 3,
                "fail_count": 0,
                "result": "pass",
            },
            {
                "checkpoint_sequence": 2,
                "values": [0.7, 0.75, 0.8],
                "pass_count": 3,
                "fail_count": 0,
                "result": "pass",
            },
        ]

        record = InspectionRecord(
            inspection_plan_id=1,
            work_order_id=100,
            lot_number="LOT-2024-001",
            sample_size=5,
            sample_ids=["S1", "S2", "S3", "S4", "S5"],
            inspected_by_id=10,
            overall_result=InspectionResult.PASS,
            measurements_json=measurements,
            defects_found=0,
            notes="All checks passed",
        )

        assert record.lot_number == "LOT-2024-001"
        assert len(record.measurements_json) == 2
        assert record.defects_found == 0

    def test_inspection_result_values(self):
        """Test all inspection result values."""
        for result in InspectionResult:
            record = InspectionRecord(
                inspection_plan_id=1,
                sample_size=1,
                inspected_by_id=1,
                overall_result=result,
            )
            assert record.overall_result == result

    def test_inspection_record_pass_rate(self):
        """Test pass_rate property."""
        record = InspectionRecord(
            inspection_plan_id=1,
            sample_size=5,
            inspected_by_id=1,
            overall_result=InspectionResult.PASS,
            measurements_json=[
                {"checkpoint_sequence": 1, "result": "pass"},
                {"checkpoint_sequence": 2, "result": "pass"},
                {"checkpoint_sequence": 3, "result": "fail"},
                {"checkpoint_sequence": 4, "result": "pass"},
            ],
        )

        # 3 pass out of 4 = 75%
        assert record.pass_rate == Decimal("75")

    def test_inspection_record_is_pass(self):
        """Test is_pass property."""
        record_pass = InspectionRecord(
            inspection_plan_id=1,
            sample_size=1,
            inspected_by_id=1,
            overall_result=InspectionResult.PASS,
        )

        record_fail = InspectionRecord(
            inspection_plan_id=1,
            sample_size=1,
            inspected_by_id=1,
            overall_result=InspectionResult.FAIL,
        )

        assert record_pass.is_pass is True
        assert record_fail.is_pass is False

    def test_inspection_record_repr(self):
        """Test string representation."""
        record = InspectionRecord(
            inspection_plan_id=1,
            sample_size=1,
            inspected_by_id=1,
            overall_result=InspectionResult.PASS,
        )

        assert "InspectionRecord" in repr(record)


class TestQualityRelationships:
    """Test Quality model relationships."""

    def test_nc_has_capa_relationship(self):
        """Test that NC has CAPA relationship."""
        nc = NonConformance(
            nc_number="NC-001",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Test",
            description="Test",
            detected_by_id=1,
        )
        assert hasattr(nc, 'capa')

    def test_capa_has_actions_list(self):
        """Test that CAPA has actions list."""
        capa = CAPA(
            capa_number="CAPA-001",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Test",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
        )
        assert hasattr(capa, 'actions')

    def test_inspection_plan_has_records_list(self):
        """Test that inspection plan has records list."""
        plan = InspectionPlan(
            name="Test",
            inspection_type=InspectionType.INCOMING,
        )
        assert hasattr(plan, 'records')


class TestQualityValidation:
    """Test validation constraints."""

    def test_nc_explicit_severity(self):
        """Test explicit NC severity is MINOR."""
        nc = NonConformance(
            nc_number="NC-001",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Test",
            description="Test",
            detected_by_id=1,
            severity=NCSeverity.MINOR,
        )
        assert nc.severity == NCSeverity.MINOR

    def test_nc_explicit_quantity_affected(self):
        """Test explicit quantity_affected is 1."""
        nc = NonConformance(
            nc_number="NC-001",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="Test",
            description="Test",
            detected_by_id=1,
            quantity_affected=1,
        )
        assert nc.quantity_affected == 1

    def test_capa_explicit_priority(self):
        """Test explicit CAPA priority is MEDIUM."""
        capa = CAPA(
            capa_number="CAPA-001",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="Test",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            priority=CAPAPriority.MEDIUM,
        )
        assert capa.priority == CAPAPriority.MEDIUM


class TestQualityEdgeCases:
    """Test edge cases for Quality models."""

    def test_nc_with_all_costs_null(self):
        """Test NC with all costs null."""
        nc = NonConformance(
            nc_number="NC-NOCOST",
            nc_type=NCType.PRODUCT,
            source=NCSource.IN_PROCESS,
            title="No cost",
            description="Test",
            detected_by_id=1,
        )

        assert nc.total_cost == Decimal("0")

    def test_capa_with_5why_analysis(self):
        """Test CAPA with complete 5-Why analysis."""
        five_why = {
            "problem": "Parts failing inspection",
            "whys": [
                {"why": "Why did parts fail?", "answer": "Dimension wrong"},
                {"why": "Why was dimension wrong?", "answer": "Tool worn"},
                {"why": "Why was tool worn?", "answer": "No replacement schedule"},
                {"why": "Why no schedule?", "answer": "Never implemented"},
                {"why": "Why never implemented?", "answer": "Process not documented"},
            ],
            "root_cause": "Lack of documented tool maintenance process",
        }

        capa = CAPA(
            capa_number="CAPA-5WHY",
            source_type=CAPASourceType.NON_CONFORMANCE,
            title="5-Why test",
            description="Test",
            owner_id=1,
            due_date=date.today() + timedelta(days=30),
            five_why_analysis=five_why,
        )

        assert len(capa.five_why_analysis["whys"]) == 5

    def test_root_cause_category_values(self):
        """Test all root cause category values."""
        for category in RootCauseCategory:
            nc = NonConformance(
                nc_number=f"NC-{category.value}",
                nc_type=NCType.PRODUCT,
                source=NCSource.IN_PROCESS,
                title=f"Test {category.value}",
                description="Test",
                detected_by_id=1,
                root_cause_category=category,
            )
            assert nc.root_cause_category == category

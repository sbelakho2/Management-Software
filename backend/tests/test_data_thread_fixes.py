"""
Tests for all data thread gap fixes.

Covers:
1. FactType misclassification fix in SingleDataThread
2. Default-deny insight filter fix in role_insights_config
3. New insight generators (Maintenance, Training, Project Management)
4. PII masking on exec endpoints
5. Warehouse RBAC role scoping (new roles)
6. Event bus publish wiring
7. Obeya operator role alignment
8. AI/ML ONNX-first embedding in self_improving_rag
9. CEO Dashboard Cognitive Obeya integration
"""

from __future__ import annotations

import asyncio
import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# =====================================================================
# 1. FactType Misclassification Fix — functional tests
# =====================================================================

from sensei.services.event_bus import DomainEvent
from sensei.services.ops.analytics_warehouse import FactType


class TestFactTypeMapping:
    """Verify _map_fact_type correctly routes ALL domain events to the right FactType."""

    def _map(self, event: DomainEvent) -> FactType:
        from sensei.services.core.single_data_thread import _map_fact_type
        return _map_fact_type(event)

    # Quality events
    def test_nc_created_maps_to_non_conformance(self):
        from sensei.services.domain_events import NCCreatedEvent
        assert self._map(NCCreatedEvent()) == FactType.NON_CONFORMANCE

    def test_capa_created_maps_to_non_conformance(self):
        from sensei.services.domain_events import CAPACreatedEvent
        assert self._map(CAPACreatedEvent()) == FactType.NON_CONFORMANCE

    def test_inspection_maps_to_non_conformance(self):
        from sensei.services.domain_events import InspectionCompletedEvent
        assert self._map(InspectionCompletedEvent()) == FactType.NON_CONFORMANCE

    def test_audit_finding_maps_to_non_conformance(self):
        from sensei.services.domain_events import AuditFindingEvent
        assert self._map(AuditFindingEvent()) == FactType.NON_CONFORMANCE

    # Finance events — previously ALL fell into QUALITY_METRIC catch-all
    def test_journal_entry_no_longer_quality_metric(self):
        from sensei.services.domain_events import JournalEntryPosted
        result = self._map(JournalEntryPosted())
        assert result == FactType.FINANCIAL_TRANSACTION
        assert result != FactType.QUALITY_METRIC, "Finance events must not fall through to QUALITY_METRIC"

    def test_cost_rollup_no_longer_quality_metric(self):
        from sensei.services.domain_events import CostRollupCompleted
        result = self._map(CostRollupCompleted())
        assert result == FactType.COST_ROLLUP
        assert result != FactType.QUALITY_METRIC

    def test_invoice_receivable_maps_to_ar(self):
        from sensei.services.domain_events import InvoiceCreatedEvent
        event = InvoiceCreatedEvent(invoice_type="receivable")
        assert self._map(event) == FactType.AR_INVOICE

    def test_invoice_payable_maps_to_ap(self):
        from sensei.services.domain_events import InvoiceCreatedEvent
        event = InvoiceCreatedEvent(invoice_type="payable")
        assert self._map(event) == FactType.AP_INVOICE

    def test_invoice_default_maps_to_ar(self):
        """Invoice with no type defaults to AR (receivable)."""
        from sensei.services.domain_events import InvoiceCreatedEvent
        assert self._map(InvoiceCreatedEvent()) == FactType.AR_INVOICE

    # HR events — previously ALL fell into QUALITY_METRIC catch-all
    def test_training_completed_no_longer_quality_metric(self):
        from sensei.services.domain_events import TrainingCompletedEvent
        result = self._map(TrainingCompletedEvent())
        assert result == FactType.TRAINING_COMPLIANCE
        assert result != FactType.QUALITY_METRIC

    def test_certification_expired_maps_to_training_compliance(self):
        from sensei.services.domain_events import CertificationExpiredEvent
        assert self._map(CertificationExpiredEvent()) == FactType.TRAINING_COMPLIANCE

    def test_employee_onboarded_maps_to_headcount_snapshot(self):
        from sensei.services.domain_events import EmployeeOnboardedEvent
        assert self._map(EmployeeOnboardedEvent()) == FactType.HEADCOUNT_SNAPSHOT

    def test_application_received_maps_to_headcount(self):
        from sensei.services.domain_events import ApplicationReceivedEvent
        assert self._map(ApplicationReceivedEvent()) == FactType.HEADCOUNT_SNAPSHOT

    # Supply chain events — previously fell to QUALITY_METRIC
    def test_mrp_run_maps_to_mrp_exception(self):
        from sensei.services.domain_events import MRPRunCompleted
        result = self._map(MRPRunCompleted())
        assert result == FactType.MRP_EXCEPTION
        assert result != FactType.QUALITY_METRIC

    def test_supplier_evaluated_maps_to_inventory(self):
        from sensei.services.domain_events import SupplierEvaluatedEvent
        assert self._map(SupplierEvaluatedEvent()) == FactType.INVENTORY_LEVEL

    # Operations — unchanged
    def test_work_order_maps_to_work_order(self):
        from sensei.services.domain_events import WorkOrderCreatedEvent
        assert self._map(WorkOrderCreatedEvent()) == FactType.WORK_ORDER

    def test_production_order_maps_to_work_order(self):
        from sensei.services.domain_events import ProductionOrderStartedEvent
        assert self._map(ProductionOrderStartedEvent()) == FactType.WORK_ORDER

    def test_downtime_maps_to_cycle_time(self):
        from sensei.services.domain_events import DowntimeRecordedEvent
        assert self._map(DowntimeRecordedEvent()) == FactType.CYCLE_TIME

    def test_pm_schedule_maps_to_work_order(self):
        from sensei.services.domain_events import PMScheduleTriggeredEvent
        assert self._map(PMScheduleTriggeredEvent()) == FactType.WORK_ORDER

    def test_all_domain_events_have_non_catchall_mapping(self):
        """Ensure NO defined domain event falls through to QUALITY_METRIC catch-all
        (except events that genuinely are quality metrics)."""
        import sensei.services.domain_events as de
        quality_events = {"AnomalyDetectedEvent", "ModelRetrainedEvent", "OpportunityStageChangedEvent"}
        for attr_name in dir(de):
            cls = getattr(de, attr_name)
            if (
                isinstance(cls, type)
                and issubclass(cls, DomainEvent)
                and cls is not DomainEvent
                and attr_name not in quality_events
            ):
                event = cls()
                result = self._map(event)
                assert result != FactType.QUALITY_METRIC, (
                    f"{attr_name} still falls to QUALITY_METRIC catch-all — add mapping"
                )


# =====================================================================
# 2. Default-Deny Insight Filter — functional tests
# =====================================================================

from sensei.services.core.role_insights_config import (
    InsightCategory,
    filter_insights_for_role,
    get_accessible_insights,
    ROLE_INSIGHT_ACCESS,
)


class TestDefaultDenyInsightFilter:
    """Verify unknown categories are excluded (default-deny)."""

    def test_unknown_category_excluded(self):
        """Previously this included unknown categories — now must deny."""
        insights = [{"category": "totally_fake_category_xyz", "title": "bad"}]
        result = filter_insights_for_role(insights, ["ceo"])
        assert len(result) == 0, "Unknown category must be denied"

    def test_no_category_excluded(self):
        """Previously included items with no category — now must deny."""
        insights = [{"title": "no category field"}]
        result = filter_insights_for_role(insights, ["ceo"])
        assert len(result) == 0, "Insights without category must be denied"

    def test_known_category_included_for_correct_role(self):
        insights = [{"category": InsightCategory.STRATEGIC_OVERVIEW.value, "title": "ok"}]
        result = filter_insights_for_role(insights, ["ceo"])
        assert len(result) == 1

    def test_known_category_excluded_for_wrong_role(self):
        insights = [{"category": InsightCategory.STRATEGIC_OVERVIEW.value, "title": "exec only"}]
        result = filter_insights_for_role(insights, ["operator"])
        assert len(result) == 0

    def test_admin_sees_all_known_categories(self):
        insights = [
            {"category": cat.value, "title": f"test_{cat.value}"}
            for cat in InsightCategory
        ]
        result = filter_insights_for_role(insights, ["admin"])
        assert len(result) == len(insights)

    def test_mixed_valid_and_invalid_categories(self):
        """A mix of valid, invalid, and missing categories — only valid ones survive."""
        insights = [
            {"category": InsightCategory.STRATEGIC_OVERVIEW.value, "title": "valid for ceo"},
            {"category": "nonexistent_category", "title": "invalid"},
            {"title": "missing category"},
            {"category": InsightCategory.FINANCIAL_KPIs.value, "title": "finance for ceo"},
        ]
        result = filter_insights_for_role(insights, ["ceo"])
        assert len(result) == 2
        assert result[0]["title"] == "valid for ceo"
        assert result[1]["title"] == "finance for ceo"

    def test_multi_role_union(self):
        """User with multiple roles gets the union of all accessible categories."""
        finance_insights = [{"category": InsightCategory.FINANCIAL_KPIs.value, "title": "fin"}]
        hr_insights = [{"category": InsightCategory.WORKFORCE_ANALYTICS.value, "title": "hr"}]
        combined = finance_insights + hr_insights

        # 'finance' role alone should only see finance
        fin_result = filter_insights_for_role(combined, ["finance"])
        assert len(fin_result) == 1 and fin_result[0]["title"] == "fin"

        # 'hr' role alone should only see HR
        hr_result = filter_insights_for_role(combined, ["hr"])
        assert len(hr_result) == 1 and hr_result[0]["title"] == "hr"

        # Both roles → see both
        both_result = filter_insights_for_role(combined, ["finance", "hr"])
        assert len(both_result) == 2

    def test_maintenance_role_sees_maintenance_insights(self):
        """Maintenance role should see maintenance-specific insight categories."""
        accessible = get_accessible_insights(["maintenance"])
        maintenance_cats = {
            InsightCategory.PREDICTIVE_MAINTENANCE,
            InsightCategory.EQUIPMENT_HEALTH,
            InsightCategory.MTBF_ANALYSIS,
            InsightCategory.SPARE_PARTS_FORECAST,
            InsightCategory.DOWNTIME_PREDICTION,
            InsightCategory.MAINTENANCE_SCHEDULE,
        }
        for cat in maintenance_cats:
            assert cat in accessible, f"Maintenance role should see {cat.value}"


# =====================================================================
# 3. Warehouse RBAC Missing Roles — functional tests
# =====================================================================


class TestWarehouseRBAC:
    """Verify new roles have proper FactType access and missing roles are no longer gaps."""

    def _get_access(self) -> dict:
        from sensei.services.ops.analytics_warehouse import _ROLE_FACT_ACCESS
        return _ROLE_FACT_ACCESS

    def test_maintenance_role_access(self):
        maint = self._get_access().get("maintenance", set())
        assert FactType.WORK_ORDER.value in maint
        assert FactType.CYCLE_TIME.value in maint
        assert FactType.ANDON_EVENT.value in maint
        # Maintenance should NOT see finance
        assert FactType.FINANCIAL_TRANSACTION.value not in maint

    def test_supply_chain_role_access(self):
        sc = self._get_access().get("supply_chain", set())
        assert FactType.INVENTORY_LEVEL.value in sc
        assert FactType.STOCK_MOVEMENT.value in sc
        assert FactType.MRP_EXCEPTION.value in sc

    def test_purchasing_role_access(self):
        p = self._get_access().get("purchasing", set())
        assert FactType.AP_INVOICE.value in p
        assert FactType.COST_ROLLUP.value in p
        assert FactType.INVENTORY_LEVEL.value in p
        # Purchasing should NOT see HR data
        assert FactType.HEADCOUNT_SNAPSHOT.value not in p

    def test_sales_role_access(self):
        s = self._get_access().get("sales", set())
        assert FactType.AR_INVOICE.value in s
        # Sales should NOT see AP data
        assert FactType.AP_INVOICE.value not in s

    def test_engineering_role_access(self):
        e = self._get_access().get("engineering", set())
        assert FactType.WORK_ORDER.value in e
        assert FactType.COST_ROLLUP.value in e
        assert FactType.NON_CONFORMANCE.value in e

    def test_supervisor_role_access(self):
        s = self._get_access().get("supervisor", set())
        assert FactType.WORK_ORDER.value in s
        assert FactType.TRAINING_COMPLIANCE.value in s
        assert FactType.HEADCOUNT_SNAPSHOT.value in s

    def test_auditor_has_full_access(self):
        a = self._get_access().get("auditor", set())
        assert a == {ft.value for ft in FactType}

    def test_all_previously_missing_roles_exist(self):
        """The 10 roles that were previously missing are now present."""
        missing_roles = [
            "maintenance", "supply_chain", "purchasing", "logistics",
            "warehouse", "sales", "engineering", "supervisor", "it", "auditor",
        ]
        access = self._get_access()
        for role in missing_roles:
            assert role in access, f"Role '{role}' still missing from _ROLE_FACT_ACCESS"

    def test_no_role_has_empty_access(self):
        """Every role in the map has at least one FactType."""
        for role, facts in self._get_access().items():
            assert len(facts) > 0, f"Role '{role}' has empty fact access"


# =====================================================================
# 4. Event Bus Publish Wiring — functional tests
# =====================================================================


class TestEventBusWiring:
    """Verify domain events are actually published from service create methods."""

    def test_nc_register_publishes_event_with_correct_data(self):
        """register_nc() must fire NCCreatedEvent with NC id, severity, type."""
        from sensei.services.quality.capa_workflow import (
            CAPAWorkflowIntegrationService, NCType, NCSeverity,
        )
        from sensei.services.domain_events import NCCreatedEvent

        svc = CAPAWorkflowIntegrationService()
        published = []

        with patch.object(
            __import__("sensei.services.event_bus", fromlist=["event_bus"]).event_bus,
            "publish_sync",
            side_effect=lambda e: published.append(e),
        ):
            nc, _ = svc.register_nc(
                nc_type=NCType.INTERNAL,
                severity=NCSeverity.CRITICAL,
                title="Test NC",
                description="Unit test",
                detected_by=uuid4(),
            )

        nc_events = [e for e in published if isinstance(e, NCCreatedEvent)]
        assert len(nc_events) == 1
        evt = nc_events[0]
        assert evt.nc_id == str(nc.id)
        assert evt.severity == "critical"
        assert evt.nc_type == "internal"

    def test_capa_auto_created_publishes_both_events(self):
        """Critical NC triggers auto-CAPA, which must publish CAPACreatedEvent."""
        from sensei.services.quality.capa_workflow import (
            CAPAWorkflowIntegrationService, NCType, NCSeverity,
        )
        from sensei.services.domain_events import NCCreatedEvent, CAPACreatedEvent

        svc = CAPAWorkflowIntegrationService()
        published = []

        with patch.object(
            __import__("sensei.services.event_bus", fromlist=["event_bus"]).event_bus,
            "publish_sync",
            side_effect=lambda e: published.append(e),
        ):
            nc, capa_result = svc.register_nc(
                nc_type=NCType.INTERNAL,
                severity=NCSeverity.CRITICAL,
                title="Critical NC for CAPA",
                description="Auto-create CAPA",
                detected_by=uuid4(),
            )

        # Must have both NC and CAPA events
        nc_events = [e for e in published if isinstance(e, NCCreatedEvent)]
        capa_events = [e for e in published if isinstance(e, CAPACreatedEvent)]
        assert len(nc_events) == 1
        assert len(capa_events) >= 1
        assert capa_events[0].auto_created is True
        assert capa_events[0].nc_id == str(nc.id)

    def test_low_severity_nc_does_not_trigger_capa_event(self):
        """Low-severity NC should NOT auto-create CAPA."""
        from sensei.services.quality.capa_workflow import (
            CAPAWorkflowIntegrationService, NCType, NCSeverity,
        )
        from sensei.services.domain_events import CAPACreatedEvent

        svc = CAPAWorkflowIntegrationService()
        published = []

        with patch.object(
            __import__("sensei.services.event_bus", fromlist=["event_bus"]).event_bus,
            "publish_sync",
            side_effect=lambda e: published.append(e),
        ):
            svc.register_nc(
                nc_type=NCType.INTERNAL,
                severity=NCSeverity.LOW,
                title="Minor NC",
                description="No CAPA needed",
                detected_by=uuid4(),
            )

        capa_events = [e for e in published if isinstance(e, CAPACreatedEvent)]
        assert len(capa_events) == 0, "Low-severity NC should not auto-create CAPA"


# =====================================================================
# 5. AI/ML ONNX-First Embedding — functional tests
# =====================================================================


class TestSelfImprovingRAGEmbedding:
    """Verify ONNX-first pattern with hash fallback in SimpleDocumentProcessor."""

    def test_fallback_produces_deterministic_embeddings(self):
        """Without ONNX, hash-based embeddings are deterministic and normalized."""
        from sensei.services.ai.self_improving_rag import SimpleDocumentProcessor

        proc = SimpleDocumentProcessor()
        proc._onnx_attempted = True
        proc._onnx_embedder = None

        vec = proc._embed_text("hello world", dim=16)
        assert len(vec) == 16
        assert all(isinstance(v, float) for v in vec)

        # Deterministic
        vec2 = proc._embed_text("hello world", dim=16)
        assert vec == vec2

        # Normalized (approximately unit norm)
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01

    def test_different_texts_produce_different_embeddings(self):
        from sensei.services.ai.self_improving_rag import SimpleDocumentProcessor

        proc = SimpleDocumentProcessor()
        proc._onnx_attempted = True
        proc._onnx_embedder = None

        vec1 = proc._embed_text("hello world", dim=16)
        vec2 = proc._embed_text("goodbye world", dim=16)
        assert vec1 != vec2

    def test_onnx_embedder_lazy_loaded(self):
        """Should attempt to load OnnxEmbedder lazily (not on __init__)."""
        from sensei.services.ai.self_improving_rag import SimpleDocumentProcessor

        proc = SimpleDocumentProcessor()
        assert proc._onnx_attempted is False
        assert proc._onnx_embedder is None

        proc._get_onnx_embedder()
        assert proc._onnx_attempted is True

    def test_onnx_embedder_used_with_truncation(self):
        """When ONNX embedder available, uses it and truncates to requested dim."""
        from sensei.services.ai.self_improving_rag import SimpleDocumentProcessor

        proc = SimpleDocumentProcessor()
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1 * i for i in range(384)]  # 384-dim
        proc._onnx_embedder = mock_embedder
        proc._onnx_attempted = True

        vec = proc._embed_text("test query", dim=16)
        mock_embedder.embed.assert_called_once_with("test query")
        assert len(vec) == 16
        # Should be the first 16 values from the 384-dim vector
        expected = [0.1 * i for i in range(16)]
        for a, b in zip(vec, expected):
            assert abs(a - b) < 1e-9

    def test_onnx_failure_falls_back_to_hash(self):
        """If ONNX embed() raises, falls back to hash-based."""
        from sensei.services.ai.self_improving_rag import SimpleDocumentProcessor

        proc = SimpleDocumentProcessor()
        mock_embedder = MagicMock()
        mock_embedder.embed.side_effect = RuntimeError("ONNX error")
        proc._onnx_embedder = mock_embedder
        proc._onnx_attempted = True

        vec = proc._embed_text("test", dim=16)
        assert len(vec) == 16  # still produces output via hash fallback

    def test_document_processing_produces_chunks_with_embeddings(self):
        """Full document processing pipeline: chunk → embed → structured output."""
        from sensei.services.ai.self_improving_rag import SimpleDocumentProcessor

        proc = SimpleDocumentProcessor(chunk_size=50)
        proc._onnx_attempted = True
        proc._onnx_embedder = None

        content = b"A" * 120  # 120 chars → should produce 3 chunks at size 50
        loop = asyncio.new_event_loop()
        chunks = loop.run_until_complete(proc.process_document("doc1", content))
        loop.close()

        assert len(chunks) == 3
        for chunk_id, chunk_text, embedding in chunks:
            assert chunk_id.startswith("doc1_chunk_")
            assert len(embedding) == 16
            assert isinstance(embedding[0], float)


# =====================================================================
# 6. Obeya Operator Role — functional test
# =====================================================================


class TestObeyaOperatorRole:
    """Verify backend Obeya router allows operator (matching frontend page-access.ts)."""

    def test_operator_in_obeya_router_roles(self):
        from sensei.api.v1.endpoints import obeya as obeya_module
        import inspect
        source = inspect.getsource(obeya_module)
        assert '"operator"' in source or "'operator'" in source

    def test_frontend_backend_obeya_roles_aligned(self):
        """The frontend OPS_ROLES from page-access.ts includes operator.
        Backend Obeya router must also include it."""
        from sensei.api.v1.endpoints import obeya as obeya_module
        import inspect
        source = inspect.getsource(obeya_module)
        # Frontend page-access.ts line 10 has operator in OPS_ROLES
        # Backend must also list it
        assert "operator" in source


# =====================================================================
# 7. CEO Dashboard Cognitive Obeya Integration — functional tests
# =====================================================================


class TestCEODashboardCognitiveObeya:
    """Verify CEO dashboard response model includes cognitive_obeya."""

    def test_response_model_has_cognitive_obeya_field(self):
        from sensei.api.v1.endpoints.executive_intel import CEODashboardResponse
        fields = CEODashboardResponse.model_fields
        assert "cognitive_obeya" in fields

    def test_cognitive_obeya_defaults_to_none(self):
        from sensei.api.v1.endpoints.executive_intel import CEODashboardResponse
        field_info = CEODashboardResponse.model_fields["cognitive_obeya"]
        assert field_info.default is None

    def test_cognitive_obeya_accepts_dict(self):
        """Can construct a CEODashboardResponse with cognitive_obeya data."""
        from sensei.api.v1.endpoints.executive_intel import CEODashboardResponse

        # Build via model_construct to skip nested model validation
        resp = CEODashboardResponse.model_construct(
            data_thread=None,
            sqdcp=None,
            kpi_summary=None,
            insights=[],
            cognitive_obeya={
                "trend_warnings": [
                    {"metric_id": "oee", "direction": "decreasing", "days_to_breach": 5}
                ],
                "warning_count": 1,
            },
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        assert resp.cognitive_obeya is not None
        assert resp.cognitive_obeya["warning_count"] == 1
        assert len(resp.cognitive_obeya["trend_warnings"]) == 1


# =====================================================================
# 8. Insight Generator — New Categories functional tests
# =====================================================================


class TestNewInsightCategories:
    """Verify insight_generator references the correct new models and categories."""

    def test_maintenance_models_imported(self):
        from sensei.services.ops import insight_generator as ig
        assert hasattr(ig, "PMSchedule")
        assert hasattr(ig, "MaintenanceWorkOrder")
        assert hasattr(ig, "DowntimeEvent")
        assert hasattr(ig, "SparePart")
        assert hasattr(ig, "FailureRecord")

    def test_training_models_imported(self):
        from sensei.services.ops import insight_generator as ig
        assert hasattr(ig, "Training")
        assert hasattr(ig, "UserSkill")
        assert hasattr(ig, "Skill")

    def test_project_models_imported(self):
        from sensei.services.ops import insight_generator as ig
        assert hasattr(ig, "Project")
        assert hasattr(ig, "Issue")
        assert hasattr(ig, "UserStory")
        assert hasattr(ig, "Sprint")

    def test_insight_helper_builds_all_required_fields(self):
        """The _insight helper must include category, title, severity, generated_at."""
        from sensei.services.ops.insight_generator import _insight
        result = _insight(
            category=InsightCategory.PREDICTIVE_MAINTENANCE,
            title="Test Insight",
            description="Testing",
            severity="warning",
            metric_value=42,
            metric_label="Count",
            recommendation="Do something",
        )
        assert result["category"] == InsightCategory.PREDICTIVE_MAINTENANCE.value
        assert result["title"] == "Test Insight"
        assert result["severity"] == "warning"
        assert result["metric_value"] == 42
        assert result["recommendation"] == "Do something"
        assert "generated_at" in result

    def test_new_maintenance_categories_in_insight_descriptions(self):
        """All maintenance categories have documentation entries."""
        from sensei.services.core.role_insights_config import INSIGHT_DESCRIPTIONS
        maint_cats = [
            InsightCategory.PREDICTIVE_MAINTENANCE,
            InsightCategory.EQUIPMENT_HEALTH,
            InsightCategory.MTBF_ANALYSIS,
            InsightCategory.SPARE_PARTS_FORECAST,
            InsightCategory.DOWNTIME_PREDICTION,
            InsightCategory.MAINTENANCE_SCHEDULE,
        ]
        for cat in maint_cats:
            assert cat in INSIGHT_DESCRIPTIONS, f"{cat.value} missing from INSIGHT_DESCRIPTIONS"


# =====================================================================
# 9. PII Masking on Exec Endpoints — structural tests
# =====================================================================


class TestPIIMaskingWiring:
    """Verify exec endpoints call mask_analytics_data."""

    def test_sqdcp_endpoint_calls_masking(self):
        """SQDCP handler must reference mask_analytics_data."""
        import inspect
        from sensei.api.v1.endpoints import executive_intel as ei
        source = inspect.getsource(ei.get_sqdcp_dashboard)
        assert "mask_analytics_data" in source

    def test_revenue_waterfall_endpoint_calls_masking(self):
        import inspect
        from sensei.api.v1.endpoints import executive_intel as ei
        source = inspect.getsource(ei.get_revenue_waterfall)
        assert "mask_analytics_data" in source

    def test_margin_analysis_endpoint_calls_masking(self):
        import inspect
        from sensei.api.v1.endpoints import executive_intel as ei
        source = inspect.getsource(ei.get_margin_analysis)
        assert "mask_analytics_data" in source

    def test_strategic_export_endpoint_calls_masking(self):
        import inspect
        from sensei.api.v1.endpoints import executive_intel as ei
        source = inspect.getsource(ei.export_strategic_report)
        assert "mask_analytics_data" in source

    def test_ceo_dashboard_uses_role_filtering_then_masking(self):
        """CEO dashboard must apply filter_insights_for_role THEN mask_analytics_data."""
        import inspect
        from sensei.api.v1.endpoints import executive_intel as ei
        source = inspect.getsource(ei.get_ceo_dashboard)
        filter_pos = source.index("filter_insights_for_role")
        mask_pos = source.index("mask_analytics_data")
        assert filter_pos < mask_pos, "Must filter BEFORE masking"


# =====================================================================
# 10. End-to-End: Event → FactType → Warehouse Scoping
# =====================================================================


class TestEndToEndEventRouting:
    """Verify the full event → FactType → RBAC scoping chain works."""

    def test_finance_event_accessible_to_finance_role_only(self):
        """JournalEntryPosted → FINANCIAL_TRANSACTION → only finance/admin roles can see it."""
        from sensei.services.core.single_data_thread import _map_fact_type
        from sensei.services.domain_events import JournalEntryPosted
        from sensei.services.ops.analytics_warehouse import _ROLE_FACT_ACCESS

        fact_type = _map_fact_type(JournalEntryPosted())
        assert fact_type == FactType.FINANCIAL_TRANSACTION

        # Finance role should see it
        assert fact_type.value in _ROLE_FACT_ACCESS["finance"]
        # Admin and ceo should see it
        assert fact_type.value in _ROLE_FACT_ACCESS["admin"]
        assert fact_type.value in _ROLE_FACT_ACCESS["ceo"]
        # Ops role should NOT see finance data
        assert fact_type.value not in _ROLE_FACT_ACCESS["ops"]
        # Maintenance should NOT see finance data
        assert fact_type.value not in _ROLE_FACT_ACCESS["maintenance"]

    def test_training_event_accessible_to_hr_and_supervisor(self):
        """TrainingCompletedEvent → TRAINING_COMPLIANCE → HR + supervisor can see it."""
        from sensei.services.core.single_data_thread import _map_fact_type
        from sensei.services.domain_events import TrainingCompletedEvent
        from sensei.services.ops.analytics_warehouse import _ROLE_FACT_ACCESS

        fact_type = _map_fact_type(TrainingCompletedEvent())
        assert fact_type == FactType.TRAINING_COMPLIANCE

        assert fact_type.value in _ROLE_FACT_ACCESS["hr"]
        assert fact_type.value in _ROLE_FACT_ACCESS["supervisor"]
        # Sales should NOT see HR/training data
        assert fact_type.value not in _ROLE_FACT_ACCESS["sales"]

    def test_mrp_event_accessible_to_supply_chain(self):
        """MRPRunCompleted → MRP_EXCEPTION → supply_chain + ops can see it."""
        from sensei.services.core.single_data_thread import _map_fact_type
        from sensei.services.domain_events import MRPRunCompleted
        from sensei.services.ops.analytics_warehouse import _ROLE_FACT_ACCESS

        fact_type = _map_fact_type(MRPRunCompleted())
        assert fact_type == FactType.MRP_EXCEPTION

        assert fact_type.value in _ROLE_FACT_ACCESS["supply_chain"]
        assert fact_type.value in _ROLE_FACT_ACCESS["ops"]
        assert fact_type.value in _ROLE_FACT_ACCESS["warehouse"]
        assert fact_type.value in _ROLE_FACT_ACCESS["purchasing"]

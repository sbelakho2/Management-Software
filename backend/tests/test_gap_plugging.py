"""Functional tests for all gap-plugging changes.

Run with:
    SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://x:x@localhost/x \
    DATABASE_URL_SYNC=postgresql://x:x@localhost/x \
    python tests/test_gap_plugging.py
"""

import sys
import os
import importlib

# Ensure we can import from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} — {detail}")


def main():
    global passed, failed

    # =====================================================================
    # SECTION 1: FactType Enum Extensions
    # =====================================================================
    print("\n=== 1. FactType Enum Extensions ===")
    from sensei.services.ops.analytics_warehouse import FactType

    for name in ("OPPORTUNITY", "RISK_EVENT", "ANOMALY_DETECTION", "MODEL_RETRAIN"):
        check(f"FactType.{name} exists", hasattr(FactType, name))

    check(
        "FactType has 20 members",
        len(FactType) == 20,
        f"got {len(FactType)}",
    )

    # =====================================================================
    # SECTION 2: _map_fact_type Routes New Events
    # =====================================================================
    print("\n=== 2. _map_fact_type Routing ===")
    from sensei.services.core.single_data_thread import _map_fact_type
    from dataclasses import dataclass

    @dataclass
    class _Ev:
        event_id: str = "test"

    test_cases = [
        ("OpportunityStageChangedEvent", FactType.OPPORTUNITY),
        ("AnomalyDetectedEvent", FactType.ANOMALY_DETECTION),
        ("ModelRetrainedEvent", FactType.MODEL_RETRAIN),
        ("NCCreatedEvent", FactType.NON_CONFORMANCE),
        ("CostRollupCompleted", FactType.COST_ROLLUP),
        ("InspectionCompletedEvent", FactType.NON_CONFORMANCE),
        ("AuditFindingEvent", FactType.NON_CONFORMANCE),
        ("PMScheduleTriggeredEvent", FactType.WORK_ORDER),
        ("ProductionOrderStartedEvent", FactType.WORK_ORDER),
        ("ProductionOrderCompletedEvent", FactType.WORK_ORDER),
        ("SupplierEvaluatedEvent", FactType.INVENTORY_LEVEL),
        ("TrainingCompletedEvent", FactType.TRAINING_COMPLIANCE),
        ("CertificationExpiredEvent", FactType.TRAINING_COMPLIANCE),
        ("EmployeeOnboardedEvent", FactType.HEADCOUNT_SNAPSHOT),
        ("ApplicationReceivedEvent", FactType.HEADCOUNT_SNAPSHOT),
        ("InvoiceCreatedEvent", FactType.AR_INVOICE),
        ("JournalEntryPosted", FactType.FINANCIAL_TRANSACTION),
        ("WorkOrderCreatedEvent", FactType.WORK_ORDER),
        ("DowntimeRecordedEvent", FactType.CYCLE_TIME),
        ("MRPRunCompleted", FactType.MRP_EXCEPTION),
    ]

    for event_name, expected_ft in test_cases:
        ev = _Ev()
        type(ev).__name__ = event_name
        result = _map_fact_type(ev)
        check(
            f"{event_name} -> {expected_ft.value}",
            result == expected_ft,
            f"got {result.value}",
        )

    # =====================================================================
    # SECTION 3: Role-Fact Access (RBAC Scoping)
    # =====================================================================
    print("\n=== 3. RBAC Role-Fact Access ===")
    from sensei.services.ops.analytics_warehouse import _ROLE_FACT_ACCESS, AnalyticsWarehouseService

    wh = AnalyticsWarehouseService()

    # CEO/admin must see everything
    for role in ("ceo", "admin", "gm", "exec"):
        allowed = wh.allowed_fact_types(actor_roles=[role])
        check(
            f"{role} sees all {len(FactType)} fact types",
            len(allowed) == len(FactType),
            f"got {len(allowed)}",
        )

    # Sales must see OPPORTUNITY
    sales_allowed = wh.allowed_fact_types(actor_roles=["sales"])
    check("sales has opportunity", "opportunity" in sales_allowed)

    # IT must see anomaly + retrain
    it_allowed = wh.allowed_fact_types(actor_roles=["it"])
    check("it has anomaly_detection", "anomaly_detection" in it_allowed)
    check("it has model_retrain", "model_retrain" in it_allowed)

    # Risk role
    risk_allowed = wh.allowed_fact_types(actor_roles=["risk"])
    check("risk has risk_event", "risk_event" in risk_allowed)

    # =====================================================================
    # SECTION 4: Domain Event Classes All Import
    # =====================================================================
    print("\n=== 4. Domain Event Classes ===")
    from sensei.services.domain_events import (
        NCCreatedEvent,
        CAPACreatedEvent,
        InspectionCompletedEvent,
        AuditFindingEvent,
        CostRollupCompleted,
        JournalEntryPosted,
        InvoiceCreatedEvent,
        WorkOrderCreatedEvent,
        DowntimeRecordedEvent,
        PMScheduleTriggeredEvent,
        TrainingCompletedEvent,
        CertificationExpiredEvent,
        EmployeeOnboardedEvent,
        ProductionOrderStartedEvent,
        ProductionOrderCompletedEvent,
        MRPRunCompleted,
        SupplierEvaluatedEvent,
        OpportunityStageChangedEvent,
        ApplicationReceivedEvent,
        AnomalyDetectedEvent,
        ModelRetrainedEvent,
    )

    check("All 21 domain events importable", True)

    # Verify they are dataclasses with event_id
    import dataclasses as dc
    for cls in (
        NCCreatedEvent, CAPACreatedEvent, InspectionCompletedEvent,
        AuditFindingEvent, CostRollupCompleted, InvoiceCreatedEvent,
        WorkOrderCreatedEvent, DowntimeRecordedEvent,
        PMScheduleTriggeredEvent, TrainingCompletedEvent,
        CertificationExpiredEvent, EmployeeOnboardedEvent,
        ProductionOrderStartedEvent, ProductionOrderCompletedEvent,
        MRPRunCompleted, SupplierEvaluatedEvent,
        OpportunityStageChangedEvent, ApplicationReceivedEvent,
        AnomalyDetectedEvent, ModelRetrainedEvent,
    ):
        check(
            f"{cls.__name__} is dataclass with event_id",
            dc.is_dataclass(cls) and "event_id" in {f.name for f in dc.fields(cls)},
        )

    # =====================================================================
    # SECTION 5: Event Bus Singleton
    # =====================================================================
    print("\n=== 5. Event Bus ===")
    from sensei.services.event_bus import event_bus

    check("event_bus is not None", event_bus is not None)
    check("event_bus has publish method", hasattr(event_bus, "publish"))
    check("event_bus has publish_sync method", hasattr(event_bus, "publish_sync"))

    # =====================================================================
    # SECTION 6: Celery Beat Schedule
    # =====================================================================
    print("\n=== 6. Celery Beat Schedule ===")
    from sensei.core.celery_app import celery_app

    beat = celery_app.conf.get("beat_schedule", {})
    check("beat_schedule exists", bool(beat), "empty or missing")
    check(
        "daily-analytics-snapshot in schedule",
        "daily-analytics-snapshot" in beat,
    )
    check(
        "compute-warehouse-kpis in schedule",
        "compute-warehouse-kpis" in beat,
    )

    # Verify task names
    if "daily-analytics-snapshot" in beat:
        task_name = beat["daily-analytics-snapshot"].get("task", "")
        check(
            "snapshot task name correct",
            task_name == "sensei.tasks.analytics_tasks.daily_analytics_snapshot",
            f"got {task_name}",
        )
    if "compute-warehouse-kpis" in beat:
        task_name = beat["compute-warehouse-kpis"].get("task", "")
        check(
            "kpi task name correct",
            task_name == "sensei.tasks.analytics_tasks.compute_warehouse_kpis",
            f"got {task_name}",
        )

    # =====================================================================
    # SECTION 7: Analytics Tasks Import
    # =====================================================================
    print("\n=== 7. Analytics Tasks ===")
    from sensei.tasks.analytics_tasks import daily_analytics_snapshot, compute_warehouse_kpis

    check("daily_analytics_snapshot is Celery task", hasattr(daily_analytics_snapshot, "delay"))
    check("compute_warehouse_kpis is Celery task", hasattr(compute_warehouse_kpis, "delay"))

    # =====================================================================
    # SECTION 8: RBAC Guards on Endpoint Routers
    # =====================================================================
    print("\n=== 8. RBAC Router Guards ===")

    endpoint_modules = [
        "sensei.api.v1.endpoints.data_lineage",
        "sensei.api.v1.endpoints.pulse",
        "sensei.api.v1.endpoints.common_thread",
        "sensei.api.v1.endpoints.state_machines",
        "sensei.api.v1.endpoints.learning",
        "sensei.api.v1.endpoints.knowledge_pack",
        "sensei.api.v1.endpoints.ai_health",
        "sensei.api.v1.endpoints.risk",
        "sensei.api.v1.endpoints.gm_onboarding",
        "sensei.api.v1.endpoints.sites",
        "sensei.api.v1.endpoints.tasks",
        "sensei.api.v1.endpoints.context_bus",
    ]

    for mod_name in endpoint_modules:
        try:
            mod = importlib.import_module(mod_name)
            router = getattr(mod, "router", None)
            if router is None:
                check(f"{mod_name.split('.')[-1]} router exists", False, "no router")
                continue
            # Check that router has dependencies
            deps = getattr(router, "dependencies", [])
            has_deps = len(deps) > 0
            check(f"{mod_name.split('.')[-1]} has RBAC dependencies", has_deps, f"deps={deps}")
        except Exception as e:
            check(f"{mod_name.split('.')[-1]} imports", False, str(e)[:80])

    # =====================================================================
    # SECTION 9: Event Publishing Wiring (import-level checks)
    # =====================================================================
    print("\n=== 9. Event Publishing Wiring ===")
    import inspect

    event_wiring = [
        ("sensei.services.quality.self_inspection_service", "InspectionCompletedEvent"),
        ("sensei.services.quality.first_article_service", "InspectionCompletedEvent"),
        ("sensei.services.quality.aql_sampling_service", "InspectionCompletedEvent"),
        ("sensei.services.quality.qms_quality", "AuditFindingEvent"),
        ("sensei.services.quality.qms_quality", "SupplierEvaluatedEvent"),
        ("sensei.services.finance.cost_rollup_service", "CostRollupCompleted"),
        ("sensei.services.maintenance.persistent_maintenance", "PMScheduleTriggeredEvent"),
        ("sensei.services.production.dispatch_traveler", "ProductionOrderStartedEvent"),
        ("sensei.services.production.dispatch_traveler", "ProductionOrderCompletedEvent"),
        ("sensei.services.crm.pipeline_automation", "OpportunityStageChangedEvent"),
        ("sensei.services.ai.ai_reasoning", "AnomalyDetectedEvent"),
        ("sensei.services.ai.semantic_anomaly_detection", "AnomalyDetectedEvent"),
    ]

    for mod_name, event_name in event_wiring:
        try:
            mod = importlib.import_module(mod_name)
            src = inspect.getsource(mod)
            has_import = event_name in src
            has_publish = "event_bus.publish" in src or "event_bus.publish_sync" in src
            check(
                f"{mod_name.split('.')[-1]} publishes {event_name}",
                has_import and has_publish,
                f"import={has_import}, publish={has_publish}",
            )
        except Exception as e:
            check(f"{mod_name.split('.')[-1]}", False, str(e)[:80])

    # ModelRetrainedEvent uses lazy import, check differently
    try:
        mod = importlib.import_module("sensei.services.ai.continuous_learning")
        src = inspect.getsource(mod)
        check(
            "continuous_learning publishes ModelRetrainedEvent",
            "ModelRetrainedEvent" in src and "event_bus.publish" in src,
        )
    except Exception as e:
        check("continuous_learning", False, str(e)[:80])

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print(f"\n{'='*60}")
    total = passed + failed
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sensei.services.ai.chatbot.chat_service import ChatService
from sensei.services.ai.nlp_command_palette import (
    NLPCommandPalette,
    EntityType,
    ActionType,
)
from sensei.services.core.alerting_config import (
    AlertingConfigService,
    ThresholdCondition,
    AggregationFunction,
    ComparisonOperator,
    AlertSeverity,
)
from sensei.services.core.business_continuity import (
    BusinessContinuityService,
    EventPriority,
    ConflictResolutionStrategy,
)
from sensei.services.sales.quote_approval_time_tracking import (
    QuoteApprovalTimeTrackingService,
    QuoteApprovalContext,
    ApprovalCriterionStatus,
    ApprovalDecision,
)
from sensei.services.sales.rfq_time_tracking import (
    RFQTimeTrackingService,
    TaskType,
)
from sensei.services.utils.job_idempotency import (
    JobIdempotencyService,
    JobType,
    JobStatus,
)
from sensei.services.ai.visual_quality_inspection import (
    VisualQualityInspectionService,
    InspectionDecision,
)


@pytest.mark.asyncio
async def test_chat_service_persistence_smoke() -> None:
    service = ChatService()
    user_id = uuid4()
    session = service.get_or_create_session(user_id)
    session.last_active = datetime.now(timezone.utc) - timedelta(hours=25)
    removed = await service.cleanup_inactive_sessions_async(max_age_hours=24)
    assert removed == 1


@pytest.mark.asyncio
async def test_nlp_command_palette_persistence_smoke() -> None:
    palette = NLPCommandPalette()
    await palette.register_known_symbols_async(EntityType.RFQ, ["RFQ-1001"])
    assert "RFQ-1001" in palette.fuzzy_matcher.known_symbols[EntityType.RFQ]

    result = await palette.execute_async(
        query="show rfq 1001",
        session_id="session-1",
        user_id="user-1",
    )
    assert result["action_type"] == ActionType.VIEW_RFQ.value


@pytest.mark.asyncio
async def test_alerting_config_persistence_smoke() -> None:
    service = AlertingConfigService()
    rule = await service.create_rule_async(
        name="CPU High",
        conditions=[
            ThresholdCondition(
                metric="cpu_usage",
                aggregation=AggregationFunction.AVG,
                operator=ComparisonOperator.GREATER_THAN,
                threshold=90.0,
                duration_seconds=60,
            )
        ],
        severity=AlertSeverity.HIGH,
        description="CPU usage too high",
        labels={"service": "api"},
    )

    alert = await service.fire_alert_async(rule.id, value=95.0)
    assert alert is not None
    await service.acknowledge_alert_async(alert.id, acknowledged_by="ops")
    await service.resolve_alert_async(alert.id)


@pytest.mark.asyncio
async def test_business_continuity_persistence_smoke() -> None:
    service = BusinessContinuityService()
    actor_roles = {"admin"}

    event = await service.queue_event_async(
        device_id="device-1",
        entity_type="work_order",
        entity_id=uuid4(),
        operation="update",
        priority=EventPriority.HIGH,
        payload={"status": "complete"},
        client_timestamp=datetime.now(timezone.utc),
    )
    await service.mark_synced_async(event.id)

    await service.set_criticality_rule_async(
        entity_type="work_order",
        resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        actor_roles=actor_roles,
    )

    await service.set_rto_rpo_targets_async(
        rto_minutes=60,
        rpo_minutes=15,
        actor_user_id=uuid4(),
        actor_roles=actor_roles,
    )

    await service.validate_rto_rpo_async(
        achieved_rto_minutes=30,
        achieved_rpo_minutes=10,
        actor_roles=actor_roles,
    )

    rehearsal = await service.schedule_rehearsal_async(
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
        actor_user_id=uuid4(),
        actor_roles=actor_roles,
    )
    await service.start_rehearsal_async(rehearsal.id, actor_roles=actor_roles)
    await service.complete_rehearsal_async(
        rehearsal.id,
        rto_achieved_minutes=45,
        rpo_achieved_minutes=12,
        notes="ok",
        actor_roles=actor_roles,
    )


@pytest.mark.asyncio
async def test_quote_approval_time_tracking_persistence_smoke() -> None:
    service = QuoteApprovalTimeTrackingService()
    context = QuoteApprovalContext(
        quote_id=uuid4(),
        quote_number="Q-1001",
        version=1,
        customer_name="Acme",
        total_value=10000.0,
        margin_percent=18.0,
        line_item_count=5,
    )
    session = await service.start_approval_session_async(
        quote_id=context.quote_id,
        approver_id=uuid4(),
        context=context,
    )
    await service.update_criterion_async(
        session.id,
        "margin_check",
        ApprovalCriterionStatus.PASSED,
        message="ok",
    )
    await service.make_decision_async(session.id, ApprovalDecision.APPROVED)


@pytest.mark.asyncio
async def test_rfq_time_tracking_persistence_smoke() -> None:
    service = RFQTimeTrackingService()
    session = await service.start_session_async(
        TaskType.RFQ_INTAKE,
        entity_id=uuid4(),
        user_id=uuid4(),
        notes="start",
    )
    await service.pause_session_async(session.id, reason="pause")
    await service.resume_session_async(session.id)
    await service.complete_session_async(session.id, notes="done")


@pytest.mark.asyncio
async def test_job_idempotency_persistence_smoke() -> None:
    service = JobIdempotencyService()
    key = service.generate_idempotency_key(JobType.REPORT_GENERATION, "r1")
    job = await service.register_job_async(key)
    assert job.idempotency_key == key.key
    await service.update_job_status_async(job.idempotency_key, JobStatus.RUNNING)
    await service.cache_result_async(job.idempotency_key, {"ok": True})
    await service.invalidate_cache_async(job.idempotency_key)


@pytest.mark.asyncio
async def test_visual_quality_inspection_persistence_smoke() -> None:
    service = VisualQualityInspectionService()
    service.record_feedback(
        inspection_id="inspection-1",
        corrected_decision=InspectionDecision.PASS,
    )
    status = await service.get_learning_status_async()
    assert status["total_feedback"] >= 1

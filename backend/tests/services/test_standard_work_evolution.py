"""Tests for Autonomous Standard Work Evolution."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from uuid import UUID

import pytest

from sqlalchemy import select

from sensei.models.a3 import A3, A3Section, A3SectionType
from sensei.models.standard_work import StandardWork, StandardWorkStatus, StandardWorkType
from sensei.models.user import User
from sensei.services.ops.kpi_metrics import KPIService, KPIValue
from sensei.services.production.standard_work_evolution import AutonomousStandardWorkEvolutionService, SYSTEM_ACTOR_ID
from sensei.services.production.standard_work_evolution_worker import StandardWorkEvolutionJobRunner


@pytest.mark.asyncio
async def test_evolution_drafts_new_revision_on_kpi_improvement(async_session) -> None:
    # System actor
    system_user = User(
        id=SYSTEM_ACTOR_ID,
        email="system@sensei.local",
        username="system",
        password_hash="x",
        first_name="System",
        last_name="User",
        status="active",
        is_superuser=True,
        email_verified=True,
    )
    async_session.add(system_user)

    # Approved StandardWork
    sw = StandardWork(
        document_number="WI-100",
        title="Work Instruction",
        description="",
        version=1,
        revision_code="A",
        document_type=StandardWorkType.WORK_INSTRUCTION,
        status=StandardWorkStatus.APPROVED,
        product_id=None,
        station_id=None,
        content_json={"steps": [{"sequence": 1, "instruction": "Do thing"}]},
        requires_training=False,
        training_duration_minutes=0,
        created_by_id=SYSTEM_ACTOR_ID,
    )
    async_session.add(sw)
    await async_session.flush()

    # A3 linking to StandardWork
    a3 = A3(
        id=uuid4(),
        a3_number="A3-1",
        title="Reduce defects",
        a3_type="problem_solving",
        status="closed",
        author_id=SYSTEM_ACTOR_ID,
        actual_completion_date=datetime(2026, 1, 10, 12, 0, 0),
        custom_fields={
            "linked_standard_work_ids": [int(sw.id)],
            "success_kpis": ["first-pass-yield"],
            "min_improvement_pct": 2.0,
            "window_days_pre": 7,
            "window_days_post": 7,
        },
    )
    a3.sections = [
        A3Section(
            id=uuid4(),
            section_type=A3SectionType.COUNTERMEASURES.value,
            section_name="Countermeasures",
            section_order=5,
            content="Add go/no-go gauge and train operators.",
            is_complete=True,
        )
    ]
    async_session.add(a3)
    await async_session.flush()

    # KPI series with improvement post-completion
    kpi = KPIService()
    kpi.record_value(
        KPIValue(
            id="pre",
            kpi_id="first-pass-yield",
            value=90.0,
            timestamp=datetime(2026, 1, 6, 10, 0, 0),
            dimensions={},
        )
    )
    kpi.record_value(
        KPIValue(
            id="post",
            kpi_id="first-pass-yield",
            value=95.0,
            timestamp=datetime(2026, 1, 12, 10, 0, 0),
            dimensions={},
        )
    )

    svc = AutonomousStandardWorkEvolutionService(kpi_service=kpi)

    decision = await svc.evaluate_and_draft(async_session, a3_id=a3.id, actor_user_id=SYSTEM_ACTOR_ID)

    assert decision.success is True
    assert len(decision.drafted_standard_work_ids) == 1

    drafted_id = decision.drafted_standard_work_ids[0]
    stmt = select(StandardWork).where(StandardWork.id == drafted_id)
    drafted = (await async_session.execute(stmt)).scalar_one()

    assert drafted.status == StandardWorkStatus.DRAFT
    assert drafted.previous_version_id == int(sw.id)
    assert drafted.version == 2
    assert drafted.created_by_id == SYSTEM_ACTOR_ID
    assert drafted.change_summary and "A3-1" in drafted.change_summary


@pytest.mark.asyncio
async def test_evolution_runner_is_idempotent_per_a3_bucket(async_session) -> None:
    system_user = User(
        id=SYSTEM_ACTOR_ID,
        email="system2@sensei.local",
        username="system2",
        password_hash="x",
        first_name="System",
        last_name="User",
        status="active",
        is_superuser=True,
        email_verified=True,
    )
    async_session.add(system_user)

    sw = StandardWork(
        document_number="WI-200",
        title="Work Instruction",
        description="",
        version=1,
        revision_code="A",
        document_type=StandardWorkType.WORK_INSTRUCTION,
        status=StandardWorkStatus.APPROVED,
        created_by_id=SYSTEM_ACTOR_ID,
        requires_training=False,
        training_duration_minutes=0,
    )
    async_session.add(sw)
    await async_session.flush()

    a3 = A3(
        id=uuid4(),
        a3_number="A3-2",
        title="Improve takt adherence",
        a3_type="problem_solving",
        status="closed",
        author_id=SYSTEM_ACTOR_ID,
        actual_completion_date=datetime(2026, 1, 10, 12, 0, 0),
        custom_fields={
            "linked_standard_work_ids": [int(sw.id)],
            "success_kpis": ["takt-adherence"],
        },
    )
    async_session.add(a3)
    await async_session.flush()

    kpi = KPIService()
    kpi.record_value(
        KPIValue(
            id="pre",
            kpi_id="takt-adherence",
            value=90.0,
            timestamp=datetime(2026, 1, 8, 10, 0, 0),
            dimensions={},
        )
    )
    kpi.record_value(
        KPIValue(
            id="post",
            kpi_id="takt-adherence",
            value=98.0,
            timestamp=datetime(2026, 1, 12, 10, 0, 0),
            dimensions={},
        )
    )

    svc = AutonomousStandardWorkEvolutionService(kpi_service=kpi)
    runner = StandardWorkEvolutionJobRunner(evolution_service=svc)

    res1 = await runner.run(db=async_session, a3_ids=[a3.id])
    assert res1.delivered_count == 1
    assert res1.cached_count == 0

    res2 = await runner.run(db=async_session, a3_ids=[a3.id])
    assert res2.delivered_count == 0
    assert res2.cached_count == 1

    # Ensure only one draft revision exists.
    stmt = select(StandardWork).where(
        StandardWork.document_number == "WI-200",
        StandardWork.status == StandardWorkStatus.DRAFT,
    )
    drafts = (await async_session.execute(stmt)).scalars().all()
    assert len(drafts) == 1

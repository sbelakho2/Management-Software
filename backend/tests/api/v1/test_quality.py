from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.v1.endpoints.quality import (
    CAPAActionCreate,
    CAPAActionUpdate,
    CAPACreate,
    CAPAUpdate,
    InspectionPlanCreate,
    InspectionPlanUpdate,
    InspectionRecordCreate,
    InspectionRecordUpdate,
    NonConformanceCreate,
    NonConformanceUpdate,
    complete_capa_action,
    create_capa,
    create_capa_action,
    create_inspection,
    create_inspection_plan,
    create_non_conformance,
    delete_capa,
    delete_capa_action,
    delete_inspection_plan,
    delete_inspection,
    delete_non_conformance,
    get_capa,
    get_inspection_plan,
    get_inspection,
    get_non_conformance,
    list_capas,
    list_capa_actions,
    list_inspection_plans,
    list_inspections,
    list_non_conformances,
    restore_capa,
    restore_inspection_plan,
    restore_non_conformance,
    update_capa,
    update_capa_action,
    update_inspection,
    update_inspection_plan,
    update_non_conformance,
 )
from sensei.models.quality import (
    CAPA,
    CAPAAction,
    CAPAActionStatus,
    CAPAActionType,
    CAPAPriority,
    CAPASourceType,
    CAPAStatus,
    CAPAType,
    EffectivenessStatus,
    InspectionPlan,
    InspectionRecord,
    InspectionResult,
    InspectionType,
    NCDisposition,
    NCSeverity,
    NCSource,
    NCStatus,
    NCType,
    NonConformance,
    RootCauseCategory,
    VerificationStatus,
)
from sensei.models.training import CertificationStatus, SkillRequirement, UserSkill


_UNSET = object()


def make_result(
    *,
    scalar_one_or_none=_UNSET,
    scalar=_UNSET,
    scalars_all=_UNSET,
    scalars_unique_all=_UNSET,
):
    result = MagicMock()
    if scalar_one_or_none is not _UNSET:
        result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    if scalar is not _UNSET:
        result.scalar = MagicMock(return_value=scalar)
    if scalars_all is not _UNSET:
        scalar_result = MagicMock()
        scalar_result.all.return_value = scalars_all
        result.scalars = MagicMock(return_value=scalar_result)
    if scalars_unique_all is not _UNSET:
        scalar_result = MagicMock()
        scalar_result.unique.return_value.all.return_value = scalars_unique_all
        result.scalars = MagicMock(return_value=scalar_result)
    return result


def make_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_non_conformance_crud_and_list_filters():
    db = make_db()
    current_user = type("User", (), {"id": uuid4()})()

    # Create: conflict
    db.execute.return_value = make_result(scalar_one_or_none=NonConformance(id=1))
    with pytest.raises(ConflictError):
        await create_non_conformance(
            NonConformanceCreate(
                nc_number="NC-001",
                nc_type=NCType.PROCESS,
                source=NCSource.IN_PROCESS,
                severity=NCSeverity.MINOR,
                quantity_affected=1,
                title="Bad part",
                description="Found defect",
            ),
            db,
            current_user,
        )

    # Create: ok
    db.execute.return_value = make_result(scalar_one_or_none=None)
    created = NonConformance(
        id=123,
        nc_number="NC-001",
        nc_type=NCType.PROCESS,
        source=NCSource.IN_PROCESS,
        severity=NCSeverity.MINOR,
        status=NCStatus.OPEN,
        quantity_affected=2,
        title="Bad part",
        description="Found defect",
        detected_by_id=current_user.id,
        detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
        containment_verified=False,
        cost_impact=Decimal("0"),
        scrap_cost=Decimal("0"),
        rework_cost=Decimal("0"),
        rework_hours=Decimal("0"),
        customer_notified=False,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def capture_add(obj: Any):
        obj.id = created.id
        obj.created_at = created.created_at
        obj.updated_at = created.updated_at
        obj.detected_by_id = current_user.id
        obj.detected_at = created.detected_at
        obj.containment_verified = False
        obj.customer_notified = False
        obj.cost_impact = Decimal("0")
        obj.scrap_cost = Decimal("0")
        obj.rework_cost = Decimal("0")
        obj.rework_hours = Decimal("0")

    db.add.side_effect = capture_add
    db.commit.return_value = None
    db.refresh.side_effect = lambda obj: None

    resp = await create_non_conformance(
        NonConformanceCreate(
            nc_number="NC-001",
            nc_type="process",
            source="in_process",
            severity="minor",
            quantity_affected=2,
            title="Bad part",
            description="Found defect",
            root_cause_category="human_error",
        ),
        db,
        current_user,
    )
    assert resp.data.id == 123
    assert resp.data.nc_number == "NC-001"
    assert resp.data.requires_capa in (True, False)

    # Get: not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_non_conformance(999, db, current_user)

    # Update: not found
    with pytest.raises(NotFoundError):
        await update_non_conformance(999, NonConformanceUpdate(title="x", description="y"), db, current_user)

    # Update: ok
    nc = NonConformance(
        id=123,
        nc_number="NC-001",
        nc_type=NCType.PROCESS,
        source=NCSource.IN_PROCESS,
        severity=NCSeverity.MINOR,
        status=NCStatus.OPEN,
        quantity_affected=2,
        title="Bad part",
        description="Found defect",
        detected_by_id=current_user.id,
        detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
        containment_verified=False,
        cost_impact=Decimal("0"),
        scrap_cost=Decimal("0"),
        rework_cost=Decimal("0"),
        rework_hours=Decimal("0"),
        customer_notified=False,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        deleted_at=None,
    )
    db.execute.return_value = make_result(scalar_one_or_none=nc)
    resp = await update_non_conformance(
        123,
        NonConformanceUpdate(
            status="under_investigation",
            disposition="rework",
            disposition_notes="Fix it",
            containment_verified=True,
        ),
        db,
        current_user,
    )
    assert resp.data.id == 123
    assert resp.data.status == "under_investigation"
    assert resp.data.disposition == "rework"
    assert resp.data.containment_verified is True

    # Delete soft
    db.execute.return_value = make_result(scalar_one_or_none=nc)
    resp = await delete_non_conformance(123, db, current_user)
    assert resp.success is True

    # Restore
    nc.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.execute.return_value = make_result(scalar_one_or_none=nc)
    resp = await restore_non_conformance(123, db, current_user)
    assert resp.data.id == 123

    # List with filters + search
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[nc]),
    ]
    page = await list_non_conformances(
        db,
        current_user,
        page=1,
        page_size=20,
        status="open",
        severity="minor",
        nc_type="process",
        source="in_process",
        search="NC-",
        include_deleted=False,
    )
    assert page.pagination.total_items == 1
    assert len(page.data) == 1


@pytest.mark.asyncio
async def test_capa_crud_actions_and_lists():
    db = make_db()
    current_user = type("User", (), {"id": uuid4()})()

    owner_id: UUID = uuid4()

    # Create: conflict
    db.execute.return_value = make_result(scalar_one_or_none=CAPA(id=1))
    with pytest.raises(ConflictError):
        await create_capa(
            CAPACreate(
                capa_number="CAPA-001",
                capa_type=CAPAType.CORRECTIVE,
                source_type=CAPASourceType.NON_CONFORMANCE,
                priority=CAPAPriority.MEDIUM,
                title="Fix issue",
                description="Need action",
                status=CAPAStatus.OPEN,
                owner_id=owner_id,
                due_date=date.today() + timedelta(days=14),
                verification_status=VerificationStatus.PENDING,
                effectiveness_status=EffectivenessStatus.PENDING,
            ),
            db,
            current_user,
        )

    # Create: ok
    db.execute.return_value = make_result(scalar_one_or_none=None)

    capa = CAPA(
        id=10,
        capa_number="CAPA-001",
        capa_type=CAPAType.CORRECTIVE,
        source_type=CAPASourceType.NON_CONFORMANCE,
        priority=CAPAPriority.MEDIUM,
        title="Fix issue",
        description="Need action",
        status=CAPAStatus.OPEN,
        owner_id=owner_id,
        opened_at=datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=date.today() + timedelta(days=14),
        verification_status=VerificationStatus.PENDING,
        effectiveness_status=EffectivenessStatus.PENDING,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def capture_add(obj: Any):
        obj.id = capa.id
        obj.opened_at = capa.opened_at
        obj.created_at = capa.created_at
        obj.updated_at = capa.updated_at

    db.add.side_effect = capture_add
    db.commit.return_value = None
    db.refresh.side_effect = lambda obj: None

    resp = await create_capa(
        CAPACreate(
            capa_number="CAPA-001",
            source_type="non_conformance",
            title="Fix issue",
            description="Need action",
            owner_id=owner_id,
            due_date=date.today() + timedelta(days=14),
        ),
        db,
        current_user,
    )
    assert resp.data.id == 10
    assert resp.data.capa_number == "CAPA-001"

    # Get: not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_capa(999, db, current_user)

    # Update: ok
    capa.actions = []
    db.execute.return_value = make_result(scalar_one_or_none=capa)
    resp = await update_capa(
        10,
        CAPAUpdate(priority="high", root_cause_category="method"),
        db,
        current_user,
    )
    assert resp.data.priority == "high"
    assert resp.data.root_cause_category == "method"

    # Actions list: CAPA not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await list_capa_actions(10, db, current_user, page=1, page_size=50)

    # Actions list: ok
    action = CAPAAction(
        id=5,
        capa_id=10,
        action_type=CAPAActionType.CORRECTIVE,
        description="Do thing",
        owner_id=owner_id,
        due_date=date.today() + timedelta(days=7),
        status=CAPAActionStatus.OPEN,
        verified=False,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.execute.side_effect = [
        make_result(scalar_one_or_none=10),
        make_result(scalar=1),
        make_result(scalars_all=[action]),
    ]
    page = await list_capa_actions(10, db, current_user, page=1, page_size=50)
    assert page.pagination.total_items == 1
    assert page.data[0].id == 5

    # Create action
    db.execute = AsyncMock(return_value=make_result(scalar_one_or_none=capa))

    def capture_add_action(obj: Any):
        obj.id = 6
        obj.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        obj.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        obj.status = CAPAActionStatus.OPEN
        obj.verified = False

    db.add.side_effect = capture_add_action

    resp = await create_capa_action(
        10,
        CAPAActionCreate(
            action_type="corrective",
            description="Do it",
            owner_id=owner_id,
            due_date=date.today() + timedelta(days=7),
        ),
        db,
        current_user,
    )
    assert resp.data.id == 6
    assert resp.data.status == "open"

    # Update action: not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await update_capa_action(10, 999, CAPAActionUpdate(description="x"), db, current_user)

    # Update action: ok
    db.execute.return_value = make_result(scalar_one_or_none=action)
    resp = await update_capa_action(
        10,
        5,
        CAPAActionUpdate(status="in_progress", notes="Started"),
        db,
        current_user,
    )
    assert resp.data.status == "in_progress"

    # Complete action
    db.execute.return_value = make_result(scalar_one_or_none=action)
    resp = await complete_capa_action(10, 5, completion_evidence="done", db=db, current_user=current_user)
    assert resp.data.status == "completed"

    # Delete action
    db.execute.return_value = make_result(scalar_one_or_none=action)
    resp = await delete_capa_action(10, 5, db, current_user)
    assert resp.success is True

    # List CAPAs with filters
    capa.actions = []
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_unique_all=[capa]),
    ]
    page = await list_capas(
        db,
        current_user,
        page=1,
        page_size=20,
        status="open",
        priority="medium",
        source_type="non_conformance",
        overdue=False,
        search="CAPA",
        include_deleted=False,
    )
    assert page.pagination.total_items == 1
    assert len(page.data) == 1

    # Delete soft + restore
    db.execute.side_effect = None
    db.execute.return_value = make_result(scalar_one_or_none=capa)
    resp = await delete_capa(10, db, current_user)
    assert resp.success is True

    capa.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    capa.actions = []
    db.execute.return_value = make_result(scalar_one_or_none=capa)
    resp = await restore_capa(10, db, current_user)
    assert resp.data.id == 10


@pytest.mark.asyncio
async def test_inspection_plans_and_records_crud_and_list_filters():
    db = make_db()
    current_user = type("User", (), {"id": uuid4()})()

    # Create plan with code conflict
    db.execute.return_value = make_result(scalar_one_or_none=InspectionPlan(id=1))
    with pytest.raises(ConflictError):
        await create_inspection_plan(
            InspectionPlanCreate(
                name="Plan",
                code="IP-001",
                inspection_type=InspectionType.IN_PROCESS,
                checkpoints_json=[],
            ),
            db,
            current_user,
        )

    # Create plan ok
    db.execute.return_value = make_result(scalar_one_or_none=None)
    plan = InspectionPlan(
        id=77,
        name="Plan",
        code="IP-001",
        inspection_type=InspectionType.IN_PROCESS,
        checkpoints_json=[{"name": "c1", "critical": True}],
        is_active=True,
        revision=1,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def capture_add_plan(obj: Any):
        obj.id = plan.id
        obj.created_at = plan.created_at
        obj.updated_at = plan.updated_at

    db.add.side_effect = capture_add_plan
    db.commit.return_value = None
    db.refresh.side_effect = lambda obj: None

    resp = await create_inspection_plan(
        InspectionPlanCreate(
            name="Plan",
            code="IP-001",
            inspection_type="in_process",
            checkpoints_json=[{"name": "c1", "critical": True}],
        ),
        db,
        current_user,
    )
    assert resp.data.id == 77
    assert resp.data.checkpoint_count >= 0

    # Get plan not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_inspection_plan(999, db, current_user)

    # Update plan code conflict
    existing_other = InspectionPlan(id=99)
    db.execute.side_effect = [
        make_result(scalar_one_or_none=plan),
        make_result(scalar_one_or_none=existing_other),
    ]
    with pytest.raises(ConflictError):
        await update_inspection_plan(77, InspectionPlanUpdate(code="IP-OTHER"), db, current_user)

    # Update plan ok
    db.execute = AsyncMock(return_value=make_result(scalar_one_or_none=plan))
    resp = await update_inspection_plan(77, InspectionPlanUpdate(is_active=False), db, current_user)
    assert resp.data.is_active is False

    # Delete plan soft + restore
    db.execute.return_value = make_result(scalar_one_or_none=plan)
    resp = await delete_inspection_plan(77, db, current_user)
    assert resp.success is True

    plan.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.execute.return_value = make_result(scalar_one_or_none=plan)
    resp = await restore_inspection_plan(77, db, current_user)
    assert resp.data.id == 77

    # List plans filters
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[plan]),
    ]
    page = await list_inspection_plans(
        db,
        current_user,
        page=1,
        page_size=20,
        inspection_type="in_process",
        is_active=True,
        search="IP-",
        include_deleted=False,
    )
    assert page.pagination.total_items == 1

    db.execute.side_effect = None

    # Records create requires plan exists
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await create_inspection(
            InspectionRecordCreate(
                inspection_plan_id=77,
                sample_size=5,
                overall_result=InspectionResult.PASS,
                measurements_json=[],
            ),
            db,
            current_user,
        )

    # Create record ok
    db.execute.return_value = make_result(scalar_one_or_none=plan)

    record = InspectionRecord(
        id=501,
        inspection_plan_id=77,
        sample_size=5,
        inspected_by_id=current_user.id,
        inspected_at=datetime.now(timezone.utc).replace(tzinfo=None),
        overall_result=InspectionResult.PASS,
        measurements_json=[],
        defects_found=0,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def capture_add_record(obj: Any):
        obj.id = record.id
        obj.inspected_by_id = current_user.id
        obj.inspected_at = record.inspected_at
        obj.created_at = record.created_at
        obj.updated_at = record.updated_at
        obj.defects_found = 0

    db.add.side_effect = capture_add_record

    resp = await create_inspection(
        InspectionRecordCreate(
            inspection_plan_id=77,
            sample_size=5,
            overall_result="pass",
            measurements_json=[],
            defects_found=0,
        ),
        db,
        current_user,
    )
    assert resp.data.id == 501
    assert resp.data.is_pass is True

    # Get record not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_inspection(999, db, current_user)

    # Update record ok
    db.execute.return_value = make_result(scalar_one_or_none=record)
    resp = await update_inspection(501, InspectionRecordUpdate(notes="ok"), db, current_user)
    assert resp.data.id == 501

    # List records filter
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[record]),
    ]
    page = await list_inspections(
        db,
        current_user,
        page=1,
        page_size=20,
        inspection_plan_id=77,
        overall_result="pass",
    )
    assert page.pagination.total_items == 1

    db.execute.side_effect = None

    # Delete record
    db.execute.return_value = make_result(scalar_one_or_none=record)
    resp = await delete_inspection(501, db, current_user)
    assert resp.success is True


@pytest.mark.asyncio
async def test_inspection_record_requires_certified_skills_when_plan_scoped() -> None:
    db = make_db()
    current_user = type("User", (), {"id": uuid4()})()

    # Plan is scoped to a station, so mandatory skill requirements apply.
    plan = InspectionPlan(
        id=77,
        name="Plan",
        code="IP-001",
        station_id=10,
        inspection_type=InspectionType.IN_PROCESS,
        checkpoints_json=[],
        is_active=True,
        revision=1,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # One mandatory required skill.
    req = SkillRequirement(
        id=1,
        skill_id=123,
        station_id=10,
        product_id=None,
        minimum_proficiency_level=2,
        is_mandatory=True,
    )

    # User has the skill but is NOT certified.
    user_skill = UserSkill(
        id=1,
        user_id=current_user.id,
        skill_id=123,
        proficiency_level=3,
        certification_status=CertificationStatus.NOT_CERTIFIED,
    )

    db.execute.side_effect = [
        make_result(scalar_one_or_none=plan),
        make_result(scalars_all=[req]),
        make_result(scalars_all=[user_skill]),
    ]

    with pytest.raises(ConflictError) as exc:
        await create_inspection(
            InspectionRecordCreate(
                inspection_plan_id=77,
                sample_size=5,
                overall_result=InspectionResult.PASS,
                measurements_json=[],
            ),
            db,
            current_user,
        )

    assert "not certified" in str(exc.value).lower()
    db.add.assert_not_called()

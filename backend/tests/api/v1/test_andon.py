"""Comprehensive tests for Andon API endpoints."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.v1.endpoints.andon import (
    AndonEventCreate,
    AndonEventUpdate,
    AndonAcknowledge,
    AndonResolve,
    AndonEscalate,
    AndonEscalationCreate,
    AndonEscalationUpdate,
    RecurrencePatternCreate,
    list_andon_events,
    create_andon_event,
    get_andon_event,
    update_andon_event,
    delete_andon_event,
    restore_andon_event,
    acknowledge_andon_event,
    start_andon_progress,
    resolve_andon_event,
    cancel_andon_event,
    escalate_andon_event,
    list_event_escalations,
    create_escalation,
    update_escalation,
    delete_escalation,
    list_recurrence_patterns,
    get_recurrence_pattern,
    create_recurrence_pattern,
    delete_recurrence_pattern,
    get_dashboard_stats,
)
from sensei.models.andon import (
    AndonEvent,
    AndonType,
    AndonSeverity,
    AndonStatus,
    EscalationLevel,
    AndonEscalation,
    ResponseStatus,
    AndonRecurrencePattern,
)


_NOT_SET = object()


def make_result(
    scalar: Any = _NOT_SET,
    scalar_one_or_none: Any = _NOT_SET,
    scalars_all: list = None,
    all_rows: list = None,
):
    """Create a mock SQLAlchemy result object."""
    result = MagicMock()
    if scalar is not _NOT_SET:
        result.scalar.return_value = scalar
    if scalar_one_or_none is not _NOT_SET:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    if scalars_all is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = scalars_all
        result.scalars.return_value = scalars_mock
    if all_rows is not None:
        result.all.return_value = all_rows
    return result


def make_db():
    """Create a mock async DB session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


def make_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    return user


@pytest.mark.asyncio
async def test_andon_event_crud_and_workflow():
    """Test Andon event CRUD operations and workflow transitions."""
    db = make_db()
    current_user = make_user()
    now = datetime.utcnow()

    # Create an Andon event
    event = AndonEvent(
        id=1,
        event_number="AND-2026-0001",
        andon_type=AndonType.QUALITY,
        severity=AndonSeverity.RED,
        station_id=10,
        product_id=5,
        work_order_id=100,
        symptom="Defective weld detected",
        description="Weld joint shows porosity",
        affected_quantity=5,
        status=AndonStatus.OPEN,
        escalation_level=EscalationLevel.NONE,
        reported_by_id=current_user.id,
        reported_at=now,
        is_recurrence=False,
        recurrence_count=0,
        created_at=now,
        updated_at=now,
    )

    # Test create - check duplicate first, then recurrence check
    db.execute.side_effect = [
        make_result(scalar_one_or_none=None),  # duplicate check
        make_result(scalar_one_or_none=None),  # recurrence pattern check
    ]

    def capture_add(obj: Any):
        obj.id = event.id
        obj.reported_at = now
        obj.created_at = now
        obj.updated_at = now
        # Set recurrence fields if they're AndonEvent
        if hasattr(obj, 'is_recurrence'):
            obj.is_recurrence = False
            obj.recurrence_count = 0

    db.add.side_effect = capture_add

    resp = await create_andon_event(
        AndonEventCreate(
            event_number="AND-2026-0001",
            andon_type="quality",
            severity="red",
            station_id=10,
            product_id=5,
            work_order_id=100,
            symptom="Defective weld detected",
            description="Weld joint shows porosity",
            affected_quantity=5,
        ),
        db,
        current_user,
    )
    assert resp.data.event_number == "AND-2026-0001"
    assert resp.data.severity == "red"
    assert resp.data.andon_type == "quality"

    db.add.side_effect = None
    db.execute.side_effect = None

    # Test conflict on duplicate event number
    db.execute.return_value = make_result(scalar_one_or_none=event)
    with pytest.raises(ConflictError):
        await create_andon_event(
            AndonEventCreate(
                event_number="AND-2026-0001",
                andon_type="quality",
                severity="yellow",
                station_id=10,
                symptom="Another issue",
            ),
            db,
            current_user,
        )

    # Test get event
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await get_andon_event(1, db, current_user)
    assert resp.data.id == 1
    assert resp.data.is_critical is True  # RED severity

    # Test get not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_andon_event(999, db, current_user)

    # Test update event
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await update_andon_event(
        1,
        AndonEventUpdate(description="Updated description", downtime_minutes=30),
        db,
        current_user,
    )
    assert resp.data.id == 1

    # Test list events with filters
    db.execute.side_effect = [
        make_result(scalar=2),
        make_result(scalars_all=[event]),
    ]
    page = await list_andon_events(
        db,
        current_user,
        page=1,
        page_size=20,
        station_id=10,
        severity="red",
        is_open=True,
        search="weld",
    )
    assert page.pagination.total_items == 2

    db.execute.side_effect = None

    # =========================================================================
    # Workflow tests
    # =========================================================================

    # Acknowledge event
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await acknowledge_andon_event(1, AndonAcknowledge(notes="On my way"), db, current_user)
    assert resp.data.id == 1

    # Cannot acknowledge if not OPEN
    event.status = AndonStatus.ACKNOWLEDGED
    db.execute.return_value = make_result(scalar_one_or_none=event)
    with pytest.raises(ConflictError):
        await acknowledge_andon_event(1, AndonAcknowledge(), db, current_user)

    # Start progress
    event.status = AndonStatus.ACKNOWLEDGED
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await start_andon_progress(1, db, current_user)
    assert resp.data.id == 1

    # Resolve event
    event.status = AndonStatus.IN_PROGRESS
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await resolve_andon_event(
        1,
        AndonResolve(
            resolution_notes="Fixed the weld parameters",
            resolution_category="Process Adjustment",
            downtime_minutes=45,
            root_cause_category="Equipment",
        ),
        db,
        current_user,
    )
    assert resp.data.id == 1

    # Cannot resolve already resolved
    event.status = AndonStatus.RESOLVED
    db.execute.return_value = make_result(scalar_one_or_none=event)
    with pytest.raises(ConflictError):
        await resolve_andon_event(
            1, AndonResolve(resolution_notes="Again"), db, current_user
        )

    # Test cancel
    event.status = AndonStatus.OPEN
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await cancel_andon_event(1, db, current_user)
    assert resp.data.id == 1

    # Cannot cancel resolved
    event.status = AndonStatus.RESOLVED
    db.execute.return_value = make_result(scalar_one_or_none=event)
    with pytest.raises(ConflictError):
        await cancel_andon_event(1, db, current_user)

    # Test soft delete
    event.status = AndonStatus.OPEN
    event.deleted_at = None
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await delete_andon_event(1, db, current_user)
    assert resp.success is True

    # Test restore
    event.deleted_at = now
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await restore_andon_event(1, db, current_user)
    assert resp.data.id == 1


@pytest.mark.asyncio
async def test_andon_escalation_workflow():
    """Test Andon escalation CRUD and workflow."""
    db = make_db()
    current_user = make_user()
    escalated_user_id = uuid4()
    now = datetime.utcnow()

    event = AndonEvent(
        id=1,
        event_number="AND-2026-0002",
        andon_type=AndonType.EQUIPMENT,
        severity=AndonSeverity.RED,
        station_id=10,
        symptom="Machine breakdown",
        status=AndonStatus.OPEN,
        escalation_level=EscalationLevel.NONE,
        reported_by_id=current_user.id,
        reported_at=now,
        is_recurrence=False,
        recurrence_count=0,
        created_at=now,
        updated_at=now,
        escalations=[],
    )

    # Escalate via event endpoint
    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await escalate_andon_event(
        1,
        AndonEscalate(
            escalation_level="level_1",
            escalated_to_user_id=escalated_user_id,
            notes="Need supervisor",
        ),
        db,
        current_user,
    )
    assert resp.data.id == 1

    # Create escalation directly
    escalation = AndonEscalation(
        id=10,
        andon_event_id=1,
        escalation_level=EscalationLevel.LEVEL_1,
        escalated_to_user_id=escalated_user_id,
        escalated_at=now,
        response_status=ResponseStatus.PENDING,
        responded_at=None,
        created_at=now,
        updated_at=now,
    )

    # Check conflict on same level
    event.escalations = [escalation]
    db.execute.return_value = make_result(scalar_one_or_none=event)
    with pytest.raises(ConflictError):
        await escalate_andon_event(
            1,
            AndonEscalate(
                escalation_level="level_1",
                escalated_to_user_id=escalated_user_id,
            ),
            db,
            current_user,
        )

    # List escalations for event
    event.escalations = []
    db.execute.side_effect = [
        make_result(scalar_one_or_none=event),
        make_result(scalars_all=[escalation]),
    ]
    resp = await list_event_escalations(1, db, current_user)
    assert len(resp.data) == 1
    assert resp.data[0].escalation_level == "level_1"

    db.execute.side_effect = None

    # Create escalation directly
    db.execute.side_effect = [
        make_result(scalar_one_or_none=event),  # event check
        make_result(scalar_one_or_none=None),   # no existing at level
    ]

    def capture_esc(obj: Any):
        obj.id = 11
        obj.escalated_at = now
        obj.created_at = now
        obj.updated_at = now

    db.add.side_effect = capture_esc

    resp = await create_escalation(
        AndonEscalationCreate(
            andon_event_id=1,
            escalation_level="level_2",
            escalated_to_user_id=escalated_user_id,
        ),
        db,
        current_user,
    )
    assert resp.data.escalation_level == "level_2"

    db.add.side_effect = None
    db.execute.side_effect = None

    # Update escalation (respond)
    db.execute.return_value = make_result(scalar_one_or_none=escalation)
    resp = await update_escalation(
        10,
        AndonEscalationUpdate(
            response_status="acknowledged",
            response_notes="Acknowledged by supervisor",
        ),
        db,
        current_user,
    )
    assert resp.data.id == 10

    # Delete escalation
    db.execute.return_value = make_result(scalar_one_or_none=escalation)
    resp = await delete_escalation(10, db, current_user)
    assert resp.success is True


@pytest.mark.asyncio
async def test_andon_recurrence_patterns():
    """Test Andon recurrence pattern CRUD and tracking."""
    db = make_db()
    current_user = make_user()
    now = datetime.utcnow()

    pattern = AndonRecurrencePattern(
        id=1,
        station_id=10,
        andon_type=AndonType.QUALITY,
        symptom_pattern="Weld porosity",
        occurrence_count=2,
        first_occurrence_at=now - timedelta(days=3),
        last_occurrence_at=now,
        window_days=7,
        escalation_threshold=3,
        escalated_to_a3=False,
        a3_id=None,
        created_at=now,
        updated_at=now,
    )

    # List patterns
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[pattern]),
    ]
    page = await list_recurrence_patterns(
        db, current_user, page=1, page_size=20, station_id=10
    )
    assert page.pagination.total_items == 1
    assert page.data[0].occurrence_count == 2

    db.execute.side_effect = None

    # Get pattern
    db.execute.return_value = make_result(scalar_one_or_none=pattern)
    resp = await get_recurrence_pattern(1, db, current_user)
    assert resp.data.symptom_pattern == "Weld porosity"

    # Get not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_recurrence_pattern(999, db, current_user)

    # Create pattern
    db.execute.return_value = make_result(scalar_one_or_none=None)

    def capture_pattern(obj: Any):
        obj.id = 2
        obj.occurrence_count = 1
        obj.first_occurrence_at = now
        obj.last_occurrence_at = now
        obj.created_at = now
        obj.updated_at = now
        obj.escalated_to_a3 = False

    db.add.side_effect = capture_pattern

    resp = await create_recurrence_pattern(
        RecurrencePatternCreate(
            station_id=20,
            andon_type="equipment",
            symptom_pattern="Bearing noise",
            window_days=7,
            escalation_threshold=3,
        ),
        db,
        current_user,
    )
    assert resp.data.station_id == 20

    db.add.side_effect = None

    # Conflict on duplicate pattern
    db.execute.return_value = make_result(scalar_one_or_none=pattern)
    with pytest.raises(ConflictError):
        await create_recurrence_pattern(
            RecurrencePatternCreate(
                station_id=10,
                andon_type="quality",
                symptom_pattern="Weld porosity",
            ),
            db,
            current_user,
        )

    # Delete pattern
    db.execute.return_value = make_result(scalar_one_or_none=pattern)
    resp = await delete_recurrence_pattern(1, db, current_user)
    assert resp.success is True

    # Delete not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await delete_recurrence_pattern(999, db, current_user)


@pytest.mark.asyncio
async def test_andon_dashboard_stats():
    """Test Andon dashboard statistics."""
    db = make_db()
    current_user = make_user()

    # Mock all stat queries
    db.execute.side_effect = [
        make_result(scalar=5),   # total_open
        make_result(scalar=2),   # total_red
        make_result(scalar=2),   # total_yellow
        make_result(scalar=1),   # total_blue
        make_result(all_rows=[(AndonType.QUALITY, 3), (AndonType.EQUIPMENT, 2)]),  # by type
        make_result(all_rows=[(10, 3), (20, 2)]),  # by station
    ]

    resp = await get_dashboard_stats(db, current_user, days=7)
    assert resp.data.total_open == 5
    assert resp.data.total_red == 2
    assert resp.data.total_yellow == 2
    assert resp.data.total_blue == 1
    assert resp.data.events_by_type["quality"] == 3
    assert resp.data.events_by_station[10] == 3


@pytest.mark.asyncio
async def test_andon_list_filters_comprehensive():
    """Test all list filter combinations."""
    db = make_db()
    current_user = make_user()
    now = datetime.utcnow()

    event = AndonEvent(
        id=1,
        event_number="AND-2026-0003",
        andon_type=AndonType.MATERIAL,
        severity=AndonSeverity.BLUE,
        station_id=15,
        product_id=None,
        work_order_id=None,
        symptom="Material shortage",
        status=AndonStatus.OPEN,
        escalation_level=EscalationLevel.NONE,
        reported_by_id=current_user.id,
        reported_at=now,
        is_recurrence=False,
        recurrence_count=0,
        created_at=now,
        updated_at=now,
    )

    # Filter by andon_type
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[event]),
    ]
    page = await list_andon_events(
        db, current_user, page=1, page_size=20, andon_type="material"
    )
    assert page.pagination.total_items == 1

    db.execute.side_effect = None

    # Filter by status
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[event]),
    ]
    page = await list_andon_events(
        db, current_user, page=1, page_size=20, status="open"
    )
    assert page.pagination.total_items == 1

    db.execute.side_effect = None

    # Filter is_open=False (closed events)
    db.execute.side_effect = [
        make_result(scalar=0),
        make_result(scalars_all=[]),
    ]
    page = await list_andon_events(
        db, current_user, page=1, page_size=20, is_open=False
    )
    assert page.pagination.total_items == 0

    db.execute.side_effect = None

    # Include deleted
    db.execute.side_effect = [
        make_result(scalar=1),
        make_result(scalars_all=[event]),
    ]
    page = await list_andon_events(
        db, current_user, page=1, page_size=20, include_deleted=True
    )
    assert page.pagination.total_items == 1


@pytest.mark.asyncio
async def test_andon_event_computed_properties():
    """Test computed properties on AndonEvent response."""
    db = make_db()
    current_user = make_user()
    now = datetime.utcnow()
    reported = now - timedelta(minutes=30)

    event = AndonEvent(
        id=1,
        event_number="AND-2026-0004",
        andon_type=AndonType.SAFETY,
        severity=AndonSeverity.RED,
        station_id=5,
        symptom="Safety concern",
        status=AndonStatus.ACKNOWLEDGED,
        escalation_level=EscalationLevel.NONE,
        reported_by_id=current_user.id,
        reported_at=reported,
        acknowledged_by_id=current_user.id,
        acknowledged_at=reported + timedelta(minutes=5),
        resolved_by_id=None,
        resolved_at=None,
        is_recurrence=False,
        recurrence_count=0,
        created_at=reported,
        updated_at=now,
    )

    db.execute.return_value = make_result(scalar_one_or_none=event)
    resp = await get_andon_event(1, db, current_user)

    # Verify computed properties
    assert resp.data.is_open is True
    assert resp.data.is_critical is True
    assert resp.data.response_time_minutes == 5
    assert resp.data.resolution_time_minutes is None  # Not resolved
    assert resp.data.elapsed_time_minutes >= 30


@pytest.mark.asyncio
async def test_andon_escalation_response_time():
    """Test escalation response time calculation."""
    db = make_db()
    current_user = make_user()
    escalated_at = datetime.utcnow() - timedelta(minutes=20)
    responded_at = datetime.utcnow() - timedelta(minutes=5)

    escalation = AndonEscalation(
        id=1,
        andon_event_id=1,
        escalation_level=EscalationLevel.LEVEL_1,
        escalated_to_user_id=uuid4(),
        escalated_at=escalated_at,
        response_status=ResponseStatus.ACKNOWLEDGED,
        responded_at=responded_at,
        created_at=escalated_at,
        updated_at=responded_at,
    )

    event = AndonEvent(
        id=1,
        event_number="AND-2026-0005",
        andon_type=AndonType.PROCESS,
        severity=AndonSeverity.YELLOW,
        station_id=5,
        symptom="Process deviation",
        status=AndonStatus.ESCALATED,
        escalation_level=EscalationLevel.LEVEL_1,
        reported_by_id=current_user.id,
        reported_at=escalated_at,
        is_recurrence=False,
        recurrence_count=0,
        created_at=escalated_at,
        updated_at=responded_at,
    )

    db.execute.side_effect = [
        make_result(scalar_one_or_none=event),
        make_result(scalars_all=[escalation]),
    ]

    resp = await list_event_escalations(1, db, current_user)
    assert len(resp.data) == 1
    assert resp.data[0].response_time_minutes == 15  # 20 - 5 = 15 minutes

"""Tests for A3 API endpoints.

Tests cover:
- A3 CRUD operations
- A3 workflow transitions (start, review, approve, etc.)
- A3 sections management
- Query endpoints
"""

from __future__ import annotations

import pytest
from datetime import datetime, date, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sensei.api.v1.endpoints.a3 import (
    router,
    create_a3,
    get_a3,
    list_a3s,
    update_a3,
    delete_a3,
    start_a3,
    submit_for_review,
    review_a3,
    approve_a3,
    reject_a3,
    implement_a3,
    close_a3,
    cancel_a3,
    add_section,
    update_section,
    complete_section,
    reopen_section,
    add_section_comment,
    delete_section,
    get_a3_by_number,
    get_my_a3s,
    get_pending_review,
    A3Create,
    A3Update,
    A3ReviewData,
    A3ApprovalData,
    SectionCreate,
    SectionUpdate,
    SectionComment,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.a3 import (
    A3,
    A3Section,
    A3Type,
    A3Status,
    A3Priority,
    A3SectionType,
    A3_SECTION_TEMPLATES,
)


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock current user."""
    user = MagicMock()
    user.id = uuid4()
    return user


def make_result(
    scalar_one_or_none=None,
    scalars_all=None,
    scalar_one=None,
):
    """Create a mock result object."""
    result = MagicMock()
    if scalar_one_or_none is not None or scalar_one_or_none is None:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    if scalars_all is not None:
        scalars_result = MagicMock()
        scalars_result.all.return_value = scalars_all
        result.scalars.return_value = scalars_result
    if scalar_one is not None:
        result.scalar_one.return_value = scalar_one
    return result


def create_mock_a3(
    a3_id=None,
    a3_number="A3-0001",
    title="Test A3",
    a3_type=A3Type.PROBLEM_SOLVING.value,
    status=A3Status.DRAFT.value,
    author_id=None,
    sponsor_id=None,
    coach_id=None,
    priority=A3Priority.MEDIUM.value,
    department="Engineering",
    sections=None,
    target_completion_date=None,
    **kwargs,
):
    """Create a mock A3 object."""
    a3 = MagicMock(spec=A3)
    a3.id = a3_id or uuid4()
    a3.a3_number = a3_number
    a3.title = title
    a3.a3_type = a3_type
    a3.status = status
    a3.author_id = author_id
    a3.sponsor_id = sponsor_id
    a3.coach_id = coach_id
    a3.priority = priority
    a3.department = department
    a3.area = kwargs.get("area")
    a3.related_entity_type = kwargs.get("related_entity_type")
    a3.related_entity_id = kwargs.get("related_entity_id")
    a3.team_members = kwargs.get("team_members")
    a3.started_date = kwargs.get("started_date")
    a3.target_completion_date = target_completion_date
    a3.actual_completion_date = kwargs.get("actual_completion_date")
    a3.last_review_date = kwargs.get("last_review_date")
    a3.review_notes = kwargs.get("review_notes")
    a3.approved_by_id = kwargs.get("approved_by_id")
    a3.approved_date = kwargs.get("approved_date")
    a3.progress_percentage = kwargs.get("progress_percentage", 0)
    a3.version = kwargs.get("version", 1)
    a3.tags = kwargs.get("tags")
    a3.custom_fields = kwargs.get("custom_fields")
    a3.summary = kwargs.get("summary")
    a3.lessons_learned = kwargs.get("lessons_learned")
    a3.is_yokoten_candidate = kwargs.get("is_yokoten_candidate", False)
    a3.yokoten_areas = kwargs.get("yokoten_areas")
    a3.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    a3.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    a3.is_deleted = kwargs.get("is_deleted", False)
    a3.deleted_at = kwargs.get("deleted_at")
    a3.is_open = status not in [A3Status.CLOSED.value, A3Status.CANCELLED.value]
    a3.is_overdue = False
    a3.sections = sections or []
    a3.update_progress = MagicMock()
    return a3


def create_mock_section(
    section_id=None,
    a3_id=None,
    section_type=A3SectionType.BACKGROUND.value,
    section_name="Background",
    section_order=1,
    content=None,
    structured_content=None,
    is_complete=False,
    completed_at=None,
    completed_by_id=None,
    guidance=None,
    attachments=None,
    comments=None,
    version=1,
):
    """Create a mock A3Section object."""
    section = MagicMock(spec=A3Section)
    section.id = section_id or uuid4()
    section.a3_id = a3_id or uuid4()
    section.section_type = section_type
    section.section_name = section_name
    section.section_order = section_order
    section.content = content
    section.structured_content = structured_content
    section.is_complete = is_complete
    section.completed_at = completed_at
    section.completed_by_id = completed_by_id
    section.guidance = guidance
    section.attachments = attachments
    section.comments = comments
    section.version = version
    section.created_at = datetime.now(timezone.utc)
    section.updated_at = datetime.now(timezone.utc)
    return section


# =============================================================================
# A3 CRUD Tests
# =============================================================================


class TestA3CRUD:
    """Tests for A3 CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_a3_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test successful A3 creation."""
        data = A3Create(
            a3_number="A3-0001",
            title="Problem Solving A3",
            a3_type=A3Type.PROBLEM_SOLVING,
            priority=A3Priority.HIGH,
            department="Operations",
            create_default_sections=False,
        )

        # Mock no duplicate
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        # Capture created A3
        captured_a3 = None
        def capture_add(obj):
            nonlocal captured_a3
            if isinstance(obj, type) or hasattr(obj, "a3_number"):
                captured_a3 = obj
        mock_db.add = capture_add

        async def mock_refresh(obj, *args):
            obj.id = uuid4()
            obj.sections = []
            obj.progress_percentage = 0
            obj.version = 1
            obj.is_yokoten_candidate = False
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await create_a3(data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 document created successfully"
        assert response.data.a3_number == "A3-0001"
        assert response.data.title == "Problem Solving A3"
        assert response.data.status == "draft"

    @pytest.mark.asyncio
    async def test_create_a3_duplicate_number(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test A3 creation fails on duplicate number."""
        data = A3Create(
            a3_number="A3-0001",
            title="Test A3",
        )

        existing = create_mock_a3(a3_number="A3-0001")
        mock_db.execute.return_value = make_result(scalar_one_or_none=existing)

        with pytest.raises(ConflictError):
            await create_a3(data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_a3_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting A3 by ID."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, title="Retrieved A3")
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        response = await get_a3(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.data.id == a3_id
        assert response.data.title == "Retrieved A3"

    @pytest.mark.asyncio
    async def test_get_a3_not_found(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting non-existent A3."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        with pytest.raises(NotFoundError):
            await get_a3(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_a3s(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test listing A3 documents."""
        a3s = [
            create_mock_a3(title="A3 One"),
            create_mock_a3(title="A3 Two"),
        ]

        # Count and data queries
        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=a3s),
        ]

        response = await list_a3s(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.total_items == 2

    @pytest.mark.asyncio
    async def test_list_a3s_filter_by_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test filtering A3s by status."""
        a3s = [create_mock_a3(status=A3Status.DRAFT.value)]

        mock_db.execute.side_effect = [
            make_result(scalar_one=1),
            make_result(scalars_all=a3s),
        ]

        response = await list_a3s(mock_db, mock_user, status=A3Status.DRAFT, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_update_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test updating an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, title="Original Title")
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        data = A3Update(title="Updated Title", summary="New summary")

        async def mock_refresh(obj, *args):
            obj.title = "Updated Title"
            obj.summary = "New summary"
        mock_db.refresh = mock_refresh

        response = await update_a3(a3_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 document updated successfully"

    @pytest.mark.asyncio
    async def test_delete_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test soft deleting an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        response = await delete_a3(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 document deleted successfully"


# =============================================================================
# A3 Workflow Tests
# =============================================================================


class TestA3Workflow:
    """Tests for A3 workflow transitions."""

    @pytest.mark.asyncio
    async def test_start_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test starting an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.DRAFT.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        async def mock_refresh(obj, *args):
            obj.status = A3Status.IN_PROGRESS.value
            obj.started_date = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await start_a3(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 started"

    @pytest.mark.asyncio
    async def test_start_a3_invalid_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test starting A3 that's already in progress."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.IN_PROGRESS.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        with pytest.raises(ConflictError):
            await start_a3(a3_id, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_submit_for_review(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test submitting A3 for review."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.IN_PROGRESS.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        async def mock_refresh(obj, *args):
            obj.status = A3Status.REVIEW.value
        mock_db.refresh = mock_refresh

        response = await submit_for_review(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 submitted for review"

    @pytest.mark.asyncio
    async def test_review_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test adding review notes."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.REVIEW.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        data = A3ReviewData(review_notes="Looks good, minor changes needed")

        async def mock_refresh(obj, *args):
            obj.review_notes = "Looks good, minor changes needed"
            obj.last_review_date = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await review_a3(a3_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 reviewed"

    @pytest.mark.asyncio
    async def test_approve_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test approving an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.REVIEW.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        data = A3ApprovalData(notes="Approved for implementation")

        async def mock_refresh(obj, *args):
            obj.status = A3Status.APPROVED.value
            obj.approved_by_id = mock_user.id
            obj.approved_date = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await approve_a3(a3_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 approved"

    @pytest.mark.asyncio
    async def test_approve_a3_invalid_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test approving A3 not in review status."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.DRAFT.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        data = A3ApprovalData()

        with pytest.raises(ConflictError):
            await approve_a3(a3_id, data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_reject_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test rejecting an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.REVIEW.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        data = A3ReviewData(review_notes="Needs more data")

        async def mock_refresh(obj, *args):
            obj.status = A3Status.IN_PROGRESS.value
        mock_db.refresh = mock_refresh

        response = await reject_a3(a3_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 returned for revision"

    @pytest.mark.asyncio
    async def test_implement_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test marking A3 as implemented."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.APPROVED.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        async def mock_refresh(obj, *args):
            obj.status = A3Status.IMPLEMENTED.value
        mock_db.refresh = mock_refresh

        response = await implement_a3(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 implemented"

    @pytest.mark.asyncio
    async def test_implement_a3_invalid_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test implementing A3 not in approved status."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.DRAFT.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        with pytest.raises(ConflictError):
            await implement_a3(a3_id, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_close_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test closing an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.IMPLEMENTED.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        async def mock_refresh(obj, *args):
            obj.status = A3Status.CLOSED.value
            obj.actual_completion_date = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await close_a3(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 closed"

    @pytest.mark.asyncio
    async def test_cancel_a3(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test cancelling an A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.IN_PROGRESS.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        async def mock_refresh(obj, *args):
            obj.status = A3Status.CANCELLED.value
        mock_db.refresh = mock_refresh

        response = await cancel_a3(a3_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 cancelled"

    @pytest.mark.asyncio
    async def test_cancel_closed_a3_fails(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test cancelling already closed A3 fails."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, status=A3Status.CLOSED.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        with pytest.raises(ConflictError):
            await cancel_a3(a3_id, mock_db, mock_user)


# =============================================================================
# A3 Section Tests
# =============================================================================


class TestA3Sections:
    """Tests for A3 section management."""

    @pytest.mark.asyncio
    async def test_add_section(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test adding a section to A3."""
        a3_id = uuid4()
        a3 = create_mock_a3(a3_id=a3_id, sections=[])
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        data = SectionCreate(
            section_type=A3SectionType.ROOT_CAUSE,
            section_name="Root Cause Analysis",
            content="5 Whys content",
            guidance="Use 5 Whys or fishbone",
        )

        captured_section = None
        original_add = mock_db.add
        def capture_add(obj):
            nonlocal captured_section
            captured_section = obj
        mock_db.add = capture_add

        async def mock_refresh(obj, *args):
            obj.id = uuid4()
            obj.is_complete = False
            obj.version = 1
            obj.section_order = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await add_section(a3_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 section created successfully"

    @pytest.mark.asyncio
    async def test_add_section_a3_not_found(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test adding section to non-existent A3."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        data = SectionCreate(section_name="Test Section")

        with pytest.raises(NotFoundError):
            await add_section(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_update_section(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test updating a section."""
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(section_id=section_id, a3_id=a3_id)
        mock_db.execute.return_value = make_result(scalar_one_or_none=section)

        data = SectionUpdate(content="Updated content")

        async def mock_refresh(obj, *args):
            obj.content = "Updated content"
        mock_db.refresh = mock_refresh

        response = await update_section(a3_id, section_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 section updated successfully"

    @pytest.mark.asyncio
    async def test_update_section_reasoning_gate_warns_and_persists_metadata(
        self,
        mock_db: AsyncMock,
        mock_user: MagicMock,
    ):
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(
            section_id=section_id,
            a3_id=a3_id,
            section_type=A3SectionType.ROOT_CAUSE.value,
            structured_content={},
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=section)

        data = SectionUpdate(content="Operator error caused the defect")

        async def mock_refresh(obj, *args):
            obj.content = data.content
        mock_db.refresh = mock_refresh

        response = await update_section(a3_id, section_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 section updated successfully (with reasoning warnings)"
        assert response.data.structured_content is not None
        assert "_reasoning_gate" in response.data.structured_content
        assert response.data.structured_content["_reasoning_gate"]["status"] == "warning"

    @pytest.mark.asyncio
    async def test_update_section_reasoning_gate_blocks_inventory_countermeasure(
        self,
        mock_db: AsyncMock,
        mock_user: MagicMock,
    ):
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(
            section_id=section_id,
            a3_id=a3_id,
            section_type=A3SectionType.COUNTERMEASURES.value,
            structured_content={},
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=section)

        data = SectionUpdate(content="Add buffer stock and increase inventory")

        with pytest.raises(ConflictError) as exc:
            await update_section(a3_id, section_id, data, mock_db, mock_user)

        assert "TPS reasoning gates" in str(exc.value)
        assert exc.value.details is not None
        assert exc.value.details.get("status") == "block"

    @pytest.mark.asyncio
    async def test_complete_section(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test completing a section."""
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(section_id=section_id, a3_id=a3_id)
        a3 = create_mock_a3(a3_id=a3_id, sections=[section])

        mock_db.execute.side_effect = [
            make_result(scalar_one_or_none=section),
            make_result(scalar_one_or_none=a3),
        ]

        async def mock_refresh(obj, *args):
            obj.is_complete = True
            obj.completed_at = datetime.now(timezone.utc)
            obj.completed_by_id = mock_user.id
        mock_db.refresh = mock_refresh

        response = await complete_section(a3_id, section_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Section completed"

    @pytest.mark.asyncio
    async def test_reopen_section(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test reopening a completed section."""
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(
            section_id=section_id,
            a3_id=a3_id,
            is_complete=True,
            completed_at=datetime.now(timezone.utc),
        )
        a3 = create_mock_a3(a3_id=a3_id, sections=[section])

        mock_db.execute.side_effect = [
            make_result(scalar_one_or_none=section),
            make_result(scalar_one_or_none=a3),
        ]

        async def mock_refresh(obj, *args):
            obj.is_complete = False
            obj.completed_at = None
            obj.completed_by_id = None
        mock_db.refresh = mock_refresh

        response = await reopen_section(a3_id, section_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Section reopened"

    @pytest.mark.asyncio
    async def test_add_section_comment(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test adding a comment to a section."""
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(section_id=section_id, a3_id=a3_id, comments=[])
        mock_db.execute.return_value = make_result(scalar_one_or_none=section)

        data = SectionComment(comment="Please add more details here")

        async def mock_refresh(obj, *args):
            pass
        mock_db.refresh = mock_refresh

        response = await add_section_comment(a3_id, section_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Comment added"

    @pytest.mark.asyncio
    async def test_delete_section(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test deleting a section."""
        a3_id = uuid4()
        section_id = uuid4()
        section = create_mock_section(section_id=section_id, a3_id=a3_id)
        a3 = create_mock_a3(a3_id=a3_id, sections=[])

        mock_db.execute.side_effect = [
            make_result(scalar_one_or_none=section),
            make_result(scalar_one_or_none=a3),
        ]

        response = await delete_section(a3_id, section_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "A3 section deleted successfully"


# =============================================================================
# A3 Query Tests
# =============================================================================


class TestA3Queries:
    """Tests for A3 query endpoints."""

    @pytest.mark.asyncio
    async def test_get_a3_by_number(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting A3 by document number."""
        a3 = create_mock_a3(a3_number="A3-UNIQUE-001")
        mock_db.execute.return_value = make_result(scalar_one_or_none=a3)

        response = await get_a3_by_number("A3-UNIQUE-001", mock_db, mock_user)

        assert response.success is True
        assert response.data.a3_number == "A3-UNIQUE-001"

    @pytest.mark.asyncio
    async def test_get_a3_by_number_not_found(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting non-existent A3 by number."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        with pytest.raises(NotFoundError):
            await get_a3_by_number("A3-NOTEXIST", mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_my_a3s(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting current user's A3s."""
        a3s = [
            create_mock_a3(author_id=mock_user.id, title="My A3 One"),
            create_mock_a3(author_id=mock_user.id, title="My A3 Two"),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=a3s),
        ]

        response = await get_my_a3s(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2

    @pytest.mark.asyncio
    async def test_get_pending_review(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting A3s pending review."""
        a3s = [
            create_mock_a3(status=A3Status.REVIEW.value, title="Pending Review 1"),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=1),
            make_result(scalars_all=a3s),
        ]

        response = await get_pending_review(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 1

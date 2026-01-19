"""
Comprehensive Tests for RFQ Endpoints

Tests all RFQ functionality including:
- CRUD operations
- Status/workflow transitions
- Question management
- Filtering and pagination
- Edge cases and error handling
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi import status

from sensei.api.v1.endpoints.rfqs import (
    router,
    list_rfqs,
    create_rfq,
    get_rfq,
    update_rfq,
    delete_rfq,
    mark_rfq_quoted,
    mark_rfq_won,
    mark_rfq_lost,
    mark_rfq_no_bid,
    list_rfq_questions,
    add_rfq_question,
    update_rfq_question,
    delete_rfq_question,
    get_rfq_stats,
    RFQCreate,
    RFQUpdate,
    QuestionCreate,
    QuestionUpdate,
    rfq_to_response,
    rfq_to_list_response,
    question_to_response,
    generate_rfq_number,
)
from sensei.models.rfq import RFQ, RFQStatus, RFQPriority, RFQSource, RFQQuestion, QuestionStatus


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.is_superuser = False
    return user


@pytest.fixture
def mock_superuser():
    """Create a mock superuser."""
    user = MagicMock()
    user.id = uuid4()
    user.is_superuser = True
    return user


@pytest.fixture
def account_id():
    """Create a test account ID."""
    return uuid4()


@pytest.fixture
def contact_id():
    """Create a test contact ID."""
    return uuid4()


@pytest.fixture
def sample_rfq(account_id, contact_id):
    """Create a sample RFQ model."""
    rfq = MagicMock(spec=RFQ)
    rfq.id = uuid4()
    rfq.rfq_number = "RFQ-2025-00001"
    rfq.customer_rfq_number = "CUST-123"
    rfq.revision = 1
    rfq.title = "Test RFQ for Precision Parts"
    rfq.description = "RFQ for machined components"
    rfq.account_id = account_id
    rfq.contact_id = contact_id
    rfq.opportunity_id = None
    rfq.status = RFQStatus.RECEIVED.value
    rfq.priority = RFQPriority.MEDIUM.value
    rfq.source = RFQSource.EMAIL.value
    rfq.received_date = datetime.now(timezone.utc)
    rfq.due_date = datetime.now(timezone.utc) + timedelta(days=7)
    rfq.customer_deadline = None
    rfq.quoted_date = None
    rfq.decision_date = None
    rfq.part_number = "PART-001"
    rfq.part_name = "Precision Shaft"
    rfq.part_revision = "A"
    rfq.drawing_number = "DWG-001"
    rfq.quantity = 100
    rfq.annual_volume = 1200
    rfq.target_price = Decimal("25.00")
    rfq.currency = "MAD"
    rfq.material_spec = "AISI 4140 Steel"
    rfq.material_grade = "4140"
    rfq.finish_requirements = "Ra 0.8 or better"
    rfq.tolerance_requirements = "±0.01mm"
    rfq.primary_process = "CNC Turning"
    rfq.secondary_processes = ["Heat Treatment", "Grinding"]
    rfq.quality_requirements = "ISO 9001 certified process"
    rfq.certifications_required = ["ISO 9001", "IATF 16949"]
    rfq.inspection_requirements = "First article inspection"
    rfq.delivery_terms = "DDP"
    rfq.delivery_location = "Casablanca, Morocco"
    rfq.lead_time_required = 30
    rfq.packaging_requirements = "Anti-corrosion packaging"
    rfq.assigned_to_id = None
    rfq.is_qualified = None
    rfq.qualification_score = None
    rfq.qualification_notes = None
    rfq.no_bid_reason = None
    rfq.is_won = None
    rfq.win_loss_reason = None
    rfq.competitor_id = None
    rfq.internal_notes = "High priority customer"
    rfq.customer_notes = None
    rfq.custom_fields = {}
    rfq.tags = ["priority", "machining"]
    rfq.created_at = datetime.now(timezone.utc)
    rfq.updated_at = datetime.now(timezone.utc)
    rfq.created_by_id = uuid4()
    rfq.deleted_at = None
    rfq.previous_status = None
    rfq.status_changed_at = None
    
    # Mock relationships
    rfq.questions = MagicMock()
    rfq.questions.all = MagicMock(return_value=[])
    rfq.quotes = MagicMock()
    rfq.quotes.all = MagicMock(return_value=[])
    
    return rfq


@pytest.fixture
def sample_question():
    """Create a sample RFQ question."""
    question = MagicMock(spec=RFQQuestion)
    question.id = uuid4()
    question.rfq_id = uuid4()
    question.question = "What is the acceptable tolerance range?"
    question.answer = None
    question.status = QuestionStatus.DRAFT.value
    question.category = "Technical"
    question.asked_at = datetime.now(timezone.utc)
    question.answered_at = None
    question.asked_by_id = uuid4()
    question.answered_by_id = None
    question.created_at = datetime.now(timezone.utc)
    question.updated_at = datetime.now(timezone.utc)
    return question


# =============================================================================
# RFQ Number Generation Tests
# =============================================================================


class TestRFQNumberGeneration:
    """Tests for RFQ number generation."""
    
    @pytest.mark.asyncio
    async def test_generate_rfq_number_first_of_year(self):
        """Should generate first RFQ number for year."""
        db = AsyncMock()
        db.execute = AsyncMock()
        
        # No existing RFQ for this year
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        number = await generate_rfq_number(db)
        
        year = datetime.now().year
        assert number == f"RFQ-{year}-00001"
    
    @pytest.mark.asyncio
    async def test_generate_rfq_number_increment(self):
        """Should increment existing RFQ number."""
        db = AsyncMock()
        db.execute = AsyncMock()
        
        year = datetime.now().year
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=f"RFQ-{year}-00042")
        db.execute.return_value = mock_result
        
        number = await generate_rfq_number(db)
        
        assert number == f"RFQ-{year}-00043"


# =============================================================================
# RFQ CRUD Tests
# =============================================================================


class TestListRFQs:
    """Tests for listing RFQs."""
    
    @pytest.mark.asyncio
    async def test_list_rfqs_empty(self, mock_user):
        """Should return empty list when no RFQs exist."""
        db = AsyncMock()
        
        # Mock count query
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        
        # Mock list query
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data == []
        assert response.pagination.total_items == 0
    
    @pytest.mark.asyncio
    async def test_list_rfqs_with_results(self, mock_user, sample_rfq):
        """Should return list of RFQs."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.data) == 1
        assert response.data[0].rfq_number == "RFQ-2025-00001"
    
    @pytest.mark.asyncio
    async def test_list_rfqs_with_search(self, mock_user, sample_rfq):
        """Should filter RFQs by search term."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search="Precision",
            status=None,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
        assert db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_rfqs_filter_by_status(self, mock_user, sample_rfq):
        """Should filter RFQs by status."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=RFQStatus.RECEIVED.value,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_rfqs_filter_by_priority(self, mock_user, sample_rfq):
        """Should filter RFQs by priority."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            priority=RFQPriority.HIGH.value,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_rfqs_filter_open_only(self, mock_user, sample_rfq):
        """Should filter only open RFQs."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=True,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_rfqs_pagination(self, mock_user):
        """Should handle pagination correctly."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=100)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=2,
            page_size=25,
            search=None,
            status=None,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.pagination.page == 2
        assert response.pagination.page_size == 25
        assert response.pagination.total_items == 100


class TestCreateRFQ:
    """Tests for RFQ creation."""
    
    @pytest.mark.asyncio
    async def test_create_rfq_success(self, mock_user, account_id, contact_id):
        """Should create an RFQ successfully."""
        db = AsyncMock()
        
        # Mock RFQ number generation
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        created_rfq = None
        
        def capture_add(rfq):
            nonlocal created_rfq
            created_rfq = rfq
            # Set required fields that would be set by the database
            rfq.id = uuid4()
            rfq.rfq_number = "RFQ-2025-00001"
            rfq.revision = 1
            rfq.currency = "MAD"  # DB default
            rfq.received_date = datetime.now(timezone.utc)
            rfq.created_at = datetime.now(timezone.utc)
            rfq.updated_at = datetime.now(timezone.utc)
            rfq.questions = MagicMock()
            rfq.questions.all = MagicMock(return_value=[])
            rfq.quotes = MagicMock()
            rfq.quotes.all = MagicMock(return_value=[])
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        rfq_data = RFQCreate(
            title="Test RFQ",
            account_id=account_id,
            contact_id=contact_id,
            priority=RFQPriority.HIGH.value,
            quantity=100,
            part_number="PART-001",
        )
        
        response = await create_rfq(
            rfq_data=rfq_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.add.called
        assert db.commit.called
        assert created_rfq.status == RFQStatus.RECEIVED.value
    
    @pytest.mark.asyncio
    async def test_create_rfq_minimal_data(self, mock_user, account_id):
        """Should create RFQ with minimal required data."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        def capture_add(rfq):
            rfq.id = uuid4()
            rfq.rfq_number = "RFQ-2025-00001"
            rfq.revision = 1
            rfq.status = RFQStatus.RECEIVED.value  # DB default
            rfq.priority = RFQPriority.MEDIUM.value  # DB default
            rfq.currency = "MAD"  # DB default
            rfq.received_date = datetime.now(timezone.utc)
            rfq.created_at = datetime.now(timezone.utc)
            rfq.updated_at = datetime.now(timezone.utc)
            rfq.questions = MagicMock()
            rfq.questions.all = MagicMock(return_value=[])
            rfq.quotes = MagicMock()
            rfq.quotes.all = MagicMock(return_value=[])
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        rfq_data = RFQCreate(
            title="Minimal RFQ",
            account_id=account_id,
        )
        
        response = await create_rfq(
            rfq_data=rfq_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True


class TestGetRFQ:
    """Tests for getting a single RFQ."""
    
    @pytest.mark.asyncio
    async def test_get_rfq_success(self, mock_user, sample_rfq):
        """Should return RFQ by ID."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        response = await get_rfq(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data.rfq_number == sample_rfq.rfq_number
    
    @pytest.mark.asyncio
    async def test_get_rfq_not_found(self, mock_user):
        """Should return 404 for non-existent RFQ."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_rfq(
                rfq_id=uuid4(),
                db=db,
                current_user=mock_user,
                include_deleted=False,
            )
    
    @pytest.mark.asyncio
    async def test_get_rfq_include_deleted(self, mock_user, sample_rfq):
        """Should return deleted RFQ when include_deleted=True."""
        db = AsyncMock()
        
        sample_rfq.deleted_at = datetime.now(timezone.utc)
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        response = await get_rfq(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
            include_deleted=True,
        )
        
        assert response.success is True


class TestUpdateRFQ:
    """Tests for updating RFQs."""
    
    @pytest.mark.asyncio
    async def test_update_rfq_success(self, mock_user, sample_rfq):
        """Should update RFQ successfully."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        update_data = RFQUpdate(
            title="Updated RFQ Title",
            priority=RFQPriority.URGENT.value,
        )
        
        response = await update_rfq(
            rfq_id=sample_rfq.id,
            rfq_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.commit.called
    
    @pytest.mark.asyncio
    async def test_update_rfq_status_change_tracking(self, mock_user, sample_rfq):
        """Should track status change."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        old_status = sample_rfq.status
        
        update_data = RFQUpdate(
            status=RFQStatus.QUOTING.value,
        )
        
        response = await update_rfq(
            rfq_id=sample_rfq.id,
            rfq_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_rfq.previous_status == old_status
    
    @pytest.mark.asyncio
    async def test_update_rfq_not_found(self, mock_user):
        """Should return 404 for non-existent RFQ."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        update_data = RFQUpdate(title="New Title")
        
        with pytest.raises(NotFoundError):
            await update_rfq(
                rfq_id=uuid4(),
                rfq_data=update_data,
                db=db,
                current_user=mock_user,
            )


class TestDeleteRFQ:
    """Tests for deleting RFQs."""
    
    @pytest.mark.asyncio
    async def test_delete_rfq_soft(self, mock_user, sample_rfq):
        """Should soft delete RFQ by default."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        response = await delete_rfq(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response.success is True
        assert sample_rfq.deleted_at is not None
        assert db.commit.called
    
    @pytest.mark.asyncio
    async def test_delete_rfq_hard_as_superuser(self, mock_superuser, sample_rfq):
        """Should hard delete RFQ as superuser."""
        db = AsyncMock()
        db.delete = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        response = await delete_rfq(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_superuser,
            hard_delete=True,
        )
        
        assert response.success is True
        assert db.delete.called
    
    @pytest.mark.asyncio
    async def test_delete_rfq_hard_forbidden(self, mock_user, sample_rfq):
        """Should forbid hard delete for non-superuser."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ForbiddenError
        
        with pytest.raises(ForbiddenError):
            await delete_rfq(
                rfq_id=sample_rfq.id,
                db=db,
                current_user=mock_user,
                hard_delete=True,
            )
    
    @pytest.mark.asyncio
    async def test_delete_rfq_not_found(self, mock_user):
        """Should return 404 for non-existent RFQ."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await delete_rfq(
                rfq_id=uuid4(),
                db=db,
                current_user=mock_user,
                hard_delete=False,
            )


# =============================================================================
# RFQ Workflow Tests
# =============================================================================


class TestRFQWorkflow:
    """Tests for RFQ workflow transitions."""
    
    @pytest.mark.asyncio
    async def test_mark_rfq_quoted(self, mock_user, sample_rfq):
        """Should mark RFQ as quoted."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        response = await mark_rfq_quoted(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_rfq.status == RFQStatus.QUOTED.value
        assert sample_rfq.quoted_date is not None
    
    @pytest.mark.asyncio
    async def test_mark_rfq_won(self, mock_user, sample_rfq):
        """Should mark RFQ as won."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        response = await mark_rfq_won(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
            _=None,
            win_reason="Best price and quality",
        )
        
        assert response.success is True
        assert sample_rfq.status == RFQStatus.WON.value
        assert sample_rfq.is_won is True
        assert sample_rfq.decision_date is not None
    
    @pytest.mark.asyncio
    async def test_mark_rfq_lost(self, mock_user, sample_rfq):
        """Should mark RFQ as lost."""
        db = AsyncMock()
        
        competitor_id = uuid4()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        response = await mark_rfq_lost(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
            _=None,
            loss_reason="Price too high",
            competitor_id=competitor_id,
        )
        
        assert response.success is True
        assert sample_rfq.status == RFQStatus.LOST.value
        assert sample_rfq.is_won is False
        assert sample_rfq.competitor_id == competitor_id
    
    @pytest.mark.asyncio
    async def test_mark_rfq_no_bid(self, mock_user, sample_rfq):
        """Should mark RFQ as no-bid."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        response = await mark_rfq_no_bid(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
            _=None,
            reason="Outside our capabilities",
        )
        
        assert response.success is True
        assert sample_rfq.status == RFQStatus.NO_BID.value
        assert sample_rfq.no_bid_reason == "Outside our capabilities"


# =============================================================================
# RFQ Question Tests
# =============================================================================


class TestRFQQuestions:
    """Tests for RFQ question management."""
    
    @pytest.mark.asyncio
    async def test_list_questions_empty(self, mock_user, sample_rfq):
        """Should return empty list when no questions exist."""
        db = AsyncMock()
        
        rfq_result = MagicMock()
        rfq_result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        
        questions_result = MagicMock()
        questions_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[rfq_result, questions_result])
        
        response = await list_rfq_questions(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data == []
    
    @pytest.mark.asyncio
    async def test_list_questions_with_results(self, mock_user, sample_rfq, sample_question):
        """Should return list of questions."""
        db = AsyncMock()
        
        sample_question.rfq_id = sample_rfq.id
        
        rfq_result = MagicMock()
        rfq_result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        
        questions_result = MagicMock()
        questions_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_question])))
        
        db.execute = AsyncMock(side_effect=[rfq_result, questions_result])
        
        response = await list_rfq_questions(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert len(response.data) == 1
    
    @pytest.mark.asyncio
    async def test_add_question(self, mock_user, sample_rfq):
        """Should add a question to RFQ."""
        db = AsyncMock()
        
        rfq_result = MagicMock()
        rfq_result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = rfq_result
        
        def capture_add(q):
            q.id = uuid4()
            q.rfq_id = sample_rfq.id
            q.status = QuestionStatus.DRAFT.value
            q.created_at = datetime.now(timezone.utc)
            q.updated_at = datetime.now(timezone.utc)
            q.asked_at = None
            q.answered_at = None
            q.answered_by_id = None
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        question_data = QuestionCreate(
            question="What is the lead time?",
            category="Logistics",
        )
        
        response = await add_rfq_question(
            rfq_id=sample_rfq.id,
            question_data=question_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.add.called
    
    @pytest.mark.asyncio
    async def test_add_question_updates_rfq_status(self, mock_user, sample_rfq):
        """Should update RFQ status to QUESTIONS_PENDING when adding first question."""
        db = AsyncMock()
        
        sample_rfq.status = RFQStatus.RECEIVED.value
        
        rfq_result = MagicMock()
        rfq_result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = rfq_result
        
        def capture_add(q):
            q.id = uuid4()
            q.rfq_id = sample_rfq.id
            q.status = QuestionStatus.DRAFT.value
            q.created_at = datetime.now(timezone.utc)
            q.updated_at = datetime.now(timezone.utc)
            q.asked_at = None
            q.answered_at = None
            q.answered_by_id = None
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        question_data = QuestionCreate(
            question="What is the tolerance?",
        )
        
        await add_rfq_question(
            rfq_id=sample_rfq.id,
            question_data=question_data,
            db=db,
            current_user=mock_user,
        )
        
        assert sample_rfq.status == RFQStatus.QUESTIONS_PENDING.value
    
    @pytest.mark.asyncio
    async def test_update_question_with_answer(self, mock_user, sample_question):
        """Should update question with answer."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_question)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        update_data = QuestionUpdate(
            answer="The tolerance is ±0.01mm",
        )
        
        response = await update_rfq_question(
            rfq_id=sample_question.rfq_id,
            question_id=sample_question.id,
            question_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_question.answer == "The tolerance is ±0.01mm"
        assert sample_question.status == QuestionStatus.ANSWERED.value
        assert sample_question.answered_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_question(self, mock_user, sample_question):
        """Should delete a question."""
        db = AsyncMock()
        db.delete = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_question)
        db.execute.return_value = result
        
        response = await delete_rfq_question(
            rfq_id=sample_question.rfq_id,
            question_id=sample_question.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.delete.called


# =============================================================================
# RFQ Statistics Tests
# =============================================================================


class TestRFQStats:
    """Tests for RFQ statistics."""
    
    @pytest.mark.asyncio
    async def test_get_rfq_stats(self, mock_user, sample_rfq):
        """Should return RFQ statistics."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        response = await get_rfq_stats(
            rfq_id=sample_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        data = response.data
        assert data["rfq_number"] == sample_rfq.rfq_number
        assert "questions" in data
        assert "quotes" in data
        assert "qualification" in data
    
    @pytest.mark.asyncio
    async def test_get_rfq_stats_not_found(self, mock_user):
        """Should return 404 for non-existent RFQ."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_rfq_stats(
                rfq_id=uuid4(),
                db=db,
                current_user=mock_user,
            )


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_rfq_to_response(self, sample_rfq):
        """Should convert RFQ model to response."""
        response = rfq_to_response(sample_rfq)
        
        assert response.id == sample_rfq.id
        assert response.rfq_number == sample_rfq.rfq_number
        assert response.title == sample_rfq.title
        assert response.status == sample_rfq.status
        assert response.priority == sample_rfq.priority
    
    def test_rfq_to_list_response(self, sample_rfq):
        """Should convert RFQ model to list response."""
        response = rfq_to_list_response(sample_rfq)
        
        assert response.id == sample_rfq.id
        assert response.rfq_number == sample_rfq.rfq_number
        assert response.title == sample_rfq.title
        assert response.status == sample_rfq.status
    
    def test_question_to_response(self, sample_question):
        """Should convert question model to response."""
        response = question_to_response(sample_question)
        
        assert response.id == sample_question.id
        assert response.question == sample_question.question
        assert response.status == sample_question.status


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and validation."""
    
    @pytest.mark.asyncio
    async def test_list_rfqs_include_deleted(self, mock_user, sample_rfq):
        """Should include deleted RFQs when flag is set."""
        db = AsyncMock()
        
        sample_rfq.deleted_at = datetime.now(timezone.utc)
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            priority=None,
            account_id=None,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=True,
        )
        
        assert response.success is True
        assert len(response.data) == 1
    
    @pytest.mark.asyncio
    async def test_update_rfq_qualification(self, mock_user, sample_rfq):
        """Should update qualification fields."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        update_data = RFQUpdate(
            is_qualified=True,
            qualification_score=Decimal("85.5"),
            qualification_notes="Good fit for our capabilities",
        )
        
        response = await update_rfq(
            rfq_id=sample_rfq.id,
            rfq_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_rfq.is_qualified is True
        assert sample_rfq.qualification_score == Decimal("85.5")
    
    @pytest.mark.asyncio
    async def test_delete_already_deleted_rfq(self, mock_user, sample_rfq):
        """Should return 404 when trying to soft delete already deleted RFQ."""
        db = AsyncMock()
        
        sample_rfq.deleted_at = datetime.now(timezone.utc)
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_rfq)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await delete_rfq(
                rfq_id=sample_rfq.id,
                db=db,
                current_user=mock_user,
                hard_delete=False,
            )
    
    @pytest.mark.asyncio
    async def test_list_rfqs_filter_by_account(self, mock_user, sample_rfq, account_id):
        """Should filter RFQs by account ID."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_rfq])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_rfqs(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            priority=None,
            account_id=account_id,
            assigned_to_id=None,
            is_open=None,
            sort="-received_date",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_mark_workflow_not_found(self, mock_user):
        """Should return 404 for workflow actions on non-existent RFQ."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await mark_rfq_quoted(
                rfq_id=uuid4(),
                db=db,
                current_user=mock_user,
            )


# =============================================================================
# RFQ Completeness Endpoint Tests
# =============================================================================


class TestRFQCompletenessEndpoints:
    """Tests for RFQ completeness scoring endpoints."""
    
    @pytest.fixture
    def complete_rfq(self, account_id, contact_id):
        """Create an RFQ with all fields filled."""
        rfq = MagicMock(spec=RFQ)
        rfq.id = uuid4()
        rfq.rfq_number = "RFQ-2025-00001"
        rfq.title = "Complete Test RFQ"
        rfq.description = "Full description"
        rfq.status = RFQStatus.RECEIVED.value
        rfq.account_id = account_id
        rfq.contact_id = contact_id
        rfq.quantity = 1000
        rfq.due_date = datetime.now(timezone.utc) + timedelta(days=14)
        rfq.part_number = "PN-12345"
        rfq.part_name = "Test Widget"
        rfq.drawing_number = "DWG-001"
        rfq.material_spec = "Aluminum 6061-T6"
        rfq.annual_volume = 10000
        rfq.primary_process = "CNC Machining"
        rfq.delivery_terms = "FOB Origin"
        rfq.target_price = Decimal("25.00")
        rfq.finish_requirements = "Anodize Black"
        rfq.tolerance_requirements = "+/- 0.005"
        rfq.quality_requirements = "ISO 9001"
        rfq.packaging_requirements = "Individual bags"
        rfq.delivery_location = "Plant A"
        rfq.lead_time_required = 14
        rfq.certifications_required = "NADCAP"
        rfq.deleted_at = None
        rfq.account = MagicMock(name="Test Account Inc")
        rfq.account.name = "Test Account Inc"
        return rfq
    
    @pytest.fixture
    def incomplete_rfq(self, account_id):
        """Create an RFQ with minimal fields."""
        rfq = MagicMock(spec=RFQ)
        rfq.id = uuid4()
        rfq.rfq_number = "RFQ-2025-00002"
        rfq.title = "Incomplete Test RFQ"
        rfq.description = None
        rfq.status = RFQStatus.DRAFT.value
        rfq.account_id = account_id
        rfq.contact_id = None
        rfq.quantity = 100
        rfq.due_date = datetime.now(timezone.utc) + timedelta(days=7)
        rfq.part_number = None
        rfq.part_name = None
        rfq.drawing_number = None
        rfq.material_spec = None
        rfq.annual_volume = None
        rfq.primary_process = None
        rfq.delivery_terms = None
        rfq.target_price = None
        rfq.finish_requirements = None
        rfq.tolerance_requirements = None
        rfq.quality_requirements = None
        rfq.packaging_requirements = None
        rfq.delivery_location = None
        rfq.lead_time_required = None
        rfq.certifications_required = None
        rfq.deleted_at = None
        rfq.account = MagicMock()
        rfq.account.name = "Incomplete Account"
        return rfq
    
    @pytest.mark.asyncio
    async def test_get_completeness_full_score(self, mock_user, complete_rfq):
        """Should return 100% completeness for a fully filled RFQ."""
        from sensei.api.v1.endpoints.rfqs import get_rfq_completeness
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=complete_rfq)
        db.execute.return_value = result
        
        response = await get_rfq_completeness(
            rfq_id=complete_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["score"] == 100
        assert response.data["can_qualify"] is True
        assert len(response.data["missing_fields"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_completeness_partial_score(self, mock_user, incomplete_rfq):
        """Should return partial score for incomplete RFQ."""
        from sensei.api.v1.endpoints.rfqs import get_rfq_completeness
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=incomplete_rfq)
        db.execute.return_value = result
        
        response = await get_rfq_completeness(
            rfq_id=incomplete_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["score"] < 100
        assert response.data["score"] > 0  # Has some filled fields
        assert len(response.data["missing_fields"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_completeness_not_found(self, mock_user):
        """Should return 404 for non-existent RFQ."""
        from sensei.api.v1.endpoints.rfqs import get_rfq_completeness
        from sensei.api.exceptions import NotFoundError
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        with pytest.raises(NotFoundError):
            await get_rfq_completeness(
                rfq_id=uuid4(),
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_generate_missing_info_email(self, mock_user, incomplete_rfq):
        """Should generate email for missing fields."""
        from sensei.api.v1.endpoints.rfqs import generate_missing_info_email
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=incomplete_rfq)
        db.execute.return_value = result
        
        response = await generate_missing_info_email(
            rfq_id=incomplete_rfq.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert "email_text" in response.data
        assert response.data["missing_count"] > 0
    
    @pytest.mark.asyncio
    async def test_transition_to_qualification_success(self, mock_user, complete_rfq):
        """Should transition to qualifying status with full completeness."""
        from sensei.api.v1.endpoints.rfqs import transition_to_qualification, QualifyRequest
        
        # Set up RFQ in proper state
        complete_rfq.status = RFQStatus.RECEIVED.value
        complete_rfq.previous_status = None
        complete_rfq.status_changed_at = None
        complete_rfq.custom_fields = None
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=complete_rfq)
        db.execute.return_value = result
        
        request = QualifyRequest(allow_override=False)
        
        response = await transition_to_qualification(
            rfq_id=complete_rfq.id,
            request=request,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["new_status"] == RFQStatus.QUALIFYING.value
        db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transition_to_qualification_blocked(self, mock_user, incomplete_rfq):
        """Should block transition when score is too low."""
        from sensei.api.v1.endpoints.rfqs import transition_to_qualification, QualifyRequest
        from sensei.api.exceptions import ForbiddenError
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=incomplete_rfq)
        db.execute.return_value = result
        
        request = QualifyRequest(allow_override=False)
        
        with pytest.raises(ForbiddenError):
            await transition_to_qualification(
                rfq_id=incomplete_rfq.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_transition_with_override(self, mock_user, incomplete_rfq):
        """Should allow transition with GM override."""
        from sensei.api.v1.endpoints.rfqs import transition_to_qualification, QualifyRequest
        
        incomplete_rfq.status = RFQStatus.RECEIVED.value
        incomplete_rfq.previous_status = None
        incomplete_rfq.status_changed_at = None
        incomplete_rfq.custom_fields = None
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=incomplete_rfq)
        db.execute.return_value = result
        
        request = QualifyRequest(
            allow_override=True,
            override_rationale="Urgent customer request - expedited processing approved by management",
        )
        
        response = await transition_to_qualification(
            rfq_id=incomplete_rfq.id,
            request=request,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["override_used"] is True
    
    @pytest.mark.asyncio
    async def test_transition_already_qualifying(self, mock_user, complete_rfq):
        """Should reject transition if already in qualifying status."""
        from sensei.api.v1.endpoints.rfqs import transition_to_qualification, QualifyRequest
        from sensei.api.exceptions import ConflictError
        
        complete_rfq.status = RFQStatus.QUALIFYING.value
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=complete_rfq)
        db.execute.return_value = result
        
        request = QualifyRequest(allow_override=False)
        
        with pytest.raises(ConflictError):
            await transition_to_qualification(
                rfq_id=complete_rfq.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_generate_missing_tasks(self, mock_user, incomplete_rfq):
        """Should generate tasks for missing fields."""
        from sensei.api.v1.endpoints.rfqs import generate_missing_info_tasks
        
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=incomplete_rfq)
        db.execute.return_value = result
        
        response = await generate_missing_info_tasks(
            rfq_id=incomplete_rfq.id,
            db=db,
            current_user=mock_user,
            assigned_to_id=None,
        )
        
        assert response.success is True
        assert response.data["tasks_generated"] > 0
        assert len(response.data["tasks"]) == response.data["tasks_generated"]
    
    @pytest.mark.asyncio
    async def test_get_field_definitions(self, mock_user):
        """Should return field definitions."""
        from sensei.api.v1.endpoints.rfqs import get_completeness_field_definitions
        
        response = await get_completeness_field_definitions(
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["field_count"] == 21
        assert response.data["qualification_threshold"] == 70
        assert len(response.data["fields"]) == 21

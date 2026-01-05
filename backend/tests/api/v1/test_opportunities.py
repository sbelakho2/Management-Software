"""
Comprehensive Tests for Opportunity Endpoints

Tests all Opportunity functionality including:
- CRUD operations
- Stage/pipeline management
- Note management
- Pipeline and forecasting
- Edge cases and error handling
"""

from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi import status

from sensei.api.v1.endpoints.opportunities import (
    router,
    list_opportunities,
    create_opportunity,
    get_opportunity,
    update_opportunity,
    delete_opportunity,
    change_opportunity_stage,
    close_opportunity_won,
    close_opportunity_lost,
    reopen_opportunity,
    list_opportunity_notes,
    add_opportunity_note,
    update_opportunity_note,
    delete_opportunity_note,
    get_pipeline_summary,
    get_forecast,
    OpportunityCreate,
    OpportunityUpdate,
    NoteCreate,
    NoteUpdate,
    StageChangeRequest,
    CloseWonRequest,
    CloseLostRequest,
    opportunity_to_response,
    opportunity_to_list_response,
    note_to_response,
    generate_opportunity_number,
    STAGE_PROBABILITIES,
)
from sensei.models.opportunity import (
    Opportunity,
    OpportunityStage,
    OpportunityType,
    OpportunitySource,
    OpportunityNote,
    NoteType,
)


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
def primary_contact_id():
    """Create a test contact ID."""
    return uuid4()


@pytest.fixture
def sample_opportunity(account_id, primary_contact_id):
    """Create a sample opportunity model."""
    opp = MagicMock(spec=Opportunity)
    opp.id = uuid4()
    opp.opportunity_number = "OPP-2025-00001"
    opp.name = "New Manufacturing Contract"
    opp.description = "Large contract for precision parts"
    opp.account_id = account_id
    opp.primary_contact_id = primary_contact_id
    opp.stage = OpportunityStage.PROPOSAL.value
    opp.opportunity_type = OpportunityType.NEW_BUSINESS.value
    opp.lead_source = OpportunitySource.TRADE_SHOW.value
    opp.amount = Decimal("500000.00")
    opp.currency = "MAD"
    opp.probability = 60
    opp.weighted_amount = Decimal("300000.00")
    opp.close_date = date.today() + timedelta(days=30)
    opp.actual_close_date = None
    opp.is_won = None
    opp.close_reason = None
    opp.competitor_id = None
    opp.next_step = "Submit proposal"
    opp.next_step_date = date.today() + timedelta(days=7)
    opp.forecast_category = "Pipeline"
    opp.custom_fields = {}
    opp.tags = ["manufacturing", "priority"]
    opp.created_at = datetime.now(timezone.utc)
    opp.updated_at = datetime.now(timezone.utc)
    opp.created_by_id = uuid4()
    opp.deleted_at = None
    
    # Mock computed properties - PROPOSAL is an open stage
    opp.is_open = True
    opp.is_closed = False
    
    # Mock relationships
    opp.notes = MagicMock()
    opp.notes.all = MagicMock(return_value=[])
    opp.rfqs = MagicMock()
    opp.rfqs.all = MagicMock(return_value=[])
    opp.quotes = MagicMock()
    opp.quotes.all = MagicMock(return_value=[])
    
    # Mock calculate method
    opp.calculate_weighted_amount = MagicMock()
    
    return opp


@pytest.fixture
def sample_note():
    """Create a sample opportunity note."""
    note = MagicMock(spec=OpportunityNote)
    note.id = uuid4()
    note.opportunity_id = uuid4()
    note.content = "Had a productive meeting with the customer"
    note.note_type = NoteType.MEETING.value
    note.created_at = datetime.now(timezone.utc)
    note.updated_at = datetime.now(timezone.utc)
    note.created_by_id = uuid4()
    return note


# =============================================================================
# Opportunity Number Generation Tests
# =============================================================================


class TestOpportunityNumberGeneration:
    """Tests for opportunity number generation."""
    
    @pytest.mark.asyncio
    async def test_generate_opportunity_number_first_of_year(self):
        """Should generate first opportunity number for year."""
        db = AsyncMock()
        db.execute = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        number = await generate_opportunity_number(db)
        
        year = datetime.now().year
        assert number == f"OPP-{year}-00001"
    
    @pytest.mark.asyncio
    async def test_generate_opportunity_number_increment(self):
        """Should increment existing opportunity number."""
        db = AsyncMock()
        db.execute = AsyncMock()
        
        year = datetime.now().year
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=f"OPP-{year}-00099")
        db.execute.return_value = mock_result
        
        number = await generate_opportunity_number(db)
        
        assert number == f"OPP-{year}-00100"


class TestStageProbabilities:
    """Tests for stage probability mapping."""
    
    def test_stage_probabilities_defined(self):
        """Should have probabilities for all stages."""
        for stage in OpportunityStage:
            assert stage.value in STAGE_PROBABILITIES
    
    def test_closed_won_is_100_percent(self):
        """Closed won should be 100% probability."""
        assert STAGE_PROBABILITIES[OpportunityStage.CLOSED_WON.value] == 100
    
    def test_closed_lost_is_0_percent(self):
        """Closed lost should be 0% probability."""
        assert STAGE_PROBABILITIES[OpportunityStage.CLOSED_LOST.value] == 0
    
    def test_probabilities_increase_through_pipeline(self):
        """Probabilities should generally increase through pipeline stages."""
        stages_in_order = [
            OpportunityStage.PROSPECTING.value,
            OpportunityStage.QUALIFICATION.value,
            OpportunityStage.NEEDS_ANALYSIS.value,
            OpportunityStage.VALUE_PROPOSITION.value,
            OpportunityStage.PROPOSAL.value,
            OpportunityStage.NEGOTIATION.value,
        ]
        
        probs = [STAGE_PROBABILITIES[s] for s in stages_in_order]
        
        # Each probability should be >= the previous
        for i in range(1, len(probs)):
            assert probs[i] >= probs[i - 1]


# =============================================================================
# Opportunity CRUD Tests
# =============================================================================


class TestListOpportunities:
    """Tests for listing opportunities."""
    
    @pytest.mark.asyncio
    async def test_list_opportunities_empty(self, mock_user):
        """Should return empty list when no opportunities exist."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            stage=None,
            account_id=None,
            assigned_to_id=None,
            is_closed=None,
            is_won=None,
            min_amount=None,
            max_amount=None,
            close_date_before=None,
            close_date_after=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data == []
        assert response.pagination.total_items == 0
    
    @pytest.mark.asyncio
    async def test_list_opportunities_with_results(self, mock_user, sample_opportunity):
        """Should return list of opportunities."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            stage=None,
            account_id=None,
            assigned_to_id=None,
            is_closed=None,
            is_won=None,
            min_amount=None,
            max_amount=None,
            close_date_before=None,
            close_date_after=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.data) == 1
        assert response.data[0].opportunity_number == "OPP-2025-00001"
    
    @pytest.mark.asyncio
    async def test_list_opportunities_filter_by_stage(self, mock_user, sample_opportunity):
        """Should filter opportunities by stage."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            stage=OpportunityStage.PROPOSAL.value,
            account_id=None,
            assigned_to_id=None,
            is_closed=None,
            is_won=None,
            min_amount=None,
            max_amount=None,
            close_date_before=None,
            close_date_after=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_opportunities_filter_open_only(self, mock_user, sample_opportunity):
        """Should filter only open opportunities."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            stage=None,
            account_id=None,
            assigned_to_id=None,
            is_closed=False,
            is_won=None,
            min_amount=None,
            max_amount=None,
            close_date_before=None,
            close_date_after=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_opportunities_filter_by_amount_range(self, mock_user, sample_opportunity):
        """Should filter opportunities by amount range."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            stage=None,
            account_id=None,
            assigned_to_id=None,
            is_closed=None,
            is_won=None,
            min_amount=Decimal("100000"),
            max_amount=Decimal("1000000"),
            close_date_before=None,
            close_date_after=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_opportunities_filter_by_close_date_range(self, mock_user, sample_opportunity):
        """Should filter opportunities by expected close date range."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            stage=None,
            account_id=None,
            assigned_to_id=None,
            is_closed=None,
            is_won=None,
            min_amount=None,
            max_amount=None,
            close_date_before=date.today() + timedelta(days=60),
            close_date_after=date.today(),
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True


class TestCreateOpportunity:
    """Tests for opportunity creation."""
    
    @pytest.mark.asyncio
    async def test_create_opportunity_success(self, mock_user, account_id, primary_contact_id):
        """Should create an opportunity successfully."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        created_opp = None
        
        def capture_add(opp):
            nonlocal created_opp
            created_opp = opp
            opp.id = uuid4()
            opp.opportunity_number = "OPP-2025-00001"
            opp.weighted_amount = Decimal("30000.00")
            opp.currency = "MAD"
            opp.created_at = datetime.now(timezone.utc)
            opp.updated_at = datetime.now(timezone.utc)
            opp.notes = MagicMock()
            opp.notes.all = MagicMock(return_value=[])
            opp.rfqs = MagicMock()
            opp.rfqs.all = MagicMock(return_value=[])
            opp.quotes = MagicMock()
            opp.quotes.all = MagicMock(return_value=[])
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        opp_data = OpportunityCreate(
            name="New Opportunity",
            account_id=account_id,
            primary_contact_id=primary_contact_id,
            amount=Decimal("100000.00"),
            stage=OpportunityStage.QUALIFICATION.value,
        )
        
        response = await create_opportunity(
            opp_data=opp_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.add.called
        assert db.commit.called
        # Probability should be set based on stage
        assert created_opp.probability == STAGE_PROBABILITIES[OpportunityStage.QUALIFICATION.value]
    
    @pytest.mark.asyncio
    async def test_create_opportunity_default_probability(self, mock_user, account_id):
        """Should set default probability based on stage."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        created_opp = None
        
        def capture_add(opp):
            nonlocal created_opp
            created_opp = opp
            opp.id = uuid4()
            opp.opportunity_number = "OPP-2025-00001"
            opp.weighted_amount = None
            opp.currency = "MAD"
            opp.created_at = datetime.now(timezone.utc)
            opp.updated_at = datetime.now(timezone.utc)
            opp.notes = MagicMock()
            opp.notes.all = MagicMock(return_value=[])
            opp.rfqs = MagicMock()
            opp.rfqs.all = MagicMock(return_value=[])
            opp.quotes = MagicMock()
            opp.quotes.all = MagicMock(return_value=[])
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        opp_data = OpportunityCreate(
            name="New Opportunity",
            account_id=account_id,
            # Using default stage (PROSPECTING)
        )
        
        await create_opportunity(
            opp_data=opp_data,
            db=db,
            current_user=mock_user,
        )
        
        # Default stage probability should be applied
        assert created_opp.probability == STAGE_PROBABILITIES[OpportunityStage.PROSPECTING.value]


class TestGetOpportunity:
    """Tests for getting a single opportunity."""
    
    @pytest.mark.asyncio
    async def test_get_opportunity_success(self, mock_user, sample_opportunity):
        """Should return opportunity by ID."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        response = await get_opportunity(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data.opportunity_number == sample_opportunity.opportunity_number
    
    @pytest.mark.asyncio
    async def test_get_opportunity_not_found(self, mock_user):
        """Should return 404 for non-existent opportunity."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_opportunity(
                opportunity_id=uuid4(),
                db=db,
                current_user=mock_user,
                include_deleted=False,
            )


class TestUpdateOpportunity:
    """Tests for updating opportunities."""
    
    @pytest.mark.asyncio
    async def test_update_opportunity_success(self, mock_user, sample_opportunity):
        """Should update opportunity successfully."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        update_data = OpportunityUpdate(
            name="Updated Opportunity Name",
            amount=Decimal("600000.00"),
        )
        
        response = await update_opportunity(
            opportunity_id=sample_opportunity.id,
            opp_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.commit.called
        # Weighted amount should be recalculated
        assert sample_opportunity.calculate_weighted_amount.called
    
    @pytest.mark.asyncio
    async def test_update_opportunity_probability_recalculates(self, mock_user, sample_opportunity):
        """Should recalculate weighted amount when probability changes."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        update_data = OpportunityUpdate(
            probability=80,
        )
        
        await update_opportunity(
            opportunity_id=sample_opportunity.id,
            opp_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert sample_opportunity.calculate_weighted_amount.called


class TestDeleteOpportunity:
    """Tests for deleting opportunities."""
    
    @pytest.mark.asyncio
    async def test_delete_opportunity_soft(self, mock_user, sample_opportunity):
        """Should soft delete opportunity by default."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        response = await delete_opportunity(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response.success is True
        assert sample_opportunity.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_opportunity_hard_as_superuser(self, mock_superuser, sample_opportunity):
        """Should hard delete opportunity as superuser."""
        db = AsyncMock()
        db.delete = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        response = await delete_opportunity(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_superuser,
            hard_delete=True,
        )
        
        assert response.success is True
        assert db.delete.called
    
    @pytest.mark.asyncio
    async def test_delete_opportunity_hard_forbidden(self, mock_user, sample_opportunity):
        """Should forbid hard delete for non-superuser."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ForbiddenError
        
        with pytest.raises(ForbiddenError):
            await delete_opportunity(
                opportunity_id=sample_opportunity.id,
                db=db,
                current_user=mock_user,
                hard_delete=True,
            )


# =============================================================================
# Stage/Workflow Tests
# =============================================================================


class TestStageWorkflow:
    """Tests for opportunity stage/workflow management."""
    
    @pytest.mark.asyncio
    async def test_change_stage_success(self, mock_user, sample_opportunity):
        """Should change opportunity stage."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        request = StageChangeRequest(
            stage=OpportunityStage.NEGOTIATION.value,
            notes="Moving to negotiation phase",
        )
        
        response = await change_opportunity_stage(
            opportunity_id=sample_opportunity.id,
            request=request,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_opportunity.stage == OpportunityStage.NEGOTIATION.value
        # Probability should be updated
        assert sample_opportunity.probability == STAGE_PROBABILITIES[OpportunityStage.NEGOTIATION.value]
    
    @pytest.mark.asyncio
    async def test_change_stage_closed_opportunity_fails(self, mock_user, sample_opportunity):
        """Should fail to change stage of closed opportunity."""
        db = AsyncMock()
        
        # Make the opportunity appear closed
        sample_opportunity.is_closed = True
        sample_opportunity.is_open = False
        sample_opportunity.stage = OpportunityStage.CLOSED_WON.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = StageChangeRequest(stage=OpportunityStage.NEGOTIATION.value)
        
        with pytest.raises(ConflictError):
            await change_opportunity_stage(
                opportunity_id=sample_opportunity.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_change_stage_invalid_stage(self, mock_user, sample_opportunity):
        """Should fail for invalid stage."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = StageChangeRequest(stage="INVALID_STAGE")
        
        with pytest.raises(ConflictError):
            await change_opportunity_stage(
                opportunity_id=sample_opportunity.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_close_won(self, mock_user, sample_opportunity):
        """Should close opportunity as won."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.add = MagicMock()
        db.refresh = AsyncMock()
        
        request = CloseWonRequest(
            notes="Deal signed!",
        )
        
        response = await close_opportunity_won(
            opportunity_id=sample_opportunity.id,
            request=request,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_opportunity.stage == OpportunityStage.CLOSED_WON.value
        assert sample_opportunity.is_closed is True
        assert sample_opportunity.is_won is True
        assert sample_opportunity.probability == 100
    
    @pytest.mark.asyncio
    async def test_close_won_already_closed(self, mock_user, sample_opportunity):
        """Should fail to close already closed opportunity."""
        db = AsyncMock()
        
        # Make the opportunity appear closed
        sample_opportunity.is_closed = True
        sample_opportunity.is_open = False
        sample_opportunity.stage = OpportunityStage.CLOSED_WON.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = CloseWonRequest()
        
        with pytest.raises(ConflictError):
            await close_opportunity_won(
                opportunity_id=sample_opportunity.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_close_lost(self, mock_user, sample_opportunity):
        """Should close opportunity as lost."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.add = MagicMock()
        db.refresh = AsyncMock()
        
        competitor_uuid = uuid4()
        request = CloseLostRequest(
            close_reason="Price was too high",
            competitor_id=competitor_uuid,
        )
        
        response = await close_opportunity_lost(
            opportunity_id=sample_opportunity.id,
            request=request,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_opportunity.stage == OpportunityStage.CLOSED_LOST.value
        assert sample_opportunity.is_closed is True
        assert sample_opportunity.is_won is False
        assert sample_opportunity.probability == 0
        assert sample_opportunity.close_reason == "Price was too high"
        assert sample_opportunity.competitor_id == competitor_uuid
    
    @pytest.mark.asyncio
    async def test_reopen_opportunity(self, mock_user, sample_opportunity):
        """Should reopen a closed opportunity."""
        db = AsyncMock()
        
        # Make the opportunity appear closed
        sample_opportunity.is_closed = True
        sample_opportunity.is_open = False
        sample_opportunity.is_won = False
        sample_opportunity.stage = OpportunityStage.CLOSED_LOST.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.add = MagicMock()
        db.refresh = AsyncMock()
        
        response = await reopen_opportunity(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            stage=OpportunityStage.PROPOSAL.value,
        )
        
        assert response.success is True
        assert sample_opportunity.is_closed is False
        assert sample_opportunity.is_won is None
        assert sample_opportunity.stage == OpportunityStage.PROPOSAL.value
    
    @pytest.mark.asyncio
    async def test_reopen_not_closed(self, mock_user, sample_opportunity):
        """Should fail to reopen opportunity that is not closed."""
        db = AsyncMock()
        
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        with pytest.raises(ConflictError):
            await reopen_opportunity(
                opportunity_id=sample_opportunity.id,
                db=db,
                current_user=mock_user,
                stage=None,
            )


# =============================================================================
# Notes Tests
# =============================================================================


class TestOpportunityNotes:
    """Tests for opportunity notes management."""
    
    @pytest.mark.asyncio
    async def test_list_notes_empty(self, mock_user, sample_opportunity):
        """Should return empty list when no notes exist."""
        db = AsyncMock()
        
        opp_result = MagicMock()
        opp_result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        
        notes_result = MagicMock()
        notes_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[opp_result, notes_result])
        
        response = await list_opportunity_notes(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            note_type=None,
        )
        
        assert response.success is True
        assert response.data == []
    
    @pytest.mark.asyncio
    async def test_list_notes_with_results(self, mock_user, sample_opportunity, sample_note):
        """Should return list of notes."""
        db = AsyncMock()
        
        sample_note.opportunity_id = sample_opportunity.id
        
        opp_result = MagicMock()
        opp_result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        
        notes_result = MagicMock()
        notes_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_note])))
        
        db.execute = AsyncMock(side_effect=[opp_result, notes_result])
        
        response = await list_opportunity_notes(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            note_type=None,
        )
        
        assert response.success is True
        assert len(response.data) == 1
    
    @pytest.mark.asyncio
    async def test_list_notes_filter_by_type(self, mock_user, sample_opportunity, sample_note):
        """Should filter notes by type."""
        db = AsyncMock()
        
        opp_result = MagicMock()
        opp_result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        
        notes_result = MagicMock()
        notes_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_note])))
        
        db.execute = AsyncMock(side_effect=[opp_result, notes_result])
        
        response = await list_opportunity_notes(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            note_type=NoteType.MEETING.value,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_add_note(self, mock_user, sample_opportunity):
        """Should add a note to opportunity."""
        db = AsyncMock()
        
        opp_result = MagicMock()
        opp_result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = opp_result
        
        def capture_add(n):
            n.id = uuid4()
            n.opportunity_id = sample_opportunity.id
            n.created_at = datetime.now(timezone.utc)
            n.updated_at = datetime.now(timezone.utc)
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        note_data = NoteCreate(
            content="Customer is interested in expanding scope",
            note_type=NoteType.CALL.value,
        )
        
        response = await add_opportunity_note(
            opportunity_id=sample_opportunity.id,
            note_data=note_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.add.called
    
    @pytest.mark.asyncio
    async def test_update_note(self, mock_user, sample_note):
        """Should update a note."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_note)
        db.execute.return_value = result
        db.refresh = AsyncMock()
        
        update_data = NoteUpdate(
            content="Updated note content",
        )
        
        response = await update_opportunity_note(
            opportunity_id=sample_note.opportunity_id,
            note_id=sample_note.id,
            note_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_note.content == "Updated note content"
    
    @pytest.mark.asyncio
    async def test_delete_note(self, mock_user, sample_note):
        """Should delete a note."""
        db = AsyncMock()
        db.delete = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_note)
        db.execute.return_value = result
        
        response = await delete_opportunity_note(
            opportunity_id=sample_note.opportunity_id,
            note_id=sample_note.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.delete.called


# =============================================================================
# Pipeline and Forecasting Tests
# =============================================================================


class TestPipelineAndForecasting:
    """Tests for pipeline summary and forecasting."""
    
    @pytest.mark.asyncio
    async def test_pipeline_summary(self, mock_user):
        """Should return pipeline summary by stage."""
        db = AsyncMock()
        
        # Mock query result with stage aggregations
        result = MagicMock()
        result.all = MagicMock(return_value=[
            MagicMock(
                stage=OpportunityStage.PROPOSAL.value,
                count=5,
                total_amount=Decimal("500000"),
                weighted_amount=Decimal("300000"),
            ),
            MagicMock(
                stage=OpportunityStage.NEGOTIATION.value,
                count=3,
                total_amount=Decimal("300000"),
                weighted_amount=Decimal("240000"),
            ),
        ])
        db.execute.return_value = result
        
        response = await get_pipeline_summary(
            db=db,
            current_user=mock_user,
            account_id=None,
            assigned_to_id=None,
        )
        
        assert response.success is True
        data = response.data
        assert "stages" in data
        assert "totals" in data
    
    @pytest.mark.asyncio
    async def test_pipeline_summary_with_filter(self, mock_user, account_id):
        """Should filter pipeline summary by account."""
        db = AsyncMock()
        
        result = MagicMock()
        result.all = MagicMock(return_value=[])
        db.execute.return_value = result
        
        response = await get_pipeline_summary(
            db=db,
            current_user=mock_user,
            account_id=account_id,
            assigned_to_id=None,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_forecast(self, mock_user, sample_opportunity):
        """Should return forecast for a period."""
        db = AsyncMock()
        
        sample_opportunity.probability = 80
        sample_opportunity.amount = Decimal("100000")
        sample_opportunity.weighted_amount = Decimal("80000")
        
        result = MagicMock()
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        db.execute.return_value = result
        
        response = await get_forecast(
            db=db,
            current_user=mock_user,
            period_start=date.today(),
            period_end=date.today() + timedelta(days=90),
            account_id=None,
            assigned_to_id=None,
        )
        
        assert response.success is True
        data = response.data
        assert "period" in data
        assert "commit" in data
        assert "best_case" in data
        assert "pipeline" in data
        assert "weighted_pipeline" in data
    
    @pytest.mark.asyncio
    async def test_forecast_bands(self, mock_user):
        """Should categorize opportunities into forecast bands."""
        db = AsyncMock()
        
        # Create opportunities with different probabilities
        opps = []
        for prob in [90, 60, 30]:  # commit, best_case, pipeline only
            opp = MagicMock()
            opp.probability = prob
            opp.amount = Decimal("100000")
            opp.weighted_amount = Decimal(str(100000 * prob / 100))
            opps.append(opp)
        
        result = MagicMock()
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=opps)))
        db.execute.return_value = result
        
        response = await get_forecast(
            db=db,
            current_user=mock_user,
            period_start=date.today(),
            period_end=date.today() + timedelta(days=90),
            account_id=None,
            assigned_to_id=None,
        )
        
        data = response.data
        
        # Commit band: prob >= 80 -> 1 opp
        assert data["commit"]["count"] == 1
        
        # Best case band: prob >= 50 -> 2 opps
        assert data["best_case"]["count"] == 2
        
        # Pipeline band: all opps -> 3 opps
        assert data["pipeline"]["count"] == 3


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_opportunity_to_response(self, sample_opportunity):
        """Should convert opportunity model to response."""
        response = opportunity_to_response(sample_opportunity)
        
        assert response.id == sample_opportunity.id
        assert response.opportunity_number == sample_opportunity.opportunity_number
        assert response.name == sample_opportunity.name
        assert response.stage == sample_opportunity.stage
        assert response.amount == sample_opportunity.amount
    
    def test_opportunity_to_list_response(self, sample_opportunity):
        """Should convert opportunity model to list response."""
        response = opportunity_to_list_response(sample_opportunity)
        
        assert response.id == sample_opportunity.id
        assert response.opportunity_number == sample_opportunity.opportunity_number
        assert response.name == sample_opportunity.name
        assert response.stage == sample_opportunity.stage
    
    def test_note_to_response(self, sample_note):
        """Should convert note model to response."""
        response = note_to_response(sample_note)
        
        assert response.id == sample_note.id
        assert response.content == sample_note.content
        assert response.note_type == sample_note.note_type


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_opportunity_not_found(self, mock_user):
        """Should return 404 for non-existent opportunity."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_opportunity(
                opportunity_id=uuid4(),
                db=db,
                current_user=mock_user,
                include_deleted=False,
            )
    
    @pytest.mark.asyncio
    async def test_note_not_found(self, mock_user):
        """Should return 404 for non-existent note."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await update_opportunity_note(
                opportunity_id=uuid4(),
                note_id=uuid4(),
                note_data=NoteUpdate(content="Test"),
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_list_opportunities_search(self, mock_user, sample_opportunity):
        """Should search opportunities by name."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_opportunity])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_opportunities(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search="Manufacturing",
            stage=None,
            account_id=None,
            assigned_to_id=None,
            is_closed=None,
            is_won=None,
            min_amount=None,
            max_amount=None,
            close_date_before=None,
            close_date_after=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_reopen_with_default_stage(self, mock_user, sample_opportunity):
        """Should reopen with default stage when not specified."""
        db = AsyncMock()
        
        # Make the opportunity appear closed
        sample_opportunity.is_closed = True
        sample_opportunity.is_open = False
        sample_opportunity.stage = OpportunityStage.CLOSED_LOST.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_opportunity)
        db.execute.return_value = result
        db.add = MagicMock()
        db.refresh = AsyncMock()
        
        response = await reopen_opportunity(
            opportunity_id=sample_opportunity.id,
            db=db,
            current_user=mock_user,
            stage=None,  # Should default to NEGOTIATION
        )
        
        assert response.success is True
        assert sample_opportunity.stage == OpportunityStage.NEGOTIATION.value

"""
Comprehensive Tests for Quote Endpoints

Tests all Quote functionality including:
- CRUD operations
- Line item management
- Version control
- Approval workflow
- Customer acceptance flow
- Edge cases and error handling
"""

from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi import status

from sensei.api.v1.endpoints.quotes import (
    router,
    list_quotes,
    create_quote,
    get_quote,
    update_quote,
    delete_quote,
    list_quote_line_items,
    add_quote_line_item,
    update_quote_line_item,
    delete_quote_line_item,
    submit_quote_for_approval,
    handle_quote_approval,
    send_quote,
    mark_quote_viewed,
    accept_quote,
    reject_quote,
    list_quote_versions,
    get_quote_version,
    revise_quote,
    get_quote_stats,
    QuoteCreate,
    QuoteUpdate,
    LineItemCreate,
    LineItemUpdate,
    ApprovalRequest,
    SendQuoteRequest,
    quote_to_response,
    quote_to_list_response,
    line_item_to_response,
    version_to_response,
    generate_quote_number,
    get_next_line_number,
    recalculate_quote_totals,
)
from sensei.models.quote import (
    Quote,
    QuoteStatus,
    ApprovalStatus,
    LineItemType,
    VersionStatus,
    QuoteVersion,
    QuoteLineItem,
)


def _scalar_result(value):
    result = MagicMock()
    result.scalar = MagicMock(return_value=value)
    return result


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
def sample_quote(account_id):
    """Create a sample quote model."""
    quote = MagicMock(spec=Quote)
    quote.id = uuid4()
    quote.quote_number = "Q-2025-00001"
    quote.title = "Quote for Precision Parts"
    quote.description = "Manufacturing quote for machined components"
    quote.account_id = account_id
    quote.rfq_id = None
    quote.opportunity_id = None
    quote.status = QuoteStatus.DRAFT.value
    quote.previous_status = None
    quote.status_changed_at = None
    quote.current_version = 1
    quote.currency = "MAD"
    quote.exchange_rate = Decimal("1.0")
    quote.subtotal = Decimal("10000.00")
    quote.discount_percentage = Decimal("5.0")
    quote.discount_amount = Decimal("500.00")
    quote.tax_rate = Decimal("20.0")
    quote.tax_amount = Decimal("1900.00")
    quote.total = Decimal("11400.00")
    quote.total_cost = Decimal("7000.00")
    quote.target_margin = Decimal("40.0")
    quote.actual_margin = Decimal("38.6")
    quote.payment_terms = "Net 30"
    quote.delivery_terms = "DDP Casablanca"
    quote.lead_time_days = 45
    quote.valid_from = date.today()
    quote.valid_until = date.today() + timedelta(days=30)
    quote.is_valid = True
    quote.sent_at = None
    quote.viewed_at = None
    quote.accepted_at = None
    quote.rejected_at = None
    quote.approval_status = ApprovalStatus.NOT_REQUIRED.value
    quote.requires_approval = False
    quote.approval_threshold = None
    quote.approved_by_id = None
    quote.approved_at = None
    quote.rejection_reason = None
    quote.internal_notes = "Priority customer"
    quote.terms_and_conditions = "Standard T&C apply"
    quote.custom_fields = {}
    quote.tags = ["machining", "priority"]
    quote.created_at = datetime.now(timezone.utc)
    quote.updated_at = datetime.now(timezone.utc)
    quote.created_by_id = uuid4()
    quote.deleted_at = None
    
    # Mock relationships
    quote.line_items = MagicMock()
    quote.line_items.all = MagicMock(return_value=[])
    quote.versions = MagicMock()
    quote.versions.all = MagicMock(return_value=[])
    
    return quote


@pytest.fixture
def sample_line_item():
    """Create a sample quote line item."""
    item = MagicMock(spec=QuoteLineItem)
    item.id = uuid4()
    item.quote_id = uuid4()
    item.line_number = 1
    item.part_number = "PART-001"
    item.description = "Precision Machined Shaft"
    item.item_type = LineItemType.PRODUCT.value
    item.quantity = Decimal("100")
    item.unit_of_measure = "EA"
    item.unit_price = Decimal("100.00")
    item.discount_percentage = Decimal("0")
    item.discount_amount = Decimal("0")
    item.line_total = Decimal("10000.00")
    item.unit_cost = Decimal("70.00")
    item.cost_total = Decimal("7000.00")
    item.margin_percentage = Decimal("30.0")
    item.nre_cost = None
    item.tooling_cost = None
    item.quantity_breaks = None
    item.lead_time_days = None
    item.notes = None
    item.internal_notes = None
    item.is_included = True
    item.is_optional = False
    item.created_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    
    # Mock calculate method
    item.calculate_totals = MagicMock()
    
    return item


@pytest.fixture
def sample_version():
    """Create a sample quote version."""
    version = MagicMock(spec=QuoteVersion)
    version.id = uuid4()
    version.quote_id = uuid4()
    version.version_number = 1
    version.status = VersionStatus.FINAL.value
    version.snapshot = {
        "title": "Quote for Precision Parts",
        "total": "11400.00",
        "line_items": [],
    }
    version.change_summary = "Initial version"
    version.created_at = datetime.now(timezone.utc)
    version.created_by_id = uuid4()
    return version


# =============================================================================
# Quote Number Generation Tests
# =============================================================================


class TestQuoteNumberGeneration:
    """Tests for quote number generation."""
    
    @pytest.mark.asyncio
    async def test_generate_quote_number_first_of_year(self):
        """Should generate first quote number for year."""
        db = AsyncMock()
        db.execute = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        number = await generate_quote_number(db)
        
        year = datetime.now().year
        assert number == f"Q-{year}-00001"
    
    @pytest.mark.asyncio
    async def test_generate_quote_number_increment(self):
        """Should increment existing quote number."""
        db = AsyncMock()
        db.execute = AsyncMock()
        
        year = datetime.now().year
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=f"Q-{year}-00123")
        db.execute.return_value = mock_result
        
        number = await generate_quote_number(db)
        
        assert number == f"Q-{year}-00124"


class TestNextLineNumber:
    """Tests for line number generation."""
    
    @pytest.mark.asyncio
    async def test_get_next_line_number_first_item(self):
        """Should return 1 for first line item."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        line_number = await get_next_line_number(db, uuid4())
        
        assert line_number == 1
    
    @pytest.mark.asyncio
    async def test_get_next_line_number_increment(self):
        """Should increment from max line number."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=5)
        db.execute.return_value = mock_result
        
        line_number = await get_next_line_number(db, uuid4())
        
        assert line_number == 6


# =============================================================================
# Quote CRUD Tests
# =============================================================================


class TestListQuotes:
    """Tests for listing quotes."""
    
    @pytest.mark.asyncio
    async def test_list_quotes_empty(self, mock_user):
        """Should return empty list when no quotes exist."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_quotes(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            account_id=None,
            rfq_id=None,
            opportunity_id=None,
            approval_status=None,
            is_valid=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data == []
        assert response.pagination.total_items == 0
    
    @pytest.mark.asyncio
    async def test_list_quotes_with_results(self, mock_user, sample_quote):
        """Should return list of quotes."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_quote])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_quotes(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            account_id=None,
            rfq_id=None,
            opportunity_id=None,
            approval_status=None,
            is_valid=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.data) == 1
        assert response.data[0].quote_number == "Q-2025-00001"
    
    @pytest.mark.asyncio
    async def test_list_quotes_filter_by_status(self, mock_user, sample_quote):
        """Should filter quotes by status."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_quote])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_quotes(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=QuoteStatus.DRAFT.value,
            account_id=None,
            rfq_id=None,
            opportunity_id=None,
            approval_status=None,
            is_valid=None,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_quotes_filter_valid_only(self, mock_user, sample_quote):
        """Should filter only valid quotes."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=1)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_quote])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_quotes(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            account_id=None,
            rfq_id=None,
            opportunity_id=None,
            approval_status=None,
            is_valid=True,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_list_quotes_filter_expired(self, mock_user, sample_quote):
        """Should filter expired quotes."""
        db = AsyncMock()
        
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        response = await list_quotes(
            db=db,
            current_user=mock_user,
            page=1,
            page_size=50,
            search=None,
            status=None,
            account_id=None,
            rfq_id=None,
            opportunity_id=None,
            approval_status=None,
            is_valid=False,  # Expired quotes
            sort="-created_at",
            include_deleted=False,
        )
        
        assert response.success is True


class TestCreateQuote:
    """Tests for quote creation."""
    
    @pytest.mark.asyncio
    async def test_create_quote_success(self, mock_user, account_id):
        """Should create a quote successfully."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        created_quote = None
        
        def capture_add(quote):
            nonlocal created_quote
            created_quote = quote
            quote.id = uuid4()
            quote.quote_number = "Q-2025-00001"
            quote.is_valid = True
            quote.created_at = datetime.now(timezone.utc)
            quote.updated_at = datetime.now(timezone.utc)
            quote.line_items = MagicMock()
            quote.line_items.all = MagicMock(return_value=[])
            quote.versions = MagicMock()
            quote.versions.all = MagicMock(return_value=[])
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        quote_data = QuoteCreate(
            title="Test Quote",
            account_id=account_id,
            
            payment_terms="Net 30",
            delivery_terms="DDP",
        )
        
        response = await create_quote(
            quote_data=quote_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.add.called
        assert db.commit.called
        assert created_quote.status == QuoteStatus.DRAFT.value
        assert created_quote.current_version == 1
        assert created_quote.approval_status == ApprovalStatus.NOT_REQUIRED.value
    
    @pytest.mark.asyncio
    async def test_create_quote_sets_valid_from(self, mock_user, account_id):
        """Should set valid_from to today if not provided."""
        db = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        db.execute.return_value = mock_result
        
        created_quote = None
        
        def capture_add(quote):
            nonlocal created_quote
            created_quote = quote
            quote.id = uuid4()
            quote.quote_number = "Q-2025-00001"
            quote.is_valid = True
            quote.created_at = datetime.now(timezone.utc)
            quote.updated_at = datetime.now(timezone.utc)
            quote.line_items = MagicMock()
            quote.line_items.all = MagicMock(return_value=[])
            quote.versions = MagicMock()
            quote.versions.all = MagicMock(return_value=[])
        
        db.add = MagicMock(side_effect=capture_add)
        db.refresh = AsyncMock()
        
        quote_data = QuoteCreate(
            title="Test Quote",
            account_id=account_id,
        )
        
        await create_quote(
            quote_data=quote_data,
            db=db,
            current_user=mock_user,
        )
        
        assert created_quote.valid_from == date.today()


class TestGetQuote:
    """Tests for getting a single quote."""
    
    @pytest.mark.asyncio
    async def test_get_quote_success(self, mock_user, sample_quote):
        """Should return quote by ID."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        
        response = await get_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data.quote_number == sample_quote.quote_number
    
    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, mock_user):
        """Should return 404 for non-existent quote."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_quote(
                quote_id=uuid4(),
                db=db,
                current_user=mock_user,
                include_deleted=False,
            )


class TestUpdateQuote:
    """Tests for updating quotes."""
    
    @pytest.mark.asyncio
    async def test_update_quote_success(self, mock_user, sample_quote):
        """Should update quote successfully."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        update_data = QuoteUpdate(
            title="Updated Quote Title",
            payment_terms="Net 45",
        )
        
        response = await update_quote(
            quote_id=sample_quote.id,
            quote_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.commit.called
    
    @pytest.mark.asyncio
    async def test_update_quote_cannot_modify_sent(self, mock_user, sample_quote):
        """Should not allow modifying sent quotes."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.SENT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        update_data = QuoteUpdate(title="New Title")
        
        with pytest.raises(ConflictError):
            await update_quote(
                quote_id=sample_quote.id,
                quote_data=update_data,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_update_quote_cannot_modify_accepted(self, mock_user, sample_quote):
        """Should not allow modifying accepted quotes."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.ACCEPTED.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        update_data = QuoteUpdate(title="New Title")
        
        with pytest.raises(ConflictError):
            await update_quote(
                quote_id=sample_quote.id,
                quote_data=update_data,
                db=db,
                current_user=mock_user,
            )


class TestDeleteQuote:
    """Tests for deleting quotes."""
    
    @pytest.mark.asyncio
    async def test_delete_quote_soft(self, mock_user, sample_quote):
        """Should soft delete quote by default."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        response = await delete_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response.success is True
        assert sample_quote.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_quote_hard_as_superuser(self, mock_superuser, sample_quote):
        """Should hard delete quote as superuser."""
        db = AsyncMock()
        db.delete = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        response = await delete_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_superuser,
            hard_delete=True,
        )
        
        assert response.success is True
        assert db.delete.called
    
    @pytest.mark.asyncio
    async def test_delete_quote_hard_forbidden(self, mock_user, sample_quote):
        """Should forbid hard delete for non-superuser."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ForbiddenError
        
        with pytest.raises(ForbiddenError):
            await delete_quote(
                quote_id=sample_quote.id,
                db=db,
                current_user=mock_user,
                hard_delete=True,
            )


# =============================================================================
# Line Item Tests
# =============================================================================


class TestLineItems:
    """Tests for quote line item management."""
    
    @pytest.mark.asyncio
    async def test_list_line_items_empty(self, mock_user, sample_quote):
        """Should return empty list when no line items exist."""
        db = AsyncMock()
        
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[quote_result, items_result])
        
        response = await list_quote_line_items(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data == []
    
    @pytest.mark.asyncio
    async def test_list_line_items_with_results(self, mock_user, sample_quote, sample_line_item):
        """Should return list of line items."""
        db = AsyncMock()
        
        sample_line_item.quote_id = sample_quote.id
        
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_line_item])))
        
        db.execute = AsyncMock(side_effect=[quote_result, items_result])
        
        response = await list_quote_line_items(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert len(response.data) == 1
    
    @pytest.mark.asyncio
    async def test_add_line_item(self, mock_user, sample_quote):
        """Should add a line item to quote."""
        db = AsyncMock()
        
        # Mock for quote lookup
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        # Mock for line number
        line_result = MagicMock()
        line_result.scalar = MagicMock(return_value=None)
        
        # Mock for recalculate (items query)
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[quote_result, line_result, items_result])
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        
        def capture_add(item):
            item.id = uuid4()
            item.quote_id = sample_quote.id
            item.line_number = 1
            item.line_total = Decimal("10000.00")
            item.cost_total = Decimal("7000.00")
            item.discount_amount = Decimal("0")
            item.unit_of_measure = "EA"
            item.margin_percentage = Decimal("30.0")
            item.created_at = datetime.now(timezone.utc)
            item.updated_at = datetime.now(timezone.utc)
        
        db.add = MagicMock(side_effect=capture_add)
        
        item_data = LineItemCreate(
            part_number="PART-001",
            description="Precision Shaft",
            quantity=100,
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("70.00"),
        )
        
        response = await add_quote_line_item(
            quote_id=sample_quote.id,
            item_data=item_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.add.called
    
    @pytest.mark.asyncio
    async def test_add_line_item_cannot_modify_sent(self, mock_user, sample_quote):
        """Should not allow adding items to sent quotes."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.SENT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        item_data = LineItemCreate(
            description="New Item",
            quantity=10,
            unit_price=Decimal("50.00"),
        )
        
        with pytest.raises(ConflictError):
            await add_quote_line_item(
                quote_id=sample_quote.id,
                item_data=item_data,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_update_line_item(self, mock_user, sample_quote, sample_line_item):
        """Should update a line item."""
        db = AsyncMock()
        
        sample_line_item.quote_id = sample_quote.id
        
        # Quote lookup
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        # Item lookup
        item_result = MagicMock()
        item_result.scalar_one_or_none = MagicMock(return_value=sample_line_item)
        
        # Items for recalculate
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_line_item])))
        
        db.execute = AsyncMock(side_effect=[quote_result, item_result, items_result])
        db.refresh = AsyncMock()
        
        update_data = LineItemUpdate(
            quantity=200,
            unit_price=Decimal("90.00"),
        )
        
        response = await update_quote_line_item(
            quote_id=sample_quote.id,
            item_id=sample_line_item.id,
            item_data=update_data,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_line_item.calculate_totals.called
    
    @pytest.mark.asyncio
    async def test_delete_line_item(self, mock_user, sample_quote, sample_line_item):
        """Should delete a line item."""
        db = AsyncMock()
        db.delete = AsyncMock()
        
        sample_line_item.quote_id = sample_quote.id
        
        # Quote lookup
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        # Item lookup
        item_result = MagicMock()
        item_result.scalar_one_or_none = MagicMock(return_value=sample_line_item)
        
        # Items for recalculate (empty after delete)
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[quote_result, item_result, items_result])
        
        response = await delete_quote_line_item(
            quote_id=sample_quote.id,
            item_id=sample_line_item.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert db.delete.called


# =============================================================================
# Quote Workflow Tests
# =============================================================================


class TestQuoteWorkflow:
    """Tests for quote workflow transitions."""
    
    @pytest.mark.asyncio
    async def test_submit_for_approval(self, mock_user, sample_quote):
        """Should submit quote for approval."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        response = await submit_quote_for_approval(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_quote.status == QuoteStatus.PENDING_APPROVAL.value
        assert sample_quote.approval_status == ApprovalStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_submit_for_approval_not_draft(self, mock_user, sample_quote):
        """Should fail to submit non-draft quote for approval."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.SENT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        with pytest.raises(ConflictError):
            await submit_quote_for_approval(
                quote_id=sample_quote.id,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_approve_quote(self, mock_user, sample_quote):
        """Should approve a quote."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.PENDING.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        request = ApprovalRequest(action="approve")
        
        response = await handle_quote_approval(
            quote_id=sample_quote.id,
            request=request,
            db=db,
            current_user=mock_user,
            _=None,
        )
        
        assert response.success is True
        assert sample_quote.approval_status == ApprovalStatus.APPROVED.value
        assert sample_quote.status == QuoteStatus.APPROVED.value
        assert sample_quote.approved_at is not None
    
    @pytest.mark.asyncio
    async def test_reject_quote(self, mock_user, sample_quote):
        """Should reject a quote."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.PENDING.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        request = ApprovalRequest(action="reject", reason="Margin too low")
        
        response = await handle_quote_approval(
            quote_id=sample_quote.id,
            request=request,
            db=db,
            current_user=mock_user,
            _=None,
        )
        
        assert response.success is True
        assert sample_quote.approval_status == ApprovalStatus.REJECTED.value
        assert sample_quote.status == QuoteStatus.DRAFT.value  # Returns to draft
        assert sample_quote.rejection_reason == "Margin too low"
    
    @pytest.mark.asyncio
    async def test_reject_quote_requires_reason(self, mock_user, sample_quote):
        """Should require reason for rejection."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.PENDING.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = ApprovalRequest(action="reject")
        
        with pytest.raises(ConflictError):
            await handle_quote_approval(
                quote_id=sample_quote.id,
                request=request,
                db=db,
                current_user=mock_user,
                _=None,
            )
    
    @pytest.mark.asyncio
    async def test_send_quote(self, mock_user, sample_quote):
        """Should send quote to customer."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.APPROVED.value
        
        # Quote lookup
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        # Items for version snapshot
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[result, items_result, _scalar_result(0), _scalar_result(0)])
        db.add = MagicMock()
        db.refresh = AsyncMock()
        
        request = SendQuoteRequest(send_method="email")
        
        response = await send_quote(
            quote_id=sample_quote.id,
            request=request,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_quote.status == QuoteStatus.SENT.value
        assert sample_quote.sent_at is not None
        # Version should be created
        assert db.add.called
    
    @pytest.mark.asyncio
    async def test_send_quote_pending_approval_fails(self, mock_user, sample_quote):
        """Should not allow sending quote pending approval."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.PENDING.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = SendQuoteRequest(send_method="email")
        
        with pytest.raises(ConflictError):
            await send_quote(
                quote_id=sample_quote.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_mark_quote_viewed(self, mock_user, sample_quote):
        """Should mark quote as viewed."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.SENT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        response = await mark_quote_viewed(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_quote.status == QuoteStatus.VIEWED.value
        assert sample_quote.viewed_at is not None
    
    @pytest.mark.asyncio
    async def test_accept_quote(self, mock_user, sample_quote):
        """Should accept quote."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.SENT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        response = await accept_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
            convert_to_order=False,
        )
        
        assert response.success is True
        assert sample_quote.status == QuoteStatus.ACCEPTED.value
        assert sample_quote.accepted_at is not None
    
    @pytest.mark.asyncio
    async def test_accept_quote_not_sent_fails(self, mock_user, sample_quote):
        """Should not accept quote that hasn't been sent."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.DRAFT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        with pytest.raises(ConflictError):
            await accept_quote(
                quote_id=sample_quote.id,
                db=db,
                current_user=mock_user,
                convert_to_order=False,
            )
    
    @pytest.mark.asyncio
    async def test_reject_quote_by_customer(self, mock_user, sample_quote):
        """Should reject quote by customer."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.SENT.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        response = await reject_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
            reason="Price too high",
        )
        
        assert response.success is True
        assert sample_quote.status == QuoteStatus.REJECTED.value
        assert sample_quote.rejected_at is not None


# =============================================================================
# Version Control Tests
# =============================================================================


class TestVersionControl:
    """Tests for quote version control."""
    
    @pytest.mark.asyncio
    async def test_list_versions(self, mock_user, sample_quote, sample_version):
        """Should list quote versions."""
        db = AsyncMock()
        
        sample_version.quote_id = sample_quote.id
        
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        versions_result = MagicMock()
        versions_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_version])))
        
        db.execute = AsyncMock(side_effect=[quote_result, versions_result])
        
        response = await list_quote_versions(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert len(response.data) == 1
    
    @pytest.mark.asyncio
    async def test_get_version(self, mock_user, sample_version):
        """Should get specific version."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_version)
        db.execute.return_value = result
        
        response = await get_quote_version(
            quote_id=sample_version.quote_id,
            version_number=sample_version.version_number,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data.version_number == sample_version.version_number
    
    @pytest.mark.asyncio
    async def test_revise_quote(self, mock_user, sample_quote):
        """Should create new revision of quote."""
        db = AsyncMock()
        
        # Quote lookup
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        # Items for version snapshot
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        db.execute = AsyncMock(side_effect=[result, items_result, _scalar_result(0), _scalar_result(0)])
        db.add = MagicMock()
        db.refresh = AsyncMock()
        
        old_version = sample_quote.current_version
        
        response = await revise_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
            change_summary="Updated pricing",
        )
        
        assert response.success is True
        assert sample_quote.current_version == old_version + 1
        assert sample_quote.status == QuoteStatus.REVISED.value
        # Old version should be created
        assert db.add.called


# =============================================================================
# Statistics Tests
# =============================================================================


class TestQuoteStats:
    """Tests for quote statistics."""
    
    @pytest.mark.asyncio
    async def test_get_quote_stats(self, mock_user, sample_quote, sample_line_item):
        """Should return quote statistics."""
        db = AsyncMock()
        
        sample_line_item.quote_id = sample_quote.id
        
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        items_result = MagicMock()
        items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_line_item])))
        
        db.execute = AsyncMock(side_effect=[quote_result, items_result])
        
        response = await get_quote_stats(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
        )
        
        assert response.success is True
        data = response.data
        assert data["quote_number"] == sample_quote.quote_number
        assert "line_items" in data
        assert "financials" in data
        assert data["line_items"]["count"] == 1


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_quote_to_response(self, sample_quote):
        """Should convert quote model to response."""
        response = quote_to_response(sample_quote)
        
        assert response.id == sample_quote.id
        assert response.quote_number == sample_quote.quote_number
        assert response.title == sample_quote.title
        assert response.status == sample_quote.status
        assert response.total == sample_quote.total
    
    def test_quote_to_list_response(self, sample_quote):
        """Should convert quote model to list response."""
        response = quote_to_list_response(sample_quote)
        
        assert response.id == sample_quote.id
        assert response.quote_number == sample_quote.quote_number
        assert response.title == sample_quote.title
    
    def test_line_item_to_response(self, sample_line_item):
        """Should convert line item model to response."""
        response = line_item_to_response(sample_line_item)
        
        assert response.id == sample_line_item.id
        assert response.part_number == sample_line_item.part_number
        assert response.quantity == sample_line_item.quantity
        assert response.line_total == sample_line_item.line_total
    
    def test_version_to_response(self, sample_version):
        """Should convert version model to response."""
        response = version_to_response(sample_version)
        
        assert response.id == sample_version.id
        assert response.version_number == sample_version.version_number
        assert response.snapshot == sample_version.snapshot


# =============================================================================
# Recalculation Tests
# =============================================================================


class TestRecalculation:
    """Tests for quote total recalculation."""
    
    @pytest.mark.asyncio
    async def test_recalculate_totals_empty(self, sample_quote):
        """Should handle quote with no line items."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        db.execute.return_value = result
        
        sample_quote.discount_percentage = None
        sample_quote.discount_amount = None
        sample_quote.tax_rate = None
        
        await recalculate_quote_totals(db, sample_quote)
        
        assert sample_quote.subtotal == Decimal("0")
        assert sample_quote.total == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_recalculate_totals_with_items(self, sample_quote, sample_line_item):
        """Should calculate totals from line items."""
        db = AsyncMock()
        
        sample_line_item.line_total = Decimal("10000.00")
        sample_line_item.cost_total = Decimal("7000.00")
        
        result = MagicMock()
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_line_item])))
        db.execute.return_value = result
        
        sample_quote.discount_percentage = Decimal("10")
        sample_quote.tax_rate = Decimal("20")
        
        await recalculate_quote_totals(db, sample_quote)
        
        assert sample_quote.subtotal == Decimal("10000.00")
        assert sample_quote.total_cost == Decimal("7000.00")
        assert sample_quote.discount_amount == Decimal("1000.00")  # 10% of 10000
        # Total = (10000 - 1000) * 1.20 = 10800
        assert sample_quote.total == Decimal("10800.00")
    
    @pytest.mark.asyncio
    async def test_recalculate_totals_with_fixed_discount(self, sample_quote, sample_line_item):
        """Should use fixed discount amount when provided."""
        db = AsyncMock()
        
        sample_line_item.line_total = Decimal("10000.00")
        sample_line_item.cost_total = Decimal("7000.00")
        
        result = MagicMock()
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_line_item])))
        db.execute.return_value = result
        
        sample_quote.discount_percentage = None
        sample_quote.discount_amount = Decimal("500.00")
        sample_quote.tax_rate = None
        
        await recalculate_quote_totals(db, sample_quote)
        
        assert sample_quote.discount_amount == Decimal("500.00")
        assert sample_quote.total == Decimal("9500.00")


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_quote_not_found(self, mock_user):
        """Should return 404 for non-existent quote."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_quote(
                quote_id=uuid4(),
                db=db,
                current_user=mock_user,
                include_deleted=False,
            )
    
    @pytest.mark.asyncio
    async def test_line_item_not_found(self, mock_user, sample_quote):
        """Should return 404 for non-existent line item."""
        db = AsyncMock()
        
        quote_result = MagicMock()
        quote_result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        
        item_result = MagicMock()
        item_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(side_effect=[quote_result, item_result])
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await update_quote_line_item(
                quote_id=sample_quote.id,
                item_id=uuid4(),
                item_data=LineItemUpdate(quantity=50),
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_version_not_found(self, mock_user):
        """Should return 404 for non-existent version."""
        db = AsyncMock()
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = result
        
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_quote_version(
                quote_id=uuid4(),
                version_number=99,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_approval_not_pending(self, mock_user, sample_quote):
        """Should fail approval action when not pending."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.NOT_REQUIRED.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = ApprovalRequest(action="approve")
        
        with pytest.raises(ConflictError):
            await handle_quote_approval(
                quote_id=sample_quote.id,
                request=request,
                db=db,
                current_user=mock_user,
                _=None,
            )
    
    @pytest.mark.asyncio
    async def test_send_rejected_quote_fails(self, mock_user, sample_quote):
        """Should not allow sending rejected quote."""
        db = AsyncMock()
        
        sample_quote.approval_status = ApprovalStatus.REJECTED.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute.return_value = result
        
        from sensei.api.exceptions import ConflictError
        
        request = SendQuoteRequest(send_method="email")
        
        with pytest.raises(ConflictError):
            await send_quote(
                quote_id=sample_quote.id,
                request=request,
                db=db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_accept_viewed_quote(self, mock_user, sample_quote):
        """Should accept quote that has been viewed."""
        db = AsyncMock()
        
        sample_quote.status = QuoteStatus.VIEWED.value
        
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=sample_quote)
        db.execute = AsyncMock(side_effect=[result, _scalar_result(0), _scalar_result(0)])
        db.refresh = AsyncMock()
        
        response = await accept_quote(
            quote_id=sample_quote.id,
            db=db,
            current_user=mock_user,
            convert_to_order=False,
        )
        
        assert response.success is True
        assert sample_quote.status == QuoteStatus.ACCEPTED.value

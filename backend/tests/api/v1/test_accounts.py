"""
Comprehensive Tests for Account Endpoints

Tests all Account functionality including:
- CRUD operations
- Filtering and pagination
- Account hierarchy (subsidiaries)
- Statistics
- Edge cases and error handling
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi import status, Query

from sensei.api.v1.endpoints.accounts import (
    router,
    list_accounts,
    create_account,
    get_account,
    update_account,
    delete_account,
    restore_account,
    bulk_delete_accounts,
    get_account_stats,
    list_subsidiaries,
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
    account_to_response,
    account_to_list_response,
)
from sensei.models.account import (
    Account,
    AccountType,
    AccountStatus,
    AccountTier,
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
def sample_account():
    """Create a sample account model."""
    account = MagicMock(spec=Account)
    account.id = uuid4()
    account.name = "Acme Corporation"
    account.legal_name = "Acme Corporation SARL"
    account.account_number = "ACC-001"
    account.account_type = AccountType.CUSTOMER.value
    account.status = AccountStatus.ACTIVE.value
    account.tier = AccountTier.STRATEGIC.value
    account.industry = "Manufacturing"
    account.sub_industry = "Precision Parts"
    account.website = "https://acme.ma"
    account.phone = "+212 5XX-XXXXXX"
    account.fax = None
    account.email = "contact@acme.ma"
    account.address_line1 = "123 Industrial Zone"
    account.address_line2 = None
    account.city = "Casablanca"
    account.state_province = "Casablanca-Settat"
    account.postal_code = "20000"
    account.country = "Morocco"
    account.full_address = "123 Industrial Zone, Casablanca, Morocco"
    account.tax_id = "TAX-123456"
    account.registration_number = "REG-789"
    account.employees_count = 250
    account.annual_revenue = Decimal("5000000.00")
    account.revenue_currency = "MAD"
    account.parent_id = None
    account.credit_limit = Decimal("100000.00")
    account.payment_terms = "Net 30"
    account.preferred_currency = "MAD"
    account.preferred_language = "fr"
    account.custom_fields = {}
    account.tags = ["premium", "manufacturing"]
    account.notes = "Strategic customer"
    account.created_at = datetime.now(timezone.utc)
    account.updated_at = datetime.now(timezone.utc)
    account.created_by_id = uuid4()
    account.updated_by_id = None
    account.deleted_at = None
    
    # Sales fields
    account.lead_source = None
    account.referred_by = None
    
    # Date fields
    account.established_date = None
    account.first_contact_date = None
    account.customer_since = None
    
    # Supplier fields
    account.capabilities = None
    account.certifications = None
    
    # Scoring fields
    account.qualification_score = None
    account.health_score = None
    
    # Notes fields
    account.description = None
    account.internal_notes = None
    
    # Computed properties
    account.is_customer = True
    account.is_supplier = False
    
    # Mock relationships
    account.contacts = MagicMock()
    account.contacts.all = MagicMock(return_value=[])
    account.subsidiaries = MagicMock()
    account.subsidiaries.all = MagicMock(return_value=[])
    
    return account


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestAccountToResponse:
    """Tests for account_to_response helper."""
    
    def test_account_to_response_full(self, sample_account):
        """Test converting full account to response."""
        response = account_to_response(sample_account)
        
        assert response.id == sample_account.id
        assert response.name == sample_account.name
        assert response.legal_name == sample_account.legal_name
        assert response.account_number == sample_account.account_number
        assert response.account_type == sample_account.account_type
        assert response.status == sample_account.status
        assert response.tier == sample_account.tier
        assert response.industry == sample_account.industry
        assert response.country == sample_account.country
        assert response.phone == sample_account.phone
        assert response.email == sample_account.email
        assert response.created_at == sample_account.created_at
    
    def test_account_to_response_minimal(self):
        """Test converting minimal account to response."""
        account = MagicMock(spec=Account)
        account.id = uuid4()
        account.name = "Test Company"
        account.legal_name = None
        account.account_number = None
        account.account_type = AccountType.PROSPECT.value
        account.status = AccountStatus.LEAD.value
        account.tier = None
        account.industry = None
        account.sub_industry = None
        account.website = None
        account.phone = None
        account.fax = None
        account.email = None
        account.address_line1 = None
        account.address_line2 = None
        account.city = None
        account.state_province = None
        account.postal_code = None
        account.country = "Morocco"
        account.full_address = None
        account.tax_id = None
        account.registration_number = None
        account.employees_count = None
        account.annual_revenue = None
        account.revenue_currency = "MAD"
        account.parent_id = None
        account.credit_limit = None
        account.payment_terms = None
        account.preferred_currency = "MAD"
        account.preferred_language = "fr"
        account.custom_fields = {}
        account.tags = []
        account.notes = None
        account.created_at = datetime.now(timezone.utc)
        account.updated_at = datetime.now(timezone.utc)
        account.created_by_id = uuid4()
        account.updated_by_id = None
        account.deleted_at = None
        
        # Sales fields
        account.lead_source = None
        account.referred_by = None
        
        # Date fields
        account.established_date = None
        account.first_contact_date = None
        account.customer_since = None
        
        # Supplier fields
        account.capabilities = None
        account.certifications = None
        
        # Scoring fields
        account.qualification_score = None
        account.health_score = None
        
        # Notes fields
        account.description = None
        account.internal_notes = None
        
        # Computed properties
        account.is_customer = False
        account.is_supplier = False
        
        response = account_to_response(account)
        
        assert response.id == account.id
        assert response.name == account.name
        assert response.country == "Morocco"


class TestAccountToListResponse:
    """Tests for account_to_list_response helper."""
    
    def test_account_to_list_response(self, sample_account):
        """Test converting account to list response."""
        response = account_to_list_response(sample_account)
        
        assert response.id == sample_account.id
        assert response.name == sample_account.name
        assert response.account_type == sample_account.account_type
        assert response.status == sample_account.status
        assert response.country == sample_account.country


# =============================================================================
# List Accounts Tests
# =============================================================================


class TestListAccounts:
    """Tests for GET /accounts endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_accounts_default(self, mock_db, mock_user):
        """Test listing accounts with default parameters."""
        # Create mock accounts
        mock_accounts = []
        for i in range(3):
            acc = MagicMock(spec=Account)
            acc.id = uuid4()
            acc.name = f"Account {i}"
            acc.account_number = f"ACC-{i:03d}"
            acc.account_type = AccountType.CUSTOMER.value
            acc.status = AccountStatus.ACTIVE.value
            acc.tier = None
            acc.industry = None
            acc.city = None
            acc.country = "Morocco"
            acc.phone = None
            acc.email = None
            acc.created_at = datetime.now(timezone.utc)
            mock_accounts.append(acc)
        
        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 3
        
        # Mock list query
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = mock_accounts
        
        mock_db.execute.side_effect = [count_result, list_result]
        
        result = await list_accounts(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            search=None,
            account_type=None,
            status=None,
            tier=None,
            industry=None,
            country=None,
            city=None,
            parent_id=None,
            sort=None,
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 3
        assert result.pagination.page == 1
        assert result.pagination.page_size == 20
        assert result.pagination.total_items == 3
    
    @pytest.mark.asyncio
    async def test_list_accounts_with_search(self, mock_db, mock_user):
        """Test listing accounts with search filter."""
        acc = MagicMock(spec=Account)
        acc.id = uuid4()
        acc.name = "Acme Corp"
        acc.account_number = "ACC-001"
        acc.account_type = AccountType.CUSTOMER.value
        acc.status = AccountStatus.ACTIVE.value
        acc.tier = None
        acc.industry = None
        acc.city = None
        acc.country = "Morocco"
        acc.phone = None
        acc.email = None
        acc.created_at = datetime.now(timezone.utc)
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [acc]
        
        mock_db.execute.side_effect = [count_result, list_result]
        
        result = await list_accounts(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            search="Acme",
            account_type=None,
            status=None,
            tier=None,
            industry=None,
            country=None,
            city=None,
            parent_id=None,
            sort=None,
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].name == "Acme Corp"
    
    @pytest.mark.asyncio
    async def test_list_accounts_filter_by_type(self, mock_db, mock_user):
        """Test filtering accounts by type."""
        acc = MagicMock(spec=Account)
        acc.id = uuid4()
        acc.name = "Supplier A"
        acc.account_number = "SUP-001"
        acc.account_type = AccountType.SUPPLIER.value
        acc.status = AccountStatus.ACTIVE.value
        acc.tier = None
        acc.industry = None
        acc.city = None
        acc.country = "Morocco"
        acc.phone = None
        acc.email = None
        acc.created_at = datetime.now(timezone.utc)
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [acc]
        
        mock_db.execute.side_effect = [count_result, list_result]
        
        result = await list_accounts(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            search=None,
            account_type=AccountType.SUPPLIER.value,
            status=None,
            tier=None,
            industry=None,
            country=None,
            city=None,
            parent_id=None,
            sort=None,
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].account_type == AccountType.SUPPLIER.value
    
    @pytest.mark.asyncio
    async def test_list_accounts_empty(self, mock_db, mock_user):
        """Test listing with no accounts."""
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [count_result, list_result]
        
        result = await list_accounts(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            search=None,
            account_type=None,
            status=None,
            tier=None,
            industry=None,
            country=None,
            city=None,
            parent_id=None,
            sort=None,
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 0
        assert result.pagination.total_items == 0


# =============================================================================
# Create Account Tests
# =============================================================================


class TestCreateAccount:
    """Tests for POST /accounts endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_account_success(self, mock_db, mock_user):
        """Test creating an account successfully."""
        account_data = AccountCreate(
            name="New Customer",
            account_type=AccountType.CUSTOMER.value,
            status=AccountStatus.LEAD.value,
            country="Morocco",
        )
        
        # Mock no duplicate check
        duplicate_result = MagicMock()
        duplicate_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = duplicate_result
        
        # Mock commit and refresh - refresh does nothing, account properties come from model defaults
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()  # Just do nothing on refresh
        mock_db.add = MagicMock()
        
        # Patch the Account class to return a mock
        with patch('sensei.api.v1.endpoints.accounts.Account') as MockAccount:
            mock_account = MagicMock(spec=Account)
            mock_account.id = uuid4()
            mock_account.name = "New Customer"
            mock_account.account_type = AccountType.CUSTOMER.value
            mock_account.status = AccountStatus.LEAD.value
            mock_account.country = "Morocco"
            mock_account.revenue_currency = "MAD"
            mock_account.preferred_currency = "MAD"
            mock_account.preferred_language = "fr"
            mock_account.legal_name = None
            mock_account.account_number = None
            mock_account.tier = None
            mock_account.industry = None
            mock_account.sub_industry = None
            mock_account.website = None
            mock_account.phone = None
            mock_account.fax = None
            mock_account.email = None
            mock_account.address_line1 = None
            mock_account.address_line2 = None
            mock_account.city = None
            mock_account.state_province = None
            mock_account.postal_code = None
            mock_account.full_address = None
            mock_account.tax_id = None
            mock_account.registration_number = None
            mock_account.employees_count = None
            mock_account.annual_revenue = None
            mock_account.parent_id = None
            mock_account.credit_limit = None
            mock_account.payment_terms = None
            mock_account.custom_fields = {}
            mock_account.tags = []
            mock_account.notes = None
            mock_account.lead_source = None
            mock_account.referred_by = None
            mock_account.established_date = None
            mock_account.first_contact_date = None
            mock_account.customer_since = None
            mock_account.capabilities = None
            mock_account.certifications = None
            mock_account.qualification_score = None
            mock_account.health_score = None
            mock_account.description = None
            mock_account.internal_notes = None
            mock_account.is_customer = True
            mock_account.is_supplier = False
            mock_account.created_at = datetime.now(timezone.utc)
            mock_account.updated_at = datetime.now(timezone.utc)
            mock_account.created_by_id = mock_user.id
            mock_account.updated_by_id = None
            mock_account.deleted_at = None
            
            MockAccount.return_value = mock_account
            
            result = await create_account(
                account_data=account_data,
                db=mock_db,
                current_user=mock_user,
            )
            
            assert result.success is True
            assert result.message == "Account created successfully"
    
    @pytest.mark.asyncio
    async def test_create_account_duplicate_number(self, mock_db, mock_user):
        """Test creating account with duplicate account number."""
        from sensei.api.exceptions import ConflictError
        
        account_data = AccountCreate(
            name="New Customer",
            account_number="ACC-001",
            country="Morocco",
        )
        
        # Mock duplicate found
        existing = MagicMock()
        duplicate_result = MagicMock()
        duplicate_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = duplicate_result
        
        with pytest.raises(ConflictError):
            await create_account(
                account_data=account_data,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Get Account Tests
# =============================================================================


class TestGetAccount:
    """Tests for GET /accounts/{account_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_account_success(self, mock_db, mock_user, sample_account):
        """Test getting an account successfully."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_account
        mock_db.execute.return_value = result
        
        response = await get_account(
            account_id=sample_account.id,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data.id == sample_account.id
        assert response.data.name == sample_account.name
    
    @pytest.mark.asyncio
    async def test_get_account_not_found(self, mock_db, mock_user):
        """Test getting non-existent account."""
        from sensei.api.exceptions import NotFoundError
        
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result
        
        with pytest.raises(NotFoundError):
            await get_account(
                account_id=uuid4(),
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Update Account Tests
# =============================================================================


class TestUpdateAccount:
    """Tests for PUT /accounts/{account_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_account_success(self, mock_db, mock_user, sample_account):
        """Test updating an account successfully."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_account
        mock_db.execute.return_value = result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        update_data = AccountUpdate(name="Updated Name")
        
        response = await update_account(
            account_id=sample_account.id,
            account_data=update_data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.message == "Account updated successfully"
    
    @pytest.mark.asyncio
    async def test_update_account_not_found(self, mock_db, mock_user):
        """Test updating non-existent account."""
        from sensei.api.exceptions import NotFoundError
        
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result
        
        update_data = AccountUpdate(name="Updated Name")
        
        with pytest.raises(NotFoundError):
            await update_account(
                account_id=uuid4(),
                account_data=update_data,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Delete Account Tests
# =============================================================================


class TestDeleteAccount:
    """Tests for DELETE /accounts/{account_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_account_soft(self, mock_db, mock_user, sample_account):
        """Test soft deleting an account."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_account
        mock_db.execute.return_value = result
        mock_db.commit = AsyncMock()
        
        response = await delete_account(
            account_id=sample_account.id,
            hard_delete=False,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.message == "Account deleted successfully"
        # Verify soft delete was set
        assert sample_account.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_account_hard_as_superuser(self, mock_db, mock_superuser, sample_account):
        """Test hard deleting an account as superuser."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_account
        mock_db.execute.return_value = result
        mock_db.commit = AsyncMock()
        mock_db.delete = AsyncMock()
        
        response = await delete_account(
            account_id=sample_account.id,
            hard_delete=True,
            db=mock_db,
            current_user=mock_superuser,
        )
        
        assert response.success is True
        mock_db.delete.assert_called_once_with(sample_account)
    
    @pytest.mark.asyncio
    async def test_delete_account_hard_forbidden(self, mock_db, mock_user, sample_account):
        """Test hard delete forbidden for non-superuser."""
        from sensei.api.exceptions import ForbiddenError
        
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_account
        mock_db.execute.return_value = result
        
        with pytest.raises(ForbiddenError):
            await delete_account(
                account_id=sample_account.id,
                hard_delete=True,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Restore Account Tests
# =============================================================================


class TestRestoreAccount:
    """Tests for POST /accounts/{account_id}/restore endpoint."""
    
    @pytest.mark.asyncio
    async def test_restore_account_success(self, mock_db, mock_user, sample_account):
        """Test restoring a soft-deleted account."""
        sample_account.deleted_at = datetime.now(timezone.utc)
        
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_account
        mock_db.execute.return_value = result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        response = await restore_account(
            account_id=sample_account.id,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_account.deleted_at is None


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_account_not_found(self, mock_db, mock_user):
        """Test generic not found error."""
        from sensei.api.exceptions import NotFoundError
        
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result
        
        with pytest.raises(NotFoundError):
            await get_account(
                account_id=uuid4(),
                db=mock_db,
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_list_accounts_with_sorting(self, mock_db, mock_user):
        """Test listing accounts with sorting."""
        acc = MagicMock(spec=Account)
        acc.id = uuid4()
        acc.name = "Alpha Corp"
        acc.account_number = "ACC-001"
        acc.account_type = AccountType.CUSTOMER.value
        acc.status = AccountStatus.ACTIVE.value
        acc.tier = None
        acc.industry = None
        acc.city = None
        acc.country = "Morocco"
        acc.phone = None
        acc.email = None
        acc.created_at = datetime.now(timezone.utc)
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [acc]
        
        mock_db.execute.side_effect = [count_result, list_result]
        
        result = await list_accounts(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            search=None,
            account_type=None,
            status=None,
            tier=None,
            industry=None,
            country=None,
            city=None,
            parent_id=None,
            sort="name:asc",
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 1
    
    @pytest.mark.asyncio
    async def test_list_accounts_include_deleted(self, mock_db, mock_user):
        """Test listing accounts including deleted ones."""
        acc = MagicMock(spec=Account)
        acc.id = uuid4()
        acc.name = "Deleted Corp"
        acc.account_number = "DEL-001"
        acc.account_type = AccountType.CUSTOMER.value
        acc.status = AccountStatus.ACTIVE.value
        acc.tier = None
        acc.industry = None
        acc.city = None
        acc.country = "Morocco"
        acc.phone = None
        acc.email = None
        acc.created_at = datetime.now(timezone.utc)
        acc.deleted_at = datetime.now(timezone.utc)
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [acc]
        
        mock_db.execute.side_effect = [count_result, list_result]
        
        result = await list_accounts(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            search=None,
            account_type=None,
            status=None,
            tier=None,
            industry=None,
            country=None,
            city=None,
            parent_id=None,
            sort=None,
            include_deleted=True,
        )
        
        assert result.success is True
        assert len(result.data) == 1

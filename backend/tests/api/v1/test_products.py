"""
Tests for Product/Part Catalog Management Endpoints

Comprehensive tests for:
- Product CRUD operations
- Product filtering, sorting, pagination
- BOM (Bill of Materials) management
- Routing management
- Product revisions
- Edge cases and error handling
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

from sensei.api.v1.endpoints.products import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    BOMItemCreate,
    BOMItemResponse,
    RoutingCreate,
    RoutingResponse,
    product_to_response,
    product_to_list_response,
    bom_item_to_response,
    routing_to_response,
)
from sensei.models.product import (
    Product,
    ProductStatus,
    UnitOfMeasure,
    BOMItem,
    Routing,
)


# =============================================================================
# Fixture Helpers
# =============================================================================


@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    product = Product(
        id=uuid4(),
        name="Widget Assembly",
        part_number="WGT-001",
        revision="A",
        description="Standard widget assembly",
        product_family="Widgets",
        product_category="Assemblies",
        unit_of_measure=UnitOfMeasure.EACH,
        weight_kg=Decimal("0.5"),
        dimensions="10x5x3 cm",
        standard_cost=Decimal("25.00"),
        standard_labor_hours=Decimal("0.5"),
        lead_time_days=5,
        setup_time_hours=Decimal("0.25"),
        status=ProductStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by_id=uuid4(),
    )
    product.bom_items = []
    product.routings = []
    return product


@pytest.fixture
def sample_bom_item(sample_product):
    """Create a sample BOM item for testing."""
    return BOMItem(
        id=1,
        product_id=sample_product.id,
        component_part_number="CMP-001",
        component_description="Component A",
        quantity=Decimal("2.0"),
        unit_of_measure=UnitOfMeasure.EACH,
        position=10,
        find_number="1",
        is_critical=True,
        is_phantom=False,
        is_alternate=False,
        scrap_factor=Decimal("0.05"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by_id=uuid4(),
    )


@pytest.fixture
def sample_routing(sample_product):
    """Create a sample routing step for testing."""
    return Routing(
        id=1,
        product_id=sample_product.id,
        sequence=10,
        operation_name="Assembly",
        operation_code="ASSY",
        description="Assemble components",
        station_id=1,
        standard_time_seconds=300,
        setup_time_seconds=60,
        move_time_seconds=30,
        queue_time_seconds=120,
        labor_hours=Decimal("0.1"),
        crew_size=1,
        is_subcontracted=False,
        is_inspection=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by_id=uuid4(),
    )


@pytest.fixture
def mock_current_user():
    """Mock current user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "admin@example.com"
    user.is_superuser = False
    return user


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestProductToResponse:
    """Tests for product_to_response converter."""
    
    def test_product_to_response_full(self, sample_product):
        """Test converting full product to response."""
        response = product_to_response(sample_product)
        
        assert isinstance(response, ProductResponse)
        assert response.id == sample_product.id
        assert response.name == sample_product.name
        assert response.part_number == sample_product.part_number
        assert response.revision == sample_product.revision
        assert response.full_part_number == f"{sample_product.part_number}-{sample_product.revision}"
        assert response.description == sample_product.description
        assert response.product_family == sample_product.product_family
        assert response.status == ProductStatus.ACTIVE.value
        assert response.is_active is True
        assert response.created_at == sample_product.created_at
    
    def test_product_to_response_minimal(self):
        """Test converting minimal product to response."""
        product = Product(
            id=uuid4(),
            name="Basic Part",
            part_number="BAS-001",
            revision="A",
            unit_of_measure=UnitOfMeasure.EACH,
            lead_time_days=0,
            status=ProductStatus.PROTOTYPE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        product.bom_items = []
        product.routings = []
        
        response = product_to_response(product)
        
        assert response.id == product.id
        assert response.name == product.name
        assert response.description is None
        assert response.standard_cost is None
        assert response.is_active is False  # PROTOTYPE status
    
    def test_product_to_response_with_bom_and_routing(self, sample_product, sample_bom_item, sample_routing):
        """Test product with BOM items and routing steps."""
        sample_product.bom_items = [sample_bom_item]
        sample_product.routings = [sample_routing]
        
        response = product_to_response(sample_product)
        
        assert response.bom_item_count == 1
        assert response.routing_step_count == 1


class TestBOMItemToResponse:
    """Tests for bom_item_to_response converter."""
    
    def test_bom_item_to_response(self, sample_bom_item):
        """Test converting BOM item to response."""
        response = bom_item_to_response(sample_bom_item)
        
        assert isinstance(response, BOMItemResponse)
        assert response.id == sample_bom_item.id
        assert response.product_id == sample_bom_item.product_id
        assert response.component_part_number == sample_bom_item.component_part_number
        assert response.quantity == sample_bom_item.quantity
        assert response.is_critical is True
        assert response.scrap_factor == Decimal("0.05")
        # Extended quantity = 2.0 * (1 + 0.05) = 2.1
        assert response.extended_quantity == Decimal("2.10")


class TestRoutingToResponse:
    """Tests for routing_to_response converter."""
    
    def test_routing_to_response(self, sample_routing):
        """Test converting routing to response."""
        response = routing_to_response(sample_routing)
        
        assert isinstance(response, RoutingResponse)
        assert response.id == sample_routing.id
        assert response.product_id == sample_routing.product_id
        assert response.sequence == sample_routing.sequence
        assert response.operation_name == sample_routing.operation_name
        assert response.standard_time_seconds == 300
        assert response.setup_time_seconds == 60
        # Total = 60 + 300 + 30 + 120 = 510
        assert response.total_time_seconds == 510


# =============================================================================
# List Products Tests
# =============================================================================


class TestListProducts:
    """Tests for GET /products endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_products_default(self, mock_db_session, mock_current_user):
        """Test listing products with default parameters."""
        from sensei.api.v1.endpoints.products import list_products
        
        # Mock database response
        mock_products = [
            Product(
                id=uuid4(),
                name=f"Product {i}",
                part_number=f"PRD-{i:03d}",
                revision="A",
                unit_of_measure=UnitOfMeasure.EACH,
                lead_time_days=5,
                status=ProductStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for i in range(1, 6)
        ]
        
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = mock_products
        
        mock_db_session.execute.side_effect = [count_result, list_result]
        
        result = await list_products(
            db=mock_db_session,
            current_user=mock_current_user,
            page=1,
            page_size=50,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 5
        assert result.pagination.total_items == 5
    
    @pytest.mark.asyncio
    async def test_list_products_with_search(self, mock_db_session, mock_current_user):
        """Test listing products with search filter."""
        from sensei.api.v1.endpoints.products import list_products
        
        mock_products = [
            Product(
                id=uuid4(),
                name="Widget Assembly",
                part_number="WGT-001",
                revision="A",
                unit_of_measure=UnitOfMeasure.EACH,
                lead_time_days=5,
                status=ProductStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = mock_products
        
        mock_db_session.execute.side_effect = [count_result, list_result]
        
        result = await list_products(
            db=mock_db_session,
            current_user=mock_current_user,
            search="Widget",
            page=1,
            page_size=50,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].name == "Widget Assembly"
    
    @pytest.mark.asyncio
    async def test_list_products_filter_by_family(self, mock_db_session, mock_current_user):
        """Test filtering products by product family."""
        from sensei.api.v1.endpoints.products import list_products
        
        mock_products = [
            Product(
                id=uuid4(),
                name="Widget A",
                part_number="WGT-A",
                revision="A",
                product_family="Widgets",
                unit_of_measure=UnitOfMeasure.EACH,
                lead_time_days=5,
                status=ProductStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = mock_products
        
        mock_db_session.execute.side_effect = [count_result, list_result]
        
        result = await list_products(
            db=mock_db_session,
            current_user=mock_current_user,
            product_family="Widgets",
            page=1,
            page_size=50,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert result.success is True
        assert result.data[0].product_family == "Widgets"
    
    @pytest.mark.asyncio
    async def test_list_products_filter_by_status(self, mock_db_session, mock_current_user):
        """Test filtering products by status."""
        from sensei.api.v1.endpoints.products import list_products
        
        mock_products = [
            Product(
                id=uuid4(),
                name="Prototype",
                part_number="PRO-001",
                revision="A",
                unit_of_measure=UnitOfMeasure.EACH,
                lead_time_days=0,
                status=ProductStatus.PROTOTYPE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = mock_products
        
        mock_db_session.execute.side_effect = [count_result, list_result]
        
        result = await list_products(
            db=mock_db_session,
            current_user=mock_current_user,
            status=ProductStatus.PROTOTYPE.value,
            page=1,
            page_size=50,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert result.success is True
        assert result.data[0].status == ProductStatus.PROTOTYPE.value
    
    @pytest.mark.asyncio
    async def test_list_products_pagination(self, mock_db_session, mock_current_user):
        """Test product pagination."""
        from sensei.api.v1.endpoints.products import list_products
        
        mock_products = [
            Product(
                id=uuid4(),
                name=f"Product {i}",
                part_number=f"PRD-{i:03d}",
                revision="A",
                unit_of_measure=UnitOfMeasure.EACH,
                lead_time_days=5,
                status=ProductStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for i in range(11, 21)
        ]
        
        count_result = MagicMock()
        count_result.scalar.return_value = 50
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = mock_products
        
        mock_db_session.execute.side_effect = [count_result, list_result]
        
        result = await list_products(
            db=mock_db_session,
            current_user=mock_current_user,
            page=2,
            page_size=10,
            sort="-created_at",
            include_deleted=False,
        )
        
        assert result.success is True
        assert result.pagination.page == 2
        assert result.pagination.page_size == 10
        assert result.pagination.total_items == 50
        assert result.pagination.total_pages == 5


# =============================================================================
# Create Product Tests
# =============================================================================


class TestCreateProduct:
    """Tests for POST /products endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_product_success(self, mock_db_session, mock_current_user):
        """Test creating a product successfully."""
        from sensei.api.v1.endpoints.products import create_product
        
        product_data = ProductCreate(
            name="New Widget",
            part_number="NWG-001",
            revision="A",
            description="A new widget product",
            product_family="Widgets",
            unit_of_measure=UnitOfMeasure.EACH.value,
            standard_cost=Decimal("15.00"),
            lead_time_days=7,
        )
        
        # Mock no existing product
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = existing_result
        
        # Mock refresh to set required fields on the product
        async def mock_refresh(obj, *args, **kwargs):
            obj.id = uuid4()
            obj.status = ProductStatus.ACTIVE
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.bom_items = []
            obj.routings = []
        
        mock_db_session.refresh = mock_refresh
        
        result = await create_product(
            product_data=product_data,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.message == "Product created successfully"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_product_duplicate(self, mock_db_session, mock_current_user, sample_product):
        """Test creating product with duplicate part number."""
        from sensei.api.v1.endpoints.products import create_product
        from sensei.api.exceptions import ConflictError
        
        product_data = ProductCreate(
            name="Duplicate Widget",
            part_number=sample_product.part_number,
            revision=sample_product.revision,
        )
        
        # Mock existing product
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = existing_result
        
        with pytest.raises(ConflictError) as exc_info:
            await create_product(
                product_data=product_data,
                db=mock_db_session,
                current_user=mock_current_user,
            )
        
        assert "already exists" in str(exc_info.value).lower()


# =============================================================================
# Get Product Tests
# =============================================================================


class TestGetProduct:
    """Tests for GET /products/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_product_success(self, mock_db_session, mock_current_user, sample_product):
        """Test retrieving a product successfully."""
        from sensei.api.v1.endpoints.products import get_product
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = result_mock
        
        result = await get_product(
            product_id=sample_product.id,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.data.id == sample_product.id
        assert result.data.part_number == sample_product.part_number
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(self, mock_db_session, mock_current_user):
        """Test getting non-existent product."""
        from sensei.api.v1.endpoints.products import get_product
        from sensei.api.exceptions import NotFoundError
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock
        
        with pytest.raises(NotFoundError):
            await get_product(
                product_id=999,
                db=mock_db_session,
                current_user=mock_current_user,
            )


# =============================================================================
# Update Product Tests
# =============================================================================


class TestUpdateProduct:
    """Tests for PATCH /products/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_product_success(self, mock_db_session, mock_current_user, sample_product):
        """Test updating a product successfully."""
        from sensei.api.v1.endpoints.products import update_product
        
        sample_product.bom_items = []
        sample_product.routings = []
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = result_mock
        mock_db_session.refresh = AsyncMock()
        
        update_data = ProductUpdate(
            name="Updated Widget",
            standard_cost=Decimal("30.00"),
        )
        
        result = await update_product(
            product_id=sample_product.id,
            product_data=update_data,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.message == "Product updated successfully"
        assert sample_product.name == "Updated Widget"
        assert sample_product.standard_cost == Decimal("30.00")
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_product_status(self, mock_db_session, mock_current_user, sample_product):
        """Test updating product status."""
        from sensei.api.v1.endpoints.products import update_product
        
        sample_product.bom_items = []
        sample_product.routings = []
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = result_mock
        mock_db_session.refresh = AsyncMock()
        
        update_data = ProductUpdate(status=ProductStatus.OBSOLETE.value)
        
        result = await update_product(
            product_id=sample_product.id,
            product_data=update_data,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert sample_product.status == ProductStatus.OBSOLETE


# =============================================================================
# Delete Product Tests
# =============================================================================


class TestDeleteProduct:
    """Tests for DELETE /products/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_product_soft(self, mock_db_session, mock_current_user, sample_product):
        """Test soft deleting a product."""
        from sensei.api.v1.endpoints.products import delete_product
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = result_mock
        
        result = await delete_product(
            product_id=sample_product.id,
            db=mock_db_session,
            current_user=mock_current_user,
            hard_delete=False,
        )
        
        assert result.success is True
        assert result.message == "Product deleted successfully"
        assert sample_product.deleted_at is not None
        assert sample_product.deleted_by_id == mock_current_user.id
    
    @pytest.mark.asyncio
    async def test_delete_product_hard_forbidden(self, mock_db_session, mock_current_user, sample_product):
        """Test hard delete forbidden for non-superuser."""
        from sensei.api.v1.endpoints.products import delete_product
        from sensei.api.exceptions import ForbiddenError
        
        mock_current_user.is_superuser = False
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = result_mock
        
        with pytest.raises(ForbiddenError):
            await delete_product(
                product_id=sample_product.id,
                db=mock_db_session,
                current_user=mock_current_user,
                hard_delete=True,
            )


# =============================================================================
# New Revision Tests
# =============================================================================


class TestCreateNewRevision:
    """Tests for POST /products/{id}/new-revision endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_new_revision_success(self, mock_db_session, mock_current_user, sample_product):
        """Test creating a new product revision."""
        from sensei.api.v1.endpoints.products import create_new_revision
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock no existing revision
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        
        mock_db_session.execute.side_effect = [product_result, existing_result]
        mock_db_session.flush = AsyncMock()
        
        # Mock refresh to set required fields on the new product
        async def mock_refresh(obj, *args, **kwargs):
            obj.id = uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.bom_items = []
            obj.routings = []
        
        mock_db_session.refresh = mock_refresh
        
        result = await create_new_revision(
            product_id=sample_product.id,
            db=mock_db_session,
            current_user=mock_current_user,
            new_revision="B",
            copy_bom=True,
            copy_routing=True,
        )
        
        assert result.success is True
        assert "B" in result.message
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_revision_duplicate(self, mock_db_session, mock_current_user, sample_product):
        """Test creating revision that already exists."""
        from sensei.api.v1.endpoints.products import create_new_revision
        from sensei.api.exceptions import ConflictError
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock existing revision
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = sample_product
        
        mock_db_session.execute.side_effect = [product_result, existing_result]
        
        with pytest.raises(ConflictError) as exc_info:
            await create_new_revision(
                product_id=sample_product.id,
                db=mock_db_session,
                current_user=mock_current_user,
                new_revision="A",
                copy_bom=True,
                copy_routing=True,
            )
        
        assert "already exists" in str(exc_info.value).lower()


# =============================================================================
# BOM Endpoints Tests
# =============================================================================


class TestBOMEndpoints:
    """Tests for BOM management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_bom_items(self, mock_db_session, mock_current_user, sample_product, sample_bom_item):
        """Test listing BOM items for a product."""
        from sensei.api.v1.endpoints.products import list_bom_items
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock BOM items
        bom_result = MagicMock()
        bom_result.scalars.return_value.all.return_value = [sample_bom_item]
        
        mock_db_session.execute.side_effect = [product_result, bom_result]
        
        result = await list_bom_items(
            product_id=sample_product.id,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].component_part_number == "CMP-001"
    
    @pytest.mark.asyncio
    async def test_add_bom_item(self, mock_db_session, mock_current_user, sample_product):
        """Test adding a BOM item."""
        from sensei.api.v1.endpoints.products import add_bom_item
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock no duplicate
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        
        mock_db_session.execute.side_effect = [product_result, existing_result]
        
        # Mock refresh to set required fields on the BOM item
        async def mock_refresh(obj, *args, **kwargs):
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            if getattr(obj, 'scrap_factor', None) is None:
                obj.scrap_factor = Decimal("0.0")
            if getattr(obj, 'unit_of_measure', None) is None:
                obj.unit_of_measure = UnitOfMeasure.EACH
            if getattr(obj, 'is_critical', None) is None:
                obj.is_critical = False
            if getattr(obj, 'is_phantom', None) is None:
                obj.is_phantom = False
            if getattr(obj, 'is_alternate', None) is None:
                obj.is_alternate = False
        
        mock_db_session.refresh = mock_refresh
        
        item_data = BOMItemCreate(
            component_part_number="NEW-CMP",
            quantity=Decimal("3.0"),
            position=20,
        )
        
        result = await add_bom_item(
            product_id=sample_product.id,
            item_data=item_data,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.message == "BOM item created successfully"
        mock_db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_bom_item(self, mock_db_session, mock_current_user, sample_product, sample_bom_item):
        """Test deleting a BOM item."""
        from sensei.api.v1.endpoints.products import delete_bom_item
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_bom_item
        mock_db_session.execute.return_value = result_mock
        mock_db_session.delete = AsyncMock()
        
        result = await delete_bom_item(
            product_id=sample_product.id,
            bom_id=sample_bom_item.id,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.message == "BOM item deleted successfully"
        mock_db_session.delete.assert_called_once_with(sample_bom_item)


# =============================================================================
# Routing Endpoints Tests
# =============================================================================


class TestRoutingEndpoints:
    """Tests for routing management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_routing_steps(self, mock_db_session, mock_current_user, sample_product, sample_routing):
        """Test listing routing steps for a product."""
        from sensei.api.v1.endpoints.products import list_routing_steps
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock routing steps
        routing_result = MagicMock()
        routing_result.scalars.return_value.all.return_value = [sample_routing]
        
        mock_db_session.execute.side_effect = [product_result, routing_result]
        
        result = await list_routing_steps(
            product_id=sample_product.id,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].operation_name == "Assembly"
    
    @pytest.mark.asyncio
    async def test_add_routing_step(self, mock_db_session, mock_current_user, sample_product):
        """Test adding a routing step."""
        from sensei.api.v1.endpoints.products import add_routing_step
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock no duplicate sequence
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        
        mock_db_session.execute.side_effect = [product_result, existing_result]
        
        # Mock refresh to set required fields on the routing
        async def mock_refresh(obj, *args, **kwargs):
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            if getattr(obj, 'setup_time_seconds', None) is None:
                obj.setup_time_seconds = 0
            if getattr(obj, 'move_time_seconds', None) is None:
                obj.move_time_seconds = 0
            if getattr(obj, 'queue_time_seconds', None) is None:
                obj.queue_time_seconds = 0
            if getattr(obj, 'is_subcontracted', None) is None:
                obj.is_subcontracted = False
            if getattr(obj, 'is_inspection', None) is None:
                obj.is_inspection = False
            if getattr(obj, 'crew_size', None) is None:
                obj.crew_size = 1
        
        mock_db_session.refresh = mock_refresh
        
        routing_data = RoutingCreate(
            sequence=10,
            operation_name="New Operation",
            station_id=1,
            standard_time_seconds=120,
        )
        
        result = await add_routing_step(
            product_id=sample_product.id,
            routing_data=routing_data,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.message == "Routing step created successfully"
        mock_db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_routing_duplicate_sequence(self, mock_db_session, mock_current_user, sample_product, sample_routing):
        """Test adding routing with duplicate sequence."""
        from sensei.api.v1.endpoints.products import add_routing_step
        from sensei.api.exceptions import ConflictError
        
        # Mock product exists
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = sample_product
        
        # Mock existing sequence
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = sample_routing
        
        mock_db_session.execute.side_effect = [product_result, existing_result]
        
        routing_data = RoutingCreate(
            sequence=10,  # Same as sample_routing
            operation_name="Duplicate",
            station_id=1,
            standard_time_seconds=120,
        )
        
        with pytest.raises(ConflictError) as exc_info:
            await add_routing_step(
                product_id=sample_product.id,
                routing_data=routing_data,
                db=mock_db_session,
                current_user=mock_current_user,
            )
        
        assert "already exists" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_delete_routing_step(self, mock_db_session, mock_current_user, sample_product, sample_routing):
        """Test deleting a routing step."""
        from sensei.api.v1.endpoints.products import delete_routing_step
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_routing
        mock_db_session.execute.return_value = result_mock
        mock_db_session.delete = AsyncMock()
        
        result = await delete_routing_step(
            product_id=sample_product.id,
            routing_id=sample_routing.id,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.message == "Routing step deleted successfully"
        mock_db_session.delete.assert_called_once_with(sample_routing)


# =============================================================================
# Product Statistics Tests
# =============================================================================


class TestProductStats:
    """Tests for GET /products/{id}/stats endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_product_stats(self, mock_db_session, mock_current_user, sample_product, sample_bom_item, sample_routing):
        """Test getting product statistics."""
        from sensei.api.v1.endpoints.products import get_product_stats
        
        sample_product.bom_items = [sample_bom_item]
        sample_product.routings = [sample_routing]
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_product
        mock_db_session.execute.return_value = result_mock
        
        result = await get_product_stats(
            product_id=sample_product.id,
            db=mock_db_session,
            current_user=mock_current_user,
        )
        
        assert result.success is True
        assert result.data["product_id"] == sample_product.id
        assert result.data["bom"]["total_items"] == 1
        assert result.data["bom"]["critical_components"] == 1
        assert result.data["routing"]["total_steps"] == 1
        assert result.data["routing"]["total_standard_time_seconds"] == 300
    
    @pytest.mark.asyncio
    async def test_get_product_stats_not_found(self, mock_db_session, mock_current_user):
        """Test stats for non-existent product."""
        from sensei.api.v1.endpoints.products import get_product_stats
        from sensei.api.exceptions import NotFoundError
        
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock
        
        with pytest.raises(NotFoundError):
            await get_product_stats(
                product_id=999,
                db=mock_db_session,
                current_user=mock_current_user,
            )

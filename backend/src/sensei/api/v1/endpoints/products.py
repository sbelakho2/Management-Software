"""
Product/Part Catalog Management Endpoints

Provides product management including:
- List products with filtering and pagination
- Create/read/update/delete products
- Bill of Materials (BOM) management
- Routing management
- Product versioning and revisions
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import (
    CurrentUser,
    DBSession,
)
from sensei.api.exceptions import (
    ConflictError,
    NotFoundError,
    ForbiddenError,
    BusinessRuleViolationError,
)
from sensei.api.schemas import (
    APIResponse,
    PaginatedResponse,
    BulkDeleteRequest,
)
from sensei.api.utils import (
    parse_sort_param,
    build_response,
    build_paginated_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    now_utc,
)
from sensei.models.product import (
    Product,
    ProductStatus,
    UnitOfMeasure,
    BOMItem,
    Routing,
)


AllowProductsModule = deps.require_role(
    "engineering",
    "ops",
    "quality",
    "supply_chain",
    "purchasing",
    "sales_engineer",
    "estimator",
    "supervisor",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "engineering",
                    "ops",
                    "quality",
                    "supply_chain",
                    "purchasing",
                    "sales_engineer",
                    "estimator",
                    "supervisor",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ProductBase(BaseModel):
    """Base product fields."""
    
    name: str = Field(..., min_length=1, max_length=255)
    part_number: str = Field(..., min_length=1, max_length=100)
    revision: str = Field(default="A", max_length=20)
    description: Optional[str] = None
    
    # Classification
    product_family: Optional[str] = Field(None, max_length=100)
    product_category: Optional[str] = Field(None, max_length=100)
    
    # Units and specifications
    unit_of_measure: str = Field(default=UnitOfMeasure.EACH.value)
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    
    # Cost and pricing
    standard_cost: Optional[Decimal] = Field(None, ge=0)
    standard_labor_hours: Optional[Decimal] = Field(None, ge=0)
    
    # Lead times
    lead_time_days: int = Field(default=0, ge=0)
    setup_time_hours: Optional[Decimal] = Field(None, ge=0)
    
    # Status
    status: str = Field(default=ProductStatus.ACTIVE.value)
    
    @field_validator("unit_of_measure")
    @classmethod
    def validate_unit_of_measure(cls, v: str) -> str:
        valid_units = [u.value for u in UnitOfMeasure]
        if v not in valid_units:
            raise ValueError(f"Invalid unit of measure. Must be one of: {valid_units}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [s.value for s in ProductStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class ProductCreate(ProductBase):
    """Product creation request."""
    pass


class ProductUpdate(BaseModel):
    """Product update request (all fields optional)."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Classification
    product_family: Optional[str] = Field(None, max_length=100)
    product_category: Optional[str] = Field(None, max_length=100)
    
    # Units and specifications
    unit_of_measure: Optional[str] = None
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    
    # Cost and pricing
    standard_cost: Optional[Decimal] = Field(None, ge=0)
    standard_labor_hours: Optional[Decimal] = Field(None, ge=0)
    
    # Lead times
    lead_time_days: Optional[int] = Field(None, ge=0)
    setup_time_hours: Optional[Decimal] = Field(None, ge=0)
    
    # Status
    status: Optional[str] = None
    
    @field_validator("unit_of_measure")
    @classmethod
    def validate_unit_of_measure(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_units = [u.value for u in UnitOfMeasure]
        if v not in valid_units:
            raise ValueError(f"Invalid unit of measure. Must be one of: {valid_units}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_statuses = [s.value for s in ProductStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class ProductResponse(BaseModel):
    """Product response."""
    
    id: int
    name: str
    part_number: str
    revision: str
    full_part_number: str
    description: Optional[str]
    
    # Classification
    product_family: Optional[str]
    product_category: Optional[str]
    
    # Units and specifications
    unit_of_measure: str
    weight_kg: Optional[Decimal]
    dimensions: Optional[str]
    
    # Cost and pricing
    standard_cost: Optional[Decimal]
    standard_labor_hours: Optional[Decimal]
    
    # Lead times
    lead_time_days: int
    setup_time_hours: Optional[Decimal]
    
    # Status
    status: str
    is_active: bool
    
    # Counts
    bom_item_count: int = 0
    routing_step_count: int = 0
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    updated_by_id: Optional[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """Simplified product for list views."""
    
    id: int
    name: str
    part_number: str
    revision: str
    full_part_number: str
    product_family: Optional[str]
    status: str
    standard_cost: Optional[Decimal]
    lead_time_days: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# BOM Schemas
# =============================================================================


class BOMItemBase(BaseModel):
    """Base BOM item fields."""
    
    component_part_number: str = Field(..., min_length=1, max_length=100)
    component_product_id: Optional[int] = None
    component_description: Optional[str] = Field(None, max_length=255)
    
    quantity: Decimal = Field(default=Decimal("1.0"), gt=0)
    unit_of_measure: str = Field(default=UnitOfMeasure.EACH.value)
    
    position: int = Field(default=0, ge=0)
    find_number: Optional[str] = Field(None, max_length=20)
    
    is_critical: bool = Field(default=False)
    is_phantom: bool = Field(default=False)
    is_alternate: bool = Field(default=False)
    
    scrap_factor: Decimal = Field(default=Decimal("0.0"), ge=0, lt=1)


class BOMItemCreate(BOMItemBase):
    """BOM item creation request."""
    pass


class BOMItemUpdate(BaseModel):
    """BOM item update request."""
    
    component_description: Optional[str] = Field(None, max_length=255)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_of_measure: Optional[str] = None
    position: Optional[int] = Field(None, ge=0)
    find_number: Optional[str] = Field(None, max_length=20)
    is_critical: Optional[bool] = None
    is_phantom: Optional[bool] = None
    is_alternate: Optional[bool] = None
    scrap_factor: Optional[Decimal] = Field(None, ge=0, lt=1)


class BOMItemResponse(BaseModel):
    """BOM item response."""
    
    id: int
    product_id: int
    component_part_number: str
    component_product_id: Optional[int]
    component_description: Optional[str]
    
    quantity: Decimal
    unit_of_measure: str
    extended_quantity: Decimal
    
    position: int
    find_number: Optional[str]
    
    is_critical: bool
    is_phantom: bool
    is_alternate: bool
    
    scrap_factor: Decimal
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Routing Schemas
# =============================================================================


class RoutingBase(BaseModel):
    """Base routing fields."""
    
    sequence: int = Field(..., gt=0)
    operation_name: str = Field(..., min_length=1, max_length=255)
    operation_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    
    station_id: int = Field(..., gt=0)
    
    # Time standards (in seconds)
    standard_time_seconds: int = Field(default=60, gt=0)
    setup_time_seconds: int = Field(default=0, ge=0)
    move_time_seconds: int = Field(default=0, ge=0)
    queue_time_seconds: int = Field(default=0, ge=0)
    
    # Labor
    labor_hours: Optional[Decimal] = Field(None, ge=0)
    crew_size: int = Field(default=1, gt=0)
    
    # Flags
    is_subcontracted: bool = Field(default=False)
    is_inspection: bool = Field(default=False)


class RoutingCreate(RoutingBase):
    """Routing creation request."""
    pass


class RoutingUpdate(BaseModel):
    """Routing update request."""
    
    sequence: Optional[int] = Field(None, gt=0)
    operation_name: Optional[str] = Field(None, min_length=1, max_length=255)
    operation_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    
    station_id: Optional[int] = Field(None, gt=0)
    
    standard_time_seconds: Optional[int] = Field(None, gt=0)
    setup_time_seconds: Optional[int] = Field(None, ge=0)
    move_time_seconds: Optional[int] = Field(None, ge=0)
    queue_time_seconds: Optional[int] = Field(None, ge=0)
    
    labor_hours: Optional[Decimal] = Field(None, ge=0)
    crew_size: Optional[int] = Field(None, gt=0)
    
    is_subcontracted: Optional[bool] = None
    is_inspection: Optional[bool] = None


class RoutingResponse(BaseModel):
    """Routing response."""
    
    id: int
    product_id: int
    sequence: int
    operation_name: str
    operation_code: Optional[str]
    description: Optional[str]
    
    station_id: int
    
    standard_time_seconds: int
    setup_time_seconds: int
    move_time_seconds: int
    queue_time_seconds: int
    total_time_seconds: int
    
    labor_hours: Optional[Decimal]
    crew_size: int
    
    is_subcontracted: bool
    is_inspection: bool
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Helper Functions
# =============================================================================


def product_to_response(product: Product) -> ProductResponse:
    """Convert Product model to response schema."""
    return ProductResponse(
        id=product.id,
        name=product.name,
        part_number=product.part_number,
        revision=product.revision,
        full_part_number=product.full_part_number,
        description=product.description,
        product_family=product.product_family,
        product_category=product.product_category,
        unit_of_measure=product.unit_of_measure.value if isinstance(product.unit_of_measure, UnitOfMeasure) else product.unit_of_measure,
        weight_kg=product.weight_kg,
        dimensions=product.dimensions,
        standard_cost=product.standard_cost,
        standard_labor_hours=product.standard_labor_hours,
        lead_time_days=product.lead_time_days,
        setup_time_hours=product.setup_time_hours,
        status=product.status.value if isinstance(product.status, ProductStatus) else product.status,
        is_active=product.is_active,
        bom_item_count=len(product.bom_items) if product.bom_items else 0,
        routing_step_count=len(product.routings) if product.routings else 0,
        created_at=product.created_at,
        updated_at=product.updated_at,
        created_by_id=product.created_by_id,
        updated_by_id=product.updated_by_id,
    )


def product_to_list_response(product: Product) -> ProductListResponse:
    """Convert Product model to list response schema."""
    return ProductListResponse(
        id=product.id,
        name=product.name,
        part_number=product.part_number,
        revision=product.revision,
        full_part_number=product.full_part_number,
        product_family=product.product_family,
        status=product.status.value if isinstance(product.status, ProductStatus) else product.status,
        standard_cost=product.standard_cost,
        lead_time_days=product.lead_time_days,
        created_at=product.created_at,
    )


def bom_item_to_response(item: BOMItem) -> BOMItemResponse:
    """Convert BOMItem model to response schema."""
    return BOMItemResponse(
        id=item.id,
        product_id=item.product_id,
        component_part_number=item.component_part_number,
        component_product_id=item.component_product_id,
        component_description=item.component_description,
        quantity=item.quantity,
        unit_of_measure=item.unit_of_measure.value if isinstance(item.unit_of_measure, UnitOfMeasure) else item.unit_of_measure,
        extended_quantity=item.extended_quantity,
        position=item.position,
        find_number=item.find_number,
        is_critical=item.is_critical,
        is_phantom=item.is_phantom,
        is_alternate=item.is_alternate,
        scrap_factor=item.scrap_factor,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def routing_to_response(routing: Routing) -> RoutingResponse:
    """Convert Routing model to response schema."""
    return RoutingResponse(
        id=routing.id,
        product_id=routing.product_id,
        sequence=routing.sequence,
        operation_name=routing.operation_name,
        operation_code=routing.operation_code,
        description=routing.description,
        station_id=routing.station_id,
        standard_time_seconds=routing.standard_time_seconds,
        setup_time_seconds=routing.setup_time_seconds,
        move_time_seconds=routing.move_time_seconds,
        queue_time_seconds=routing.queue_time_seconds,
        total_time_seconds=routing.total_time_seconds,
        labor_hours=routing.labor_hours,
        crew_size=routing.crew_size,
        is_subcontracted=routing.is_subcontracted,
        is_inspection=routing.is_inspection,
        created_at=routing.created_at,
        updated_at=routing.updated_at,
    )


# =============================================================================
# Product Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse)
async def list_products(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Search in name, part_number"),
    product_family: Optional[str] = Query(default=None, description="Filter by product family"),
    product_category: Optional[str] = Query(default=None, description="Filter by product category"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    sort: Optional[str] = Query(default=None, description="Sort field"),
    include_deleted: bool = Query(default=False, description="Include soft-deleted products"),
):
    """
    List products with filtering and pagination.
    """
    # Build base query
    query = select(Product)
    count_query = select(func.count(Product.id))
    
    # Exclude deleted unless requested
    if not include_deleted:
        query = query.where(Product.deleted_at.is_(None))
        count_query = count_query.where(Product.deleted_at.is_(None))
    
    # Apply search filter
    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.part_number.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Apply product_family filter
    if product_family:
        query = query.where(Product.product_family == product_family)
        count_query = count_query.where(Product.product_family == product_family)
    
    # Apply product_category filter
    if product_category:
        query = query.where(Product.product_category == product_category)
        count_query = count_query.where(Product.product_category == product_category)
    
    # Apply status filter
    if status:
        query = query.where(Product.status == status)
        count_query = count_query.where(Product.status == status)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    if sort:
        sort_orders = parse_sort_param(sort)
        for sort_order in sort_orders:
            if hasattr(Product, sort_order.field):
                column = getattr(Product, sort_order.field)
                if sort_order.direction == "desc":
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())
    else:
        # Default sort by part_number
        query = query.order_by(Product.part_number.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Convert to response
    items = [product_to_list_response(p) for p in products]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new product.
    """
    # Check for duplicate part_number + revision
    existing = await db.execute(
        select(Product).where(
            Product.part_number == product_data.part_number,
            Product.revision == product_data.revision,
            Product.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            message=f"Product with part number '{product_data.part_number}' revision '{product_data.revision}' already exists"
        )
    
    # Create product
    product_dict = product_data.model_dump(exclude_unset=True)
    
    # Convert enum values
    if "unit_of_measure" in product_dict:
        product_dict["unit_of_measure"] = UnitOfMeasure(product_dict["unit_of_measure"])
    if "status" in product_dict:
        product_dict["status"] = ProductStatus(product_dict["status"])
    
    product = Product(
        **product_dict,
        created_by_id=current_user.id,
    )
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return build_created_response(
        data=product_to_response(product),
        resource_name="Product",
    )


@router.get("/{product_id}", response_model=APIResponse)
async def get_product(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False, description="Include if soft-deleted"),
):
    """
    Get product by ID.
    """
    query = select(Product).where(Product.id == product_id)
    
    if not include_deleted:
        query = query.where(Product.deleted_at.is_(None))
    
    # Eager load relationships
    query = query.options(
        selectinload(Product.bom_items),
        selectinload(Product.routings),
    )
    
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    return build_response(data=product_to_response(product))


@router.patch("/{product_id}", response_model=APIResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a product.
    """
    # Get existing product
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Update fields
    update_dict = product_data.model_dump(exclude_unset=True)
    
    # Convert enum values
    if "unit_of_measure" in update_dict and update_dict["unit_of_measure"]:
        update_dict["unit_of_measure"] = UnitOfMeasure(update_dict["unit_of_measure"])
    if "status" in update_dict and update_dict["status"]:
        update_dict["status"] = ProductStatus(update_dict["status"])
    
    for key, value in update_dict.items():
        setattr(product, key, value)
    
    product.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(product)
    
    return build_updated_response(
        data=product_to_response(product),
        resource_name="Product",
    )


@router.delete("/{product_id}", response_model=APIResponse)
async def delete_product(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False, description="Permanently delete"),
):
    """
    Delete a product (soft delete by default).
    """
    # Get existing product
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    if product.deleted_at and not hard_delete:
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    if hard_delete:
        if not current_user.is_superuser:
            raise ForbiddenError(
                message="Only administrators can permanently delete products"
            )
        await db.delete(product)
    else:
        product.deleted_at = now_utc()
        product.deleted_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Product")


@router.post("/{product_id}/new-revision", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_revision(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
    new_revision: str = Query(..., min_length=1, max_length=20, description="New revision code"),
    copy_bom: bool = Query(default=True, description="Copy BOM items to new revision"),
    copy_routing: bool = Query(default=True, description="Copy routing to new revision"),
):
    """
    Create a new revision of a product, optionally copying BOM and routing.
    """
    # Get existing product
    result = await db.execute(
        select(Product)
        .where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
        .options(
            selectinload(Product.bom_items),
            selectinload(Product.routings),
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Check if new revision already exists
    existing = await db.execute(
        select(Product).where(
            Product.part_number == product.part_number,
            Product.revision == new_revision,
            Product.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            message=f"Revision '{new_revision}' already exists for part {product.part_number}"
        )
    
    # Create new product revision
    new_product = Product(
        name=product.name,
        part_number=product.part_number,
        revision=new_revision,
        description=product.description,
        product_family=product.product_family,
        product_category=product.product_category,
        unit_of_measure=product.unit_of_measure,
        weight_kg=product.weight_kg,
        dimensions=product.dimensions,
        standard_cost=product.standard_cost,
        standard_labor_hours=product.standard_labor_hours,
        lead_time_days=product.lead_time_days,
        setup_time_hours=product.setup_time_hours,
        status=ProductStatus.PROTOTYPE,  # New revisions start as prototype
        created_by_id=current_user.id,
    )
    
    db.add(new_product)
    await db.flush()  # Get the new product ID
    
    # Copy BOM items if requested
    if copy_bom and product.bom_items:
        for bom_item in product.bom_items:
            new_bom_item = BOMItem(
                product_id=new_product.id,
                component_part_number=bom_item.component_part_number,
                component_product_id=bom_item.component_product_id,
                component_description=bom_item.component_description,
                quantity=bom_item.quantity,
                unit_of_measure=bom_item.unit_of_measure,
                position=bom_item.position,
                find_number=bom_item.find_number,
                is_critical=bom_item.is_critical,
                is_phantom=bom_item.is_phantom,
                is_alternate=bom_item.is_alternate,
                scrap_factor=bom_item.scrap_factor,
                created_by_id=current_user.id,
            )
            db.add(new_bom_item)
    
    # Copy routing if requested
    if copy_routing and product.routings:
        for routing in product.routings:
            new_routing = Routing(
                product_id=new_product.id,
                sequence=routing.sequence,
                operation_name=routing.operation_name,
                operation_code=routing.operation_code,
                description=routing.description,
                station_id=routing.station_id,
                standard_time_seconds=routing.standard_time_seconds,
                setup_time_seconds=routing.setup_time_seconds,
                move_time_seconds=routing.move_time_seconds,
                queue_time_seconds=routing.queue_time_seconds,
                labor_hours=routing.labor_hours,
                crew_size=routing.crew_size,
                is_subcontracted=routing.is_subcontracted,
                is_inspection=routing.is_inspection,
                created_by_id=current_user.id,
            )
            db.add(new_routing)
    
    await db.commit()
    await db.refresh(new_product)
    
    return build_created_response(
        data=product_to_response(new_product),
        resource_name=f"Product revision {new_revision}",
    )


# =============================================================================
# BOM Endpoints
# =============================================================================


@router.get("/{product_id}/bom", response_model=APIResponse)
async def list_bom_items(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    List all BOM items for a product.
    """
    # Verify product exists
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Get BOM items
    result = await db.execute(
        select(BOMItem)
        .where(BOMItem.product_id == product_id)
        .order_by(BOMItem.position.asc())
    )
    items = result.scalars().all()
    
    return build_response(
        data=[bom_item_to_response(item) for item in items]
    )


@router.post("/{product_id}/bom", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_bom_item(
    product_id: int,
    item_data: BOMItemCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Add a BOM item to a product.
    """
    # Verify product exists
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Check for duplicate
    existing = await db.execute(
        select(BOMItem).where(
            BOMItem.product_id == product_id,
            BOMItem.component_part_number == item_data.component_part_number,
            BOMItem.position == item_data.position,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            message=f"BOM item with component '{item_data.component_part_number}' at position {item_data.position} already exists"
        )
    
    # Create BOM item
    item_dict = item_data.model_dump(exclude_unset=True)
    
    # Convert enum values
    if "unit_of_measure" in item_dict:
        item_dict["unit_of_measure"] = UnitOfMeasure(item_dict["unit_of_measure"])
    
    bom_item = BOMItem(
        product_id=product_id,
        **item_dict,
        created_by_id=current_user.id,
    )
    
    db.add(bom_item)
    await db.commit()
    await db.refresh(bom_item)
    
    return build_created_response(
        data=bom_item_to_response(bom_item),
        resource_name="BOM item",
    )


@router.patch("/{product_id}/bom/{bom_id}", response_model=APIResponse)
async def update_bom_item(
    product_id: int,
    bom_id: int,
    item_data: BOMItemUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a BOM item.
    """
    # Get existing BOM item
    result = await db.execute(
        select(BOMItem).where(
            BOMItem.id == bom_id,
            BOMItem.product_id == product_id,
        )
    )
    bom_item = result.scalar_one_or_none()
    
    if not bom_item:
        raise NotFoundError(resource="BOM item", identifier=str(bom_id))
    
    # Update fields
    update_dict = item_data.model_dump(exclude_unset=True)
    
    # Convert enum values
    if "unit_of_measure" in update_dict and update_dict["unit_of_measure"]:
        update_dict["unit_of_measure"] = UnitOfMeasure(update_dict["unit_of_measure"])
    
    for key, value in update_dict.items():
        setattr(bom_item, key, value)
    
    bom_item.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(bom_item)
    
    return build_updated_response(
        data=bom_item_to_response(bom_item),
        resource_name="BOM item",
    )


@router.delete("/{product_id}/bom/{bom_id}", response_model=APIResponse)
async def delete_bom_item(
    product_id: int,
    bom_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Delete a BOM item.
    """
    # Get existing BOM item
    result = await db.execute(
        select(BOMItem).where(
            BOMItem.id == bom_id,
            BOMItem.product_id == product_id,
        )
    )
    bom_item = result.scalar_one_or_none()
    
    if not bom_item:
        raise NotFoundError(resource="BOM item", identifier=str(bom_id))
    
    await db.delete(bom_item)
    await db.commit()
    
    return build_deleted_response(resource_name="BOM item")


# =============================================================================
# Routing Endpoints
# =============================================================================


@router.get("/{product_id}/routing", response_model=APIResponse)
async def list_routing_steps(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    List all routing steps for a product.
    """
    # Verify product exists
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Get routing steps
    result = await db.execute(
        select(Routing)
        .where(Routing.product_id == product_id)
        .order_by(Routing.sequence.asc())
    )
    routings = result.scalars().all()
    
    return build_response(
        data=[routing_to_response(r) for r in routings]
    )


@router.post("/{product_id}/routing", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_routing_step(
    product_id: int,
    routing_data: RoutingCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Add a routing step to a product.
    """
    # Verify product exists
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Check for duplicate sequence
    existing = await db.execute(
        select(Routing).where(
            Routing.product_id == product_id,
            Routing.sequence == routing_data.sequence,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            message=f"Routing step with sequence {routing_data.sequence} already exists"
        )
    
    # Create routing
    routing_dict = routing_data.model_dump(exclude_unset=True)
    
    routing = Routing(
        product_id=product_id,
        **routing_dict,
        created_by_id=current_user.id,
    )
    
    db.add(routing)
    await db.commit()
    await db.refresh(routing)
    
    return build_created_response(
        data=routing_to_response(routing),
        resource_name="Routing step",
    )


@router.patch("/{product_id}/routing/{routing_id}", response_model=APIResponse)
async def update_routing_step(
    product_id: int,
    routing_id: int,
    routing_data: RoutingUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a routing step.
    """
    # Get existing routing
    result = await db.execute(
        select(Routing).where(
            Routing.id == routing_id,
            Routing.product_id == product_id,
        )
    )
    routing = result.scalar_one_or_none()
    
    if not routing:
        raise NotFoundError(resource="Routing step", identifier=str(routing_id))
    
    # Check for sequence conflict if updating sequence
    update_dict = routing_data.model_dump(exclude_unset=True)
    if "sequence" in update_dict and update_dict["sequence"] != routing.sequence:
        existing = await db.execute(
            select(Routing).where(
                Routing.product_id == product_id,
                Routing.sequence == update_dict["sequence"],
                Routing.id != routing_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                message=f"Routing step with sequence {update_dict['sequence']} already exists"
            )
    
    for key, value in update_dict.items():
        setattr(routing, key, value)
    
    routing.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(routing)
    
    return build_updated_response(
        data=routing_to_response(routing),
        resource_name="Routing step",
    )


@router.delete("/{product_id}/routing/{routing_id}", response_model=APIResponse)
async def delete_routing_step(
    product_id: int,
    routing_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Delete a routing step.
    """
    # Get existing routing
    result = await db.execute(
        select(Routing).where(
            Routing.id == routing_id,
            Routing.product_id == product_id,
        )
    )
    routing = result.scalar_one_or_none()
    
    if not routing:
        raise NotFoundError(resource="Routing step", identifier=str(routing_id))
    
    await db.delete(routing)
    await db.commit()
    
    return build_deleted_response(resource_name="Routing step")


# =============================================================================
# Product Statistics Endpoints
# =============================================================================


@router.get("/{product_id}/stats", response_model=APIResponse)
async def get_product_stats(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Get statistics for a product including BOM analysis and routing summary.
    """
    # Verify product exists
    result = await db.execute(
        select(Product)
        .where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
        .options(
            selectinload(Product.bom_items),
            selectinload(Product.routings),
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise NotFoundError(resource="Product", identifier=str(product_id))
    
    # Calculate BOM statistics
    bom_count = len(product.bom_items) if product.bom_items else 0
    critical_components = sum(1 for item in product.bom_items if item.is_critical) if product.bom_items else 0
    phantom_assemblies = sum(1 for item in product.bom_items if item.is_phantom) if product.bom_items else 0
    
    # Calculate routing statistics
    routing_count = len(product.routings) if product.routings else 0
    total_standard_time = sum(r.standard_time_seconds for r in product.routings) if product.routings else 0
    total_setup_time = sum(r.setup_time_seconds for r in product.routings) if product.routings else 0
    inspection_steps = sum(1 for r in product.routings if r.is_inspection) if product.routings else 0
    subcontracted_steps = sum(1 for r in product.routings if r.is_subcontracted) if product.routings else 0
    
    stats = {
        "product_id": product.id,
        "part_number": product.part_number,
        "revision": product.revision,
        "status": product.status.value if isinstance(product.status, ProductStatus) else product.status,
        "bom": {
            "total_items": bom_count,
            "critical_components": critical_components,
            "phantom_assemblies": phantom_assemblies,
        },
        "routing": {
            "total_steps": routing_count,
            "total_standard_time_seconds": total_standard_time,
            "total_setup_time_seconds": total_setup_time,
            "inspection_steps": inspection_steps,
            "subcontracted_steps": subcontracted_steps,
            "total_time_minutes": round((total_standard_time + total_setup_time) / 60, 2),
        },
        "cost": {
            "standard_cost": float(product.standard_cost) if product.standard_cost else None,
            "standard_labor_hours": float(product.standard_labor_hours) if product.standard_labor_hours else None,
        },
        "lead_time_days": product.lead_time_days,
    }
    
    return build_response(data=stats)

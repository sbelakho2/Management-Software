"""
Account Management Endpoints

Provides account (customer, supplier, prospect) management including:
- List accounts with filtering and pagination
- Create/read/update/delete accounts
- Account hierarchy management
- Account search and analytics
"""

from datetime import datetime
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from sensei.api.deps import (
    CurrentUser,
    DBSession,
    Pagination,
    RoleChecker,
)
from sensei.api.exceptions import (
    ConflictError,
    NotFoundError,
    ForbiddenError,
)
from sensei.api.schemas import (
    APIResponse,
    FilterOperator,
    PaginatedResponse,
    PaginationMeta,
    SortOrder,
    BulkDeleteRequest,
    success_response,
    error_response,
)
from sensei.api.utils import (
    parse_sort_param,
    parse_filter_param,
    build_response,
    build_paginated_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    now_utc,
)
from sensei.models.account import (
    Account,
    AccountContact,
    AccountStatus,
    AccountTier,
    AccountType,
    Contact,
)


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class AddressSchema(BaseModel):
    """Address fields."""
    
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="Morocco", max_length=100)


class AccountBase(BaseModel):
    """Base account fields."""
    
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    account_type: str = Field(default=AccountType.PROSPECT.value)
    status: str = Field(default=AccountStatus.LEAD.value)
    tier: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    sub_industry: Optional[str] = Field(None, max_length=100)
    
    # Contact information
    website: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    fax: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="Morocco", max_length=100)
    
    # Business info
    tax_id: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=100)
    employees_count: Optional[int] = Field(None, ge=0)
    annual_revenue: Optional[float] = Field(None, ge=0)
    revenue_currency: str = Field(default="MAD", max_length=3)
    
    # Sales info
    lead_source: Optional[str] = Field(None, max_length=100)
    referred_by: Optional[str] = Field(None, max_length=255)
    
    # Notes
    description: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # Custom fields
    custom_fields: Optional[dict] = None
    tags: Optional[list[str]] = None
    
    # Parent account
    parent_id: Optional[UUID] = None
    
    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        valid_types = [t.value for t in AccountType]
        if v not in valid_types:
            raise ValueError(f"Invalid account type. Must be one of: {valid_types}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [s.value for s in AccountStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v
    
    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_tiers = [t.value for t in AccountTier]
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier. Must be one of: {valid_tiers}")
        return v


class AccountCreate(AccountBase):
    """Account creation request."""
    
    account_number: Optional[str] = Field(None, max_length=50)
    
    # Dates
    established_date: Optional[datetime] = None
    first_contact_date: Optional[datetime] = None
    customer_since: Optional[datetime] = None
    
    # Supplier capabilities
    capabilities: Optional[list[str]] = None
    certifications: Optional[list[str]] = None


class AccountUpdate(BaseModel):
    """Account update request (all fields optional)."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    account_number: Optional[str] = Field(None, max_length=50)
    account_type: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    sub_industry: Optional[str] = Field(None, max_length=100)
    
    # Contact information
    website: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    fax: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Business info
    tax_id: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=100)
    employees_count: Optional[int] = Field(None, ge=0)
    annual_revenue: Optional[float] = Field(None, ge=0)
    revenue_currency: Optional[str] = Field(None, max_length=3)
    
    # Sales info
    lead_source: Optional[str] = Field(None, max_length=100)
    referred_by: Optional[str] = Field(None, max_length=255)
    
    # Dates
    established_date: Optional[datetime] = None
    first_contact_date: Optional[datetime] = None
    customer_since: Optional[datetime] = None
    
    # Supplier capabilities
    capabilities: Optional[list[str]] = None
    certifications: Optional[list[str]] = None
    
    # Scoring
    qualification_score: Optional[float] = Field(None, ge=0, le=100)
    health_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Notes
    description: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # Custom fields
    custom_fields: Optional[dict] = None
    tags: Optional[list[str]] = None
    
    # Parent account
    parent_id: Optional[UUID] = None


class AccountResponse(BaseModel):
    """Account response."""

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    legal_name: Optional[str]
    account_number: Optional[str]
    account_type: str
    status: str
    tier: Optional[str]
    industry: Optional[str]
    sub_industry: Optional[str]
    
    # Contact
    website: Optional[str]
    phone: Optional[str]
    fax: Optional[str]
    email: Optional[str]
    
    # Address
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state_province: Optional[str]
    postal_code: Optional[str]
    country: str
    full_address: Optional[str]
    
    # Business
    tax_id: Optional[str]
    registration_number: Optional[str]
    employees_count: Optional[int]
    annual_revenue: Optional[float]
    revenue_currency: str
    
    # Sales
    lead_source: Optional[str]
    referred_by: Optional[str]
    
    # Dates
    established_date: Optional[datetime]
    first_contact_date: Optional[datetime]
    customer_since: Optional[datetime]
    
    # Supplier
    capabilities: Optional[list[str]]
    certifications: Optional[list[str]]
    
    # Scoring
    qualification_score: Optional[float]
    health_score: Optional[float]
    
    # Notes
    description: Optional[str]
    internal_notes: Optional[str]
    
    # Meta
    custom_fields: Optional[dict]
    tags: Optional[list[str]]
    parent_id: Optional[UUID]
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    updated_by_id: Optional[UUID]
    
    # Computed
    is_customer: bool
    is_supplier: bool
    


class AccountListResponse(BaseModel):
    """Simplified account for list views."""

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    account_number: Optional[str]
    account_type: str
    status: str
    tier: Optional[str]
    industry: Optional[str]
    city: Optional[str]
    country: str
    phone: Optional[str]
    email: Optional[str]
    created_at: datetime
    


class AccountStatsResponse(BaseModel):
    """Account statistics."""
    
    total_accounts: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    by_tier: dict[str, int]
    by_country: dict[str, int]
    new_this_month: int
    active_customers: int


# =============================================================================
# Helper Functions
# =============================================================================


def account_to_response(account: Account) -> AccountResponse:
    """Convert Account model to response schema."""
    return AccountResponse(
        id=account.id,
        name=account.name,
        legal_name=account.legal_name,
        account_number=account.account_number,
        account_type=account.account_type,
        status=account.status,
        tier=account.tier,
        industry=account.industry,
        sub_industry=account.sub_industry,
        website=account.website,
        phone=account.phone,
        fax=account.fax,
        email=account.email,
        address_line1=account.address_line1,
        address_line2=account.address_line2,
        city=account.city,
        state_province=account.state_province,
        postal_code=account.postal_code,
        country=account.country,
        full_address=account.full_address,
        tax_id=account.tax_id,
        registration_number=account.registration_number,
        employees_count=account.employees_count,
        annual_revenue=float(account.annual_revenue) if account.annual_revenue else None,
        revenue_currency=account.revenue_currency,
        lead_source=account.lead_source,
        referred_by=account.referred_by,
        established_date=account.established_date,
        first_contact_date=account.first_contact_date,
        customer_since=account.customer_since,
        capabilities=account.capabilities,
        certifications=account.certifications,
        qualification_score=float(account.qualification_score) if account.qualification_score else None,
        health_score=float(account.health_score) if account.health_score else None,
        description=account.description,
        internal_notes=account.internal_notes,
        custom_fields=account.custom_fields,
        tags=account.tags,
        parent_id=account.parent_id,
        created_at=account.created_at,
        updated_at=account.updated_at,
        created_by_id=account.created_by_id,
        updated_by_id=account.updated_by_id,
        is_customer=account.is_customer,
        is_supplier=account.is_supplier,
    )


def account_to_list_response(account: Account) -> AccountListResponse:
    """Convert Account model to list response schema."""
    return AccountListResponse(
        id=account.id,
        name=account.name,
        account_number=account.account_number,
        account_type=account.account_type,
        status=account.status,
        tier=account.tier,
        industry=account.industry,
        city=account.city,
        country=account.country,
        phone=account.phone,
        email=account.email,
        created_at=account.created_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse)
async def list_accounts(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in name, email, account_number"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    city: Optional[str] = Query(None, description="Filter by city"),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent account"),
    sort: Optional[str] = Query(None, description="Sort field (e.g., 'name:asc,created_at:desc')"),
    include_deleted: bool = Query(False, description="Include soft-deleted accounts"),
):
    """
    List accounts with filtering and pagination.
    
    Supports:
    - Full-text search across name, email, account_number
    - Filtering by type, status, tier, industry, country, city
    - Sorting by any field
    - Pagination
    """
    # Build base query
    query = select(Account)
    count_query = select(func.count(Account.id))
    
    # Exclude deleted unless requested
    if not include_deleted:
        query = query.where(Account.deleted_at.is_(None))
        count_query = count_query.where(Account.deleted_at.is_(None))
    
    # Apply search filter
    if search:
        search_filter = or_(
            Account.name.ilike(f"%{search}%"),
            Account.email.ilike(f"%{search}%"),
            Account.account_number.ilike(f"%{search}%"),
            Account.legal_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Apply type filter
    if account_type:
        query = query.where(Account.account_type == account_type)
        count_query = count_query.where(Account.account_type == account_type)
    
    # Apply status filter
    if status:
        query = query.where(Account.status == status)
        count_query = count_query.where(Account.status == status)
    
    # Apply tier filter
    if tier:
        query = query.where(Account.tier == tier)
        count_query = count_query.where(Account.tier == tier)
    
    # Apply industry filter
    if industry:
        query = query.where(Account.industry == industry)
        count_query = count_query.where(Account.industry == industry)
    
    # Apply country filter
    if country:
        query = query.where(Account.country == country)
        count_query = count_query.where(Account.country == country)
    
    # Apply city filter
    if city:
        query = query.where(Account.city == city)
        count_query = count_query.where(Account.city == city)
    
    # Apply parent filter
    if parent_id:
        query = query.where(Account.parent_id == parent_id)
        count_query = count_query.where(Account.parent_id == parent_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_orders = parse_sort_param(sort) if sort else []
    if not sort_orders:
        # Default sort by name
        query = query.order_by(Account.name.asc())
    else:
        for sort_order in sort_orders:
            if hasattr(Account, sort_order.field):
                column = getattr(Account, sort_order.field)
                if sort_order.direction == "desc":
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    # Convert to response
    items = [account_to_list_response(acc) for acc in accounts]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new account.
    
    Returns the created account with generated ID and timestamps.
    """
    # Check for duplicate account number
    if account_data.account_number:
        existing = await db.execute(
            select(Account).where(
                Account.account_number == account_data.account_number,
                Account.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                message=f"Account with number '{account_data.account_number}' already exists"
            )
    
    # Validate parent account if specified
    if account_data.parent_id:
        parent = await db.execute(
            select(Account).where(
                Account.id == account_data.parent_id,
                Account.deleted_at.is_(None),
            )
        )
        if not parent.scalar_one_or_none():
            raise NotFoundError(
                resource="Parent Account",
                identifier=str(account_data.parent_id),
            )
    
    # Create account
    account = Account(
        **account_data.model_dump(exclude_unset=True),
        created_by_id=current_user.id,
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    return build_created_response(
        data=account_to_response(account),
        resource_name="Account",
    )


@router.get("/{account_id}", response_model=APIResponse)
async def get_account(
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(False, description="Include if soft-deleted"),
):
    """
    Get account by ID.
    
    Returns full account details including computed properties.
    """
    query = select(Account).where(Account.id == account_id)
    
    if not include_deleted:
        query = query.where(Account.deleted_at.is_(None))
    
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise NotFoundError(resource="Account", identifier=str(account_id))
    
    return build_response(data=account_to_response(account))


@router.patch("/{account_id}", response_model=APIResponse)
async def update_account(
    account_id: UUID,
    account_data: AccountUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update an account.
    
    Only provided fields are updated (partial update).
    """
    # Get existing account
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise NotFoundError(resource="Account", identifier=str(account_id))
    
    # Check for duplicate account number if changing
    update_dict = account_data.model_dump(exclude_unset=True)
    if "account_number" in update_dict and update_dict["account_number"]:
        existing = await db.execute(
            select(Account).where(
                Account.account_number == update_dict["account_number"],
                Account.id != account_id,
                Account.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                message=f"Account with number '{update_dict['account_number']}' already exists"
            )
    
    # Validate parent account if changing
    if "parent_id" in update_dict and update_dict["parent_id"]:
        # Prevent self-reference
        if update_dict["parent_id"] == account_id:
            raise ConflictError(message="Account cannot be its own parent")
        
        parent = await db.execute(
            select(Account).where(
                Account.id == update_dict["parent_id"],
                Account.deleted_at.is_(None),
            )
        )
        if not parent.scalar_one_or_none():
            raise NotFoundError(
                resource="Parent Account",
                identifier=str(update_dict["parent_id"]),
            )
    
    # Update fields
    for key, value in update_dict.items():
        setattr(account, key, value)
    
    account.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(account)
    
    return build_updated_response(
        data=account_to_response(account),
        resource_name="Account",
    )


@router.delete("/{account_id}", response_model=APIResponse)
async def delete_account(
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(False, description="Permanently delete (requires admin)"),
):
    """
    Delete an account (soft delete by default).
    
    Soft delete marks the account as deleted but retains the record.
    Hard delete permanently removes the record (admin only).
    """
    # Get existing account
    result = await db.execute(
        select(Account).where(Account.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise NotFoundError(resource="Account", identifier=str(account_id))
    
    if account.deleted_at and not hard_delete:
        raise NotFoundError(resource="Account", identifier=str(account_id))
    
    if hard_delete:
        # Check admin permission
        if not current_user.is_superuser:
            raise ForbiddenError(
                message="Only administrators can permanently delete accounts"
            )
        await db.delete(account)
    else:
        # Soft delete
        account.deleted_at = now_utc()
        account.deleted_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Account")


@router.post("/{account_id}/restore", response_model=APIResponse)
async def restore_account(
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Restore a soft-deleted account.
    """
    # Get deleted account
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.deleted_at.isnot(None),
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise NotFoundError(
            resource="Deleted Account",
            identifier=str(account_id),
        )
    
    # Restore
    account.deleted_at = None
    account.deleted_by_id = None
    account.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(account)
    
    return build_response(
        data=account_to_response(account),
        message="Account restored successfully",
    )


@router.delete("", response_model=APIResponse)
async def bulk_delete_accounts(
    request: BulkDeleteRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Bulk delete multiple accounts (soft delete).
    """
    # Get accounts
    result = await db.execute(
        select(Account).where(
            Account.id.in_(request.ids),
            Account.deleted_at.is_(None),
        )
    )
    accounts = result.scalars().all()
    
    if not accounts:
        raise NotFoundError(resource="Accounts", identifier="provided IDs")
    
    deleted_count = 0
    for account in accounts:
        if request.force:
            if not current_user.is_superuser:
                raise ForbiddenError(
                    message="Only administrators can permanently delete accounts"
                )
            await db.delete(account)
        else:
            account.deleted_at = now_utc()
            account.deleted_by_id = current_user.id
        deleted_count += 1
    
    await db.commit()
    
    return build_response(
        data={"deleted_count": deleted_count},
        message=f"Successfully deleted {deleted_count} account(s)",
    )


@router.get("/stats", response_model=APIResponse)
async def get_account_stats(
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Get account statistics and analytics.
    """
    # Total accounts
    total_result = await db.execute(
        select(func.count(Account.id)).where(Account.deleted_at.is_(None))
    )
    total_accounts = total_result.scalar() or 0
    
    # By type
    type_result = await db.execute(
        select(Account.account_type, func.count(Account.id))
        .where(Account.deleted_at.is_(None))
        .group_by(Account.account_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}
    
    # By status
    status_result = await db.execute(
        select(Account.status, func.count(Account.id))
        .where(Account.deleted_at.is_(None))
        .group_by(Account.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}
    
    # By tier
    tier_result = await db.execute(
        select(Account.tier, func.count(Account.id))
        .where(Account.deleted_at.is_(None), Account.tier.isnot(None))
        .group_by(Account.tier)
    )
    by_tier = {row[0]: row[1] for row in tier_result.all()}
    
    # By country (top 10)
    country_result = await db.execute(
        select(Account.country, func.count(Account.id))
        .where(Account.deleted_at.is_(None))
        .group_by(Account.country)
        .order_by(func.count(Account.id).desc())
        .limit(10)
    )
    by_country = {row[0]: row[1] for row in country_result.all()}
    
    # New this month
    month_start = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_result = await db.execute(
        select(func.count(Account.id))
        .where(
            Account.deleted_at.is_(None),
            Account.created_at >= month_start,
        )
    )
    new_this_month = new_result.scalar() or 0
    
    # Active customers
    active_result = await db.execute(
        select(func.count(Account.id))
        .where(
            Account.deleted_at.is_(None),
            Account.account_type == AccountType.CUSTOMER.value,
            Account.status == AccountStatus.ACTIVE.value,
        )
    )
    active_customers = active_result.scalar() or 0
    
    stats = AccountStatsResponse(
        total_accounts=total_accounts,
        by_type=by_type,
        by_status=by_status,
        by_tier=by_tier,
        by_country=by_country,
        new_this_month=new_this_month,
        active_customers=active_customers,
    )
    
    return build_response(data=stats)


@router.get("/{account_id}/subsidiaries", response_model=PaginatedResponse)
async def list_subsidiaries(
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List subsidiary accounts (children) of an account.
    """
    # Verify parent account exists
    parent_result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.deleted_at.is_(None),
        )
    )
    if not parent_result.scalar_one_or_none():
        raise NotFoundError(resource="Account", identifier=str(account_id))
    
    # Get subsidiaries
    query = select(Account).where(
        Account.parent_id == account_id,
        Account.deleted_at.is_(None),
    )
    count_query = select(func.count(Account.id)).where(
        Account.parent_id == account_id,
        Account.deleted_at.is_(None),
    )
    
    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Account.name.asc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    subsidiaries = result.scalars().all()
    
    items = [account_to_list_response(acc) for acc in subsidiaries]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )

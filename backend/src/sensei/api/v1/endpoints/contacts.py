"""
Contact Management Endpoints

Provides contact (individuals) management including:
- List contacts with filtering and pagination
- Create/read/update/delete contacts
- Contact-account relationships
- Contact search
"""

from datetime import datetime
from typing import Annotated, Optional
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
from sensei.models.account import (
    Account,
    AccountContact,
    Contact,
    ContactRole,
)


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ContactBase(BaseModel):
    """Base contact fields."""
    
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    salutation: Optional[str] = Field(None, max_length=20)
    suffix: Optional[str] = Field(None, max_length=20)
    
    # Contact info
    email: Optional[EmailStr] = None
    email_secondary: Optional[EmailStr] = None
    phone_mobile: Optional[str] = Field(None, max_length=50)
    phone_work: Optional[str] = Field(None, max_length=50)
    phone_home: Optional[str] = Field(None, max_length=50)
    
    # Professional
    job_title: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    
    # Preferences
    preferred_language: str = Field(default="fr", max_length=10)
    preferred_contact_method: Optional[str] = Field(None, max_length=50)
    timezone: str = Field(default="Africa/Casablanca", max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Social
    linkedin_url: Optional[str] = Field(None, max_length=500)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    
    # Marketing
    email_opt_out: bool = Field(default=False)
    do_not_call: bool = Field(default=False)
    
    # Notes
    description: Optional[str] = None
    
    # Custom
    custom_fields: Optional[dict] = None
    tags: Optional[list[str]] = None


class ContactCreate(ContactBase):
    """Contact creation request."""
    
    birthdate: Optional[datetime] = None
    
    # Optionally associate with an account on creation
    account_id: Optional[UUID] = None
    account_role: Optional[str] = Field(default=ContactRole.OTHER.value)
    is_primary: bool = Field(default=False)


class ContactUpdate(BaseModel):
    """Contact update request (all fields optional)."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    salutation: Optional[str] = Field(None, max_length=20)
    suffix: Optional[str] = Field(None, max_length=20)
    
    # Contact info
    email: Optional[EmailStr] = None
    email_secondary: Optional[EmailStr] = None
    phone_mobile: Optional[str] = Field(None, max_length=50)
    phone_work: Optional[str] = Field(None, max_length=50)
    phone_home: Optional[str] = Field(None, max_length=50)
    
    # Professional
    job_title: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    
    # Preferences
    preferred_language: Optional[str] = Field(None, max_length=10)
    preferred_contact_method: Optional[str] = Field(None, max_length=50)
    timezone: Optional[str] = Field(None, max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Social
    linkedin_url: Optional[str] = Field(None, max_length=500)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    
    # Marketing
    email_opt_out: Optional[bool] = None
    do_not_call: Optional[bool] = None
    
    # Dates
    birthdate: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    
    # Notes
    description: Optional[str] = None
    
    # Custom
    custom_fields: Optional[dict] = None
    tags: Optional[list[str]] = None


class ContactResponse(BaseModel):
    """Contact response."""

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    first_name: str
    last_name: str
    middle_name: Optional[str]
    salutation: Optional[str]
    suffix: Optional[str]
    full_name: str
    display_name: str
    
    # Contact info
    email: Optional[str]
    email_secondary: Optional[str]
    phone_mobile: Optional[str]
    phone_work: Optional[str]
    phone_home: Optional[str]
    
    # Professional
    job_title: Optional[str]
    department: Optional[str]
    
    # Preferences
    preferred_language: str
    preferred_contact_method: Optional[str]
    timezone: str
    
    # Address
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state_province: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    
    # Social
    linkedin_url: Optional[str]
    twitter_handle: Optional[str]
    
    # Marketing
    email_opt_out: bool
    do_not_call: bool
    
    # Dates
    birthdate: Optional[datetime]
    last_contacted_at: Optional[datetime]
    
    # Notes
    description: Optional[str]
    
    # Custom
    custom_fields: Optional[dict]
    tags: Optional[list[str]]
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    updated_by_id: Optional[UUID]
    


class ContactListResponse(BaseModel):
    """Simplified contact for list views."""

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    first_name: str
    last_name: str
    display_name: str
    email: Optional[str]
    phone_mobile: Optional[str]
    phone_work: Optional[str]
    job_title: Optional[str]
    created_at: datetime
    


class AccountContactRequest(BaseModel):
    """Request to associate a contact with an account."""
    
    account_id: UUID
    role: str = Field(default=ContactRole.OTHER.value)
    is_primary: bool = Field(default=False)
    notes: Optional[str] = None
    start_date: Optional[datetime] = None
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = [r.value for r in ContactRole]
        if v not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
        return v


class AccountContactResponse(BaseModel):
    """Account-contact relationship response."""

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    account_id: UUID
    account_name: str
    contact_id: UUID
    role: str
    is_primary: bool
    is_active: bool
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    


class ContactAccountInfo(BaseModel):
    """Contact with associated account info."""

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    first_name: str
    last_name: str
    display_name: str
    email: Optional[str]
    phone_mobile: Optional[str]
    job_title: Optional[str]
    role: str
    is_primary: bool
    account_id: UUID
    account_name: str
    


# =============================================================================
# Helper Functions
# =============================================================================


def contact_to_response(contact: Contact) -> ContactResponse:
    """Convert Contact model to response schema."""
    return ContactResponse(
        id=contact.id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        middle_name=contact.middle_name,
        salutation=contact.salutation,
        suffix=contact.suffix,
        full_name=contact.full_name,
        display_name=contact.display_name,
        email=contact.email,
        email_secondary=contact.email_secondary,
        phone_mobile=contact.phone_mobile,
        phone_work=contact.phone_work,
        phone_home=contact.phone_home,
        job_title=contact.job_title,
        department=contact.department,
        preferred_language=contact.preferred_language,
        preferred_contact_method=contact.preferred_contact_method,
        timezone=contact.timezone,
        address_line1=contact.address_line1,
        address_line2=contact.address_line2,
        city=contact.city,
        state_province=contact.state_province,
        postal_code=contact.postal_code,
        country=contact.country,
        linkedin_url=contact.linkedin_url,
        twitter_handle=contact.twitter_handle,
        email_opt_out=contact.email_opt_out,
        do_not_call=contact.do_not_call,
        birthdate=contact.birthdate,
        last_contacted_at=contact.last_contacted_at,
        description=contact.description,
        custom_fields=contact.custom_fields,
        tags=contact.tags,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        created_by_id=contact.created_by_id,
        updated_by_id=contact.updated_by_id,
    )


def contact_to_list_response(contact: Contact) -> ContactListResponse:
    """Convert Contact model to list response schema."""
    return ContactListResponse(
        id=contact.id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        display_name=contact.display_name,
        email=contact.email,
        phone_mobile=contact.phone_mobile,
        phone_work=contact.phone_work,
        job_title=contact.job_title,
        created_at=contact.created_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse)
async def list_contacts(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in name, email"),
    account_id: Optional[UUID] = Query(None, description="Filter by associated account"),
    job_title: Optional[str] = Query(None, description="Filter by job title"),
    department: Optional[str] = Query(None, description="Filter by department"),
    country: Optional[str] = Query(None, description="Filter by country"),
    email_opt_out: Optional[bool] = Query(None, description="Filter by email opt-out"),
    sort: Optional[str] = Query(None, description="Sort field"),
    include_deleted: bool = Query(False, description="Include soft-deleted contacts"),
):
    """
    List contacts with filtering and pagination.
    """
    # Build base query
    query = select(Contact)
    count_query = select(func.count(Contact.id))
    
    # Exclude deleted unless requested
    if not include_deleted:
        query = query.where(Contact.deleted_at.is_(None))
        count_query = count_query.where(Contact.deleted_at.is_(None))
    
    # Apply search filter
    if search:
        search_filter = or_(
            Contact.first_name.ilike(f"%{search}%"),
            Contact.last_name.ilike(f"%{search}%"),
            Contact.email.ilike(f"%{search}%"),
            func.concat(Contact.first_name, " ", Contact.last_name).ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Apply account filter
    if account_id:
        query = query.join(AccountContact).where(
            AccountContact.account_id == account_id,
            AccountContact.is_active.is_(True),
        )
        count_query = count_query.join(AccountContact).where(
            AccountContact.account_id == account_id,
            AccountContact.is_active.is_(True),
        )
    
    # Apply job_title filter
    if job_title:
        query = query.where(Contact.job_title.ilike(f"%{job_title}%"))
        count_query = count_query.where(Contact.job_title.ilike(f"%{job_title}%"))
    
    # Apply department filter
    if department:
        query = query.where(Contact.department == department)
        count_query = count_query.where(Contact.department == department)
    
    # Apply country filter
    if country:
        query = query.where(Contact.country == country)
        count_query = count_query.where(Contact.country == country)
    
    # Apply email_opt_out filter
    if email_opt_out is not None:
        query = query.where(Contact.email_opt_out == email_opt_out)
        count_query = count_query.where(Contact.email_opt_out == email_opt_out)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_orders = parse_sort_param(sort) if sort else []
    if not sort_orders:
        # Default sort by last_name, first_name
        query = query.order_by(Contact.last_name.asc(), Contact.first_name.asc())
    else:
        for sort_order in sort_orders:
            if hasattr(Contact, sort_order.field):
                column = getattr(Contact, sort_order.field)
                if sort_order.direction == "desc":
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    contacts = result.scalars().all()
    
    # Convert to response
    items = [contact_to_list_response(c) for c in contacts]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_data: ContactCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new contact.
    
    Optionally associates with an account if account_id is provided.
    """
    # Validate account if specified
    if contact_data.account_id:
        account_result = await db.execute(
            select(Account).where(
                Account.id == contact_data.account_id,
                Account.deleted_at.is_(None),
            )
        )
        if not account_result.scalar_one_or_none():
            raise NotFoundError(
                resource="Account",
                identifier=str(contact_data.account_id),
            )
    
    # Create contact
    contact_dict = contact_data.model_dump(
        exclude={"account_id", "account_role", "is_primary"},
        exclude_unset=True,
    )
    contact = Contact(
        **contact_dict,
        created_by_id=current_user.id,
    )
    
    db.add(contact)
    await db.flush()  # Get the ID
    
    # Create account association if specified
    if contact_data.account_id:
        # If this is primary, unset other primary contacts for this account
        if contact_data.is_primary:
            await db.execute(
                select(AccountContact)
                .where(
                    AccountContact.account_id == contact_data.account_id,
                    AccountContact.is_primary.is_(True),
                )
            )
            existing_primary = await db.execute(
                select(AccountContact).where(
                    AccountContact.account_id == contact_data.account_id,
                    AccountContact.is_primary.is_(True),
                )
            )
            for ac in existing_primary.scalars().all():
                ac.is_primary = False
        
        account_contact = AccountContact(
            account_id=contact_data.account_id,
            contact_id=contact.id,
            role=contact_data.account_role or ContactRole.OTHER.value,
            is_primary=contact_data.is_primary,
        )
        db.add(account_contact)
    
    await db.commit()
    await db.refresh(contact)
    
    return build_created_response(
        data=contact_to_response(contact),
        resource_name="Contact",
    )


@router.get("/{contact_id}", response_model=APIResponse)
async def get_contact(
    contact_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(False, description="Include if soft-deleted"),
):
    """
    Get contact by ID.
    """
    query = select(Contact).where(Contact.id == contact_id)
    
    if not include_deleted:
        query = query.where(Contact.deleted_at.is_(None))
    
    result = await db.execute(query)
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise NotFoundError(resource="Contact", identifier=str(contact_id))
    
    return build_response(data=contact_to_response(contact))


@router.patch("/{contact_id}", response_model=APIResponse)
async def update_contact(
    contact_id: UUID,
    contact_data: ContactUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a contact.
    """
    # Get existing contact
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise NotFoundError(resource="Contact", identifier=str(contact_id))
    
    # Update fields
    update_dict = contact_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(contact, key, value)
    
    contact.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(contact)
    
    return build_updated_response(
        data=contact_to_response(contact),
        resource_name="Contact",
    )


@router.delete("/{contact_id}", response_model=APIResponse)
async def delete_contact(
    contact_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(False, description="Permanently delete"),
):
    """
    Delete a contact (soft delete by default).
    """
    # Get existing contact
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise NotFoundError(resource="Contact", identifier=str(contact_id))
    
    if contact.deleted_at and not hard_delete:
        raise NotFoundError(resource="Contact", identifier=str(contact_id))
    
    if hard_delete:
        if not current_user.is_superuser:
            raise ForbiddenError(
                message="Only administrators can permanently delete contacts"
            )
        await db.delete(contact)
    else:
        contact.deleted_at = now_utc()
        contact.deleted_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Contact")


@router.post("/{contact_id}/restore", response_model=APIResponse)
async def restore_contact(
    contact_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Restore a soft-deleted contact.
    """
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.isnot(None),
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise NotFoundError(
            resource="Deleted Contact",
            identifier=str(contact_id),
        )
    
    contact.deleted_at = None
    contact.deleted_by_id = None
    contact.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(contact)
    
    return build_response(
        data=contact_to_response(contact),
        message="Contact restored successfully",
    )


@router.delete("", response_model=APIResponse)
async def bulk_delete_contacts(
    request: BulkDeleteRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Bulk delete multiple contacts (soft delete).
    """
    result = await db.execute(
        select(Contact).where(
            Contact.id.in_(request.ids),
            Contact.deleted_at.is_(None),
        )
    )
    contacts = result.scalars().all()
    
    if not contacts:
        raise NotFoundError(resource="Contacts", identifier="provided IDs")
    
    deleted_count = 0
    for contact in contacts:
        if request.force:
            if not current_user.is_superuser:
                raise ForbiddenError(
                    message="Only administrators can permanently delete contacts"
                )
            await db.delete(contact)
        else:
            contact.deleted_at = now_utc()
            contact.deleted_by_id = current_user.id
        deleted_count += 1
    
    await db.commit()
    
    return build_response(
        data={"deleted_count": deleted_count},
        message=f"Successfully deleted {deleted_count} contact(s)",
    )


# =============================================================================
# Account-Contact Relationship Endpoints
# =============================================================================


@router.get("/{contact_id}/accounts", response_model=APIResponse)
async def list_contact_accounts(
    contact_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    List all accounts associated with a contact.
    """
    # Verify contact exists
    contact_result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.is_(None),
        )
    )
    if not contact_result.scalar_one_or_none():
        raise NotFoundError(resource="Contact", identifier=str(contact_id))
    
    # Get account associations
    result = await db.execute(
        select(AccountContact, Account)
        .join(Account, AccountContact.account_id == Account.id)
        .where(
            AccountContact.contact_id == contact_id,
            AccountContact.is_active.is_(True),
            Account.deleted_at.is_(None),
        )
    )
    associations = result.all()
    
    accounts = []
    for ac, account in associations:
        accounts.append(AccountContactResponse(
            id=ac.id,
            account_id=account.id,
            account_name=account.name,
            contact_id=contact_id,
            role=ac.role,
            is_primary=ac.is_primary,
            is_active=ac.is_active,
            start_date=ac.start_date,
            end_date=ac.end_date,
            notes=ac.notes,
            created_at=ac.created_at,
        ))
    
    return build_response(data=accounts)


@router.post("/{contact_id}/accounts", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_contact_to_account(
    contact_id: UUID,
    request: AccountContactRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Associate a contact with an account.
    """
    # Verify contact exists
    contact_result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.is_(None),
        )
    )
    if not contact_result.scalar_one_or_none():
        raise NotFoundError(resource="Contact", identifier=str(contact_id))
    
    # Verify account exists
    account_result = await db.execute(
        select(Account).where(
            Account.id == request.account_id,
            Account.deleted_at.is_(None),
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise NotFoundError(resource="Account", identifier=str(request.account_id))
    
    # Check if association already exists
    existing = await db.execute(
        select(AccountContact).where(
            AccountContact.contact_id == contact_id,
            AccountContact.account_id == request.account_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            message="Contact is already associated with this account"
        )
    
    # If this is primary, unset other primary contacts for this account
    if request.is_primary:
        existing_primary = await db.execute(
            select(AccountContact).where(
                AccountContact.account_id == request.account_id,
                AccountContact.is_primary.is_(True),
            )
        )
        for ac in existing_primary.scalars().all():
            ac.is_primary = False
    
    # Create association
    account_contact = AccountContact(
        contact_id=contact_id,
        account_id=request.account_id,
        role=request.role,
        is_primary=request.is_primary,
        notes=request.notes,
        start_date=request.start_date or now_utc(),
    )
    
    db.add(account_contact)
    await db.commit()
    await db.refresh(account_contact)
    
    return build_created_response(
        data=AccountContactResponse(
            id=account_contact.id,
            account_id=account.id,
            account_name=account.name,
            contact_id=contact_id,
            role=account_contact.role,
            is_primary=account_contact.is_primary,
            is_active=account_contact.is_active,
            start_date=account_contact.start_date,
            end_date=account_contact.end_date,
            notes=account_contact.notes,
            created_at=account_contact.created_at,
        ),
        resource_name="Account association",
    )


@router.delete("/{contact_id}/accounts/{account_id}", response_model=APIResponse)
async def remove_contact_from_account(
    contact_id: UUID,
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Remove a contact's association with an account.
    """
    # Get association
    result = await db.execute(
        select(AccountContact).where(
            AccountContact.contact_id == contact_id,
            AccountContact.account_id == account_id,
        )
    )
    account_contact = result.scalar_one_or_none()
    
    if not account_contact:
        raise NotFoundError(
            resource="Account-Contact association",
            identifier=f"{contact_id}/{account_id}",
        )
    
    # Soft deactivate (keep history)
    account_contact.is_active = False
    account_contact.end_date = now_utc()
    
    await db.commit()
    
    return build_deleted_response(resource_name="Account association")


@router.patch("/{contact_id}/accounts/{account_id}", response_model=APIResponse)
async def update_contact_account_role(
    contact_id: UUID,
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    role: Optional[str] = Query(None, description="New role"),
    is_primary: Optional[bool] = Query(None, description="Set as primary contact"),
    notes: Optional[str] = Query(None, description="Update notes"),
):
    """
    Update a contact's role or primary status at an account.
    """
    # Get association
    result = await db.execute(
        select(AccountContact).where(
            AccountContact.contact_id == contact_id,
            AccountContact.account_id == account_id,
        )
    )
    account_contact = result.scalar_one_or_none()
    
    if not account_contact:
        raise NotFoundError(
            resource="Account-Contact association",
            identifier=f"{contact_id}/{account_id}",
        )
    
    # Validate role if provided
    if role:
        valid_roles = [r.value for r in ContactRole]
        if role not in valid_roles:
            raise ConflictError(
                message=f"Invalid role. Must be one of: {valid_roles}"
            )
        account_contact.role = role
    
    # Handle primary status
    if is_primary is not None:
        if is_primary:
            # Unset other primary contacts for this account
            existing_primary = await db.execute(
                select(AccountContact).where(
                    AccountContact.account_id == account_id,
                    AccountContact.is_primary.is_(True),
                    AccountContact.id != account_contact.id,
                )
            )
            for ac in existing_primary.scalars().all():
                ac.is_primary = False
        account_contact.is_primary = is_primary
    
    if notes is not None:
        account_contact.notes = notes
    
    await db.commit()
    await db.refresh(account_contact)
    
    # Get account for response
    account_result = await db.execute(
        select(Account).where(Account.id == account_id)
    )
    account = account_result.scalar_one()
    
    return build_updated_response(
        data=AccountContactResponse(
            id=account_contact.id,
            account_id=account.id,
            account_name=account.name,
            contact_id=contact_id,
            role=account_contact.role,
            is_primary=account_contact.is_primary,
            is_active=account_contact.is_active,
            start_date=account_contact.start_date,
            end_date=account_contact.end_date,
            notes=account_contact.notes,
            created_at=account_contact.created_at,
        ),
        resource_name="Account association",
    )

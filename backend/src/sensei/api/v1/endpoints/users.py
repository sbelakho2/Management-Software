"""
User Management Endpoints

Provides user management including:
- Get current user profile
- Update user profile
- List users (admin)
- Create/update/delete users (admin)
- 2FA management
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from sensei.api.deps import (
    CurrentUser,
    DBSession,
    Pagination,
    RoleChecker,
    get_token_data,
)
from sensei.core.security import (
    TokenData,
    generate_backup_codes,
    hash_backup_codes,
    hash_password,
    setup_totp,
    verify_password,
    verify_totp,
)
from sensei.models.user import Permission, Role, RolePermission, User, UserRole, UserStatus


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class UserBase(BaseModel):
    """Base user fields."""
    
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=100)
    locale: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class UserCreate(BaseModel):
    """User creation request."""
    
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=100)
    role_ids: list[UUID] = Field(default_factory=list)
    is_superuser: bool = False


class UserUpdate(UserBase):
    """User update request."""
    
    preferences: Optional[dict] = None


class AdminUserUpdate(UserUpdate):
    """Admin user update (includes status and roles)."""
    
    status: Optional[str] = None
    is_superuser: Optional[bool] = None
    role_ids: Optional[list[UUID]] = None


class UserResponse(BaseModel):
    """User response."""
    
    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    status: str
    is_superuser: bool
    email_verified: bool
    totp_enabled: bool
    last_login_at: Optional[datetime] = None
    locale: str
    timezone: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class UserWithRolesResponse(UserResponse):
    """User response with roles."""
    
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class UserListResponse(BaseModel):
    """Paginated user list response."""
    
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TOTPSetupResponse(BaseModel):
    """TOTP setup response."""
    
    secret: str
    provisioning_uri: str
    qr_code_base64: str


class TOTPVerifyRequest(BaseModel):
    """TOTP verification request."""
    
    code: str = Field(..., min_length=6, max_length=6)


class BackupCodesResponse(BaseModel):
    """Backup codes response."""
    
    codes: list[str]


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str
    success: bool = True


# =============================================================================
# Current User Endpoints
# =============================================================================


@router.get(
    "/me",
    response_model=UserWithRolesResponse,
)
async def get_current_user_profile(
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """Get current authenticated user's profile with roles and permissions."""
    user_id = UUID(token_data.sub)
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserWithRolesResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        phone=user.phone,
        department=user.department,
        job_title=user.job_title,
        status=user.status,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified,
        totp_enabled=user.totp_enabled,
        last_login_at=user.last_login_at,
        locale=user.locale,
        timezone=user.timezone,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=token_data.roles,
        permissions=token_data.permissions,
    )


@router.patch(
    "/me",
    response_model=UserResponse,
)
async def update_current_user_profile(
    request: UserUpdate,
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """Update current user's profile."""
    user_id = UUID(token_data.sub)
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


# =============================================================================
# 2FA Endpoints
# =============================================================================


@router.post(
    "/me/totp/setup",
    response_model=TOTPSetupResponse,
)
async def setup_2fa(
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Set up TOTP 2FA for current user.
    
    Returns secret and QR code for authenticator app.
    The user must verify with a code before 2FA is enabled.
    """
    user_id = UUID(token_data.sub)
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )
    
    # Generate TOTP setup
    totp_setup = setup_totp(user.email)
    
    # Store secret temporarily (not enabled yet)
    user.totp_secret = totp_setup.secret
    await db.commit()
    
    return TOTPSetupResponse(
        secret=totp_setup.secret,
        provisioning_uri=totp_setup.provisioning_uri,
        qr_code_base64=totp_setup.qr_code_base64,
    )


@router.post(
    "/me/totp/verify",
    response_model=BackupCodesResponse,
)
async def verify_and_enable_2fa(
    request: TOTPVerifyRequest,
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Verify TOTP code and enable 2FA.
    
    Returns backup codes that should be saved securely.
    """
    user_id = UUID(token_data.sub)
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not set up. Call /me/totp/setup first.",
        )
    
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )
    
    # Verify the code
    if not verify_totp(user.totp_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )
    
    # Generate backup codes
    backup_codes = generate_backup_codes()
    hashed_codes = hash_backup_codes(backup_codes)
    
    # Enable 2FA
    user.totp_enabled = True
    user.backup_codes = hashed_codes
    await db.commit()
    
    return BackupCodesResponse(codes=backup_codes)


@router.delete(
    "/me/totp",
    response_model=MessageResponse,
)
async def disable_2fa(
    password: str,
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Disable 2FA for current user.
    
    Requires password confirmation.
    """
    user_id = UUID(token_data.sub)
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    
    # Disable 2FA
    user.totp_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    await db.commit()
    
    return MessageResponse(message="2FA disabled successfully")


@router.post(
    "/me/totp/backup-codes",
    response_model=BackupCodesResponse,
)
async def regenerate_backup_codes(
    password: str,
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Regenerate backup codes for 2FA.
    
    Requires password confirmation. Old backup codes will be invalidated.
    """
    user_id = UUID(token_data.sub)
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    
    # Generate new backup codes
    backup_codes = generate_backup_codes()
    hashed_codes = hash_backup_codes(backup_codes)
    
    user.backup_codes = hashed_codes
    await db.commit()
    
    return BackupCodesResponse(codes=backup_codes)


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=UserListResponse,
    dependencies=[Depends(RoleChecker(["admin", "gm"]))],
)
async def list_users(
    db: DBSession,
    pagination: Pagination,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, max_length=100),
):
    """
    List all users (admin/GM only).
    
    Supports filtering by status and searching by name/email.
    """
    query = select(User).where(User.deleted_at.is_(None))
    count_query = select(func.count(User.id)).where(User.deleted_at.is_(None))
    
    if status_filter:
        query = query.where(User.status == status_filter)
        count_query = count_query.where(User.status == status_filter)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) |
            (User.first_name.ilike(search_pattern)) |
            (User.last_name.ilike(search_pattern)) |
            (User.username.ilike(search_pattern))
        )
        count_query = count_query.where(
            (User.email.ilike(search_pattern)) |
            (User.first_name.ilike(search_pattern)) |
            (User.last_name.ilike(search_pattern)) |
            (User.username.ilike(search_pattern))
        )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset(pagination.offset).limit(pagination.limit)
    query = query.order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
async def create_user(
    request: UserCreate,
    db: DBSession,
):
    """
    Create a new user (admin only).
    """
    # Check for existing email
    existing = await db.execute(
        select(User).where(User.email == request.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check for existing username
    existing = await db.execute(
        select(User).where(User.username == request.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Create user
    user = User(
        email=request.email.lower(),
        username=request.username,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        display_name=request.display_name,
        phone=request.phone,
        department=request.department,
        job_title=request.job_title,
        status=UserStatus.PENDING.value,
        is_superuser=request.is_superuser,
    )
    
    db.add(user)
    await db.flush()
    
    # Assign roles
    for role_id in request.role_ids:
        user_role = UserRole(user_id=user.id, role_id=role_id)
        db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserWithRolesResponse,
    dependencies=[Depends(RoleChecker(["admin", "gm"]))],
)
async def get_user(
    user_id: UUID,
    db: DBSession,
):
    """Get user by ID (admin/GM only)."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get roles
    roles_result = await db.execute(
        select(Role.name).join(UserRole).where(
            UserRole.user_id == user_id,
            Role.is_active == True,
        )
    )
    roles = [r[0] for r in roles_result.fetchall()]
    
    # Get permissions
    perms_result = await db.execute(
        select(Permission.resource, Permission.action).join(
            RolePermission
        ).join(Role).join(UserRole).where(
            UserRole.user_id == user_id,
            Role.is_active == True,
        ).distinct()
    )
    permissions = [f"{p[0]}:{p[1]}" for p in perms_result.fetchall()]
    
    return UserWithRolesResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        phone=user.phone,
        department=user.department,
        job_title=user.job_title,
        status=user.status,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified,
        totp_enabled=user.totp_enabled,
        last_login_at=user.last_login_at,
        locale=user.locale,
        timezone=user.timezone,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
        permissions=permissions,
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
async def update_user(
    user_id: UUID,
    request: AdminUserUpdate,
    db: DBSession,
):
    """Update user by ID (admin only)."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True, exclude={"role_ids"})
    for field, value in update_data.items():
        setattr(user, field, value)
    
    # Update roles if provided
    if request.role_ids is not None:
        from sensei.models.user import UserRole
        from sqlalchemy import delete
        
        # Remove existing roles
        await db.execute(
            delete(UserRole).where(UserRole.user_id == user_id)
        )
        
        # Add new roles
        for role_id in request.role_ids:
            user_role = UserRole(user_id=user.id, role_id=role_id)
            db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
async def delete_user(
    user_id: UUID,
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """Soft delete user by ID (admin only)."""
    # Prevent self-deletion
    if str(user_id) == token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Soft delete
    from datetime import datetime, timezone
    user.deleted_at = datetime.now(timezone.utc)
    user.status = UserStatus.INACTIVE.value
    
    await db.commit()

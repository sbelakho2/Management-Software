"""
Sensei OS API Dependencies

FastAPI dependencies for:
- Database session management
- Authentication and authorization
- Rate limiting
- Request validation
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.config import settings
from sensei.core.database import async_session_factory
from sensei.core.redis import redis_client
from sensei.core.security import TokenData, decode_token, get_rate_limit_key


# =============================================================================
# Database Session Dependency
# =============================================================================


async def get_db() -> AsyncSession:
    """
    Get database session dependency.
    
    Yields an async database session and ensures proper cleanup.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Type alias for database dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Authentication Dependencies
# =============================================================================


# HTTP Bearer scheme for JWT tokens
bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_data(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> TokenData:
    """
    Extract and validate token data from Authorization header.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        TokenData from the validated token
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token_data = decode_token(credentials.credentials, "access")
        
        # Check if token is revoked
        revoked_key = f"revoked_token:{token_data.jti}"
        if await redis_client.exists(revoked_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token_data
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_token_data(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> Optional[TokenData]:
    """
    Optionally extract token data - returns None if no token provided.
    
    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        token_data = decode_token(credentials.credentials, "access")
        
        revoked_key = f"revoked_token:{token_data.jti}"
        if await redis_client.exists(revoked_key):
            return None
        
        return token_data
    except JWTError:
        return None


async def get_current_user(
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Get current authenticated user from database.
    
    Args:
        db: Database session
        token_data: Validated token data
        
    Returns:
        User model instance
        
    Raises:
        HTTPException: 401 if user not found or inactive
    """
    from sensei.models.user import User, UserStatus
    
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User account is {user.status}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    user = Depends(get_current_user),
):
    """
    Get current active user (alias for get_current_user).
    
    Use this when you want to emphasize that the user must be active.
    """
    return user


async def get_current_superuser(
    user = Depends(get_current_user),
):
    """
    Get current user and verify they are a superuser.
    
    Raises:
        HTTPException: 403 if user is not a superuser
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return user


# Type aliases for common dependencies
CurrentUser = Annotated[object, Depends(get_current_user)]
CurrentActiveUser = Annotated[object, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[object, Depends(get_current_superuser)]


# =============================================================================
# Permission Checking Dependencies
# =============================================================================


class PermissionChecker:
    """
    Dependency class for checking user permissions.
    
    Usage:
        @router.get("/resource")
        async def get_resource(
            _: Annotated[bool, Depends(PermissionChecker("resource:read"))],
            user: CurrentUser,
        ):
            ...
    """
    
    def __init__(self, required_permission: str):
        """
        Initialize permission checker.
        
        Args:
            required_permission: Permission string in format "resource:action"
        """
        self.required_permission = required_permission
    
    async def __call__(
        self,
        token_data: Annotated[TokenData, Depends(get_token_data)],
    ) -> bool:
        """Check if user has required permission."""
        # Superusers have all permissions
        if "admin" in token_data.roles:
            return True
        
        if self.required_permission not in token_data.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.required_permission} required",
            )
        
        return True


class RoleChecker:
    """
    Dependency class for checking user roles.
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            _: Annotated[bool, Depends(RoleChecker(["admin", "gm"]))],
            user: CurrentUser,
        ):
            ...
    """
    
    def __init__(self, required_roles: list[str]):
        """
        Initialize role checker.
        
        Args:
            required_roles: List of allowed roles (any match grants access)
        """
        self.required_roles = required_roles
    
    async def __call__(
        self,
        token_data: Annotated[TokenData, Depends(get_token_data)],
    ) -> bool:
        """Check if user has any of the required roles."""
        if not any(role in token_data.roles for role in self.required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires one of {self.required_roles}",
            )
        
        return True


def require_permission(permission: str):
    """
    Decorator-style permission requirement.
    
    Usage:
        RequireRead = require_permission("resource:read")
        
        @router.get("/resource")
        async def get_resource(
            _: RequireRead,
            user: CurrentUser,
        ):
            ...
    """
    return Annotated[bool, Depends(PermissionChecker(permission))]


def require_role(*roles: str):
    """
    Decorator-style role requirement.
    
    Usage:
        RequireAdmin = require_role("admin", "gm")
        
        @router.get("/admin")
        async def admin_endpoint(
            _: RequireAdmin,
            user: CurrentUser,
        ):
            ...
    """
    return Annotated[bool, Depends(RoleChecker(list(roles)))]


# =============================================================================
# Rate Limiting Dependencies
# =============================================================================


class RateLimiter:
    """
    Rate limiting dependency.
    
    Usage:
        @router.post("/login")
        async def login(
            _: Annotated[bool, Depends(RateLimiter(requests=5, window=60))],
        ):
            ...
    """
    
    def __init__(
        self,
        requests: int = None,
        window: int = None,
        key_prefix: str = "api",
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests: Maximum requests allowed (default from settings)
            window: Time window in seconds (default from settings)
            key_prefix: Prefix for Redis key
        """
        self.requests = requests or settings.RATE_LIMIT_REQUESTS
        self.window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        self.key_prefix = key_prefix
    
    async def __call__(
        self,
        request: Request,
        token_data: Annotated[Optional[TokenData], Depends(get_optional_token_data)] = None,
    ) -> bool:
        """Check rate limit for request."""
        # Use user ID if authenticated, otherwise use IP
        if token_data:
            identifier = token_data.sub
        else:
            identifier = request.client.host if request.client else "unknown"
        
        key = get_rate_limit_key(identifier, self.key_prefix)
        
        # Increment counter
        count = await redis_client.incr(key)
        
        # Set expiry on first request
        if count == 1:
            await redis_client.expire(key, self.window)
        
        # Check limit
        if count > self.requests:
            ttl = await redis_client.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)},
            )
        
        return True


# Common rate limiter instances
StandardRateLimit = Annotated[bool, Depends(RateLimiter())]
StrictRateLimit = Annotated[bool, Depends(RateLimiter(requests=10, window=60))]
AuthRateLimit = Annotated[bool, Depends(RateLimiter(requests=5, window=60, key_prefix="auth"))]


# =============================================================================
# Pagination Dependencies
# =============================================================================


class PaginationParams:
    """Pagination parameters for list endpoints."""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
    ):
        """
        Initialize pagination parameters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page (max 100)
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100
        
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size


Pagination = Annotated[PaginationParams, Depends()]


# =============================================================================
# Request Context Dependencies
# =============================================================================


async def get_correlation_id(
    x_correlation_id: Annotated[Optional[str], Header()] = None,
) -> str:
    """Get or generate correlation ID for request tracing."""
    import uuid
    return x_correlation_id or str(uuid.uuid4())


CorrelationId = Annotated[str, Depends(get_correlation_id)]

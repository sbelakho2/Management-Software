"""
Sensei OS API Package

Provides the core API framework including:
- Schemas for request/response models
- Exception handling
- Repository pattern for CRUD operations
- API utilities
"""

from sensei.api.schemas import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    ErrorResponse,
    ValidationErrorResponse,
    success_response,
    error_response,
    paginated_response,
)

from sensei.api.exceptions import (
    SenseiException,
    NotFoundError,
    ConflictError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    UnprocessableEntityError,
    RateLimitError,
    ServiceUnavailableError,
    BusinessRuleViolationError,
    StateTransitionError,
    ApprovalRequiredError,
    register_exception_handlers,
)

from sensei.api.repository import BaseRepository

from sensei.api.deps import (
    DBSession,
    CurrentUser,
    CurrentActiveUser,
    CurrentSuperuser,
    Pagination,
    StandardRateLimit,
    StrictRateLimit,
    AuthRateLimit,
    PermissionChecker,
    RoleChecker,
    require_permission,
    require_role,
)

__all__ = [
    # Schemas
    "APIResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "ErrorResponse",
    "ValidationErrorResponse",
    "success_response",
    "error_response",
    "paginated_response",
    # Exceptions
    "SenseiException",
    "NotFoundError",
    "ConflictError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "UnprocessableEntityError",
    "RateLimitError",
    "ServiceUnavailableError",
    "BusinessRuleViolationError",
    "StateTransitionError",
    "ApprovalRequiredError",
    "register_exception_handlers",
    # Repository
    "BaseRepository",
    # Dependencies
    "DBSession",
    "CurrentUser",
    "CurrentActiveUser",
    "CurrentSuperuser",
    "Pagination",
    "StandardRateLimit",
    "StrictRateLimit",
    "AuthRateLimit",
    "PermissionChecker",
    "RoleChecker",
    "require_permission",
    "require_role",
]

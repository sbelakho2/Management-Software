"""
Sensei OS Exception Handlers

Global exception handlers for the FastAPI application.
Provides consistent error responses across all endpoints.
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from sensei.api.schemas import ErrorResponse, ValidationErrorDetail, ValidationErrorResponse

logger = structlog.get_logger(__name__)

# Pre-compiled regex for SQL sanitization (#147)
import re
_SQL_STATEMENT_RE = re.compile(
    r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|FROM|WHERE|VALUES|SET)\b.*',
    re.IGNORECASE | re.DOTALL,
)


def _sanitize_sql_error(error_str: str) -> str:
    """
    Remove raw SQL statements from error messages to prevent
    leaking schema details and query structure in logs (#147).
    
    Keeps the constraint/error type but strips the SQL body.
    """
    # Strip SQL statements, keeping only the constraint message
    sanitized = _SQL_STATEMENT_RE.sub('[SQL REDACTED]', error_str)
    # Cap length to prevent very large error strings in logs
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + '...[truncated]'
    return sanitized


# =============================================================================
# Custom Exceptions
# =============================================================================


class SenseiException(Exception):
    """Base exception for all Sensei OS errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class NotFoundError(SenseiException):
    """Resource not found error."""
    
    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with ID '{identifier}' not found"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details,
        )


class ConflictError(SenseiException):
    """Resource conflict error (duplicate, state conflict, etc.)."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class BadRequestError(SenseiException):
    """Bad request error."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            details=details,
        )


class UnauthorizedError(SenseiException):
    """Unauthorized access error."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenError(SenseiException):
    """Forbidden access error."""
    
    def __init__(
        self,
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if required_permission:
            message = f"Access denied: {required_permission} permission required"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            details=details,
        )


class UnprocessableEntityError(SenseiException):
    """Unprocessable entity error for business logic violations."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="UNPROCESSABLE_ENTITY",
            details=details,
        )


class RateLimitError(SenseiException):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        retry_after: int = 60,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after, **(details or {})},
        )
        self.retry_after = retry_after


class ServiceUnavailableError(SenseiException):
    """Service unavailable error."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
        )


class BusinessRuleViolationError(SenseiException):
    """Business rule violation error."""
    
    def __init__(
        self,
        rule: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=f"BUSINESS_RULE_VIOLATION:{rule}",
            details=details,
        )


class StateTransitionError(SenseiException):
    """Invalid state transition error."""
    
    def __init__(
        self,
        from_state: str,
        to_state: str,
        entity_type: str,
        allowed_transitions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Cannot transition {entity_type} from '{from_state}' to '{to_state}'"
        if allowed_transitions:
            message += f". Allowed transitions: {', '.join(allowed_transitions)}"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="INVALID_STATE_TRANSITION",
            details={
                "from_state": from_state,
                "to_state": to_state,
                "entity_type": entity_type,
                "allowed_transitions": allowed_transitions,
                **(details or {}),
            },
        )


class ApprovalRequiredError(SenseiException):
    """Approval required error."""
    
    def __init__(
        self,
        action: str,
        approvers: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Approval required for action: {action}"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="APPROVAL_REQUIRED",
            details={
                "action": action,
                "approvers": approvers,
                **(details or {}),
            },
        )


class FileOperationError(SenseiException):
    """File operation error."""
    
    def __init__(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"File {operation} failed: {message}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=f"FILE_OPERATION_FAILED:{operation.upper()}",
            details=details,
        )


class ExternalServiceError(SenseiException):
    """External service error."""
    
    def __init__(
        self,
        service: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"External service error ({service}): {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=f"EXTERNAL_SERVICE_ERROR:{service.upper()}",
            details=details,
        )


# =============================================================================
# Exception Handlers
# =============================================================================


async def sensei_exception_handler(
    request: Request,
    exc: SenseiException,
) -> JSONResponse:
    """Handle custom Sensei exceptions."""
    logger.warning(
        "Application error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=str(request.url.path),
        method=request.method,
    )
    
    headers = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        ).model_dump(),
        headers=headers or None,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url.path),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=str(exc.detail) if exc.detail else "HTTP Error",
            error_code=f"HTTP_{exc.status_code}",
        ).model_dump(),
        headers=exc.headers if hasattr(exc, "headers") else None,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle request validation errors."""
    errors = []
    
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        if not field_path:
            field_path = str(error["loc"][-1]) if error["loc"] else "unknown"
        
        errors.append(
            ValidationErrorDetail(
                field=field_path,
                message=error["msg"],
                type=error["type"],
            )
        )
    
    logger.warning(
        "Validation error",
        error_count=len(errors),
        path=str(request.url.path),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ValidationErrorResponse(
            message="Validation error",
            errors=errors,
        ).model_dump(),
    )


async def pydantic_validation_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors (for internal validation)."""
    errors = []
    
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        errors.append(
            ValidationErrorDetail(
                field=field_path,
                message=error["msg"],
                type=error["type"],
            )
        )
    
    logger.warning(
        "Pydantic validation error",
        error_count=len(errors),
        path=str(request.url.path),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ValidationErrorResponse(
            message="Validation error",
            errors=errors,
        ).model_dump(),
    )


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """Handle database integrity errors."""
    # Sanitize SQL from logged error to prevent leaking schema details (#147)
    raw_error = str(exc.orig)
    # Only log the constraint type, not the full SQL statement
    sanitized_error = _sanitize_sql_error(raw_error)
    logger.warning(
        "Database integrity error",
        error=sanitized_error,
        path=str(request.url.path),
        method=request.method,
    )
    
    # Parse common integrity errors
    error_str = str(exc.orig).lower()
    
    if "duplicate" in error_str or "unique" in error_str:
        message = "A record with this value already exists"
        error_code = "DUPLICATE_ENTRY"
    elif "foreign key" in error_str:
        message = "Referenced record does not exist or cannot be deleted"
        error_code = "FOREIGN_KEY_VIOLATION"
    elif "not null" in error_str:
        message = "Required field is missing"
        error_code = "NOT_NULL_VIOLATION"
    else:
        message = "Database constraint violation"
        error_code = "INTEGRITY_ERROR"
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            message=message,
            error_code=error_code,
        ).model_dump(),
    )


async def sqlalchemy_error_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """Handle SQLAlchemy errors."""
    # Sanitize SQL from logged error to prevent leaking schema/query details (#147)
    sanitized_error = _sanitize_sql_error(str(exc))
    logger.error(
        "Database error",
        error=sanitized_error,
        path=str(request.url.path),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="Database error occurred",
            error_code="DATABASE_ERROR",
        ).model_dump(),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=str(request.url.path),
        method=request.method,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
        ).model_dump(),
    )


# =============================================================================
# Register Exception Handlers
# =============================================================================


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    
    # Custom exceptions
    app.add_exception_handler(SenseiException, sensei_exception_handler)  # type: ignore[arg-type]
    
    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    
    # Validation exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, pydantic_validation_handler)  # type: ignore[arg-type]
    
    # Database exceptions
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)  # type: ignore[arg-type]
    
    # Generic fallback
    app.add_exception_handler(Exception, generic_exception_handler)

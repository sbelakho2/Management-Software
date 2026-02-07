"""
Sensei OS API Utilities

Common utilities for API endpoints including:
- Response builders
- Query parameter parsing
- File handling
- Data transformation
- Security utilities
"""

from datetime import datetime, timezone
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from uuid import UUID

from fastapi import Query, UploadFile
from pydantic import BaseModel
from starlette.requests import Request

from sensei.api.schemas import (
    APIResponse,
    FilterOperator,
    PaginatedResponse,
    PaginationMeta,
    SortOrder,
)
from sensei.core.config import settings

T = TypeVar("T")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


async def maybe_await(value: Any) -> Any:
    """Await the value if it is awaitable, otherwise return it as-is."""
    if inspect.isawaitable(value):
        return await value
    return value


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address from a request, handling
    reverse-proxy headers in priority order (#247).

    Checks X-Forwarded-For first (first entry = original client),
    then X-Real-IP, then falls back to request.client.host.

    This is the single canonical implementation — all middleware and
    dependencies should import this instead of rolling their own.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


# =============================================================================
# Security Utilities
# =============================================================================


def escape_like_pattern(value: str) -> str:
    """
    Escape special characters in LIKE/ILIKE patterns to prevent SQL injection.
    
    PostgreSQL LIKE patterns treat '%', '_', and '\\' as special characters.
    This function escapes them so they are treated literally.
    
    Args:
        value: The search string to escape
        
    Returns:
        Escaped string safe for use in LIKE/ILIKE patterns
        
    Example:
        >>> escape_like_pattern("test%value")
        'test\\%value'
        >>> escape_like_pattern("user_name")
        'user\\_name'
    """
    if not value:
        return value
    # Escape backslash first (since it's the escape character)
    value = value.replace("\\", "\\\\")
    # Escape percent sign
    value = value.replace("%", "\\%")
    # Escape underscore
    value = value.replace("_", "\\_")
    return value


# =============================================================================
# Query Parameter Utilities
# =============================================================================


def parse_sort_param(
    sort: Optional[str] = Query(
        None,
        description="Sort field and direction (e.g., 'created_at:desc' or 'name:asc,updated_at:desc')",
    ),
) -> List[SortOrder]:
    """
    Parse sort query parameter into list of SortOrder objects.
    
    Format: field:direction,field:direction
    Example: "created_at:desc,name:asc"
    """
    if not sort:
        return []
    
    result = []
    
    for part in sort.split(","):
        part = part.strip()
        if ":" in part:
            field, direction = part.split(":", 1)
            direction = direction.lower()
            if direction not in ("asc", "desc"):
                direction = "asc"
        else:
            field = part
            direction = "asc"
        
        result.append(SortOrder(field=field, direction=direction))
    
    return result


def parse_filter_param(
    filter_param: Optional[str] = Query(
        None,
        alias="filter",
        description="Filter expression (e.g., 'status:eq:active,priority:gte:5')",
    ),
) -> List[FilterOperator]:
    """
    Parse filter query parameter into list of FilterOperator objects.
    
    Format: field:operator:value,field:operator:value
    Example: "status:eq:active,created_at:gte:2024-01-01"
    """
    if not filter_param:
        return []
    
    result = []
    
    for part in filter_param.split(","):
        part = part.strip()
        parts = part.split(":", 2)
        
        if len(parts) >= 3:
            field, operator, value = parts[0], parts[1], parts[2]
            
            # Parse value types
            parsed_value = _parse_filter_value(value)
            
            result.append(FilterOperator(
                field=field,
                operator=operator.lower(),
                value=parsed_value,
            ))
        elif len(parts) == 2:
            # Assume eq operator
            field, value = parts[0], parts[1]
            result.append(FilterOperator(
                field=field,
                operator="eq",
                value=_parse_filter_value(value),
            ))
    
    return result


def _parse_filter_value(value: str) -> Any:
    """Parse filter value to appropriate type."""
    # Check for list values (pipe-separated)
    if "|" in value:
        return [_parse_single_value(v) for v in value.split("|")]
    
    return _parse_single_value(value)


def _parse_single_value(value: str) -> Any:
    """Parse a single value to appropriate type.
    
    Conservative coercion: only converts when format is unambiguous.
    Callers that need explicit types should use schema validation instead.
    """
    # Boolean
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    
    # None/null
    if value.lower() in ("null", "none"):
        return None
    
    # UUID — only if it matches the canonical 8-4-4-4-12 hex format
    try:
        return UUID(value)
    except ValueError:
        pass
    
    # ISO datetime — only if value contains 'T' (strict ISO 8601)
    if "T" in value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    # Integer — only if the ENTIRE string is digits (with optional leading minus)
    # This avoids coercing part numbers like "00123" or zip codes.
    stripped = value.lstrip("-")
    if stripped.isdigit() and not value.startswith("0") or value in ("0", "-0"):
        try:
            return int(value)
        except ValueError:
            pass
    
    # Skip float coercion — too many false positives (version strings, IPs, etc.)
    # Callers should use typed schema validation for numeric fields.
    
    # String (default)
    return value


# =============================================================================
# Response Builders
# =============================================================================


def build_response(
    data: Any = None,
    message: Optional[str] = None,
    success: bool = True,
) -> APIResponse:
    """Build a standard API response."""
    return APIResponse(
        success=success,
        message=message,
        data=data,
    )


def build_paginated_response(
    data: List[Any],
    page: int,
    page_size: int,
    total: int,
    message: Optional[str] = None,
) -> PaginatedResponse:
    """Build a paginated API response."""
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        pagination=PaginationMeta.from_pagination(
            page=page,
            page_size=page_size,
            total_items=total,
        ),
    )


def build_created_response(
    data: Any,
    resource_name: str = "Resource",
) -> APIResponse:
    """Build a response for resource creation."""
    return APIResponse(
        success=True,
        message=f"{resource_name} created successfully",
        data=data,
    )


def build_updated_response(
    data: Any,
    resource_name: str = "Resource",
) -> APIResponse:
    """Build a response for resource update."""
    return APIResponse(
        success=True,
        message=f"{resource_name} updated successfully",
        data=data,
    )


def build_deleted_response(
    resource_name: str = "Resource",
) -> APIResponse:
    """Build a response for resource deletion."""
    return APIResponse(
        success=True,
        message=f"{resource_name} deleted successfully",
        data=None,
    )


# =============================================================================
# Data Transformation Utilities
# =============================================================================


# Fields that must NEVER appear in API responses, regardless of caller exclude/include.
_SENSITIVE_FIELDS = frozenset({
    "password_hash", "hashed_password", "password",
    "totp_secret", "totp_seed", "mfa_secret",
    "api_key", "api_secret", "secret_key",
    "refresh_token", "access_token",
})


def model_to_dict(
    model: Any,
    exclude: Optional[List[str]] = None,
    include: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model to dictionary.
    
    Args:
        model: SQLAlchemy model instance
        exclude: Fields to exclude
        include: Fields to include (if None, all fields)
        
    Returns:
        Dictionary representation
    """
    exclude_set = _SENSITIVE_FIELDS | set(exclude or [])
    result = {}
    
    for column in model.__table__.columns:
        key = column.name
        
        if key in exclude_set:
            continue
        
        if include and key not in include:
            continue
        
        value = getattr(model, key)
        
        # Handle special types
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        
        result[key] = value
    
    return result


def models_to_dicts(
    models: List[Any],
    exclude: Optional[List[str]] = None,
    include: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Convert multiple SQLAlchemy models to dictionaries."""
    return [model_to_dict(m, exclude=exclude, include=include) for m in models]


def to_schema(
    model: Any,
    schema: Type[SchemaT],
) -> SchemaT:
    """
    Convert a SQLAlchemy model to a Pydantic schema.
    
    Args:
        model: SQLAlchemy model instance
        schema: Pydantic schema class
        
    Returns:
        Pydantic schema instance
    """
    return schema.model_validate(model)


def to_schemas(
    models: List[Any],
    schema: Type[SchemaT],
) -> List[SchemaT]:
    """Convert multiple SQLAlchemy models to Pydantic schemas."""
    return [schema.model_validate(m) for m in models]


def apply_partial_update(
    model: Any,
    update_data: Dict[str, Any],
    exclude_unset: bool = True,
) -> None:
    """
    Apply partial update to a model.
    
    Args:
        model: SQLAlchemy model instance
        update_data: Dictionary with update values
        exclude_unset: Skip None values
    """
    for key, value in update_data.items():
        if exclude_unset and value is None:
            continue
        if hasattr(model, key):
            setattr(model, key, value)


# =============================================================================
# File Handling Utilities
# =============================================================================


def validate_file_extension(
    filename: str,
    allowed_extensions: Optional[List[str]] = None,
) -> bool:
    """
    Validate file extension against allowed list.
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (default from settings)
        
    Returns:
        True if valid, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = settings.ALLOWED_UPLOAD_EXTENSIONS
    
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    return ext in [e.lower() for e in allowed_extensions]


def validate_file_size(
    file: UploadFile,
    max_size_mb: Optional[int] = None,
) -> bool:
    """
    Validate file size against maximum.
    
    Args:
        file: Uploaded file
        max_size_mb: Maximum size in MB (default from settings)
        
    Returns:
        True if valid, False otherwise
    """
    if max_size_mb is None:
        max_size_mb = settings.MAX_UPLOAD_SIZE_MB
    
    # Read file size (seek to end)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    max_bytes = max_size_mb * 1024 * 1024
    
    return size <= max_bytes


def generate_unique_filename(
    original_filename: str,
    prefix: Optional[str] = None,
) -> str:
    """
    Generate a unique filename.
    
    Args:
        original_filename: Original filename
        prefix: Optional prefix for the filename
        
    Returns:
        Unique filename
    """
    import uuid
    
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}.{ext}"
    
    return f"{timestamp}_{unique_id}.{ext}"


def get_content_type(filename: str) -> str:
    """
    Get content type from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        MIME content type
    """
    import mimetypes
    
    content_type, _ = mimetypes.guess_type(filename)
    
    return content_type or "application/octet-stream"


# =============================================================================
# Validation Utilities
# =============================================================================


def validate_uuid(value: str) -> Optional[UUID]:
    """
    Validate and parse UUID string.
    
    Args:
        value: String to validate
        
    Returns:
        UUID if valid, None otherwise
    """
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


def validate_uuids(values: List[str]) -> List[UUID]:
    """
    Validate and parse list of UUID strings.
    
    Args:
        values: List of strings to validate
        
    Returns:
        List of valid UUIDs (invalid ones are skipped)
    """
    result = []
    for value in values:
        uuid = validate_uuid(value)
        if uuid:
            result.append(uuid)
    return result


def is_valid_email(email: str) -> bool:
    """
    Basic email validation.
    
    Args:
        email: Email string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    import re
    
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    return bool(re.match(pattern, email))


# =============================================================================
# Date/Time Utilities
# =============================================================================


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def parse_datetime(value: str) -> Optional[datetime]:
    """
    Parse datetime from ISO format string.
    
    Args:
        value: ISO format datetime string
        
    Returns:
        Datetime if valid, None otherwise
    """
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def format_datetime(dt: datetime, format: str = "iso") -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime to format
        format: Format type ('iso', 'date', 'datetime')
        
    Returns:
        Formatted string
    """
    if format == "iso":
        return dt.isoformat()
    elif format == "date":
        return dt.strftime("%Y-%m-%d")
    elif format == "datetime":
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return dt.isoformat()


# =============================================================================
# Slug and URL Utilities
# =============================================================================


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.
    
    Args:
        text: Text to slugify
        
    Returns:
        URL-safe slug
    """
    import re
    import unicodedata
    
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace non-alphanumeric with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    
    # Remove leading/trailing hyphens
    text = text.strip("-")
    
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    
    return text


def generate_unique_code(
    prefix: str = "",
    length: int = 8,
) -> str:
    """
    Generate a unique code.
    
    Args:
        prefix: Code prefix
        length: Length of random part
        
    Returns:
        Unique code string
    """
    import secrets
    import string
    
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(length))
    
    if prefix:
        return f"{prefix}-{random_part}"
    
    return random_part


# =============================================================================
# Batch Processing Utilities
# =============================================================================


def chunk_list(
    items: List[T],
    chunk_size: int,
) -> List[List[T]]:
    """
    Split a list into chunks.
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


async def process_in_batches(
    items: List[T],
    processor: Callable[[List[T]], Any],
    batch_size: int = 100,
) -> List[Any]:
    """
    Process items in batches.
    
    Args:
        items: Items to process
        processor: Async function to process each batch
        batch_size: Size of each batch
        
    Returns:
        List of results from each batch
    """
    results = []
    
    for chunk in chunk_list(items, batch_size):
        result = await processor(chunk)
        results.append(result)
    
    return results


# =============================================================================
# Cache Key Utilities
# =============================================================================


def build_cache_key(
    prefix: str,
    *args,
    **kwargs,
) -> str:
    """
    Build a cache key from arguments.
    
    Args:
        prefix: Key prefix
        *args: Positional arguments to include
        **kwargs: Keyword arguments to include
        
    Returns:
        Cache key string
    """
    parts = [prefix]
    
    for arg in args:
        parts.append(str(arg))
    
    for key, value in sorted(kwargs.items()):
        parts.append(f"{key}={value}")
    
    return ":".join(parts)

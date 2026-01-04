"""
Sensei OS API Schemas

Common Pydantic models for API requests and responses.
Provides standardized response formats across all endpoints.
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Generic Type Variables
# =============================================================================

T = TypeVar("T")
DataT = TypeVar("DataT", bound=BaseModel)


# =============================================================================
# Base Response Models
# =============================================================================


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    
    All API responses should use this format for consistency.
    """
    
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated API response wrapper.
    
    Used for list endpoints that return multiple items.
    """
    
    success: bool = True
    message: Optional[str] = None
    data: List[T] = Field(default_factory=list)
    pagination: "PaginationMeta"
    
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")
    
    @classmethod
    def from_pagination(
        cls,
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginationMeta":
        """Create pagination metadata from parameters."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    success: bool = False
    message: str
    errors: Optional[List[str]] = None
    error_code: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class ValidationErrorDetail(BaseModel):
    """Validation error detail for individual field."""
    
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Validation error response with field-level details."""
    
    success: bool = False
    message: str = "Validation error"
    errors: List[ValidationErrorDetail]


# =============================================================================
# Common Request Models
# =============================================================================


class IDRequest(BaseModel):
    """Request with single ID."""
    
    id: UUID


class IDsRequest(BaseModel):
    """Request with multiple IDs."""
    
    ids: List[UUID]


class BulkDeleteRequest(BaseModel):
    """Bulk delete request."""
    
    ids: List[UUID] = Field(..., min_length=1, max_length=100)
    force: bool = Field(
        default=False,
        description="Force delete without soft delete",
    )


class SortOrder(BaseModel):
    """Sort order specification."""
    
    field: str
    direction: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort direction: asc or desc",
    )


class SearchRequest(BaseModel):
    """Full-text search request."""
    
    query: str = Field(..., min_length=1, max_length=500)
    fields: Optional[List[str]] = Field(
        default=None,
        description="Fields to search in (default: all searchable fields)",
    )


class FilterOperator(BaseModel):
    """Filter operator for advanced filtering."""
    
    field: str
    operator: str = Field(
        default="eq",
        description="Filter operator: eq, ne, gt, gte, lt, lte, like, ilike, in, notin, isnull, isnotnull",
    )
    value: Any


class FilterRequest(BaseModel):
    """Advanced filter request."""
    
    filters: List[FilterOperator] = Field(default_factory=list)
    search: Optional[str] = None
    sort: Optional[List[SortOrder]] = None


# =============================================================================
# Audit and Metadata Models
# =============================================================================


class AuditInfo(BaseModel):
    """Audit information for an entity."""
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)


class EntityMeta(BaseModel):
    """Common entity metadata."""
    
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Status and State Models
# =============================================================================


class StatusUpdateRequest(BaseModel):
    """Request to update entity status."""
    
    status: str
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for status change",
    )


class ArchiveRequest(BaseModel):
    """Request to archive/unarchive entity."""
    
    archived: bool
    reason: Optional[str] = None


# =============================================================================
# File and Attachment Models
# =============================================================================


class AttachmentInfo(BaseModel):
    """Attachment information."""
    
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by: Optional[UUID] = None
    url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AttachmentUploadResponse(BaseModel):
    """Response for file upload."""
    
    success: bool = True
    attachment: AttachmentInfo


# =============================================================================
# Health and Status Models
# =============================================================================


class HealthStatus(BaseModel):
    """System health status."""
    
    status: str = Field(description="Overall status: healthy, degraded, unhealthy")
    version: str
    environment: str
    services: dict[str, bool] = Field(
        default_factory=dict,
        description="Status of dependent services",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceStatus(BaseModel):
    """Individual service status."""
    
    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    message: Optional[str] = None


# =============================================================================
# Permission and Access Models
# =============================================================================


class PermissionInfo(BaseModel):
    """Permission information for current user on entity."""
    
    can_view: bool = True
    can_edit: bool = False
    can_delete: bool = False
    can_approve: bool = False
    can_export: bool = False


class AccessControlResponse(BaseModel):
    """Access control check response."""
    
    allowed: bool
    reason: Optional[str] = None
    required_permissions: Optional[List[str]] = None


# =============================================================================
# Bulk Operation Models
# =============================================================================


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    
    success: bool = True
    total: int
    succeeded: int
    failed: int
    errors: Optional[List[dict[str, Any]]] = None


class BulkUpdateRequest(BaseModel, Generic[T]):
    """Bulk update request."""
    
    ids: List[UUID] = Field(..., min_length=1, max_length=100)
    update: T


# =============================================================================
# Export Models
# =============================================================================


class ExportRequest(BaseModel):
    """Export request configuration."""
    
    format: str = Field(
        default="csv",
        pattern="^(csv|xlsx|pdf|json)$",
        description="Export format",
    )
    fields: Optional[List[str]] = Field(
        default=None,
        description="Fields to include (default: all)",
    )
    filters: Optional[FilterRequest] = None
    filename: Optional[str] = None


class ExportResponse(BaseModel):
    """Export response."""
    
    success: bool = True
    download_url: str
    filename: str
    format: str
    record_count: int
    expires_at: datetime


# =============================================================================
# Import Models
# =============================================================================


class ImportResult(BaseModel):
    """Result of an import operation."""
    
    success: bool = True
    total_rows: int
    imported: int
    skipped: int
    failed: int
    errors: Optional[List[dict[str, Any]]] = None


class ImportPreviewRow(BaseModel):
    """Preview row for import validation."""
    
    row_number: int
    data: dict[str, Any]
    valid: bool
    errors: Optional[List[str]] = None


class ImportPreviewResponse(BaseModel):
    """Import preview response."""
    
    success: bool = True
    total_rows: int
    valid_rows: int
    invalid_rows: int
    preview: List[ImportPreviewRow] = Field(max_length=10)
    column_mapping: dict[str, str]


# =============================================================================
# Webhook Models
# =============================================================================


class WebhookEvent(BaseModel):
    """Webhook event payload."""
    
    event_type: str
    timestamp: datetime
    object_type: str
    object_id: UUID
    action: str
    actor_id: Optional[UUID] = None
    data: Optional[dict[str, Any]] = None
    previous_data: Optional[dict[str, Any]] = None


# =============================================================================
# Helper Functions
# =============================================================================


def success_response(
    data: Any = None,
    message: Optional[str] = None,
) -> APIResponse:
    """Create a success response."""
    return APIResponse(
        success=True,
        message=message,
        data=data,
    )


def error_response(
    message: str,
    errors: Optional[List[str]] = None,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> ErrorResponse:
    """Create an error response."""
    return ErrorResponse(
        success=False,
        message=message,
        errors=errors,
        error_code=error_code,
        details=details,
    )


def paginated_response(
    data: List[Any],
    page: int,
    page_size: int,
    total_items: int,
    message: Optional[str] = None,
) -> PaginatedResponse:
    """Create a paginated response."""
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        pagination=PaginationMeta.from_pagination(
            page=page,
            page_size=page_size,
            total_items=total_items,
        ),
    )

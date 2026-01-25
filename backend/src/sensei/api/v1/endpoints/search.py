"""
Full-Text Search API endpoints.

Provides REST API for searching across entities, quick navigation,
and autocomplete suggestions.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.api.deps import CurrentActiveUser, CurrentSuperuser
from sensei.core.config import settings
from sensei.services.core.search import (
    FullTextSearchService,
    SearchableEntityType,
    SearchSortField,
    SearchSortOrder,
    SearchFilter,
    SearchableDocument,
    index_account,
    index_rfq,
    index_quote,
    index_task,
    index_a3,
    index_ctq,
)

router = APIRouter(prefix="/search", tags=["Search"])


def _deny_production_indexing() -> None:
    """Prevent mutation of the in-memory search index in production."""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")

# --------------------------------------------------------------------------
# Service Instance (in production, would be dependency injected)
# --------------------------------------------------------------------------

_service = FullTextSearchService()


def get_service() -> FullTextSearchService:
    """Get the search service."""
    return _service


# --------------------------------------------------------------------------
# Request/Response Schemas
# --------------------------------------------------------------------------

class SearchResultResponse(BaseModel):
    """A single search result."""
    
    entity_type: str
    entity_id: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    status: str | None = None
    relevance_score: float = 0.0
    matched_fields: list[str] = []
    highlights: dict[str, str] = {}
    url: str | None = None
    icon: str | None = None
    extra_data: dict[str, Any] = {}


class SearchResultSetResponse(BaseModel):
    """Search result set with metadata."""
    
    results: list[SearchResultResponse]
    query: str
    total_count: int = 0
    entity_counts: dict[str, int] = {}
    search_time_ms: float = 0.0
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class QuickSearchResultResponse(BaseModel):
    """Quick search results for navigation."""
    
    results: list[SearchResultResponse]
    query: str


class SuggestionsResponse(BaseModel):
    """Autocomplete suggestions."""
    
    prefix: str
    suggestions: list[str]


class IndexDocumentRequest(BaseModel):
    """Request to index a document."""
    
    entity_type: str
    entity_id: str
    title: str
    identifier: str | None = None
    description: str | None = None
    tags: list[str] = []
    notes: str | None = None
    custom_fields: dict[str, str] = {}
    status: str | None = None
    owner_id: str | None = None
    assigned_to_id: str | None = None
    account_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    subtitle: str | None = None
    url: str | None = None
    icon: str | None = None
    extra_data: dict[str, Any] = {}


class IndexAccountRequest(BaseModel):
    """Request to index an account."""
    
    account_id: str
    name: str
    description: str | None = None
    industry: str | None = None
    status: str | None = None
    owner_id: str | None = None


class IndexRFQRequest(BaseModel):
    """Request to index an RFQ."""
    
    rfq_id: str
    rfq_number: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    account_name: str | None = None
    owner_id: str | None = None
    account_id: str | None = None


class IndexQuoteRequest(BaseModel):
    """Request to index a quote."""
    
    quote_id: str
    quote_number: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    account_name: str | None = None
    owner_id: str | None = None
    account_id: str | None = None
    total_value: float | None = None


class IndexTaskRequest(BaseModel):
    """Request to index a task."""
    
    task_id: str
    title: str
    description: str | None = None
    status: str | None = None
    assignee_name: str | None = None
    owner_id: str | None = None
    assigned_to_id: str | None = None
    due_date: str | None = None


class IndexStatsResponse(BaseModel):
    """Index statistics."""
    
    total_documents: int
    entity_counts: dict[str, int]
    indexed_entity_types: list[str]


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _parse_uuid(value: str | None) -> UUID | None:
    """Parse a UUID string, returning None if invalid."""
    if not value:
        return None
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse a datetime string."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def _parse_entity_type(value: str) -> SearchableEntityType:
    """Parse an entity type string."""
    try:
        return SearchableEntityType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {value}",
        )


def _parse_sort_field(value: str) -> SearchSortField:
    """Parse a sort field string."""
    try:
        return SearchSortField(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field: {value}",
        )


def _parse_sort_order(value: str) -> SearchSortOrder:
    """Parse a sort order string."""
    try:
        return SearchSortOrder(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort order: {value}",
        )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("", response_model=SearchResultSetResponse)
async def search(
    current_user: CurrentActiveUser,
    q: str = Query(..., description="Search query"),
    entity_types: str | None = Query(None, description="Comma-separated entity types to filter"),
    status: str | None = Query(None, description="Comma-separated status values to filter"),
    owner_id: str | None = Query(None, description="Filter by owner ID"),
    account_id: str | None = Query(None, description="Filter by account ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("relevance", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    fuzzy: bool = Query(True, description="Enable fuzzy matching"),
) -> SearchResultSetResponse:
    """
    Perform a full-text search across all indexed entities.
    
    Supports filtering by entity type, status, owner, and account.
    Results are paginated and sorted by relevance by default.
    """
    service = get_service()
    
    # Build filter
    filters = SearchFilter()
    
    if entity_types:
        filters.entity_types = [_parse_entity_type(et.strip()) for et in entity_types.split(",")]
    
    if status:
        filters.status = [s.strip() for s in status.split(",")]
    
    if owner_id:
        filters.owner_id = _parse_uuid(owner_id)
    
    if account_id:
        filters.account_id = _parse_uuid(account_id)
    
    result = service.search(
        query=q,
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=_parse_sort_field(sort_by),
        sort_order=_parse_sort_order(sort_order),
        fuzzy=fuzzy,
    )
    
    return SearchResultSetResponse(
        results=[
            SearchResultResponse(
                entity_type=r.entity_type.value,
                entity_id=r.entity_id,
                title=r.title,
                subtitle=r.subtitle,
                description=r.description,
                status=r.status,
                relevance_score=r.relevance_score,
                matched_fields=r.matched_fields,
                highlights=r.highlights,
                url=r.url,
                icon=r.icon,
                extra_data=r.extra_data,
            )
            for r in result.results
        ],
        query=result.query,
        total_count=result.total_count,
        entity_counts=result.entity_counts,
        search_time_ms=result.search_time_ms,
        page=result.page,
        page_size=result.page_size,
        has_more=result.has_more,
    )


@router.get("/quick", response_model=QuickSearchResultResponse)
async def quick_search(
    current_user: CurrentActiveUser,
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    entity_types: str | None = Query(None, description="Comma-separated entity types to filter"),
) -> QuickSearchResultResponse:
    """
    Perform a quick search for fast navigation.
    
    Returns a small number of top results for keyboard navigation.
    """
    service = get_service()
    
    et_filter = None
    if entity_types:
        et_filter = [_parse_entity_type(et.strip()) for et in entity_types.split(",")]
    
    results = service.quick_search(
        query=q,
        limit=limit,
        entity_types=et_filter,
    )
    
    return QuickSearchResultResponse(
        results=[
            SearchResultResponse(
                entity_type=r.entity_type.value,
                entity_id=r.entity_id,
                title=r.title,
                subtitle=r.subtitle,
                description=r.description,
                status=r.status,
                relevance_score=r.relevance_score,
                matched_fields=r.matched_fields,
                highlights=r.highlights,
                url=r.url,
                icon=r.icon,
                extra_data=r.extra_data,
            )
            for r in results
        ],
        query=q,
    )


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    current_user: CurrentActiveUser,
    prefix: str = Query(..., description="Search prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=20, description="Maximum suggestions"),
    entity_types: str | None = Query(None, description="Comma-separated entity types to filter"),
) -> SuggestionsResponse:
    """
    Get autocomplete suggestions based on a prefix.
    
    Returns suggested search terms for autocomplete dropdowns.
    """
    service = get_service()
    
    et_filter = None
    if entity_types:
        et_filter = [_parse_entity_type(et.strip()) for et in entity_types.split(",")]
    
    suggestions = service.get_suggestions(
        prefix=prefix,
        limit=limit,
        entity_types=et_filter,
    )
    
    return SuggestionsResponse(
        prefix=prefix,
        suggestions=suggestions,
    )


@router.get("/entity-types")
async def list_entity_types(current_user: CurrentActiveUser) -> list[dict[str, str]]:
    """
    List all searchable entity types. Requires authentication.
    """
    return [
        {"value": et.value, "name": et.name}
        for et in SearchableEntityType
    ]


@router.get("/stats", response_model=IndexStatsResponse)
async def get_index_stats(current_user: CurrentActiveUser) -> IndexStatsResponse:
    """
    Get statistics about the search index. Requires authentication.
    """
    service = get_service()
    
    indexed_types = service.get_indexed_entity_types()
    entity_counts = {
        et.value: service.get_document_count(et)
        for et in indexed_types
    }
    
    return IndexStatsResponse(
        total_documents=service.get_document_count(),
        entity_counts=entity_counts,
        indexed_entity_types=[et.value for et in indexed_types],
    )


# --------------------------------------------------------------------------
# Index Management Endpoints
# --------------------------------------------------------------------------

@router.post("/index", status_code=status.HTTP_201_CREATED)
async def index_document(request: IndexDocumentRequest, current_user: CurrentSuperuser) -> dict[str, Any]:
    """
    Index a document for searching. Requires superuser access.
    """
    _deny_production_indexing()
    service = get_service()
    
    doc = SearchableDocument(
        entity_type=_parse_entity_type(request.entity_type),
        entity_id=request.entity_id,
        title=request.title,
        identifier=request.identifier or "",
        description=request.description or "",
        tags=request.tags,
        notes=request.notes or "",
        custom_fields=request.custom_fields,
        status=request.status,
        owner_id=_parse_uuid(request.owner_id),
        assigned_to_id=_parse_uuid(request.assigned_to_id),
        account_id=_parse_uuid(request.account_id),
        created_at=_parse_datetime(request.created_at),
        updated_at=_parse_datetime(request.updated_at),
        subtitle=request.subtitle or "",
        url=request.url,
        icon=request.icon,
        extra_data=request.extra_data,
    )
    
    service.index_document(doc)
    
    return {
        "indexed": True,
        "entity_type": request.entity_type,
        "entity_id": request.entity_id,
    }


@router.post("/index/account", status_code=status.HTTP_201_CREATED)
async def index_account_endpoint(request: IndexAccountRequest, current_user: CurrentSuperuser) -> dict[str, Any]:
    """
    Index an account for searching. Requires superuser access.
    """
    _deny_production_indexing()
    service = get_service()
    
    index_account(
        service,
        account_id=request.account_id,
        name=request.name,
        description=request.description,
        industry=request.industry,
        status=request.status,
        owner_id=_parse_uuid(request.owner_id),
    )
    
    return {
        "indexed": True,
        "entity_type": "account",
        "entity_id": request.account_id,
    }


@router.post("/index/rfq", status_code=status.HTTP_201_CREATED)
async def index_rfq_endpoint(request: IndexRFQRequest, current_user: CurrentSuperuser) -> dict[str, Any]:
    """
    Index an RFQ for searching. Requires superuser access.
    """
    _deny_production_indexing()
    service = get_service()
    
    index_rfq(
        service,
        rfq_id=request.rfq_id,
        rfq_number=request.rfq_number,
        title=request.title,
        description=request.description,
        status=request.status,
        account_name=request.account_name,
        owner_id=_parse_uuid(request.owner_id),
        account_id=_parse_uuid(request.account_id),
    )
    
    return {
        "indexed": True,
        "entity_type": "rfq",
        "entity_id": request.rfq_id,
    }


@router.post("/index/quote", status_code=status.HTTP_201_CREATED)
async def index_quote_endpoint(request: IndexQuoteRequest, current_user: CurrentSuperuser) -> dict[str, Any]:
    """
    Index a quote for searching. Requires superuser access.
    """
    _deny_production_indexing()
    service = get_service()
    
    index_quote(
        service,
        quote_id=request.quote_id,
        quote_number=request.quote_number,
        title=request.title,
        description=request.description,
        status=request.status,
        account_name=request.account_name,
        owner_id=_parse_uuid(request.owner_id),
        account_id=_parse_uuid(request.account_id),
        total_value=request.total_value,
    )
    
    return {
        "indexed": True,
        "entity_type": "quote",
        "entity_id": request.quote_id,
    }


@router.post("/index/task", status_code=status.HTTP_201_CREATED)
async def index_task_endpoint(request: IndexTaskRequest, current_user: CurrentSuperuser) -> dict[str, Any]:
    """
    Index a task for searching. Requires superuser access.
    """
    _deny_production_indexing()
    service = get_service()
    
    index_task(
        service,
        task_id=request.task_id,
        title=request.title,
        description=request.description,
        status=request.status,
        assignee_name=request.assignee_name,
        owner_id=_parse_uuid(request.owner_id),
        assigned_to_id=_parse_uuid(request.assigned_to_id),
        due_date=_parse_datetime(request.due_date),
    )
    
    return {
        "indexed": True,
        "entity_type": "task",
        "entity_id": request.task_id,
    }


@router.delete("/index/{entity_type}/{entity_id}")
async def remove_document(
    entity_type: str,
    entity_id: str,
    current_user: CurrentSuperuser,
) -> dict[str, Any]:
    """
    Remove a document from the search index. Requires superuser access.
    """
    _deny_production_indexing()
    service = get_service()
    
    et = _parse_entity_type(entity_type)
    removed = service.remove_document(et, entity_id)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {entity_type}/{entity_id}",
        )
    
    return {
        "removed": True,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }


@router.delete("/index/clear")
async def clear_index(
    current_user: CurrentSuperuser,
    entity_type: str | None = Query(None, description="Entity type to clear (all if not specified)"),
) -> dict[str, Any]:
    """
    Clear the search index. Requires superuser access.
    
    If entity_type is provided, only clears documents of that type.
    """
    _deny_production_indexing()
    service = get_service()
    
    et = _parse_entity_type(entity_type) if entity_type else None
    count = service.clear_index(et)
    
    return {
        "cleared": True,
        "entity_type": entity_type,
        "documents_removed": count,
    }

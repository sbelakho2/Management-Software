"""
Full-Text Search Service.

Provides search functionality across multiple entity types including
Accounts, RFQs, Quotes, CTQs, A3s, Tasks, and more.

Key features:
- Full-text search with ranking
- Entity-specific filtering
- Fuzzy matching for typos
- Quick-open/fast navigation
- Search result highlighting
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from html import escape as html_escape
from typing import Any, Callable
from uuid import UUID
import re


class SearchableEntityType(str, Enum):
    """Entity types that can be searched."""
    
    ACCOUNT = "account"
    CONTACT = "contact"
    RFQ = "rfq"
    QUOTE = "quote"
    OPPORTUNITY = "opportunity"
    CTQ = "ctq"
    A3 = "a3"
    TASK = "task"
    PRODUCT = "product"
    WORK_ORDER = "work_order"
    ANDON_EVENT = "andon_event"
    USER = "user"
    TRAINING = "training"
    STANDARD_WORK = "standard_work"


class SearchSortField(str, Enum):
    """Fields available for sorting search results."""
    
    RELEVANCE = "relevance"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"
    STATUS = "status"


class SearchSortOrder(str, Enum):
    """Sort order for search results."""
    
    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchResult:
    """A single search result."""
    
    entity_type: SearchableEntityType
    entity_id: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    status: str | None = None
    relevance_score: float = 0.0
    matched_fields: list[str] = field(default_factory=list)
    highlights: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    icon: str | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResultSet:
    """A set of search results with metadata."""
    
    results: list[SearchResult]
    query: str
    total_count: int = 0
    entity_counts: dict[str, int] = field(default_factory=dict)
    search_time_ms: float = 0.0
    page: int = 1
    page_size: int = 20
    has_more: bool = False


@dataclass
class SearchFilter:
    """Filter for narrowing search results."""
    
    entity_types: list[SearchableEntityType] | None = None
    status: list[str] | None = None
    owner_id: UUID | None = None
    assigned_to_id: UUID | None = None
    account_id: UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None
    tags: list[str] | None = None
    custom_filters: dict[str, Any] = field(default_factory=dict)


@dataclass 
class SearchableDocument:
    """
    A searchable document representing an entity.
    
    This is the indexed representation of an entity for searching.
    """
    
    entity_type: SearchableEntityType
    entity_id: str
    
    # Primary search fields (higher weight)
    title: str = ""
    identifier: str = ""  # RFQ number, quote number, etc.
    
    # Secondary search fields
    description: str = ""
    tags: list[str] = field(default_factory=list)
    
    # Tertiary search fields
    notes: str = ""
    custom_fields: dict[str, str] = field(default_factory=dict)
    
    # Metadata (for filtering)
    status: str | None = None
    owner_id: UUID | None = None
    assigned_to_id: UUID | None = None
    account_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    # Display info
    subtitle: str = ""
    url: str | None = None
    icon: str | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)


class FullTextSearchService:
    """
    Service for performing full-text search across entities.
    
    This is an in-memory implementation suitable for moderate data sizes.
    For production with large datasets, integrate with PostgreSQL FTS
    or Elasticsearch.
    """
    
    def __init__(self):
        """Initialize the search service."""
        self._documents: dict[str, SearchableDocument] = {}
        self._entity_type_icons = {
            SearchableEntityType.ACCOUNT: "building",
            SearchableEntityType.CONTACT: "user",
            SearchableEntityType.RFQ: "file-text",
            SearchableEntityType.QUOTE: "dollar-sign",
            SearchableEntityType.OPPORTUNITY: "target",
            SearchableEntityType.CTQ: "check-square",
            SearchableEntityType.A3: "layout",
            SearchableEntityType.TASK: "check-circle",
            SearchableEntityType.PRODUCT: "box",
            SearchableEntityType.WORK_ORDER: "clipboard",
            SearchableEntityType.ANDON_EVENT: "alert-triangle",
            SearchableEntityType.USER: "users",
            SearchableEntityType.TRAINING: "book",
            SearchableEntityType.STANDARD_WORK: "file",
        }
    
    def _make_key(self, entity_type: SearchableEntityType, entity_id: str) -> str:
        """Create a unique key for an entity."""
        return f"{entity_type.value}::{entity_id}"
    
    def index_document(self, doc: SearchableDocument) -> None:
        """
        Index a document for searching.
        
        Args:
            doc: The document to index
        """
        key = self._make_key(doc.entity_type, doc.entity_id)
        self._documents[key] = doc
    
    def index_documents(self, docs: list[SearchableDocument]) -> int:
        """
        Index multiple documents.
        
        Args:
            docs: Documents to index
            
        Returns:
            Number of documents indexed
        """
        for doc in docs:
            self.index_document(doc)
        return len(docs)
    
    def remove_document(
        self,
        entity_type: SearchableEntityType,
        entity_id: str,
    ) -> bool:
        """
        Remove a document from the index.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            
        Returns:
            True if removed, False if not found
        """
        key = self._make_key(entity_type, entity_id)
        if key in self._documents:
            del self._documents[key]
            return True
        return False
    
    def clear_index(self, entity_type: SearchableEntityType | None = None) -> int:
        """
        Clear the index.
        
        Args:
            entity_type: If provided, only clear documents of this type
            
        Returns:
            Number of documents removed
        """
        if entity_type is None:
            count = len(self._documents)
            self._documents.clear()
            return count
        
        keys_to_remove = [
            k for k, v in self._documents.items()
            if v.entity_type == entity_type
        ]
        for key in keys_to_remove:
            del self._documents[key]
        return len(keys_to_remove)
    
    def search(
        self,
        query: str,
        filters: SearchFilter | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: SearchSortField = SearchSortField.RELEVANCE,
        sort_order: SearchSortOrder = SearchSortOrder.DESC,
        fuzzy: bool = True,
    ) -> SearchResultSet:
        """
        Perform a full-text search.
        
        Args:
            query: Search query string
            filters: Optional filters
            page: Page number (1-indexed)
            page_size: Results per page
            sort_by: Field to sort by
            sort_order: Sort order
            fuzzy: Enable fuzzy matching
            
        Returns:
            Search result set
        """
        import time
        start = time.time()
        
        # Prepare query
        query = query.strip().lower()
        if not query:
            return SearchResultSet(
                results=[],
                query=query,
                total_count=0,
                search_time_ms=0.0,
                page=page,
                page_size=page_size,
            )
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        # Score all documents
        scored_results: list[tuple[SearchableDocument, float, list[str], dict[str, str]]] = []
        
        for doc in self._documents.values():
            # Apply filters
            if not self._matches_filters(doc, filters):
                continue
            
            # Calculate relevance score
            score, matched_fields, highlights = self._score_document(
                doc, query, query_tokens, fuzzy
            )
            
            if score > 0:
                scored_results.append((doc, score, matched_fields, highlights))
        
        # Sort results
        scored_results = self._sort_results(scored_results, sort_by, sort_order)
        
        # Count by entity type
        entity_counts: dict[str, int] = {}
        for doc, _, _, _ in scored_results:
            et = doc.entity_type.value
            entity_counts[et] = entity_counts.get(et, 0) + 1
        
        # Paginate
        total_count = len(scored_results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = scored_results[start_idx:end_idx]
        
        # Convert to SearchResult objects
        results = []
        for doc, score, matched_fields, highlights in page_results:
            results.append(SearchResult(
                entity_type=doc.entity_type,
                entity_id=doc.entity_id,
                title=doc.title,
                subtitle=doc.subtitle,
                description=doc.description[:200] if doc.description else None,
                status=doc.status,
                relevance_score=score,
                matched_fields=matched_fields,
                highlights=highlights,
                url=doc.url or self._generate_url(doc),
                icon=doc.icon or self._entity_type_icons.get(doc.entity_type),
                extra_data=doc.extra_data,
            ))
        
        elapsed_ms = (time.time() - start) * 1000
        
        return SearchResultSet(
            results=results,
            query=query,
            total_count=total_count,
            entity_counts=entity_counts,
            search_time_ms=elapsed_ms,
            page=page,
            page_size=page_size,
            has_more=end_idx < total_count,
        )
    
    def quick_search(
        self,
        query: str,
        limit: int = 10,
        entity_types: list[SearchableEntityType] | None = None,
    ) -> list[SearchResult]:
        """
        Perform a quick search for fast navigation.
        
        Args:
            query: Search query
            limit: Maximum results
            entity_types: Optional entity type filter
            
        Returns:
            List of search results
        """
        filters = SearchFilter(entity_types=entity_types) if entity_types else None
        result_set = self.search(query, filters=filters, page_size=limit)
        return result_set.results
    
    def get_suggestions(
        self,
        prefix: str,
        limit: int = 10,
        entity_types: list[SearchableEntityType] | None = None,
    ) -> list[str]:
        """
        Get autocomplete suggestions based on prefix.
        
        Args:
            prefix: Search prefix
            limit: Maximum suggestions
            entity_types: Optional entity type filter
            
        Returns:
            List of suggested search terms
        """
        prefix = prefix.strip().lower()
        if not prefix:
            return []
        
        suggestions = set()
        
        for doc in self._documents.values():
            if entity_types and doc.entity_type not in entity_types:
                continue
            
            # Check title
            if doc.title.lower().startswith(prefix):
                suggestions.add(doc.title)
            
            # Check identifier
            if doc.identifier.lower().startswith(prefix):
                suggestions.add(doc.identifier)
            
            # Check words in title
            for word in doc.title.split():
                if word.lower().startswith(prefix):
                    suggestions.add(word)
            
            if len(suggestions) >= limit * 2:
                break
        
        return sorted(suggestions)[:limit]
    
    def get_document_count(
        self,
        entity_type: SearchableEntityType | None = None,
    ) -> int:
        """
        Get the number of indexed documents.
        
        Args:
            entity_type: Optional filter by type
            
        Returns:
            Document count
        """
        if entity_type is None:
            return len(self._documents)
        
        return sum(
            1 for doc in self._documents.values()
            if doc.entity_type == entity_type
        )
    
    def get_indexed_entity_types(self) -> list[SearchableEntityType]:
        """Get list of entity types that have indexed documents."""
        types = set()
        for doc in self._documents.values():
            types.add(doc.entity_type)
        return sorted(types, key=lambda x: x.value)
    
    # --------------------------------------------------------------------------
    # Private Methods
    # --------------------------------------------------------------------------
    
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into searchable tokens."""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [t for t in text.split() if len(t) >= 2]
    
    def _matches_filters(
        self,
        doc: SearchableDocument,
        filters: SearchFilter | None,
    ) -> bool:
        """Check if a document matches the given filters."""
        if filters is None:
            return True
        
        if filters.entity_types and doc.entity_type not in filters.entity_types:
            return False
        
        if filters.status and doc.status not in filters.status:
            return False
        
        if filters.owner_id and doc.owner_id != filters.owner_id:
            return False
        
        if filters.assigned_to_id and doc.assigned_to_id != filters.assigned_to_id:
            return False
        
        if filters.account_id and doc.account_id != filters.account_id:
            return False
        
        if filters.created_after and doc.created_at:
            if doc.created_at < filters.created_after:
                return False
        
        if filters.created_before and doc.created_at:
            if doc.created_at > filters.created_before:
                return False
        
        if filters.updated_after and doc.updated_at:
            if doc.updated_at < filters.updated_after:
                return False
        
        if filters.updated_before and doc.updated_at:
            if doc.updated_at > filters.updated_before:
                return False
        
        if filters.tags:
            if not any(tag in doc.tags for tag in filters.tags):
                return False
        
        return True
    
    def _score_document(
        self,
        doc: SearchableDocument,
        query: str,
        query_tokens: list[str],
        fuzzy: bool,
    ) -> tuple[float, list[str], dict[str, str]]:
        """
        Score a document against a query.
        
        Returns:
            Tuple of (score, matched_fields, highlights)
        """
        score = 0.0
        matched_fields: list[str] = []
        highlights: dict[str, str] = {}
        
        # Exact match in title - highest score
        title_lower = doc.title.lower()
        if query in title_lower:
            score += 100.0
            matched_fields.append("title")
            highlights["title"] = self._highlight(doc.title, query)
        elif any(token in title_lower for token in query_tokens):
            for token in query_tokens:
                if token in title_lower:
                    score += 50.0
            matched_fields.append("title")
            highlights["title"] = self._highlight_tokens(doc.title, query_tokens)
        elif fuzzy and self._fuzzy_match(title_lower, query_tokens):
            score += 25.0
            matched_fields.append("title")
        
        # Exact match in identifier
        id_lower = doc.identifier.lower()
        if query in id_lower:
            score += 80.0
            matched_fields.append("identifier")
            highlights["identifier"] = self._highlight(doc.identifier, query)
        elif any(token in id_lower for token in query_tokens):
            for token in query_tokens:
                if token in id_lower:
                    score += 40.0
            matched_fields.append("identifier")
        
        # Match in description
        desc_lower = doc.description.lower()
        if query in desc_lower:
            score += 30.0
            matched_fields.append("description")
            highlights["description"] = self._highlight(doc.description[:200], query)
        elif any(token in desc_lower for token in query_tokens):
            for token in query_tokens:
                if token in desc_lower:
                    score += 10.0
            matched_fields.append("description")
        
        # Match in tags
        for tag in doc.tags:
            tag_lower = tag.lower()
            if query in tag_lower or any(token in tag_lower for token in query_tokens):
                score += 20.0
                matched_fields.append("tags")
                break
        
        # Match in notes
        notes_lower = doc.notes.lower()
        if query in notes_lower or any(token in notes_lower for token in query_tokens):
            score += 5.0
            matched_fields.append("notes")
        
        # Match in custom fields
        for field_name, field_value in doc.custom_fields.items():
            field_lower = field_value.lower()
            if query in field_lower or any(token in field_lower for token in query_tokens):
                score += 5.0
                matched_fields.append(f"custom:{field_name}")
        
        return score, matched_fields, highlights
    
    def _fuzzy_match(self, text: str, tokens: list[str], threshold: int = 2) -> bool:
        """Check for fuzzy matches (allowing for typos)."""
        for token in tokens:
            for word in text.split():
                if self._levenshtein_distance(token, word) <= threshold:
                    return True
        return False
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row: list[int] = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _highlight(self, text: str, query: str) -> str:
        """
        Highlight query matches in text.
        
        SECURITY: Text and query are HTML-escaped to prevent XSS attacks.
        """
        # HTML-escape both the text and query to prevent XSS
        safe_text = html_escape(text)
        safe_query = html_escape(query)
        
        pattern = re.compile(re.escape(safe_query), re.IGNORECASE)
        return pattern.sub(f"<mark>{safe_query}</mark>", safe_text)
    
    def _highlight_tokens(self, text: str, tokens: list[str]) -> str:
        """
        Highlight token matches in text.
        
        SECURITY: Text and tokens are HTML-escaped to prevent XSS attacks.
        """
        # HTML-escape the text first
        result = html_escape(text)
        
        for token in tokens:
            # HTML-escape each token
            safe_token = html_escape(token)
            pattern = re.compile(re.escape(safe_token), re.IGNORECASE)
            result = pattern.sub(f"<mark>{safe_token}</mark>", result)
        return result
    
    def _sort_results(
        self,
        results: list[tuple[SearchableDocument, float, list[str], dict[str, str]]],
        sort_by: SearchSortField,
        sort_order: SearchSortOrder,
    ) -> list[tuple[SearchableDocument, float, list[str], dict[str, str]]]:
        """Sort results by the specified field and order."""
        reverse = sort_order == SearchSortOrder.DESC
        
        if sort_by == SearchSortField.RELEVANCE:
            return sorted(results, key=lambda x: x[1], reverse=reverse)
        elif sort_by == SearchSortField.CREATED_AT:
            return sorted(
                results,
                key=lambda x: x[0].created_at or datetime.min,
                reverse=reverse
            )
        elif sort_by == SearchSortField.UPDATED_AT:
            return sorted(
                results,
                key=lambda x: x[0].updated_at or datetime.min,
                reverse=reverse
            )
        elif sort_by == SearchSortField.NAME:
            return sorted(results, key=lambda x: x[0].title.lower(), reverse=reverse)
        elif sort_by == SearchSortField.STATUS:
            return sorted(
                results,
                key=lambda x: x[0].status or "",
                reverse=reverse
            )
        
        return results
    
    def _generate_url(self, doc: SearchableDocument) -> str:
        """Generate a URL for navigating to the entity."""
        et = doc.entity_type.value.replace("_", "-")
        return f"/{et}s/{doc.entity_id}"


# --------------------------------------------------------------------------
# Helper functions for indexing common entities
# --------------------------------------------------------------------------

def index_account(
    service: FullTextSearchService,
    account_id: str,
    name: str,
    description: str | None = None,
    industry: str | None = None,
    status: str | None = None,
    owner_id: UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Index an account for searching."""
    doc = SearchableDocument(
        entity_type=SearchableEntityType.ACCOUNT,
        entity_id=account_id,
        title=name,
        identifier=name,
        description=description or "",
        status=status,
        owner_id=owner_id,
        created_at=created_at,
        updated_at=updated_at,
        subtitle=industry or "",
        extra_data=extra_data or {},
    )
    service.index_document(doc)


def index_rfq(
    service: FullTextSearchService,
    rfq_id: str,
    rfq_number: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    account_name: str | None = None,
    owner_id: UUID | None = None,
    account_id: UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Index an RFQ for searching."""
    doc = SearchableDocument(
        entity_type=SearchableEntityType.RFQ,
        entity_id=rfq_id,
        title=title or rfq_number,
        identifier=rfq_number,
        description=description or "",
        status=status,
        owner_id=owner_id,
        account_id=account_id,
        created_at=created_at,
        updated_at=updated_at,
        subtitle=account_name or "",
        extra_data=extra_data or {},
    )
    service.index_document(doc)


def index_quote(
    service: FullTextSearchService,
    quote_id: str,
    quote_number: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    account_name: str | None = None,
    owner_id: UUID | None = None,
    account_id: UUID | None = None,
    total_value: float | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Index a quote for searching."""
    extra = extra_data or {}
    if total_value is not None:
        extra["total_value"] = total_value
    
    doc = SearchableDocument(
        entity_type=SearchableEntityType.QUOTE,
        entity_id=quote_id,
        title=title or quote_number,
        identifier=quote_number,
        description=description or "",
        status=status,
        owner_id=owner_id,
        account_id=account_id,
        created_at=created_at,
        updated_at=updated_at,
        subtitle=account_name or "",
        extra_data=extra,
    )
    service.index_document(doc)


def index_task(
    service: FullTextSearchService,
    task_id: str,
    title: str,
    description: str | None = None,
    status: str | None = None,
    assignee_name: str | None = None,
    owner_id: UUID | None = None,
    assigned_to_id: UUID | None = None,
    due_date: datetime | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Index a task for searching."""
    extra = extra_data or {}
    if due_date is not None:
        extra["due_date"] = due_date.isoformat()
    
    doc = SearchableDocument(
        entity_type=SearchableEntityType.TASK,
        entity_id=task_id,
        title=title,
        identifier=task_id[:8] if len(task_id) > 8 else task_id,
        description=description or "",
        status=status,
        owner_id=owner_id,
        assigned_to_id=assigned_to_id,
        created_at=created_at,
        updated_at=updated_at,
        subtitle=assignee_name or "",
        extra_data=extra,
    )
    service.index_document(doc)


def index_a3(
    service: FullTextSearchService,
    a3_id: str,
    title: str,
    problem_statement: str | None = None,
    status: str | None = None,
    owner_name: str | None = None,
    owner_id: UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Index an A3 document for searching."""
    doc = SearchableDocument(
        entity_type=SearchableEntityType.A3,
        entity_id=a3_id,
        title=title,
        identifier=a3_id[:8] if len(a3_id) > 8 else a3_id,
        description=problem_statement or "",
        status=status,
        owner_id=owner_id,
        created_at=created_at,
        updated_at=updated_at,
        subtitle=owner_name or "",
        extra_data=extra_data or {},
    )
    service.index_document(doc)


def index_ctq(
    service: FullTextSearchService,
    ctq_id: str,
    name: str,
    description: str | None = None,
    category: str | None = None,
    product_name: str | None = None,
    owner_id: UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Index a CTQ for searching."""
    doc = SearchableDocument(
        entity_type=SearchableEntityType.CTQ,
        entity_id=ctq_id,
        title=name,
        identifier=ctq_id[:8] if len(ctq_id) > 8 else ctq_id,
        description=description or "",
        status=category,
        owner_id=owner_id,
        created_at=created_at,
        updated_at=updated_at,
        subtitle=product_name or "",
        tags=[category] if category else [],
        extra_data=extra_data or {},
    )
    service.index_document(doc)

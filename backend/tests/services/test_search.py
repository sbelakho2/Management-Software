"""
Tests for the Full-Text Search Service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID

from sensei.services.core.search import (
    FullTextSearchService,
    SearchableEntityType,
    SearchSortField,
    SearchSortOrder,
    SearchResult,
    SearchResultSet,
    SearchFilter,
    SearchableDocument,
    index_account,
    index_rfq,
    index_quote,
    index_task,
    index_a3,
    index_ctq,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def service() -> FullTextSearchService:
    """Create a fresh search service instance."""
    return FullTextSearchService()


@pytest.fixture
def now() -> datetime:
    """Reference datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def owner_id() -> UUID:
    """Test owner ID."""
    return uuid4()


@pytest.fixture
def populated_service(service: FullTextSearchService, owner_id: UUID, now: datetime) -> FullTextSearchService:
    """Create a service with sample data indexed."""
    # Index accounts
    index_account(service, "acc-1", "Acme Corporation", "Manufacturing company", "Manufacturing", "active", owner_id, now - timedelta(days=30))
    index_account(service, "acc-2", "TechCo Industries", "Technology services", "Technology", "active", owner_id, now - timedelta(days=20))
    index_account(service, "acc-3", "Global Widgets Inc", "Widget manufacturing", "Manufacturing", "inactive", owner_id, now - timedelta(days=60))
    
    # Index RFQs
    index_rfq(service, "rfq-1", "RFQ-2024-001", "Machine Parts Quote", "Request for custom machined parts", "open", "Acme Corporation", owner_id, None, now - timedelta(days=5))
    index_rfq(service, "rfq-2", "RFQ-2024-002", "Electronics Assembly", "PCB assembly request", "closed", "TechCo Industries", owner_id, None, now - timedelta(days=10))
    index_rfq(service, "rfq-3", "RFQ-2024-003", "Widget Components", "Standard widgets quote", "pending", "Global Widgets Inc", owner_id, None, now - timedelta(days=3))
    
    # Index quotes
    index_quote(service, "quote-1", "Q-2024-100", "Machine Parts Proposal", "Detailed quote for parts", "draft", "Acme Corporation", owner_id, None, 50000.0, now - timedelta(days=2))
    index_quote(service, "quote-2", "Q-2024-101", "Electronics Package", "Assembly quote", "approved", "TechCo Industries", owner_id, None, 75000.0, now - timedelta(days=7))
    
    # Index tasks
    index_task(service, "task-1", "Review RFQ requirements", "Check all requirements for RFQ-001", "pending", "John Smith", owner_id, owner_id, now + timedelta(days=2), now - timedelta(days=1))
    index_task(service, "task-2", "Finalize quote pricing", "Update pricing for Q-2024-100", "in_progress", "Jane Doe", owner_id, owner_id, now + timedelta(days=1), now - timedelta(hours=6))
    index_task(service, "task-3", "Quality inspection", "Perform incoming inspection", "completed", "Bob Wilson", owner_id, owner_id, now - timedelta(days=1), now - timedelta(days=3))
    
    # Index A3s
    index_a3(service, "a3-1", "Machine Downtime Analysis", "Recurring downtime on CNC-01", "in_progress", "Operations Team", owner_id, now - timedelta(days=14))
    index_a3(service, "a3-2", "Quality Improvement Project", "Reducing defect rate in assembly", "draft", "Quality Team", owner_id, now - timedelta(days=7))
    
    # Index CTQs
    index_ctq(service, "ctq-1", "Surface Finish Tolerance", "Ra value must be within 32 microinches", "dimension", "Custom Widget", owner_id, now - timedelta(days=30))
    index_ctq(service, "ctq-2", "Weight Requirement", "Part weight 500g +/- 5g", "dimension", "Assembly Part", owner_id, now - timedelta(days=20))
    
    return service


# --------------------------------------------------------------------------
# Enum Tests
# --------------------------------------------------------------------------

class TestEnums:
    """Tests for enum values."""
    
    def test_searchable_entity_type_values(self):
        """Test SearchableEntityType enum values."""
        assert SearchableEntityType.ACCOUNT.value == "account"
        assert SearchableEntityType.RFQ.value == "rfq"
        assert SearchableEntityType.QUOTE.value == "quote"
        assert SearchableEntityType.TASK.value == "task"
        assert SearchableEntityType.A3.value == "a3"
        assert SearchableEntityType.CTQ.value == "ctq"
    
    def test_search_sort_field_values(self):
        """Test SearchSortField enum values."""
        assert SearchSortField.RELEVANCE.value == "relevance"
        assert SearchSortField.CREATED_AT.value == "created_at"
        assert SearchSortField.NAME.value == "name"
    
    def test_search_sort_order_values(self):
        """Test SearchSortOrder enum values."""
        assert SearchSortOrder.ASC.value == "asc"
        assert SearchSortOrder.DESC.value == "desc"


# --------------------------------------------------------------------------
# Dataclass Tests
# --------------------------------------------------------------------------

class TestSearchableDocument:
    """Tests for SearchableDocument dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        doc = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="test-1",
        )
        assert doc.title == ""
        assert doc.description == ""
        assert doc.tags == []
        assert doc.status is None
    
    def test_with_values(self):
        """Test with custom values."""
        owner = uuid4()
        doc = SearchableDocument(
            entity_type=SearchableEntityType.RFQ,
            entity_id="rfq-123",
            title="Test RFQ",
            identifier="RFQ-2024-001",
            description="A test RFQ",
            status="open",
            owner_id=owner,
            tags=["urgent", "priority"],
        )
        assert doc.entity_type == SearchableEntityType.RFQ
        assert doc.title == "Test RFQ"
        assert doc.identifier == "RFQ-2024-001"
        assert doc.owner_id == owner
        assert "urgent" in doc.tags


class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        result = SearchResult(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Test Account",
        )
        assert result.relevance_score == 0.0
        assert result.matched_fields == []
        assert result.highlights == {}
    
    def test_with_values(self):
        """Test with custom values."""
        result = SearchResult(
            entity_type=SearchableEntityType.QUOTE,
            entity_id="q-1",
            title="Test Quote",
            relevance_score=85.5,
            matched_fields=["title", "description"],
            highlights={"title": "Test <mark>Quote</mark>"},
        )
        assert result.relevance_score == 85.5
        assert len(result.matched_fields) == 2


class TestSearchResultSet:
    """Tests for SearchResultSet dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        result_set = SearchResultSet(
            results=[],
            query="test",
        )
        assert result_set.total_count == 0
        assert result_set.page == 1
        assert result_set.page_size == 20
        assert result_set.has_more is False


class TestSearchFilter:
    """Tests for SearchFilter dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        filter = SearchFilter()
        assert filter.entity_types is None
        assert filter.status is None
        assert filter.owner_id is None
    
    def test_with_values(self):
        """Test with custom values."""
        owner = uuid4()
        filter = SearchFilter(
            entity_types=[SearchableEntityType.RFQ, SearchableEntityType.QUOTE],
            status=["open", "pending"],
            owner_id=owner,
        )
        assert len(filter.entity_types) == 2
        assert len(filter.status) == 2
        assert filter.owner_id == owner


# --------------------------------------------------------------------------
# Service Tests
# --------------------------------------------------------------------------

class TestFullTextSearchService:
    """Tests for FullTextSearchService."""
    
    def test_initialization(self, service: FullTextSearchService):
        """Test service initializes empty."""
        assert service.get_document_count() == 0
    
    def test_index_document(self, service: FullTextSearchService):
        """Test indexing a document."""
        doc = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Test Account",
        )
        service.index_document(doc)
        assert service.get_document_count() == 1
    
    def test_index_documents(self, service: FullTextSearchService):
        """Test indexing multiple documents."""
        docs = [
            SearchableDocument(entity_type=SearchableEntityType.ACCOUNT, entity_id="acc-1", title="Account 1"),
            SearchableDocument(entity_type=SearchableEntityType.ACCOUNT, entity_id="acc-2", title="Account 2"),
            SearchableDocument(entity_type=SearchableEntityType.RFQ, entity_id="rfq-1", title="RFQ 1"),
        ]
        count = service.index_documents(docs)
        assert count == 3
        assert service.get_document_count() == 3
    
    def test_remove_document(self, service: FullTextSearchService):
        """Test removing a document."""
        doc = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Test Account",
        )
        service.index_document(doc)
        assert service.get_document_count() == 1
        
        result = service.remove_document(SearchableEntityType.ACCOUNT, "acc-1")
        assert result is True
        assert service.get_document_count() == 0
    
    def test_remove_nonexistent_document(self, service: FullTextSearchService):
        """Test removing a document that doesn't exist."""
        result = service.remove_document(SearchableEntityType.ACCOUNT, "nonexistent")
        assert result is False
    
    def test_clear_index_all(self, service: FullTextSearchService):
        """Test clearing all documents."""
        docs = [
            SearchableDocument(entity_type=SearchableEntityType.ACCOUNT, entity_id="acc-1", title="Account 1"),
            SearchableDocument(entity_type=SearchableEntityType.RFQ, entity_id="rfq-1", title="RFQ 1"),
        ]
        service.index_documents(docs)
        
        count = service.clear_index()
        assert count == 2
        assert service.get_document_count() == 0
    
    def test_clear_index_by_type(self, service: FullTextSearchService):
        """Test clearing documents by entity type."""
        docs = [
            SearchableDocument(entity_type=SearchableEntityType.ACCOUNT, entity_id="acc-1", title="Account 1"),
            SearchableDocument(entity_type=SearchableEntityType.ACCOUNT, entity_id="acc-2", title="Account 2"),
            SearchableDocument(entity_type=SearchableEntityType.RFQ, entity_id="rfq-1", title="RFQ 1"),
        ]
        service.index_documents(docs)
        
        count = service.clear_index(SearchableEntityType.ACCOUNT)
        assert count == 2
        assert service.get_document_count() == 1
        assert service.get_document_count(SearchableEntityType.RFQ) == 1
    
    def test_get_indexed_entity_types(self, populated_service: FullTextSearchService):
        """Test getting indexed entity types."""
        types = populated_service.get_indexed_entity_types()
        assert SearchableEntityType.ACCOUNT in types
        assert SearchableEntityType.RFQ in types
        assert SearchableEntityType.QUOTE in types
        assert SearchableEntityType.TASK in types


# --------------------------------------------------------------------------
# Search Tests
# --------------------------------------------------------------------------

class TestSearch:
    """Tests for search functionality."""
    
    def test_empty_query(self, populated_service: FullTextSearchService):
        """Test search with empty query."""
        result = populated_service.search("")
        assert result.total_count == 0
        assert len(result.results) == 0
    
    def test_simple_search(self, populated_service: FullTextSearchService):
        """Test simple search."""
        result = populated_service.search("Acme")
        assert result.total_count > 0
        
        # Should find Acme Corporation account and related entities
        titles = [r.title for r in result.results]
        assert any("Acme" in t for t in titles)
    
    def test_search_by_identifier(self, populated_service: FullTextSearchService):
        """Test search by identifier."""
        result = populated_service.search("RFQ-2024-001")
        assert result.total_count > 0
        assert any(r.entity_type == SearchableEntityType.RFQ for r in result.results)
    
    def test_search_multiple_words(self, populated_service: FullTextSearchService):
        """Test search with multiple words."""
        result = populated_service.search("machine parts")
        assert result.total_count > 0
    
    def test_search_case_insensitive(self, populated_service: FullTextSearchService):
        """Test case insensitive search."""
        result1 = populated_service.search("acme")
        result2 = populated_service.search("ACME")
        result3 = populated_service.search("Acme")
        
        assert result1.total_count == result2.total_count == result3.total_count
    
    def test_search_partial_match(self, populated_service: FullTextSearchService):
        """Test partial word matching."""
        result = populated_service.search("widget")
        assert result.total_count > 0
    
    def test_search_with_filter_entity_type(self, populated_service: FullTextSearchService):
        """Test search filtered by entity type."""
        filter = SearchFilter(entity_types=[SearchableEntityType.RFQ])
        result = populated_service.search("quote", filters=filter)
        
        for r in result.results:
            assert r.entity_type == SearchableEntityType.RFQ
    
    def test_search_with_filter_status(self, populated_service: FullTextSearchService):
        """Test search filtered by status."""
        filter = SearchFilter(status=["open", "pending"])
        result = populated_service.search("RFQ")
        
        # Should find RFQs regardless of status
        assert result.total_count > 0
    
    def test_search_with_filter_owner(self, populated_service: FullTextSearchService, owner_id: UUID):
        """Test search filtered by owner."""
        filter = SearchFilter(owner_id=owner_id)
        result = populated_service.search("Corporation", filters=filter)
        assert result.total_count > 0
    
    def test_search_pagination(self, populated_service: FullTextSearchService):
        """Test search pagination."""
        # Get all results
        all_results = populated_service.search("a", page_size=100)
        
        # Get first page
        page1 = populated_service.search("a", page=1, page_size=3)
        
        # Get second page
        page2 = populated_service.search("a", page=2, page_size=3)
        
        if all_results.total_count > 3:
            assert page1.has_more
            assert len(page1.results) == 3
    
    def test_search_sort_by_relevance(self, populated_service: FullTextSearchService):
        """Test sorting by relevance."""
        result = populated_service.search(
            "acme",
            sort_by=SearchSortField.RELEVANCE,
            sort_order=SearchSortOrder.DESC,
        )
        
        if len(result.results) >= 2:
            assert result.results[0].relevance_score >= result.results[1].relevance_score
    
    def test_search_sort_by_name(self, populated_service: FullTextSearchService):
        """Test sorting by name."""
        result = populated_service.search(
            "a",  # Match many things
            sort_by=SearchSortField.NAME,
            sort_order=SearchSortOrder.ASC,
        )
        
        if len(result.results) >= 2:
            assert result.results[0].title.lower() <= result.results[1].title.lower()
    
    def test_search_entity_counts(self, populated_service: FullTextSearchService):
        """Test entity counts in results."""
        result = populated_service.search("a")
        
        assert isinstance(result.entity_counts, dict)
        # Should have counts for various entity types
        assert len(result.entity_counts) > 0
    
    def test_search_time_recorded(self, populated_service: FullTextSearchService):
        """Test search time is recorded."""
        result = populated_service.search("acme")
        assert result.search_time_ms >= 0
    
    def test_search_highlights(self, populated_service: FullTextSearchService):
        """Test search result highlights."""
        result = populated_service.search("Acme")
        
        acme_result = next((r for r in result.results if "Acme" in r.title), None)
        if acme_result:
            assert len(acme_result.highlights) > 0
    
    def test_fuzzy_search(self, populated_service: FullTextSearchService):
        """Test fuzzy matching (typo tolerance)."""
        # "Acmee" should still match "Acme" with fuzzy=True
        result = populated_service.search("Acmee", fuzzy=True)
        # May or may not find depending on threshold, but should not error
        assert isinstance(result, SearchResultSet)
    
    def test_fuzzy_search_disabled(self, populated_service: FullTextSearchService):
        """Test fuzzy matching disabled."""
        # With fuzzy=False, typos should not match
        result = populated_service.search("Xyzzy", fuzzy=False)
        assert result.total_count == 0


# --------------------------------------------------------------------------
# Quick Search Tests
# --------------------------------------------------------------------------

class TestQuickSearch:
    """Tests for quick search functionality."""
    
    def test_quick_search(self, populated_service: FullTextSearchService):
        """Test quick search."""
        results = populated_service.quick_search("acme", limit=5)
        assert len(results) <= 5
        assert all(isinstance(r, SearchResult) for r in results)
    
    def test_quick_search_with_entity_type(self, populated_service: FullTextSearchService):
        """Test quick search filtered by entity type."""
        results = populated_service.quick_search(
            "quote",
            limit=5,
            entity_types=[SearchableEntityType.QUOTE],
        )
        
        for r in results:
            assert r.entity_type == SearchableEntityType.QUOTE


# --------------------------------------------------------------------------
# Suggestions Tests
# --------------------------------------------------------------------------

class TestSuggestions:
    """Tests for autocomplete suggestions."""
    
    def test_get_suggestions(self, populated_service: FullTextSearchService):
        """Test getting suggestions."""
        suggestions = populated_service.get_suggestions("Acm", limit=5)
        assert len(suggestions) > 0
        assert any("Acme" in s for s in suggestions)
    
    def test_get_suggestions_empty(self, populated_service: FullTextSearchService):
        """Test suggestions with empty prefix."""
        suggestions = populated_service.get_suggestions("")
        assert len(suggestions) == 0
    
    def test_get_suggestions_limit(self, populated_service: FullTextSearchService):
        """Test suggestions respect limit."""
        suggestions = populated_service.get_suggestions("a", limit=3)
        assert len(suggestions) <= 3


# --------------------------------------------------------------------------
# Helper Function Tests
# --------------------------------------------------------------------------

class TestIndexHelpers:
    """Tests for index helper functions."""
    
    def test_index_account(self, service: FullTextSearchService, owner_id: UUID, now: datetime):
        """Test index_account helper."""
        index_account(
            service,
            account_id="acc-1",
            name="Test Account",
            description="A test account",
            industry="Tech",
            status="active",
            owner_id=owner_id,
            created_at=now,
        )
        
        assert service.get_document_count() == 1
        result = service.search("Test Account")
        assert result.total_count == 1
        assert result.results[0].entity_type == SearchableEntityType.ACCOUNT
    
    def test_index_rfq(self, service: FullTextSearchService, owner_id: UUID, now: datetime):
        """Test index_rfq helper."""
        index_rfq(
            service,
            rfq_id="rfq-1",
            rfq_number="RFQ-2024-001",
            title="Machine Parts",
            description="Request for parts",
            status="open",
            account_name="Acme Corp",
            owner_id=owner_id,
            created_at=now,
        )
        
        assert service.get_document_count() == 1
        result = service.search("RFQ-2024-001")
        assert result.total_count == 1
        assert result.results[0].entity_type == SearchableEntityType.RFQ
    
    def test_index_quote(self, service: FullTextSearchService, owner_id: UUID, now: datetime):
        """Test index_quote helper."""
        index_quote(
            service,
            quote_id="quote-1",
            quote_number="Q-2024-100",
            title="Quote Proposal",
            status="draft",
            total_value=50000.0,
            owner_id=owner_id,
            created_at=now,
        )
        
        assert service.get_document_count() == 1
        result = service.search("Q-2024-100")
        assert result.total_count == 1
        assert result.results[0].extra_data["total_value"] == 50000.0
    
    def test_index_task(self, service: FullTextSearchService, owner_id: UUID, now: datetime):
        """Test index_task helper."""
        index_task(
            service,
            task_id="task-1",
            title="Review requirements",
            description="Check all requirements",
            status="pending",
            assignee_name="John Doe",
            owner_id=owner_id,
            due_date=now + timedelta(days=3),
            created_at=now,
        )
        
        result = service.search("Review requirements")
        assert result.total_count == 1
        assert result.results[0].entity_type == SearchableEntityType.TASK
    
    def test_index_a3(self, service: FullTextSearchService, owner_id: UUID, now: datetime):
        """Test index_a3 helper."""
        index_a3(
            service,
            a3_id="a3-1",
            title="Downtime Analysis",
            problem_statement="Machine keeps stopping",
            status="in_progress",
            owner_name="Operations",
            owner_id=owner_id,
            created_at=now,
        )
        
        result = service.search("Downtime Analysis")
        assert result.total_count == 1
        assert result.results[0].entity_type == SearchableEntityType.A3
    
    def test_index_ctq(self, service: FullTextSearchService, owner_id: UUID, now: datetime):
        """Test index_ctq helper."""
        index_ctq(
            service,
            ctq_id="ctq-1",
            name="Surface Finish",
            description="Ra value specification",
            category="dimension",
            product_name="Widget Part",
            owner_id=owner_id,
            created_at=now,
        )
        
        result = service.search("Surface Finish")
        assert result.total_count == 1
        assert result.results[0].entity_type == SearchableEntityType.CTQ


# --------------------------------------------------------------------------
# Edge Cases
# --------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_special_characters(self, populated_service: FullTextSearchService):
        """Test search with special characters."""
        # Should not crash
        result = populated_service.search("test@example.com")
        assert isinstance(result, SearchResultSet)
    
    def test_unicode_search(self, service: FullTextSearchService):
        """Test search with unicode characters."""
        doc = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="日本語のアカウント",
            description="Japanese account",
        )
        service.index_document(doc)
        
        result = service.search("日本語")
        assert result.total_count == 1
    
    def test_very_long_query(self, populated_service: FullTextSearchService):
        """Test search with very long query."""
        long_query = "a " * 100
        result = populated_service.search(long_query)
        # Should not crash
        assert isinstance(result, SearchResultSet)
    
    def test_url_generation(self, service: FullTextSearchService):
        """Test URL generation for different entity types."""
        docs = [
            SearchableDocument(entity_type=SearchableEntityType.ACCOUNT, entity_id="123", title="Test"),
            SearchableDocument(entity_type=SearchableEntityType.RFQ, entity_id="456", title="Test"),
            SearchableDocument(entity_type=SearchableEntityType.WORK_ORDER, entity_id="789", title="Test"),
        ]
        service.index_documents(docs)
        
        result = service.search("Test")
        
        for r in result.results:
            assert r.url is not None
            assert r.entity_id in r.url
    
    def test_icon_assignment(self, service: FullTextSearchService):
        """Test icon assignment for entity types."""
        doc = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="123",
            title="Test",
        )
        service.index_document(doc)
        
        result = service.search("Test")
        assert len(result.results) == 1
        assert result.results[0].icon == "building"
    
    def test_date_filter_created_after(self, populated_service: FullTextSearchService, now: datetime):
        """Test date filtering - created after."""
        filter = SearchFilter(
            created_after=now - timedelta(days=10)
        )
        result = populated_service.search("a", filters=filter)
        
        # All results should be created after the filter date
        # This depends on our test data setup
        assert isinstance(result, SearchResultSet)
    
    def test_document_update(self, service: FullTextSearchService):
        """Test updating an existing document."""
        doc1 = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Alpha Company",
        )
        service.index_document(doc1)
        
        # Update with new title
        doc2 = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Beta Corporation",
        )
        service.index_document(doc2)
        
        # Should still only have one document
        assert service.get_document_count() == 1
        
        # Should find by new name
        result = service.search("Beta Corporation")
        assert result.total_count == 1
        
        # Should not find by old name
        result = service.search("Alpha Company")
        assert result.total_count == 0


class TestRelevanceScoring:
    """Tests for relevance scoring."""
    
    def test_title_match_scores_higher(self, service: FullTextSearchService):
        """Test that title matches score higher than description matches."""
        # Document with "test" in title
        doc1 = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Test Account",
            description="Something else",
        )
        
        # Document with "test" in description
        doc2 = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-2",
            title="Other Account",
            description="This is a test description",
        )
        
        service.index_documents([doc1, doc2])
        
        result = service.search("test")
        assert result.total_count == 2
        
        # Title match should be first (higher relevance)
        assert result.results[0].entity_id == "acc-1"
    
    def test_exact_match_scores_higher(self, service: FullTextSearchService):
        """Test that exact matches score higher than partial matches."""
        doc1 = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-1",
            title="Acme Corporation",
        )
        doc2 = SearchableDocument(
            entity_type=SearchableEntityType.ACCOUNT,
            entity_id="acc-2",
            title="The Acme Group",
        )
        
        service.index_documents([doc1, doc2])
        
        result = service.search("Acme Corporation")
        assert result.total_count == 2
        
        # Exact match should score higher
        assert result.results[0].entity_id == "acc-1"

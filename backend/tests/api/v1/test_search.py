"""
Tests for Search API endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uuid import uuid4

from sensei.api.v1.endpoints.search import router, get_service, _service
from sensei.services.core.search import (
    FullTextSearchService,
    SearchableEntityType,
    SearchableDocument,
    index_account,
    index_rfq,
    index_quote,
    index_task,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with search router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_service():
    """Clear the service before each test."""
    _service.clear_index()
    yield
    _service.clear_index()


# --------------------------------------------------------------------------
# Search Endpoint Tests
# --------------------------------------------------------------------------

class TestSearchEndpoint:
    """Tests for GET /search endpoint."""
    
    def test_search_empty_index(self, client: TestClient):
        """Test searching an empty index."""
        response = client.get("/search", params={"q": "test"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["total_count"] == 0
        assert data["results"] == []
    
    def test_search_with_results(self, client: TestClient):
        """Test searching with matching results."""
        service = get_service()
        index_account(service, "acc-1", "Acme Corporation", "Industrial equipment")
        index_account(service, "acc-2", "Beta Industries", "Software development")
        
        response = client.get("/search", params={"q": "Acme"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Acme Corporation"
    
    def test_search_pagination(self, client: TestClient):
        """Test search pagination."""
        service = get_service()
        for i in range(25):
            index_account(service, f"acc-{i}", f"Company {i}", f"Description {i}")
        
        response = client.get("/search", params={"q": "Company", "page": 1, "page_size": 10})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 25
        assert len(data["results"]) == 10
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["has_more"] is True
        
        # Get page 2
        response = client.get("/search", params={"q": "Company", "page": 2, "page_size": 10})
        data = response.json()
        assert len(data["results"]) == 10
        assert data["page"] == 2
    
    def test_search_filter_by_entity_type(self, client: TestClient):
        """Test filtering by entity type."""
        service = get_service()
        index_account(service, "acc-1", "Test Account", "Description")
        index_rfq(service, "rfq-1", "RFQ-001", "Test RFQ")
        
        response = client.get("/search", params={"q": "Test", "entity_types": "account"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["results"][0]["entity_type"] == "account"
    
    def test_search_filter_by_multiple_entity_types(self, client: TestClient):
        """Test filtering by multiple entity types."""
        service = get_service()
        index_account(service, "acc-1", "Test Account", "Description")
        index_rfq(service, "rfq-1", "RFQ-001", "Test RFQ")
        index_quote(service, "quote-1", "Q-001", "Test Quote")
        
        response = client.get("/search", params={"q": "Test", "entity_types": "account,rfq"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        entity_types = {r["entity_type"] for r in data["results"]}
        assert entity_types == {"account", "rfq"}
    
    def test_search_filter_by_status(self, client: TestClient):
        """Test filtering by status."""
        service = get_service()
        index_account(service, "acc-1", "Test Account 1", status="active")
        index_account(service, "acc-2", "Test Account 2", status="inactive")
        
        response = client.get("/search", params={"q": "Test", "status": "active"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["results"][0]["status"] == "active"
    
    def test_search_filter_by_owner(self, client: TestClient):
        """Test filtering by owner ID."""
        service = get_service()
        owner_id = uuid4()
        index_account(service, "acc-1", "Test Account 1", owner_id=owner_id)
        index_account(service, "acc-2", "Test Account 2", owner_id=uuid4())
        
        response = client.get("/search", params={"q": "Test", "owner_id": str(owner_id)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
    
    def test_search_sort_by_title(self, client: TestClient):
        """Test sorting by title."""
        service = get_service()
        index_account(service, "acc-1", "Zebra Corp")
        index_account(service, "acc-2", "Alpha Corp")
        index_account(service, "acc-3", "Beta Corp")
        
        response = client.get("/search", params={"q": "Corp", "sort_by": "name", "sort_order": "asc"})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert data["results"][0]["title"] == "Alpha Corp"
        assert data["results"][1]["title"] == "Beta Corp"
        assert data["results"][2]["title"] == "Zebra Corp"
    
    def test_search_invalid_entity_type(self, client: TestClient):
        """Test with invalid entity type."""
        response = client.get("/search", params={"q": "test", "entity_types": "invalid"})
        
        assert response.status_code == 400
        assert "Invalid entity type" in response.json()["detail"]
    
    def test_search_invalid_sort_field(self, client: TestClient):
        """Test with invalid sort field."""
        response = client.get("/search", params={"q": "test", "sort_by": "invalid"})
        
        assert response.status_code == 400
        assert "Invalid sort field" in response.json()["detail"]
    
    def test_search_response_includes_highlights(self, client: TestClient):
        """Test that response includes highlights."""
        service = get_service()
        index_account(service, "acc-1", "Acme Corporation", "Industrial equipment manufacturer")
        
        response = client.get("/search", params={"q": "Acme"})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert "title" in data["results"][0]["highlights"]


class TestQuickSearchEndpoint:
    """Tests for GET /search/quick endpoint."""
    
    def test_quick_search_empty(self, client: TestClient):
        """Test quick search on empty index."""
        response = client.get("/search/quick", params={"q": "test"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["results"] == []
    
    def test_quick_search_with_results(self, client: TestClient):
        """Test quick search with matching results."""
        service = get_service()
        index_account(service, "acc-1", "Acme Corporation")
        index_account(service, "acc-2", "Acme Industries")
        
        response = client.get("/search/quick", params={"q": "Acme"})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
    
    def test_quick_search_limit(self, client: TestClient):
        """Test quick search respects limit."""
        service = get_service()
        for i in range(20):
            index_account(service, f"acc-{i}", f"Test Company {i}")
        
        response = client.get("/search/quick", params={"q": "Test", "limit": 5})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 5
    
    def test_quick_search_filter_entity_types(self, client: TestClient):
        """Test quick search with entity type filter."""
        service = get_service()
        index_account(service, "acc-1", "Test Account")
        index_rfq(service, "rfq-1", "RFQ-001", "Test RFQ")
        
        response = client.get("/search/quick", params={"q": "Test", "entity_types": "rfq"})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["entity_type"] == "rfq"


class TestSuggestionsEndpoint:
    """Tests for GET /search/suggestions endpoint."""
    
    def test_suggestions_empty(self, client: TestClient):
        """Test suggestions on empty index."""
        response = client.get("/search/suggestions", params={"prefix": "te"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["prefix"] == "te"
        assert data["suggestions"] == []
    
    def test_suggestions_with_matches(self, client: TestClient):
        """Test suggestions with matching results."""
        service = get_service()
        index_account(service, "acc-1", "Testing Company", "Description of testing")
        index_account(service, "acc-2", "Technical Services", "Technical description")
        
        response = client.get("/search/suggestions", params={"prefix": "te"})
        
        assert response.status_code == 200
        data = response.json()
        # Should find words starting with "te"
        assert len(data["suggestions"]) > 0
    
    def test_suggestions_limit(self, client: TestClient):
        """Test suggestions respects limit."""
        service = get_service()
        for i in range(15):
            index_account(service, f"acc-{i}", f"Test{i} Company")
        
        response = client.get("/search/suggestions", params={"prefix": "test", "limit": 5})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) <= 5


class TestEntityTypesEndpoint:
    """Tests for GET /search/entity-types endpoint."""
    
    def test_list_entity_types(self, client: TestClient):
        """Test listing all entity types."""
        response = client.get("/search/entity-types")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        # Check structure
        for item in data:
            assert "value" in item
            assert "name" in item
        
        # Check some expected types
        values = [item["value"] for item in data]
        assert "account" in values
        assert "rfq" in values
        assert "quote" in values


class TestStatsEndpoint:
    """Tests for GET /search/stats endpoint."""
    
    def test_stats_empty_index(self, client: TestClient):
        """Test stats on empty index."""
        response = client.get("/search/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 0
        assert data["entity_counts"] == {}
        assert data["indexed_entity_types"] == []
    
    def test_stats_with_documents(self, client: TestClient):
        """Test stats with indexed documents."""
        service = get_service()
        index_account(service, "acc-1", "Test Account 1")
        index_account(service, "acc-2", "Test Account 2")
        index_rfq(service, "rfq-1", "RFQ-001", "Test RFQ")
        
        response = client.get("/search/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 3
        assert data["entity_counts"]["account"] == 2
        assert data["entity_counts"]["rfq"] == 1
        assert "account" in data["indexed_entity_types"]
        assert "rfq" in data["indexed_entity_types"]


# --------------------------------------------------------------------------
# Index Management Endpoint Tests
# --------------------------------------------------------------------------

class TestIndexDocumentEndpoint:
    """Tests for POST /search/index endpoint."""
    
    def test_index_document(self, client: TestClient):
        """Test indexing a document."""
        response = client.post("/search/index", json={
            "entity_type": "account",
            "entity_id": "acc-123",
            "title": "Test Account",
            "description": "Test description",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["indexed"] is True
        assert data["entity_type"] == "account"
        assert data["entity_id"] == "acc-123"
        
        # Verify it's searchable
        search_response = client.get("/search", params={"q": "Test Account"})
        assert search_response.status_code == 200
        assert search_response.json()["total_count"] == 1
    
    def test_index_document_with_all_fields(self, client: TestClient):
        """Test indexing with all fields."""
        owner_id = str(uuid4())
        account_id = str(uuid4())
        
        response = client.post("/search/index", json={
            "entity_type": "task",
            "entity_id": "task-123",
            "title": "Important Task",
            "identifier": "TASK-001",
            "description": "Task description",
            "tags": ["urgent", "priority"],
            "notes": "Some notes",
            "custom_fields": {"field1": "value1"},
            "status": "in_progress",
            "owner_id": owner_id,
            "account_id": account_id,
            "subtitle": "Subtitle text",
        })
        
        assert response.status_code == 201
    
    def test_index_document_invalid_entity_type(self, client: TestClient):
        """Test indexing with invalid entity type."""
        response = client.post("/search/index", json={
            "entity_type": "invalid",
            "entity_id": "test-123",
            "title": "Test",
        })
        
        assert response.status_code == 400
        assert "Invalid entity type" in response.json()["detail"]


class TestIndexAccountEndpoint:
    """Tests for POST /search/index/account endpoint."""
    
    def test_index_account(self, client: TestClient):
        """Test indexing an account."""
        response = client.post("/search/index/account", json={
            "account_id": "acc-456",
            "name": "Acme Corp",
            "description": "Manufacturing company",
            "industry": "Manufacturing",
            "status": "active",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["indexed"] is True
        assert data["entity_type"] == "account"
        assert data["entity_id"] == "acc-456"


class TestIndexRFQEndpoint:
    """Tests for POST /search/index/rfq endpoint."""
    
    def test_index_rfq(self, client: TestClient):
        """Test indexing an RFQ."""
        response = client.post("/search/index/rfq", json={
            "rfq_id": "rfq-789",
            "rfq_number": "RFQ-2024-001",
            "title": "New RFQ",
            "description": "RFQ description",
            "status": "open",
            "account_name": "Acme Corp",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["indexed"] is True
        assert data["entity_type"] == "rfq"


class TestIndexQuoteEndpoint:
    """Tests for POST /search/index/quote endpoint."""
    
    def test_index_quote(self, client: TestClient):
        """Test indexing a quote."""
        response = client.post("/search/index/quote", json={
            "quote_id": "quote-123",
            "quote_number": "Q-2024-001",
            "title": "New Quote",
            "description": "Quote description",
            "status": "draft",
            "total_value": 10000.00,
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["indexed"] is True
        assert data["entity_type"] == "quote"


class TestIndexTaskEndpoint:
    """Tests for POST /search/index/task endpoint."""
    
    def test_index_task(self, client: TestClient):
        """Test indexing a task."""
        response = client.post("/search/index/task", json={
            "task_id": "task-456",
            "title": "Complete Documentation",
            "description": "Write documentation for the API",
            "status": "pending",
            "assignee_name": "John Doe",
            "due_date": "2024-01-15T10:00:00Z",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["indexed"] is True
        assert data["entity_type"] == "task"


class TestRemoveDocumentEndpoint:
    """Tests for DELETE /search/index/{entity_type}/{entity_id} endpoint."""
    
    def test_remove_document(self, client: TestClient):
        """Test removing a document."""
        service = get_service()
        index_account(service, "acc-to-remove", "Account to Remove")
        
        response = client.delete("/search/index/account/acc-to-remove")
        
        assert response.status_code == 200
        data = response.json()
        assert data["removed"] is True
        
        # Verify it's no longer searchable
        search_response = client.get("/search", params={"q": "Account to Remove"})
        assert search_response.json()["total_count"] == 0
    
    def test_remove_nonexistent_document(self, client: TestClient):
        """Test removing a document that doesn't exist."""
        response = client.delete("/search/index/account/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_remove_document_invalid_entity_type(self, client: TestClient):
        """Test removing with invalid entity type."""
        response = client.delete("/search/index/invalid/some-id")
        
        assert response.status_code == 400
        assert "Invalid entity type" in response.json()["detail"]


class TestClearIndexEndpoint:
    """Tests for DELETE /search/index/clear endpoint."""
    
    def test_clear_all(self, client: TestClient):
        """Test clearing entire index."""
        service = get_service()
        index_account(service, "acc-1", "Account 1")
        index_rfq(service, "rfq-1", "RFQ-001", "RFQ 1")
        
        response = client.delete("/search/index/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cleared"] is True
        assert data["documents_removed"] == 2
        
        # Verify index is empty
        stats_response = client.get("/search/stats")
        assert stats_response.json()["total_documents"] == 0
    
    def test_clear_by_entity_type(self, client: TestClient):
        """Test clearing only one entity type."""
        service = get_service()
        index_account(service, "acc-1", "Account 1")
        index_account(service, "acc-2", "Account 2")
        index_rfq(service, "rfq-1", "RFQ-001", "RFQ 1")
        
        response = client.delete("/search/index/clear", params={"entity_type": "account"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["cleared"] is True
        assert data["entity_type"] == "account"
        assert data["documents_removed"] == 2
        
        # Verify RFQs still exist
        stats_response = client.get("/search/stats")
        stats = stats_response.json()
        assert stats["total_documents"] == 1
        assert "rfq" in stats["indexed_entity_types"]
    
    def test_clear_invalid_entity_type(self, client: TestClient):
        """Test clearing with invalid entity type."""
        response = client.delete("/search/index/clear", params={"entity_type": "invalid"})
        
        assert response.status_code == 400
        assert "Invalid entity type" in response.json()["detail"]


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestSearchIntegration:
    """Integration tests for search workflow."""
    
    def test_full_search_workflow(self, client: TestClient):
        """Test complete search workflow."""
        # 1. Index some documents via API
        client.post("/search/index/account", json={
            "account_id": "acc-1",
            "name": "Acme Manufacturing",
            "description": "Industrial equipment manufacturer",
            "industry": "Manufacturing",
            "status": "active",
        })
        
        client.post("/search/index/rfq", json={
            "rfq_id": "rfq-1",
            "rfq_number": "RFQ-2024-001",
            "title": "Acme Equipment Order",
            "description": "Large equipment order",
            "status": "open",
            "account_name": "Acme Manufacturing",
        })
        
        # 2. Check stats
        stats = client.get("/search/stats").json()
        assert stats["total_documents"] == 2
        
        # 3. Search for Acme
        results = client.get("/search", params={"q": "Acme"}).json()
        assert results["total_count"] == 2
        
        # 4. Filter by entity type
        filtered = client.get("/search", params={"q": "Acme", "entity_types": "account"}).json()
        assert filtered["total_count"] == 1
        assert filtered["results"][0]["entity_type"] == "account"
        
        # 5. Quick search
        quick = client.get("/search/quick", params={"q": "Acme", "limit": 5}).json()
        assert len(quick["results"]) == 2
        
        # 6. Get suggestions
        suggestions = client.get("/search/suggestions", params={"prefix": "acm"}).json()
        assert "acme" in [s.lower() for s in suggestions["suggestions"]]
        
        # 7. Remove one document
        client.delete("/search/index/rfq/rfq-1")
        
        # 8. Verify removal
        final_stats = client.get("/search/stats").json()
        assert final_stats["total_documents"] == 1
    
    def test_search_across_entity_types(self, client: TestClient):
        """Test searching across multiple entity types."""
        service = get_service()
        
        # Index various entities
        index_account(service, "acc-1", "Universal Corp", "Universal solutions")
        index_rfq(service, "rfq-1", "RFQ-UNIV-001", "Universal RFQ")
        index_quote(service, "q-1", "Q-UNIV-001", "Universal Quote")
        index_task(service, "task-1", "Universal Task Review", "Review universal components")
        
        # Search for "Universal"
        response = client.get("/search", params={"q": "Universal"})
        data = response.json()
        
        assert data["total_count"] == 4
        
        # Check entity counts
        assert "account" in data["entity_counts"]
        assert "rfq" in data["entity_counts"]
        assert "quote" in data["entity_counts"]
        assert "task" in data["entity_counts"]
    
    def test_fuzzy_search_via_api(self, client: TestClient):
        """Test fuzzy matching through API."""
        service = get_service()
        index_account(service, "acc-1", "Manufacturing Solutions")
        
        # Search with typo
        response = client.get("/search", params={"q": "Manufactring", "fuzzy": True})
        data = response.json()
        
        assert data["total_count"] == 1
        assert data["results"][0]["title"] == "Manufacturing Solutions"
    
    def test_search_with_special_characters(self, client: TestClient):
        """Test searching with special characters."""
        service = get_service()
        index_account(service, "acc-1", "C++ Development Services")
        index_account(service, "acc-2", "C# Solutions Inc.")
        
        # Search for C++
        response = client.get("/search", params={"q": "C++"})
        data = response.json()
        
        # Should handle gracefully
        assert response.status_code == 200

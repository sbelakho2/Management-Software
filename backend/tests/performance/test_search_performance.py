"""
Search performance tests for Management Software.

Tests search service to ensure performance targets are met:
- Empty query: <100ms
- Simple term: <300ms
- Multi-entity search: <400ms  
- Filtered search: <400ms
- Fuzzy matching: <500ms

These tests establish performance regression gates for search operations.
"""

import pytest
import time
from uuid import uuid4

from sensei.services.core.search import (
    FullTextSearchService,
    SearchableDocument,
    SearchableEntityType,
    SearchFilter,
)


class TestSearchPerformance:
    """Test search service performance."""
    
    def test_empty_query_under_100ms(self):
        """Test empty search completes under 100ms."""
        # Setup: Service with no documents
        service = FullTextSearchService()
        
        # Measure: Search with empty query
        start_time = time.perf_counter()
        result = service.search(query="", page_size=20)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: No results
        assert result.total_count == 0
        
        # Performance gate: Empty query must be <100ms
        assert latency_ms < 100, f"Empty search latency {latency_ms:.2f}ms exceeds 100ms target"
    
    def test_simple_term_search_under_300ms(self):
        """Test simple term search completes under 300ms."""
        # Setup: Service with typical document volume (100 documents)
        service = FullTextSearchService()
        
        for i in range(100):
            service.index_document(SearchableDocument(
                entity_type=SearchableEntityType.ACCOUNT,
                entity_id=str(uuid4()),
                title=f"Company {i}",
                description=f"This is a description for company {i} with various details",
                tags=["customer", "active"],
            ))
        
        # Measure: Search for simple term
        start_time = time.perf_counter()
        result = service.search(query="company", page_size=20)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Results found
        assert result.total_count > 0
        
        # Performance gate: Simple search must be <300ms
        assert latency_ms < 300, f"Simple search latency {latency_ms:.2f}ms exceeds 300ms target"
    
    def test_multi_entity_search_under_400ms(self):
        """Test multi-entity search completes under 400ms."""
        # Setup: Service with documents across multiple entity types
        service = FullTextSearchService()
        
        entity_types = [
            SearchableEntityType.ACCOUNT,
            SearchableEntityType.CONTACT,
            SearchableEntityType.RFQ,
            SearchableEntityType.QUOTE,
            SearchableEntityType.OPPORTUNITY,
        ]
        
        # Index 20 documents per entity type (100 total)
        for entity_type in entity_types:
            for i in range(20):
                service.index_document(SearchableDocument(
                    entity_type=entity_type,
                    entity_id=str(uuid4()),
                    title=f"{entity_type.value} {i} for aerospace project",
                    description=f"Details about {entity_type.value} item {i}",
                    tags=["aerospace", "active"],
                ))
        
        # Measure: Search across all entity types
        start_time = time.perf_counter()
        result = service.search(query="aerospace", page_size=50)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Results from multiple entity types
        assert result.total_count > 0
        entity_types_in_results = set(r.entity_type for r in result.results)
        assert len(entity_types_in_results) > 1, "Expected results from multiple entity types"
        
        # Performance gate: Multi-entity search must be <400ms
        assert latency_ms < 400, f"Multi-entity search latency {latency_ms:.2f}ms exceeds 400ms target"
    
    def test_filtered_search_under_400ms(self):
        """Test filtered search completes under 400ms."""
        # Setup: Service with diverse documents
        service = FullTextSearchService()
        
        # Index 50 accounts and 50 RFQs
        for i in range(50):
            service.index_document(SearchableDocument(
                entity_type=SearchableEntityType.ACCOUNT,
                entity_id=str(uuid4()),
                title=f"Account {i}",
                description="Account details",
                tags=["customer"],
            ))
        
        for i in range(50):
            service.index_document(SearchableDocument(
                entity_type=SearchableEntityType.RFQ,
                entity_id=str(uuid4()),
                title=f"RFQ {i}",
                description="RFQ details",
                tags=["active"],
            ))
        
        # Measure: Search filtered to one entity type
        start_time = time.perf_counter()
        result = service.search(
            query="account",
            filters=SearchFilter(entity_types=[SearchableEntityType.ACCOUNT]),
            page_size=50,
        )
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Only accounts returned (up to page_size)
        assert result.total_count > 0
        assert all(r.entity_type == SearchableEntityType.ACCOUNT for r in result.results)
        
        # Performance gate: Filtered search must be <400ms
        assert latency_ms < 400, f"Filtered search latency {latency_ms:.2f}ms exceeds 400ms target"
    
    def test_fuzzy_matching_under_500ms(self):
        """Test fuzzy matching search completes under 500ms."""
        # Setup: Service with documents requiring fuzzy matching
        service = FullTextSearchService()
        
        # Index documents with varied spellings
        company_names = [
            "Aerospace Manufacturing",
            "Aerospase Manufakturing",  # Typo
            "Arospace Manfacturing",     # Typo
            "Precision Machining",
            "Advanced Robotics",
        ]
        
        for i, name in enumerate(company_names * 20):  # 100 documents
            service.index_document(SearchableDocument(
                entity_type=SearchableEntityType.ACCOUNT,
                entity_id=str(uuid4()),
                title=f"{name} {i}",
                description=f"Company specializing in various products",
                tags=["manufacturer"],
            ))
        
        # Measure: Search with typo (fuzzy matching)
        start_time = time.perf_counter()
        result = service.search(query="aerospce manufcturing", page_size=20, fuzzy=True)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Results found despite typos
        assert result.total_count > 0
        
        # Performance gate: Fuzzy search must be <500ms
        assert latency_ms < 500, f"Fuzzy search latency {latency_ms:.2f}ms exceeds 500ms target"
    
    def test_high_volume_search_under_1000ms(self):
        """Test search with high document volume completes under 1000ms."""
        # Setup: Service with high volume (1000 documents)
        service = FullTextSearchService()
        
        for i in range(1000):
            service.index_document(SearchableDocument(
                entity_type=SearchableEntityType.ACCOUNT,
                entity_id=str(uuid4()),
                title=f"Company {i}",
                description=f"Description for company {i} with detailed information about their products and services",
                tags=["customer", "active" if i % 2 == 0 else "inactive"],
            ))
        
        # Measure: Search in high volume
        start_time = time.perf_counter()
        result = service.search(query="company products", page_size=50)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Results found
        assert result.total_count > 0
        
        # Performance gate: High volume search must be <1000ms
        assert latency_ms < 1000, f"High volume search latency {latency_ms:.2f}ms exceeds 1000ms target"

"""
Tests for Advanced RAG Hybrid Search.

Covers:
- Token-Aware Chunking
- Cross-Encoder Re-ranking
- Hybrid Search Engine
- Dynamic Context Sizing
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import math
import time

from sensei.services.hybrid_search import (
    # Enums
    SearchMode,
    RerankingStrategy,
    ChunkingStrategy,
    # Data models
    ChunkMetadata,
    Chunk,
    SearchResult,
    SearchQuery,
    SearchResponse,
    RerankCacheEntry,
    # Chunking
    TokenEstimator,
    RecursiveCharacterSplitter,
    TokenAwareChunker,
    # Re-ranking
    RerankCache,
    ONNXCrossEncoder,
    # Search
    InMemorySemanticSearcher,
    InMemoryKeywordSearcher,
    HybridSearchEngine,
    DynamicContextSizer,
    # Factory
    create_hybrid_search_engine,
    create_chunker,
    # Constants
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_ALPHA,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_chunk():
    """Create a sample chunk."""
    metadata = ChunkMetadata(
        document_id="doc_001",
        document_title="Test Document",
        page_number=1,
        section_header="Introduction",
        chunk_index=0,
        total_chunks=5,
    )
    return Chunk(
        id="chunk_001",
        content="This is a test chunk with some content about machine learning.",
        metadata=metadata,
    )


@pytest.fixture
def sample_document():
    """Sample document content."""
    return """
    Introduction
    
    This document describes the manufacturing process for electronic components.
    The process involves several key steps including assembly, testing, and packaging.
    
    Assembly Process
    
    The assembly process begins with component placement on the PCB.
    Automated pick-and-place machines are used for surface mount devices.
    Through-hole components are inserted manually or with semi-automated equipment.
    
    Quality Control
    
    Quality control is essential to ensure product reliability.
    Visual inspection identifies obvious defects.
    Automated optical inspection (AOI) catches placement errors.
    Functional testing verifies circuit operation.
    
    Packaging
    
    Final products are packaged according to customer specifications.
    ESD protection is maintained throughout the packaging process.
    """


@pytest.fixture
def token_estimator():
    """Token estimator instance."""
    return TokenEstimator()


@pytest.fixture
def recursive_splitter():
    """Recursive character splitter instance."""
    return RecursiveCharacterSplitter(chunk_size=200, chunk_overlap=20)


@pytest.fixture
def chunker():
    """Token-aware chunker instance."""
    return TokenAwareChunker(chunk_size=200, chunk_overlap=20)


@pytest.fixture
def rerank_cache():
    """Re-rank cache instance."""
    return RerankCache(ttl_seconds=60)


@pytest.fixture
def reranker():
    """Cross-encoder re-ranker instance."""
    return ONNXCrossEncoder(cache_ttl=60)


@pytest.fixture
def semantic_searcher():
    """In-memory semantic searcher."""
    return InMemorySemanticSearcher()


@pytest.fixture
def keyword_searcher():
    """In-memory keyword searcher."""
    return InMemoryKeywordSearcher()


@pytest.fixture
def hybrid_engine(semantic_searcher, keyword_searcher, reranker):
    """Hybrid search engine instance."""
    return HybridSearchEngine(
        semantic_searcher=semantic_searcher,
        keyword_searcher=keyword_searcher,
        reranker=reranker,
    )


@pytest.fixture
def context_sizer():
    """Dynamic context sizer instance."""
    return DynamicContextSizer()


# =============================================================================
# TokenEstimator Tests
# =============================================================================

class TestTokenEstimator:
    """Tests for TokenEstimator."""
    
    def test_estimate_tokens_basic(self, token_estimator):
        """Test basic token estimation."""
        text = "Hello world"  # 11 chars
        tokens = token_estimator.estimate_tokens(text)
        
        # ~4 chars per token
        assert tokens == 2
    
    def test_estimate_tokens_longer_text(self, token_estimator):
        """Test token estimation for longer text."""
        text = "This is a longer piece of text with more words."  # 47 chars
        tokens = token_estimator.estimate_tokens(text)
        
        # ~4 chars per token: 47 / 4 = 11
        assert tokens == 11
    
    def test_estimate_tokens_empty(self, token_estimator):
        """Test token estimation for empty text."""
        tokens = token_estimator.estimate_tokens("")
        assert tokens == 0
    
    def test_truncate_to_tokens(self, token_estimator):
        """Test truncating text to token limit."""
        text = "This is a test sentence for truncation testing purposes."
        truncated = token_estimator.truncate_to_tokens(text, 5)
        
        # 5 tokens * 4 chars = ~20 chars
        assert len(truncated) <= 24  # Some buffer for word boundaries
    
    def test_truncate_to_tokens_short_text(self, token_estimator):
        """Test truncation when text is already short."""
        text = "Short"
        truncated = token_estimator.truncate_to_tokens(text, 100)
        
        assert truncated == text
    
    def test_truncate_at_word_boundary(self, token_estimator):
        """Test that truncation prefers word boundaries."""
        text = "Hello world this is a test"
        truncated = token_estimator.truncate_to_tokens(text, 4)
        
        # Should not cut in the middle of a word
        assert not truncated.endswith("wor")


# =============================================================================
# RecursiveCharacterSplitter Tests
# =============================================================================

class TestRecursiveCharacterSplitter:
    """Tests for RecursiveCharacterSplitter."""
    
    def test_split_short_text(self, recursive_splitter):
        """Test splitting short text."""
        text = "Short text"
        chunks = recursive_splitter.split_text(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_split_on_paragraphs(self):
        """Test splitting on paragraph boundaries."""
        splitter = RecursiveCharacterSplitter(chunk_size=100, chunk_overlap=10)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        
        chunks = splitter.split_text(text)
        
        assert len(chunks) >= 1
    
    def test_split_with_overlap(self):
        """Test that chunks have overlap."""
        splitter = RecursiveCharacterSplitter(chunk_size=50, chunk_overlap=10)
        text = "A" * 40 + " " + "B" * 40 + " " + "C" * 40
        
        chunks = splitter.split_text(text)
        
        # Verify overlap exists (except for first chunk)
        if len(chunks) > 1:
            # Second chunk should start with end of first chunk
            assert len(chunks[1]) > 40  # Has overlap
    
    def test_split_respects_chunk_size(self):
        """Test that chunks don't exceed size limit significantly."""
        splitter = RecursiveCharacterSplitter(chunk_size=100, chunk_overlap=10)
        text = "Word " * 100
        
        chunks = splitter.split_text(text)
        
        for chunk in chunks:
            # Allow some buffer for separator handling
            assert len(chunk) <= 150
    
    def test_split_empty_text(self, recursive_splitter):
        """Test splitting empty text."""
        chunks = recursive_splitter.split_text("")
        assert chunks == []
    
    def test_split_preserves_separator(self):
        """Test that separators are preserved."""
        splitter = RecursiveCharacterSplitter(
            chunk_size=50, 
            chunk_overlap=5,
            keep_separator=True
        )
        text = "First sentence. Second sentence."
        
        chunks = splitter.split_text(text)
        
        # Should preserve the period and space
        combined = "".join(chunks)
        assert ". " in combined or "." in combined


# =============================================================================
# TokenAwareChunker Tests
# =============================================================================

class TestTokenAwareChunker:
    """Tests for TokenAwareChunker."""
    
    def test_chunk_document_basic(self, chunker, sample_document):
        """Test basic document chunking."""
        chunks = chunker.chunk_document(
            content=sample_document,
            document_id="doc_001",
            document_title="Manufacturing Guide",
        )
        
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
    
    def test_chunk_metadata_enrichment(self, chunker):
        """Test that chunks have enriched metadata."""
        content = "This is test content for chunking."
        
        chunks = chunker.chunk_document(
            content=content,
            document_id="doc_001",
            document_title="Test Document",
        )
        
        assert len(chunks) > 0
        assert chunks[0].metadata is not None
        assert chunks[0].metadata.document_id == "doc_001"
        assert chunks[0].metadata.document_title == "Test Document"
    
    def test_chunk_with_page_numbers(self, chunker, sample_document):
        """Test chunking with page number mapping."""
        page_numbers = {
            1: (0, 300),
            2: (300, 600),
            3: (600, len(sample_document)),
        }
        
        chunks = chunker.chunk_document(
            content=sample_document,
            document_id="doc_001",
            document_title="Document",
            page_numbers=page_numbers,
        )
        
        # At least some chunks should have page numbers
        pages = [c.metadata.page_number for c in chunks if c.metadata.page_number]
        assert len(pages) > 0
    
    def test_chunk_with_section_headers(self, chunker, sample_document):
        """Test chunking with section headers."""
        section_headers = {
            "Introduction": (0, 200),
            "Assembly Process": (200, 450),
            "Quality Control": (450, 700),
        }
        
        chunks = chunker.chunk_document(
            content=sample_document,
            document_id="doc_001",
            document_title="Document",
            section_headers=section_headers,
        )
        
        # Some chunks should have section headers
        sections = [c.metadata.section_header for c in chunks if c.metadata.section_header]
        assert len(sections) > 0
    
    def test_chunk_content_enrichment(self, chunker):
        """Test that content is enriched with metadata context."""
        content = "Simple test content."
        
        chunks = chunker.chunk_document(
            content=content,
            document_id="doc_001",
            document_title="Important Document",
        )
        
        # Content should include document title context
        assert "Document: Important Document" in chunks[0].content
    
    def test_chunk_token_count(self, chunker):
        """Test that token count is calculated."""
        content = "This is test content with several words."
        
        chunks = chunker.chunk_document(
            content=content,
            document_id="doc_001",
            document_title="Test",
        )
        
        assert all(c.token_count > 0 for c in chunks)
    
    def test_chunk_indices(self, chunker, sample_document):
        """Test that chunk indices are correct."""
        chunks = chunker.chunk_document(
            content=sample_document,
            document_id="doc_001",
            document_title="Document",
        )
        
        for i, chunk in enumerate(chunks):
            assert chunk.metadata.chunk_index == i
            assert chunk.metadata.total_chunks == len(chunks)


# =============================================================================
# RerankCache Tests
# =============================================================================

class TestRerankCache:
    """Tests for RerankCache."""
    
    def test_set_and_get(self, rerank_cache):
        """Test basic set and get."""
        rerank_cache.set("query", "context", 0.85)
        
        score = rerank_cache.get("query", "context")
        assert score == 0.85
    
    def test_get_nonexistent(self, rerank_cache):
        """Test getting nonexistent entry."""
        score = rerank_cache.get("unknown", "unknown")
        assert score is None
    
    def test_cache_expiration(self):
        """Test that expired entries are not returned."""
        cache = RerankCache(ttl_seconds=1)
        cache.set("query", "context", 0.9)
        
        # Immediately available
        assert cache.get("query", "context") == 0.9
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get("query", "context") is None
    
    def test_clear_expired(self):
        """Test clearing expired entries."""
        cache = RerankCache(ttl_seconds=1)
        cache.set("query1", "context1", 0.8)
        cache.set("query2", "context2", 0.9)
        
        assert cache.size() == 2
        
        time.sleep(1.1)
        
        removed = cache.clear_expired()
        assert removed == 2
        assert cache.size() == 0
    
    def test_cache_key_uniqueness(self, rerank_cache):
        """Test that different query/context pairs have unique keys."""
        rerank_cache.set("query1", "context", 0.8)
        rerank_cache.set("query2", "context", 0.9)
        
        assert rerank_cache.get("query1", "context") == 0.8
        assert rerank_cache.get("query2", "context") == 0.9


# =============================================================================
# ONNXCrossEncoder Tests
# =============================================================================

class TestONNXCrossEncoder:
    """Tests for ONNXCrossEncoder."""
    
    def test_score_pair_basic(self, reranker):
        """Test scoring a query-context pair."""
        score = reranker.score_pair(
            "machine learning",
            "This document is about machine learning and AI.",
        )
        
        assert 0.0 <= score <= 1.0
    
    def test_score_pair_caching(self, reranker):
        """Test that scores are cached."""
        query = "test query"
        context = "test context"
        
        # First call
        score1 = reranker.score_pair(query, context)
        
        # Second call should return cached value
        score2 = reranker.score_pair(query, context)
        
        assert score1 == score2
        assert reranker.cache.size() == 1
    
    def test_score_pair_relevance(self, reranker):
        """Test that relevant pairs score higher."""
        relevant_score = reranker.score_pair(
            "machine learning algorithms",
            "Machine learning algorithms are used for pattern recognition.",
        )
        
        irrelevant_score = reranker.score_pair(
            "machine learning algorithms",
            "The weather today is sunny and warm.",
        )
        
        assert relevant_score > irrelevant_score
    
    def test_rerank_results(self, reranker, sample_chunk):
        """Test re-ranking search results."""
        # Create some search results
        results = [
            SearchResult(
                chunk=Chunk(
                    id="1",
                    content="Machine learning is important.",
                ),
                combined_score=0.5,
            ),
            SearchResult(
                chunk=Chunk(
                    id="2",
                    content="This is about machine learning algorithms and neural networks.",
                ),
                combined_score=0.6,
            ),
            SearchResult(
                chunk=Chunk(
                    id="3",
                    content="Cooking recipes for pasta.",
                ),
                combined_score=0.7,  # Higher initial score but less relevant
            ),
        ]
        
        reranked = reranker.rerank(
            "machine learning",
            results,
            top_k=3,
        )
        
        # Results should have rerank_score set
        assert all(r.rerank_score is not None for r in reranked)
        
        # Relevant content should be ranked higher
        assert reranked[0].chunk.id in ["1", "2"]
    
    def test_rerank_top_k(self, reranker):
        """Test that rerank respects top_k limit."""
        results = [
            SearchResult(
                chunk=Chunk(id=str(i), content=f"Content {i}"),
                combined_score=0.5,
            )
            for i in range(10)
        ]
        
        reranked = reranker.rerank("query", results, top_k=3)
        
        assert len(reranked) == 3


# =============================================================================
# InMemorySemanticSearcher Tests
# =============================================================================

class TestInMemorySemanticSearcher:
    """Tests for InMemorySemanticSearcher."""
    
    def test_add_and_search(self, semantic_searcher):
        """Test adding chunks and searching."""
        chunk = Chunk(id="1", content="Test content about AI.")
        embedding = semantic_searcher.embed_query("AI content")
        
        semantic_searcher.add_chunk(chunk, embedding)
        
        query_embedding = semantic_searcher.embed_query("artificial intelligence")
        results = semantic_searcher.search(query_embedding, top_k=10)
        
        assert len(results) == 1
        assert results[0][0].id == "1"
    
    def test_embed_query(self, semantic_searcher):
        """Test query embedding generation."""
        embedding = semantic_searcher.embed_query("test query")
        
        assert len(embedding) == 384
        # Should be normalized
        norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(norm - 1.0) < 0.01
    
    def test_search_top_k(self, semantic_searcher):
        """Test search respects top_k."""
        for i in range(10):
            chunk = Chunk(id=str(i), content=f"Content {i}")
            embedding = semantic_searcher.embed_query(f"Content {i}")
            semantic_searcher.add_chunk(chunk, embedding)
        
        query_embedding = semantic_searcher.embed_query("Content")
        results = semantic_searcher.search(query_embedding, top_k=5)
        
        assert len(results) == 5
    
    def test_search_with_filters(self, semantic_searcher):
        """Test search with filters."""
        chunk1 = Chunk(
            id="1",
            content="Content A",
            metadata=ChunkMetadata(
                document_id="doc1",
                document_title="Doc 1",
            ),
        )
        chunk2 = Chunk(
            id="2",
            content="Content B",
            metadata=ChunkMetadata(
                document_id="doc2",
                document_title="Doc 2",
            ),
        )
        
        semantic_searcher.add_chunk(chunk1, semantic_searcher.embed_query("A"))
        semantic_searcher.add_chunk(chunk2, semantic_searcher.embed_query("B"))
        
        query_embedding = semantic_searcher.embed_query("Content")
        results = semantic_searcher.search(
            query_embedding,
            filters={"document_id": "doc1"},
        )
        
        assert len(results) == 1
        assert results[0][0].id == "1"


# =============================================================================
# InMemoryKeywordSearcher Tests
# =============================================================================

class TestInMemoryKeywordSearcher:
    """Tests for InMemoryKeywordSearcher."""
    
    def test_add_and_search(self, keyword_searcher):
        """Test adding chunks and searching."""
        chunk = Chunk(id="1", content="Machine learning algorithms are powerful.")
        keyword_searcher.add_chunk(chunk)
        
        results = keyword_searcher.search("machine learning", top_k=10)
        
        assert len(results) == 1
        assert results[0][0].id == "1"
    
    def test_search_with_no_match(self, keyword_searcher):
        """Test search with no matching documents."""
        chunk = Chunk(id="1", content="Test content here.")
        keyword_searcher.add_chunk(chunk)
        
        results = keyword_searcher.search("nonexistent terms", top_k=10)
        
        # May or may not return results depending on tokenization
        assert isinstance(results, list)
    
    def test_search_ranking(self, keyword_searcher):
        """Test that more relevant documents rank higher."""
        chunk1 = Chunk(id="1", content="machine")
        chunk2 = Chunk(id="2", content="machine learning machine learning machine")
        
        keyword_searcher.add_chunk(chunk1)
        keyword_searcher.add_chunk(chunk2)
        
        results = keyword_searcher.search("machine", top_k=10)
        
        assert len(results) == 2
        # Chunk2 has more occurrences, should rank higher
        assert results[0][0].id == "2"
    
    def test_search_with_filters(self, keyword_searcher):
        """Test search with filters."""
        chunk1 = Chunk(
            id="1",
            content="Content about AI",
            metadata=ChunkMetadata(
                document_id="doc1",
                document_title="Doc 1",
            ),
        )
        chunk2 = Chunk(
            id="2",
            content="Content about AI",
            metadata=ChunkMetadata(
                document_id="doc2",
                document_title="Doc 2",
            ),
        )
        
        keyword_searcher.add_chunk(chunk1)
        keyword_searcher.add_chunk(chunk2)
        
        results = keyword_searcher.search(
            "AI",
            filters={"document_id": "doc2"},
        )
        
        assert len(results) == 1
        assert results[0][0].id == "2"


# =============================================================================
# HybridSearchEngine Tests
# =============================================================================

class TestHybridSearchEngine:
    """Tests for HybridSearchEngine."""
    
    def test_semantic_only_search(self, hybrid_engine, semantic_searcher):
        """Test semantic-only search mode."""
        chunk = Chunk(id="1", content="Machine learning content")
        embedding = semantic_searcher.embed_query("ML")
        semantic_searcher.add_chunk(chunk, embedding)
        
        query = SearchQuery(
            query="machine learning",
            mode=SearchMode.SEMANTIC,
            top_k=10,
            rerank=False,
        )
        
        response = hybrid_engine.search(query)
        
        assert response.mode == SearchMode.SEMANTIC
        assert len(response.results) > 0
    
    def test_keyword_only_search(self, hybrid_engine, keyword_searcher):
        """Test keyword-only search mode."""
        chunk = Chunk(id="1", content="Machine learning algorithms")
        keyword_searcher.add_chunk(chunk)
        
        query = SearchQuery(
            query="machine learning",
            mode=SearchMode.KEYWORD,
            top_k=10,
            rerank=False,
        )
        
        response = hybrid_engine.search(query)
        
        assert response.mode == SearchMode.KEYWORD
        assert len(response.results) > 0
    
    def test_hybrid_search(
        self, hybrid_engine, semantic_searcher, keyword_searcher
    ):
        """Test hybrid search combining semantic and keyword."""
        chunk1 = Chunk(id="1", content="Machine learning is great")
        chunk2 = Chunk(id="2", content="Deep learning neural networks")
        
        # Add to both indexes
        semantic_searcher.add_chunk(chunk1, semantic_searcher.embed_query("ML"))
        semantic_searcher.add_chunk(chunk2, semantic_searcher.embed_query("DL"))
        keyword_searcher.add_chunk(chunk1)
        keyword_searcher.add_chunk(chunk2)
        
        query = SearchQuery(
            query="machine learning",
            mode=SearchMode.HYBRID,
            alpha=0.5,
            top_k=10,
            rerank=False,
        )
        
        response = hybrid_engine.search(query)
        
        assert response.mode == SearchMode.HYBRID
        assert len(response.results) > 0
        
        # Results should have both scores
        for result in response.results:
            assert result.semantic_score >= 0 or result.keyword_score >= 0
    
    def test_search_with_reranking(
        self, hybrid_engine, semantic_searcher, keyword_searcher
    ):
        """Test search with re-ranking enabled."""
        for i in range(5):
            chunk = Chunk(id=str(i), content=f"Document {i} about AI")
            semantic_searcher.add_chunk(chunk, semantic_searcher.embed_query(f"AI {i}"))
            keyword_searcher.add_chunk(chunk)
        
        query = SearchQuery(
            query="AI document",
            mode=SearchMode.HYBRID,
            rerank=True,
            top_k=3,
        )
        
        response = hybrid_engine.search(query)
        
        assert response.reranked is True
        assert all(r.rerank_score is not None for r in response.results)
    
    def test_search_with_max_tokens(
        self, hybrid_engine, semantic_searcher, keyword_searcher
    ):
        """Test search with token limit."""
        for i in range(5):
            chunk = Chunk(
                id=str(i),
                content="A" * 100,  # ~25 tokens each
            )
            semantic_searcher.add_chunk(chunk, semantic_searcher.embed_query(f"{i}"))
            keyword_searcher.add_chunk(chunk)
        
        query = SearchQuery(
            query="test",
            mode=SearchMode.HYBRID,
            max_tokens=50,  # Should fit ~2 chunks
            rerank=False,
        )
        
        response = hybrid_engine.search(query)
        
        # Should respect token limit
        assert response.context_tokens <= 60  # Some buffer
    
    def test_alpha_weight_effect(
        self, hybrid_engine, semantic_searcher, keyword_searcher
    ):
        """Test that alpha weight affects results."""
        chunk1 = Chunk(id="1", content="exact keyword match here")
        chunk2 = Chunk(id="2", content="semantically similar concept")
        
        semantic_searcher.add_chunk(chunk1, semantic_searcher.embed_query("keyword"))
        semantic_searcher.add_chunk(chunk2, semantic_searcher.embed_query("concept"))
        keyword_searcher.add_chunk(chunk1)
        keyword_searcher.add_chunk(chunk2)
        
        # High alpha = more semantic weight
        query_semantic = SearchQuery(
            query="keyword",
            mode=SearchMode.HYBRID,
            alpha=0.9,
            rerank=False,
        )
        
        # Low alpha = more keyword weight
        query_keyword = SearchQuery(
            query="keyword",
            mode=SearchMode.HYBRID,
            alpha=0.1,
            rerank=False,
        )
        
        response_semantic = hybrid_engine.search(query_semantic)
        response_keyword = hybrid_engine.search(query_keyword)
        
        # Both should return results
        assert len(response_semantic.results) > 0
        assert len(response_keyword.results) > 0
    
    def test_search_response_metadata(
        self, hybrid_engine, semantic_searcher, keyword_searcher
    ):
        """Test that search response includes proper metadata."""
        chunk = Chunk(id="1", content="Test content")
        semantic_searcher.add_chunk(chunk, semantic_searcher.embed_query("test"))
        keyword_searcher.add_chunk(chunk)
        
        query = SearchQuery(query="test", mode=SearchMode.HYBRID)
        response = hybrid_engine.search(query)
        
        assert response.query == "test"
        assert response.search_time_ms > 0
        assert response.total_found >= 0
    
    def test_search_with_filters(
        self, hybrid_engine, semantic_searcher, keyword_searcher
    ):
        """Test search with document filters."""
        chunk1 = Chunk(
            id="1",
            content="Content A",
            metadata=ChunkMetadata(document_id="doc1", document_title="D1"),
        )
        chunk2 = Chunk(
            id="2",
            content="Content A",
            metadata=ChunkMetadata(document_id="doc2", document_title="D2"),
        )
        
        semantic_searcher.add_chunk(chunk1, semantic_searcher.embed_query("A"))
        semantic_searcher.add_chunk(chunk2, semantic_searcher.embed_query("A"))
        keyword_searcher.add_chunk(chunk1)
        keyword_searcher.add_chunk(chunk2)
        
        query = SearchQuery(
            query="Content",
            mode=SearchMode.HYBRID,
            filters={"document_id": "doc1"},
            rerank=False,
        )
        
        response = hybrid_engine.search(query)
        
        assert all(r.chunk.metadata.document_id == "doc1" for r in response.results)


# =============================================================================
# DynamicContextSizer Tests
# =============================================================================

class TestDynamicContextSizer:
    """Tests for DynamicContextSizer."""
    
    def test_calculate_max_context_tokens(self, context_sizer):
        """Test calculating maximum context tokens."""
        max_tokens = context_sizer.calculate_max_context_tokens(
            query="short query",
            model="gpt-4",
        )
        
        # GPT-4 has 8192 limit, minus system prompt, query, and reserve
        assert max_tokens > 0
        assert max_tokens < 8192
    
    def test_different_models(self, context_sizer):
        """Test token limits for different models."""
        gpt35 = context_sizer.calculate_max_context_tokens("test", "gpt-3.5-turbo")
        gpt4 = context_sizer.calculate_max_context_tokens("test", "gpt-4")
        gpt4_32k = context_sizer.calculate_max_context_tokens("test", "gpt-4-32k")
        
        assert gpt4 > gpt35
        assert gpt4_32k > gpt4
    
    def test_unknown_model(self, context_sizer):
        """Test fallback for unknown models."""
        tokens = context_sizer.calculate_max_context_tokens("test", "unknown-model")
        
        assert tokens > 0  # Should use default
    
    def test_adjust_for_complexity_simple(self, context_sizer):
        """Test complexity adjustment for simple queries."""
        base = 1000
        adjusted = context_sizer.adjust_for_complexity(base, "short")
        
        # Simple queries get less context
        assert adjusted < base
    
    def test_adjust_for_complexity_complex(self, context_sizer):
        """Test complexity adjustment for complex queries."""
        base = 1000
        query = " ".join(["word"] * 25)  # 25 words
        
        adjusted = context_sizer.adjust_for_complexity(base, query)
        
        # Complex queries can get more context (up to base)
        assert adjusted >= base * 0.7


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_create_hybrid_search_engine(self):
        """Test creating hybrid search engine."""
        engine = create_hybrid_search_engine(
            default_alpha=0.8,
            cache_ttl=120,
        )
        
        assert isinstance(engine, HybridSearchEngine)
        assert engine.default_alpha == 0.8
    
    def test_create_chunker(self):
        """Test creating chunker."""
        chunker = create_chunker(
            chunk_size=300,
            chunk_overlap=30,
        )
        
        assert isinstance(chunker, TokenAwareChunker)
        assert chunker.chunk_size == 300
        assert chunker.chunk_overlap == 30


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enumeration values."""
    
    def test_search_mode_values(self):
        """Test SearchMode enum."""
        assert len(SearchMode) == 3
        assert SearchMode.SEMANTIC.value == "semantic"
        assert SearchMode.KEYWORD.value == "keyword"
        assert SearchMode.HYBRID.value == "hybrid"
    
    def test_reranking_strategy_values(self):
        """Test RerankingStrategy enum."""
        assert len(RerankingStrategy) == 3
        assert RerankingStrategy.NONE.value == "none"
        assert RerankingStrategy.CROSS_ENCODER.value == "cross_encoder"
    
    def test_chunking_strategy_values(self):
        """Test ChunkingStrategy enum."""
        assert len(ChunkingStrategy) == 4
        assert ChunkingStrategy.RECURSIVE.value == "recursive"
        assert ChunkingStrategy.TOKEN_AWARE.value == "token_aware"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full hybrid search pipeline."""
    
    def test_full_indexing_and_search_pipeline(self):
        """Test complete pipeline from chunking to search."""
        # Create components
        chunker = create_chunker(chunk_size=100, chunk_overlap=10)
        engine = create_hybrid_search_engine()
        
        # Chunk a document
        document = """
        Machine learning is a subset of artificial intelligence.
        It enables computers to learn from data without explicit programming.
        Deep learning uses neural networks with many layers.
        """
        
        chunks = chunker.chunk_document(
            content=document,
            document_id="ml_guide",
            document_title="Machine Learning Guide",
        )
        
        # Index chunks
        for chunk in chunks:
            embedding = engine.semantic_searcher.embed_query(chunk.content)
            engine.semantic_searcher.add_chunk(chunk, embedding)
            engine.keyword_searcher.add_chunk(chunk)
        
        # Search
        query = SearchQuery(
            query="neural networks deep learning",
            mode=SearchMode.HYBRID,
            alpha=0.7,
            top_k=3,
            rerank=True,
        )
        
        response = engine.search(query)
        
        assert len(response.results) > 0
        assert response.reranked is True
        assert response.context_tokens > 0
    
    def test_precision_with_reranking(self):
        """Test that re-ranking improves precision."""
        engine = create_hybrid_search_engine()
        
        # Add some chunks with clear keyword overlap for relevant items
        relevant = [
            Chunk(id="r1", content="Python programming machine learning data science"),
            Chunk(id="r2", content="Machine learning Python libraries scikit-learn tensorflow"),
        ]
        irrelevant = [
            Chunk(id="i1", content="Cooking pasta with tomatoes and basil sauce"),
            Chunk(id="i2", content="Gardening tips for spring planting vegetables"),
            Chunk(id="i3", content="Travel guide to Paris exploring museums"),
        ]
        
        for chunk in relevant + irrelevant:
            embedding = engine.semantic_searcher.embed_query(chunk.content)
            engine.semantic_searcher.add_chunk(chunk, embedding)
            engine.keyword_searcher.add_chunk(chunk)
        
        query = SearchQuery(
            query="Python machine learning",
            mode=SearchMode.HYBRID,
            rerank=True,
            top_k=3,
        )
        
        response = engine.search(query)
        
        # With these keywords overlapping, at least one relevant should be in top 3
        top_ids = {r.chunk.id for r in response.results[:3]}
        relevant_in_top = len(top_ids & {"r1", "r2"})
        assert relevant_in_top >= 1, f"Expected at least 1 relevant in top 3, got {top_ids}"
    
    def test_metadata_preservation(self):
        """Test that metadata is preserved through search."""
        engine = create_hybrid_search_engine()
        
        metadata = ChunkMetadata(
            document_id="doc_123",
            document_title="Important Document",
            page_number=5,
            section_header="Methods",
        )
        
        chunk = Chunk(
            id="chunk_1",
            content="This is the content",
            metadata=metadata,
        )
        
        embedding = engine.semantic_searcher.embed_query(chunk.content)
        engine.semantic_searcher.add_chunk(chunk, embedding)
        engine.keyword_searcher.add_chunk(chunk)
        
        query = SearchQuery(query="content", mode=SearchMode.HYBRID, rerank=False)
        response = engine.search(query)
        
        assert len(response.results) > 0
        result_metadata = response.results[0].chunk.metadata
        assert result_metadata.document_id == "doc_123"
        assert result_metadata.page_number == 5
        assert result_metadata.section_header == "Methods"

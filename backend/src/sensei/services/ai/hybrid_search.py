"""
Advanced RAG Hybrid Search.

This module implements enhanced retrieval with:
- Hybrid Search: Combining semantic (pgvector) and Full-Text Search (FTS)
- Parameter Tuning: Alpha weight for balancing semantic vs keyword results
- Cross-Encoder Re-ranking with ONNX support
- Token-Aware Chunking with metadata enrichment
- Dynamic Context Sizing based on model limits
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import math

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_ALPHA = 0.7  # Semantic weight (1 - alpha = keyword weight)
DEFAULT_TOP_K = 50
DEFAULT_RERANK_CACHE_TTL = 3600  # 1 hour in seconds
MAX_TOKEN_LIMIT = 8192  # Default model token limit


# =============================================================================
# Enums
# =============================================================================

class SearchMode(Enum):
    """Search mode options."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RerankingStrategy(Enum):
    """Re-ranking strategy options."""
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    SCORE_FUSION = "score_fusion"


class ChunkingStrategy(Enum):
    """Document chunking strategies."""
    FIXED_SIZE = "fixed_size"
    RECURSIVE = "recursive"
    SENTENCE = "sentence"
    TOKEN_AWARE = "token_aware"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""
    document_id: str
    document_title: str
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    chunk_index: int = 0
    total_chunks: int = 1
    char_start: int = 0
    char_end: int = 0
    source_type: str = "document"
    created_at: datetime = field(default_factory=_utcnow)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A document chunk with content and metadata."""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[ChunkMetadata] = None
    token_count: int = 0
    
    def __post_init__(self):
        if self.token_count == 0:
            # Rough estimate: ~4 chars per token
            self.token_count = len(self.content) // 4


@dataclass
class SearchResult:
    """A search result with scores."""
    chunk: Chunk
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: Optional[float] = None
    final_score: float = 0.0
    
    def __post_init__(self):
        if self.final_score == 0.0:
            self.final_score = self.combined_score


@dataclass
class SearchQuery:
    """A search query with configuration."""
    query: str
    mode: SearchMode = SearchMode.HYBRID
    alpha: float = DEFAULT_ALPHA
    top_k: int = DEFAULT_TOP_K
    rerank: bool = True
    filters: Dict[str, Any] = field(default_factory=dict)
    max_tokens: Optional[int] = None


@dataclass
class SearchResponse:
    """Response from a search operation."""
    results: List[SearchResult]
    query: str
    mode: SearchMode
    total_found: int
    search_time_ms: float
    reranked: bool = False
    context_tokens: int = 0


@dataclass
class RerankCacheEntry:
    """Cached re-rank result."""
    query_hash: str
    context_hash: str
    score: float
    created_at: datetime
    expires_at: datetime


# =============================================================================
# Token-Aware Chunking
# =============================================================================

class TokenEstimator:
    """Estimates token counts for text."""
    
    def __init__(self, chars_per_token: float = 4.0):
        self.chars_per_token = chars_per_token
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self.chars_per_token)
    
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately max_tokens."""
        max_chars = int(max_tokens * self.chars_per_token)
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at word boundary
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:  # Don't truncate too much
            return truncated[:last_space]
        return truncated


class RecursiveCharacterSplitter:
    """
    Recursive character splitter with overlap.
    
    Splits text recursively on separators, respecting chunk size limits.
    """
    
    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]
    
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS
        self.keep_separator = keep_separator
        self.token_estimator = TokenEstimator()
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        return self._split_text_recursive(text, self.separators)
    
    def _split_text_recursive(
        self,
        text: str,
        separators: List[str],
    ) -> List[str]:
        """Recursively split text on separators."""
        if not text:
            return []
        
        final_chunks = []
        separator = separators[-1]  # Default to last (empty string)
        new_separators = []
        
        # Find the first separator that works
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break
        
        # Split on this separator
        splits = self._split_on_separator(text, separator)
        
        # Merge or recurse
        good_splits = []
        current = ""
        
        for split in splits:
            if len(current) + len(split) <= self.chunk_size:
                current += split
            else:
                if current:
                    good_splits.append(current)
                
                if len(split) <= self.chunk_size:
                    current = split
                else:
                    # Recursively split if still too large
                    if new_separators:
                        sub_splits = self._split_text_recursive(split, new_separators)
                        good_splits.extend(sub_splits)
                        current = ""
                    else:
                        good_splits.append(split[:self.chunk_size])
                        current = ""
        
        if current:
            good_splits.append(current)
        
        # Add overlap
        final_chunks = self._add_overlap(good_splits)
        
        return final_chunks
    
    def _split_on_separator(self, text: str, separator: str) -> List[str]:
        """Split text on a separator."""
        if separator == "":
            return list(text)
        
        splits = text.split(separator)
        
        if self.keep_separator:
            # Add separator back to each split (except last)
            result = []
            for i, split in enumerate(splits):
                if i < len(splits) - 1:
                    result.append(split + separator)
                else:
                    result.append(split)
            return result
        
        return splits
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlap to chunks."""
        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks
        
        result = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                result.append(chunk)
            else:
                # Add overlap from previous chunk
                prev = chunks[i - 1]
                overlap = prev[-self.chunk_overlap:] if len(prev) >= self.chunk_overlap else prev
                result.append(overlap + chunk)
        
        return result


class TokenAwareChunker:
    """
    Token-aware document chunker with metadata enrichment.
    """
    
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        self.splitter = RecursiveCharacterSplitter(chunk_size, chunk_overlap)
        self.token_estimator = TokenEstimator()
    
    def chunk_document(
        self,
        content: str,
        document_id: str,
        document_title: str,
        page_numbers: Optional[Dict[int, Tuple[int, int]]] = None,
        section_headers: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> List[Chunk]:
        """
        Chunk a document with metadata enrichment.
        
        Args:
            content: Document content
            document_id: Document identifier
            document_title: Document title
            page_numbers: Optional mapping of page number to (start, end) char positions
            section_headers: Optional mapping of section header to (start, end) char positions
            
        Returns:
            List of chunks with enriched metadata
        """
        # Split content
        raw_chunks = self.splitter.split_text(content)
        
        chunks = []
        char_offset = 0
        
        for i, raw_content in enumerate(raw_chunks):
            # Find char positions
            char_start = content.find(raw_content, char_offset)
            if char_start == -1:
                char_start = char_offset
            char_end = char_start + len(raw_content)
            char_offset = char_end
            
            # Determine page number
            page_num = None
            if page_numbers:
                for page, (start, end) in page_numbers.items():
                    if start <= char_start < end:
                        page_num = page
                        break
            
            # Determine section header
            section = None
            if section_headers:
                for header, (start, end) in section_headers.items():
                    if start <= char_start:
                        section = header
            
            # Create metadata
            metadata = ChunkMetadata(
                document_id=document_id,
                document_title=document_title,
                page_number=page_num,
                section_header=section,
                chunk_index=i,
                total_chunks=len(raw_chunks),
                char_start=char_start,
                char_end=char_end,
            )
            
            # Enrich content with metadata context
            enriched_content = self._enrich_content(raw_content, metadata)
            
            # Create chunk
            chunk_id = f"{document_id}_chunk_{i}"
            chunk = Chunk(
                id=chunk_id,
                content=enriched_content,
                metadata=metadata,
                token_count=self.token_estimator.estimate_tokens(enriched_content),
            )
            chunks.append(chunk)
        
        return chunks
    
    def _enrich_content(
        self,
        content: str,
        metadata: ChunkMetadata,
    ) -> str:
        """Enrich content with metadata context."""
        context_parts = []
        
        # Add document title
        if metadata.document_title:
            context_parts.append(f"Document: {metadata.document_title}")
        
        # Add section header
        if metadata.section_header:
            context_parts.append(f"Section: {metadata.section_header}")
        
        # Add page number
        if metadata.page_number is not None:
            context_parts.append(f"Page: {metadata.page_number}")
        
        if context_parts:
            context = " | ".join(context_parts)
            return f"[{context}]\n{content}"
        
        return content


# =============================================================================
# Cross-Encoder Re-ranking
# =============================================================================

class RerankCache:
    """Cache for re-ranking results."""
    
    def __init__(self, ttl_seconds: int = DEFAULT_RERANK_CACHE_TTL):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, RerankCacheEntry] = {}
    
    def _make_key(self, query: str, context: str) -> str:
        """Create cache key from query and context."""
        combined = f"{query}|||{context}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def get(self, query: str, context: str) -> Optional[float]:
        """Get cached score if available and not expired."""
        key = self._make_key(query, context)
        entry = self._cache.get(key)
        
        if entry and entry.expires_at > _utcnow():
            return entry.score
        
        # Clean up expired entry
        if entry:
            del self._cache[key]
        
        return None
    
    def set(self, query: str, context: str, score: float) -> None:
        """Cache a re-ranking score."""
        key = self._make_key(query, context)
        now = _utcnow()
        
        entry = RerankCacheEntry(
            query_hash=hashlib.sha256(query.encode()).hexdigest()[:16],
            context_hash=hashlib.sha256(context.encode()).hexdigest()[:16],
            score=score,
            created_at=now,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        self._cache[key] = entry
    
    def clear_expired(self) -> int:
        """Clear expired entries. Returns count removed."""
        now = _utcnow()
        expired = [k for k, v in self._cache.items() if v.expires_at <= now]
        
        for key in expired:
            del self._cache[key]
        
        return len(expired)
    
    def size(self) -> int:
        """Return cache size."""
        return len(self._cache)


class CrossEncoderReranker(ABC):
    """Abstract cross-encoder re-ranker."""
    
    @abstractmethod
    def score_pair(self, query: str, context: str) -> float:
        """Score a query-context pair."""
        pass
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Re-rank search results."""
        pass


class ONNXCrossEncoder(CrossEncoderReranker):
    """
    ONNX-based cross-encoder re-ranker.
    
    Uses the production ONNX cross-encoder from onnx_cross_encoder module
    for high-quality relevance scoring on CPU.
    
    Falls back to TF-IDF scoring if ONNX runtime is unavailable.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        cache_ttl: int = DEFAULT_RERANK_CACHE_TTL,
    ):
        self.model_path = model_path
        self.cache = RerankCache(cache_ttl)
        self._model_loaded = False
        self._encoder = None
        self._fallback = None
        
        # Try to load the ONNX cross-encoder
        self._init_encoder()
    
    def _init_encoder(self) -> None:
        """Initialize the ONNX cross-encoder or fallback."""
        try:
            from sensei.services.ai.onnx_cross_encoder import (
                CrossEncoderConfig,
                ONNXCrossEncoder as RealONNXCrossEncoder,
                TFIDFScorer,
            )
            from pathlib import Path
            import os
            
            # Configure with cache TTL
            cache_dir = Path(os.getenv("SENSEI_ONNX_CACHE_DIR", ".cache/sensei/onnx"))
            config = CrossEncoderConfig(
                model_id=os.getenv(
                    "SENSEI_ONNX_RERANKER_MODEL",
                    "cross-encoder/ms-marco-MiniLM-L-6-v2"
                ),
                cache_dir=cache_dir,
                quantize_int8=True,
                cache_ttl_seconds=self.cache.ttl if hasattr(self.cache, 'ttl') else DEFAULT_RERANK_CACHE_TTL,
            )
            
            self._encoder = RealONNXCrossEncoder(config)
            self._model_loaded = True
            logger.info("Initialized ONNX cross-encoder for re-ranking")
            
        except ImportError as e:
            logger.warning(f"Could not import ONNX cross-encoder, using TF-IDF fallback: {e}")
            self._init_fallback()
        except Exception as e:
            logger.warning(f"Failed to initialize ONNX cross-encoder, using fallback: {e}")
            self._init_fallback()
    
    def _init_fallback(self) -> None:
        """Initialize TF-IDF fallback scorer."""
        try:
            from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
            self._fallback = TFIDFScorer()
        except ImportError:
            # Inline fallback if import fails
            self._fallback = _InlineTFIDFScorer()
    
    def load_model(self) -> bool:
        """Load the ONNX model."""
        if self._encoder is not None:
            return True
        self._init_encoder()
        return self._model_loaded
    
    def score_pair(self, query: str, context: str) -> float:
        """
        Score a query-context pair.
        
        Returns a relevance score between 0 and 1.
        Uses ONNX model if available, otherwise TF-IDF fallback.
        """
        # Check cache first
        cached = self.cache.get(query, context)
        if cached is not None:
            return cached
        
        # Score using ONNX or fallback
        if self._encoder is not None:
            score = self._encoder.score_pair(query, context)
        elif self._fallback is not None:
            score = self._fallback.score(query, context)
        else:
            score = self._heuristic_score(query, context)
        
        # Cache the result
        self.cache.set(query, context, score)
        
        return score
    
    def _heuristic_score(self, query: str, context: str) -> float:
        """
        Simple heuristic scoring as last-resort fallback.
        """
        query_terms = set(query.lower().split())
        context_lower = context.lower()
        
        if not query_terms:
            return 0.0
        
        # Exact phrase match bonus
        if query.lower() in context_lower:
            return 0.9
        
        # Term overlap
        context_terms = set(context_lower.split())
        overlap = len(query_terms & context_terms)
        overlap_score = overlap / len(query_terms)
        
        # Length factor (prefer medium-length contexts)
        len_factor = min(1.0, len(context) / 200) if len(context) < 200 else min(1.0, 400 / len(context))
        
        # Combine
        score = 0.7 * overlap_score + 0.3 * len_factor
        
        return min(1.0, max(0.0, score))
    
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Re-rank search results using cross-encoder scoring."""
        if not results:
            return []
        
        # Use batch scoring if ONNX encoder available
        if self._encoder is not None:
            contents = [r.chunk.content for r in results]
            scores = self._encoder.score_pairs_batch(query, contents)
            
            for result, score in zip(results, scores):
                result.rerank_score = score
                result.final_score = score
        else:
            # Score individually
            for result in results:
                result.rerank_score = self.score_pair(query, result.chunk.content)
                result.final_score = result.rerank_score
        
        # Sort by rerank score
        results.sort(key=lambda r: r.final_score, reverse=True)
        
        return results[:top_k]


class _InlineTFIDFScorer:
    """Inline TF-IDF fallback when import fails."""
    
    def score(self, query: str, context: str) -> float:
        """Simple TF-IDF-like scoring."""
        import re as _re
        
        def tokenize(text: str) -> List[str]:
            text = text.lower()
            terms = _re.findall(r'[a-z0-9]+', text)
            stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'of', 
                        'to', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'and', 
                        'but', 'or', 'it', 'its', 'this', 'that'}
            return [t for t in terms if t not in stopwords and len(t) > 1]
        
        query_terms = set(tokenize(query))
        context_terms = tokenize(context)
        
        if not query_terms or not context_terms:
            return 0.0
        
        # Term frequency in context
        tf = {}
        for term in context_terms:
            tf[term] = tf.get(term, 0) + 1
        
        # BM25-like score
        k1 = 1.2
        score = 0.0
        for term in query_terms:
            if term in tf:
                freq = tf[term]
                score += (freq * (k1 + 1)) / (freq + k1)
        
        # Normalize
        max_possible = len(query_terms) * (k1 + 1)
        normalized = score / max_possible if max_possible > 0 else 0.0
        
        # Exact phrase match bonus
        if query.lower() in context.lower():
            normalized = min(1.0, normalized + 0.2)
        
        return min(1.0, max(0.0, normalized))


# =============================================================================
# Hybrid Search
# =============================================================================

class SemanticSearcher(ABC):
    """Abstract semantic searcher using vector embeddings."""
    
    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Search for similar chunks."""
        pass
    
    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query."""
        pass


class KeywordSearcher(ABC):
    """Abstract keyword searcher using full-text search."""
    
    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Search for matching chunks using FTS."""
        pass


class InMemorySemanticSearcher(SemanticSearcher):
    """
    In-memory semantic searcher.
    
    Uses ONNX embedder for production-quality embeddings when available,
    with a fallback to deterministic hash-based embeddings for testing.
    """
    
    def __init__(self, embedder: Optional[Any] = None):
        """
        Initialize the searcher.
        
        Args:
            embedder: Optional embedder with embed_text method
        """
        self._chunks: Dict[str, Tuple[Chunk, List[float]]] = {}
        self._embedder = embedder
        self._embedder_initialized = False
    
    def _get_embedder(self):
        """Lazily initialize the embedder."""
        if self._embedder is not None:
            return self._embedder
        
        if self._embedder_initialized:
            return None
        
        self._embedder_initialized = True
        
        try:
            from sensei.services.ai.onnx_text_embeddings import (
                ONNXTextEmbedder,
                EmbeddingConfig,
            )
            from pathlib import Path
            
            config = EmbeddingConfig(
                model_id="sentence-transformers/all-MiniLM-L6-v2",
                cache_dir=Path.home() / ".cache" / "sensei" / "embeddings",
                quantize_int8=True,
                max_length=256,
            )
            self._embedder = ONNXTextEmbedder(config)
            return self._embedder
        except Exception:
            return None
    
    def add_chunk(self, chunk: Chunk, embedding: List[float]) -> None:
        """Add a chunk with its embedding."""
        self._chunks[chunk.id] = (chunk, embedding)
        chunk.embedding = embedding
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query using the ONNX embedder."""
        embedder = self._get_embedder()
        
        if embedder is not None:
            try:
                return embedder.embed_text(query)
            except Exception:
                pass
        
        # Fallback: deterministic hash-based embedding
        import hashlib
        h = hashlib.sha256(query.encode()).hexdigest()
        
        embedding = []
        for i in range(0, 64, 2):
            embedding.append((int(h[i:i+2], 16) - 128) / 128.0)
        
        # Extend to 384 dimensions
        while len(embedding) < 384:
            idx = len(embedding) % 32
            embedding.append(embedding[idx] * 0.5)
        
        # Normalize
        norm = math.sqrt(sum(x * x for x in embedding)) or 1.0
        return [x / norm for x in embedding]
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Search using cosine similarity."""
        results = []
        
        for chunk_id, (chunk, embedding) in self._chunks.items():
            # Apply filters
            if filters and not self._matches_filters(chunk, filters):
                continue
            
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, embedding)
            results.append((chunk, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(a) != len(b):
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def _matches_filters(self, chunk: Chunk, filters: Dict[str, Any]) -> bool:
        """Check if chunk matches filters."""
        if not chunk.metadata:
            return True
        
        for key, value in filters.items():
            if key == "document_id" and chunk.metadata.document_id != value:
                return False
            if key == "source_type" and chunk.metadata.source_type != value:
                return False
        
        return True


class InMemoryKeywordSearcher(KeywordSearcher):
    """In-memory keyword searcher for testing."""
    
    def __init__(self):
        self._chunks: Dict[str, Chunk] = {}
        self._inverted_index: Dict[str, Set[str]] = defaultdict(set)
    
    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk to the index."""
        self._chunks[chunk.id] = chunk
        
        # Build inverted index
        terms = self._tokenize(chunk.content)
        for term in terms:
            self._inverted_index[term].add(chunk.id)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        # Simple tokenization: lowercase, split on non-alphanumeric
        text = text.lower()
        terms = re.findall(r'[a-z0-9]+', text)
        return terms
    
    def search(
        self,
        query: str,
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Search using keyword matching (BM25-like scoring)."""
        query_terms = self._tokenize(query)
        
        if not query_terms:
            return []
        
        # Score each chunk
        scores: Dict[str, float] = defaultdict(float)
        
        for term in query_terms:
            matching_ids = self._inverted_index.get(term, set())
            
            # IDF-like weighting
            idf = math.log(len(self._chunks) / (len(matching_ids) + 1) + 1)
            
            for chunk_id in matching_ids:
                chunk = self._chunks[chunk_id]
                
                # Apply filters
                if filters and not self._matches_filters(chunk, filters):
                    continue
                
                # TF-like weighting
                tf = chunk.content.lower().count(term)
                
                scores[chunk_id] += tf * idf
        
        # Sort by score
        results = [
            (self._chunks[chunk_id], score)
            for chunk_id, score in scores.items()
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def _matches_filters(self, chunk: Chunk, filters: Dict[str, Any]) -> bool:
        """Check if chunk matches filters."""
        if not chunk.metadata:
            return True
        
        for key, value in filters.items():
            if key == "document_id" and chunk.metadata.document_id != value:
                return False
            if key == "source_type" and chunk.metadata.source_type != value:
                return False
        
        return True


class HybridSearchEngine:
    """
    Hybrid search engine combining semantic and keyword search.
    
    Features:
    - Configurable alpha weight for semantic vs keyword balance
    - Score fusion (RRF or linear)
    - Cross-encoder re-ranking
    - Dynamic context sizing
    """
    
    def __init__(
        self,
        semantic_searcher: SemanticSearcher,
        keyword_searcher: KeywordSearcher,
        reranker: Optional[CrossEncoderReranker] = None,
        default_alpha: float = DEFAULT_ALPHA,
    ):
        self.semantic_searcher = semantic_searcher
        self.keyword_searcher = keyword_searcher
        self.reranker = reranker or ONNXCrossEncoder()
        self.default_alpha = default_alpha
        self.token_estimator = TokenEstimator()
    
    def search(self, query: SearchQuery) -> SearchResponse:
        """
        Execute a hybrid search.
        
        Args:
            query: Search query with configuration
            
        Returns:
            Search response with results
        """
        start_time = time.time()
        
        # Determine search mode
        if query.mode == SearchMode.SEMANTIC:
            results = self._semantic_search(query)
        elif query.mode == SearchMode.KEYWORD:
            results = self._keyword_search(query)
        else:  # HYBRID
            results = self._hybrid_search(query)
        
        # Re-rank if requested
        reranked = False
        if query.rerank and len(results) > 0:
            results = self.reranker.rerank(query.query, results, query.top_k)
            reranked = True
        
        # Apply dynamic context sizing
        if query.max_tokens:
            results = self._fit_to_token_limit(results, query.max_tokens)
        
        # Calculate total context tokens
        context_tokens = sum(r.chunk.token_count for r in results)
        
        search_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=results,
            query=query.query,
            mode=query.mode,
            total_found=len(results),
            search_time_ms=search_time_ms,
            reranked=reranked,
            context_tokens=context_tokens,
        )
    
    def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute semantic search only."""
        embedding = self.semantic_searcher.embed_query(query.query)
        raw_results = self.semantic_searcher.search(
            embedding, query.top_k, query.filters
        )
        
        return [
            SearchResult(
                chunk=chunk,
                semantic_score=score,
                combined_score=score,
                final_score=score,
            )
            for chunk, score in raw_results
        ]
    
    def _keyword_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute keyword search only."""
        raw_results = self.keyword_searcher.search(
            query.query, query.top_k, query.filters
        )
        
        # Normalize scores
        max_score = max((s for _, s in raw_results), default=1.0)
        
        return [
            SearchResult(
                chunk=chunk,
                keyword_score=score / max_score if max_score > 0 else 0,
                combined_score=score / max_score if max_score > 0 else 0,
                final_score=score / max_score if max_score > 0 else 0,
            )
            for chunk, score in raw_results
        ]
    
    def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute hybrid search combining semantic and keyword."""
        alpha = query.alpha
        
        # Get semantic results
        embedding = self.semantic_searcher.embed_query(query.query)
        semantic_results = self.semantic_searcher.search(
            embedding, query.top_k, query.filters
        )
        
        # Get keyword results
        keyword_results = self.keyword_searcher.search(
            query.query, query.top_k, query.filters
        )
        
        # Normalize keyword scores
        max_kw_score = max((s for _, s in keyword_results), default=1.0)
        
        # Combine results using Reciprocal Rank Fusion (RRF)
        chunk_scores: Dict[str, SearchResult] = {}
        
        # Add semantic results
        for rank, (chunk, score) in enumerate(semantic_results):
            rrf_score = 1.0 / (60 + rank + 1)  # RRF with k=60
            
            if chunk.id not in chunk_scores:
                chunk_scores[chunk.id] = SearchResult(
                    chunk=chunk,
                    semantic_score=score,
                    keyword_score=0.0,
                )
            chunk_scores[chunk.id].semantic_score = score
        
        # Add keyword results
        for rank, (chunk, score) in enumerate(keyword_results):
            rrf_score = 1.0 / (60 + rank + 1)
            normalized_score = score / max_kw_score if max_kw_score > 0 else 0
            
            if chunk.id not in chunk_scores:
                chunk_scores[chunk.id] = SearchResult(
                    chunk=chunk,
                    semantic_score=0.0,
                    keyword_score=normalized_score,
                )
            else:
                chunk_scores[chunk.id].keyword_score = normalized_score
        
        # Calculate combined scores
        results = list(chunk_scores.values())
        for result in results:
            result.combined_score = (
                alpha * result.semantic_score +
                (1 - alpha) * result.keyword_score
            )
            result.final_score = result.combined_score
        
        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)
        
        return results[:query.top_k]
    
    def _fit_to_token_limit(
        self,
        results: List[SearchResult],
        max_tokens: int,
    ) -> List[SearchResult]:
        """Fit results to token limit."""
        fitted = []
        total_tokens = 0
        
        for result in results:
            if total_tokens + result.chunk.token_count <= max_tokens:
                fitted.append(result)
                total_tokens += result.chunk.token_count
            else:
                # Try to fit partial chunk
                remaining = max_tokens - total_tokens
                if remaining > 50:  # Minimum useful size
                    # Truncate chunk content
                    truncated_content = self.token_estimator.truncate_to_tokens(
                        result.chunk.content, remaining
                    )
                    truncated_chunk = Chunk(
                        id=result.chunk.id,
                        content=truncated_content,
                        embedding=result.chunk.embedding,
                        metadata=result.chunk.metadata,
                        token_count=remaining,
                    )
                    fitted.append(SearchResult(
                        chunk=truncated_chunk,
                        semantic_score=result.semantic_score,
                        keyword_score=result.keyword_score,
                        combined_score=result.combined_score,
                        rerank_score=result.rerank_score,
                        final_score=result.final_score,
                    ))
                break
        
        return fitted


class DynamicContextSizer:
    """
    Dynamic context sizer based on model limits and query complexity.
    """
    
    # Local model token limits (on-device)
    MODEL_LIMITS = {
        "local-llm-small": 8192,
        "local-llm-large": 32768,
        "mistral-7b": 32768,
        "llama-3-8b": 128000,
    }
    
    def __init__(
        self,
        default_model: str = "llama-3-8b",
        system_prompt_tokens: int = 500,
        response_reserve_tokens: int = 1000,
    ):
        self.default_model = default_model
        self.system_prompt_tokens = system_prompt_tokens
        self.response_reserve_tokens = response_reserve_tokens
        self.token_estimator = TokenEstimator()
    
    def calculate_max_context_tokens(
        self,
        query: str,
        model: Optional[str] = None,
    ) -> int:
        """
        Calculate maximum context tokens available.
        
        Accounts for:
        - Model token limit
        - System prompt
        - Query tokens
        - Response reserve
        """
        model = model or self.default_model
        limit = self.MODEL_LIMITS.get(model, MAX_TOKEN_LIMIT)
        
        query_tokens = self.token_estimator.estimate_tokens(query)
        
        available = (
            limit -
            self.system_prompt_tokens -
            query_tokens -
            self.response_reserve_tokens
        )
        
        return max(0, available)
    
    def adjust_for_complexity(
        self,
        base_tokens: int,
        query: str,
    ) -> int:
        """
        Adjust context size based on query complexity.
        
        Complex queries (longer, more entities) may need more context.
        """
        # Simple heuristic: more words = more complex
        word_count = len(query.split())
        
        if word_count < 5:
            # Simple query, reduce context
            return int(base_tokens * 0.7)
        elif word_count > 20:
            # Complex query, allow more context
            return min(int(base_tokens * 1.2), base_tokens)
        
        return base_tokens


# =============================================================================
# Factory Functions
# =============================================================================

def create_hybrid_search_engine(
    default_alpha: float = DEFAULT_ALPHA,
    cache_ttl: int = DEFAULT_RERANK_CACHE_TTL,
) -> HybridSearchEngine:
    """
    Create a hybrid search engine with in-memory stores for testing.
    
    Args:
        default_alpha: Default semantic/keyword weight
        cache_ttl: Re-rank cache TTL in seconds
        
    Returns:
        Configured HybridSearchEngine
    """
    semantic = InMemorySemanticSearcher()
    keyword = InMemoryKeywordSearcher()
    reranker = ONNXCrossEncoder(cache_ttl=cache_ttl)
    
    return HybridSearchEngine(
        semantic_searcher=semantic,
        keyword_searcher=keyword,
        reranker=reranker,
        default_alpha=default_alpha,
    )


def create_chunker(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> TokenAwareChunker:
    """
    Create a token-aware chunker.
    
    Args:
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        Configured TokenAwareChunker
    """
    return TokenAwareChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=ChunkingStrategy.RECURSIVE,
    )

"""Hybrid search utilities for advanced RAG workflows.

.. warning:: Deterministic Fallbacks Active

   Several components in this module use **deterministic heuristic fallbacks**
   instead of real ML models.  These are clearly marked:

   * ``InMemorySemanticSearcher.embed_query()`` — Uses SHAKE-256 hash expansion
     to produce 384-dim embeddings.  Replace with a real sentence-transformer
     (e.g. ``all-MiniLM-L6-v2``) loaded via ONNX Runtime for production quality.
     See checklist item **#201, #455**.

   * ``HeuristicCrossEncoder`` — Uses bag-of-words overlap instead of a trained
     cross-encoder.  Replace with ``ms-marco-MiniLM-L-6-v2`` via ONNX Runtime.
     See checklist item **#202**.

   * ``InMemoryKeywordSearcher`` — Linear scan; replace with an inverted index
     or pgvector full-text search for production scale.  See **#461**.

   The interfaces are designed for drop-in replacement: implement the same
   ``embed_query()`` / ``score_pair()`` signatures with real model calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import math
import os
import time
from typing import Any, Iterable

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin


DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_ALPHA = 0.7


class SearchMode(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RerankingStrategy(str, Enum):
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    HEURISTIC = "heuristic"


class ChunkingStrategy(str, Enum):
    RECURSIVE = "recursive"
    TOKEN_AWARE = "token_aware"
    SENTENCE = "sentence"
    FIXED = "fixed"


@dataclass
class ChunkMetadata:
    document_id: str
    document_title: str
    page_number: int | None = None
    section_header: str | None = None
    chunk_index: int = 0
    total_chunks: int = 0


@dataclass
class Chunk:
    id: str
    content: str
    metadata: ChunkMetadata | None = None
    token_count: int = 0


@dataclass
class SearchResult:
    chunk: Chunk
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: float | None = None


@dataclass
class SearchQuery:
    query: str
    mode: SearchMode = SearchMode.HYBRID
    alpha: float = DEFAULT_ALPHA
    top_k: int = 10
    rerank: bool = False
    max_tokens: int | None = None
    filters: dict[str, Any] | None = None


@dataclass
class SearchResponse:
    query: str
    mode: SearchMode
    results: list[SearchResult]
    total_found: int
    search_time_ms: int
    context_tokens: int
    reranked: bool = False


@dataclass
class RerankCacheEntry:
    score: float
    timestamp: float


class TokenEstimator:
    """Improved token estimator with heuristics for different content types.

    The default 4-chars-per-token heuristic is accurate for English prose but
    under-estimates for code/URLs (more special chars) and CJK/Arabic text
    (fewer chars per semantic unit, but most tokenizers produce ~1-2 chars per
    token for such scripts).

    This estimator detects the predominant content type and adjusts accordingly:
    * English prose: ~4 chars/token (GPT-family average)
    * Code/technical: ~3.3 chars/token (more symbols → more tokens)
    * CJK/Arabic/non-Latin: ~1.5 chars/token (each char ≈ 1 token)
    * Mixed: weighted average
    """

    @staticmethod
    def _non_latin_ratio(text: str) -> float:
        """Return the fraction of characters that are non-Latin/non-ASCII."""
        if not text:
            return 0.0
        non_latin = sum(1 for ch in text if ord(ch) > 0x024F)  # beyond Latin Extended-B
        return non_latin / len(text)

    @staticmethod
    def _code_ratio(text: str) -> float:
        """Return the fraction of characters that are code-like symbols."""
        if not text:
            return 0.0
        code_chars = sum(1 for ch in text if ch in "{}[]();:=<>|&!@#$%^*~`/\\")
        return code_chars / len(text)

    def _chars_per_token(self, text: str) -> float:
        """Estimate chars-per-token based on content type heuristics."""
        nl_ratio = self._non_latin_ratio(text)
        cd_ratio = self._code_ratio(text)

        if nl_ratio > 0.3:
            # Predominantly non-Latin: most tokenizers ≈ 1.5 chars/token
            return 1.5
        if cd_ratio > 0.08:
            # Code-heavy: more tokens per character
            return 3.3
        # Standard English prose
        return 4.0

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        cpt = self._chars_per_token(text)
        return max(1, int(len(text) / cpt))

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        if not text:
            return ""
        cpt = self._chars_per_token(text)
        max_chars = int(max_tokens * cpt)
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        if " " in truncated:
            truncated = truncated.rsplit(" ", 1)[0]
        return truncated


class RecursiveCharacterSplitter:
    """Basic character splitter with overlap."""

    def __init__(self, chunk_size: int, chunk_overlap: int, keep_separator: bool = False):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.keep_separator = keep_separator

    def split_text(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        step = max(1, self.chunk_size - self.chunk_overlap)
        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += step
        return chunks

    def split_text_with_indices(self, text: str) -> list[tuple[str, int, int]]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [(text, 0, len(text))]

        chunks: list[tuple[str, int, int]] = []
        start = 0
        step = max(1, self.chunk_size - self.chunk_overlap)
        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunks.append((text[start:end], start, end))
            if end == len(text):
                break
            start += step
        return chunks


class TokenAwareChunker:
    """Chunk documents using token estimation and metadata enrichment."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterSplitter(chunk_size, chunk_overlap)
        self._token_estimator = TokenEstimator()

    def chunk_document(
        self,
        *,
        content: str,
        document_id: str,
        document_title: str,
        page_numbers: dict[int, tuple[int, int]] | None = None,
        section_headers: dict[str, tuple[int, int]] | None = None,
    ) -> list[Chunk]:
        if not content:
            return []

        enriched_prefix = f"Document: {document_title}\n"
        chunks_with_idx = self._splitter.split_text_with_indices(content)
        total_chunks = len(chunks_with_idx)
        results: list[Chunk] = []

        for idx, (chunk_text, start, _end) in enumerate(chunks_with_idx):
            page_number = self._resolve_range_value(page_numbers, start)
            section_header = self._resolve_section_header(section_headers, start)

            metadata = ChunkMetadata(
                document_id=document_id,
                document_title=document_title,
                page_number=page_number,
                section_header=section_header,
                chunk_index=idx,
                total_chunks=total_chunks,
            )
            enriched_content = f"{enriched_prefix}{chunk_text.strip()}"
            token_count = self._token_estimator.estimate_tokens(enriched_content)

            results.append(
                Chunk(
                    id=f"{document_id}_chunk_{idx}",
                    content=enriched_content,
                    metadata=metadata,
                    token_count=token_count,
                )
            )

        return results

    @staticmethod
    def _resolve_range_value(mapping: dict[int, tuple[int, int]] | None, start: int) -> int | None:
        if not mapping:
            return None
        for key, (s, e) in mapping.items():
            if s <= start < e:
                return key
        return None

    @staticmethod
    def _resolve_section_header(mapping: dict[str, tuple[int, int]] | None, start: int) -> str | None:
        if not mapping:
            return None
        for header, (s, e) in mapping.items():
            if s <= start < e:
                return header
        return None


class RerankCache:
    """TTL cache for rerank scores with bounded size to prevent memory leaks."""

    MAX_ENTRIES = 10_000  # cap to prevent unbounded growth

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, RerankCacheEntry] = {}

    def _key(self, query: str, context: str) -> str:
        return f"{query}:::{context}"

    def set(self, query: str, context: str, score: float) -> None:
        if len(self._entries) >= self.MAX_ENTRIES:
            self.clear_expired()
            # If still at capacity after clearing expired, evict oldest 25%
            if len(self._entries) >= self.MAX_ENTRIES:
                sorted_keys = sorted(
                    self._entries, key=lambda k: self._entries[k].timestamp
                )
                for k in sorted_keys[: len(sorted_keys) // 4]:
                    self._entries.pop(k, None)
        self._entries[self._key(query, context)] = RerankCacheEntry(score=score, timestamp=time.time())

    def get(self, query: str, context: str) -> float | None:
        key = self._key(query, context)
        entry = self._entries.get(key)
        if not entry:
            return None
        if time.time() - entry.timestamp > self.ttl_seconds:
            self._entries.pop(key, None)
            return None
        return entry.score

    def clear_expired(self) -> int:
        now = time.time()
        expired = [k for k, v in self._entries.items() if now - v.timestamp > self.ttl_seconds]
        for k in expired:
            self._entries.pop(k, None)
        return len(expired)

    def size(self) -> int:
        return len(self._entries)


class HeuristicCrossEncoder:
    """Lightweight heuristic cross-encoder scorer with caching.

    Note: This is a bag-of-words overlap heuristic, NOT a real ONNX
    cross-encoder model. For production quality, replace with an actual
    cross-encoder (e.g. ``ms-marco-MiniLM-L-6-v2``) loaded via ONNX Runtime.
    The interface is kept compatible so swapping is drop-in.
    """

    def __init__(self, cache_ttl: int = 60):
        self.cache = RerankCache(ttl_seconds=cache_ttl)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {t for t in text.lower().split() if t}

    def score_pair(self, query: str, context: str) -> float:
        cached = self.cache.get(query, context)
        if cached is not None:
            return cached

        q_tokens = self._tokenize(query)
        c_tokens = self._tokenize(context)
        if not q_tokens or not c_tokens:
            score = 0.0
        else:
            overlap = len(q_tokens & c_tokens)
            score = min(1.0, overlap / max(1, len(q_tokens)))

        self.cache.set(query, context, score)
        return score

    def rerank(self, query: str, results: list[SearchResult], top_k: int = 10) -> list[SearchResult]:
        for result in results:
            result.rerank_score = self.score_pair(query, result.chunk.content)
        ranked = sorted(results, key=lambda r: r.rerank_score or 0.0, reverse=True)
        return ranked[:top_k]


class InMemorySemanticSearcher:
    """Semantic searcher with ONNX model support.

    When an ONNX sentence-transformer model is available (set via
    SENSEI_EMBED_MODEL_PATH env var), embed_query() produces real
    semantic embeddings. Otherwise falls back to SHAKE-256 deterministic
    hashing. The search() method uses brute-force in-memory matching;
    for production scale, use PgVectorSearcher from real_ml_implementations.

    Performance optimisations:
    * Embeddings are LRU-cached (up to 1024 queries).
    * _cosine_similarity() exploits pre-normalised vectors (dot-product only).
    """

    _EMBED_DIM = 384
    _EMBED_CACHE_MAX = 512

    def __init__(self) -> None:
        self._chunks: dict[str, tuple[Chunk, list[float]]] = {}
        self._embed_cache: dict[str, list[float]] = {}
        # Use real ONNX embedder when available (#455)
        try:
            from sensei.services.ai.real_ml_implementations import OnnxEmbedder
            self._onnx_embedder = OnnxEmbedder()
        except ImportError:
            self._onnx_embedder = None  # type: ignore[assignment]

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def embed_query(self, text: str) -> list[float]:
        """Produce a 384-dim embedding.

        Uses real ONNX model when available (#455), otherwise falls back
        to SHAKE-256 deterministic expansion. Results are LRU-cached.
        """
        cached = self._embed_cache.get(text)
        if cached is not None:
            return cached

        # Prefer real ONNX embeddings when available
        if self._onnx_embedder is not None and self._onnx_embedder.is_real_model:
            result = self._onnx_embedder.embed(text)
        else:
            # SHAKE-256 fallback — single hash call for all dimensions
            digest = hashlib.shake_256(text.encode("utf-8")).digest(self._EMBED_DIM * 4)
            vector: list[float] = []
            for i in range(self._EMBED_DIM):
                value = int.from_bytes(digest[i * 4 : i * 4 + 4], "big") / 2**32
                vector.append(value)
            result = self._normalize(vector)

        # Bounded LRU-style cache
        if len(self._embed_cache) >= self._EMBED_CACHE_MAX:
            # evict first (oldest) entry
            oldest = next(iter(self._embed_cache))
            del self._embed_cache[oldest]
        self._embed_cache[text] = result
        return result

    def add_chunk(self, chunk: Chunk, embedding: list[float]) -> None:
        self._chunks[chunk.id] = (chunk, self._normalize(list(embedding)))

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Both vectors are pre-normalised on insert / embed, so the cosine
        similarity is simply the dot product — no need to recompute norms.
        A guard clause handles the (rare) zero-length edge case.
        """
        if not a or not b:
            return 0.0
        return sum(x * y for x, y in zip(a, b))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        results: list[tuple[Chunk, float]] = []
        for chunk, embedding in self._chunks.values():
            if filters and chunk.metadata:
                if any(getattr(chunk.metadata, k, None) != v for k, v in filters.items()):
                    continue
            score = self._cosine_similarity(query_embedding, embedding)
            results.append((chunk, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class InMemoryKeywordSearcher:
    """In-memory keyword searcher using term frequency.

    Optimisations:
    * Pre-tokenizes and caches token lists on ``add_chunk`` so we never
      re-tokenize stored content during search.
    * Stores sqrt(len) alongside tokens to avoid repeated sqrt calls.
    """

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._chunk_tokens: dict[str, tuple[list[str], float]] = {}  # tokens, sqrt_len

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t for t in text.lower().split() if t]

    def add_chunk(self, chunk: Chunk) -> None:
        self._chunks[chunk.id] = chunk
        tokens = self._tokenize(chunk.content)
        sqrt_len = math.sqrt(len(tokens)) if tokens else 1.0
        self._chunk_tokens[chunk.id] = (tokens, sqrt_len)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []
        # Convert to set for O(1) membership test when checking unique matches
        q_token_set = set(q_tokens)
        results: list[tuple[Chunk, float]] = []
        for chunk_id, chunk in self._chunks.items():
            if filters and chunk.metadata:
                if any(getattr(chunk.metadata, k, None) != v for k, v in filters.items()):
                    continue
            cached = self._chunk_tokens.get(chunk_id)
            if cached is None:
                continue
            c_tokens, sqrt_len = cached
            if not c_tokens:
                continue
            raw_score = sum(1 for t in c_tokens if t in q_token_set)
            if raw_score > 0:
                score = raw_score / sqrt_len
                results.append((chunk, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class HybridSearchEngine(PersistentServiceMixin):
    """Hybrid search engine combining semantic and keyword search."""

    SERVICE_NAME = "hybrid_search"

    def __init__(
        self,
        *,
        semantic_searcher: InMemorySemanticSearcher,
        keyword_searcher: InMemoryKeywordSearcher,
        reranker: HeuristicCrossEncoder,
        default_alpha: float = DEFAULT_ALPHA,
    ) -> None:
        self.semantic_searcher = semantic_searcher
        self.keyword_searcher = keyword_searcher
        self.reranker = reranker
        self.default_alpha = default_alpha
        self._token_estimator = TokenEstimator()

    def search(self, query: SearchQuery) -> SearchResponse:
        start = time.time()
        alpha = query.alpha if query.alpha is not None else self.default_alpha
        semantic_results: list[tuple[Chunk, float]] = []
        keyword_results: list[tuple[Chunk, float]] = []

        if query.mode in (SearchMode.SEMANTIC, SearchMode.HYBRID):
            embedding = self.semantic_searcher.embed_query(query.query)
            semantic_results = self.semantic_searcher.search(
                embedding,
                top_k=query.top_k,
                filters=query.filters,
            )

        if query.mode in (SearchMode.KEYWORD, SearchMode.HYBRID):
            keyword_results = self.keyword_searcher.search(
                query.query,
                top_k=query.top_k,
                filters=query.filters,
            )

        results_map: dict[str, SearchResult] = {}
        for chunk, score in semantic_results:
            results_map[chunk.id] = SearchResult(
                chunk=chunk,
                semantic_score=score,
                keyword_score=0.0,
                combined_score=score,
            )
        for chunk, score in keyword_results:
            if chunk.id in results_map:
                existing = results_map[chunk.id]
                existing.keyword_score = score
            else:
                results_map[chunk.id] = SearchResult(
                    chunk=chunk,
                    semantic_score=0.0,
                    keyword_score=score,
                    combined_score=score,
                )

        if query.mode == SearchMode.HYBRID:
            for result in results_map.values():
                result.combined_score = alpha * result.semantic_score + (1 - alpha) * result.keyword_score

        combined_results = list(results_map.values())
        combined_results.sort(key=lambda r: r.combined_score, reverse=True)

        if query.rerank:
            combined_results = self.reranker.rerank(query.query, combined_results, top_k=query.top_k)
            reranked = True
        else:
            combined_results = combined_results[: query.top_k]
            reranked = False

        trimmed_results: list[SearchResult] = []
        context_tokens = 0
        for result in combined_results:
            token_count = result.chunk.token_count or self._token_estimator.estimate_tokens(result.chunk.content)
            if query.max_tokens is not None and context_tokens + token_count > query.max_tokens:
                break
            trimmed_results.append(result)
            context_tokens += token_count

        search_time_ms = int((time.time() - start) * 1000)
        return SearchResponse(
            query=query.query,
            mode=query.mode,
            results=trimmed_results,
            total_found=len(results_map),
            search_time_ms=max(1, search_time_ms),
            context_tokens=context_tokens,
            reranked=reranked,
        )


class DynamicContextSizer:
    """Determine token budgets for context based on model and query complexity."""

    MODEL_LIMITS = {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
    }

    def __init__(self) -> None:
        self._token_estimator = TokenEstimator()

    def calculate_max_context_tokens(self, query: str, model: str) -> int:
        limit = self.MODEL_LIMITS.get(model, 4096)
        reserved = 512
        query_tokens = self._token_estimator.estimate_tokens(query)
        available = max(256, limit - reserved - query_tokens)
        return min(available, limit - 1)

    def adjust_for_complexity(self, base_tokens: int, query: str) -> int:
        word_count = len(query.split())
        if word_count <= 8:
            return int(base_tokens * 0.6)
        if word_count >= 20:
            return int(base_tokens * 1.0)
        ratio = 0.6 + (word_count - 8) * (0.4 / 12)
        return int(base_tokens * ratio)


def create_hybrid_search_engine(
    *,
    default_alpha: float = DEFAULT_ALPHA,
    cache_ttl: int = 60,
) -> HybridSearchEngine:
    return HybridSearchEngine(
        semantic_searcher=InMemorySemanticSearcher(),
        keyword_searcher=InMemoryKeywordSearcher(),
        reranker=HeuristicCrossEncoder(cache_ttl=cache_ttl),
        default_alpha=default_alpha,
    )


def create_chunker(*, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> TokenAwareChunker:
    return TokenAwareChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


# Backward-compatible alias — the heuristic was previously misnamed "ONNXCrossEncoder"
# in this module. The real ONNX implementation lives in onnx_cross_encoder.py.
ONNXCrossEncoder = HeuristicCrossEncoder

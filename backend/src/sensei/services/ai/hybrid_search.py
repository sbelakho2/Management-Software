"""Hybrid search utilities for advanced RAG workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import math
import os
import time
from typing import Any, Iterable


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
    """Simple token estimator using ~4 chars per token."""

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        if not text:
            return ""
        max_chars = max_tokens * 4
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
    """TTL cache for rerank scores."""

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, RerankCacheEntry] = {}

    def _key(self, query: str, context: str) -> str:
        return f"{query}:::{context}"

    def set(self, query: str, context: str, score: float) -> None:
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


class ONNXCrossEncoder:
    """Lightweight heuristic cross-encoder scorer with caching."""

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
    """In-memory semantic searcher with deterministic embeddings."""

    def __init__(self) -> None:
        self._chunks: dict[str, tuple[Chunk, list[float]]] = {}

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def embed_query(self, text: str) -> list[float]:
        vector: list[float] = []
        for i in range(384):
            digest = hashlib.sha256(f"{text}:{i}".encode("utf-8")).digest()
            value = int.from_bytes(digest[:4], "big") / 2**32
            vector.append(value)
        return self._normalize(vector)

    def add_chunk(self, chunk: Chunk, embedding: list[float]) -> None:
        self._chunks[chunk.id] = (chunk, self._normalize(list(embedding)))

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
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
    """In-memory keyword searcher using term frequency."""

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t for t in text.lower().split() if t]

    def add_chunk(self, chunk: Chunk) -> None:
        self._chunks[chunk.id] = chunk

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        q_tokens = self._tokenize(query)
        results: list[tuple[Chunk, float]] = []
        for chunk in self._chunks.values():
            if filters and chunk.metadata:
                if any(getattr(chunk.metadata, k, None) != v for k, v in filters.items()):
                    continue
            c_tokens = self._tokenize(chunk.content)
            score = sum(c_tokens.count(t) for t in q_tokens)
            results.append((chunk, float(score)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class HybridSearchEngine:
    """Hybrid search engine combining semantic and keyword search."""

    def __init__(
        self,
        *,
        semantic_searcher: InMemorySemanticSearcher,
        keyword_searcher: InMemoryKeywordSearcher,
        reranker: ONNXCrossEncoder,
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
        reranker=ONNXCrossEncoder(cache_ttl=cache_ttl),
        default_alpha=default_alpha,
    )


def create_chunker(*, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> TokenAwareChunker:
    return TokenAwareChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

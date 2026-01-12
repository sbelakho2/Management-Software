"""
Self-Improving RAG (Retrieval-Augmented Generation) System.

This module implements continuous improvement for the RAG system:
- Retrieval Quality Tracking: Log and track chunk utility
- Decay Algorithm: Reduce scores for ignored/corrected chunks
- Autonomous Re-indexing: Re-process low-utility documents
- Incremental Vector Index Updates: No downtime re-indexing
- CPU Throttling: Limit processing during business hours
"""

from __future__ import annotations

import asyncio
import hashlib
import heapq
import logging
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math
import json

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Enums and Constants
# =============================================================================

class ChunkUtilityStatus(Enum):
    """Status indicating whether a chunk was useful."""
    USED = "used"           # Chunk was present in final answer
    IGNORED = "ignored"     # Chunk was retrieved but not used
    CORRECTED = "corrected" # Chunk led to a correction
    UNKNOWN = "unknown"     # Status not determined


class DocumentQuality(Enum):
    """Quality classification for documents."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEEDS_REPROCESSING = "needs_reprocessing"


class ReindexPriority(Enum):
    """Priority levels for re-indexing."""
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class IndexingMode(Enum):
    """Indexing operation modes."""
    INCREMENTAL = "incremental"
    FULL = "full"
    PARTIAL = "partial"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""
    chunk_id: str
    document_id: str
    content_hash: str
    created_at: datetime
    last_retrieved_at: Optional[datetime] = None
    retrieval_count: int = 0
    utility_score: float = 1.0
    decay_factor: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkUtilityEvent:
    """Event recording chunk utility."""
    chunk_id: str
    query_id: str
    timestamp: datetime
    status: ChunkUtilityStatus
    relevance_score: float
    was_in_answer: bool
    user_feedback: Optional[str] = None
    correction_id: Optional[str] = None


@dataclass
class DocumentMetrics:
    """Metrics for a document."""
    document_id: str
    total_chunks: int
    avg_utility_score: float
    retrieval_count: int
    used_count: int
    ignored_count: int
    corrected_count: int
    quality: DocumentQuality
    last_indexed_at: datetime
    needs_reindex: bool = False
    reindex_priority: Optional[ReindexPriority] = None


@dataclass
class ReindexJob:
    """A job for re-indexing a document."""
    job_id: str
    document_id: str
    priority: ReindexPriority
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    status: str = "pending"  # pending, scheduled, running, completed, failed


@dataclass
class ThrottleConfig:
    """Configuration for CPU throttling."""
    business_hours_start: time = field(default_factory=lambda: time(8, 0))
    business_hours_end: time = field(default_factory=lambda: time(18, 0))
    business_hours_threads: int = 1
    off_hours_threads: int = 4
    idle_window_start: time = field(default_factory=lambda: time(2, 0))
    idle_window_end: time = field(default_factory=lambda: time(5, 0))
    idle_threads: int = 8


# =============================================================================
# Chunk Utility Tracker
# =============================================================================

class ChunkUtilityTracker:
    """
    Tracks the utility of retrieved chunks.
    
    Logs whether chunks were actually used in answers and applies
    decay to consistently ignored or corrected chunks.
    """
    
    DEFAULT_DECAY_RATE = 0.95  # Decay per ignored event
    CORRECTION_PENALTY = 0.8   # Additional decay for corrections
    USAGE_BOOST = 1.05         # Boost per usage
    MAX_UTILITY = 2.0
    MIN_UTILITY = 0.1
    
    def __init__(
        self,
        decay_rate: float = DEFAULT_DECAY_RATE,
        correction_penalty: float = CORRECTION_PENALTY,
        usage_boost: float = USAGE_BOOST,
    ):
        self.decay_rate = decay_rate
        self.correction_penalty = correction_penalty
        self.usage_boost = usage_boost
        
        self._chunks: Dict[str, ChunkMetadata] = {}
        self._events: List[ChunkUtilityEvent] = []
        self._document_chunks: Dict[str, Set[str]] = defaultdict(set)
    
    def register_chunk(self, chunk: ChunkMetadata) -> None:
        """Register a chunk for tracking."""
        self._chunks[chunk.chunk_id] = chunk
        self._document_chunks[chunk.document_id].add(chunk.chunk_id)
    
    def log_retrieval(
        self,
        chunk_id: str,
        query_id: str,
        relevance_score: float,
        was_in_answer: bool,
        user_feedback: Optional[str] = None,
        correction_id: Optional[str] = None,
    ) -> ChunkUtilityEvent:
        """
        Log a chunk retrieval event and update utility scores.
        
        Args:
            chunk_id: The ID of the retrieved chunk
            query_id: The ID of the query
            relevance_score: Initial relevance score from retrieval
            was_in_answer: Whether the chunk appeared in the final answer
            user_feedback: Optional user feedback
            correction_id: Optional correction ID if chunk led to correction
            
        Returns:
            The utility event that was logged
        """
        # Determine status
        if correction_id:
            status = ChunkUtilityStatus.CORRECTED
        elif was_in_answer:
            status = ChunkUtilityStatus.USED
        else:
            status = ChunkUtilityStatus.IGNORED
        
        event = ChunkUtilityEvent(
            chunk_id=chunk_id,
            query_id=query_id,
            timestamp=_utcnow(),
            status=status,
            relevance_score=relevance_score,
            was_in_answer=was_in_answer,
            user_feedback=user_feedback,
            correction_id=correction_id,
        )
        
        self._events.append(event)
        
        # Update chunk utility
        if chunk_id in self._chunks:
            self._update_chunk_utility(chunk_id, event)
        
        return event
    
    def _update_chunk_utility(
        self,
        chunk_id: str,
        event: ChunkUtilityEvent,
    ) -> None:
        """Update chunk utility based on event."""
        chunk = self._chunks[chunk_id]
        chunk.retrieval_count += 1
        chunk.last_retrieved_at = event.timestamp
        
        if event.status == ChunkUtilityStatus.USED:
            # Boost for usage
            chunk.utility_score = min(
                self.MAX_UTILITY,
                chunk.utility_score * self.usage_boost
            )
        elif event.status == ChunkUtilityStatus.IGNORED:
            # Apply decay
            chunk.utility_score = max(
                self.MIN_UTILITY,
                chunk.utility_score * self.decay_rate
            )
            chunk.decay_factor *= self.decay_rate
        elif event.status == ChunkUtilityStatus.CORRECTED:
            # Apply correction penalty
            chunk.utility_score = max(
                self.MIN_UTILITY,
                chunk.utility_score * self.correction_penalty
            )
            chunk.decay_factor *= self.correction_penalty
    
    def get_chunk_utility(self, chunk_id: str) -> float:
        """Get the current utility score for a chunk."""
        if chunk_id in self._chunks:
            return self._chunks[chunk_id].utility_score
        return 1.0  # Default for unknown chunks
    
    def get_low_utility_chunks(
        self,
        threshold: float = 0.5,
        limit: int = 100,
    ) -> List[ChunkMetadata]:
        """Get chunks with utility below threshold."""
        low_utility = [
            chunk for chunk in self._chunks.values()
            if chunk.utility_score < threshold
        ]
        low_utility.sort(key=lambda c: c.utility_score)
        return low_utility[:limit]
    
    def get_document_metrics(self, document_id: str) -> Optional[DocumentMetrics]:
        """Calculate metrics for a document."""
        chunk_ids = self._document_chunks.get(document_id)
        if not chunk_ids:
            return None
        
        chunks = [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]
        if not chunks:
            return None
        
        # Count events by status for this document
        used_count = 0
        ignored_count = 0
        corrected_count = 0
        
        for event in self._events:
            if event.chunk_id in chunk_ids:
                if event.status == ChunkUtilityStatus.USED:
                    used_count += 1
                elif event.status == ChunkUtilityStatus.IGNORED:
                    ignored_count += 1
                elif event.status == ChunkUtilityStatus.CORRECTED:
                    corrected_count += 1
        
        avg_utility = sum(c.utility_score for c in chunks) / len(chunks)
        retrieval_count = sum(c.retrieval_count for c in chunks)
        
        # Determine quality
        if avg_utility >= 0.8:
            quality = DocumentQuality.HIGH
        elif avg_utility >= 0.5:
            quality = DocumentQuality.MEDIUM
        elif avg_utility >= 0.3:
            quality = DocumentQuality.LOW
        else:
            quality = DocumentQuality.NEEDS_REPROCESSING
        
        needs_reindex = quality == DocumentQuality.NEEDS_REPROCESSING or avg_utility < 0.4
        
        return DocumentMetrics(
            document_id=document_id,
            total_chunks=len(chunks),
            avg_utility_score=avg_utility,
            retrieval_count=retrieval_count,
            used_count=used_count,
            ignored_count=ignored_count,
            corrected_count=corrected_count,
            quality=quality,
            last_indexed_at=max(c.created_at for c in chunks),
            needs_reindex=needs_reindex,
            reindex_priority=ReindexPriority.HIGH if needs_reindex else None,
        )
    
    def get_documents_needing_reindex(
        self,
        utility_threshold: float = 0.4,
    ) -> List[Tuple[str, float]]:
        """Get documents that need re-indexing based on utility."""
        document_utilities: Dict[str, List[float]] = defaultdict(list)
        
        for chunk in self._chunks.values():
            document_utilities[chunk.document_id].append(chunk.utility_score)
        
        needing_reindex = []
        for doc_id, utilities in document_utilities.items():
            avg_utility = sum(utilities) / len(utilities)
            if avg_utility < utility_threshold:
                needing_reindex.append((doc_id, avg_utility))
        
        # Sort by utility (lowest first)
        needing_reindex.sort(key=lambda x: x[1])
        return needing_reindex
    
    def export_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Export events for analysis."""
        filtered = self._events
        
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        return [
            {
                "chunk_id": e.chunk_id,
                "query_id": e.query_id,
                "timestamp": e.timestamp.isoformat(),
                "status": e.status.value,
                "relevance_score": e.relevance_score,
                "was_in_answer": e.was_in_answer,
            }
            for e in filtered
        ]


# =============================================================================
# Vector Index Manager
# =============================================================================

class VectorIndexStore(ABC):
    """Abstract base class for vector index storage."""
    
    @abstractmethod
    async def upsert_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
    ) -> int:
        """Upsert vectors into the index."""
        pass
    
    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> int:
        """Delete vectors from the index."""
        pass
    
    @abstractmethod
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Query the index."""
        pass


class InMemoryVectorStore(VectorIndexStore):
    """In-memory vector store for testing."""
    
    def __init__(self):
        self._vectors: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
    
    async def upsert_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
    ) -> int:
        """Upsert vectors."""
        for id_, vec, meta in vectors:
            self._vectors[id_] = (vec, meta)
        return len(vectors)
    
    async def delete_vectors(self, ids: List[str]) -> int:
        """Delete vectors."""
        deleted = 0
        for id_ in ids:
            if id_ in self._vectors:
                del self._vectors[id_]
                deleted += 1
        return deleted
    
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Simple cosine similarity query."""
        results = []
        
        for id_, (stored_vec, meta) in self._vectors.items():
            # Apply filter if provided
            if filter:
                match = all(
                    meta.get(k) == v
                    for k, v in filter.items()
                )
                if not match:
                    continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(vector, stored_vec)
            results.append((id_, similarity, meta))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


class IncrementalIndexManager:
    """
    Manages incremental updates to the vector index.
    
    Allows adding, updating, and removing vectors without full re-indexing.
    """
    
    def __init__(self, store: VectorIndexStore):
        self.store = store
        self._pending_upserts: List[Tuple[str, List[float], Dict[str, Any]]] = []
        self._pending_deletes: List[str] = []
        self._batch_size = 100
        self._lock = asyncio.Lock()
    
    async def add_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        flush: bool = True,
    ) -> int:
        """Add vectors to the index."""
        async with self._lock:
            self._pending_upserts.extend(vectors)
            
            if flush or len(self._pending_upserts) >= self._batch_size:
                return await self._flush_upserts()
        return 0
    
    async def update_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
    ) -> int:
        """Update existing vectors."""
        return await self.add_vectors(vectors, flush=True)
    
    async def remove_vectors(
        self,
        ids: List[str],
        flush: bool = True,
    ) -> int:
        """Remove vectors from the index."""
        async with self._lock:
            self._pending_deletes.extend(ids)
            
            if flush or len(self._pending_deletes) >= self._batch_size:
                return await self._flush_deletes()
        return 0
    
    async def _flush_upserts(self) -> int:
        """Flush pending upserts to the store."""
        if not self._pending_upserts:
            return 0
        
        count = await self.store.upsert_vectors(self._pending_upserts)
        self._pending_upserts.clear()
        logger.info(f"Flushed {count} vectors to index")
        return count
    
    async def _flush_deletes(self) -> int:
        """Flush pending deletes to the store."""
        if not self._pending_deletes:
            return 0
        
        count = await self.store.delete_vectors(self._pending_deletes)
        self._pending_deletes.clear()
        logger.info(f"Deleted {count} vectors from index")
        return count
    
    async def flush_all(self) -> Tuple[int, int]:
        """Flush all pending operations."""
        async with self._lock:
            upserted = await self._flush_upserts()
            deleted = await self._flush_deletes()
        return upserted, deleted
    
    async def reindex_document(
        self,
        document_id: str,
        new_vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        old_chunk_ids: List[str],
    ) -> Tuple[int, int]:
        """
        Re-index a document by removing old chunks and adding new ones.
        
        This is done atomically to prevent query inconsistencies.
        """
        async with self._lock:
            # Delete old chunks
            deleted = await self.store.delete_vectors(old_chunk_ids)
            
            # Add new chunks
            added = await self.store.upsert_vectors(new_vectors)
            
            logger.info(
                f"Reindexed document {document_id}: "
                f"removed {deleted} chunks, added {added} chunks"
            )
            
            return added, deleted


# =============================================================================
# CPU Throttling & Scheduling
# =============================================================================

class ThrottleManager:
    """
    Manages CPU throttling for background processing.
    
    Limits threads during business hours and allows full speed during idle windows.
    """
    
    def __init__(self, config: Optional[ThrottleConfig] = None):
        self.config = config or ThrottleConfig()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._current_threads = 0
    
    def _is_business_hours(self, current: datetime) -> bool:
        """Check if current time is during business hours."""
        current_time = current.time()
        return self.config.business_hours_start <= current_time < self.config.business_hours_end
    
    def _is_idle_window(self, current: datetime) -> bool:
        """Check if current time is during idle window."""
        current_time = current.time()
        # Handle overnight window (2AM-5AM)
        if self.config.idle_window_start < self.config.idle_window_end:
            return self.config.idle_window_start <= current_time < self.config.idle_window_end
        else:
            # Wraps around midnight
            return current_time >= self.config.idle_window_start or current_time < self.config.idle_window_end
    
    def get_allowed_threads(self, current: Optional[datetime] = None) -> int:
        """Get the number of allowed threads for the current time."""
        current = current or _utcnow()
        
        if self._is_idle_window(current):
            return self.config.idle_threads
        elif self._is_business_hours(current):
            return self.config.business_hours_threads
        else:
            return self.config.off_hours_threads
    
    async def acquire(self) -> bool:
        """Acquire a processing slot."""
        allowed = self.get_allowed_threads()
        
        # Recreate semaphore if thread limit changed
        if self._semaphore is None or self._current_threads != allowed:
            self._semaphore = asyncio.Semaphore(allowed)
            self._current_threads = allowed
        
        await self._semaphore.acquire()
        return True
    
    def release(self) -> None:
        """Release a processing slot."""
        if self._semaphore:
            self._semaphore.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


# =============================================================================
# Autonomous Re-indexing
# =============================================================================

class ReindexScheduler:
    """
    Schedules and manages document re-indexing jobs.
    
    Uses priority queues and respects CPU throttling.
    """
    
    def __init__(
        self,
        throttle_manager: ThrottleManager,
        max_concurrent_jobs: int = 5,
    ):
        self.throttle = throttle_manager
        self.max_concurrent = max_concurrent_jobs
        
        self._job_queue: List[Tuple[int, datetime, ReindexJob]] = []  # Priority queue
        self._active_jobs: Dict[str, ReindexJob] = {}
        self._completed_jobs: List[ReindexJob] = []
        self._lock = asyncio.Lock()
        self._job_counter = 0
        self._running = False
    
    async def schedule_reindex(
        self,
        document_id: str,
        priority: ReindexPriority = ReindexPriority.MEDIUM,
    ) -> ReindexJob:
        """Schedule a document for re-indexing."""
        async with self._lock:
            self._job_counter += 1
            job = ReindexJob(
                job_id=f"reindex_{self._job_counter}_{document_id}",
                document_id=document_id,
                priority=priority,
                created_at=_utcnow(),
            )
            
            # Add to priority queue
            heapq.heappush(
                self._job_queue,
                (priority.value, job.created_at, job)
            )
            
            logger.info(f"Scheduled reindex job {job.job_id} with priority {priority.name}")
            return job
    
    async def get_next_job(self) -> Optional[ReindexJob]:
        """Get the next job to process."""
        async with self._lock:
            if not self._job_queue:
                return None
            
            if len(self._active_jobs) >= self.max_concurrent:
                return None
            
            _, _, job = heapq.heappop(self._job_queue)
            job.status = "running"
            job.started_at = _utcnow()
            self._active_jobs[job.job_id] = job
            
            return job
    
    async def complete_job(
        self,
        job_id: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Mark a job as completed."""
        async with self._lock:
            if job_id in self._active_jobs:
                job = self._active_jobs.pop(job_id)
                job.completed_at = _utcnow()
                job.status = "completed" if success else "failed"
                job.error = error
                self._completed_jobs.append(job)
                
                logger.info(
                    f"Completed reindex job {job_id}: "
                    f"{'success' if success else f'failed: {error}'}"
                )
    
    def get_queue_length(self) -> int:
        """Get the number of pending jobs."""
        return len(self._job_queue)
    
    def get_active_jobs(self) -> List[ReindexJob]:
        """Get currently active jobs."""
        return list(self._active_jobs.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "pending_jobs": len(self._job_queue),
            "active_jobs": len(self._active_jobs),
            "completed_jobs": len(self._completed_jobs),
            "total_processed": self._job_counter,
        }


# =============================================================================
# Document Processor
# =============================================================================

class DocumentProcessor(ABC):
    """Abstract base class for document processing."""
    
    @abstractmethod
    async def process_document(
        self,
        document_id: str,
        content: bytes,
    ) -> List[Tuple[str, str, List[float]]]:
        """
        Process a document and return chunks with embeddings.
        
        Returns:
            List of (chunk_id, chunk_text, embedding)
        """
        pass


class SimpleDocumentProcessor(DocumentProcessor):
    """
    Simple document processor that uses the ONNX embedder for production-ready embeddings.
    
    Falls back to a deterministic hash-based embedding only if the ONNX embedder
    is not available (e.g., model not downloaded yet).
    """
    
    def __init__(self, chunk_size: int = 500, embedder: Optional[Any] = None):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks
            embedder: Optional embedder with embed_text method. If None, will try to
                      load the ONNX embedder.
        """
        self.chunk_size = chunk_size
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
            logger.info("Initialized ONNX text embedder for document processing")
            return self._embedder
        except Exception as e:
            logger.warning(
                f"Failed to initialize ONNX embedder, using fallback: {e}"
            )
            return None
    
    async def process_document(
        self,
        document_id: str,
        content: bytes,
    ) -> List[Tuple[str, str, List[float]]]:
        """Process document into chunks with embeddings."""
        text = content.decode("utf-8", errors="ignore")
        chunks = []
        
        embedder = self._get_embedder()
        
        for i in range(0, len(text), self.chunk_size):
            chunk_text = text[i:i + self.chunk_size]
            chunk_id = f"{document_id}_chunk_{i // self.chunk_size}"
            
            if embedder is not None:
                # Use real embedder
                try:
                    embedding = embedder.embed_text(chunk_text)
                except Exception as e:
                    logger.warning(f"Embedding failed for chunk {chunk_id}: {e}")
                    embedding = self._fallback_embedding(chunk_text)
            else:
                # Fallback: deterministic hash-based embedding
                embedding = self._fallback_embedding(chunk_text)
            
            chunks.append((chunk_id, chunk_text, embedding))
        
        return chunks
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic fallback embedding based on text hash.
        
        This is NOT suitable for production semantic search but provides
        a consistent vector for testing and development.
        """
        # Use SHA-256 for better distribution
        h = hashlib.sha256(text.encode()).hexdigest()
        
        # Generate 384-dimensional vector to match MiniLM
        values = []
        for i in range(0, 64, 2):
            values.append((int(h[i:i+2], 16) - 128) / 128.0)
        
        # Extend to 384 dimensions by cycling
        while len(values) < 384:
            idx = len(values) % 32
            values.append(values[idx] * 0.5)
        
        # Normalize to unit vector
        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]
        
        return values


# =============================================================================
# Self-Improving RAG Service
# =============================================================================

class SelfImprovingRAGService:
    """
    Main service for self-improving RAG.
    
    Coordinates utility tracking, re-indexing, and index updates.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorIndexStore] = None,
        processor: Optional[DocumentProcessor] = None,
        throttle_config: Optional[ThrottleConfig] = None,
        utility_threshold: float = 0.4,
        max_concurrent_reindex: int = 5,
    ):
        self.vector_store = vector_store or InMemoryVectorStore()
        self.processor = processor or SimpleDocumentProcessor()
        
        self.utility_tracker = ChunkUtilityTracker()
        self.index_manager = IncrementalIndexManager(self.vector_store)
        self.throttle = ThrottleManager(throttle_config)
        self.scheduler = ReindexScheduler(self.throttle, max_concurrent_reindex)
        
        self.utility_threshold = utility_threshold
        self._document_content: Dict[str, bytes] = {}  # For testing
    
    async def index_document(
        self,
        document_id: str,
        content: bytes,
    ) -> int:
        """Index a new document."""
        self._document_content[document_id] = content
        
        # Process document
        chunks = await self.processor.process_document(document_id, content)
        
        # Register chunks for tracking
        for chunk_id, chunk_text, embedding in chunks:
            chunk_meta = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=document_id,
                content_hash=hashlib.md5(chunk_text.encode()).hexdigest(),
                created_at=_utcnow(),
            )
            self.utility_tracker.register_chunk(chunk_meta)
        
        # Add to vector index
        vectors = [
            (chunk_id, embedding, {"document_id": document_id, "text": text})
            for chunk_id, text, embedding in chunks
        ]
        
        count = await self.index_manager.add_vectors(vectors)
        logger.info(f"Indexed document {document_id}: {count} chunks")
        
        return count
    
    async def query(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Query the vector index with utility-adjusted scores."""
        raw_results = await self.vector_store.query(query_vector, top_k * 2, filter)
        
        # Adjust scores based on utility
        adjusted_results = []
        for chunk_id, score, metadata in raw_results:
            utility = self.utility_tracker.get_chunk_utility(chunk_id)
            adjusted_score = score * utility
            adjusted_results.append((chunk_id, adjusted_score, metadata))
        
        # Re-sort by adjusted score
        adjusted_results.sort(key=lambda x: x[1], reverse=True)
        
        return adjusted_results[:top_k]
    
    async def log_query_result(
        self,
        query_id: str,
        retrieved_chunks: List[str],
        chunks_in_answer: List[str],
        corrections: Optional[Dict[str, str]] = None,
    ) -> List[ChunkUtilityEvent]:
        """Log the result of a query for utility tracking."""
        events = []
        corrections = corrections or {}
        
        for chunk_id in retrieved_chunks:
            was_in_answer = chunk_id in chunks_in_answer
            correction_id = corrections.get(chunk_id)
            
            event = self.utility_tracker.log_retrieval(
                chunk_id=chunk_id,
                query_id=query_id,
                relevance_score=1.0,  # Simplified
                was_in_answer=was_in_answer,
                correction_id=correction_id,
            )
            events.append(event)
        
        return events
    
    async def check_and_schedule_reindex(self) -> int:
        """Check for low-utility documents and schedule re-indexing."""
        documents = self.utility_tracker.get_documents_needing_reindex(
            self.utility_threshold
        )
        
        scheduled = 0
        for doc_id, utility in documents:
            # Determine priority based on utility
            if utility < 0.2:
                priority = ReindexPriority.URGENT
            elif utility < 0.3:
                priority = ReindexPriority.HIGH
            else:
                priority = ReindexPriority.MEDIUM
            
            await self.scheduler.schedule_reindex(doc_id, priority)
            scheduled += 1
        
        logger.info(f"Scheduled {scheduled} documents for re-indexing")
        return scheduled
    
    async def process_reindex_job(self, job: ReindexJob) -> bool:
        """Process a single re-index job."""
        try:
            async with self.throttle:
                content = self._document_content.get(job.document_id)
                if not content:
                    raise ValueError(f"Document {job.document_id} not found")
                
                # Get old chunk IDs
                old_chunks = list(
                    self.utility_tracker._document_chunks.get(job.document_id, set())
                )
                
                # Re-process document
                new_chunks = await self.processor.process_document(
                    job.document_id, content
                )
                
                # Register new chunks
                for chunk_id, chunk_text, embedding in new_chunks:
                    chunk_meta = ChunkMetadata(
                        chunk_id=chunk_id,
                        document_id=job.document_id,
                        content_hash=hashlib.md5(chunk_text.encode()).hexdigest(),
                        created_at=_utcnow(),
                    )
                    self.utility_tracker.register_chunk(chunk_meta)
                
                # Update index
                new_vectors = [
                    (chunk_id, embedding, {"document_id": job.document_id, "text": text})
                    for chunk_id, text, embedding in new_chunks
                ]
                
                await self.index_manager.reindex_document(
                    job.document_id,
                    new_vectors,
                    old_chunks,
                )
                
                await self.scheduler.complete_job(job.job_id, success=True)
                return True
                
        except Exception as e:
            logger.error(f"Reindex job {job.job_id} failed: {e}")
            await self.scheduler.complete_job(job.job_id, success=False, error=str(e))
            return False
    
    async def run_reindex_cycle(self, max_jobs: int = 10) -> int:
        """Run a cycle of re-indexing jobs."""
        processed = 0
        
        while processed < max_jobs:
            job = await self.scheduler.get_next_job()
            if not job:
                break
            
            await self.process_reindex_job(job)
            processed += 1
        
        return processed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "utility_tracker": {
                "tracked_chunks": len(self.utility_tracker._chunks),
                "total_events": len(self.utility_tracker._events),
                "documents_tracked": len(self.utility_tracker._document_chunks),
            },
            "scheduler": self.scheduler.get_stats(),
            "current_threads": self.throttle.get_allowed_threads(),
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_self_improving_rag(
    vector_store: Optional[VectorIndexStore] = None,
    processor: Optional[DocumentProcessor] = None,
    throttle_config: Optional[ThrottleConfig] = None,
    utility_threshold: float = 0.4,
) -> SelfImprovingRAGService:
    """
    Create a self-improving RAG service.
    
    Args:
        vector_store: Vector index store implementation
        processor: Document processor implementation
        throttle_config: CPU throttling configuration
        utility_threshold: Utility threshold for re-indexing
        
    Returns:
        Configured SelfImprovingRAGService
    """
    return SelfImprovingRAGService(
        vector_store=vector_store,
        processor=processor,
        throttle_config=throttle_config,
        utility_threshold=utility_threshold,
    )

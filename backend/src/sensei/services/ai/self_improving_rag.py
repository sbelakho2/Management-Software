"""Self-improving RAG components with in-memory persistence for tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from enum import Enum
import asyncio
import hashlib
import math
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChunkUtilityStatus(str, Enum):
    USED = "used"
    IGNORED = "ignored"
    CORRECTED = "corrected"


class DocumentQuality(str, Enum):
    HIGH = "high"
    LOW = "low"
    NEEDS_REPROCESSING = "needs_reprocessing"


class ReindexPriority(int, Enum):
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class IndexingMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class ChunkMetadata:
    chunk_id: str
    document_id: str
    content_hash: str
    created_at: datetime
    utility_score: float = 1.0
    decay_factor: float = 1.0
    retrieval_count: int = 0
    last_retrieved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkUtilityEvent:
    chunk_id: str
    query_id: str
    relevance_score: float
    status: ChunkUtilityStatus
    timestamp: datetime = field(default_factory=_utcnow)
    was_in_answer: bool = False
    correction_id: str | None = None


@dataclass
class DocumentMetrics:
    document_id: str
    total_chunks: int
    used_count: int
    ignored_count: int
    corrected_count: int
    average_utility: float


@dataclass
class ReindexJob:
    job_id: str
    document_id: str
    priority: ReindexPriority
    status: str
    created_at: datetime = field(default_factory=_utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class ThrottleConfig:
    business_hours_start: time = time(8, 0)
    business_hours_end: time = time(18, 0)
    business_hours_threads: int = 1
    off_hours_threads: int = 4
    idle_window_start: time = time(2, 0)
    idle_window_end: time = time(5, 0)
    idle_threads: int = 8


class ChunkUtilityTracker:
    """Tracks per-chunk utility with decay/boost signals."""

    MIN_UTILITY = 0.1
    MAX_UTILITY = 2.0

    def __init__(self) -> None:
        self._chunks: dict[str, ChunkMetadata] = {}
        self._events: list[ChunkUtilityEvent] = []
        self._document_chunks: dict[str, list[str]] = {}

    def register_chunk(self, chunk: ChunkMetadata) -> None:
        self._chunks[chunk.chunk_id] = chunk
        self._document_chunks.setdefault(chunk.document_id, []).append(chunk.chunk_id)

    def remove_document(self, document_id: str) -> None:
        for chunk_id in self._document_chunks.get(document_id, []):
            self._chunks.pop(chunk_id, None)
        self._document_chunks.pop(document_id, None)

    def log_retrieval(
        self,
        chunk_id: str,
        query_id: str,
        relevance_score: float,
        was_in_answer: bool,
        correction_id: str | None = None,
    ) -> ChunkUtilityEvent:
        status = ChunkUtilityStatus.USED if was_in_answer else ChunkUtilityStatus.IGNORED
        if correction_id:
            status = ChunkUtilityStatus.CORRECTED

        event = ChunkUtilityEvent(
            chunk_id=chunk_id,
            query_id=query_id,
            relevance_score=relevance_score,
            was_in_answer=was_in_answer,
            status=status,
            correction_id=correction_id,
        )
        self._events.append(event)

        chunk = self._chunks.get(chunk_id)
        if chunk:
            if status == ChunkUtilityStatus.USED:
                chunk.utility_score = min(self.MAX_UTILITY, chunk.utility_score + 0.1)
            elif status == ChunkUtilityStatus.IGNORED:
                chunk.utility_score = max(self.MIN_UTILITY, chunk.utility_score * 0.9)
            else:
                chunk.utility_score = max(self.MIN_UTILITY, chunk.utility_score * 0.7)

            chunk.retrieval_count += 1
            chunk.last_retrieved_at = event.timestamp
        return event

    def get_chunk_utility(self, chunk_id: str) -> float:
        chunk = self._chunks.get(chunk_id)
        if not chunk:
            return 1.0
        return chunk.utility_score

    def get_low_utility_chunks(self, threshold: float) -> list[ChunkMetadata]:
        return [c for c in self._chunks.values() if c.utility_score < threshold]

    def get_document_metrics(self, document_id: str) -> DocumentMetrics | None:
        chunk_ids = self._document_chunks.get(document_id)
        if not chunk_ids:
            return None
        events = [e for e in self._events if e.chunk_id in chunk_ids]
        used = sum(1 for e in events if e.status == ChunkUtilityStatus.USED)
        ignored = sum(1 for e in events if e.status == ChunkUtilityStatus.IGNORED)
        corrected = sum(1 for e in events if e.status == ChunkUtilityStatus.CORRECTED)
        utilities = [self._chunks[cid].utility_score for cid in chunk_ids if cid in self._chunks]
        avg_utility = sum(utilities) / len(utilities) if utilities else 1.0
        return DocumentMetrics(
            document_id=document_id,
            total_chunks=len(chunk_ids),
            used_count=used,
            ignored_count=ignored,
            corrected_count=corrected,
            average_utility=avg_utility,
        )

    def get_documents_needing_reindex(self, threshold: float) -> list[tuple[str, float]]:
        needing: list[tuple[str, float]] = []
        for document_id in self._document_chunks:
            metrics = self.get_document_metrics(document_id)
            if metrics and metrics.average_utility < threshold:
                needing.append((document_id, metrics.average_utility))
        return needing

    def export_events(self) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": e.chunk_id,
                "query_id": e.query_id,
                "relevance_score": e.relevance_score,
                "status": e.status.value,
                "timestamp": e.timestamp.isoformat(),
                "was_in_answer": e.was_in_answer,
                "correction_id": e.correction_id,
            }
            for e in self._events
        ]


class InMemoryVectorStore:
    """Simple in-memory vector store."""

    def __init__(self) -> None:
        self._vectors: dict[str, tuple[list[float], dict[str, Any]]] = {}

    async def upsert_vectors(self, vectors: list[tuple[str, list[float], dict[str, Any]]]) -> int:
        for vid, vec, metadata in vectors:
            self._vectors[vid] = (vec, metadata)
        return len(vectors)

    async def delete_vectors(self, vector_ids: list[str]) -> int:
        deleted = 0
        for vid in vector_ids:
            if vid in self._vectors:
                deleted += 1
                self._vectors.pop(vid, None)
        return deleted

    async def query(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        results: list[tuple[str, float, dict[str, Any]]] = []
        for vid, (vec, metadata) in self._vectors.items():
            if filter and any(metadata.get(k) != v for k, v in filter.items()):
                continue
            score = self._cosine_similarity(vector, vec)
            results.append((vid, score, metadata))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


class IncrementalIndexManager:
    """Minimal incremental index manager."""

    def __init__(self, vector_store: InMemoryVectorStore) -> None:
        self.vector_store = vector_store
        self._pending_upserts: list[tuple[str, list[float], dict[str, Any]]] = []
        self._pending_deletes: list[str] = []

    async def add_vectors(self, vectors: list[tuple[str, list[float], dict[str, Any]]]) -> int:
        self._pending_upserts.extend(vectors)
        count = await self.vector_store.upsert_vectors(vectors)
        self._pending_upserts = []
        return count

    async def remove_vectors(self, vector_ids: list[str]) -> int:
        self._pending_deletes.extend(vector_ids)
        deleted = await self.vector_store.delete_vectors(vector_ids)
        self._pending_deletes = []
        return deleted

    async def update_vectors(self, vectors: list[tuple[str, list[float], dict[str, Any]]]) -> int:
        return await self.add_vectors(vectors)

    async def reindex_document(
        self,
        document_id: str,
        new_vectors: list[tuple[str, list[float], dict[str, Any]]],
        old_vector_ids: list[str],
    ) -> tuple[int, int]:
        added = await self.add_vectors(new_vectors)
        deleted = await self.remove_vectors(old_vector_ids)
        return added, deleted

    async def flush_all(self) -> tuple[int, int]:
        upserted = 0
        deleted = 0
        if self._pending_upserts:
            upserted = await self.vector_store.upsert_vectors(self._pending_upserts)
            self._pending_upserts = []
        if self._pending_deletes:
            deleted = await self.vector_store.delete_vectors(self._pending_deletes)
            self._pending_deletes = []
        return upserted, deleted


class ThrottleManager:
    """Throttle background processing based on time windows."""

    def __init__(self, config: ThrottleConfig | None = None) -> None:
        self.config = config or ThrottleConfig()
        self._semaphore = asyncio.Semaphore(self.config.off_hours_threads)

    def _is_business_hours(self, dt: datetime) -> bool:
        return self.config.business_hours_start <= dt.time() <= self.config.business_hours_end

    def _is_idle_window(self, dt: datetime) -> bool:
        return self.config.idle_window_start <= dt.time() <= self.config.idle_window_end

    def get_allowed_threads(self, dt: datetime | None = None) -> int:
        dt = dt or _utcnow()
        if self._is_idle_window(dt):
            return self.config.idle_threads
        if self._is_business_hours(dt):
            return self.config.business_hours_threads
        return self.config.off_hours_threads

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()

    async def __aenter__(self) -> "ThrottleManager":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.release()


class ReindexScheduler:
    """Schedules and runs re-index jobs."""

    def __init__(self, throttle: ThrottleManager, max_concurrent_jobs: int = 3) -> None:
        self.throttle = throttle
        self.max_concurrent_jobs = max_concurrent_jobs
        self._pending: list[ReindexJob] = []
        self._active: dict[str, ReindexJob] = {}
        self._completed: list[ReindexJob] = []

    async def schedule_reindex(
        self,
        document_id: str,
        priority: ReindexPriority = ReindexPriority.MEDIUM,
    ) -> ReindexJob:
        job = ReindexJob(
            job_id=f"reindex_{document_id}_{len(self._pending)}",
            document_id=document_id,
            priority=priority,
            status="pending",
        )
        self._pending.append(job)
        return job

    async def get_next_job(self) -> ReindexJob | None:
        if len(self._active) >= self.max_concurrent_jobs:
            return None
        if not self._pending:
            return None
        self._pending.sort(key=lambda j: j.priority.value)
        job = self._pending.pop(0)
        job.status = "running"
        job.started_at = _utcnow()
        self._active[job.job_id] = job
        return job

    async def complete_job(self, job_id: str, success: bool, error: str | None = None) -> None:
        job = self._active.pop(job_id, None)
        if not job:
            return
        job.completed_at = _utcnow()
        if success:
            job.status = "completed"
        else:
            job.status = "failed"
            job.error = error
        self._completed.append(job)

    def get_queue_length(self) -> int:
        return len(self._pending)

    def get_stats(self) -> dict[str, int]:
        return {
            "pending_jobs": len(self._pending),
            "active_jobs": len(self._active),
            "completed_jobs": len(self._completed),
        }


class SimpleDocumentProcessor:
    """Simple document processor producing embeddings."""

    def __init__(self, chunk_size: int = 200) -> None:
        self.chunk_size = chunk_size

    def _embed_text(self, text: str, dim: int = 16) -> list[float]:
        values: list[float] = []
        for i in range(dim):
            digest = hashlib.sha256(f"{text}:{i}".encode("utf-8")).digest()
            value = int.from_bytes(digest[:4], "big") / 2**32
            values.append(value)
        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0:
            return values
        return [v / norm for v in values]

    async def process_document(self, document_id: str, content: bytes) -> list[tuple[str, str, list[float]]]:
        text = content.decode("utf-8", errors="ignore")
        chunks: list[tuple[str, str, list[float]]] = []
        if not text:
            return chunks
        for idx in range(0, len(text), self.chunk_size):
            chunk_text = text[idx : idx + self.chunk_size].strip()
            if not chunk_text:
                continue
            chunk_id = f"{document_id}_chunk_{idx // self.chunk_size}"
            embedding = self._embed_text(chunk_text)
            chunks.append((chunk_id, chunk_text, embedding))
        return chunks


class SelfImprovingRAGService:
    """Top-level orchestrator for self-improving RAG."""

    def __init__(
        self,
        *,
        vector_store: InMemoryVectorStore,
        utility_tracker: ChunkUtilityTracker,
        index_manager: IncrementalIndexManager,
        throttle: ThrottleManager,
        scheduler: ReindexScheduler,
        processor: SimpleDocumentProcessor,
        utility_threshold: float = 0.4,
    ) -> None:
        self.vector_store = vector_store
        self.utility_tracker = utility_tracker
        self.index_manager = index_manager
        self.throttle = throttle
        self.scheduler = scheduler
        self.processor = processor
        self.utility_threshold = utility_threshold
        self._documents: dict[str, bytes] = {}

    async def index_document(self, document_id: str, content: bytes) -> int:
        self._documents[document_id] = content
        chunks = await self.processor.process_document(document_id, content)
        if not chunks:
            return 0
        vectors: list[tuple[str, list[float], dict[str, Any]]] = []
        for chunk_id, text, embedding in chunks:
            vectors.append((chunk_id, embedding, {"document_id": document_id, "text": text}))
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=document_id,
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                created_at=_utcnow(),
            )
            self.utility_tracker.register_chunk(metadata)
        count = await self.index_manager.add_vectors(vectors)
        return count

    async def query(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[str, float, dict[str, Any]]]:
        results = await self.vector_store.query(query_embedding, top_k=top_k)
        adjusted: list[tuple[str, float, dict[str, Any]]] = []
        for chunk_id, score, metadata in results:
            utility = self.utility_tracker.get_chunk_utility(chunk_id)
            adjusted.append((chunk_id, score * utility, metadata))
        adjusted.sort(key=lambda x: x[1], reverse=True)
        return adjusted

    async def log_query_result(
        self,
        *,
        query_id: str,
        retrieved_chunks: list[str],
        chunks_in_answer: list[str],
        correction_id: str | None = None,
    ) -> list[ChunkUtilityEvent]:
        events: list[ChunkUtilityEvent] = []
        retrieved_set = set(retrieved_chunks)
        in_answer_set = set(chunks_in_answer)
        for chunk_id in retrieved_set:
            event = self.utility_tracker.log_retrieval(
                chunk_id=chunk_id,
                query_id=query_id,
                relevance_score=0.9,
                was_in_answer=chunk_id in in_answer_set,
                correction_id=correction_id if chunk_id in in_answer_set else None,
            )
            events.append(event)
        return events

    async def check_and_schedule_reindex(self) -> int:
        needing = self.utility_tracker.get_documents_needing_reindex(self.utility_threshold)
        scheduled = 0
        for document_id, _score in needing:
            await self.scheduler.schedule_reindex(document_id, ReindexPriority.HIGH)
            scheduled += 1
        return scheduled

    async def process_reindex_job(self, job: ReindexJob) -> bool:
        document_id = job.document_id
        content = self._documents.get(document_id)
        if content is None:
            await self.scheduler.complete_job(job.job_id, success=False, error="Document missing")
            return False
        old_ids = list(self.utility_tracker._document_chunks.get(document_id, []))
        self.utility_tracker.remove_document(document_id)
        chunks = await self.processor.process_document(document_id, content)
        vectors: list[tuple[str, list[float], dict[str, Any]]] = []
        for chunk_id, text, embedding in chunks:
            vectors.append((chunk_id, embedding, {"document_id": document_id, "text": text}))
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=document_id,
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                created_at=_utcnow(),
            )
            self.utility_tracker.register_chunk(metadata)
        await self.index_manager.reindex_document(document_id, vectors, old_ids)
        await self.scheduler.complete_job(job.job_id, success=True)
        return True

    async def run_reindex_cycle(self, max_jobs: int = 10) -> int:
        processed = 0
        while processed < max_jobs:
            job = await self.scheduler.get_next_job()
            if job is None:
                break
            await self.process_reindex_job(job)
            processed += 1
        return processed

    def get_stats(self) -> dict[str, Any]:
        return {
            "utility_tracker": {
                "total_chunks": len(self.utility_tracker._chunks),
                "total_events": len(self.utility_tracker._events),
            },
            "scheduler": self.scheduler.get_stats(),
            "current_threads": self.throttle.get_allowed_threads(_utcnow()),
        }


def create_self_improving_rag(
    *,
    vector_store: InMemoryVectorStore | None = None,
    utility_threshold: float = 0.4,
    throttle_config: ThrottleConfig | None = None,
) -> SelfImprovingRAGService:
    store = vector_store or InMemoryVectorStore()
    utility_tracker = ChunkUtilityTracker()
    index_manager = IncrementalIndexManager(store)
    throttle = ThrottleManager(throttle_config)
    scheduler = ReindexScheduler(throttle)
    processor = SimpleDocumentProcessor()
    return SelfImprovingRAGService(
        vector_store=store,
        utility_tracker=utility_tracker,
        index_manager=index_manager,
        throttle=throttle,
        scheduler=scheduler,
        processor=processor,
        utility_threshold=utility_threshold,
    )

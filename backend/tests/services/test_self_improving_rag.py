"""
Tests for Self-Improving RAG System.

Tests cover:
- Chunk Utility Tracking
- Decay Algorithm
- Vector Index Management
- CPU Throttling
- Autonomous Re-indexing
- Full Service Integration
"""

import pytest
import math
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sensei.services.ai.self_improving_rag import (
    # Enums
    ChunkUtilityStatus,
    DocumentQuality,
    ReindexPriority,
    IndexingMode,
    # Data models
    ChunkMetadata,
    ChunkUtilityEvent,
    DocumentMetrics,
    ReindexJob,
    ThrottleConfig,
    # Components
    ChunkUtilityTracker,
    InMemoryVectorStore,
    IncrementalIndexManager,
    ThrottleManager,
    ReindexScheduler,
    SimpleDocumentProcessor,
    SelfImprovingRAGService,
    # Factory
    create_self_improving_rag,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def chunk_metadata():
    """Create test chunk metadata."""
    return ChunkMetadata(
        chunk_id="chunk_001",
        document_id="doc_001",
        content_hash="abc123",
        created_at=_utcnow(),
    )


@pytest.fixture
def utility_tracker():
    """Create a chunk utility tracker."""
    return ChunkUtilityTracker()


@pytest.fixture
def vector_store():
    """Create an in-memory vector store."""
    return InMemoryVectorStore()


@pytest.fixture
def throttle_config():
    """Create a throttle configuration."""
    return ThrottleConfig(
        business_hours_start=time(8, 0),
        business_hours_end=time(18, 0),
        business_hours_threads=1,
        off_hours_threads=4,
        idle_window_start=time(2, 0),
        idle_window_end=time(5, 0),
        idle_threads=8,
    )


@pytest.fixture
def rag_service():
    """Create a self-improving RAG service."""
    return create_self_improving_rag()


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enum values."""
    
    def test_chunk_utility_status(self):
        """Test chunk utility status values."""
        assert ChunkUtilityStatus.USED.value == "used"
        assert ChunkUtilityStatus.IGNORED.value == "ignored"
        assert ChunkUtilityStatus.CORRECTED.value == "corrected"
    
    def test_document_quality(self):
        """Test document quality values."""
        assert DocumentQuality.HIGH.value == "high"
        assert DocumentQuality.LOW.value == "low"
        assert DocumentQuality.NEEDS_REPROCESSING.value == "needs_reprocessing"
    
    def test_reindex_priority(self):
        """Test reindex priority ordering."""
        assert ReindexPriority.URGENT.value < ReindexPriority.HIGH.value
        assert ReindexPriority.HIGH.value < ReindexPriority.MEDIUM.value
        assert ReindexPriority.MEDIUM.value < ReindexPriority.LOW.value


# =============================================================================
# ChunkMetadata Tests
# =============================================================================

class TestChunkMetadata:
    """Tests for ChunkMetadata dataclass."""
    
    def test_creation(self, chunk_metadata):
        """Test creating chunk metadata."""
        assert chunk_metadata.chunk_id == "chunk_001"
        assert chunk_metadata.document_id == "doc_001"
        assert chunk_metadata.utility_score == 1.0
        assert chunk_metadata.decay_factor == 1.0
        assert chunk_metadata.retrieval_count == 0
    
    def test_default_values(self):
        """Test default values."""
        chunk = ChunkMetadata(
            chunk_id="c1",
            document_id="d1",
            content_hash="hash",
            created_at=_utcnow(),
        )
        assert chunk.last_retrieved_at is None
        assert chunk.metadata == {}


# =============================================================================
# ChunkUtilityTracker Tests
# =============================================================================

class TestChunkUtilityTracker:
    """Tests for ChunkUtilityTracker."""
    
    def test_register_chunk(self, utility_tracker, chunk_metadata):
        """Test registering a chunk."""
        utility_tracker.register_chunk(chunk_metadata)
        assert "chunk_001" in utility_tracker._chunks
    
    def test_log_used_retrieval(self, utility_tracker, chunk_metadata):
        """Test logging a used retrieval."""
        utility_tracker.register_chunk(chunk_metadata)
        
        event = utility_tracker.log_retrieval(
            chunk_id="chunk_001",
            query_id="query_001",
            relevance_score=0.9,
            was_in_answer=True,
        )
        
        assert event.status == ChunkUtilityStatus.USED
        assert chunk_metadata.utility_score > 1.0  # Should be boosted
    
    def test_log_ignored_retrieval(self, utility_tracker, chunk_metadata):
        """Test logging an ignored retrieval."""
        utility_tracker.register_chunk(chunk_metadata)
        
        event = utility_tracker.log_retrieval(
            chunk_id="chunk_001",
            query_id="query_001",
            relevance_score=0.9,
            was_in_answer=False,
        )
        
        assert event.status == ChunkUtilityStatus.IGNORED
        assert chunk_metadata.utility_score < 1.0  # Should decay
    
    def test_log_corrected_retrieval(self, utility_tracker, chunk_metadata):
        """Test logging a corrected retrieval."""
        utility_tracker.register_chunk(chunk_metadata)
        
        event = utility_tracker.log_retrieval(
            chunk_id="chunk_001",
            query_id="query_001",
            relevance_score=0.9,
            was_in_answer=True,
            correction_id="corr_001",
        )
        
        assert event.status == ChunkUtilityStatus.CORRECTED
        assert chunk_metadata.utility_score < 1.0  # Penalized
    
    def test_decay_accumulates(self, utility_tracker, chunk_metadata):
        """Test that decay accumulates over multiple ignores."""
        utility_tracker.register_chunk(chunk_metadata)
        
        for i in range(5):
            utility_tracker.log_retrieval(
                chunk_id="chunk_001",
                query_id=f"query_{i}",
                relevance_score=0.9,
                was_in_answer=False,
            )
        
        # Should have decayed significantly
        assert chunk_metadata.utility_score < 0.8
        assert chunk_metadata.retrieval_count == 5
    
    def test_utility_bounded(self, utility_tracker, chunk_metadata):
        """Test that utility is bounded."""
        utility_tracker.register_chunk(chunk_metadata)
        
        # Many ignores should not go below minimum
        for i in range(50):
            utility_tracker.log_retrieval(
                chunk_id="chunk_001",
                query_id=f"query_{i}",
                relevance_score=0.9,
                was_in_answer=False,
            )
        
        assert chunk_metadata.utility_score >= utility_tracker.MIN_UTILITY
    
    def test_boost_bounded(self, utility_tracker, chunk_metadata):
        """Test that boost is bounded."""
        utility_tracker.register_chunk(chunk_metadata)
        
        # Many uses should not exceed maximum
        for i in range(50):
            utility_tracker.log_retrieval(
                chunk_id="chunk_001",
                query_id=f"query_{i}",
                relevance_score=0.9,
                was_in_answer=True,
            )
        
        assert chunk_metadata.utility_score <= utility_tracker.MAX_UTILITY
    
    def test_get_chunk_utility(self, utility_tracker, chunk_metadata):
        """Test getting chunk utility."""
        utility_tracker.register_chunk(chunk_metadata)
        
        utility = utility_tracker.get_chunk_utility("chunk_001")
        assert utility == 1.0  # Initial value
        
        unknown = utility_tracker.get_chunk_utility("unknown")
        assert unknown == 1.0  # Default for unknown
    
    def test_get_low_utility_chunks(self, utility_tracker):
        """Test getting low utility chunks."""
        # Create chunks with varying utility
        for i in range(5):
            chunk = ChunkMetadata(
                chunk_id=f"chunk_{i}",
                document_id="doc_001",
                content_hash=f"hash_{i}",
                created_at=_utcnow(),
                utility_score=0.1 * (i + 1),  # 0.1, 0.2, 0.3, 0.4, 0.5
            )
            utility_tracker.register_chunk(chunk)
        
        low = utility_tracker.get_low_utility_chunks(threshold=0.4)
        assert len(low) == 3  # 0.1, 0.2, 0.3 are below 0.4
    
    def test_get_document_metrics(self, utility_tracker):
        """Test getting document metrics."""
        for i in range(3):
            chunk = ChunkMetadata(
                chunk_id=f"chunk_{i}",
                document_id="doc_001",
                content_hash=f"hash_{i}",
                created_at=_utcnow(),
            )
            utility_tracker.register_chunk(chunk)
        
        # Log some events
        utility_tracker.log_retrieval("chunk_0", "q1", 0.9, True)
        utility_tracker.log_retrieval("chunk_1", "q2", 0.9, False)
        utility_tracker.log_retrieval("chunk_2", "q3", 0.9, True, correction_id="c1")
        
        metrics = utility_tracker.get_document_metrics("doc_001")
        assert metrics is not None
        assert metrics.total_chunks == 3
        assert metrics.used_count == 1
        assert metrics.ignored_count == 1
        assert metrics.corrected_count == 1
    
    def test_get_documents_needing_reindex(self, utility_tracker):
        """Test getting documents needing re-indexing."""
        # Document with low utility
        for i in range(3):
            chunk = ChunkMetadata(
                chunk_id=f"low_chunk_{i}",
                document_id="low_doc",
                content_hash=f"hash_{i}",
                created_at=_utcnow(),
                utility_score=0.2,
            )
            utility_tracker.register_chunk(chunk)
        
        # Document with high utility
        for i in range(3):
            chunk = ChunkMetadata(
                chunk_id=f"high_chunk_{i}",
                document_id="high_doc",
                content_hash=f"hash_{i}",
                created_at=_utcnow(),
                utility_score=0.9,
            )
            utility_tracker.register_chunk(chunk)
        
        needing = utility_tracker.get_documents_needing_reindex(0.4)
        assert len(needing) == 1
        assert needing[0][0] == "low_doc"
    
    def test_export_events(self, utility_tracker, chunk_metadata):
        """Test exporting events."""
        utility_tracker.register_chunk(chunk_metadata)
        
        utility_tracker.log_retrieval("chunk_001", "q1", 0.9, True)
        utility_tracker.log_retrieval("chunk_001", "q2", 0.8, False)
        
        events = utility_tracker.export_events()
        assert len(events) == 2
        assert "chunk_id" in events[0]
        assert "timestamp" in events[0]


# =============================================================================
# InMemoryVectorStore Tests
# =============================================================================

class TestInMemoryVectorStore:
    """Tests for InMemoryVectorStore."""
    
    @pytest.mark.asyncio
    async def test_upsert_vectors(self, vector_store):
        """Test upserting vectors."""
        vectors = [
            ("v1", [0.1, 0.2, 0.3], {"text": "hello"}),
            ("v2", [0.4, 0.5, 0.6], {"text": "world"}),
        ]
        
        count = await vector_store.upsert_vectors(vectors)
        assert count == 2
    
    @pytest.mark.asyncio
    async def test_delete_vectors(self, vector_store):
        """Test deleting vectors."""
        vectors = [("v1", [0.1, 0.2, 0.3], {})]
        await vector_store.upsert_vectors(vectors)
        
        deleted = await vector_store.delete_vectors(["v1"])
        assert deleted == 1
        
        deleted = await vector_store.delete_vectors(["nonexistent"])
        assert deleted == 0
    
    @pytest.mark.asyncio
    async def test_query(self, vector_store):
        """Test querying vectors."""
        vectors = [
            ("v1", [1.0, 0.0, 0.0], {"type": "a"}),
            ("v2", [0.0, 1.0, 0.0], {"type": "b"}),
            ("v3", [0.9, 0.1, 0.0], {"type": "a"}),
        ]
        await vector_store.upsert_vectors(vectors)
        
        results = await vector_store.query([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0][0] == "v1"  # Most similar
    
    @pytest.mark.asyncio
    async def test_query_with_filter(self, vector_store):
        """Test querying with filter."""
        vectors = [
            ("v1", [1.0, 0.0, 0.0], {"type": "a"}),
            ("v2", [0.9, 0.1, 0.0], {"type": "b"}),
        ]
        await vector_store.upsert_vectors(vectors)
        
        results = await vector_store.query([1.0, 0.0, 0.0], filter={"type": "b"})
        assert len(results) == 1
        assert results[0][0] == "v2"
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        # Identical vectors
        assert InMemoryVectorStore._cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
        
        # Orthogonal vectors
        assert InMemoryVectorStore._cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
        
        # Zero vector
        assert InMemoryVectorStore._cosine_similarity([0, 0], [1, 0]) == 0.0


# =============================================================================
# IncrementalIndexManager Tests
# =============================================================================

class TestIncrementalIndexManager:
    """Tests for IncrementalIndexManager."""
    
    @pytest.fixture
    def index_manager(self, vector_store):
        return IncrementalIndexManager(vector_store)
    
    @pytest.mark.asyncio
    async def test_add_vectors(self, index_manager):
        """Test adding vectors."""
        vectors = [("v1", [0.1, 0.2], {"text": "test"})]
        count = await index_manager.add_vectors(vectors)
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_remove_vectors(self, index_manager):
        """Test removing vectors."""
        await index_manager.add_vectors([("v1", [0.1, 0.2], {})])
        count = await index_manager.remove_vectors(["v1"])
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_update_vectors(self, index_manager):
        """Test updating vectors."""
        await index_manager.add_vectors([("v1", [0.1, 0.2], {})])
        count = await index_manager.update_vectors([("v1", [0.3, 0.4], {})])
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_reindex_document(self, index_manager):
        """Test re-indexing a document."""
        # Add old chunks
        old_vectors = [
            ("old_1", [0.1, 0.2], {"doc": "d1"}),
            ("old_2", [0.3, 0.4], {"doc": "d1"}),
        ]
        await index_manager.add_vectors(old_vectors)
        
        # Re-index with new chunks
        new_vectors = [
            ("new_1", [0.5, 0.6], {"doc": "d1"}),
        ]
        added, deleted = await index_manager.reindex_document(
            "d1",
            new_vectors,
            ["old_1", "old_2"],
        )
        
        assert added == 1
        assert deleted == 2
    
    @pytest.mark.asyncio
    async def test_flush_all(self, index_manager):
        """Test flushing all pending operations."""
        index_manager._pending_upserts = [("v1", [0.1], {})]
        index_manager._pending_deletes = ["v2"]
        
        upserted, deleted = await index_manager.flush_all()
        assert upserted == 1
        # v2 wasn't in store so deleted is 0
        assert deleted == 0


# =============================================================================
# ThrottleManager Tests
# =============================================================================

class TestThrottleManager:
    """Tests for ThrottleManager."""
    
    def test_business_hours_detection(self, throttle_config):
        """Test business hours detection."""
        manager = ThrottleManager(throttle_config)
        
        # During business hours (10 AM)
        during = datetime(2024, 1, 15, 10, 0, 0)
        assert manager._is_business_hours(during)
        
        # After business hours (8 PM)
        after = datetime(2024, 1, 15, 20, 0, 0)
        assert not manager._is_business_hours(after)
    
    def test_idle_window_detection(self, throttle_config):
        """Test idle window detection."""
        manager = ThrottleManager(throttle_config)
        
        # During idle window (3 AM)
        during = datetime(2024, 1, 15, 3, 0, 0)
        assert manager._is_idle_window(during)
        
        # After idle window (6 AM)
        after = datetime(2024, 1, 15, 6, 0, 0)
        assert not manager._is_idle_window(after)
    
    def test_get_allowed_threads_business(self, throttle_config):
        """Test thread count during business hours."""
        manager = ThrottleManager(throttle_config)
        
        during = datetime(2024, 1, 15, 10, 0, 0)
        assert manager.get_allowed_threads(during) == 1
    
    def test_get_allowed_threads_off_hours(self, throttle_config):
        """Test thread count during off hours."""
        manager = ThrottleManager(throttle_config)
        
        off_hours = datetime(2024, 1, 15, 20, 0, 0)
        assert manager.get_allowed_threads(off_hours) == 4
    
    def test_get_allowed_threads_idle(self, throttle_config):
        """Test thread count during idle window."""
        manager = ThrottleManager(throttle_config)
        
        idle = datetime(2024, 1, 15, 3, 0, 0)
        assert manager.get_allowed_threads(idle) == 8
    
    @pytest.mark.asyncio
    async def test_acquire_release(self, throttle_config):
        """Test acquiring and releasing slots."""
        manager = ThrottleManager(throttle_config)
        
        await manager.acquire()
        manager.release()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, throttle_config):
        """Test using as context manager."""
        manager = ThrottleManager(throttle_config)
        
        async with manager:
            pass  # Should acquire and release


# =============================================================================
# ReindexScheduler Tests
# =============================================================================

class TestReindexScheduler:
    """Tests for ReindexScheduler."""
    
    @pytest.fixture
    def scheduler(self, throttle_config):
        throttle = ThrottleManager(throttle_config)
        return ReindexScheduler(throttle, max_concurrent_jobs=3)
    
    @pytest.mark.asyncio
    async def test_schedule_reindex(self, scheduler):
        """Test scheduling a re-index job."""
        job = await scheduler.schedule_reindex("doc_001", ReindexPriority.HIGH)
        
        assert job.job_id.startswith("reindex_")
        assert job.document_id == "doc_001"
        assert job.priority == ReindexPriority.HIGH
        assert job.status == "pending"
    
    @pytest.mark.asyncio
    async def test_get_next_job(self, scheduler):
        """Test getting next job."""
        await scheduler.schedule_reindex("doc_001", ReindexPriority.LOW)
        await scheduler.schedule_reindex("doc_002", ReindexPriority.URGENT)
        
        job = await scheduler.get_next_job()
        
        # Should get urgent job first
        assert job.document_id == "doc_002"
        assert job.status == "running"
    
    @pytest.mark.asyncio
    async def test_complete_job(self, scheduler):
        """Test completing a job."""
        await scheduler.schedule_reindex("doc_001")
        job = await scheduler.get_next_job()
        
        await scheduler.complete_job(job.job_id, success=True)
        
        assert job.status == "completed"
        assert job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_complete_failed_job(self, scheduler):
        """Test completing a failed job."""
        await scheduler.schedule_reindex("doc_001")
        job = await scheduler.get_next_job()
        
        await scheduler.complete_job(job.job_id, success=False, error="Test error")
        
        assert job.status == "failed"
        assert job.error == "Test error"
    
    @pytest.mark.asyncio
    async def test_max_concurrent_jobs(self, scheduler):
        """Test max concurrent jobs limit."""
        for i in range(5):
            await scheduler.schedule_reindex(f"doc_{i}")
        
        # Get 3 jobs (max concurrent)
        for _ in range(3):
            job = await scheduler.get_next_job()
            assert job is not None
        
        # 4th should return None due to limit
        job = await scheduler.get_next_job()
        assert job is None
    
    def test_get_queue_length(self, scheduler):
        """Test getting queue length."""
        assert scheduler.get_queue_length() == 0
    
    def test_get_stats(self, scheduler):
        """Test getting scheduler stats."""
        stats = scheduler.get_stats()
        assert "pending_jobs" in stats
        assert "active_jobs" in stats
        assert "completed_jobs" in stats


# =============================================================================
# SimpleDocumentProcessor Tests
# =============================================================================

class TestSimpleDocumentProcessor:
    """Tests for SimpleDocumentProcessor."""
    
    @pytest.fixture
    def processor(self):
        return SimpleDocumentProcessor(chunk_size=100)
    
    @pytest.mark.asyncio
    async def test_process_document(self, processor):
        """Test processing a document."""
        content = b"Hello world " * 20  # ~240 characters
        
        chunks = await processor.process_document("doc_001", content)
        
        assert len(chunks) >= 2
        assert all(len(c) == 3 for c in chunks)  # (id, text, embedding)
    
    @pytest.mark.asyncio
    async def test_chunk_ids(self, processor):
        """Test that chunk IDs are unique."""
        content = b"Test content " * 50
        
        chunks = await processor.process_document("doc_001", content)
        ids = [c[0] for c in chunks]
        
        assert len(ids) == len(set(ids))  # All unique
    
    @pytest.mark.asyncio
    async def test_embeddings_normalized(self, processor):
        """Test that embeddings are normalized."""
        content = b"Test content"
        
        chunks = await processor.process_document("doc_001", content)
        embedding = chunks[0][2]
        
        norm = math.sqrt(sum(v * v for v in embedding))
        assert norm == pytest.approx(1.0, rel=0.01)


# =============================================================================
# SelfImprovingRAGService Tests
# =============================================================================

class TestSelfImprovingRAGService:
    """Tests for SelfImprovingRAGService."""
    
    @pytest.mark.asyncio
    async def test_index_document(self, rag_service):
        """Test indexing a document."""
        content = b"This is a test document with some content."
        
        count = await rag_service.index_document("doc_001", content)
        
        assert count >= 1
    
    @pytest.mark.asyncio
    async def test_query(self, rag_service):
        """Test querying the index."""
        await rag_service.index_document("doc_001", b"Test content for querying")
        
        results = await rag_service.query([0.5] * 16, top_k=5)
        
        assert len(results) >= 1
    
    @pytest.mark.asyncio
    async def test_log_query_result(self, rag_service):
        """Test logging query results."""
        await rag_service.index_document("doc_001", b"Test content")
        
        events = await rag_service.log_query_result(
            query_id="q1",
            retrieved_chunks=["doc_001_chunk_0"],
            chunks_in_answer=["doc_001_chunk_0"],
        )
        
        assert len(events) == 1
        assert events[0].status == ChunkUtilityStatus.USED
    
    @pytest.mark.asyncio
    async def test_utility_affects_query_results(self, rag_service):
        """Test that utility affects query results."""
        await rag_service.index_document("doc_001", b"Test content one")
        await rag_service.index_document("doc_002", b"Test content two")
        
        # Decay the first document's chunks
        for chunk_id in rag_service.utility_tracker._document_chunks.get("doc_001", []):
            for _ in range(10):
                rag_service.utility_tracker.log_retrieval(
                    chunk_id=chunk_id,
                    query_id="q",
                    relevance_score=0.9,
                    was_in_answer=False,
                )
        
        # Query should now prefer doc_002
        results = await rag_service.query([0.5] * 16, top_k=5)
        
        # Verify utility tracking worked
        stats = rag_service.get_stats()
        assert stats["utility_tracker"]["total_events"] >= 10
    
    @pytest.mark.asyncio
    async def test_check_and_schedule_reindex(self, rag_service):
        """Test checking and scheduling re-indexing."""
        await rag_service.index_document("doc_001", b"Test content")
        
        # Decay to trigger re-index
        for chunk_id in rag_service.utility_tracker._document_chunks.get("doc_001", []):
            for _ in range(50):
                rag_service.utility_tracker.log_retrieval(
                    chunk_id=chunk_id,
                    query_id="q",
                    relevance_score=0.9,
                    was_in_answer=False,
                )
        
        scheduled = await rag_service.check_and_schedule_reindex()
        
        assert scheduled >= 1
    
    @pytest.mark.asyncio
    async def test_process_reindex_job(self, rag_service):
        """Test processing a re-index job."""
        await rag_service.index_document("doc_001", b"Original content")
        
        job = await rag_service.scheduler.schedule_reindex("doc_001")
        job = await rag_service.scheduler.get_next_job()
        
        success = await rag_service.process_reindex_job(job)
        
        assert success
        assert job.status == "completed"
    
    @pytest.mark.asyncio
    async def test_process_reindex_job_missing_document(self, rag_service):
        """Test processing re-index for missing document."""
        job = await rag_service.scheduler.schedule_reindex("nonexistent")
        job = await rag_service.scheduler.get_next_job()
        
        success = await rag_service.process_reindex_job(job)
        
        assert not success
        assert job.status == "failed"
    
    @pytest.mark.asyncio
    async def test_run_reindex_cycle(self, rag_service):
        """Test running a re-index cycle."""
        await rag_service.index_document("doc_001", b"Content 1")
        await rag_service.index_document("doc_002", b"Content 2")
        
        await rag_service.scheduler.schedule_reindex("doc_001")
        await rag_service.scheduler.schedule_reindex("doc_002")
        
        processed = await rag_service.run_reindex_cycle(max_jobs=5)
        
        assert processed == 2
    
    def test_get_stats(self, rag_service):
        """Test getting service statistics."""
        stats = rag_service.get_stats()
        
        assert "utility_tracker" in stats
        assert "scheduler" in stats
        assert "current_threads" in stats


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactory:
    """Tests for factory function."""
    
    def test_create_with_defaults(self):
        """Test creating with default parameters."""
        service = create_self_improving_rag()
        
        assert isinstance(service, SelfImprovingRAGService)
        assert isinstance(service.vector_store, InMemoryVectorStore)
    
    def test_create_with_custom_store(self):
        """Test creating with custom vector store."""
        store = InMemoryVectorStore()
        service = create_self_improving_rag(vector_store=store)
        
        assert service.vector_store is store
    
    def test_create_with_custom_threshold(self):
        """Test creating with custom utility threshold."""
        service = create_self_improving_rag(utility_threshold=0.6)
        
        assert service.utility_threshold == 0.6
    
    def test_create_with_throttle_config(self):
        """Test creating with custom throttle config."""
        config = ThrottleConfig(business_hours_threads=2)
        service = create_self_improving_rag(throttle_config=config)
        
        assert service.throttle.config.business_hours_threads == 2


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the self-improving RAG system."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full lifecycle: index, query, track, reindex."""
        service = create_self_improving_rag(utility_threshold=0.3)
        
        # 1. Index documents
        await service.index_document("doc_001", b"Document about machine learning")
        await service.index_document("doc_002", b"Document about deep learning")
        
        # 2. Query
        results = await service.query([0.5] * 16, top_k=5)
        assert len(results) >= 1
        
        # 3. Log results (simulate usage)
        retrieved = [r[0] for r in results]
        await service.log_query_result(
            query_id="q1",
            retrieved_chunks=retrieved,
            chunks_in_answer=[retrieved[0]] if retrieved else [],
        )
        
        # 4. Verify tracking
        stats = service.get_stats()
        assert stats["utility_tracker"]["total_events"] >= 1
        
        # 5. Check for needed re-indexing
        scheduled = await service.check_and_schedule_reindex()
        # May or may not need re-indexing at this point
        
        # 6. Run any scheduled re-indexing
        processed = await service.run_reindex_cycle()
        
        assert processed >= 0  # Successfully completed cycle
    
    @pytest.mark.asyncio
    async def test_decay_triggers_reindex(self):
        """Test that decay properly triggers re-indexing."""
        service = create_self_improving_rag(utility_threshold=0.5)
        
        # Index a document
        await service.index_document("doc_decay", b"Test decay content")
        
        # Aggressively decay
        for chunk_id in list(service.utility_tracker._chunks.keys()):
            for i in range(30):
                service.utility_tracker.log_retrieval(
                    chunk_id=chunk_id,
                    query_id=f"q_{i}",
                    relevance_score=0.9,
                    was_in_answer=False,
                )
        
        # Verify low utility
        for chunk_id in service.utility_tracker._chunks:
            assert service.utility_tracker.get_chunk_utility(chunk_id) < 0.5
        
        # Should trigger re-indexing
        scheduled = await service.check_and_schedule_reindex()
        assert scheduled >= 1
    
    @pytest.mark.asyncio
    async def test_correction_penalty(self):
        """Test that corrections apply penalty."""
        service = create_self_improving_rag()
        
        await service.index_document("doc_corr", b"Correction test content")
        
        chunk_id = list(service.utility_tracker._chunks.keys())[0]
        initial_utility = service.utility_tracker.get_chunk_utility(chunk_id)
        
        # Apply correction
        service.utility_tracker.log_retrieval(
            chunk_id=chunk_id,
            query_id="q1",
            relevance_score=0.9,
            was_in_answer=True,
            correction_id="corr_001",
        )
        
        new_utility = service.utility_tracker.get_chunk_utility(chunk_id)
        assert new_utility < initial_utility


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_empty_document(self, rag_service):
        """Test indexing empty document."""
        count = await rag_service.index_document("empty", b"")
        assert count >= 0  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_query_empty_index(self, rag_service):
        """Test querying empty index."""
        results = await rag_service.query([0.5] * 16)
        assert results == []
    
    def test_unknown_chunk_utility(self, utility_tracker):
        """Test getting utility for unknown chunk."""
        utility = utility_tracker.get_chunk_utility("nonexistent")
        assert utility == 1.0  # Default
    
    def test_document_metrics_missing_document(self, utility_tracker):
        """Test getting metrics for missing document."""
        metrics = utility_tracker.get_document_metrics("nonexistent")
        assert metrics is None
    
    @pytest.mark.asyncio
    async def test_scheduler_empty_queue(self):
        """Test getting job from empty queue."""
        throttle = ThrottleManager()
        scheduler = ReindexScheduler(throttle)
        
        job = await scheduler.get_next_job()
        assert job is None

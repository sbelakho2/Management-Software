"""Tests for AI Model Enrichment / Knowledge Synthesis (Development Plan 22.13)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.services.knowledge_enrichment import (
    KnowledgeEnrichmentService,
    SourceType,
    ContentFormat,
    IngestionStatus,
    ChunkType,
    TaxonomyCategory,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> KnowledgeEnrichmentService:
    return KnowledgeEnrichmentService()


@pytest.fixture
def admin_roles() -> set[str]:
    return {"admin"}


@pytest.fixture
def curator_roles() -> set[str]:
    return {"knowledge_curator"}


@pytest.fixture
def reader_roles() -> set[str]:
    return {"gm"}


@pytest.fixture
def viewer_roles() -> set[str]:
    return {"viewer"}


# ============================================================
# Default Source Tests
# ============================================================


class TestDefaultSources:
    def test_default_sources_initialized(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        assert len(sources) >= 8  # At least 8 default sources

    def test_toyota_global_source_exists(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(
            actor_roles=reader_roles, source_type=SourceType.TOYOTA_GLOBAL
        )
        assert len(sources) == 1
        assert "TPS" in sources[0].name

    def test_mit_ocw_source_exists(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(
            actor_roles=reader_roles, source_type=SourceType.MIT_OCW
        )
        assert len(sources) == 1
        assert "MIT" in sources[0].name

    def test_nist_mep_source_exists(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(
            actor_roles=reader_roles, source_type=SourceType.NIST_MEP
        )
        assert len(sources) == 1

    def test_gutenberg_source_exists(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(
            actor_roles=reader_roles, source_type=SourceType.PROJECT_GUTENBERG
        )
        assert len(sources) == 1
        assert "Taylor" in sources[0].name

    def test_filter_by_tag(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles, tag="lean")
        assert len(sources) >= 3


# ============================================================
# Source Management Tests
# ============================================================


class TestSourceManagement:
    def test_register_custom_source(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str]
    ) -> None:
        source = svc.register_custom_source(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            name="Custom Lean Guide",
            url="https://example.com/lean.pdf",
            content_format=ContentFormat.PDF,
            license_type="internal",
            tags=["lean", "custom"],
        )

        assert source.name == "Custom Lean Guide"
        assert source.source_type == SourceType.CUSTOM_PDF

    def test_viewer_cannot_register_source(
        self, svc: KnowledgeEnrichmentService, viewer_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Knowledge curator access required"):
            svc.register_custom_source(
                actor_id="viewer1",
                actor_roles=viewer_roles,
                correlation_id="cor-1",
                name="Test",
                url="https://test.com",
                content_format=ContentFormat.PDF,
                license_type="test",
                tags=[],
            )


# ============================================================
# Acquisition Tests (Step 1)
# ============================================================


class TestAcquisition:
    def test_acquire_resource_with_content(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        job = svc.acquire_resource(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            simulated_content=b"Sample TPS content about just-in-time and kaizen.",
        )

        assert job.status == IngestionStatus.ACQUIRED
        assert job.file_hash is not None
        assert job.file_size_bytes > 0

    def test_acquire_resource_pending_without_content(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        job = svc.acquire_resource(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
        )

        assert job.status == IngestionStatus.PENDING

    def test_mark_acquisition_complete(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        job = svc.acquire_resource(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
        )

        updated = svc.mark_acquisition_complete(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-2",
            job_id=job.id,
            file_path="/tmp/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
        )

        assert updated.status == IngestionStatus.ACQUIRED
        assert updated.file_path == "/tmp/test.pdf"

    def test_mark_acquisition_failed(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        job = svc.acquire_resource(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
        )

        failed = svc.mark_acquisition_failed(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-2",
            job_id=job.id,
            error_message="Network timeout",
        )

        assert failed.status == IngestionStatus.FAILED
        assert failed.error_message == "Network timeout"


# ============================================================
# Ingestion Tests (Step 2)
# ============================================================


class TestIngestion:
    def test_ingest_content_creates_chunks(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        Just-in-time (JIT) is a core principle of the Toyota Production System.
        It means producing only what is needed, when it is needed, in the amount needed.

        Kaizen refers to continuous improvement. Small, incremental changes
        lead to significant improvements over time. Everyone in the organization
        participates in kaizen activities.

        Muda (waste) is anything that does not add value to the product.
        The seven types of muda include: overproduction, waiting, transportation,
        over-processing, inventory, motion, and defects.
        """

        chunks = svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        assert len(chunks) >= 2

    def test_taxonomy_detection(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        Just-in-time production ensures that parts arrive exactly when needed.
        This pull system reduces inventory waste and improves flow.
        """

        chunks = svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        assert len(chunks) >= 1
        # JIT keywords should be detected
        assert TaxonomyCategory.JUST_IN_TIME in chunks[0].taxonomy_categories


# ============================================================
# Chunking Tests (Step 3)
# ============================================================


class TestChunking:
    def test_process_chunks_splits_large_content(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        # Create a large paragraph
        large_content = "Kaizen is continuous improvement. " * 50

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=large_content,
        )

        processed = svc.process_chunks(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-2",
            source_id=source.id,
            max_chunk_size=500,
        )

        # Should have split into multiple chunks
        assert len(processed) >= 2


# ============================================================
# Embedding Tests (Step 4)
# ============================================================


class TestEmbedding:
    def test_embed_chunks_creates_embeddings(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        The PDCA cycle (Plan-Do-Check-Act) is a fundamental problem-solving method.
        It provides a systematic approach to continuous improvement.
        """

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        embeddings = svc.embed_chunks(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-2",
            source_id=source.id,
        )

        assert len(embeddings) >= 1
        assert embeddings[0].model_name == "all-MiniLM-L6-v2"
        assert embeddings[0].embedding_dim == 384


# ============================================================
# Alignment Tests (Step 5)
# ============================================================


class TestAlignment:
    def test_verify_alignment_with_pdca_content(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        The PDCA cycle is essential for continuous improvement.
        Kaizen activities should follow the Plan-Do-Check-Act approach.
        Identifying muda (waste) is the first step in improvement.
        """

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        svc.embed_chunks(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-2",
            source_id=source.id,
        )

        result = svc.verify_alignment(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-3",
            source_id=source.id,
        )

        assert result.socratic_mentor_verified is True  # PDCA detected
        assert result.pdca_coach_verified is True  # Kaizen/Muda detected


# ============================================================
# Knowledge Pack Tests
# ============================================================


class TestKnowledgePacks:
    def test_create_knowledge_pack(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source_ids = [s.id for s in sources[:3]]

        pack = svc.create_knowledge_pack(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            name="TPS Core Pack",
            description="Core TPS knowledge sources",
            source_ids=source_ids,
        )

        assert pack.name == "TPS Core Pack"
        assert len(pack.source_ids) == 3

    def test_list_knowledge_packs(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)

        svc.create_knowledge_pack(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            name="Pack 1",
            description="First pack",
            source_ids=[sources[0].id],
        )

        packs = svc.list_knowledge_packs(actor_roles=reader_roles)
        assert len(packs) >= 1

    def test_deactivate_knowledge_pack(
        self, svc: KnowledgeEnrichmentService, admin_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)

        pack = svc.create_knowledge_pack(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Temp Pack",
            description="Temporary",
            source_ids=[sources[0].id],
        )

        deactivated = svc.deactivate_knowledge_pack(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            pack_id=pack.id,
        )

        assert deactivated.is_active is False

        active_packs = svc.list_knowledge_packs(actor_roles=reader_roles, active_only=True)
        assert all(p.id != pack.id for p in active_packs)


# ============================================================
# Search Tests
# ============================================================


class TestSearch:
    def test_search_by_taxonomy(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        Kanban is a visual signaling system. Cards or other signals indicate
        when to produce or move parts. This pull-based approach reduces overproduction.
        """

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        results = svc.search_chunks_by_taxonomy(
            actor_roles=reader_roles, category=TaxonomyCategory.KANBAN
        )

        assert len(results) >= 1

    def test_search_by_keyword(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        Poka-yoke devices prevent mistakes before they happen.
        Error-proofing is essential for built-in quality.
        """

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        results = svc.search_chunks_by_keyword(
            actor_roles=reader_roles, keyword="poka-yoke"
        )

        assert len(results) >= 1


# ============================================================
# Statistics Tests
# ============================================================


class TestStatistics:
    def test_get_enrichment_stats(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        content = """
        Value stream mapping helps visualize the flow of materials and information.
        It identifies waste and opportunities for improvement.
        """

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            raw_content=content,
        )

        stats = svc.get_enrichment_stats(actor_roles=reader_roles)

        assert stats["total_sources"] >= 8
        assert stats["total_chunks"] >= 1


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_viewer_cannot_read_sources(
        self, svc: KnowledgeEnrichmentService, viewer_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Knowledge read access required"):
            svc.list_sources(actor_roles=viewer_roles)

    def test_reader_can_read_sources(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        assert len(sources) >= 1

    def test_curator_cannot_deactivate_pack(
        self, svc: KnowledgeEnrichmentService, curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)

        pack = svc.create_knowledge_pack(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            name="Test Pack",
            description="Test",
            source_ids=[sources[0].id],
        )

        with pytest.raises(PermissionError, match="Admin role required"):
            svc.deactivate_knowledge_pack(
                actor_id="curator1",
                actor_roles=curator_roles,
                correlation_id="cor-2",
                pack_id=pack.id,
            )


# ============================================================
# Audit Trail Tests
# ============================================================


class TestAuditTrail:
    def test_audit_trail_for_operations(
        self, svc: KnowledgeEnrichmentService, admin_roles: set[str], curator_roles: set[str], reader_roles: set[str]
    ) -> None:
        sources = svc.list_sources(actor_roles=reader_roles)
        source = sources[0]

        svc.acquire_resource(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-1",
            source_id=source.id,
            simulated_content=b"Test content",
        )

        svc.ingest_content(
            actor_id="curator1",
            actor_roles=curator_roles,
            correlation_id="cor-2",
            source_id=source.id,
            raw_content="Kaizen is continuous improvement.",
        )

        events = svc.list_audit_events(actor_roles=admin_roles)
        actions = [e.action for e in events]

        assert "resource.acquire" in actions
        assert "content.ingest" in actions

    def test_non_auditor_cannot_view_audit(
        self, svc: KnowledgeEnrichmentService, reader_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Audit access required"):
            svc.list_audit_events(actor_roles=reader_roles)

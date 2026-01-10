"""AI Model Enrichment: TPS & Lean Knowledge Synthesis (Development Plan 22.13).

Implements:
- TPS/Lean Resource Ingestion (Toyota TPS, MIT OCW, NIST MEP, Wikipedia, Gutenberg)
- CLI Enrichment Workflow (Acquisition, Ingestion, Chunking, Vectorization, Alignment)
- Knowledge Pack management
- Semantic chunking with citation preservation
- ONNX vectorization for CPU-optimized embeddings
- Integration with Socratic Mentor and PDCA Coaching Engine
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


# ============================================================
# Role Definitions
# ============================================================

_ADMIN_ROLES = frozenset({"admin"})
_KNOWLEDGE_CURATOR_ROLES = frozenset({"admin", "knowledge_curator", "ml_engineer"})
_READER_ROLES = frozenset(
    {"admin", "knowledge_curator", "ml_engineer", "gm", "ops", "auditor", "ceo"}
)


# ============================================================
# Enums
# ============================================================


class SourceType(str, Enum):
    """Knowledge source types."""

    TOYOTA_GLOBAL = "toyota_global"
    MIT_OCW = "mit_ocw"
    NIST_MEP = "nist_mep"
    WIKIPEDIA = "wikipedia"
    PROJECT_GUTENBERG = "project_gutenberg"
    CUSTOM_PDF = "custom_pdf"
    INTERNAL_DOCUMENT = "internal_document"


class ContentFormat(str, Enum):
    """Content formats."""

    HTML = "html"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    ZIP = "zip"


class IngestionStatus(str, Enum):
    """Ingestion pipeline status."""

    PENDING = "pending"
    ACQUIRED = "acquired"
    INGESTED = "ingested"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    ALIGNED = "aligned"
    FAILED = "failed"


class ChunkType(str, Enum):
    """Semantic chunk types."""

    CONCEPT = "concept"
    EXAMPLE = "example"
    PRINCIPLE = "principle"
    TOOL = "tool"
    CASE_STUDY = "case_study"
    DEFINITION = "definition"
    PROCESS = "process"


class TaxonomyCategory(str, Enum):
    """Lean/TPS taxonomy categories."""

    JUST_IN_TIME = "just_in_time"
    JIDOKA = "jidoka"
    HEIJUNKA = "heijunka"
    KAIZEN = "kaizen"
    FIVE_S = "five_s"
    MUDA = "muda"
    MURI = "muri"
    MURA = "mura"
    PDCA = "pdca"
    A3_THINKING = "a3_thinking"
    ANDON = "andon"
    KANBAN = "kanban"
    POKA_YOKE = "poka_yoke"
    VALUE_STREAM = "value_stream"
    GEMBA = "gemba"
    HOSHIN_KANRI = "hoshin_kanri"
    TPM = "tpm"
    SMED = "smed"
    TAKT_TIME = "takt_time"
    STANDARD_WORK = "standard_work"


# ============================================================
# Data Models
# ============================================================


@dataclass(frozen=True)
class KnowledgeSource:
    """External knowledge source definition."""

    id: UUID
    name: str
    source_type: SourceType
    url: str
    cli_command: str
    content_format: ContentFormat
    license_type: str
    tags: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True)
class AcquisitionJob:
    """Job to acquire a knowledge resource."""

    id: UUID
    source_id: UUID
    started_at: datetime
    completed_at: datetime | None
    status: IngestionStatus
    file_path: str | None
    file_hash: str | None
    file_size_bytes: int | None
    error_message: str | None = None


@dataclass(frozen=True)
class SemanticChunk:
    """Semantic chunk from knowledge corpus."""

    id: UUID
    source_id: UUID
    chunk_type: ChunkType
    content: str
    citation: str
    taxonomy_categories: tuple[TaxonomyCategory, ...]
    page_number: int | None
    section_title: str | None
    embedding_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EmbeddingRecord:
    """ONNX embedding record."""

    id: UUID
    chunk_id: UUID
    model_name: str
    embedding_dim: int
    embedding_hash: str  # Hash of the vector for integrity
    created_at: datetime


@dataclass(frozen=True)
class AlignmentResult:
    """Alignment verification result."""

    id: UUID
    source_id: UUID
    aligned_at: datetime
    socratic_mentor_verified: bool
    pdca_coach_verified: bool
    verification_notes: str


@dataclass(frozen=True)
class KnowledgePack:
    """Knowledge pack containing multiple sources."""

    id: UUID
    name: str
    description: str
    source_ids: tuple[UUID, ...]
    created_at: datetime
    is_active: bool = True


@dataclass
class AuditEntry:
    """Audit log entry."""

    id: UUID
    timestamp: datetime
    actor_id: str
    action: str
    entity_type: str
    entity_id: UUID | None
    correlation_id: str
    details: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Default Knowledge Sources
# ============================================================

_DEFAULT_SOURCES: list[dict[str, Any]] = [
    {
        "name": "Toyota Global TPS Library",
        "source_type": SourceType.TOYOTA_GLOBAL,
        "url": "https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/",
        "cli_command": "curl -s https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/",
        "content_format": ContentFormat.HTML,
        "license_type": "public_info",
        "tags": ("tps", "lean", "toyota", "jit", "jidoka"),
    },
    {
        "name": "MIT OCW Lean Enterprise Course",
        "source_type": SourceType.MIT_OCW,
        "url": "https://ocw.mit.edu/courses/16-852j-integrating-the-lean-enterprise-fall-2005/",
        "cli_command": "wget https://ocw.mit.edu/courses/16-852j-integrating-the-lean-enterprise-fall-2005/16-852j-fall-2005.zip",
        "content_format": ContentFormat.ZIP,
        "license_type": "CC-BY-NC-SA",
        "tags": ("lean", "enterprise", "mit", "education"),
    },
    {
        "name": "NIST MEP Lean Framework",
        "source_type": SourceType.NIST_MEP,
        "url": "https://www.nist.gov/system/files/documents/mep/Lean-Manufacturing-Guide.pdf",
        "cli_command": "curl -o lean_guide.pdf https://www.nist.gov/system/files/documents/mep/Lean-Manufacturing-Guide.pdf",
        "content_format": ContentFormat.PDF,
        "license_type": "public_domain_us_gov",
        "tags": ("lean", "manufacturing", "nist", "guide"),
    },
    {
        "name": "Wikipedia Lean Manufacturing",
        "source_type": SourceType.WIKIPEDIA,
        "url": "https://en.wikipedia.org/wiki/Lean_manufacturing",
        "cli_command": "python -m sensei.cli.knowledge ingest https://en.wikipedia.org/wiki/Lean_manufacturing --tag lean",
        "content_format": ContentFormat.HTML,
        "license_type": "CC-BY-SA",
        "tags": ("lean", "manufacturing", "wikipedia"),
    },
    {
        "name": "Wikipedia Six Sigma",
        "source_type": SourceType.WIKIPEDIA,
        "url": "https://en.wikipedia.org/wiki/Six_Sigma",
        "cli_command": "python -m sensei.cli.knowledge ingest https://en.wikipedia.org/wiki/Six_Sigma --tag six_sigma",
        "content_format": ContentFormat.HTML,
        "license_type": "CC-BY-SA",
        "tags": ("six_sigma", "quality", "wikipedia"),
    },
    {
        "name": "Wikipedia Kaizen",
        "source_type": SourceType.WIKIPEDIA,
        "url": "https://en.wikipedia.org/wiki/Kaizen",
        "cli_command": "python -m sensei.cli.knowledge ingest https://en.wikipedia.org/wiki/Kaizen --tag kaizen",
        "content_format": ContentFormat.HTML,
        "license_type": "CC-BY-SA",
        "tags": ("kaizen", "continuous_improvement", "wikipedia"),
    },
    {
        "name": "Wikipedia TQM",
        "source_type": SourceType.WIKIPEDIA,
        "url": "https://en.wikipedia.org/wiki/Total_quality_management",
        "cli_command": "python -m sensei.cli.knowledge ingest https://en.wikipedia.org/wiki/Total_quality_management --tag tqm",
        "content_format": ContentFormat.HTML,
        "license_type": "CC-BY-SA",
        "tags": ("tqm", "quality", "wikipedia"),
    },
    {
        "name": "Taylor Scientific Management (Gutenberg)",
        "source_type": SourceType.PROJECT_GUTENBERG,
        "url": "https://www.gutenberg.org/files/6435/6435-h/6435-h.htm",
        "cli_command": "curl -o taylor_principles.html https://www.gutenberg.org/files/6435/6435-h/6435-h.htm",
        "content_format": ContentFormat.HTML,
        "license_type": "public_domain",
        "tags": ("scientific_management", "taylor", "gutenberg", "history"),
    },
]


# ============================================================
# Taxonomy Keyword Mapping
# ============================================================

_TAXONOMY_KEYWORDS: dict[TaxonomyCategory, tuple[str, ...]] = {
    TaxonomyCategory.JUST_IN_TIME: ("just-in-time", "jit", "pull system", "flow"),
    TaxonomyCategory.JIDOKA: ("jidoka", "autonomation", "built-in quality", "stop the line"),
    TaxonomyCategory.HEIJUNKA: ("heijunka", "level loading", "production leveling"),
    TaxonomyCategory.KAIZEN: ("kaizen", "continuous improvement", "small improvement"),
    TaxonomyCategory.FIVE_S: ("5s", "five s", "sort", "set in order", "shine", "standardize", "sustain"),
    TaxonomyCategory.MUDA: ("muda", "waste", "non-value-added", "seven wastes", "eight wastes"),
    TaxonomyCategory.MURI: ("muri", "overburden", "unreasonable"),
    TaxonomyCategory.MURA: ("mura", "unevenness", "irregularity"),
    TaxonomyCategory.PDCA: ("pdca", "plan-do-check-act", "deming cycle", "shewhart cycle"),
    TaxonomyCategory.A3_THINKING: ("a3", "a3 thinking", "problem solving", "one-page"),
    TaxonomyCategory.ANDON: ("andon", "signal", "visual control", "warning light"),
    TaxonomyCategory.KANBAN: ("kanban", "signboard", "pull signal", "card system"),
    TaxonomyCategory.POKA_YOKE: ("poka-yoke", "mistake-proofing", "error-proofing", "fail-safe"),
    TaxonomyCategory.VALUE_STREAM: ("value stream", "vsm", "value stream mapping", "current state", "future state"),
    TaxonomyCategory.GEMBA: ("gemba", "genba", "go and see", "actual place", "shop floor"),
    TaxonomyCategory.HOSHIN_KANRI: ("hoshin kanri", "policy deployment", "strategy deployment", "x-matrix"),
    TaxonomyCategory.TPM: ("tpm", "total productive maintenance", "autonomous maintenance", "planned maintenance"),
    TaxonomyCategory.SMED: ("smed", "single-minute exchange", "quick changeover", "setup reduction"),
    TaxonomyCategory.TAKT_TIME: ("takt time", "takt", "customer demand rate", "cycle time"),
    TaxonomyCategory.STANDARD_WORK: ("standard work", "standardized work", "work sequence", "work elements"),
}


# ============================================================
# Service
# ============================================================


class KnowledgeEnrichmentService:
    """AI Model Enrichment / TPS & Lean Knowledge Service."""

    def __init__(self) -> None:
        self._sources: dict[UUID, KnowledgeSource] = {}
        self._acquisition_jobs: dict[UUID, AcquisitionJob] = {}
        self._chunks: dict[UUID, SemanticChunk] = {}
        self._embeddings: dict[UUID, EmbeddingRecord] = {}
        self._alignments: dict[UUID, AlignmentResult] = {}
        self._knowledge_packs: dict[UUID, KnowledgePack] = {}
        self._audit_log: list[AuditEntry] = []

        # Initialize default sources
        self._initialize_default_sources()

    def _initialize_default_sources(self) -> None:
        """Initialize built-in TPS/Lean knowledge sources."""
        for src_def in _DEFAULT_SOURCES:
            source = KnowledgeSource(
                id=uuid4(),
                name=src_def["name"],
                source_type=src_def["source_type"],
                url=src_def["url"],
                cli_command=src_def["cli_command"],
                content_format=src_def["content_format"],
                license_type=src_def["license_type"],
                tags=tuple(src_def["tags"]),
                created_at=datetime.now(timezone.utc),
            )
            self._sources[source.id] = source

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _require_curator(self, actor_roles: set[str]) -> None:
        if not actor_roles & _KNOWLEDGE_CURATOR_ROLES:
            raise PermissionError("Knowledge curator access required")

    def _require_reader(self, actor_roles: set[str]) -> None:
        if not actor_roles & _READER_ROLES:
            raise PermissionError("Knowledge read access required")

    def _require_admin(self, actor_roles: set[str]) -> None:
        if not actor_roles & _ADMIN_ROLES:
            raise PermissionError("Admin role required")

    def _audit(
        self,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._audit_log.append(
            AuditEntry(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                details=details or {},
            )
        )

    def _compute_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _detect_taxonomy_categories(
        self, content: str
    ) -> tuple[TaxonomyCategory, ...]:
        """Detect taxonomy categories based on keyword matching."""
        content_lower = content.lower()
        detected = []
        for category, keywords in _TAXONOMY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    detected.append(category)
                    break
        return tuple(set(detected))

    def _detect_chunk_type(self, content: str) -> ChunkType:
        """Detect chunk type based on content patterns."""
        content_lower = content.lower()
        if any(word in content_lower for word in ("example:", "for example", "case:")):
            return ChunkType.EXAMPLE
        if any(word in content_lower for word in ("principle:", "key principle", "core principle")):
            return ChunkType.PRINCIPLE
        if any(word in content_lower for word in ("tool:", "technique:", "method:")):
            return ChunkType.TOOL
        if any(word in content_lower for word in ("case study", "at toyota", "at company")):
            return ChunkType.CASE_STUDY
        if any(word in content_lower for word in ("definition:", "is defined as", "refers to")):
            return ChunkType.DEFINITION
        if any(word in content_lower for word in ("step 1", "process:", "procedure:")):
            return ChunkType.PROCESS
        return ChunkType.CONCEPT

    # --------------------------------------------------------
    # Source Management
    # --------------------------------------------------------

    def list_sources(
        self,
        actor_roles: set[str],
        source_type: SourceType | None = None,
        tag: str | None = None,
    ) -> list[KnowledgeSource]:
        """List knowledge sources with optional filtering."""
        self._require_reader(actor_roles)
        sources = list(self._sources.values())
        if source_type:
            sources = [s for s in sources if s.source_type == source_type]
        if tag:
            sources = [s for s in sources if tag in s.tags]
        return sources

    def get_source(
        self, actor_roles: set[str], source_id: UUID
    ) -> KnowledgeSource:
        """Get a specific knowledge source."""
        self._require_reader(actor_roles)
        if source_id not in self._sources:
            raise ValueError(f"Source {source_id} not found")
        return self._sources[source_id]

    def register_custom_source(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        name: str,
        url: str,
        content_format: ContentFormat,
        license_type: str,
        tags: list[str],
    ) -> KnowledgeSource:
        """Register a custom knowledge source."""
        self._require_curator(actor_roles)

        source = KnowledgeSource(
            id=uuid4(),
            name=name,
            source_type=SourceType.CUSTOM_PDF,
            url=url,
            cli_command=f"curl -o custom_source.pdf {url}",
            content_format=content_format,
            license_type=license_type,
            tags=tuple(tags),
            created_at=datetime.now(timezone.utc),
        )
        self._sources[source.id] = source

        self._audit(
            actor_id,
            "source.register",
            "knowledge_source",
            source.id,
            correlation_id,
            {"name": name, "url": url},
        )
        return source

    # --------------------------------------------------------
    # Step 1: Resource Acquisition
    # --------------------------------------------------------

    def acquire_resource(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        source_id: UUID,
        simulated_content: bytes | None = None,
    ) -> AcquisitionJob:
        """Execute acquisition for a knowledge source (Step 1)."""
        self._require_curator(actor_roles)

        if source_id not in self._sources:
            raise ValueError(f"Source {source_id} not found")

        source = self._sources[source_id]

        # In production, this would execute the CLI command
        # For testing, we simulate with provided content
        if simulated_content:
            file_hash = self._compute_hash(simulated_content)
            file_size = len(simulated_content)
            status = IngestionStatus.ACQUIRED
            file_path = f"/tmp/knowledge_pack/{source.name.replace(' ', '_').lower()}"
        else:
            file_hash = None
            file_size = None
            status = IngestionStatus.PENDING
            file_path = None

        job = AcquisitionJob(
            id=uuid4(),
            source_id=source_id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if simulated_content else None,
            status=status,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
        )
        self._acquisition_jobs[job.id] = job

        self._audit(
            actor_id,
            "resource.acquire",
            "acquisition_job",
            job.id,
            correlation_id,
            {"source_id": str(source_id), "status": status.value},
        )
        return job

    def mark_acquisition_complete(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        job_id: UUID,
        file_path: str,
        file_hash: str,
        file_size_bytes: int,
    ) -> AcquisitionJob:
        """Mark an acquisition job as complete."""
        self._require_curator(actor_roles)

        if job_id not in self._acquisition_jobs:
            raise ValueError(f"Job {job_id} not found")

        old = self._acquisition_jobs[job_id]
        updated = AcquisitionJob(
            id=old.id,
            source_id=old.source_id,
            started_at=old.started_at,
            completed_at=datetime.now(timezone.utc),
            status=IngestionStatus.ACQUIRED,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size_bytes,
        )
        self._acquisition_jobs[job_id] = updated

        self._audit(
            actor_id,
            "acquisition.complete",
            "acquisition_job",
            job_id,
            correlation_id,
        )
        return updated

    def mark_acquisition_failed(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        job_id: UUID,
        error_message: str,
    ) -> AcquisitionJob:
        """Mark an acquisition job as failed."""
        self._require_curator(actor_roles)

        if job_id not in self._acquisition_jobs:
            raise ValueError(f"Job {job_id} not found")

        old = self._acquisition_jobs[job_id]
        updated = AcquisitionJob(
            id=old.id,
            source_id=old.source_id,
            started_at=old.started_at,
            completed_at=datetime.now(timezone.utc),
            status=IngestionStatus.FAILED,
            file_path=old.file_path,
            file_hash=old.file_hash,
            file_size_bytes=old.file_size_bytes,
            error_message=error_message,
        )
        self._acquisition_jobs[job_id] = updated

        self._audit(
            actor_id,
            "acquisition.failed",
            "acquisition_job",
            job_id,
            correlation_id,
            {"error": error_message},
        )
        return updated

    # --------------------------------------------------------
    # Step 2: Semantic Ingestion
    # --------------------------------------------------------

    def ingest_content(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        source_id: UUID,
        raw_content: str,
        tag: str | None = None,
    ) -> list[SemanticChunk]:
        """Ingest raw content and create semantic chunks (Step 2)."""
        self._require_curator(actor_roles)

        if source_id not in self._sources:
            raise ValueError(f"Source {source_id} not found")

        source = self._sources[source_id]

        # Simple paragraph-based chunking
        paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip()]

        chunks = []
        for i, para in enumerate(paragraphs):
            if len(para) < 50:  # Skip very short paragraphs
                continue

            taxonomy = self._detect_taxonomy_categories(para)
            chunk_type = self._detect_chunk_type(para)

            chunk = SemanticChunk(
                id=uuid4(),
                source_id=source_id,
                chunk_type=chunk_type,
                content=para,
                citation=f"{source.name}, paragraph {i + 1}",
                taxonomy_categories=taxonomy,
                page_number=None,
                section_title=None,
                created_at=datetime.now(timezone.utc),
            )
            self._chunks[chunk.id] = chunk
            chunks.append(chunk)

        self._audit(
            actor_id,
            "content.ingest",
            "semantic_chunk",
            None,
            correlation_id,
            {"source_id": str(source_id), "chunk_count": len(chunks)},
        )
        return chunks

    # --------------------------------------------------------
    # Step 3: Recursive Chunking
    # --------------------------------------------------------

    def process_chunks(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        source_id: UUID,
        max_chunk_size: int = 1000,
    ) -> list[SemanticChunk]:
        """Process and re-chunk content for high fidelity (Step 3)."""
        self._require_curator(actor_roles)

        source_chunks = [c for c in self._chunks.values() if c.source_id == source_id]

        processed = []
        for chunk in source_chunks:
            if len(chunk.content) <= max_chunk_size:
                processed.append(chunk)
                continue

            # Split large chunks
            sentences = re.split(r"(?<=[.!?])\s+", chunk.content)
            current = []
            current_len = 0

            for sent in sentences:
                if current_len + len(sent) > max_chunk_size and current:
                    new_content = " ".join(current)
                    new_chunk = SemanticChunk(
                        id=uuid4(),
                        source_id=source_id,
                        chunk_type=chunk.chunk_type,
                        content=new_content,
                        citation=f"{chunk.citation} (split)",
                        taxonomy_categories=self._detect_taxonomy_categories(new_content),
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                    )
                    self._chunks[new_chunk.id] = new_chunk
                    processed.append(new_chunk)
                    current = []
                    current_len = 0

                current.append(sent)
                current_len += len(sent) + 1

            if current:
                new_content = " ".join(current)
                new_chunk = SemanticChunk(
                    id=uuid4(),
                    source_id=source_id,
                    chunk_type=chunk.chunk_type,
                    content=new_content,
                    citation=f"{chunk.citation} (split)",
                    taxonomy_categories=self._detect_taxonomy_categories(new_content),
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                )
                self._chunks[new_chunk.id] = new_chunk
                processed.append(new_chunk)

        self._audit(
            actor_id,
            "chunks.process",
            "semantic_chunk",
            None,
            correlation_id,
            {"source_id": str(source_id), "processed_count": len(processed)},
        )
        return processed

    # --------------------------------------------------------
    # Step 4: Vectorization (ONNX)
    # --------------------------------------------------------

    def embed_chunks(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        source_id: UUID,
        model_name: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384,
    ) -> list[EmbeddingRecord]:
        """Generate embeddings for chunks using ONNX (Step 4)."""
        self._require_curator(actor_roles)

        source_chunks = [c for c in self._chunks.values() if c.source_id == source_id]

        embeddings = []
        for chunk in source_chunks:
            # Simulate embedding generation
            # In production, this would use ONNX runtime
            simulated_embedding_hash = self._compute_hash(
                f"{chunk.content}{model_name}".encode()
            )

            record = EmbeddingRecord(
                id=uuid4(),
                chunk_id=chunk.id,
                model_name=model_name,
                embedding_dim=embedding_dim,
                embedding_hash=simulated_embedding_hash,
                created_at=datetime.now(timezone.utc),
            )
            self._embeddings[record.id] = record
            embeddings.append(record)

            # Update chunk with embedding reference
            updated_chunk = SemanticChunk(
                id=chunk.id,
                source_id=chunk.source_id,
                chunk_type=chunk.chunk_type,
                content=chunk.content,
                citation=chunk.citation,
                taxonomy_categories=chunk.taxonomy_categories,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                embedding_id=record.id,
                created_at=chunk.created_at,
            )
            self._chunks[chunk.id] = updated_chunk

        self._audit(
            actor_id,
            "chunks.embed",
            "embedding",
            None,
            correlation_id,
            {"source_id": str(source_id), "embedding_count": len(embeddings)},
        )
        return embeddings

    # --------------------------------------------------------
    # Step 5: Reasoning Alignment
    # --------------------------------------------------------

    def verify_alignment(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        source_id: UUID,
    ) -> AlignmentResult:
        """Verify alignment with Socratic Mentor and PDCA Coach (Step 5)."""
        self._require_curator(actor_roles)

        if source_id not in self._sources:
            raise ValueError(f"Source {source_id} not found")

        # Check that chunks exist and are embedded
        source_chunks = [c for c in self._chunks.values() if c.source_id == source_id]
        if not source_chunks:
            raise ValueError(f"No chunks found for source {source_id}")

        embedded_count = sum(1 for c in source_chunks if c.embedding_id)
        all_embedded = embedded_count == len(source_chunks)

        # Check taxonomy coverage
        all_taxonomies: set[TaxonomyCategory] = set()
        for chunk in source_chunks:
            all_taxonomies.update(chunk.taxonomy_categories)

        # Determine alignment success based on coverage
        socratic_verified = TaxonomyCategory.PDCA in all_taxonomies or TaxonomyCategory.A3_THINKING in all_taxonomies
        pdca_verified = TaxonomyCategory.KAIZEN in all_taxonomies or TaxonomyCategory.MUDA in all_taxonomies

        result = AlignmentResult(
            id=uuid4(),
            source_id=source_id,
            aligned_at=datetime.now(timezone.utc),
            socratic_mentor_verified=socratic_verified,
            pdca_coach_verified=pdca_verified,
            verification_notes=f"Embedded: {embedded_count}/{len(source_chunks)}, Taxonomies: {len(all_taxonomies)}",
        )
        self._alignments[result.id] = result

        self._audit(
            actor_id,
            "alignment.verify",
            "alignment",
            result.id,
            correlation_id,
            {"socratic": socratic_verified, "pdca": pdca_verified},
        )
        return result

    # --------------------------------------------------------
    # Knowledge Pack Management
    # --------------------------------------------------------

    def create_knowledge_pack(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        name: str,
        description: str,
        source_ids: list[UUID],
    ) -> KnowledgePack:
        """Create a knowledge pack containing multiple sources."""
        self._require_curator(actor_roles)

        # Validate sources exist
        for sid in source_ids:
            if sid not in self._sources:
                raise ValueError(f"Source {sid} not found")

        pack = KnowledgePack(
            id=uuid4(),
            name=name,
            description=description,
            source_ids=tuple(source_ids),
            created_at=datetime.now(timezone.utc),
        )
        self._knowledge_packs[pack.id] = pack

        self._audit(
            actor_id,
            "knowledge_pack.create",
            "knowledge_pack",
            pack.id,
            correlation_id,
            {"name": name, "source_count": len(source_ids)},
        )
        return pack

    def list_knowledge_packs(
        self, actor_roles: set[str], active_only: bool = True
    ) -> list[KnowledgePack]:
        """List knowledge packs."""
        self._require_reader(actor_roles)
        packs = list(self._knowledge_packs.values())
        if active_only:
            packs = [p for p in packs if p.is_active]
        return packs

    def deactivate_knowledge_pack(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        pack_id: UUID,
    ) -> KnowledgePack:
        """Deactivate a knowledge pack."""
        self._require_admin(actor_roles)

        if pack_id not in self._knowledge_packs:
            raise ValueError(f"Pack {pack_id} not found")

        old = self._knowledge_packs[pack_id]
        updated = KnowledgePack(
            id=old.id,
            name=old.name,
            description=old.description,
            source_ids=old.source_ids,
            created_at=old.created_at,
            is_active=False,
        )
        self._knowledge_packs[pack_id] = updated

        self._audit(
            actor_id,
            "knowledge_pack.deactivate",
            "knowledge_pack",
            pack_id,
            correlation_id,
        )
        return updated

    # --------------------------------------------------------
    # Query / Search
    # --------------------------------------------------------

    def search_chunks_by_taxonomy(
        self,
        actor_roles: set[str],
        category: TaxonomyCategory,
        limit: int = 20,
    ) -> list[SemanticChunk]:
        """Search chunks by taxonomy category."""
        self._require_reader(actor_roles)
        matching = [
            c for c in self._chunks.values() if category in c.taxonomy_categories
        ]
        return matching[:limit]

    def search_chunks_by_keyword(
        self,
        actor_roles: set[str],
        keyword: str,
        limit: int = 20,
    ) -> list[SemanticChunk]:
        """Search chunks by keyword in content."""
        self._require_reader(actor_roles)
        keyword_lower = keyword.lower()
        matching = [
            c for c in self._chunks.values() if keyword_lower in c.content.lower()
        ]
        return matching[:limit]

    def get_chunk(self, actor_roles: set[str], chunk_id: UUID) -> SemanticChunk:
        """Get a specific chunk by ID."""
        self._require_reader(actor_roles)
        if chunk_id not in self._chunks:
            raise ValueError(f"Chunk {chunk_id} not found")
        return self._chunks[chunk_id]

    def list_chunks_for_source(
        self, actor_roles: set[str], source_id: UUID
    ) -> list[SemanticChunk]:
        """List all chunks for a source."""
        self._require_reader(actor_roles)
        return [c for c in self._chunks.values() if c.source_id == source_id]

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    def get_enrichment_stats(self, actor_roles: set[str]) -> dict[str, Any]:
        """Get enrichment statistics."""
        self._require_reader(actor_roles)

        taxonomy_counts: dict[str, int] = {}
        for chunk in self._chunks.values():
            for cat in chunk.taxonomy_categories:
                taxonomy_counts[cat.value] = taxonomy_counts.get(cat.value, 0) + 1

        return {
            "total_sources": len(self._sources),
            "total_chunks": len(self._chunks),
            "total_embeddings": len(self._embeddings),
            "total_alignments": len(self._alignments),
            "taxonomy_distribution": taxonomy_counts,
            "knowledge_packs": len(self._knowledge_packs),
        }

    # --------------------------------------------------------
    # Audit Trail
    # --------------------------------------------------------

    def list_audit_events(
        self,
        actor_roles: set[str],
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """List audit events (admin/auditor only)."""
        if not actor_roles & {"admin", "auditor"}:
            raise PermissionError("Audit access required")
        events = self._audit_log[-limit:]
        if entity_type:
            events = [e for e in events if e.entity_type == entity_type]
        return events

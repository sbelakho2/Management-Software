"""
Knowledge Pack models for ingested learning content.

Implements storage for externally sourced learning materials with:
- License tracking and attribution
- Semantic chunking with provenance
- Taxonomy tagging
- Vector embeddings for semantic search
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from sensei.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class LicenseType(str, Enum):
    """Allowed open licenses for knowledge content."""
    
    PUBLIC_DOMAIN = "public_domain"
    CC0 = "cc0"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    MIT = "mit"
    APACHE_2 = "apache_2"
    BSD = "bsd"
    OTHER_OPEN = "other_open"


class ContentFormat(str, Enum):
    """Original format of ingested content."""
    
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    JSON = "json"


class TaxonomyTag(str, Enum):
    """Taxonomy tags for categorizing knowledge."""
    
    TPS = "tps"  # Toyota Production System
    PDCA = "pdca"  # Plan-Do-Check-Act
    KATA = "kata"  # Improvement kata
    QUOTING = "quoting"
    QUALIFICATION = "qualification"
    CTQ = "ctq"  # Critical to Quality
    OBEYA = "obeya"
    A3_THINKING = "a3_thinking"
    STANDARD_WORK = "standard_work"
    VISUAL_MANAGEMENT = "visual_management"
    PROBLEM_SOLVING = "problem_solving"
    LEAN_PRINCIPLES = "lean_principles"
    QUALITY_GATES = "quality_gates"
    CONTINUOUS_IMPROVEMENT = "continuous_improvement"
    RISK_MANAGEMENT = "risk_management"


class KnowledgeDocument(Base, TimestampMixin):
    """
    Root document in the knowledge pack.
    
    Represents a complete source document with full metadata
    and license information for attribution.
    """
    
    __tablename__ = "knowledge_documents"
    
    # Source Information
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # License and Attribution
    license_type: Mapped[LicenseType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    license_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Content
    original_format: Mapped[ContentFormat] = mapped_column(
        String(50),
        nullable=False,
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Taxonomy
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    
    # Processing Status
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_indexed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Additional metadata as JSON
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    
    # Relationships
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_knowledge_documents_tags", "tags", postgresql_using="gin"),
        Index("ix_knowledge_documents_license", "license_type"),
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeDocument(title='{self.title}', license='{self.license_type}')>"


class KnowledgeChunk(Base, TimestampMixin):
    """
    Semantic chunk of a knowledge document.
    
    Documents are split into heading-aware chunks for better
    retrieval and context preservation.
    """
    
    __tablename__ = "knowledge_chunks"
    
    # Document Reference
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Chunk Content
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Context Information
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    section_path: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    
    # Chunk Metadata
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    start_position: Mapped[int] = mapped_column(Integer, nullable=False)
    end_position: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Quality Metrics
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_boilerplate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Taxonomy (inherited from document, can be refined per chunk)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    
    # Vector Embedding (1536 dimensions for OpenAI ada-002 or similar)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )
    
    # Provenance and Attribution
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Additional metadata
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    
    # Relationships
    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
    
    __table_args__ = (
        Index("ix_knowledge_chunks_document", "document_id"),
        Index("ix_knowledge_chunks_tags", "tags", postgresql_using="gin"),
        Index("ix_knowledge_chunks_embedding", "embedding", postgresql_using="ivfflat"),
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeChunk(doc={self.document_id}, index={self.chunk_index})>"


class IngestionLog(Base, TimestampMixin):
    """
    Log of ingestion operations for audit trail.
    
    Tracks all ingestion attempts, successes, and failures.
    """
    
    __tablename__ = "ingestion_logs"
    
    # Ingestion Details
    source_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'ingest', 'update', 'delete'
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # 'success', 'failed', 'skipped'
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Linked Document
    document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Metrics
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Details
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    
    __table_args__ = (
        Index("ix_ingestion_logs_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<IngestionLog(url='{self.source_url}', status='{self.status}')>"

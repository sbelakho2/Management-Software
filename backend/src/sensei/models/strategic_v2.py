"""
Strategic & AI Persistence Models (V2).

Provides a robust persistence layer for:
- Visual Quality Inspection (Continuous Learning)
- Multi-Agent RFQ Analysis (Debates & Consensus)
- Knowledge Enrichment (Sources, Chunks, Embeddings)
- Factory Launchpad (Site Maturity & Checklists)
- UI/Backend Integration (Action Audits)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin


# =============================================================================
# VISUAL QUALITY INSPECTION
# =============================================================================

class InspectionFeedback(Base, TimestampMixin):
    """Operator feedback on AI inspection results."""
    __tablename__ = "ai_inspection_feedback"

    inspection_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    operator_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class TrainingSample(Base, TimestampMixin):
    """Training samples for continuous model improvement."""
    __tablename__ = "ai_training_samples"

    sample_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "anomaly", "defect"
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    label_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_used_in_training: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)


# =============================================================================
# MULTI-AGENT RFQ ANALYSIS
# =============================================================================

class AgentAnalysisRecord(Base, TimestampMixin):
    """Persisted agent analysis results."""
    __tablename__ = "ai_agent_analyses"

    rfq_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    analysis_category: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    findings: Mapped[dict] = mapped_column(JSONB, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSONB, nullable=False)


class ConsensusDebateRecord(Base, TimestampMixin):
    """History of agent debates and consensus reaching."""
    __tablename__ = "ai_agent_debates"

    rfq_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), index=True)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    rounds: Mapped[int] = mapped_column(Integer, default=1)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    final_consensus_score: Mapped[float] = mapped_column(Float, nullable=False)
    debate_log: Mapped[list] = mapped_column(JSONB, nullable=False)


# =============================================================================
# KNOWLEDGE ENRICHMENT
# =============================================================================

class KnowledgeSourceRecord(Base, TimestampMixin):
    """External or internal knowledge sources."""
    __tablename__ = "ai_knowledge_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "url", "file", "db"
    uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_fields: Mapped[dict] = mapped_column(JSONB, default=dict)


class SemanticChunkRecord(Base, TimestampMixin):
    """Text chunks for semantic search."""
    __tablename__ = "ai_knowledge_chunks"

    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ai_knowledge_sources.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)


class KnowledgePackRecord(Base, TimestampMixin):
    """Knowledge packs that group sources together."""
    __tablename__ = "ai_knowledge_packs"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    metadata_fields: Mapped[dict] = mapped_column(JSONB, default=dict)

    sources: Mapped[list["KnowledgePackSourceRecord"]] = relationship(
        "KnowledgePackSourceRecord",
        back_populates="pack",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnowledgePackSourceRecord(Base):
    """Join table linking knowledge packs to sources."""
    __tablename__ = "ai_knowledge_pack_sources"

    pack_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_knowledge_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    pack: Mapped[KnowledgePackRecord] = relationship("KnowledgePackRecord", back_populates="sources")
    source: Mapped[KnowledgeSourceRecord] = relationship("KnowledgeSourceRecord")

    __table_args__ = (
        Index("ix_ai_knowledge_pack_sources_unique", pack_id, source_id, unique=True),
    )


# =============================================================================
# FACTORY LAUNCHPAD (PERSISTENCE)
# =============================================================================

class SiteMaturityRecord(Base, TimestampMixin):
    """Per-site maturity configuration and tracking."""
    __tablename__ = "factory_site_maturity"

    site_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_in_transition: Mapped[bool] = mapped_column(Boolean, default=False)
    deployment_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)


class LevelUpChecklistRecord(Base, TimestampMixin):
    """Checklist for maturity level transitions."""
    __tablename__ = "factory_level_up_checklists"

    site_id: Mapped[str] = mapped_column(String(100), ForeignKey("factory_site_maturity.site_id"), index=True)
    from_level: Mapped[int] = mapped_column(Integer, nullable=False)
    to_level: Mapped[int] = mapped_column(Integer, nullable=False)
    items: Mapped[list] = mapped_column(JSONB, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# =============================================================================
# UI ACTION AUDIT
# =============================================================================

class UIActionAuditRecord(Base, TimestampMixin):
    """Audit log for UI-triggered actions."""
    __tablename__ = "ui_action_audits"

    action_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    ui_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(100))


# =============================================================================
# JIT LEAN LEARNING
# =============================================================================

class LessonDeliveryRecord(Base, TimestampMixin):
    """Bite-sized lesson delivery tracking."""
    __tablename__ = "ai_lesson_deliveries"

    lesson_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    recipient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="delivered")
    feedback_score: Mapped[Optional[int]] = mapped_column(Integer)


class StandardWorkEvolutionRecord(Base, TimestampMixin):
    """Evolution of standard work documents based on performance data."""
    __tablename__ = "ai_standard_work_evolution"

    original_standard_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    suggested_changes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    performer_ids: Mapped[list] = mapped_column(JSONB, default=list)
    performance_gain_pct: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

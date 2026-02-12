"""
CRM Pipeline Automation Service.

Provides automated stage transitions, deal scoring, follow-up reminders,
and activity tracking for the sales pipeline.

All state is persisted via the database (Opportunity + OpportunityNote models).
No in-memory storage — safe across restarts.

Features:
- Auto-advance deals based on conditions (e.g. proposal sent → negotiation)
- Weighted deal scoring based on configurable factors
- Follow-up reminders for stale deals
- Activity tracking and next-best-action suggestions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.opportunity import (
    Opportunity,
    OpportunityNote,
    OpportunityStage,
    NoteType,
)

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Standard CRM pipeline stages (maps to OpportunityStage)."""

    LEAD = "lead"
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    VALUE_PROPOSITION = "value_proposition"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityType(str, Enum):
    """Types of CRM activities."""

    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"
    PROPOSAL_SENT = "proposal_sent"
    CONTRACT_SENT = "contract_sent"
    FOLLOW_UP = "follow_up"
    STATUS_CHANGE = "status_change"


# Maps our ActivityType → OpportunityNote.NoteType
_ACTIVITY_TO_NOTE = {
    ActivityType.CALL: NoteType.CALL.value,
    ActivityType.EMAIL: NoteType.EMAIL.value,
    ActivityType.MEETING: NoteType.MEETING.value,
    ActivityType.NOTE: NoteType.NOTE.value,
    ActivityType.TASK: NoteType.TASK.value,
    ActivityType.PROPOSAL_SENT: NoteType.NOTE.value,
    ActivityType.CONTRACT_SENT: NoteType.NOTE.value,
    ActivityType.FOLLOW_UP: NoteType.NOTE.value,
    ActivityType.STATUS_CHANGE: NoteType.STATUS_CHANGE.value,
}


@dataclass
class DealScore:
    """Computed deal score with breakdown."""

    total: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class StageTransition:
    """Record of a pipeline stage change."""

    id: str = field(default_factory=lambda: str(uuid4()))
    deal_id: str = ""
    from_stage: str | None = None
    to_stage: str = ""
    triggered_by: str = "system"
    reason: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class FollowUpReminder:
    """A follow-up reminder derived from stale opportunities."""

    id: str = field(default_factory=lambda: str(uuid4()))
    deal_id: str = ""
    owner_id: str = ""
    due_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    message: str = ""
    completed: bool = False


@dataclass
class ScoringConfig:
    """Weights for deal scoring factors."""

    engagement_weight: float = 0.25
    recency_weight: float = 0.20
    deal_size_weight: float = 0.20
    stage_weight: float = 0.15
    fit_weight: float = 0.10
    champion_weight: float = 0.10

    stale_days_threshold: int = 14
    high_value_threshold: float = 50_000.0


# Stage progression order for scoring
STAGE_ORDER = [
    OpportunityStage.PROSPECTING.value,
    OpportunityStage.QUALIFICATION.value,
    OpportunityStage.NEEDS_ANALYSIS.value,
    OpportunityStage.VALUE_PROPOSITION.value,
    OpportunityStage.PROPOSAL.value,
    OpportunityStage.NEGOTIATION.value,
    OpportunityStage.CLOSED_WON.value,
]


class CRMPipelineAutomation:
    """Automated pipeline management — fully DB-backed via Opportunity model."""

    def __init__(
        self,
        *,
        scoring_config: ScoringConfig | None = None,
    ) -> None:
        self._config = scoring_config or ScoringConfig()

    # ------------------------------------------------------------------
    # Deal scoring (reads from DB)
    # ------------------------------------------------------------------

    async def score_deal(
        self, db: AsyncSession, opportunity_id: UUID
    ) -> DealScore:
        """Compute a weighted deal score (0–100) from DB data."""
        cfg = self._config
        factors: dict[str, float] = {}

        opp = await db.get(Opportunity, opportunity_id)
        if opp is None:
            return DealScore(total=0.0, factors={}, confidence=0.0)

        # Count activities from opportunity_notes
        note_count_q = select(func.count()).select_from(OpportunityNote).where(
            OpportunityNote.opportunity_id == opportunity_id
        )
        note_count = int((await db.execute(note_count_q)).scalar_one())

        # Engagement score
        engagement = min(note_count / 10.0, 1.0) * 100
        factors["engagement"] = round(engagement, 1)

        # Recency score (last note timestamp)
        last_note_q = (
            select(func.max(OpportunityNote.created_at))
            .where(OpportunityNote.opportunity_id == opportunity_id)
        )
        last_note_ts = (await db.execute(last_note_q)).scalar_one_or_none()

        if last_note_ts:
            days_ago = (datetime.now(timezone.utc) - last_note_ts.replace(tzinfo=timezone.utc)).days
            recency = max(0, 100 - days_ago * 5)
        else:
            recency = 0
        factors["recency"] = recency

        # Deal size score
        amount = float(opp.amount or 0)
        size_score = min(amount / cfg.high_value_threshold, 1.0) * 100
        factors["deal_size"] = round(size_score, 1)

        # Stage progression score
        stage_val = opp.stage.value if hasattr(opp.stage, "value") else str(opp.stage)
        stage_idx = STAGE_ORDER.index(stage_val) if stage_val in STAGE_ORDER else 0
        stage_score = (stage_idx / max(len(STAGE_ORDER) - 1, 1)) * 100
        factors["stage"] = round(stage_score, 1)

        # Fit score (from opportunity.score or custom_fields)
        fit = float(opp.score or 50)
        factors["fit"] = fit

        # Champion score (primary_contact_id set = has champion)
        has_champion = opp.primary_contact_id is not None
        factors["champion"] = 100 if has_champion else 0

        # Weighted total
        total = (
            factors["engagement"] * cfg.engagement_weight
            + factors["recency"] * cfg.recency_weight
            + factors["deal_size"] * cfg.deal_size_weight
            + factors["stage"] * cfg.stage_weight
            + factors["fit"] * cfg.fit_weight
            + factors["champion"] * cfg.champion_weight
        )

        confidence = min(note_count / 5.0, 1.0)

        # Persist score back to the opportunity
        opp.score = Decimal(str(round(total, 2)))
        db.add(opp)
        await db.flush()

        return DealScore(
            total=round(total, 1),
            factors=factors,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Auto-advance (reads + writes DB)
    # ------------------------------------------------------------------

    async def evaluate_auto_advance(
        self, db: AsyncSession, opportunity_id: UUID
    ) -> StageTransition | None:
        """Check if an opportunity should auto-advance based on activities."""
        opp = await db.get(Opportunity, opportunity_id)
        if opp is None:
            return None

        stage_val = opp.stage.value if hasattr(opp.stage, "value") else str(opp.stage)

        # Get activity types from notes
        notes_q = select(OpportunityNote.note_type).where(
            OpportunityNote.opportunity_id == opportunity_id
        )
        notes_result = await db.execute(notes_q)
        activity_types = {row[0] for row in notes_result}
        note_count_q = select(func.count()).select_from(OpportunityNote).where(
            OpportunityNote.opportunity_id == opportunity_id
        )
        note_count = int((await db.execute(note_count_q)).scalar_one())

        new_stage: str | None = None
        reason = ""

        if stage_val == OpportunityStage.PROSPECTING.value and note_count >= 2:
            new_stage = OpportunityStage.QUALIFICATION.value
            reason = "Sufficient engagement (2+ activities)"
        elif stage_val == OpportunityStage.QUALIFICATION.value and NoteType.NOTE.value in activity_types:
            # Check if a "proposal_sent" note exists
            proposal_q = select(func.count()).select_from(OpportunityNote).where(
                OpportunityNote.opportunity_id == opportunity_id,
                OpportunityNote.content.ilike("%proposal sent%"),
            )
            has_proposal = int((await db.execute(proposal_q)).scalar_one()) > 0
            if has_proposal:
                new_stage = OpportunityStage.PROPOSAL.value
                reason = "Proposal sent"
        elif stage_val == OpportunityStage.PROPOSAL.value:
            contract_q = select(func.count()).select_from(OpportunityNote).where(
                OpportunityNote.opportunity_id == opportunity_id,
                OpportunityNote.content.ilike("%contract sent%"),
            )
            has_contract = int((await db.execute(contract_q)).scalar_one()) > 0
            if has_contract:
                new_stage = OpportunityStage.NEGOTIATION.value
                reason = "Contract sent"

        if new_stage is None:
            return None

        old_stage = stage_val

        # Update opportunity stage in DB
        opp.stage = OpportunityStage(new_stage)
        opp.stage_changed_at = datetime.now(timezone.utc)
        opp.previous_stage = old_stage
        db.add(opp)

        # Record the stage transition as a note
        transition_note = OpportunityNote(
            opportunity_id=opportunity_id,
            note_type=NoteType.STATUS_CHANGE.value,
            subject=f"Auto-advanced: {old_stage} → {new_stage}",
            content=reason,
            old_value=old_stage,
            new_value=new_stage,
        )
        db.add(transition_note)
        await db.flush()

        transition = StageTransition(
            deal_id=str(opportunity_id),
            from_stage=old_stage,
            to_stage=new_stage,
            triggered_by="system",
            reason=reason,
        )

        logger.info(
            "Auto-advanced opportunity %s: %s → %s (%s)",
            opportunity_id,
            old_stage,
            new_stage,
            reason,
        )
        return transition

    # ------------------------------------------------------------------
    # Activity tracking (persisted as OpportunityNote)
    # ------------------------------------------------------------------

    async def log_activity(
        self,
        db: AsyncSession,
        opportunity_id: UUID,
        activity_type: ActivityType,
        *,
        user_id: UUID | None = None,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log a CRM activity as an OpportunityNote in the DB."""
        note_type = _ACTIVITY_TO_NOTE.get(activity_type, NoteType.NOTE.value)

        note = OpportunityNote(
            opportunity_id=opportunity_id,
            note_type=note_type,
            subject=f"{activity_type.value} activity",
            content=notes or f"Logged {activity_type.value} activity",
            created_by_id=user_id,
            activity_date=datetime.now(timezone.utc),
            is_internal=True,
        )
        db.add(note)
        await db.flush()

        return {
            "id": str(note.id),
            "deal_id": str(opportunity_id),
            "type": activity_type.value,
            "user_id": str(user_id) if user_id else None,
            "notes": notes,
            "timestamp": note.created_at,
            "metadata": metadata or {},
        }

    async def get_activities(
        self,
        db: AsyncSession,
        opportunity_id: UUID,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get activities for an opportunity from DB, most recent first."""
        stmt = (
            select(OpportunityNote)
            .where(OpportunityNote.opportunity_id == opportunity_id)
            .order_by(OpportunityNote.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        notes = result.scalars().all()

        return [
            {
                "id": str(n.id),
                "deal_id": str(n.opportunity_id),
                "type": n.note_type,
                "subject": n.subject,
                "content": n.content,
                "user_id": str(n.created_by_id) if n.created_by_id else None,
                "timestamp": n.created_at,
                "old_value": n.old_value,
                "new_value": n.new_value,
            }
            for n in notes
        ]

    # ------------------------------------------------------------------
    # Follow-up reminders (query-based, derived from stale opportunities)
    # ------------------------------------------------------------------

    async def get_stale_opportunities(
        self,
        db: AsyncSession,
        *,
        owner_id: UUID | None = None,
    ) -> list[FollowUpReminder]:
        """Find open opportunities with no recent activity (DB query)."""
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=self._config.stale_days_threshold)

        # Subquery: most recent note date per opportunity
        latest_note_sub = (
            select(
                OpportunityNote.opportunity_id,
                func.max(OpportunityNote.created_at).label("last_note"),
            )
            .group_by(OpportunityNote.opportunity_id)
            .subquery()
        )

        stmt = (
            select(Opportunity)
            .outerjoin(latest_note_sub, Opportunity.id == latest_note_sub.c.opportunity_id)
            .where(
                Opportunity.stage.notin_([
                    OpportunityStage.CLOSED_WON,
                    OpportunityStage.CLOSED_LOST,
                ]),
                Opportunity.is_deleted == False,  # noqa: E712
            )
            .where(
                # Either no notes at all, or last note is older than threshold
                (latest_note_sub.c.last_note == None) | (latest_note_sub.c.last_note < threshold)  # noqa: E711
            )
        )
        if owner_id is not None:
            stmt = stmt.where(Opportunity.owner_id == owner_id)

        result = await db.execute(stmt)
        opps = result.scalars().all()

        reminders = []
        for opp in opps:
            reminders.append(
                FollowUpReminder(
                    deal_id=str(opp.id),
                    owner_id=str(opp.owner_id) if opp.owner_id else "",
                    due_date=now,
                    message=f"Opportunity '{opp.name}' has been stale for {self._config.stale_days_threshold}+ days",
                )
            )
        return reminders

    # ------------------------------------------------------------------
    # Transition history (from OpportunityNote status_change entries)
    # ------------------------------------------------------------------

    async def get_transitions(
        self,
        db: AsyncSession,
        opportunity_id: UUID | None = None,
        *,
        limit: int = 100,
    ) -> list[StageTransition]:
        """Get stage transition history from DB."""
        stmt = (
            select(OpportunityNote)
            .where(OpportunityNote.note_type == NoteType.STATUS_CHANGE.value)
        )
        if opportunity_id:
            stmt = stmt.where(OpportunityNote.opportunity_id == opportunity_id)
        stmt = stmt.order_by(OpportunityNote.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        notes = result.scalars().all()

        return [
            StageTransition(
                id=str(n.id),
                deal_id=str(n.opportunity_id),
                from_stage=n.old_value,
                to_stage=n.new_value or "",
                triggered_by=str(n.created_by_id) if n.created_by_id else "system",
                reason=n.content or "",
                timestamp=n.created_at,
            )
            for n in notes
        ]

    async def get_pipeline_velocity(
        self, db: AsyncSession
    ) -> dict[str, Any]:
        """Compute pipeline velocity metrics from DB transition records."""
        stmt = (
            select(OpportunityNote)
            .where(OpportunityNote.note_type == NoteType.STATUS_CHANGE.value)
        )
        result = await db.execute(stmt)
        transitions = result.scalars().all()

        if not transitions:
            return {"avg_days_per_stage": 0, "total_transitions": 0}

        stage_counts: dict[str, int] = {}
        for t in transitions:
            if t.old_value:
                stage_counts[t.old_value] = stage_counts.get(t.old_value, 0) + 1

        return {
            "total_transitions": len(transitions),
            "by_stage": {
                stage: {"count": count}
                for stage, count in stage_counts.items()
            },
        }


# Keep backwards-compatible alias used by __init__.py
PipelineAutomationService = CRMPipelineAutomation

"""
CRM Pipeline Automation Service.

Provides automated stage transitions, deal scoring, follow-up reminders,
and activity tracking for the sales pipeline.

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
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Standard CRM pipeline stages."""

    LEAD = "lead"
    QUALIFIED = "qualified"
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
    from_stage: PipelineStage | None = None
    to_stage: PipelineStage = PipelineStage.LEAD
    triggered_by: str = "system"  # "system" or user_id
    reason: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class FollowUpReminder:
    """A follow-up reminder for a deal."""

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


class CRMPipelineAutomation:
    """Automated pipeline management for CRM deals."""

    STAGE_ORDER = [
        PipelineStage.LEAD,
        PipelineStage.QUALIFIED,
        PipelineStage.PROPOSAL,
        PipelineStage.NEGOTIATION,
        PipelineStage.CLOSED_WON,
    ]

    def __init__(
        self,
        *,
        scoring_config: ScoringConfig | None = None,
    ) -> None:
        self._config = scoring_config or ScoringConfig()
        self._transitions: list[StageTransition] = []
        self._reminders: dict[str, list[FollowUpReminder]] = {}
        self._activities: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Deal scoring
    # ------------------------------------------------------------------

    def score_deal(self, deal: dict[str, Any]) -> DealScore:
        """Compute a weighted deal score (0–100)."""
        cfg = self._config
        factors: dict[str, float] = {}

        # Engagement score (number of activities)
        activities = self._activities.get(deal.get("id", ""), [])
        engagement = min(len(activities) / 10.0, 1.0) * 100
        factors["engagement"] = round(engagement, 1)

        # Recency score (days since last activity)
        if activities:
            last = max(
                a.get("timestamp", datetime.min) for a in activities
            )
            if isinstance(last, str):
                last = datetime.fromisoformat(last)
            days_ago = (datetime.now(timezone.utc) - last).days
            recency = max(0, 100 - days_ago * 5)
        else:
            recency = 0
        factors["recency"] = recency

        # Deal size score
        amount = deal.get("amount", 0) or 0
        size_score = min(amount / cfg.high_value_threshold, 1.0) * 100
        factors["deal_size"] = round(size_score, 1)

        # Stage progression score
        stage = deal.get("stage", PipelineStage.LEAD)
        if isinstance(stage, str):
            try:
                stage = PipelineStage(stage)
            except ValueError:
                stage = PipelineStage.LEAD
        stage_idx = (
            self.STAGE_ORDER.index(stage)
            if stage in self.STAGE_ORDER
            else 0
        )
        stage_score = (stage_idx / max(len(self.STAGE_ORDER) - 1, 1)) * 100
        factors["stage"] = round(stage_score, 1)

        # Fit score (based on ICP match — simplified)
        fit = deal.get("fit_score", 50)
        factors["fit"] = fit

        # Champion score
        has_champion = bool(deal.get("champion_id") or deal.get("champion"))
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

        return DealScore(
            total=round(total, 1),
            factors=factors,
            confidence=min(len(activities) / 5.0, 1.0),
        )

    # ------------------------------------------------------------------
    # Auto-advance
    # ------------------------------------------------------------------

    def evaluate_auto_advance(
        self, deal: dict[str, Any]
    ) -> StageTransition | None:
        """Check if a deal should auto-advance to the next stage."""
        stage = deal.get("stage", PipelineStage.LEAD)
        if isinstance(stage, str):
            try:
                stage = PipelineStage(stage)
            except ValueError:
                return None

        deal_id = deal.get("id", "")
        activities = self._activities.get(deal_id, [])
        activity_types = {a.get("type") for a in activities}

        new_stage: PipelineStage | None = None
        reason = ""

        if stage == PipelineStage.LEAD and len(activities) >= 2:
            new_stage = PipelineStage.QUALIFIED
            reason = "Sufficient engagement (2+ activities)"
        elif (
            stage == PipelineStage.QUALIFIED
            and ActivityType.PROPOSAL_SENT.value in activity_types
        ):
            new_stage = PipelineStage.PROPOSAL
            reason = "Proposal sent"
        elif (
            stage == PipelineStage.PROPOSAL
            and ActivityType.CONTRACT_SENT.value in activity_types
        ):
            new_stage = PipelineStage.NEGOTIATION
            reason = "Contract sent"

        if new_stage:
            transition = StageTransition(
                deal_id=deal_id,
                from_stage=stage,
                to_stage=new_stage,
                triggered_by="system",
                reason=reason,
            )
            self._transitions.append(transition)
            logger.info(
                "Auto-advanced deal %s: %s → %s (%s)",
                deal_id,
                stage.value,
                new_stage.value,
                reason,
            )
            return transition

        return None

    # ------------------------------------------------------------------
    # Activity tracking
    # ------------------------------------------------------------------

    def log_activity(
        self,
        deal_id: str,
        activity_type: ActivityType,
        *,
        user_id: str | None = None,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log a CRM activity for a deal."""
        activity = {
            "id": str(uuid4()),
            "deal_id": deal_id,
            "type": activity_type.value,
            "user_id": user_id,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {},
        }
        self._activities.setdefault(deal_id, []).append(activity)
        return activity

    def get_activities(
        self, deal_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get activities for a deal, most recent first."""
        return sorted(
            self._activities.get(deal_id, []),
            key=lambda a: a.get("timestamp", datetime.min),
            reverse=True,
        )[:limit]

    # ------------------------------------------------------------------
    # Follow-up reminders
    # ------------------------------------------------------------------

    def create_reminder(
        self,
        deal_id: str,
        owner_id: str,
        due_date: datetime,
        message: str = "Follow up on deal",
    ) -> FollowUpReminder:
        """Create a follow-up reminder."""
        reminder = FollowUpReminder(
            deal_id=deal_id,
            owner_id=owner_id,
            due_date=due_date,
            message=message,
        )
        self._reminders.setdefault(deal_id, []).append(reminder)
        return reminder

    def get_overdue_reminders(
        self, owner_id: str | None = None
    ) -> list[FollowUpReminder]:
        """Get all overdue uncompleted reminders."""
        now = datetime.now(timezone.utc)
        overdue: list[FollowUpReminder] = []
        for reminders in self._reminders.values():
            for r in reminders:
                if r.completed:
                    continue
                if r.due_date <= now:
                    if owner_id is None or r.owner_id == owner_id:
                        overdue.append(r)
        return overdue

    def generate_stale_deal_reminders(
        self, deals: list[dict[str, Any]]
    ) -> list[FollowUpReminder]:
        """Create reminders for deals with no recent activity."""
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=self._config.stale_days_threshold)
        created: list[FollowUpReminder] = []

        for deal in deals:
            deal_id = deal.get("id", "")
            stage = deal.get("stage", "")
            if stage in (
                PipelineStage.CLOSED_WON.value,
                PipelineStage.CLOSED_LOST.value,
            ):
                continue

            activities = self._activities.get(deal_id, [])
            if activities:
                last_ts = max(a.get("timestamp", datetime.min) for a in activities)
                if isinstance(last_ts, str):
                    last_ts = datetime.fromisoformat(last_ts)
                if last_ts > threshold:
                    continue

            owner_id = deal.get("owner_id", "")
            reminder = self.create_reminder(
                deal_id=deal_id,
                owner_id=owner_id,
                due_date=now,
                message=f"Deal '{deal.get('name', deal_id)}' has been stale for {self._config.stale_days_threshold}+ days",
            )
            created.append(reminder)

        return created

    # ------------------------------------------------------------------
    # Transition history
    # ------------------------------------------------------------------

    def get_transitions(
        self, deal_id: str | None = None, *, limit: int = 100
    ) -> list[StageTransition]:
        """Get stage transition history."""
        transitions = self._transitions
        if deal_id:
            transitions = [t for t in transitions if t.deal_id == deal_id]
        return transitions[-limit:]

    def get_pipeline_velocity(self) -> dict[str, Any]:
        """Compute pipeline velocity metrics."""
        if not self._transitions:
            return {"avg_days_per_stage": 0, "total_transitions": 0}

        stage_durations: dict[str, list[float]] = {}
        for t in self._transitions:
            if t.from_stage:
                stage_durations.setdefault(t.from_stage.value, []).append(1.0)

        return {
            "total_transitions": len(self._transitions),
            "by_stage": {
                stage: {
                    "count": len(durations),
                    "avg_transitions": round(sum(durations) / len(durations), 1),
                }
                for stage, durations in stage_durations.items()
            },
        }

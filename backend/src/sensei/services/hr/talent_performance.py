"""Talent & Performance (Lean-Aligned) Service (Development Plan 21.7).

Implements:
- Lean Performance Reviews: periodic reviews that incorporate A3 contributions,
  suggestion participation, and OEE signals.
- Succession Planning: track high-potential employees for key roles.
- Recognition Engine: award praise milestones tied to successful A3 outcomes.

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin


def _require_tzaware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("All datetimes must be timezone-aware")


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


_HR_WRITE_ROLES: set[str] = {"admin", "hr"}
_MANAGER_ROLES: set[str] = {"gm", "exec", "ops", "supervisor", "manager"}
_SUCCESSION_WRITE_ROLES: set[str] = _HR_WRITE_ROLES.union({"exec", "ceo"})


class ReviewCycleType(str, Enum):
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"


class A3ContributionType(str, Enum):
    OWNER = "owner"
    CONTRIBUTOR = "contributor"


class SuggestionStatus(str, Enum):
    SUBMITTED = "submitted"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"


class PraiseType(str, Enum):
    A3_SUCCESS = "a3_success"
    KAIZEN_CHAMPION = "kaizen_champion"
    OEE_EXCELLENCE = "oee_excellence"


@dataclass(frozen=True)
class A3Contribution:
    id: UUID
    employee_id: str
    a3_id: str
    contribution_type: A3ContributionType
    points: int
    occurred_at: datetime


@dataclass(frozen=True)
class Suggestion:
    id: UUID
    employee_id: str
    title: str
    status: SuggestionStatus
    created_at: datetime

    decided_at: datetime | None = None
    decided_by: str | None = None


@dataclass(frozen=True)
class OeeSnapshot:
    id: UUID
    employee_id: str
    station_id: str
    day: date

    oee: float  # 0..1
    availability: float | None = None
    performance: float | None = None
    quality: float | None = None

    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PerformanceReviewMetrics:
    a3_points: int
    a3_count: int
    suggestions_submitted: int
    suggestions_implemented: int
    avg_oee: float | None

    score: float


@dataclass(frozen=True)
class PerformanceReview:
    id: UUID
    employee_id: str
    cycle_type: ReviewCycleType
    period_start: date
    period_end: date

    status: ReviewStatus
    created_at: datetime
    created_by: str

    reviewer_employee_id: str | None = None
    submitted_at: datetime | None = None
    submitted_by: str | None = None

    approved_at: datetime | None = None
    approved_by: str | None = None

    employee_notes: str = ""
    reviewer_notes: str = ""

    metrics: PerformanceReviewMetrics | None = None


@dataclass(frozen=True)
class SuccessionCandidate:
    id: UUID
    employee_id: str
    target_role: str
    readiness: float  # 0..1

    created_at: datetime
    created_by: str

    updated_at: datetime | None = None
    updated_by: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class PraiseMilestone:
    id: UUID
    employee_id: str
    praise_type: PraiseType
    message: str

    source_type: str
    source_id: str

    awarded_at: datetime
    awarded_by: str


class TalentPerformanceService(PersistentServiceMixin):
    """Lean talent & performance service."""

    SERVICE_NAME = "talent_performance"

    def __init__(self) -> None:
        self._a3_contribs: dict[UUID, A3Contribution] = {}
        self._suggestions: dict[UUID, Suggestion] = {}
        self._oee: dict[UUID, OeeSnapshot] = {}
        self._reviews: dict[UUID, PerformanceReview] = {}
        self._succession: dict[UUID, SuccessionCandidate] = {}
        self._praise: dict[UUID, PraiseMilestone] = {}

        # Optional org map for manager checks (employee -> manager)
        self._manager_of: dict[str, str] = {}

    def set_manager(self, *, employee_id: str, manager_employee_id: str, actor_roles: Iterable[str]) -> None:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_HR_WRITE_ROLES.union(_MANAGER_ROLES)):
            raise PermissionError("HR/Manager role required")
        self._manager_of[employee_id] = manager_employee_id

    def record_a3_contribution(
        self,
        *,
        employee_id: str,
        a3_id: str,
        contribution_type: A3ContributionType,
        occurred_at: datetime | None = None,
        points: int | None = None,
    ) -> A3Contribution:
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)
        _require_tzaware(occurred_at)

        if points is None:
            points = 5 if contribution_type == A3ContributionType.OWNER else 2

        contrib = A3Contribution(
            id=uuid4(),
            employee_id=employee_id,
            a3_id=a3_id,
            contribution_type=contribution_type,
            points=int(points),
            occurred_at=occurred_at,
        )
        self._a3_contribs[contrib.id] = contrib
        return contrib

    def submit_suggestion(
        self,
        *,
        employee_id: str,
        title: str,
        created_at: datetime | None = None,
    ) -> Suggestion:
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        _require_tzaware(created_at)
        sug = Suggestion(
            id=uuid4(),
            employee_id=employee_id,
            title=title.strip(),
            status=SuggestionStatus.SUBMITTED,
            created_at=created_at,
        )
        self._suggestions[sug.id] = sug
        return sug

    def decide_suggestion(
        self,
        *,
        suggestion_id: UUID,
        status: SuggestionStatus,
        decided_by: str,
        actor_roles: Iterable[str],
        decided_at: datetime | None = None,
    ) -> Suggestion:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_HR_WRITE_ROLES.union(_MANAGER_ROLES)):
            raise PermissionError("HR/Manager role required")
        if decided_at is None:
            decided_at = datetime.now(timezone.utc)
        _require_tzaware(decided_at)

        existing = self._suggestions.get(suggestion_id)
        if existing is None:
            raise KeyError("Suggestion not found")
        if status == SuggestionStatus.SUBMITTED:
            raise ValueError("Cannot decide suggestion back to submitted")

        updated = replace(
            existing,
            status=status,
            decided_at=decided_at,
            decided_by=decided_by,
        )
        self._suggestions[suggestion_id] = updated
        return updated

    def record_oee_snapshot(
        self,
        *,
        employee_id: str,
        station_id: str,
        day: date,
        oee: float,
        availability: float | None = None,
        performance: float | None = None,
        quality: float | None = None,
        recorded_at: datetime | None = None,
    ) -> OeeSnapshot:
        if not (0.0 <= float(oee) <= 1.0):
            raise ValueError("oee must be in [0, 1]")
        if recorded_at is None:
            recorded_at = datetime.now(timezone.utc)
        _require_tzaware(recorded_at)

        snap = OeeSnapshot(
            id=uuid4(),
            employee_id=employee_id,
            station_id=station_id,
            day=day,
            oee=float(oee),
            availability=None if availability is None else float(availability),
            performance=None if performance is None else float(performance),
            quality=None if quality is None else float(quality),
            recorded_at=recorded_at,
        )
        self._oee[snap.id] = snap
        return snap

    def _is_manager_of(self, *, manager_employee_id: str, employee_id: str) -> bool:
        return self._manager_of.get(employee_id) == manager_employee_id

    def _require_review_write(
        self,
        *,
        actor_employee_id: str,
        actor_roles: Iterable[str],
        employee_id: str,
    ) -> None:
        roles = _norm_roles(actor_roles)
        if roles.intersection(_HR_WRITE_ROLES):
            return
        if roles.intersection(_MANAGER_ROLES) and self._is_manager_of(
            manager_employee_id=actor_employee_id, employee_id=employee_id
        ):
            return
        raise PermissionError("HR/Admin or direct manager required")

    def compute_metrics(
        self,
        *,
        employee_id: str,
        period_start: date,
        period_end: date,
    ) -> PerformanceReviewMetrics:
        if period_end < period_start:
            raise ValueError("period_end must be >= period_start")

        a3 = [
            c
            for c in self._a3_contribs.values()
            if c.employee_id == employee_id
            and period_start <= c.occurred_at.date() <= period_end
        ]
        a3_points = sum(c.points for c in a3)

        suggestions = [
            s
            for s in self._suggestions.values()
            if s.employee_id == employee_id
            and period_start <= s.created_at.date() <= period_end
        ]
        suggestions_submitted = len(suggestions)
        suggestions_implemented = len(
            [s for s in suggestions if s.status == SuggestionStatus.IMPLEMENTED]
        )

        oee_snaps = [
            o
            for o in self._oee.values()
            if o.employee_id == employee_id and period_start <= o.day <= period_end
        ]
        avg_oee = None
        if oee_snaps:
            avg_oee = sum(o.oee for o in oee_snaps) / len(oee_snaps)

        # Simple, deterministic scoring:
        # - A3 contributions are worth points (owner 5, contributor 2)
        # - Suggestions: submitted 1 each, implemented 3 each
        # - OEE: average oee * 10 (0..10)
        suggestion_points = (suggestions_submitted * 1) + (suggestions_implemented * 3)
        oee_points = (avg_oee * 10.0) if avg_oee is not None else 0.0
        score = float(a3_points) + float(suggestion_points) + float(oee_points)

        return PerformanceReviewMetrics(
            a3_points=a3_points,
            a3_count=len(a3),
            suggestions_submitted=suggestions_submitted,
            suggestions_implemented=suggestions_implemented,
            avg_oee=avg_oee,
            score=score,
        )

    def create_performance_review(
        self,
        *,
        employee_id: str,
        cycle_type: ReviewCycleType,
        period_start: date,
        period_end: date,
        created_by: str,
        actor_roles: Iterable[str],
        reviewer_employee_id: str | None = None,
        created_at: datetime | None = None,
    ) -> PerformanceReview:
        self._require_review_write(
            actor_employee_id=created_by,
            actor_roles=actor_roles,
            employee_id=employee_id,
        )
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        _require_tzaware(created_at)

        metrics = self.compute_metrics(
            employee_id=employee_id, period_start=period_start, period_end=period_end
        )

        review = PerformanceReview(
            id=uuid4(),
            employee_id=employee_id,
            cycle_type=cycle_type,
            period_start=period_start,
            period_end=period_end,
            status=ReviewStatus.DRAFT,
            created_at=created_at,
            created_by=created_by,
            reviewer_employee_id=reviewer_employee_id,
            metrics=metrics,
        )
        self._reviews[review.id] = review
        return review

    def submit_review(
        self,
        *,
        review_id: UUID,
        submitted_by: str,
        actor_roles: Iterable[str],
        submitted_at: datetime | None = None,
    ) -> PerformanceReview:
        if submitted_at is None:
            submitted_at = datetime.now(timezone.utc)
        _require_tzaware(submitted_at)

        existing = self._reviews.get(review_id)
        if existing is None:
            raise KeyError("Review not found")

        # Employee can submit their own review; HR/manager can submit as well.
        if submitted_by != existing.employee_id:
            self._require_review_write(
                actor_employee_id=submitted_by,
                actor_roles=actor_roles,
                employee_id=existing.employee_id,
            )

        updated = replace(
            existing,
            status=ReviewStatus.SUBMITTED,
            submitted_at=submitted_at,
            submitted_by=submitted_by,
        )
        self._reviews[review_id] = updated
        return updated

    def approve_review(
        self,
        *,
        review_id: UUID,
        approved_by: str,
        actor_roles: Iterable[str],
        approved_at: datetime | None = None,
    ) -> PerformanceReview:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_HR_WRITE_ROLES.union({"gm", "exec", "ceo"})):
            raise PermissionError("HR/Admin/GM/Exec role required")
        if approved_at is None:
            approved_at = datetime.now(timezone.utc)
        _require_tzaware(approved_at)

        existing = self._reviews.get(review_id)
        if existing is None:
            raise KeyError("Review not found")
        if existing.status != ReviewStatus.SUBMITTED:
            raise ValueError("Review must be submitted before approval")

        updated = replace(
            existing,
            status=ReviewStatus.APPROVED,
            approved_at=approved_at,
            approved_by=approved_by,
        )
        self._reviews[review_id] = updated
        return updated

    def upsert_succession_candidate(
        self,
        *,
        employee_id: str,
        target_role: str,
        readiness: float,
        actor_id: str,
        actor_roles: Iterable[str],
        notes: str = "",
        now: datetime | None = None,
    ) -> SuccessionCandidate:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_SUCCESSION_WRITE_ROLES):
            raise PermissionError("HR/Admin/Exec role required")
        if not (0.0 <= float(readiness) <= 1.0):
            raise ValueError("readiness must be in [0, 1]")
        if now is None:
            now = datetime.now(timezone.utc)
        _require_tzaware(now)

        # Find existing by employee_id + target_role
        existing_id = None
        for cid, cand in self._succession.items():
            if cand.employee_id == employee_id and cand.target_role == target_role:
                existing_id = cid
                break

        if existing_id is None:
            cand = SuccessionCandidate(
                id=uuid4(),
                employee_id=employee_id,
                target_role=target_role.strip(),
                readiness=float(readiness),
                created_at=now,
                created_by=actor_id,
                notes=notes.strip(),
            )
            self._succession[cand.id] = cand
            return cand

        prev = self._succession[existing_id]
        updated = replace(
            prev,
            readiness=float(readiness),
            notes=notes.strip(),
            updated_at=now,
            updated_by=actor_id,
        )
        self._succession[existing_id] = updated
        return updated

    def list_succession_candidates(self, *, target_role: str | None = None) -> list[SuccessionCandidate]:
        items = list(self._succession.values())
        if target_role:
            items = [c for c in items if c.target_role == target_role]
        return sorted(items, key=lambda c: (-c.readiness, c.created_at))

    def record_a3_outcome(
        self,
        *,
        a3_id: str,
        success: bool,
        impact_score: float,
        closed_at: datetime | None = None,
        closed_by: str,
        actor_roles: Iterable[str],
    ) -> list[PraiseMilestone]:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_HR_WRITE_ROLES.union(_MANAGER_ROLES)):
            raise PermissionError("HR/Manager role required")
        if closed_at is None:
            closed_at = datetime.now(timezone.utc)
        _require_tzaware(closed_at)

        if not success or impact_score <= 0:
            return []

        contribs = [c for c in self._a3_contribs.values() if c.a3_id == a3_id]
        # Award the owner (or all contributors if owner unknown)
        owners = [c for c in contribs if c.contribution_type == A3ContributionType.OWNER]
        awardees = owners if owners else contribs

        created: list[PraiseMilestone] = []
        for c in awardees:
            milestone = PraiseMilestone(
                id=uuid4(),
                employee_id=c.employee_id,
                praise_type=PraiseType.A3_SUCCESS,
                message=f"A3 success: {a3_id} (impact {impact_score:.1f})",
                source_type="a3",
                source_id=a3_id,
                awarded_at=closed_at,
                awarded_by=closed_by,
            )
            self._praise[milestone.id] = milestone
            created.append(milestone)

        return created

    def list_praise(self, *, employee_id: str | None = None) -> list[PraiseMilestone]:
        items = list(self._praise.values())
        if employee_id is not None:
            items = [p for p in items if p.employee_id == employee_id]
        return sorted(items, key=lambda p: p.awarded_at)

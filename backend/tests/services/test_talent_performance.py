from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from sensei.services.hr.talent_performance import (
    A3ContributionType,
    PraiseType,
    ReviewCycleType,
    ReviewStatus,
    SuggestionStatus,
    TalentPerformanceService,
)


def _dt(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


class TestTalentPerformance:
    def test_review_metrics_and_score_include_a3_suggestions_and_oee(self):
        service = TalentPerformanceService()
        employee_id = "emp-1"

        # Contributions
        service.record_a3_contribution(
            employee_id=employee_id,
            a3_id="a3-1",
            contribution_type=A3ContributionType.OWNER,
            occurred_at=_dt(2026, 1, 2, 10, 0),
        )
        service.record_a3_contribution(
            employee_id=employee_id,
            a3_id="a3-2",
            contribution_type=A3ContributionType.CONTRIBUTOR,
            occurred_at=_dt(2026, 1, 3, 10, 0),
        )

        # Suggestion submitted + implemented
        sug = service.submit_suggestion(
            employee_id=employee_id, title="Improve changeover checklist", created_at=_dt(2026, 1, 4, 9, 0)
        )
        sug2 = service.decide_suggestion(
            suggestion_id=sug.id,
            status=SuggestionStatus.IMPLEMENTED,
            decided_by="mgr-1",
            actor_roles=["supervisor"],
            decided_at=_dt(2026, 1, 10, 9, 0),
        )
        assert sug2.status == SuggestionStatus.IMPLEMENTED

        # OEE snapshots
        service.record_oee_snapshot(
            employee_id=employee_id,
            station_id="st-1",
            day=date(2026, 1, 5),
            oee=0.80,
        )
        service.record_oee_snapshot(
            employee_id=employee_id,
            station_id="st-1",
            day=date(2026, 1, 6),
            oee=0.90,
        )

        review = service.create_performance_review(
            employee_id=employee_id,
            cycle_type=ReviewCycleType.QUARTERLY,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            created_by="hr-1",
            actor_roles=["hr"],
            reviewer_employee_id="mgr-1",
            created_at=_dt(2026, 2, 1, 9, 0),
        )

        assert review.metrics is not None
        assert review.metrics.a3_count == 2
        assert review.metrics.a3_points == 7  # owner 5 + contributor 2
        assert review.metrics.suggestions_submitted == 1
        assert review.metrics.suggestions_implemented == 1
        assert review.metrics.avg_oee == pytest.approx(0.85)

        # score = a3_points (7) + suggestion_points (1 + 3) + oee_points (0.85*10=8.5)
        assert review.metrics.score == pytest.approx(19.5)

    def test_review_creation_requires_hr_or_direct_manager(self):
        service = TalentPerformanceService()
        service.set_manager(employee_id="emp-2", manager_employee_id="mgr-2", actor_roles=["hr"])

        with pytest.raises(PermissionError):
            service.create_performance_review(
                employee_id="emp-2",
                cycle_type=ReviewCycleType.QUARTERLY,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                created_by="someone",
                actor_roles=["operator"],
            )

        # Direct manager allowed
        review = service.create_performance_review(
            employee_id="emp-2",
            cycle_type=ReviewCycleType.QUARTERLY,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            created_by="mgr-2",
            actor_roles=["supervisor"],
        )
        assert review.employee_id == "emp-2"

    def test_succession_candidate_requires_privileged_roles(self):
        service = TalentPerformanceService()

        with pytest.raises(PermissionError):
            service.upsert_succession_candidate(
                employee_id="emp-3",
                target_role="gm",
                readiness=0.7,
                actor_id="emp-3",
                actor_roles=["operator"],
            )

        cand = service.upsert_succession_candidate(
            employee_id="emp-3",
            target_role="gm",
            readiness=0.7,
            actor_id="hr-1",
            actor_roles=["hr"],
            notes="Strong kata coaching",
            now=_dt(2026, 1, 15, 9, 0),
        )
        assert cand.readiness == pytest.approx(0.7)

        cand2 = service.upsert_succession_candidate(
            employee_id="emp-3",
            target_role="gm",
            readiness=0.8,
            actor_id="hr-1",
            actor_roles=["hr"],
            notes="Improving leadership",
            now=_dt(2026, 2, 1, 9, 0),
        )
        assert cand2.id == cand.id
        assert cand2.readiness == pytest.approx(0.8)

    def test_a3_success_awards_praise_to_owner(self):
        service = TalentPerformanceService()
        service.record_a3_contribution(
            employee_id="emp-4",
            a3_id="a3-99",
            contribution_type=A3ContributionType.OWNER,
            occurred_at=_dt(2026, 1, 5, 10, 0),
        )

        milestones = service.record_a3_outcome(
            a3_id="a3-99",
            success=True,
            impact_score=2.5,
            closed_by="mgr-9",
            actor_roles=["supervisor"],
            closed_at=_dt(2026, 1, 20, 12, 0),
        )
        assert len(milestones) == 1
        assert milestones[0].employee_id == "emp-4"
        assert milestones[0].praise_type == PraiseType.A3_SUCCESS

        listed = service.list_praise(employee_id="emp-4")
        assert len(listed) == 1
        assert listed[0].source_id == "a3-99"

    def test_review_submit_and_approve_flow(self):
        service = TalentPerformanceService()
        service.set_manager(employee_id="emp-5", manager_employee_id="mgr-5", actor_roles=["hr"])

        review = service.create_performance_review(
            employee_id="emp-5",
            cycle_type=ReviewCycleType.QUARTERLY,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            created_by="mgr-5",
            actor_roles=["manager"],
        )
        assert review.status == ReviewStatus.DRAFT

        submitted = service.submit_review(
            review_id=review.id,
            submitted_by="emp-5",
            actor_roles=["operator"],
            submitted_at=_dt(2026, 2, 1, 9, 0),
        )
        assert submitted.status == ReviewStatus.SUBMITTED

        with pytest.raises(PermissionError):
            service.approve_review(
                review_id=review.id,
                approved_by="emp-5",
                actor_roles=["operator"],
            )

        approved = service.approve_review(
            review_id=review.id,
            approved_by="hr-1",
            actor_roles=["hr"],
            approved_at=_dt(2026, 2, 2, 9, 0),
        )
        assert approved.status == ReviewStatus.APPROVED

        with pytest.raises(ValueError):
            service.approve_review(
                review_id=review.id,
                approved_by="hr-1",
                actor_roles=["hr"],
            )

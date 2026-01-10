"""Tests for Hypercare Monitoring & Cutover Seeding service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.hypercare import (
    ChangeApprovalStatus,
    ChecklistItemStatus,
    ConfigChangeRequest,
    ConfigChangeType,
    FeedbackStatus,
    FeedbackType,
    GoLiveChecklist,
    HypercareService,
    SeedJob,
    SeedStatus,
    UserFeedback,
)


@pytest.fixture
def svc() -> HypercareService:
    return HypercareService()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ADMIN_ROLES = ("admin",)
IT_ROLES = ("it",)
OPS_ROLES = ("ops",)
VIEWER_ROLES = ("viewer",)


class TestUserFeedback:
    def test_any_user_can_submit_feedback(self, svc: HypercareService) -> None:
        feedback = svc.submit_feedback(
            user_id=uuid4(),
            feedback_type=FeedbackType.BUG,
            message="The button doesn't work",
            page_context="/dashboard",
        )

        assert isinstance(feedback, UserFeedback)
        assert feedback.status == FeedbackStatus.NEW

    def test_list_feedback_requires_role(self, svc: HypercareService) -> None:
        svc.submit_feedback(
            user_id=uuid4(),
            feedback_type=FeedbackType.SUGGESTION,
            message="Add dark mode",
        )

        with pytest.raises(PermissionError):
            svc.list_feedback(actor_roles=VIEWER_ROLES)

        feedbacks = svc.list_feedback(actor_roles=OPS_ROLES)
        assert len(feedbacks) == 1

    def test_update_feedback_status(self, svc: HypercareService) -> None:
        feedback = svc.submit_feedback(
            user_id=uuid4(),
            feedback_type=FeedbackType.QUESTION,
            message="How do I export?",
        )

        resolved = svc.update_feedback_status(
            feedback.id, status=FeedbackStatus.RESOLVED, actor_roles=ADMIN_ROLES
        )
        assert resolved.status == FeedbackStatus.RESOLVED
        assert resolved.resolved_at is not None


class TestConfigChangeControl:
    def test_request_and_approve_change(self, svc: HypercareService) -> None:
        request = svc.request_config_change(
            change_type=ConfigChangeType.FEATURE_FLAG,
            key="ENABLE_NEW_DASHBOARD",
            old_value=False,
            new_value=True,
            reason="Go-live rollout",
            actor_user_id=uuid4(),
            actor_roles=IT_ROLES,
        )

        assert isinstance(request, ConfigChangeRequest)
        assert request.status == ChangeApprovalStatus.PENDING

        # Dry-run.
        validated = svc.dry_run_change(request.id, actor_roles=ADMIN_ROLES)
        assert validated.dry_run_result is not None
        assert validated.dry_run_result["valid"] is True

        # Approve.
        approved = svc.approve_change(
            request.id, actor_user_id=uuid4(), actor_roles=ADMIN_ROLES
        )
        assert approved.status == ChangeApprovalStatus.APPROVED

    def test_requires_role(self, svc: HypercareService) -> None:
        with pytest.raises(PermissionError):
            svc.request_config_change(
                change_type=ConfigChangeType.SETTING,
                key="THEME",
                old_value="light",
                new_value="dark",
                reason="Test",
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )


class TestEnvironmentSync:
    def test_export_and_import_config(self, svc: HypercareService) -> None:
        config_data = {"feature_x": True, "timeout": 30}

        export = svc.export_config(
            environment="staging",
            config_data=config_data,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        imported = svc.import_config(export.id, actor_roles=IT_ROLES)
        assert imported == config_data


class TestSeedJobs:
    def test_create_and_run_seed_job(self, svc: HypercareService) -> None:
        job = svc.create_seed_job(
            entity_type="parts",
            record_count=1000,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(job, SeedJob)
        assert job.status == SeedStatus.PENDING

        completed = svc.run_seed_job(job.id, actor_roles=ADMIN_ROLES)
        assert completed.status == SeedStatus.COMPLETED
        assert completed.completed_at is not None

    def test_seed_job_failure(self, svc: HypercareService) -> None:
        job = svc.create_seed_job(
            entity_type="boms",
            record_count=500,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        failed = svc.run_seed_job(job.id, actor_roles=ADMIN_ROLES, simulate_failure=True)
        assert failed.status == SeedStatus.FAILED
        assert failed.error_message is not None


class TestGoLiveChecklist:
    def test_create_and_sign_off(self, svc: HypercareService) -> None:
        checklist = svc.create_checklist(
            name="Plant A Go-Live",
            target_date=_utcnow() + timedelta(days=7),
            departments=["IT", "Operations", "Quality"],
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(checklist, GoLiveChecklist)
        assert len(checklist.items) == 3
        assert not svc.is_checklist_complete(checklist.id)

        # Sign off all items.
        for item in checklist.items:
            svc.sign_off_item(
                checklist.id, item.id, actor_user_id=uuid4(), actor_roles=ADMIN_ROLES
            )

        assert svc.is_checklist_complete(checklist.id)

    def test_checklist_requires_role(self, svc: HypercareService) -> None:
        with pytest.raises(PermissionError):
            svc.create_checklist(
                name="Test",
                target_date=_utcnow(),
                departments=["IT"],
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

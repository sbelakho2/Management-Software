"""Hypercare Monitoring & Cutover Seeding (Development Plan 21.10).

Implements:
- In-App Feedback: one-tap user feedback during first 90 days of site Level-Up.
- Configuration Change Control: heightened audit + dry-run validation for go-live.
- Environment Sync: config export/import between Staging and Production.
- Master Data Seed Scripts: bulk data migration tooling.
- Go-Live Checklist Engine: department sign-off gates before cutover.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class FeedbackType(str, Enum):
    BUG = "bug"
    SUGGESTION = "suggestion"
    QUESTION = "question"
    PRAISE = "praise"


class FeedbackStatus(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class ConfigChangeType(str, Enum):
    SETTING = "setting"
    FEATURE_FLAG = "feature_flag"
    PERMISSION = "permission"
    INTEGRATION = "integration"


class ChangeApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SeedStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChecklistItemStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SIGNED_OFF = "signed_off"
    BLOCKED = "blocked"


_HYPERCARE_ADMIN_ROLES: set[str] = {"admin", "gm", "exec", "ceo", "ops"}
_CUTOVER_ADMIN_ROLES: set[str] = {"admin", "it", "gm"}
_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserFeedback:
    id: UUID
    user_id: UUID
    feedback_type: FeedbackType
    message: str
    page_context: str | None
    status: FeedbackStatus
    created_at: datetime
    resolved_at: datetime | None = None


@dataclass
class ConfigChangeRequest:
    id: UUID
    change_type: ConfigChangeType
    key: str
    old_value: Any
    new_value: Any
    reason: str
    status: ChangeApprovalStatus
    dry_run_result: dict[str, Any] | None
    requested_by: UUID
    requested_at: datetime
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None


@dataclass(frozen=True)
class EnvironmentConfig:
    id: UUID
    environment: str
    config_data: dict[str, Any]
    exported_at: datetime
    exported_by: UUID


@dataclass
class SeedJob:
    id: UUID
    entity_type: str
    record_count: int
    status: SeedStatus
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: UUID
    created_at: datetime


@dataclass
class ChecklistItem:
    id: UUID
    checklist_id: UUID
    department: str
    description: str
    status: ChecklistItemStatus
    signed_off_by: UUID | None
    signed_off_at: datetime | None


@dataclass
class GoLiveChecklist:
    id: UUID
    name: str
    target_date: datetime
    items: list[ChecklistItem]
    created_by: UUID
    created_at: datetime


class HypercareService(PersistentServiceMixin):
    """In-memory hypercare monitoring & cutover support service."""

    SERVICE_NAME = "hypercare"

    def __init__(self) -> None:
        self._feedback: dict[UUID, UserFeedback] = {}
        self._change_requests: dict[UUID, ConfigChangeRequest] = {}
        self._exports: dict[UUID, EnvironmentConfig] = {}
        self._seed_jobs: dict[UUID, SeedJob] = {}
        self._checklists: dict[UUID, GoLiveChecklist] = {}
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        feedback_data = await self.load_state(_DEFAULT_TENANT_ID, "feedback") or {}
        changes_data = await self.load_state(_DEFAULT_TENANT_ID, "changes") or {}
        exports_data = await self.load_state(_DEFAULT_TENANT_ID, "exports") or {}
        seed_jobs_data = await self.load_state(_DEFAULT_TENANT_ID, "seed_jobs") or {}
        checklists_data = await self.load_state(_DEFAULT_TENANT_ID, "checklists") or {}

        self._feedback = {UUID(fid): decode_dataclass(f, UserFeedback) for fid, f in feedback_data.items()}
        self._change_requests = {UUID(cid): decode_dataclass(c, ConfigChangeRequest) for cid, c in changes_data.items()}
        self._exports = {UUID(eid): decode_dataclass(e, EnvironmentConfig) for eid, e in exports_data.items()}
        self._seed_jobs = {UUID(sid): decode_dataclass(s, SeedJob) for sid, s in seed_jobs_data.items()}
        self._checklists = {UUID(cid): decode_dataclass(c, GoLiveChecklist) for cid, c in checklists_data.items()}
        self._state_loaded = True

    async def persist_all(self) -> None:
        feedback_data = {str(fid): encode_dataclass(f) for fid, f in self._feedback.items()}
        changes_data = {str(cid): encode_dataclass(c) for cid, c in self._change_requests.items()}
        exports_data = {str(eid): encode_dataclass(e) for eid, e in self._exports.items()}
        seed_jobs_data = {str(sid): encode_dataclass(s) for sid, s in self._seed_jobs.items()}
        checklists_data = {str(cid): encode_dataclass(c) for cid, c in self._checklists.items()}

        await self.save_state(_DEFAULT_TENANT_ID, "feedback", feedback_data)
        await self.save_state(_DEFAULT_TENANT_ID, "changes", changes_data)
        await self.save_state(_DEFAULT_TENANT_ID, "exports", exports_data)
        await self.save_state(_DEFAULT_TENANT_ID, "seed_jobs", seed_jobs_data)
        await self.save_state(_DEFAULT_TENANT_ID, "checklists", checklists_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ---- RBAC ----

    def can_admin_hypercare(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_HYPERCARE_ADMIN_ROLES)) > 0

    def can_admin_cutover(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_CUTOVER_ADMIN_ROLES)) > 0

    # ---- In-App Feedback ----

    def submit_feedback(
        self,
        *,
        user_id: UUID,
        feedback_type: FeedbackType,
        message: str,
        page_context: str | None = None,
    ) -> UserFeedback:
        """Any user can submit feedback (no role check)."""
        feedback = UserFeedback(
            id=uuid4(),
            user_id=user_id,
            feedback_type=feedback_type,
            message=message.strip(),
            page_context=page_context,
            status=FeedbackStatus.NEW,
            created_at=_utcnow(),
        )
        self._feedback[feedback.id] = feedback
        return feedback

    async def submit_feedback_async(self, **kwargs: Any) -> UserFeedback:
        await self._ensure_loaded()
        feedback = self.submit_feedback(**kwargs)
        await self.persist_all()
        return feedback

    def list_feedback(
        self,
        *,
        actor_roles: Iterable[str],
        status: FeedbackStatus | None = None,
    ) -> list[UserFeedback]:
        if not self.can_admin_hypercare(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view feedback")

        result = list(self._feedback.values())
        if status:
            result = [f for f in result if f.status == status]
        result.sort(key=lambda f: f.created_at, reverse=True)
        return result

    async def list_feedback_async(self, **kwargs: Any) -> list[UserFeedback]:
        await self._ensure_loaded()
        return self.list_feedback(**kwargs)

    def update_feedback_status(
        self,
        feedback_id: UUID,
        *,
        status: FeedbackStatus,
        actor_roles: Iterable[str],
    ) -> UserFeedback:
        if not self.can_admin_hypercare(actor_roles=actor_roles):
            raise PermissionError("Not permitted to update feedback")
        if feedback_id not in self._feedback:
            raise KeyError("Feedback not found")

        feedback = self._feedback[feedback_id]
        feedback.status = status
        if status == FeedbackStatus.RESOLVED:
            feedback.resolved_at = _utcnow()
        return feedback

    async def update_feedback_status_async(self, **kwargs: Any) -> UserFeedback:
        await self._ensure_loaded()
        feedback = self.update_feedback_status(**kwargs)
        await self.persist_all()
        return feedback

    # ---- Configuration Change Control ----

    def request_config_change(
        self,
        *,
        change_type: ConfigChangeType,
        key: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> ConfigChangeRequest:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to request config changes")

        request = ConfigChangeRequest(
            id=uuid4(),
            change_type=change_type,
            key=key,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            status=ChangeApprovalStatus.PENDING,
            dry_run_result=None,
            requested_by=actor_user_id,
            requested_at=_utcnow(),
        )
        self._change_requests[request.id] = request
        return request

    async def request_config_change_async(self, **kwargs: Any) -> ConfigChangeRequest:
        await self._ensure_loaded()
        change = self.request_config_change(**kwargs)
        await self.persist_all()
        return change

    def dry_run_change(
        self,
        request_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> ConfigChangeRequest:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to run dry-run")
        if request_id not in self._change_requests:
            raise KeyError("Change request not found")

        request = self._change_requests[request_id]

        # Simulate dry-run validation.
        request.dry_run_result = {
            "valid": True,
            "affected_entities": 0,
            "warnings": [],
        }
        return request

    async def dry_run_change_async(self, **kwargs: Any) -> ConfigChangeRequest:
        await self._ensure_loaded()
        change = self.dry_run_change(**kwargs)
        await self.persist_all()
        return change

    def approve_change(
        self,
        request_id: UUID,
        *,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> ConfigChangeRequest:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to approve changes")
        if request_id not in self._change_requests:
            raise KeyError("Change request not found")

        request = self._change_requests[request_id]
        request.status = ChangeApprovalStatus.APPROVED
        request.reviewed_by = actor_user_id
        request.reviewed_at = _utcnow()
        return request

    async def approve_change_async(self, **kwargs: Any) -> ConfigChangeRequest:
        await self._ensure_loaded()
        change = self.approve_change(**kwargs)
        await self.persist_all()
        return change

    def list_change_requests(
        self,
        *,
        actor_roles: Iterable[str],
        status: ChangeApprovalStatus | None = None,
    ) -> list[ConfigChangeRequest]:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view change requests")

        result = list(self._change_requests.values())
        if status:
            result = [r for r in result if r.status == status]
        result.sort(key=lambda r: r.requested_at, reverse=True)
        return result

    async def list_change_requests_async(self, **kwargs: Any) -> list[ConfigChangeRequest]:
        await self._ensure_loaded()
        return self.list_change_requests(**kwargs)

    # ---- Environment Sync ----

    def export_config(
        self,
        *,
        environment: str,
        config_data: dict[str, Any],
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> EnvironmentConfig:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to export config")

        export = EnvironmentConfig(
            id=uuid4(),
            environment=environment,
            config_data=config_data,
            exported_at=_utcnow(),
            exported_by=actor_user_id,
        )
        self._exports[export.id] = export
        return export

    async def export_config_async(self, **kwargs: Any) -> EnvironmentConfig:
        await self._ensure_loaded()
        export = self.export_config(**kwargs)
        await self.persist_all()
        return export

    def import_config(
        self,
        export_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> dict[str, Any]:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to import config")
        if export_id not in self._exports:
            raise KeyError("Export not found")

        return self._exports[export_id].config_data

    async def import_config_async(self, **kwargs: Any) -> dict[str, Any]:
        await self._ensure_loaded()
        return self.import_config(**kwargs)

    # ---- Master Data Seed Scripts ----

    def create_seed_job(
        self,
        *,
        entity_type: str,
        record_count: int,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> SeedJob:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create seed jobs")

        job = SeedJob(
            id=uuid4(),
            entity_type=entity_type,
            record_count=record_count,
            status=SeedStatus.PENDING,
            error_message=None,
            started_at=None,
            completed_at=None,
            created_by=actor_user_id,
            created_at=_utcnow(),
        )
        self._seed_jobs[job.id] = job
        return job

    async def create_seed_job_async(self, **kwargs: Any) -> SeedJob:
        await self._ensure_loaded()
        seed = self.create_seed_job(**kwargs)
        await self.persist_all()
        return seed

    def run_seed_job(
        self,
        job_id: UUID,
        *,
        actor_roles: Iterable[str],
        simulate_failure: bool = False,
    ) -> SeedJob:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to run seed jobs")
        if job_id not in self._seed_jobs:
            raise KeyError("Seed job not found")

        job = self._seed_jobs[job_id]
        job.status = SeedStatus.RUNNING
        job.started_at = _utcnow()

        if simulate_failure:
            job.status = SeedStatus.FAILED
            job.error_message = "Simulated failure"
        else:
            job.status = SeedStatus.COMPLETED
            job.completed_at = _utcnow()

        return job

    async def run_seed_job_async(self, **kwargs: Any) -> SeedJob:
        await self._ensure_loaded()
        seed = self.run_seed_job(**kwargs)
        await self.persist_all()
        return seed

    def list_seed_jobs(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[SeedJob]:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view seed jobs")

        result = list(self._seed_jobs.values())
        result.sort(key=lambda j: j.created_at, reverse=True)
        return result

    async def list_seed_jobs_async(self, **kwargs: Any) -> list[SeedJob]:
        await self._ensure_loaded()
        return self.list_seed_jobs(**kwargs)

    # ---- Go-Live Checklist ----

    def create_checklist(
        self,
        *,
        name: str,
        target_date: datetime,
        departments: list[str],
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> GoLiveChecklist:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create checklists")

        checklist_id = uuid4()
        items = [
            ChecklistItem(
                id=uuid4(),
                checklist_id=checklist_id,
                department=dept,
                description=f"{dept} sign-off",
                status=ChecklistItemStatus.NOT_STARTED,
                signed_off_by=None,
                signed_off_at=None,
            )
            for dept in departments
        ]

        checklist = GoLiveChecklist(
            id=checklist_id,
            name=name.strip(),
            target_date=target_date,
            items=items,
            created_by=actor_user_id,
            created_at=_utcnow(),
        )
        self._checklists[checklist.id] = checklist
        return checklist

    async def create_checklist_async(self, **kwargs: Any) -> GoLiveChecklist:
        await self._ensure_loaded()
        checklist = self.create_checklist(**kwargs)
        await self.persist_all()
        return checklist

    def sign_off_item(
        self,
        checklist_id: UUID,
        item_id: UUID,
        *,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> ChecklistItem:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to sign off checklist items")
        if checklist_id not in self._checklists:
            raise KeyError("Checklist not found")

        checklist = self._checklists[checklist_id]
        for item in checklist.items:
            if item.id == item_id:
                item.status = ChecklistItemStatus.SIGNED_OFF
                item.signed_off_by = actor_user_id
                item.signed_off_at = _utcnow()
                return item

        raise KeyError("Checklist item not found")

    async def sign_off_item_async(self, **kwargs: Any) -> ChecklistItem:
        await self._ensure_loaded()
        item = self.sign_off_item(**kwargs)
        await self.persist_all()
        return item

    def is_checklist_complete(self, checklist_id: UUID) -> bool:
        if checklist_id not in self._checklists:
            raise KeyError("Checklist not found")

        checklist = self._checklists[checklist_id]
        return all(item.status == ChecklistItemStatus.SIGNED_OFF for item in checklist.items)

    async def is_checklist_complete_async(self, checklist_id: UUID) -> bool:
        await self._ensure_loaded()
        return self.is_checklist_complete(checklist_id)

    def list_checklists(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[GoLiveChecklist]:
        if not self.can_admin_cutover(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view checklists")

        result = list(self._checklists.values())
        result.sort(key=lambda c: c.target_date)
        return result

    async def list_checklists_async(self, **kwargs: Any) -> list[GoLiveChecklist]:
        await self._ensure_loaded()
        return self.list_checklists(**kwargs)

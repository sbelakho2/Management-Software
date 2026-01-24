"""
Main Today Screen service composing all managers.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.time import utcnow_naive
from sensei.models.project_management import (
    Project,
    ProjectMilestone,
    UserStory,
    UserStoryStatus,
)
from sensei.core.redis import redis_client
from sensei.services.ops.today_screen_v2.base import BaseRedisStore, InMemoryRedis, UUIDEncoder
from sensei.services.ops.today_screen_v2.priorities import PriorityManager
from sensei.services.ops.today_screen_v2.risks import RiskManager
from sensei.services.ops.today_screen_v2.commitments import CommitmentManager
from sensei.services.ops.today_screen_v2.abnormalities import AbnormalityManager
from sensei.services.ops.today_screen_v2.drills import MicroDrillManager
from sensei.services.ops.today_screen_models import RiskCategory, Commitment
from sensei.services.ops.today_screen_v2.shop_floor import ShopFloorManager
from sensei.services.ops.today_screen_models import (
    AbnormalityType,
    CommitmentType,
    LSWChecklistSummary,
    LSWChecklistStatus,
    MicroDrill,
    QuickMetric,
    TodayScreenData,
)

logger = logging.getLogger(__name__)


class AsyncTodayScreenService:
    """
    Async service for Today Screen with composable managers.
    
    This service composes all manager components to provide 
    a unified API for the Today Screen feature.
    """
    
    def __init__(self, redis: Any = None) -> None:
        self._redis = redis if redis is not None else InMemoryRedis()
        self.logger = logging.getLogger(__name__)
        
        # Compose managers
        self._priority_manager = PriorityManager(self._redis)
        self._risk_manager = RiskManager(self._redis)
        self._commitment_manager = CommitmentManager(self._redis)
        self._abnormality_manager = AbnormalityManager(self._redis)
        self._drill_manager = MicroDrillManager(self._redis)
        self._shop_floor_manager = ShopFloorManager(self._redis)

    # ========== Priorities (delegated) ==========
    
    async def set_top_priorities(self, user_id: UUID, priority_ids: List[UUID]) -> List:
        return await self._priority_manager.set_top_priorities(user_id, priority_ids)
    
    async def add_priority(self, user_id: UUID, **kwargs):
        return await self._priority_manager.add_priority(user_id, **kwargs)
    
    async def remove_priority(self, user_id: UUID, priority_id: UUID) -> bool:
        return await self._priority_manager.remove_priority(user_id, priority_id)
    
    async def get_user_priorities(self, user_id: UUID):
        return await self._priority_manager.get_user_priorities(user_id)

    # ========== Risks (delegated) ==========
    
    async def add_risk(self, user_id: UUID, **kwargs):
        return await self._risk_manager.add_risk(user_id, **kwargs)
    
    async def get_risks_by_category(self, user_id: UUID, category: RiskCategory | None = None, top_n: int | None = None):
        return await self._risk_manager.get_risks_by_category(user_id, category, top_n)
    
    async def get_top_risks(self, user_id: UUID, n: int = 3):
        return await self._risk_manager.get_top_risks(user_id, n)
    
    async def get_risk_count(self, user_id: UUID) -> int:
        return await self._risk_manager.get_risk_count(user_id)
    
    async def get_critical_risk_count(self, user_id: UUID) -> int:
        return await self._risk_manager.get_critical_risk_count(user_id)

    # ========== Commitments (delegated) ==========
    
    async def add_commitment(self, user_id: UUID, **kwargs):
        return await self._commitment_manager.add_commitment(user_id, **kwargs)
    
    async def complete_commitment(self, user_id: UUID, commitment_id: UUID) -> Commitment | None:
        return await self._commitment_manager.complete_commitment(user_id, commitment_id)
    
    async def get_commitments(self, user_id: UUID, **kwargs):
        return await self._commitment_manager.get_commitments(user_id, **kwargs)
    
    async def clear_auto_generated_commitments(self, user_id: UUID) -> None:
        return await self._commitment_manager.clear_auto_generated(user_id)

    # ========== Abnormalities (delegated) ==========
    
    async def add_abnormality(self, user_id: UUID, **kwargs):
        return await self._abnormality_manager.add_abnormality(user_id, **kwargs)
    
    async def resolve_abnormality(self, user_id: UUID, abnormality_id: UUID) -> bool:
        return await self._abnormality_manager.resolve_abnormality(user_id, abnormality_id)
    
    async def get_abnormalities(self, user_id: UUID, **kwargs):
        return await self._abnormality_manager.get_abnormalities(user_id, **kwargs)
    
    async def get_abnormality_counts(self, user_id: UUID):
        return await self._abnormality_manager.get_abnormality_counts(user_id)
    
    async def clear_auto_generated_abnormalities(self, user_id: UUID) -> None:
        return await self._abnormality_manager.clear_auto_generated(user_id)

    # ========== Micro-drills (delegated) ==========
    
    async def add_micro_drill(self, user_id: UUID, **kwargs):
        return await self._drill_manager.add_micro_drill(user_id, **kwargs)
    
    async def get_todays_drills(self, user_id: UUID, count: int = 3):
        return await self._drill_manager.get_todays_drills(user_id, count)
    
    async def complete_drill(self, user_id: UUID, drill_id: UUID, correct: bool):
        return await self._drill_manager.complete_drill(user_id, drill_id, correct)
    
    async def get_drill_progress(self, user_id: UUID):
        return await self._drill_manager.get_drill_progress(user_id)

    # ========== Shop Floor (delegated) ==========
    
    async def add_work_order_at_risk(self, **kwargs):
        return await self._shop_floor_manager.add_work_order_at_risk(**kwargs)
    
    async def get_work_orders_at_risk(self, **kwargs):
        return await self._shop_floor_manager.get_work_orders_at_risk(**kwargs)
    
    async def resolve_work_order_risk(self, work_order_id: UUID) -> bool:
        return await self._shop_floor_manager.resolve_work_order_risk(work_order_id)
    
    async def add_critical_andon(self, **kwargs):
        return await self._shop_floor_manager.add_critical_andon(**kwargs)
    
    async def acknowledge_andon(self, **kwargs):
        return await self._shop_floor_manager.acknowledge_andon(**kwargs)
    
    async def resolve_andon(self, andon_id: UUID) -> bool:
        return await self._shop_floor_manager.resolve_andon(andon_id)
    
    async def get_critical_andons(self, **kwargs):
        return await self._shop_floor_manager.get_critical_andons(**kwargs)
    
    async def add_station_efficiency(self, **kwargs):
        return await self._shop_floor_manager.add_station_efficiency(**kwargs)
    
    async def get_low_efficiency_stations(self, **kwargs):
        return await self._shop_floor_manager.get_low_efficiency_stations(**kwargs)
    
    async def add_cell_oee(self, **kwargs):
        return await self._shop_floor_manager.add_cell_oee(**kwargs)
    
    async def get_low_oee_cells(self, **kwargs):
        return await self._shop_floor_manager.get_low_oee_cells(**kwargs)
    
    async def get_overall_oee(self) -> float:
        return await self._shop_floor_manager.get_overall_oee()
    
    async def add_kanban_alert(self, **kwargs):
        return await self._shop_floor_manager.add_kanban_alert(**kwargs)
    
    async def update_kanban_status(self, kanban_id: UUID, status: str):
        return await self._shop_floor_manager.update_kanban_status(kanban_id, status)
    
    async def resolve_kanban_alert(self, kanban_id: UUID) -> bool:
        return await self._shop_floor_manager.resolve_kanban_alert(kanban_id)
    
    async def get_overdue_kanbans(self, **kwargs):
        return await self._shop_floor_manager.get_overdue_kanbans(**kwargs)
    
    async def add_expiring_certification(self, **kwargs):
        return await self._shop_floor_manager.add_expiring_certification(**kwargs)
    
    async def get_expiring_certifications(self, **kwargs):
        return await self._shop_floor_manager.get_expiring_certifications(**kwargs)
    
    async def renew_certification(self, certification_id: UUID) -> bool:
        return await self._shop_floor_manager.renew_certification(certification_id)
    
    async def add_wip_violation(self, **kwargs):
        return await self._shop_floor_manager.add_wip_violation(**kwargs)
    
    async def get_wip_violations(self, **kwargs):
        return await self._shop_floor_manager.get_wip_violations(**kwargs)
    
    async def resolve_wip_violation(self, violation_id: UUID) -> bool:
        return await self._shop_floor_manager.resolve_wip_violation(violation_id)
    
    async def add_capa_verification(self, **kwargs):
        return await self._shop_floor_manager.add_capa_verification(**kwargs)
    
    async def get_capa_verifications_due(self, **kwargs):
        return await self._shop_floor_manager.get_capa_verifications_due(**kwargs)
    
    async def resolve_capa_verification(self, capa_id: UUID) -> bool:
        return await self._shop_floor_manager.resolve_capa_verification(capa_id)
    
    async def add_scheduled_training(self, **kwargs):
        return await self._shop_floor_manager.add_scheduled_training(**kwargs)
    
    async def get_scheduled_trainings(self, **kwargs):
        return await self._shop_floor_manager.get_scheduled_trainings(**kwargs)
    
    async def enroll_in_training(self, training_id: UUID):
        return await self._shop_floor_manager.enroll_in_training(training_id)
    
    async def get_shop_floor_summary(self, **kwargs):
        return await self._shop_floor_manager.get_shop_floor_summary(**kwargs)

    # ========== LSW & Quick Metrics (static) ==========
    
    def get_lsw_summary(self, user_id: UUID) -> LSWChecklistSummary:
        """Get LSW checklist summary for user."""
        # In production, this would query the LSW service
        return LSWChecklistSummary(
            daily_status=LSWChecklistStatus.IN_PROGRESS,
            daily_total=5,
            daily_completed=3,
            weekly_status=LSWChecklistStatus.NOT_STARTED,
            weekly_total=3,
            weekly_completed=0,
            monthly_status=LSWChecklistStatus.COMPLETED,
            monthly_total=2,
            monthly_completed=2,
            overdue_count=1,
            next_due_item="Review daily metrics",
        )
    
    def get_quick_metrics(self, user_id: UUID) -> List[QuickMetric]:
        """Get quick metrics for the Today screen."""
        # In production, this would call the KPI service
        return [
            QuickMetric(
                id="rfq-pipeline",
                name="Open RFQs",
                value=12,
                unit=None,
                trend="up",
                trend_value=2,
                status="good",
                target=15,
                link="/rfqs?status=open",
            ),
            QuickMetric(
                id="quotes-pending",
                name="Pending Quotes",
                value=8,
                unit=None,
                trend="down",
                trend_value=-3,
                status="neutral",
                target=10,
                link="/quotes?status=pending",
            ),
        ]

    # ========== Internal Store Access (for compatibility) ==========
    
    async def _get_store(self, user_id: UUID, store_name: str | None = None) -> Dict[str, Any]:
        """Get user-specific store data. For backward compatibility."""
        if store_name == "risks":
            return await self._risk_manager._get_store(user_id)
        elif store_name == "commitments":
            return await self._commitment_manager._get_store(user_id)
        elif store_name == "abnormalities":
            return await self._abnormality_manager._get_store(user_id)
        elif store_name == "priorities":
            return await self._priority_manager._get_store(user_id)
        elif store_name == "micro_drills":
            return await self._drill_manager._get_store(user_id)
        return {}
    
    async def _save_store(self, user_id: UUID, store_name: str, data: Dict[str, Any]) -> None:
        """Save user-specific store data. For backward compatibility."""
        if store_name == "risks":
            await self._risk_manager._save_store(user_id, data)
        elif store_name == "commitments":
            await self._commitment_manager._save_store(user_id, data)
        elif store_name == "abnormalities":
            await self._abnormality_manager._save_store(user_id, data)
        elif store_name == "priorities":
            await self._priority_manager._save_store(user_id, data)
        elif store_name == "micro_drills":
            await self._drill_manager._save_store(user_id, data)

    # ========== Full Today Screen Data ==========
    
    async def get_today_screen(
        self,
        user_id: UUID,
        user_name: str,
        db: AsyncSession | None = None,
    ) -> TodayScreenData:
        """Get complete Today screen data for a user."""
        today = date.today()
        
        # Aggregate real-time data if DB is provided and cache is expired
        if db:
            cache_key = f"today:{user_id}:last_aggregated"
            last_agg = await redis_client.get(cache_key)
            now = utcnow_naive()
            
            should_aggregate = True
            if last_agg:
                try:
                    last_agg_dt = datetime.fromisoformat(last_agg)
                    if (now - last_agg_dt).total_seconds() < 300:  # 5 minutes
                        should_aggregate = False
                except ValueError:
                    self.logger.warning("Invalid cached aggregation timestamp for %s", cache_key)
            
            if should_aggregate:
                await self._aggregate_project_data(db, user_id)
                await redis_client.set(cache_key, now.isoformat(), ex=3600)
        
        # Get greeting based on time of day
        hour = datetime.now().hour
        if hour < 12:
            greeting = f"Good morning, {user_name.split()[0]}"
        elif hour < 17:
            greeting = f"Good afternoon, {user_name.split()[0]}"
        else:
            greeting = f"Good evening, {user_name.split()[0]}"
        
        # Get priorities
        all_priorities = await self.get_user_priorities(user_id)
        top_priorities = [p for p in all_priorities if p.is_user_selected]
        unselected_priorities = [p for p in all_priorities if not p.is_user_selected]
        
        # Get risks
        risks_by_category = await self.get_risks_by_category(user_id, top_n=3)
        total_risks = await self.get_risk_count(user_id)
        critical_risks = await self.get_critical_risk_count(user_id)
        
        # Get commitments
        todays_commitments = await self.get_commitments(user_id, target_date=today)
        tomorrows_commitments = await self.get_commitments(user_id, target_date=today + timedelta(days=1))
        overdue_commitments = await self.get_commitments(user_id, include_overdue=True, include_completed=False)
        overdue_commitments = [c for c in overdue_commitments if c.is_overdue]
        
        # Get abnormalities
        abnormalities = await self.get_abnormalities(user_id)
        abnormality_counts = await self.get_abnormality_counts(user_id)
        
        # Get micro-drills
        todays_drills = await self.get_todays_drills(user_id)
        drill_progress = await self.get_drill_progress(user_id)
        
        # Get LSW summary
        lsw_summary = self.get_lsw_summary(user_id)
        
        # Get quick metrics
        quick_metrics = self.get_quick_metrics(user_id)
        
        # Get shop floor summary (Phase 3)
        shop_floor = await self.get_shop_floor_summary(user_id=user_id)
        
        return TodayScreenData(
            user_id=user_id,
            user_name=user_name,
            current_date=today,
            greeting=greeting,
            top_priorities=top_priorities,
            unselected_priorities=unselected_priorities,
            top_risks=risks_by_category,
            total_risk_count=total_risks,
            critical_risk_count=critical_risks,
            todays_commitments=todays_commitments,
            tomorrows_commitments=tomorrows_commitments,
            overdue_commitments=overdue_commitments,
            abnormalities=abnormalities,
            abnormality_counts=abnormality_counts,
            todays_micro_drills=todays_drills,
            drills_completed_today=drill_progress["drills_completed_today"],
            drill_streak=drill_progress["streak"],
            lsw_summary=lsw_summary,
            quick_metrics=quick_metrics,
            shop_floor_summary=shop_floor,
            cache_valid_until=utcnow_naive() + timedelta(minutes=5),
        )
    
    async def _clear_auto_generated_items(self, user_id: UUID) -> None:
        """Clear auto-generated commitments and abnormalities for a user."""
        await self.clear_auto_generated_commitments(user_id)
        await self.clear_auto_generated_abnormalities(user_id)

    async def _aggregate_project_data(self, db: AsyncSession, user_id: UUID) -> None:
        """Aggregate project data into commitments and abnormalities."""
        # Clear existing auto-generated items first to avoid duplication
        await self._clear_auto_generated_items(user_id)
        
        today = date.today()
        
        # 1. Fetch Overdue/Upcoming Milestones
        milestone_stmt = (
            select(ProjectMilestone, Project.name)
            .join(Project, ProjectMilestone.project_id == Project.id)
            .where(
                ProjectMilestone.owner_id == user_id,
                ProjectMilestone.is_closed.is_(False),
                ProjectMilestone.deleted_at.is_(None)
            )
        )
        result = await db.execute(milestone_stmt)
        milestones = result.all()
        
        # Batch updates to Redis
        commitments_data = await self._get_store(user_id, "commitments")
        abnormalities_data = await self._get_store(user_id, "abnormalities")

        for ms, project_name in milestones:
            # Overdue Milestone as Abnormality
            if ms.due_date < today:
                ab_id = f"ab_ms_{ms.id}"
                abnormalities_data[ab_id] = {
                    "id": ab_id,
                    "title": f"Overdue Milestone: {ms.name}",
                    "type": AbnormalityType.OVERDUE_PROJECT_MILESTONE.value,
                    "severity": 8,
                    "description": f"Project: {project_name}. Due on {ms.due_date}",
                    "detected_at": utcnow_naive().isoformat(),
                    "entity_type": "project_milestone",
                    "entity_id": str(ms.id),
                    "is_auto_generated": True,
                    "is_resolved": False,
                }
            
            # Milestone as Commitment
            c_id = f"c_ms_{ms.id}"
            commitments_data[c_id] = {
                "id": c_id,
                "title": f"Milestone: {ms.name}",
                "type": CommitmentType.PROJECT_MILESTONE_DUE.value,
                "due_date": ms.due_date.isoformat(),
                "description": f"Project: {project_name}",
                "entity_type": "project_milestone",
                "entity_id": str(ms.id),
                "is_auto_generated": True,
                "is_completed": False,
            }

        # 2. Fetch Assigned User Stories with due dates
        story_stmt = (
            select(UserStory, Project.name)
            .join(Project, UserStory.project_id == Project.id)
            .where(
                UserStory.owner_id == user_id,
                UserStory.status != UserStoryStatus.DONE.value,
                UserStory.deleted_at.is_(None),
                UserStory.due_date.isnot(None)
            )
        )
        result = await db.execute(story_stmt)
        stories = result.all()
        
        for story, project_name in stories:
            # Overdue Story as Abnormality
            if story.due_date < today:
                ab_id = f"ab_us_{story.id}"
                abnormalities_data[ab_id] = {
                    "id": ab_id,
                    "title": f"Late User Story: US-{story.ref}",
                    "type": AbnormalityType.LATE_USER_STORY.value,
                    "severity": 6,
                    "description": f"{story.subject} (Project: {project_name})",
                    "detected_at": utcnow_naive().isoformat(),
                    "entity_type": "user_story",
                    "entity_id": str(story.id),
                    "is_auto_generated": True,
                    "is_resolved": False,
                }
            
            # Story as Commitment
            c_id = f"c_us_{story.id}"
            commitments_data[c_id] = {
                "id": c_id,
                "title": f"US-{story.ref}: {story.subject}",
                "type": CommitmentType.USER_STORY_DUE.value,
                "due_date": story.due_date.isoformat(),
                "description": f"Project: {project_name}",
                "entity_type": "user_story",
                "entity_id": str(story.id),
                "is_auto_generated": True,
                "is_completed": False,
            }
        
        await self._save_store(user_id, "commitments", commitments_data)
        await self._save_store(user_id, "abnormalities", abnormalities_data)


class TodayScreenService:
    """Sync-friendly wrapper around AsyncTodayScreenService."""

    def __init__(self, redis_client: Any = None) -> None:
        # Use the provided redis_client or fall back to InMemoryRedis for testing
        self._redis = redis_client if redis_client is not None else InMemoryRedis()
        self._async = AsyncTodayScreenService(redis=self._redis)
        self._default_user_id = uuid4()
        self.logger = logging.getLogger(__name__)
        # Only set up in-memory hashes if using InMemoryRedis
        if isinstance(self._redis, InMemoryRedis):
            self._risks = self._redis._hashes.setdefault(f"today:{self._default_user_id}:risks", {})
            self._commitments = self._redis._hashes.setdefault(f"today:{self._default_user_id}:commitments", {})
            self._abnormalities = self._redis._hashes.setdefault(f"today:{self._default_user_id}:abnormalities", {})

    def _run(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        return coro

    async def _get_todays_drills_async(self, user_id: UUID, count: int = 3) -> List[MicroDrill]:
        return await self._async.get_todays_drills(user_id, count=count)

    def get_todays_drills(self, user_id: UUID, count: int = 3) -> List[MicroDrill]:
        return self._run(self._get_todays_drills_async(user_id, count=count))

    async def _get_today_screen_async(
        self,
        user_id: UUID,
        user_name: str,
        db: AsyncSession | None = None,
    ) -> TodayScreenData:
        screen = await self._async.get_today_screen(user_id, user_name, db=db)
        if screen.total_risk_count == 0 and user_id != self._default_user_id:
            fallback_risks_data = await self._async._get_store(self._default_user_id, "risks")
            if fallback_risks_data:
                screen.top_risks = await self._async.get_risks_by_category(self._default_user_id, top_n=3)
                screen.total_risk_count = len(fallback_risks_data)
                screen.critical_risk_count = sum(
                    1 for r in fallback_risks_data.values() if r.get("severity", 0) >= 8
                )
        has_data = any(
            [
                screen.top_priorities,
                screen.unselected_priorities,
                screen.top_risks,
                screen.todays_commitments,
                screen.abnormalities,
                screen.todays_micro_drills,
                screen.drills_completed_today,
            ]
        )
        if not has_data:
            fallback = await self._async.get_today_screen(self._default_user_id, user_name, db=db)
            fallback.user_id = user_id
            fallback.user_name = user_name
            return fallback
        return screen

    def get_today_screen(
        self,
        user_id: UUID,
        user_name: str,
        db: AsyncSession | None = None,
    ) -> TodayScreenData:
        return self._run(self._get_today_screen_async(user_id, user_name, db=db))

    async def _complete_capa_verification_async(self, capa_id: UUID) -> bool:
        return await self._async.resolve_capa_verification(capa_id)

    def complete_capa_verification(self, capa_id: UUID) -> bool:
        return self._run(self._complete_capa_verification_async(capa_id))

    def __getattr__(self, name: str):
        attr = getattr(self._async, name)
        if asyncio.iscoroutinefunction(attr):
            async def async_wrapper(*args, **kwargs):
                try:
                    import inspect
                    id_only_methods = {
                        "complete_commitment",
                        "resolve_abnormality",
                    }
                    read_methods = {
                        "get_risks_by_category",
                        "get_top_risks",
                        "get_commitments",
                        "get_abnormalities",
                        "get_abnormality_counts",
                        "get_todays_drills",
                        "get_drill_progress",
                        "get_lsw_summary",
                        "get_quick_metrics",
                        "get_today_screen",
                    }
                    optional_user_id_methods = {
                        "get_expiring_certifications",
                    }
                    sig = inspect.signature(attr)
                    params = list(sig.parameters.values())
                    user_param_index = None
                    if params and params[0].name == "user_id":
                        user_param_index = 0
                    elif len(params) >= 2 and params[1].name == "user_id":
                        user_param_index = 1
                    user_id_value = None
                    if user_param_index is not None:
                        if name in optional_user_id_methods and "user_id" not in kwargs and len(args) <= user_param_index:
                            user_id_value = None
                        elif "user_id" not in kwargs and len(args) <= user_param_index:
                            inferred_user_id = kwargs.get("owner_id", self._default_user_id)
                            args = (inferred_user_id, *args)
                            user_id_value = inferred_user_id
                        elif "user_id" in kwargs:
                            user_id_value = kwargs.get("user_id")
                        elif len(args) > user_param_index:
                            user_id_value = args[user_param_index]
                    if name in id_only_methods and "user_id" not in kwargs and len(args) == 1:
                        args = (self._default_user_id, *args)
                except Exception:
                    self.logger.exception("Failed to infer user_id for TodayScreenService method %s", name)
                result = await attr(*args, **kwargs)
                try:
                    if name in read_methods and user_id_value and user_id_value != self._default_user_id:
                        empty = result is None
                        if not empty and hasattr(result, "__len__"):
                            empty = len(result) == 0
                        if empty:
                            fallback_args = (self._default_user_id, *args[1:]) if args else (self._default_user_id,)
                            fallback_kwargs = dict(kwargs)
                            fallback_kwargs.pop("user_id", None)
                            result = await attr(*fallback_args, **fallback_kwargs)
                except Exception:
                    self.logger.exception("TodayScreenService fallback failed for method %s", name)
                return result

            def wrapper(*args, **kwargs):
                return self._run(async_wrapper(*args, **kwargs))

            return wrapper
        return attr


# Module-level service instance
_service: TodayScreenService | None = None


def get_today_screen_service(redis_client_override: Any = None) -> TodayScreenService:
    """Get or create the Today screen service instance."""
    global _service
    if _service is None:
        _service = TodayScreenService(redis_client=redis_client_override)
    return _service


def reset_today_screen_service() -> None:
    """Reset the service instance (for testing)."""
    global _service
    _service = None

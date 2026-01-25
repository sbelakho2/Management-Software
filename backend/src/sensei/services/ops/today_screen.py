"""
Today Screen Data Aggregation Service.

Aggregates data for the Manager GPS "Today" screen, including:
- Top 3 Priorities (forced selection)
- Top Risks (Delivery/Quality/Cash/Reputation)
- Commitments (due quotes, calls, follow-ups)
- Abnormalities (late quotes, stalled RFQs, missing CTQs)
- Micro-Drill recall questions
- LSW Checklist status
- Quick metrics and KPIs
"""

import json
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Any, List, Dict, Optional, Coroutine, TypeVar

T = TypeVar("T")
from uuid import UUID, uuid4

from sensei.core.redis import redis_client
from sensei.core.config import settings


from sensei.models.project_management import UserStory, ProjectMilestone, Project, ProjectStatus, UserStoryStatus
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.core.time import now_utc, utcnow_naive
from sensei.services.ops.today_screen_models import (
    RiskCategory, AbnormalityType, CommitmentType, PriorityLevel,
    LSWChecklistStatus, ShopFloorAreaType, ShopFloorAlertSeverity,
    Priority, Risk, Commitment, Abnormality, MicroDrill,
    LSWChecklistSummary, QuickMetric, WorkOrderAtRisk, CriticalAndon,
    StationEfficiency, CellOEE, KanbanAlert, ExpiringCertification,
    WIPViolation, CAPAVerification, ScheduledTraining, ShopFloorSummary,
    TodayScreenData, HandoverNoteSummary, GlobalPulseSummary
)
from sensei.services.production.handover_service import get_handover_service
from sensei.services.ops.pulse_service import get_pulse_service

def _utcnow() -> datetime:
    return utcnow_naive()


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUIDs."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class InMemoryRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, Any]] = {}

    async def hgetall(self, key: str) -> dict[str, Any]:
        return dict(self._hashes.get(key, {}))

    async def hset(self, key: str, field: str | None = None, value: Any | None = None, mapping: dict[str, Any] | None = None) -> None:
        bucket = self._hashes.setdefault(key, {})
        if mapping:
            bucket.update(mapping)
        elif field is not None and value is not None:
            bucket[field] = value

    async def delete(self, key: str) -> None:
        self._hashes.pop(key, None)

    async def hdel(self, key: str, field: str) -> int:
        bucket = self._hashes.get(key)
        if not bucket or field not in bucket:
            return 0
        del bucket[field]
        return 1

    async def expire(self, key: str, _ttl: int) -> None:
        return None

    def pipeline(self, transaction: bool = True) -> "InMemoryRedis":
        return self

    async def execute(self) -> None:
        return None

    async def __aenter__(self) -> "InMemoryRedis":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


# Note: All enums and data classes (Priority, Risk, Commitment, etc.) are imported from 
# sensei.services.ops.today_screen_models to avoid duplication.
# Do not define local versions here.


class AsyncTodayScreenService:
    """Service for aggregating Today screen data."""
    
    def __init__(self, *, redis: InMemoryRedis | None = None) -> None:
        """Initialize the Today screen service."""
        self.logger = logging.getLogger(__name__)
        self._redis = redis or redis_client
        # Note: Internal in-memory stores have been migrated to Redis for persistence and concurrency
        
        self._drill_progress: dict[UUID, dict[str, Any]] = {}
        
        # Sample data should be registered via an async bootstrap process if needed
    
    async def _get_store(self, user_id: UUID, store_name: str) -> Dict[str, Any]:
        """Get a user-specific store from Redis (using Hashes for atomicity)."""
        key = f"today:{user_id}:{store_name}"
        data = await self._redis.hgetall(key) if self._redis else {}  # type: ignore[misc]
        if not data:
            return {}
        if isinstance(self._redis, InMemoryRedis):
            return dict(data)
        return {k: json.loads(v) for k, v in data.items()}

    async def _save_store(self, user_id: UUID, store_name: str, data: Dict[str, Any]) -> None:
        """Save a user-specific store to Redis (using Hashes)."""
        key = f"today:{user_id}:{store_name}"
        if not data:
            if self._redis:
                await self._redis.delete(key)
            return
        
        serialized = data if isinstance(self._redis, InMemoryRedis) else {k: json.dumps(v, cls=UUIDEncoder) for k, v in data.items()}
        # We delete and recreate to ensure it exactly matches the provided data
        # In a high-concurrency environment, Lua would be better.
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.delete(key)  # type: ignore[misc]
            await pipe.hset(key, mapping=serialized)  # type: ignore[misc]
            await pipe.expire(key, 86400)  # type: ignore[misc]
            await pipe.execute()  # type: ignore[misc]

    async def _get_global_store(self, store_name: str) -> Dict[str, Any]:
        """Get a global store from Redis."""
        key = f"today:global:{store_name}"
        data = await self._redis.hgetall(key) if self._redis else {}  # type: ignore[misc]
        if not data:
            return {}
        if isinstance(self._redis, InMemoryRedis):
            return dict(data)
        return {k: json.loads(v) for k, v in data.items()}

    async def _save_global_item(self, store_name: str, item_id: str, data: Any) -> None:
        """Save an item to a global store in Redis."""
        key = f"today:global:{store_name}"
        if self._redis:
            val = data if isinstance(self._redis, InMemoryRedis) else json.dumps(data, cls=UUIDEncoder)
            await self._redis.hset(key, item_id, val)  # type: ignore[misc]
            await self._redis.expire(key, 86400)  # type: ignore[misc]

    # ========== Priority Management ==========
    
    async def set_top_priorities(
        self,
        user_id: UUID,
        priority_ids: List[UUID],
    ) -> List[Priority]:
        """Set the user's top 3 priorities (forced selection)."""
        if len(priority_ids) > 3:
            raise ValueError("Maximum 3 top priorities allowed")
        
        priorities_data = await self._get_store(user_id, "priorities")
        priorities = [Priority(**p) if isinstance(p, dict) else p for p in priorities_data.values()]
        
        # Reset all user-selected flags
        for p in priorities:
            p.is_user_selected = False
            p.rank = 0
        for p_dict in priorities_data.values():
            if isinstance(p_dict, dict):
                p_dict["is_user_selected"] = False
                p_dict["rank"] = 0
        
        # Set selected priorities
        for rank, pid in enumerate(priority_ids, 1):
            pid_str = str(pid)
            if pid_str in priorities_data:
                p_dict = priorities_data[pid_str]
                p_dict['is_user_selected'] = True
                p_dict['rank'] = rank
        
        await self._save_store(user_id, "priorities", priorities_data)
        return [Priority(**p) for p in priorities_data.values() if p.get('is_user_selected')]
    
    async def add_priority(
        self,
        user_id: UUID,
        title: str,
        entity_type: str,
        entity_id: UUID,
        priority_level: PriorityLevel = PriorityLevel.MEDIUM,
        description: str | None = None,
        due_date: date | None = None,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
    ) -> Priority:
        """Add a priority item."""
        priority = Priority(
            id=uuid4(),
            title=title,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            priority_level=priority_level,
            due_date=due_date,
            owner_id=owner_id,
            owner_name=owner_name,
        )
        
        priorities_data = await self._get_store(user_id, "priorities")
        
        # Datetime needs special handling for JSON
        priority_dict = asdict(priority)
        priority_dict['created_at'] = priority.created_at.isoformat()
        if priority.due_date:
            priority_dict['due_date'] = priority.due_date.isoformat()
        
        priorities_data[str(priority.id)] = priority_dict
        await self._save_store(user_id, "priorities", priorities_data)
        
        return priority
    
    async def remove_priority(self, user_id: UUID, priority_id: UUID) -> bool:
        """Remove a priority item."""
        priorities_data = await self._get_store(user_id, "priorities")
        pid_str = str(priority_id)
        
        if pid_str in priorities_data:
            del priorities_data[pid_str]
            await self._save_store(user_id, "priorities", priorities_data)
            return True
        return False
    
    async def get_user_priorities(
        self,
        user_id: UUID,
        include_selected: bool = True,
        include_unselected: bool = True,
    ) -> List[Priority]:
        """Get priorities for a user."""
        priorities_data = await self._get_store(user_id, "priorities")
        
        result = []
        for p_dict in priorities_data.values():
            # Handle date/datetime conversions from JSON
            if isinstance(p_dict['created_at'], str):
                p_dict['created_at'] = datetime.fromisoformat(p_dict['created_at'])
            if p_dict.get('due_date') and isinstance(p_dict['due_date'], str):
                p_dict['due_date'] = date.fromisoformat(p_dict['due_date'])
                
            p = Priority(**p_dict)
            if p.is_user_selected and include_selected:
                result.append(p)
            elif not p.is_user_selected and include_unselected:
                result.append(p)
        
        # Sort: selected first by rank, then unselected by priority level
        result.sort(key=lambda p: (
            0 if p.is_user_selected else 1,
            p.rank if p.is_user_selected else 999,
            0 if p.priority_level == PriorityLevel.HIGH else 1 if p.priority_level == PriorityLevel.MEDIUM else 2,
        ))
        return result
    
    # ========== Risk Management ==========
    
    async def add_risk(
        self,
        user_id: UUID,
        title: str,
        category: RiskCategory,
        severity: int,
        probability: int,
        description: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
        mitigation: str | None = None,
        due_date: date | None = None,
    ) -> Risk:
        """Add a risk item."""
        risk = Risk(
            id=uuid4(),
            title=title,
            description=description,
            category=category,
            severity=min(10, max(1, severity)),
            probability=min(10, max(1, probability)),
            entity_type=entity_type,
            entity_id=entity_id,
            owner_id=owner_id or user_id,
            owner_name=owner_name,
            mitigation=mitigation,
            due_date=due_date,
        )
        
        risks_data = await self._get_store(user_id, "risks")
        
        risk_dict = asdict(risk)
        risk_dict['created_at'] = risk.created_at.isoformat()
        if risk.due_date:
            risk_dict['due_date'] = risk.due_date.isoformat()
            
        risks_data[str(risk.id)] = risk_dict
        await self._save_store(user_id, "risks", risks_data)
        
        return risk
    
    async def get_risks_by_category(
        self,
        user_id: UUID,
        category: RiskCategory | None = None,
        top_n: int | None = None,
    ) -> dict[RiskCategory, list[Risk]]:
        """Get risks grouped by category."""
        risks_data = await self._get_store(user_id, "risks")
        risks = []
        for r_dict in risks_data.values():
            if 'due_date' in r_dict and r_dict['due_date'] and isinstance(r_dict['due_date'], str):
                r_dict['due_date'] = date.fromisoformat(r_dict['due_date'])
            if 'created_at' in r_dict and r_dict['created_at'] and isinstance(r_dict['created_at'], str):
                r_dict['created_at'] = datetime.fromisoformat(r_dict['created_at'])
            risks.append(Risk(**r_dict))

        result: dict[RiskCategory, list[Risk]] = {}
        
        for risk in risks:
            if category is not None and risk.category != category:
                continue
            
            if risk.category not in result:
                result[risk.category] = []
            result[risk.category].append(risk)
        
        # Sort each category by risk score descending
        for cat in result:
            result[cat].sort(key=lambda r: r.risk_score, reverse=True)
            if top_n is not None:
                result[cat] = result[cat][:top_n]
        
        return result
    
    async def get_top_risks(self, user_id: UUID, top_n: int = 5) -> list[Risk]:
        """Get top N risks across all categories."""
        risks_data = await self._get_store(user_id, "risks")
        risks = []
        for r_dict in risks_data.values():
            if 'due_date' in r_dict and r_dict['due_date'] and isinstance(r_dict['due_date'], str):
                r_dict['due_date'] = date.fromisoformat(r_dict['due_date'])
            if 'created_at' in r_dict and r_dict['created_at'] and isinstance(r_dict['created_at'], str):
                r_dict['created_at'] = datetime.fromisoformat(r_dict['created_at'])
            risks.append(Risk(**r_dict))

        risks.sort(key=lambda r: r.risk_score, reverse=True)
        return risks[:top_n]
    
    # ========== Commitment Management ==========
    
    async def add_commitment(
        self,
        user_id: UUID,
        title: str,
        commitment_type: CommitmentType,
        due_date: date,
        description: str | None = None,
        due_time: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
        customer_name: str | None = None,
        is_auto_generated: bool = False,
    ) -> Commitment:
        """Add a commitment."""
        commitment = Commitment(
            id=uuid4(),
            title=title,
            description=description,
            commitment_type=commitment_type,
            entity_type=entity_type,
            entity_id=entity_id,
            due_date=due_date,
            due_time=due_time,
            owner_id=owner_id or user_id,
            owner_name=owner_name,
            customer_name=customer_name,
            is_overdue=due_date < date.today(),
            is_auto_generated=is_auto_generated,
        )
        
        commitments_data = await self._get_store(user_id, "commitments")
        
        commitment_dict = asdict(commitment)
        commitment_dict['created_at'] = commitment.created_at.isoformat()
        if commitment.due_date:
            commitment_dict['due_date'] = commitment.due_date.isoformat()
            
        commitments_data[str(commitment.id)] = commitment_dict
        await self._save_store(user_id, "commitments", commitments_data)
        
        return commitment
    
    async def complete_commitment(self, user_id: UUID, commitment_id: UUID) -> Commitment | None:
        """Mark a commitment as completed."""
        commitments_data = await self._get_store(user_id, "commitments")
        cid_str = str(commitment_id)
        
        if cid_str in commitments_data:
            c_dict = commitments_data[cid_str]
            c_dict['is_completed'] = True
            await self._save_store(user_id, "commitments", commitments_data)
            
            if 'due_date' in c_dict and c_dict['due_date'] and isinstance(c_dict['due_date'], str):
                c_dict['due_date'] = date.fromisoformat(c_dict['due_date'])
            if 'created_at' in c_dict and c_dict['created_at'] and isinstance(c_dict['created_at'], str):
                c_dict['created_at'] = datetime.fromisoformat(c_dict['created_at'])
            return Commitment(**c_dict)
        return None
    
    async def get_commitments(
        self,
        user_id: UUID,
        target_date: date | None = None,
        include_overdue: bool = True,
        include_completed: bool = False,
    ) -> list[Commitment]:
        """Get commitments with filtering."""
        commitments_data = await self._get_store(user_id, "commitments")
        commitments = []
        for c_dict in commitments_data.values():
            if 'due_date' in c_dict and c_dict['due_date'] and isinstance(c_dict['due_date'], str):
                c_dict['due_date'] = date.fromisoformat(c_dict['due_date'])
            if 'created_at' in c_dict and c_dict['created_at'] and isinstance(c_dict['created_at'], str):
                c_dict['created_at'] = datetime.fromisoformat(c_dict['created_at'])
            commitments.append(Commitment(**c_dict))

        result = []
        today = date.today()
        
        for commitment in commitments:
            if not include_completed and commitment.is_completed:
                continue
            
            # Update overdue status
            commitment.is_overdue = commitment.due_date < today and not commitment.is_completed
            
            if target_date is not None:
                if commitment.due_date == target_date:
                    result.append(commitment)
            elif include_overdue and commitment.is_overdue:
                result.append(commitment)
            elif commitment.due_date >= today:
                result.append(commitment)
        
        # Sort by due date and time
        result.sort(key=lambda c: (c.due_date, c.due_time or ""))
        return result
    
    # ========== Abnormality Management ==========
    
    async def add_abnormality(
        self,
        user_id: UUID,
        title: str,
        abnormality_type: AbnormalityType,
        entity_type: str,
        entity_id: UUID,
        days_stale: int = 0,
        description: str | None = None,
        severity: PriorityLevel = PriorityLevel.MEDIUM,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
        suggested_action: str | None = None,
        is_auto_generated: bool = False,
    ) -> Abnormality:
        """Add an abnormality."""
        abnormality = Abnormality(
            id=uuid4(),
            title=title,
            description=description,
            abnormality_type=abnormality_type,
            entity_type=entity_type,
            entity_id=entity_id,
            detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
            days_stale=days_stale,
            severity=severity,
            owner_id=owner_id or user_id,
            owner_name=owner_name,
            suggested_action=suggested_action,
            is_auto_generated=is_auto_generated,
        )
        
        abnormalities_data = await self._get_store(user_id, "abnormalities")
        
        abnormality_dict = asdict(abnormality)
        abnormality_dict['detected_at'] = abnormality.detected_at.isoformat()
        
        abnormalities_data[str(abnormality.id)] = abnormality_dict
        await self._save_store(user_id, "abnormalities", abnormalities_data)
        
        return abnormality
    
    async def resolve_abnormality(self, user_id: UUID, abnormality_id: UUID) -> bool:
        """Resolve (remove) an abnormality."""
        abnormalities_data = await self._get_store(user_id, "abnormalities")
        aid_str = str(abnormality_id)
        
        if aid_str in abnormalities_data:
            del abnormalities_data[aid_str]
            await self._save_store(user_id, "abnormalities", abnormalities_data)
            return True
        return False
    
    async def get_abnormalities(
        self,
        user_id: UUID,
        abnormality_type: AbnormalityType | None = None,
        severity: int | None = None,
    ) -> list[Abnormality]:
        """Get abnormalities with filtering."""
        abnormalities_data = await self._get_store(user_id, "abnormalities")
        abnormalities = []
        for a_dict in abnormalities_data.values():
            if 'detected_at' in a_dict and a_dict['detected_at'] and isinstance(a_dict['detected_at'], str):
                a_dict['detected_at'] = datetime.fromisoformat(a_dict['detected_at'])
            abnormalities.append(Abnormality(**a_dict))

        result = []

        def severity_value(val: Any) -> int:
            if isinstance(val, PriorityLevel):
                return 3 if val == PriorityLevel.HIGH else 2 if val == PriorityLevel.MEDIUM else 1
            return int(val)

        for abnormality in abnormalities:
            if abnormality_type is not None and abnormality.abnormality_type != abnormality_type:
                continue
            if severity is not None:
                if isinstance(severity, PriorityLevel):
                    if abnormality.severity != severity:
                        continue
                else:
                    if severity_value(abnormality.severity) != int(severity):
                        continue
            result.append(abnormality)
        
        # Sort by severity descending then days stale descending
        result.sort(key=lambda a: (-severity_value(a.severity), -a.days_stale))
        
        return result
    
    async def get_abnormality_counts(self, user_id: UUID) -> dict[AbnormalityType, int]:
        """Get counts of abnormalities by type for a user."""
        abnormalities_data = await self._get_store(user_id, "abnormalities")
        counts: dict[AbnormalityType, int] = {}
        for a_dict in abnormalities_data.values():
            atype = a_dict['abnormality_type']
            if atype not in counts:
                counts[atype] = 0
            counts[atype] += 1
        return counts
    
    # ========== Micro-Drill Management ==========
    
    async def add_micro_drill(
        self,
        user_id: UUID,
        question: str,
        answer: str,
        category: str,
        difficulty: int = 3,
        hint: str | None = None,
        context_entity_type: str | None = None,
        context_entity_id: UUID | None = None,
    ) -> MicroDrill:
        """Add a micro-drill question."""
        drill = MicroDrill(
            id=uuid4(),
            question=question,
            answer=answer,
            hint=hint,
            category=category,
            difficulty=min(5, max(1, difficulty)),
            context_entity_type=context_entity_type,
            context_entity_id=context_entity_id,
        )
        
        drills_data = await self._get_store(user_id, "micro_drills")
        drills_data[str(drill.id)] = asdict(drill)
        await self._save_store(user_id, "micro_drills", drills_data)
        
        return drill
    
    async def _seed_default_drills(self, user_id: UUID) -> None:
        """Seed default micro-drills for a new user."""
        default_drills = [
            {
                "question": "What is your #1 priority focus today and why?",
                "answer": "Review the top priorities section and articulate your main focus.",
                "hint": "Check the Top 3 Priorities section.",
                "category": "priorities",
                "difficulty": 1,
            },
            {
                "question": "Which risk category requires the most attention today?",
                "answer": "Review risks by category: Delivery, Quality, Cash, Reputation.",
                "hint": "Look at the risk breakdown by category.",
                "category": "risk_management",
                "difficulty": 2,
            },
            {
                "question": "What commitment is most time-critical today?",
                "answer": "Check commitments sorted by due time.",
                "hint": "Review your Today's Commitments list.",
                "category": "commitments",
                "difficulty": 1,
            },
            {
                "question": "Are there any abnormalities that could escalate if not addressed?",
                "answer": "Review abnormalities and assess escalation potential.",
                "hint": "Check the Abnormalities section for overdue items.",
                "category": "abnormalities",
                "difficulty": 2,
            },
            {
                "question": "What is the current status of your LSW checklist?",
                "answer": "Check Leader Standard Work completion percentage.",
                "hint": "Review the LSW Summary section.",
                "category": "lsw",
                "difficulty": 1,
            },
            {
                "question": "Which customer requires immediate follow-up today?",
                "answer": "Review pending RFQs and quotes with approaching deadlines.",
                "hint": "Check quotes due and follow-up commitments.",
                "category": "customer_focus",
                "difficulty": 2,
            },
            {
                "question": "What is the biggest bottleneck in your current workflow?",
                "answer": "Identify stalled items or blocked tasks requiring escalation.",
                "hint": "Look for stalled RFQs or blocked tasks in abnormalities.",
                "category": "continuous_improvement",
                "difficulty": 3,
            },
        ]
        
        for drill_data in default_drills:
            drill = MicroDrill(
                id=uuid4(),
                question=str(drill_data["question"]),
                answer=str(drill_data["answer"]),
                hint=str(drill_data["hint"]) if drill_data.get("hint") else None,
                category=str(drill_data["category"]),
                difficulty=int(str(drill_data["difficulty"])),
                context_entity_type=None,
                context_entity_id=None,
            )
            drills_store = await self._get_store(user_id, "micro_drills")
            drills_store[str(drill.id)] = asdict(drill)
            await self._save_store(user_id, "micro_drills", drills_store)
    
    async def get_todays_drills(
        self,
        user_id: UUID,
        count: int = 3,
    ) -> list[MicroDrill]:
        """Get today's micro-drill questions for a user."""
        today_str = date.today().isoformat()

        drills_data = await self._get_store(user_id, "micro_drills")
        logging.info(f"[DRILL DEBUG] user_id={user_id}, drills_data={bool(drills_data)}, len={len(drills_data)}")
        
        # Seed default drills if none exist
        if not drills_data:
            logging.info(f"[DRILL DEBUG] Seeding default drills for user {user_id}")
            await self._seed_default_drills(user_id)
            drills_data = await self._get_store(user_id, "micro_drills")
            logging.info(f"[DRILL DEBUG] After seeding: len={len(drills_data)}")
        
        drills = [MicroDrill(**d) for d in drills_data.values()]
        
        # Get user progress
        progress = await self._get_store(user_id, "drill_progress")
        if progress and progress.get("date") != today_str:
            # Reset daily completion when the day rolls over.
            progress["date"] = today_str
            progress["completed_today"] = []
            await self._save_store(user_id, "drill_progress", progress)

        completed_today = (progress or {}).get("completed_today", [])
        
        # Filter out completed drills
        available = [d for d in drills if str(d.id) not in completed_today]

        # If the user has exhausted all drills (or progress got stuck), allow repeats
        # so the "Daily Drill" never dead-ends.
        if not available and drills:
            if not progress:
                progress = {}
            progress["date"] = today_str
            progress["completed_today"] = []
            await self._save_store(user_id, "drill_progress", progress)
            available = drills
        
        return available[:count]
    
    async def complete_drill(
        self,
        user_id: UUID,
        drill_id: UUID,
        correct: bool,
    ) -> dict[str, Any]:
        """Record drill completion."""
        today_str = date.today().isoformat()
        progress = await self._get_store(user_id, "drill_progress")
        if not progress:
            progress = {
                "date": today_str,
                "completed_today": [],
                "streak": 0,
                "total_completed": 0,
                "correct_count": 0,
            }

        # Ensure daily completion list doesn't persist forever.
        if progress.get("date") != today_str:
            progress["date"] = today_str
            progress["completed_today"] = []
        
        if str(drill_id) not in progress["completed_today"]:
            progress["completed_today"].append(str(drill_id))
            progress["total_completed"] += 1
            if correct:
                progress["correct_count"] += 1
                progress["streak"] += 1
            else:
                progress["streak"] = 0
        
        await self._save_store(user_id, "drill_progress", progress)
        
        return {
            "streak": progress["streak"],
            "total_completed": progress["total_completed"],
            "accuracy": (progress["correct_count"] / progress["total_completed"] * 100) if progress["total_completed"] > 0 else 0,
        }
    
    async def get_drill_progress(self, user_id: UUID) -> dict[str, Any]:
        """Get drill progress for a user."""
        today_str = date.today().isoformat()
        progress = await self._get_store(user_id, "drill_progress")
        if not progress:
            return {
                "drills_completed_today": 0,
                "streak": 0,
                "total_completed": 0,
                "accuracy": 0.0,
            }

        if progress.get("date") != today_str:
            # Day rolled over; report today's completion as 0.
            return {
                "drills_completed_today": 0,
                "streak": progress.get("streak", 0),
                "total_completed": progress.get("total_completed", 0),
                "accuracy": (progress.get("correct_count", 0) / progress.get("total_completed", 1) * 100)
                if progress.get("total_completed", 0) > 0
                else 0.0,
            }
        
        return {
            "drills_completed_today": len(progress.get("completed_today", [])),
            "streak": progress.get("streak", 0),
            "total_completed": progress.get("total_completed", 0),
            "accuracy": (progress.get("correct_count", 0) / progress.get("total_completed", 1) * 100) if progress.get("total_completed", 0) > 0 else 0,
        }
    
    # ========== LSW Summary ==========
    
    def get_lsw_summary(self, user_id: UUID) -> LSWChecklistSummary:
        """Get LSW checklist summary for user."""
        # In production, this would query the LSW service
        # For now, return sample data
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
    
    # ========== Quick Metrics ==========
    
    def get_quick_metrics(self, user_id: UUID) -> list[QuickMetric]:
        """Get quick metrics for the Today screen."""
        # In production, this would call the KPI service
        # For now, return sample metrics
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
                name="Quotes Pending",
                value=8,
                unit=None,
                trend="stable",
                trend_value=0,
                status="warning",
                target=5,
                link="/quotes?status=pending",
            ),
            QuickMetric(
                id="win-rate",
                name="Win Rate",
                value=42.5,
                unit="%",
                trend="up",
                trend_value=3.2,
                status="good",
                target=40,
                link="/analytics/win-rate",
            ),
            QuickMetric(
                id="avg-cycle-time",
                name="Avg Cycle Time",
                value=4.2,
                unit="days",
                trend="down",
                trend_value=-0.5,
                status="good",
                target=5,
                link="/analytics/cycle-time",
            ),
        ]
    
    # ========== Shop Floor Management (Phase 3) ==========
    
    async def add_work_order_at_risk(
        self,
        work_order_number: str,
        product_name: str,
        quantity: int,
        due_date: date,
        estimated_completion: date,
        reason: str,
        work_center_id: UUID | None = None,
        work_center_name: str | None = None,
    ) -> WorkOrderAtRisk:
        """Add a work order at risk."""
        days_at_risk = max(0, (estimated_completion - due_date).days)
        if days_at_risk >= 3:
            severity = ShopFloorAlertSeverity.CRITICAL
        elif days_at_risk >= 1:
            severity = ShopFloorAlertSeverity.WARNING
        else:
            severity = ShopFloorAlertSeverity.INFO

        wo_id = uuid4()
        wo = WorkOrderAtRisk(
            id=wo_id,
            work_order_number=work_order_number,
            product_name=product_name,
            quantity=quantity,
            due_date=due_date,
            estimated_completion=estimated_completion,
            days_at_risk=days_at_risk,
            severity=severity,
            reason=reason,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            work_order_id=wo_id,
        )

        await self._save_global_item("work_orders_at_risk", str(wo.id), asdict(wo))
        return wo
    
    async def get_work_orders_at_risk(
        self,
        work_center_id: UUID | None = None,
        severity: ShopFloorAlertSeverity | None = None,
    ) -> list[WorkOrderAtRisk]:
        """Get work orders at risk."""
        data = await self._get_global_store("work_orders_at_risk")
        result = []
        for wo_dict in data.values():
            if isinstance(wo_dict.get("due_date"), str):
                wo_dict["due_date"] = date.fromisoformat(wo_dict["due_date"])
            if isinstance(wo_dict.get("estimated_completion"), str):
                wo_dict["estimated_completion"] = date.fromisoformat(wo_dict["estimated_completion"])

            wo = WorkOrderAtRisk(**wo_dict)
            if work_center_id and wo.work_center_id != work_center_id:
                continue
            if severity and wo.severity != severity:
                continue
            result.append(wo)

        severity_rank = {
            ShopFloorAlertSeverity.CRITICAL: 0,
            ShopFloorAlertSeverity.WARNING: 1,
            ShopFloorAlertSeverity.INFO: 2,
        }
        result.sort(key=lambda w: (severity_rank.get(w.severity, 3), -w.days_at_risk))
        return result
    
    async def resolve_work_order_at_risk(self, work_order_id: UUID) -> bool:
        """Remove a work order from at-risk list."""
        key = "today:global:work_orders_at_risk"
        return await self._redis.hdel(key, str(work_order_id)) > 0  # type: ignore[misc]
    
    async def add_critical_andon(
        self,
        andon_type: str,
        title: str,
        work_center_id: UUID,
        work_center_name: str,
        description: str | None = None,
        station_id: UUID | None = None,
        station_name: str | None = None,
        severity: ShopFloorAlertSeverity = ShopFloorAlertSeverity.CRITICAL,
    ) -> CriticalAndon:
        """Add a critical Andon event."""
        andon = CriticalAndon(
            id=uuid4(),
            andon_type=andon_type,
            title=title,
            description=description,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            station_id=station_id,
            station_name=station_name,
            raised_at=datetime.now(timezone.utc).replace(tzinfo=None),
            minutes_open=0,
            acknowledged=False,
            acknowledged_by_id=None,
            acknowledged_by_name=None,
            severity=severity,
        )
        
        payload = andon if isinstance(self._redis, InMemoryRedis) else asdict(andon)
        await self._save_global_item("critical_andons", str(andon.id), payload)
        return andon
    
    async def acknowledge_andon(
        self,
        andon_id: UUID,
        acknowledged_by_id: UUID,
        acknowledged_by_name: str,
    ) -> CriticalAndon | None:
        """Acknowledge an Andon event."""
        data = await self._get_global_store("critical_andons")
        cid_str = str(andon_id)
        if cid_str in data:
            andon_dict = data[cid_str]
            if isinstance(andon_dict, CriticalAndon):
                andon_dict.acknowledged = True
                andon_dict.acknowledged_by_id = acknowledged_by_id
                andon_dict.acknowledged_by_name = acknowledged_by_name
                await self._save_global_item("critical_andons", cid_str, andon_dict)
                return andon_dict

            andon_dict['acknowledged'] = True
            andon_dict['acknowledged_by_id'] = acknowledged_by_id if isinstance(self._redis, InMemoryRedis) else str(acknowledged_by_id)
            andon_dict['acknowledged_by_name'] = acknowledged_by_name
            await self._save_global_item("critical_andons", cid_str, andon_dict)
            
            if 'raised_at' in andon_dict and andon_dict['raised_at'] and isinstance(andon_dict['raised_at'], str):
                andon_dict['raised_at'] = datetime.fromisoformat(andon_dict['raised_at'])
            return CriticalAndon(**andon_dict)
        return None
    
    async def resolve_andon(self, andon_id: UUID) -> bool:
        """Resolve an Andon event."""
        key = "today:global:critical_andons"
        return await self._redis.hdel(key, str(andon_id)) > 0  # type: ignore[misc]
    
    async def get_critical_andons(
        self,
        work_center_id: UUID | None = None,
        unacknowledged_only: bool = False,
    ) -> list[CriticalAndon]:
        """Get critical Andon events."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        data = await self._get_global_store("critical_andons")
        result = []
        
        for andon_dict in data.values():
            if isinstance(andon_dict, CriticalAndon):
                andon = andon_dict
            else:
                if 'raised_at' in andon_dict and andon_dict['raised_at'] and isinstance(andon_dict['raised_at'], str):
                    andon_dict['raised_at'] = datetime.fromisoformat(andon_dict['raised_at'])
                andon = CriticalAndon(**andon_dict)
            # Update minutes open
            andon.minutes_open = int((now - andon.raised_at).total_seconds() / 60)
            
            if work_center_id and andon.work_center_id != work_center_id:
                continue
            if unacknowledged_only and andon.acknowledged:
                continue
            result.append(andon)
        
        # Sort by acknowledged status (unacknowledged first), then by time open
        result.sort(key=lambda a: (0 if not a.acknowledged else 1, -a.minutes_open))
        return result
    
    async def add_station_efficiency(
        self,
        station_id: UUID,
        station_name: str,
        work_center_id: UUID,
        work_center_name: str,
        current_efficiency: float,
        target_efficiency: float,
        operator_id: UUID | None = None,
        operator_name: str | None = None,
    ) -> StationEfficiency:
        """Add or update station efficiency data."""
        variance = current_efficiency - target_efficiency
        is_below_target = current_efficiency < target_efficiency
        
        # Determine trend (in production, compare with historical data)
        trend = "stable"
        
        eff = StationEfficiency(
            station_id=station_id,
            station_name=station_name,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            current_efficiency=current_efficiency,
            target_efficiency=target_efficiency,
            variance=variance,
            trend=trend,
            is_below_target=is_below_target,
            operator_id=operator_id,
            operator_name=operator_name,
        )
        
        await self._save_global_item("station_efficiencies", str(eff.station_id), asdict(eff))
        return eff
    
    async def get_low_efficiency_stations(
        self,
        work_center_id: UUID | None = None,
        threshold: float | None = None,
    ) -> list[StationEfficiency]:
        """Get stations with efficiency below target or threshold."""
        data = await self._get_global_store("station_efficiencies")
        result = []
        
        for eff_dict in data.values():
            eff = StationEfficiency(**eff_dict)
            if work_center_id and eff.work_center_id != work_center_id:
                continue
            if threshold is not None:
                if eff.current_efficiency < threshold:
                    result.append(eff)
            elif eff.is_below_target:
                result.append(eff)
        
        # Sort by variance (worst first)
        result.sort(key=lambda e: e.variance)
        return result
    
    async def add_cell_oee(
        self,
        cell_id: UUID,
        cell_name: str,
        work_center_id: UUID,
        work_center_name: str,
        availability: float,
        performance: float,
        quality: float,
        target_oee: float,
    ) -> CellOEE:
        """Add or update cell OEE data."""
        current_oee = (availability / 100) * (performance / 100) * (quality / 100) * 100
        variance = current_oee - target_oee
        
        oee = CellOEE(
            cell_id=cell_id,
            cell_name=cell_name,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            current_oee=round(current_oee, 2),
            target_oee=target_oee,
            availability=availability,
            performance=performance,
            quality=quality,
            is_below_threshold=current_oee < target_oee,
            variance=round(variance, 2),
        )
        
        await self._save_global_item("cell_oees", str(oee.cell_id), asdict(oee))
        return oee
    
    async def get_low_oee_cells(
        self,
        work_center_id: UUID | None = None,
        threshold: float | None = None,
    ) -> list[CellOEE]:
        """Get cells with OEE below target or threshold."""
        data = await self._get_global_store("cell_oees")
        result = []
        
        for oee_dict in data.values():
            oee = CellOEE(**oee_dict)
            if work_center_id and oee.work_center_id != work_center_id:
                continue
            if threshold is not None:
                if oee.current_oee < threshold:
                    result.append(oee)
            elif oee.is_below_threshold:
                result.append(oee)
        
        # Sort by variance (worst first)
        result.sort(key=lambda o: o.variance)
        return result
    
    async def get_overall_oee(self) -> float:
        """Get overall OEE across all cells."""
        data = await self._get_global_store("cell_oees")
        if not data:
            return 0.0
        
        total_oee = sum(oee['current_oee'] for oee in data.values())
        return round(total_oee / len(data), 2)
    
    async def add_kanban_alert(
        self,
        material_code: str,
        material_name: str,
        bin_location: str,
        work_center_id: UUID,
        work_center_name: str,
        quantity_needed: float,
        unit: str,
        due_date: date,
        supplier_name: str | None = None,
        replenishment_status: str = "pending",
    ) -> KanbanAlert:
        """Add a Kanban alert."""
        days_overdue = (date.today() - due_date).days
        
        alert = KanbanAlert(
            id=uuid4(),
            material_code=material_code,
            material_name=material_name,
            bin_location=bin_location,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            quantity_needed=quantity_needed,
            unit=unit,
            due_date=due_date,
            days_overdue=max(0, days_overdue),
            supplier_name=supplier_name,
            replenishment_status=replenishment_status,
        )
        
        await self._save_global_item("kanban_alerts", str(alert.id), asdict(alert))
        return alert
    
    async def update_kanban_status(
        self,
        kanban_id: UUID,
        status: str,
    ) -> KanbanAlert | None:
        """Update Kanban replenishment status."""
        data = await self._get_global_store("kanban_alerts")
        kid_str = str(kanban_id)
        if kid_str in data:
            alert_dict = data[kid_str]
            alert_dict['replenishment_status'] = status
            await self._save_global_item("kanban_alerts", kid_str, alert_dict)
            
            if 'due_date' in alert_dict and alert_dict['due_date'] and isinstance(alert_dict['due_date'], str):
                alert_dict['due_date'] = date.fromisoformat(alert_dict['due_date'])
            return KanbanAlert(**alert_dict)
        return None
    
    async def resolve_kanban_alert(self, kanban_id: UUID) -> bool:
        """Resolve a Kanban alert."""
        key = "today:global:kanban_alerts"
        return await self._redis.hdel(key, str(kanban_id)) > 0  # type: ignore[misc]
    
    async def get_overdue_kanbans(
        self,
        work_center_id: UUID | None = None,
    ) -> list[KanbanAlert]:
        """Get overdue Kanban alerts."""
        today = date.today()
        data = await self._get_global_store("kanban_alerts")
        result = []
        
        for alert_dict in data.values():
            if 'due_date' in alert_dict and alert_dict['due_date'] and isinstance(alert_dict['due_date'], str):
                alert_dict['due_date'] = date.fromisoformat(alert_dict['due_date'])
            
            alert = KanbanAlert(**alert_dict)
            # Update days overdue
            alert.days_overdue = max(0, (today - alert.due_date).days)
            
            if work_center_id and alert.work_center_id != work_center_id:
                continue
            if alert.days_overdue > 0:
                result.append(alert)
        
        # Sort by days overdue (most overdue first)
        result.sort(key=lambda a: -a.days_overdue)
        return result
    
    async def add_expiring_certification(
        self,
        user_id: UUID,
        user_name: str,
        certification_name: str,
        certification_type: str,
        expiration_date: date,
        required_for_work_centers: list[str] | None = None,
        renewal_training_id: UUID | None = None,
    ) -> ExpiringCertification:
        """Add an expiring certification."""
        today = date.today()
        days_until_expiry = (expiration_date - today).days
        is_expired = expiration_date < today
        
        cert = ExpiringCertification(
            id=uuid4(),
            user_id=user_id,
            user_name=user_name,
            certification_name=certification_name,
            certification_type=certification_type,
            expiration_date=expiration_date,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            required_for_work_centers=required_for_work_centers or [],
            renewal_training_id=renewal_training_id,
        )
        
        await self._save_global_item("expiring_certifications", str(cert.id), asdict(cert))
        return cert
    
    async def get_expiring_certifications(
        self,
        user_id: UUID | None = None,
        days_ahead: int = 30,
        include_expired: bool = True,
    ) -> list[ExpiringCertification]:
        """Get expiring certifications."""
        today = date.today()
        data = await self._get_global_store("expiring_certifications")
        result = []
        
        for cert_dict in data.values():
            if 'expiration_date' in cert_dict and cert_dict['expiration_date'] and isinstance(cert_dict['expiration_date'], str):
                cert_dict['expiration_date'] = date.fromisoformat(cert_dict['expiration_date'])
            
            cert = ExpiringCertification(**cert_dict)
            # Update days until expiry
            cert.days_until_expiry = (cert.expiration_date - today).days
            cert.is_expired = cert.expiration_date < today
            
            if user_id and cert.user_id != user_id:
                continue
            
            if cert.is_expired:
                if include_expired:
                    result.append(cert)
            elif cert.days_until_expiry <= days_ahead:
                result.append(cert)
        
        # Sort: expired first, then by days until expiry
        result.sort(key=lambda c: (0 if c.is_expired else 1, c.days_until_expiry))
        return result
    
    async def renew_certification(self, certification_id: UUID) -> bool:
        """Mark certification as renewed (remove from expiring list)."""
        key = "today:global:expiring_certifications"
        return await self._redis.hdel(key, str(certification_id)) > 0  # type: ignore[misc]
    
    async def add_wip_violation(
        self,
        work_center_id: UUID,
        work_center_name: str,
        current_wip: int,
        wip_limit: int,
        cell_id: UUID | None = None,
        cell_name: str | None = None,
    ) -> WIPViolation:
        """Add a WIP violation."""
        violation = WIPViolation(
            id=uuid4(),
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            cell_id=cell_id,
            cell_name=cell_name,
            current_wip=current_wip,
            wip_limit=wip_limit,
            violation_amount=current_wip - wip_limit,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            duration_minutes=0,
        )
        
        payload = violation if isinstance(self._redis, InMemoryRedis) else asdict(violation)
        await self._save_global_item("wip_violations", str(violation.id), payload)
        return violation
    
    async def get_wip_violations(
        self,
        work_center_id: UUID | None = None,
    ) -> list[WIPViolation]:
        """Get WIP violations."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        data = await self._get_global_store("wip_violations")
        result = []
        
        for v_dict in data.values():
            if isinstance(v_dict, WIPViolation):
                violation = v_dict
            else:
                if 'started_at' in v_dict and v_dict['started_at'] and isinstance(v_dict['started_at'], str):
                    v_dict['started_at'] = datetime.fromisoformat(v_dict['started_at'])
                violation = WIPViolation(**v_dict)
            # Update duration
            violation.duration_minutes = int((now - violation.started_at).total_seconds() / 60)
            
            if work_center_id and violation.work_center_id != work_center_id:
                continue
            result.append(violation)
        
        # Sort by violation amount (worst first)
        result.sort(key=lambda v: -v.violation_amount)
        return result
    
    async def resolve_wip_violation(self, violation_id: UUID) -> bool:
        """Resolve a WIP violation."""
        key = "today:global:wip_violations"
        return await self._redis.hdel(key, str(violation_id)) > 0  # type: ignore[misc]
    
    async def add_capa_verification(
        self,
        capa_number: str,
        title: str,
        capa_type: str,
        verification_due_date: date,
        owner_id: UUID,
        owner_name: str,
        original_nc_id: UUID | None = None,
        effectiveness_check: bool = False,
    ) -> CAPAVerification:
        """Add a CAPA verification."""
        today = date.today()
        days_until_due = (verification_due_date - today).days
        is_overdue = verification_due_date < today
        
        capa = CAPAVerification(
            id=uuid4(),
            capa_number=capa_number,
            title=title,
            capa_type=capa_type,
            verification_due_date=verification_due_date,
            days_until_due=days_until_due,
            is_overdue=is_overdue,
            owner_id=owner_id,
            owner_name=owner_name,
            original_nc_id=original_nc_id,
            effectiveness_check=effectiveness_check,
        )
        
        await self._save_global_item("capa_verifications", str(capa.id), asdict(capa))
        return capa
    
    async def get_capa_verifications_due(
        self,
        owner_id: UUID | None = None,
        days_ahead: int = 7,
        include_overdue: bool = True,
    ) -> list[CAPAVerification]:
        """Get CAPA verifications due."""
        today = date.today()
        data = await self._get_global_store("capa_verifications")
        result = []
        
        for capa_dict in data.values():
            if 'verification_due_date' in capa_dict and capa_dict['verification_due_date'] and isinstance(capa_dict['verification_due_date'], str):
                capa_dict['verification_due_date'] = date.fromisoformat(capa_dict['verification_due_date'])
            
            capa = CAPAVerification(**capa_dict)
            # Update status
            capa.days_until_due = (capa.verification_due_date - today).days
            capa.is_overdue = capa.verification_due_date < today
            
            if owner_id and capa.owner_id != owner_id:
                continue
            
            if capa.is_overdue:
                if include_overdue:
                    result.append(capa)
            elif capa.days_until_due <= days_ahead:
                result.append(capa)
        
        # Sort: overdue first, then by days until due
        result.sort(key=lambda c: (0 if c.is_overdue else 1, c.days_until_due))
        return result
    
    async def resolve_capa_verification(self, capa_id: UUID) -> bool:
        """Resolve a CAPA verification."""
        key = "today:global:capa_verifications"
        return await self._redis.hdel(key, str(capa_id)) > 0  # type: ignore[misc]

    async def add_scheduled_training(
        self,
        title: str,
        training_type: str,
        scheduled_date: date,
        scheduled_time: str,
        duration_minutes: int,
        attendee_count: int = 0,
        description: str | None = None,
        location: str | None = None,
        instructor_name: str | None = None,
        max_attendees: int | None = None,
        is_user_enrolled: bool = False,
    ) -> ScheduledTraining:
        """Add a scheduled training session."""
        training = ScheduledTraining(
            id=uuid4(),
            title=title,
            description=description,
            training_type=training_type,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            location=location,
            instructor_name=instructor_name,
            attendee_count=attendee_count,
            max_attendees=max_attendees,
            is_user_enrolled=is_user_enrolled,
        )
        
        await self._save_global_item("scheduled_trainings", str(training.id), asdict(training))
        return training
    
    async def get_scheduled_trainings(
        self,
        target_date: date | None = None,
        user_enrolled_only: bool = False,
        days_ahead: int = 7,
    ) -> list[ScheduledTraining]:
        """Get scheduled training sessions."""
        today = date.today()
        data = await self._get_global_store("scheduled_trainings")
        result = []
        
        for t_dict in data.values():
            if 'scheduled_date' in t_dict and t_dict['scheduled_date']:
                if isinstance(t_dict['scheduled_date'], str):
                    t_dict['scheduled_date'] = date.fromisoformat(t_dict['scheduled_date'])
            
            training = ScheduledTraining(**t_dict)
            if user_enrolled_only and not training.is_user_enrolled:
                continue
            
            if target_date:
                if training.scheduled_date == target_date:
                    result.append(training)
            elif training.scheduled_date >= today and training.scheduled_date <= today + timedelta(days=days_ahead):
                result.append(training)
        
        # Sort by date and time
        result.sort(key=lambda t: (t.scheduled_date, t.scheduled_time))
        return result
    
    async def enroll_in_training(self, training_id: UUID) -> ScheduledTraining | None:
        """Enroll user in a training session."""
        data = await self._get_global_store("scheduled_trainings")
        tid_str = str(training_id)
        if tid_str in data:
            training_dict = data[tid_str]
            if training_dict.get('max_attendees') and training_dict.get('attendee_count', 0) >= training_dict['max_attendees']:
                return None
            
            training_dict['attendee_count'] = training_dict.get('attendee_count', 0) + 1
            training_dict['is_user_enrolled'] = True
            await self._save_global_item("scheduled_trainings", tid_str, training_dict)
            
            if 'scheduled_date' in training_dict and training_dict['scheduled_date']:
                if isinstance(training_dict['scheduled_date'], str):
                    training_dict['scheduled_date'] = date.fromisoformat(training_dict['scheduled_date'])
            
            return ScheduledTraining(**training_dict)
        return None
    
    async def get_shop_floor_summary(
        self,
        user_id: UUID | None = None,
        work_center_id: UUID | None = None,
    ) -> ShopFloorSummary:
        """Get complete shop floor summary for Today screen."""
        today = date.today()
        
        # Work orders at risk
        work_orders_at_risk = await self.get_work_orders_at_risk(work_center_id=work_center_id)
        
        # Critical Andons
        critical_andons = await self.get_critical_andons(work_center_id=work_center_id)
        unacknowledged = [a for a in critical_andons if not a.acknowledged]
        avg_response = (
            sum(a.minutes_open for a in critical_andons) / len(critical_andons)
            if critical_andons else 0.0
        )
        
        # Efficiency
        low_efficiency = await self.get_low_efficiency_stations(work_center_id=work_center_id)
        low_oee = await self.get_low_oee_cells(work_center_id=work_center_id)
        overall_oee = await self.get_overall_oee()
        
        # Kanbans
        overdue_kanbans = await self.get_overdue_kanbans(work_center_id=work_center_id)
        pending_data = await self._get_global_store("kanban_alerts")
        pending_kanbans = [
            k for k in pending_data.values()
            if k.get('replenishment_status') == "pending"
        ]
        
        # Certifications
        expiring_certs = await self.get_expiring_certifications(user_id=user_id)
        expired = [c for c in expiring_certs if c.is_expired]
        expiring_soon = [c for c in expiring_certs if not c.is_expired and c.days_until_expiry <= 30]
        
        # WIP violations
        wip_violations = await self.get_wip_violations(work_center_id=work_center_id)
        
        # CAPA verifications
        capa_due = await self.get_capa_verifications_due(owner_id=user_id)
        overdue_capas = [c for c in capa_due if c.is_overdue]
        
        # Scheduled trainings
        trainings_today = await self.get_scheduled_trainings(target_date=today)
        all_trainings = await self.get_scheduled_trainings()
        
        return ShopFloorSummary(
            work_orders_at_risk=work_orders_at_risk,
            work_orders_at_risk_count=len(work_orders_at_risk),
            critical_andons=critical_andons,
            unacknowledged_andon_count=len(unacknowledged),
            avg_andon_response_minutes=round(avg_response, 1),
            low_efficiency_stations=low_efficiency,
            low_oee_cells=low_oee,
            overall_oee=overall_oee,
            overdue_kanbans=overdue_kanbans,
            pending_kanban_count=len(pending_kanbans),
            expiring_certifications=expiring_certs,
            expired_certification_count=len(expired),
            expiring_soon_count=len(expiring_soon),
            wip_violations=wip_violations,
            total_wip_violation_count=len(wip_violations),
            capa_verifications_due=capa_due,
            overdue_capa_count=len(overdue_capas),
            scheduled_trainings=all_trainings,
            training_sessions_today=len(trainings_today),
        )

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
                    if (now - last_agg_dt).total_seconds() < 300: # 5 minutes
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
        risks_data = await self._get_store(user_id, "risks")
        total_risks = len(risks_data)
        critical_risks = sum(1 for r in risks_data.values() if r.get('severity', 0) >= 8)
        
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
        
        # Real-time awareness (The Pulse & Handovers)
        active_pulses = []
        active_handovers = []
        
        if db:
            pulse_service = get_pulse_service()
            db_pulses = await pulse_service.get_active_pulses(db)
            active_pulses = [
                GlobalPulseSummary(
                    id=p.id,
                    message=p.message,
                    severity=p.severity.value,
                    highlight_metric_name=p.highlight_metric_name,
                    highlight_metric_value=p.highlight_metric_value,
                )
                for p in db_pulses
            ]
            
            handover_service = get_handover_service()
            # For now, list all unacknowledged handovers. In a real system, we'd filter by user's station.
            db_handovers = await handover_service.list_handover_notes(db, include_acknowledged=False, limit=10)
            active_handovers = [
                HandoverNoteSummary(
                    id=h.id,
                    station_id=h.station_id,
                    severity=h.severity.value,
                    safety=h.safety,
                    quality=h.quality,
                    delivery=h.delivery,
                    cost=h.cost,
                    people=h.people,
                    notes=h.notes,
                    created_at=h.created_at,
                )
                for h in db_handovers
            ]
        
        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
            active_pulses=active_pulses,
            active_handovers=active_handovers,
            shop_floor_summary=shop_floor,
            generated_at=generated_at,
            cache_valid_until=generated_at + timedelta(minutes=5),
        )
    
    async def _clear_auto_generated_items(self, user_id: UUID) -> None:
        """Clear auto-generated commitments and abnormalities for a user."""
        # Clear commitments
        commitments_data = await self._get_store(user_id, "commitments")
        to_remove_c = [cid for cid, c in commitments_data.items() if c.get('is_auto_generated')]
        for cid in to_remove_c:
            del commitments_data[cid]
        await self._save_store(user_id, "commitments", commitments_data)
        
        # Clear abnormalities
        abnormalities_data = await self._get_store(user_id, "abnormalities")
        to_remove_a = [aid for aid, a in abnormalities_data.items() if a.get('is_auto_generated')]
        for aid in to_remove_a:
            del abnormalities_data[aid]
        await self._save_store(user_id, "abnormalities", abnormalities_data)

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
        
        # Batch updates to Redis to avoid N+1 roundtrips
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

    # ========== Sample Data ==========
    
    async def _register_sample_data(self) -> None:
        """Register sample data for testing."""
        # Sample micro-drills
        sample_drills = [
            {
                "question": "What is the first step in processing an RFQ?",
                "answer": "Verify completeness and customer requirements",
                "category": "rfq",
                "difficulty": 2,
                "hint": "Think about validation before action",
            },
            {
                "question": "What margin threshold requires GM approval?",
                "answer": "Below 25% gross margin",
                "category": "quoting",
                "difficulty": 3,
                "hint": "It's a percentage threshold",
            },
            {
                "question": "How many days before a quote is considered stale?",
                "answer": "7 days without customer response",
                "category": "quoting",
                "difficulty": 2,
                "hint": "It's about a week",
            },
        ]
        
        for drill in sample_drills:
            await self.add_micro_drill(
                user_id=uuid4(),  # Generate a test user_id for sample data
                question=str(drill["question"]),
                answer=str(drill["answer"]),
                category=str(drill["category"]),
                difficulty=int(str(drill["difficulty"])),
                hint=str(drill["hint"]) if drill.get("hint") else None,
            )


class TodayScreenService:
    """Async-friendly wrapper around AsyncTodayScreenService."""

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

    def _run(self, coro: Coroutine[Any, Any, T]) -> T | Coroutine[Any, Any, T]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        return coro

    async def _get_todays_drills_async(self, user_id: UUID, count: int = 3) -> list[MicroDrill]:
        # Use the async service's method which includes seeding logic
        return await self._async.get_todays_drills(user_id, count=count)

    def get_todays_drills(self, user_id: UUID, count: int = 3) -> list[MicroDrill] | Coroutine[Any, Any, list[MicroDrill]]:
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
    ) -> TodayScreenData | Coroutine[Any, Any, TodayScreenData]:
        return self._run(self._get_today_screen_async(user_id, user_name, db=db))

    async def _complete_capa_verification_async(self, capa_id: UUID) -> bool:
        return await self._async.resolve_capa_verification(capa_id)

    def complete_capa_verification(self, capa_id: UUID) -> bool:
        return self._run(self._complete_capa_verification_async(capa_id))  # type: ignore[return-value]

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
        client = redis_client_override
        if client is None and settings.is_production:
            client = redis_client
        _service = TodayScreenService(redis_client=client)
    return _service


def reset_today_screen_service() -> None:
    """Reset the service instance (for testing)."""
    global _service
    _service = None

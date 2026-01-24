"""
Micro-drill management for Today Screen.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, List, Dict, TypedDict
from uuid import UUID, uuid4

from sensei.services.ops.today_screen_v2.base import BaseRedisStore
from sensei.services.ops.today_screen_models import MicroDrill

logger = logging.getLogger(__name__)


class DrillTemplate(TypedDict):
    """Type definition for default drill templates."""
    question: str
    answer: str
    hint: str
    category: str
    difficulty: int


DEFAULT_DRILLS: List[DrillTemplate] = [
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


class MicroDrillManager(BaseRedisStore):
    """Manages micro-drills for the Today screen."""
    
    def __init__(self, redis_client: Any) -> None:
        super().__init__(redis_client, "micro_drills")
        self._progress_store_name = "drill_progress"

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
        
        drills_data = await self._get_store(user_id)
        drills_data[str(drill.id)] = asdict(drill)
        await self._save_store(user_id, drills_data)
        
        return drill
    
    async def _seed_default_drills(self, user_id: UUID) -> None:
        """Seed default micro-drills for a new user."""
        for drill_data in DEFAULT_DRILLS:
            drill = MicroDrill(
                id=uuid4(),
                question=drill_data["question"],
                answer=drill_data["answer"],
                hint=drill_data["hint"],
                category=drill_data["category"],
                difficulty=drill_data["difficulty"],
                context_entity_type=None,
                context_entity_id=None,
            )
            drills_store = await self._get_store(user_id)
            drills_store[str(drill.id)] = asdict(drill)
            await self._save_store(user_id, drills_store)
    
    async def get_todays_drills(
        self,
        user_id: UUID,
        count: int = 3,
    ) -> List[MicroDrill]:
        """Get today's micro-drill questions for a user."""
        drills_data = await self._get_store(user_id)
        logger.info(f"[DRILL DEBUG] user_id={user_id}, drills_data={bool(drills_data)}, len={len(drills_data)}")
        
        # Seed default drills if none exist
        if not drills_data:
            logger.info(f"[DRILL DEBUG] Seeding default drills for user {user_id}")
            await self._seed_default_drills(user_id)
            drills_data = await self._get_store(user_id)
            logger.info(f"[DRILL DEBUG] After seeding: len={len(drills_data)}")
        
        drills = [MicroDrill(**d) for d in drills_data.values()]
        
        # Get user progress
        progress = await self._get_progress(user_id)
        completed_today = progress.get("completed_today", [])
        
        # Filter out completed drills
        available = [d for d in drills if str(d.id) not in completed_today]
        
        return available[:count]
    
    async def complete_drill(
        self,
        user_id: UUID,
        drill_id: UUID,
        correct: bool,
    ) -> Dict[str, Any]:
        """Record drill completion."""
        progress = await self._get_progress(user_id)
        if not progress:
            progress = {
                "completed_today": [],
                "streak": 0,
                "total_completed": 0,
                "correct_count": 0,
            }
        
        if str(drill_id) not in progress["completed_today"]:
            progress["completed_today"].append(str(drill_id))
            progress["total_completed"] += 1
            if correct:
                progress["correct_count"] += 1
                progress["streak"] += 1
            else:
                progress["streak"] = 0
        
        await self._save_progress(user_id, progress)
        
        return {
            "streak": progress["streak"],
            "total_completed": progress["total_completed"],
            "accuracy": (
                progress["correct_count"] / progress["total_completed"] * 100
            ) if progress["total_completed"] > 0 else 0,
        }
    
    async def get_drill_progress(self, user_id: UUID) -> Dict[str, Any]:
        """Get drill progress for a user."""
        progress = await self._get_progress(user_id)
        if not progress:
            return {
                "drills_completed_today": 0,
                "streak": 0,
                "total_completed": 0,
                "accuracy": 0.0,
            }
        
        return {
            "drills_completed_today": len(progress.get("completed_today", [])),
            "streak": progress.get("streak", 0),
            "total_completed": progress.get("total_completed", 0),
            "accuracy": (
                progress.get("correct_count", 0) / progress.get("total_completed", 1) * 100
            ) if progress.get("total_completed", 0) > 0 else 0,
        }

    async def _get_progress(self, user_id: UUID) -> Dict[str, Any]:
        """Get drill progress from Redis."""
        key = f"today:{user_id}:{self._progress_store_name}"
        from sensei.services.ops.today_screen_v2.base import InMemoryRedis
        import json
        
        data = await self._redis.hgetall(key) if self._redis else {}
        if not data:
            return {}
        if isinstance(self._redis, InMemoryRedis):
            return dict(data)
        return {k: json.loads(v) for k, v in data.items()}

    async def _save_progress(self, user_id: UUID, data: Dict[str, Any]) -> None:
        """Save drill progress to Redis."""
        key = f"today:{user_id}:{self._progress_store_name}"
        from sensei.services.ops.today_screen_v2.base import InMemoryRedis, UUIDEncoder
        import json
        
        if not data:
            if self._redis:
                await self._redis.delete(key)
            return
        
        serialized = (
            data if isinstance(self._redis, InMemoryRedis)
            else {k: json.dumps(v, cls=UUIDEncoder) for k, v in data.items()}
        )
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.delete(key)
            await pipe.hset(key, mapping=serialized)
            await pipe.expire(key, 86400)
            await pipe.execute()

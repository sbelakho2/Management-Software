"""
Priority management for Today Screen.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, date
from typing import Any, List
from uuid import UUID, uuid4

from sensei.services.ops.today_screen_v2.base import BaseRedisStore
from sensei.services.ops.today_screen_models import Priority, PriorityLevel


class PriorityManager(BaseRedisStore):
    """Manages user priorities for the Today screen."""
    
    def __init__(self, redis_client: Any) -> None:
        super().__init__(redis_client, "priorities")

    async def set_top_priorities(
        self,
        user_id: UUID,
        priority_ids: List[UUID],
    ) -> List[Priority]:
        """Set the user's top 3 priorities (forced selection)."""
        if len(priority_ids) > 3:
            raise ValueError("Maximum 3 top priorities allowed")
        
        priorities_data = await self._get_store(user_id)
        
        # Reset all user-selected flags
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
        
        await self._save_store(user_id, priorities_data)
        return [
            self._dict_to_priority(p)
            for p in priorities_data.values()
            if p.get('is_user_selected')
        ]
    
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
        
        priorities_data = await self._get_store(user_id)
        
        priority_dict = asdict(priority)
        priority_dict['created_at'] = priority.created_at.isoformat()
        if priority.due_date:
            priority_dict['due_date'] = priority.due_date.isoformat()
        
        priorities_data[str(priority.id)] = priority_dict
        await self._save_store(user_id, priorities_data)
        
        return priority
    
    async def remove_priority(self, user_id: UUID, priority_id: UUID) -> bool:
        """Remove a priority item."""
        priorities_data = await self._get_store(user_id)
        pid_str = str(priority_id)
        
        if pid_str in priorities_data:
            del priorities_data[pid_str]
            await self._save_store(user_id, priorities_data)
            return True
        return False
    
    async def get_user_priorities(
        self,
        user_id: UUID,
        include_selected: bool = True,
        include_unselected: bool = True,
    ) -> List[Priority]:
        """Get priorities for a user."""
        priorities_data = await self._get_store(user_id)
        
        result = []
        for p_dict in priorities_data.values():
            p = self._dict_to_priority(p_dict)
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

    def _dict_to_priority(self, p_dict: dict[str, Any]) -> Priority:
        """Convert a dictionary to a Priority, handling date conversions."""
        if isinstance(p_dict['created_at'], str):
            p_dict['created_at'] = datetime.fromisoformat(p_dict['created_at'])
        if p_dict.get('due_date') and isinstance(p_dict['due_date'], str):
            p_dict['due_date'] = date.fromisoformat(p_dict['due_date'])
        return Priority(**p_dict)

"""
Abnormality management for Today Screen.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, List, Dict
from uuid import UUID, uuid4

from sensei.services.ops.today_screen_v2.base import BaseRedisStore
from sensei.services.ops.today_screen_models import Abnormality, AbnormalityType, PriorityLevel


class AbnormalityManager(BaseRedisStore):
    """Manages abnormalities for the Today screen."""
    
    def __init__(self, redis_client: Any) -> None:
        super().__init__(redis_client, "abnormalities")

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
        
        abnormalities_data = await self._get_store(user_id)
        
        abnormality_dict = asdict(abnormality)
        abnormality_dict['detected_at'] = abnormality.detected_at.isoformat()
        
        abnormalities_data[str(abnormality.id)] = abnormality_dict
        await self._save_store(user_id, abnormalities_data)
        
        return abnormality
    
    async def resolve_abnormality(
        self,
        user_id: UUID,
        abnormality_id: UUID,
    ) -> bool:
        """Resolve (remove) an abnormality."""
        abnormalities_data = await self._get_store(user_id)
        aid_str = str(abnormality_id)
        
        if aid_str in abnormalities_data:
            del abnormalities_data[aid_str]
            await self._save_store(user_id, abnormalities_data)
            return True
        return False
    
    async def get_abnormalities(
        self,
        user_id: UUID,
        abnormality_type: AbnormalityType | None = None,
        severity: int | None = None,
    ) -> List[Abnormality]:
        """Get abnormalities with filtering."""
        abnormalities_data = await self._get_store(user_id)
        abnormalities = [
            self._dict_to_abnormality(a_dict)
            for a_dict in abnormalities_data.values()
        ]

        result = []

        for abnormality in abnormalities:
            if abnormality_type is not None and abnormality.abnormality_type != abnormality_type:
                continue
            if severity is not None:
                if self._severity_value(abnormality.severity) != self._severity_value(severity):
                    continue
            result.append(abnormality)
        
        # Sort by severity descending then days stale descending
        result.sort(key=lambda a: (-self._severity_value(a.severity), -a.days_stale))
        
        return result
    
    async def get_abnormality_counts(self, user_id: UUID) -> Dict[AbnormalityType, int]:
        """Get counts of abnormalities by type for a user."""
        abnormalities_data = await self._get_store(user_id)
        counts: Dict[AbnormalityType, int] = {}
        for a_dict in abnormalities_data.values():
            atype = a_dict['abnormality_type']
            if atype not in counts:
                counts[atype] = 0
            counts[atype] += 1
        return counts

    async def clear_auto_generated(self, user_id: UUID) -> None:
        """Clear auto-generated abnormalities for a user."""
        abnormalities_data = await self._get_store(user_id)
        to_remove = [
            aid for aid, a in abnormalities_data.items()
            if a.get('is_auto_generated')
        ]
        for aid in to_remove:
            del abnormalities_data[aid]
        await self._save_store(user_id, abnormalities_data)

    def _dict_to_abnormality(self, a_dict: dict[str, Any]) -> Abnormality:
        """Convert a dictionary to an Abnormality, handling date conversions."""
        if 'detected_at' in a_dict and a_dict['detected_at'] and isinstance(a_dict['detected_at'], str):
            a_dict['detected_at'] = datetime.fromisoformat(a_dict['detected_at'])
        return Abnormality(**a_dict)

    def _severity_value(self, val: Any) -> int:
        """Convert severity to numeric value for comparison."""
        if isinstance(val, PriorityLevel):
            return 3 if val == PriorityLevel.HIGH else 2 if val == PriorityLevel.MEDIUM else 1
        return int(val)

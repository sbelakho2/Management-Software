"""
Commitment management for Today Screen.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, date
from typing import Any, List
from uuid import UUID, uuid4

from sensei.services.ops.today_screen_v2.base import BaseRedisStore
from sensei.services.ops.today_screen_models import Commitment, CommitmentType


class CommitmentManager(BaseRedisStore):
    """Manages commitments for the Today screen."""
    
    def __init__(self, redis_client: Any) -> None:
        super().__init__(redis_client, "commitments")

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
        
        commitments_data = await self._get_store(user_id)
        
        commitment_dict = asdict(commitment)
        commitment_dict['created_at'] = commitment.created_at.isoformat()
        if commitment.due_date:
            commitment_dict['due_date'] = commitment.due_date.isoformat()
            
        commitments_data[str(commitment.id)] = commitment_dict
        await self._save_store(user_id, commitments_data)
        
        return commitment
    
    async def complete_commitment(
        self,
        user_id: UUID,
        commitment_id: UUID,
    ) -> Commitment | None:
        """Mark a commitment as completed."""
        commitments_data = await self._get_store(user_id)
        cid_str = str(commitment_id)
        
        if cid_str in commitments_data:
            c_dict = commitments_data[cid_str]
            c_dict['is_completed'] = True
            await self._save_store(user_id, commitments_data)
            return self._dict_to_commitment(c_dict)
        return None
    
    async def get_commitments(
        self,
        user_id: UUID,
        target_date: date | None = None,
        include_overdue: bool = True,
        include_completed: bool = False,
    ) -> List[Commitment]:
        """Get commitments with filtering."""
        commitments_data = await self._get_store(user_id)
        commitments = [
            self._dict_to_commitment(c_dict)
            for c_dict in commitments_data.values()
        ]

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

    async def clear_auto_generated(self, user_id: UUID) -> None:
        """Clear auto-generated commitments for a user."""
        commitments_data = await self._get_store(user_id)
        to_remove = [
            cid for cid, c in commitments_data.items()
            if c.get('is_auto_generated')
        ]
        for cid in to_remove:
            del commitments_data[cid]
        await self._save_store(user_id, commitments_data)

    def _dict_to_commitment(self, c_dict: dict[str, Any]) -> Commitment:
        """Convert a dictionary to a Commitment, handling date conversions."""
        if 'due_date' in c_dict and c_dict['due_date'] and isinstance(c_dict['due_date'], str):
            c_dict['due_date'] = date.fromisoformat(c_dict['due_date'])
        if 'created_at' in c_dict and c_dict['created_at'] and isinstance(c_dict['created_at'], str):
            c_dict['created_at'] = datetime.fromisoformat(c_dict['created_at'])
        return Commitment(**c_dict)

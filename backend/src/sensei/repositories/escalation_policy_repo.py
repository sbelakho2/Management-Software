"""
Database repository for Escalation Policy.

Provides async database access for escalation configuration persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.service_persistence import (
    EscalationPolicyDB,
    EscalationThresholdDB,
)


class EscalationPolicyRepository:
    """Repository for escalation policy database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session
    
    # --------------------------------------------------------------------------
    # Policies
    # --------------------------------------------------------------------------
    
    async def create_policy(
        self,
        name: str,
        priority: str,
        escalation_sequence: list[dict[str, Any]],
        notification_channels: list[str],
        auto_escalate: bool = True,
        escalation_interval_minutes: int = 60,
        max_escalation_level: int = 3,
        schedule_config: dict[str, Any] | None = None,
        conditions: dict[str, Any] | None = None,
        is_active: bool = True,
        created_by: UUID | None = None,
    ) -> EscalationPolicyDB:
        """Create a new escalation policy."""
        policy = EscalationPolicyDB(
            name=name,
            priority=priority,
            escalation_sequence=escalation_sequence,
            notification_channels=notification_channels,
            auto_escalate=auto_escalate,
            escalation_interval_minutes=escalation_interval_minutes,
            max_escalation_level=max_escalation_level,
            schedule_config=schedule_config,
            conditions=conditions,
            is_active=is_active,
            created_by=created_by,
        )
        self._session.add(policy)
        await self._session.flush()
        await self._session.refresh(policy)
        return policy
    
    async def get_policy(self, policy_id: UUID) -> EscalationPolicyDB | None:
        """Get a policy by ID."""
        result = await self._session.execute(
            select(EscalationPolicyDB).where(EscalationPolicyDB.id == policy_id)
        )
        return result.scalar_one_or_none()
    
    async def get_policy_by_name(self, name: str) -> EscalationPolicyDB | None:
        """Get a policy by name."""
        result = await self._session.execute(
            select(EscalationPolicyDB).where(EscalationPolicyDB.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_policy_for_priority(self, priority: str) -> EscalationPolicyDB | None:
        """Get the active policy for a priority level."""
        result = await self._session.execute(
            select(EscalationPolicyDB).where(
                and_(
                    EscalationPolicyDB.priority == priority,
                    EscalationPolicyDB.is_active.is_(True),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_policy(
        self,
        policy_id: UUID,
        **fields: Any,
    ) -> EscalationPolicyDB | None:
        """Update a policy."""
        policy = await self.get_policy(policy_id)
        if not policy:
            return None
        
        for field, value in fields.items():
            if hasattr(policy, field):
                setattr(policy, field, value)
        
        policy.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(policy)
        return policy
    
    async def delete_policy(self, policy_id: UUID) -> bool:
        """Delete a policy and its thresholds."""
        # Delete thresholds first
        await self._session.execute(
            delete(EscalationThresholdDB).where(
                EscalationThresholdDB.policy_id == policy_id
            )
        )
        
        result = await self._session.execute(
            delete(EscalationPolicyDB).where(EscalationPolicyDB.id == policy_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def list_policies(
        self,
        active_only: bool = False,
        priority: str | None = None,
        limit: int = 100,
    ) -> list[EscalationPolicyDB]:
        """List escalation policies."""
        query = select(EscalationPolicyDB)
        
        if active_only:
            query = query.where(EscalationPolicyDB.is_active.is_(True))
        
        if priority:
            query = query.where(EscalationPolicyDB.priority == priority)
        
        query = query.order_by(EscalationPolicyDB.name)
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def deactivate_policy(self, policy_id: UUID) -> EscalationPolicyDB | None:
        """Deactivate a policy."""
        return await self.update_policy(policy_id, is_active=False)
    
    async def activate_policy(self, policy_id: UUID) -> EscalationPolicyDB | None:
        """Activate a policy."""
        return await self.update_policy(policy_id, is_active=True)
    
    # --------------------------------------------------------------------------
    # Thresholds
    # --------------------------------------------------------------------------
    
    async def create_threshold(
        self,
        policy_id: UUID,
        threshold_name: str,
        metric_type: str,
        threshold_value: float,
        comparison_operator: str,
        trigger_level: int,
        notification_message: str | None = None,
        cooldown_minutes: int = 15,
    ) -> EscalationThresholdDB:
        """Create an escalation threshold."""
        threshold = EscalationThresholdDB(
            policy_id=policy_id,
            threshold_name=threshold_name,
            metric_type=metric_type,
            threshold_value=threshold_value,
            comparison_operator=comparison_operator,
            trigger_level=trigger_level,
            notification_message=notification_message,
            cooldown_minutes=cooldown_minutes,
        )
        self._session.add(threshold)
        await self._session.flush()
        await self._session.refresh(threshold)
        return threshold
    
    async def get_threshold(self, threshold_id: UUID) -> EscalationThresholdDB | None:
        """Get a threshold by ID."""
        result = await self._session.execute(
            select(EscalationThresholdDB).where(
                EscalationThresholdDB.id == threshold_id
            )
        )
        return result.scalar_one_or_none()
    
    async def list_thresholds_for_policy(
        self,
        policy_id: UUID,
    ) -> list[EscalationThresholdDB]:
        """List thresholds for a policy."""
        result = await self._session.execute(
            select(EscalationThresholdDB)
            .where(EscalationThresholdDB.policy_id == policy_id)
            .order_by(EscalationThresholdDB.trigger_level)
        )
        return list(result.scalars().all())
    
    async def update_threshold(
        self,
        threshold_id: UUID,
        **fields: Any,
    ) -> EscalationThresholdDB | None:
        """Update a threshold."""
        threshold = await self.get_threshold(threshold_id)
        if not threshold:
            return None
        
        for field, value in fields.items():
            if hasattr(threshold, field):
                setattr(threshold, field, value)
        
        threshold.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(threshold)
        return threshold
    
    async def delete_threshold(self, threshold_id: UUID) -> bool:
        """Delete a threshold."""
        result = await self._session.execute(
            delete(EscalationThresholdDB).where(
                EscalationThresholdDB.id == threshold_id
            )
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def record_trigger(
        self,
        threshold_id: UUID,
        trigger_count: int = 1,
    ) -> EscalationThresholdDB | None:
        """Record a threshold trigger event."""
        threshold = await self.get_threshold(threshold_id)
        if not threshold:
            return None
        
        threshold.trigger_count = (threshold.trigger_count or 0) + trigger_count
        threshold.last_triggered_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(threshold)
        return threshold


async def get_escalation_policy_repo(
    session: AsyncSession,
) -> EscalationPolicyRepository:
    """Dependency injection helper for EscalationPolicyRepository."""
    return EscalationPolicyRepository(session)

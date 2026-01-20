"""
Risk management for Today Screen.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, date
from typing import Any, List, Dict
from uuid import UUID, uuid4

from sensei.services.ops.today_screen_v2.base import BaseRedisStore
from sensei.services.ops.today_screen_models import Risk, RiskCategory


class RiskManager(BaseRedisStore):
    """Manages risks for the Today screen."""
    
    def __init__(self, redis_client: Any) -> None:
        super().__init__(redis_client, "risks")

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
        clamped_severity = min(10, max(1, severity))
        clamped_probability = min(10, max(1, probability))
        
        risk = Risk(
            id=uuid4(),
            title=title,
            description=description,
            category=category,
            severity=clamped_severity,
            probability=clamped_probability,
            entity_type=entity_type,
            entity_id=entity_id,
            owner_id=owner_id or user_id,
            owner_name=owner_name,
            mitigation=mitigation,
            due_date=due_date,
        )
        
        risks_data = await self._get_store(user_id)
        
        risk_dict = asdict(risk)
        risk_dict['created_at'] = risk.created_at.isoformat()
        risk_dict['risk_score'] = risk.risk_score
        if risk.due_date:
            risk_dict['due_date'] = risk.due_date.isoformat()
            
        risks_data[str(risk.id)] = risk_dict
        await self._save_store(user_id, risks_data)
        
        return risk
    
    async def get_risks_by_category(
        self,
        user_id: UUID,
        category: RiskCategory | None = None,
        top_n: int | None = None,
    ) -> Dict[RiskCategory, List[Risk]]:
        """Get risks grouped by category."""
        risks_data = await self._get_store(user_id)
        risks = [self._dict_to_risk(r_dict) for r_dict in risks_data.values()]

        result: Dict[RiskCategory, List[Risk]] = {}
        
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
    
    async def get_top_risks(self, user_id: UUID, top_n: int = 5) -> List[Risk]:
        """Get top N risks across all categories."""
        risks_data = await self._get_store(user_id)
        risks = [self._dict_to_risk(r_dict) for r_dict in risks_data.values()]
        risks.sort(key=lambda r: r.risk_score, reverse=True)
        return risks[:top_n]

    async def get_risk_count(self, user_id: UUID) -> int:
        """Get total count of risks for a user."""
        risks_data = await self._get_store(user_id)
        return len(risks_data)

    async def get_critical_risk_count(self, user_id: UUID, threshold: int = 8) -> int:
        """Get count of critical risks (severity >= threshold)."""
        risks_data = await self._get_store(user_id)
        return sum(1 for r in risks_data.values() if r.get('severity', 0) >= threshold)

    def _dict_to_risk(self, r_dict: dict[str, Any]) -> Risk:
        """Convert a dictionary to a Risk, handling date conversions."""
        if 'due_date' in r_dict and r_dict['due_date'] and isinstance(r_dict['due_date'], str):
            r_dict['due_date'] = date.fromisoformat(r_dict['due_date'])
        if 'created_at' in r_dict and r_dict['created_at'] and isinstance(r_dict['created_at'], str):
            r_dict['created_at'] = datetime.fromisoformat(r_dict['created_at'])
        # Remove risk_score from dict if present (it's a property)
        r_dict.pop('risk_score', None)
        return Risk(**r_dict)

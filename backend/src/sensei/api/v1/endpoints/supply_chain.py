from typing import Any

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from sensei.services.supply_chain.supply_chain_simulation import get_supply_chain_simulator, SupplyChainSimulator, DisruptionLibrary
from sensei.api import deps
from sensei.core.config import settings


def _deny_production() -> None:
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")

AllowSupplyChainModule = deps.require_role(
    "supply_chain",
    "purchasing",
    "logistics",
    "warehouse",
    "ops",
    "gm",
    "finance",
    "accountant",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(_deny_production),
        Depends(
            deps.RoleChecker(
                [
                    "supply_chain",
                    "purchasing",
                    "logistics",
                    "warehouse",
                    "ops",
                    "gm",
                    "finance",
                    "accountant",
                ]
            )
        )
    ]
)


def _severity_score(severity: str) -> float:
    mapping = {
        "minimal": 0.1,
        "low": 0.25,
        "moderate": 0.5,
        "high": 0.75,
        "critical": 1.0,
    }
    return float(mapping.get(severity, 0.5))

@router.get("/stats", response_model=dict[str, Any])
async def get_supply_chain_stats(
    service: SupplyChainSimulator = Depends(get_supply_chain_simulator),
):
    """Get supply chain simulator statistics."""
    return service.get_statistics()

@router.get("/scenarios", response_model=list[dict[str, Any]])
async def list_scenarios(
):
    """List all available disruption scenarios."""
    scenarios = DisruptionLibrary.get_all_scenarios()
    return [
        {
            "scenario_id": s.scenario_id,
            "name": s.name,
            "disruption_type": s.disruption_type.value,
            "severity": s.severity.value,
            "delay_percentage": s.delay_percentage,
            "cost_increase_percentage": s.cost_increase_percentage,
            "availability_impact": s.availability_impact,
            "duration_days": s.duration_days,
            "probability": s.probability,
            "description": s.description,
            "affected_regions": s.affected_regions,
            "affected_suppliers": s.affected_suppliers,
        }
        for s in scenarios
    ]

@router.get("/risk-analysis", response_model=dict[str, Any])
async def get_risk_analysis(
    service: SupplyChainSimulator = Depends(get_supply_chain_simulator),
):
    """Get overall supply chain risk analysis."""
    scenarios = DisruptionLibrary.get_all_scenarios()
    if not scenarios:
        return {
            "global_risk_index": 0.0,
            "primary_risk_drivers": [],
            "mitigation_readiness": float(getattr(service, "confidence_level", 0.0) or 0.0),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    weighted: list[tuple[float, Any]] = []
    for s in scenarios:
        sev = _severity_score(getattr(s.severity, "value", str(s.severity)))
        prob = float(getattr(s, "probability", 0.0) or 0.0)
        # Keep this conservative: risk is driven primarily by likelihood * severity.
        weighted.append((prob * sev, s))

    weighted.sort(key=lambda t: t[0], reverse=True)
    global_risk_index = sum(w for w, _ in weighted)
    # Clamp to [0, 1] for UI friendliness.
    global_risk_index = max(0.0, min(1.0, float(global_risk_index)))

    primary = []
    for _, s in weighted[:3]:
        dt = getattr(getattr(s, "disruption_type", None), "value", None) or "unknown"
        if dt not in primary:
            primary.append(dt)

    return {
        "global_risk_index": global_risk_index,
        "primary_risk_drivers": primary,
        # Not a readiness score; expose simulator configuration rather than inventing a metric.
        "mitigation_readiness": float(getattr(service, "confidence_level", 0.0) or 0.0),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

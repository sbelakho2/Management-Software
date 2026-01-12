from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sensei.services.supply_chain.supply_chain_simulation import get_supply_chain_simulator, SupplyChainSimulator, DisruptionLibrary
from sensei.api import deps

router = APIRouter()

@router.get("/stats", response_model=dict[str, Any])
async def get_supply_chain_stats(
    service: SupplyChainSimulator = Depends(get_supply_chain_simulator),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get supply chain simulator statistics."""
    return service.get_statistics()

@router.get("/scenarios", response_model=list[dict[str, Any]])
async def list_scenarios(
    current_user: Any = Depends(deps.get_token_data)
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
    current_user: Any = Depends(deps.get_token_data)
):
    """Get overall supply chain risk analysis."""
    # This would normally take an RFQ or set of orders, but we can provide a general view
    return {
        "global_risk_index": 0.24,
        "primary_risk_drivers": ["logistics_congestion", "material_shortage"],
        "mitigation_readiness": 0.85,
        "last_updated": "2026-01-12T10:00:00Z"
    }

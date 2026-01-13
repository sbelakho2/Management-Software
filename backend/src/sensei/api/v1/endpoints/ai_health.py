"""
AI Health and Readiness Endpoints.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from sensei.api.deps import get_current_active_user
from sensei.services.ai.ai_readiness import get_ai_readiness_service, AIReadinessReport
from sensei.models.user import User

router = APIRouter()


@router.get("/status", response_model=AIReadinessReport)
async def get_ai_status(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get comprehensive status of all on-device AI components.
    """
    service = get_ai_readiness_service()
    return service.generate_report()


@router.post("/verify", response_model=Dict[str, Any])
async def verify_ai_performance(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Trigger a real-time performance verification of AI models.
    """
    # Only allow for admin or tech roles
    if not any(role.name in ["ADMIN", "OPS", "EXEC"] for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to run AI verification",
        )
    
    service = get_ai_readiness_service()
    return await service.verify_performance()

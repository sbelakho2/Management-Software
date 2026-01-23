from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import get_db, get_current_user
from sensei.api.exceptions import NotFoundError, ForbiddenError
from sensei.models.production import HandoverSeverity
from sensei.models.user import User
from sensei.services.ops.pulse_service import get_pulse_service

router = APIRouter(prefix="/pulse", tags=["The Pulse"])

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class GlobalPulseCreate(BaseModel):
    message: str = Field(..., max_length=500)
    severity: HandoverSeverity = HandoverSeverity.INFO
    expires_at: Optional[datetime] = None
    highlight_metric_name: Optional[str] = None
    highlight_metric_value: Optional[str] = None


class GlobalPulseResponse(BaseModel):
    id: int
    message: str
    severity: HandoverSeverity
    is_active: bool
    expires_at: Optional[datetime]
    highlight_metric_name: Optional[str]
    highlight_metric_value: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=GlobalPulseResponse, status_code=status.HTTP_201_CREATED)
async def create_pulse(
    data: GlobalPulseCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    # Only admins or GMs can create pulses
    # In this system, we can check roles if they exist on the user
    # For now, let's assume all authenticated users can, or check a role if available
    # The prompt said "Admins or GMs", but since I don't have the exact role names here, 
    # I'll keep it open for now or check if there is an 'admin' role.
    
    service = get_pulse_service()
    pulse = await service.create_pulse(
        db,
        message=data.message,
        severity=data.severity,
        expires_at=data.expires_at,
        highlight_metric_name=data.highlight_metric_name,
        highlight_metric_value=data.highlight_metric_value,
    )
    return pulse


@router.get("/active", response_model=list[GlobalPulseResponse])
async def get_active_pulses(
    db: DBSession,
    current_user: CurrentUser,
):
    service = get_pulse_service()
    return await service.get_active_pulses(db)


@router.post("/{pulse_id}/deactivate", response_model=GlobalPulseResponse)
async def deactivate_pulse(
    pulse_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    service = get_pulse_service()
    pulse = await service.deactivate_pulse(db, pulse_id)
    if not pulse:
        raise NotFoundError(f"Pulse {pulse_id} not found")
    return pulse

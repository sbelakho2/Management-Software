from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.deps import get_db, get_current_user
from sensei.api.exceptions import NotFoundError
from sensei.models.production import HandoverSeverity
from sensei.models.user import User
from sensei.services.production.handover_service import get_handover_service

AllowProductionModule = deps.require_role(
    "ops",
    "supervisor",
    "team_lead",
    "operator",
    "quality",
    "sales_engineer",
    "engineering",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    prefix="/production/handovers",
    tags=["Production Handovers"],
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "ops",
                    "supervisor",
                    "team_lead",
                    "operator",
                    "quality",
                    "sales_engineer",
                    "engineering",
                    "gm",
                    "exec",
                ]
            )
        )
    ],
)

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class HandoverNoteCreate(BaseModel):
    station_id: int
    work_order_id: Optional[int] = None
    severity: HandoverSeverity = HandoverSeverity.INFO
    safety: str = ""
    quality: str = ""
    delivery: str = ""
    cost: str = ""
    people: str = ""
    notes: str = ""


class HandoverNoteResponse(BaseModel):
    id: int
    station_id: int
    work_order_id: Optional[int]
    severity: HandoverSeverity
    safety: str
    quality: str
    delivery: str
    cost: str
    people: str
    notes: str
    acknowledged: bool
    acknowledged_by_id: Optional[UUID]
    acknowledged_at: Optional[datetime]
    created_at: datetime
    created_by_id: UUID

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=HandoverNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_handover(
    data: HandoverNoteCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    service = get_handover_service()
    note = await service.create_handover_note(
        db,
        station_id=data.station_id,
        created_by_id=current_user.id,
        work_order_id=data.work_order_id,
        severity=data.severity,
        safety=data.safety,
        quality=data.quality,
        delivery=data.delivery,
        cost=data.cost,
        people=data.people,
        notes=data.notes,
    )
    return note


@router.get("", response_model=list[HandoverNoteResponse])
async def list_handovers(
    db: DBSession,
    current_user: CurrentUser,
    station_id: Optional[int] = Query(None),
    include_acknowledged: bool = Query(True),
    limit: int = Query(50, le=100),
):
    service = get_handover_service()
    return await service.list_handover_notes(
        db,
        station_id=station_id,
        include_acknowledged=include_acknowledged,
        limit=limit,
    )


@router.post("/{handover_id}/acknowledge", response_model=HandoverNoteResponse)
async def acknowledge_handover(
    handover_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    service = get_handover_service()
    note = await service.acknowledge_handover_note(
        db,
        note_id=handover_id,
        acknowledged_by_id=current_user.id,
    )
    if not note:
        raise NotFoundError(f"Handover note {handover_id} not found")
    return note

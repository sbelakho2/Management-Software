from __future__ import annotations

from typing import Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.deps import RoleChecker
from sensei.api.exceptions import NotFoundError
from sensei.core.database import get_db_session
from sensei.services.core.site_service import SiteService

router = APIRouter(
    dependencies=[Depends(RoleChecker(["admin", "gm", "exec"]))],
)


class SiteCreate(BaseModel):
    site_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    status: Optional[str] = Field(default="active")
    timezone: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    default_currency: Optional[str] = None
    metadata_json: Optional[dict] = None


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    timezone: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    default_currency: Optional[str] = None
    metadata_json: Optional[dict] = None


@router.get("/sites", response_model=list[dict])
async def list_sites(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = SiteService(db)
    sites = await svc.list_sites()
    return [s.to_dict() for s in sites]


@router.post("/sites", response_model=dict)
async def create_site(
    payload: SiteCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = SiteService(db)
    site = await svc.create_site(
        site_code=payload.site_code,
        name=payload.name,
        status=payload.status or "active",
        timezone=payload.timezone,
        country=payload.country,
        address=payload.address,
        default_currency=payload.default_currency,
        metadata_json=payload.metadata_json,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(site)
    return site.to_dict()


@router.patch("/sites/{site_id}", response_model=dict)
async def update_site(
    site_id: UUID,
    payload: SiteUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = SiteService(db)
    site = await svc.get_site(site_id)
    if not site:
        raise NotFoundError("Site", str(site_id))
    update_payload = payload.model_dump(exclude_unset=True)
    update_payload["updated_by_id"] = getattr(current_user, "id", None)
    site = await svc.update_site(site, **update_payload)
    await db.commit()
    await db.refresh(site)
    return site.to_dict()

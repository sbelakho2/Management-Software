from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.utils import APIResponse, build_response
from sensei.models.strategic_v2 import SiteMaturityRecord
from sensei.services.core.factory_launchpad import (
    AsyncMaturityManager,
    FeatureModule,
    MATURITY_FEATURES,
    MaturityLevel,
)

router = APIRouter()

_async_maturity_manager = AsyncMaturityManager()


def _enabled_features_for_level(level: MaturityLevel) -> list[str]:
    enabled: set[FeatureModule] = set()
    for lvl in MaturityLevel:
        if lvl.value <= level.value:
            enabled.update(MATURITY_FEATURES.get(lvl, set()))
    return sorted([f.value for f in enabled])


def _site_record_to_api(site: SiteMaturityRecord) -> dict[str, Any]:
    metadata = dict(site.deployment_metadata or {})
    timezone = metadata.get("timezone", "UTC")
    try:
        current_level = MaturityLevel(site.current_level)
    except Exception:
        current_level = MaturityLevel.L0_STRATEGIC

    return {
        "id": str(site.id),
        "site_id": site.site_id,
        "site_name": site.site_name,
        "current_level": current_level.value,
        "target_level": site.target_level,
        "is_in_transition": site.is_in_transition,
        "timezone": timezone,
        "metadata": {k: v for k, v in metadata.items() if k != "timezone"},
        "created_at": site.created_at.isoformat() if getattr(site, "created_at", None) else None,
        "updated_at": site.updated_at.isoformat() if getattr(site, "updated_at", None) else None,
    }

class SiteRegisterRequest(BaseModel):
    site_id: str
    site_name: str
    initial_level: MaturityLevel = MaturityLevel.L0_STRATEGIC
    timezone: str = "UTC"
    metadata: dict[str, Any] = {}

class LevelUpdateRequest(BaseModel):
    target_level: MaturityLevel

@router.post("/sites", response_model=APIResponse)
async def register_site(
    request: SiteRegisterRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Register a new site for maturity tracking."""
    existing = (
        await db.execute(select(SiteMaturityRecord).where(SiteMaturityRecord.site_id == request.site_id))
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Site '{request.site_id}' already exists")

    site = await _async_maturity_manager.register_site(
        db,
        site_id=request.site_id,
        site_name=request.site_name,
        initial_level=request.initial_level,
        timezone=request.timezone,
        metadata=request.metadata,
    )
    return build_response(data=_site_record_to_api(site))

@router.get("/sites", response_model=APIResponse)
async def get_all_sites(db: DBSession, user: CurrentUser):
    """Get all sites tracked by the launchpad."""
    sites = (await db.execute(select(SiteMaturityRecord).order_by(SiteMaturityRecord.site_id))).scalars().all()
    return build_response(data=[_site_record_to_api(s) for s in sites])

@router.get("/sites/{site_id}", response_model=APIResponse)
async def get_site_details(site_id: str, db: DBSession, user: CurrentUser):
    """Get maturity details for a specific site."""
    site = (await db.execute(select(SiteMaturityRecord).where(SiteMaturityRecord.site_id == site_id))).scalar_one_or_none()
    if not site:
        raise NotFoundError("Site", site_id)

    current_level = MaturityLevel(site.current_level)
    return build_response(
        data={
            "config": _site_record_to_api(site),
            "enabled_features": _enabled_features_for_level(current_level),
            "current_level": current_level.value,
        }
    )

@router.post("/sites/{site_id}/level-up", response_model=APIResponse)
async def create_level_up_checklist(site_id: str, db: DBSession, user: CurrentUser):
    """Create a checklist for leveling up a site."""
    checklist = await _async_maturity_manager.create_level_up_checklist(db, site_id)
    if not checklist:
        raise ConflictError("Cannot create checklist. Site may be at max level or not found.")
    return build_response(data=checklist.to_dict())

@router.get("/sites/{site_id}/features/{feature}", response_model=APIResponse)
async def check_feature(site_id: str, feature: str, db: DBSession, user: CurrentUser):
    """Check if a specific feature is enabled for a site."""
    try:
        f_module = FeatureModule(feature)
    except ValueError:
        raise ConflictError(f"Invalid feature module: {feature}")

    site = (await db.execute(select(SiteMaturityRecord).where(SiteMaturityRecord.site_id == site_id))).scalar_one_or_none()
    if not site:
        raise NotFoundError("Site", site_id)

    current_level = MaturityLevel(site.current_level)
    enabled = f_module.value in _enabled_features_for_level(current_level)
    return build_response(data={"feature": feature, "enabled": enabled})

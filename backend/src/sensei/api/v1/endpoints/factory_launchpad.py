from __future__ import annotations

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.utils import APIResponse, build_response
from sensei.services.core.factory_launchpad import (
    MaturityManager,
    MaturityLevel,
    FeatureModule,
    SiteConfig,
)

router = APIRouter()

# Singleton for the orchestrator (in a real app this might be in deps or app.state)
_maturity_manager = MaturityManager()

# Pre-register some sites for demo/initial state if needed, 
# or rely on the service to handle persistence if it were connected to DB.
# For now, we wire the service as is.

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
    user: CurrentUser,
):
    """Register a new site for maturity tracking."""
    site = _maturity_manager.register_site(
        site_id=request.site_id,
        site_name=request.site_name,
        initial_level=request.initial_level,
        timezone=request.timezone,
        metadata=request.metadata,
    )
    return build_response(data=site.__dict__)

@router.get("/sites", response_model=APIResponse)
async def get_all_sites(user: CurrentUser):
    """Get all sites tracked by the launchpad."""
    sites = _maturity_manager.get_all_sites()
    return build_response(data=[s.__dict__ for s in sites])

@router.get("/sites/{site_id}", response_model=APIResponse)
async def get_site_details(site_id: str, user: CurrentUser):
    """Get maturity details for a specific site."""
    site = _maturity_manager.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    return build_response(data={
        "config": site.__dict__,
        "enabled_features": [f.value for f in site.get_enabled_features()],
        "current_level": site.current_level.value
    })

@router.post("/sites/{site_id}/level-up", response_model=APIResponse)
async def create_level_up_checklist(site_id: str, user: CurrentUser):
    """Create a checklist for leveling up a site."""
    checklist = _maturity_manager.create_level_up_checklist(site_id)
    if not checklist:
        raise HTTPException(
            status_code=400, 
            detail="Cannot create checklist. Site may be at max level or not found."
        )
    return build_response(data=checklist.__dict__)

@router.get("/sites/{site_id}/features/{feature}", response_model=APIResponse)
async def check_feature(site_id: str, feature: str, user: CurrentUser):
    """Check if a specific feature is enabled for a site."""
    try:
        f_module = FeatureModule(feature)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid feature module: {feature}")
    
    enabled = _maturity_manager.is_feature_enabled(site_id, f_module)
    return build_response(data={"feature": feature, "enabled": enabled})

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sensei.services.maintenance.maintenance_tpm import get_maintenance_service, MaintenanceService, Asset, MaintenanceWorkOrder
from sensei.api import deps

router = APIRouter()

@router.get("/stats", response_model=dict[str, Any])
async def get_maintenance_stats(
    service: MaintenanceService = Depends(get_maintenance_service),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get maintenance statistics."""
    return service.get_statistics()

@router.get("/assets", response_model=list[dict[str, Any]])
async def list_assets(
    service: MaintenanceService = Depends(get_maintenance_service),
    current_user: Any = Depends(deps.get_token_data)
):
    """List all assets."""
    assets = list(service._assets.values())
    return [vars(a) for a in assets]

@router.get("/assets/{asset_id}", response_model=dict[str, Any])
async def get_asset(
    asset_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get a specific asset."""
    asset = service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return vars(asset)

@router.get("/work-orders", response_model=list[dict[str, Any]])
async def list_work_orders(
    service: MaintenanceService = Depends(get_maintenance_service),
    current_user: Any = Depends(deps.get_token_data)
):
    """List all maintenance work orders."""
    work_orders = list(service._work_orders.values())
    return [vars(wo) for wo in work_orders]

@router.get("/overdue-pms", response_model=list[dict[str, Any]])
async def list_overdue_pms(
    service: MaintenanceService = Depends(get_maintenance_service),
    current_user: Any = Depends(deps.get_token_data)
):
    """List overdue preventive maintenance tasks."""
    overdue = service.get_overdue_pms()
    return overdue

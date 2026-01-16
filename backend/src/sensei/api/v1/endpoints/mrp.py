from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sensei.api import deps
from sensei.core.database import get_db_session
from sensei.models.mrp import BOMComponent, MRPDemand, MRPSuggestion, MRPRun
from sensei.services.production.mps_service import MPSService
from sensei.services.production.persistent_mrp import PersistentMRPService
from pydantic import BaseModel

router = APIRouter()


class MPSPlanSchema(BaseModel):
    name: str
    status: str = "draft"
    period_start: date
    period_end: date
    horizon_days: int = 30
    notes: str | None = None


class MPSLineSchema(BaseModel):
    product_id: int
    bucket_date: date
    quantity: float
    source_type: str | None = None

@router.get("/bom", response_model=List[dict])
async def list_bom_components(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all BOM components."""
    svc = PersistentMRPService(db)
    components = await svc.list_bom()
    return [c.to_dict() for c in components]

@router.get("/demands", response_model=List[dict])
async def list_mrp_demands(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all MRP demands."""
    svc = PersistentMRPService(db)
    demands = await svc.list_demands()
    return [d.to_dict() for d in demands]

@router.get("/suggestions", response_model=List[dict])
async def list_mrp_suggestions(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all MRP suggestions."""
    svc = PersistentMRPService(db)
    suggestions = await svc.list_suggestions()
    return [s.to_dict() for s in suggestions]

@router.post("/run", response_model=dict)
async def run_mrp(
    planning_horizon_days: int = 30,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """Execute MRP calculation."""
    svc = PersistentMRPService(db)
    run = await svc.run_mrp(planning_horizon_days, current_user.id)
    await db.commit()
    return run.to_dict()


@router.get("/mps/plans", response_model=List[dict])
async def list_mps_plans(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = MPSService(db)
    plans = await svc.list_plans()
    return [p.to_dict() for p in plans]


@router.post("/mps/plans", response_model=dict)
async def create_mps_plan(
    payload: MPSPlanSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = MPSService(db)
    plan = await svc.create_plan(
        name=payload.name,
        status=payload.status,
        period_start=payload.period_start,
        period_end=payload.period_end,
        horizon_days=payload.horizon_days,
        notes=payload.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(plan)
    return plan.to_dict()


@router.get("/mps/plans/{plan_id}/lines", response_model=List[dict])
async def list_mps_lines(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = MPSService(db)
    lines = await svc.list_lines(plan_id)
    return [l.to_dict() for l in lines]


@router.post("/mps/plans/{plan_id}/lines", response_model=dict)
async def create_mps_line(
    plan_id: UUID,
    payload: MPSLineSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = MPSService(db)
    line = await svc.add_line(
        plan_id=plan_id,
        product_id=payload.product_id,
        bucket_date=payload.bucket_date,
        quantity=payload.quantity,
        source_type=payload.source_type,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(line)
    return line.to_dict()

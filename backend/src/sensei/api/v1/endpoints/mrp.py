"""
MRP (Material Requirements Planning) Endpoints.

Provides endpoints for:
- BOM (Bill of Materials) management
- MRP Demands
- MRP Suggestions and their conversion to Purchase Requisitions
- MPS (Master Production Schedule) Plans
"""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import NotFoundError, ConflictError
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response, build_created_response, now_utc
from sensei.core.database import get_db_session
from sensei.models.mrp import BOMComponent, MRPDemand, MRPSuggestion, MRPRun
from sensei.models.accounts_payable import PurchaseRequisition, PRLine
from sensei.models.product import Product
from sensei.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from sensei.services.production.mps_service import MPSService
from sensei.services.production.persistent_mrp import PersistentMRPService
from sensei.services.core.common_thread import get_common_thread_service
from pydantic import BaseModel, Field

AllowMRPModule = deps.require_role(
    "ops",
    "supply_chain",
    "purchasing",
    "supervisor",
    "engineering",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "ops",
                    "supply_chain",
                    "purchasing",
                    "supervisor",
                    "engineering",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)
logger = logging.getLogger(__name__)


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


# =============================================================================
# MRP Suggestion Management & Conversion to PR
# =============================================================================


class SuggestionApprovalSchema(BaseModel):
    """Approve an MRP suggestion."""
    suggestion_ids: List[UUID] = Field(..., min_length=1)
    notes: Optional[str] = None


class SuggestionRejectionSchema(BaseModel):
    """Reject MRP suggestions."""
    suggestion_ids: List[UUID] = Field(..., min_length=1)
    rejection_reason: str = Field(..., min_length=1)


class SuggestionToPRSchema(BaseModel):
    """Convert MRP suggestions to Purchase Requisition."""
    suggestion_ids: List[UUID] = Field(..., min_length=1)
    supplier_id: Optional[UUID] = None  # Optional preferred supplier
    justification: str = "Auto-generated from MRP suggestions"


class PRConversionResult(BaseModel):
    """Result of MRP to PR conversion."""
    requisition_id: UUID
    pr_number: str
    line_count: int
    total_quantity: Decimal
    suggestion_ids: List[UUID]
    converted_at: datetime


class SuggestionToWOSchema(BaseModel):
    """Convert approved 'build' MRP suggestions to Work Orders."""
    suggestion_ids: List[UUID] = Field(..., min_length=1)
    priority: str = "normal"  # low, normal, high, urgent, critical
    notes: Optional[str] = None


class WOConversionResult(BaseModel):
    """Result of MRP to Work Order conversion."""
    work_order_ids: List[int]
    work_order_numbers: List[str]
    count: int
    total_quantity: Decimal
    suggestion_ids: List[UUID]
    converted_at: datetime


async def _generate_pr_number(db: AsyncSession) -> str:
    """Generate next PR number."""
    result = await db.execute(select(func.count(PurchaseRequisition.id)))
    count = result.scalar() or 0
    return f"PR-{datetime.now(timezone.utc).year}-{count + 1:05d}"


@router.get("/suggestions/pending", response_model=APIResponse[List[dict]])
async def list_pending_suggestions(
    db: DBSession,
    current_user: CurrentUser,
    requirement_type: Optional[str] = Query(None, enum=["buy", "build"]),
):
    """List pending MRP suggestions that need action."""
    stmt = select(MRPSuggestion).options(
        selectinload(MRPSuggestion.product)
    ).where(MRPSuggestion.status == "pending")
    
    if requirement_type:
        stmt = stmt.where(MRPSuggestion.requirement_type == requirement_type)
    
    stmt = stmt.order_by(MRPSuggestion.needed_date.asc())
    result = await db.execute(stmt)
    suggestions = result.scalars().all()
    
    return build_response([{
        **s.to_dict(),
        "product_name": s.product.name if s.product else None,
        "product_sku": s.product.part_number if s.product else None,
    } for s in suggestions])


@router.post("/suggestions/approve", response_model=APIResponse[List[dict]])
async def approve_suggestions(
    payload: SuggestionApprovalSchema,
    db: DBSession,
    current_user: CurrentUser,
):
    """Approve MRP suggestions."""
    result = await db.execute(
        select(MRPSuggestion)
        .where(and_(
            MRPSuggestion.id.in_(payload.suggestion_ids),
            MRPSuggestion.status == "pending"
        ))
    )
    suggestions = list(result.scalars().all())
    
    if len(suggestions) != len(payload.suggestion_ids):
        raise ConflictError("Some suggestions not found or not in pending status")
    
    approved = []
    for s in suggestions:
        s.status = "approved"
        s.approved_at = now_utc()
        s.approved_by_id = current_user.id
        if payload.notes:
            s.notes = payload.notes
        approved.append(s.to_dict())
    
    await db.commit()
    return build_response(approved)


@router.post("/suggestions/reject", response_model=APIResponse[List[dict]])
async def reject_suggestions(
    payload: SuggestionRejectionSchema,
    db: DBSession,
    current_user: CurrentUser,
):
    """Reject MRP suggestions."""
    result = await db.execute(
        select(MRPSuggestion)
        .where(and_(
            MRPSuggestion.id.in_(payload.suggestion_ids),
            MRPSuggestion.status == "pending"
        ))
    )
    suggestions = list(result.scalars().all())
    
    if len(suggestions) != len(payload.suggestion_ids):
        raise ConflictError("Some suggestions not found or not in pending status")
    
    rejected = []
    for s in suggestions:
        s.status = "rejected"
        s.rejection_reason = payload.rejection_reason
        rejected.append(s.to_dict())
    
    await db.commit()
    return build_response(rejected)


@router.post("/suggestions/convert-to-pr", response_model=APIResponse[PRConversionResult])
async def convert_suggestions_to_pr(
    payload: SuggestionToPRSchema,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Convert approved MRP 'buy' suggestions to a Purchase Requisition.
    
    This creates a new PR with line items for each approved suggestion.
    Only 'buy' type suggestions can be converted to PRs.
    """
    # Fetch approved 'buy' suggestions
    result = await db.execute(
        select(MRPSuggestion).options(
            selectinload(MRPSuggestion.product)
        ).where(and_(
            MRPSuggestion.id.in_(payload.suggestion_ids),
            MRPSuggestion.status == "approved",
            MRPSuggestion.requirement_type == "buy"
        ))
    )
    suggestions = list(result.scalars().all())
    
    if not suggestions:
        raise NotFoundError("No approved 'buy' suggestions found with the provided IDs")
    
    if len(suggestions) != len(payload.suggestion_ids):
        raise ConflictError(
            f"Found {len(suggestions)} approved buy suggestions, "
            f"but {len(payload.suggestion_ids)} IDs provided. "
            "Ensure all suggestions are approved and of type 'buy'."
        )
    
    # Generate PR number
    pr_number = await _generate_pr_number(db)
    
    # Create Purchase Requisition
    pr = PurchaseRequisition(
        pr_number=pr_number,
        status="draft",
        currency="USD",  # Default currency, could be configurable
        requested_by_id=current_user.id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        metadata_json={
            "justification": payload.justification,
            "source": "mrp_conversion",
            "suggestion_ids": [str(s) for s in payload.suggestion_ids],
        },
    )
    db.add(pr)
    await db.flush()
    
    # Create PR lines from suggestions
    total_qty = Decimal("0")
    for suggestion in suggestions:
        product = suggestion.product
        pr_line = PRLine(
            pr_id=pr.id,
            sku=product.sku if product else f"PROD-{suggestion.product_id}",
            description=f"{product.name if product else f'Product-{suggestion.product_id}'} - From MRP suggestion. Lead time: {suggestion.lead_time_days} days.",
            quantity=suggestion.quantity,
            unit_price=product.unit_cost if product else Decimal("0"),
        )
        db.add(pr_line)
        total_qty += suggestion.quantity
        
        # Mark suggestion as released
        suggestion.status = "released"
    
    await db.commit()
    
    return build_created_response(PRConversionResult(
        requisition_id=pr.id,
        pr_number=pr.pr_number,
        line_count=len(suggestions),
        total_quantity=total_qty,
        suggestion_ids=[s.id for s in suggestions],
        converted_at=now_utc(),
    ))


async def _generate_wo_number(db: AsyncSession) -> str:
    """Generate next work order number from MAX existing."""
    year = datetime.now(timezone.utc).year
    prefix = f"WO-{year}-"
    result = await db.execute(
        select(func.max(WorkOrder.work_order_number)).where(
            WorkOrder.work_order_number.like(f"{prefix}%")
        )
    )
    last = result.scalar()
    if last:
        try:
            seq = int(last.replace(prefix, "")) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


@router.post("/suggestions/convert-to-wo", response_model=APIResponse[WOConversionResult])
async def convert_suggestions_to_wo(
    payload: SuggestionToWOSchema,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Convert approved MRP 'build' suggestions to Work Orders.

    Each suggestion becomes a separate Work Order for the production floor.
    Only 'build' type suggestions that are approved can be converted.
    """
    # Fetch approved 'build' suggestions
    result = await db.execute(
        select(MRPSuggestion).options(
            selectinload(MRPSuggestion.product)
        ).where(and_(
            MRPSuggestion.id.in_(payload.suggestion_ids),
            MRPSuggestion.status == "approved",
            MRPSuggestion.requirement_type == "build",
        ))
    )
    suggestions = list(result.scalars().all())

    if not suggestions:
        raise NotFoundError("No approved 'build' suggestions found with the provided IDs")

    if len(suggestions) != len(payload.suggestion_ids):
        raise ConflictError(
            f"Found {len(suggestions)} approved build suggestions, "
            f"but {len(payload.suggestion_ids)} IDs provided. "
            "Ensure all suggestions are approved and of type 'build'."
        )

    # Map priority string to enum
    priority_map = {p.value: p for p in WorkOrderPriority}
    wo_priority = priority_map.get(payload.priority, WorkOrderPriority.NORMAL)

    work_orders: list[WorkOrder] = []
    total_qty = Decimal("0")

    for suggestion in suggestions:
        wo_number = await _generate_wo_number(db)
        wo = WorkOrder(
            work_order_number=wo_number,
            product_id=suggestion.product_id,
            quantity_ordered=suggestion.quantity,
            priority=wo_priority,
            status=WorkOrderStatus.DRAFT,
            notes=payload.notes or f"Auto-generated from MRP suggestion. Lead time: {suggestion.lead_time_days} days.",
            external_reference=f"MRP-{suggestion.id}",
        )
        if suggestion.needed_date:
            wo.scheduled_end = datetime.combine(
                suggestion.needed_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)

        db.add(wo)
        await db.flush()
        work_orders.append(wo)
        total_qty += suggestion.quantity

        # Mark suggestion as released
        suggestion.status = "released"

    # Bind lineage for the created work orders
    try:
        ct = get_common_thread_service()
        for wo in work_orders:
            await ct.bind(
                db,
                work_order_id=wo.id,
                created_by_id=current_user.id,
                source="mrp_build_conversion",
            )
    except Exception:
        logger.debug("common_thread bind skipped for WO conversion", exc_info=True)

    await db.commit()

    return build_created_response(WOConversionResult(
        work_order_ids=[wo.id for wo in work_orders],
        work_order_numbers=[wo.work_order_number for wo in work_orders],
        count=len(work_orders),
        total_quantity=total_qty,
        suggestion_ids=[s.id for s in suggestions],
        converted_at=now_utc(),
    ))


@router.get("/stats", response_model=APIResponse[dict])
async def get_mrp_stats(
    db: DBSession,
    current_user: CurrentUser,
):
    """Get MRP dashboard statistics."""
    # Count suggestions by status
    pending_count = await db.scalar(
        select(func.count(MRPSuggestion.id)).where(MRPSuggestion.status == "pending")
    )
    approved_count = await db.scalar(
        select(func.count(MRPSuggestion.id)).where(MRPSuggestion.status == "approved")
    )
    released_count = await db.scalar(
        select(func.count(MRPSuggestion.id)).where(MRPSuggestion.status == "released")
    )
    
    # Count by type
    buy_count = await db.scalar(
        select(func.count(MRPSuggestion.id)).where(
            and_(MRPSuggestion.requirement_type == "buy", MRPSuggestion.status == "pending")
        )
    )
    build_count = await db.scalar(
        select(func.count(MRPSuggestion.id)).where(
            and_(MRPSuggestion.requirement_type == "build", MRPSuggestion.status == "pending")
        )
    )
    
    # Get last run info
    last_run_result = await db.execute(
        select(MRPRun).order_by(MRPRun.run_at.desc()).limit(1)
    )
    last_run = last_run_result.scalar_one_or_none()
    
    return build_response({
        "suggestions": {
            "pending": pending_count or 0,
            "approved": approved_count or 0,
            "released": released_count or 0,
        },
        "pending_by_type": {
            "buy": buy_count or 0,
            "build": build_count or 0,
        },
        "last_run": {
            "run_at": last_run.run_at.isoformat() if last_run else None,
            "suggestions_count": last_run.suggestions_count if last_run else 0,
            "shortages_count": last_run.shortages_count if last_run else 0,
        } if last_run else None,
    })

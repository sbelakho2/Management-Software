from datetime import datetime
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.api import deps
from sensei.core.database import get_db_session
from sensei.services.maintenance.persistent_maintenance import PersistentMaintenanceService
from sensei.services.maintenance.lockout_tagout import LockoutTagoutService
from sensei.services.maintenance.tool_crib import ToolCribService
from sensei.services.maintenance.warranty_tracking import WarrantyTrackingService
from sensei.services.maintenance.maintenance_budget import MaintenanceBudgetService
from sensei.services.maintenance.field_returns import FieldReturnService

AllowMaintenanceModule = deps.require_role(
    "maintenance",
    "ops",
    "supervisor",
    "team_lead",
    "operator",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                ["maintenance", "ops", "supervisor", "team_lead", "operator"]
            )
        )
    ]
)

@router.get("/stats", response_model=dict[str, Any])
async def get_maintenance_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get maintenance statistics."""
    svc = PersistentMaintenanceService(db)
    return await svc.get_statistics()

@router.get("/assets", response_model=list[dict[str, Any]])
async def list_assets(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List all assets."""
    svc = PersistentMaintenanceService(db)
    assets = await svc.list_assets()
    return [a.to_dict() for a in assets]

@router.get("/assets/{asset_id}", response_model=dict[str, Any])
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get a specific asset."""
    svc = PersistentMaintenanceService(db)
    asset = await svc.get_asset(UUID(asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset.to_dict()

@router.get("/work-orders", response_model=list[dict[str, Any]])
async def list_work_orders(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List all maintenance work orders."""
    svc = PersistentMaintenanceService(db)
    work_orders = await svc.list_work_orders()
    return [wo.to_dict() for wo in work_orders]


@router.post("/work-orders/{work_order_id}/approval/request", response_model=dict[str, Any])
async def request_work_order_approval(
    work_order_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Request approval for a maintenance work order."""
    svc = PersistentMaintenanceService(db)
    wo = await svc.request_work_order_approval(work_order_id, UUID(current_user.sub))
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    await db.commit()
    await db.refresh(wo)
    return wo.to_dict()


@router.post("/work-orders/{work_order_id}/approval/approve", response_model=dict[str, Any])
async def approve_work_order(
    work_order_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Approve a maintenance work order."""
    svc = PersistentMaintenanceService(db)
    wo = await svc.approve_work_order(work_order_id, UUID(current_user.sub), payload.get("notes"))
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    await db.commit()
    await db.refresh(wo)
    return wo.to_dict()


@router.post("/work-orders/{work_order_id}/approval/reject", response_model=dict[str, Any])
async def reject_work_order(
    work_order_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Reject a maintenance work order."""
    svc = PersistentMaintenanceService(db)
    wo = await svc.reject_work_order(work_order_id, UUID(current_user.sub), payload.get("notes"))
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    await db.commit()
    await db.refresh(wo)
    return wo.to_dict()

@router.get("/overdue-pms", response_model=list[dict[str, Any]])
async def list_overdue_pms(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List overdue preventive maintenance tasks."""
    svc = PersistentMaintenanceService(db)
    overdue_schedules = await svc.list_overdue_pms()
    return [s.to_dict() for s in overdue_schedules]


@router.get("/pm-schedules", response_model=list[dict[str, Any]])
async def list_pm_schedules(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List PM schedules."""
    svc = PersistentMaintenanceService(db)
    schedules = await svc.list_pm_schedules()
    return [s.to_dict() for s in schedules]


@router.get("/pm-route", response_model=list[dict[str, Any]])
async def get_pm_route(
    days_ahead: int = 7,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get PM route plan for upcoming schedule window."""
    svc = PersistentMaintenanceService(db)
    return await svc.get_pm_route(days_ahead=days_ahead)


@router.get("/loto/procedures", response_model=list[dict[str, Any]])
async def list_loto_procedures(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List all LOTO procedures."""
    svc = LockoutTagoutService(db)
    procedures = await svc.list_procedures()
    result: list[dict[str, Any]] = []
    for proc in procedures:
        data = proc.to_dict()
        data["energy_sources"] = [src.to_dict() for src in proc.energy_sources]
        result.append(data)
    return result


@router.get("/loto/procedures/{procedure_id}", response_model=dict[str, Any])
async def get_loto_procedure(
    procedure_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get a specific LOTO procedure."""
    svc = LockoutTagoutService(db)
    procedure = await svc.get_procedure(procedure_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="LOTO procedure not found")
    data = procedure.to_dict()
    data["energy_sources"] = [src.to_dict() for src in procedure.energy_sources]
    return data


@router.post("/loto/procedures", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_loto_procedure(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Create a LOTO procedure."""
    svc = LockoutTagoutService(db)
    procedure = await svc.create_procedure(
        asset_id=UUID(payload["asset_id"]),
        title=payload["title"],
        description=payload.get("description"),
        status=payload.get("status", "active"),
        requires_verification=payload.get("requires_verification", True),
        version=payload.get("version", "v1"),
        energy_sources=payload.get("energy_sources"),
        created_by_id=UUID(current_user.sub),
    )
    await db.commit()
    await db.refresh(procedure)
    data = procedure.to_dict()
    data["energy_sources"] = [src.to_dict() for src in procedure.energy_sources]
    return data


@router.get("/loto/locks/active", response_model=list[dict[str, Any]])
async def list_active_locks(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List active LOTO locks."""
    svc = LockoutTagoutService(db)
    locks = await svc.list_active_locks()
    return [lock.to_dict() for lock in locks]


@router.post("/loto/locks", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_loto_lock(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Create (apply) a LOTO lock."""
    svc = LockoutTagoutService(db)
    lock = await svc.create_lock(
        procedure_id=UUID(payload["procedure_id"]),
        asset_id=UUID(payload["asset_id"]),
        work_order_id=UUID(payload["work_order_id"]) if payload.get("work_order_id") else None,
        lock_number=payload["lock_number"],
        reason=payload.get("reason"),
        applied_by_id=UUID(current_user.sub),
        verification_required=payload.get("verification_required", True),
    )
    await db.commit()
    await db.refresh(lock)
    return lock.to_dict()


@router.post("/loto/locks/{lock_id}/verify", response_model=dict[str, Any])
async def verify_loto_lock(
    lock_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Verify a LOTO lock."""
    svc = LockoutTagoutService(db)
    lock = await svc.verify_lock(
        lock_id=lock_id,
        verified_by_id=UUID(current_user.sub),
        verification_notes=payload.get("verification_notes"),
    )
    if not lock:
        raise HTTPException(status_code=404, detail="LOTO lock not found")
    await db.commit()
    await db.refresh(lock)
    return lock.to_dict()


@router.post("/loto/locks/{lock_id}/release", response_model=dict[str, Any])
async def release_loto_lock(
    lock_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Release a LOTO lock."""
    svc = LockoutTagoutService(db)
    lock = await svc.release_lock(
        lock_id=lock_id,
        released_by_id=UUID(current_user.sub),
        verification_notes=payload.get("verification_notes"),
    )
    if not lock:
        raise HTTPException(status_code=404, detail="LOTO lock not found")
    await db.commit()
    await db.refresh(lock)
    return lock.to_dict()


@router.get("/tools", response_model=list[dict[str, Any]])
async def list_tools(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List tool crib inventory."""
    svc = ToolCribService(db)
    tools = await svc.list_tools()
    return [tool.to_dict() for tool in tools]


@router.get("/tools/{tool_id}", response_model=dict[str, Any])
async def get_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get a specific tool."""
    svc = ToolCribService(db)
    tool = await svc.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool.to_dict()


@router.post("/tools", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_tool(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Create a tool crib item."""
    svc = ToolCribService(db)
    calibration_due_at = payload.get("calibration_due_at")
    if isinstance(calibration_due_at, str):
        calibration_due_at = datetime.fromisoformat(calibration_due_at)
    tool = await svc.create_tool(
        tool_number=payload["tool_number"],
        name=payload["name"],
        description=payload.get("description"),
        category=payload.get("category"),
        status=payload.get("status", "available"),
        location_id=payload.get("location_id"),
        quantity_on_hand=int(payload.get("quantity_on_hand", 1)),
        min_quantity=int(payload.get("min_quantity", 0)),
        life_limit_cycles=payload.get("life_limit_cycles"),
        life_used_cycles=int(payload.get("life_used_cycles", 0)),
        calibration_due_at=calibration_due_at,
        created_by_id=UUID(current_user.sub),
        updated_by_id=UUID(current_user.sub),
        owner_id=UUID(current_user.sub),
    )
    await db.commit()
    await db.refresh(tool)
    return tool.to_dict()


@router.get("/tools/checkouts/active", response_model=list[dict[str, Any]])
async def list_active_tool_checkouts(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List active tool checkouts."""
    svc = ToolCribService(db)
    checkouts = await svc.list_active_checkouts()
    return [checkout.to_dict() for checkout in checkouts]


@router.post("/tools/checkouts", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def checkout_tool(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Checkout a tool from the crib."""
    svc = ToolCribService(db)
    checkout = await svc.checkout_tool(
        tool_id=UUID(payload["tool_id"]),
        checked_out_by_id=UUID(current_user.sub),
        work_order_id=UUID(payload["work_order_id"]) if payload.get("work_order_id") else None,
        due_back_at=payload.get("due_back_at"),
        condition_out=payload.get("condition_out"),
        notes=payload.get("notes"),
    )
    if not checkout:
        raise HTTPException(status_code=409, detail="Tool not available for checkout")
    await db.commit()
    await db.refresh(checkout)
    return checkout.to_dict()


@router.post("/tools/checkouts/{checkout_id}/return", response_model=dict[str, Any])
async def return_tool(
    checkout_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Return a checked out tool."""
    svc = ToolCribService(db)
    checkout = await svc.return_tool(
        checkout_id=checkout_id,
        returned_by_id=UUID(current_user.sub),
        condition_in=payload.get("condition_in"),
        notes=payload.get("notes"),
    )
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found or already returned")
    await db.commit()
    await db.refresh(checkout)
    return checkout.to_dict()


@router.get("/warranties", response_model=list[dict[str, Any]])
async def list_warranties(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List asset warranties."""
    svc = WarrantyTrackingService(db)
    warranties = await svc.list_warranties()
    result: list[dict[str, Any]] = []
    for warranty in warranties:
        data = warranty.to_dict()
        data["claims"] = [claim.to_dict() for claim in warranty.claims]
        result.append(data)
    return result


@router.get("/warranties/{warranty_id}", response_model=dict[str, Any])
async def get_warranty(
    warranty_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Get a specific asset warranty."""
    svc = WarrantyTrackingService(db)
    warranty = await svc.get_warranty(warranty_id)
    if not warranty:
        raise HTTPException(status_code=404, detail="Warranty not found")
    data = warranty.to_dict()
    data["claims"] = [claim.to_dict() for claim in warranty.claims]
    return data


@router.post("/warranties", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_warranty(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Create a warranty for an asset."""
    svc = WarrantyTrackingService(db)
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)

    warranty = await svc.create_warranty(
        asset_id=UUID(payload["asset_id"]),
        warranty_type=payload["warranty_type"],
        provider_name=payload.get("provider_name"),
        vendor_id=UUID(payload["vendor_id"]) if payload.get("vendor_id") else None,
        start_date=start_date,
        end_date=end_date,
        coverage_type=payload.get("coverage_type", "parts_labor"),
        status=payload.get("status", "active"),
        terms=payload.get("terms"),
        claim_contact=payload.get("claim_contact"),
        created_by_id=UUID(current_user.sub),
        updated_by_id=UUID(current_user.sub),
        owner_id=UUID(current_user.sub),
    )
    await db.commit()
    await db.refresh(warranty)
    data = warranty.to_dict()
    data["claims"] = []
    return data


@router.post("/warranties/{warranty_id}/claims", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def file_warranty_claim(
    warranty_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """File a warranty claim."""
    svc = WarrantyTrackingService(db)
    claim = await svc.file_claim(
        warranty_id=warranty_id,
        asset_id=UUID(payload["asset_id"]),
        work_order_id=UUID(payload["work_order_id"]) if payload.get("work_order_id") else None,
        claim_number=payload["claim_number"],
        claim_amount=payload.get("claim_amount"),
        notes=payload.get("notes"),
        submitted_by_id=UUID(current_user.sub),
    )
    await db.commit()
    await db.refresh(claim)
    return claim.to_dict()


@router.post("/warranties/claims/{claim_id}/resolve", response_model=dict[str, Any])
async def resolve_warranty_claim(
    claim_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Resolve a warranty claim."""
    svc = WarrantyTrackingService(db)
    claim = await svc.resolve_claim(
        claim_id=claim_id,
        status=payload.get("status", "closed"),
        approved_amount=payload.get("approved_amount"),
        notes=payload.get("notes"),
        resolved_by_id=UUID(current_user.sub),
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Warranty claim not found")
    await db.commit()
    await db.refresh(claim)
    return claim.to_dict()


@router.get("/field-returns", response_model=list[dict[str, Any]])
async def list_field_returns(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List field returns for warranty analysis."""
    svc = FieldReturnService(db)
    returns = await svc.list_returns()
    return [r.to_dict() for r in returns]


@router.post("/field-returns", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_field_return(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Create a field return record."""
    svc = FieldReturnService(db)
    failure_date = payload.get("failure_date")
    received_at = payload.get("received_at")
    if isinstance(failure_date, str):
        failure_date = datetime.fromisoformat(failure_date)
    if isinstance(received_at, str):
        received_at = datetime.fromisoformat(received_at)

    field_return = await svc.create_return(
        asset_id=UUID(payload["asset_id"]),
        warranty_id=UUID(payload["warranty_id"]) if payload.get("warranty_id") else None,
        claim_id=UUID(payload["claim_id"]) if payload.get("claim_id") else None,
        customer_id=UUID(payload["customer_id"]) if payload.get("customer_id") else None,
        return_number=payload["return_number"],
        status=payload.get("status", "received"),
        failure_date=failure_date,
        received_at=received_at or datetime.utcnow(),
        defect_code=payload.get("defect_code"),
        failure_mode=payload.get("failure_mode"),
        root_cause=payload.get("root_cause"),
        corrective_action=payload.get("corrective_action"),
        cost_impact=payload.get("cost_impact"),
        notes=payload.get("notes"),
        created_by_id=UUID(current_user.sub),
        updated_by_id=UUID(current_user.sub),
        owner_id=UUID(current_user.sub),
    )
    await db.commit()
    await db.refresh(field_return)
    return field_return.to_dict()


@router.patch("/field-returns/{return_id}", response_model=dict[str, Any])
async def update_field_return(
    return_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Update a field return record."""
    svc = FieldReturnService(db)
    field_return = await svc.get_return(return_id)
    if not field_return:
        raise HTTPException(status_code=404, detail="Field return not found")
    update_payload = dict(payload)
    if "failure_date" in update_payload and isinstance(update_payload["failure_date"], str):
        update_payload["failure_date"] = datetime.fromisoformat(update_payload["failure_date"])
    if "received_at" in update_payload and isinstance(update_payload["received_at"], str):
        update_payload["received_at"] = datetime.fromisoformat(update_payload["received_at"])
    update_payload["updated_by_id"] = UUID(current_user.sub)
    update_payload["updated_at"] = datetime.utcnow()
    field_return = await svc.update_return(field_return, **update_payload)
    await db.commit()
    await db.refresh(field_return)
    return field_return.to_dict()


@router.post("/field-returns/{return_id}/close", response_model=dict[str, Any])
async def close_field_return(
    return_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Close a field return record."""
    svc = FieldReturnService(db)
    field_return = await svc.get_return(return_id)
    if not field_return:
        raise HTTPException(status_code=404, detail="Field return not found")
    field_return.updated_by_id = UUID(current_user.sub)
    field_return.updated_at = datetime.utcnow()
    field_return = await svc.close_return(field_return)
    await db.commit()
    await db.refresh(field_return)
    return field_return.to_dict()


@router.get("/budgets", response_model=list[dict[str, Any]])
async def list_maintenance_budgets(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """List maintenance budgets."""
    svc = MaintenanceBudgetService(db)
    budgets = await svc.list_budgets()
    return [budget.to_dict() for budget in budgets]


@router.post("/budgets", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_maintenance_budget(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Create a maintenance budget."""
    svc = MaintenanceBudgetService(db)
    period_start = payload.get("period_start")
    period_end = payload.get("period_end")
    if isinstance(period_start, str):
        period_start = datetime.fromisoformat(period_start)
    if isinstance(period_end, str):
        period_end = datetime.fromisoformat(period_end)

    budget = await svc.create_budget(
        name=payload["name"],
        period_start=period_start,
        period_end=period_end,
        budget_amount=payload["budget_amount"],
        actual_amount=payload.get("actual_amount", 0),
        variance_amount=payload.get("variance_amount", 0),
        currency=payload.get("currency", "MAD"),
        notes=payload.get("notes"),
        created_by_id=UUID(current_user.sub),
        updated_by_id=UUID(current_user.sub),
        owner_id=UUID(current_user.sub),
    )
    await db.commit()
    await db.refresh(budget)
    return budget.to_dict()


@router.post("/budgets/{budget_id}/actuals", response_model=dict[str, Any])
async def update_budget_actuals(
    budget_id: UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_token_data)
):
    """Update maintenance budget actuals."""
    svc = MaintenanceBudgetService(db)
    budget = await svc.update_actuals(
        budget_id,
        payload["actual_amount"],
        UUID(current_user.sub),
    )
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.commit()
    await db.refresh(budget)
    return budget.to_dict()

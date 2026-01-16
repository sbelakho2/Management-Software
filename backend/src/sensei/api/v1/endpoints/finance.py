from datetime import date
from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sensei.api import deps
from sensei.api.schemas import APIResponse
from sensei.core.database import get_db_session
from sensei.models.finance import GLAccount, JournalEntry, AccountingPeriod, CurrencySetting, FXRate
from sensei.services.finance.currency_settings import CurrencySettingsService
from sensei.services.finance.cost_rollup_service import CostRollupService
from sensei.services.finance.tax_service import TaxService
from sensei.services.finance import get_accounting_service
from pydantic import BaseModel

router = APIRouter()

class GLAccountSchema(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    is_active: bool = True


class CurrencySettingsSchema(BaseModel):
    base_currency: str
    reporting_currency: str | None = None
    allowed_currencies: list[str] | None = None
    fx_source: str | None = None
    auto_update_rates: bool = False


class FXRateSchema(BaseModel):
    as_of: date
    from_currency: str
    to_currency: str
    rate: float


class StandardCostSchema(BaseModel):
    sku: str
    currency: str
    effective_date: date
    material_unit_cost: float
    labor_unit_cost: float
    overhead_unit_cost: float


class CostRollupSchema(BaseModel):
    work_order_id: str
    finished_sku: str
    currency: str
    planned_quantity: float
    completed_quantity: float
    actual_material_cost: float
    actual_labor_cost: float
    actual_overhead_cost: float
    relieved_actual_cost: float
    variance_material: float
    variance_labor: float
    variance_overhead: float
    variance_total: float


class TaxJurisdictionSchema(BaseModel):
    code: str
    name: str
    country: str
    region: str | None = None
    status: str = "active"


class TaxRateEntrySchema(BaseModel):
    jurisdiction_id: UUID
    tax_type: str
    rate: float
    effective_date: date
    status: str = "active"


class TaxTransactionSchema(BaseModel):
    jurisdiction_id: UUID
    tax_rate_id: UUID
    reference_type: str
    reference_id: str
    taxable_amount: float
    tax_amount: float
    currency: str
    status: str = "pending"

@router.get("/accounts", response_model=List[dict])
async def list_gl_accounts(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all General Ledger accounts."""
    svc = get_accounting_service(db)
    accounts = await svc.list_accounts()
    return [a.to_dict() for a in accounts]

@router.post("/accounts", response_model=dict)
async def create_gl_account(
    account_in: GLAccountSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """Create a new GL account."""
    svc = get_accounting_service(db)
    account = await svc.upsert_account(
        code=account_in.account_code,
        name=account_in.account_name,
        account_type=account_in.account_type,
        is_active=account_in.is_active
    )
    await db.commit()
    return account.to_dict()

@router.get("/trial-balance", response_model=List[dict])
async def get_trial_balance(
    as_of: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """Get the trial balance as of a specific date."""
    svc = get_accounting_service(db)
    return await svc.get_trial_balance(as_of)

@router.get("/journal-entries", response_model=List[dict])
async def list_journal_entries(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all journal entries."""
    result = await db.execute(select(JournalEntry))
    entries = result.scalars().all()
    return [e.to_dict() for e in entries]

@router.get("/periods", response_model=List[dict])
async def list_accounting_periods(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all accounting periods."""
    result = await db.execute(select(AccountingPeriod))
    periods = result.scalars().all()
    return [p.to_dict() for p in periods]


@router.get("/currency-settings", response_model=dict)
async def get_currency_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CurrencySettingsService(db)
    settings = await svc.get_settings()
    return settings.to_dict()


@router.post("/currency-settings", response_model=dict)
async def update_currency_settings(
    payload: CurrencySettingsSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CurrencySettingsService(db)
    settings = await svc.get_settings()
    settings = await svc.update_settings(
        settings,
        base_currency=payload.base_currency,
        reporting_currency=payload.reporting_currency,
        allowed_currencies=payload.allowed_currencies,
        fx_source=payload.fx_source,
        auto_update_rates=payload.auto_update_rates,
        updated_by_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(settings)
    return settings.to_dict()


@router.get("/fx-rates", response_model=List[dict])
async def list_fx_rates(
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CurrencySettingsService(db)
    rates = await svc.list_fx_rates(as_of=as_of)
    return [r.to_dict() for r in rates]


@router.post("/fx-rates", response_model=dict)
async def upsert_fx_rate(
    payload: FXRateSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CurrencySettingsService(db)
    rate = await svc.upsert_fx_rate(
        as_of=payload.as_of,
        from_currency=payload.from_currency,
        to_currency=payload.to_currency,
        rate=payload.rate,
    )
    await db.commit()
    await db.refresh(rate)
    return rate.to_dict()


@router.get("/costing/standard-costs", response_model=List[dict])
async def list_standard_costs(
    sku: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CostRollupService(db)
    records = await svc.list_standard_costs(sku=sku)
    return [r.to_dict() for r in records]


@router.post("/costing/standard-costs", response_model=dict)
async def upsert_standard_cost(
    payload: StandardCostSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CostRollupService(db)
    record = await svc.upsert_standard_cost(
        sku=payload.sku,
        currency=payload.currency,
        effective_date=payload.effective_date,
        material_unit_cost=payload.material_unit_cost,
        labor_unit_cost=payload.labor_unit_cost,
        overhead_unit_cost=payload.overhead_unit_cost,
    )
    await db.commit()
    await db.refresh(record)
    return record.to_dict()


@router.get("/costing/rollups", response_model=List[dict])
async def list_cost_rollups(
    work_order_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CostRollupService(db)
    rollups = await svc.list_rollups(work_order_id=work_order_id)
    return [r.to_dict() for r in rollups]


@router.post("/costing/rollups", response_model=dict)
async def create_cost_rollup(
    payload: CostRollupSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = CostRollupService(db)
    rollup = await svc.create_rollup(
        work_order_id=payload.work_order_id,
        finished_sku=payload.finished_sku,
        currency=payload.currency,
        planned_quantity=payload.planned_quantity,
        completed_quantity=payload.completed_quantity,
        actual_material_cost=payload.actual_material_cost,
        actual_labor_cost=payload.actual_labor_cost,
        actual_overhead_cost=payload.actual_overhead_cost,
        relieved_actual_cost=payload.relieved_actual_cost,
        variance_material=payload.variance_material,
        variance_labor=payload.variance_labor,
        variance_overhead=payload.variance_overhead,
        variance_total=payload.variance_total,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(rollup)
    return rollup.to_dict()


@router.get("/tax/jurisdictions", response_model=List[dict])
async def list_tax_jurisdictions(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = TaxService(db)
    jurisdictions = await svc.list_jurisdictions()
    return [j.to_dict() for j in jurisdictions]


@router.post("/tax/jurisdictions", response_model=dict)
async def create_tax_jurisdiction(
    payload: TaxJurisdictionSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = TaxService(db)
    jurisdiction = await svc.create_jurisdiction(
        code=payload.code,
        name=payload.name,
        country=payload.country,
        region=payload.region,
        status=payload.status,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(jurisdiction)
    return jurisdiction.to_dict()


@router.get("/tax/rates", response_model=List[dict])
async def list_tax_rates(
    jurisdiction_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = TaxService(db)
    rates = await svc.list_rates(jurisdiction_id=jurisdiction_id)
    return [r.to_dict() for r in rates]


@router.post("/tax/rates", response_model=dict)
async def create_tax_rate(
    payload: TaxRateEntrySchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = TaxService(db)
    rate = await svc.create_rate(
        jurisdiction_id=payload.jurisdiction_id,
        tax_type=payload.tax_type,
        rate=payload.rate,
        effective_date=payload.effective_date,
        status=payload.status,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(rate)
    return rate.to_dict()


@router.get("/tax/transactions", response_model=List[dict])
async def list_tax_transactions(
    reference_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = TaxService(db)
    transactions = await svc.list_transactions(reference_id=reference_id)
    return [t.to_dict() for t in transactions]


@router.post("/tax/transactions", response_model=dict)
async def create_tax_transaction(
    payload: TaxTransactionSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    svc = TaxService(db)
    transaction = await svc.create_transaction(
        jurisdiction_id=payload.jurisdiction_id,
        tax_rate_id=payload.tax_rate_id,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        taxable_amount=payload.taxable_amount,
        tax_amount=payload.tax_amount,
        currency=payload.currency,
        status=payload.status,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(transaction)
    return transaction.to_dict()

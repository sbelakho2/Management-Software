from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from sensei.api import deps
from sensei.api.schemas import APIResponse
from sensei.core.config import settings
from sensei.core.database import get_db_session
from sensei.models.finance import (
    GLAccount, JournalEntry, JournalLine, AccountingPeriod,
    CurrencySetting, FXRate, Currency, PaymentTerm, BankAccount, BankTransaction,
)
from sensei.models.user import User
from sensei.services.finance.currency_settings import CurrencySettingsService
from sensei.services.finance.cost_rollup_service import CostRollupService
from sensei.services.finance.tax_service import TaxService
from sensei.services.finance import get_accounting_service
from pydantic import BaseModel

AllowFinanceModule = deps.require_role("finance", "accountant", "gm", "exec")  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[Depends(deps.RoleChecker(["finance", "accountant", "gm", "exec"]))]
)

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


# --- Schemas for currencies, payment terms, bank accounts, bank transactions ---

class CurrencySchema(BaseModel):
    code: str
    name: str
    symbol: str | None = None
    decimal_places: int = 2
    is_active: bool = True


class CurrencyUpdateSchema(BaseModel):
    name: str | None = None
    symbol: str | None = None
    decimal_places: int | None = None
    is_active: bool | None = None


class PaymentTermSchema(BaseModel):
    code: str
    name: str
    days_due: int = 30
    discount_percent: float = 0
    discount_days: int = 0
    description: str | None = None
    is_active: bool = True


class PaymentTermUpdateSchema(BaseModel):
    name: str | None = None
    days_due: int | None = None
    discount_percent: float | None = None
    discount_days: int | None = None
    description: str | None = None
    is_active: bool | None = None


class BankAccountSchema(BaseModel):
    account_name: str
    account_number: str
    bank_name: str
    bank_code: str | None = None
    iban: str | None = None
    currency: str = "USD"
    account_type: str = "checking"
    site_id: UUID | None = None
    gl_account_id: UUID | None = None
    is_active: bool = True


class BankAccountUpdateSchema(BaseModel):
    account_name: str | None = None
    bank_name: str | None = None
    bank_code: str | None = None
    iban: str | None = None
    currency: str | None = None
    account_type: str | None = None
    is_active: bool | None = None


class BankTransactionSchema(BaseModel):
    bank_account_id: UUID
    transaction_date: date
    value_date: date | None = None
    transaction_type: str
    reference: str | None = None
    description: str
    amount: float
    currency: str = "USD"
    status: str = "posted"
    source_type: str | None = None
    source_id: UUID | None = None

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
    as_of: date = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
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
        rate=Decimal(str(payload.rate)),
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
        material_unit_cost=Decimal(str(payload.material_unit_cost)),
        labor_unit_cost=Decimal(str(payload.labor_unit_cost)),
        overhead_unit_cost=Decimal(str(payload.overhead_unit_cost)),
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


# Dashboard Stats Endpoint
@router.get("/dashboard-stats", response_model=dict)
async def get_finance_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Get finance dashboard statistics.

    This endpoint must not return mocked values. When business source data isn't
    available yet, it derives what it can from persisted GL/journal records and
    returns zero/empty-derived metrics.
    """

    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    prev_month_end = month_start.fromordinal(month_start.toordinal() - 1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_period_end = min(prev_month_end, prev_month_start.fromordinal(prev_month_start.toordinal() + today.day - 1))

    total_accounts = (
        await db.execute(select(func.count(GLAccount.id)))
    ).scalar_one() or 0
    active_accounts = (
        await db.execute(select(func.count(GLAccount.id)).where(GLAccount.is_active.is_(True)))
    ).scalar_one() or 0
    total_entries = (
        await db.execute(select(func.count(JournalEntry.id)))
    ).scalar_one() or 0

    revenue_mtd = (
        await db.execute(
            select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0))
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .join(GLAccount, JournalLine.account_id == GLAccount.id)
            .where(
                GLAccount.account_type == "revenue",
                JournalEntry.status == "posted",
                JournalEntry.entry_date >= month_start,
                JournalEntry.entry_date <= today,
            )
        )
    ).scalar_one()
    revenue_mtd = Decimal(revenue_mtd or 0)

    revenue_prev = (
        await db.execute(
            select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0))
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .join(GLAccount, JournalLine.account_id == GLAccount.id)
            .where(
                GLAccount.account_type == "revenue",
                JournalEntry.status == "posted",
                JournalEntry.entry_date >= prev_month_start,
                JournalEntry.entry_date <= prev_period_end,
            )
        )
    ).scalar_one()
    revenue_prev = Decimal(revenue_prev or 0)

    opex_mtd = (
        await db.execute(
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .join(GLAccount, JournalLine.account_id == GLAccount.id)
            .where(
                GLAccount.account_type == "expense",
                JournalEntry.status == "posted",
                JournalEntry.entry_date >= month_start,
                JournalEntry.entry_date <= today,
            )
        )
    ).scalar_one()
    opex_mtd = Decimal(opex_mtd or 0)

    opex_prev = (
        await db.execute(
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .join(GLAccount, JournalLine.account_id == GLAccount.id)
            .where(
                GLAccount.account_type == "expense",
                JournalEntry.status == "posted",
                JournalEntry.entry_date >= prev_month_start,
                JournalEntry.entry_date <= prev_period_end,
            )
        )
    ).scalar_one()
    opex_prev = Decimal(opex_prev or 0)

    liquidity_reserve = (
        await db.execute(
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .join(GLAccount, JournalLine.account_id == GLAccount.id)
            .where(
                GLAccount.account_type == "asset",
                JournalEntry.status == "posted",
                JournalEntry.entry_date <= today,
            )
        )
    ).scalar_one()
    liquidity_reserve = Decimal(liquidity_reserve or 0)

    pending_approvals = (
        await db.execute(select(func.count(JournalEntry.id)).where(JournalEntry.status == "draft"))
    ).scalar_one() or 0

    revenue_change = 0.0
    if revenue_prev != 0:
        revenue_change = float(((revenue_mtd - revenue_prev) / revenue_prev) * Decimal("100"))

    gross_margin = 0.0
    if revenue_mtd != 0:
        gross_margin = float(((revenue_mtd - opex_mtd) / revenue_mtd) * Decimal("100"))

    prev_margin = 0.0
    if revenue_prev != 0:
        prev_margin = float(((revenue_prev - opex_prev) / revenue_prev) * Decimal("100"))

    margin_change = gross_margin - prev_margin

    liquidity_status = "optimal" if liquidity_reserve > 0 else "low"

    return {
        "revenue_mtd": float(revenue_mtd),
        "revenue_change": round(revenue_change, 2),
        "gross_margin": round(gross_margin, 2),
        "margin_change": round(margin_change, 2),
        "opex": float(opex_mtd),
        "budget_utilization": 0,
        "liquidity_reserve": float(liquidity_reserve),
        "liquidity_status": liquidity_status,
        "total_accounts": int(total_accounts),
        "active_accounts": int(active_accounts),
        "total_journal_entries": int(total_entries),
        "pending_approvals": int(pending_approvals),
        "overdue_invoices": 0,
        "overdue_amount": 0.0,
    }


@router.get("/revenue-by-product", response_model=list)
async def get_revenue_by_product(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Get revenue breakdown.

    Uses revenue GL accounts as a proxy when product-level sales data isn't available.
    """
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)

    result = await db.execute(
        select(
            GLAccount.account_name,
            func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0).label("revenue"),
        )
        .select_from(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .join(GLAccount, JournalLine.account_id == GLAccount.id)
        .where(
            GLAccount.account_type == "revenue",
            JournalEntry.status == "posted",
            JournalEntry.entry_date >= month_start,
            JournalEntry.entry_date <= today,
        )
        .group_by(GLAccount.account_name)
        .order_by(func.sum(JournalLine.credit - JournalLine.debit).desc())
    )

    rows = [(name, Decimal(amount or 0)) for (name, amount) in result.all()]
    total = sum((amt for _, amt in rows), Decimal("0"))

    response: list[dict] = []
    for name, amount in rows:
        pct = float((amount / total) * Decimal("100")) if total != 0 else 0.0
        response.append({"name": name, "revenue": float(amount), "percentage": round(pct, 2)})
    return response


@router.get("/expense-breakdown", response_model=list)
async def get_expense_breakdown(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Get expense breakdown.

    Uses expense GL accounts as categories when a richer taxonomy isn't configured.
    """
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)

    result = await db.execute(
        select(
            GLAccount.account_name,
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0).label("amount"),
        )
        .select_from(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .join(GLAccount, JournalLine.account_id == GLAccount.id)
        .where(
            GLAccount.account_type == "expense",
            JournalEntry.status == "posted",
            JournalEntry.entry_date >= month_start,
            JournalEntry.entry_date <= today,
        )
        .group_by(GLAccount.account_name)
        .order_by(func.sum(JournalLine.debit - JournalLine.credit).desc())
    )

    rows = [(name, Decimal(amount or 0)) for (name, amount) in result.all()]
    total = sum((amt for _, amt in rows), Decimal("0"))

    response: list[dict] = []
    for name, amount in rows:
        pct = float((amount / total) * Decimal("100")) if total != 0 else 0.0
        response.append(
            {
                "category": name,
                "amount": float(amount),
                "percentage": round(pct, 2),
                "status": "normal",
            }
        )
    return response


@router.get("/pending-approvals", response_model=list)
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Get list of pending financial approvals.

    Currently maps to draft Journal Entries.
    """
    result = await db.execute(
        select(
            JournalEntry.id,
            JournalEntry.description,
            JournalEntry.entry_date,
            User.first_name,
            User.last_name,
            func.coalesce(func.sum(JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("total_credit"),
        )
        .select_from(JournalEntry)
        .outerjoin(User, User.id == JournalEntry.created_by_id)
        .outerjoin(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(JournalEntry.status == "draft")
        .group_by(JournalEntry.id, User.first_name, User.last_name)
        .order_by(JournalEntry.entry_date.desc())
        .limit(settings.AUDIT_LOG_QUERY_LIMIT)
    )

    approvals: list[dict] = []
    for (
        entry_id,
        description,
        entry_date,
        first_name,
        last_name,
        total_debit,
        total_credit,
    ) in result.all():
        requestor = (f"{first_name} {last_name}".strip() if first_name and last_name else "Unknown")
        debit_amt = Decimal(total_debit or 0)
        credit_amt = Decimal(total_credit or 0)
        amount = float(max(debit_amt, credit_amt))
        approvals.append(
            {
                "id": str(entry_id),
                "type": "Journal Entry",
                "description": description,
                "amount": amount,
                "requestor": requestor,
                "submitted": entry_date.isoformat(),
            }
        )

    return approvals


# =============================================================================
# Currency CRUD (C1 fix — frontend calls these endpoints)
# =============================================================================


@router.get("/currencies", response_model=List[dict])
async def list_currencies(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """List all currencies."""
    result = await db.execute(select(Currency).order_by(Currency.code))
    return [c.to_dict() for c in result.scalars().all()]


@router.post("/currencies", response_model=dict, status_code=201)
async def create_currency(
    payload: CurrencySchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Create a new currency."""
    currency = Currency(
        code=payload.code.upper(),
        name=payload.name,
        symbol=payload.symbol,
        decimal_places=payload.decimal_places,
        is_active=payload.is_active,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    db.add(currency)
    await db.commit()
    await db.refresh(currency)
    return currency.to_dict()


@router.patch("/currencies/{currency_id}", response_model=dict)
async def update_currency(
    currency_id: UUID,
    payload: CurrencyUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Update an existing currency."""
    result = await db.execute(select(Currency).where(Currency.id == currency_id))
    currency = result.scalar_one_or_none()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(currency, field, value)
    currency.updated_by_id = getattr(current_user, "id", None)
    await db.commit()
    await db.refresh(currency)
    return currency.to_dict()


# =============================================================================
# Payment Term CRUD
# =============================================================================


@router.get("/payment-terms", response_model=List[dict])
async def list_payment_terms(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """List all payment terms."""
    result = await db.execute(select(PaymentTerm).order_by(PaymentTerm.code))
    return [pt.to_dict() for pt in result.scalars().all()]


@router.post("/payment-terms", response_model=dict, status_code=201)
async def create_payment_term(
    payload: PaymentTermSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Create a new payment term."""
    pt = PaymentTerm(
        code=payload.code,
        name=payload.name,
        days_due=payload.days_due,
        discount_percent=Decimal(str(payload.discount_percent)),
        discount_days=payload.discount_days,
        description=payload.description,
        is_active=payload.is_active,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    db.add(pt)
    await db.commit()
    await db.refresh(pt)
    return pt.to_dict()


@router.patch("/payment-terms/{term_id}", response_model=dict)
async def update_payment_term(
    term_id: UUID,
    payload: PaymentTermUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Update an existing payment term."""
    result = await db.execute(select(PaymentTerm).where(PaymentTerm.id == term_id))
    pt = result.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Payment term not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "discount_percent" in update_data:
        update_data["discount_percent"] = Decimal(str(update_data["discount_percent"]))
    for field, value in update_data.items():
        setattr(pt, field, value)
    pt.updated_by_id = getattr(current_user, "id", None)
    await db.commit()
    await db.refresh(pt)
    return pt.to_dict()


# =============================================================================
# Bank Account CRUD
# =============================================================================


@router.get("/bank-accounts", response_model=List[dict])
async def list_bank_accounts(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """List all bank accounts."""
    result = await db.execute(
        select(BankAccount).order_by(BankAccount.account_name)
    )
    return [ba.to_dict() for ba in result.scalars().all()]


@router.post("/bank-accounts", response_model=dict, status_code=201)
async def create_bank_account(
    payload: BankAccountSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Create a new bank account."""
    ba = BankAccount(
        account_name=payload.account_name,
        account_number=payload.account_number,
        bank_name=payload.bank_name,
        bank_code=payload.bank_code,
        iban=payload.iban,
        currency=payload.currency,
        account_type=payload.account_type,
        site_id=payload.site_id,
        gl_account_id=payload.gl_account_id,
        is_active=payload.is_active,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    db.add(ba)
    await db.commit()
    await db.refresh(ba)
    return ba.to_dict()


@router.patch("/bank-accounts/{account_id}", response_model=dict)
async def update_bank_account(
    account_id: UUID,
    payload: BankAccountUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Update an existing bank account."""
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    ba = result.scalar_one_or_none()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ba, field, value)
    ba.updated_by_id = getattr(current_user, "id", None)
    await db.commit()
    await db.refresh(ba)
    return ba.to_dict()


# =============================================================================
# Bank Transaction CRUD + Reconcile
# =============================================================================


@router.get("/bank-transactions", response_model=List[dict])
async def list_bank_transactions(
    bank_account_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """List bank transactions, optionally filtered by bank account."""
    stmt = select(BankTransaction).order_by(BankTransaction.transaction_date.desc())
    if bank_account_id:
        stmt = stmt.where(BankTransaction.bank_account_id == bank_account_id)
    result = await db.execute(stmt.limit(500))
    return [bt.to_dict() for bt in result.scalars().all()]


@router.post("/bank-transactions", response_model=dict, status_code=201)
async def create_bank_transaction(
    payload: BankTransactionSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Record a new bank transaction."""
    # Verify bank account exists
    ba_result = await db.execute(select(BankAccount).where(BankAccount.id == payload.bank_account_id))
    ba = ba_result.scalar_one_or_none()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")

    bt = BankTransaction(
        bank_account_id=payload.bank_account_id,
        transaction_date=payload.transaction_date,
        value_date=payload.value_date,
        transaction_type=payload.transaction_type,
        reference=payload.reference,
        description=payload.description,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency,
        status=payload.status,
        source_type=payload.source_type,
        source_id=payload.source_id,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    db.add(bt)

    # Update bank account running balance
    ba.current_balance += Decimal(str(payload.amount))
    bt.running_balance = ba.current_balance

    await db.commit()
    await db.refresh(bt)
    
    # Best-effort: bind common thread lineage
    try:
        from sensei.services.core.common_thread import get_common_thread_service
        ct = get_common_thread_service()
        await ct.bind(
            db,
            bank_transaction_id=str(bt.id),
            created_by_id=getattr(current_user, "id", None),
            source="bank_transaction_create",
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.debug("Failed to capture bank_transaction common-thread")
    
    return bt.to_dict()


@router.post("/bank-transactions/{transaction_id}/reconcile", response_model=dict)
async def reconcile_bank_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user),
):
    """Mark a bank transaction as reconciled."""
    result = await db.execute(select(BankTransaction).where(BankTransaction.id == transaction_id))
    bt = result.scalar_one_or_none()
    if not bt:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    if bt.status == "reconciled":
        raise HTTPException(status_code=409, detail="Transaction is already reconciled")

    bt.status = "reconciled"
    bt.reconciled_at = datetime.now(timezone.utc)
    bt.reconciled_by_id = getattr(current_user, "id", None)
    bt.updated_by_id = getattr(current_user, "id", None)

    await db.commit()
    await db.refresh(bt)
    return bt.to_dict()

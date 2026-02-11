"""
GL Posting Helper Service.

Provides convenience methods for creating and posting journal entries
from operational events (GRN, invoice, work order completion, payments).
All operations are DB-backed via the persistent accounting service.

This wires finance into the operational flow — every significant
financial event creates proper double-entry GL journal entries.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.finance import GLAccount, JournalEntry, JournalLine, FXRate, CurrencySetting

logger = logging.getLogger(__name__)

# Well-known default GL account codes.  The system will auto-create these
# if they don't exist when first needed.
_DEFAULT_ACCOUNTS = {
    "1100": ("Cash / Bank", "asset"),
    "1200": ("Inventory", "asset"),
    "1250": ("Finished Goods Inventory", "asset"),
    "1300": ("Accounts Receivable", "asset"),
    "1400": ("Work-In-Progress", "asset"),
    "2100": ("GRN Accrual / Goods Received Not Invoiced", "liability"),
    "4000": ("Sales Revenue", "revenue"),
    "5000": ("Cost of Goods Sold / Variance", "expense"),
}


async def _ensure_account(db: AsyncSession, code: str) -> GLAccount:
    """Return an existing GL account or auto-create a default one."""
    result = await db.execute(select(GLAccount).where(GLAccount.account_code == code))
    account = result.scalar_one_or_none()
    if account is not None:
        return account

    if code in _DEFAULT_ACCOUNTS:
        name, acct_type = _DEFAULT_ACCOUNTS[code]
        account = GLAccount(
            account_code=code,
            account_name=name,
            account_type=acct_type,
            is_active=True,
        )
        db.add(account)
        await db.flush()
        return account

    raise ValueError(f"GL Account not found and no default defined: {code}")


async def _get_fx_rate(
    db: AsyncSession,
    from_currency: str,
    to_base: str,
    as_of: date,
) -> Decimal:
    """Look up the FX rate for a given currency pair, defaulting to 1 if same."""
    if from_currency == to_base:
        return Decimal("1")

    result = await db.execute(
        select(FXRate)
        .where(
            FXRate.from_currency == from_currency,
            FXRate.to_currency == to_base,
            FXRate.as_of <= as_of,
        )
        .order_by(FXRate.as_of.desc())
        .limit(1)
    )
    fx = result.scalar_one_or_none()
    if fx is not None:
        return fx.rate

    # Try inverse
    result2 = await db.execute(
        select(FXRate)
        .where(
            FXRate.from_currency == to_base,
            FXRate.to_currency == from_currency,
            FXRate.as_of <= as_of,
        )
        .order_by(FXRate.as_of.desc())
        .limit(1)
    )
    fx2 = result2.scalar_one_or_none()
    if fx2 is not None and fx2.rate != 0:
        return Decimal("1") / fx2.rate

    logger.warning("No FX rate found for %s→%s as of %s, using 1.0", from_currency, to_base, as_of)
    return Decimal("1")


async def _get_base_currency(db: AsyncSession) -> str:
    result = await db.execute(select(CurrencySetting).limit(1))
    cs = result.scalar_one_or_none()
    return cs.base_currency if cs else "USD"


async def _create_and_post_je(
    db: AsyncSession,
    *,
    reference: str,
    entry_date: date,
    description: str,
    lines: list[dict],
    user_id: UUID | None = None,
) -> JournalEntry:
    """Create a journal entry with lines and auto-post it.

    Each line dict: {account_code, debit, credit, currency, memo}
    """
    base_currency = await _get_base_currency(db)

    entry = JournalEntry(
        reference=reference,
        entry_date=entry_date,
        description=description,
        status="posted",
        posted_at=datetime.now(timezone.utc),
        posted_by_id=user_id,
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    db.add(entry)
    await db.flush()

    # Batch-resolve all account codes
    codes = list({ld["account_code"] for ld in lines})
    for code in codes:
        await _ensure_account(db, code)

    acc_result = await db.execute(
        select(GLAccount).where(GLAccount.account_code.in_(codes))
    )
    code_map = {a.account_code: a for a in acc_result.scalars().all()}

    for ld in lines:
        account = code_map[ld["account_code"]]
        line_currency = ld.get("currency", base_currency)
        debit = Decimal(str(ld.get("debit", 0)))
        credit = Decimal(str(ld.get("credit", 0)))
        fx_rate = await _get_fx_rate(db, line_currency, base_currency, entry_date)
        amount_base = (debit - credit) * fx_rate

        jl = JournalLine(
            entry_id=entry.id,
            account_id=account.id,
            debit=debit,
            credit=credit,
            currency=line_currency,
            amount_base=amount_base,
            memo=ld.get("memo"),
        )
        db.add(jl)

    await db.flush()
    return entry


# -------------------------------------------------------------------------
# Public API used by operational endpoints
# -------------------------------------------------------------------------


async def post_grn_to_gl(
    db: AsyncSession,
    *,
    grn_reference: str,
    total_value: Decimal,
    currency: str = "USD",
    user_id: UUID | None = None,
) -> JournalEntry | None:
    """Create GL entries for a Goods Receipt: Dr Inventory / Cr GRN Accrual."""
    if total_value <= 0:
        return None
    try:
        today = datetime.now(timezone.utc).date()
        return await _create_and_post_je(
            db,
            reference=f"GRN-{grn_reference}",
            entry_date=today,
            description=f"Goods Receipt {grn_reference} — inventory received",
            lines=[
                {"account_code": "1200", "debit": total_value, "credit": Decimal("0"), "currency": currency, "memo": "Inventory received"},
                {"account_code": "2100", "debit": Decimal("0"), "credit": total_value, "currency": currency, "memo": "GRN accrual"},
            ],
            user_id=user_id,
        )
    except Exception:
        logger.warning("GL posting for GRN %s failed", grn_reference, exc_info=True)
        return None


async def post_invoice_to_gl(
    db: AsyncSession,
    *,
    invoice_number: str,
    total_amount: Decimal,
    currency: str = "USD",
    user_id: UUID | None = None,
) -> JournalEntry | None:
    """Create GL entries for a Customer Invoice: Dr A/R / Cr Revenue."""
    if total_amount <= 0:
        return None
    try:
        today = datetime.now(timezone.utc).date()
        return await _create_and_post_je(
            db,
            reference=f"INV-{invoice_number}",
            entry_date=today,
            description=f"Customer Invoice {invoice_number}",
            lines=[
                {"account_code": "1300", "debit": total_amount, "credit": Decimal("0"), "currency": currency, "memo": "Accounts Receivable"},
                {"account_code": "4000", "debit": Decimal("0"), "credit": total_amount, "currency": currency, "memo": "Sales Revenue"},
            ],
            user_id=user_id,
        )
    except Exception:
        logger.warning("GL posting for Invoice %s failed", invoice_number, exc_info=True)
        return None


async def post_wo_completion_to_gl(
    db: AsyncSession,
    *,
    work_order_id: int,
    total_cost: Decimal,
    currency: str = "USD",
    user_id: UUID | None = None,
) -> JournalEntry | None:
    """Create GL entries for WO completion: Dr Finished Goods / Cr WIP."""
    if total_cost <= 0:
        return None
    try:
        today = datetime.now(timezone.utc).date()
        return await _create_and_post_je(
            db,
            reference=f"WO-{work_order_id}-COMPLETE",
            entry_date=today,
            description=f"Work Order {work_order_id} completion — FG receipt / WIP relief",
            lines=[
                {"account_code": "1250", "debit": total_cost, "credit": Decimal("0"), "currency": currency, "memo": "Finished goods inventory"},
                {"account_code": "1400", "debit": Decimal("0"), "credit": total_cost, "currency": currency, "memo": "WIP relief"},
            ],
            user_id=user_id,
        )
    except Exception:
        logger.warning("GL posting for WO %s failed", work_order_id, exc_info=True)
        return None


async def post_payment_to_gl(
    db: AsyncSession,
    *,
    payment_reference: str,
    amount: Decimal,
    currency: str = "USD",
    user_id: UUID | None = None,
) -> JournalEntry | None:
    """Create GL entries for a customer payment: Dr Cash / Cr A/R."""
    if amount <= 0:
        return None
    try:
        today = datetime.now(timezone.utc).date()
        return await _create_and_post_je(
            db,
            reference=f"PMT-{payment_reference}",
            entry_date=today,
            description=f"Customer Payment {payment_reference}",
            lines=[
                # Debit a generic "Cash/Bank" asset — code 1100
                {"account_code": "1100", "debit": amount, "credit": Decimal("0"), "currency": currency, "memo": "Cash received"},
                {"account_code": "1300", "debit": Decimal("0"), "credit": amount, "currency": currency, "memo": "A/R reduction"},
            ],
            user_id=user_id,
        )
    except Exception:
        logger.warning("GL posting for payment %s failed", payment_reference, exc_info=True)
        return None

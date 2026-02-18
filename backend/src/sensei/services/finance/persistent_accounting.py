"""
Persistent Accounting Ledger Service.

Database-backed general ledger implementation. Persists
accounts, journal entries, posted lines, fiscal periods,
and FX rates to PostgreSQL.
"""

from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, List, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from sensei.models.finance import GLAccount, JournalEntry, JournalLine, AccountingPeriod, FXRate
from sensei.models.user import User
from sensei.services.event_bus import event_bus
from sensei.services.domain_events import JournalEntryPosted

class PersistentAccountingLedgerService:
    """Persistent General Ledger service using SQLAlchemy."""

    def __init__(self, db: AsyncSession, base_currency: str = "USD"):
        self.db = db
        self.base_currency = base_currency

    async def list_accounts(self) -> List[GLAccount]:
        result = await self.db.execute(select(GLAccount))
        return list(result.scalars().all())

    async def upsert_account(
        self,
        code: str,
        name: str,
        account_type: str,
        currency: str | None = None,
        is_active: bool = True
    ) -> GLAccount:
        result = await self.db.execute(select(GLAccount).where(GLAccount.account_code == code))
        account = result.scalar_one_or_none()
        
        if account:
            account.account_name = name
            account.account_type = account_type
            account.is_active = is_active
        else:
            account = GLAccount(
                account_code=code,
                account_name=name,
                account_type=account_type,
                is_active=is_active
            )
            self.db.add(account)
        
        await self.db.flush()
        return account

    async def create_journal_entry(
        self,
        reference: str,
        entry_date: date,
        description: str,
        lines: List[dict]
    ) -> JournalEntry:
        entry = JournalEntry(
            reference=reference,
            entry_date=entry_date,
            description=description,
            status="draft"
        )
        self.db.add(entry)
        await self.db.flush()

        # M8 fix: batch-resolve all account_codes in one query instead of N+1
        account_codes = [ld["account_code"] for ld in lines]
        acc_result = await self.db.execute(
            select(GLAccount).where(GLAccount.account_code.in_(account_codes))
        )
        code_to_account = {a.account_code: a for a in acc_result.scalars().all()}

        for line_data in lines:
            account = code_to_account.get(line_data["account_code"])
            if account is None:
                raise ValueError(f"GL Account not found: {line_data['account_code']}")

            line = JournalLine(
                entry_id=entry.id,
                account_id=account.id,
                debit=line_data.get("debit", Decimal("0")),
                credit=line_data.get("credit", Decimal("0")),
                currency=line_data.get("currency", self.base_currency),
                amount_base=line_data.get("debit", Decimal("0")) - line_data.get("credit", Decimal("0")),
                memo=line_data.get("memo")
            )
            self.db.add(line)
        
        await self.db.flush()

        # Publish domain event — feeds single data thread
        total_debit = sum(float(ld.get("debit", 0)) for ld in lines)
        total_credit = sum(float(ld.get("credit", 0)) for ld in lines)
        await event_bus.publish(JournalEntryPosted(
            entry_id=str(entry.id),
            debit_total=total_debit,
            credit_total=total_credit,
            period=str(entry_date),
        ))

        return entry

    async def post_journal_entry(self, entry_id: UUID, user_id: UUID):
        result = await self.db.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
        entry = result.scalar_one()
        
        if entry.status != "draft":
            raise ValueError("Only draft entries can be posted")
        
        entry.status = "posted"
        entry.posted_at = datetime.now(timezone.utc)
        entry.posted_by_id = user_id
        
        await self.db.flush()

    async def get_trial_balance(self, as_of: date) -> List[dict]:
        # H4 fix: use outerjoin so accounts with zero posted lines still appear
        result = await self.db.execute(
            select(
                GLAccount.account_code,
                GLAccount.account_name,
                func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
                func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit")
            )
            .outerjoin(
                JournalLine,
                GLAccount.id == JournalLine.account_id,
            )
            .outerjoin(
                JournalEntry,
                (JournalLine.entry_id == JournalEntry.id)
                & (JournalEntry.entry_date <= as_of)
                & (JournalEntry.status == "posted"),
            )
            .group_by(GLAccount.account_code, GLAccount.account_name)
        )
        
        rows = result.all()
        return [
            {
                "account_code": r[0],
                "account_name": r[1],
                "debit": r[2] or Decimal("0"),
                "credit": r[3] or Decimal("0"),
                "balance": (r[2] or Decimal("0")) - (r[3] or Decimal("0"))
            }
            for r in rows
        ]

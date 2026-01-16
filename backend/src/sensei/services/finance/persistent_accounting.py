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

        for line_data in lines:
            # line_data should have account_code, debit, credit, currency
            acc_result = await self.db.execute(
                select(GLAccount).where(GLAccount.account_code == line_data["account_code"])
            )
            account = acc_result.scalar_one()
            
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
        # This is a bit complex for a quick implementation but essential
        result = await self.db.execute(
            select(
                GLAccount.account_code,
                GLAccount.account_name,
                func.sum(JournalLine.debit).label("total_debit"),
                func.sum(JournalLine.credit).label("total_credit")
            )
            .join(JournalLine, GLAccount.id == JournalLine.account_id)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .where(JournalEntry.entry_date <= as_of)
            .where(JournalEntry.status == "posted")
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

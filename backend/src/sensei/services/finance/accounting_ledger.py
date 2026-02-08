"""Accounting Ledger (General Ledger) service.

Implements Development Plan Section 22.1 (Accounting Core):
- Chart of Accounts (CoA)
- Journal entries (create/approve/post/reverse)
- Accounting periods (open/close/reopen)
- Financial statements (trial balance, P&L, balance sheet)
- Multi-currency posting with FX rates + period-end revaluation

This module follows the project pattern of pure-Python, in-memory services
with async database persistence via PersistentServiceMixin.
State is held in memory for fast reads and asynchronously synced to
PostgreSQL gl_accounts, journal_entries, and journal_lines tables.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


_FINANCE_READ_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "auditor",
}

_FINANCE_WRITE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
}

_FINANCE_APPROVE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
}


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class EntryStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"


class PeriodStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    occurred_at: datetime
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartAccount:
    id: UUID
    code: str
    name: str
    account_type: AccountType
    currency: str  # native currency for the account (usually base)
    is_active: bool = True
    allow_manual_posting: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JournalLine:
    account_code: str
    debit: Decimal
    credit: Decimal
    currency: str
    memo: str | None = None


@dataclass
class JournalEntry:
    id: UUID
    reference: str
    entry_date: date
    description: str
    created_at: datetime
    created_by: str
    status: EntryStatus = EntryStatus.DRAFT
    approved_at: datetime | None = None
    approved_by: str | None = None
    posted_at: datetime | None = None
    posted_by: str | None = None
    reversed_entry_id: UUID | None = None
    lines: list[JournalLine] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountingPeriod:
    id: UUID
    period_key: str  # e.g. "2026-01"
    start_date: date
    end_date: date
    status: PeriodStatus = PeriodStatus.OPEN
    closed_at: datetime | None = None
    closed_by: str | None = None
    reopened_at: datetime | None = None
    reopened_by: str | None = None


@dataclass(frozen=True)
class FXRate:
    as_of: date
    from_currency: str
    to_currency: str
    rate: Decimal


@dataclass(frozen=True)
class PostedLine:
    entry_id: UUID
    entry_date: date
    account_code: str
    amount_base: Decimal
    amount_txn: Decimal
    currency_txn: str


@dataclass(frozen=True)
class TrialBalanceRow:
    account_code: str
    account_name: str
    account_type: AccountType
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True)
class Statement:
    as_of: date
    currency: str
    totals: dict[str, Decimal]
    lines: list[dict[str, Any]]


def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


def _validate_currency(code: str) -> str:
    c = (code or "").strip().upper()
    if len(c) != 3 or not c.isalpha():
        raise ValueError("Invalid currency code")
    return c


def _validate_account_code(code: str) -> str:
    c = (code or "").strip().upper()
    if not c:
        raise ValueError("Account code is required")
    if len(c) > 32:
        raise ValueError("Account code too long")
    return c


class AccountingLedgerService(PersistentServiceMixin):
    """GL with CoA, periods, postings, and statements.

    In-memory state is the primary data store for low-latency reads.
    PersistentServiceMixin syncs state to PostgreSQL for durability
    (gl_accounts, journal_entries, journal_lines, fiscal_periods tables).
    """

    SERVICE_NAME = "accounting_ledger"
    _MAX_POSTED_LINES = 100_000
    _MAX_AUDIT_EVENTS = 50_000

    def __init__(self, *, base_currency: str = "EUR"):
        self._base_currency = _validate_currency(base_currency)

        self._coa_by_code: dict[str, ChartAccount] = {}
        self._periods_by_key: dict[str, AccountingPeriod] = {}

        self._entries: dict[UUID, JournalEntry] = {}
        self._posted_lines: list[PostedLine] = []
        # Secondary index: account_code -> list of PostedLine (#98)
        self._posted_by_account: dict[str, list[PostedLine]] = {}
        self._accounts_with_postings: set[str] = set()

        # FX rate table keyed by (as_of, from, to)
        self._fx_rates: dict[tuple[date, str, str], FXRate] = {}

        self._audit: list[AuditEvent] = []

        # CoA governance token: increment on changes for external syncing (22.10)
        self._coa_version: int = 1

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        return list(self._audit)

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
        require_write: bool = True,
    ) -> None:
        roles = _norm_roles(actor_roles)
        if require_write:
            _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")
        else:
            _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        self._audit.append(
            AuditEvent(
                id=uuid4(),
                occurred_at=_now(),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                metadata=metadata or {},
            )
        )
        # Trim if over cap (#119 — prevent unbounded memory growth)
        if len(self._audit) > self._MAX_AUDIT_EVENTS:
            self._audit = self._audit[-self._MAX_AUDIT_EVENTS // 2:]

    # ------------------------------------------------------------------
    # Chart of Accounts
    # ------------------------------------------------------------------

    @property
    def base_currency(self) -> str:
        return self._base_currency

    @property
    def coa_version(self) -> int:
        return self._coa_version

    def upsert_account(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        code: str,
        name: str,
        account_type: AccountType,
        currency: str | None = None,
        is_active: bool = True,
        allow_manual_posting: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ChartAccount:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")

        acct_code = _validate_account_code(code)
        acct_currency = _validate_currency(currency or self._base_currency)
        nm = (name or "").strip()
        if not nm:
            raise ValueError("Account name is required")

        existing = self._coa_by_code.get(acct_code)
        if existing is None:
            account = ChartAccount(
                id=uuid4(),
                code=acct_code,
                name=nm,
                account_type=account_type,
                currency=acct_currency,
                is_active=is_active,
                allow_manual_posting=allow_manual_posting,
                metadata=metadata or {},
            )
            self._coa_by_code[acct_code] = account
            self._coa_version += 1
            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="coa.account.create",
                entity_type="coa_account",
                entity_id=acct_code,
                correlation_id=correlation_id,
                metadata={"account_type": account_type.value, "currency": acct_currency},
            )
            return account

        # Guard: changing type/currency after postings is risky
        has_postings = acct_code in self._accounts_with_postings
        if has_postings and (existing.account_type != account_type or existing.currency != acct_currency):
            raise ValueError("Cannot change account type/currency after postings")

        existing.name = nm
        existing.is_active = is_active
        existing.allow_manual_posting = allow_manual_posting
        existing.metadata = metadata or existing.metadata
        self._coa_version += 1
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="coa.account.update",
            entity_type="coa_account",
            entity_id=acct_code,
            correlation_id=correlation_id,
        )
        return existing

    def get_account(self, *, actor_roles: Iterable[str], code: str) -> ChartAccount | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        return self._coa_by_code.get(_validate_account_code(code))

    def list_accounts(self, *, actor_roles: Iterable[str], active_only: bool = False) -> list[ChartAccount]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        accounts = list(self._coa_by_code.values())
        if active_only:
            accounts = [a for a in accounts if a.is_active]
        accounts.sort(key=lambda a: a.code)
        return accounts

    # ------------------------------------------------------------------
    # FX Rates
    # ------------------------------------------------------------------

    def set_fx_rate(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        as_of: date,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
    ) -> FXRate:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")
        fc = _validate_currency(from_currency)
        tc = _validate_currency(to_currency)
        if fc == tc:
            raise ValueError("FX rate from/to must differ")
        if rate <= 0:
            raise ValueError("FX rate must be positive")

        fx = FXRate(as_of=as_of, from_currency=fc, to_currency=tc, rate=_q2(rate))
        self._fx_rates[(as_of, fc, tc)] = fx
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="fx.rate.set",
            entity_type="fx_rate",
            entity_id=f"{as_of}:{fc}->{tc}",
            correlation_id=correlation_id,
            metadata={"rate": str(fx.rate)},
        )
        return fx

    def get_fx_rate(self, *, as_of: date, from_currency: str, to_currency: str) -> FXRate | None:
        fc = _validate_currency(from_currency)
        tc = _validate_currency(to_currency)
        if fc == tc:
            return FXRate(as_of=as_of, from_currency=fc, to_currency=tc, rate=Decimal("1.00"))
        return self._fx_rates.get((as_of, fc, tc))

    def _convert_to_base(self, *, amount: Decimal, currency: str, as_of: date) -> Decimal:
        c = _validate_currency(currency)
        if c == self._base_currency:
            return _q2(amount)
        fx = self.get_fx_rate(as_of=as_of, from_currency=c, to_currency=self._base_currency)
        if fx is None:
            raise ValueError(f"Missing FX rate for {c}->{self._base_currency} on {as_of}")
        return _q2(amount * fx.rate)

    # ------------------------------------------------------------------
    # Periods
    # ------------------------------------------------------------------

    def create_period(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        period_key: str,
        start_date: date,
        end_date: date,
    ) -> AccountingPeriod:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")
        key = (period_key or "").strip()
        if not key:
            raise ValueError("period_key required")
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")
        if key in self._periods_by_key:
            raise ValueError("period_key already exists")

        period = AccountingPeriod(
            id=uuid4(),
            period_key=key,
            start_date=start_date,
            end_date=end_date,
        )
        self._periods_by_key[key] = period
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="period.create",
            entity_type="period",
            entity_id=key,
            correlation_id=correlation_id,
        )
        return period

    def get_period(self, *, actor_roles: Iterable[str], period_key: str) -> AccountingPeriod | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        return self._periods_by_key.get((period_key or "").strip())

    def close_period(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        period_key: str,
    ) -> AccountingPeriod:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")
        period = self._periods_by_key.get((period_key or "").strip())
        if period is None:
            raise ValueError("Unknown period")
        if period.status == PeriodStatus.CLOSED:
            return period

        # Hard lock rule: no DRAFT/APPROVED entries dated inside this period
        open_entries = [
            e
            for e in self._entries.values()
            if period.start_date <= e.entry_date <= period.end_date and e.status in {EntryStatus.DRAFT, EntryStatus.APPROVED}
        ]
        if open_entries:
            raise ValueError("Cannot close period with unposted entries")

        period.status = PeriodStatus.CLOSED
        period.closed_at = _now()
        period.closed_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="period.close",
            entity_type="period",
            entity_id=period.period_key,
            correlation_id=correlation_id,
        )
        return period

    def reopen_period(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        period_key: str,
        reason: str,
    ) -> AccountingPeriod:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")
        period = self._periods_by_key.get((period_key or "").strip())
        if period is None:
            raise ValueError("Unknown period")
        if period.status == PeriodStatus.OPEN:
            return period
        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")
        period.status = PeriodStatus.OPEN
        period.reopened_at = _now()
        period.reopened_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="period.reopen",
            entity_type="period",
            entity_id=period.period_key,
            correlation_id=correlation_id,
            metadata={"reason": r},
        )
        return period

    def _ensure_period_open_for_date(self, *, entry_date: date) -> None:
        for period in self._periods_by_key.values():
            if period.start_date <= entry_date <= period.end_date:
                if period.status != PeriodStatus.OPEN:
                    raise ValueError("Accounting period is closed")
                return
        # If no period defined, allow posting (useful for early bootstrap), but caller should define periods.

    # ------------------------------------------------------------------
    # Journal Entries
    # ------------------------------------------------------------------

    def create_journal_entry(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        reference: str,
        entry_date: date,
        description: str,
        lines: list[JournalLine],
        metadata: dict[str, Any] | None = None,
    ) -> JournalEntry:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")
        ref = (reference or "").strip()
        if not ref:
            raise ValueError("reference required")
        desc = (description or "").strip()
        if not desc:
            raise ValueError("description required")
        if not lines:
            raise ValueError("At least one line required")

        self._validate_lines(lines)

        entry = JournalEntry(
            id=uuid4(),
            reference=ref,
            entry_date=entry_date,
            description=desc,
            created_at=_now(),
            created_by=actor_id,
            lines=list(lines),
            metadata=metadata or {},
        )
        self._entries[entry.id] = entry
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="je.create",
            entity_type="journal_entry",
            entity_id=str(entry.id),
            correlation_id=correlation_id,
            metadata={"reference": ref, "entry_date": entry_date.isoformat()},
        )
        return entry

    def approve_journal_entry(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entry_id: UUID,
    ) -> JournalEntry:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError("Unknown journal entry")
        if entry.status != EntryStatus.DRAFT:
            return entry
        entry.status = EntryStatus.APPROVED
        entry.approved_at = _now()
        entry.approved_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="je.approve",
            entity_type="journal_entry",
            entity_id=str(entry.id),
            correlation_id=correlation_id,
        )
        return entry

    def post_journal_entry(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entry_id: UUID,
    ) -> JournalEntry:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError("Unknown journal entry")
        if entry.status == EntryStatus.POSTED:
            return entry
        if entry.status != EntryStatus.APPROVED:
            raise ValueError("Entry must be approved before posting")

        self._ensure_period_open_for_date(entry_date=entry.entry_date)
        self._validate_lines(entry.lines)

        # Post lines as base-currency amounts
        for ln in entry.lines:
            amt_txn = _q2(ln.debit - ln.credit)
            amt_base = self._convert_to_base(amount=amt_txn, currency=ln.currency, as_of=entry.entry_date)
            self._posted_lines.append(
                PostedLine(
                    entry_id=entry.id,
                    entry_date=entry.entry_date,
                    account_code=_validate_account_code(ln.account_code),
                    amount_base=amt_base,
                    amount_txn=amt_txn,
                    currency_txn=_validate_currency(ln.currency),
                )
            )
            acct_code = _validate_account_code(ln.account_code)
            self._posted_by_account.setdefault(acct_code, []).append(self._posted_lines[-1])
            self._accounts_with_postings.add(acct_code)

        # Trim if over cap (#117 — prevent unbounded memory growth)
        if len(self._posted_lines) > self._MAX_POSTED_LINES:
            self._posted_lines = self._posted_lines[-self._MAX_POSTED_LINES // 2:]
            # Rebuild secondary index after trim
            self._posted_by_account.clear()
            self._accounts_with_postings.clear()
            for pl in self._posted_lines:
                self._posted_by_account.setdefault(pl.account_code, []).append(pl)
                self._accounts_with_postings.add(pl.account_code)

        entry.status = EntryStatus.POSTED
        entry.posted_at = _now()
        entry.posted_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="je.post",
            entity_type="journal_entry",
            entity_id=str(entry.id),
            correlation_id=correlation_id,
        )
        return entry

    def reverse_journal_entry(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entry_id: UUID,
        reversal_date: date,
        reason: str,
    ) -> JournalEntry:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError("Unknown journal entry")
        if entry.status != EntryStatus.POSTED:
            raise ValueError("Only posted entries can be reversed")
        if entry.reversed_entry_id is not None:
            raise ValueError("Entry already reversed")
        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")

        self._ensure_period_open_for_date(entry_date=reversal_date)

        reversal_lines: list[JournalLine] = []
        for ln in entry.lines:
            reversal_lines.append(
                JournalLine(
                    account_code=ln.account_code,
                    debit=ln.credit,
                    credit=ln.debit,
                    currency=ln.currency,
                    memo=f"Reversal: {r}",
                )
            )

        rev = self.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=f"REV-{entry.reference}",
            entry_date=reversal_date,
            description=f"Reversal of {entry.reference}: {r}",
            lines=reversal_lines,
            metadata={"reversal_of": str(entry.id)},
        )
        self.approve_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            entry_id=rev.id,
        )
        self.post_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            entry_id=rev.id,
        )

        entry.status = EntryStatus.REVERSED
        entry.reversed_entry_id = rev.id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="je.reverse",
            entity_type="journal_entry",
            entity_id=str(entry.id),
            correlation_id=correlation_id,
            metadata={"reversal_entry_id": str(rev.id)},
        )
        return rev

    def _validate_lines(self, lines: list[JournalLine]) -> None:
        if not lines:
            raise ValueError("Lines required")

        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for ln in lines:
            code = _validate_account_code(ln.account_code)
            acct = self._coa_by_code.get(code)
            if acct is None:
                raise ValueError(f"Unknown account {code}")
            if not acct.is_active:
                raise ValueError(f"Inactive account {code}")
            if not acct.allow_manual_posting:
                raise ValueError(f"Account {code} does not allow manual posting")

            if ln.debit < 0 or ln.credit < 0:
                raise ValueError("Debit/credit must be non-negative")
            if ln.debit == 0 and ln.credit == 0:
                raise ValueError("Line cannot have both debit and credit = 0")
            if ln.debit > 0 and ln.credit > 0:
                raise ValueError("Line cannot have both debit and credit")

            _validate_currency(ln.currency)
            total_debit += ln.debit
            total_credit += ln.credit

        if _q2(total_debit) != _q2(total_credit):
            raise ValueError("Entry is not balanced")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def trial_balance(
        self,
        *,
        actor_roles: Iterable[str],
        as_of: date,
    ) -> list[TrialBalanceRow]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")

        # Sum posted lines up to as_of
        sums: dict[str, Decimal] = {}
        for pl in self._posted_lines:
            if pl.entry_date <= as_of:
                sums[pl.account_code] = sums.get(pl.account_code, Decimal("0")) + pl.amount_base

        rows: list[TrialBalanceRow] = []
        for code, account in self._coa_by_code.items():
            bal = _q2(sums.get(code, Decimal("0")))
            debit = bal if bal > 0 else Decimal("0")
            credit = -bal if bal < 0 else Decimal("0")
            rows.append(
                TrialBalanceRow(
                    account_code=code,
                    account_name=account.name,
                    account_type=account.account_type,
                    debit=_q2(debit),
                    credit=_q2(credit),
                )
            )

        rows.sort(key=lambda r: r.account_code)
        return rows

    def profit_and_loss(
        self,
        *,
        actor_roles: Iterable[str],
        start: date,
        end: date,
        reporting_currency: str | None = None,
    ) -> Statement:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        cur = _validate_currency(reporting_currency or self._base_currency)

        totals: dict[str, Decimal] = {
            "revenue": Decimal("0"),
            "expense": Decimal("0"),
            "net_income": Decimal("0"),
        }
        lines: list[dict[str, Any]] = []

        for code, acct in self._coa_by_code.items():
            if acct.account_type not in {AccountType.REVENUE, AccountType.EXPENSE}:
                continue
            bal_base = self._balance_for_account(code=code, start=start, end=end)
            bal = bal_base
            if cur != self._base_currency:
                # For reporting conversion, use end-date rate (simple approach)
                bal = self._convert_from_base(amount=bal_base, to_currency=cur, as_of=end)

            if acct.account_type == AccountType.REVENUE:
                totals["revenue"] += -bal  # revenue usually credits (negative balances)
            else:
                totals["expense"] += bal

            lines.append(
                {
                    "account_code": code,
                    "account_name": acct.name,
                    "type": acct.account_type.value,
                    "amount": str(_q2(bal)),
                }
            )

        totals["revenue"] = _q2(totals["revenue"])
        totals["expense"] = _q2(totals["expense"])
        totals["net_income"] = _q2(totals["revenue"] - totals["expense"])

        return Statement(as_of=end, currency=cur, totals={k: _q2(v) for k, v in totals.items()}, lines=lines)

    def balance_sheet(
        self,
        *,
        actor_roles: Iterable[str],
        as_of: date,
        reporting_currency: str | None = None,
    ) -> Statement:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        cur = _validate_currency(reporting_currency or self._base_currency)

        totals: dict[str, Decimal] = {
            "assets": Decimal("0"),
            "liabilities": Decimal("0"),
            "equity": Decimal("0"),
        }
        lines: list[dict[str, Any]] = []

        for code, acct in self._coa_by_code.items():
            if acct.account_type not in {AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY}:
                continue
            bal_base = self._balance_for_account(code=code, start=None, end=as_of)
            bal = bal_base
            if cur != self._base_currency:
                bal = self._convert_from_base(amount=bal_base, to_currency=cur, as_of=as_of)

            if acct.account_type == AccountType.ASSET:
                totals["assets"] += bal
            elif acct.account_type == AccountType.LIABILITY:
                totals["liabilities"] += -bal  # liabilities typically credit
            else:
                totals["equity"] += -bal

            lines.append(
                {
                    "account_code": code,
                    "account_name": acct.name,
                    "type": acct.account_type.value,
                    "amount": str(_q2(bal)),
                }
            )

        return Statement(as_of=as_of, currency=cur, totals={k: _q2(v) for k, v in totals.items()}, lines=lines)

    def _balance_for_account(self, *, code: str, start: date | None, end: date) -> Decimal:
        bal = Decimal("0")
        for pl in self._posted_by_account.get(code, []):
            if pl.entry_date > end:
                continue
            if start is not None and pl.entry_date < start:
                continue
            bal += pl.amount_base
        return _q2(bal)

    def _convert_from_base(self, *, amount: Decimal, to_currency: str, as_of: date) -> Decimal:
        tc = _validate_currency(to_currency)
        if tc == self._base_currency:
            return _q2(amount)
        fx = self.get_fx_rate(as_of=as_of, from_currency=self._base_currency, to_currency=tc)
        if fx is None:
            raise ValueError(f"Missing FX rate for {self._base_currency}->{tc} on {as_of}")
        return _q2(amount * fx.rate)

    # ------------------------------------------------------------------
    # Period-end FX revaluation
    # ------------------------------------------------------------------

    def revalue_foreign_balances(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        as_of: date,
        fx_gain_account: str,
        fx_loss_account: str,
        reference: str = "FX-REVAL",
    ) -> JournalEntry | None:
        """Create and post a revaluation JE for foreign-currency posted lines.

        Strategy:
        - For each account that has foreign-currency postings, compute:
          - base_sum: sum(amount_base)
          - txn_sum: sum(amount_txn) per currency
          - expected_base: convert txn_sum to base using as_of rate
          - delta = expected_base - base_sum
        - Post delta to the account and offset to FX gain/loss.

        This is a simplified but auditable approach suitable for a first full implementation.
        """

        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")

        fx_gain = _validate_account_code(fx_gain_account)
        fx_loss = _validate_account_code(fx_loss_account)
        if fx_gain not in self._coa_by_code or fx_loss not in self._coa_by_code:
            raise ValueError("FX gain/loss accounts must exist")

        # collect foreign postings up to as_of
        per_acct_cur: dict[tuple[str, str], dict[str, Decimal]] = {}
        for pl in self._posted_lines:
            if pl.entry_date > as_of:
                continue
            if pl.currency_txn == self._base_currency:
                continue
            key = (pl.account_code, pl.currency_txn)
            agg = per_acct_cur.setdefault(key, {"base": Decimal("0"), "txn": Decimal("0")})
            agg["base"] += pl.amount_base
            agg["txn"] += pl.amount_txn

        lines: list[JournalLine] = []
        for (acct_code, cur), agg in per_acct_cur.items():
            base_sum = _q2(agg["base"])
            txn_sum = _q2(agg["txn"])
            expected_base = self._convert_to_base(amount=txn_sum, currency=cur, as_of=as_of)
            delta = _q2(expected_base - base_sum)
            if delta == 0:
                continue

            # Post delta to the account (debit if positive, credit if negative)
            if delta > 0:
                lines.append(JournalLine(account_code=acct_code, debit=delta, credit=Decimal("0"), currency=self._base_currency, memo="FX revaluation"))
                # Offset to gain/loss
                lines.append(JournalLine(account_code=fx_gain, debit=Decimal("0"), credit=delta, currency=self._base_currency, memo="FX revaluation offset"))
            else:
                amt = -delta
                lines.append(JournalLine(account_code=acct_code, debit=Decimal("0"), credit=amt, currency=self._base_currency, memo="FX revaluation"))
                lines.append(JournalLine(account_code=fx_loss, debit=amt, credit=Decimal("0"), currency=self._base_currency, memo="FX revaluation offset"))

        if not lines:
            return None

        je = self.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=reference,
            entry_date=as_of,
            description=f"FX revaluation as of {as_of.isoformat()}",
            lines=lines,
            metadata={"type": "fx_revaluation"},
        )
        self.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        return je

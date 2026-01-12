from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sensei.services.finance.accounting_ledger import (
    AccountingLedgerService,
    AccountType,
    JournalLine,
)


def _roles(*names: str) -> list[str]:
    return list(names)


def test_coa_upsert_and_list_requires_rbac():
    svc = AccountingLedgerService(base_currency="EUR")

    with pytest.raises(PermissionError):
        svc.upsert_account(
            actor_id="u1",
            actor_roles=_roles("operator"),
            correlation_id="c1",
            code="1000",
            name="Cash",
            account_type=AccountType.ASSET,
        )

    svc.upsert_account(
        actor_id="u1",
        actor_roles=_roles("finance"),
        correlation_id="c1",
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
    )

    with pytest.raises(PermissionError):
        svc.list_accounts(actor_roles=_roles("viewer"))

    accounts = svc.list_accounts(actor_roles=_roles("auditor"))
    assert [a.code for a in accounts] == ["1000"]


def test_journal_entry_lifecycle_post_and_trial_balance():
    svc = AccountingLedgerService(base_currency="EUR")
    roles = _roles("finance")

    svc.upsert_account(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
    )
    svc.upsert_account(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        code="4000",
        name="Revenue",
        account_type=AccountType.REVENUE,
    )

    entry = svc.create_journal_entry(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        reference="INV-1",
        entry_date=date(2026, 1, 10),
        description="Test sale",
        lines=[
            JournalLine(account_code="1000", debit=Decimal("100.00"), credit=Decimal("0"), currency="EUR"),
            JournalLine(account_code="4000", debit=Decimal("0"), credit=Decimal("100.00"), currency="EUR"),
        ],
    )

    with pytest.raises(ValueError):
        svc.post_journal_entry(actor_id="u1", actor_roles=roles, correlation_id="c1", entry_id=entry.id)

    svc.approve_journal_entry(actor_id="u2", actor_roles=_roles("gm"), correlation_id="c2", entry_id=entry.id)
    svc.post_journal_entry(actor_id="u2", actor_roles=_roles("gm"), correlation_id="c2", entry_id=entry.id)

    tb = svc.trial_balance(actor_roles=_roles("auditor"), as_of=date(2026, 1, 10))
    tb_map = {r.account_code: (r.debit, r.credit) for r in tb}
    assert tb_map["1000"] == (Decimal("100.00"), Decimal("0.00"))
    assert tb_map["4000"] == (Decimal("0.00"), Decimal("100.00"))


def test_period_close_blocks_unposted_entries_and_reopen_requires_reason():
    svc = AccountingLedgerService(base_currency="EUR")
    roles = _roles("finance")

    svc.create_period(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        period_key="2026-01",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    svc.upsert_account(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
    )
    svc.upsert_account(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        code="2000",
        name="AP",
        account_type=AccountType.LIABILITY,
    )

    entry = svc.create_journal_entry(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        reference="JE-1",
        entry_date=date(2026, 1, 10),
        description="Draft entry",
        lines=[
            JournalLine(account_code="1000", debit=Decimal("10.00"), credit=Decimal("0"), currency="EUR"),
            JournalLine(account_code="2000", debit=Decimal("0"), credit=Decimal("10.00"), currency="EUR"),
        ],
    )

    with pytest.raises(ValueError):
        svc.close_period(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c2", period_key="2026-01")

    svc.approve_journal_entry(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c2", entry_id=entry.id)
    svc.post_journal_entry(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c2", entry_id=entry.id)

    svc.close_period(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c3", period_key="2026-01")

    with pytest.raises(ValueError):
        svc.reopen_period(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c4", period_key="2026-01", reason="")

    svc.reopen_period(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c4", period_key="2026-01", reason="Correction")


def test_multi_currency_posting_and_fx_revaluation_creates_entry():
    svc = AccountingLedgerService(base_currency="EUR")
    roles = _roles("finance")

    # CoA
    svc.upsert_account(actor_id="u1", actor_roles=roles, correlation_id="c1", code="1000", name="Cash", account_type=AccountType.ASSET)
    svc.upsert_account(actor_id="u1", actor_roles=roles, correlation_id="c1", code="5000", name="Expense", account_type=AccountType.EXPENSE)
    svc.upsert_account(actor_id="u1", actor_roles=roles, correlation_id="c1", code="7999", name="FX Gain", account_type=AccountType.REVENUE)
    svc.upsert_account(actor_id="u1", actor_roles=roles, correlation_id="c1", code="8999", name="FX Loss", account_type=AccountType.EXPENSE)

    # FX rates USD->EUR
    svc.set_fx_rate(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        as_of=date(2026, 1, 10),
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.90"),
    )
    svc.set_fx_rate(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        as_of=date(2026, 1, 31),
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("1.00"),
    )

    # Post 100 USD expense paid from cash (both lines in USD for simplicity)
    entry = svc.create_journal_entry(
        actor_id="u1",
        actor_roles=roles,
        correlation_id="c1",
        reference="BILL-1",
        entry_date=date(2026, 1, 10),
        description="USD bill",
        lines=[
            JournalLine(account_code="5000", debit=Decimal("100.00"), credit=Decimal("0"), currency="USD"),
            JournalLine(account_code="1000", debit=Decimal("0"), credit=Decimal("100.00"), currency="USD"),
        ],
    )
    svc.approve_journal_entry(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c2", entry_id=entry.id)
    svc.post_journal_entry(actor_id="u2", actor_roles=_roles("finance"), correlation_id="c2", entry_id=entry.id)

    # Revalue at period end: USD strengthens from 0.90 to 1.00 EUR per USD; delta should trigger a JE.
    reval = svc.revalue_foreign_balances(
        actor_id="u2",
        actor_roles=_roles("finance"),
        correlation_id="c3",
        as_of=date(2026, 1, 31),
        fx_gain_account="7999",
        fx_loss_account="8999",
    )

    assert reval is not None
    tb_end = svc.trial_balance(actor_roles=_roles("auditor"), as_of=date(2026, 1, 31))
    # sanity: still balanced overall (sum debit == sum credit)
    total_debit = sum(r.debit for r in tb_end)
    total_credit = sum(r.credit for r in tb_end)
    assert total_debit == total_credit

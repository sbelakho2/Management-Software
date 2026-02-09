import asyncio
import sys
import os
from pathlib import Path

# Add src to path (robust: relative to this script's location)
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from sensei.core.database import async_session_factory
from sensei.services.finance.persistent_accounting import PersistentAccountingLedgerService
from scripts.bootstrap_starz_regions import (
    _ensure_sites,
    _ensure_currency_settings,
    _ensure_jurisdictions_and_rates,
)

async def main():
    async with async_session_factory() as db:
        svc = PersistentAccountingLedgerService(db)
        print("Bootstrapping GL Accounts...")
        await svc.upsert_account("1000", "Cash", "asset")
        await svc.upsert_account("1100", "Accounts Receivable", "asset")
        await svc.upsert_account("2000", "Accounts Payable", "liability")
        await svc.upsert_account("4000", "Sales Revenue", "revenue")
        await svc.upsert_account("5000", "Cost of Goods Sold", "expense")
        print("Seeding Starz regional configuration...")
        await _ensure_sites(db)
        await _ensure_currency_settings(db)
        await _ensure_jurisdictions_and_rates(db)
        await db.commit()
        print("ERP Bootstrapped successfully")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from sensei.core.database import async_session_factory
from sensei.services.finance.persistent_accounting import PersistentAccountingLedgerService

async def main():
    async with async_session_factory() as db:
        svc = PersistentAccountingLedgerService(db)
        print("Bootstrapping GL Accounts...")
        await svc.upsert_account("1000", "Cash", "asset")
        await svc.upsert_account("1100", "Accounts Receivable", "asset")
        await svc.upsert_account("2000", "Accounts Payable", "liability")
        await svc.upsert_account("4000", "Sales Revenue", "revenue")
        await svc.upsert_account("5000", "Cost of Goods Sold", "expense")
        await db.commit()
        print("ERP Bootstrapped successfully")

if __name__ == "__main__":
    asyncio.run(main())

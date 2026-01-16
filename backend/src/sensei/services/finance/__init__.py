from .persistent_accounting import PersistentAccountingLedgerService
from sqlalchemy.ext.asyncio import AsyncSession

def get_accounting_service(db: AsyncSession) -> PersistentAccountingLedgerService:
    return PersistentAccountingLedgerService(db)

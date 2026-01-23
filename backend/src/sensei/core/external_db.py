"""
External Database Connections for Sensei OS.

Handles connections to legacy or third-party databases like starzERP (MySQL).
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sensei.core.config import settings

# engine for starzERP (MySQL)
starz_erp_engine: AsyncEngine = create_async_engine(
    settings.STARZ_ERP_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

starz_erp_session_factory = async_sessionmaker(
    starz_erp_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_starz_erp_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async session for starzERP database."""
    async with starz_erp_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

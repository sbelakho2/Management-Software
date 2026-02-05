"""
External Database Connections for Sensei OS.

Handles connections to legacy or third-party databases like starzERP (MySQL).

NOTE: Connections are initialized lazily to avoid startup crashes when
STARZ_ERP_DATABASE_URL is not configured.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sensei.core.config import settings

_starz_erp_engine: AsyncEngine | None = None
_starz_erp_session_factory: async_sessionmaker | None = None


def _ensure_starz_erp_engine() -> AsyncEngine:
    """Create starzERP engine lazily. Raises if URL not configured."""
    global _starz_erp_engine, _starz_erp_session_factory
    if _starz_erp_engine is not None and _starz_erp_session_factory is not None:
        return _starz_erp_engine

    if not settings.STARZ_ERP_DATABASE_URL:
        raise RuntimeError(
            "STARZ_ERP_DATABASE_URL is not configured. "
            "Set it to enable starzERP integration."
        )

    _starz_erp_engine = create_async_engine(
        settings.STARZ_ERP_DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    _starz_erp_session_factory = async_sessionmaker(
        _starz_erp_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _starz_erp_engine

async def get_starz_erp_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async session for starzERP database."""
    _ensure_starz_erp_engine()
    assert _starz_erp_session_factory is not None
    async with _starz_erp_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

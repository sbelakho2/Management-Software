"""
External Database Connections for Sensei OS.

Handles connections to legacy or third-party databases like starzERP (MySQL).

NOTE: Connections are initialized lazily to avoid startup crashes when
STARZ_ERP_DATABASE_URL is not configured.
"""

import asyncio
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
_init_lock = asyncio.Lock()  # Prevent race conditions on pool creation (#278)


async def _ensure_starz_erp_engine() -> AsyncEngine:
    """Create starzERP engine lazily with lock guard. Raises if URL not configured.

    Uses ``_init_lock`` so concurrent callers don't create duplicate pools. (#370)
    """
    global _starz_erp_engine, _starz_erp_session_factory
    # Fast path: already initialised (no lock needed)
    if _starz_erp_engine is not None and _starz_erp_session_factory is not None:
        return _starz_erp_engine

    async with _init_lock:
        # Double-check after acquiring lock
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
            pool_size=5,           # Connection pool size (#279)
            max_overflow=10,       # Allow up to 15 total connections (#279)
            pool_recycle=1800,     # Recycle connections after 30 min (#279)
            pool_timeout=30,       # Timeout waiting for a connection (#279)
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
    await _ensure_starz_erp_engine()
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

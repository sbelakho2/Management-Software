"""
Sensei OS Database Module

PostgreSQL database connection with async SQLAlchemy, connection pooling,
and health checking.

IMPORTANT: Session Configuration Notes
--------------------------------------
The session factory is configured with `autoflush=True` to ensure that
modifications are visible within the same transaction when queried.

If you experience unexpected behavior:
1. After modifying an object, call `await session.flush()` before querying
   if autoflush is disabled for a specific operation.
2. Use `session.expire_all()` to clear the identity map if you need fresh data.
3. For bulk operations, consider using `session.execute()` directly.
"""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from sensei.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def create_engine() -> AsyncEngine:
    """Create and configure the async database engine.

    Pool tuning notes for high concurrency:
    - pool_use_lifo=True: reuses hot connections, lets idle ones expire
    - pool_pre_ping=True: avoids stale-connection errors from PG restarts
    - pool_reset_on_return="rollback": ensures clean state without DISCARD ALL
    - prepared_statement_cache_size: asyncpg caches parsed SQL on the connection
    - jit=off server setting: JIT compilation adds latency for short OLTP queries
    """
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_use_lifo=True,
        pool_pre_ping=True,
        pool_reset_on_return="rollback",
        connect_args={
            "statement_cache_size": settings.DATABASE_STATEMENT_CACHE_SIZE,
            "prepared_statement_cache_size": 256,
            "server_settings": {
                "statement_timeout": str(settings.DATABASE_STATEMENT_TIMEOUT_MS),
                "idle_in_transaction_session_timeout": "30000",
                "jit": "off",
            },
        },
        echo=settings.DEBUG,
    )


engine = create_engine()

# Session factory configuration:
# - expire_on_commit=False: Keep loaded objects accessible after commit
# - autoflush=True: Automatically flush pending changes before queries
#   This ensures that modifications within a transaction are visible
#   when querying. Prevents subtle bugs where updates aren't seen.
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
)

# Read-only session factory for query-heavy endpoints (analytics, lists, reports).
# Uses execution_options to set the connection as read-only at the PG level.
async_readonly_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # No writes expected
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session with auto-commit.

    This session auto-commits on success and auto-rollbacks on exception.
    It is the canonical session for write operations.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_readonly_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for read-only database sessions.

    Provides a session that does NOT auto-commit. Use for list/search/analytics
    endpoints where no writes are expected. This reduces lock contention and
    allows PostgreSQL to optimize read paths.
    """
    async with async_readonly_session_factory() as session:
        try:
            # Set transaction as read-only at the database level
            await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session
        finally:
            await session.close()


async def check_database_connection(eng: AsyncEngine) -> bool:
    """Check if the database connection is healthy."""
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

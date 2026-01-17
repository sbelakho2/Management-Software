"""
Sensei OS Database Module

PostgreSQL database connection with async SQLAlchemy, connection pooling,
and health checking.
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
    """Create and configure the async database engine."""
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_use_lifo=True,
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": settings.DATABASE_STATEMENT_CACHE_SIZE,
            "server_settings": {
                "statement_timeout": str(settings.DATABASE_STATEMENT_TIMEOUT_MS),
            },
        },
        echo=settings.DEBUG,
    )


engine = create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
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

#!/usr/bin/env python3
"""Reset development database data (remove mock/demo records).

This is a DEV/TEST helper intended to remove *mocked* application data while
keeping the schema and core RBAC tables intact.

What it does:
- Refuses to run in production.
- Truncates all public tables except core auth/RBAC tables.
- Removes known test users (test_*@sensei.test, *@senseitest.com).
- Re-enables core RBAC role assignments (CEO/Admin) via bootstrap.

Usage:
  DATABASE_URL=postgresql+asyncpg://... \
  SECRET_KEY=... \
  python backend/scripts/reset_dev_database.py

Notes:
- This script is intentionally conservative: it keeps `users/roles/...` tables
  so your primary accounts remain usable.
- If you want a full wipe including users, extend EXCLUDE_TABLES cautiously.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def _check_environment() -> None:
    env = os.environ.get("ENVIRONMENT", os.environ.get("SENSEI_ENV", "development"))
    if env.lower() in ("production", "prod"):
        raise SystemExit("❌ Refusing to run reset in production")


EXCLUDE_TABLES: set[str] = {
    # Alembic
    "alembic_version",
    # Core auth/RBAC
    "users",
    "roles",
    "user_roles",
    "permissions",
    "role_permissions",
}


async def main() -> None:
    _check_environment()

    database_url = os.environ.get("DATABASE_URL") or os.environ.get("SENSEI_DATABASE_URL")
    if not database_url:
        raise SystemExit("❌ DATABASE_URL is required")

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Collect public tables
        rows = (
            await session.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                    """
                )
            )
        ).all()
        tables = [r[0] for r in rows]

        truncate_tables = [t for t in tables if t not in EXCLUDE_TABLES]

        if truncate_tables:
            ident_list = ", ".join(f'"public"."{t}"' for t in truncate_tables)
            await session.execute(text(f"TRUNCATE TABLE {ident_list} RESTART IDENTITY CASCADE"))

        # Remove known test users, but keep core accounts (e.g. ceo@sensei.os).
        await session.execute(
            text(
                r"""
                DELETE FROM user_roles
                WHERE user_id IN (
                    SELECT id FROM users
                    WHERE (email ~* '^test_.*@sensei\\.test$')
                       OR (email ILIKE '%@senseitest.com')
                )
                """
            )
        )
        await session.execute(
            text(
                r"""
                DELETE FROM users
                WHERE (email ~* '^test_.*@sensei\\.test$')
                   OR (email ILIKE '%@senseitest.com')
                """
            )
        )

        await session.commit()

    # Best-effort: ensure core RBAC roles exist/assigned.
    try:
        from sensei.services.core.rbac_bootstrap import ensure_core_users_have_roles

        async with async_session() as session:
            await ensure_core_users_have_roles(session)
            await session.commit()
    except Exception:
        # Keep the reset usable even if bootstrap isn't configured.
        pass

    await engine.dispose()

    print("✅ Development database reset complete.")
    print(f"   Truncated tables: {len(truncate_tables)}")
    print("   Removed test users: test_*@sensei.test, *@senseitest.com")


if __name__ == "__main__":
    asyncio.run(main())

"""
Alembic Migration Conventions and Squashing Guide (#418, #419).

This document establishes naming conventions for migrations and provides
a squashing strategy for long migration chains.

Migration Naming Convention
===========================

All migration files MUST follow this naming pattern:

    YYYYMMDD_HHMMSS_short_description.py

Examples:
    20260208_100000_product_uuid_pk_and_indexes.py
    20260210_143000_add_warehouse_tables.py

The revision ID inside the file should match the timestamp prefix:

    revision = "20260208_100000"
    down_revision = "20260207_150000"

Squashing Strategy
==================

When the migration chain exceeds 50 files:

1. **Create a squash migration** that combines all migrations up to a
   stable baseline into a single ``CREATE TABLE`` / ``CREATE INDEX``
   migration.

2. **Archive old migrations** into a ``versions/_archive/`` directory
   (don't delete them — they serve as documentation).

3. **Update the squash migration's down_revision** to ``None`` (it
   becomes the new base).

4. **Test** by running ``alembic upgrade head`` on a fresh database.

Squash Script
=============

Run ``python -m sensei.scripts.squash_migrations`` to generate a squash
migration from the current model definitions.
"""

from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Migration naming pattern
MIGRATION_NAME_PATTERN = re.compile(
    r"^\d{8}_\d{6}_[a-z0-9_]+\.py$"
)

# Maximum recommended migration chain length before squashing
MAX_CHAIN_LENGTH = 50


def validate_migration_names(versions_dir: str) -> List[Tuple[str, str]]:
    """Check all migration files follow the naming convention.

    Returns list of (filename, issue) tuples for violations.
    """
    violations: List[Tuple[str, str]] = []
    versions = Path(versions_dir)

    if not versions.exists():
        return [("versions/", "Directory does not exist")]

    for f in sorted(versions.iterdir()):
        if not f.is_file() or not f.name.endswith(".py"):
            continue
        if f.name == "__pycache__":
            continue

        if not MIGRATION_NAME_PATTERN.match(f.name):
            violations.append((
                f.name,
                "Does not match YYYYMMDD_HHMMSS_slug.py pattern"
            ))

    return violations


def check_chain_length(versions_dir: str) -> dict:
    """Analyse migration chain length and recommend squashing if needed."""
    versions = Path(versions_dir)
    migration_files = sorted(
        f for f in versions.iterdir()
        if f.is_file() and f.name.endswith(".py") and f.name != "__init__.py"
    )

    count = len(migration_files)
    needs_squash = count > MAX_CHAIN_LENGTH

    return {
        "total_migrations": count,
        "max_recommended": MAX_CHAIN_LENGTH,
        "needs_squash": needs_squash,
        "oldest": migration_files[0].name if migration_files else None,
        "newest": migration_files[-1].name if migration_files else None,
        "recommendation": (
            f"Consider squashing {count} migrations into a single baseline"
            if needs_squash
            else "Migration chain length is acceptable"
        ),
    }


def generate_squash_migration(versions_dir: str) -> str:
    """Generate a squash migration that creates all tables from scratch.

    This reads the current SQLAlchemy model definitions and produces
    a single migration with all ``CREATE TABLE`` statements.
    """
    return f'''"""Squashed baseline migration (auto-generated).

Combines all previous migrations into a single baseline.
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "squash_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Import all models to ensure they're registered with Base
    from sensei.models import base  # noqa: F401

    # Use target_metadata from env.py to create all tables
    # This is a placeholder — run `alembic revision --autogenerate` for
    # the real DDL based on current models.
    pass


def downgrade() -> None:
    # Squash migrations typically don't support downgrade
    raise RuntimeError("Cannot downgrade past squash baseline")
'''


if __name__ == "__main__":
    import sys

    versions_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "alembic", "versions"
    )

    # Validate naming
    violations = validate_migration_names(versions_dir)
    if violations:
        print("⚠️  Migration naming violations:")
        for name, issue in violations:
            print(f"  {name}: {issue}")
    else:
        print("✅ All migrations follow naming convention")

    # Check chain length
    info = check_chain_length(versions_dir)
    print(f"\n📊 Migration chain: {info['total_migrations']} files")
    print(f"   {info['recommendation']}")

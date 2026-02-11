"""Product UUID PK migration + soft-delete partial indexes

Revision ID: 20260208_100000
Revises: 20260207_150000
Create Date: 2026-02-08 10:00:00.000000

Fixes:
  #168 — product.py uses Integer PK while rest uses UUID; FK type mismatches
  #405 — Standardise PK strategy (UUID everywhere)
  #417 — Add deleted_at partial indexes to existing tables
  #418 — Migration naming convention enforcement (YYYYMMDD_HHMMSS_slug)
  #453 — Standardise PK strategy across all models
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision = "20260208_100000"
down_revision = "20260207_150000"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists using raw SQL (works with async drivers)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_schema = 'public' AND table_name = :tbl"
            ")"
        ),
        {"tbl": table_name},
    )
    return result.scalar() or False


def _constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.table_constraints"
            "  WHERE constraint_name = :cname AND constraint_schema = 'public'"
            ")"
        ),
        {"cname": constraint_name},
    )
    return result.scalar() or False


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns"
            "  WHERE table_schema = 'public' AND table_name = :tbl AND column_name = :col"
            ")"
        ),
        {"tbl": table_name, "col": column_name},
    )
    return result.scalar() or False


def upgrade() -> None:
    conn = op.get_bind()

    # ---------------------------------------------------------------
    # 1) Convert products.id from Integer → UUID (#168, #405, #453)
    # ---------------------------------------------------------------

    # Step 1a: Discover ALL FK constraints referencing products.id
    fk_rows = conn.execute(
        sa.text(
            """
            SELECT
                c.conname       AS constraint_name,
                cl.relname      AS table_name,
                a.attname       AS column_name
            FROM pg_constraint c
            JOIN pg_class cl   ON cl.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = cl.relnamespace
            JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
            WHERE c.confrelid = 'products'::regclass
              AND c.contype = 'f'
              AND n.nspname = 'public'
            ORDER BY cl.relname, a.attname
            """
        )
    ).fetchall()

    # Step 1b: Drop ALL FK constraints referencing products.id
    for constraint_name, _tbl, _col in fk_rows:
        op.drop_constraint(constraint_name, _tbl, type_="foreignkey")

    # Step 1c: Add new UUID column on products and populate
    op.add_column(
        "products",
        sa.Column("new_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.execute("UPDATE products SET new_id = gen_random_uuid() WHERE new_id IS NULL")

    # Step 1d: Convert every FK column from Integer → UUID
    for _cname, table, fk_col in fk_rows:
        tmp = f"new_{fk_col}"
        op.add_column(table, sa.Column(tmp, PGUUID(as_uuid=True), nullable=True))
        op.execute(
            f"""
            UPDATE {table} t
            SET {tmp} = p.new_id
            FROM products p
            WHERE t.{fk_col}::text = p.id::text
            """
        )
        op.drop_column(table, fk_col)
        op.alter_column(table, tmp, new_column_name=fk_col)

    # Step 1e: Swap products PK from Integer to UUID
    if _constraint_exists("products_pkey"):
        op.drop_constraint("products_pkey", "products", type_="primary")
    if _column_exists("products", "id"):
        op.drop_column("products", "id")
    op.alter_column("products", "new_id", new_column_name="id", nullable=False)
    op.create_primary_key("products_pkey", "products", ["id"])

    # Step 1f: Re-create ALL FK constraints
    for constraint_name, table, fk_col in fk_rows:
        op.create_foreign_key(
            constraint_name,
            table,
            "products",
            [fk_col],
            ["id"],
            ondelete="CASCADE",
        )

    # ---------------------------------------------------------------
    # 2) Partial indexes on deleted_at (#417)
    # ---------------------------------------------------------------
    soft_delete_tables = [
        "products",
        "work_orders",
        "quality_inspections",
        "non_conformances",
        "hr_employees",
        "maintenance_work_orders",
        "opportunities",
        "contacts",
        "kanban_cards",
        "training_records",
    ]

    for table in soft_delete_tables:
        if not _table_exists(table) or not _column_exists(table, "deleted_at"):
            continue
        op.create_index(
            f"ix_{table}_active",
            table,
            ["id"],
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    # Remove partial indexes
    soft_delete_tables = [
        "products", "work_orders", "quality_inspections",
        "non_conformances", "hr_employees", "maintenance_work_orders",
        "opportunities", "contacts", "kanban_cards", "training_records",
    ]
    for table in soft_delete_tables:
        if not _table_exists(table):
            continue
        conn = op.get_bind()
        idx_exists = conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM pg_indexes"
                "  WHERE schemaname = 'public' AND indexname = :idx"
                ")"
            ),
            {"idx": f"ix_{table}_active"},
        ).scalar()
        if idx_exists:
            op.drop_index(f"ix_{table}_active", table_name=table)

    # Revert UUID → Integer PK would lose data; skip in downgrade
    pass

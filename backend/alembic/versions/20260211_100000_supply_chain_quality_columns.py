"""Add supply-chain and quality columns.

- Product: reorder_point, safety_stock
- NonConformance: supplier_id FK, purchase_order_id FK

Revision ID: 20260211_100000
Revises: 20260210_100000
Create Date: 2026-02-11 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "20260211_100000"
down_revision = "20260210_100000"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Existence helpers – query the live catalogue so guards are safe for re-runs
# ---------------------------------------------------------------------------

def _table_exists(table_name: str) -> bool:
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


def _column_exists(table_name: str, column_name: str) -> bool:
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


def _constraint_exists(constraint_name: str) -> bool:
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


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_indexes"
            "  WHERE schemaname = 'public' AND indexname = :idx"
            ")"
        ),
        {"idx": index_name},
    )
    return result.scalar() or False


def upgrade() -> None:
    # -- Product: per-product reorder point and safety stock --
    if _table_exists("products"):
        if not _column_exists("products", "reorder_point"):
            op.add_column(
                "products",
                sa.Column("reorder_point", sa.Numeric(12, 4), nullable=True),
            )
        if not _column_exists("products", "safety_stock"):
            op.add_column(
                "products",
                sa.Column("safety_stock", sa.Numeric(12, 4), nullable=True),
            )

    # -- NonConformance: proper FK to supplier (accounts) and PO --
    if _table_exists("non_conformances"):
        if not _column_exists("non_conformances", "supplier_id"):
            op.add_column(
                "non_conformances",
                sa.Column("supplier_id", UUID(as_uuid=True), nullable=True),
            )
        if not _column_exists("non_conformances", "purchase_order_id"):
            op.add_column(
                "non_conformances",
                sa.Column("purchase_order_id", UUID(as_uuid=True), nullable=True),
            )

        # FK to accounts (supplier) — only if both tables exist
        if (
            _table_exists("accounts")
            and _column_exists("non_conformances", "supplier_id")
            and not _constraint_exists("fk_nc_supplier_id")
        ):
            op.create_foreign_key(
                "fk_nc_supplier_id",
                "non_conformances",
                "accounts",
                ["supplier_id"],
                ["id"],
            )

        # FK to purchase_orders — only if both tables exist
        if (
            _table_exists("purchase_orders")
            and _column_exists("non_conformances", "purchase_order_id")
            and not _constraint_exists("fk_nc_purchase_order_id")
        ):
            op.create_foreign_key(
                "fk_nc_purchase_order_id",
                "non_conformances",
                "purchase_orders",
                ["purchase_order_id"],
                ["id"],
            )

        if _column_exists("non_conformances", "supplier_id") and not _index_exists("ix_nc_supplier_id"):
            op.create_index("ix_nc_supplier_id", "non_conformances", ["supplier_id"])
        if _column_exists("non_conformances", "purchase_order_id") and not _index_exists("ix_nc_purchase_order_id"):
            op.create_index("ix_nc_purchase_order_id", "non_conformances", ["purchase_order_id"])


def downgrade() -> None:
    if _table_exists("non_conformances"):
        if _index_exists("ix_nc_purchase_order_id"):
            op.drop_index("ix_nc_purchase_order_id", table_name="non_conformances")
        if _index_exists("ix_nc_supplier_id"):
            op.drop_index("ix_nc_supplier_id", table_name="non_conformances")
        if _constraint_exists("fk_nc_purchase_order_id"):
            op.drop_constraint("fk_nc_purchase_order_id", "non_conformances", type_="foreignkey")
        if _constraint_exists("fk_nc_supplier_id"):
            op.drop_constraint("fk_nc_supplier_id", "non_conformances", type_="foreignkey")
        if _column_exists("non_conformances", "purchase_order_id"):
            op.drop_column("non_conformances", "purchase_order_id")
        if _column_exists("non_conformances", "supplier_id"):
            op.drop_column("non_conformances", "supplier_id")
    if _table_exists("products"):
        if _column_exists("products", "safety_stock"):
            op.drop_column("products", "safety_stock")
        if _column_exists("products", "reorder_point"):
            op.drop_column("products", "reorder_point")

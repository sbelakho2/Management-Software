"""Finance model fixes.

- WorkOrderCostRollup.work_order_id: String(50) -> Integer + FK to work_orders.id
- BankAccount.currency: default TND -> USD
- BankTransaction.currency: default TND -> USD
- StandardCostRecord: add product_id FK to products

Revision ID: 20260212_100000
Revises: 20260211_100000
Create Date: 2026-02-12 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "20260212_100000"
down_revision = "20260211_100000"
branch_labels = None
depends_on = None


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


def upgrade() -> None:
    # H2: Change work_order_cost_rollups.work_order_id from VARCHAR(50) to INTEGER
    if _table_exists("work_order_cost_rollups"):
        op.execute("DELETE FROM work_order_cost_rollups WHERE work_order_id !~ '^[0-9]+$'")
        op.alter_column(
            "work_order_cost_rollups",
            "work_order_id",
            existing_type=sa.String(50),
            type_=sa.Integer(),
            postgresql_using="work_order_id::integer",
            existing_nullable=False,
        )
        if not _constraint_exists("fk_wo_cost_rollup_work_order") and _table_exists("work_orders"):
            op.create_foreign_key(
                "fk_wo_cost_rollup_work_order",
                "work_order_cost_rollups",
                "work_orders",
                ["work_order_id"],
                ["id"],
                ondelete="CASCADE",
            )

    # M2: Add product_id FK to standard_costs for referential integrity
    if _table_exists("standard_costs"):
        if not _column_exists("standard_costs", "product_id"):
            op.add_column(
                "standard_costs",
                sa.Column("product_id", UUID(as_uuid=True), nullable=True),
            )
            op.create_index("ix_standard_costs_product_id", "standard_costs", ["product_id"])
            if _table_exists("products"):
                op.create_foreign_key(
                    "fk_standard_costs_product",
                    "standard_costs",
                    "products",
                    ["product_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    # M3: Change default currency from TND to USD for bank_accounts and bank_transactions
    if _table_exists("bank_accounts"):
        op.alter_column(
            "bank_accounts",
            "currency",
            existing_type=sa.String(3),
            server_default="USD",
            existing_nullable=False,
        )
    if _table_exists("bank_transactions"):
        op.alter_column(
            "bank_transactions",
            "currency",
            existing_type=sa.String(3),
            server_default="USD",
            existing_nullable=False,
        )


def downgrade() -> None:
    if _table_exists("standard_costs") and _constraint_exists("fk_standard_costs_product"):
        op.drop_constraint("fk_standard_costs_product", "standard_costs", type_="foreignkey")
        op.drop_index("ix_standard_costs_product_id", table_name="standard_costs")
        op.drop_column("standard_costs", "product_id")
    if _table_exists("work_order_cost_rollups") and _constraint_exists("fk_wo_cost_rollup_work_order"):
        op.drop_constraint("fk_wo_cost_rollup_work_order", "work_order_cost_rollups", type_="foreignkey")
        op.alter_column(
            "work_order_cost_rollups",
            "work_order_id",
            existing_type=sa.Integer(),
            type_=sa.String(50),
            postgresql_using="work_order_id::text",
            existing_nullable=False,
        )
    if _table_exists("bank_accounts"):
        op.alter_column(
            "bank_accounts",
            "currency",
            existing_type=sa.String(3),
            server_default="TND",
            existing_nullable=False,
        )
    if _table_exists("bank_transactions"):
        op.alter_column(
            "bank_transactions",
            "currency",
            existing_type=sa.String(3),
            server_default="TND",
            existing_nullable=False,
        )

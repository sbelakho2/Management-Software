"""Add CRM hard FK columns to work_orders table.

Bridges the CRM → Production gap by adding quote_id, sales_order_id,
rfq_id, and account_id foreign keys directly on work_orders.

Revision ID: 20260212_100000
Revises: 20260209_120000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260212_100000"
down_revision = "20260209_120000"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns"
            "  WHERE table_schema = 'public'"
            "    AND table_name = :tbl"
            "    AND column_name = :col"
            ")"
        ),
        {"tbl": table_name, "col": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    columns = [
        ("quote_id", "quotes", "id"),
        ("sales_order_id", "sales_orders", "id"),
        ("rfq_id", "rfqs", "id"),
        ("account_id", "accounts", "id"),
    ]

    for col_name, ref_table, ref_col in columns:
        if not _column_exists("work_orders", col_name):
            op.add_column(
                "work_orders",
                sa.Column(col_name, UUID(as_uuid=True), nullable=True),
            )
            op.create_index(
                f"ix_work_orders_{col_name}",
                "work_orders",
                [col_name],
            )
            op.create_foreign_key(
                f"fk_work_orders_{col_name}_{ref_table}",
                "work_orders",
                ref_table,
                [col_name],
                [ref_col],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    for col_name, ref_table in [
        ("account_id", "accounts"),
        ("rfq_id", "rfqs"),
        ("sales_order_id", "sales_orders"),
        ("quote_id", "quotes"),
    ]:
        if _column_exists("work_orders", col_name):
            op.drop_constraint(
                f"fk_work_orders_{col_name}_{ref_table}",
                "work_orders",
                type_="foreignkey",
            )
            op.drop_index(f"ix_work_orders_{col_name}", table_name="work_orders")
            op.drop_column("work_orders", col_name)

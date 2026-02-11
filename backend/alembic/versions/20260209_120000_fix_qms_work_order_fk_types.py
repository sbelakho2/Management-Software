"""Fix QMS work_order_id FK types: UUID → Integer.

The work_orders.id column is Integer, but three QMS tables declared
work_order_id as UUID.  This migration drops the old UUID column and
FK, then re-creates the column with the correct Integer type and FK.

Affected tables:
  - qms_first_article_inspections
  - qms_self_inspections
  - qms_lab_samples

Revision ID: 20260209_120000
Revises: 20260211_100000
Create Date: 2026-02-09 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260209_120000"
down_revision = "20260212_100000"
branch_labels = None
depends_on = None


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

_TABLES = [
    "qms_first_article_inspections",
    "qms_self_inspections",
    "qms_lab_samples",
]


def upgrade() -> None:
    # After fixing the original migrations to create work_order_id as Integer,
    # the columns are already the correct type. This migration ensures the FK
    # constraint and index exist with our expected naming convention.
    for table in _TABLES:
        # Check if the column is already Integer (from the fixed original migration).
        # If it's UUID (old migration ran before fix), convert it.
        conn = op.get_bind()
        result = conn.execute(
            sa.text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = 'work_order_id'"
            ),
            {"table": table},
        )
        row = result.fetchone()
        if row is None:
            # Column doesn't exist at all — shouldn't happen, but skip safely
            continue

        col_type = row[0].lower()

        if col_type == "integer":
            # Already correct type — just ensure FK and index exist
            fk_name = f"fk_{table}_work_order_id"
            if not _constraint_exists(fk_name):
                op.create_foreign_key(
                    fk_name,
                    table,
                    "work_orders",
                    ["work_order_id"],
                    ["id"],
                )
            idx_name = f"ix_{table}_work_order_id"
            if not _index_exists(idx_name):
                op.create_index(idx_name, table, ["work_order_id"])
        else:
            # UUID column — need to convert
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_constraint(
                    f"{table}_work_order_id_fkey", type_="foreignkey"
                )
                batch_op.drop_index(f"ix_{table}_work_order_id")
                batch_op.drop_column("work_order_id")

            op.add_column(
                table,
                sa.Column("work_order_id", sa.Integer(), nullable=True),
            )
            op.create_foreign_key(
                f"fk_{table}_work_order_id",
                table,
                "work_orders",
                ["work_order_id"],
                ["id"],
            )
            op.create_index(f"ix_{table}_work_order_id", table, ["work_order_id"])


def downgrade() -> None:
    from sqlalchemy.dialects.postgresql import UUID

    for table in reversed(_TABLES):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(
                f"fk_{table}_work_order_id", type_="foreignkey"
            )
            batch_op.drop_index(f"ix_{table}_work_order_id")
            batch_op.drop_column("work_order_id")

        op.add_column(
            table,
            sa.Column("work_order_id", UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            f"{table}_work_order_id_fkey",
            table,
            "work_orders",
            ["work_order_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_work_order_id", table, ["work_order_id"])

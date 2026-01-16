"""Add cost rollup tables

Revision ID: 9ef5d6e7f8a9
Revises: 8d04c5d6e7f8
Create Date: 2026-01-16 23:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9ef5d6e7f8a9"
down_revision: Union[str, None] = "8d04c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "standard_costs",
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("material_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("labor_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("overhead_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku", "effective_date", name="uq_standard_cost_sku_date"),
    )
    op.create_index("ix_standard_costs_sku", "standard_costs", ["sku"], unique=False)

    op.create_table(
        "work_order_cost_rollups",
        sa.Column("work_order_id", sa.String(length=50), nullable=False),
        sa.Column("finished_sku", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("completed_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_material_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_labor_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_overhead_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("relieved_actual_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance_material", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance_labor", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance_overhead", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_order_cost_rollups_work_order_id", "work_order_cost_rollups", ["work_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_work_order_cost_rollups_work_order_id", table_name="work_order_cost_rollups")
    op.drop_table("work_order_cost_rollups")

    op.drop_index("ix_standard_costs_sku", table_name="standard_costs")
    op.drop_table("standard_costs")

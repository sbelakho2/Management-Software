"""Add tool crib tables

Revision ID: 7a8b9c0d1e2f
Revises: 1f2c3d4e5f6a
Create Date: 2026-01-16 15:15:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, None] = "1f2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_tool_items",
        sa.Column("tool_number", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("location_id", sa.String(length=100), nullable=True),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False),
        sa.Column("min_quantity", sa.Integer(), nullable=False),
        sa.Column("life_limit_cycles", sa.Integer(), nullable=True),
        sa.Column("life_used_cycles", sa.Integer(), nullable=False),
        sa.Column("calibration_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_number"),
    )
    op.create_index("ix_maintenance_tool_items_tool_number", "maintenance_tool_items", ["tool_number"], unique=False)

    op.create_table(
        "maintenance_tool_checkouts",
        sa.Column("tool_id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("checked_out_by_id", sa.UUID(), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_by_id", sa.UUID(), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("condition_out", sa.String(length=100), nullable=True),
        sa.Column("condition_in", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["tool_id"], ["maintenance_tool_items.id"], ),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"], ),
        sa.ForeignKeyConstraint(["checked_out_by_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["returned_by_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_tool_checkouts_tool_id", "maintenance_tool_checkouts", ["tool_id"], unique=False)
    op.create_index("ix_maintenance_tool_checkouts_work_order_id", "maintenance_tool_checkouts", ["work_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_maintenance_tool_checkouts_work_order_id", table_name="maintenance_tool_checkouts")
    op.drop_index("ix_maintenance_tool_checkouts_tool_id", table_name="maintenance_tool_checkouts")
    op.drop_table("maintenance_tool_checkouts")

    op.drop_index("ix_maintenance_tool_items_tool_number", table_name="maintenance_tool_items")
    op.drop_table("maintenance_tool_items")

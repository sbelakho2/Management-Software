"""Add maintenance approval fields

Revision ID: 9a0b1c2d3e4f
Revises: 3b4c5d6e7f8a
Create Date: 2026-01-16 15:35:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9a0b1c2d3e4f"
down_revision: Union[str, None] = "3b4c5d6e7f8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("maintenance_work_orders", sa.Column("approval_status", sa.String(length=20), nullable=False, server_default="not_required"))
    op.add_column("maintenance_work_orders", sa.Column("approval_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("maintenance_work_orders", sa.Column("approved_by_id", sa.UUID(), nullable=True))
    op.add_column("maintenance_work_orders", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("maintenance_work_orders", sa.Column("approval_notes", sa.Text(), nullable=True))
    op.create_foreign_key("fk_maintenance_work_orders_approved_by", "maintenance_work_orders", "users", ["approved_by_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_maintenance_work_orders_approved_by", "maintenance_work_orders", type_="foreignkey")
    op.drop_column("maintenance_work_orders", "approval_notes")
    op.drop_column("maintenance_work_orders", "approved_at")
    op.drop_column("maintenance_work_orders", "approved_by_id")
    op.drop_column("maintenance_work_orders", "approval_requested_at")
    op.drop_column("maintenance_work_orders", "approval_status")

"""Add self-inspection tables

Revision ID: 05f6a7b8c9d0
Revises: f4a5b6c7d8e9
Create Date: 2026-01-16 18:30:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "05f6a7b8c9d0"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_self_inspections",
        sa.Column("inspection_number", sa.String(length=50), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_number"),
    )
    op.create_index(
        "ix_qms_self_inspections_work_order_id",
        "qms_self_inspections",
        ["work_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_qms_self_inspections_product_id",
        "qms_self_inspections",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "qms_self_inspection_checks",
        sa.Column("inspection_id", sa.UUID(), nullable=False),
        sa.Column("characteristic", sa.String(length=255), nullable=False),
        sa.Column("specification", sa.String(length=255), nullable=True),
        sa.Column("actual_value", sa.String(length=255), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["qms_self_inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qms_self_inspection_checks_inspection_id",
        "qms_self_inspection_checks",
        ["inspection_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qms_self_inspection_checks_inspection_id", table_name="qms_self_inspection_checks")
    op.drop_table("qms_self_inspection_checks")

    op.drop_index("ix_qms_self_inspections_product_id", table_name="qms_self_inspections")
    op.drop_index("ix_qms_self_inspections_work_order_id", table_name="qms_self_inspections")
    op.drop_table("qms_self_inspections")

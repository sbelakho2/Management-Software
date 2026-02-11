"""Add FAI tables

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-01-16 18:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_first_article_inspections",
        sa.Column("inspection_number", sa.String(length=50), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("work_order_id", sa.Integer(), nullable=True),
        sa.Column("part_number", sa.String(length=100), nullable=False),
        sa.Column("revision", sa.String(length=50), nullable=True),
        sa.Column("drawing_number", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("inspector_id", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"]),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_number"),
    )
    op.create_index(
        "ix_qms_first_article_inspections_product_id",
        "qms_first_article_inspections",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_qms_first_article_inspections_work_order_id",
        "qms_first_article_inspections",
        ["work_order_id"],
        unique=False,
    )

    op.create_table(
        "qms_fai_characteristics",
        sa.Column("inspection_id", sa.UUID(), nullable=False),
        sa.Column("characteristic_number", sa.Integer(), nullable=False),
        sa.Column("requirement", sa.String(length=255), nullable=False),
        sa.Column("nominal", sa.Numeric(18, 6), nullable=True),
        sa.Column("tolerance", sa.String(length=50), nullable=True),
        sa.Column("actual", sa.Numeric(18, 6), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("method", sa.String(length=100), nullable=True),
        sa.Column("tool_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["qms_first_article_inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["qms_gauges.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qms_fai_characteristics_inspection_id",
        "qms_fai_characteristics",
        ["inspection_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qms_fai_characteristics_inspection_id", table_name="qms_fai_characteristics")
    op.drop_table("qms_fai_characteristics")

    op.drop_index("ix_qms_first_article_inspections_work_order_id", table_name="qms_first_article_inspections")
    op.drop_index("ix_qms_first_article_inspections_product_id", table_name="qms_first_article_inspections")
    op.drop_table("qms_first_article_inspections")

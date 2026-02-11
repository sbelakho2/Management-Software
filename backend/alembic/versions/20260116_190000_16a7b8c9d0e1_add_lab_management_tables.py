"""Add lab management tables

Revision ID: 16a7b8c9d0e1
Revises: 05f6a7b8c9d0
Create Date: 2026-01-16 19:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "16a7b8c9d0e1"
down_revision: Union[str, None] = "05f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_lab_test_methods",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("standard", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("lower_spec", sa.Numeric(18, 6), nullable=True),
        sa.Column("upper_spec", sa.Numeric(18, 6), nullable=True),
        sa.Column("target_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
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

    op.create_table(
        "qms_lab_samples",
        sa.Column("sample_number", sa.String(length=50), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("work_order_id", sa.Integer(), nullable=True),
        sa.Column("lot_number", sa.String(length=100), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_by_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"]),
        sa.ForeignKeyConstraint(["collected_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_number"),
    )
    op.create_index(
        "ix_qms_lab_samples_product_id",
        "qms_lab_samples",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_qms_lab_samples_work_order_id",
        "qms_lab_samples",
        ["work_order_id"],
        unique=False,
    )

    op.create_table(
        "qms_lab_test_runs",
        sa.Column("sample_id", sa.UUID(), nullable=False),
        sa.Column("method_id", sa.UUID(), nullable=False),
        sa.Column("result_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_status", sa.String(length=20), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tester_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["sample_id"], ["qms_lab_samples.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["method_id"], ["qms_lab_test_methods.id"]),
        sa.ForeignKeyConstraint(["tester_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qms_lab_test_runs_sample_id",
        "qms_lab_test_runs",
        ["sample_id"],
        unique=False,
    )
    op.create_index(
        "ix_qms_lab_test_runs_method_id",
        "qms_lab_test_runs",
        ["method_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qms_lab_test_runs_method_id", table_name="qms_lab_test_runs")
    op.drop_index("ix_qms_lab_test_runs_sample_id", table_name="qms_lab_test_runs")
    op.drop_table("qms_lab_test_runs")

    op.drop_index("ix_qms_lab_samples_work_order_id", table_name="qms_lab_samples")
    op.drop_index("ix_qms_lab_samples_product_id", table_name="qms_lab_samples")
    op.drop_table("qms_lab_samples")

    op.drop_table("qms_lab_test_methods")

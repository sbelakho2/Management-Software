"""Add AQL sampling tables

Revision ID: 38c9d0e1f2a3
Revises: 27b8c9d0e1f2
Create Date: 2026-01-16 20:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "38c9d0e1f2a3"
down_revision: Union[str, None] = "27b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_aql_sampling_plans",
        sa.Column("plan_code", sa.String(length=50), nullable=False),
        sa.Column("standard", sa.String(length=50), nullable=False),
        sa.Column("inspection_level", sa.String(length=10), nullable=False),
        sa.Column("aql_level", sa.String(length=10), nullable=False),
        sa.Column("lot_size_min", sa.Integer(), nullable=False),
        sa.Column("lot_size_max", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("accept_limit", sa.Integer(), nullable=False),
        sa.Column("reject_limit", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("plan_code"),
    )
    op.create_index(
        "ix_qms_aql_sampling_plans_plan_code",
        "qms_aql_sampling_plans",
        ["plan_code"],
        unique=False,
    )

    op.create_table(
        "qms_aql_lot_inspections",
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("lot_number", sa.String(length=100), nullable=False),
        sa.Column("lot_size", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("defect_count", sa.Integer(), nullable=False),
        sa.Column("accept_limit", sa.Integer(), nullable=False),
        sa.Column("reject_limit", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inspector_id", sa.UUID(), nullable=True),
        sa.Column("inspection_level", sa.String(length=10), nullable=False),
        sa.Column("aql_level", sa.String(length=10), nullable=False),
        sa.Column("defects_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["qms_aql_sampling_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qms_aql_lot_inspections_plan_id",
        "qms_aql_lot_inspections",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_qms_aql_lot_inspections_lot_number",
        "qms_aql_lot_inspections",
        ["lot_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qms_aql_lot_inspections_lot_number", table_name="qms_aql_lot_inspections")
    op.drop_index("ix_qms_aql_lot_inspections_plan_id", table_name="qms_aql_lot_inspections")
    op.drop_table("qms_aql_lot_inspections")

    op.drop_index("ix_qms_aql_sampling_plans_plan_code", table_name="qms_aql_sampling_plans")
    op.drop_table("qms_aql_sampling_plans")

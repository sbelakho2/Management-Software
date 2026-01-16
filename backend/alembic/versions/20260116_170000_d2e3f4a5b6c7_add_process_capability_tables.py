"""Add process capability tables

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-01-16 17:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_process_capability_studies",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("process_name", sa.String(length=255), nullable=False),
        sa.Column("characteristic", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("lsl", sa.Numeric(18, 6), nullable=False),
        sa.Column("usl", sa.Numeric(18, 6), nullable=False),
        sa.Column("target", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
    )

    op.create_table(
        "qms_process_capability_measurements",
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("sample_label", sa.String(length=100), nullable=True),
        sa.Column("measured_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["study_id"], ["qms_process_capability_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qms_process_capability_measurements_study_id",
        "qms_process_capability_measurements",
        ["study_id"],
        unique=False,
    )

    op.create_table(
        "qms_process_capability_results",
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("mean", sa.Numeric(18, 6), nullable=False),
        sa.Column("std_dev", sa.Numeric(18, 6), nullable=False),
        sa.Column("cp", sa.Numeric(18, 6), nullable=False),
        sa.Column("cpk", sa.Numeric(18, 6), nullable=False),
        sa.Column("cpu", sa.Numeric(18, 6), nullable=False),
        sa.Column("cpl", sa.Numeric(18, 6), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["study_id"], ["qms_process_capability_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qms_process_capability_results_study_id",
        "qms_process_capability_results",
        ["study_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qms_process_capability_results_study_id", table_name="qms_process_capability_results")
    op.drop_table("qms_process_capability_results")

    op.drop_index(
        "ix_qms_process_capability_measurements_study_id",
        table_name="qms_process_capability_measurements",
    )
    op.drop_table("qms_process_capability_measurements")

    op.drop_table("qms_process_capability_studies")

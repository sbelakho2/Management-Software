"""Add MSA tables

Revision ID: c1d2e3f4a5b6
Revises: ab12cd34ef56
Create Date: 2026-01-16 16:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_msa_studies",
        sa.Column("gauge_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("study_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("parts_count", sa.Integer(), nullable=False),
        sa.Column("operators_count", sa.Integer(), nullable=False),
        sa.Column("trials_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["gauge_id"], ["qms_gauges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qms_msa_studies_gauge_id", "qms_msa_studies", ["gauge_id"], unique=False)

    op.create_table(
        "qms_msa_measurements",
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("part_id", sa.String(length=100), nullable=False),
        sa.Column("trial_number", sa.Integer(), nullable=False),
        sa.Column("measured_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["study_id"], ["qms_msa_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qms_msa_measurements_study_id", "qms_msa_measurements", ["study_id"], unique=False)
    op.create_index("ix_qms_msa_measurements_operator_id", "qms_msa_measurements", ["operator_id"], unique=False)

    op.create_table(
        "qms_msa_results",
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("repeatability_ev", sa.Numeric(18, 6), nullable=False),
        sa.Column("reproducibility_av", sa.Numeric(18, 6), nullable=False),
        sa.Column("grr", sa.Numeric(18, 6), nullable=False),
        sa.Column("part_variation_pv", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_variation_tv", sa.Numeric(18, 6), nullable=False),
        sa.Column("grr_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("ndc", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["study_id"], ["qms_msa_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qms_msa_results_study_id", "qms_msa_results", ["study_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_qms_msa_results_study_id", table_name="qms_msa_results")
    op.drop_table("qms_msa_results")

    op.drop_index("ix_qms_msa_measurements_operator_id", table_name="qms_msa_measurements")
    op.drop_index("ix_qms_msa_measurements_study_id", table_name="qms_msa_measurements")
    op.drop_table("qms_msa_measurements")

    op.drop_index("ix_qms_msa_studies_gauge_id", table_name="qms_msa_studies")
    op.drop_table("qms_msa_studies")

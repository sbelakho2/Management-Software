"""Add LOTO tables

Revision ID: 1f2c3d4e5f6a
Revises: 0ec05606703a
Create Date: 2026-01-16 15:05:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1f2c3d4e5f6a"
down_revision: Union[str, None] = "0ec05606703a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_loto_procedures",
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requires_verification", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["maintenance_assets.id"], ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_loto_procedures_asset_id", "maintenance_loto_procedures", ["asset_id"], unique=False)

    op.create_table(
        "maintenance_loto_energy_sources",
        sa.Column("procedure_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("isolation_point", sa.String(length=255), nullable=False),
        sa.Column("lock_required", sa.Boolean(), nullable=False),
        sa.Column("verification_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["procedure_id"], ["maintenance_loto_procedures.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_loto_energy_sources_procedure_id", "maintenance_loto_energy_sources", ["procedure_id"], unique=False)

    op.create_table(
        "maintenance_loto_locks",
        sa.Column("procedure_id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("lock_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("applied_by_id", sa.UUID(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_by_id", sa.UUID(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_required", sa.Boolean(), nullable=False),
        sa.Column("verified_by_id", sa.UUID(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["procedure_id"], ["maintenance_loto_procedures.id"], ),
        sa.ForeignKeyConstraint(["asset_id"], ["maintenance_assets.id"], ),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"], ),
        sa.ForeignKeyConstraint(["applied_by_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["released_by_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["verified_by_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lock_number"),
    )
    op.create_index("ix_maintenance_loto_locks_asset_id", "maintenance_loto_locks", ["asset_id"], unique=False)
    op.create_index("ix_maintenance_loto_locks_procedure_id", "maintenance_loto_locks", ["procedure_id"], unique=False)
    op.create_index("ix_maintenance_loto_locks_work_order_id", "maintenance_loto_locks", ["work_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_maintenance_loto_locks_work_order_id", table_name="maintenance_loto_locks")
    op.drop_index("ix_maintenance_loto_locks_procedure_id", table_name="maintenance_loto_locks")
    op.drop_index("ix_maintenance_loto_locks_asset_id", table_name="maintenance_loto_locks")
    op.drop_table("maintenance_loto_locks")

    op.drop_index("ix_maintenance_loto_energy_sources_procedure_id", table_name="maintenance_loto_energy_sources")
    op.drop_table("maintenance_loto_energy_sources")

    op.drop_index("ix_maintenance_loto_procedures_asset_id", table_name="maintenance_loto_procedures")
    op.drop_table("maintenance_loto_procedures")

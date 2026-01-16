"""Add field returns table

Revision ID: 27b8c9d0e1f2
Revises: 16a7b8c9d0e1
Create Date: 2026-01-16 19:30:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "27b8c9d0e1f2"
down_revision: Union[str, None] = "16a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_field_returns",
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("warranty_id", sa.UUID(), nullable=True),
        sa.Column("claim_id", sa.UUID(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("return_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("failure_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("defect_code", sa.String(length=100), nullable=True),
        sa.Column("failure_mode", sa.String(length=255), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column("cost_impact", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["maintenance_assets.id"]),
        sa.ForeignKeyConstraint(["warranty_id"], ["maintenance_asset_warranties.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["maintenance_warranty_claims.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("return_number"),
    )
    op.create_index("ix_maintenance_field_returns_asset_id", "maintenance_field_returns", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_maintenance_field_returns_asset_id", table_name="maintenance_field_returns")
    op.drop_table("maintenance_field_returns")

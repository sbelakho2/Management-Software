"""Add maintenance warranty tables

Revision ID: 3b4c5d6e7f8a
Revises: 7a8b9c0d1e2f
Create Date: 2026-01-16 15:25:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3b4c5d6e7f8a"
down_revision: Union[str, None] = "7a8b9c0d1e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_asset_warranties",
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("warranty_type", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=255), nullable=True),
        sa.Column("vendor_id", sa.UUID(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("claim_contact", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["maintenance_assets.id"], ),
        sa.ForeignKeyConstraint(["vendor_id"], ["accounts.id"], ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_asset_warranties_asset_id", "maintenance_asset_warranties", ["asset_id"], unique=False)

    op.create_table(
        "maintenance_warranty_claims",
        sa.Column("warranty_id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("claim_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("claim_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("approved_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["warranty_id"], ["maintenance_asset_warranties.id"], ),
        sa.ForeignKeyConstraint(["asset_id"], ["maintenance_assets.id"], ),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"], ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_number"),
    )
    op.create_index("ix_maintenance_warranty_claims_asset_id", "maintenance_warranty_claims", ["asset_id"], unique=False)
    op.create_index("ix_maintenance_warranty_claims_warranty_id", "maintenance_warranty_claims", ["warranty_id"], unique=False)
    op.create_index("ix_maintenance_warranty_claims_work_order_id", "maintenance_warranty_claims", ["work_order_id"], unique=False)
    op.create_index("ix_maintenance_warranty_claims_claim_number", "maintenance_warranty_claims", ["claim_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_maintenance_warranty_claims_claim_number", table_name="maintenance_warranty_claims")
    op.drop_index("ix_maintenance_warranty_claims_work_order_id", table_name="maintenance_warranty_claims")
    op.drop_index("ix_maintenance_warranty_claims_warranty_id", table_name="maintenance_warranty_claims")
    op.drop_index("ix_maintenance_warranty_claims_asset_id", table_name="maintenance_warranty_claims")
    op.drop_table("maintenance_warranty_claims")

    op.drop_index("ix_maintenance_asset_warranties_asset_id", table_name="maintenance_asset_warranties")
    op.drop_table("maintenance_asset_warranties")

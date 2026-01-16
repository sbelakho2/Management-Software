"""Add currency settings

Revision ID: 7cf3b4c5d6e7
Revises: 6bf2a3b4c5d6
Create Date: 2026-01-16 22:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7cf3b4c5d6e7"
down_revision: Union[str, None] = "6bf2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finance_currency_settings",
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("reporting_currency", sa.String(length=3), nullable=True),
        sa.Column("allowed_currencies", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fx_source", sa.String(length=50), nullable=True),
        sa.Column("auto_update_rates", sa.Boolean(), nullable=False),
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


def downgrade() -> None:
    op.drop_table("finance_currency_settings")

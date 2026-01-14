"""add project sequences

Revision ID: 0917bb9fc206
Revises: partition_audit_and_condition
Create Date: 2026-01-14 08:53:14.912343+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0917bb9fc206"
down_revision: Union[str, None] = "partition_audit_and_condition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_sequences",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "entity_type"),
    )


def downgrade() -> None:
    op.drop_table("project_sequences")

"""add subtask status

Revision ID: 5d8e7f9a2b3c
Revises: 0917bb9fc206
Create Date: 2026-01-14 10:30:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d8e7f9a2b3c"
down_revision: Union[str, None] = "0917bb9fc206"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subtasks", sa.Column("status", sa.String(length=50), server_default="open", nullable=False))
    op.create_index(op.f("ix_subtasks_status"), "subtasks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subtasks_status"), table_name="subtasks")
    op.drop_column("subtasks", "status")

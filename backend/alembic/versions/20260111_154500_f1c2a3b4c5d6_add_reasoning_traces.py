"""add reasoning traces

Revision ID: f1c2a3b4c5d6
Revises: 8f3a2c1d4b7a
Create Date: 2026-01-11 15:45:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f1c2a3b4c5d6"
down_revision = "8f3a2c1d4b7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reasoning_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("reasoning_id", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "reasoning_id",
            name="uq_reasoning_trace_entity_reasoning",
        ),
    )

    op.create_index("ix_reasoning_trace_entity", "reasoning_traces", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_reasoning_traces_reasoning_id"), "reasoning_traces", ["reasoning_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reasoning_traces_reasoning_id"), table_name="reasoning_traces")
    op.drop_index("ix_reasoning_trace_entity", table_name="reasoning_traces")
    op.drop_table("reasoning_traces")

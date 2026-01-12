"""add data lineage links

Revision ID: 8f3a2c1d4b7a
Revises: cc096eda932a
Create Date: 2026-01-11 13:05:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "8f3a2c1d4b7a"
down_revision = "cc096eda932a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_lineage_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_entity_type", sa.String(length=80), nullable=False),
        sa.Column("source_entity_id", sa.String(length=80), nullable=False),
        sa.Column("target_entity_type", sa.String(length=80), nullable=False),
        sa.Column("target_entity_id", sa.String(length=80), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("reasoning_id", sa.String(length=120), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_entity_type",
            "source_entity_id",
            "relationship_type",
            "target_entity_type",
            "target_entity_id",
            name="uq_data_lineage_link",
        ),
    )

    op.create_index(
        "ix_data_lineage_link_source",
        "data_lineage_links",
        ["source_entity_type", "source_entity_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_data_lineage_link_target",
        "data_lineage_links",
        ["target_entity_type", "target_entity_id", "created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_data_lineage_links_relationship_type"),
        "data_lineage_links",
        ["relationship_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_data_lineage_links_reasoning_id"),
        "data_lineage_links",
        ["reasoning_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_data_lineage_links_reasoning_id"), table_name="data_lineage_links")
    op.drop_index(op.f("ix_data_lineage_links_relationship_type"), table_name="data_lineage_links")
    op.drop_index("ix_data_lineage_link_target", table_name="data_lineage_links")
    op.drop_index("ix_data_lineage_link_source", table_name="data_lineage_links")
    op.drop_table("data_lineage_links")

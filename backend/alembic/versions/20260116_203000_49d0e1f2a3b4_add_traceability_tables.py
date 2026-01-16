"""Add traceability tables

Revision ID: 49d0e1f2a3b4
Revises: 38c9d0e1f2a3
Create Date: 2026-01-16 20:30:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "49d0e1f2a3b4"
down_revision: Union[str, None] = "38c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qms_traceability_matrices",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("work_order_id", sa.Integer(), nullable=True),
        sa.Column("lot_number", sa.String(length=100), nullable=True),
        sa.Column("batch_id", sa.String(length=100), nullable=True),
        sa.Column("external_reference", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qms_traceability_matrices_product_id", "qms_traceability_matrices", ["product_id"], unique=False)
    op.create_index("ix_qms_traceability_matrices_work_order_id", "qms_traceability_matrices", ["work_order_id"], unique=False)
    op.create_index("ix_qms_traceability_matrices_lot_number", "qms_traceability_matrices", ["lot_number"], unique=False)

    op.create_table(
        "qms_traceability_links",
        sa.Column("matrix_id", sa.UUID(), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.Column("reference_id", sa.String(length=100), nullable=False),
        sa.Column("reference_table", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["matrix_id"], ["qms_traceability_matrices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qms_traceability_links_matrix_id", "qms_traceability_links", ["matrix_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_qms_traceability_links_matrix_id", table_name="qms_traceability_links")
    op.drop_table("qms_traceability_links")

    op.drop_index("ix_qms_traceability_matrices_lot_number", table_name="qms_traceability_matrices")
    op.drop_index("ix_qms_traceability_matrices_work_order_id", table_name="qms_traceability_matrices")
    op.drop_index("ix_qms_traceability_matrices_product_id", table_name="qms_traceability_matrices")
    op.drop_table("qms_traceability_matrices")

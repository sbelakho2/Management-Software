"""add kpi tables

Revision ID: a1b2c3d4e5f6
Revises: 20260209_100000
Create Date: 2026-02-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "20260209_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # KPI Definitions
    op.create_table(
        "kpi_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(20), nullable=False, server_default="custom"),
        sa.Column("unit", sa.String(20), nullable=False, server_default="count"),
        sa.Column("direction", sa.String(30), nullable=False, server_default="higher_is_better"),
        sa.Column("data_source", postgresql.JSONB(), nullable=True),
        sa.Column("formula", sa.Text(), nullable=False, server_default=""),
        sa.Column("component_kpis", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("threshold_target", sa.Float(), nullable=True),
        sa.Column("threshold_warning", sa.Float(), nullable=False, server_default="10.0"),
        sa.Column("threshold_critical", sa.Float(), nullable=False, server_default="20.0"),
        sa.Column("threshold_min", sa.Float(), nullable=True),
        sa.Column("threshold_max", sa.Float(), nullable=True),
        sa.Column("decimal_places", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("display_format", sa.String(50), nullable=False, server_default=""),
        sa.Column("owner_role", sa.String(50), nullable=False, server_default=""),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="daily"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("custom_calculator", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_kpi_definitions_active", "kpi_definitions", ["is_active", "category"])

    # KPI Values
    op.create_table(
        "kpi_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kpi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="no_data"),
        sa.Column("dimensions", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_kpi_values_kpi_ts", "kpi_values", ["kpi_id", "recorded_at"])
    op.create_index("ix_kpi_values_kpi_id", "kpi_values", ["kpi_id"])

    # KPI Dashboards
    op.create_table(
        "kpi_dashboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kpi_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("layout", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("default_time_range", sa.String(30), nullable=False, server_default="last_30_days"),
        sa.Column("dimension_filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("owner_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("kpi_dashboards")
    op.drop_index("ix_kpi_values_kpi_ts", table_name="kpi_values")
    op.drop_index("ix_kpi_values_kpi_id", table_name="kpi_values")
    op.drop_table("kpi_values")
    op.drop_index("ix_kpi_definitions_active", table_name="kpi_definitions")
    op.drop_table("kpi_definitions")

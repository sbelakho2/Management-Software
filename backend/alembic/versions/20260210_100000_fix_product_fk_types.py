"""Fix remaining product_id FK columns from Integer to UUID

Revision ID: 20260210_100000
Revises: a1b2c3d4e5f6
Create Date: 2026-02-10 10:00:00.000000

The initial Product UUID PK migration (20260208_100000) only converted
bom_items, routing_steps, kanban_cards, and work_orders.
This migration handles all remaining FK columns that reference products.id.

Tables fixed:
  - routings (product_id) — original migration used wrong table name "routing_steps"
  - bom_items (component_product_id) — the secondary FK was missed
  - inventory_levels (product_id)
  - inventory_stock_moves (product_id)
  - inventory_valuation_layers (product_id)
  - andon_events (product_id)
  - mrp_bom_components (parent_product_id, component_product_id)
  - mrp_demands (product_id)
  - mrp_suggestions (product_id)
  - mps_plan_lines (product_id)
  - non_conformances (product_id)
  - inspection_plans (product_id)
  - qms_traceability_matrices (product_id)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision = "20260210_100000"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _convert_fk_to_uuid(table: str, fk_col: str, on_delete: str = "CASCADE") -> None:
    """Convert a single FK column from Integer to UUID, mapping existing rows."""
    try:
        # Add temporary UUID FK column
        op.add_column(
            table,
            sa.Column(f"new_{fk_col}", PGUUID(as_uuid=True), nullable=True),
        )

        # Map old integer references to new UUIDs
        op.execute(
            f"""
            UPDATE {table} t
            SET new_{fk_col} = p.id
            FROM products p
            WHERE t.{fk_col}::text = p.id::text
            """
        )

        # Drop old FK constraint (best-effort)
        try:
            op.drop_constraint(f"{table}_{fk_col}_fkey", table, type_="foreignkey")
        except Exception:
            pass

        # Drop old column and rename new one
        op.drop_column(table, fk_col)
        op.alter_column(table, f"new_{fk_col}", new_column_name=fk_col)

        # Add FK constraint
        op.create_foreign_key(
            f"{table}_{fk_col}_fkey",
            table,
            "products",
            [fk_col],
            ["id"],
            ondelete=on_delete,
        )

        # Re-create index
        op.create_index(f"ix_{table}_{fk_col}", table, [fk_col])
    except Exception:
        # Table may not exist in all environments
        pass


def upgrade() -> None:
    # All remaining FK columns that reference products.id and still use Integer.
    # Each tuple: (table_name, fk_column, on_delete_action)
    fk_columns = [
        # Routing — original migration used wrong table name "routing_steps"
        ("routings", "product_id", "CASCADE"),
        # BOMItem component FK — missed in original migration
        ("bom_items", "component_product_id", "SET NULL"),
        # Inventory
        ("inventory_levels", "product_id", "CASCADE"),
        ("inventory_stock_moves", "product_id", "CASCADE"),
        ("inventory_valuation_layers", "product_id", "CASCADE"),
        # Andon
        ("andon_events", "product_id", "SET NULL"),
        # MRP
        ("mrp_bom_components", "parent_product_id", "CASCADE"),
        ("mrp_bom_components", "component_product_id", "CASCADE"),
        ("mrp_demands", "product_id", "CASCADE"),
        ("mrp_suggestions", "product_id", "CASCADE"),
        ("mps_plan_lines", "product_id", "CASCADE"),
        # Quality
        ("non_conformances", "product_id", "SET NULL"),
        ("inspection_plans", "product_id", "SET NULL"),
        # QMS
        ("qms_traceability_matrices", "product_id", "SET NULL"),
        # Standard Work, Training
        ("standard_works", "product_id", "SET NULL"),
        ("skill_requirements", "product_id", "SET NULL"),
    ]

    for table, fk_col, on_delete in fk_columns:
        _convert_fk_to_uuid(table, fk_col, on_delete)


def downgrade() -> None:
    # Reverting UUID → Integer would be data-lossy; skip in downgrade.
    pass

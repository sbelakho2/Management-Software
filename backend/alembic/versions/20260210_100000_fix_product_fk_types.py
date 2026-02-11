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


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_schema = 'public' AND table_name = :tbl"
            ")"
        ),
        {"tbl": table_name},
    )
    return result.scalar() or False


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns"
            "  WHERE table_schema = 'public' AND table_name = :tbl AND column_name = :col"
            ")"
        ),
        {"tbl": table_name, "col": column_name},
    )
    return result.scalar() or False


def _constraint_exists(constraint_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.table_constraints"
            "  WHERE constraint_name = :cname AND constraint_schema = 'public'"
            ")"
        ),
        {"cname": constraint_name},
    )
    return result.scalar() or False


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_indexes"
            "  WHERE schemaname = 'public' AND indexname = :idx"
            ")"
        ),
        {"idx": index_name},
    )
    return result.scalar() or False


def _convert_fk_to_uuid(table: str, fk_col: str, on_delete: str = "CASCADE") -> None:
    """Convert a single FK column from Integer to UUID, mapping existing rows."""
    if not _table_exists(table) or not _column_exists(table, fk_col):
        return

    # Check if column is already UUID type
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :tbl AND column_name = :col"
        ),
        {"tbl": table, "col": fk_col},
    )
    row = result.fetchone()
    if row and row[0].lower() == "uuid":
        return  # Already UUID

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

    # Drop old FK constraint if it exists
    fk_name = f"{table}_{fk_col}_fkey"
    if _constraint_exists(fk_name):
        op.drop_constraint(fk_name, table, type_="foreignkey")

    # Drop old column and rename new one
    op.drop_column(table, fk_col)
    op.alter_column(table, f"new_{fk_col}", new_column_name=fk_col)

    # Add FK constraint
    op.create_foreign_key(
        fk_name,
        table,
        "products",
        [fk_col],
        ["id"],
        ondelete=on_delete,
    )

    # Re-create index
    idx_name = f"ix_{table}_{fk_col}"
    if not _index_exists(idx_name):
        op.create_index(idx_name, table, [fk_col])


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
        ("qms_first_article_inspections", "product_id", "SET NULL"),
        ("qms_self_inspections", "product_id", "SET NULL"),
        ("qms_lab_samples", "product_id", "SET NULL"),
        # Standard Work, Training
        ("standard_works", "product_id", "SET NULL"),
        ("skill_requirements", "product_id", "SET NULL"),
    ]

    for table, fk_col, on_delete in fk_columns:
        _convert_fk_to_uuid(table, fk_col, on_delete)


def downgrade() -> None:
    # Reverting UUID → Integer would be data-lossy; skip in downgrade.
    pass

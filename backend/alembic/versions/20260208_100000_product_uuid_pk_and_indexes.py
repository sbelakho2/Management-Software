"""Product UUID PK migration + soft-delete partial indexes

Revision ID: 20260208_100000
Revises: 20260207_150000
Create Date: 2026-02-08 10:00:00.000000

Fixes:
  #168 — product.py uses Integer PK while rest uses UUID; FK type mismatches
  #405 — Standardise PK strategy (UUID everywhere)
  #417 — Add deleted_at partial indexes to existing tables
  #418 — Migration naming convention enforcement (YYYYMMDD_HHMMSS_slug)
  #453 — Standardise PK strategy across all models
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision = "20260208_100000"
down_revision = "20260207_150000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # 1) Convert products.id from Integer → UUID (#168, #405, #453)
    # ---------------------------------------------------------------
    # Step 1a: Add new UUID column
    op.add_column(
        "products",
        sa.Column("new_id", PGUUID(as_uuid=True), nullable=True),
    )

    # Step 1b: Populate new_id with gen_random_uuid()
    op.execute("UPDATE products SET new_id = gen_random_uuid() WHERE new_id IS NULL")

    # Step 1c: Update FK references in dependent tables.
    # We do this by adding new UUID FK columns, mapping old int → new uuid,
    # then dropping old FK columns.
    dependent_tables = [
        ("bom_items", "product_id"),
        ("routing_steps", "product_id"),
        ("kanban_cards", "product_id"),
        ("work_orders", "product_id"),
    ]

    for table, fk_col in dependent_tables:
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
                SET new_{fk_col} = p.new_id
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
                ondelete="CASCADE",
            )
        except Exception:
            # Table may not exist yet in all environments
            pass

    # Step 1d: Drop old integer PK and replace with UUID
    op.drop_constraint("products_pkey", "products", type_="primary")
    op.drop_column("products", "id")
    op.alter_column("products", "new_id", new_column_name="id", nullable=False)
    op.create_primary_key("products_pkey", "products", ["id"])

    # ---------------------------------------------------------------
    # 2) Partial indexes on deleted_at (#417)
    # ---------------------------------------------------------------
    soft_delete_tables = [
        "products",
        "work_orders",
        "quality_inspections",
        "non_conformances",
        "hr_employees",
        "maintenance_work_orders",
        "opportunities",
        "contacts",
        "kanban_cards",
        "training_records",
    ]

    for table in soft_delete_tables:
        try:
            op.create_index(
                f"ix_{table}_active",
                table,
                ["id"],
                postgresql_where=sa.text("deleted_at IS NULL"),
            )
        except Exception:
            # Table or column may not exist
            pass


def downgrade() -> None:
    # Remove partial indexes
    soft_delete_tables = [
        "products", "work_orders", "quality_inspections",
        "non_conformances", "hr_employees", "maintenance_work_orders",
        "opportunities", "contacts", "kanban_cards", "training_records",
    ]
    for table in soft_delete_tables:
        try:
            op.drop_index(f"ix_{table}_active", table_name=table)
        except Exception:
            pass

    # Revert UUID → Integer PK would lose data; skip in downgrade
    pass

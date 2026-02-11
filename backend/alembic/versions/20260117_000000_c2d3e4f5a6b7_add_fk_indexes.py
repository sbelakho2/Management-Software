"""Add missing foreign key indexes.

Revision ID: c2d3e4f5a6b7
Revises: b1f7a8b9c0d1
Create Date: 2026-01-17 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1f7a8b9c0d1"
branch_labels = None
depends_on = None


INDEXES = [
    ("customer_credit_profiles", "account_id"),
    ("customer_credit_profiles", "approved_by_id"),
    ("customer_credit_profiles", "released_by_id"),
    ("customer_credit_profiles", "source_quote_id"),
    ("customer_credit_profiles", "sales_order_id"),
    ("customer_credit_profiles", "received_by_id"),
    ("customer_credit_profiles", "opened_by_id"),
    ("customer_credit_profiles", "resolved_by_id"),
    ("ai_inspection_feedback", "operator_id"),
    ("ai_inspection_feedback", "user_id"),
    ("pii_fields", "subject_id"),
    ("pii_fields", "user_id"),
    ("pii_fields", "field_id"),
    ("pii_fields", "requested_by_id"),
    ("maintenance_assets", "work_center_id"),
    ("maintenance_assets", "station_id"),
    ("maintenance_assets", "parent_asset_id"),
    ("maintenance_assets", "pm_schedule_id"),
    ("maintenance_assets", "assigned_to_id"),
    ("maintenance_assets", "approved_by_id"),
    ("maintenance_assets", "technician_id"),
    ("maintenance_assets", "part_id"),
    ("maintenance_assets", "vendor_id"),
    ("maintenance_assets", "work_order_id"),
    ("maintenance_assets", "recorded_by_id"),
    ("maintenance_assets", "verified_by_id"),
    ("maintenance_assets", "applied_by_id"),
    ("maintenance_assets", "released_by_id"),
    ("maintenance_assets", "checked_out_by_id"),
    ("maintenance_assets", "returned_by_id"),
    ("inventory_warehouses", "warehouse_id"),
    ("inventory_warehouses", "parent_id"),
    ("inventory_warehouses", "source_location_id"),
    ("inventory_warehouses", "destination_location_id"),
    ("qms_documents", "owner_id"),
    ("qms_documents", "current_revision_id"),
    ("qms_documents", "created_by_id"),
    ("qms_documents", "superseded_by_id"),
    ("qms_documents", "related_nc_id"),
    ("qms_documents", "related_capa_id"),
    ("qms_documents", "supplier_id"),
    ("qms_documents", "assigned_to_id"),
    ("qms_documents", "linked_nc_id"),
    ("qms_documents", "linked_capa_id"),
    ("qms_documents", "performed_by_id"),
    ("qms_documents", "inspector_id"),
    ("qms_documents", "tool_id"),
    ("qms_documents", "operator_id"),
    ("qms_documents", "collected_by_id"),
    ("qms_documents", "tester_id"),
    ("qms_documents", "assignee_id"),
    ("qms_documents", "customer_id"),
    ("hr_employees", "user_id"),
    ("hr_employees", "manager_id"),
    ("hr_employees", "employee_id"),
    ("hr_employees", "hiring_manager_id"),
    ("hr_employees", "job_opening_id"),
    ("hr_employees", "appraiser_id"),
    ("hr_employees", "approved_by_id"),
    ("purchase_requisitions", "requested_by_id"),
    ("purchase_requisitions", "supplier_id"),
    ("purchase_requisitions", "submitted_by_id"),
    ("purchase_requisitions", "approved_by_id"),
    ("purchase_requisitions", "rejected_by_id"),
    ("purchase_requisitions", "source_pr_id"),
    ("purchase_requisitions", "sent_by_id"),
    ("purchase_requisitions", "received_by_id"),
    ("purchase_requisitions", "po_id"),
    ("purchase_requisitions", "posted_by_id"),
    ("purchase_requisitions", "paid_by_id"),
    ("purchase_requisitions", "executed_by_id"),
    ("purchase_requisitions", "payment_id"),
    ("purchase_requisitions", "invoice_id"),
    ("mrp_bom_components", "approved_by_id"),
    ("mrp_bom_components", "executed_by_id"),
    ("gl_accounts", "parent_id"),
    ("gl_accounts", "account_id"),
    ("gl_accounts", "closed_by_id"),
    ("gl_accounts", "approved_by_id"),
    ("gl_accounts", "posted_by_id"),
    ("gl_accounts", "reversed_entry_id"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for table, column in INDEXES:
        # Check that both table and column exist before creating the index
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :tbl AND column_name = :col"
            ),
            {"tbl": table, "col": column},
        ).fetchone()
        if exists is None:
            continue
        index_name = f"ix_{table}_{column}"
        op.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})")


def downgrade() -> None:
    for table, column in INDEXES:
        index_name = f"ix_{table}_{column}"
        op.execute(f"DROP INDEX IF EXISTS {index_name}")

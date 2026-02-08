"""Comprehensive migration to create tables for all in-memory services.

This single migration creates the database tables needed to persist data from
63+ in-memory services that currently store state in Python dicts and lose
data on restart.

Checklist items addressed: #1-42, #44-64

Revision ID: 20260209_100000
Revises: 20260208_100000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20260209_100000"
down_revision = "20260208_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =====================================================================
    # A1 — FINANCE TABLES
    # =====================================================================

    # #1 — accounting_ledger.py
    op.create_table(
        "gl_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("gl_accounts.id")),
        sa.Column("balance", sa.Numeric(18, 4), server_default="0"),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_gl_accounts_tenant", "gl_accounts", ["tenant_id"])
    op.create_index("ix_gl_accounts_code", "gl_accounts", ["tenant_id", "code"], unique=True,
                     postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "journal_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entry_number", sa.String(50), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("posted_by", UUID(as_uuid=True)),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_journal_entries_tenant", "journal_entries", ["tenant_id"])

    op.create_table(
        "journal_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entry_id", UUID(as_uuid=True), sa.ForeignKey("journal_entries.id"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("gl_accounts.id"), nullable=False),
        sa.Column("debit", sa.Numeric(18, 4), server_default="0"),
        sa.Column("credit", sa.Numeric(18, 4), server_default="0"),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fiscal_periods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #2 — accounts_payable.py
    op.create_table(
        "ap_invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("invoice_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("paid_amount", sa.Numeric(18, 4), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ap_invoices_tenant", "ap_invoices", ["tenant_id"])

    op.create_table(
        "ap_payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("ap_invoices.id")),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("reference", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "purchase_requisitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pr_number", sa.String(50), nullable=False),
        sa.Column("requestor_id", UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("total_amount", sa.Numeric(18, 4), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("po_number", sa.String(50), nullable=False),
        sa.Column("vendor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("total_amount", sa.Numeric(18, 4), server_default="0"),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("expected_delivery", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("po_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True)),
        sa.Column("description", sa.Text()),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "goods_receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("po_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id")),
        sa.Column("receipt_date", sa.Date, nullable=False),
        sa.Column("received_by", UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), server_default="received"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #3 — accounts_receivable.py
    op.create_table(
        "ar_invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("invoice_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("paid_amount", sa.Numeric(18, 4), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ar_invoices_tenant", "ar_invoices", ["tenant_id"])

    op.create_table(
        "ar_payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("ar_invoices.id")),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("reference", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "credit_memos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # #4 — cost_accounting.py
    op.create_table(
        "cost_centers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("cost_centers.id")),
        sa.Column("budget", sa.Numeric(18, 4), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "cost_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_center_id", UUID(as_uuid=True), sa.ForeignKey("cost_centers.id")),
        sa.Column("target_center_id", UUID(as_uuid=True), sa.ForeignKey("cost_centers.id")),
        sa.Column("allocation_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("period", sa.String(20)),
        sa.Column("amount", sa.Numeric(18, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #5 — fixed_assets.py
    op.create_table(
        "fixed_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_number", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50)),
        sa.Column("acquisition_date", sa.Date, nullable=False),
        sa.Column("acquisition_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("useful_life_months", sa.Integer()),
        sa.Column("salvage_value", sa.Numeric(18, 4), server_default="0"),
        sa.Column("depreciation_method", sa.String(30), server_default="straight_line"),
        sa.Column("accumulated_depreciation", sa.Numeric(18, 4), server_default="0"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("location", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "depreciation_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("fixed_assets.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("posted", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #6 — payroll_labor_costing.py
    op.create_table(
        "labor_rates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rate_type", sa.String(30), nullable=False),
        sa.Column("rate", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "time_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", UUID(as_uuid=True)),
        sa.Column("cost_center_id", UUID(as_uuid=True)),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("hours", sa.Numeric(6, 2), nullable=False),
        sa.Column("rate", sa.Numeric(18, 4)),
        sa.Column("total_cost", sa.Numeric(18, 4)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "payroll_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("batch_number", sa.String(50), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("total_amount", sa.Numeric(18, 4), server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #7 — tax_service.py
    op.create_table(
        "tax_rates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=False),
        sa.Column("tax_type", sa.String(50), nullable=False),
        sa.Column("rate", sa.Numeric(8, 5), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #8 — cost_rollup.py
    op.create_table(
        "cost_rollups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("material_cost", sa.Numeric(18, 4), server_default="0"),
        sa.Column("labor_cost", sa.Numeric(18, 4), server_default="0"),
        sa.Column("overhead_cost", sa.Numeric(18, 4), server_default="0"),
        sa.Column("total_cost", sa.Numeric(18, 4), server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =====================================================================
    # A2 — HR TABLES
    # =====================================================================

    # #9 — compensation_management.py
    op.create_table(
        "compensation_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("base_salary", sa.Numeric(18, 4)),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("pay_grade", sa.String(20)),
        sa.Column("pay_band", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "pay_bands",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("min_salary", sa.Numeric(18, 4)),
        sa.Column("mid_salary", sa.Numeric(18, 4)),
        sa.Column("max_salary", sa.Numeric(18, 4)),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #10 — leave_management.py
    op.create_table(
        "leave_balances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type", sa.String(50), nullable=False),
        sa.Column("balance_days", sa.Numeric(6, 2), server_default="0"),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "leave_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type", sa.String(50), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("days", sa.Numeric(6, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "leave_accrual_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type", sa.String(50), nullable=False),
        sa.Column("accrual_rate", sa.Numeric(6, 2), nullable=False),
        sa.Column("accrual_frequency", sa.String(20), server_default="monthly"),
        sa.Column("max_balance", sa.Numeric(6, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #11 — employee_lifecycle.py
    op.create_table(
        "employee_lifecycle_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("details", JSONB),
        sa.Column("processed_by", UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #12 — recruiting.py
    op.create_table(
        "job_postings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("department", sa.String(100)),
        sa.Column("location", sa.String(200)),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("description", sa.Text()),
        sa.Column("requirements", sa.Text()),
        sa.Column("salary_min", sa.Numeric(18, 4)),
        sa.Column("salary_max", sa.Numeric(18, 4)),
        sa.Column("posted_date", sa.Date),
        sa.Column("closing_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # #13 — staffing_roster.py
    op.create_table(
        "shift_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("shift_start", sa.Time(), nullable=False),
        sa.Column("shift_end", sa.Time(), nullable=False),
        sa.Column("days_of_week", JSONB),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "roster_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", UUID(as_uuid=True), sa.ForeignKey("shift_schedules.id")),
        sa.Column("assignment_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #14 — talent_performance.py
    op.create_table(
        "performance_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", UUID(as_uuid=True)),
        sa.Column("review_period_start", sa.Date),
        sa.Column("review_period_end", sa.Date),
        sa.Column("overall_rating", sa.Numeric(3, 1)),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("comments", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "performance_goals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("target_date", sa.Date),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("progress_pct", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #15 — training_matrix.py (records in existing training model)
    # #16 — hr_cases.py
    op.create_table(
        "hr_cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("case_number", sa.String(50), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True)),
        sa.Column("case_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("description", sa.Text()),
        sa.Column("resolution", sa.Text()),
        sa.Column("assigned_to", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # =====================================================================
    # A3 — PRODUCTION TABLES
    # =====================================================================

    # #17 — mrp_lite.py
    op.create_table(
        "mrp_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("run_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("parameters", JSONB),
        sa.Column("results_summary", JSONB),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "mrp_demand",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("source_type", sa.String(30)),
        sa.Column("source_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "mrp_supply",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("available_date", sa.Date, nullable=False),
        sa.Column("source_type", sa.String(30)),
        sa.Column("source_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #18 — wms_integration.py
    op.create_table(
        "wms_locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("zone", sa.String(50)),
        sa.Column("aisle", sa.String(20)),
        sa.Column("rack", sa.String(20)),
        sa.Column("level", sa.String(20)),
        sa.Column("bin", sa.String(20)),
        sa.Column("location_type", sa.String(30), server_default="storage"),
        sa.Column("capacity", sa.Numeric(12, 4)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "wms_inventory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), sa.ForeignKey("wms_locations.id"), nullable=False),
        sa.Column("lot_number", sa.String(50)),
        sa.Column("serial_number", sa.String(50)),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("uom", sa.String(20), server_default="EA"),
        sa.Column("status", sa.String(20), server_default="available"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "wms_pick_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True)),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("from_location_id", UUID(as_uuid=True), sa.ForeignKey("wms_locations.id")),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("assigned_to", UUID(as_uuid=True)),
        sa.Column("picked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "wms_shipments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_number", sa.String(50), nullable=False),
        sa.Column("carrier", sa.String(100)),
        sa.Column("tracking_number", sa.String(100)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("shipped_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #19 — lot_serial_traceability.py
    op.create_table(
        "lot_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("lot_number", sa.String(50), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("manufactured_date", sa.Date),
        sa.Column("expiry_date", sa.Date),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "genealogy_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("parent_lot_id", UUID(as_uuid=True), sa.ForeignKey("lot_records.id")),
        sa.Column("child_lot_id", UUID(as_uuid=True), sa.ForeignKey("lot_records.id")),
        sa.Column("relationship_type", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "trace_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lot_records.id")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_data", JSONB),
        sa.Column("location", sa.String(200)),
        sa.Column("performed_by", UUID(as_uuid=True)),
        sa.Column("event_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #20 — spc_scrap_rework.py
    op.create_table(
        "spc_measurements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("process_id", sa.String(100), nullable=False),
        sa.Column("characteristic", sa.String(100), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("usl", sa.Numeric(18, 6)),
        sa.Column("lsl", sa.Numeric(18, 6)),
        sa.Column("target", sa.Numeric(18, 6)),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("measured_by", UUID(as_uuid=True)),
    )

    op.create_table(
        "copq_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("record_type", sa.String(30), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True)),
        sa.Column("work_order_id", UUID(as_uuid=True)),
        sa.Column("quantity", sa.Numeric(12, 4)),
        sa.Column("cost", sa.Numeric(18, 4)),
        sa.Column("reason", sa.Text()),
        sa.Column("disposition", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # #21-24 — dispatch_traveler, label_printing, production_scheduling, maintenance_tpm
    # (maintenance tables created in separate migration)
    op.create_table(
        "dispatch_travelers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("traveler_number", sa.String(50), nullable=False),
        sa.Column("work_order_id", UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("operations", JSONB),
        sa.Column("current_operation", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "label_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("template_type", sa.String(30)),
        sa.Column("zpl_template", sa.Text()),
        sa.Column("width_mm", sa.Integer()),
        sa.Column("height_mm", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "production_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", UUID(as_uuid=True)),
        sa.Column("resource_id", UUID(as_uuid=True)),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True)),
        sa.Column("actual_end", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Maintenance tables (#24)
    op.create_table(
        "tpm_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_tag", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location", sa.String(200)),
        sa.Column("category", sa.String(50)),
        sa.Column("status", sa.String(20), server_default="operational"),
        sa.Column("criticality", sa.String(20), server_default="medium"),
        sa.Column("parent_asset_id", UUID(as_uuid=True), sa.ForeignKey("tpm_assets.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "pm_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("tpm_assets.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("frequency_days", sa.Integer(), nullable=False),
        sa.Column("last_performed", sa.Date),
        sa.Column("next_due", sa.Date),
        sa.Column("instructions", sa.Text()),
        sa.Column("assigned_to", UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tpm_work_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("tpm_assets.id"), nullable=False),
        sa.Column("wo_number", sa.String(50), nullable=False),
        sa.Column("type", sa.String(30), server_default="corrective"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("description", sa.Text()),
        sa.Column("assigned_to", UUID(as_uuid=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "downtime_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("tpm_assets.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.Text()),
        sa.Column("downtime_category", sa.String(50)),
        sa.Column("planned", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "spare_parts_inventory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("part_number", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer(), server_default="0"),
        sa.Column("reorder_point", sa.Integer(), server_default="0"),
        sa.Column("unit_cost", sa.Numeric(18, 4)),
        sa.Column("location", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =====================================================================
    # A4 — QUALITY TABLES (#25-29)
    # =====================================================================

    op.create_table(
        "quality_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("doc_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("revision", sa.String(20), server_default="A"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("content", sa.Text()),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("review_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "internal_audits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("audit_number", sa.String(50), nullable=False),
        sa.Column("audit_type", sa.String(50), nullable=False),
        sa.Column("scope", sa.Text()),
        sa.Column("lead_auditor", UUID(as_uuid=True)),
        sa.Column("scheduled_date", sa.Date),
        sa.Column("completed_date", sa.Date),
        sa.Column("status", sa.String(30), server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("audit_id", UUID(as_uuid=True), sa.ForeignKey("internal_audits.id"), nullable=False),
        sa.Column("finding_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("clause_reference", sa.String(50)),
        sa.Column("corrective_action", sa.Text()),
        sa.Column("status", sa.String(30), server_default="open"),
        sa.Column("due_date", sa.Date),
        sa.Column("closed_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "gauge_calibrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("gauge_id", sa.String(50), nullable=False),
        sa.Column("gauge_name", sa.String(200), nullable=False),
        sa.Column("calibration_date", sa.Date, nullable=False),
        sa.Column("next_calibration_date", sa.Date, nullable=False),
        sa.Column("calibrated_by", sa.String(100)),
        sa.Column("status", sa.String(20), server_default="in_tolerance"),
        sa.Column("certificate_number", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "supplier_corrective_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scar_number", sa.String(50), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), nullable=False),
        sa.Column("issue_description", sa.Text()),
        sa.Column("root_cause", sa.Text()),
        sa.Column("corrective_action", sa.Text()),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("due_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "risk_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("risk_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50)),
        sa.Column("severity", sa.Integer()),
        sa.Column("occurrence", sa.Integer()),
        sa.Column("detection", sa.Integer()),
        sa.Column("rpn", sa.Integer()),
        sa.Column("mitigation", sa.Text()),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("owner", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "engineering_change_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("eco_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("change_type", sa.String(30)),
        sa.Column("affected_items", JSONB),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("requested_by", UUID(as_uuid=True)),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # =====================================================================
    # A5 — AI TABLES (#30-37)
    # =====================================================================

    # #30 — hybrid_search (pgvector-backed)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "search_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB),
        sa.Column("token_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.execute("ALTER TABLE search_documents ADD COLUMN IF NOT EXISTS embedding vector(384)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_docs_embedding ON search_documents USING hnsw (embedding vector_cosine_ops)")
    op.create_index("ix_search_docs_tenant_doc", "search_documents", ["tenant_id", "document_id"])

    # #31-37 — reasoning, RAG, anomaly, meta, etc.
    op.create_table(
        "ai_patterns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_type", sa.String(50), nullable=False),
        sa.Column("pattern_key", sa.String(200), nullable=False),
        sa.Column("pattern_data", JSONB, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), server_default="0"),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rag_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB),
        sa.Column("token_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.execute("ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS embedding vector(384)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops)")

    op.create_table(
        "rag_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True)),
        sa.Column("search_id", sa.String(100)),
        sa.Column("relevant", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "anomaly_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20)),
        sa.Column("details", JSONB),
        sa.Column("acknowledged", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ai_training_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("parameters", JSONB),
        sa.Column("metrics", JSONB),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =====================================================================
    # A6-A8 — CORE, EMAIL, NOTIFICATIONS, OTHER (#38-64)
    # =====================================================================

    op.create_table(
        "backup_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("cron_expression", sa.String(50), nullable=False),
        sa.Column("backup_type", sa.String(30), server_default="full"),
        sa.Column("target_path", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "backup_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("schedule_id", UUID(as_uuid=True), sa.ForeignKey("backup_schedules.id")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("file_path", sa.Text()),
        sa.Column("error_message", sa.Text()),
    )

    op.create_table(
        "notification_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("conditions", JSONB),
        sa.Column("channels", JSONB, nullable=False),
        sa.Column("template", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", UUID(as_uuid=True), sa.ForeignKey("notification_rules.id")),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("subject", sa.Text()),
        sa.Column("status", sa.String(20), server_default="sent"),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "email_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("to_address", sa.String(200)),
        sa.Column("subject", sa.String(500)),
        sa.Column("body", sa.Text()),
        sa.Column("template_id", sa.String(100)),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "task_timing_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("metadata", JSONB),
    )

    op.create_table(
        "supplier_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("scope", JSONB),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_tokens_hash", "supplier_tokens", ["token_hash"], unique=True)

    # Generic service state table for remaining services (#41, #42, #44-63)
    op.create_table(
        "service_state",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("state_key", sa.String(200), nullable=False),
        sa.Column("state_data", JSONB, nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_service_state_lookup", "service_state", ["tenant_id", "service_name", "state_key"], unique=True)

    # Redis health state (#40)
    # Health check state is stored in Redis, not PostgreSQL.
    # The health_checks service should use Redis GET/SET with TTL.


def downgrade() -> None:
    # Drop all tables in reverse order to respect FK constraints
    tables = [
        "service_state", "supplier_tokens", "task_timing_sessions",
        "email_drafts", "notification_log", "notification_rules",
        "backup_history", "backup_schedules",
        "ai_training_jobs", "anomaly_alerts", "rag_feedback", "rag_chunks",
        "ai_patterns", "search_documents",
        "engineering_change_orders", "risk_assessments",
        "supplier_corrective_actions", "gauge_calibrations",
        "audit_findings", "internal_audits", "quality_documents",
        "spare_parts_inventory", "downtime_events", "tpm_work_orders",
        "pm_schedules", "tpm_assets",
        "production_schedules", "label_templates", "dispatch_travelers",
        "copq_records", "spc_measurements",
        "trace_events", "genealogy_records", "lot_records",
        "wms_shipments", "wms_pick_tasks", "wms_inventory", "wms_locations",
        "mrp_supply", "mrp_demand", "mrp_runs",
        "hr_cases", "performance_goals", "performance_reviews",
        "roster_assignments", "shift_schedules", "job_postings",
        "leave_accrual_rules", "leave_requests", "leave_balances",
        "pay_bands", "compensation_records",
        "employee_lifecycle_events",
        "cost_rollups", "tax_rates",
        "payroll_batches", "time_entries", "labor_rates",
        "depreciation_schedules", "fixed_assets",
        "cost_allocations", "cost_centers",
        "credit_memos", "ar_payments", "ar_invoices",
        "goods_receipts", "purchase_order_lines", "purchase_orders",
        "purchase_requisitions", "ap_payments", "ap_invoices",
        "fiscal_periods", "journal_lines", "journal_entries", "gl_accounts",
    ]
    for table in tables:
        op.drop_table(table)

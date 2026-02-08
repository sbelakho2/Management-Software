"""Template and registry for creating Alembic migrations for in-memory services.

This module provides:
1. A registry of all 49+ in-memory services that need DB persistence.
2. Table schema templates for each service's data structures.
3. A generator to produce Alembic migration files.

Usage:
    python -m sensei.scripts.generate_persistence_migrations

Checklist items addressed: #416, #449
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TableDefinition:
    """Defines a table to be created for an in-memory service."""

    name: str
    columns: list[str]  # Raw SQL column definitions
    indexes: list[str] = field(default_factory=list)
    comment: str = ""


@dataclass
class ServiceMigration:
    """Migration metadata for a single in-memory service."""

    service_file: str
    module_path: str
    tables: list[TableDefinition]
    category: str  # finance, hr, production, quality, ai, core, etc.
    priority: int = 1  # 1=critical, 2=high, 3=medium


# ---------------------------------------------------------------------------
# Complete registry of all in-memory services needing DB persistence
# ---------------------------------------------------------------------------

SERVICE_MIGRATIONS: list[ServiceMigration] = [
    # ---- A1: Finance ----
    ServiceMigration(
        service_file="accounting_ledger.py",
        module_path="sensei.services.finance.accounting_ledger",
        category="finance",
        priority=1,
        tables=[
            TableDefinition("gl_accounts", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "code VARCHAR(20) NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "account_type VARCHAR(50) NOT NULL",
                "parent_id UUID REFERENCES gl_accounts(id)",
                "balance NUMERIC(18,4) DEFAULT 0",
                "currency VARCHAR(3) DEFAULT 'USD'",
                "is_active BOOLEAN DEFAULT TRUE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ], indexes=["CREATE INDEX ix_gl_accounts_tenant ON gl_accounts(tenant_id)",
                        "CREATE UNIQUE INDEX ix_gl_accounts_code ON gl_accounts(tenant_id, code) WHERE deleted_at IS NULL"]),
            TableDefinition("journal_entries", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "entry_number VARCHAR(50) NOT NULL",
                "entry_date DATE NOT NULL",
                "description TEXT",
                "status VARCHAR(20) DEFAULT 'draft'",
                "posted_by UUID",
                "posted_at TIMESTAMPTZ",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("journal_lines", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "entry_id UUID NOT NULL REFERENCES journal_entries(id)",
                "account_id UUID NOT NULL REFERENCES gl_accounts(id)",
                "debit NUMERIC(18,4) DEFAULT 0",
                "credit NUMERIC(18,4) DEFAULT 0",
                "description TEXT",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("fiscal_periods", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "name VARCHAR(50) NOT NULL",
                "start_date DATE NOT NULL",
                "end_date DATE NOT NULL",
                "status VARCHAR(20) DEFAULT 'open'",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="accounts_payable.py",
        module_path="sensei.services.finance.accounts_payable",
        category="finance",
        priority=1,
        tables=[
            TableDefinition("ap_invoices", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "vendor_id UUID NOT NULL",
                "invoice_number VARCHAR(100) NOT NULL",
                "invoice_date DATE NOT NULL",
                "due_date DATE NOT NULL",
                "amount NUMERIC(18,4) NOT NULL",
                "currency VARCHAR(3) DEFAULT 'USD'",
                "status VARCHAR(20) DEFAULT 'pending'",
                "paid_amount NUMERIC(18,4) DEFAULT 0",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("ap_payments", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "invoice_id UUID REFERENCES ap_invoices(id)",
                "amount NUMERIC(18,4) NOT NULL",
                "payment_date DATE NOT NULL",
                "payment_method VARCHAR(50)",
                "reference VARCHAR(100)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("purchase_orders", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "po_number VARCHAR(50) NOT NULL",
                "vendor_id UUID NOT NULL",
                "status VARCHAR(20) DEFAULT 'draft'",
                "total_amount NUMERIC(18,4) DEFAULT 0",
                "order_date DATE NOT NULL",
                "expected_delivery DATE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("purchase_order_lines", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "po_id UUID NOT NULL REFERENCES purchase_orders(id)",
                "product_id UUID",
                "description TEXT",
                "quantity NUMERIC(12,4) NOT NULL",
                "unit_price NUMERIC(18,4) NOT NULL",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="accounts_receivable.py",
        module_path="sensei.services.finance.accounts_receivable",
        category="finance",
        priority=1,
        tables=[
            TableDefinition("ar_invoices", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "customer_id UUID NOT NULL",
                "invoice_number VARCHAR(100) NOT NULL",
                "invoice_date DATE NOT NULL",
                "due_date DATE NOT NULL",
                "amount NUMERIC(18,4) NOT NULL",
                "currency VARCHAR(3) DEFAULT 'USD'",
                "status VARCHAR(20) DEFAULT 'pending'",
                "paid_amount NUMERIC(18,4) DEFAULT 0",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("ar_payments", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "invoice_id UUID REFERENCES ar_invoices(id)",
                "amount NUMERIC(18,4) NOT NULL",
                "payment_date DATE NOT NULL",
                "payment_method VARCHAR(50)",
                "reference VARCHAR(100)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("credit_memos", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "customer_id UUID NOT NULL",
                "amount NUMERIC(18,4) NOT NULL",
                "reason TEXT",
                "status VARCHAR(20) DEFAULT 'draft'",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="cost_accounting.py",
        module_path="sensei.services.finance.cost_accounting",
        category="finance",
        priority=1,
        tables=[
            TableDefinition("cost_centers", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "code VARCHAR(20) NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "parent_id UUID REFERENCES cost_centers(id)",
                "budget NUMERIC(18,4) DEFAULT 0",
                "is_active BOOLEAN DEFAULT TRUE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("cost_allocations", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "source_center_id UUID REFERENCES cost_centers(id)",
                "target_center_id UUID REFERENCES cost_centers(id)",
                "allocation_pct NUMERIC(5,2) NOT NULL",
                "period VARCHAR(20)",
                "amount NUMERIC(18,4)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="fixed_assets.py",
        module_path="sensei.services.finance.fixed_assets",
        category="finance",
        priority=2,
        tables=[
            TableDefinition("fixed_assets", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "asset_number VARCHAR(50) NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "category VARCHAR(50)",
                "acquisition_date DATE NOT NULL",
                "acquisition_cost NUMERIC(18,4) NOT NULL",
                "useful_life_months INTEGER",
                "salvage_value NUMERIC(18,4) DEFAULT 0",
                "depreciation_method VARCHAR(30) DEFAULT 'straight_line'",
                "accumulated_depreciation NUMERIC(18,4) DEFAULT 0",
                "status VARCHAR(20) DEFAULT 'active'",
                "location VARCHAR(200)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("depreciation_schedules", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "asset_id UUID NOT NULL REFERENCES fixed_assets(id)",
                "period_start DATE NOT NULL",
                "period_end DATE NOT NULL",
                "amount NUMERIC(18,4) NOT NULL",
                "posted BOOLEAN DEFAULT FALSE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),

    # ---- A2: HR ----
    ServiceMigration(
        service_file="compensation_management.py",
        module_path="sensei.services.hr.compensation_management",
        category="hr",
        priority=1,
        tables=[
            TableDefinition("compensation_records", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "employee_id UUID NOT NULL",
                "effective_date DATE NOT NULL",
                "base_salary NUMERIC(18,4)",
                "currency VARCHAR(3) DEFAULT 'USD'",
                "pay_grade VARCHAR(20)",
                "pay_band VARCHAR(20)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("pay_bands", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "name VARCHAR(100) NOT NULL",
                "min_salary NUMERIC(18,4)",
                "mid_salary NUMERIC(18,4)",
                "max_salary NUMERIC(18,4)",
                "currency VARCHAR(3) DEFAULT 'USD'",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="leave_management.py",
        module_path="sensei.services.hr.leave_management",
        category="hr",
        priority=1,
        tables=[
            TableDefinition("leave_balances", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "employee_id UUID NOT NULL",
                "leave_type VARCHAR(50) NOT NULL",
                "balance_days NUMERIC(6,2) DEFAULT 0",
                "year INTEGER NOT NULL",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("leave_requests", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "employee_id UUID NOT NULL",
                "leave_type VARCHAR(50) NOT NULL",
                "start_date DATE NOT NULL",
                "end_date DATE NOT NULL",
                "days NUMERIC(6,2) NOT NULL",
                "status VARCHAR(20) DEFAULT 'pending'",
                "approved_by UUID",
                "reason TEXT",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
        ],
    ),

    # ---- A3: Production ----
    ServiceMigration(
        service_file="maintenance_tpm.py",
        module_path="sensei.services.ops.maintenance_tpm",
        category="production",
        priority=1,
        tables=[
            TableDefinition("tpm_assets", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "asset_tag VARCHAR(50) NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "location VARCHAR(200)",
                "category VARCHAR(50)",
                "status VARCHAR(20) DEFAULT 'operational'",
                "criticality VARCHAR(20) DEFAULT 'medium'",
                "parent_asset_id UUID REFERENCES tpm_assets(id)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("pm_schedules", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "asset_id UUID NOT NULL REFERENCES tpm_assets(id)",
                "name VARCHAR(200) NOT NULL",
                "frequency_days INTEGER NOT NULL",
                "last_performed DATE",
                "next_due DATE",
                "instructions TEXT",
                "assigned_to UUID",
                "is_active BOOLEAN DEFAULT TRUE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("maintenance_work_orders", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "asset_id UUID NOT NULL REFERENCES tpm_assets(id)",
                "wo_number VARCHAR(50) NOT NULL",
                "type VARCHAR(30) DEFAULT 'corrective'",
                "priority VARCHAR(20) DEFAULT 'medium'",
                "status VARCHAR(20) DEFAULT 'open'",
                "description TEXT",
                "assigned_to UUID",
                "started_at TIMESTAMPTZ",
                "completed_at TIMESTAMPTZ",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("downtime_events", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "asset_id UUID NOT NULL REFERENCES tpm_assets(id)",
                "start_time TIMESTAMPTZ NOT NULL",
                "end_time TIMESTAMPTZ",
                "reason TEXT",
                "downtime_category VARCHAR(50)",
                "planned BOOLEAN DEFAULT FALSE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("spare_parts_inventory", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "part_number VARCHAR(50) NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "quantity_on_hand INTEGER DEFAULT 0",
                "reorder_point INTEGER DEFAULT 0",
                "unit_cost NUMERIC(18,4)",
                "location VARCHAR(100)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="wms_integration.py",
        module_path="sensei.services.ops.wms_integration",
        category="production",
        priority=1,
        tables=[
            TableDefinition("wms_locations", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "code VARCHAR(50) NOT NULL",
                "zone VARCHAR(50)",
                "aisle VARCHAR(20)",
                "rack VARCHAR(20)",
                "level VARCHAR(20)",
                "bin VARCHAR(20)",
                "location_type VARCHAR(30) DEFAULT 'storage'",
                "capacity NUMERIC(12,4)",
                "is_active BOOLEAN DEFAULT TRUE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("wms_inventory", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "product_id UUID NOT NULL",
                "location_id UUID NOT NULL REFERENCES wms_locations(id)",
                "lot_number VARCHAR(50)",
                "serial_number VARCHAR(50)",
                "quantity NUMERIC(12,4) NOT NULL",
                "uom VARCHAR(20) DEFAULT 'EA'",
                "status VARCHAR(20) DEFAULT 'available'",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),

    # ---- A4: Quality ----
    ServiceMigration(
        service_file="qms_quality.py",
        module_path="sensei.services.quality.qms_quality",
        category="quality",
        priority=1,
        tables=[
            TableDefinition("quality_documents", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "doc_number VARCHAR(50) NOT NULL",
                "title VARCHAR(300) NOT NULL",
                "doc_type VARCHAR(50) NOT NULL",
                "revision VARCHAR(20) DEFAULT 'A'",
                "status VARCHAR(30) DEFAULT 'draft'",
                "content TEXT",
                "approved_by UUID",
                "approved_at TIMESTAMPTZ",
                "review_date DATE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("internal_audits", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "audit_number VARCHAR(50) NOT NULL",
                "audit_type VARCHAR(50) NOT NULL",
                "scope TEXT",
                "lead_auditor UUID",
                "scheduled_date DATE",
                "completed_date DATE",
                "status VARCHAR(30) DEFAULT 'planned'",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("audit_findings", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "audit_id UUID NOT NULL REFERENCES internal_audits(id)",
                "finding_type VARCHAR(30) NOT NULL",
                "severity VARCHAR(20) NOT NULL",
                "description TEXT NOT NULL",
                "clause_reference VARCHAR(50)",
                "corrective_action TEXT",
                "status VARCHAR(30) DEFAULT 'open'",
                "due_date DATE",
                "closed_date DATE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("gauge_calibrations", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "gauge_id VARCHAR(50) NOT NULL",
                "gauge_name VARCHAR(200) NOT NULL",
                "calibration_date DATE NOT NULL",
                "next_calibration_date DATE NOT NULL",
                "calibrated_by VARCHAR(100)",
                "status VARCHAR(20) DEFAULT 'in_tolerance'",
                "certificate_number VARCHAR(100)",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),

    # ---- A5: AI ----
    ServiceMigration(
        service_file="reasoning_engine.py",
        module_path="sensei.services.ai.reasoning_engine",
        category="ai",
        priority=2,
        tables=[
            TableDefinition("ai_known_patterns", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "pattern_key VARCHAR(200) NOT NULL",
                "pattern_data JSONB NOT NULL",
                "confidence NUMERIC(5,4) DEFAULT 0",
                "last_seen TIMESTAMPTZ",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("ai_causal_chains", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "cause TEXT NOT NULL",
                "effect TEXT NOT NULL",
                "strength NUMERIC(5,4) DEFAULT 0",
                "evidence_count INTEGER DEFAULT 0",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("ai_meta_cognitive_log", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "event_type VARCHAR(50) NOT NULL",
                "payload JSONB",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="self_improving_rag.py",
        module_path="sensei.services.ai.self_improving_rag",
        category="ai",
        priority=1,
        tables=[
            TableDefinition("rag_chunks", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "document_id VARCHAR(200) NOT NULL",
                "content TEXT NOT NULL",
                "metadata JSONB",
                "embedding vector(384)",
                "token_count INTEGER",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ], indexes=[
                "CREATE INDEX ix_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops)",
                "CREATE INDEX ix_rag_chunks_document ON rag_chunks(tenant_id, document_id)",
            ]),
            TableDefinition("rag_feedback", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "chunk_id UUID REFERENCES rag_chunks(id)",
                "search_id VARCHAR(100)",
                "relevant BOOLEAN NOT NULL",
                "comment TEXT",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),

    # ---- A6: Core ----
    ServiceMigration(
        service_file="backup_scheduler.py",
        module_path="sensei.services.core.backup_scheduler",
        category="core",
        priority=2,
        tables=[
            TableDefinition("backup_schedules", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "cron_expression VARCHAR(50) NOT NULL",
                "backup_type VARCHAR(30) DEFAULT 'full'",
                "target_path TEXT",
                "is_active BOOLEAN DEFAULT TRUE",
                "last_run_at TIMESTAMPTZ",
                "next_run_at TIMESTAMPTZ",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
            TableDefinition("backup_history", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "schedule_id UUID REFERENCES backup_schedules(id)",
                "started_at TIMESTAMPTZ NOT NULL",
                "completed_at TIMESTAMPTZ",
                "status VARCHAR(20) DEFAULT 'running'",
                "size_bytes BIGINT",
                "file_path TEXT",
                "error_message TEXT",
            ]),
        ],
    ),
    ServiceMigration(
        service_file="notification_trigger.py",
        module_path="sensei.services.core.notification_trigger",
        category="core",
        priority=2,
        tables=[
            TableDefinition("notification_rules", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "name VARCHAR(200) NOT NULL",
                "event_type VARCHAR(100) NOT NULL",
                "conditions JSONB",
                "channels JSONB NOT NULL",
                "template TEXT",
                "is_active BOOLEAN DEFAULT TRUE",
                "created_at TIMESTAMPTZ DEFAULT NOW()",
                "updated_at TIMESTAMPTZ DEFAULT NOW()",
                "deleted_at TIMESTAMPTZ",
            ]),
            TableDefinition("notification_log", [
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "tenant_id UUID NOT NULL",
                "rule_id UUID REFERENCES notification_rules(id)",
                "channel VARCHAR(50) NOT NULL",
                "recipient VARCHAR(200) NOT NULL",
                "subject TEXT",
                "status VARCHAR(20) DEFAULT 'sent'",
                "sent_at TIMESTAMPTZ DEFAULT NOW()",
            ]),
        ],
    ),
]


def get_all_table_names() -> list[str]:
    """Return all table names across all service migrations."""
    names: list[str] = []
    for svc in SERVICE_MIGRATIONS:
        for table in svc.tables:
            names.append(table.name)
    return names


def get_migrations_by_category(category: str) -> list[ServiceMigration]:
    """Filter migrations by category."""
    return [m for m in SERVICE_MIGRATIONS if m.category == category]


def generate_create_table_sql(table: TableDefinition) -> str:
    """Generate CREATE TABLE SQL for a single table definition."""
    cols = ",\n    ".join(table.columns)
    sql = f"CREATE TABLE IF NOT EXISTS {table.name} (\n    {cols}\n);"
    if table.indexes:
        idx_sql = "\n".join(f"{idx};" for idx in table.indexes)
        sql += f"\n{idx_sql}"
    return sql


def generate_migration_file(
    service: ServiceMigration,
    revision_id: str | None = None,
) -> str:
    """Generate a complete Alembic migration file for a service."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = service.service_file.replace(".py", "").replace("_", "-")
    rev = revision_id or f"auto_{timestamp}"

    upgrade_stmts: list[str] = []
    downgrade_stmts: list[str] = []

    for table in service.tables:
        upgrade_stmts.append(generate_create_table_sql(table))
        downgrade_stmts.append(f"op.execute('DROP TABLE IF EXISTS {table.name} CASCADE')")

    upgrade_sql = "\n\n    ".join(
        f"op.execute('''{stmt}''')" for stmt in upgrade_stmts
    )
    downgrade_sql = "\n    ".join(downgrade_stmts)

    return textwrap.dedent(f'''\
        """Persist {service.service_file} in-memory data to PostgreSQL.

        Revision ID: {rev}
        Category: {service.category}
        Module: {service.module_path}
        """

        from alembic import op
        import sqlalchemy as sa

        revision = "{rev}"
        down_revision = None  # Set to previous revision in chain
        branch_labels = None
        depends_on = None


        def upgrade() -> None:
            {upgrade_sql}


        def downgrade() -> None:
            {downgrade_sql}
    ''')


def print_migration_summary() -> None:
    """Print a summary of all needed migrations."""
    categories = sorted(set(m.category for m in SERVICE_MIGRATIONS))
    total_tables = sum(len(m.tables) for m in SERVICE_MIGRATIONS)
    print(f"Total services: {len(SERVICE_MIGRATIONS)}")
    print(f"Total tables: {total_tables}")
    print()
    for cat in categories:
        cat_migrations = get_migrations_by_category(cat)
        cat_tables = sum(len(m.tables) for m in cat_migrations)
        print(f"  {cat}: {len(cat_migrations)} services, {cat_tables} tables")
        for m in cat_migrations:
            table_names = ", ".join(t.name for t in m.tables)
            print(f"    - {m.service_file}: {table_names}")


if __name__ == "__main__":
    print_migration_summary()

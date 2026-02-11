"""Add HR indexes and updated_at indexes

Adds:
- Index on hr_employees.manager_id (#110)
- Index on hr_employees.department (#110)
- Index on hr_employees.status (#110)
- Index on hr_employees.hire_date (#111)
- Composite index on hr_employees(status, department) (#110)
- Index on updated_at for key tables (#112)

Revision ID: 20260207_140000
Revises: 20260207_130000
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "20260207_140000"
down_revision = "20260207_130000"
branch_labels = None
depends_on = None


def _safe_create_index(name: str, table: str, columns: list, **kwargs) -> None:
    """Create an index inside a savepoint so failures don't abort the transaction."""
    conn = op.get_bind()
    try:
        conn.execute(sa.text("SAVEPOINT _idx"))
        op.create_index(name, table, columns, **kwargs)
        conn.execute(sa.text("RELEASE SAVEPOINT _idx"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT _idx"))


def _safe_drop_index(name: str, table: str) -> None:
    """Drop an index inside a savepoint so failures don't abort the transaction."""
    conn = op.get_bind()
    try:
        conn.execute(sa.text("SAVEPOINT _idx"))
        op.drop_index(name, table)
        conn.execute(sa.text("RELEASE SAVEPOINT _idx"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT _idx"))


def upgrade() -> None:
    """Add HR model indexes and updated_at indexes."""

    # ── HR Employee indexes (#110, #111) ──
    _safe_create_index("ix_hr_employees_manager_id", "hr_employees", ["manager_id"])
    _safe_create_index("ix_hr_employees_department", "hr_employees", ["department"])
    _safe_create_index("ix_hr_employees_status", "hr_employees", ["status"])
    _safe_create_index("ix_hr_employees_hire_date", "hr_employees", ["hire_date"])
    _safe_create_index(
        "ix_hr_employees_status_dept",
        "hr_employees",
        ["status", "department"],
    )

    # ── updated_at indexes for "recently modified" queries (#112) ──
    tables_needing_updated_at_index = [
        "users",
        "accounts",
        "contacts",
        "opportunities",
        "rfqs",
        "quotes",
        "hr_employees",
        "hr_job_openings",
        "hr_job_applications",
        "hr_appraisals",
        "knowledge_documents",
        "knowledge_chunks",
        "audit_log",
    ]

    for table in tables_needing_updated_at_index:
        _safe_create_index(
            f"ix_{table}_updated_at",
            table,
            ["updated_at"],
        )


def downgrade() -> None:
    """Remove HR and updated_at indexes."""
    tables_needing_updated_at_index = [
        "users",
        "accounts",
        "contacts",
        "opportunities",
        "rfqs",
        "quotes",
        "hr_employees",
        "hr_job_openings",
        "hr_job_applications",
        "hr_appraisals",
        "knowledge_documents",
        "knowledge_chunks",
        "audit_log",
    ]

    for table in tables_needing_updated_at_index:
        try:
            op.drop_index(f"ix_{table}_updated_at", table)
        except Exception:
            pass

    try:
        op.drop_index("ix_hr_employees_status_dept", "hr_employees")
    except Exception:
        pass
    try:
        op.drop_index("ix_hr_employees_hire_date", "hr_employees")
    except Exception:
        pass
    try:
        op.drop_index("ix_hr_employees_status", "hr_employees")
    except Exception:
        pass
    try:
        op.drop_index("ix_hr_employees_department", "hr_employees")
    except Exception:
        pass
    try:
        op.drop_index("ix_hr_employees_manager_id", "hr_employees")
    except Exception:
        pass

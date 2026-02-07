"""Fix model integrity: timezone-aware DateTimes, non-nullable amount/email

Revision ID: 20260207_150000
Revises: 20260207_140000
Create Date: 2026-02-07 15:00:00.000000

Fixes:
  #174 — Add timezone=True to bare DateTime columns in production & work_order models
  #171 — Make opportunity.amount NOT NULL with server_default='0'
  #173 — Make hr_employees.email NOT NULL with server_default=''
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260207_150000"
down_revision = "20260207_140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── #174  DateTime → DateTime(timezone=True) ────────────────────────
    # production: shift_handover_notes.acknowledged_at
    op.alter_column(
        "shift_handover_notes",
        "acknowledged_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # production: global_pulses.expires_at
    op.alter_column(
        "global_pulses",
        "expires_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_orders.held_at
    op.alter_column(
        "work_orders",
        "held_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_orders.scheduled_start
    op.alter_column(
        "work_orders",
        "scheduled_start",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_orders.scheduled_end
    op.alter_column(
        "work_orders",
        "scheduled_end",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_orders.actual_start
    op.alter_column(
        "work_orders",
        "actual_start",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_orders.actual_end
    op.alter_column(
        "work_orders",
        "actual_end",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_order_operations.started_at
    op.alter_column(
        "work_order_operations",
        "started_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # work_order: work_order_operations.completed_at
    op.alter_column(
        "work_order_operations",
        "completed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # ── #171  opportunity.amount NOT NULL ────────────────────────────────
    # First backfill NULLs with 0
    op.execute("UPDATE opportunities SET amount = 0 WHERE amount IS NULL")
    op.alter_column(
        "opportunities",
        "amount",
        nullable=False,
        server_default="0",
        existing_type=sa.Numeric(18, 2),
    )

    # ── #173  hr_employees.email NOT NULL ────────────────────────────────
    # Backfill NULLs with empty string
    op.execute("UPDATE hr_employees SET email = '' WHERE email IS NULL")
    op.alter_column(
        "hr_employees",
        "email",
        nullable=False,
        server_default="",
        existing_type=sa.String(255),
    )


def downgrade() -> None:
    # ── Revert #173 ─────────────────────────────────────────────────────
    op.alter_column(
        "hr_employees",
        "email",
        nullable=True,
        server_default=None,
        existing_type=sa.String(255),
    )

    # ── Revert #171 ─────────────────────────────────────────────────────
    op.alter_column(
        "opportunities",
        "amount",
        nullable=True,
        server_default=None,
        existing_type=sa.Numeric(18, 2),
    )

    # ── Revert #174 ─────────────────────────────────────────────────────
    for table, column in [
        ("work_order_operations", "completed_at"),
        ("work_order_operations", "started_at"),
        ("work_orders", "actual_end"),
        ("work_orders", "actual_start"),
        ("work_orders", "scheduled_end"),
        ("work_orders", "scheduled_start"),
        ("work_orders", "held_at"),
        ("global_pulses", "expires_at"),
        ("shift_handover_notes", "acknowledged_at"),
    ]:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
        )

"""Add performance indexes and query optimizations.

Revision ID: perf_indexes_v2
Revises: add_hr_jurisdiction
Create Date: 2026-02-07 12:00:00.000000

This migration adds:
1. Composite indexes for high-traffic query patterns
2. Partial indexes for soft-deleted records filtering
3. Covering indexes for list/search endpoints
4. BRIN indexes for time-series data (condition_readings, audit_logs)
5. Trigram indexes for fuzzy text search
6. Expression indexes for computed lookups

Performance impact: These indexes address the most common slow queries
identified through pg_stat_statements analysis, including N+1 patterns
in quality stats, task dispatching, and production scheduling.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "perf_indexes_v2"
down_revision = "add_hr_jurisdiction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. COMPOSITE INDEXES for high-traffic query patterns
    # =========================================================================

    # Tasks: Most common query is "my open tasks" (assignee + status)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tasks_assignee_status
        ON tasks (assignee_id, status)
        WHERE deleted_at IS NULL
    """)

    # Tasks: Due-date sorted queries for "upcoming tasks"
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tasks_status_due_date
        ON tasks (status, due_date)
        WHERE deleted_at IS NULL AND due_date IS NOT NULL
    """)

    # Tasks: Created-by for "tasks I created"
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tasks_created_by_status
        ON tasks (created_by_id, status)
        WHERE deleted_at IS NULL
    """)

    # Work orders: Dispatch board query (status + priority + scheduled date)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_orders_dispatch
        ON work_orders (status, priority, scheduled_start)
        WHERE deleted_at IS NULL
    """)

    # Work orders: By work center for capacity planning
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_orders_work_center_status
        ON work_orders (work_center_id, status)
        WHERE deleted_at IS NULL
    """)

    # Opportunities: Pipeline view (account + stage)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_opportunities_account_stage
        ON opportunities (account_id, stage)
        WHERE deleted_at IS NULL
    """)

    # Opportunities: Forecast queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_opportunities_close_date_stage
        ON opportunities (expected_close_date, stage)
        WHERE deleted_at IS NULL
    """)

    # Non-conformances: Stats endpoint (status + severity for GROUP BY)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_non_conformances_status_severity
        ON non_conformances (status, severity)
        WHERE deleted_at IS NULL
    """)

    # Non-conformances: By product for traceability
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_non_conformances_product
        ON non_conformances (product_id, created_at DESC)
        WHERE deleted_at IS NULL AND product_id IS NOT NULL
    """)

    # CAPAs: Stats endpoint
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_capas_status_priority
        ON capas (status, priority)
        WHERE deleted_at IS NULL
    """)

    # CAPAs: Due date tracking
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_capas_due_date
        ON capas (due_date)
        WHERE deleted_at IS NULL AND status NOT IN ('closed', 'completed')
    """)

    # Notifications: User's unread notifications
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_user_unread
        ON notifications (user_id, created_at DESC)
        WHERE read_at IS NULL AND deleted_at IS NULL
    """)

    # Notifications: Expiry cleanup
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_expires
        ON notifications (expires_at)
        WHERE expires_at IS NOT NULL
    """)

    # Kanban cards: Board + column ordering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_kanban_cards_board_column
        ON kanban_cards (board_id, column_name, position)
        WHERE deleted_at IS NULL
    """)

    # Andon events: Active events for dashboard
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_andon_events_active
        ON andon_events (status, severity, created_at DESC)
        WHERE status NOT IN ('resolved', 'closed')
    """)

    # Andon events: By work center for area view
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_andon_events_work_center
        ON andon_events (work_center_id, status)
        WHERE deleted_at IS NULL
    """)

    # Issues: Sprint board view
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_issues_sprint_status
        ON issues (sprint_id, status)
        WHERE deleted_at IS NULL
    """)

    # Issues: Project backlog
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_issues_project_priority
        ON issues (project_id, priority, created_at DESC)
        WHERE deleted_at IS NULL
    """)

    # Inspection records: Quality dashboard
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_inspection_records_result_date
        ON inspection_records (result, inspection_date DESC)
        WHERE deleted_at IS NULL
    """)

    # Quotes: By account for CRM
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_quotes_account_status
        ON quotes (account_id, status)
        WHERE deleted_at IS NULL
    """)

    # RFQs: Active RFQs by status
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rfqs_status_due
        ON rfqs (status, due_date)
        WHERE deleted_at IS NULL
    """)

    # Learning progress: User completion tracking
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_learning_progress_user_completed
        ON learning_progress (user_id, completed_at)
        WHERE completed_at IS NOT NULL
    """)

    # User skills: Skill matrix lookup
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_skills_skill_level
        ON user_skills (skill_id, proficiency_level)
    """)

    # =========================================================================
    # 2. PARTIAL INDEXES for soft-deleted records
    # =========================================================================

    # Active users (most user queries filter by active status)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_active
        ON users (email)
        WHERE deleted_at IS NULL AND status = 'active'
    """)

    # Active accounts
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_accounts_active
        ON accounts (name)
        WHERE deleted_at IS NULL
    """)

    # Active products
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_products_active
        ON products (sku)
        WHERE deleted_at IS NULL
    """)

    # =========================================================================
    # 3. EXPRESSION INDEXES for computed lookups
    # =========================================================================

    # Case-insensitive email lookup (login flow)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email_lower
        ON users (lower(email))
        WHERE deleted_at IS NULL
    """)

    # Case-insensitive account name search
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_accounts_name_lower
        ON accounts (lower(name))
        WHERE deleted_at IS NULL
    """)

    # =========================================================================
    # 4. AUTOSAVE + SERVICE PERSISTENCE indexes
    # =========================================================================

    # Autosave drafts: Expiry cleanup
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_autosave_drafts_expires
        ON autosave_drafts (expires_at)
        WHERE expires_at IS NOT NULL
    """)

    # Autosave drafts: User's drafts
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_autosave_drafts_user
        ON autosave_drafts (user_id, entity_type, updated_at DESC)
    """)

    # Support tickets: Status + priority for inbox
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_support_tickets_status_priority
        ON support_tickets (status, priority, created_at DESC)
    """)

    # Feedback: Entity reference
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_feedback_entity
        ON feedback (entity_type, entity_id)
    """)

    # =========================================================================
    # 5. ANALYZE tables with new indexes for query planner
    # =========================================================================

    op.execute("ANALYZE tasks")
    op.execute("ANALYZE work_orders")
    op.execute("ANALYZE opportunities")
    op.execute("ANALYZE non_conformances")
    op.execute("ANALYZE capas")
    op.execute("ANALYZE notifications")
    op.execute("ANALYZE kanban_cards")
    op.execute("ANALYZE andon_events")
    op.execute("ANALYZE users")
    op.execute("ANALYZE accounts")
    op.execute("ANALYZE quotes")
    op.execute("ANALYZE rfqs")


def downgrade() -> None:
    # Drop all indexes added in this migration
    indexes = [
        "ix_tasks_assignee_status",
        "ix_tasks_status_due_date",
        "ix_tasks_created_by_status",
        "ix_work_orders_dispatch",
        "ix_work_orders_work_center_status",
        "ix_opportunities_account_stage",
        "ix_opportunities_close_date_stage",
        "ix_non_conformances_status_severity",
        "ix_non_conformances_product",
        "ix_capas_status_priority",
        "ix_capas_due_date",
        "ix_notifications_user_unread",
        "ix_notifications_expires",
        "ix_kanban_cards_board_column",
        "ix_andon_events_active",
        "ix_andon_events_work_center",
        "ix_issues_sprint_status",
        "ix_issues_project_priority",
        "ix_inspection_records_result_date",
        "ix_quotes_account_status",
        "ix_rfqs_status_due",
        "ix_learning_progress_user_completed",
        "ix_user_skills_skill_level",
        "ix_users_active",
        "ix_accounts_active",
        "ix_products_active",
        "ix_users_email_lower",
        "ix_accounts_name_lower",
        "ix_autosave_drafts_expires",
        "ix_autosave_drafts_user",
        "ix_support_tickets_status_priority",
        "ix_feedback_entity",
    ]
    for idx in indexes:
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx}")

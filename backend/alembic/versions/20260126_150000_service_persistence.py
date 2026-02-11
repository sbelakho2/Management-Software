"""Add service persistence tables

Revision ID: 20260126_150000_svc_persist
Revises: 20260117_000000_c2d3e4f5a6b7_add_fk_indexes
Create Date: 2026-01-26 15:00:00.000000

Adds database tables for services that previously used in-memory storage:
- saved_views: User-created filter/view configurations
- autosave_drafts: Work-in-progress draft storage
- support_tickets: Support inbox tickets
- user_feedback: User feedback submissions
- routing_rules: Ticket routing configuration
- a3_lite_records: Lightweight A3 problem records
- escalation_policies: Custom escalation configurations
- escalation_thresholds: Custom escalation thresholds
- mentions: @mention tracking
- entity_assignments: Assignment tracking
- tasks_from_comments: Tasks created from comment mentions
- smart_ingestion_jobs: Ingestion job tracking
- smart_ingestion_documents: Ingestion document metadata
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_150000_svc_persist'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Saved Views
    # ==========================================================================
    op.create_table(
        'saved_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='private'),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conditions', postgresql.JSONB(), nullable=True),
        sa.Column('sort_fields', postgresql.JSONB(), nullable=True),
        sa.Column('columns', postgresql.JSONB(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(50), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_saved_views_owner_entity', 'saved_views', ['owner_id', 'entity_type'])
    op.create_index('ix_saved_views_visibility', 'saved_views', ['visibility'])
    op.create_index('ix_saved_views_entity_type', 'saved_views', ['entity_type'])

    # ==========================================================================
    # Autosave Drafts
    # ==========================================================================
    op.create_table(
        'autosave_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('draft_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('form_id', sa.String(255), nullable=True),
        sa.Column('route', sa.String(500), nullable=True),
        sa.Column('content', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('current_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('base_version', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovery_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_drafts_user_entity', 'autosave_drafts', ['user_id', 'entity_type', 'entity_id'])
    op.create_index('ix_drafts_user_active', 'autosave_drafts', ['user_id', 'status'])
    op.create_index('ix_drafts_status', 'autosave_drafts', ['status'])

    op.create_table(
        'autosave_draft_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('draft_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('auto_saved', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('save_reason', sa.String(255), nullable=True),
        sa.Column('changed_fields', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['draft_id'], ['autosave_drafts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('draft_id', 'version_number', name='uq_draft_version'),
    )
    op.create_index('ix_draft_versions_draft', 'autosave_draft_versions', ['draft_id'])

    # ==========================================================================
    # Support Inbox
    # ==========================================================================
    op.create_table(
        'support_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='open'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reporter_email', sa.String(255), nullable=True),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_breached', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('first_response_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalation_level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('related_entity_type', sa.String(50), nullable=True),
        sa.Column('related_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('custom_fields', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('ix_support_tickets_priority', 'support_tickets', ['priority'])
    op.create_index('ix_support_tickets_category', 'support_tickets', ['category'])
    op.create_index('ix_support_tickets_reporter', 'support_tickets', ['reporter_id'])
    op.create_index('ix_support_tickets_assignee', 'support_tickets', ['assignee_id'])
    op.create_index('ix_tickets_status_priority', 'support_tickets', ['status', 'priority'])
    op.create_index('ix_tickets_sla', 'support_tickets', ['sla_due_at', 'sla_breached'])

    op.create_table(
        'support_ticket_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_resolution', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ticket_comments_ticket', 'support_ticket_comments', ['ticket_id'])

    op.create_table(
        'user_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('feedback_type', sa.String(30), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('page_url', sa.String(500), nullable=True),
        sa.Column('feature_area', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='new'),
        sa.Column('linked_ticket_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['linked_ticket_id'], ['support_tickets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_feedback_user', 'user_feedback', ['user_id'])

    op.create_table(
        'support_routing_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('conditions', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('target', sa.String(50), nullable=False),
        sa.Column('target_config', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'a3_lite_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_ticket_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('problem_statement', sa.Text(), nullable=True),
        sa.Column('current_state', sa.Text(), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('countermeasures', sa.Text(), nullable=True),
        sa.Column('target_state', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='open'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['source_ticket_id'], ['support_tickets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_a3_lite_ticket', 'a3_lite_records', ['source_ticket_id'])
    op.create_index('ix_a3_lite_owner', 'a3_lite_records', ['owner_id'])
    op.create_index('ix_a3_lite_status', 'a3_lite_records', ['status'])

    # ==========================================================================
    # Escalation Policies
    # ==========================================================================
    op.create_table(
        'escalation_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('conditions', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('escalation_levels', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('auto_create_task', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_escalation_policy_name'),
    )
    op.create_index('ix_escalation_policies_target', 'escalation_policies', ['target_type'])
    op.create_index('ix_escalation_policies_active', 'escalation_policies', ['is_active'])

    op.create_table(
        'escalation_thresholds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('threshold_key', sa.String(100), nullable=False),
        sa.Column('value_numeric', sa.Numeric(15, 4), nullable=True),
        sa.Column('value_hours', sa.Integer(), nullable=True),
        sa.Column('value_config', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'threshold_key', name='uq_escalation_threshold'),
    )

    # ==========================================================================
    # Mentions & Assignments
    # ==========================================================================
    op.create_table(
        'mentions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mentioned_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mentions_user', 'mentions', ['mentioned_user_id'])
    op.create_index('ix_mentions_user_unread', 'mentions', ['mentioned_user_id', 'is_read'])
    op.create_index('ix_mentions_source', 'mentions', ['source_type', 'source_id'])

    op.create_table(
        'entity_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assignee_type', sa.String(20), nullable=False, server_default='user'),
        sa.Column('assigned_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='active'),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assignments_entity', 'entity_assignments', ['entity_type', 'entity_id'])
    op.create_index('ix_assignments_assignee', 'entity_assignments', ['assignee_id'])
    op.create_index('ix_assignments_assignee_active', 'entity_assignments', ['assignee_id', 'status'])

    op.create_table(
        'tasks_from_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_comment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tasks_from_comments_task', 'tasks_from_comments', ['task_id'])

    # ==========================================================================
    # Smart Ingestion
    # ==========================================================================
    op.create_table(
        'smart_ingestion_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('source_id', sa.String(500), nullable=True),
        sa.Column('source_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extracted_entities', postgresql.JSONB(), nullable=True),
        sa.Column('created_entity_ids', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ingestion_jobs_status', 'smart_ingestion_jobs', ['status'])

    op.create_table(
        'smart_ingestion_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(1000), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('extracted_fields', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['smart_ingestion_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ingestion_documents_job', 'smart_ingestion_documents', ['job_id'])


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting foreign keys)
    op.drop_table('smart_ingestion_documents')
    op.drop_table('smart_ingestion_jobs')
    op.drop_table('tasks_from_comments')
    op.drop_table('entity_assignments')
    op.drop_table('mentions')
    op.drop_table('escalation_thresholds')
    op.drop_table('escalation_policies')
    op.drop_table('a3_lite_records')
    op.drop_table('support_routing_rules')
    op.drop_table('user_feedback')
    op.drop_table('support_ticket_comments')
    op.drop_table('support_tickets')
    op.drop_table('autosave_draft_versions')
    op.drop_table('autosave_drafts')
    op.drop_table('saved_views')

"""
Repository layer for database persistence.

Provides async database access for service state persistence.
"""

from sensei.repositories.autosave_drafts_repo import (
    AutosaveDraftsRepository,
    get_autosave_drafts_repo,
)
from sensei.repositories.escalation_policy_repo import (
    EscalationPolicyRepository,
    get_escalation_policy_repo,
)
from sensei.repositories.mentions_assignments_repo import (
    MentionsAssignmentsRepository,
    get_mentions_assignments_repo,
)
from sensei.repositories.saved_views_repo import (
    SavedViewsRepository,
    get_saved_views_repo,
)
from sensei.repositories.smart_ingestion_repo import (
    SmartIngestionRepository,
    get_smart_ingestion_repo,
)
from sensei.repositories.support_tickets_repo import (
    SupportTicketsRepository,
    get_support_tickets_repo,
)


__all__ = [
    # Autosave Drafts
    "AutosaveDraftsRepository",
    "get_autosave_drafts_repo",
    # Escalation Policy
    "EscalationPolicyRepository",
    "get_escalation_policy_repo",
    # Mentions and Assignments
    "MentionsAssignmentsRepository",
    "get_mentions_assignments_repo",
    # Saved Views
    "SavedViewsRepository",
    "get_saved_views_repo",
    # Smart Ingestion
    "SmartIngestionRepository",
    "get_smart_ingestion_repo",
    # Support Tickets
    "SupportTicketsRepository",
    "get_support_tickets_repo",
]

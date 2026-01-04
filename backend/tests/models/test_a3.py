"""
Tests for A3 problem-solving models.

Tests:
- A3 model fields and defaults
- A3Section model
- A3 status workflow
- Enums
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.models.a3 import (
    A3,
    A3Priority,
    A3Section,
    A3SectionType,
    A3Status,
    A3Type,
)


class TestA3Model:
    """Tests for the A3 model."""

    def test_a3_required_fields(self):
        """A3 should require a3_number and title."""
        a3 = A3(
            a3_number="A3-2024-001",
            title="Reduce Scrap Rate in CNC Cell",
        )
        assert a3.a3_number == "A3-2024-001"
        assert a3.title == "Reduce Scrap Rate in CNC Cell"

    def test_a3_explicit_status(self):
        """A3 status should be set when explicitly provided."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            status=A3Status.DRAFT.value,
        )
        assert a3.status == A3Status.DRAFT.value

    def test_a3_explicit_priority(self):
        """A3 priority should be set when explicitly provided."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            priority=A3Priority.MEDIUM.value,
        )
        assert a3.priority == A3Priority.MEDIUM.value

    def test_a3_explicit_a3_type(self):
        """A3 type should be set when explicitly provided."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            a3_type=A3Type.PROBLEM_SOLVING.value,
        )
        assert a3.a3_type == A3Type.PROBLEM_SOLVING.value

    def test_a3_is_open_true_for_active_statuses(self):
        """is_open should be True for non-closed statuses."""
        for status in [
            A3Status.DRAFT,
            A3Status.IN_PROGRESS,
            A3Status.REVIEW,
            A3Status.APPROVED,
            A3Status.IMPLEMENTED,
        ]:
            a3 = A3(
                a3_number="A3-001",
                title="Test",
                status=status.value,
            )
            assert a3.is_open is True

    def test_a3_is_open_false_for_closed_statuses(self):
        """is_open should be False for closed statuses."""
        for status in [
            A3Status.CLOSED,
            A3Status.CANCELLED,
        ]:
            a3 = A3(
                a3_number="A3-001",
                title="Test",
                status=status.value,
            )
            assert a3.is_open is False

    def test_a3_is_overdue_true_when_past_target(self):
        """is_overdue should be True when target_completion_date is past and still open."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            target_completion_date=datetime.now(timezone.utc) - timedelta(days=1),
            status=A3Status.IN_PROGRESS.value,
        )
        assert a3.is_overdue is True

    def test_a3_is_overdue_false_when_closed(self):
        """is_overdue should be False when closed even if past target."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            target_completion_date=datetime.now(timezone.utc) - timedelta(days=1),
            status=A3Status.CLOSED.value,
        )
        assert a3.is_overdue is False

    def test_a3_is_overdue_false_when_no_target(self):
        """is_overdue should be False when no target_completion_date."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            status=A3Status.IN_PROGRESS.value,
        )
        assert a3.is_overdue is False

    def test_a3_team_members_jsonb(self):
        """team_members should accept a list."""
        user_ids = [str(uuid4()), str(uuid4())]
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            team_members=user_ids,
        )
        assert a3.team_members == user_ids

    def test_a3_tags_jsonb(self):
        """tags should accept a list."""
        tags = ["quality", "safety", "lean"]
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            tags=tags,
        )
        assert a3.tags == tags

    def test_a3_department_field(self):
        """department field should be settable."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            department="Manufacturing",
        )
        assert a3.department == "Manufacturing"

    def test_a3_progress_percentage_field(self):
        """progress_percentage should be settable."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            progress_percentage=50,
        )
        assert a3.progress_percentage == 50

    def test_a3_version_field(self):
        """version should be settable."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            version=1,
        )
        assert a3.version == 1

    def test_a3_ownership_ids(self):
        """A3 should accept author_id, sponsor_id, coach_id."""
        author_id = uuid4()
        sponsor_id = uuid4()
        coach_id = uuid4()
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            author_id=author_id,
            sponsor_id=sponsor_id,
            coach_id=coach_id,
        )
        assert a3.author_id == author_id
        assert a3.sponsor_id == sponsor_id
        assert a3.coach_id == coach_id

    def test_a3_date_fields(self):
        """A3 date fields should be settable."""
        now = datetime.now(timezone.utc)
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            started_date=now,
            target_completion_date=now + timedelta(days=30),
        )
        assert a3.started_date == now
        assert a3.target_completion_date == now + timedelta(days=30)

    def test_a3_approval_fields(self):
        """A3 approval fields should be settable."""
        approver_id = uuid4()
        now = datetime.now(timezone.utc)
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            approved_by_id=approver_id,
            approved_date=now,
        )
        assert a3.approved_by_id == approver_id
        assert a3.approved_date == now

    def test_a3_related_entity_fields(self):
        """A3 should accept related entity fields."""
        entity_id = uuid4()
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            related_entity_type="work_order",
            related_entity_id=entity_id,
        )
        assert a3.related_entity_type == "work_order"
        assert a3.related_entity_id == entity_id

    def test_a3_is_yokoten_candidate(self):
        """is_yokoten_candidate should be settable."""
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            is_yokoten_candidate=True,
        )
        assert a3.is_yokoten_candidate is True

    def test_a3_custom_fields_jsonb(self):
        """custom_fields should accept a dict."""
        custom = {"key1": "value1", "key2": 123}
        a3 = A3(
            a3_number="A3-001",
            title="Test",
            custom_fields=custom,
        )
        assert a3.custom_fields == custom


class TestA3StatusEnum:
    """Tests for A3Status enum."""

    def test_all_statuses_defined(self):
        """All expected A3 statuses should be defined."""
        assert A3Status.DRAFT.value == "draft"
        assert A3Status.IN_PROGRESS.value == "in_progress"
        assert A3Status.REVIEW.value == "review"
        assert A3Status.APPROVED.value == "approved"
        assert A3Status.IMPLEMENTED.value == "implemented"
        assert A3Status.CLOSED.value == "closed"
        assert A3Status.CANCELLED.value == "cancelled"


class TestA3TypeEnum:
    """Tests for A3Type enum."""

    def test_all_types_defined(self):
        """All expected A3 types should be defined."""
        assert A3Type.PROBLEM_SOLVING.value == "problem_solving"
        assert A3Type.PROPOSAL.value == "proposal"
        assert A3Type.STATUS_REPORT.value == "status_report"
        assert A3Type.STRATEGY.value == "strategy"


class TestA3PriorityEnum:
    """Tests for A3Priority enum."""

    def test_all_priorities_defined(self):
        """All expected A3 priorities should be defined."""
        assert A3Priority.CRITICAL.value == "critical"
        assert A3Priority.HIGH.value == "high"
        assert A3Priority.MEDIUM.value == "medium"
        assert A3Priority.LOW.value == "low"


class TestA3SectionModel:
    """Tests for the A3Section model."""

    def test_a3_section_required_fields(self):
        """A3Section should require a3_id, section_type, section_name, section_order."""
        a3_id = uuid4()
        section = A3Section(
            a3_id=a3_id,
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
        )
        assert section.a3_id == a3_id
        assert section.section_type == A3SectionType.BACKGROUND.value
        assert section.section_name == "Background"
        assert section.section_order == 1

    def test_a3_section_content_field(self):
        """A3Section content should be settable."""
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
            content="This describes the background context.",
        )
        assert section.content == "This describes the background context."

    def test_a3_section_is_complete_field(self):
        """A3Section is_complete should be settable."""
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
            is_complete=True,
        )
        assert section.is_complete is True

    def test_a3_section_guidance_field(self):
        """A3Section guidance should be settable."""
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
            guidance="Provide context about the problem.",
        )
        assert section.guidance == "Provide context about the problem."

    def test_a3_section_structured_content_jsonb(self):
        """A3Section structured_content should accept a dict."""
        structured = {"five_whys": ["Why 1", "Why 2", "Why 3"]}
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.ROOT_CAUSE.value,
            section_name="Root Cause Analysis",
            section_order=4,
            structured_content=structured,
        )
        assert section.structured_content == structured

    def test_a3_section_attachments_jsonb(self):
        """A3Section attachments should accept a list."""
        attachments = [{"file_id": str(uuid4()), "name": "diagram.png"}]
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
            attachments=attachments,
        )
        assert section.attachments == attachments

    def test_a3_section_comments_jsonb(self):
        """A3Section comments should accept a list."""
        comments = [{"user_id": str(uuid4()), "text": "Good analysis"}]
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.ANALYSIS.value,
            section_name="Analysis",
            section_order=3,
            comments=comments,
        )
        assert section.comments == comments

    def test_a3_section_completion_tracking(self):
        """A3Section should track completion info."""
        user_id = uuid4()
        completed_at = datetime.now(timezone.utc)
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
            is_complete=True,
            completed_at=completed_at,
            completed_by_id=user_id,
        )
        assert section.is_complete is True
        assert section.completed_at == completed_at
        assert section.completed_by_id == user_id

    def test_a3_section_version_field(self):
        """A3Section version should be settable."""
        section = A3Section(
            a3_id=uuid4(),
            section_type=A3SectionType.BACKGROUND.value,
            section_name="Background",
            section_order=1,
            version=2,
        )
        assert section.version == 2


class TestA3SectionTypeEnum:
    """Tests for A3SectionType enum."""

    def test_problem_solving_section_types_defined(self):
        """Problem-solving A3 section types should be defined."""
        assert A3SectionType.BACKGROUND.value == "background"
        assert A3SectionType.CURRENT_CONDITION.value == "current_condition"
        assert A3SectionType.GOAL.value == "goal"
        assert A3SectionType.ROOT_CAUSE.value == "root_cause"
        assert A3SectionType.COUNTERMEASURES.value == "countermeasures"
        assert A3SectionType.IMPLEMENTATION_PLAN.value == "implementation_plan"
        assert A3SectionType.FOLLOW_UP.value == "follow_up"

    def test_proposal_section_types_defined(self):
        """Proposal A3 section types should be defined."""
        assert A3SectionType.PROBLEM_STATEMENT.value == "problem_statement"
        assert A3SectionType.ANALYSIS.value == "analysis"
        assert A3SectionType.PROPOSED_SOLUTION.value == "proposed_solution"
        assert A3SectionType.COST_BENEFIT.value == "cost_benefit"
        assert A3SectionType.TIMELINE.value == "timeline"
        assert A3SectionType.RISKS.value == "risks"

    def test_custom_section_type_defined(self):
        """Custom section type should be defined."""
        assert A3SectionType.CUSTOM.value == "custom"


class TestA3SectionOrdering:
    """Tests for A3 section ordering logic."""

    def test_sections_have_correct_order(self):
        """Sections should have sequential order values."""
        a3_id = uuid4()
        sections = [
            A3Section(a3_id=a3_id, section_type=A3SectionType.BACKGROUND.value, section_name="Background", section_order=1),
            A3Section(a3_id=a3_id, section_type=A3SectionType.CURRENT_CONDITION.value, section_name="Current Condition", section_order=2),
            A3Section(a3_id=a3_id, section_type=A3SectionType.GOAL.value, section_name="Goal", section_order=3),
            A3Section(a3_id=a3_id, section_type=A3SectionType.ROOT_CAUSE.value, section_name="Root Cause Analysis", section_order=4),
            A3Section(a3_id=a3_id, section_type=A3SectionType.COUNTERMEASURES.value, section_name="Countermeasures", section_order=5),
            A3Section(a3_id=a3_id, section_type=A3SectionType.IMPLEMENTATION_PLAN.value, section_name="Implementation Plan", section_order=6),
            A3Section(a3_id=a3_id, section_type=A3SectionType.FOLLOW_UP.value, section_name="Follow-Up", section_order=7),
        ]
        
        for i, section in enumerate(sections, start=1):
            assert section.section_order == i

    def test_problem_solving_a3_sections(self):
        """Problem-solving A3 should have 7 standard sections."""
        a3_id = uuid4()
        section_types = [
            A3SectionType.BACKGROUND,
            A3SectionType.CURRENT_CONDITION,
            A3SectionType.GOAL,
            A3SectionType.ROOT_CAUSE,
            A3SectionType.COUNTERMEASURES,
            A3SectionType.IMPLEMENTATION_PLAN,
            A3SectionType.FOLLOW_UP,
        ]
        
        sections = []
        for i, st in enumerate(section_types, start=1):
            sections.append(
                A3Section(
                    a3_id=a3_id,
                    section_type=st.value,
                    section_name=st.name.replace("_", " ").title(),
                    section_order=i,
                )
            )
        
        assert len(sections) == 7
        assert sections[0].section_type == A3SectionType.BACKGROUND.value
        assert sections[-1].section_type == A3SectionType.FOLLOW_UP.value

    def test_proposal_a3_sections(self):
        """Proposal A3 should use proposal-specific section types."""
        a3_id = uuid4()
        section_types = [
            A3SectionType.BACKGROUND,
            A3SectionType.PROBLEM_STATEMENT,
            A3SectionType.ANALYSIS,
            A3SectionType.PROPOSED_SOLUTION,
            A3SectionType.COST_BENEFIT,
            A3SectionType.TIMELINE,
            A3SectionType.RISKS,
        ]
        
        sections = []
        for i, st in enumerate(section_types, start=1):
            sections.append(
                A3Section(
                    a3_id=a3_id,
                    section_type=st.value,
                    section_name=st.name.replace("_", " ").title(),
                    section_order=i,
                )
            )
        
        assert len(sections) == 7
        assert sections[1].section_type == A3SectionType.PROBLEM_STATEMENT.value
        assert sections[-1].section_type == A3SectionType.RISKS.value

"""
Comprehensive tests for the Today Screen (Manager GPS) service.

Tests cover all aspects of the TodayScreenService:
- Priority management (top 3 forced selection)
- Risk tracking by category
- Commitment management with due dates
- Abnormality detection and resolution
- Micro-drill questions for recall
- LSW checklist summary
- Quick metrics aggregation
- Full today screen data assembly
"""

import pytest
from datetime import datetime, timedelta, date
from uuid import uuid4, UUID

from sensei.core.time import utcnow_naive

from sensei.services.ops.today_screen import (
    TodayScreenService,
    TodayScreenData,
    Priority,
    Risk,
    Commitment,
    Abnormality,
    MicroDrill,
    LSWChecklistSummary,
    QuickMetric,
    RiskCategory,
    AbnormalityType,
    CommitmentType,
    PriorityLevel,
    LSWChecklistStatus,
    get_today_screen_service,
    reset_today_screen_service,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """Provide a fresh TodayScreenService instance."""
    reset_today_screen_service()
    return get_today_screen_service()


@pytest.fixture
def sample_user_id():
    """Provide a sample user ID."""
    return uuid4()


@pytest.fixture
def sample_user_name():
    """Provide a sample user name."""
    return "Test User"


# ============================================================================
# Priority Management Tests
# ============================================================================


class TestPriorityManagement:
    """Tests for priority management functionality."""

    def test_add_priority(self, service, sample_user_id):
        """Test adding an individual priority."""
        priority = service.add_priority(
            user_id=sample_user_id,
            entity_type="quote",
            entity_id=uuid4(),
            title="Urgent quote",
            priority_level=PriorityLevel.HIGH,
            description="Needs immediate attention",
            due_date=date.today() + timedelta(days=1),
        )

        assert priority.id is not None
        assert priority.title == "Urgent quote"
        assert priority.priority_level == PriorityLevel.HIGH
        assert priority.is_user_selected is False  # Not part of top 3

    def test_add_multiple_priorities(self, service, sample_user_id):
        """Test adding multiple priorities for a user."""
        for i in range(5):
            service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Priority {i+1}",
                priority_level=PriorityLevel.HIGH if i < 2 else PriorityLevel.LOW,
            )

        priorities = service.get_user_priorities(sample_user_id)
        assert len(priorities) == 5

    def test_set_top_priorities(self, service, sample_user_id):
        """Test setting top 3 priorities from existing priorities."""
        # First add some priorities
        priority_ids = []
        for i in range(5):
            p = service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Priority {i+1}",
                priority_level=PriorityLevel.MEDIUM,
            )
            priority_ids.append(p.id)

        # Select top 3
        selected = service.set_top_priorities(sample_user_id, priority_ids[:3])

        assert len(selected) == 3
        for i, p in enumerate(selected):
            assert p.is_user_selected is True
            assert p.rank == i + 1

    def test_set_top_priorities_max_three(self, service, sample_user_id):
        """Test that setting more than 3 priorities raises error."""
        priority_ids = [uuid4() for _ in range(4)]

        with pytest.raises(ValueError, match="Maximum 3"):
            service.set_top_priorities(sample_user_id, priority_ids)

    def test_set_top_priorities_replaces_existing(self, service, sample_user_id):
        """Test that setting new priorities replaces existing ones."""
        # Add priorities
        priority_ids = []
        for i in range(6):
            p = service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Priority {i+1}",
                priority_level=PriorityLevel.MEDIUM,
            )
            priority_ids.append(p.id)

        # Set first batch
        service.set_top_priorities(sample_user_id, priority_ids[:3])

        # Set second batch
        selected = service.set_top_priorities(sample_user_id, priority_ids[3:6])

        assert len(selected) == 3
        # First batch should no longer be selected
        all_priorities = service.get_user_priorities(sample_user_id)
        for p in all_priorities:
            if p.id in priority_ids[:3]:
                assert p.is_user_selected is False
            if p.id in priority_ids[3:6]:
                assert p.is_user_selected is True

    def test_remove_priority(self, service, sample_user_id):
        """Test removing a priority."""
        priority = service.add_priority(
            user_id=sample_user_id,
            entity_type="quote",
            entity_id=uuid4(),
            title="To be removed",
            priority_level=PriorityLevel.MEDIUM,
        )

        result = service.remove_priority(sample_user_id, priority.id)
        assert result is True

        # Verify it's gone
        priorities = service.get_user_priorities(sample_user_id)
        assert not any(p.id == priority.id for p in priorities)

    def test_remove_nonexistent_priority(self, service, sample_user_id):
        """Test removing a non-existent priority."""
        result = service.remove_priority(sample_user_id, uuid4())
        assert result is False

    def test_remove_priority_wrong_user(self, service, sample_user_id):
        """Test removing priority from user who has none."""
        other_user = uuid4()
        result = service.remove_priority(other_user, uuid4())
        assert result is False

    def test_get_user_priorities_filtered(self, service, sample_user_id):
        """Test getting priorities with filters."""
        priority_ids = []
        for i in range(5):
            p = service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Priority {i+1}",
                priority_level=PriorityLevel.MEDIUM,
            )
            priority_ids.append(p.id)

        # Select first 3
        service.set_top_priorities(sample_user_id, priority_ids[:3])

        # Get only selected
        selected_only = service.get_user_priorities(
            sample_user_id, include_selected=True, include_unselected=False
        )
        assert len(selected_only) == 3

        # Get only unselected
        unselected_only = service.get_user_priorities(
            sample_user_id, include_selected=False, include_unselected=True
        )
        assert len(unselected_only) == 2

    def test_get_user_priorities_ordered_by_rank(self, service, sample_user_id):
        """Test that priorities are ordered by rank."""
        priority_ids = []
        for i in range(3):
            p = service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Rank {i+1}",
                priority_level=PriorityLevel.MEDIUM,
            )
            priority_ids.append(p.id)

        # Select in reverse order
        service.set_top_priorities(sample_user_id, list(reversed(priority_ids)))

        priorities = service.get_user_priorities(
            sample_user_id, include_selected=True, include_unselected=False
        )
        
        for i, p in enumerate(priorities):
            assert p.rank == i + 1

    def test_priority_with_optional_fields(self, service, sample_user_id):
        """Test adding priority with optional fields omitted."""
        priority = service.add_priority(
            user_id=sample_user_id,
            entity_type="quote",
            entity_id=uuid4(),
            title="Simple priority",
            priority_level=PriorityLevel.LOW,
        )

        assert priority.description is None
        assert priority.due_date is None
        assert priority.owner_id is None

    def test_priority_with_all_fields(self, service, sample_user_id):
        """Test adding priority with all fields."""
        owner_id = uuid4()
        due = date.today() + timedelta(days=3)
        
        priority = service.add_priority(
            user_id=sample_user_id,
            entity_type="quote",
            entity_id=uuid4(),
            title="Full priority",
            priority_level=PriorityLevel.HIGH,
            description="Detailed description",
            due_date=due,
            owner_id=owner_id,
            owner_name="John Doe",
        )

        assert priority.description == "Detailed description"
        assert priority.due_date == due
        assert priority.owner_id == owner_id
        assert priority.owner_name == "John Doe"


# ============================================================================
# Risk Management Tests
# ============================================================================


class TestRiskManagement:
    """Tests for risk tracking functionality."""

    def test_add_risk(self, service):
        """Test adding a risk."""
        risk = service.add_risk(
            title="Delayed delivery",
            category=RiskCategory.DELIVERY,
            severity=8,
            probability=6,
            description="Vendor capacity issue",
            mitigation="Source alternative vendor",
        )

        assert risk.id is not None
        assert risk.category == RiskCategory.DELIVERY
        assert risk.severity == 8
        assert risk.probability == 6
        assert risk.risk_score == 48  # severity * probability

    def test_add_risk_clamps_severity_and_probability(self, service):
        """Test that severity and probability are clamped to 1-10."""
        risk = service.add_risk(
            title="Extreme risk",
            category=RiskCategory.QUALITY,
            severity=15,  # Will be clamped to 10
            probability=-5,  # Will be clamped to 1
        )

        assert risk.severity == 10
        assert risk.probability == 1
        assert risk.risk_score == 10

    def test_add_risk_with_entity(self, service):
        """Test adding risk with entity reference."""
        entity_id = uuid4()
        risk = service.add_risk(
            title="Entity-linked risk",
            category=RiskCategory.CASH,
            severity=5,
            probability=5,
            entity_type="quote",
            entity_id=entity_id,
        )

        assert risk.entity_type == "quote"
        assert risk.entity_id == entity_id

    def test_get_risks_by_category(self, service):
        """Test getting risks filtered by category."""
        # Add risks in various categories
        service.add_risk(title="Delivery 1", category=RiskCategory.DELIVERY, severity=5, probability=5)
        service.add_risk(title="Delivery 2", category=RiskCategory.DELIVERY, severity=7, probability=6)
        service.add_risk(title="Quality 1", category=RiskCategory.QUALITY, severity=4, probability=3)
        service.add_risk(title="Cash 1", category=RiskCategory.CASH, severity=6, probability=4)

        # Get all categories
        risks_by_category = service.get_risks_by_category()
        
        assert RiskCategory.DELIVERY in risks_by_category
        assert len(risks_by_category[RiskCategory.DELIVERY]) == 2
        assert RiskCategory.QUALITY in risks_by_category
        assert len(risks_by_category[RiskCategory.QUALITY]) == 1

    def test_get_risks_by_category_with_filter(self, service):
        """Test getting risks for specific category."""
        service.add_risk(title="Delivery 1", category=RiskCategory.DELIVERY, severity=5, probability=5)
        service.add_risk(title="Quality 1", category=RiskCategory.QUALITY, severity=4, probability=3)

        risks = service.get_risks_by_category(category=RiskCategory.DELIVERY)
        
        assert RiskCategory.DELIVERY in risks
        assert RiskCategory.QUALITY not in risks

    def test_get_risks_by_category_with_top_n(self, service):
        """Test limiting risks per category."""
        for i in range(5):
            service.add_risk(
                title=f"Delivery {i+1}",
                category=RiskCategory.DELIVERY,
                severity=i + 1,
                probability=5,
            )

        risks = service.get_risks_by_category(top_n=3)
        
        assert len(risks[RiskCategory.DELIVERY]) == 3
        # Should be sorted by risk score descending
        scores = [r.risk_score for r in risks[RiskCategory.DELIVERY]]
        assert scores == sorted(scores, reverse=True)

    def test_get_top_risks_ordered_by_score(self, service):
        """Test getting top risks ordered by risk score."""
        risk_data = [
            (4, 5),  # Score: 20
            (2, 2),  # Score: 4
            (5, 8),  # Score: 40
            (3, 3),  # Score: 9
        ]
        for i, (sev, prob) in enumerate(risk_data):
            service.add_risk(
                title=f"Risk {i+1}",
                category=RiskCategory.DELIVERY,
                severity=sev,
                probability=prob,
            )

        top_risks = service.get_top_risks(top_n=3)
        
        assert len(top_risks) == 3
        # Should be ordered by risk score descending
        assert top_risks[0].risk_score >= top_risks[1].risk_score >= top_risks[2].risk_score

    def test_get_all_risk_categories(self, service):
        """Test adding risks for all categories."""
        for cat in RiskCategory:
            service.add_risk(
                title=f"{cat.value} risk",
                category=cat,
                severity=5,
                probability=5,
            )

        risks_by_category = service.get_risks_by_category()
        
        for cat in RiskCategory:
            assert cat in risks_by_category

    def test_risk_with_mitigation(self, service):
        """Test risk with mitigation strategy."""
        risk = service.add_risk(
            title="Reputation risk",
            category=RiskCategory.REPUTATION,
            severity=7,
            probability=4,
            mitigation="Proactive customer communication",
        )

        assert risk.mitigation == "Proactive customer communication"

    def test_risk_with_due_date(self, service):
        """Test risk with due date."""
        due = date.today() + timedelta(days=7)
        risk = service.add_risk(
            title="Time-bound risk",
            category=RiskCategory.COST,
            severity=5,
            probability=5,
            due_date=due,
        )

        assert risk.due_date == due


# ============================================================================
# Commitment Management Tests
# ============================================================================


class TestCommitmentManagement:
    """Tests for commitment tracking functionality."""

    def test_add_commitment(self, service):
        """Test adding a commitment."""
        due = date.today() + timedelta(days=1)
        commitment = service.add_commitment(
            title="Quote for Customer X",
            commitment_type=CommitmentType.QUOTE_DUE,
            due_date=due,
            description="Promised by 3pm",
        )

        assert commitment.id is not None
        assert commitment.commitment_type == CommitmentType.QUOTE_DUE
        assert commitment.is_completed is False
        assert commitment.is_overdue is False

    def test_commitment_detects_overdue(self, service):
        """Test that overdue commitments are detected."""
        past_due = date.today() - timedelta(days=2)
        commitment = service.add_commitment(
            title="Follow up call",
            commitment_type=CommitmentType.FOLLOW_UP,
            due_date=past_due,
        )

        assert commitment.is_overdue is True

    def test_complete_commitment(self, service):
        """Test completing a commitment."""
        commitment = service.add_commitment(
            title="Customer meeting",
            commitment_type=CommitmentType.MEETING,
            due_date=date.today() + timedelta(days=1),
        )

        result = service.complete_commitment(commitment.id)
        
        assert result is not None
        assert result.is_completed is True

    def test_complete_nonexistent_commitment(self, service):
        """Test completing a non-existent commitment."""
        result = service.complete_commitment(uuid4())
        assert result is None

    def test_get_commitments_basic(self, service):
        """Test getting commitments."""
        service.add_commitment(
            title="Task 1",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=date.today() + timedelta(days=1),
        )
        service.add_commitment(
            title="Task 2",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=date.today() + timedelta(days=2),
        )

        commitments = service.get_commitments()
        
        # Note: sample data may add more - just verify our additions are there
        titles = [c.title for c in commitments]
        assert "Task 1" in titles
        assert "Task 2" in titles

    def test_get_commitments_excludes_completed_by_default(self, service):
        """Test that completed commitments are excluded by default."""
        c1 = service.add_commitment(
            title="Task 1",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=date.today() + timedelta(days=1),
        )
        service.add_commitment(
            title="Task 2",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=date.today() + timedelta(days=2),
        )

        service.complete_commitment(c1.id)

        active = service.get_commitments(include_completed=False)
        
        assert not any(c.id == c1.id for c in active)

    def test_get_commitments_includes_completed_when_requested(self, service):
        """Test including completed commitments when requested."""
        c1 = service.add_commitment(
            title="Call 1",
            commitment_type=CommitmentType.CALL_SCHEDULED,
            due_date=date.today() + timedelta(days=1),
        )
        service.add_commitment(
            title="Call 2",
            commitment_type=CommitmentType.CALL_SCHEDULED,
            due_date=date.today() + timedelta(days=2),
        )

        service.complete_commitment(c1.id)

        all_commitments = service.get_commitments(include_completed=True)
        
        assert any(c.id == c1.id for c in all_commitments)

    def test_get_commitments_by_date(self, service, sample_user_id):
        """Test getting commitments for a specific date."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        service.add_commitment(
            title="Today's commitment",
            commitment_type=CommitmentType.APPROVAL_NEEDED,
            due_date=today,
            owner_id=sample_user_id,
        )
        service.add_commitment(
            title="Tomorrow's commitment",
            commitment_type=CommitmentType.FOLLOW_UP,
            due_date=tomorrow,
            owner_id=sample_user_id,
        )

        todays = service.get_commitments(user_id=sample_user_id, target_date=today)
        
        assert len(todays) >= 1
        assert all(c.due_date == today for c in todays)

    def test_commitment_with_all_fields(self, service, sample_user_id):
        """Test commitment with all optional fields."""
        commitment = service.add_commitment(
            title="Full commitment",
            commitment_type=CommitmentType.DELIVERY_DUE,
            due_date=date.today() + timedelta(days=3),
            description="Detailed description",
            due_time="14:30",
            entity_type="work_order",
            entity_id=uuid4(),
            owner_id=sample_user_id,
            owner_name="Jane Doe",
            customer_name="Acme Corp",
        )

        assert commitment.description == "Detailed description"
        assert commitment.due_time == "14:30"
        assert commitment.customer_name == "Acme Corp"

    def test_commitments_sorted_by_due_date(self, service):
        """Test that commitments are sorted by due date."""
        dates = [
            date.today() + timedelta(days=3),
            date.today() + timedelta(days=1),
            date.today() + timedelta(days=2),
        ]
        for i, d in enumerate(dates):
            service.add_commitment(
                title=f"Commitment {i+1}",
                commitment_type=CommitmentType.TASK_DUE,
                due_date=d,
            )

        commitments = service.get_commitments()
        
        # Verify sorted order
        due_dates = [c.due_date for c in commitments]
        assert due_dates == sorted(due_dates)


# ============================================================================
# Abnormality Management Tests
# ============================================================================


class TestAbnormalityManagement:
    """Tests for abnormality detection and resolution."""

    def test_add_abnormality(self, service):
        """Test adding an abnormality."""
        abnormality = service.add_abnormality(
            title="RFQ stalled for 7 days",
            abnormality_type=AbnormalityType.STALLED_RFQ,
            entity_type="rfq",
            entity_id=uuid4(),
            days_stale=7,
            description="No activity since last week",
            suggested_action="Contact supplier",
        )

        assert abnormality.id is not None
        assert abnormality.abnormality_type == AbnormalityType.STALLED_RFQ
        assert abnormality.days_stale == 7

    def test_resolve_abnormality(self, service):
        """Test resolving an abnormality."""
        abnormality = service.add_abnormality(
            title="Missing CTQ requirements",
            abnormality_type=AbnormalityType.MISSING_CTQ,
            entity_type="quote",
            entity_id=uuid4(),
            days_stale=2,
        )

        result = service.resolve_abnormality(abnormality.id)
        assert result is True

        # Resolved should not appear in list
        abnormalities = service.get_abnormalities()
        assert not any(a.id == abnormality.id for a in abnormalities)

    def test_resolve_nonexistent_abnormality(self, service):
        """Test resolving a non-existent abnormality."""
        result = service.resolve_abnormality(uuid4())
        assert result is False

    def test_get_abnormalities_by_type(self, service):
        """Test filtering abnormalities by type."""
        service.add_abnormality(
            title="Late 1", abnormality_type=AbnormalityType.LATE_QUOTE,
            entity_type="quote", entity_id=uuid4(), days_stale=1,
        )
        service.add_abnormality(
            title="Overdue 1", abnormality_type=AbnormalityType.OVERDUE_APPROVAL,
            entity_type="quote", entity_id=uuid4(), days_stale=2,
        )
        service.add_abnormality(
            title="Late 2", abnormality_type=AbnormalityType.LATE_QUOTE,
            entity_type="quote", entity_id=uuid4(), days_stale=3,
        )

        late_quotes = service.get_abnormalities(abnormality_type=AbnormalityType.LATE_QUOTE)
        
        assert len(late_quotes) == 2
        assert all(a.abnormality_type == AbnormalityType.LATE_QUOTE for a in late_quotes)

    def test_get_abnormalities_by_severity(self, service):
        """Test filtering abnormalities by severity."""
        service.add_abnormality(
            title="High severity", abnormality_type=AbnormalityType.BLOCKED_TASK,
            entity_type="task", entity_id=uuid4(), days_stale=1, severity=PriorityLevel.HIGH,
        )
        service.add_abnormality(
            title="Low severity", abnormality_type=AbnormalityType.LOW_MARGIN,
            entity_type="quote", entity_id=uuid4(), days_stale=2, severity=PriorityLevel.LOW,
        )

        high_severity = service.get_abnormalities(severity=PriorityLevel.HIGH)
        
        assert len(high_severity) == 1
        assert high_severity[0].severity == PriorityLevel.HIGH

    def test_get_abnormality_counts(self, service):
        """Test getting counts by abnormality type."""
        types = [
            AbnormalityType.LATE_QUOTE,
            AbnormalityType.STALLED_RFQ,
            AbnormalityType.LATE_QUOTE,
            AbnormalityType.EXPIRED_QUOTE,
            AbnormalityType.STALLED_RFQ,
            AbnormalityType.STALLED_RFQ,
        ]
        for i, atype in enumerate(types):
            service.add_abnormality(
                title=f"Abnormality {i+1}",
                abnormality_type=atype,
                entity_type="quote",
                entity_id=uuid4(),
                days_stale=i + 1,
            )

        counts = service.get_abnormality_counts()
        
        assert counts[AbnormalityType.LATE_QUOTE] == 2
        assert counts[AbnormalityType.STALLED_RFQ] == 3
        assert counts[AbnormalityType.EXPIRED_QUOTE] == 1

    def test_abnormalities_sorted_by_severity_and_staleness(self, service):
        """Test that abnormalities are sorted by severity then staleness."""
        service.add_abnormality(
            title="Medium old", abnormality_type=AbnormalityType.RECURRING_ISSUE,
            entity_type="product", entity_id=uuid4(), days_stale=10, severity=PriorityLevel.MEDIUM,
        )
        service.add_abnormality(
            title="High new", abnormality_type=AbnormalityType.MISSING_FOLLOW_UP,
            entity_type="opportunity", entity_id=uuid4(), days_stale=1, severity=PriorityLevel.HIGH,
        )
        service.add_abnormality(
            title="High old", abnormality_type=AbnormalityType.BLOCKED_TASK,
            entity_type="task", entity_id=uuid4(), days_stale=5, severity=PriorityLevel.HIGH,
        )

        abnormalities = service.get_abnormalities()
        
        # High severity should come first, then within same severity, more stale first
        assert abnormalities[0].severity == PriorityLevel.HIGH
        assert abnormalities[1].severity == PriorityLevel.HIGH
        assert abnormalities[2].severity == PriorityLevel.MEDIUM

    def test_abnormality_with_all_fields(self, service, sample_user_id):
        """Test abnormality with all optional fields."""
        abnormality = service.add_abnormality(
            title="Recurring quality issue",
            abnormality_type=AbnormalityType.RECURRING_ISSUE,
            entity_type="product",
            entity_id=uuid4(),
            days_stale=15,
            description="Same issue happening repeatedly",
            severity=PriorityLevel.HIGH,
            owner_id=sample_user_id,
            owner_name="Quality Manager",
            suggested_action="Root cause analysis needed",
        )

        assert abnormality.description == "Same issue happening repeatedly"
        assert abnormality.suggested_action == "Root cause analysis needed"
        assert abnormality.owner_name == "Quality Manager"


# ============================================================================
# Micro-Drill Tests
# ============================================================================


class TestMicroDrill:
    """Tests for micro-drill (recall question) functionality."""

    def test_add_micro_drill(self, service):
        """Test adding a micro-drill question."""
        drill = service.add_micro_drill(
            question="What is standard lead time for PCB?",
            answer="4-6 weeks for standard, 2-3 weeks for expedited",
            category="operations",
            difficulty=2,
        )

        assert drill.id is not None
        assert drill.question == "What is standard lead time for PCB?"
        assert drill.difficulty == 2

    def test_add_micro_drill_clamps_difficulty(self, service):
        """Test that difficulty is clamped to 1-5."""
        drill1 = service.add_micro_drill(
            question="Easy question",
            answer="Answer",
            category="test",
            difficulty=0,  # Will be clamped to 1
        )
        drill2 = service.add_micro_drill(
            question="Hard question",
            answer="Answer",
            category="test",
            difficulty=10,  # Will be clamped to 5
        )

        assert drill1.difficulty == 1
        assert drill2.difficulty == 5

    def test_add_micro_drill_with_context(self, service):
        """Test adding drill with context entity."""
        entity_id = uuid4()
        drill = service.add_micro_drill(
            question="Product-specific question",
            answer="Product answer",
            category="product",
            difficulty=3,
            context_entity_type="product",
            context_entity_id=entity_id,
        )

        assert drill.context_entity_type == "product"
        assert drill.context_entity_id == entity_id

    def test_add_micro_drill_with_hint(self, service):
        """Test adding drill with hint."""
        drill = service.add_micro_drill(
            question="Tricky question",
            answer="Tricky answer",
            category="trivia",
            difficulty=4,
            hint="Think about the process",
        )

        assert drill.hint == "Think about the process"

    def test_get_todays_drills(self, service, sample_user_id):
        """Test getting drills scheduled for today."""
        # Add some drills
        service.add_micro_drill(
            question="Custom question 1",
            answer="Answer 1",
            category="custom",
            difficulty=2,
        )
        service.add_micro_drill(
            question="Custom question 2",
            answer="Answer 2",
            category="custom",
            difficulty=3,
        )

        todays = service.get_todays_drills(sample_user_id)
        
        # Should return drills (default 3 or available)
        assert len(todays) > 0
        assert len(todays) <= 3

    def test_get_todays_drills_custom_count(self, service, sample_user_id):
        """Test getting custom number of drills."""
        for i in range(10):
            service.add_micro_drill(
                question=f"Question {i+1}",
                answer=f"Answer {i+1}",
                category="test",
                difficulty=2,
            )

        drills = service.get_todays_drills(sample_user_id, count=5)
        
        # Should be limited to requested count
        assert len(drills) <= 5

    def test_complete_drill(self, service, sample_user_id):
        """Test completing a drill."""
        drill = service.add_micro_drill(
            question="Test question",
            answer="Test answer",
            category="test",
            difficulty=1,
        )

        result = service.complete_drill(sample_user_id, drill.id, correct=True)
        
        assert result["streak"] >= 1
        assert result["total_completed"] >= 1
        assert "accuracy" in result

    def test_complete_drill_tracks_correctness(self, service, sample_user_id):
        """Test that drill completion tracks correct/incorrect."""
        drills = [
            service.add_micro_drill(
                question=f"Q{i}",
                answer=f"A{i}",
                category="test",
                difficulty=1,
            )
            for i in range(3)
        ]

        service.complete_drill(sample_user_id, drills[0].id, correct=True)
        service.complete_drill(sample_user_id, drills[1].id, correct=False)
        result = service.complete_drill(sample_user_id, drills[2].id, correct=True)

        # After incorrect answer, streak should reset
        # But after correct, it should be 1 again
        assert result["streak"] == 1  # Reset after incorrect
        assert result["total_completed"] == 3

    def test_get_drill_progress(self, service, sample_user_id):
        """Test getting drill progress."""
        drill = service.add_micro_drill(
            question="Progress test",
            answer="Answer",
            category="test",
            difficulty=1,
        )
        service.complete_drill(sample_user_id, drill.id, correct=True)

        progress = service.get_drill_progress(sample_user_id)
        
        assert progress["drills_completed_today"] >= 1
        assert progress["streak"] >= 0
        assert "accuracy" in progress

    def test_drill_excludes_completed_today(self, service, sample_user_id):
        """Test that completed drills are excluded from today's list."""
        drill = service.add_micro_drill(
            question="Unique question",
            answer="Answer",
            category="test",
            difficulty=1,
        )

        # Complete the drill
        service.complete_drill(sample_user_id, drill.id, correct=True)

        # Get today's drills - should not include completed one
        todays = service.get_todays_drills(sample_user_id)
        
        assert not any(d.id == drill.id for d in todays)


# ============================================================================
# LSW Checklist Summary Tests
# ============================================================================


class TestLSWChecklistSummary:
    """Tests for LSW checklist summary functionality."""

    def test_get_lsw_summary_returns_data(self, service, sample_user_id):
        """Test getting LSW summary."""
        summary = service.get_lsw_summary(sample_user_id)

        assert isinstance(summary, LSWChecklistSummary)
        assert summary.daily_total >= 0
        assert summary.daily_completed >= 0
        assert summary.daily_status in LSWChecklistStatus

    def test_lsw_summary_has_all_frequencies(self, service, sample_user_id):
        """Test that LSW summary covers daily, weekly, monthly."""
        summary = service.get_lsw_summary(sample_user_id)

        # Check daily
        assert summary.daily_status is not None
        assert summary.daily_total >= 0
        assert summary.daily_completed >= 0

        # Check weekly
        assert summary.weekly_status is not None
        assert summary.weekly_total >= 0
        assert summary.weekly_completed >= 0

        # Check monthly
        assert summary.monthly_status is not None
        assert summary.monthly_total >= 0
        assert summary.monthly_completed >= 0

    def test_lsw_summary_has_overdue_count(self, service, sample_user_id):
        """Test that summary includes overdue count."""
        summary = service.get_lsw_summary(sample_user_id)
        
        assert summary.overdue_count >= 0

    def test_lsw_summary_has_next_due_item(self, service, sample_user_id):
        """Test that summary includes next due item."""
        summary = service.get_lsw_summary(sample_user_id)
        
        # May or may not have a next item
        assert summary.next_due_item is None or isinstance(summary.next_due_item, str)


# ============================================================================
# Quick Metrics Tests
# ============================================================================


class TestQuickMetrics:
    """Tests for quick metrics aggregation."""

    def test_get_quick_metrics_returns_list(self, service, sample_user_id):
        """Test getting quick metrics."""
        metrics = service.get_quick_metrics(sample_user_id)

        assert isinstance(metrics, list)
        for metric in metrics:
            assert isinstance(metric, QuickMetric)
            assert metric.name is not None
            assert metric.value is not None

    def test_quick_metrics_have_required_fields(self, service, sample_user_id):
        """Test that metrics have all required fields."""
        metrics = service.get_quick_metrics(sample_user_id)

        for metric in metrics:
            assert metric.id is not None
            assert metric.name is not None
            assert metric.value is not None
            assert metric.trend in ["up", "down", "stable"]
            assert metric.status in ["good", "warning", "critical"]

    def test_quick_metrics_have_optional_fields(self, service, sample_user_id):
        """Test that metrics may have optional fields."""
        metrics = service.get_quick_metrics(sample_user_id)

        # At least some metrics should have units, targets, or links
        has_unit = any(m.unit is not None for m in metrics)
        has_target = any(m.target is not None for m in metrics)
        has_link = any(m.link is not None for m in metrics)

        assert has_unit or has_target or has_link


# ============================================================================
# Full Today Screen Data Tests
# ============================================================================


class TestTodayScreenData:
    """Tests for the full today screen data aggregation."""

    def test_get_today_screen_returns_all_data(self, service, sample_user_id, sample_user_name):
        """Test getting the full today screen data."""
        # Add some data first
        for i in range(3):
            service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Priority {i+1}",
                priority_level=PriorityLevel.HIGH,
            )

        service.add_risk(
            title="Risk 1",
            category=RiskCategory.DELIVERY,
            severity=7,
            probability=5,
        )

        service.add_commitment(
            title="Commitment 1",
            commitment_type=CommitmentType.QUOTE_DUE,
            due_date=date.today(),
        )

        # Get full screen data
        screen = service.get_today_screen(sample_user_id, sample_user_name)

        assert isinstance(screen, TodayScreenData)
        assert screen.user_id == sample_user_id
        assert screen.user_name == sample_user_name
        assert screen.current_date == date.today()
        assert screen.greeting is not None
        assert isinstance(screen.lsw_summary, LSWChecklistSummary)
        assert isinstance(screen.quick_metrics, list)
        assert screen.generated_at is not None

    def test_today_screen_has_greeting(self, service, sample_user_id):
        """Test that today screen includes appropriate greeting."""
        screen = service.get_today_screen(sample_user_id, "John Smith")

        # Greeting should include first name
        assert "John" in screen.greeting
        # Should have time-based greeting
        assert any(g in screen.greeting for g in ["morning", "afternoon", "evening"])

    def test_today_screen_separates_priorities(self, service, sample_user_id, sample_user_name):
        """Test that priorities are separated into selected and unselected."""
        priority_ids = []
        for i in range(5):
            p = service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"Priority {i+1}",
                priority_level=PriorityLevel.MEDIUM,
            )
            priority_ids.append(p.id)

        service.set_top_priorities(sample_user_id, priority_ids[:3])

        screen = service.get_today_screen(sample_user_id, sample_user_name)

        assert len(screen.top_priorities) == 3
        assert len(screen.unselected_priorities) == 2

    def test_today_screen_groups_risks_by_category(self, service, sample_user_id, sample_user_name):
        """Test that risks are grouped by category."""
        service.add_risk(title="Delivery risk", category=RiskCategory.DELIVERY, severity=5, probability=5)
        service.add_risk(title="Quality risk", category=RiskCategory.QUALITY, severity=6, probability=4)

        screen = service.get_today_screen(sample_user_id, sample_user_name)

        assert RiskCategory.DELIVERY in screen.top_risks
        assert RiskCategory.QUALITY in screen.top_risks

    def test_today_screen_separates_commitments(self, service, sample_user_id, sample_user_name):
        """Test that commitments are separated by date."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        service.add_commitment(
            title="Today",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=today,
            owner_id=sample_user_id,
        )
        service.add_commitment(
            title="Tomorrow",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=tomorrow,
            owner_id=sample_user_id,
        )
        service.add_commitment(
            title="Overdue",
            commitment_type=CommitmentType.TASK_DUE,
            due_date=yesterday,
            owner_id=sample_user_id,
        )

        screen = service.get_today_screen(sample_user_id, sample_user_name)

        # Each should be in appropriate bucket
        assert any(c.title == "Today" for c in screen.todays_commitments)
        assert any(c.title == "Tomorrow" for c in screen.tomorrows_commitments)
        assert any(c.title == "Overdue" for c in screen.overdue_commitments)

    def test_today_screen_includes_drill_progress(self, service, sample_user_id, sample_user_name):
        """Test that today screen includes drill progress."""
        drill = service.add_micro_drill(
            question="Test",
            answer="Answer",
            category="test",
            difficulty=1,
        )
        service.complete_drill(sample_user_id, drill.id, correct=True)

        screen = service.get_today_screen(sample_user_id, sample_user_name)

        assert screen.drills_completed_today >= 1
        assert screen.drill_streak >= 0

    def test_today_screen_includes_cache_info(self, service, sample_user_id, sample_user_name):
        """Test that today screen includes cache info."""
        screen = service.get_today_screen(sample_user_id, sample_user_name)

        assert screen.cache_valid_until is not None
        assert screen.cache_valid_until > screen.generated_at


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestSingletonPattern:
    """Tests for the singleton service pattern."""

    def test_get_service_returns_same_instance(self):
        """Test that get_today_screen_service returns the same instance."""
        reset_today_screen_service()
        service1 = get_today_screen_service()
        service2 = get_today_screen_service()

        assert service1 is service2

    def test_reset_creates_new_instance(self):
        """Test that reset creates a new instance."""
        service1 = get_today_screen_service()
        
        # Add a risk
        service1.add_risk(
            title="Safety risk",
            category=RiskCategory.SAFETY,
            severity=9,
            probability=8,
        )

        reset_today_screen_service()
        service2 = get_today_screen_service()

        # New instance should have fresh sample data only
        assert service1 is not service2

    def test_data_persists_across_calls(self):
        """Test that data persists across multiple calls to get_service."""
        reset_today_screen_service()

        service1 = get_today_screen_service()
        commitment = service1.add_commitment(
            title="Persistent commitment",
            commitment_type=CommitmentType.DELIVERY_DUE,
            due_date=date.today() + timedelta(days=1),
        )

        service2 = get_today_screen_service()
        commitments = service2.get_commitments()

        assert any(c.id == commitment.id for c in commitments)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_user_priorities(self, service, sample_user_id):
        """Test getting priorities for user with none."""
        priorities = service.get_user_priorities(sample_user_id)
        assert priorities == []

    def test_no_risks(self, service):
        """Test when there are no risks."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        # Clear all risks added by sample data
        svc._risks.clear()
        
        risks = svc.get_top_risks()
        assert risks == []

    def test_no_commitments(self, service):
        """Test when there are no commitments."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        svc._commitments.clear()
        
        commitments = svc.get_commitments()
        assert commitments == []

    def test_no_abnormalities(self, service):
        """Test when there are no abnormalities."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        svc._abnormalities.clear()
        
        abnormalities = svc.get_abnormalities()
        assert abnormalities == []

    def test_today_screen_for_new_user(self, service, sample_user_name):
        """Test getting today screen for user with no data."""
        new_user = uuid4()
        screen = service.get_today_screen(new_user, sample_user_name)

        assert isinstance(screen, TodayScreenData)
        assert screen.user_id == new_user
        assert len(screen.top_priorities) == 0
        # Note: risks, commitments, drills are global, not per-user

    def test_set_fewer_than_three_priorities(self, service, sample_user_id):
        """Test setting fewer than 3 priorities works."""
        p = service.add_priority(
            user_id=sample_user_id,
            entity_type="quote",
            entity_id=uuid4(),
            title="Only one",
            priority_level=PriorityLevel.HIGH,
        )

        selected = service.set_top_priorities(sample_user_id, [p.id])
        
        assert len(selected) == 1

    def test_set_empty_priorities(self, service, sample_user_id):
        """Test setting empty priority list clears selection."""
        # Add and select some priorities
        priority_ids = []
        for i in range(3):
            p = service.add_priority(
                user_id=sample_user_id,
                entity_type="quote",
                entity_id=uuid4(),
                title=f"P{i+1}",
                priority_level=PriorityLevel.MEDIUM,
            )
            priority_ids.append(p.id)

        service.set_top_priorities(sample_user_id, priority_ids)

        # Clear selection
        selected = service.set_top_priorities(sample_user_id, [])
        
        assert len(selected) == 0

        # Verify all are unselected
        all_priorities = service.get_user_priorities(sample_user_id)
        assert all(not p.is_user_selected for p in all_priorities)

    def test_drill_accuracy_with_no_completions(self, service, sample_user_id):
        """Test drill progress when nothing completed."""
        progress = service.get_drill_progress(sample_user_id)
        
        assert progress["accuracy"] == 0
        assert progress["drills_completed_today"] == 0

    def test_risks_by_category_empty_result(self, service):
        """Test getting risks by category with no matching risks."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        svc._risks.clear()
        
        risks = svc.get_risks_by_category(category=RiskCategory.SAFETY)
        
        # Should return empty dict when no matching risks
        assert risks == {} or RiskCategory.SAFETY not in risks


# ============================================================================
# Shop Floor Management Tests (Phase 3)
# ============================================================================


# Import additional types for shop floor tests
from sensei.services.ops.today_screen import (
    ShopFloorAreaType,
    ShopFloorAlertSeverity,
    WorkOrderAtRisk,
    CriticalAndon,
    StationEfficiency,
    CellOEE,
    KanbanAlert,
    ExpiringCertification,
    WIPViolation,
    CAPAVerification,
    ScheduledTraining,
    ShopFloorSummary,
)


class TestWorkOrdersAtRisk:
    """Tests for work orders at risk management."""

    def test_add_work_order_at_risk(self, service):
        """Test adding a work order at risk."""
        due = date.today() + timedelta(days=3)
        estimated = date.today() + timedelta(days=5)
        
        wo = service.add_work_order_at_risk(
            work_order_number="WO-001",
            product_name="Widget A",
            quantity=100,
            due_date=due,
            estimated_completion=estimated,
            reason="Machine breakdown",
            work_center_id=uuid4(),
            work_center_name="Assembly",
        )
        
        assert wo.id is not None
        assert wo.work_order_number == "WO-001"
        assert wo.product_name == "Widget A"
        assert wo.quantity == 100
        assert wo.days_at_risk == 2  # 5 - 3 = 2 days late
        assert wo.severity == ShopFloorAlertSeverity.WARNING

    def test_work_order_critical_severity(self, service):
        """Test work order gets critical severity when very late."""
        due = date.today()
        estimated = date.today() + timedelta(days=5)  # 5 days late
        
        wo = service.add_work_order_at_risk(
            work_order_number="WO-002",
            product_name="Widget B",
            quantity=50,
            due_date=due,
            estimated_completion=estimated,
            reason="Material shortage",
        )
        
        assert wo.days_at_risk == 5
        assert wo.severity == ShopFloorAlertSeverity.CRITICAL

    def test_work_order_info_severity(self, service):
        """Test work order gets info severity when on time."""
        due = date.today() + timedelta(days=3)
        estimated = due  # On time
        
        wo = service.add_work_order_at_risk(
            work_order_number="WO-003",
            product_name="Widget C",
            quantity=25,
            due_date=due,
            estimated_completion=estimated,
            reason="Tight schedule",
        )
        
        assert wo.days_at_risk == 0
        assert wo.severity == ShopFloorAlertSeverity.INFO

    def test_get_work_orders_at_risk(self, service):
        """Test retrieving work orders at risk."""
        wc_id = uuid4()
        
        for i in range(3):
            service.add_work_order_at_risk(
                work_order_number=f"WO-{i}",
                product_name=f"Product {i}",
                quantity=10 * (i + 1),
                due_date=date.today(),
                estimated_completion=date.today() + timedelta(days=i + 1),
                reason="Test",
                work_center_id=wc_id,
                work_center_name="Test Center",
            )
        
        # Add one for different work center
        service.add_work_order_at_risk(
            work_order_number="WO-OTHER",
            product_name="Other",
            quantity=5,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=1),
            reason="Test",
            work_center_id=uuid4(),
            work_center_name="Other Center",
        )
        
        # Filter by work center
        wos = service.get_work_orders_at_risk(work_center_id=wc_id)
        assert len(wos) == 3
        assert all(w.work_center_id == wc_id for w in wos)

    def test_get_work_orders_at_risk_by_severity(self, service):
        """Test filtering work orders by severity."""
        # Add critical
        service.add_work_order_at_risk(
            work_order_number="WO-CRIT",
            product_name="Critical",
            quantity=100,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=5),
            reason="Very late",
        )
        
        # Add warning
        service.add_work_order_at_risk(
            work_order_number="WO-WARN",
            product_name="Warning",
            quantity=50,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=2),
            reason="Slightly late",
        )
        
        critical = service.get_work_orders_at_risk(severity=ShopFloorAlertSeverity.CRITICAL)
        assert len(critical) == 1
        assert critical[0].work_order_number == "WO-CRIT"

    def test_resolve_work_order_at_risk(self, service):
        """Test resolving a work order at risk."""
        wo = service.add_work_order_at_risk(
            work_order_number="WO-RESOLVE",
            product_name="Resolve Me",
            quantity=10,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=1),
            reason="Test",
        )
        
        assert service.resolve_work_order_at_risk(wo.id) is True
        assert service.resolve_work_order_at_risk(wo.id) is False  # Already removed

    def test_work_orders_sorted_by_severity(self, service):
        """Test work orders are sorted by severity and days at risk."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        # Add in random order
        svc.add_work_order_at_risk(
            work_order_number="WO-1",
            product_name="P1",
            quantity=10,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=1),  # Warning
            reason="T",
        )
        svc.add_work_order_at_risk(
            work_order_number="WO-2",
            product_name="P2",
            quantity=10,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=10),  # Critical
            reason="T",
        )
        svc.add_work_order_at_risk(
            work_order_number="WO-3",
            product_name="P3",
            quantity=10,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=5),  # Critical
            reason="T",
        )
        
        wos = svc.get_work_orders_at_risk()
        assert wos[0].work_order_number == "WO-2"  # Most critical first
        assert wos[1].work_order_number == "WO-3"


class TestCriticalAndons:
    """Tests for critical Andon management."""

    def test_add_critical_andon(self, service):
        """Test adding a critical Andon."""
        wc_id = uuid4()
        
        andon = service.add_critical_andon(
            andon_type="quality",
            title="Defect detected",
            work_center_id=wc_id,
            work_center_name="Assembly Line 1",
            description="Surface defect on part",
            station_id=uuid4(),
            station_name="Station 3",
        )
        
        assert andon.id is not None
        assert andon.andon_type == "quality"
        assert andon.title == "Defect detected"
        assert andon.acknowledged is False
        assert andon.minutes_open == 0
        assert andon.severity == ShopFloorAlertSeverity.CRITICAL

    def test_acknowledge_andon(self, service):
        """Test acknowledging an Andon."""
        wc_id = uuid4()
        user_id = uuid4()
        
        andon = service.add_critical_andon(
            andon_type="safety",
            title="Safety hazard",
            work_center_id=wc_id,
            work_center_name="Welding",
        )
        
        result = service.acknowledge_andon(
            andon_id=andon.id,
            acknowledged_by_id=user_id,
            acknowledged_by_name="John Smith",
        )
        
        assert result is not None
        assert result.acknowledged is True
        assert result.acknowledged_by_id == user_id
        assert result.acknowledged_by_name == "John Smith"

    def test_resolve_andon(self, service):
        """Test resolving an Andon."""
        wc_id = uuid4()
        
        andon = service.add_critical_andon(
            andon_type="equipment",
            title="Machine jam",
            work_center_id=wc_id,
            work_center_name="CNC",
        )
        
        assert service.resolve_andon(andon.id) is True
        assert service.resolve_andon(andon.id) is False  # Already resolved

    def test_get_critical_andons(self, service):
        """Test getting critical Andons."""
        wc_id = uuid4()
        
        for i in range(3):
            service.add_critical_andon(
                andon_type="quality",
                title=f"Andon {i}",
                work_center_id=wc_id,
                work_center_name="Test",
            )
        
        andons = service.get_critical_andons(work_center_id=wc_id)
        assert len(andons) == 3

    def test_get_unacknowledged_andons_only(self, service):
        """Test filtering for unacknowledged Andons."""
        wc_id = uuid4()
        
        andon1 = service.add_critical_andon(
            andon_type="quality",
            title="Andon 1",
            work_center_id=wc_id,
            work_center_name="Test",
        )
        service.add_critical_andon(
            andon_type="quality",
            title="Andon 2",
            work_center_id=wc_id,
            work_center_name="Test",
        )
        
        # Acknowledge one
        service.acknowledge_andon(andon1.id, uuid4(), "User")
        
        unacked = service.get_critical_andons(unacknowledged_only=True)
        assert len(unacked) == 1
        assert unacked[0].title == "Andon 2"

    def test_andon_minutes_open_updates(self, service):
        """Test that minutes open is updated when retrieving."""
        wc_id = uuid4()
        
        andon = service.add_critical_andon(
            andon_type="material",
            title="Material shortage",
            work_center_id=wc_id,
            work_center_name="Test",
        )
        
        # Manually set raised_at to past
        andon.raised_at = utcnow_naive() - timedelta(minutes=30)
        
        andons = service.get_critical_andons()
        assert andons[0].minutes_open >= 30


class TestStationEfficiency:
    """Tests for station efficiency tracking."""

    def test_add_station_efficiency(self, service):
        """Test adding station efficiency data."""
        station_id = uuid4()
        wc_id = uuid4()
        
        eff = service.add_station_efficiency(
            station_id=station_id,
            station_name="Station 1",
            work_center_id=wc_id,
            work_center_name="Assembly",
            current_efficiency=85.0,
            target_efficiency=90.0,
            operator_id=uuid4(),
            operator_name="Jane Doe",
        )
        
        assert eff.station_id == station_id
        assert eff.current_efficiency == 85.0
        assert eff.target_efficiency == 90.0
        assert eff.variance == -5.0
        assert eff.is_below_target is True

    def test_station_efficiency_above_target(self, service):
        """Test station above target is not flagged."""
        station_id = uuid4()
        wc_id = uuid4()
        
        eff = service.add_station_efficiency(
            station_id=station_id,
            station_name="Good Station",
            work_center_id=wc_id,
            work_center_name="Assembly",
            current_efficiency=95.0,
            target_efficiency=90.0,
        )
        
        assert eff.variance == 5.0
        assert eff.is_below_target is False

    def test_get_low_efficiency_stations(self, service):
        """Test getting low efficiency stations."""
        wc_id = uuid4()
        
        # Add low efficiency
        service.add_station_efficiency(
            station_id=uuid4(),
            station_name="Low 1",
            work_center_id=wc_id,
            work_center_name="Test",
            current_efficiency=75.0,
            target_efficiency=90.0,
        )
        service.add_station_efficiency(
            station_id=uuid4(),
            station_name="Low 2",
            work_center_id=wc_id,
            work_center_name="Test",
            current_efficiency=80.0,
            target_efficiency=90.0,
        )
        
        # Add high efficiency
        service.add_station_efficiency(
            station_id=uuid4(),
            station_name="High",
            work_center_id=wc_id,
            work_center_name="Test",
            current_efficiency=95.0,
            target_efficiency=90.0,
        )
        
        low = service.get_low_efficiency_stations(work_center_id=wc_id)
        assert len(low) == 2
        # Sorted by variance (worst first)
        assert low[0].station_name == "Low 1"

    def test_get_low_efficiency_with_threshold(self, service):
        """Test filtering by custom threshold."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        svc.add_station_efficiency(
            station_id=uuid4(),
            station_name="S1",
            work_center_id=uuid4(),
            work_center_name="Test",
            current_efficiency=70.0,
            target_efficiency=80.0,
        )
        svc.add_station_efficiency(
            station_id=uuid4(),
            station_name="S2",
            work_center_id=uuid4(),
            work_center_name="Test",
            current_efficiency=80.0,
            target_efficiency=80.0,
        )
        
        low = svc.get_low_efficiency_stations(threshold=75.0)
        assert len(low) == 1
        assert low[0].station_name == "S1"


class TestCellOEE:
    """Tests for cell OEE tracking."""

    def test_add_cell_oee(self, service):
        """Test adding cell OEE data."""
        cell_id = uuid4()
        wc_id = uuid4()
        
        oee = service.add_cell_oee(
            cell_id=cell_id,
            cell_name="Cell A",
            work_center_id=wc_id,
            work_center_name="Machining",
            availability=90.0,
            performance=85.0,
            quality=98.0,
            target_oee=80.0,
        )
        
        assert oee.cell_id == cell_id
        assert oee.availability == 90.0
        assert oee.performance == 85.0
        assert oee.quality == 98.0
        # OEE = 0.90 * 0.85 * 0.98 * 100 = 74.97
        assert oee.current_oee == pytest.approx(74.97, rel=0.01)
        assert oee.is_below_threshold is True

    def test_cell_oee_above_threshold(self, service):
        """Test cell above threshold is not flagged."""
        cell_id = uuid4()
        wc_id = uuid4()
        
        oee = service.add_cell_oee(
            cell_id=cell_id,
            cell_name="Good Cell",
            work_center_id=wc_id,
            work_center_name="Machining",
            availability=95.0,
            performance=95.0,
            quality=99.0,
            target_oee=80.0,
        )
        
        # OEE = 0.95 * 0.95 * 0.99 * 100 = 89.35
        assert oee.current_oee > 80.0
        assert oee.is_below_threshold is False

    def test_get_low_oee_cells(self, service):
        """Test getting low OEE cells."""
        wc_id = uuid4()
        
        service.add_cell_oee(
            cell_id=uuid4(),
            cell_name="Low OEE",
            work_center_id=wc_id,
            work_center_name="Test",
            availability=80.0,
            performance=80.0,
            quality=80.0,
            target_oee=60.0,  # Below: 51.2%
        )
        service.add_cell_oee(
            cell_id=uuid4(),
            cell_name="High OEE",
            work_center_id=wc_id,
            work_center_name="Test",
            availability=95.0,
            performance=95.0,
            quality=99.0,
            target_oee=85.0,  # Above: 89.35%
        )
        
        low = service.get_low_oee_cells(work_center_id=wc_id)
        assert len(low) == 1
        assert low[0].cell_name == "Low OEE"

    def test_get_overall_oee(self, service):
        """Test calculating overall OEE."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        svc.add_cell_oee(
            cell_id=uuid4(),
            cell_name="Cell 1",
            work_center_id=uuid4(),
            work_center_name="Test",
            availability=90.0,
            performance=90.0,
            quality=90.0,
            target_oee=80.0,
        )
        svc.add_cell_oee(
            cell_id=uuid4(),
            cell_name="Cell 2",
            work_center_id=uuid4(),
            work_center_name="Test",
            availability=80.0,
            performance=80.0,
            quality=80.0,
            target_oee=80.0,
        )
        
        # Cell 1: 72.9%, Cell 2: 51.2%, Average: 62.05%
        overall = svc.get_overall_oee()
        assert overall == pytest.approx(62.05, rel=0.01)

    def test_get_overall_oee_empty(self, service):
        """Test overall OEE with no cells."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        assert svc.get_overall_oee() == 0.0


class TestKanbanAlerts:
    """Tests for Kanban alert management."""

    def test_add_kanban_alert(self, service):
        """Test adding a Kanban alert."""
        wc_id = uuid4()
        past_date = date.today() - timedelta(days=3)
        
        alert = service.add_kanban_alert(
            material_code="MAT-001",
            material_name="Steel Plate",
            bin_location="A-12-3",
            work_center_id=wc_id,
            work_center_name="Fabrication",
            quantity_needed=50.0,
            unit="pcs",
            due_date=past_date,
            supplier_name="Acme Steel",
        )
        
        assert alert.id is not None
        assert alert.material_code == "MAT-001"
        assert alert.days_overdue == 3
        assert alert.replenishment_status == "pending"

    def test_kanban_not_overdue(self, service):
        """Test Kanban due in future is not overdue."""
        wc_id = uuid4()
        future_date = date.today() + timedelta(days=2)
        
        alert = service.add_kanban_alert(
            material_code="MAT-002",
            material_name="Bolts",
            bin_location="B-5-1",
            work_center_id=wc_id,
            work_center_name="Assembly",
            quantity_needed=100.0,
            unit="pcs",
            due_date=future_date,
        )
        
        assert alert.days_overdue == 0

    def test_update_kanban_status(self, service):
        """Test updating Kanban status."""
        wc_id = uuid4()
        
        alert = service.add_kanban_alert(
            material_code="MAT-003",
            material_name="Nuts",
            bin_location="B-5-2",
            work_center_id=wc_id,
            work_center_name="Assembly",
            quantity_needed=200.0,
            unit="pcs",
            due_date=date.today(),
        )
        
        result = service.update_kanban_status(alert.id, "ordered")
        assert result is not None
        assert result.replenishment_status == "ordered"

    def test_resolve_kanban_alert(self, service):
        """Test resolving a Kanban alert."""
        wc_id = uuid4()
        
        alert = service.add_kanban_alert(
            material_code="MAT-004",
            material_name="Washers",
            bin_location="B-5-3",
            work_center_id=wc_id,
            work_center_name="Assembly",
            quantity_needed=500.0,
            unit="pcs",
            due_date=date.today(),
        )
        
        assert service.resolve_kanban_alert(alert.id) is True
        assert service.resolve_kanban_alert(alert.id) is False

    def test_get_overdue_kanbans(self, service):
        """Test getting overdue Kanbans."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        wc_id = uuid4()
        
        # Add overdue
        svc.add_kanban_alert(
            material_code="MAT-OVD",
            material_name="Overdue",
            bin_location="X-1",
            work_center_id=wc_id,
            work_center_name="Test",
            quantity_needed=10.0,
            unit="pcs",
            due_date=date.today() - timedelta(days=2),
        )
        
        # Add not overdue
        svc.add_kanban_alert(
            material_code="MAT-OK",
            material_name="On Time",
            bin_location="X-2",
            work_center_id=wc_id,
            work_center_name="Test",
            quantity_needed=10.0,
            unit="pcs",
            due_date=date.today() + timedelta(days=2),
        )
        
        overdue = svc.get_overdue_kanbans(work_center_id=wc_id)
        assert len(overdue) == 1
        assert overdue[0].material_code == "MAT-OVD"


class TestExpiringCertifications:
    """Tests for expiring certification tracking."""

    def test_add_expiring_certification(self, service):
        """Test adding an expiring certification."""
        user_id = uuid4()
        exp_date = date.today() + timedelta(days=15)
        
        cert = service.add_expiring_certification(
            user_id=user_id,
            user_name="John Doe",
            certification_name="Forklift Operator",
            certification_type="equipment",
            expiration_date=exp_date,
            required_for_work_centers=["Warehouse", "Shipping"],
        )
        
        assert cert.id is not None
        assert cert.certification_name == "Forklift Operator"
        assert cert.days_until_expiry == 15
        assert cert.is_expired is False

    def test_expired_certification(self, service):
        """Test that expired certification is flagged."""
        user_id = uuid4()
        exp_date = date.today() - timedelta(days=5)
        
        cert = service.add_expiring_certification(
            user_id=user_id,
            user_name="Jane Doe",
            certification_name="Safety Training",
            certification_type="safety",
            expiration_date=exp_date,
        )
        
        assert cert.is_expired is True
        assert cert.days_until_expiry == -5

    def test_get_expiring_certifications(self, service):
        """Test getting expiring certifications."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        user_id = uuid4()
        
        # Expired
        svc.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Expired Cert",
            certification_type="process",
            expiration_date=date.today() - timedelta(days=5),
        )
        
        # Expiring soon (within 30 days)
        svc.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Expiring Soon",
            certification_type="equipment",
            expiration_date=date.today() + timedelta(days=20),
        )
        
        # Far future (beyond 30 days)
        svc.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Far Future",
            certification_type="safety",
            expiration_date=date.today() + timedelta(days=60),
        )
        
        certs = svc.get_expiring_certifications(user_id=user_id, days_ahead=30)
        assert len(certs) == 2  # Expired and Expiring Soon
        
        # Expired should be first
        assert certs[0].certification_name == "Expired Cert"

    def test_get_expiring_certifications_exclude_expired(self, service):
        """Test excluding expired certifications."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        user_id = uuid4()
        
        svc.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Expired",
            certification_type="process",
            expiration_date=date.today() - timedelta(days=5),
        )
        svc.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Valid",
            certification_type="process",
            expiration_date=date.today() + timedelta(days=10),
        )
        
        certs = svc.get_expiring_certifications(include_expired=False)
        assert len(certs) == 1
        assert certs[0].certification_name == "Valid"

    def test_renew_certification(self, service):
        """Test renewing a certification."""
        user_id = uuid4()
        
        cert = service.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Renewed",
            certification_type="process",
            expiration_date=date.today() + timedelta(days=5),
        )
        
        assert service.renew_certification(cert.id) is True
        assert service.renew_certification(cert.id) is False


class TestWIPViolations:
    """Tests for WIP violation tracking."""

    def test_add_wip_violation(self, service):
        """Test adding a WIP violation."""
        wc_id = uuid4()
        
        violation = service.add_wip_violation(
            work_center_id=wc_id,
            work_center_name="Assembly",
            current_wip=25,
            wip_limit=20,
            cell_id=uuid4(),
            cell_name="Cell A",
        )
        
        assert violation.id is not None
        assert violation.current_wip == 25
        assert violation.wip_limit == 20
        assert violation.violation_amount == 5
        assert violation.duration_minutes == 0

    def test_get_wip_violations(self, service):
        """Test getting WIP violations."""
        wc_id = uuid4()
        
        service.add_wip_violation(
            work_center_id=wc_id,
            work_center_name="Test",
            current_wip=30,
            wip_limit=20,
        )
        service.add_wip_violation(
            work_center_id=wc_id,
            work_center_name="Test",
            current_wip=25,
            wip_limit=20,
        )
        
        violations = service.get_wip_violations(work_center_id=wc_id)
        assert len(violations) == 2
        # Sorted by violation amount (worst first)
        assert violations[0].violation_amount == 10
        assert violations[1].violation_amount == 5

    def test_resolve_wip_violation(self, service):
        """Test resolving a WIP violation."""
        wc_id = uuid4()
        
        violation = service.add_wip_violation(
            work_center_id=wc_id,
            work_center_name="Test",
            current_wip=25,
            wip_limit=20,
        )
        
        assert service.resolve_wip_violation(violation.id) is True
        assert service.resolve_wip_violation(violation.id) is False

    def test_wip_violation_duration_updates(self, service):
        """Test that duration is updated when retrieving."""
        wc_id = uuid4()
        
        violation = service.add_wip_violation(
            work_center_id=wc_id,
            work_center_name="Test",
            current_wip=25,
            wip_limit=20,
        )
        
        # Manually set started_at to past
        violation.started_at = utcnow_naive() - timedelta(minutes=45)
        
        violations = service.get_wip_violations()
        assert violations[0].duration_minutes >= 45


class TestCAPAVerifications:
    """Tests for CAPA verification tracking."""

    def test_add_capa_verification(self, service):
        """Test adding a CAPA verification."""
        owner_id = uuid4()
        due_date = date.today() + timedelta(days=3)
        
        capa = service.add_capa_verification(
            capa_number="CAPA-001",
            title="Root cause analysis for defect",
            capa_type="corrective",
            verification_due_date=due_date,
            owner_id=owner_id,
            owner_name="Quality Manager",
            original_nc_id=uuid4(),
            effectiveness_check=True,
        )
        
        assert capa.id is not None
        assert capa.capa_number == "CAPA-001"
        assert capa.days_until_due == 3
        assert capa.is_overdue is False
        assert capa.effectiveness_check is True

    def test_overdue_capa_verification(self, service):
        """Test that overdue CAPA is flagged."""
        owner_id = uuid4()
        due_date = date.today() - timedelta(days=2)
        
        capa = service.add_capa_verification(
            capa_number="CAPA-002",
            title="Overdue CAPA",
            capa_type="preventive",
            verification_due_date=due_date,
            owner_id=owner_id,
            owner_name="Engineer",
        )
        
        assert capa.is_overdue is True
        assert capa.days_until_due == -2

    def test_get_capa_verifications_due(self, service):
        """Test getting CAPA verifications due."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        owner_id = uuid4()
        
        # Overdue
        svc.add_capa_verification(
            capa_number="CAPA-OVD",
            title="Overdue",
            capa_type="corrective",
            verification_due_date=date.today() - timedelta(days=3),
            owner_id=owner_id,
            owner_name="Owner",
        )
        
        # Due soon
        svc.add_capa_verification(
            capa_number="CAPA-SOON",
            title="Due Soon",
            capa_type="corrective",
            verification_due_date=date.today() + timedelta(days=5),
            owner_id=owner_id,
            owner_name="Owner",
        )
        
        # Due far
        svc.add_capa_verification(
            capa_number="CAPA-FAR",
            title="Due Far",
            capa_type="preventive",
            verification_due_date=date.today() + timedelta(days=30),
            owner_id=owner_id,
            owner_name="Owner",
        )
        
        due = svc.get_capa_verifications_due(owner_id=owner_id, days_ahead=7)
        assert len(due) == 2
        # Overdue first
        assert due[0].capa_number == "CAPA-OVD"

    def test_complete_capa_verification(self, service):
        """Test completing a CAPA verification."""
        owner_id = uuid4()
        
        capa = service.add_capa_verification(
            capa_number="CAPA-COMP",
            title="Complete Me",
            capa_type="corrective",
            verification_due_date=date.today() + timedelta(days=1),
            owner_id=owner_id,
            owner_name="Owner",
        )
        
        assert service.complete_capa_verification(capa.id) is True
        assert service.complete_capa_verification(capa.id) is False


class TestScheduledTrainings:
    """Tests for scheduled training management."""

    def test_add_scheduled_training(self, service):
        """Test adding a scheduled training."""
        training = service.add_scheduled_training(
            title="Safety Orientation",
            training_type="initial",
            scheduled_date=date.today(),
            scheduled_time="09:00",
            duration_minutes=120,
            description="New employee safety training",
            location="Training Room A",
            instructor_name="Safety Officer",
            attendee_count=5,
            max_attendees=20,
        )
        
        assert training.id is not None
        assert training.title == "Safety Orientation"
        assert training.duration_minutes == 120
        assert training.attendee_count == 5
        assert training.is_user_enrolled is False

    def test_get_scheduled_trainings_today(self, service):
        """Test getting trainings for today."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        # Today
        svc.add_scheduled_training(
            title="Today's Training",
            training_type="refresher",
            scheduled_date=date.today(),
            scheduled_time="10:00",
            duration_minutes=60,
        )
        
        # Tomorrow
        svc.add_scheduled_training(
            title="Tomorrow's Training",
            training_type="certification",
            scheduled_date=date.today() + timedelta(days=1),
            scheduled_time="14:00",
            duration_minutes=180,
        )
        
        today_trainings = svc.get_scheduled_trainings(target_date=date.today())
        assert len(today_trainings) == 1
        assert today_trainings[0].title == "Today's Training"

    def test_get_scheduled_trainings_enrolled_only(self, service):
        """Test filtering by enrolled trainings."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        svc.add_scheduled_training(
            title="Enrolled",
            training_type="refresher",
            scheduled_date=date.today(),
            scheduled_time="10:00",
            duration_minutes=60,
            is_user_enrolled=True,
        )
        svc.add_scheduled_training(
            title="Not Enrolled",
            training_type="refresher",
            scheduled_date=date.today(),
            scheduled_time="14:00",
            duration_minutes=60,
            is_user_enrolled=False,
        )
        
        enrolled = svc.get_scheduled_trainings(user_enrolled_only=True)
        assert len(enrolled) == 1
        assert enrolled[0].title == "Enrolled"

    def test_enroll_in_training(self, service):
        """Test enrolling in a training."""
        training = service.add_scheduled_training(
            title="Enrollment Test",
            training_type="certification",
            scheduled_date=date.today() + timedelta(days=3),
            scheduled_time="09:00",
            duration_minutes=240,
            attendee_count=5,
            max_attendees=10,
        )
        
        result = service.enroll_in_training(training.id)
        assert result is not None
        assert result.is_user_enrolled is True
        assert result.attendee_count == 6

    def test_enroll_in_full_training(self, service):
        """Test cannot enroll in full training."""
        training = service.add_scheduled_training(
            title="Full Training",
            training_type="certification",
            scheduled_date=date.today() + timedelta(days=1),
            scheduled_time="09:00",
            duration_minutes=60,
            attendee_count=10,
            max_attendees=10,
        )
        
        result = service.enroll_in_training(training.id)
        assert result is None

    def test_trainings_sorted_by_date_and_time(self, service):
        """Test trainings are sorted by date and time."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        svc.add_scheduled_training(
            title="Later Today",
            training_type="refresher",
            scheduled_date=date.today(),
            scheduled_time="14:00",
            duration_minutes=60,
        )
        svc.add_scheduled_training(
            title="Tomorrow Morning",
            training_type="refresher",
            scheduled_date=date.today() + timedelta(days=1),
            scheduled_time="09:00",
            duration_minutes=60,
        )
        svc.add_scheduled_training(
            title="Earlier Today",
            training_type="refresher",
            scheduled_date=date.today(),
            scheduled_time="10:00",
            duration_minutes=60,
        )
        
        trainings = svc.get_scheduled_trainings()
        assert trainings[0].title == "Earlier Today"
        assert trainings[1].title == "Later Today"
        assert trainings[2].title == "Tomorrow Morning"


class TestShopFloorSummary:
    """Tests for shop floor summary generation."""

    def test_get_shop_floor_summary_empty(self, service):
        """Test shop floor summary with no data."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        summary = svc.get_shop_floor_summary()
        
        assert isinstance(summary, ShopFloorSummary)
        assert summary.work_orders_at_risk_count == 0
        assert summary.unacknowledged_andon_count == 0
        assert summary.overall_oee == 0.0
        assert summary.expired_certification_count == 0
        assert summary.total_wip_violation_count == 0
        assert summary.overdue_capa_count == 0
        assert summary.training_sessions_today == 0

    def test_get_shop_floor_summary_with_data(self, service):
        """Test shop floor summary with various data."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        wc_id = uuid4()
        user_id = uuid4()
        
        # Add work order at risk
        svc.add_work_order_at_risk(
            work_order_number="WO-1",
            product_name="Product",
            quantity=100,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=5),
            reason="Test",
            work_center_id=wc_id,
            work_center_name="Test",
        )
        
        # Add critical Andon (unacknowledged)
        svc.add_critical_andon(
            andon_type="quality",
            title="Andon 1",
            work_center_id=wc_id,
            work_center_name="Test",
        )
        
        # Add cell OEE
        svc.add_cell_oee(
            cell_id=uuid4(),
            cell_name="Cell 1",
            work_center_id=wc_id,
            work_center_name="Test",
            availability=90.0,
            performance=90.0,
            quality=90.0,
            target_oee=80.0,
        )
        
        # Add expiring certification
        svc.add_expiring_certification(
            user_id=user_id,
            user_name="User",
            certification_name="Cert 1",
            certification_type="process",
            expiration_date=date.today() - timedelta(days=1),  # Expired
        )
        
        # Add WIP violation
        svc.add_wip_violation(
            work_center_id=wc_id,
            work_center_name="Test",
            current_wip=25,
            wip_limit=20,
        )
        
        # Add overdue CAPA
        svc.add_capa_verification(
            capa_number="CAPA-1",
            title="Test",
            capa_type="corrective",
            verification_due_date=date.today() - timedelta(days=1),
            owner_id=user_id,
            owner_name="Owner",
        )
        
        # Add today's training
        svc.add_scheduled_training(
            title="Training 1",
            training_type="refresher",
            scheduled_date=date.today(),
            scheduled_time="10:00",
            duration_minutes=60,
        )
        
        summary = svc.get_shop_floor_summary(user_id=user_id, work_center_id=wc_id)
        
        assert summary.work_orders_at_risk_count == 1
        assert summary.unacknowledged_andon_count == 1
        assert summary.overall_oee > 0
        assert summary.expired_certification_count == 1
        assert summary.total_wip_violation_count == 1
        assert summary.overdue_capa_count == 1
        assert summary.training_sessions_today == 1


class TestTodayScreenWithShopFloor:
    """Tests for Today screen with shop floor integration."""

    def test_today_screen_includes_shop_floor(self, service, sample_user_id, sample_user_name):
        """Test Today screen includes shop floor summary."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        # Add some shop floor data
        svc.add_work_order_at_risk(
            work_order_number="WO-TEST",
            product_name="Test Product",
            quantity=50,
            due_date=date.today(),
            estimated_completion=date.today() + timedelta(days=2),
            reason="Testing",
        )
        
        data = svc.get_today_screen(sample_user_id, sample_user_name)
        
        assert data.shop_floor is not None
        assert isinstance(data.shop_floor, ShopFloorSummary)
        assert data.shop_floor.work_orders_at_risk_count >= 1

    def test_shop_floor_abnormalities_in_today_screen(self, service, sample_user_id):
        """Test shop floor abnormality types work in Today screen."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        # Add shop floor abnormality
        abn = svc.add_abnormality(
            title="Critical Andon Unacknowledged",
            abnormality_type=AbnormalityType.CRITICAL_ANDON,
            entity_type="andon",
            entity_id=uuid4(),
            days_stale=0,
            severity=PriorityLevel.HIGH,
            owner_id=sample_user_id,
            owner_name="Test User",
            suggested_action="Acknowledge the Andon immediately",
        )
        
        abnormalities = svc.get_abnormalities(user_id=sample_user_id)
        assert len(abnormalities) == 1
        assert abnormalities[0].abnormality_type == AbnormalityType.CRITICAL_ANDON

    def test_shop_floor_commitments_in_today_screen(self, service, sample_user_id):
        """Test shop floor commitment types work in Today screen."""
        reset_today_screen_service()
        svc = get_today_screen_service()
        
        # Add training session commitment
        commitment = svc.add_commitment(
            title="Safety Training Session",
            commitment_type=CommitmentType.TRAINING_SESSION,
            due_date=date.today(),
            due_time="09:00",
            owner_id=sample_user_id,
            owner_name="Test User",
            description="Mandatory safety refresher",
        )
        
        commitments = svc.get_commitments(user_id=sample_user_id, target_date=date.today())
        assert len(commitments) == 1
        assert commitments[0].commitment_type == CommitmentType.TRAINING_SESSION


class TestShopFloorEnums:
    """Tests for shop floor enum values."""

    def test_shop_floor_area_type_values(self):
        """Test ShopFloorAreaType has expected values."""
        assert ShopFloorAreaType.WORK_CENTER == "work_center"
        assert ShopFloorAreaType.CELL == "cell"
        assert ShopFloorAreaType.STATION == "station"
        assert ShopFloorAreaType.LINE == "line"
        assert ShopFloorAreaType.DEPARTMENT == "department"

    def test_shop_floor_alert_severity_values(self):
        """Test ShopFloorAlertSeverity has expected values."""
        assert ShopFloorAlertSeverity.CRITICAL == "critical"
        assert ShopFloorAlertSeverity.WARNING == "warning"
        assert ShopFloorAlertSeverity.INFO == "info"

    def test_abnormality_type_shop_floor_values(self):
        """Test AbnormalityType includes shop floor values."""
        # Original values
        assert AbnormalityType.LATE_QUOTE == "late_quote"
        assert AbnormalityType.STALLED_RFQ == "stalled_rfq"
        
        # Shop floor values
        assert AbnormalityType.CRITICAL_ANDON == "critical_andon"
        assert AbnormalityType.WORK_ORDER_AT_RISK == "work_order_at_risk"
        assert AbnormalityType.CAPA_VERIFICATION_DUE == "capa_verification_due"
        assert AbnormalityType.STATION_LOW_EFFICIENCY == "station_low_efficiency"
        assert AbnormalityType.CELL_LOW_OEE == "cell_low_oee"
        assert AbnormalityType.KANBAN_OVERDUE == "kanban_overdue"
        assert AbnormalityType.EXPIRING_CERTIFICATION == "expiring_certification"
        assert AbnormalityType.WIP_LIMIT_VIOLATION == "wip_limit_violation"
        assert AbnormalityType.OPEN_NC_CRITICAL == "open_nc_critical"

    def test_commitment_type_shop_floor_values(self):
        """Test CommitmentType includes shop floor values."""
        # Original values
        assert CommitmentType.QUOTE_DUE == "quote_due"
        assert CommitmentType.MEETING == "meeting"
        
        # Shop floor values
        assert CommitmentType.TRAINING_SESSION == "training_session"
        assert CommitmentType.AUDIT_SCHEDULED == "audit_scheduled"
        assert CommitmentType.MAINTENANCE_DUE == "maintenance_due"
        assert CommitmentType.CERTIFICATION_RENEWAL == "certification_renewal"
        assert CommitmentType.SHIFT_HANDOFF == "shift_handoff"
        assert CommitmentType.PRODUCTION_TARGET == "production_target"

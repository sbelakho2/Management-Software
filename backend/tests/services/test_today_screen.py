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

from sensei.services.today_screen import (
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

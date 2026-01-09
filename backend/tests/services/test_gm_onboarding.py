"""
Tests for GM Onboarding Service

Tests the Day-1 onboarding functionality for new GM users.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from sensei.services.gm_onboarding import (
    GMDashboardTourSpot,
    GMFirstAction,
    GMKeyMetric,
    GMOnboardingService,
    OnboardingChecklistItem,
    OnboardingProgress,
    OnboardingStatus,
    OnboardingStep,
    OnboardingStepType,
    get_gm_onboarding_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service() -> GMOnboardingService:
    """Create a fresh onboarding service."""
    return GMOnboardingService()


@pytest.fixture
def user_id() -> str:
    """Sample user ID."""
    return "user-123"


@pytest.fixture
def started_onboarding(
    service: GMOnboardingService,
    user_id: str,
) -> OnboardingProgress:
    """Start onboarding for a user."""
    return service.start_onboarding(
        user_id=user_id,
        user_name="John Doe",
        role="GM",
    )


# =============================================================================
# Test Onboarding Initialization
# =============================================================================


class TestOnboardingInitialization:
    """Tests for onboarding initialization."""

    def test_start_onboarding_creates_progress(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test starting onboarding creates progress record."""
        progress = service.start_onboarding(
            user_id=user_id,
            user_name="John Doe",
            role="GM",
        )
        
        assert progress is not None
        assert progress.user_id == user_id
        assert progress.user_name == "John Doe"
        assert progress.role == "GM"

    def test_start_onboarding_sets_status(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test onboarding starts with in_progress status."""
        progress = service.start_onboarding(user_id, "John", "GM")
        
        assert progress.status == OnboardingStatus.IN_PROGRESS
        assert progress.started_at is not None
        assert progress.completed_at is None

    def test_start_onboarding_creates_steps(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test onboarding creates all required steps."""
        progress = service.start_onboarding(user_id, "John", "GM")
        
        assert len(progress.steps) > 0
        assert all(isinstance(s, OnboardingStep) for s in progress.steps)

    def test_steps_have_correct_order(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test steps are ordered correctly."""
        progress = service.start_onboarding(user_id, "John", "GM")
        
        orders = [s.order for s in progress.steps]
        assert orders == sorted(orders)

    def test_first_step_is_welcome(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test first step is welcome."""
        progress = service.start_onboarding(user_id, "John", "GM")
        
        first_step = progress.steps[0]
        assert first_step.step_type == OnboardingStepType.WELCOME

    def test_last_step_is_completion(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test last step is completion."""
        progress = service.start_onboarding(user_id, "John", "GM")
        
        last_step = progress.steps[-1]
        assert last_step.step_type == OnboardingStepType.COMPLETION


# =============================================================================
# Test Progress Tracking
# =============================================================================


class TestProgressTracking:
    """Tests for progress tracking."""

    def test_get_progress_returns_saved(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test get_progress returns saved progress."""
        service.start_onboarding(user_id, "John", "GM")
        
        progress = service.get_progress(user_id)
        assert progress is not None
        assert progress.user_id == user_id

    def test_get_progress_returns_none_for_unknown(
        self, service: GMOnboardingService
    ):
        """Test get_progress returns None for unknown user."""
        progress = service.get_progress("unknown-user")
        assert progress is None

    def test_current_step_initially_first(
        self, started_onboarding: OnboardingProgress
    ):
        """Test current step is first step initially."""
        assert started_onboarding.current_step_index == 0
        assert started_onboarding.current_step is not None

    def test_completion_percentage_starts_zero(
        self, started_onboarding: OnboardingProgress
    ):
        """Test completion percentage starts at 0."""
        assert started_onboarding.completion_percentage == 0.0

    def test_estimated_remaining_time(
        self, started_onboarding: OnboardingProgress
    ):
        """Test estimated remaining time is calculated."""
        assert started_onboarding.estimated_remaining_minutes > 0


# =============================================================================
# Test Step Management
# =============================================================================


class TestStepManagement:
    """Tests for step management."""

    def test_start_step(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test starting a step."""
        step = service.start_step(started_onboarding.user_id, "welcome")
        
        assert step is not None
        assert step.status == OnboardingStatus.IN_PROGRESS
        assert step.started_at is not None

    def test_complete_step(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test completing a step."""
        service.start_step(started_onboarding.user_id, "welcome")
        step = service.complete_step(started_onboarding.user_id, "welcome")
        
        assert step is not None
        assert step.status == OnboardingStatus.COMPLETED
        assert step.completed_at is not None
        assert step.is_complete is True

    def test_complete_step_with_data(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test completing a step with data."""
        step = service.complete_step(
            started_onboarding.user_id,
            "welcome",
            data={"acknowledged": True},
        )
        
        assert step.data["acknowledged"] is True

    def test_complete_step_updates_percentage(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test completing step updates percentage."""
        service.complete_step(started_onboarding.user_id, "welcome")
        
        progress = service.get_progress(started_onboarding.user_id)
        assert progress.completion_percentage > 0

    def test_skip_optional_step(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test skipping an optional step."""
        # Find an optional step
        optional_step = next(
            (s for s in started_onboarding.steps if not s.required),
            None
        )
        
        if optional_step:
            step = service.skip_step(started_onboarding.user_id, optional_step.id)
            assert step is not None
            assert step.status == OnboardingStatus.SKIPPED

    def test_cannot_skip_required_step(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test cannot skip required step."""
        # Welcome is required
        step = service.skip_step(started_onboarding.user_id, "welcome")
        assert step is None

    def test_time_spent_calculated(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test time spent is calculated on completion."""
        service.start_step(started_onboarding.user_id, "welcome")
        step = service.complete_step(started_onboarding.user_id, "welcome")
        
        assert step.time_spent_seconds >= 0


# =============================================================================
# Test Onboarding Completion
# =============================================================================


class TestOnboardingCompletion:
    """Tests for onboarding completion."""

    def test_complete_all_required_steps(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test completing all required steps completes onboarding."""
        # Complete all required steps
        for step in started_onboarding.steps:
            if step.required:
                service.complete_step(started_onboarding.user_id, step.id)
        
        progress = service.get_progress(started_onboarding.user_id)
        assert progress.status == OnboardingStatus.COMPLETED
        assert progress.completed_at is not None

    def test_completion_percentage_100(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test 100% completion when all steps done."""
        for step in started_onboarding.steps:
            service.complete_step(started_onboarding.user_id, step.id)
        
        progress = service.get_progress(started_onboarding.user_id)
        assert progress.completion_percentage == 100.0

    def test_skip_optional_counts_toward_completion(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test skipped optional steps count toward completion."""
        total_steps = len(started_onboarding.steps)
        
        for step in started_onboarding.steps:
            if step.required:
                service.complete_step(started_onboarding.user_id, step.id)
            else:
                service.skip_step(started_onboarding.user_id, step.id)
        
        progress = service.get_progress(started_onboarding.user_id)
        assert progress.completion_percentage == 100.0


# =============================================================================
# Test Dashboard Tour
# =============================================================================


class TestDashboardTour:
    """Tests for dashboard tour."""

    def test_get_dashboard_tour(self, service: GMOnboardingService):
        """Test getting dashboard tour spots."""
        spots = service.get_dashboard_tour()
        
        assert len(spots) > 0
        assert all(isinstance(s, GMDashboardTourSpot) for s in spots)

    def test_tour_spots_ordered(self, service: GMOnboardingService):
        """Test tour spots are ordered."""
        spots = service.get_dashboard_tour()
        
        orders = [s.order for s in spots]
        assert orders == sorted(orders)

    def test_tour_spots_have_selectors(self, service: GMOnboardingService):
        """Test tour spots have element selectors."""
        spots = service.get_dashboard_tour()
        
        for spot in spots:
            assert spot.element_selector
            assert spot.title
            assert spot.description


# =============================================================================
# Test Key Metrics
# =============================================================================


class TestKeyMetrics:
    """Tests for key metrics."""

    def test_get_key_metrics(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test getting key metrics."""
        metrics = service.get_key_metrics(user_id)
        
        assert len(metrics) > 0
        assert all(isinstance(m, GMKeyMetric) for m in metrics)

    def test_metrics_have_required_fields(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test metrics have required fields."""
        metrics = service.get_key_metrics(user_id)
        
        for metric in metrics:
            assert metric.id
            assert metric.name
            assert metric.description
            assert metric.importance in ["high", "medium", "low"]


# =============================================================================
# Test First Actions
# =============================================================================


class TestFirstActions:
    """Tests for first actions."""

    def test_get_first_actions(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test getting first actions."""
        actions = service.get_first_actions(user_id)
        
        assert len(actions) > 0
        assert all(isinstance(a, GMFirstAction) for a in actions)

    def test_actions_have_priorities(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test actions have priorities."""
        actions = service.get_first_actions(user_id)
        
        priorities = [a.priority for a in actions]
        assert all(p > 0 for p in priorities)

    def test_actions_have_urls(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test actions have URLs."""
        actions = service.get_first_actions(user_id)
        
        for action in actions:
            assert action.url

    def test_complete_first_action(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test completing a first action."""
        action = service.complete_first_action(
            started_onboarding.user_id,
            "review_today",
        )
        
        assert action is not None
        assert action.completed is True


# =============================================================================
# Test Workflow Checklist
# =============================================================================


class TestWorkflowChecklist:
    """Tests for workflow checklist."""

    def test_get_workflow_checklist(self, service: GMOnboardingService):
        """Test getting workflow checklist."""
        checklist = service.get_workflow_checklist()
        
        assert len(checklist) > 0
        assert all(isinstance(i, OnboardingChecklistItem) for i in checklist)

    def test_checklist_items_have_actions(self, service: GMOnboardingService):
        """Test checklist items have action URLs."""
        checklist = service.get_workflow_checklist()
        
        for item in checklist:
            assert item.action_url


# =============================================================================
# Test Listeners
# =============================================================================


class TestListeners:
    """Tests for progress listeners."""

    def test_add_listener(self, service: GMOnboardingService):
        """Test adding a listener."""
        listener = MagicMock()
        service.add_listener(listener)
        
        assert listener in service._listeners

    def test_remove_listener(self, service: GMOnboardingService):
        """Test removing a listener."""
        listener = MagicMock()
        service.add_listener(listener)
        service.remove_listener(listener)
        
        assert listener not in service._listeners

    def test_listener_called_on_start(
        self, service: GMOnboardingService, user_id: str
    ):
        """Test listener is called when onboarding starts."""
        listener = MagicMock()
        service.add_listener(listener)
        
        service.start_onboarding(user_id, "John", "GM")
        
        listener.assert_called_once()

    def test_listener_called_on_step_complete(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test listener is called when step completes."""
        listener = MagicMock()
        service.add_listener(listener)
        
        service.complete_step(started_onboarding.user_id, "welcome")
        
        listener.assert_called_once()


# =============================================================================
# Test Reset
# =============================================================================


class TestReset:
    """Tests for reset functionality."""

    def test_reset_onboarding(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test resetting onboarding."""
        result = service.reset_onboarding(started_onboarding.user_id)
        
        assert result is True
        assert service.get_progress(started_onboarding.user_id) is None

    def test_reset_unknown_user(self, service: GMOnboardingService):
        """Test resetting unknown user returns False."""
        result = service.reset_onboarding("unknown-user")
        assert result is False


# =============================================================================
# Test Summary
# =============================================================================


class TestSummary:
    """Tests for onboarding summary."""

    def test_get_summary_not_started(
        self, service: GMOnboardingService
    ):
        """Test summary for user who hasn't started."""
        summary = service.get_onboarding_summary("unknown-user")
        
        assert summary["status"] == OnboardingStatus.NOT_STARTED.value
        assert summary["has_started"] is False

    def test_get_summary_in_progress(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test summary for in-progress onboarding."""
        summary = service.get_onboarding_summary(started_onboarding.user_id)
        
        assert summary["has_started"] is True
        assert summary["started_at"] is not None
        assert summary["completion_percentage"] == 0.0

    def test_get_summary_completed(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test summary for completed onboarding."""
        # Complete all required steps
        for step in started_onboarding.steps:
            if step.required:
                service.complete_step(started_onboarding.user_id, step.id)
        
        summary = service.get_onboarding_summary(started_onboarding.user_id)
        
        assert summary["status"] == OnboardingStatus.COMPLETED.value
        assert summary["completed_at"] is not None


# =============================================================================
# Test Singleton
# =============================================================================


class TestSingleton:
    """Tests for singleton instance."""

    def test_get_gm_onboarding_service(self):
        """Test getting singleton service."""
        service1 = get_gm_onboarding_service()
        service2 = get_gm_onboarding_service()
        
        assert service1 is service2


# =============================================================================
# Test OnboardingStep Properties
# =============================================================================


class TestOnboardingStepProperties:
    """Tests for OnboardingStep properties."""

    def test_is_complete_false_initially(self):
        """Test is_complete is False initially."""
        step = OnboardingStep(
            id="test",
            step_type=OnboardingStepType.WELCOME,
            title="Test",
            description="Test step",
            order=1,
        )
        
        assert step.is_complete is False

    def test_is_complete_true_when_completed(self):
        """Test is_complete is True when completed."""
        step = OnboardingStep(
            id="test",
            step_type=OnboardingStepType.WELCOME,
            title="Test",
            description="Test step",
            order=1,
            status=OnboardingStatus.COMPLETED,
        )
        
        assert step.is_complete is True

    def test_can_skip_false_for_required(self):
        """Test can_skip is False for required steps."""
        step = OnboardingStep(
            id="test",
            step_type=OnboardingStepType.WELCOME,
            title="Test",
            description="Test step",
            order=1,
            required=True,
        )
        
        assert step.can_skip is False

    def test_can_skip_true_for_optional(self):
        """Test can_skip is True for optional steps."""
        step = OnboardingStep(
            id="test",
            step_type=OnboardingStepType.WELCOME,
            title="Test",
            description="Test step",
            order=1,
            required=False,
        )
        
        assert step.can_skip is True


# =============================================================================
# Test OnboardingProgress Properties
# =============================================================================


class TestOnboardingProgressProperties:
    """Tests for OnboardingProgress properties."""

    def test_completed_steps(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test completed_steps property."""
        service.complete_step(started_onboarding.user_id, "welcome")
        
        progress = service.get_progress(started_onboarding.user_id)
        assert len(progress.completed_steps) == 1

    def test_remaining_steps(
        self, service: GMOnboardingService, started_onboarding: OnboardingProgress
    ):
        """Test remaining_steps property."""
        initial_remaining = len(started_onboarding.remaining_steps)
        
        service.complete_step(started_onboarding.user_id, "welcome")
        
        progress = service.get_progress(started_onboarding.user_id)
        assert len(progress.remaining_steps) == initial_remaining - 1

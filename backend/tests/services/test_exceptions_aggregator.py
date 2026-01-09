"""
Tests for Exceptions Aggregator Service

Tests the unified exceptions view, navigation badges,
and exceptions-first dashboard functionality.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from sensei.services.exceptions_aggregator import (
    ExceptionCategory,
    ExceptionItem,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionSummary,
    ExceptionsAggregator,
    NavigationBadge,
    create_exception,
    get_exceptions_aggregator,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def aggregator() -> ExceptionsAggregator:
    """Create a fresh aggregator for testing."""
    return ExceptionsAggregator()


@pytest.fixture
def sample_exception() -> ExceptionItem:
    """Create a sample exception."""
    return create_exception(
        title="Critical Production Issue",
        description="Machine 5 down, line stopped",
        category=ExceptionCategory.PRODUCTION,
        severity=ExceptionSeverity.CRITICAL,
        owner_id="user-1",
        owner_name="John Doe",
        due_date=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@pytest.fixture
def sample_exceptions() -> list[ExceptionItem]:
    """Create a list of sample exceptions."""
    now = datetime.now(timezone.utc)
    return [
        create_exception(
            title="Critical Andon Alert",
            description="Safety issue on line 3",
            category=ExceptionCategory.ANDON,
            severity=ExceptionSeverity.CRITICAL,
            due_date=now + timedelta(hours=1),
        ),
        create_exception(
            title="Overdue Quote",
            description="Quote for Customer X is overdue",
            category=ExceptionCategory.QUOTE,
            severity=ExceptionSeverity.HIGH,
            due_date=now - timedelta(hours=2),  # Overdue
        ),
        create_exception(
            title="Quality NCR",
            description="Non-conformance on part ABC",
            category=ExceptionCategory.QUALITY,
            severity=ExceptionSeverity.MEDIUM,
            due_date=now + timedelta(days=1),
        ),
        create_exception(
            title="Training Gap",
            description="Operator needs certification",
            category=ExceptionCategory.TRAINING,
            severity=ExceptionSeverity.LOW,
            due_date=now + timedelta(days=7),
        ),
    ]


# =============================================================================
# Test ExceptionItem
# =============================================================================


class TestExceptionItem:
    """Tests for ExceptionItem dataclass."""

    def test_create_exception(self, sample_exception: ExceptionItem):
        """Test creating an exception item."""
        assert sample_exception.id is not None
        assert sample_exception.title == "Critical Production Issue"
        assert sample_exception.category == ExceptionCategory.PRODUCTION
        assert sample_exception.severity == ExceptionSeverity.CRITICAL
        assert sample_exception.status == ExceptionStatus.OPEN

    def test_is_overdue_false(self, sample_exception: ExceptionItem):
        """Test is_overdue returns False when not overdue."""
        assert sample_exception.is_overdue is False

    def test_is_overdue_true(self):
        """Test is_overdue returns True when past due date."""
        exception = create_exception(
            title="Overdue Item",
            description="This is overdue",
            category=ExceptionCategory.TASK,
            severity=ExceptionSeverity.HIGH,
            due_date=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert exception.is_overdue is True

    def test_is_overdue_no_due_date(self):
        """Test is_overdue returns False when no due date."""
        exception = create_exception(
            title="No Due Date",
            description="No deadline",
            category=ExceptionCategory.TASK,
            severity=ExceptionSeverity.LOW,
        )
        assert exception.is_overdue is False

    def test_time_to_due(self, sample_exception: ExceptionItem):
        """Test time_to_due calculation."""
        ttd = sample_exception.time_to_due
        assert ttd is not None
        assert ttd.total_seconds() > 0

    def test_age_minutes(self, sample_exception: ExceptionItem):
        """Test age_minutes calculation."""
        # Newly created, should be close to 0
        assert sample_exception.age_minutes >= 0
        assert sample_exception.age_minutes < 1

    def test_priority_score_critical(self):
        """Test priority score for critical severity."""
        exception = create_exception(
            title="Critical",
            description="Critical issue",
            category=ExceptionCategory.ANDON,
            severity=ExceptionSeverity.CRITICAL,
        )
        assert exception.priority_score >= 100

    def test_priority_score_high(self):
        """Test priority score for high severity."""
        exception = create_exception(
            title="High",
            description="High priority",
            category=ExceptionCategory.QUOTE,
            severity=ExceptionSeverity.HIGH,
        )
        assert 70 <= exception.priority_score < 100

    def test_priority_score_overdue_bonus(self):
        """Test priority score increases when overdue."""
        exception = create_exception(
            title="Overdue",
            description="Overdue item",
            category=ExceptionCategory.TASK,
            severity=ExceptionSeverity.MEDIUM,
            due_date=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        # Medium is 40, overdue adds up to 50
        assert exception.priority_score > 40

    def test_priority_score_escalated_bonus(self):
        """Test priority score increases when escalated."""
        exception = create_exception(
            title="Escalated",
            description="Escalated issue",
            category=ExceptionCategory.A3,
            severity=ExceptionSeverity.HIGH,
        )
        exception.status = ExceptionStatus.ESCALATED
        # High is 70, escalated adds 30
        assert exception.priority_score >= 100


# =============================================================================
# Test ExceptionsAggregator Initialization
# =============================================================================


class TestAggregatorInitialization:
    """Tests for aggregator initialization."""

    def test_creates_empty_aggregator(self, aggregator: ExceptionsAggregator):
        """Test aggregator starts empty."""
        assert len(aggregator.get_all()) == 0

    def test_no_sources_initially(self, aggregator: ExceptionsAggregator):
        """Test no sources registered initially."""
        assert len(aggregator._sources) == 0


# =============================================================================
# Test Source Registration
# =============================================================================


class TestSourceRegistration:
    """Tests for exception source registration."""

    def test_register_source(self, aggregator: ExceptionsAggregator):
        """Test registering an exception source."""
        source = MagicMock(return_value=[])
        aggregator.register_source("test", source)
        assert "test" in aggregator._sources

    def test_unregister_source(self, aggregator: ExceptionsAggregator):
        """Test unregistering an exception source."""
        source = MagicMock(return_value=[])
        aggregator.register_source("test", source)
        aggregator.unregister_source("test")
        assert "test" not in aggregator._sources

    def test_refresh_calls_sources(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test refresh calls registered sources."""
        source = MagicMock(return_value=[sample_exception])
        aggregator.register_source("test", source)
        
        aggregator.refresh(force=True)
        
        source.assert_called_once()
        exceptions = aggregator.get_all()
        assert len(exceptions) == 1
        assert exceptions[0].title == sample_exception.title

    def test_refresh_handles_source_errors(self, aggregator: ExceptionsAggregator):
        """Test refresh continues when a source fails."""
        failing_source = MagicMock(side_effect=Exception("Source error"))
        working_source = MagicMock(return_value=[
            create_exception(
                title="Working",
                description="From working source",
                category=ExceptionCategory.TASK,
                severity=ExceptionSeverity.LOW,
            )
        ])
        
        aggregator.register_source("failing", failing_source)
        aggregator.register_source("working", working_source)
        
        aggregator.refresh(force=True)
        
        # Should still have the exception from the working source
        exceptions = aggregator.get_all()
        assert len(exceptions) == 1


# =============================================================================
# Test Exception Management
# =============================================================================


class TestExceptionManagement:
    """Tests for exception CRUD operations."""

    def test_add_exception(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test adding an exception manually."""
        aggregator.add_exception(sample_exception)
        
        exceptions = aggregator.get_all()
        assert len(exceptions) == 1
        assert exceptions[0].id == sample_exception.id

    def test_update_exception(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test updating an exception."""
        aggregator.add_exception(sample_exception)
        
        updated = aggregator.update_exception(
            sample_exception.id,
            {"status": ExceptionStatus.ACKNOWLEDGED}
        )
        
        assert updated is not None
        assert updated.status == ExceptionStatus.ACKNOWLEDGED

    def test_update_nonexistent_exception(self, aggregator: ExceptionsAggregator):
        """Test updating a non-existent exception returns None."""
        result = aggregator.update_exception("nonexistent", {"status": ExceptionStatus.RESOLVED})
        assert result is None

    def test_resolve_exception(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test resolving an exception."""
        aggregator.add_exception(sample_exception)
        
        resolved = aggregator.resolve_exception(sample_exception.id)
        
        assert resolved is not None
        assert resolved.status == ExceptionStatus.RESOLVED
        assert resolved.resolution_time_minutes is not None

    def test_escalate_exception(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test escalating an exception."""
        aggregator.add_exception(sample_exception)
        
        escalated = aggregator.escalate_exception(
            sample_exception.id,
            escalate_to="manager@example.com"
        )
        
        assert escalated is not None
        assert escalated.status == ExceptionStatus.ESCALATED
        assert escalated.escalated_to == "manager@example.com"
        assert escalated.escalated_at is not None

    def test_acknowledge_exception(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test acknowledging an exception."""
        aggregator.add_exception(sample_exception)
        
        acked = aggregator.acknowledge_exception(sample_exception.id)
        
        assert acked is not None
        assert acked.status == ExceptionStatus.ACKNOWLEDGED


# =============================================================================
# Test Filtering
# =============================================================================


class TestFiltering:
    """Tests for exception filtering."""

    def test_get_by_category(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test filtering by category."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        andon = aggregator.get_by_category(ExceptionCategory.ANDON)
        assert len(andon) == 1
        assert andon[0].category == ExceptionCategory.ANDON

    def test_get_by_severity(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test filtering by severity."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        critical = aggregator.get_all(severity=ExceptionSeverity.CRITICAL)
        assert len(critical) == 1
        assert critical[0].severity == ExceptionSeverity.CRITICAL

    def test_get_by_status(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test filtering by status."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        # All should be open initially
        open_items = aggregator.get_all(status=ExceptionStatus.OPEN)
        assert len(open_items) == 4

    def test_get_overdue(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test getting overdue exceptions."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        overdue = aggregator.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].is_overdue is True

    def test_get_critical(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test getting critical/high exceptions."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        critical = aggregator.get_critical()
        assert len(critical) == 2  # 1 critical + 1 high

    def test_get_escalated(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test getting escalated exceptions."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        # Escalate one
        aggregator.escalate_exception(sample_exceptions[0].id, "manager@example.com")
        
        escalated = aggregator.get_escalated()
        assert len(escalated) == 1

    def test_get_with_limit(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test limiting results."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        limited = aggregator.get_all(limit=2)
        assert len(limited) == 2


# =============================================================================
# Test Summary
# =============================================================================


class TestSummary:
    """Tests for exception summary."""

    def test_get_summary(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test getting exception summary."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        summary = aggregator.get_summary()
        
        assert summary.total_open == 4
        assert summary.critical_count == 1
        assert summary.high_count == 1
        assert summary.overdue_count == 1
        assert len(summary.by_category) > 0

    def test_summary_excludes_resolved(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test summary excludes resolved exceptions."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        # Resolve one
        aggregator.resolve_exception(sample_exceptions[0].id)
        
        summary = aggregator.get_summary()
        assert summary.total_open == 3

    def test_summary_counts_escalated(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test summary counts escalated exceptions."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        aggregator.escalate_exception(sample_exceptions[0].id, "manager")
        
        summary = aggregator.get_summary()
        assert summary.escalated_count == 1

    def test_summary_by_category(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test summary includes by_category breakdown."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        summary = aggregator.get_summary()
        
        assert "andon" in summary.by_category
        assert summary.by_category["andon"] == 1


# =============================================================================
# Test Navigation Badges
# =============================================================================


class TestNavigationBadges:
    """Tests for navigation badge generation."""

    def test_get_navigation_badges(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test generating navigation badges."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        badges = aggregator.get_navigation_badges()
        
        assert len(badges) > 0
        assert all(isinstance(b, NavigationBadge) for b in badges)

    def test_badges_map_to_modules(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test badges map categories to navigation modules."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        badges = aggregator.get_navigation_badges()
        modules = [b.module for b in badges]
        
        # Production should appear (from andon)
        assert "production" in modules or "quotes" in modules or "quality" in modules

    def test_badges_use_highest_severity(self, aggregator: ExceptionsAggregator):
        """Test badges use highest severity for module."""
        # Add two production issues with different severities
        aggregator.add_exception(create_exception(
            title="Low Production Issue",
            description="Minor issue",
            category=ExceptionCategory.PRODUCTION,
            severity=ExceptionSeverity.LOW,
        ))
        aggregator.add_exception(create_exception(
            title="Critical Production Issue",
            description="Major issue",
            category=ExceptionCategory.PRODUCTION,
            severity=ExceptionSeverity.CRITICAL,
        ))
        
        badges = aggregator.get_navigation_badges()
        production_badge = next((b for b in badges if b.module == "production"), None)
        
        assert production_badge is not None
        assert production_badge.severity == ExceptionSeverity.CRITICAL
        assert production_badge.count == 2

    def test_badges_exclude_resolved(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test badges exclude resolved exceptions."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        # Resolve all
        for e in sample_exceptions:
            aggregator.resolve_exception(e.id)
        
        badges = aggregator.get_navigation_badges()
        assert len(badges) == 0


# =============================================================================
# Test Trends
# =============================================================================


class TestTrends:
    """Tests for exception trend data."""

    def test_get_trends(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test getting exception trends."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        trends = aggregator.get_trends(days=7)
        
        assert len(trends) == 7
        assert all(hasattr(t, "critical") for t in trends)

    def test_trends_count_by_severity(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test trends count by severity."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        trends = aggregator.get_trends(days=1)
        today = trends[-1]
        
        # All created today
        assert today.created == 4
        assert today.critical == 1
        assert today.high == 1
        assert today.medium == 1
        assert today.low == 1


# =============================================================================
# Test Listeners
# =============================================================================


class TestListeners:
    """Tests for exception update listeners."""

    def test_add_listener(self, aggregator: ExceptionsAggregator):
        """Test adding a listener."""
        listener = MagicMock()
        aggregator.add_listener(listener)
        assert listener in aggregator._listeners

    def test_remove_listener(self, aggregator: ExceptionsAggregator):
        """Test removing a listener."""
        listener = MagicMock()
        aggregator.add_listener(listener)
        aggregator.remove_listener(listener)
        assert listener not in aggregator._listeners

    def test_listeners_called_on_add(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test listeners are called when exception is added."""
        listener = MagicMock()
        aggregator.add_listener(listener)
        
        aggregator.add_exception(sample_exception)
        
        listener.assert_called_once()
        call_args = listener.call_args[0][0]
        assert isinstance(call_args, ExceptionSummary)

    def test_listeners_called_on_update(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test listeners are called when exception is updated."""
        aggregator.add_exception(sample_exception)
        
        listener = MagicMock()
        aggregator.add_listener(listener)
        
        aggregator.update_exception(sample_exception.id, {"status": ExceptionStatus.ACKNOWLEDGED})
        
        listener.assert_called_once()

    def test_listener_errors_dont_break_flow(
        self, aggregator: ExceptionsAggregator, sample_exception: ExceptionItem
    ):
        """Test listener errors don't break the flow."""
        failing_listener = MagicMock(side_effect=Exception("Listener error"))
        working_listener = MagicMock()
        
        aggregator.add_listener(failing_listener)
        aggregator.add_listener(working_listener)
        
        # Should not raise
        aggregator.add_exception(sample_exception)
        
        # Both should have been called
        failing_listener.assert_called_once()
        working_listener.assert_called_once()


# =============================================================================
# Test Singleton
# =============================================================================


class TestSingleton:
    """Tests for singleton instance."""

    def test_get_exceptions_aggregator(self):
        """Test getting singleton aggregator."""
        agg1 = get_exceptions_aggregator()
        agg2 = get_exceptions_aggregator()
        assert agg1 is agg2


# =============================================================================
# Test Caching
# =============================================================================


class TestCaching:
    """Tests for refresh caching."""

    def test_refresh_respects_cache(self, aggregator: ExceptionsAggregator):
        """Test refresh respects cache TTL."""
        source = MagicMock(return_value=[])
        aggregator.register_source("test", source)
        
        # First refresh
        aggregator.refresh()
        
        # Second refresh should use cache
        aggregator.refresh()
        
        # Source should only be called once
        assert source.call_count == 1

    def test_force_refresh_ignores_cache(self, aggregator: ExceptionsAggregator):
        """Test force refresh ignores cache."""
        source = MagicMock(return_value=[])
        aggregator.register_source("test", source)
        
        aggregator.refresh()
        aggregator.refresh(force=True)
        
        assert source.call_count == 2


# =============================================================================
# Test Sorting
# =============================================================================


class TestSorting:
    """Tests for exception sorting by priority."""

    def test_exceptions_sorted_by_priority(
        self, aggregator: ExceptionsAggregator, sample_exceptions: list[ExceptionItem]
    ):
        """Test exceptions are sorted by priority score."""
        for e in sample_exceptions:
            aggregator.add_exception(e)
        
        exceptions = aggregator.get_all()
        
        # Should be sorted by priority (highest first)
        for i in range(len(exceptions) - 1):
            assert exceptions[i].priority_score >= exceptions[i + 1].priority_score

    def test_critical_appears_first(self, aggregator: ExceptionsAggregator):
        """Test critical exceptions appear first."""
        aggregator.add_exception(create_exception(
            title="Low",
            description="Low priority",
            category=ExceptionCategory.TASK,
            severity=ExceptionSeverity.LOW,
        ))
        aggregator.add_exception(create_exception(
            title="Critical",
            description="Critical priority",
            category=ExceptionCategory.ANDON,
            severity=ExceptionSeverity.CRITICAL,
        ))
        
        exceptions = aggregator.get_all()
        assert exceptions[0].severity == ExceptionSeverity.CRITICAL

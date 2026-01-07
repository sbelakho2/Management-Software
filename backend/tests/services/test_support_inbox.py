"""Tests for Support Inbox Service."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sensei.services.support_inbox import (
    SupportInboxService,
    SupportTicket,
    TicketComment,
    TicketAttachment,
    RoutingDecision,
    UserFeedback,
    RoutingRule,
    A3LiteRecord,
    InboxStats,
    TicketPriority,
    TicketStatus,
    TicketCategory,
    FeedbackType,
    RoutingTarget,
)


class TestEnums:
    """Tests for enum values."""

    def test_ticket_priority_values(self) -> None:
        """Test TicketPriority enum values."""
        assert TicketPriority.LOW.value == "low"
        assert TicketPriority.MEDIUM.value == "medium"
        assert TicketPriority.HIGH.value == "high"
        assert TicketPriority.CRITICAL.value == "critical"

    def test_ticket_status_values(self) -> None:
        """Test TicketStatus enum values."""
        assert TicketStatus.OPEN.value == "open"
        assert TicketStatus.IN_PROGRESS.value == "in_progress"
        assert TicketStatus.RESOLVED.value == "resolved"
        assert TicketStatus.CLOSED.value == "closed"
        assert TicketStatus.ESCALATED.value == "escalated"

    def test_ticket_category_values(self) -> None:
        """Test TicketCategory enum values."""
        assert TicketCategory.BUG.value == "bug"
        assert TicketCategory.FEATURE_REQUEST.value == "feature_request"
        assert TicketCategory.QUESTION.value == "question"

    def test_feedback_type_values(self) -> None:
        """Test FeedbackType enum values."""
        assert FeedbackType.SUGGESTION.value == "suggestion"
        assert FeedbackType.COMPLAINT.value == "complaint"
        assert FeedbackType.BUG_REPORT.value == "bug_report"

    def test_routing_target_values(self) -> None:
        """Test RoutingTarget enum values."""
        assert RoutingTarget.A3_LITE.value == "a3_lite"
        assert RoutingTarget.TASK.value == "task"
        assert RoutingTarget.MANUAL_REVIEW.value == "manual_review"


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_service_creates(self) -> None:
        """Test service initializes."""
        service = SupportInboxService()
        assert service is not None

    def test_default_sla_hours(self) -> None:
        """Test default SLA hours set."""
        service = SupportInboxService()
        sla = service.get_sla_config()

        assert sla["critical"] == 2
        assert sla["high"] == 8
        assert sla["medium"] == 24
        assert sla["low"] == 72

    def test_default_routing_rules(self) -> None:
        """Test default routing rules created."""
        service = SupportInboxService()
        rules = service.get_routing_rules()

        assert len(rules) >= 5


class TestTicketCreation:
    """Tests for ticket creation."""

    def test_create_ticket(self) -> None:
        """Test creating a ticket."""
        service = SupportInboxService()
        user_id = uuid4()

        ticket = service.create_ticket(
            subject="Login not working",
            description="Cannot access the system",
            submitted_by=user_id,
            submitter_name="John Doe",
            submitter_email="john@example.com",
            category=TicketCategory.BUG,
            priority=TicketPriority.HIGH,
        )

        assert ticket is not None
        assert ticket.subject == "Login not working"
        assert ticket.status == TicketStatus.OPEN

    def test_create_ticket_sets_sla(self) -> None:
        """Test creating a ticket sets SLA due date."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            subject="Test",
            description="Test",
            submitted_by=uuid4(),
            priority=TicketPriority.CRITICAL,
        )

        assert ticket.sla_due_at is not None
        # Critical = 2 hours
        expected = ticket.created_at + timedelta(hours=2)
        assert abs((ticket.sla_due_at - expected).total_seconds()) < 1

    def test_create_ticket_with_related_entity(self) -> None:
        """Test creating ticket with related entity."""
        service = SupportInboxService()
        entity_id = uuid4()

        ticket = service.create_ticket(
            subject="RFQ Question",
            description="Question about RFQ",
            submitted_by=uuid4(),
            related_entity_type="rfq",
            related_entity_id=entity_id,
        )

        assert ticket.related_entity_type == "rfq"
        assert ticket.related_entity_id == entity_id

    def test_create_ticket_with_tags(self) -> None:
        """Test creating ticket with tags."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            subject="Test",
            description="Test",
            submitted_by=uuid4(),
            tags=["urgent", "production"],
        )

        assert "urgent" in ticket.tags
        assert "production" in ticket.tags

    def test_create_ticket_auto_routes(self) -> None:
        """Test ticket is auto-routed."""
        service = SupportInboxService()

        # Critical bug should route to A3
        ticket = service.create_ticket(
            subject="Critical Bug",
            description="System crashed",
            submitted_by=uuid4(),
            category=TicketCategory.BUG,
            priority=TicketPriority.CRITICAL,
        )

        assert ticket.routing_decision is not None
        assert ticket.routing_decision.target == RoutingTarget.A3_LITE

    def test_create_ticket_no_auto_route(self) -> None:
        """Test ticket without auto-routing."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            subject="Test",
            description="Test",
            submitted_by=uuid4(),
            auto_route=False,
        )

        assert ticket.routing_decision is None


class TestTicketRetrieval:
    """Tests for ticket retrieval."""

    def test_get_ticket_by_id(self) -> None:
        """Test getting ticket by ID."""
        service = SupportInboxService()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        found = service.get_ticket(ticket.id)
        assert found is not None
        assert found.subject == "Test"

    def test_get_nonexistent_ticket(self) -> None:
        """Test getting nonexistent ticket."""
        service = SupportInboxService()

        result = service.get_ticket(uuid4())
        assert result is None

    def test_get_tickets_by_status(self) -> None:
        """Test filtering tickets by status."""
        service = SupportInboxService()

        service.create_ticket("T1", "D1", uuid4())
        service.create_ticket("T2", "D2", uuid4())

        open_tickets = service.get_tickets(status=TicketStatus.OPEN)
        assert all(t.status == TicketStatus.OPEN for t in open_tickets)

    def test_get_tickets_by_category(self) -> None:
        """Test filtering tickets by category."""
        service = SupportInboxService()

        service.create_ticket("Bug", "D1", uuid4(), category=TicketCategory.BUG)
        service.create_ticket("Feature", "D2", uuid4(), category=TicketCategory.FEATURE_REQUEST)

        bugs = service.get_tickets(category=TicketCategory.BUG)
        assert all(t.category == TicketCategory.BUG for t in bugs)

    def test_get_tickets_by_priority(self) -> None:
        """Test filtering tickets by priority."""
        service = SupportInboxService()

        service.create_ticket("High", "D1", uuid4(), priority=TicketPriority.HIGH)
        service.create_ticket("Low", "D2", uuid4(), priority=TicketPriority.LOW)

        high = service.get_tickets(priority=TicketPriority.HIGH)
        assert all(t.priority == TicketPriority.HIGH for t in high)

    def test_get_tickets_by_assignee(self) -> None:
        """Test filtering tickets by assignee."""
        service = SupportInboxService()
        assignee_id = uuid4()

        t1 = service.create_ticket("T1", "D1", uuid4())
        service.assign_ticket(t1.id, assignee_id)
        service.create_ticket("T2", "D2", uuid4())

        assigned = service.get_tickets(assigned_to=assignee_id)
        assert all(t.assigned_to == assignee_id for t in assigned)


class TestTicketUpdates:
    """Tests for ticket updates."""

    def test_update_ticket_subject(self) -> None:
        """Test updating ticket subject."""
        service = SupportInboxService()

        ticket = service.create_ticket("Old Subject", "Desc", uuid4())

        updated = service.update_ticket(ticket.id, subject="New Subject")
        assert updated is not None
        assert updated.subject == "New Subject"

    def test_update_ticket_priority(self) -> None:
        """Test updating ticket priority."""
        service = SupportInboxService()

        ticket = service.create_ticket("Test", "Desc", uuid4(), priority=TicketPriority.LOW)

        updated = service.update_ticket(ticket.id, priority=TicketPriority.HIGH)
        assert updated is not None
        assert updated.priority == TicketPriority.HIGH

    def test_update_nonexistent_ticket(self) -> None:
        """Test updating nonexistent ticket."""
        service = SupportInboxService()

        result = service.update_ticket(uuid4(), subject="New")
        assert result is None

    def test_assign_ticket(self) -> None:
        """Test assigning a ticket."""
        service = SupportInboxService()
        assignee_id = uuid4()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        assigned = service.assign_ticket(ticket.id, assignee_id, "Jane Doe")
        assert assigned is not None
        assert assigned.assigned_to == assignee_id
        assert assigned.status == TicketStatus.IN_PROGRESS


class TestTicketComments:
    """Tests for ticket comments."""

    def test_add_comment(self) -> None:
        """Test adding a comment."""
        service = SupportInboxService()
        author_id = uuid4()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        comment = service.add_comment(
            ticket.id,
            author_id,
            "Support Agent",
            "Working on this",
            is_from_user=False,
        )

        assert comment is not None
        assert comment.content == "Working on this"
        assert len(ticket.comments) == 1

    def test_add_comment_tracks_first_response(self) -> None:
        """Test first response is tracked."""
        service = SupportInboxService()

        ticket = service.create_ticket("Test", "Desc", uuid4())
        assert ticket.first_response_at is None

        service.add_comment(ticket.id, uuid4(), "Agent", "Response", is_from_user=False)

        assert ticket.first_response_at is not None

    def test_add_internal_comment(self) -> None:
        """Test adding internal comment."""
        service = SupportInboxService()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        comment = service.add_comment(
            ticket.id,
            uuid4(),
            "Agent",
            "Internal note",
            is_internal=True,
        )

        assert comment is not None
        assert comment.is_internal is True


class TestTicketStatus:
    """Tests for ticket status changes."""

    def test_change_status_to_resolved(self) -> None:
        """Test changing status to resolved."""
        service = SupportInboxService()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        updated = service.change_status(ticket.id, TicketStatus.RESOLVED)
        assert updated is not None
        assert updated.status == TicketStatus.RESOLVED
        assert updated.resolved_at is not None

    def test_change_status_to_closed(self) -> None:
        """Test changing status to closed."""
        service = SupportInboxService()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        updated = service.change_status(ticket.id, TicketStatus.CLOSED)
        assert updated is not None
        assert updated.status == TicketStatus.CLOSED
        assert updated.closed_at is not None

    def test_escalate_ticket(self) -> None:
        """Test escalating a ticket."""
        service = SupportInboxService()
        escalate_to = uuid4()

        ticket = service.create_ticket("Test", "Desc", uuid4())

        escalated = service.escalate_ticket(ticket.id, "Needs manager", escalate_to)
        assert escalated is not None
        assert escalated.status == TicketStatus.ESCALATED
        assert escalated.priority == TicketPriority.HIGH
        assert escalated.assigned_to == escalate_to


class TestRouting:
    """Tests for ticket routing."""

    def test_route_to_a3_lite(self) -> None:
        """Test routing ticket to A3-lite."""
        service = SupportInboxService()
        actor_id = uuid4()

        ticket = service.create_ticket("Test", "Desc", uuid4(), auto_route=False)

        decision = service.route_ticket(ticket.id, RoutingTarget.A3_LITE, actor_id)
        assert decision is not None
        assert decision.target == RoutingTarget.A3_LITE
        assert decision.target_id is not None

    def test_route_to_task(self) -> None:
        """Test routing ticket to task."""
        service = SupportInboxService()
        actor_id = uuid4()

        ticket = service.create_ticket("Test", "Desc", uuid4(), auto_route=False)

        decision = service.route_ticket(ticket.id, RoutingTarget.TASK, actor_id)
        assert decision is not None
        assert decision.target == RoutingTarget.TASK

    def test_auto_route_critical_bug(self) -> None:
        """Test auto-routing critical bug to A3."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            "Critical Bug",
            "System down",
            uuid4(),
            category=TicketCategory.BUG,
            priority=TicketPriority.CRITICAL,
        )

        assert ticket.routing_decision is not None
        assert ticket.routing_decision.target == RoutingTarget.A3_LITE

    def test_auto_route_feature_request(self) -> None:
        """Test auto-routing feature request to task."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            "New Feature",
            "Please add",
            uuid4(),
            category=TicketCategory.FEATURE_REQUEST,
        )

        assert ticket.routing_decision is not None
        # Feature requests match the feature request rule


class TestRoutingRules:
    """Tests for routing rule management."""

    def test_create_routing_rule(self) -> None:
        """Test creating a routing rule."""
        service = SupportInboxService()

        rule = service.create_routing_rule(
            name="Performance Issues",
            description="Route performance issues to A3",
            conditions={"category": "performance"},
            target=RoutingTarget.A3_LITE,
            priority=95,
        )

        assert rule is not None
        assert rule.name == "Performance Issues"

    def test_get_routing_rules(self) -> None:
        """Test getting routing rules."""
        service = SupportInboxService()

        rules = service.get_routing_rules()
        assert len(rules) >= 5

    def test_get_active_routing_rules(self) -> None:
        """Test getting active routing rules."""
        service = SupportInboxService()

        rules = service.get_routing_rules(active_only=True)
        assert all(r.is_active for r in rules)

    def test_update_routing_rule(self) -> None:
        """Test updating a routing rule."""
        service = SupportInboxService()

        rule = service.create_routing_rule(
            name="Test Rule",
            description="Test",
            conditions={},
            target=RoutingTarget.MANUAL_REVIEW,
        )

        updated = service.update_routing_rule(rule.id, name="Updated Rule")
        assert updated is not None
        assert updated.name == "Updated Rule"

    def test_deactivate_routing_rule(self) -> None:
        """Test deactivating a routing rule."""
        service = SupportInboxService()

        rule = service.create_routing_rule(
            name="Test",
            description="Test",
            conditions={},
            target=RoutingTarget.MANUAL_REVIEW,
        )

        updated = service.update_routing_rule(rule.id, is_active=False)
        assert updated is not None
        assert updated.is_active is False

    def test_delete_routing_rule(self) -> None:
        """Test deleting a routing rule."""
        service = SupportInboxService()

        rule = service.create_routing_rule(
            name="To Delete",
            description="Test",
            conditions={},
            target=RoutingTarget.MANUAL_REVIEW,
        )

        result = service.delete_routing_rule(rule.id)
        assert result is True

        rules = service.get_routing_rules()
        assert all(r.id != rule.id for r in rules)


class TestFeedback:
    """Tests for feedback management."""

    def test_submit_feedback(self) -> None:
        """Test submitting feedback."""
        service = SupportInboxService()

        feedback = service.submit_feedback(
            content="Great feature!",
            feedback_type=FeedbackType.PRAISE,
            submitted_by=uuid4(),
            submitter_name="Happy User",
        )

        assert feedback is not None
        assert feedback.content == "Great feature!"

    def test_submit_feedback_with_rating(self) -> None:
        """Test submitting feedback with rating."""
        service = SupportInboxService()

        feedback = service.submit_feedback(
            content="Could be better",
            feedback_type=FeedbackType.USABILITY,
            submitted_by=uuid4(),
            rating=3,
        )

        assert feedback.rating == 3

    def test_get_feedback_by_type(self) -> None:
        """Test filtering feedback by type."""
        service = SupportInboxService()

        service.submit_feedback("Bug!", FeedbackType.BUG_REPORT, uuid4())
        service.submit_feedback("Nice!", FeedbackType.PRAISE, uuid4())

        bug_reports = service.get_feedback(feedback_type=FeedbackType.BUG_REPORT)
        assert all(f.feedback_type == FeedbackType.BUG_REPORT for f in bug_reports)

    def test_get_unreviewed_feedback(self) -> None:
        """Test getting unreviewed feedback."""
        service = SupportInboxService()

        service.submit_feedback("Test", FeedbackType.SUGGESTION, uuid4())

        unreviewed = service.get_feedback(reviewed=False)
        assert all(not f.reviewed for f in unreviewed)

    def test_review_feedback(self) -> None:
        """Test marking feedback as reviewed."""
        service = SupportInboxService()
        reviewer_id = uuid4()

        feedback = service.submit_feedback("Test", FeedbackType.SUGGESTION, uuid4())

        reviewed = service.review_feedback(feedback.id, reviewer_id)
        assert reviewed is not None
        assert reviewed.reviewed is True
        assert reviewed.reviewed_by == reviewer_id

    def test_convert_feedback_to_ticket(self) -> None:
        """Test converting feedback to ticket."""
        service = SupportInboxService()

        feedback = service.submit_feedback(
            content="Please add this feature",
            feedback_type=FeedbackType.SUGGESTION,
            submitted_by=uuid4(),
            submitter_name="User",
        )

        ticket = service.convert_feedback_to_ticket(feedback.id)
        assert ticket is not None
        assert feedback.converted_to_ticket is True
        assert feedback.ticket_id == ticket.id

    def test_convert_feedback_already_converted(self) -> None:
        """Test converting already converted feedback."""
        service = SupportInboxService()

        feedback = service.submit_feedback("Test", FeedbackType.SUGGESTION, uuid4())
        ticket1 = service.convert_feedback_to_ticket(feedback.id)
        ticket2 = service.convert_feedback_to_ticket(feedback.id)

        assert ticket1 is not None
        assert ticket2 is not None
        assert ticket1.id == ticket2.id


class TestA3Lite:
    """Tests for A3-lite records."""

    def test_get_a3_lite_for_ticket(self) -> None:
        """Test getting A3-lite for a ticket."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            "Critical Bug",
            "System down",
            uuid4(),
            category=TicketCategory.BUG,
            priority=TicketPriority.CRITICAL,
        )

        a3 = service.get_a3_lite_for_ticket(ticket.id)
        assert a3 is not None
        assert a3.source_ticket_id == ticket.id

    def test_update_a3_lite(self) -> None:
        """Test updating A3-lite record."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            "Bug",
            "Issue",
            uuid4(),
            category=TicketCategory.BUG,
            priority=TicketPriority.CRITICAL,
        )

        a3 = service.get_a3_lite_for_ticket(ticket.id)
        assert a3 is not None

        updated = service.update_a3_lite(
            a3.id,
            root_cause="Configuration error",
            countermeasures="Update config file",
        )

        assert updated is not None
        assert updated.root_cause == "Configuration error"

    def test_complete_a3_lite(self) -> None:
        """Test completing A3-lite record."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            "Bug",
            "Issue",
            uuid4(),
            category=TicketCategory.BUG,
            priority=TicketPriority.CRITICAL,
        )

        a3 = service.get_a3_lite_for_ticket(ticket.id)
        assert a3 is not None

        completed = service.update_a3_lite(a3.id, status="completed")
        assert completed is not None
        assert completed.completed_at is not None


class TestStatistics:
    """Tests for statistics and reporting."""

    def test_get_inbox_stats(self) -> None:
        """Test getting inbox statistics."""
        service = SupportInboxService()

        service.create_ticket("T1", "D1", uuid4())
        service.create_ticket("T2", "D2", uuid4())

        stats = service.get_inbox_stats()
        assert stats.total_open >= 2

    def test_stats_count_by_category(self) -> None:
        """Test stats count by category."""
        service = SupportInboxService()

        service.create_ticket("Bug", "D", uuid4(), category=TicketCategory.BUG)
        service.create_ticket("Bug2", "D", uuid4(), category=TicketCategory.BUG)

        stats = service.get_inbox_stats()
        assert "bug" in stats.by_category
        assert stats.by_category["bug"] >= 2

    def test_get_overdue_tickets(self) -> None:
        """Test getting overdue tickets."""
        service = SupportInboxService()

        # Create a ticket with an already-passed SLA
        ticket = service.create_ticket("Overdue", "D", uuid4(), priority=TicketPriority.CRITICAL)
        ticket.sla_due_at = datetime.now(timezone.utc) - timedelta(hours=1)

        overdue = service.get_overdue_tickets()
        assert any(t.id == ticket.id for t in overdue)

    def test_get_unassigned_tickets(self) -> None:
        """Test getting unassigned tickets."""
        service = SupportInboxService()

        ticket = service.create_ticket("Unassigned", "D", uuid4())

        unassigned = service.get_unassigned_tickets()
        assert any(t.id == ticket.id for t in unassigned)

    def test_get_ticket_summary(self) -> None:
        """Test getting ticket summary."""
        service = SupportInboxService()

        ticket = service.create_ticket(
            "Test Ticket",
            "Description",
            uuid4(),
            submitter_name="User",
        )

        summary = service.get_ticket_summary(ticket.id)
        assert summary is not None
        assert summary["subject"] == "Test Ticket"
        assert "status" in summary
        assert "comment_count" in summary


class TestSLAManagement:
    """Tests for SLA management."""

    def test_update_sla_hours(self) -> None:
        """Test updating SLA hours."""
        service = SupportInboxService()

        service.update_sla_hours(TicketPriority.CRITICAL, 1)

        sla = service.get_sla_config()
        assert sla["critical"] == 1

    def test_update_sla_invalid_hours(self) -> None:
        """Test updating with invalid hours."""
        service = SupportInboxService()

        service.update_sla_hours(TicketPriority.CRITICAL, 0)

        # Should not update
        sla = service.get_sla_config()
        assert sla["critical"] == 2


class TestSearch:
    """Tests for ticket search."""

    def test_search_by_subject(self) -> None:
        """Test searching by subject."""
        service = SupportInboxService()

        service.create_ticket("Login Problem", "Cannot login", uuid4())
        service.create_ticket("Password Reset", "Need reset", uuid4())

        results = service.search_tickets("login")
        assert len(results) >= 1
        assert any("Login" in t.subject for t in results)

    def test_search_by_description(self) -> None:
        """Test searching by description."""
        service = SupportInboxService()

        service.create_ticket("Issue", "Authentication failed", uuid4())

        results = service.search_tickets("authentication")
        assert len(results) >= 1

    def test_search_by_tag(self) -> None:
        """Test searching by tag."""
        service = SupportInboxService()

        service.create_ticket("Tagged", "Desc", uuid4(), tags=["production"])

        results = service.search_tickets("production")
        assert len(results) >= 1

    def test_search_limit(self) -> None:
        """Test search result limit."""
        service = SupportInboxService()

        for i in range(10):
            service.create_ticket(f"Test {i}", "Desc", uuid4())

        results = service.search_tickets("Test", limit=5)
        assert len(results) <= 5


class TestEdgeCases:
    """Tests for edge cases."""

    def test_add_comment_invalid_ticket(self) -> None:
        """Test adding comment to invalid ticket."""
        service = SupportInboxService()

        result = service.add_comment(uuid4(), uuid4(), "Author", "Content")
        assert result is None

    def test_change_status_invalid_ticket(self) -> None:
        """Test changing status of invalid ticket."""
        service = SupportInboxService()

        result = service.change_status(uuid4(), TicketStatus.RESOLVED)
        assert result is None

    def test_route_invalid_ticket(self) -> None:
        """Test routing invalid ticket."""
        service = SupportInboxService()

        result = service.route_ticket(uuid4(), RoutingTarget.TASK, uuid4())
        assert result is None

    def test_convert_invalid_feedback(self) -> None:
        """Test converting invalid feedback."""
        service = SupportInboxService()

        result = service.convert_feedback_to_ticket(uuid4())
        assert result is None

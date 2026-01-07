"""Tests for Runbooks Service.

Tests runbook management, templates, steps, versions,
and execution tracking.
"""

import pytest
from datetime import datetime, timezone

from sensei.services.runbooks import (
    RunbooksService,
    Runbook,
    RunbookCategory,
    RunbookSeverity,
    RunbookStatus,
    RunbookStep,
    RunbookTemplate,
    RunbookVersion,
    RunbookExecution,
    StepType,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service() -> RunbooksService:
    """Create a fresh RunbooksService instance."""
    return RunbooksService()


@pytest.fixture
def sample_runbook(service: RunbooksService) -> Runbook:
    """Create a sample runbook."""
    return service.create_runbook(
        title="Test Runbook",
        description="A test runbook for testing",
        category=RunbookCategory.INCIDENT_RESPONSE,
        created_by="user-123",
        owner_team="backend",
        applicable_severities=[RunbookSeverity.SEV2, RunbookSeverity.SEV3],
        tags=["test", "incident"],
    )


@pytest.fixture
def runbook_with_steps(service: RunbooksService) -> Runbook:
    """Create a runbook with steps."""
    runbook = service.create_runbook(
        title="Runbook with Steps",
        description="For testing step operations",
        category=RunbookCategory.TROUBLESHOOTING,
        created_by="user-123",
    )

    steps = [
        RunbookStep(
            order=1,
            title="Step 1",
            description="First step",
            step_type=StepType.MANUAL,
            estimated_duration_minutes=5,
        ),
        RunbookStep(
            order=2,
            title="Step 2",
            description="Second step",
            step_type=StepType.AUTOMATED,
            command="echo 'hello'",
            estimated_duration_minutes=2,
        ),
        RunbookStep(
            order=3,
            title="Step 3",
            description="Third step",
            step_type=StepType.VERIFICATION,
            estimated_duration_minutes=3,
        ),
    ]

    for step in steps:
        service.add_step(runbook.id, step)

    return service.get_runbook(runbook.id)


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Test enum values."""

    def test_runbook_categories(self) -> None:
        """Verify all categories exist."""
        expected = {
            "incident_response", "troubleshooting", "deployment",
            "maintenance", "recovery", "security", "monitoring",
            "scaling", "database", "network", "general",
        }
        actual = {c.value for c in RunbookCategory}
        assert actual == expected

    def test_runbook_severities(self) -> None:
        """Verify all severities exist."""
        expected = {"sev1", "sev2", "sev3", "sev4", "sev5", "all"}
        actual = {s.value for s in RunbookSeverity}
        assert actual == expected

    def test_step_types(self) -> None:
        """Verify all step types exist."""
        expected = {
            "manual", "automated", "decision", "notification",
            "verification", "escalation",
        }
        actual = {t.value for t in StepType}
        assert actual == expected

    def test_runbook_statuses(self) -> None:
        """Verify all statuses exist."""
        expected = {"draft", "review", "approved", "deprecated", "archived"}
        actual = {s.value for s in RunbookStatus}
        assert actual == expected


# ============================================================
# Template Tests
# ============================================================


class TestTemplates:
    """Test template management."""

    def test_default_templates_loaded(self, service: RunbooksService) -> None:
        """Test that default templates are loaded."""
        templates = service.get_all_templates()
        assert len(templates) >= 4  # We defined 4 default templates

    def test_get_template(self, service: RunbooksService) -> None:
        """Test getting a template."""
        templates = service.get_all_templates()
        template = service.get_template(templates[0].id)
        assert template is not None
        assert template.id == templates[0].id

    def test_get_template_nonexistent(self, service: RunbooksService) -> None:
        """Test getting non-existent template."""
        template = service.get_template("nonexistent")
        assert template is None

    def test_get_templates_by_category(self, service: RunbooksService) -> None:
        """Test getting templates by category."""
        incident_templates = service.get_templates_by_category(
            RunbookCategory.INCIDENT_RESPONSE
        )
        assert len(incident_templates) >= 1

    def test_create_template(self, service: RunbooksService) -> None:
        """Test creating a custom template."""
        template = service.create_template(
            name="Custom Template",
            description="A custom template",
            category=RunbookCategory.MAINTENANCE,
        )
        assert template.name == "Custom Template"
        assert template.category == RunbookCategory.MAINTENANCE

    def test_create_template_with_steps(self, service: RunbooksService) -> None:
        """Test creating template with default steps."""
        steps = [
            RunbookStep(order=1, title="First", step_type=StepType.MANUAL),
            RunbookStep(order=2, title="Second", step_type=StepType.VERIFICATION),
        ]
        template = service.create_template(
            name="With Steps",
            default_steps=steps,
        )
        assert len(template.default_steps) == 2

    def test_create_runbook_from_template(self, service: RunbooksService) -> None:
        """Test creating runbook from template."""
        templates = service.get_all_templates()
        template = templates[0]

        runbook = service.create_runbook_from_template(
            template_id=template.id,
            title="My Incident Runbook",
            created_by="user-123",
            owner_team="backend",
        )

        assert runbook is not None
        assert runbook.title == "My Incident Runbook"
        assert runbook.category == template.category
        assert len(runbook.steps) == len(template.default_steps)
        assert runbook.status == RunbookStatus.DRAFT

    def test_create_runbook_from_nonexistent_template(
        self, service: RunbooksService
    ) -> None:
        """Test creating runbook from non-existent template."""
        runbook = service.create_runbook_from_template(
            template_id="nonexistent",
            title="Test",
        )
        assert runbook is None


# ============================================================
# Runbook Management Tests
# ============================================================


class TestRunbookManagement:
    """Test runbook management."""

    def test_create_runbook(self, service: RunbooksService) -> None:
        """Test creating a runbook."""
        runbook = service.create_runbook(
            title="New Runbook",
            description="A new runbook",
            category=RunbookCategory.DEPLOYMENT,
            created_by="user-123",
            owner_team="devops",
        )

        assert runbook.title == "New Runbook"
        assert runbook.status == RunbookStatus.DRAFT
        assert runbook.owner_team == "devops"

    def test_default_runbooks_loaded(self, service: RunbooksService) -> None:
        """Test that default runbooks are loaded."""
        runbooks = service.get_all_runbooks()
        assert len(runbooks) >= 2  # We defined 2 default runbooks

    def test_get_runbook(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test getting a runbook."""
        retrieved = service.get_runbook(sample_runbook.id)
        assert retrieved is not None
        assert retrieved.id == sample_runbook.id

    def test_get_runbook_nonexistent(self, service: RunbooksService) -> None:
        """Test getting non-existent runbook."""
        runbook = service.get_runbook("nonexistent")
        assert runbook is None

    def test_get_all_runbooks(self, service: RunbooksService) -> None:
        """Test getting all runbooks."""
        service.create_runbook(title="Additional 1")
        service.create_runbook(title="Additional 2")

        runbooks = service.get_all_runbooks()
        assert len(runbooks) >= 4  # 2 default + 2 new

    def test_get_runbooks_by_category(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test getting runbooks by category."""
        incident_runbooks = service.get_runbooks_by_category(
            RunbookCategory.INCIDENT_RESPONSE
        )
        assert len(incident_runbooks) >= 1

    def test_get_runbooks_by_status(self, service: RunbooksService) -> None:
        """Test getting runbooks by status."""
        approved = service.get_runbooks_by_status(RunbookStatus.APPROVED)
        assert len(approved) >= 2  # Default runbooks are approved

    def test_get_runbooks_by_severity(self, service: RunbooksService) -> None:
        """Test getting runbooks by severity."""
        sev2_runbooks = service.get_runbooks_by_severity(RunbookSeverity.SEV2)
        assert len(sev2_runbooks) >= 1

    def test_get_runbooks_by_severity_all(self, service: RunbooksService) -> None:
        """Test runbooks with ALL severity match any query."""
        runbook = service.create_runbook(
            title="Universal Runbook",
            applicable_severities=[RunbookSeverity.ALL],
        )

        for severity in [RunbookSeverity.SEV1, RunbookSeverity.SEV3, RunbookSeverity.SEV5]:
            matching = service.get_runbooks_by_severity(severity)
            assert runbook.id in [r.id for r in matching]

    def test_get_runbooks_by_service(self, service: RunbooksService) -> None:
        """Test getting runbooks by service."""
        api_runbooks = service.get_runbooks_by_service("api")
        assert len(api_runbooks) >= 1

    def test_get_runbooks_by_team(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test getting runbooks by team."""
        backend_runbooks = service.get_runbooks_by_team("backend")
        assert len(backend_runbooks) >= 1

    def test_search_runbooks_by_title(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test searching runbooks by title."""
        results = service.search_runbooks("Test Runbook")
        assert len(results) >= 1
        assert sample_runbook.id in [r.id for r in results]

    def test_search_runbooks_by_description(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test searching runbooks by description."""
        results = service.search_runbooks("testing")
        assert len(results) >= 1

    def test_search_runbooks_by_tag(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test searching runbooks by tag."""
        results = service.search_runbooks("incident")
        assert len(results) >= 1

    def test_search_runbooks_case_insensitive(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test that search is case insensitive."""
        results = service.search_runbooks("TEST RUNBOOK")
        assert len(results) >= 1

    def test_update_runbook(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test updating a runbook."""
        updated = service.update_runbook(
            sample_runbook.id,
            title="Updated Title",
            description="Updated description",
            updated_by="user-456",
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.description == "Updated description"
        assert updated.updated_by == "user-456"

    def test_update_runbook_nonexistent(self, service: RunbooksService) -> None:
        """Test updating non-existent runbook."""
        updated = service.update_runbook("nonexistent", title="Test")
        assert updated is None

    def test_update_runbook_tags(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test updating runbook tags."""
        updated = service.update_runbook(
            sample_runbook.id,
            tags=["new-tag", "another-tag"],
        )

        assert updated is not None
        assert "new-tag" in updated.tags
        assert len(updated.tags) == 2

    def test_update_runbook_status(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test updating runbook status."""
        updated = service.update_runbook_status(
            sample_runbook.id,
            RunbookStatus.REVIEW,
            updated_by="reviewer",
        )

        assert updated is not None
        assert updated.status == RunbookStatus.REVIEW

    def test_delete_runbook(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test deleting a runbook."""
        result = service.delete_runbook(sample_runbook.id)
        assert result is True
        assert service.get_runbook(sample_runbook.id) is None

    def test_delete_runbook_nonexistent(self, service: RunbooksService) -> None:
        """Test deleting non-existent runbook."""
        result = service.delete_runbook("nonexistent")
        assert result is False


# ============================================================
# Step Management Tests
# ============================================================


class TestStepManagement:
    """Test step management."""

    def test_add_step(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test adding a step."""
        step = RunbookStep(
            title="First Step",
            description="Do something",
            step_type=StepType.MANUAL,
        )

        updated = service.add_step(sample_runbook.id, step)
        assert updated is not None
        assert len(updated.steps) == 1
        assert updated.steps[0].title == "First Step"

    def test_add_step_auto_order(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test that steps get auto-ordered."""
        step1 = RunbookStep(title="Step 1")
        step2 = RunbookStep(title="Step 2")

        service.add_step(sample_runbook.id, step1)
        service.add_step(sample_runbook.id, step2)

        updated = service.get_runbook(sample_runbook.id)
        assert updated.steps[0].order == 1
        assert updated.steps[1].order == 2

    def test_add_step_updates_duration(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test that adding step updates total duration."""
        step = RunbookStep(
            title="Long Step",
            estimated_duration_minutes=30,
        )

        updated = service.add_step(sample_runbook.id, step)
        assert updated.estimated_total_duration_minutes == 30

    def test_update_step(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test updating a step."""
        step_id = runbook_with_steps.steps[0].id
        updated = service.update_step(
            runbook_with_steps.id,
            step_id,
            title="Updated Step Title",
            description="Updated description",
            estimated_duration_minutes=15,
        )

        assert updated is not None
        assert updated.title == "Updated Step Title"
        assert updated.estimated_duration_minutes == 15

    def test_update_step_nonexistent_runbook(self, service: RunbooksService) -> None:
        """Test updating step in non-existent runbook."""
        result = service.update_step(
            "nonexistent",
            "step-id",
            title="Test",
        )
        assert result is None

    def test_update_step_nonexistent_step(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test updating non-existent step."""
        result = service.update_step(
            runbook_with_steps.id,
            "nonexistent",
            title="Test",
        )
        assert result is None

    def test_remove_step(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test removing a step."""
        step_id = runbook_with_steps.steps[1].id
        updated = service.remove_step(runbook_with_steps.id, step_id)

        assert updated is not None
        assert len(updated.steps) == 2
        assert step_id not in [s.id for s in updated.steps]

    def test_remove_step_reorders(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test that removing step reorders remaining steps."""
        # Remove middle step
        step_id = runbook_with_steps.steps[1].id
        updated = service.remove_step(runbook_with_steps.id, step_id)

        assert updated.steps[0].order == 1
        assert updated.steps[1].order == 2

    def test_reorder_steps(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test reordering steps."""
        step_ids = [s.id for s in runbook_with_steps.steps]
        reversed_ids = list(reversed(step_ids))

        updated = service.reorder_steps(runbook_with_steps.id, reversed_ids)
        assert updated is not None
        assert [s.id for s in updated.steps] == reversed_ids


# ============================================================
# Version Management Tests
# ============================================================


class TestVersionManagement:
    """Test version management."""

    def test_create_version(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test creating a version."""
        updated = service.create_version(
            runbook_with_steps.id,
            version="2.0.0",
            change_summary="Major update with new steps",
            created_by="user-123",
        )

        assert updated is not None
        assert updated.version == "2.0.0"
        assert len(updated.version_history) == 1

    def test_version_history_snapshot(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test that version includes steps snapshot."""
        service.create_version(
            runbook_with_steps.id,
            version="1.1.0",
            change_summary="Minor update",
        )

        history = service.get_version_history(runbook_with_steps.id)
        assert len(history) == 1
        assert len(history[0].steps_snapshot) == 3  # 3 steps in runbook

    def test_multiple_versions(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test creating multiple versions."""
        service.create_version(runbook_with_steps.id, "1.1.0", "First update")
        service.create_version(runbook_with_steps.id, "1.2.0", "Second update")
        service.create_version(runbook_with_steps.id, "2.0.0", "Major update")

        history = service.get_version_history(runbook_with_steps.id)
        assert len(history) == 3
        assert history[-1].version == "2.0.0"

    def test_get_version_history_nonexistent(self, service: RunbooksService) -> None:
        """Test getting version history for non-existent runbook."""
        history = service.get_version_history("nonexistent")
        assert history == []


# ============================================================
# Execution Tracking Tests
# ============================================================


class TestExecutionTracking:
    """Test execution tracking."""

    def test_start_execution(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test starting an execution."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )

        assert execution is not None
        assert execution.runbook_id == runbook_with_steps.id
        assert execution.executed_by == "user-123"
        assert execution.status == "in_progress"
        assert execution.current_step_id == runbook_with_steps.steps[0].id

    def test_start_execution_with_incident(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test starting execution with incident ID."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
            incident_id="INC-001",
        )

        assert execution.incident_id == "INC-001"

    def test_start_execution_empty_runbook(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test starting execution on runbook with no steps."""
        execution = service.start_execution(
            sample_runbook.id,
            executed_by="user-123",
        )
        assert execution is None

    def test_start_execution_nonexistent(self, service: RunbooksService) -> None:
        """Test starting execution on non-existent runbook."""
        execution = service.start_execution(
            "nonexistent",
            executed_by="user-123",
        )
        assert execution is None

    def test_get_execution(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test getting an execution."""
        created = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )
        retrieved = service.get_execution(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_executions_for_runbook(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test getting executions for a runbook."""
        service.start_execution(runbook_with_steps.id, "user-1")
        service.start_execution(runbook_with_steps.id, "user-2")

        executions = service.get_executions_for_runbook(runbook_with_steps.id)
        assert len(executions) == 2

    def test_get_executions_for_incident(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test getting executions for an incident."""
        service.start_execution(
            runbook_with_steps.id,
            "user-1",
            incident_id="INC-001",
        )
        service.start_execution(
            runbook_with_steps.id,
            "user-2",
            incident_id="INC-001",
        )
        service.start_execution(
            runbook_with_steps.id,
            "user-3",
            incident_id="INC-002",
        )

        executions = service.get_executions_for_incident("INC-001")
        assert len(executions) == 2

    def test_complete_step(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test completing a step."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )
        step_id = runbook_with_steps.steps[0].id

        updated = service.complete_step(
            execution.id,
            step_id,
            notes="Completed successfully",
        )

        assert updated is not None
        assert step_id in updated.steps_completed
        assert len(updated.notes) == 1

    def test_complete_step_advances_current(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test that completing step advances current step."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )
        first_step = runbook_with_steps.steps[0].id
        second_step = runbook_with_steps.steps[1].id

        updated = service.complete_step(execution.id, first_step)
        assert updated.current_step_id == second_step

    def test_complete_last_step(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test completing the last step."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )

        # Complete all steps
        for step in runbook_with_steps.steps:
            service.complete_step(execution.id, step.id)

        updated = service.get_execution(execution.id)
        assert updated.current_step_id == ""

    def test_complete_execution(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test completing an execution."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )

        updated = service.complete_execution(
            execution.id,
            outcome="Successfully resolved issue",
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.completed_at is not None
        assert "Successfully" in updated.outcome

    def test_abort_execution(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test aborting an execution."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-123",
        )

        updated = service.abort_execution(
            execution.id,
            reason="No longer needed",
        )

        assert updated is not None
        assert updated.status == "aborted"
        assert "No longer needed" in updated.outcome


# ============================================================
# Summary Tests
# ============================================================


class TestSummary:
    """Test summary functionality."""

    def test_get_summary(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test getting summary."""
        summary = service.get_summary()

        assert "total_runbooks" in summary
        assert "total_templates" in summary
        assert "total_executions" in summary
        assert "by_category" in summary
        assert "by_status" in summary
        assert "approved_runbooks" in summary

    def test_summary_counts(self, service: RunbooksService) -> None:
        """Test summary counts are accurate."""
        # Create additional runbooks
        service.create_runbook(title="Test 1", category=RunbookCategory.DEPLOYMENT)
        service.create_runbook(title="Test 2", category=RunbookCategory.DEPLOYMENT)
        service.create_runbook(title="Test 3", category=RunbookCategory.SECURITY)

        summary = service.get_summary()

        # Should have at least 2 default + 3 new = 5
        assert summary["total_runbooks"] >= 5
        assert summary["by_category"]["deployment"] >= 2
        assert summary["by_category"]["security"] >= 1

    def test_summary_with_executions(
        self, service: RunbooksService, runbook_with_steps: Runbook
    ) -> None:
        """Test summary includes execution counts."""
        execution = service.start_execution(
            runbook_with_steps.id,
            executed_by="user-1",
        )
        service.complete_execution(execution.id, "Done")

        service.start_execution(runbook_with_steps.id, "user-2")

        summary = service.get_summary()
        assert summary["total_executions"] == 2
        assert summary["completed_executions"] == 1


# ============================================================
# Edge Cases and Integration Tests
# ============================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_runbook_with_all_step_types(self, service: RunbooksService) -> None:
        """Test runbook with all step types."""
        runbook = service.create_runbook(title="All Steps")

        for step_type in StepType:
            step = RunbookStep(
                title=f"{step_type.value} step",
                step_type=step_type,
            )
            service.add_step(runbook.id, step)

        updated = service.get_runbook(runbook.id)
        assert len(updated.steps) == len(StepType)

    def test_runbook_lifecycle(self, service: RunbooksService) -> None:
        """Test complete runbook lifecycle."""
        # Create
        runbook = service.create_runbook(
            title="Lifecycle Test",
            category=RunbookCategory.TROUBLESHOOTING,
            created_by="author",
        )
        assert runbook.status == RunbookStatus.DRAFT

        # Add steps
        service.add_step(runbook.id, RunbookStep(title="Step 1"))
        service.add_step(runbook.id, RunbookStep(title="Step 2"))

        # Review
        service.update_runbook_status(runbook.id, RunbookStatus.REVIEW)
        updated = service.get_runbook(runbook.id)
        assert updated.status == RunbookStatus.REVIEW

        # Approve
        service.update_runbook_status(runbook.id, RunbookStatus.APPROVED)
        updated = service.get_runbook(runbook.id)
        assert updated.status == RunbookStatus.APPROVED

        # Version
        service.create_version(runbook.id, "1.0.0", "Initial release")

        # Execute
        execution = service.start_execution(runbook.id, "user-123")
        for step in service.get_runbook(runbook.id).steps:
            service.complete_step(execution.id, step.id)
        service.complete_execution(execution.id, "Resolved")

        # Verify
        final_execution = service.get_execution(execution.id)
        assert final_execution.status == "completed"

        # Deprecate
        service.update_runbook_status(runbook.id, RunbookStatus.DEPRECATED)
        final = service.get_runbook(runbook.id)
        assert final.status == RunbookStatus.DEPRECATED

    def test_step_with_approval_required(
        self, service: RunbooksService, sample_runbook: Runbook
    ) -> None:
        """Test step with approval requirement."""
        step = RunbookStep(
            title="Approval Required Step",
            step_type=StepType.MANUAL,
            requires_approval=True,
            approver_role="Manager",
        )
        service.add_step(sample_runbook.id, step)

        updated = service.get_runbook(sample_runbook.id)
        assert updated.steps[0].requires_approval is True
        assert updated.steps[0].approver_role == "Manager"


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, service: RunbooksService) -> None:
        """Test complete workflow from template to execution."""
        # Get a template
        templates = service.get_templates_by_category(RunbookCategory.INCIDENT_RESPONSE)
        template = templates[0]

        # Create runbook from template
        runbook = service.create_runbook_from_template(
            template.id,
            title="Production Incident Response",
            created_by="oncall-team",
            owner_team="sre",
        )

        # Customize
        service.update_runbook(
            runbook.id,
            related_services=["api", "database", "cache"],
            applicable_severities=[RunbookSeverity.SEV1, RunbookSeverity.SEV2],
            tags=["production", "critical"],
        )

        # Approve
        service.update_runbook_status(
            runbook.id,
            RunbookStatus.APPROVED,
            updated_by="sre-lead",
        )

        # Version it
        service.create_version(
            runbook.id,
            "1.0.0",
            "Production ready",
            created_by="sre-lead",
        )

        # Verify it's searchable
        results = service.search_runbooks("production")
        assert runbook.id in [r.id for r in results]

        # Execute during incident
        execution = service.start_execution(
            runbook.id,
            executed_by="oncall-engineer",
            incident_id="INC-12345",
        )

        # Complete all steps
        for step in runbook.steps:
            service.complete_step(
                execution.id,
                step.id,
                notes=f"Completed {step.title}",
            )

        # Complete execution
        service.complete_execution(
            execution.id,
            outcome="Incident resolved successfully",
        )

        # Verify metrics
        summary = service.get_summary()
        assert summary["completed_executions"] >= 1

        # Check execution history
        executions = service.get_executions_for_incident("INC-12345")
        assert len(executions) == 1
        assert executions[0].status == "completed"

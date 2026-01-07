"""Tests for Integration Tests Service."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sensei.services.integration_tests import (
    IntegrationTestService,
    IntegrationTest,
    TestStep,
    TestSuite,
    TestExecution,
    TestContext,
    TestResult,
    TestCategory,
    TestPriority,
)


class TestEnums:
    """Tests for enum values."""

    def test_test_result_values(self) -> None:
        """Test TestResult enum values."""
        assert TestResult.PASSED.value == "passed"
        assert TestResult.FAILED.value == "failed"
        assert TestResult.SKIPPED.value == "skipped"
        assert TestResult.ERROR.value == "error"

    def test_test_category_values(self) -> None:
        """Test TestCategory enum values."""
        assert TestCategory.RFQ_WORKFLOW.value == "rfq_workflow"
        assert TestCategory.QUOTE_WORKFLOW.value == "quote_workflow"
        assert TestCategory.AUDIT_VERIFICATION.value == "audit_verification"

    def test_test_priority_values(self) -> None:
        """Test TestPriority enum values."""
        assert TestPriority.CRITICAL.value == "critical"
        assert TestPriority.HIGH.value == "high"
        assert TestPriority.MEDIUM.value == "medium"
        assert TestPriority.LOW.value == "low"


class TestDataclasses:
    """Tests for dataclass structures."""

    def test_test_step_creation(self) -> None:
        """Test TestStep creation."""
        step = TestStep(
            id=uuid4(),
            sequence=1,
            name="Test Step",
            description="Step description",
            action=None,
            expected_outcome="Success",
        )

        assert step.sequence == 1
        assert step.name == "Test Step"
        assert step.passed is None

    def test_test_context_creation(self) -> None:
        """Test TestContext creation."""
        ctx = TestContext()

        assert ctx.data == {}
        assert ctx.user_id is None
        assert ctx.created_objects == {}
        assert ctx.audit_entries == []

    def test_test_context_with_data(self) -> None:
        """Test TestContext with data."""
        ctx = TestContext(
            data={"key": "value"},
            user_id=uuid4(),
        )

        assert ctx.data["key"] == "value"
        assert ctx.user_id is not None


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_service_creates(self) -> None:
        """Test service initializes correctly."""
        service = IntegrationTestService()
        assert service is not None

    def test_default_tests_created(self) -> None:
        """Test default tests are created on init."""
        service = IntegrationTestService()
        tests = service.get_tests()

        assert len(tests) > 0

    def test_default_tests_have_categories(self) -> None:
        """Test default tests have all categories."""
        service = IntegrationTestService()
        tests = service.get_tests()

        categories = {t.category for t in tests}
        assert TestCategory.RFQ_WORKFLOW in categories
        assert TestCategory.QUOTE_WORKFLOW in categories


class TestDefaultTests:
    """Tests for default integration tests."""

    def test_rfq_qualification_test_exists(self) -> None:
        """Test RFQ to Qualification test exists."""
        service = IntegrationTestService()
        tests = service.get_tests(category=TestCategory.RFQ_WORKFLOW)

        assert any("RFQ" in t.name for t in tests)

    def test_quote_approval_test_exists(self) -> None:
        """Test Quote approval test exists."""
        service = IntegrationTestService()
        tests = service.get_tests(category=TestCategory.QUOTE_WORKFLOW)

        assert any("Quote" in t.name for t in tests)

    def test_audit_verification_test_exists(self) -> None:
        """Test audit verification test exists."""
        service = IntegrationTestService()
        tests = service.get_tests(category=TestCategory.AUDIT_VERIFICATION)

        assert len(tests) > 0

    def test_e2e_test_exists(self) -> None:
        """Test end-to-end test exists."""
        service = IntegrationTestService()
        tests = service.get_tests(category=TestCategory.CROSS_MODULE)

        assert any("Complete Journey" in t.name for t in tests)

    def test_andon_a3_test_exists(self) -> None:
        """Test Andon to A3 test exists."""
        service = IntegrationTestService()
        tests = service.get_tests(category=TestCategory.PRODUCTION_WORKFLOW)

        assert any("Andon" in t.name for t in tests)

    def test_nc_capa_test_exists(self) -> None:
        """Test NC to CAPA test exists."""
        service = IntegrationTestService()
        tests = service.get_tests(category=TestCategory.QUALITY_WORKFLOW)

        assert any("CAPA" in t.name for t in tests)

    def test_default_tests_have_steps(self) -> None:
        """Test default tests have steps defined."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            assert len(test.steps) > 0

    def test_steps_have_expected_outcomes(self) -> None:
        """Test all steps have expected outcomes."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            for step in test.steps:
                assert step.expected_outcome != ""


class TestTestManagement:
    """Tests for test CRUD operations."""

    def test_create_test(self) -> None:
        """Test creating a new test."""
        service = IntegrationTestService()

        test = service.create_test(
            name="Custom Test",
            description="A custom integration test",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.MEDIUM,
            steps=[
                {"name": "Step 1", "expected_outcome": "Success"},
                {"name": "Step 2", "expected_outcome": "Complete"},
            ],
            tags=["custom", "test"],
        )

        assert test is not None
        assert test.name == "Custom Test"
        assert len(test.steps) == 2

    def test_get_test_by_id(self) -> None:
        """Test getting test by ID."""
        service = IntegrationTestService()

        test = service.create_test(
            name="Findable Test",
            description="Test to find",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.LOW,
            steps=[{"name": "Step", "expected_outcome": "Done"}],
        )

        found = service.get_test(test.id)
        assert found is not None
        assert found.name == "Findable Test"

    def test_get_nonexistent_test(self) -> None:
        """Test getting nonexistent test."""
        service = IntegrationTestService()

        result = service.get_test(uuid4())
        assert result is None

    def test_get_tests_by_category(self) -> None:
        """Test filtering tests by category."""
        service = IntegrationTestService()

        rfq_tests = service.get_tests(category=TestCategory.RFQ_WORKFLOW)

        for test in rfq_tests:
            assert test.category == TestCategory.RFQ_WORKFLOW

    def test_get_tests_by_priority(self) -> None:
        """Test filtering tests by priority."""
        service = IntegrationTestService()

        critical_tests = service.get_tests(priority=TestPriority.CRITICAL)

        for test in critical_tests:
            assert test.priority == TestPriority.CRITICAL

    def test_get_tests_by_tag(self) -> None:
        """Test filtering tests by tag."""
        service = IntegrationTestService()

        tagged_tests = service.get_tests(tag="workflow")

        for test in tagged_tests:
            assert "workflow" in test.tags

    def test_update_test(self) -> None:
        """Test updating a test."""
        service = IntegrationTestService()

        test = service.create_test(
            name="Original Name",
            description="Original description",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.LOW,
            steps=[{"name": "Step", "expected_outcome": "Done"}],
        )

        updated = service.update_test(
            test.id,
            name="Updated Name",
            description="Updated description",
        )

        assert updated is not None
        assert updated.name == "Updated Name"

    def test_deactivate_test(self) -> None:
        """Test deactivating a test."""
        service = IntegrationTestService()

        test = service.create_test(
            name="Active Test",
            description="Will be deactivated",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.LOW,
            steps=[{"name": "Step", "expected_outcome": "Done"}],
        )

        service.update_test(test.id, is_active=False)

        # Should not appear in active-only query
        active_tests = service.get_tests(active_only=True)
        assert test.id not in [t.id for t in active_tests]

    def test_delete_test(self) -> None:
        """Test deleting a test."""
        service = IntegrationTestService()

        test = service.create_test(
            name="To Delete",
            description="Will be deleted",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.LOW,
            steps=[{"name": "Step", "expected_outcome": "Done"}],
        )

        result = service.delete_test(test.id)
        assert result is True
        assert service.get_test(test.id) is None

    def test_delete_nonexistent_test(self) -> None:
        """Test deleting nonexistent test."""
        service = IntegrationTestService()

        result = service.delete_test(uuid4())
        assert result is False


class TestTestSuites:
    """Tests for test suite management."""

    def test_create_suite(self) -> None:
        """Test creating a test suite."""
        service = IntegrationTestService()
        tests = service.get_tests()[:3]

        suite = service.create_suite(
            name="My Suite",
            description="A test suite",
            test_ids=[t.id for t in tests],
        )

        assert suite is not None
        assert suite.name == "My Suite"
        assert len(suite.tests) == 3

    def test_get_suite_by_id(self) -> None:
        """Test getting suite by ID."""
        service = IntegrationTestService()
        tests = service.get_tests()[:2]

        suite = service.create_suite(
            name="Findable Suite",
            description="Suite to find",
            test_ids=[t.id for t in tests],
        )

        found = service.get_suite(suite.id)
        assert found is not None
        assert found.name == "Findable Suite"

    def test_get_nonexistent_suite(self) -> None:
        """Test getting nonexistent suite."""
        service = IntegrationTestService()

        result = service.get_suite(uuid4())
        assert result is None

    def test_get_all_suites(self) -> None:
        """Test getting all suites."""
        service = IntegrationTestService()
        tests = service.get_tests()

        service.create_suite("Suite 1", "First", [tests[0].id])
        service.create_suite("Suite 2", "Second", [tests[1].id])

        suites = service.get_all_suites()
        assert len(suites) >= 2

    def test_suite_with_invalid_test_ids(self) -> None:
        """Test creating suite with invalid test IDs."""
        service = IntegrationTestService()
        tests = service.get_tests()[:1]

        suite = service.create_suite(
            name="Partial Suite",
            description="Has some invalid IDs",
            test_ids=[tests[0].id, uuid4(), uuid4()],
        )

        # Only valid tests included
        assert len(suite.tests) == 1


class TestTestExecution:
    """Tests for test execution."""

    def test_execute_test(self) -> None:
        """Test executing a test."""
        service = IntegrationTestService()
        tests = service.get_tests()

        execution = service.execute_test(tests[0].id)

        assert execution is not None
        assert execution.test_id == tests[0].id
        assert execution.result in [TestResult.PASSED, TestResult.FAILED, TestResult.ERROR]

    def test_execute_with_context(self) -> None:
        """Test executing test with context."""
        service = IntegrationTestService()
        tests = service.get_tests()

        ctx = TestContext(data={"initial": "value"})
        execution = service.execute_test(tests[0].id, context=ctx)

        assert execution is not None

    def test_execute_nonexistent_test(self) -> None:
        """Test executing nonexistent test."""
        service = IntegrationTestService()

        with pytest.raises(ValueError):
            service.execute_test(uuid4())

    def test_execution_has_timestamps(self) -> None:
        """Test execution has timestamps."""
        service = IntegrationTestService()
        tests = service.get_tests()

        execution = service.execute_test(tests[0].id)

        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert execution.duration_ms is not None

    def test_execution_has_step_results(self) -> None:
        """Test execution has step results."""
        service = IntegrationTestService()
        tests = service.get_tests()

        execution = service.execute_test(tests[0].id)

        assert len(execution.step_results) > 0
        for result in execution.step_results:
            assert "name" in result
            assert "passed" in result

    def test_execute_suite(self) -> None:
        """Test executing a test suite."""
        service = IntegrationTestService()
        tests = service.get_tests()[:2]

        suite = service.create_suite(
            name="Execution Suite",
            description="For execution",
            test_ids=[t.id for t in tests],
        )

        executions = service.execute_suite(suite.id)

        assert len(executions) == 2

    def test_execute_nonexistent_suite(self) -> None:
        """Test executing nonexistent suite."""
        service = IntegrationTestService()

        with pytest.raises(ValueError):
            service.execute_suite(uuid4())

    def test_execute_by_category(self) -> None:
        """Test executing all tests in category."""
        service = IntegrationTestService()

        executions = service.execute_by_category(TestCategory.AUDIT_VERIFICATION)

        assert len(executions) > 0
        for execution in executions:
            test = service.get_test(execution.test_id)
            assert test is not None
            assert test.category == TestCategory.AUDIT_VERIFICATION


class TestExecutionHistory:
    """Tests for execution history."""

    def test_get_executions(self) -> None:
        """Test getting execution history."""
        service = IntegrationTestService()
        tests = service.get_tests()

        service.execute_test(tests[0].id)
        service.execute_test(tests[1].id)

        executions = service.get_executions()
        assert len(executions) >= 2

    def test_get_executions_by_test(self) -> None:
        """Test filtering executions by test."""
        service = IntegrationTestService()
        tests = service.get_tests()

        service.execute_test(tests[0].id)
        service.execute_test(tests[0].id)
        service.execute_test(tests[1].id)

        executions = service.get_executions(test_id=tests[0].id)

        for execution in executions:
            assert execution.test_id == tests[0].id

    def test_get_executions_with_limit(self) -> None:
        """Test execution limit."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for _ in range(5):
            service.execute_test(tests[0].id)

        executions = service.get_executions(limit=3)
        assert len(executions) <= 3

    def test_get_latest_execution(self) -> None:
        """Test getting latest execution."""
        service = IntegrationTestService()
        tests = service.get_tests()

        service.execute_test(tests[0].id)
        latest = service.execute_test(tests[0].id)

        result = service.get_latest_execution(tests[0].id)
        assert result is not None
        assert result.id == latest.id

    def test_get_latest_no_executions(self) -> None:
        """Test getting latest when no executions."""
        service = IntegrationTestService()

        result = service.get_latest_execution(uuid4())
        assert result is None


class TestStatisticsAndReporting:
    """Tests for statistics and reporting."""

    def test_get_summary(self) -> None:
        """Test getting summary."""
        service = IntegrationTestService()

        summary = service.get_summary()

        assert "total_tests" in summary
        assert "active_tests" in summary
        assert "total_suites" in summary
        assert "by_category" in summary
        assert "by_priority" in summary

    def test_summary_counts_tests(self) -> None:
        """Test summary counts tests correctly."""
        service = IntegrationTestService()
        tests = service.get_tests()

        summary = service.get_summary()

        assert summary["total_tests"] >= len(tests)

    def test_get_test_coverage(self) -> None:
        """Test getting test coverage."""
        service = IntegrationTestService()

        coverage = service.get_test_coverage()

        assert "rfq_workflow" in coverage
        assert "quote_workflow" in coverage
        assert "audit_compliance" in coverage

    def test_coverage_includes_tests(self) -> None:
        """Test coverage includes test names."""
        service = IntegrationTestService()

        coverage = service.get_test_coverage()

        has_tests = any(len(tests) > 0 for tests in coverage.values())
        assert has_tests

    def test_generate_report(self) -> None:
        """Test generating execution report."""
        service = IntegrationTestService()
        tests = service.get_tests()

        service.execute_test(tests[0].id)
        service.execute_test(tests[1].id)

        report = service.generate_report()

        assert "total" in report
        assert "passed" in report
        assert "failed" in report
        assert "pass_rate" in report
        assert "test_results" in report

    def test_generate_report_for_suite(self) -> None:
        """Test generating report for specific suite."""
        service = IntegrationTestService()
        tests = service.get_tests()[:2]

        suite = service.create_suite("Report Suite", "For report", [t.id for t in tests])
        service.execute_suite(suite.id)

        report = service.generate_report(suite_id=suite.id)

        assert report["total"] >= 2

    def test_generate_report_empty(self) -> None:
        """Test report with no executions."""
        service = IntegrationTestService()

        # Create a new suite with no executions
        test = service.create_test(
            name="No Exec Test",
            description="Never executed",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.LOW,
            steps=[{"name": "Step", "expected_outcome": "Done"}],
        )
        suite = service.create_suite("Empty Suite", "No execs", [test.id])

        report = service.generate_report(suite_id=suite.id)

        assert report["total"] == 0
        assert report["pass_rate"] == 0


class TestTestSteps:
    """Tests for test step handling."""

    def test_steps_have_sequence(self) -> None:
        """Test steps have proper sequence."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            sequences = [step.sequence for step in test.steps]
            assert sequences == sorted(sequences)

    def test_steps_are_numbered_from_one(self) -> None:
        """Test steps start from 1."""
        service = IntegrationTestService()

        test = service.create_test(
            name="Numbered Steps",
            description="Test step numbering",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.LOW,
            steps=[
                {"name": "First", "expected_outcome": "1"},
                {"name": "Second", "expected_outcome": "2"},
            ],
        )

        assert test.steps[0].sequence == 1
        assert test.steps[1].sequence == 2


class TestTestProperties:
    """Tests for test properties."""

    def test_tests_have_tags(self) -> None:
        """Test tests have tags."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            assert isinstance(test.tags, list)

    def test_tests_have_prerequisites(self) -> None:
        """Test tests have prerequisites."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            assert isinstance(test.prerequisites, list)

    def test_tests_have_descriptions(self) -> None:
        """Test all tests have descriptions."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            assert test.description != ""

    def test_tests_have_timeout(self) -> None:
        """Test tests have timeout set."""
        service = IntegrationTestService()
        tests = service.get_tests()

        for test in tests:
            assert test.timeout_seconds > 0


class TestMultipleFilters:
    """Tests for combining filters."""

    def test_category_and_priority_filter(self) -> None:
        """Test filtering by category and priority."""
        service = IntegrationTestService()

        tests = service.get_tests(
            category=TestCategory.RFQ_WORKFLOW,
            priority=TestPriority.CRITICAL,
        )

        for test in tests:
            assert test.category == TestCategory.RFQ_WORKFLOW
            assert test.priority == TestPriority.CRITICAL

    def test_category_and_tag_filter(self) -> None:
        """Test filtering by category and tag."""
        service = IntegrationTestService()

        tests = service.get_tests(
            category=TestCategory.QUOTE_WORKFLOW,
            tag="approval",
        )

        for test in tests:
            assert test.category == TestCategory.QUOTE_WORKFLOW
            assert "approval" in test.tags


class TestExecutionEnvironment:
    """Tests for execution environment handling."""

    def test_execution_records_environment(self) -> None:
        """Test execution records environment."""
        service = IntegrationTestService()
        tests = service.get_tests()

        execution = service.execute_test(tests[0].id, environment="staging")

        assert execution.environment == "staging"

    def test_default_environment(self) -> None:
        """Test default environment is test."""
        service = IntegrationTestService()
        tests = service.get_tests()

        execution = service.execute_test(tests[0].id)

        assert execution.environment == "test"

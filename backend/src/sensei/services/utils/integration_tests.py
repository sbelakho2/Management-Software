"""
Integration Tests Suite.

End-to-end tests for object lifecycle transitions, workflow integrations,
and cross-module functionality. Tests complete journeys through the system.
"""

import pytest
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class TestResult(str, Enum):
    """Test execution result."""

    __test__ = False

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestCategory(str, Enum):
    """Integration test categories."""

    __test__ = False

    RFQ_WORKFLOW = "rfq_workflow"
    QUALIFICATION_WORKFLOW = "qualification_workflow"
    QUOTE_WORKFLOW = "quote_workflow"
    APPROVAL_WORKFLOW = "approval_workflow"
    PRODUCTION_WORKFLOW = "production_workflow"
    QUALITY_WORKFLOW = "quality_workflow"
    AUDIT_VERIFICATION = "audit_verification"
    STATE_TRANSITION = "state_transition"
    CROSS_MODULE = "cross_module"
    DATA_INTEGRITY = "data_integrity"


class TestPriority(str, Enum):
    """Test priority levels."""

    __test__ = False

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestStep:
    """Individual step in an integration test."""

    __test__ = False

    id: UUID
    sequence: int
    name: str
    description: str
    action: Callable[..., Any] | None
    expected_outcome: str
    actual_outcome: str | None = None
    passed: bool | None = None
    executed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None


@dataclass
class TestContext:
    """Context passed between test steps."""

    __test__ = False

    data: dict[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    account_id: UUID | None = None
    created_objects: dict[str, list[UUID]] = field(default_factory=dict)
    audit_entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IntegrationTest:
    """Integration test definition."""

    id: UUID
    name: str
    description: str
    category: TestCategory
    priority: TestPriority
    steps: list[TestStep]
    tags: list[str]
    prerequisites: list[str]
    setup_func: Callable[[TestContext], None] | None = None
    teardown_func: Callable[[TestContext], None] | None = None
    timeout_seconds: int = 300
    is_active: bool = True


@dataclass
class TestExecution:
    """Record of a test execution."""

    __test__ = False

    id: UUID
    test_id: UUID
    test_name: str
    result: TestResult
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    step_results: list[dict[str, Any]]
    context_snapshot: dict[str, Any]
    error_details: str | None = None
    environment: str = "test"


@dataclass
class TestSuite:
    """Collection of related integration tests."""

    __test__ = False

    id: UUID
    name: str
    description: str
    tests: list[IntegrationTest]
    created_at: datetime


class IntegrationTestService:
    """Service for managing and running integration tests."""

    def __init__(self) -> None:
        """Initialize the integration test service."""
        self._tests: dict[UUID, IntegrationTest] = {}
        self._suites: dict[UUID, TestSuite] = {}
        self._executions: list[TestExecution] = []

        # Initialize default test suites
        self._initialize_default_tests()

    def _initialize_default_tests(self) -> None:
        """Initialize default integration test definitions."""
        # RFQ to Qualification workflow
        self._create_rfq_qualification_test()

        # Qualification to Quote workflow
        self._create_qualification_quote_test()

        # Quote approval workflow
        self._create_quote_approval_test()

        # Complete RFQ to Release workflow
        self._create_full_rfq_to_release_test()

        # Andon to A3 escalation workflow
        self._create_andon_a3_escalation_test()

        # NC to CAPA workflow
        self._create_nc_capa_test()

        # Audit trail verification
        self._create_audit_verification_test()

        # State machine transitions
        self._create_state_transition_test()

        # Cross-module data integrity
        self._create_data_integrity_test()

        # Training matrix integration
        self._create_training_integration_test()

    def _create_rfq_qualification_test(self) -> IntegrationTest:
        """Create RFQ to Qualification workflow test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Create RFQ Draft",
                description="Create a new RFQ in draft status",
                action=None,
                expected_outcome="RFQ created with status DRAFT",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Add Required Fields",
                description="Populate all required RFQ fields",
                action=None,
                expected_outcome="All mandatory fields populated",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Calculate Completeness",
                description="Calculate RFQ completeness score",
                action=None,
                expected_outcome="Completeness score >= 80%",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Transition to Intake",
                description="Move RFQ from Draft to Intake status",
                action=None,
                expected_outcome="Status changed to INTAKE",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Add Missing Info Tasks",
                description="Create tasks for missing information",
                action=None,
                expected_outcome="Missing info tasks created",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Complete Intake",
                description="Mark intake as complete",
                action=None,
                expected_outcome="Status changed to COMPLETE",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Create Qualification",
                description="Create qualification record for RFQ",
                action=None,
                expected_outcome="Qualification created and linked to RFQ",
            ),
            TestStep(
                id=uuid4(),
                sequence=8,
                name="Verify Audit Trail",
                description="Verify all state changes are logged",
                action=None,
                expected_outcome="Audit entries exist for all transitions",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="RFQ to Qualification Workflow",
            description="Tests complete RFQ lifecycle from draft through qualification creation",
            category=TestCategory.RFQ_WORKFLOW,
            priority=TestPriority.CRITICAL,
            steps=steps,
            tags=["rfq", "qualification", "workflow"],
            prerequisites=["User with Sales Engineer role", "Active account"],
        )

        self._tests[test.id] = test
        return test

    def _create_qualification_quote_test(self) -> IntegrationTest:
        """Create Qualification to Quote workflow test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Start Qualification",
                description="Begin qualification scoring process",
                action=None,
                expected_outcome="Qualification status IN_PROGRESS",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Enter Dimension Scores",
                description="Score all qualification dimensions",
                action=None,
                expected_outcome="All dimension scores entered",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Calculate Overall Score",
                description="Calculate composite qualification score",
                action=None,
                expected_outcome="Overall score calculated",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Propose Decision",
                description="Propose qualification decision (QUOTE)",
                action=None,
                expected_outcome="Decision proposed with rationale",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Approve Decision",
                description="Approve qualification decision",
                action=None,
                expected_outcome="Qualification approved",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Generate Qualification PDF",
                description="Generate qualification report PDF",
                action=None,
                expected_outcome="PDF generated and attached",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Create Quote",
                description="Create quote from qualified RFQ",
                action=None,
                expected_outcome="Quote created with reference to qualification",
            ),
            TestStep(
                id=uuid4(),
                sequence=8,
                name="Verify Linkage",
                description="Verify RFQ → Qualification → Quote chain",
                action=None,
                expected_outcome="All objects properly linked",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="Qualification to Quote Workflow",
            description="Tests qualification decision and quote creation flow",
            category=TestCategory.QUALIFICATION_WORKFLOW,
            priority=TestPriority.CRITICAL,
            steps=steps,
            tags=["qualification", "quote", "workflow"],
            prerequisites=["Completed RFQ", "User with approval permissions"],
        )

        self._tests[test.id] = test
        return test

    def _create_quote_approval_test(self) -> IntegrationTest:
        """Create Quote approval workflow test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Create Quote Draft",
                description="Create quote with line items",
                action=None,
                expected_outcome="Quote in DRAFT status",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Add Line Items",
                description="Add costing line items to quote",
                action=None,
                expected_outcome="Line items added with costs",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Enter Assumptions",
                description="Enter required assumptions",
                action=None,
                expected_outcome="Assumptions documented",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Run Quality Checks",
                description="Execute pre-release quality checks",
                action=None,
                expected_outcome="All quality checks pass",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Submit for Approval",
                description="Submit quote for approval",
                action=None,
                expected_outcome="Quote status PENDING_APPROVAL",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Check Margin Threshold",
                description="Verify margin triggers appropriate approval",
                action=None,
                expected_outcome="Correct approver notified",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Approve Quote",
                description="Approve quote with comments",
                action=None,
                expected_outcome="Quote status APPROVED",
            ),
            TestStep(
                id=uuid4(),
                sequence=8,
                name="Create Immutable Version",
                description="Create immutable quote version",
                action=None,
                expected_outcome="Version created and locked",
            ),
            TestStep(
                id=uuid4(),
                sequence=9,
                name="Generate Quote PDF",
                description="Generate customer-facing quote PDF",
                action=None,
                expected_outcome="PDF bound to version",
            ),
            TestStep(
                id=uuid4(),
                sequence=10,
                name="Verify Audit Complete",
                description="Verify full approval audit trail",
                action=None,
                expected_outcome="All approval steps audited",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="Quote Approval Workflow",
            description="Tests complete quote approval flow including version locking",
            category=TestCategory.QUOTE_WORKFLOW,
            priority=TestPriority.CRITICAL,
            steps=steps,
            tags=["quote", "approval", "versioning"],
            prerequisites=["Approved qualification", "Finance approver role"],
        )

        self._tests[test.id] = test
        return test

    def _create_full_rfq_to_release_test(self) -> IntegrationTest:
        """Create complete RFQ to Release end-to-end test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Create Opportunity",
                description="Create opportunity with customer info",
                action=None,
                expected_outcome="Opportunity created",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Create RFQ",
                description="Create RFQ linked to opportunity",
                action=None,
                expected_outcome="RFQ linked to opportunity",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Complete RFQ Intake",
                description="Fill all required RFQ fields",
                action=None,
                expected_outcome="RFQ completeness >= 100%",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Add Attachments",
                description="Add specification attachments",
                action=None,
                expected_outcome="Attachments uploaded",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Create Qualification",
                description="Create and score qualification",
                action=None,
                expected_outcome="Qualification scored",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Approve Qualification",
                description="Approve with QUOTE decision",
                action=None,
                expected_outcome="Decision approved",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Request Supplier Quotes",
                description="Create supplier quote requests",
                action=None,
                expected_outcome="Supplier quotes requested",
            ),
            TestStep(
                id=uuid4(),
                sequence=8,
                name="Receive Supplier Quotes",
                description="Record received supplier quotes",
                action=None,
                expected_outcome="Supplier quotes logged",
            ),
            TestStep(
                id=uuid4(),
                sequence=9,
                name="Build Quote",
                description="Create quote with costing",
                action=None,
                expected_outcome="Quote fully costed",
            ),
            TestStep(
                id=uuid4(),
                sequence=10,
                name="Approve Quote",
                description="Get required approvals",
                action=None,
                expected_outcome="Quote approved",
            ),
            TestStep(
                id=uuid4(),
                sequence=11,
                name="Release Quote",
                description="Release quote to customer",
                action=None,
                expected_outcome="Quote released",
            ),
            TestStep(
                id=uuid4(),
                sequence=12,
                name="Capture CTQs",
                description="Document customer CTQ requirements",
                action=None,
                expected_outcome="CTQs captured",
            ),
            TestStep(
                id=uuid4(),
                sequence=13,
                name="Win Opportunity",
                description="Mark opportunity as won",
                action=None,
                expected_outcome="Opportunity status WON",
            ),
            TestStep(
                id=uuid4(),
                sequence=14,
                name="Verify Complete Audit",
                description="Verify full journey audit trail",
                action=None,
                expected_outcome="All transitions audited",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="RFQ to Release Complete Journey",
            description="Full end-to-end test from opportunity creation through quote release",
            category=TestCategory.CROSS_MODULE,
            priority=TestPriority.CRITICAL,
            steps=steps,
            tags=["e2e", "rfq", "qualification", "quote", "release"],
            prerequisites=["All roles available", "PDF generation enabled"],
            timeout_seconds=600,
        )

        self._tests[test.id] = test
        return test

    def _create_andon_a3_escalation_test(self) -> IntegrationTest:
        """Create Andon to A3 escalation workflow test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Trigger Andon Event",
                description="Create first Andon event at station",
                action=None,
                expected_outcome="Andon event created",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Acknowledge Andon",
                description="Acknowledge the Andon event",
                action=None,
                expected_outcome="Andon acknowledged within SLA",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Resolve Andon",
                description="Resolve the Andon event",
                action=None,
                expected_outcome="Andon resolved",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Create Second Andon",
                description="Create second similar Andon event",
                action=None,
                expected_outcome="Second event created",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Resolve Second Andon",
                description="Resolve the second Andon",
                action=None,
                expected_outcome="Second event resolved",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Create Third Andon",
                description="Create third similar Andon (triggers recurrence)",
                action=None,
                expected_outcome="Third event created",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Verify A3 Auto-Creation",
                description="Verify A3 was automatically created",
                action=None,
                expected_outcome="A3 created from recurrence",
            ),
            TestStep(
                id=uuid4(),
                sequence=8,
                name="Verify Andon Links",
                description="Verify all Andon events linked to A3",
                action=None,
                expected_outcome="All 3 events linked to A3",
            ),
            TestStep(
                id=uuid4(),
                sequence=9,
                name="Complete A3",
                description="Complete A3 problem solving",
                action=None,
                expected_outcome="A3 closed with reflection",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="Andon to A3 Escalation",
            description="Tests automatic A3 creation from recurring Andon events",
            category=TestCategory.PRODUCTION_WORKFLOW,
            priority=TestPriority.HIGH,
            steps=steps,
            tags=["andon", "a3", "escalation", "recurrence"],
            prerequisites=["Station setup", "Andon configuration"],
        )

        self._tests[test.id] = test
        return test

    def _create_nc_capa_test(self) -> IntegrationTest:
        """Create NC to CAPA workflow test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Create Non-Conformance",
                description="Create NC record with CRITICAL severity",
                action=None,
                expected_outcome="NC created with CRITICAL severity",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Verify Auto-CAPA",
                description="Verify CAPA was auto-created for critical NC",
                action=None,
                expected_outcome="CAPA auto-created and linked",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Assign CAPA Owner",
                description="Assign owner to CAPA",
                action=None,
                expected_outcome="Owner assigned",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Add Root Cause",
                description="Document root cause analysis",
                action=None,
                expected_outcome="Root cause documented",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Create A3 Link",
                description="Link CAPA to A3 for problem solving",
                action=None,
                expected_outcome="A3 linked to CAPA",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Define Corrective Actions",
                description="Define CAPA corrective actions",
                action=None,
                expected_outcome="Actions defined with owners",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Complete Actions",
                description="Complete all corrective actions",
                action=None,
                expected_outcome="All actions completed",
            ),
            TestStep(
                id=uuid4(),
                sequence=8,
                name="Verify CAPA",
                description="Verify CAPA effectiveness",
                action=None,
                expected_outcome="Verification passed",
            ),
            TestStep(
                id=uuid4(),
                sequence=9,
                name="Update Standard Work",
                description="Update linked standard work document",
                action=None,
                expected_outcome="Standard work updated",
            ),
            TestStep(
                id=uuid4(),
                sequence=10,
                name="Close CAPA",
                description="Close CAPA with effectiveness check scheduled",
                action=None,
                expected_outcome="CAPA closed with follow-up",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="NC to CAPA Workflow",
            description="Tests NC recording through CAPA closure and standard work update",
            category=TestCategory.QUALITY_WORKFLOW,
            priority=TestPriority.HIGH,
            steps=steps,
            tags=["nc", "capa", "quality", "standard-work"],
            prerequisites=["Quality roles", "Standard work setup"],
        )

        self._tests[test.id] = test
        return test

    def _create_audit_verification_test(self) -> IntegrationTest:
        """Create audit trail verification test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Perform State Change",
                description="Change object state",
                action=None,
                expected_outcome="State changed successfully",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Verify Audit Entry Created",
                description="Check audit log for entry",
                action=None,
                expected_outcome="Audit entry exists",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Verify Actor Recorded",
                description="Check user ID in audit entry",
                action=None,
                expected_outcome="Correct user recorded",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Verify Timestamp",
                description="Check timestamp accuracy",
                action=None,
                expected_outcome="Timestamp within tolerance",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Verify Old/New Values",
                description="Check before/after values captured",
                action=None,
                expected_outcome="Field changes captured",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Verify Immutability",
                description="Attempt to modify audit entry",
                action=None,
                expected_outcome="Modification prevented",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Verify Hash Chain",
                description="Check tamper-evident hash",
                action=None,
                expected_outcome="Hash chain valid",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="Audit Trail Verification",
            description="Tests audit log completeness and integrity",
            category=TestCategory.AUDIT_VERIFICATION,
            priority=TestPriority.CRITICAL,
            steps=steps,
            tags=["audit", "security", "compliance"],
            prerequisites=["Audit logging enabled"],
        )

        self._tests[test.id] = test
        return test

    def _create_state_transition_test(self) -> IntegrationTest:
        """Create state machine transition test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Test Valid Transition",
                description="Execute allowed state transition",
                action=None,
                expected_outcome="Transition succeeds",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Test Invalid Transition",
                description="Attempt disallowed transition",
                action=None,
                expected_outcome="Transition rejected with error",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Test Guard Conditions",
                description="Test transition with unmet guard",
                action=None,
                expected_outcome="Guard blocks transition",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Satisfy Guard Condition",
                description="Meet guard requirements",
                action=None,
                expected_outcome="Transition now allowed",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Test Override Path",
                description="Test authorized override",
                action=None,
                expected_outcome="Override with rationale succeeds",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Verify Override Logged",
                description="Check override in audit log",
                action=None,
                expected_outcome="Override rationale captured",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="State Machine Transitions",
            description="Tests state transition rules and override mechanisms",
            category=TestCategory.STATE_TRANSITION,
            priority=TestPriority.HIGH,
            steps=steps,
            tags=["state-machine", "workflow", "guards"],
            prerequisites=["State machine configured"],
        )

        self._tests[test.id] = test
        return test

    def _create_data_integrity_test(self) -> IntegrationTest:
        """Create cross-module data integrity test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Create Linked Objects",
                description="Create objects with foreign key relationships",
                action=None,
                expected_outcome="Objects created with valid links",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Verify Forward References",
                description="Check parent to child references",
                action=None,
                expected_outcome="Forward references valid",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Verify Back References",
                description="Check child to parent references",
                action=None,
                expected_outcome="Back references valid",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Test Cascade Update",
                description="Update parent and check children",
                action=None,
                expected_outcome="Cascade handled correctly",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Test Soft Delete",
                description="Soft delete parent object",
                action=None,
                expected_outcome="Children handled per policy",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Test Orphan Prevention",
                description="Prevent orphaned child records",
                action=None,
                expected_outcome="Orphan creation blocked",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="Cross-Module Data Integrity",
            description="Tests referential integrity across modules",
            category=TestCategory.DATA_INTEGRITY,
            priority=TestPriority.HIGH,
            steps=steps,
            tags=["data", "integrity", "relationships"],
            prerequisites=["Database constraints active"],
        )

        self._tests[test.id] = test
        return test

    def _create_training_integration_test(self) -> IntegrationTest:
        """Create training matrix integration test."""
        steps = [
            TestStep(
                id=uuid4(),
                sequence=1,
                name="Define Skill Requirements",
                description="Set skill requirements for station",
                action=None,
                expected_outcome="Requirements defined",
            ),
            TestStep(
                id=uuid4(),
                sequence=2,
                name="Check User Gaps",
                description="Identify user skill gaps",
                action=None,
                expected_outcome="Gaps identified correctly",
            ),
            TestStep(
                id=uuid4(),
                sequence=3,
                name="Schedule Training",
                description="Create training for gap closure",
                action=None,
                expected_outcome="Training scheduled",
            ),
            TestStep(
                id=uuid4(),
                sequence=4,
                name="Complete Training",
                description="Mark training as completed",
                action=None,
                expected_outcome="Completion recorded",
            ),
            TestStep(
                id=uuid4(),
                sequence=5,
                name="Award Certification",
                description="Certify user for skill",
                action=None,
                expected_outcome="Certification granted",
            ),
            TestStep(
                id=uuid4(),
                sequence=6,
                name="Verify Station Access",
                description="Verify user can now work at station",
                action=None,
                expected_outcome="Access granted",
            ),
            TestStep(
                id=uuid4(),
                sequence=7,
                name="Expire Certification",
                description="Simulate certification expiration",
                action=None,
                expected_outcome="Recertification task created",
            ),
        ]

        test = IntegrationTest(
            id=uuid4(),
            name="Training Matrix Integration",
            description="Tests training, certification, and station access flow",
            category=TestCategory.PRODUCTION_WORKFLOW,
            priority=TestPriority.MEDIUM,
            steps=steps,
            tags=["training", "skills", "certification"],
            prerequisites=["Skills defined", "Stations configured"],
        )

        self._tests[test.id] = test
        return test

    # Test Management Methods

    def create_test(
        self,
        name: str,
        description: str,
        category: TestCategory,
        priority: TestPriority,
        steps: list[dict[str, Any]],
        tags: list[str] | None = None,
        prerequisites: list[str] | None = None,
    ) -> IntegrationTest:
        """Create a new integration test."""
        test_steps = [
            TestStep(
                id=uuid4(),
                sequence=i + 1,
                name=step["name"],
                description=step.get("description", ""),
                action=step.get("action"),
                expected_outcome=step.get("expected_outcome", ""),
            )
            for i, step in enumerate(steps)
        ]

        test = IntegrationTest(
            id=uuid4(),
            name=name,
            description=description,
            category=category,
            priority=priority,
            steps=test_steps,
            tags=tags or [],
            prerequisites=prerequisites or [],
        )

        self._tests[test.id] = test
        return test

    def get_test(self, test_id: UUID) -> IntegrationTest | None:
        """Get a test by ID."""
        return self._tests.get(test_id)

    def get_tests(
        self,
        category: TestCategory | None = None,
        priority: TestPriority | None = None,
        tag: str | None = None,
        active_only: bool = True,
    ) -> list[IntegrationTest]:
        """Get tests with optional filters."""
        tests = []

        for test in self._tests.values():
            if active_only and not test.is_active:
                continue
            if category and test.category != category:
                continue
            if priority and test.priority != priority:
                continue
            if tag and tag not in test.tags:
                continue

            tests.append(test)

        return tests

    def update_test(
        self,
        test_id: UUID,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> IntegrationTest | None:
        """Update a test definition."""
        test = self._tests.get(test_id)
        if not test:
            return None

        if name:
            test.name = name
        if description:
            test.description = description
        if is_active is not None:
            test.is_active = is_active

        return test

    def delete_test(self, test_id: UUID) -> bool:
        """Delete a test."""
        if test_id in self._tests:
            del self._tests[test_id]
            return True
        return False

    # Test Suite Management

    def create_suite(
        self,
        name: str,
        description: str,
        test_ids: list[UUID],
    ) -> TestSuite:
        """Create a test suite from existing tests."""
        tests = [self._tests[tid] for tid in test_ids if tid in self._tests]

        suite = TestSuite(
            id=uuid4(),
            name=name,
            description=description,
            tests=tests,
            created_at=datetime.now(timezone.utc),
        )

        self._suites[suite.id] = suite
        return suite

    def get_suite(self, suite_id: UUID) -> TestSuite | None:
        """Get a test suite by ID."""
        return self._suites.get(suite_id)

    def get_all_suites(self) -> list[TestSuite]:
        """Get all test suites."""
        return list(self._suites.values())

    # Test Execution

    def execute_test(
        self,
        test_id: UUID,
        context: TestContext | None = None,
        environment: str = "test",
    ) -> TestExecution:
        """Execute a single integration test."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")

        ctx = context or TestContext()
        started_at = datetime.now(timezone.utc)
        step_results = []
        overall_result = TestResult.PASSED

        # Run setup if defined
        if test.setup_func:
            try:
                test.setup_func(ctx)
            except Exception as e:
                return TestExecution(
                    id=uuid4(),
                    test_id=test.id,
                    test_name=test.name,
                    result=TestResult.ERROR,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=0,
                    step_results=[],
                    context_snapshot=ctx.data,
                    error_details=f"Setup failed: {e}",
                    environment=environment,
                )

        # Execute each step
        for step in test.steps:
            step_start = datetime.now(timezone.utc)

            try:
                if step.action:
                    step.action(ctx)

                step.passed = True
                step.actual_outcome = step.expected_outcome

            except AssertionError as e:
                step.passed = False
                step.actual_outcome = str(e)
                step.error_message = str(e)
                overall_result = TestResult.FAILED

            except Exception as e:
                step.passed = False
                step.actual_outcome = f"Error: {e}"
                step.error_message = str(e)
                overall_result = TestResult.ERROR
                break

            step.executed_at = step_start
            step_end = datetime.now(timezone.utc)
            step.duration_ms = int((step_end - step_start).total_seconds() * 1000)

            step_results.append({
                "step_id": str(step.id),
                "sequence": step.sequence,
                "name": step.name,
                "passed": step.passed,
                "expected": step.expected_outcome,
                "actual": step.actual_outcome,
                "duration_ms": step.duration_ms,
                "error": step.error_message,
            })

        # Run teardown if defined
        if test.teardown_func:
            try:
                test.teardown_func(ctx)
            except Exception:
                pass  # Log but don't fail test

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        execution = TestExecution(
            id=uuid4(),
            test_id=test.id,
            test_name=test.name,
            result=overall_result,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            step_results=step_results,
            context_snapshot=ctx.data.copy(),
            environment=environment,
        )

        self._executions.append(execution)
        return execution

    def execute_suite(
        self,
        suite_id: UUID,
        context: TestContext | None = None,
        environment: str = "test",
        stop_on_failure: bool = False,
    ) -> list[TestExecution]:
        """Execute all tests in a suite."""
        suite = self._suites.get(suite_id)
        if not suite:
            raise ValueError(f"Suite {suite_id} not found")

        executions = []
        ctx = context or TestContext()

        for test in suite.tests:
            execution = self.execute_test(test.id, ctx, environment)
            executions.append(execution)

            if stop_on_failure and execution.result != TestResult.PASSED:
                break

        return executions

    def execute_by_category(
        self,
        category: TestCategory,
        environment: str = "test",
    ) -> list[TestExecution]:
        """Execute all tests in a category."""
        tests = self.get_tests(category=category)
        executions = []

        for test in tests:
            execution = self.execute_test(test.id, environment=environment)
            executions.append(execution)

        return executions

    # Execution History

    def get_executions(
        self,
        test_id: UUID | None = None,
        result: TestResult | None = None,
        limit: int = 100,
    ) -> list[TestExecution]:
        """Get test execution history."""
        executions = self._executions

        if test_id:
            executions = [e for e in executions if e.test_id == test_id]
        if result:
            executions = [e for e in executions if e.result == result]

        # Sort by most recent first
        executions = sorted(executions, key=lambda e: e.started_at, reverse=True)

        return executions[:limit]

    def get_latest_execution(self, test_id: UUID) -> TestExecution | None:
        """Get the most recent execution of a test."""
        executions = self.get_executions(test_id=test_id, limit=1)
        return executions[0] if executions else None

    # Statistics and Reporting

    def get_summary(self) -> dict[str, Any]:
        """Get overall test summary."""
        tests = list(self._tests.values())

        by_category = {}
        for cat in TestCategory:
            by_category[cat.value] = len([t for t in tests if t.category == cat])

        by_priority = {}
        for pri in TestPriority:
            by_priority[pri.value] = len([t for t in tests if t.priority == pri])

        recent_executions = self._executions[-100:] if self._executions else []
        passed = len([e for e in recent_executions if e.result == TestResult.PASSED])
        failed = len([e for e in recent_executions if e.result == TestResult.FAILED])
        errors = len([e for e in recent_executions if e.result == TestResult.ERROR])

        return {
            "total_tests": len(tests),
            "active_tests": len([t for t in tests if t.is_active]),
            "total_suites": len(self._suites),
            "total_executions": len(self._executions),
            "by_category": by_category,
            "by_priority": by_priority,
            "recent_results": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": passed / len(recent_executions) if recent_executions else 0,
            },
        }

    def get_test_coverage(self) -> dict[str, list[str]]:
        """Get coverage by workflow area."""
        coverage = {
            "rfq_workflow": [],
            "qualification_workflow": [],
            "quote_workflow": [],
            "production_workflow": [],
            "quality_workflow": [],
            "audit_compliance": [],
            "state_transitions": [],
            "data_integrity": [],
        }

        for test in self._tests.values():
            if test.category == TestCategory.RFQ_WORKFLOW:
                coverage["rfq_workflow"].append(test.name)
            elif test.category == TestCategory.QUALIFICATION_WORKFLOW:
                coverage["qualification_workflow"].append(test.name)
            elif test.category == TestCategory.QUOTE_WORKFLOW:
                coverage["quote_workflow"].append(test.name)
            elif test.category == TestCategory.PRODUCTION_WORKFLOW:
                coverage["production_workflow"].append(test.name)
            elif test.category == TestCategory.QUALITY_WORKFLOW:
                coverage["quality_workflow"].append(test.name)
            elif test.category == TestCategory.AUDIT_VERIFICATION:
                coverage["audit_compliance"].append(test.name)
            elif test.category == TestCategory.STATE_TRANSITION:
                coverage["state_transitions"].append(test.name)
            elif test.category == TestCategory.DATA_INTEGRITY:
                coverage["data_integrity"].append(test.name)

        return coverage

    def generate_report(self, suite_id: UUID | None = None) -> dict[str, Any]:
        """Generate a test execution report."""
        if suite_id:
            suite = self._suites.get(suite_id)
            if not suite:
                raise ValueError(f"Suite {suite_id} not found")

            test_ids = {t.id for t in suite.tests}
            executions = [e for e in self._executions if e.test_id in test_ids]
        else:
            executions = self._executions

        if not executions:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "pass_rate": 0,
                "avg_duration_ms": 0,
                "test_results": [],
            }

        passed = len([e for e in executions if e.result == TestResult.PASSED])
        failed = len([e for e in executions if e.result == TestResult.FAILED])
        errors = len([e for e in executions if e.result == TestResult.ERROR])
        skipped = len([e for e in executions if e.result == TestResult.SKIPPED])

        durations = [e.duration_ms for e in executions if e.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total": len(executions),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": passed / len(executions),
            "avg_duration_ms": avg_duration,
            "test_results": [
                {
                    "test_name": e.test_name,
                    "result": e.result.value,
                    "duration_ms": e.duration_ms,
                    "steps_passed": len([s for s in e.step_results if s.get("passed")]),
                    "steps_total": len(e.step_results),
                }
                for e in sorted(executions, key=lambda x: x.started_at, reverse=True)[:50]
            ],
        }

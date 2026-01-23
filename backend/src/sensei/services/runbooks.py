"""Runbooks Documentation Service.

Provides structured runbook management for operational procedures,
incident response guides, and troubleshooting documentation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class RunbookCategory(Enum):
    """Categories for runbooks."""

    INCIDENT_RESPONSE = "incident_response"
    TROUBLESHOOTING = "troubleshooting"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"
    RECOVERY = "recovery"
    SECURITY = "security"
    MONITORING = "monitoring"
    SCALING = "scaling"
    DATABASE = "database"
    NETWORK = "network"
    GENERAL = "general"


class RunbookSeverity(Enum):
    """Severity levels that runbooks apply to."""

    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"
    SEV5 = "sev5"
    ALL = "all"


class StepType(Enum):
    """Types of runbook steps."""

    MANUAL = "manual"
    AUTOMATED = "automated"
    DECISION = "decision"
    NOTIFICATION = "notification"
    VERIFICATION = "verification"
    ESCALATION = "escalation"


class RunbookStatus(Enum):
    """Runbook status."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class RunbookStep:
    """A single step in a runbook."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order: int = 0
    title: str = ""
    description: str = ""
    step_type: StepType = StepType.MANUAL
    command: str = ""  # Command to run if automated
    expected_output: str = ""  # Expected output for verification
    success_criteria: str = ""
    failure_criteria: str = ""
    rollback_instructions: str = ""
    estimated_duration_minutes: int = 5
    requires_approval: bool = False
    approver_role: str = ""
    notes: list[str] = field(default_factory=list)
    related_links: list[str] = field(default_factory=list)


@dataclass
class DecisionBranch:
    """A decision branch for decision-type steps."""

    condition: str = ""
    next_step_id: str = ""
    description: str = ""


@dataclass
class RunbookVersion:
    """Version history entry for a runbook."""

    version: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_by: str = ""
    change_summary: str = ""
    steps_snapshot: list[dict] = field(default_factory=list)


@dataclass
class RunbookExecution:
    """Execution record of a runbook."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    runbook_id: str = ""
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    executed_by: str = ""
    incident_id: str = ""  # Associated incident if any
    steps_completed: list[str] = field(default_factory=list)  # Step IDs
    current_step_id: str = ""
    status: str = "in_progress"  # in_progress, completed, aborted, failed
    notes: list[dict] = field(default_factory=list)
    outcome: str = ""


@dataclass
class Runbook:
    """A runbook document."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    category: RunbookCategory = RunbookCategory.GENERAL
    applicable_severities: list[RunbookSeverity] = field(default_factory=list)
    status: RunbookStatus = RunbookStatus.DRAFT
    version: str = "1.0.0"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_by: str = ""
    updated_by: str = ""
    owner_team: str = ""
    steps: list[RunbookStep] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    required_access: list[str] = field(default_factory=list)
    related_services: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version_history: list[RunbookVersion] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    estimated_total_duration_minutes: int = 0


@dataclass
class RunbookTemplate:
    """Template for creating runbooks."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: RunbookCategory = RunbookCategory.GENERAL
    default_steps: list[RunbookStep] = field(default_factory=list)
    default_prerequisites: list[str] = field(default_factory=list)
    default_required_tools: list[str] = field(default_factory=list)


# Default runbook templates
DEFAULT_TEMPLATES: list[dict] = [
    {
        "name": "Basic Incident Response",
        "description": "Template for general incident response procedures",
        "category": RunbookCategory.INCIDENT_RESPONSE,
        "default_steps": [
            RunbookStep(
                order=1,
                title="Initial Assessment",
                description="Assess the scope and severity of the incident",
                step_type=StepType.MANUAL,
                estimated_duration_minutes=5,
            ),
            RunbookStep(
                order=2,
                title="Notify Stakeholders",
                description="Notify relevant stakeholders based on severity",
                step_type=StepType.NOTIFICATION,
                estimated_duration_minutes=5,
            ),
            RunbookStep(
                order=3,
                title="Investigate Root Cause",
                description="Investigate and identify the root cause",
                step_type=StepType.MANUAL,
                estimated_duration_minutes=30,
            ),
            RunbookStep(
                order=4,
                title="Implement Fix",
                description="Implement the fix or workaround",
                step_type=StepType.MANUAL,
                estimated_duration_minutes=30,
            ),
            RunbookStep(
                order=5,
                title="Verify Resolution",
                description="Verify the incident is resolved",
                step_type=StepType.VERIFICATION,
                estimated_duration_minutes=10,
            ),
        ],
        "default_prerequisites": [
            "Access to monitoring dashboards",
            "Access to relevant logs",
        ],
    },
    {
        "name": "Database Recovery",
        "description": "Template for database recovery procedures",
        "category": RunbookCategory.DATABASE,
        "default_steps": [
            RunbookStep(
                order=1,
                title="Assess Database State",
                description="Check database health and status",
                step_type=StepType.MANUAL,
                command="pg_isready -h localhost -p 5432",
            ),
            RunbookStep(
                order=2,
                title="Check Replication Status",
                description="Verify replication lag and status",
                step_type=StepType.AUTOMATED,
                command="SELECT * FROM pg_stat_replication;",
            ),
            RunbookStep(
                order=3,
                title="Decision: Failover Required?",
                description="Determine if failover to replica is needed",
                step_type=StepType.DECISION,
            ),
            RunbookStep(
                order=4,
                title="Execute Recovery",
                description="Execute recovery procedure",
                step_type=StepType.MANUAL,
                requires_approval=True,
                approver_role="DBA",
            ),
        ],
        "default_prerequisites": [
            "DBA access",
            "SSH access to database servers",
            "Access to backup systems",
        ],
        "default_required_tools": ["psql", "pg_dump", "pg_restore"],
    },
    {
        "name": "Service Deployment",
        "description": "Template for deploying services",
        "category": RunbookCategory.DEPLOYMENT,
        "default_steps": [
            RunbookStep(
                order=1,
                title="Pre-deployment Checks",
                description="Run pre-deployment health checks",
                step_type=StepType.AUTOMATED,
            ),
            RunbookStep(
                order=2,
                title="Create Deployment Backup",
                description="Backup current deployment state",
                step_type=StepType.AUTOMATED,
            ),
            RunbookStep(
                order=3,
                title="Deploy New Version",
                description="Deploy the new version",
                step_type=StepType.AUTOMATED,
                requires_approval=True,
            ),
            RunbookStep(
                order=4,
                title="Run Smoke Tests",
                description="Execute smoke tests on deployed version",
                step_type=StepType.AUTOMATED,
            ),
            RunbookStep(
                order=5,
                title="Monitor Deployment",
                description="Monitor for 15 minutes post-deployment",
                step_type=StepType.VERIFICATION,
                estimated_duration_minutes=15,
            ),
        ],
        "default_prerequisites": [
            "Approved release artifacts",
            "Deployment access",
        ],
    },
    {
        "name": "Security Incident Response",
        "description": "Template for security incident handling",
        "category": RunbookCategory.SECURITY,
        "default_steps": [
            RunbookStep(
                order=1,
                title="Contain Threat",
                description="Immediately contain the security threat",
                step_type=StepType.MANUAL,
                estimated_duration_minutes=15,
            ),
            RunbookStep(
                order=2,
                title="Preserve Evidence",
                description="Preserve logs and forensic evidence",
                step_type=StepType.MANUAL,
                estimated_duration_minutes=30,
            ),
            RunbookStep(
                order=3,
                title="Notify Security Team",
                description="Escalate to security team",
                step_type=StepType.ESCALATION,
                estimated_duration_minutes=5,
            ),
            RunbookStep(
                order=4,
                title="Assess Impact",
                description="Assess the security impact",
                step_type=StepType.MANUAL,
                estimated_duration_minutes=60,
            ),
            RunbookStep(
                order=5,
                title="Remediate",
                description="Apply security remediations",
                step_type=StepType.MANUAL,
                requires_approval=True,
                approver_role="Security Lead",
            ),
        ],
        "default_prerequisites": [
            "Security team contact list",
            "Access to security logs",
            "Incident response tools",
        ],
    },
]


class RunbooksService:
    """Service for managing runbooks."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._runbooks: dict[str, Runbook] = {}
        self._templates: dict[str, RunbookTemplate] = {}
        self._executions: dict[str, RunbookExecution] = {}
        self._initialize_default_templates()
        self._initialize_default_runbooks()

    def _initialize_default_templates(self) -> None:
        """Initialize default runbook templates."""
        for template_data in DEFAULT_TEMPLATES:
            template = RunbookTemplate(
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                default_steps=template_data["default_steps"],
                default_prerequisites=template_data.get("default_prerequisites", []),
                default_required_tools=template_data.get("default_required_tools", []),
            )
            self._templates[template.id] = template

    def _initialize_default_runbooks(self) -> None:
        """Initialize default runbooks from templates."""
        # Create a few ready-to-use runbooks
        defaults = [
            {
                "title": "API Service High Error Rate Response",
                "description": "Runbook for handling elevated error rates in API services",
                "category": RunbookCategory.INCIDENT_RESPONSE,
                "owner_team": "backend",
                "related_services": ["api", "gateway"],
                "applicable_severities": [RunbookSeverity.SEV1, RunbookSeverity.SEV2],
                "steps": [
                    RunbookStep(
                        order=1,
                        title="Check Current Error Rate",
                        description="Monitor current error rate and trend",
                        step_type=StepType.VERIFICATION,
                        command="curl -s http://prometheus:9090/api/v1/query?query=rate(http_errors_total[5m])",
                        estimated_duration_minutes=2,
                    ),
                    RunbookStep(
                        order=2,
                        title="Identify Affected Endpoints",
                        description="Identify which endpoints are failing",
                        step_type=StepType.MANUAL,
                        estimated_duration_minutes=5,
                    ),
                    RunbookStep(
                        order=3,
                        title="Check Downstream Dependencies",
                        description="Verify health of database, cache, and external services",
                        step_type=StepType.MANUAL,
                        estimated_duration_minutes=5,
                    ),
                    RunbookStep(
                        order=4,
                        title="Decision: Scale or Fix",
                        description="Decide whether to scale or apply fix",
                        step_type=StepType.DECISION,
                    ),
                    RunbookStep(
                        order=5,
                        title="Apply Mitigation",
                        description="Apply scaling or code fix",
                        step_type=StepType.MANUAL,
                        requires_approval=True,
                        approver_role="Tech Lead",
                    ),
                    RunbookStep(
                        order=6,
                        title="Verify Resolution",
                        description="Confirm error rate has normalized",
                        step_type=StepType.VERIFICATION,
                        success_criteria="Error rate below 1%",
                        estimated_duration_minutes=10,
                    ),
                ],
                "tags": ["api", "errors", "sev1", "sev2"],
            },
            {
                "title": "Database Connection Pool Exhaustion",
                "description": "Runbook for handling database connection pool issues",
                "category": RunbookCategory.DATABASE,
                "owner_team": "platform",
                "related_services": ["database", "api"],
                "applicable_severities": [RunbookSeverity.SEV2, RunbookSeverity.SEV3],
                "steps": [
                    RunbookStep(
                        order=1,
                        title="Check Connection Count",
                        description="Check current active connections",
                        step_type=StepType.AUTOMATED,
                        command="SELECT count(*) FROM pg_stat_activity WHERE state != 'idle';",
                        estimated_duration_minutes=1,
                    ),
                    RunbookStep(
                        order=2,
                        title="Identify Long-Running Queries",
                        description="Find queries holding connections",
                        step_type=StepType.AUTOMATED,
                        command="SELECT pid, query, state, now() - query_start as duration FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;",
                        estimated_duration_minutes=2,
                    ),
                    RunbookStep(
                        order=3,
                        title="Kill Problematic Connections",
                        description="Terminate long-running or stuck connections",
                        step_type=StepType.MANUAL,
                        command="SELECT pg_terminate_backend(pid);",
                        requires_approval=True,
                        approver_role="DBA",
                        estimated_duration_minutes=5,
                    ),
                    RunbookStep(
                        order=4,
                        title="Increase Pool Size (if needed)",
                        description="Temporarily increase connection pool",
                        step_type=StepType.MANUAL,
                        estimated_duration_minutes=10,
                    ),
                    RunbookStep(
                        order=5,
                        title="Verify Pool Health",
                        description="Confirm connection pool is healthy",
                        step_type=StepType.VERIFICATION,
                        success_criteria="Available connections > 50%",
                        estimated_duration_minutes=5,
                    ),
                ],
                "tags": ["database", "connections", "postgresql"],
            },
        ]

        for runbook_data in defaults:
            runbook = Runbook(
                title=str(runbook_data["title"]),
                description=str(runbook_data["description"]),
                category=runbook_data["category"],  # type: ignore[arg-type]
                owner_team=str(runbook_data["owner_team"]),
                related_services=runbook_data["related_services"],  # type: ignore[arg-type]
                applicable_severities=runbook_data["applicable_severities"],  # type: ignore[arg-type]
                steps=runbook_data["steps"],  # type: ignore[arg-type]
                tags=runbook_data["tags"],  # type: ignore[arg-type]
                status=RunbookStatus.APPROVED,
            )
            runbook.estimated_total_duration_minutes = sum(
                s.estimated_duration_minutes for s in runbook.steps
            )
            self._runbooks[runbook.id] = runbook

    # ========================================
    # Template Management
    # ========================================

    def get_template(self, template_id: str) -> Optional[RunbookTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def get_all_templates(self) -> list[RunbookTemplate]:
        """Get all templates."""
        return list(self._templates.values())

    def get_templates_by_category(
        self, category: RunbookCategory
    ) -> list[RunbookTemplate]:
        """Get templates by category."""
        return [t for t in self._templates.values() if t.category == category]

    def create_template(
        self,
        name: str,
        description: str = "",
        category: RunbookCategory = RunbookCategory.GENERAL,
        default_steps: Optional[list[RunbookStep]] = None,
        default_prerequisites: Optional[list[str]] = None,
        default_required_tools: Optional[list[str]] = None,
    ) -> RunbookTemplate:
        """Create a new template."""
        template = RunbookTemplate(
            name=name,
            description=description,
            category=category,
            default_steps=default_steps or [],
            default_prerequisites=default_prerequisites or [],
            default_required_tools=default_required_tools or [],
        )
        self._templates[template.id] = template
        return template

    def create_runbook_from_template(
        self,
        template_id: str,
        title: str,
        description: str = "",
        created_by: str = "",
        owner_team: str = "",
    ) -> Optional[Runbook]:
        """Create a runbook from a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        # Deep copy the steps
        steps = [
            RunbookStep(
                order=s.order,
                title=s.title,
                description=s.description,
                step_type=s.step_type,
                command=s.command,
                expected_output=s.expected_output,
                success_criteria=s.success_criteria,
                failure_criteria=s.failure_criteria,
                rollback_instructions=s.rollback_instructions,
                estimated_duration_minutes=s.estimated_duration_minutes,
                requires_approval=s.requires_approval,
                approver_role=s.approver_role,
            )
            for s in template.default_steps
        ]

        runbook = Runbook(
            title=title,
            description=description or template.description,
            category=template.category,
            status=RunbookStatus.DRAFT,
            created_by=created_by,
            updated_by=created_by,
            owner_team=owner_team,
            steps=steps,
            prerequisites=list(template.default_prerequisites),
            required_tools=list(template.default_required_tools),
        )
        runbook.estimated_total_duration_minutes = sum(
            s.estimated_duration_minutes for s in steps
        )
        self._runbooks[runbook.id] = runbook
        return runbook

    # ========================================
    # Runbook Management
    # ========================================

    def create_runbook(
        self,
        title: str,
        description: str = "",
        category: RunbookCategory = RunbookCategory.GENERAL,
        created_by: str = "",
        owner_team: str = "",
        applicable_severities: Optional[list[RunbookSeverity]] = None,
        steps: Optional[list[RunbookStep]] = None,
        prerequisites: Optional[list[str]] = None,
        required_tools: Optional[list[str]] = None,
        required_access: Optional[list[str]] = None,
        related_services: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> Runbook:
        """Create a new runbook."""
        runbook = Runbook(
            title=title,
            description=description,
            category=category,
            status=RunbookStatus.DRAFT,
            created_by=created_by,
            updated_by=created_by,
            owner_team=owner_team,
            applicable_severities=applicable_severities or [],
            steps=steps or [],
            prerequisites=prerequisites or [],
            required_tools=required_tools or [],
            required_access=required_access or [],
            related_services=related_services or [],
            tags=tags or [],
        )
        runbook.estimated_total_duration_minutes = sum(
            s.estimated_duration_minutes for s in runbook.steps
        )
        self._runbooks[runbook.id] = runbook
        return runbook

    def get_runbook(self, runbook_id: str) -> Optional[Runbook]:
        """Get a runbook by ID."""
        return self._runbooks.get(runbook_id)

    def get_all_runbooks(self) -> list[Runbook]:
        """Get all runbooks."""
        return list(self._runbooks.values())

    def get_runbooks_by_category(self, category: RunbookCategory) -> list[Runbook]:
        """Get runbooks by category."""
        return [r for r in self._runbooks.values() if r.category == category]

    def get_runbooks_by_status(self, status: RunbookStatus) -> list[Runbook]:
        """Get runbooks by status."""
        return [r for r in self._runbooks.values() if r.status == status]

    def get_runbooks_by_severity(self, severity: RunbookSeverity) -> list[Runbook]:
        """Get runbooks applicable to a severity."""
        return [
            r
            for r in self._runbooks.values()
            if severity in r.applicable_severities
            or RunbookSeverity.ALL in r.applicable_severities
        ]

    def get_runbooks_by_service(self, service: str) -> list[Runbook]:
        """Get runbooks for a specific service."""
        return [r for r in self._runbooks.values() if service in r.related_services]

    def get_runbooks_by_team(self, team: str) -> list[Runbook]:
        """Get runbooks owned by a team."""
        return [r for r in self._runbooks.values() if r.owner_team == team]

    def search_runbooks(self, query: str) -> list[Runbook]:
        """Search runbooks by title, description, or tags."""
        query_lower = query.lower()
        return [
            r
            for r in self._runbooks.values()
            if query_lower in r.title.lower()
            or query_lower in r.description.lower()
            or any(query_lower in tag.lower() for tag in r.tags)
        ]

    def update_runbook(
        self,
        runbook_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        updated_by: str = "",
        owner_team: Optional[str] = None,
        applicable_severities: Optional[list[RunbookSeverity]] = None,
        prerequisites: Optional[list[str]] = None,
        required_tools: Optional[list[str]] = None,
        required_access: Optional[list[str]] = None,
        related_services: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[Runbook]:
        """Update a runbook's metadata."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        if title is not None:
            runbook.title = title
        if description is not None:
            runbook.description = description
        if owner_team is not None:
            runbook.owner_team = owner_team
        if applicable_severities is not None:
            runbook.applicable_severities = applicable_severities
        if prerequisites is not None:
            runbook.prerequisites = prerequisites
        if required_tools is not None:
            runbook.required_tools = required_tools
        if required_access is not None:
            runbook.required_access = required_access
        if related_services is not None:
            runbook.related_services = related_services
        if tags is not None:
            runbook.tags = tags

        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = updated_by

        return runbook

    def update_runbook_status(
        self,
        runbook_id: str,
        status: RunbookStatus,
        updated_by: str = "",
    ) -> Optional[Runbook]:
        """Update runbook status."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        runbook.status = status
        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = updated_by
        return runbook

    def delete_runbook(self, runbook_id: str) -> bool:
        """Delete a runbook."""
        if runbook_id in self._runbooks:
            del self._runbooks[runbook_id]
            return True
        return False

    # ========================================
    # Step Management
    # ========================================

    def add_step(
        self,
        runbook_id: str,
        step: RunbookStep,
        updated_by: str = "",
    ) -> Optional[Runbook]:
        """Add a step to a runbook."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        # Set order if not specified
        if step.order == 0:
            step.order = len(runbook.steps) + 1

        runbook.steps.append(step)
        runbook.steps.sort(key=lambda s: s.order)
        runbook.estimated_total_duration_minutes = sum(
            s.estimated_duration_minutes for s in runbook.steps
        )
        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = updated_by

        return runbook

    def update_step(
        self,
        runbook_id: str,
        step_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        step_type: Optional[StepType] = None,
        command: Optional[str] = None,
        expected_output: Optional[str] = None,
        success_criteria: Optional[str] = None,
        failure_criteria: Optional[str] = None,
        rollback_instructions: Optional[str] = None,
        estimated_duration_minutes: Optional[int] = None,
        requires_approval: Optional[bool] = None,
        approver_role: Optional[str] = None,
        updated_by: str = "",
    ) -> Optional[RunbookStep]:
        """Update a step."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        step = next((s for s in runbook.steps if s.id == step_id), None)
        if not step:
            return None

        if title is not None:
            step.title = title
        if description is not None:
            step.description = description
        if step_type is not None:
            step.step_type = step_type
        if command is not None:
            step.command = command
        if expected_output is not None:
            step.expected_output = expected_output
        if success_criteria is not None:
            step.success_criteria = success_criteria
        if failure_criteria is not None:
            step.failure_criteria = failure_criteria
        if rollback_instructions is not None:
            step.rollback_instructions = rollback_instructions
        if estimated_duration_minutes is not None:
            step.estimated_duration_minutes = estimated_duration_minutes
        if requires_approval is not None:
            step.requires_approval = requires_approval
        if approver_role is not None:
            step.approver_role = approver_role

        runbook.estimated_total_duration_minutes = sum(
            s.estimated_duration_minutes for s in runbook.steps
        )
        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = updated_by

        return step

    def remove_step(
        self,
        runbook_id: str,
        step_id: str,
        updated_by: str = "",
    ) -> Optional[Runbook]:
        """Remove a step from a runbook."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        runbook.steps = [s for s in runbook.steps if s.id != step_id]
        # Re-order remaining steps
        for i, step in enumerate(runbook.steps, start=1):
            step.order = i

        runbook.estimated_total_duration_minutes = sum(
            s.estimated_duration_minutes for s in runbook.steps
        )
        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = updated_by

        return runbook

    def reorder_steps(
        self,
        runbook_id: str,
        step_ids: list[str],
        updated_by: str = "",
    ) -> Optional[Runbook]:
        """Reorder steps in a runbook."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        step_map = {s.id: s for s in runbook.steps}
        new_steps = []
        for i, step_id in enumerate(step_ids, start=1):
            if step_id in step_map:
                step_map[step_id].order = i
                new_steps.append(step_map[step_id])

        runbook.steps = new_steps
        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = updated_by

        return runbook

    # ========================================
    # Version Management
    # ========================================

    def create_version(
        self,
        runbook_id: str,
        version: str,
        change_summary: str,
        created_by: str = "",
    ) -> Optional[Runbook]:
        """Create a new version of a runbook."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return None

        # Snapshot current steps
        steps_snapshot = [
            {
                "id": s.id,
                "order": s.order,
                "title": s.title,
                "description": s.description,
                "step_type": s.step_type.value,
                "command": s.command,
            }
            for s in runbook.steps
        ]

        version_entry = RunbookVersion(
            version=version,
            created_by=created_by,
            change_summary=change_summary,
            steps_snapshot=steps_snapshot,
        )

        runbook.version_history.append(version_entry)
        runbook.version = version
        runbook.updated_at = datetime.now(timezone.utc)
        runbook.updated_by = created_by

        return runbook

    def get_version_history(self, runbook_id: str) -> list[RunbookVersion]:
        """Get version history for a runbook."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook:
            return []
        return runbook.version_history

    # ========================================
    # Execution Tracking
    # ========================================

    def start_execution(
        self,
        runbook_id: str,
        executed_by: str,
        incident_id: str = "",
    ) -> Optional[RunbookExecution]:
        """Start executing a runbook."""
        runbook = self._runbooks.get(runbook_id)
        if not runbook or not runbook.steps:
            return None

        execution = RunbookExecution(
            runbook_id=runbook_id,
            executed_by=executed_by,
            incident_id=incident_id,
            current_step_id=runbook.steps[0].id,
            status="in_progress",
        )
        self._executions[execution.id] = execution
        return execution

    def get_execution(self, execution_id: str) -> Optional[RunbookExecution]:
        """Get an execution by ID."""
        return self._executions.get(execution_id)

    def get_executions_for_runbook(self, runbook_id: str) -> list[RunbookExecution]:
        """Get all executions for a runbook."""
        return [e for e in self._executions.values() if e.runbook_id == runbook_id]

    def get_executions_for_incident(self, incident_id: str) -> list[RunbookExecution]:
        """Get all executions for an incident."""
        return [e for e in self._executions.values() if e.incident_id == incident_id]

    def complete_step(
        self,
        execution_id: str,
        step_id: str,
        notes: str = "",
    ) -> Optional[RunbookExecution]:
        """Mark a step as completed."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        runbook = self._runbooks.get(execution.runbook_id)
        if not runbook:
            return None

        execution.steps_completed.append(step_id)
        if notes:
            execution.notes.append({
                "step_id": step_id,
                "notes": notes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Find next step
        current_idx = next(
            (i for i, s in enumerate(runbook.steps) if s.id == step_id), -1
        )
        if current_idx >= 0 and current_idx < len(runbook.steps) - 1:
            execution.current_step_id = runbook.steps[current_idx + 1].id
        else:
            execution.current_step_id = ""

        return execution

    def complete_execution(
        self,
        execution_id: str,
        outcome: str = "",
    ) -> Optional[RunbookExecution]:
        """Complete an execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.status = "completed"
        execution.completed_at = datetime.now(timezone.utc)
        execution.outcome = outcome
        return execution

    def abort_execution(
        self,
        execution_id: str,
        reason: str = "",
    ) -> Optional[RunbookExecution]:
        """Abort an execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.status = "aborted"
        execution.completed_at = datetime.now(timezone.utc)
        execution.outcome = f"Aborted: {reason}"
        return execution

    # ========================================
    # Summary and Metrics
    # ========================================

    def get_summary(self) -> dict:
        """Get summary of runbooks."""
        runbooks = self.get_all_runbooks()
        executions = list(self._executions.values())

        by_category: dict[str, int] = {}
        for r in runbooks:
            cat = r.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        by_status: dict[str, int] = {}
        for r in runbooks:
            status = r.status.value
            by_status[status] = by_status.get(status, 0) + 1

        completed_executions = [
            e for e in executions if e.status == "completed"
        ]

        return {
            "total_runbooks": len(runbooks),
            "total_templates": len(self._templates),
            "total_executions": len(executions),
            "completed_executions": len(completed_executions),
            "by_category": by_category,
            "by_status": by_status,
            "approved_runbooks": len(
                [r for r in runbooks if r.status == RunbookStatus.APPROVED]
            ),
        }

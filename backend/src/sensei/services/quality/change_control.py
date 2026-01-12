"""Change Control Service.

Requires approval and audit log for production changes to:
- Thresholds
- Margin floors
- Pipeline stages
- Templates

Provides a formal change request workflow with approvals,
impact assessment, and rollback capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class ChangeType(Enum):
    """Types of configuration changes."""

    THRESHOLD = "threshold"
    MARGIN_FLOOR = "margin_floor"
    PIPELINE_STAGE = "pipeline_stage"
    TEMPLATE = "template"
    SYSTEM_CONFIG = "system_config"
    WORKFLOW_RULE = "workflow_rule"
    PERMISSION = "permission"
    INTEGRATION = "integration"


class ChangeStatus(Enum):
    """Status of a change request."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ChangeRisk(Enum):
    """Risk level of a change."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeImpact(Enum):
    """Impact level of a change."""

    MINIMAL = "minimal"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


class ApprovalDecision(Enum):
    """Approval decision options."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"


@dataclass
class ConfigValue:
    """A configuration value (before or after)."""

    key: str = ""
    value: Any = None
    value_type: str = "string"
    description: str = ""


@dataclass
class ChangeApproval:
    """Approval record for a change."""

    id: UUID = field(default_factory=uuid4)
    change_id: UUID = field(default_factory=uuid4)
    approver_id: UUID = field(default_factory=uuid4)
    approver_name: str = ""
    decision: ApprovalDecision = ApprovalDecision.APPROVED
    comments: str = ""
    approved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    conditions: list[str] = field(default_factory=list)


@dataclass
class ImpactAssessment:
    """Impact assessment for a change."""

    id: UUID = field(default_factory=uuid4)
    change_id: UUID = field(default_factory=uuid4)
    risk_level: ChangeRisk = ChangeRisk.LOW
    impact_level: ChangeImpact = ChangeImpact.MINIMAL
    affected_areas: list[str] = field(default_factory=list)
    affected_user_count: int = 0
    rollback_plan: str = ""
    testing_required: bool = False
    testing_notes: str = ""
    dependencies: list[str] = field(default_factory=list)
    estimated_downtime_minutes: int = 0
    assessed_by: UUID = field(default_factory=uuid4)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChangeAuditEntry:
    """Audit entry for change actions."""

    id: UUID = field(default_factory=uuid4)
    change_id: UUID = field(default_factory=uuid4)
    action: str = ""
    actor_id: UUID = field(default_factory=uuid4)
    actor_name: str = ""
    details: dict = field(default_factory=dict)
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChangeRequest:
    """A change request for configuration changes."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    change_type: ChangeType = ChangeType.SYSTEM_CONFIG
    status: ChangeStatus = ChangeStatus.DRAFT
    requester_id: UUID = field(default_factory=uuid4)
    requester_name: str = ""
    config_key: str = ""
    previous_value: Optional[ConfigValue] = None
    new_value: Optional[ConfigValue] = None
    justification: str = ""
    environment: str = "production"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    approvals: list[ChangeApproval] = field(default_factory=list)
    impact_assessment: Optional[ImpactAssessment] = None
    audit_entries: list[ChangeAuditEntry] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    related_ticket_id: Optional[UUID] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ApprovalPolicy:
    """Policy for change approvals."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    change_type: ChangeType = ChangeType.SYSTEM_CONFIG
    risk_levels: list[ChangeRisk] = field(default_factory=list)
    required_approvers: int = 1
    approver_roles: list[str] = field(default_factory=list)
    requires_impact_assessment: bool = True
    auto_approve_low_risk: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class ConfigSnapshot:
    """Snapshot of configuration state."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    configs: dict[str, ConfigValue] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID = field(default_factory=uuid4)
    environment: str = "production"


class ChangeControlService:
    """Service for managing configuration change control.

    Provides formal change request workflow with approvals,
    impact assessment, audit logging, and rollback capabilities.
    """

    def __init__(self) -> None:
        """Initialize the change control service."""
        self._changes: dict[UUID, ChangeRequest] = {}
        self._policies: dict[UUID, ApprovalPolicy] = {}
        self._snapshots: dict[UUID, ConfigSnapshot] = {}
        self._current_config: dict[str, ConfigValue] = {}
        self._setup_default_policies()

    def _setup_default_policies(self) -> None:
        """Set up default approval policies."""
        policies = [
            ApprovalPolicy(
                name="Threshold Changes",
                description="Policy for threshold modifications",
                change_type=ChangeType.THRESHOLD,
                risk_levels=[ChangeRisk.LOW, ChangeRisk.MEDIUM, ChangeRisk.HIGH, ChangeRisk.CRITICAL],
                required_approvers=1,
                approver_roles=["GM", "Admin"],
                requires_impact_assessment=True,
            ),
            ApprovalPolicy(
                name="Margin Floor Changes",
                description="Policy for margin floor modifications",
                change_type=ChangeType.MARGIN_FLOOR,
                risk_levels=[ChangeRisk.LOW, ChangeRisk.MEDIUM, ChangeRisk.HIGH, ChangeRisk.CRITICAL],
                required_approvers=2,
                approver_roles=["GM", "Finance"],
                requires_impact_assessment=True,
            ),
            ApprovalPolicy(
                name="Pipeline Stage Changes",
                description="Policy for pipeline stage modifications",
                change_type=ChangeType.PIPELINE_STAGE,
                risk_levels=[ChangeRisk.LOW, ChangeRisk.MEDIUM, ChangeRisk.HIGH, ChangeRisk.CRITICAL],
                required_approvers=1,
                approver_roles=["GM", "Admin"],
                requires_impact_assessment=True,
            ),
            ApprovalPolicy(
                name="Template Changes",
                description="Policy for template modifications",
                change_type=ChangeType.TEMPLATE,
                risk_levels=[ChangeRisk.LOW, ChangeRisk.MEDIUM],
                required_approvers=1,
                approver_roles=["GM", "Admin"],
                requires_impact_assessment=False,
                auto_approve_low_risk=True,
            ),
            ApprovalPolicy(
                name="Critical System Changes",
                description="Policy for critical system modifications",
                change_type=ChangeType.SYSTEM_CONFIG,
                risk_levels=[ChangeRisk.HIGH, ChangeRisk.CRITICAL],
                required_approvers=2,
                approver_roles=["Admin"],
                requires_impact_assessment=True,
            ),
        ]

        for policy in policies:
            self._policies[policy.id] = policy

    # --- Change Request Management ---

    def create_change_request(
        self,
        title: str,
        description: str,
        change_type: ChangeType,
        config_key: str,
        new_value: Any,
        requester_id: UUID,
        requester_name: str = "",
        justification: str = "",
        environment: str = "production",
        tags: Optional[list[str]] = None,
        related_ticket_id: Optional[UUID] = None,
    ) -> ChangeRequest:
        """Create a new change request.

        Args:
            title: Change title
            description: Detailed description
            change_type: Type of change
            config_key: Configuration key to change
            new_value: New value for the configuration
            requester_id: ID of requester
            requester_name: Name of requester
            justification: Business justification
            environment: Target environment
            tags: Optional tags
            related_ticket_id: Related support ticket

        Returns:
            Created change request
        """
        # Capture previous value if exists
        previous_config = self._current_config.get(config_key)
        previous_value = None
        if previous_config:
            previous_value = ConfigValue(
                key=config_key,
                value=previous_config.value,
                value_type=previous_config.value_type,
                description=previous_config.description,
            )

        new_config_value = ConfigValue(
            key=config_key,
            value=new_value,
            value_type=type(new_value).__name__,
        )

        change = ChangeRequest(
            title=title,
            description=description,
            change_type=change_type,
            requester_id=requester_id,
            requester_name=requester_name,
            config_key=config_key,
            previous_value=previous_value,
            new_value=new_config_value,
            justification=justification,
            environment=environment,
            tags=tags or [],
            related_ticket_id=related_ticket_id,
        )

        # Add creation audit entry
        self._add_audit_entry(
            change,
            "created",
            requester_id,
            requester_name,
            {"title": title, "change_type": change_type.value},
        )

        self._changes[change.id] = change
        return change

    def get_change_request(self, change_id: UUID) -> Optional[ChangeRequest]:
        """Get a change request by ID."""
        return self._changes.get(change_id)

    def get_change_requests(
        self,
        status: Optional[ChangeStatus] = None,
        change_type: Optional[ChangeType] = None,
        requester_id: Optional[UUID] = None,
        environment: Optional[str] = None,
    ) -> list[ChangeRequest]:
        """Get change requests with optional filters."""
        changes = list(self._changes.values())

        if status:
            changes = [c for c in changes if c.status == status]
        if change_type:
            changes = [c for c in changes if c.change_type == change_type]
        if requester_id:
            changes = [c for c in changes if c.requester_id == requester_id]
        if environment:
            changes = [c for c in changes if c.environment == environment]

        return sorted(changes, key=lambda x: x.created_at, reverse=True)

    def update_change_request(
        self,
        change_id: UUID,
        actor_id: UUID,
        actor_name: str = "",
        title: Optional[str] = None,
        description: Optional[str] = None,
        new_value: Optional[Any] = None,
        justification: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[ChangeRequest]:
        """Update a change request (only in draft status)."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.DRAFT:
            return None

        if title is not None:
            change.title = title
        if description is not None:
            change.description = description
        if new_value is not None:
            if change.new_value:
                change.new_value.value = new_value
            else:
                change.new_value = ConfigValue(key=change.config_key, value=new_value)
        if justification is not None:
            change.justification = justification
        if tags is not None:
            change.tags = tags

        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change, "updated", actor_id, actor_name, {"fields": "updated"}
        )

        return change

    def cancel_change_request(
        self,
        change_id: UUID,
        actor_id: UUID,
        actor_name: str = "",
        reason: str = "",
    ) -> Optional[ChangeRequest]:
        """Cancel a change request."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status in [ChangeStatus.COMPLETED, ChangeStatus.ROLLED_BACK]:
            return None

        change.status = ChangeStatus.CANCELLED
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change, "cancelled", actor_id, actor_name, {"reason": reason}
        )

        return change

    # --- Workflow ---

    def submit_for_review(
        self,
        change_id: UUID,
        actor_id: UUID,
        actor_name: str = "",
    ) -> Optional[ChangeRequest]:
        """Submit a change request for review."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.DRAFT:
            return None

        # Validate required fields
        if not change.title or not change.config_key or not change.new_value:
            return None

        change.status = ChangeStatus.PENDING_REVIEW
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change, "submitted_for_review", actor_id, actor_name
        )

        return change

    def add_impact_assessment(
        self,
        change_id: UUID,
        assessor_id: UUID,
        risk_level: ChangeRisk,
        impact_level: ChangeImpact,
        affected_areas: list[str],
        affected_user_count: int = 0,
        rollback_plan: str = "",
        testing_required: bool = False,
        testing_notes: str = "",
        dependencies: Optional[list[str]] = None,
        estimated_downtime_minutes: int = 0,
    ) -> Optional[ImpactAssessment]:
        """Add impact assessment to a change request."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status not in [ChangeStatus.PENDING_REVIEW, ChangeStatus.PENDING_APPROVAL]:
            return None

        assessment = ImpactAssessment(
            change_id=change_id,
            risk_level=risk_level,
            impact_level=impact_level,
            affected_areas=affected_areas,
            affected_user_count=affected_user_count,
            rollback_plan=rollback_plan,
            testing_required=testing_required,
            testing_notes=testing_notes,
            dependencies=dependencies or [],
            estimated_downtime_minutes=estimated_downtime_minutes,
            assessed_by=assessor_id,
        )

        change.impact_assessment = assessment
        change.status = ChangeStatus.PENDING_APPROVAL
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change,
            "impact_assessed",
            assessor_id,
            "",
            {"risk_level": risk_level.value, "impact_level": impact_level.value},
        )

        return assessment

    def approve_change(
        self,
        change_id: UUID,
        approver_id: UUID,
        approver_name: str = "",
        comments: str = "",
        conditions: Optional[list[str]] = None,
    ) -> Optional[ChangeApproval]:
        """Approve a change request."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.PENDING_APPROVAL:
            return None

        # Check for required impact assessment
        policy = self._get_policy_for_change(change)
        if policy and policy.requires_impact_assessment and not change.impact_assessment:
            return None

        approval = ChangeApproval(
            change_id=change_id,
            approver_id=approver_id,
            approver_name=approver_name,
            decision=ApprovalDecision.APPROVED,
            comments=comments,
            conditions=conditions or [],
        )

        change.approvals.append(approval)
        change.updated_at = datetime.now(timezone.utc)

        # Check if enough approvals
        required = policy.required_approvers if policy else 1
        if len([a for a in change.approvals if a.decision == ApprovalDecision.APPROVED]) >= required:
            change.status = ChangeStatus.APPROVED

        self._add_audit_entry(
            change, "approved", approver_id, approver_name, {"comments": comments}
        )

        return approval

    def reject_change(
        self,
        change_id: UUID,
        approver_id: UUID,
        approver_name: str = "",
        reason: str = "",
    ) -> Optional[ChangeApproval]:
        """Reject a change request."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.PENDING_APPROVAL:
            return None

        if not reason:
            return None

        approval = ChangeApproval(
            change_id=change_id,
            approver_id=approver_id,
            approver_name=approver_name,
            decision=ApprovalDecision.REJECTED,
            comments=reason,
        )

        change.approvals.append(approval)
        change.status = ChangeStatus.REJECTED
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change, "rejected", approver_id, approver_name, {"reason": reason}
        )

        return approval

    def request_info(
        self,
        change_id: UUID,
        approver_id: UUID,
        approver_name: str = "",
        questions: str = "",
    ) -> Optional[ChangeApproval]:
        """Request more information for a change."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.PENDING_APPROVAL:
            return None

        approval = ChangeApproval(
            change_id=change_id,
            approver_id=approver_id,
            approver_name=approver_name,
            decision=ApprovalDecision.NEEDS_INFO,
            comments=questions,
        )

        change.approvals.append(approval)
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change, "info_requested", approver_id, approver_name, {"questions": questions}
        )

        return approval

    def schedule_change(
        self,
        change_id: UUID,
        scheduled_at: datetime,
        actor_id: UUID,
        actor_name: str = "",
    ) -> Optional[ChangeRequest]:
        """Schedule an approved change for implementation."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.APPROVED:
            return None

        change.status = ChangeStatus.SCHEDULED
        change.scheduled_at = scheduled_at
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change,
            "scheduled",
            actor_id,
            actor_name,
            {"scheduled_at": scheduled_at.isoformat()},
        )

        return change

    def apply_change(
        self,
        change_id: UUID,
        actor_id: UUID,
        actor_name: str = "",
    ) -> Optional[ChangeRequest]:
        """Apply an approved change."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status not in [ChangeStatus.APPROVED, ChangeStatus.SCHEDULED]:
            return None

        # Mark as in progress
        change.status = ChangeStatus.IN_PROGRESS
        change.updated_at = datetime.now(timezone.utc)

        # Apply the change
        if change.new_value:
            self._current_config[change.config_key] = change.new_value

        # Mark as completed
        change.status = ChangeStatus.COMPLETED
        change.applied_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change,
            "applied",
            actor_id,
            actor_name,
            {
                "previous_value": change.previous_value.value if change.previous_value else None,
                "new_value": change.new_value.value if change.new_value else None,
            },
            previous_value=change.previous_value.value if change.previous_value else None,
            new_value=change.new_value.value if change.new_value else None,
        )

        return change

    def rollback_change(
        self,
        change_id: UUID,
        actor_id: UUID,
        actor_name: str = "",
        reason: str = "",
    ) -> Optional[ChangeRequest]:
        """Rollback a completed change."""
        change = self._changes.get(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.COMPLETED:
            return None

        # Restore previous value
        if change.previous_value:
            self._current_config[change.config_key] = change.previous_value
        elif change.config_key in self._current_config:
            del self._current_config[change.config_key]

        change.status = ChangeStatus.ROLLED_BACK
        change.rolled_back_at = datetime.now(timezone.utc)
        change.updated_at = datetime.now(timezone.utc)

        self._add_audit_entry(
            change,
            "rolled_back",
            actor_id,
            actor_name,
            {"reason": reason},
            previous_value=change.new_value.value if change.new_value else None,
            new_value=change.previous_value.value if change.previous_value else None,
        )

        return change

    # --- Policies ---

    def create_policy(
        self,
        name: str,
        description: str,
        change_type: ChangeType,
        required_approvers: int = 1,
        approver_roles: Optional[list[str]] = None,
        risk_levels: Optional[list[ChangeRisk]] = None,
        requires_impact_assessment: bool = True,
        auto_approve_low_risk: bool = False,
    ) -> ApprovalPolicy:
        """Create a new approval policy."""
        policy = ApprovalPolicy(
            name=name,
            description=description,
            change_type=change_type,
            required_approvers=required_approvers,
            approver_roles=approver_roles or ["Admin"],
            risk_levels=risk_levels or [ChangeRisk.LOW, ChangeRisk.MEDIUM, ChangeRisk.HIGH, ChangeRisk.CRITICAL],
            requires_impact_assessment=requires_impact_assessment,
            auto_approve_low_risk=auto_approve_low_risk,
        )

        self._policies[policy.id] = policy
        return policy

    def get_policies(
        self,
        change_type: Optional[ChangeType] = None,
        active_only: bool = False,
    ) -> list[ApprovalPolicy]:
        """Get approval policies."""
        policies = list(self._policies.values())

        if change_type:
            policies = [p for p in policies if p.change_type == change_type]
        if active_only:
            policies = [p for p in policies if p.is_active]

        return policies

    def update_policy(
        self,
        policy_id: UUID,
        name: Optional[str] = None,
        required_approvers: Optional[int] = None,
        approver_roles: Optional[list[str]] = None,
        requires_impact_assessment: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[ApprovalPolicy]:
        """Update an approval policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None

        if name is not None:
            policy.name = name
        if required_approvers is not None:
            policy.required_approvers = required_approvers
        if approver_roles is not None:
            policy.approver_roles = approver_roles
        if requires_impact_assessment is not None:
            policy.requires_impact_assessment = requires_impact_assessment
        if is_active is not None:
            policy.is_active = is_active

        return policy

    def _get_policy_for_change(self, change: ChangeRequest) -> Optional[ApprovalPolicy]:
        """Get the applicable policy for a change."""
        for policy in self._policies.values():
            if policy.is_active and policy.change_type == change.change_type:
                return policy
        return None

    # --- Configuration Snapshots ---

    def create_snapshot(
        self,
        name: str,
        description: str,
        created_by: UUID,
        environment: str = "production",
    ) -> ConfigSnapshot:
        """Create a snapshot of current configuration."""
        snapshot = ConfigSnapshot(
            name=name,
            description=description,
            configs=dict(self._current_config),
            created_by=created_by,
            environment=environment,
        )

        self._snapshots[snapshot.id] = snapshot
        return snapshot

    def get_snapshots(
        self,
        environment: Optional[str] = None,
    ) -> list[ConfigSnapshot]:
        """Get configuration snapshots."""
        snapshots = list(self._snapshots.values())

        if environment:
            snapshots = [s for s in snapshots if s.environment == environment]

        return sorted(snapshots, key=lambda x: x.created_at, reverse=True)

    def restore_snapshot(
        self,
        snapshot_id: UUID,
        actor_id: UUID,
        actor_name: str = "",
    ) -> Optional[ConfigSnapshot]:
        """Restore configuration from a snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return None

        # Create change requests for each config difference
        for key, value in snapshot.configs.items():
            if key not in self._current_config or self._current_config[key].value != value.value:
                change = self.create_change_request(
                    title=f"Restore: {key}",
                    description=f"Restored from snapshot: {snapshot.name}",
                    change_type=ChangeType.SYSTEM_CONFIG,
                    config_key=key,
                    new_value=value.value,
                    requester_id=actor_id,
                    requester_name=actor_name,
                    justification=f"Snapshot restore: {snapshot.name}",
                )
                change.status = ChangeStatus.APPROVED
                self.apply_change(change.id, actor_id, actor_name)

        return snapshot

    # --- Audit ---

    def _add_audit_entry(
        self,
        change: ChangeRequest,
        action: str,
        actor_id: UUID,
        actor_name: str = "",
        details: Optional[dict] = None,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
    ) -> ChangeAuditEntry:
        """Add an audit entry to a change."""
        entry = ChangeAuditEntry(
            change_id=change.id,
            action=action,
            actor_id=actor_id,
            actor_name=actor_name,
            details=details or {},
            previous_value=previous_value,
            new_value=new_value,
        )

        change.audit_entries.append(entry)
        return entry

    def get_audit_trail(
        self,
        change_id: UUID,
    ) -> list[ChangeAuditEntry]:
        """Get audit trail for a change."""
        change = self._changes.get(change_id)
        if not change:
            return []

        return sorted(change.audit_entries, key=lambda x: x.timestamp)

    def get_all_audit_entries(
        self,
        actor_id: Optional[UUID] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[ChangeAuditEntry]:
        """Get all audit entries with optional filters."""
        entries: list[ChangeAuditEntry] = []

        for change in self._changes.values():
            entries.extend(change.audit_entries)

        if actor_id:
            entries = [e for e in entries if e.actor_id == actor_id]
        if action:
            entries = [e for e in entries if e.action == action]
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        return sorted(entries, key=lambda x: x.timestamp, reverse=True)

    # --- Reporting ---

    def get_change_summary(self, change_id: UUID) -> Optional[dict]:
        """Get a summary of a change request."""
        change = self._changes.get(change_id)
        if not change:
            return None

        approval_count = len([a for a in change.approvals if a.decision == ApprovalDecision.APPROVED])
        rejection_count = len([a for a in change.approvals if a.decision == ApprovalDecision.REJECTED])

        return {
            "id": str(change.id),
            "title": change.title,
            "status": change.status.value,
            "change_type": change.change_type.value,
            "requester": change.requester_name or str(change.requester_id),
            "config_key": change.config_key,
            "previous_value": change.previous_value.value if change.previous_value else None,
            "new_value": change.new_value.value if change.new_value else None,
            "created_at": change.created_at.isoformat(),
            "applied_at": change.applied_at.isoformat() if change.applied_at else None,
            "approval_count": approval_count,
            "rejection_count": rejection_count,
            "has_impact_assessment": change.impact_assessment is not None,
            "risk_level": change.impact_assessment.risk_level.value if change.impact_assessment else None,
            "audit_entry_count": len(change.audit_entries),
        }

    def get_statistics(self) -> dict:
        """Get change control statistics."""
        changes = list(self._changes.values())

        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}

        for change in changes:
            status = change.status.value
            by_status[status] = by_status.get(status, 0) + 1

            ctype = change.change_type.value
            by_type[ctype] = by_type.get(ctype, 0) + 1

        completed = [c for c in changes if c.status == ChangeStatus.COMPLETED]
        rolled_back = [c for c in changes if c.status == ChangeStatus.ROLLED_BACK]

        # Calculate average approval time
        approval_times: list[float] = []
        for change in completed:
            if change.approvals:
                first_approval = min(a.approved_at for a in change.approvals)
                delta = first_approval - change.created_at
                approval_times.append(delta.total_seconds() / 3600)

        avg_approval_time = sum(approval_times) / len(approval_times) if approval_times else 0

        return {
            "total_changes": len(changes),
            "completed_changes": len(completed),
            "rolled_back_changes": len(rolled_back),
            "pending_approval": len([c for c in changes if c.status == ChangeStatus.PENDING_APPROVAL]),
            "by_status": by_status,
            "by_type": by_type,
            "rollback_rate": len(rolled_back) / len(completed) * 100 if completed else 0,
            "avg_approval_time_hours": round(avg_approval_time, 2),
            "active_policies": len([p for p in self._policies.values() if p.is_active]),
            "total_snapshots": len(self._snapshots),
        }

    # --- Current Config ---

    def get_current_config(self) -> dict[str, Any]:
        """Get current configuration values."""
        return {k: v.value for k, v in self._current_config.items()}

    def set_config_value(
        self,
        key: str,
        value: Any,
        value_type: str = "string",
        description: str = "",
    ) -> ConfigValue:
        """Directly set a configuration value (for initialization)."""
        config = ConfigValue(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
        )
        self._current_config[key] = config
        return config

    def get_pending_changes(self) -> list[ChangeRequest]:
        """Get all pending changes awaiting action."""
        return [
            c for c in self._changes.values()
            if c.status in [ChangeStatus.PENDING_REVIEW, ChangeStatus.PENDING_APPROVAL]
        ]

    def get_scheduled_changes(self) -> list[ChangeRequest]:
        """Get all scheduled changes."""
        return sorted(
            [c for c in self._changes.values() if c.status == ChangeStatus.SCHEDULED],
            key=lambda x: x.scheduled_at or x.created_at,
        )

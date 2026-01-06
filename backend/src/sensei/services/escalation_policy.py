"""
Escalation Policy Engine for Sensei OS.

Implements escalation policies for:
- Aging approvals (approvals not acted on for X days)
- High-severity risks requiring attention
- Andon events needing escalation
- Stale items needing management attention

Designed to be called periodically and integrated with notifications.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import UUID


class EscalationTargetType(str, Enum):
    """Types of entities that can be escalated."""
    
    QUOTE_APPROVAL = "quote_approval"
    RISK = "risk"
    ANDON = "andon"
    TASK = "task"
    RFQ = "rfq"
    OPPORTUNITY = "opportunity"


class EscalationReason(str, Enum):
    """Reason for escalation."""
    
    # Approval-related
    APPROVAL_AGING = "approval_aging"
    APPROVAL_VALUE_THRESHOLD = "approval_value_threshold"
    
    # Risk-related
    RISK_SEVERITY_HIGH = "risk_severity_high"
    RISK_SEVERITY_CRITICAL = "risk_severity_critical"
    RISK_OVERDUE = "risk_overdue"
    RISK_UNMITIGATED = "risk_unmitigated"
    
    # Andon-related
    ANDON_SLA_BREACH = "andon_sla_breach"
    ANDON_RECURRENCE = "andon_recurrence"
    ANDON_CRITICAL = "andon_critical"
    
    # General
    OWNER_UNAVAILABLE = "owner_unavailable"
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_MISSED = "deadline_missed"
    STALE_CRITICAL = "stale_critical"


class EscalationLevel(str, Enum):
    """Level of escalation."""
    
    L1 = "l1"  # Direct supervisor/team lead
    L2 = "l2"  # Department manager
    L3 = "l3"  # Director/GM level
    L4 = "l4"  # Executive escalation


class EscalationStatus(str, Enum):
    """Status of an escalation."""
    
    PENDING = "pending"        # Escalation sent, awaiting response
    ACKNOWLEDGED = "acknowledged"  # Recipient acknowledged
    IN_PROGRESS = "in_progress"   # Being worked on
    RESOLVED = "resolved"      # Issue resolved
    DELEGATED = "delegated"    # Delegated to another person
    EXPIRED = "expired"        # Escalation expired without response
    CANCELLED = "cancelled"    # Escalation cancelled


class EscalationPriority(str, Enum):
    """Priority of escalation."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


@dataclass
class EscalationPolicy:
    """
    Definition of an escalation policy.
    
    Attributes:
        name: Unique name of the policy
        description: Human-readable description
        target_type: Type of entity this policy applies to
        enabled: Whether the policy is active
        conditions: Dict of conditions that trigger escalation
        escalation_levels: List of escalation level configurations
        notification_template: Template key for notifications
        auto_create_task: Whether to create a follow-up task
        metadata: Additional policy configuration
    """
    name: str
    description: str
    target_type: EscalationTargetType
    enabled: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)
    escalation_levels: list["EscalationLevelConfig"] = field(default_factory=list)
    notification_template: str | None = None
    auto_create_task: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationLevelConfig:
    """
    Configuration for a specific escalation level.
    
    Attributes:
        level: The escalation level
        wait_hours: Hours to wait at this level before escalating further
        escalate_to_role: Role to escalate to at this level
        escalate_to_user_id: Specific user ID (optional, overrides role)
        notification_channels: Channels to use for notification
        require_acknowledgment: Whether acknowledgment is required
        acknowledgment_timeout_hours: Hours before reminding/re-escalating
    """
    level: EscalationLevel
    wait_hours: int = 24
    escalate_to_role: str | None = None
    escalate_to_user_id: UUID | None = None
    notification_channels: list[str] = field(default_factory=lambda: ["in_app", "email"])
    require_acknowledgment: bool = True
    acknowledgment_timeout_hours: int = 4


@dataclass
class EscalationItem:
    """
    An item requiring escalation.
    
    Attributes:
        entity_id: UUID of the entity requiring escalation
        entity_type: Type of the entity
        entity_name: Display name/identifier
        reason: Why escalation is needed
        priority: Priority of the escalation
        current_level: Current escalation level
        status: Current escalation status
        owner_id: Current owner of the entity
        owner_name: Name of the owner
        escalated_to_id: Who it's escalated to
        escalated_to_name: Name of escalation recipient
        escalated_at: When escalation was initiated
        acknowledged_at: When escalation was acknowledged
        due_at: When the underlying item is due
        days_overdue: Days overdue (if applicable)
        value: Monetary value (for approvals)
        severity: Severity level (for risks)
        context: Additional context
    """
    entity_id: UUID
    entity_type: EscalationTargetType
    entity_name: str
    reason: EscalationReason
    priority: EscalationPriority
    current_level: EscalationLevel = EscalationLevel.L1
    status: EscalationStatus = EscalationStatus.PENDING
    owner_id: UUID | None = None
    owner_name: str | None = None
    escalated_to_id: UUID | None = None
    escalated_to_name: str | None = None
    escalated_at: datetime | None = None
    acknowledged_at: datetime | None = None
    due_at: datetime | None = None
    days_overdue: int = 0
    value: Decimal | None = None
    severity: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationResult:
    """
    Result of an escalation policy evaluation.
    
    Attributes:
        policy_name: Name of the policy that was evaluated
        target_type: Type of entities evaluated
        total_evaluated: Total number of entities checked
        items_escalated: Number of items that need escalation
        items: List of escalation items
        evaluated_at: When the evaluation was performed
        errors: List of any errors during evaluation
    """
    policy_name: str
    target_type: EscalationTargetType
    total_evaluated: int = 0
    items_escalated: int = 0
    items: list[EscalationItem] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    errors: list[str] = field(default_factory=list)


class EscalationPolicyService:
    """
    Service for evaluating escalation policies.
    
    Provides methods to:
    - Detect aging approvals needing escalation
    - Detect high-severity risks requiring attention
    - Detect Andon events breaching SLAs
    - Configure escalation thresholds
    - Get escalation targets based on policy
    """
    
    # Default policies
    _default_policies: dict[str, EscalationPolicy] = {}
    
    # Approval aging thresholds (hours)
    APPROVAL_ESCALATION_THRESHOLDS = {
        "l1": 24,   # 1 day to L1
        "l2": 48,   # 2 days to L2
        "l3": 72,   # 3 days to L3
        "l4": 96,   # 4 days to L4
    }
    
    # Value-based approval thresholds (requires higher-level approval)
    APPROVAL_VALUE_THRESHOLDS = {
        "l1": Decimal("0"),         # Any value
        "l2": Decimal("50000"),     # > 50K
        "l3": Decimal("100000"),    # > 100K
        "l4": Decimal("500000"),    # > 500K
    }
    
    # Risk escalation configuration
    RISK_SEVERITY_ESCALATION = {
        "critical": EscalationLevel.L3,
        "high": EscalationLevel.L2,
        "medium": EscalationLevel.L1,
        "low": None,  # No escalation for low risks
    }
    
    RISK_OVERDUE_DAYS_ESCALATION = {
        "l1": 7,    # 1 week overdue
        "l2": 14,   # 2 weeks overdue
        "l3": 30,   # 1 month overdue
    }
    
    # Andon SLA multipliers for escalation
    ANDON_SLA_MULTIPLIERS = {
        "l1": 1.5,  # 1.5x SLA
        "l2": 2.0,  # 2x SLA
        "l3": 3.0,  # 3x SLA
    }
    
    def __init__(self) -> None:
        """Initialize the escalation policy service."""
        self._custom_thresholds: dict[str, dict[str, Any]] = {}
        self._policies: dict[str, EscalationPolicy] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        """Initialize default escalation policies."""
        self._policies = {
            "approval_aging": EscalationPolicy(
                name="approval_aging",
                description="Escalate approvals that haven't been acted on",
                target_type=EscalationTargetType.QUOTE_APPROVAL,
                conditions={
                    "status": "pending",
                    "min_age_hours": 24,
                },
                escalation_levels=[
                    EscalationLevelConfig(
                        level=EscalationLevel.L1,
                        wait_hours=24,
                        escalate_to_role="team_lead",
                    ),
                    EscalationLevelConfig(
                        level=EscalationLevel.L2,
                        wait_hours=48,
                        escalate_to_role="department_manager",
                    ),
                    EscalationLevelConfig(
                        level=EscalationLevel.L3,
                        wait_hours=72,
                        escalate_to_role="general_manager",
                    ),
                ],
                auto_create_task=True,
            ),
            "approval_value": EscalationPolicy(
                name="approval_value",
                description="Escalate approvals based on value thresholds",
                target_type=EscalationTargetType.QUOTE_APPROVAL,
                conditions={
                    "status": "pending",
                    "min_value": Decimal("50000"),
                },
                escalation_levels=[
                    EscalationLevelConfig(
                        level=EscalationLevel.L2,
                        wait_hours=0,  # Immediate
                        escalate_to_role="department_manager",
                    ),
                ],
            ),
            "high_severity_risk": EscalationPolicy(
                name="high_severity_risk",
                description="Escalate high and critical severity risks",
                target_type=EscalationTargetType.RISK,
                conditions={
                    "severity": ["high", "critical"],
                    "status": ["identified", "analyzing", "mitigating"],
                },
                escalation_levels=[
                    EscalationLevelConfig(
                        level=EscalationLevel.L2,
                        wait_hours=0,
                        escalate_to_role="department_manager",
                    ),
                    EscalationLevelConfig(
                        level=EscalationLevel.L3,
                        wait_hours=48,
                        escalate_to_role="general_manager",
                    ),
                ],
                auto_create_task=True,
            ),
            "risk_overdue": EscalationPolicy(
                name="risk_overdue",
                description="Escalate risks past their target resolution date",
                target_type=EscalationTargetType.RISK,
                conditions={
                    "status": ["identified", "analyzing", "mitigating", "monitoring"],
                    "overdue": True,
                },
                escalation_levels=[
                    EscalationLevelConfig(
                        level=EscalationLevel.L1,
                        wait_hours=0,
                        escalate_to_role="team_lead",
                    ),
                    EscalationLevelConfig(
                        level=EscalationLevel.L2,
                        wait_hours=168,  # 1 week
                        escalate_to_role="department_manager",
                    ),
                ],
            ),
            "andon_sla_breach": EscalationPolicy(
                name="andon_sla_breach",
                description="Escalate Andon events breaching SLA",
                target_type=EscalationTargetType.ANDON,
                conditions={
                    "status": ["open", "acknowledged", "in_progress"],
                    "sla_breached": True,
                },
                escalation_levels=[
                    EscalationLevelConfig(
                        level=EscalationLevel.L1,
                        wait_hours=0,
                        escalate_to_role="supervisor",
                        notification_channels=["in_app", "email", "push"],
                    ),
                    EscalationLevelConfig(
                        level=EscalationLevel.L2,
                        wait_hours=1,
                        escalate_to_role="production_manager",
                        notification_channels=["in_app", "email", "push", "sms"],
                    ),
                ],
                auto_create_task=False,  # Andon has its own tracking
            ),
        }
    
    def get_policy(self, name: str) -> EscalationPolicy | None:
        """Get a specific escalation policy by name."""
        return self._policies.get(name)
    
    def get_all_policies(self) -> dict[str, EscalationPolicy]:
        """Get all configured policies."""
        return dict(self._policies)
    
    def add_policy(self, policy: EscalationPolicy) -> None:
        """Add or update an escalation policy."""
        self._policies[policy.name] = policy
    
    def remove_policy(self, name: str) -> bool:
        """Remove a policy by name. Returns True if removed."""
        if name in self._policies:
            del self._policies[name]
            return True
        return False
    
    def set_approval_threshold(
        self,
        level: EscalationLevel,
        hours: int | None = None,
        value: Decimal | None = None,
    ) -> None:
        """Update approval escalation thresholds."""
        if level.value not in self._custom_thresholds:
            self._custom_thresholds[level.value] = {}
        
        if hours is not None:
            key = f"approval_hours_{level.value}"
            self._custom_thresholds[level.value]["hours"] = hours
        
        if value is not None:
            self._custom_thresholds[level.value]["value"] = value
    
    def get_approval_thresholds(self) -> dict[str, dict[str, Any]]:
        """Get current approval escalation thresholds."""
        result = {}
        for level in EscalationLevel:
            level_key = level.value
            result[level_key] = {
                "hours": self._custom_thresholds.get(level_key, {}).get(
                    "hours",
                    self.APPROVAL_ESCALATION_THRESHOLDS.get(level_key, 24)
                ),
                "value": self._custom_thresholds.get(level_key, {}).get(
                    "value",
                    self.APPROVAL_VALUE_THRESHOLDS.get(level_key, Decimal("0"))
                ),
            }
        return result
    
    def set_risk_threshold(
        self,
        severity: str,
        escalation_level: EscalationLevel | None,
    ) -> None:
        """Update risk severity escalation level."""
        if "risk" not in self._custom_thresholds:
            self._custom_thresholds["risk"] = {}
        self._custom_thresholds["risk"][severity] = escalation_level
    
    def get_risk_thresholds(self) -> dict[str, EscalationLevel | None]:
        """Get current risk escalation thresholds."""
        base = dict(self.RISK_SEVERITY_ESCALATION)
        if "risk" in self._custom_thresholds:
            base.update(self._custom_thresholds["risk"])
        return base
    
    def detect_aging_approvals(
        self,
        approvals: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> EscalationResult:
        """
        Detect approvals that need escalation due to aging.
        
        Args:
            approvals: List of approval dicts with keys:
                - id: UUID
                - name: str (quote number/title)
                - status: str (approval_status)
                - value: Decimal (quote total)
                - requested_at: datetime
                - owner_id: UUID
                - owner_name: str
                - current_escalation_level: str | None
                - account_name: str | None
            reference_time: Time to use as "now" (default: utcnow)
        
        Returns:
            EscalationResult with items needing escalation
        """
        ref_time = reference_time or datetime.utcnow()
        result = EscalationResult(
            policy_name="approval_aging",
            target_type=EscalationTargetType.QUOTE_APPROVAL,
            total_evaluated=len(approvals),
        )
        
        thresholds = self.get_approval_thresholds()
        
        for approval in approvals:
            try:
                # Skip non-pending approvals
                status = approval.get("status", "")
                if status != "pending":
                    continue
                
                requested_at = approval.get("requested_at")
                if not requested_at:
                    continue
                
                # Handle timezone
                if requested_at.tzinfo:
                    requested_at = requested_at.replace(tzinfo=None)
                
                # Calculate age in hours
                age_delta = ref_time - requested_at
                age_hours = age_delta.total_seconds() / 3600
                
                # Determine escalation level based on age
                escalation_level = None
                for level in [EscalationLevel.L4, EscalationLevel.L3, 
                              EscalationLevel.L2, EscalationLevel.L1]:
                    threshold_hours = thresholds.get(level.value, {}).get("hours", 24)
                    if age_hours >= threshold_hours:
                        escalation_level = level
                        break
                
                if not escalation_level:
                    continue  # Not old enough for escalation
                
                # Check if already escalated to this level
                current_level = approval.get("current_escalation_level")
                if current_level:
                    try:
                        current = EscalationLevel(current_level)
                        # Skip if already at or above this level
                        level_order = [EscalationLevel.L1, EscalationLevel.L2, 
                                      EscalationLevel.L3, EscalationLevel.L4]
                        if level_order.index(current) >= level_order.index(escalation_level):
                            continue
                    except ValueError:
                        pass  # Invalid level, proceed with escalation
                
                # Determine priority based on value and age
                value = approval.get("value", Decimal("0")) or Decimal("0")
                priority = self._calculate_approval_priority(value, age_hours)
                
                # Calculate days overdue
                days_overdue = max(0, int(age_hours / 24))
                
                item = EscalationItem(
                    entity_id=approval["id"],
                    entity_type=EscalationTargetType.QUOTE_APPROVAL,
                    entity_name=approval.get("name", "Unknown"),
                    reason=EscalationReason.APPROVAL_AGING,
                    priority=priority,
                    current_level=escalation_level,
                    owner_id=approval.get("owner_id"),
                    owner_name=approval.get("owner_name"),
                    days_overdue=days_overdue,
                    value=value,
                    context={
                        "age_hours": round(age_hours, 1),
                        "account_name": approval.get("account_name"),
                        "requested_at": requested_at.isoformat(),
                    },
                )
                result.items.append(item)
                
            except Exception as e:
                result.errors.append(f"Error processing approval {approval.get('id')}: {str(e)}")
        
        result.items_escalated = len(result.items)
        return result
    
    def detect_value_based_approvals(
        self,
        approvals: list[dict[str, Any]],
    ) -> EscalationResult:
        """
        Detect approvals that need escalation based on value thresholds.
        
        High-value approvals require higher-level approval regardless of age.
        
        Args:
            approvals: List of approval dicts (same format as detect_aging_approvals)
        
        Returns:
            EscalationResult with items needing escalation
        """
        result = EscalationResult(
            policy_name="approval_value",
            target_type=EscalationTargetType.QUOTE_APPROVAL,
            total_evaluated=len(approvals),
        )
        
        thresholds = self.get_approval_thresholds()
        
        for approval in approvals:
            try:
                # Skip non-pending approvals
                status = approval.get("status", "")
                if status != "pending":
                    continue
                
                value = approval.get("value", Decimal("0")) or Decimal("0")
                
                # Determine required level based on value
                required_level = None
                for level in [EscalationLevel.L4, EscalationLevel.L3, 
                              EscalationLevel.L2, EscalationLevel.L1]:
                    threshold_value = thresholds.get(level.value, {}).get("value", Decimal("0"))
                    if value >= threshold_value:
                        required_level = level
                        break
                
                if not required_level or required_level == EscalationLevel.L1:
                    continue  # Standard approval, no escalation needed
                
                # Check if already at required level
                current_level = approval.get("current_escalation_level")
                if current_level:
                    try:
                        current = EscalationLevel(current_level)
                        level_order = [EscalationLevel.L1, EscalationLevel.L2, 
                                      EscalationLevel.L3, EscalationLevel.L4]
                        if level_order.index(current) >= level_order.index(required_level):
                            continue
                    except ValueError:
                        pass
                
                # High-value approvals are always high priority
                priority = EscalationPriority.HIGH
                if value >= self.APPROVAL_VALUE_THRESHOLDS.get("l4", Decimal("500000")):
                    priority = EscalationPriority.CRITICAL
                
                item = EscalationItem(
                    entity_id=approval["id"],
                    entity_type=EscalationTargetType.QUOTE_APPROVAL,
                    entity_name=approval.get("name", "Unknown"),
                    reason=EscalationReason.APPROVAL_VALUE_THRESHOLD,
                    priority=priority,
                    current_level=required_level,
                    owner_id=approval.get("owner_id"),
                    owner_name=approval.get("owner_name"),
                    value=value,
                    context={
                        "threshold_level": required_level.value,
                        "account_name": approval.get("account_name"),
                    },
                )
                result.items.append(item)
                
            except Exception as e:
                result.errors.append(f"Error processing approval {approval.get('id')}: {str(e)}")
        
        result.items_escalated = len(result.items)
        return result
    
    def detect_high_severity_risks(
        self,
        risks: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> EscalationResult:
        """
        Detect high-severity risks needing escalation.
        
        Args:
            risks: List of risk dicts with keys:
                - id: UUID
                - risk_number: str
                - title: str
                - status: str
                - risk_level: str (low/medium/high/critical)
                - inherent_risk_score: int
                - residual_risk_score: int | None
                - risk_owner_id: UUID | None
                - risk_owner_name: str | None
                - target_resolution_date: datetime | None
                - identified_date: datetime
                - category: str
                - current_escalation_level: str | None
            reference_time: Time to use as "now" (default: utcnow)
        
        Returns:
            EscalationResult with items needing escalation
        """
        ref_time = reference_time or datetime.utcnow()
        result = EscalationResult(
            policy_name="high_severity_risk",
            target_type=EscalationTargetType.RISK,
            total_evaluated=len(risks),
        )
        
        risk_thresholds = self.get_risk_thresholds()
        
        for risk in risks:
            try:
                # Skip closed/accepted risks
                status = risk.get("status", "")
                if status in ("closed", "accepted", "occurred"):
                    continue
                
                risk_level = risk.get("risk_level", "medium")
                required_level = risk_thresholds.get(risk_level)
                
                if not required_level:
                    continue  # No escalation for this severity
                
                # Check if already escalated to this level
                current_level = risk.get("current_escalation_level")
                if current_level:
                    try:
                        current = EscalationLevel(current_level)
                        level_order = [EscalationLevel.L1, EscalationLevel.L2, 
                                      EscalationLevel.L3, EscalationLevel.L4]
                        if level_order.index(current) >= level_order.index(required_level):
                            continue
                    except ValueError:
                        pass
                
                # Determine reason and priority
                if risk_level == "critical":
                    reason = EscalationReason.RISK_SEVERITY_CRITICAL
                    priority = EscalationPriority.CRITICAL
                else:
                    reason = EscalationReason.RISK_SEVERITY_HIGH
                    priority = EscalationPriority.HIGH
                
                # Check for overdue
                target_date = risk.get("target_resolution_date")
                days_overdue = 0
                if target_date:
                    target_date_naive = target_date.replace(tzinfo=None) if target_date.tzinfo else target_date
                    if ref_time > target_date_naive:
                        days_overdue = (ref_time - target_date_naive).days
                        reason = EscalationReason.RISK_OVERDUE
                
                # Calculate risk score for context
                risk_score = risk.get("residual_risk_score") or risk.get("inherent_risk_score", 0)
                
                item = EscalationItem(
                    entity_id=risk["id"],
                    entity_type=EscalationTargetType.RISK,
                    entity_name=f"{risk.get('risk_number', 'Unknown')}: {risk.get('title', '')}",
                    reason=reason,
                    priority=priority,
                    current_level=required_level,
                    owner_id=risk.get("risk_owner_id"),
                    owner_name=risk.get("risk_owner_name"),
                    days_overdue=days_overdue,
                    severity=risk_level,
                    context={
                        "category": risk.get("category"),
                        "risk_score": risk_score,
                        "status": status,
                        "target_resolution_date": target_date.isoformat() if target_date else None,
                        "identified_date": risk.get("identified_date").isoformat() 
                            if risk.get("identified_date") else None,
                    },
                )
                result.items.append(item)
                
            except Exception as e:
                result.errors.append(f"Error processing risk {risk.get('id')}: {str(e)}")
        
        result.items_escalated = len(result.items)
        return result
    
    def detect_overdue_risks(
        self,
        risks: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> EscalationResult:
        """
        Detect risks that are past their target resolution date.
        
        Args:
            risks: List of risk dicts (same format as detect_high_severity_risks)
            reference_time: Time to use as "now" (default: utcnow)
        
        Returns:
            EscalationResult with overdue risks
        """
        ref_time = reference_time or datetime.utcnow()
        result = EscalationResult(
            policy_name="risk_overdue",
            target_type=EscalationTargetType.RISK,
            total_evaluated=len(risks),
        )
        
        for risk in risks:
            try:
                # Skip closed/accepted risks
                status = risk.get("status", "")
                if status in ("closed", "accepted", "occurred"):
                    continue
                
                target_date = risk.get("target_resolution_date")
                if not target_date:
                    continue
                
                # Handle timezone
                target_date_naive = target_date.replace(tzinfo=None) if target_date.tzinfo else target_date
                
                if ref_time <= target_date_naive:
                    continue  # Not overdue
                
                days_overdue = (ref_time - target_date_naive).days
                
                # Determine escalation level based on days overdue
                escalation_level = None
                for level in [EscalationLevel.L3, EscalationLevel.L2, EscalationLevel.L1]:
                    threshold_days = self.RISK_OVERDUE_DAYS_ESCALATION.get(level.value, 7)
                    if days_overdue >= threshold_days:
                        escalation_level = level
                        break
                
                if not escalation_level:
                    continue  # Not overdue enough
                
                # Check if already escalated to this level
                current_level = risk.get("current_escalation_level")
                if current_level:
                    try:
                        current = EscalationLevel(current_level)
                        level_order = [EscalationLevel.L1, EscalationLevel.L2, 
                                      EscalationLevel.L3, EscalationLevel.L4]
                        if level_order.index(current) >= level_order.index(escalation_level):
                            continue
                    except ValueError:
                        pass
                
                # Priority based on days overdue
                if days_overdue >= 30:
                    priority = EscalationPriority.CRITICAL
                elif days_overdue >= 14:
                    priority = EscalationPriority.HIGH
                elif days_overdue >= 7:
                    priority = EscalationPriority.NORMAL
                else:
                    priority = EscalationPriority.LOW
                
                item = EscalationItem(
                    entity_id=risk["id"],
                    entity_type=EscalationTargetType.RISK,
                    entity_name=f"{risk.get('risk_number', 'Unknown')}: {risk.get('title', '')}",
                    reason=EscalationReason.RISK_OVERDUE,
                    priority=priority,
                    current_level=escalation_level,
                    owner_id=risk.get("risk_owner_id"),
                    owner_name=risk.get("risk_owner_name"),
                    due_at=target_date,
                    days_overdue=days_overdue,
                    severity=risk.get("risk_level"),
                    context={
                        "category": risk.get("category"),
                        "status": status,
                        "target_resolution_date": target_date.isoformat(),
                    },
                )
                result.items.append(item)
                
            except Exception as e:
                result.errors.append(f"Error processing risk {risk.get('id')}: {str(e)}")
        
        result.items_escalated = len(result.items)
        return result
    
    def detect_andon_sla_breaches(
        self,
        andons: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> EscalationResult:
        """
        Detect Andon events that have breached SLA.
        
        Args:
            andons: List of Andon dicts with keys:
                - id: int
                - andon_number: str
                - description: str
                - status: str
                - severity: str (red/yellow/green)
                - reported_at: datetime
                - acknowledged_at: datetime | None
                - station_id: int
                - station_name: str
                - red_ack_minutes: int
                - yellow_ack_minutes: int
                - current_escalation_level: str | None
                - assigned_to_id: UUID | None
                - assigned_to_name: str | None
            reference_time: Time to use as "now" (default: utcnow)
        
        Returns:
            EscalationResult with SLA-breaching Andons
        """
        ref_time = reference_time or datetime.utcnow()
        result = EscalationResult(
            policy_name="andon_sla_breach",
            target_type=EscalationTargetType.ANDON,
            total_evaluated=len(andons),
        )
        
        for andon in andons:
            try:
                # Skip resolved Andons
                status = andon.get("status", "")
                if status == "resolved":
                    continue
                
                reported_at = andon.get("reported_at")
                if not reported_at:
                    continue
                
                # Handle timezone
                reported_at_naive = reported_at.replace(tzinfo=None) if reported_at.tzinfo else reported_at
                
                # Calculate elapsed time
                elapsed_minutes = (ref_time - reported_at_naive).total_seconds() / 60
                
                # Get SLA based on severity
                severity = andon.get("severity", "yellow")
                if severity == "red":
                    sla_minutes = andon.get("red_ack_minutes", 5)
                else:
                    sla_minutes = andon.get("yellow_ack_minutes", 15)
                
                # Check if SLA breached
                if elapsed_minutes <= sla_minutes:
                    continue  # Within SLA
                
                # Determine escalation level based on SLA multiple
                sla_multiple = elapsed_minutes / sla_minutes if sla_minutes > 0 else 10
                
                escalation_level = EscalationLevel.L1
                if sla_multiple >= self.ANDON_SLA_MULTIPLIERS.get("l3", 3.0):
                    escalation_level = EscalationLevel.L3
                elif sla_multiple >= self.ANDON_SLA_MULTIPLIERS.get("l2", 2.0):
                    escalation_level = EscalationLevel.L2
                elif sla_multiple >= self.ANDON_SLA_MULTIPLIERS.get("l1", 1.5):
                    escalation_level = EscalationLevel.L1
                else:
                    continue  # SLA breached but not enough for escalation
                
                # Check if already escalated to this level
                current_level = andon.get("current_escalation_level")
                if current_level:
                    try:
                        current = EscalationLevel(current_level)
                        level_order = [EscalationLevel.L1, EscalationLevel.L2, 
                                      EscalationLevel.L3, EscalationLevel.L4]
                        if level_order.index(current) >= level_order.index(escalation_level):
                            continue
                    except ValueError:
                        pass
                
                # Priority based on severity and SLA breach
                if severity == "red":
                    priority = EscalationPriority.CRITICAL if sla_multiple >= 2 else EscalationPriority.URGENT
                else:
                    priority = EscalationPriority.HIGH if sla_multiple >= 2 else EscalationPriority.NORMAL
                
                item = EscalationItem(
                    entity_id=UUID(str(andon["id"]).zfill(32)[:32]) if isinstance(andon["id"], int) 
                        else andon["id"],
                    entity_type=EscalationTargetType.ANDON,
                    entity_name=f"{andon.get('andon_number', 'Unknown')}: {andon.get('description', '')[:50]}",
                    reason=EscalationReason.ANDON_SLA_BREACH,
                    priority=priority,
                    current_level=escalation_level,
                    owner_id=andon.get("assigned_to_id"),
                    owner_name=andon.get("assigned_to_name"),
                    severity=severity,
                    context={
                        "station_id": andon.get("station_id"),
                        "station_name": andon.get("station_name"),
                        "sla_minutes": sla_minutes,
                        "elapsed_minutes": round(elapsed_minutes, 1),
                        "sla_multiple": round(sla_multiple, 2),
                        "acknowledged": andon.get("acknowledged_at") is not None,
                        "reported_at": reported_at.isoformat(),
                    },
                )
                result.items.append(item)
                
            except Exception as e:
                result.errors.append(f"Error processing andon {andon.get('id')}: {str(e)}")
        
        result.items_escalated = len(result.items)
        return result
    
    def _calculate_approval_priority(
        self,
        value: Decimal,
        age_hours: float,
    ) -> EscalationPriority:
        """Calculate priority based on value and age."""
        # Value-based priority
        if value >= Decimal("500000"):
            base_priority = 4  # Critical
        elif value >= Decimal("100000"):
            base_priority = 3  # High
        elif value >= Decimal("50000"):
            base_priority = 2  # Normal
        else:
            base_priority = 1  # Low
        
        # Age modifier
        if age_hours >= 96:  # 4+ days
            age_modifier = 2
        elif age_hours >= 48:  # 2+ days
            age_modifier = 1
        else:
            age_modifier = 0
        
        final = min(base_priority + age_modifier, 5)
        
        priority_map = {
            1: EscalationPriority.LOW,
            2: EscalationPriority.NORMAL,
            3: EscalationPriority.HIGH,
            4: EscalationPriority.URGENT,
            5: EscalationPriority.CRITICAL,
        }
        
        return priority_map.get(final, EscalationPriority.NORMAL)
    
    def get_escalation_target_role(
        self,
        level: EscalationLevel,
        target_type: EscalationTargetType,
    ) -> str:
        """Get the role to escalate to for a given level and target type."""
        policy_name = None
        if target_type == EscalationTargetType.QUOTE_APPROVAL:
            policy_name = "approval_aging"
        elif target_type == EscalationTargetType.RISK:
            policy_name = "high_severity_risk"
        elif target_type == EscalationTargetType.ANDON:
            policy_name = "andon_sla_breach"
        
        if policy_name and policy_name in self._policies:
            policy = self._policies[policy_name]
            for level_config in policy.escalation_levels:
                if level_config.level == level:
                    return level_config.escalate_to_role or "supervisor"
        
        # Default role mapping
        default_roles = {
            EscalationLevel.L1: "team_lead",
            EscalationLevel.L2: "department_manager",
            EscalationLevel.L3: "general_manager",
            EscalationLevel.L4: "executive",
        }
        return default_roles.get(level, "supervisor")


class EscalationJobRunner:
    """
    Async job runner for escalation policy evaluation.
    
    Runs all configured policies and aggregates results.
    Supports callbacks for creating notifications and tasks.
    """
    
    def __init__(
        self,
        service: EscalationPolicyService | None = None,
        on_escalation: Callable[[EscalationItem], Coroutine[Any, Any, None]] | None = None,
        on_notification_needed: Callable[[EscalationItem, str], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """
        Initialize the job runner.
        
        Args:
            service: EscalationPolicyService instance (creates default if not provided)
            on_escalation: Async callback for each escalation item
            on_notification_needed: Async callback for sending notifications
        """
        self.service = service or EscalationPolicyService()
        self.on_escalation = on_escalation
        self.on_notification_needed = on_notification_needed
    
    async def run_approval_escalation(
        self,
        approvals: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> dict[str, EscalationResult]:
        """
        Run all approval-related escalation policies.
        
        Returns dict with policy names as keys and results as values.
        """
        results = {}
        
        # Aging escalation
        aging_result = self.service.detect_aging_approvals(approvals, reference_time)
        results["approval_aging"] = aging_result
        
        # Value-based escalation
        value_result = self.service.detect_value_based_approvals(approvals)
        results["approval_value"] = value_result
        
        # Trigger callbacks
        for result in results.values():
            for item in result.items:
                if self.on_escalation:
                    await self.on_escalation(item)
                if self.on_notification_needed:
                    template = f"escalation_{item.reason.value}"
                    await self.on_notification_needed(item, template)
        
        return results
    
    async def run_risk_escalation(
        self,
        risks: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> dict[str, EscalationResult]:
        """
        Run all risk-related escalation policies.
        
        Returns dict with policy names as keys and results as values.
        """
        results = {}
        
        # High severity escalation
        severity_result = self.service.detect_high_severity_risks(risks, reference_time)
        results["high_severity_risk"] = severity_result
        
        # Overdue escalation
        overdue_result = self.service.detect_overdue_risks(risks, reference_time)
        results["risk_overdue"] = overdue_result
        
        # Trigger callbacks
        for result in results.values():
            for item in result.items:
                if self.on_escalation:
                    await self.on_escalation(item)
                if self.on_notification_needed:
                    template = f"escalation_{item.reason.value}"
                    await self.on_notification_needed(item, template)
        
        return results
    
    async def run_andon_escalation(
        self,
        andons: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> dict[str, EscalationResult]:
        """
        Run Andon SLA breach escalation policy.
        
        Returns dict with policy name as key and result as value.
        """
        results = {}
        
        sla_result = self.service.detect_andon_sla_breaches(andons, reference_time)
        results["andon_sla_breach"] = sla_result
        
        # Trigger callbacks
        for item in sla_result.items:
            if self.on_escalation:
                await self.on_escalation(item)
            if self.on_notification_needed:
                template = "escalation_andon_sla"
                await self.on_notification_needed(item, template)
        
        return results
    
    async def run_full_escalation_scan(
        self,
        approvals: list[dict[str, Any]] | None = None,
        risks: list[dict[str, Any]] | None = None,
        andons: list[dict[str, Any]] | None = None,
        reference_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Run all escalation policies across all entity types.
        
        Args:
            approvals: List of approvals to check
            risks: List of risks to check
            andons: List of Andons to check
            reference_time: Reference time for calculations
        
        Returns:
            Summary dict with results from all policies
        """
        all_results: dict[str, EscalationResult] = {}
        
        if approvals is not None:
            approval_results = await self.run_approval_escalation(approvals, reference_time)
            all_results.update(approval_results)
        
        if risks is not None:
            risk_results = await self.run_risk_escalation(risks, reference_time)
            all_results.update(risk_results)
        
        if andons is not None:
            andon_results = await self.run_andon_escalation(andons, reference_time)
            all_results.update(andon_results)
        
        # Build summary
        total_evaluated = sum(r.total_evaluated for r in all_results.values())
        total_escalated = sum(r.items_escalated for r in all_results.values())
        all_errors = []
        for r in all_results.values():
            all_errors.extend(r.errors)
        
        return {
            "scan_time": (reference_time or datetime.utcnow()).isoformat(),
            "total_evaluated": total_evaluated,
            "total_escalated": total_escalated,
            "by_policy": {
                name: {
                    "total_evaluated": result.total_evaluated,
                    "items_escalated": result.items_escalated,
                    "items": result.items,
                }
                for name, result in all_results.items()
            },
            "errors": all_errors,
        }
    
    def get_escalation_summary(
        self,
        results: dict[str, EscalationResult],
    ) -> dict[str, Any]:
        """Generate a summary of escalation results."""
        summary = {
            "total_policies_run": len(results),
            "total_evaluated": 0,
            "total_escalated": 0,
            "by_priority": {p.value: 0 for p in EscalationPriority},
            "by_level": {l.value: 0 for l in EscalationLevel},
            "by_type": {t.value: 0 for t in EscalationTargetType},
            "errors": [],
        }
        
        for result in results.values():
            summary["total_evaluated"] += result.total_evaluated
            summary["total_escalated"] += result.items_escalated
            summary["errors"].extend(result.errors)
            
            for item in result.items:
                summary["by_priority"][item.priority.value] += 1
                summary["by_level"][item.current_level.value] += 1
                summary["by_type"][item.entity_type.value] += 1
        
        return summary

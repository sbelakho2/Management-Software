"""Incident Flow Service.

Defines severity levels, on-call schedules, escalation paths,
and incident management workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, time
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class IncidentSeverity(Enum):
    """Incident severity levels."""

    SEV1 = "sev1"  # Critical - Complete outage, data loss
    SEV2 = "sev2"  # Major - Significant degradation
    SEV3 = "sev3"  # Moderate - Partial impact
    SEV4 = "sev4"  # Low - Minor issues
    SEV5 = "sev5"  # Informational - No immediate impact


class IncidentStatus(Enum):
    """Incident lifecycle status."""

    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentCategory(Enum):
    """Categories of incidents."""

    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATA = "data"
    INTEGRATION = "integration"
    BUSINESS = "business"


class NotificationChannel(Enum):
    """Notification channels for incidents."""

    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    PHONE_CALL = "phone_call"


class EscalationTrigger(Enum):
    """Triggers for escalation."""

    TIME_ELAPSED = "time_elapsed"
    NO_ACKNOWLEDGEMENT = "no_acknowledgement"
    NO_PROGRESS = "no_progress"
    SEVERITY_UPGRADE = "severity_upgrade"
    MANUAL = "manual"


@dataclass
class SeverityConfig:
    """Configuration for a severity level."""

    severity: IncidentSeverity
    name: str
    description: str
    response_time_minutes: int
    resolution_target_hours: int
    notification_channels: list[NotificationChannel]
    auto_escalate_after_minutes: int
    requires_postmortem: bool = False
    wake_on_call: bool = False
    customer_communication: bool = False


@dataclass
class OnCallPerson:
    """A person in the on-call rotation."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    slack_handle: str = ""
    timezone: str = "UTC"


@dataclass
class OnCallSchedule:
    """An on-call schedule for a team."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    team: str = ""
    rotation_type: str = "weekly"  # weekly, daily, custom
    rotation_members: list[OnCallPerson] = field(default_factory=list)
    current_index: int = 0
    rotation_start_day: int = 0  # 0=Monday for weekly
    rotation_start_time: str = "09:00"
    escalation_timeout_minutes: int = 15
    backup_schedule_id: Optional[str] = None


@dataclass
class EscalationLevel:
    """A level in the escalation chain."""

    level: int = 1
    name: str = ""
    responders: list[OnCallPerson] = field(default_factory=list)
    schedule_id: Optional[str] = None
    timeout_minutes: int = 15
    notification_channels: list[NotificationChannel] = field(default_factory=list)


@dataclass
class EscalationPolicy:
    """A complete escalation policy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    levels: list[EscalationLevel] = field(default_factory=list)
    repeat_after_level: int = 0  # 0 = don't repeat
    max_escalations: int = 3
    is_active: bool = True


@dataclass
class Incident:
    """An incident record."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    severity: IncidentSeverity = IncidentSeverity.SEV3
    status: IncidentStatus = IncidentStatus.DETECTED
    category: IncidentCategory = IncidentCategory.APPLICATION
    affected_services: list[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    escalation_level: int = 1
    escalation_policy_id: Optional[str] = None
    timeline: list[dict] = field(default_factory=list)
    root_cause: str = ""
    resolution: str = ""
    postmortem_url: str = ""
    external_ticket_id: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class IncidentNotification:
    """A notification sent for an incident."""

    id: str = field(default_factory=lambda: str(uuid4()))
    incident_id: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    recipient: str = ""
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    message: str = ""


@dataclass
class IncidentMetrics:
    """Metrics for incident management."""

    total_incidents: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    mean_time_to_acknowledge_minutes: float = 0.0
    mean_time_to_resolve_hours: float = 0.0
    sla_met_percentage: float = 0.0


# Default severity configurations
SEVERITY_CONFIGS: dict[IncidentSeverity, SeverityConfig] = {
    IncidentSeverity.SEV1: SeverityConfig(
        severity=IncidentSeverity.SEV1,
        name="Critical",
        description="Complete service outage or data loss affecting all users",
        response_time_minutes=5,
        resolution_target_hours=1,
        notification_channels=[
            NotificationChannel.PAGERDUTY,
            NotificationChannel.PHONE_CALL,
            NotificationChannel.SLACK,
        ],
        auto_escalate_after_minutes=5,
        requires_postmortem=True,
        wake_on_call=True,
        customer_communication=True,
    ),
    IncidentSeverity.SEV2: SeverityConfig(
        severity=IncidentSeverity.SEV2,
        name="Major",
        description="Significant service degradation affecting many users",
        response_time_minutes=15,
        resolution_target_hours=4,
        notification_channels=[
            NotificationChannel.PAGERDUTY,
            NotificationChannel.SLACK,
        ],
        auto_escalate_after_minutes=15,
        requires_postmortem=True,
        wake_on_call=True,
        customer_communication=True,
    ),
    IncidentSeverity.SEV3: SeverityConfig(
        severity=IncidentSeverity.SEV3,
        name="Moderate",
        description="Partial service impact, workaround available",
        response_time_minutes=30,
        resolution_target_hours=8,
        notification_channels=[
            NotificationChannel.SLACK,
            NotificationChannel.EMAIL,
        ],
        auto_escalate_after_minutes=30,
        requires_postmortem=False,
        wake_on_call=False,
    ),
    IncidentSeverity.SEV4: SeverityConfig(
        severity=IncidentSeverity.SEV4,
        name="Low",
        description="Minor issue with limited impact",
        response_time_minutes=60,
        resolution_target_hours=24,
        notification_channels=[
            NotificationChannel.SLACK,
            NotificationChannel.EMAIL,
        ],
        auto_escalate_after_minutes=60,
    ),
    IncidentSeverity.SEV5: SeverityConfig(
        severity=IncidentSeverity.SEV5,
        name="Informational",
        description="No immediate impact, awareness only",
        response_time_minutes=480,  # 8 hours
        resolution_target_hours=72,
        notification_channels=[NotificationChannel.EMAIL],
        auto_escalate_after_minutes=240,
    ),
}


class IncidentFlowService:
    """Service for managing incident workflows."""

    def __init__(self) -> None:
        """Initialize the incident flow service."""
        self._incidents: dict[str, Incident] = {}
        self._schedules: dict[str, OnCallSchedule] = {}
        self._policies: dict[str, EscalationPolicy] = {}
        self._notifications: list[IncidentNotification] = []
        self._severity_configs = dict(SEVERITY_CONFIGS)
        self._setup_default_policies()

    def _setup_default_policies(self) -> None:
        """Set up default escalation policies."""
        # Default policy
        default_policy = EscalationPolicy(
            name="Default Escalation",
            description="Standard escalation for all incidents",
            levels=[
                EscalationLevel(
                    level=1,
                    name="Primary On-Call",
                    timeout_minutes=15,
                    notification_channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
                ),
                EscalationLevel(
                    level=2,
                    name="Secondary On-Call",
                    timeout_minutes=15,
                    notification_channels=[NotificationChannel.PAGERDUTY, NotificationChannel.SLACK],
                ),
                EscalationLevel(
                    level=3,
                    name="Team Lead",
                    timeout_minutes=30,
                    notification_channels=[
                        NotificationChannel.PHONE_CALL,
                        NotificationChannel.PAGERDUTY,
                    ],
                ),
            ],
            repeat_after_level=3,
            max_escalations=5,
        )
        self._policies[default_policy.id] = default_policy

    # --- Severity Configuration ---

    def get_severity_config(self, severity: IncidentSeverity) -> SeverityConfig:
        """Get configuration for a severity level."""
        return self._severity_configs[severity]

    def get_all_severity_configs(self) -> list[SeverityConfig]:
        """Get all severity configurations."""
        return list(self._severity_configs.values())

    def update_severity_config(
        self,
        severity: IncidentSeverity,
        response_time_minutes: Optional[int] = None,
        resolution_target_hours: Optional[int] = None,
        auto_escalate_after_minutes: Optional[int] = None,
    ) -> SeverityConfig:
        """Update a severity configuration."""
        config = self._severity_configs[severity]

        if response_time_minutes is not None:
            config.response_time_minutes = response_time_minutes
        if resolution_target_hours is not None:
            config.resolution_target_hours = resolution_target_hours
        if auto_escalate_after_minutes is not None:
            config.auto_escalate_after_minutes = auto_escalate_after_minutes

        return config

    # --- On-Call Schedule Management ---

    def create_schedule(
        self,
        name: str,
        team: str,
        rotation_type: str = "weekly",
        members: Optional[list[OnCallPerson]] = None,
    ) -> OnCallSchedule:
        """Create an on-call schedule."""
        schedule = OnCallSchedule(
            name=name,
            team=team,
            rotation_type=rotation_type,
            rotation_members=members or [],
        )
        self._schedules[schedule.id] = schedule
        return schedule

    def get_schedule(self, schedule_id: str) -> Optional[OnCallSchedule]:
        """Get a schedule by ID."""
        return self._schedules.get(schedule_id)

    def get_all_schedules(self) -> list[OnCallSchedule]:
        """Get all schedules."""
        return list(self._schedules.values())

    def get_schedules_by_team(self, team: str) -> list[OnCallSchedule]:
        """Get schedules for a team."""
        return [s for s in self._schedules.values() if s.team == team]

    def add_member_to_schedule(
        self,
        schedule_id: str,
        member: OnCallPerson,
    ) -> Optional[OnCallSchedule]:
        """Add a member to a schedule."""
        schedule = self._schedules.get(schedule_id)
        if schedule:
            schedule.rotation_members.append(member)
        return schedule

    def remove_member_from_schedule(
        self,
        schedule_id: str,
        user_id: str,
    ) -> Optional[OnCallSchedule]:
        """Remove a member from a schedule."""
        schedule = self._schedules.get(schedule_id)
        if schedule:
            schedule.rotation_members = [
                m for m in schedule.rotation_members if m.user_id != user_id
            ]
        return schedule

    def get_current_on_call(self, schedule_id: str) -> Optional[OnCallPerson]:
        """Get the current on-call person for a schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule or not schedule.rotation_members:
            return None
        return schedule.rotation_members[schedule.current_index % len(schedule.rotation_members)]

    def rotate_schedule(self, schedule_id: str) -> Optional[OnCallPerson]:
        """Rotate to the next person in the schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule or not schedule.rotation_members:
            return None

        schedule.current_index = (schedule.current_index + 1) % len(schedule.rotation_members)
        return self.get_current_on_call(schedule_id)

    # --- Escalation Policy Management ---

    def create_policy(
        self,
        name: str,
        description: str = "",
        levels: Optional[list[EscalationLevel]] = None,
    ) -> EscalationPolicy:
        """Create an escalation policy."""
        policy = EscalationPolicy(
            name=name,
            description=description,
            levels=levels or [],
        )
        self._policies[policy.id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[EscalationPolicy]:
        """Get an escalation policy by ID."""
        return self._policies.get(policy_id)

    def get_all_policies(self) -> list[EscalationPolicy]:
        """Get all escalation policies."""
        return list(self._policies.values())

    def add_level_to_policy(
        self,
        policy_id: str,
        level: EscalationLevel,
    ) -> Optional[EscalationPolicy]:
        """Add a level to an escalation policy."""
        policy = self._policies.get(policy_id)
        if policy:
            policy.levels.append(level)
            # Sort by level number
            policy.levels.sort(key=lambda l: l.level)
        return policy

    def get_escalation_level(
        self,
        policy_id: str,
        level_number: int,
    ) -> Optional[EscalationLevel]:
        """Get a specific escalation level."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        for level in policy.levels:
            if level.level == level_number:
                return level
        return None

    # --- Incident Management ---

    def create_incident(
        self,
        title: str,
        description: str = "",
        severity: IncidentSeverity = IncidentSeverity.SEV3,
        category: IncidentCategory = IncidentCategory.APPLICATION,
        affected_services: Optional[list[str]] = None,
        escalation_policy_id: Optional[str] = None,
    ) -> Incident:
        """Create a new incident."""
        incident = Incident(
            title=title,
            description=description,
            severity=severity,
            category=category,
            affected_services=affected_services or [],
            escalation_policy_id=escalation_policy_id,
        )

        # Add initial timeline entry
        incident.timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "incident_created",
            "details": f"Incident created with severity {severity.value}",
        })

        self._incidents[incident.id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID."""
        return self._incidents.get(incident_id)

    def get_all_incidents(self) -> list[Incident]:
        """Get all incidents."""
        return list(self._incidents.values())

    def get_incidents_by_status(self, status: IncidentStatus) -> list[Incident]:
        """Get incidents by status."""
        return [i for i in self._incidents.values() if i.status == status]

    def get_incidents_by_severity(self, severity: IncidentSeverity) -> list[Incident]:
        """Get incidents by severity."""
        return [i for i in self._incidents.values() if i.severity == severity]

    def get_open_incidents(self) -> list[Incident]:
        """Get all open (unresolved) incidents."""
        closed_statuses = {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
        return [i for i in self._incidents.values() if i.status not in closed_statuses]

    def acknowledge_incident(
        self,
        incident_id: str,
        user_id: str,
    ) -> Optional[Incident]:
        """Acknowledge an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = datetime.now(timezone.utc)
        incident.assigned_to = user_id

        incident.timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "acknowledged",
            "user": user_id,
        })

        return incident

    def update_incident_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        notes: str = "",
    ) -> Optional[Incident]:
        """Update incident status."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        old_status = incident.status
        incident.status = status

        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now(timezone.utc)
        elif status == IncidentStatus.CLOSED:
            incident.closed_at = datetime.now(timezone.utc)

        incident.timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "status_changed",
            "from": old_status.value,
            "to": status.value,
            "notes": notes,
        })

        return incident

    def escalate_incident(
        self,
        incident_id: str,
        trigger: EscalationTrigger = EscalationTrigger.MANUAL,
        notes: str = "",
    ) -> Optional[Incident]:
        """Escalate an incident to the next level."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        policy = self._policies.get(incident.escalation_policy_id or "")
        if policy and incident.escalation_level < len(policy.levels):
            incident.escalation_level += 1

            incident.timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "escalated",
                "level": incident.escalation_level,
                "trigger": trigger.value,
                "notes": notes,
            })

        return incident

    def update_incident_severity(
        self,
        incident_id: str,
        severity: IncidentSeverity,
        reason: str = "",
    ) -> Optional[Incident]:
        """Update incident severity."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        old_severity = incident.severity
        incident.severity = severity

        incident.timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "severity_changed",
            "from": old_severity.value,
            "to": severity.value,
            "reason": reason,
        })

        return incident

    def add_incident_note(
        self,
        incident_id: str,
        note: str,
        user_id: str,
    ) -> Optional[Incident]:
        """Add a note to an incident timeline."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        incident.timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "note_added",
            "user": user_id,
            "note": note,
        })

        return incident

    def set_root_cause(
        self,
        incident_id: str,
        root_cause: str,
    ) -> Optional[Incident]:
        """Set the root cause of an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.root_cause = root_cause
            incident.timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "root_cause_identified",
                "root_cause": root_cause,
            })
        return incident

    def set_resolution(
        self,
        incident_id: str,
        resolution: str,
    ) -> Optional[Incident]:
        """Set the resolution of an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.resolution = resolution
            incident.timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "resolution_recorded",
                "resolution": resolution,
            })
        return incident

    # --- Notifications ---

    def send_notification(
        self,
        incident_id: str,
        channel: NotificationChannel,
        recipient: str,
        message: str,
    ) -> IncidentNotification:
        """Send a notification for an incident."""
        notification = IncidentNotification(
            incident_id=incident_id,
            channel=channel,
            recipient=recipient,
            message=message,
        )
        self._notifications.append(notification)
        return notification

    def get_notifications_for_incident(
        self,
        incident_id: str,
    ) -> list[IncidentNotification]:
        """Get all notifications for an incident."""
        return [n for n in self._notifications if n.incident_id == incident_id]

    def acknowledge_notification(
        self,
        notification_id: str,
    ) -> Optional[IncidentNotification]:
        """Mark a notification as acknowledged."""
        for notification in self._notifications:
            if notification.id == notification_id:
                notification.acknowledged = True
                notification.acknowledged_at = datetime.now(timezone.utc)
                return notification
        return None

    # --- SLA Checking ---

    def check_response_sla(self, incident: Incident) -> dict:
        """Check if response SLA is met for an incident."""
        config = self._severity_configs[incident.severity]
        response_target = timedelta(minutes=config.response_time_minutes)

        if incident.acknowledged_at:
            response_time = incident.acknowledged_at - incident.detected_at
            is_met = response_time <= response_target
        else:
            elapsed = datetime.now(timezone.utc) - incident.detected_at
            is_met = elapsed <= response_target
            response_time = elapsed

        return {
            "target_minutes": config.response_time_minutes,
            "actual_minutes": response_time.total_seconds() / 60,
            "is_met": is_met,
            "is_acknowledged": incident.acknowledged_at is not None,
        }

    def check_resolution_sla(self, incident: Incident) -> dict:
        """Check if resolution SLA is met for an incident."""
        config = self._severity_configs[incident.severity]
        resolution_target = timedelta(hours=config.resolution_target_hours)

        if incident.resolved_at:
            resolution_time = incident.resolved_at - incident.detected_at
            is_met = resolution_time <= resolution_target
        else:
            elapsed = datetime.now(timezone.utc) - incident.detected_at
            is_met = elapsed <= resolution_target
            resolution_time = elapsed

        return {
            "target_hours": config.resolution_target_hours,
            "actual_hours": resolution_time.total_seconds() / 3600,
            "is_met": is_met,
            "is_resolved": incident.resolved_at is not None,
        }

    def should_escalate(self, incident: Incident) -> bool:
        """Check if an incident should be auto-escalated."""
        if incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
            return False

        config = self._severity_configs[incident.severity]
        escalate_after = timedelta(minutes=config.auto_escalate_after_minutes)

        # Check time since last escalation or detection
        if incident.timeline:
            last_escalation = None
            for entry in reversed(incident.timeline):
                if entry.get("event") == "escalated":
                    last_escalation = datetime.fromisoformat(entry["timestamp"])
                    break

            if last_escalation:
                elapsed = datetime.now(timezone.utc) - last_escalation
            else:
                elapsed = datetime.now(timezone.utc) - incident.detected_at
        else:
            elapsed = datetime.now(timezone.utc) - incident.detected_at

        return elapsed > escalate_after

    # --- Metrics ---

    def get_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> IncidentMetrics:
        """Get incident metrics for a time period."""
        incidents_list = list(self._incidents.values())

        if start_date:
            incidents_list = [i for i in incidents_list if i.detected_at >= start_date]
        if end_date:
            incidents_list = [i for i in incidents_list if i.detected_at <= end_date]

        metrics = IncidentMetrics(total_incidents=len(incidents_list))

        # Count by severity
        for sev in IncidentSeverity:
            count = len([i for i in incidents_list if i.severity == sev])
            metrics.by_severity[sev.value] = count

        # Count by status
        for status in IncidentStatus:
            count = len([i for i in incidents_list if i.status == status])
            metrics.by_status[status.value] = count

        # Count by category
        for cat in IncidentCategory:
            count = len([i for i in incidents_list if i.category == cat])
            metrics.by_category[cat.value] = count

        # Calculate MTTA
        acknowledged_incidents = [
            i for i in incidents_list if i.acknowledged_at is not None
        ]
        if acknowledged_incidents:
            total_tta = sum(
                (i.acknowledged_at - i.detected_at).total_seconds() / 60  # type: ignore[operator, misc]
                for i in acknowledged_incidents
            )
            metrics.mean_time_to_acknowledge_minutes = total_tta / len(acknowledged_incidents)

        # Calculate MTTR
        resolved_incidents = [
            i for i in incidents_list if i.resolved_at is not None
        ]
        if resolved_incidents:
            total_ttr = sum(
                (i.resolved_at - i.detected_at).total_seconds() / 3600  # type: ignore[operator, misc]
                for i in resolved_incidents
            )
            metrics.mean_time_to_resolve_hours = total_ttr / len(resolved_incidents)

        # Calculate SLA percentage
        sla_checked = 0
        sla_met = 0
        for incident in resolved_incidents:
            sla_checked += 1
            sla_result = self.check_resolution_sla(incident)
            if sla_result["is_met"]:
                sla_met += 1

        if sla_checked > 0:
            metrics.sla_met_percentage = (sla_met / sla_checked) * 100

        return metrics

    # --- Summary ---

    def get_summary(self) -> dict:
        """Get a summary of the incident flow configuration."""
        return {
            "total_incidents": len(self._incidents),
            "open_incidents": len(self.get_open_incidents()),
            "total_schedules": len(self._schedules),
            "total_policies": len(self._policies),
            "severities_configured": len(self._severity_configs),
        }

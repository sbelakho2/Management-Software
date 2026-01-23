from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

class RiskCategory(str, Enum):
    """Categories of risks for Today screen."""
    
    DELIVERY = "delivery"
    QUALITY = "quality"
    CASH = "cash"
    REPUTATION = "reputation"
    SAFETY = "safety"
    COST = "cost"


class AbnormalityType(str, Enum):
    """Types of abnormalities to surface."""
    
    # Quote-to-Cash abnormalities
    LATE_QUOTE = "late_quote"
    STALLED_RFQ = "stalled_rfq"
    MISSING_CTQ = "missing_ctq"
    OVERDUE_APPROVAL = "overdue_approval"
    EXPIRED_QUOTE = "expired_quote"
    BLOCKED_TASK = "blocked_task"
    RECURRING_ISSUE = "recurring_issue"
    LOW_MARGIN = "low_margin"
    MISSING_FOLLOW_UP = "missing_follow_up"
    
    # Project Management abnormalities
    LATE_USER_STORY = "late_user_story"
    OVERDUE_PROJECT_MILESTONE = "overdue_project_milestone"
    STALLED_PROJECT_TASK = "stalled_project_task"
    STALLED_PROJECT = "stalled_project"
    OVERDUE_MILESTONE = "overdue_milestone"
    BUDGET_OVERRUN = "budget_overrun"
    RESOURCE_BOTTLENECK = "resource_bottleneck"

    # Shop Floor abnormalities (Phase 3)
    CRITICAL_ANDON = "critical_andon"  # Critical Andon events requiring acknowledgement
    WORK_ORDER_AT_RISK = "work_order_at_risk"  # Work orders at risk of missing due date
    CAPA_VERIFICATION_DUE = "capa_verification_due"  # CAPA verifications due today
    STATION_LOW_EFFICIENCY = "station_low_efficiency"  # Stations with efficiency < target
    CELL_LOW_OEE = "cell_low_oee"  # Cells with OEE < threshold
    KANBAN_OVERDUE = "kanban_overdue"  # Material Kanban cards overdue for replenishment
    WIP_LIMIT_VIOLATION = "wip_limit_violation"  # Production area exceeding WIP limits
    EXPIRING_CERTIFICATION = "expiring_certification"  # Operator certification expiring soon
    MISSING_SKILL_GAP = "missing_skill_gap"  # Skill gap identified for scheduled production
    OPEN_NC_CRITICAL = "open_nc_critical"  # Open critical non-conformances


class CommitmentType(str, Enum):
    """Types of commitments."""
    
    CUSTOMER_CALL = "customer_call"
    QUOTE_DUE = "quote_due"
    FOLLOW_UP = "follow_up"
    INTERNAL_MEETING = "internal_meeting"
    PROJECT_DEADLINE = "project_deadline"
    NCR_RESPONSE = "ncr_response"
    AUDIT = "audit"
    SHIPMENT = "shipment"
    
    # Additional commitment types
    CALL_SCHEDULED = "call_scheduled"
    APPROVAL_NEEDED = "approval_needed"
    MEETING = "meeting"
    TASK_DUE = "task_due"
    DELIVERY_DUE = "delivery_due"
    
    # Project Management commitments
    PROJECT_MILESTONE_DUE = "project_milestone_due"
    USER_STORY_DUE = "user_story_due"
    SUBTASK_DUE = "subtask_due"
    
    # Shop Floor commitments (Phase 3)
    TRAINING_SESSION = "training_session"
    AUDIT_SCHEDULED = "audit_scheduled"
    MAINTENANCE_DUE = "maintenance_due"
    CERTIFICATION_RENEWAL = "certification_renewal"
    SHIFT_HANDOFF = "shift_handoff"
    PRODUCTION_TARGET = "production_target"


class PriorityLevel(str, Enum):
    """Priority levels for items."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class LSWChecklistStatus(str, Enum):
    """Status of Lean Standard Work checklist items."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class ShopFloorAreaType(str, Enum):
    """Types of shop floor areas."""
    
    WORK_CENTER = "work_center"
    STATION = "station"
    CELL = "cell"
    LINE = "line"
    DEPARTMENT = "department"


class ShopFloorAlertSeverity(str, Enum):
    """Severity levels for shop floor alerts."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Priority:
    """A user-selected top priority."""
    
    id: UUID
    title: str
    description: str | None
    entity_type: str  # quote, rfq, task, project, nc
    entity_id: UUID
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    due_date: date | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    is_user_selected: bool = False
    rank: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Risk:
    """A risk identified by the system."""
    
    id: UUID
    title: str
    category: RiskCategory
    severity: int  # 1-10
    probability: int  # 1-10
    description: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    mitigation: str | None = None
    due_date: date | None = None
    status: str = "open"
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def risk_score(self) -> int:
        return self.severity * self.probability


@dataclass
class Commitment:
    """A time-bound commitment."""
    
    id: UUID
    title: str
    commitment_type: CommitmentType
    due_date: date
    description: str | None = None
    due_time: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    customer_name: str | None = None
    is_completed: bool = False
    is_overdue: bool = False
    is_auto_generated: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Abnormality:
    """An abnormality detected in the system."""
    
    id: UUID
    title: str
    abnormality_type: AbnormalityType
    entity_type: str
    entity_id: UUID
    detected_at: datetime = field(default_factory=datetime.now)
    days_stale: int = 0
    description: str | None = None
    severity: PriorityLevel = PriorityLevel.MEDIUM
    owner_id: UUID | None = None
    owner_name: str | None = None
    suggested_action: str | None = None
    is_auto_generated: bool = False
    is_resolved: bool = False


@dataclass
class MicroDrill:
    """A daily micro-drill question."""
    
    id: UUID
    question: str
    answer: str
    category: str
    difficulty: int  # 1-5
    hint: str | None = None
    context_entity_type: str | None = None
    context_entity_id: UUID | None = None


@dataclass
class LSWChecklistSummary:
    """Summary of user's LSW checklist."""
    
    daily_status: LSWChecklistStatus
    daily_total: int
    daily_completed: int
    weekly_status: LSWChecklistStatus
    weekly_total: int
    weekly_completed: int
    monthly_status: LSWChecklistStatus
    monthly_total: int
    monthly_completed: int
    overdue_count: int
    next_due_item: str | None = None


@dataclass
class QuickMetric:
    """A key metric for the Today screen."""
    
    id: str
    name: str
    value: float | int | str
    unit: str | None = None
    trend: str = "stable"  # up, down, stable
    trend_value: float | None = None
    status: str = "neutral"  # success, warning, critical, neutral
    target: float | None = None
    link: str | None = None


@dataclass
@dataclass
class WorkOrderAtRisk:
    """A work order that is at risk of being late."""
    
    work_order_id: UUID
    work_order_number: str
    job_name: str
    customer_name: str
    scheduled_ship_date: date
    days_until_due: int
    current_operation: str
    work_center_id: UUID
    work_center_name: str
    reason_at_risk: str
    estimated_delay_hours: float | None = None
    priority: int = 3


@dataclass
class CriticalAndon:
    """An active critical Andon alert."""
    
    id: UUID
    work_center_id: UUID
    work_center_name: str
    andon_type: str
    raised_at: datetime
    minutes_open: int
    station_id: UUID | None = None
    station_name: str | None = None
    description: str | None = None
    title: str | None = None
    raised_by_id: UUID | None = None
    raised_by_name: str | None = None
    acknowledged: bool = False
    acknowledged_by_id: UUID | None = None
    acknowledged_by_name: str | None = None
    severity: ShopFloorAlertSeverity = ShopFloorAlertSeverity.CRITICAL


@dataclass
class StationEfficiency:
    """Efficiency data for a production station."""
    
    station_id: UUID
    station_name: str
    work_center_id: UUID
    work_center_name: str
    current_efficiency: float
    target_efficiency: float
    variance: float
    trend: str
    is_below_target: bool
    operator_id: UUID | None = None
    operator_name: str | None = None


@dataclass
class CellOEE:
    """OEE data for a production cell."""
    
    cell_id: UUID
    cell_name: str
    work_center_id: UUID
    work_center_name: str
    current_oee: float
    target_oee: float
    availability: float
    performance: float
    quality: float
    is_below_threshold: bool
    variance: float


@dataclass
class KanbanAlert:
    """Alert for a Kanban signal."""
    
    id: UUID
    material_code: str
    material_name: str
    bin_location: str
    work_center_id: UUID
    work_center_name: str
    quantity_needed: float
    unit: str
    due_date: date
    days_overdue: int
    supplier_name: str | None = None
    replenishment_status: str = "pending"


@dataclass
class ExpiringCertification:
    """Alert for an expiring operator certification."""
    
    id: UUID
    user_id: UUID
    user_name: str
    certification_name: str
    certification_type: str
    expiration_date: date
    days_until_expiry: int
    is_expired: bool
    required_for_work_centers: List[str]
    renewal_training_id: UUID | None = None


@dataclass
class WIPViolation:
    """Violation of Work-In-Progress limits."""
    
    id: UUID
    work_center_id: UUID
    work_center_name: str
    cell_id: UUID | None
    cell_name: str | None
    current_wip: int
    wip_limit: int
    violation_amount: int
    started_at: datetime
    duration_minutes: int


@dataclass
class CAPAVerification:
    """Due verification for a CAPA."""
    
    id: UUID
    capa_number: str
    title: str
    capa_type: str
    verification_due_date: date
    days_until_due: int
    is_overdue: bool
    owner_id: UUID
    owner_name: str
    original_nc_id: UUID | None = None
    effectiveness_check: bool = False


@dataclass
class ScheduledTraining:
    """Upcoming training session."""
    
    id: UUID
    title: str
    description: str | None
    training_type: str
    scheduled_date: date
    scheduled_time: str
    duration_minutes: int
    location: str | None
    instructor_name: str | None
    attendee_count: int
    max_attendees: int | None
    is_user_enrolled: bool


@dataclass
class ShopFloorSummary:
    """Aggregated summary of shop floor status."""
    
    work_orders_at_risk: list[WorkOrderAtRisk]
    work_orders_at_risk_count: int
    critical_andons: list[CriticalAndon]
    unacknowledged_andon_count: int
    avg_andon_response_minutes: float
    low_efficiency_stations: list[StationEfficiency]
    low_oee_cells: list[CellOEE]
    overall_oee: float
    overdue_kanbans: list[KanbanAlert]
    pending_kanban_count: int
    expiring_certifications: list[ExpiringCertification]
    expired_certification_count: int
    expiring_soon_count: int
    wip_violations: list[WIPViolation]
    total_wip_violation_count: int
    capa_verifications_due: list[CAPAVerification]
    overdue_capa_count: int
    scheduled_trainings: list[ScheduledTraining]
    training_sessions_today: int
    total_stations: int = 0
    active_stations: int = 0


@dataclass
class HandoverNoteSummary:
    """Summary of a shift handover note."""
    
    id: int
    station_id: int
    severity: str
    safety: str
    quality: str
    delivery: str
    cost: str
    people: str
    notes: str
    created_at: datetime


@dataclass
class GlobalPulseSummary:
    """Summary of a global pulse announcement."""
    
    id: int
    message: str
    severity: str
    highlight_metric_name: Optional[str] = None
    highlight_metric_value: Optional[str] = None


@dataclass
class TodayScreenData:
    """Complete data for the Today screen."""
    
    user_id: UUID
    user_name: str
    current_date: date
    greeting: str
    
    # Executive / Management data
    top_priorities: list[Priority] = field(default_factory=list)
    unselected_priorities: list[Priority] = field(default_factory=list)
    
    top_risks: dict[RiskCategory, list[Risk]] = field(default_factory=dict)
    total_risk_count: int = 0
    critical_risk_count: int = 0
    
    todays_commitments: list[Commitment] = field(default_factory=list)
    tomorrows_commitments: list[Commitment] = field(default_factory=list)
    overdue_commitments: list[Commitment] = field(default_factory=list)
    
    abnormalities: list[Abnormality] = field(default_factory=list)
    abnormality_counts: dict[AbnormalityType, int] = field(default_factory=dict)
    
    todays_micro_drills: list[MicroDrill] = field(default_factory=list)
    drills_completed_today: int = 0
    drill_streak: int = 0
    
    lsw_summary: LSWChecklistSummary | None = None
    quick_metrics: list[QuickMetric] = field(default_factory=list)
    
    # Real-time awareness (The Pulse & Handovers)
    active_pulses: list[GlobalPulseSummary] = field(default_factory=list)
    active_handovers: list[HandoverNoteSummary] = field(default_factory=list)
    
    # Shop Floor / MES data
    shop_floor_summary: ShopFloorSummary | None = None
    
    generated_at: datetime = field(default_factory=datetime.now)
    cache_valid_until: datetime | None = None

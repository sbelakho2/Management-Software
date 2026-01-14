"""
Today Screen Data Aggregation Service.

Aggregates data for the Manager GPS "Today" screen, including:
- Top 3 Priorities (forced selection)
- Top Risks (Delivery/Quality/Cash/Reputation)
- Commitments (due quotes, calls, follow-ups)
- Abnormalities (late quotes, stalled RFQs, missing CTQs)
- Micro-Drill recall questions
- LSW Checklist status
- Quick metrics and KPIs
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Any, List, Dict, Optional
from uuid import UUID, uuid4

from sensei.core.redis import redis_client


from sensei.models.project_management import UserStory, ProjectMilestone, Project, ProjectStatus, UserStoryStatus
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.core.time import now_utc

def _utcnow() -> datetime:
    return now_utc()


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
    
    # Shop Floor abnormalities (Phase 3)
    CRITICAL_ANDON = "critical_andon"  # Critical Andon events requiring acknowledgement
    WORK_ORDER_AT_RISK = "work_order_at_risk"  # Work orders at risk of missing due date
    CAPA_VERIFICATION_DUE = "capa_verification_due"  # CAPA verifications due today
    STATION_LOW_EFFICIENCY = "station_low_efficiency"  # Stations with efficiency < target
    CELL_LOW_OEE = "cell_low_oee"  # Cells with OEE < threshold
    KANBAN_OVERDUE = "kanban_overdue"  # Material Kanban cards overdue for replenishment
    EXPIRING_CERTIFICATION = "expiring_certification"  # Certifications expiring soon
    WIP_LIMIT_VIOLATION = "wip_limit_violation"  # WIP limit exceeded
    OPEN_NC_CRITICAL = "open_nc_critical"  # Open critical non-conformances


class CommitmentType(str, Enum):
    """Types of commitments."""
    
    # Quote-to-Cash commitments
    QUOTE_DUE = "quote_due"
    CALL_SCHEDULED = "call_scheduled"
    FOLLOW_UP = "follow_up"
    APPROVAL_NEEDED = "approval_needed"
    MEETING = "meeting"
    TASK_DUE = "task_due"
    DELIVERY_DUE = "delivery_due"
    
    # Project Management commitments
    PROJECT_MILESTONE_DUE = "project_milestone_due"
    USER_STORY_DUE = "user_story_due"
    SUBTASK_DUE = "subtask_due"
    
    # Shop Floor commitments (Phase 3)
    TRAINING_SESSION = "training_session"  # Scheduled training sessions
    AUDIT_SCHEDULED = "audit_scheduled"  # Quality audits scheduled
    MAINTENANCE_DUE = "maintenance_due"  # Preventive maintenance due
    CERTIFICATION_RENEWAL = "certification_renewal"  # Certifications that need renewal
    SHIFT_HANDOFF = "shift_handoff"  # Shift handoff meeting
    PRODUCTION_TARGET = "production_target"  # Production targets/milestones


class PriorityLevel(str, Enum):
    """Priority levels."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LSWChecklistStatus(str, Enum):
    """Status of LSW checklist."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class ShopFloorAreaType(str, Enum):
    """Types of shop floor areas."""
    
    WORK_CENTER = "work_center"
    CELL = "cell"
    STATION = "station"
    LINE = "line"
    DEPARTMENT = "department"


class ShopFloorAlertSeverity(str, Enum):
    """Severity levels for shop floor alerts."""
    
    CRITICAL = "critical"  # Immediate attention required
    WARNING = "warning"  # Needs attention soon
    INFO = "info"  # Informational


@dataclass
class Priority:
    """A priority item for the Today screen."""
    
    id: UUID
    title: str
    description: str | None
    entity_type: str  # "rfq", "quote", "task", etc.
    entity_id: UUID
    priority_level: PriorityLevel
    due_date: date | None
    owner_id: UUID | None
    owner_name: str | None
    is_user_selected: bool = False  # User-forced selection
    rank: int = 0  # 1, 2, 3 for top 3
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Risk:
    """A risk item for the Today screen."""
    
    id: UUID
    title: str
    description: str | None
    category: RiskCategory
    severity: int  # 1-10
    probability: int  # 1-10
    risk_score: int  # severity * probability
    entity_type: str | None
    entity_id: UUID | None
    owner_id: UUID | None
    owner_name: str | None
    mitigation: str | None
    due_date: date | None
    status: str = "open"


@dataclass
class Commitment:
    """A commitment item for the Today screen."""
    
    id: UUID
    title: str
    description: str | None
    commitment_type: CommitmentType
    entity_type: str | None
    entity_id: UUID | None
    due_date: date
    due_time: str | None  # "14:00" format
    owner_id: UUID | None
    owner_name: str | None
    customer_name: str | None
    is_completed: bool = False
    is_overdue: bool = False


@dataclass
class Abnormality:
    """An abnormality item for the Today screen."""
    
    id: UUID
    title: str
    description: str | None
    abnormality_type: AbnormalityType
    entity_type: str
    entity_id: UUID
    detected_at: datetime
    days_stale: int
    severity: PriorityLevel
    owner_id: UUID | None
    owner_name: str | None
    suggested_action: str | None


@dataclass
class MicroDrill:
    """A micro-drill recall question."""
    
    id: UUID
    question: str
    answer: str
    hint: str | None
    category: str
    difficulty: int  # 1-5
    context_entity_type: str | None
    context_entity_id: UUID | None


@dataclass
class LSWChecklistSummary:
    """Summary of LSW checklist status."""
    
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
    next_due_item: str | None


@dataclass
class QuickMetric:
    """A quick metric for the Today screen."""
    
    id: str
    name: str
    value: float | int | str
    unit: str | None
    trend: str  # "up", "down", "stable"
    trend_value: float | None
    status: str  # "good", "warning", "critical"
    target: float | None
    link: str | None  # URL to drill down


# ========== Shop Floor Dataclasses (Phase 3) ==========

@dataclass
class WorkOrderAtRisk:
    """A work order at risk of missing its due date."""
    
    id: UUID
    work_order_number: str
    product_name: str
    quantity: int
    due_date: date
    estimated_completion: date
    days_at_risk: int  # Positive = will be late
    work_center_id: UUID | None
    work_center_name: str | None
    reason: str  # Why it's at risk
    severity: ShopFloorAlertSeverity
    assigned_to_id: UUID | None
    assigned_to_name: str | None


@dataclass
class CriticalAndon:
    """A critical Andon event requiring attention."""
    
    id: UUID
    andon_type: str  # "quality", "safety", "equipment", "material"
    title: str
    description: str | None
    work_center_id: UUID
    work_center_name: str
    station_id: UUID | None
    station_name: str | None
    raised_at: datetime
    minutes_open: int
    acknowledged: bool
    acknowledged_by_id: UUID | None
    acknowledged_by_name: str | None
    severity: ShopFloorAlertSeverity


@dataclass
class StationEfficiency:
    """Station efficiency data."""
    
    station_id: UUID
    station_name: str
    work_center_id: UUID
    work_center_name: str
    current_efficiency: float  # Percentage
    target_efficiency: float
    variance: float  # current - target
    trend: str  # "up", "down", "stable"
    is_below_target: bool
    operator_id: UUID | None
    operator_name: str | None


@dataclass
class CellOEE:
    """Cell OEE (Overall Equipment Effectiveness) data."""
    
    cell_id: UUID
    cell_name: str
    work_center_id: UUID
    work_center_name: str
    current_oee: float  # Percentage
    target_oee: float
    availability: float
    performance: float
    quality: float
    is_below_threshold: bool
    variance: float


@dataclass
class KanbanAlert:
    """An overdue Kanban card."""
    
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
    supplier_name: str | None
    replenishment_status: str  # "pending", "ordered", "in_transit"


@dataclass
class ExpiringCertification:
    """An expiring certification for a user."""
    
    id: UUID
    user_id: UUID
    user_name: str
    certification_name: str
    certification_type: str  # "process", "equipment", "safety", etc.
    expiration_date: date
    days_until_expiry: int
    is_expired: bool
    required_for_work_centers: list[str]
    renewal_training_id: UUID | None


@dataclass
class WIPViolation:
    """A WIP limit violation."""
    
    id: UUID
    work_center_id: UUID
    work_center_name: str
    cell_id: UUID | None
    cell_name: str | None
    current_wip: int
    wip_limit: int
    violation_amount: int  # current - limit
    started_at: datetime
    duration_minutes: int


@dataclass
class CAPAVerification:
    """A CAPA verification due."""
    
    id: UUID
    capa_number: str
    title: str
    capa_type: str  # "corrective", "preventive"
    verification_due_date: date
    days_until_due: int
    is_overdue: bool
    owner_id: UUID
    owner_name: str
    original_nc_id: UUID | None
    effectiveness_check: bool


@dataclass
class ScheduledTraining:
    """A scheduled training session."""
    
    id: UUID
    title: str
    description: str | None
    training_type: str  # "initial", "refresher", "certification"
    scheduled_date: date
    scheduled_time: str  # "HH:MM" format
    duration_minutes: int
    location: str | None
    instructor_name: str | None
    attendee_count: int
    max_attendees: int | None
    is_user_enrolled: bool


@dataclass
class ShopFloorSummary:
    """Summary of shop floor status for Today screen."""
    
    # Work Orders
    work_orders_at_risk: list[WorkOrderAtRisk]
    work_orders_at_risk_count: int
    
    # Andon
    critical_andons: list[CriticalAndon]
    unacknowledged_andon_count: int
    avg_andon_response_minutes: float
    
    # Efficiency
    low_efficiency_stations: list[StationEfficiency]
    low_oee_cells: list[CellOEE]
    overall_oee: float
    
    # Kanban
    overdue_kanbans: list[KanbanAlert]
    pending_kanban_count: int
    
    # Certifications
    expiring_certifications: list[ExpiringCertification]
    expired_certification_count: int
    expiring_soon_count: int  # Within 30 days
    
    # WIP
    wip_violations: list[WIPViolation]
    total_wip_violation_count: int
    
    # CAPA
    capa_verifications_due: list[CAPAVerification]
    overdue_capa_count: int
    
    # Training
    scheduled_trainings: list[ScheduledTraining]
    training_sessions_today: int


@dataclass
class TodayScreenData:
    """Complete data for the Today screen."""
    
    # User info
    user_id: UUID
    user_name: str
    current_date: date
    greeting: str
    
    # Top 3 priorities (forced selection)
    top_priorities: list[Priority]
    unselected_priorities: list[Priority]  # Available for selection
    
    # Top risks by category
    top_risks: dict[RiskCategory, list[Risk]]
    total_risk_count: int
    critical_risk_count: int
    
    # Commitments
    todays_commitments: list[Commitment]
    tomorrows_commitments: list[Commitment]
    overdue_commitments: list[Commitment]
    
    # Abnormalities
    abnormalities: list[Abnormality]
    abnormality_counts: dict[AbnormalityType, int]
    
    # Micro-drill
    todays_micro_drills: list[MicroDrill]
    drills_completed_today: int
    drill_streak: int
    
    # LSW Checklist
    lsw_summary: LSWChecklistSummary
    
    # Quick metrics
    quick_metrics: list[QuickMetric]
    
    # Shop Floor (Phase 3)
    shop_floor: ShopFloorSummary | None = None
    
    # Timestamps
    generated_at: datetime = field(default_factory=_utcnow)
    cache_valid_until: datetime | None = None


class TodayScreenService:
    """Service for aggregating Today screen data."""
    
    def __init__(self) -> None:
        """Initialize the Today screen service."""
        self.logger = logging.getLogger(__name__)
    
    async def _get_store(self, user_id: UUID, store_name: str) -> Dict[str, Any]:
        """Get a user-specific store from Redis."""
        key = f"today:{user_id}:{store_name}"
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return {}

    async def _save_store(self, user_id: UUID, store_name: str, data: Dict[str, Any]) -> None:
        """Save a user-specific store to Redis."""
        key = f"today:{user_id}:{store_name}"
        await redis_client.set(key, json.dumps(data), ex=86400) # 24h TTL

    # ========== Priority Management ==========
    
    async def set_top_priorities(
        self,
        user_id: UUID,
        priority_ids: List[UUID],
    ) -> List[Priority]:
        """Set the user's top 3 priorities (forced selection)."""
        if len(priority_ids) > 3:
            raise ValueError("Maximum 3 top priorities allowed")
        
        priorities_data = await self._get_store(user_id, "priorities")
        priorities = [Priority(**p) if isinstance(p, dict) else p for p in priorities_data.values()]
        
        # Reset all user-selected flags
        for p in priorities:
            p.is_user_selected = False
            p.rank = 0
        
        # Set selected priorities
        for rank, pid in enumerate(priority_ids, 1):
            pid_str = str(pid)
            if pid_str in priorities_data:
                p_dict = priorities_data[pid_str]
                p_dict['is_user_selected'] = True
                p_dict['rank'] = rank
        
        await self._save_store(user_id, "priorities", priorities_data)
        return [Priority(**p) for p in priorities_data.values() if p.get('is_user_selected')]
    
    async def add_priority(
        self,
        user_id: UUID,
        title: str,
        entity_type: str,
        entity_id: UUID,
        priority_level: PriorityLevel = PriorityLevel.MEDIUM,
        description: str | None = None,
        due_date: date | None = None,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
    ) -> Priority:
        """Add a priority item."""
        priority = Priority(
            id=uuid4(),
            title=title,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            priority_level=priority_level,
            due_date=due_date,
            owner_id=owner_id,
            owner_name=owner_name,
        )
        
        priorities_data = await self._get_store(user_id, "priorities")
        
        # Datetime needs special handling for JSON
        priority_dict = asdict(priority)
        priority_dict['created_at'] = priority.created_at.isoformat()
        if priority.due_date:
            priority_dict['due_date'] = priority.due_date.isoformat()
        
        priorities_data[str(priority.id)] = priority_dict
        await self._save_store(user_id, "priorities", priorities_data)
        
        return priority
    
    async def remove_priority(self, user_id: UUID, priority_id: UUID) -> bool:
        """Remove a priority item."""
        priorities_data = await self._get_store(user_id, "priorities")
        pid_str = str(priority_id)
        
        if pid_str in priorities_data:
            del priorities_data[pid_str]
            await self._save_store(user_id, "priorities", priorities_data)
            return True
        return False
    
    async def get_user_priorities(
        self,
        user_id: UUID,
        include_selected: bool = True,
        include_unselected: bool = True,
    ) -> List[Priority]:
        """Get priorities for a user."""
        priorities_data = await self._get_store(user_id, "priorities")
        
        result = []
        for p_dict in priorities_data.values():
            # Handle date/datetime conversions from JSON
            if isinstance(p_dict['created_at'], str):
                p_dict['created_at'] = datetime.fromisoformat(p_dict['created_at'])
            if p_dict.get('due_date') and isinstance(p_dict['due_date'], str):
                p_dict['due_date'] = date.fromisoformat(p_dict['due_date'])
                
            p = Priority(**p_dict)
            if p.is_user_selected and include_selected:
                result.append(p)
            elif not p.is_user_selected and include_unselected:
                result.append(p)
        
        # Sort: selected first by rank, then unselected by priority level
        result.sort(key=lambda p: (
            0 if p.is_user_selected else 1,
            p.rank if p.is_user_selected else 999,
            0 if p.priority_level == PriorityLevel.HIGH else 1 if p.priority_level == PriorityLevel.MEDIUM else 2,
        ))
        return result
    
    # ========== Risk Management ==========
    
    def add_risk(
        self,
        title: str,
        category: RiskCategory,
        severity: int,
        probability: int,
        description: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
        mitigation: str | None = None,
        due_date: date | None = None,
    ) -> Risk:
        """Add a risk item."""
        risk = Risk(
            id=uuid4(),
            title=title,
            description=description,
            category=category,
            severity=min(10, max(1, severity)),
            probability=min(10, max(1, probability)),
            risk_score=min(10, max(1, severity)) * min(10, max(1, probability)),
            entity_type=entity_type,
            entity_id=entity_id,
            owner_id=owner_id,
            owner_name=owner_name,
            mitigation=mitigation,
            due_date=due_date,
        )
        
        self._risks[risk.id] = risk
        return risk
    
    def get_risks_by_category(
        self,
        category: RiskCategory | None = None,
        top_n: int | None = None,
    ) -> dict[RiskCategory, list[Risk]]:
        """Get risks grouped by category."""
        result: dict[RiskCategory, list[Risk]] = {}
        
        for risk in self._risks.values():
            if category is not None and risk.category != category:
                continue
            
            if risk.category not in result:
                result[risk.category] = []
            result[risk.category].append(risk)
        
        # Sort each category by risk score descending
        for cat in result:
            result[cat].sort(key=lambda r: r.risk_score, reverse=True)
            if top_n is not None:
                result[cat] = result[cat][:top_n]
        
        return result
    
    def get_top_risks(self, top_n: int = 5) -> list[Risk]:
        """Get top N risks across all categories."""
        risks = list(self._risks.values())
        risks.sort(key=lambda r: r.risk_score, reverse=True)
        return risks[:top_n]
    
    # ========== Commitment Management ==========
    
    def add_commitment(
        self,
        title: str,
        commitment_type: CommitmentType,
        due_date: date,
        description: str | None = None,
        due_time: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
        customer_name: str | None = None,
    ) -> Commitment:
        """Add a commitment."""
        commitment = Commitment(
            id=uuid4(),
            title=title,
            description=description,
            commitment_type=commitment_type,
            entity_type=entity_type,
            entity_id=entity_id,
            due_date=due_date,
            due_time=due_time,
            owner_id=owner_id,
            owner_name=owner_name,
            customer_name=customer_name,
            is_overdue=due_date < date.today(),
        )
        
        self._commitments[commitment.id] = commitment
        return commitment
    
    def complete_commitment(self, commitment_id: UUID) -> Commitment | None:
        """Mark a commitment as completed."""
        commitment = self._commitments.get(commitment_id)
        if commitment:
            commitment.is_completed = True
        return commitment
    
    def get_commitments(
        self,
        user_id: UUID | None = None,
        target_date: date | None = None,
        include_overdue: bool = True,
        include_completed: bool = False,
    ) -> list[Commitment]:
        """Get commitments with filtering."""
        result = []
        today = date.today()
        
        for commitment in self._commitments.values():
            if user_id is not None and commitment.owner_id != user_id:
                continue
            
            if not include_completed and commitment.is_completed:
                continue
            
            # Update overdue status
            commitment.is_overdue = commitment.due_date < today and not commitment.is_completed
            
            if target_date is not None:
                if commitment.due_date == target_date:
                    result.append(commitment)
            elif include_overdue and commitment.is_overdue:
                result.append(commitment)
            elif commitment.due_date >= today:
                result.append(commitment)
        
        # Sort by due date and time
        result.sort(key=lambda c: (c.due_date, c.due_time or ""))
        return result
    
    # ========== Abnormality Management ==========
    
    def add_abnormality(
        self,
        title: str,
        abnormality_type: AbnormalityType,
        entity_type: str,
        entity_id: UUID,
        days_stale: int = 0,
        description: str | None = None,
        severity: PriorityLevel = PriorityLevel.MEDIUM,
        owner_id: UUID | None = None,
        owner_name: str | None = None,
        suggested_action: str | None = None,
    ) -> Abnormality:
        """Add an abnormality."""
        abnormality = Abnormality(
            id=uuid4(),
            title=title,
            description=description,
            abnormality_type=abnormality_type,
            entity_type=entity_type,
            entity_id=entity_id,
            detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
            days_stale=days_stale,
            severity=severity,
            owner_id=owner_id,
            owner_name=owner_name,
            suggested_action=suggested_action,
        )
        
        self._abnormalities[abnormality.id] = abnormality
        return abnormality
    
    def resolve_abnormality(self, abnormality_id: UUID) -> bool:
        """Resolve (remove) an abnormality."""
        if abnormality_id in self._abnormalities:
            del self._abnormalities[abnormality_id]
            return True
        return False
    
    def get_abnormalities(
        self,
        user_id: UUID | None = None,
        abnormality_type: AbnormalityType | None = None,
        severity: PriorityLevel | None = None,
    ) -> list[Abnormality]:
        """Get abnormalities with filtering."""
        result = []
        
        for abnormality in self._abnormalities.values():
            if user_id is not None and abnormality.owner_id != user_id:
                continue
            if abnormality_type is not None and abnormality.abnormality_type != abnormality_type:
                continue
            if severity is not None and abnormality.severity != severity:
                continue
            result.append(abnormality)
        
        # Sort by severity then days stale
        result.sort(key=lambda a: (
            0 if a.severity == PriorityLevel.HIGH else 1 if a.severity == PriorityLevel.MEDIUM else 2,
            -a.days_stale,
        ))
        
        return result
    
    def get_abnormality_counts(self) -> dict[AbnormalityType, int]:
        """Get counts of abnormalities by type."""
        counts: dict[AbnormalityType, int] = {}
        for abnormality in self._abnormalities.values():
            if abnormality.abnormality_type not in counts:
                counts[abnormality.abnormality_type] = 0
            counts[abnormality.abnormality_type] += 1
        return counts
    
    # ========== Micro-Drill Management ==========
    
    def add_micro_drill(
        self,
        question: str,
        answer: str,
        category: str,
        difficulty: int = 3,
        hint: str | None = None,
        context_entity_type: str | None = None,
        context_entity_id: UUID | None = None,
    ) -> MicroDrill:
        """Add a micro-drill question."""
        drill = MicroDrill(
            id=uuid4(),
            question=question,
            answer=answer,
            hint=hint,
            category=category,
            difficulty=min(5, max(1, difficulty)),
            context_entity_type=context_entity_type,
            context_entity_id=context_entity_id,
        )
        
        self._micro_drills[drill.id] = drill
        return drill
    
    def get_todays_drills(
        self,
        user_id: UUID,
        count: int = 3,
    ) -> list[MicroDrill]:
        """Get today's micro-drill questions for a user."""
        # In production, this would use spaced repetition algorithm
        # For now, return random selection
        drills = list(self._micro_drills.values())
        
        # Get user progress
        progress = self._drill_progress.get(user_id, {})
        completed_today = progress.get("completed_today", [])
        
        # Filter out completed drills
        available = [d for d in drills if str(d.id) not in completed_today]
        
        return available[:count]
    
    def complete_drill(
        self,
        user_id: UUID,
        drill_id: UUID,
        correct: bool,
    ) -> dict[str, Any]:
        """Record drill completion."""
        if user_id not in self._drill_progress:
            self._drill_progress[user_id] = {
                "completed_today": [],
                "streak": 0,
                "total_completed": 0,
                "correct_count": 0,
            }
        
        progress = self._drill_progress[user_id]
        progress["completed_today"].append(str(drill_id))
        progress["total_completed"] += 1
        if correct:
            progress["correct_count"] += 1
            progress["streak"] += 1
        else:
            progress["streak"] = 0
        
        return {
            "streak": progress["streak"],
            "total_completed": progress["total_completed"],
            "accuracy": progress["correct_count"] / progress["total_completed"] * 100,
        }
    
    def get_drill_progress(self, user_id: UUID) -> dict[str, Any]:
        """Get user's drill progress."""
        progress = self._drill_progress.get(user_id, {
            "completed_today": [],
            "streak": 0,
            "total_completed": 0,
            "correct_count": 0,
        })
        
        return {
            "drills_completed_today": len(progress.get("completed_today", [])),
            "streak": progress.get("streak", 0),
            "total_completed": progress.get("total_completed", 0),
            "accuracy": (
                progress.get("correct_count", 0) / progress.get("total_completed", 1) * 100
                if progress.get("total_completed", 0) > 0 else 0
            ),
        }
    
    # ========== LSW Summary ==========
    
    def get_lsw_summary(self, user_id: UUID) -> LSWChecklistSummary:
        """Get LSW checklist summary for user."""
        # In production, this would query the LSW service
        # For now, return sample data
        return LSWChecklistSummary(
            daily_status=LSWChecklistStatus.IN_PROGRESS,
            daily_total=5,
            daily_completed=3,
            weekly_status=LSWChecklistStatus.NOT_STARTED,
            weekly_total=3,
            weekly_completed=0,
            monthly_status=LSWChecklistStatus.COMPLETED,
            monthly_total=2,
            monthly_completed=2,
            overdue_count=1,
            next_due_item="Review daily metrics",
        )
    
    # ========== Quick Metrics ==========
    
    def get_quick_metrics(self, user_id: UUID) -> list[QuickMetric]:
        """Get quick metrics for the Today screen."""
        # In production, this would call the KPI service
        # For now, return sample metrics
        return [
            QuickMetric(
                id="rfq-pipeline",
                name="Open RFQs",
                value=12,
                unit=None,
                trend="up",
                trend_value=2,
                status="good",
                target=15,
                link="/rfqs?status=open",
            ),
            QuickMetric(
                id="quotes-pending",
                name="Quotes Pending",
                value=8,
                unit=None,
                trend="stable",
                trend_value=0,
                status="warning",
                target=5,
                link="/quotes?status=pending",
            ),
            QuickMetric(
                id="win-rate",
                name="Win Rate",
                value=42.5,
                unit="%",
                trend="up",
                trend_value=3.2,
                status="good",
                target=40,
                link="/analytics/win-rate",
            ),
            QuickMetric(
                id="avg-cycle-time",
                name="Avg Cycle Time",
                value=4.2,
                unit="days",
                trend="down",
                trend_value=-0.5,
                status="good",
                target=5,
                link="/analytics/cycle-time",
            ),
        ]
    
    # ========== Shop Floor Management (Phase 3) ==========
    
    def add_work_order_at_risk(
        self,
        work_order_number: str,
        product_name: str,
        quantity: int,
        due_date: date,
        estimated_completion: date,
        reason: str,
        work_center_id: UUID | None = None,
        work_center_name: str | None = None,
        assigned_to_id: UUID | None = None,
        assigned_to_name: str | None = None,
    ) -> WorkOrderAtRisk:
        """Add a work order at risk."""
        days_at_risk = (estimated_completion - due_date).days
        severity = (
            ShopFloorAlertSeverity.CRITICAL if days_at_risk > 3
            else ShopFloorAlertSeverity.WARNING if days_at_risk > 0
            else ShopFloorAlertSeverity.INFO
        )
        
        wo = WorkOrderAtRisk(
            id=uuid4(),
            work_order_number=work_order_number,
            product_name=product_name,
            quantity=quantity,
            due_date=due_date,
            estimated_completion=estimated_completion,
            days_at_risk=days_at_risk,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            reason=reason,
            severity=severity,
            assigned_to_id=assigned_to_id,
            assigned_to_name=assigned_to_name,
        )
        
        self._work_orders_at_risk[wo.id] = wo
        return wo
    
    def get_work_orders_at_risk(
        self,
        work_center_id: UUID | None = None,
        severity: ShopFloorAlertSeverity | None = None,
    ) -> list[WorkOrderAtRisk]:
        """Get work orders at risk."""
        result = []
        for wo in self._work_orders_at_risk.values():
            if work_center_id and wo.work_center_id != work_center_id:
                continue
            if severity and wo.severity != severity:
                continue
            result.append(wo)
        
        # Sort by severity (critical first) then days at risk
        result.sort(key=lambda w: (
            0 if w.severity == ShopFloorAlertSeverity.CRITICAL else 1,
            -w.days_at_risk,
        ))
        return result
    
    def resolve_work_order_at_risk(self, work_order_id: UUID) -> bool:
        """Remove a work order from at-risk list."""
        if work_order_id in self._work_orders_at_risk:
            del self._work_orders_at_risk[work_order_id]
            return True
        return False
    
    def add_critical_andon(
        self,
        andon_type: str,
        title: str,
        work_center_id: UUID,
        work_center_name: str,
        description: str | None = None,
        station_id: UUID | None = None,
        station_name: str | None = None,
        severity: ShopFloorAlertSeverity = ShopFloorAlertSeverity.CRITICAL,
    ) -> CriticalAndon:
        """Add a critical Andon event."""
        andon = CriticalAndon(
            id=uuid4(),
            andon_type=andon_type,
            title=title,
            description=description,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            station_id=station_id,
            station_name=station_name,
            raised_at=datetime.now(timezone.utc).replace(tzinfo=None),
            minutes_open=0,
            acknowledged=False,
            acknowledged_by_id=None,
            acknowledged_by_name=None,
            severity=severity,
        )
        
        self._critical_andons[andon.id] = andon
        return andon
    
    def acknowledge_andon(
        self,
        andon_id: UUID,
        acknowledged_by_id: UUID,
        acknowledged_by_name: str,
    ) -> CriticalAndon | None:
        """Acknowledge an Andon event."""
        andon = self._critical_andons.get(andon_id)
        if andon:
            andon.acknowledged = True
            andon.acknowledged_by_id = acknowledged_by_id
            andon.acknowledged_by_name = acknowledged_by_name
        return andon
    
    def resolve_andon(self, andon_id: UUID) -> bool:
        """Resolve an Andon event."""
        if andon_id in self._critical_andons:
            del self._critical_andons[andon_id]
            return True
        return False
    
    def get_critical_andons(
        self,
        work_center_id: UUID | None = None,
        unacknowledged_only: bool = False,
    ) -> list[CriticalAndon]:
        """Get critical Andon events."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = []
        
        for andon in self._critical_andons.values():
            # Update minutes open
            andon.minutes_open = int((now - andon.raised_at).total_seconds() / 60)
            
            if work_center_id and andon.work_center_id != work_center_id:
                continue
            if unacknowledged_only and andon.acknowledged:
                continue
            result.append(andon)
        
        # Sort by acknowledged status (unacknowledged first), then by time open
        result.sort(key=lambda a: (0 if not a.acknowledged else 1, -a.minutes_open))
        return result
    
    def add_station_efficiency(
        self,
        station_id: UUID,
        station_name: str,
        work_center_id: UUID,
        work_center_name: str,
        current_efficiency: float,
        target_efficiency: float,
        operator_id: UUID | None = None,
        operator_name: str | None = None,
    ) -> StationEfficiency:
        """Add or update station efficiency data."""
        variance = current_efficiency - target_efficiency
        is_below_target = current_efficiency < target_efficiency
        
        # Determine trend (in production, compare with historical data)
        trend = "stable"
        
        eff = StationEfficiency(
            station_id=station_id,
            station_name=station_name,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            current_efficiency=current_efficiency,
            target_efficiency=target_efficiency,
            variance=variance,
            trend=trend,
            is_below_target=is_below_target,
            operator_id=operator_id,
            operator_name=operator_name,
        )
        
        self._station_efficiencies[station_id] = eff
        return eff
    
    def get_low_efficiency_stations(
        self,
        work_center_id: UUID | None = None,
        threshold: float | None = None,
    ) -> list[StationEfficiency]:
        """Get stations with efficiency below target or threshold."""
        result = []
        
        for eff in self._station_efficiencies.values():
            if work_center_id and eff.work_center_id != work_center_id:
                continue
            if threshold is not None:
                if eff.current_efficiency < threshold:
                    result.append(eff)
            elif eff.is_below_target:
                result.append(eff)
        
        # Sort by variance (worst first)
        result.sort(key=lambda e: e.variance)
        return result
    
    def add_cell_oee(
        self,
        cell_id: UUID,
        cell_name: str,
        work_center_id: UUID,
        work_center_name: str,
        availability: float,
        performance: float,
        quality: float,
        target_oee: float,
    ) -> CellOEE:
        """Add or update cell OEE data."""
        current_oee = (availability / 100) * (performance / 100) * (quality / 100) * 100
        variance = current_oee - target_oee
        
        oee = CellOEE(
            cell_id=cell_id,
            cell_name=cell_name,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            current_oee=round(current_oee, 2),
            target_oee=target_oee,
            availability=availability,
            performance=performance,
            quality=quality,
            is_below_threshold=current_oee < target_oee,
            variance=round(variance, 2),
        )
        
        self._cell_oees[cell_id] = oee
        return oee
    
    def get_low_oee_cells(
        self,
        work_center_id: UUID | None = None,
        threshold: float | None = None,
    ) -> list[CellOEE]:
        """Get cells with OEE below target or threshold."""
        result = []
        
        for oee in self._cell_oees.values():
            if work_center_id and oee.work_center_id != work_center_id:
                continue
            if threshold is not None:
                if oee.current_oee < threshold:
                    result.append(oee)
            elif oee.is_below_threshold:
                result.append(oee)
        
        # Sort by variance (worst first)
        result.sort(key=lambda o: o.variance)
        return result
    
    def get_overall_oee(self) -> float:
        """Get overall OEE across all cells."""
        if not self._cell_oees:
            return 0.0
        
        total_oee = sum(oee.current_oee for oee in self._cell_oees.values())
        return round(total_oee / len(self._cell_oees), 2)
    
    def add_kanban_alert(
        self,
        material_code: str,
        material_name: str,
        bin_location: str,
        work_center_id: UUID,
        work_center_name: str,
        quantity_needed: float,
        unit: str,
        due_date: date,
        supplier_name: str | None = None,
        replenishment_status: str = "pending",
    ) -> KanbanAlert:
        """Add a Kanban alert."""
        days_overdue = (date.today() - due_date).days
        
        alert = KanbanAlert(
            id=uuid4(),
            material_code=material_code,
            material_name=material_name,
            bin_location=bin_location,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            quantity_needed=quantity_needed,
            unit=unit,
            due_date=due_date,
            days_overdue=max(0, days_overdue),
            supplier_name=supplier_name,
            replenishment_status=replenishment_status,
        )
        
        self._kanban_alerts[alert.id] = alert
        return alert
    
    def update_kanban_status(
        self,
        kanban_id: UUID,
        status: str,
    ) -> KanbanAlert | None:
        """Update Kanban replenishment status."""
        alert = self._kanban_alerts.get(kanban_id)
        if alert:
            alert.replenishment_status = status
        return alert
    
    def resolve_kanban_alert(self, kanban_id: UUID) -> bool:
        """Resolve a Kanban alert."""
        if kanban_id in self._kanban_alerts:
            del self._kanban_alerts[kanban_id]
            return True
        return False
    
    def get_overdue_kanbans(
        self,
        work_center_id: UUID | None = None,
    ) -> list[KanbanAlert]:
        """Get overdue Kanban alerts."""
        today = date.today()
        result = []
        
        for alert in self._kanban_alerts.values():
            # Update days overdue
            alert.days_overdue = max(0, (today - alert.due_date).days)
            
            if work_center_id and alert.work_center_id != work_center_id:
                continue
            if alert.days_overdue > 0:
                result.append(alert)
        
        # Sort by days overdue (most overdue first)
        result.sort(key=lambda a: -a.days_overdue)
        return result
    
    def add_expiring_certification(
        self,
        user_id: UUID,
        user_name: str,
        certification_name: str,
        certification_type: str,
        expiration_date: date,
        required_for_work_centers: list[str] | None = None,
        renewal_training_id: UUID | None = None,
    ) -> ExpiringCertification:
        """Add an expiring certification."""
        today = date.today()
        days_until_expiry = (expiration_date - today).days
        is_expired = expiration_date < today
        
        cert = ExpiringCertification(
            id=uuid4(),
            user_id=user_id,
            user_name=user_name,
            certification_name=certification_name,
            certification_type=certification_type,
            expiration_date=expiration_date,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            required_for_work_centers=required_for_work_centers or [],
            renewal_training_id=renewal_training_id,
        )
        
        self._expiring_certifications[cert.id] = cert
        return cert
    
    def get_expiring_certifications(
        self,
        user_id: UUID | None = None,
        days_ahead: int = 30,
        include_expired: bool = True,
    ) -> list[ExpiringCertification]:
        """Get expiring certifications."""
        today = date.today()
        result = []
        
        for cert in self._expiring_certifications.values():
            # Update days until expiry
            cert.days_until_expiry = (cert.expiration_date - today).days
            cert.is_expired = cert.expiration_date < today
            
            if user_id and cert.user_id != user_id:
                continue
            
            if cert.is_expired:
                if include_expired:
                    result.append(cert)
            elif cert.days_until_expiry <= days_ahead:
                result.append(cert)
        
        # Sort: expired first, then by days until expiry
        result.sort(key=lambda c: (0 if c.is_expired else 1, c.days_until_expiry))
        return result
    
    def renew_certification(self, certification_id: UUID) -> bool:
        """Mark certification as renewed (remove from expiring list)."""
        if certification_id in self._expiring_certifications:
            del self._expiring_certifications[certification_id]
            return True
        return False
    
    def add_wip_violation(
        self,
        work_center_id: UUID,
        work_center_name: str,
        current_wip: int,
        wip_limit: int,
        cell_id: UUID | None = None,
        cell_name: str | None = None,
    ) -> WIPViolation:
        """Add a WIP violation."""
        violation = WIPViolation(
            id=uuid4(),
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            cell_id=cell_id,
            cell_name=cell_name,
            current_wip=current_wip,
            wip_limit=wip_limit,
            violation_amount=current_wip - wip_limit,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            duration_minutes=0,
        )
        
        self._wip_violations[violation.id] = violation
        return violation
    
    def get_wip_violations(
        self,
        work_center_id: UUID | None = None,
    ) -> list[WIPViolation]:
        """Get WIP violations."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = []
        
        for violation in self._wip_violations.values():
            # Update duration
            violation.duration_minutes = int((now - violation.started_at).total_seconds() / 60)
            
            if work_center_id and violation.work_center_id != work_center_id:
                continue
            result.append(violation)
        
        # Sort by violation amount (worst first)
        result.sort(key=lambda v: -v.violation_amount)
        return result
    
    def resolve_wip_violation(self, violation_id: UUID) -> bool:
        """Resolve a WIP violation."""
        if violation_id in self._wip_violations:
            del self._wip_violations[violation_id]
            return True
        return False
    
    def add_capa_verification(
        self,
        capa_number: str,
        title: str,
        capa_type: str,
        verification_due_date: date,
        owner_id: UUID,
        owner_name: str,
        original_nc_id: UUID | None = None,
        effectiveness_check: bool = False,
    ) -> CAPAVerification:
        """Add a CAPA verification due."""
        today = date.today()
        days_until_due = (verification_due_date - today).days
        
        capa = CAPAVerification(
            id=uuid4(),
            capa_number=capa_number,
            title=title,
            capa_type=capa_type,
            verification_due_date=verification_due_date,
            days_until_due=days_until_due,
            is_overdue=verification_due_date < today,
            owner_id=owner_id,
            owner_name=owner_name,
            original_nc_id=original_nc_id,
            effectiveness_check=effectiveness_check,
        )
        
        self._capa_verifications[capa.id] = capa
        return capa
    
    def get_capa_verifications_due(
        self,
        owner_id: UUID | None = None,
        days_ahead: int = 7,
        include_overdue: bool = True,
    ) -> list[CAPAVerification]:
        """Get CAPA verifications due."""
        today = date.today()
        result = []
        
        for capa in self._capa_verifications.values():
            # Update status
            capa.days_until_due = (capa.verification_due_date - today).days
            capa.is_overdue = capa.verification_due_date < today
            
            if owner_id and capa.owner_id != owner_id:
                continue
            
            if capa.is_overdue:
                if include_overdue:
                    result.append(capa)
            elif capa.days_until_due <= days_ahead:
                result.append(capa)
        
        # Sort: overdue first, then by due date
        result.sort(key=lambda c: (0 if c.is_overdue else 1, c.days_until_due))
        return result
    
    def complete_capa_verification(self, capa_id: UUID) -> bool:
        """Mark CAPA verification as complete."""
        if capa_id in self._capa_verifications:
            del self._capa_verifications[capa_id]
            return True
        return False
    
    def add_scheduled_training(
        self,
        title: str,
        training_type: str,
        scheduled_date: date,
        scheduled_time: str,
        duration_minutes: int,
        attendee_count: int = 0,
        description: str | None = None,
        location: str | None = None,
        instructor_name: str | None = None,
        max_attendees: int | None = None,
        is_user_enrolled: bool = False,
    ) -> ScheduledTraining:
        """Add a scheduled training session."""
        training = ScheduledTraining(
            id=uuid4(),
            title=title,
            description=description,
            training_type=training_type,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            location=location,
            instructor_name=instructor_name,
            attendee_count=attendee_count,
            max_attendees=max_attendees,
            is_user_enrolled=is_user_enrolled,
        )
        
        self._scheduled_trainings[training.id] = training
        return training
    
    def get_scheduled_trainings(
        self,
        target_date: date | None = None,
        user_enrolled_only: bool = False,
        days_ahead: int = 7,
    ) -> list[ScheduledTraining]:
        """Get scheduled training sessions."""
        today = date.today()
        result = []
        
        for training in self._scheduled_trainings.values():
            if user_enrolled_only and not training.is_user_enrolled:
                continue
            
            if target_date:
                if training.scheduled_date == target_date:
                    result.append(training)
            elif training.scheduled_date >= today and training.scheduled_date <= today + timedelta(days=days_ahead):
                result.append(training)
        
        # Sort by date and time
        result.sort(key=lambda t: (t.scheduled_date, t.scheduled_time))
        return result
    
    def enroll_in_training(self, training_id: UUID) -> ScheduledTraining | None:
        """Enroll user in a training session."""
        training = self._scheduled_trainings.get(training_id)
        if training:
            if training.max_attendees and training.attendee_count >= training.max_attendees:
                return None
            training.is_user_enrolled = True
            training.attendee_count += 1
        return training
    
    def get_shop_floor_summary(
        self,
        user_id: UUID | None = None,
        work_center_id: UUID | None = None,
    ) -> ShopFloorSummary:
        """Get complete shop floor summary for Today screen."""
        today = date.today()
        
        # Work orders at risk
        work_orders_at_risk = self.get_work_orders_at_risk(work_center_id=work_center_id)
        
        # Critical Andons
        critical_andons = self.get_critical_andons(work_center_id=work_center_id)
        unacknowledged = [a for a in critical_andons if not a.acknowledged]
        avg_response = (
            sum(a.minutes_open for a in critical_andons) / len(critical_andons)
            if critical_andons else 0.0
        )
        
        # Efficiency
        low_efficiency = self.get_low_efficiency_stations(work_center_id=work_center_id)
        low_oee = self.get_low_oee_cells(work_center_id=work_center_id)
        overall_oee = self.get_overall_oee()
        
        # Kanbans
        overdue_kanbans = self.get_overdue_kanbans(work_center_id=work_center_id)
        pending_kanbans = [
            k for k in self._kanban_alerts.values()
            if k.replenishment_status == "pending"
        ]
        
        # Certifications
        expiring_certs = self.get_expiring_certifications(user_id=user_id)
        expired = [c for c in expiring_certs if c.is_expired]
        expiring_soon = [c for c in expiring_certs if not c.is_expired and c.days_until_expiry <= 30]
        
        # WIP violations
        wip_violations = self.get_wip_violations(work_center_id=work_center_id)
        
        # CAPA verifications
        capa_due = self.get_capa_verifications_due(owner_id=user_id)
        overdue_capas = [c for c in capa_due if c.is_overdue]
        
        # Scheduled trainings
        trainings_today = self.get_scheduled_trainings(target_date=today)
        all_trainings = self.get_scheduled_trainings()
        
        return ShopFloorSummary(
            work_orders_at_risk=work_orders_at_risk,
            work_orders_at_risk_count=len(work_orders_at_risk),
            critical_andons=critical_andons,
            unacknowledged_andon_count=len(unacknowledged),
            avg_andon_response_minutes=round(avg_response, 1),
            low_efficiency_stations=low_efficiency,
            low_oee_cells=low_oee,
            overall_oee=overall_oee,
            overdue_kanbans=overdue_kanbans,
            pending_kanban_count=len(pending_kanbans),
            expiring_certifications=expiring_certs,
            expired_certification_count=len(expired),
            expiring_soon_count=len(expiring_soon),
            wip_violations=wip_violations,
            total_wip_violation_count=len(wip_violations),
            capa_verifications_due=capa_due,
            overdue_capa_count=len(overdue_capas),
            scheduled_trainings=all_trainings,
            training_sessions_today=len(trainings_today),
        )

    # ========== Full Today Screen Data ==========
    
    async def get_today_screen(
        self,
        user_id: UUID,
        user_name: str,
        db: AsyncSession | None = None,
    ) -> TodayScreenData:
        """Get complete Today screen data for a user."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Aggregate real-time data if DB is provided
        if db:
            await self._aggregate_project_data(db, user_id)
        
        # Get greeting based on time of day
        hour = datetime.now().hour
        if hour < 12:
            greeting = f"Good morning, {user_name.split()[0]}"
        elif hour < 17:
            greeting = f"Good afternoon, {user_name.split()[0]}"
        else:
            greeting = f"Good evening, {user_name.split()[0]}"
        
        # Get priorities
        all_priorities = self.get_user_priorities(user_id)
        top_priorities = [p for p in all_priorities if p.is_user_selected]
        unselected_priorities = [p for p in all_priorities if not p.is_user_selected]
        
        # Get risks
        risks_by_category = self.get_risks_by_category(top_n=3)
        total_risks = len(self._risks)
        critical_risks = len([r for r in self._risks.values() if r.risk_score >= 50])
        
        # Get commitments
        todays_commitments = self.get_commitments(user_id=user_id, target_date=today)
        tomorrows_commitments = self.get_commitments(user_id=user_id, target_date=tomorrow)
        overdue_commitments = [c for c in self.get_commitments(user_id=user_id) if c.is_overdue]
        
        # Get abnormalities
        abnormalities = self.get_abnormalities(user_id=user_id)
        abnormality_counts = self.get_abnormality_counts()
        
        # Get micro-drills
        todays_drills = self.get_todays_drills(user_id)
        drill_progress = self.get_drill_progress(user_id)
        
        # Get LSW summary
        lsw_summary = self.get_lsw_summary(user_id)
        
        # Get quick metrics
        quick_metrics = self.get_quick_metrics(user_id)
        
        # Get shop floor summary (Phase 3)
        shop_floor = self.get_shop_floor_summary(user_id=user_id)
        
        return TodayScreenData(
            user_id=user_id,
            user_name=user_name,
            current_date=today,
            greeting=greeting,
            top_priorities=top_priorities,
            unselected_priorities=unselected_priorities,
            top_risks=risks_by_category,
            total_risk_count=total_risks,
            critical_risk_count=critical_risks,
            todays_commitments=todays_commitments,
            tomorrows_commitments=tomorrows_commitments,
            overdue_commitments=overdue_commitments,
            abnormalities=abnormalities,
            abnormality_counts=abnormality_counts,
            todays_micro_drills=todays_drills,
            drills_completed_today=drill_progress["drills_completed_today"],
            drill_streak=drill_progress["streak"],
            lsw_summary=lsw_summary,
            quick_metrics=quick_metrics,
            shop_floor=shop_floor,
            cache_valid_until=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5),
        )
    
    async def _aggregate_project_data(self, db: AsyncSession, user_id: UUID) -> None:
        """Aggregate project data into commitments and abnormalities."""
        today = date.today()
        
        # 1. Fetch Overdue/Upcoming Milestones
        milestone_stmt = (
            select(ProjectMilestone, Project.name)
            .join(Project, ProjectMilestone.project_id == Project.id)
            .where(
                ProjectMilestone.owner_id == user_id,
                ProjectMilestone.status != "completed",
                ProjectMilestone.deleted_at.is_(None)
            )
        )
        result = await db.execute(milestone_stmt)
        milestones = result.all()
        
        for ms, project_name in milestones:
            # Overdue Milestone as Abnormality
            if ms.due_date < today:
                self.add_abnormality(
                    user_id=user_id,
                    title=f"Overdue Milestone: {ms.name}",
                    atype=AbnormalityType.OVERDUE_PROJECT_MILESTONE,
                    severity=8,
                    description=f"Project: {project_name}. Due on {ms.due_date}",
                    entity_type="project_milestone",
                    entity_id=ms.id,
                )
            
            # Milestone as Commitment
            self.add_commitment(
                user_id=user_id,
                title=f"Milestone: {ms.name}",
                ctype=CommitmentType.PROJECT_MILESTONE_DUE,
                target_date=ms.due_date,
                description=f"Project: {project_name}",
                entity_type="project_milestone",
                entity_id=ms.id,
                priority=PriorityLevel.HIGH if ms.due_date <= today else PriorityLevel.MEDIUM
            )

        # 2. Fetch Assigned User Stories with due dates
        # Note: We use a simplified check for assigned users since it's a JSON/Array field depending on implementation
        # For now, we check owner_id for direct accountability on Today screen
        story_stmt = (
            select(UserStory, Project.name)
            .join(Project, UserStory.project_id == Project.id)
            .where(
                UserStory.owner_id == user_id,
                UserStory.status != UserStoryStatus.DONE.value,
                UserStory.deleted_at.is_(None),
                UserStory.due_date.isnot(None)
            )
        )
        result = await db.execute(story_stmt)
        stories = result.all()
        
        for story, project_name in stories:
            # Overdue Story as Abnormality
            if story.due_date < today:
                self.add_abnormality(
                    user_id=user_id,
                    title=f"Late User Story: US-{story.ref}",
                    atype=AbnormalityType.LATE_USER_STORY,
                    severity=6,
                    description=f"{story.subject} (Project: {project_name})",
                    entity_type="user_story",
                    entity_id=story.id,
                )
            
            # Story as Commitment
            self.add_commitment(
                user_id=user_id,
                title=f"US-{story.ref}: {story.subject}",
                ctype=CommitmentType.USER_STORY_DUE,
                target_date=story.due_date,
                description=f"Project: {project_name}",
                entity_type="user_story",
                entity_id=story.id,
            )

    # ========== Sample Data ==========
    
    def _register_sample_data(self) -> None:
        """Register sample data for testing."""
        # Sample micro-drills
        sample_drills = [
            {
                "question": "What is the first step in processing an RFQ?",
                "answer": "Verify completeness and customer requirements",
                "category": "rfq",
                "difficulty": 2,
                "hint": "Think about validation before action",
            },
            {
                "question": "What margin threshold requires GM approval?",
                "answer": "Below 25% gross margin",
                "category": "quoting",
                "difficulty": 3,
                "hint": "It's a percentage threshold",
            },
            {
                "question": "How many days before a quote is considered stale?",
                "answer": "7 days without customer response",
                "category": "quoting",
                "difficulty": 2,
                "hint": "It's about a week",
            },
        ]
        
        for drill in sample_drills:
            self.add_micro_drill(**drill)


# Module-level service instance
_service: TodayScreenService | None = None


def get_today_screen_service() -> TodayScreenService:
    """Get or create the Today screen service instance."""
    global _service
    if _service is None:
        _service = TodayScreenService()
    return _service


def reset_today_screen_service() -> None:
    """Reset the service instance (for testing)."""
    global _service
    _service = None

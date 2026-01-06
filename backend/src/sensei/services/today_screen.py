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

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


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
    
    LATE_QUOTE = "late_quote"
    STALLED_RFQ = "stalled_rfq"
    MISSING_CTQ = "missing_ctq"
    OVERDUE_APPROVAL = "overdue_approval"
    EXPIRED_QUOTE = "expired_quote"
    BLOCKED_TASK = "blocked_task"
    RECURRING_ISSUE = "recurring_issue"
    LOW_MARGIN = "low_margin"
    MISSING_FOLLOW_UP = "missing_follow_up"


class CommitmentType(str, Enum):
    """Types of commitments."""
    
    QUOTE_DUE = "quote_due"
    CALL_SCHEDULED = "call_scheduled"
    FOLLOW_UP = "follow_up"
    APPROVAL_NEEDED = "approval_needed"
    MEETING = "meeting"
    TASK_DUE = "task_due"
    DELIVERY_DUE = "delivery_due"


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
    created_at: datetime = field(default_factory=datetime.utcnow)


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
    
    # Timestamps
    generated_at: datetime = field(default_factory=datetime.utcnow)
    cache_valid_until: datetime | None = None


class TodayScreenService:
    """Service for aggregating Today screen data."""
    
    def __init__(self) -> None:
        """Initialize the Today screen service."""
        # In-memory storage for user priorities
        self._user_priorities: dict[UUID, list[Priority]] = {}
        
        # Mock data stores (in production, these would query actual repositories)
        self._risks: dict[UUID, Risk] = {}
        self._commitments: dict[UUID, Commitment] = {}
        self._abnormalities: dict[UUID, Abnormality] = {}
        self._micro_drills: dict[UUID, MicroDrill] = {}
        
        # User drill progress
        self._drill_progress: dict[UUID, dict[str, Any]] = {}
        
        # Register sample data for testing
        self._register_sample_data()
    
    # ========== Priority Management ==========
    
    def set_top_priorities(
        self,
        user_id: UUID,
        priority_ids: list[UUID],
    ) -> list[Priority]:
        """Set the user's top 3 priorities (forced selection)."""
        if len(priority_ids) > 3:
            raise ValueError("Maximum 3 top priorities allowed")
        
        priorities = self._user_priorities.get(user_id, [])
        
        # Reset all user-selected flags
        for p in priorities:
            p.is_user_selected = False
            p.rank = 0
        
        # Set selected priorities
        for rank, pid in enumerate(priority_ids, 1):
            for p in priorities:
                if p.id == pid:
                    p.is_user_selected = True
                    p.rank = rank
                    break
        
        return [p for p in priorities if p.is_user_selected]
    
    def add_priority(
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
        
        if user_id not in self._user_priorities:
            self._user_priorities[user_id] = []
        
        self._user_priorities[user_id].append(priority)
        return priority
    
    def remove_priority(self, user_id: UUID, priority_id: UUID) -> bool:
        """Remove a priority item."""
        if user_id not in self._user_priorities:
            return False
        
        priorities = self._user_priorities[user_id]
        self._user_priorities[user_id] = [p for p in priorities if p.id != priority_id]
        return len(self._user_priorities[user_id]) < len(priorities)
    
    def get_user_priorities(
        self,
        user_id: UUID,
        include_selected: bool = True,
        include_unselected: bool = True,
    ) -> list[Priority]:
        """Get priorities for a user."""
        priorities = self._user_priorities.get(user_id, [])
        
        result = []
        for p in priorities:
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
            detected_at=datetime.utcnow(),
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
    
    # ========== Full Today Screen Data ==========
    
    def get_today_screen(
        self,
        user_id: UUID,
        user_name: str,
    ) -> TodayScreenData:
        """Get complete Today screen data for a user."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
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
            cache_valid_until=datetime.utcnow() + timedelta(minutes=5),
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

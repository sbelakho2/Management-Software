"""
Leader Standard Work (LSW) Scheduling & Checklists Service.

Implements:
- Auto-generation of recurring LSW items (daily/weekly/monthly)
- Interactive checklists with completion evidence
- Reminder scheduling
- Cadence management for leadership routines
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class LSWFrequency(str, Enum):
    """Frequency of LSW checklist items."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class LSWCategory(str, Enum):
    """Category of LSW activity."""
    
    GEMBA_WALK = "gemba_walk"  # Go and see
    TIER_MEETING = "tier_meeting"  # Tiered daily meetings
    STANDARD_REVIEW = "standard_review"  # Review standard work docs
    SAFETY_CHECK = "safety_check"  # Safety observations
    QUALITY_CHECK = "quality_check"  # Quality verifications
    COACHING = "coaching"  # One-on-one coaching
    PROCESS_AUDIT = "process_audit"  # Process confirmation
    PERFORMANCE_REVIEW = "performance_review"  # KPI review
    PROBLEM_SOLVING = "problem_solving"  # A3/PDCA review
    TRAINING = "training"  # Training verification
    CUSTOMER_CONTACT = "customer_contact"  # Customer touchpoints
    PLANNING = "planning"  # Weekly/monthly planning
    RECOGNITION = "recognition"  # Team recognition
    OTHER = "other"


class LSWItemStatus(str, Enum):
    """Status of an LSW checklist item instance."""
    
    PENDING = "pending"  # Not yet due
    DUE = "due"  # Due today
    OVERDUE = "overdue"  # Past due
    IN_PROGRESS = "in_progress"  # Started but not complete
    COMPLETED = "completed"  # Done
    SKIPPED = "skipped"  # Intentionally skipped
    DEFERRED = "deferred"  # Rescheduled


class DayOfWeek(str, Enum):
    """Days of the week."""
    
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


@dataclass
class LSWChecklistTemplate:
    """Template for an LSW checklist item."""
    
    id: str
    name: str
    description: str
    category: LSWCategory
    frequency: LSWFrequency
    estimated_duration_minutes: int = 15
    required: bool = True
    
    # Scheduling
    preferred_time: time | None = None  # Preferred time of day
    days_of_week: list[DayOfWeek] = field(default_factory=list)  # For weekly items
    day_of_month: int | None = None  # For monthly items (1-28)
    week_of_month: int | None = None  # 1-4 for monthly items
    
    # Role/assignment
    role_id: str | None = None  # Role this applies to
    owner_id: str | None = None  # Specific owner
    
    # Evidence requirements
    requires_notes: bool = False
    requires_evidence: bool = False
    evidence_prompt: str = ""
    
    # Checklists within the item
    sub_items: list[str] = field(default_factory=list)
    
    # Linkages
    linked_area_id: str | None = None  # Work center/production cell
    linked_kpi_id: str | None = None  # KPI to review
    
    # Active status
    is_active: bool = True
    effective_from: date | None = None
    effective_until: date | None = None
    
    # Custom fields
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class LSWChecklistInstance:
    """An instance of an LSW checklist item for a specific date."""
    
    id: str
    template_id: str
    scheduled_date: date
    status: LSWItemStatus = LSWItemStatus.PENDING
    
    # Completion tracking
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by_id: str | None = None
    
    # Evidence
    notes: str = ""
    evidence_attachment_ids: list[str] = field(default_factory=list)
    
    # Sub-item completion
    sub_items_completed: list[str] = field(default_factory=list)
    
    # Skip/defer tracking
    skip_reason: str = ""
    deferred_to: date | None = None
    
    # Duration
    actual_duration_minutes: int | None = None
    
    # Observations/findings
    findings: list[dict[str, Any]] = field(default_factory=list)
    
    # Generated actions
    generated_task_ids: list[str] = field(default_factory=list)
    generated_a3_ids: list[str] = field(default_factory=list)


@dataclass
class LSWChecklist:
    """A complete LSW checklist for a user/date."""
    
    id: str
    owner_id: str
    date: date
    items: list[LSWChecklistInstance]
    created_at: datetime
    
    # Summary
    total_items: int = 0
    completed_count: int = 0
    skipped_count: int = 0
    overdue_count: int = 0
    
    # Roll-up metrics
    total_estimated_minutes: int = 0
    total_actual_minutes: int = 0


@dataclass
class LSWReminder:
    """A reminder for an LSW item."""
    
    id: str
    instance_id: str
    reminder_time: datetime
    sent: bool = False
    sent_at: datetime | None = None
    channel: str = "in_app"  # in_app, email
    message: str = ""


@dataclass
class LSWGenerationResult:
    """Result of generating LSW checklist items."""
    
    date: date
    owner_id: str
    generated_count: int
    items: list[LSWChecklistInstance]
    reminders: list[LSWReminder]


class LSWSchedulingService:
    """Service for managing Leader Standard Work scheduling and checklists."""
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._templates: dict[str, LSWChecklistTemplate] = {}
        self._instances: dict[str, LSWChecklistInstance] = {}
        self._checklists: dict[str, LSWChecklist] = {}
        self._reminders: dict[str, LSWReminder] = {}
        
        # Register default templates
        self._register_default_templates()
    
    def _register_default_templates(self) -> None:
        """Register default LSW templates."""
        defaults = [
            # Daily items
            LSWChecklistTemplate(
                id="daily-gemba",
                name="Daily Gemba Walk",
                description="Go to the production floor, observe operations, identify abnormalities",
                category=LSWCategory.GEMBA_WALK,
                frequency=LSWFrequency.DAILY,
                estimated_duration_minutes=30,
                required=True,
                preferred_time=time(8, 0),
                requires_notes=True,
                sub_items=[
                    "Walk through all work areas",
                    "Observe 5S conditions",
                    "Check safety visual controls",
                    "Note any abnormalities",
                    "Acknowledge team members",
                ],
            ),
            LSWChecklistTemplate(
                id="daily-tier1",
                name="Tier 1 Meeting",
                description="Daily production team meeting at the gemba board",
                category=LSWCategory.TIER_MEETING,
                frequency=LSWFrequency.DAILY,
                estimated_duration_minutes=15,
                required=True,
                preferred_time=time(7, 30),
                requires_notes=True,
                sub_items=[
                    "Review yesterday's performance",
                    "Discuss today's targets",
                    "Review safety incidents",
                    "Review quality issues",
                    "Identify escalations",
                ],
            ),
            LSWChecklistTemplate(
                id="daily-safety",
                name="Safety Observation",
                description="Observe one safety behavior or condition",
                category=LSWCategory.SAFETY_CHECK,
                frequency=LSWFrequency.DAILY,
                estimated_duration_minutes=10,
                required=True,
                requires_notes=True,
                requires_evidence=True,
                evidence_prompt="Describe the safety observation and any feedback given",
            ),
            
            # Weekly items
            LSWChecklistTemplate(
                id="weekly-tier2",
                name="Tier 2 Meeting",
                description="Weekly value stream/area review meeting",
                category=LSWCategory.TIER_MEETING,
                frequency=LSWFrequency.WEEKLY,
                estimated_duration_minutes=60,
                required=True,
                days_of_week=[DayOfWeek.MONDAY],
                preferred_time=time(9, 0),
                requires_notes=True,
                sub_items=[
                    "Review week's KPIs",
                    "Discuss escalated issues",
                    "Review A3 progress",
                    "Plan countermeasures",
                    "Update visual boards",
                ],
            ),
            LSWChecklistTemplate(
                id="weekly-coaching",
                name="One-on-One Coaching",
                description="Individual coaching session with direct report",
                category=LSWCategory.COACHING,
                frequency=LSWFrequency.WEEKLY,
                estimated_duration_minutes=30,
                required=False,
                requires_notes=True,
                evidence_prompt="Document development goals discussed",
            ),
            LSWChecklistTemplate(
                id="weekly-process-audit",
                name="Process Confirmation",
                description="Verify one process follows standard work",
                category=LSWCategory.PROCESS_AUDIT,
                frequency=LSWFrequency.WEEKLY,
                estimated_duration_minutes=20,
                required=True,
                requires_notes=True,
                requires_evidence=True,
                sub_items=[
                    "Select process to audit",
                    "Review standard work document",
                    "Observe actual process",
                    "Note deviations",
                    "Provide feedback",
                ],
            ),
            
            # Monthly items
            LSWChecklistTemplate(
                id="monthly-tier3",
                name="Tier 3 / Obeya Meeting",
                description="Monthly plant/organization review in Obeya room",
                category=LSWCategory.TIER_MEETING,
                frequency=LSWFrequency.MONTHLY,
                estimated_duration_minutes=120,
                required=True,
                week_of_month=1,
                days_of_week=[DayOfWeek.WEDNESDAY],
                preferred_time=time(13, 0),
                requires_notes=True,
                sub_items=[
                    "Review monthly KPIs",
                    "Discuss strategic initiatives",
                    "Review open A3s",
                    "Address red items",
                    "Set next month's priorities",
                ],
            ),
            LSWChecklistTemplate(
                id="monthly-standard-review",
                name="Standard Work Review",
                description="Review and update standard work documents due for review",
                category=LSWCategory.STANDARD_REVIEW,
                frequency=LSWFrequency.MONTHLY,
                estimated_duration_minutes=45,
                required=True,
                requires_notes=True,
            ),
            LSWChecklistTemplate(
                id="monthly-training-check",
                name="Training Verification",
                description="Verify training completeness for team",
                category=LSWCategory.TRAINING,
                frequency=LSWFrequency.MONTHLY,
                estimated_duration_minutes=30,
                required=True,
                requires_notes=True,
            ),
            LSWChecklistTemplate(
                id="monthly-recognition",
                name="Team Recognition",
                description="Recognize team member achievements",
                category=LSWCategory.RECOGNITION,
                frequency=LSWFrequency.MONTHLY,
                estimated_duration_minutes=15,
                required=False,
                requires_notes=True,
                evidence_prompt="Document recognition given",
            ),
        ]
        
        for template in defaults:
            self._templates[template.id] = template
    
    # --------------------------------------------------------------------------
    # Template Management
    # --------------------------------------------------------------------------
    
    def create_template(self, template: LSWChecklistTemplate) -> LSWChecklistTemplate:
        """Create a new LSW checklist template."""
        if not template.id:
            template.id = str(uuid4())
        self._templates[template.id] = template
        return template
    
    def get_template(self, template_id: str) -> LSWChecklistTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def update_template(self, template_id: str, updates: dict[str, Any]) -> LSWChecklistTemplate | None:
        """Update a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False
    
    def list_templates(
        self,
        frequency: LSWFrequency | None = None,
        category: LSWCategory | None = None,
        active_only: bool = True,
    ) -> list[LSWChecklistTemplate]:
        """List templates with optional filtering."""
        templates = list(self._templates.values())
        
        if frequency:
            templates = [t for t in templates if t.frequency == frequency]
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        return templates
    
    # --------------------------------------------------------------------------
    # Checklist Generation
    # --------------------------------------------------------------------------
    
    def generate_checklist(
        self,
        owner_id: str,
        target_date: date,
        template_ids: list[str] | None = None,
    ) -> LSWGenerationResult:
        """Generate LSW checklist items for a specific date and owner."""
        items: list[LSWChecklistInstance] = []
        reminders: list[LSWReminder] = []
        
        # Get applicable templates
        if template_ids:
            templates = [self._templates[tid] for tid in template_ids if tid in self._templates]
        else:
            templates = list(self._templates.values())
        
        for template in templates:
            if not template.is_active:
                continue
            
            # Check if template applies to this date
            if not self._template_applies_to_date(template, target_date):
                continue
            
            # Check effective dates
            if template.effective_from and target_date < template.effective_from:
                continue
            if template.effective_until and target_date > template.effective_until:
                continue
            
            # Create instance
            instance = LSWChecklistInstance(
                id=str(uuid4()),
                template_id=template.id,
                scheduled_date=target_date,
                status=LSWItemStatus.PENDING,
            )
            items.append(instance)
            self._instances[instance.id] = instance
            
            # Create reminder if preferred time is set
            if template.preferred_time:
                reminder_dt = datetime.combine(target_date, template.preferred_time)
                if reminder_dt > datetime.now():
                    reminder = LSWReminder(
                        id=str(uuid4()),
                        instance_id=instance.id,
                        reminder_time=reminder_dt,
                        message=f"LSW Reminder: {template.name}",
                    )
                    reminders.append(reminder)
                    self._reminders[reminder.id] = reminder
        
        # Create checklist record
        checklist = LSWChecklist(
            id=str(uuid4()),
            owner_id=owner_id,
            date=target_date,
            items=items,
            created_at=datetime.now(),
            total_items=len(items),
            total_estimated_minutes=sum(
                self._templates[i.template_id].estimated_duration_minutes
                for i in items
            ),
        )
        self._checklists[checklist.id] = checklist
        
        return LSWGenerationResult(
            date=target_date,
            owner_id=owner_id,
            generated_count=len(items),
            items=items,
            reminders=reminders,
        )
    
    def _template_applies_to_date(self, template: LSWChecklistTemplate, target_date: date) -> bool:
        """Check if a template should generate an item for the given date."""
        if template.frequency == LSWFrequency.DAILY:
            return True
        
        weekday_map = {
            0: DayOfWeek.MONDAY,
            1: DayOfWeek.TUESDAY,
            2: DayOfWeek.WEDNESDAY,
            3: DayOfWeek.THURSDAY,
            4: DayOfWeek.FRIDAY,
            5: DayOfWeek.SATURDAY,
            6: DayOfWeek.SUNDAY,
        }
        current_weekday = weekday_map[target_date.weekday()]
        
        if template.frequency == LSWFrequency.WEEKLY:
            if template.days_of_week:
                return current_weekday in template.days_of_week
            # Default to Monday for weekly items without day specified
            return target_date.weekday() == 0
        
        if template.frequency == LSWFrequency.BI_WEEKLY:
            # Every other week - use ISO week number
            if template.days_of_week and current_weekday not in template.days_of_week:
                return False
            return target_date.isocalendar()[1] % 2 == 0
        
        if template.frequency == LSWFrequency.MONTHLY:
            if template.day_of_month:
                return target_date.day == template.day_of_month
            if template.week_of_month:
                week_num = (target_date.day - 1) // 7 + 1
                if week_num != template.week_of_month:
                    return False
                if template.days_of_week:
                    return current_weekday in template.days_of_week
                return target_date.weekday() == 0
            # Default to first day of month
            return target_date.day == 1
        
        if template.frequency == LSWFrequency.QUARTERLY:
            # First Monday of each quarter
            is_quarter_start_month = target_date.month in [1, 4, 7, 10]
            if not is_quarter_start_month:
                return False
            # First Monday
            first_of_month = target_date.replace(day=1)
            days_until_monday = (7 - first_of_month.weekday()) % 7
            first_monday = first_of_month + timedelta(days=days_until_monday)
            return target_date == first_monday
        
        if template.frequency == LSWFrequency.ANNUAL:
            # First day of year
            return target_date.month == 1 and target_date.day == 1
        
        return False
    
    def generate_week_checklists(
        self,
        owner_id: str,
        start_date: date,
    ) -> list[LSWGenerationResult]:
        """Generate checklists for a full week."""
        results = []
        for i in range(7):
            target_date = start_date + timedelta(days=i)
            result = self.generate_checklist(owner_id, target_date)
            if result.generated_count > 0:
                results.append(result)
        return results
    
    # --------------------------------------------------------------------------
    # Checklist Retrieval
    # --------------------------------------------------------------------------
    
    def get_checklist(
        self,
        owner_id: str,
        target_date: date,
    ) -> LSWChecklist | None:
        """Get checklist for a specific owner and date."""
        for checklist in self._checklists.values():
            if checklist.owner_id == owner_id and checklist.date == target_date:
                return checklist
        return None
    
    def get_instance(self, instance_id: str) -> LSWChecklistInstance | None:
        """Get a checklist instance by ID."""
        return self._instances.get(instance_id)
    
    def get_pending_items(
        self,
        owner_id: str,
        include_overdue: bool = True,
    ) -> list[LSWChecklistInstance]:
        """Get all pending items for an owner."""
        today = date.today()
        items = []
        
        for instance in self._instances.values():
            checklist = self._get_checklist_for_instance(instance)
            if checklist and checklist.owner_id != owner_id:
                continue
            
            if instance.status in [LSWItemStatus.PENDING, LSWItemStatus.DUE]:
                items.append(instance)
            elif include_overdue and instance.status == LSWItemStatus.OVERDUE:
                items.append(instance)
        
        return sorted(items, key=lambda x: x.scheduled_date)
    
    def get_overdue_items(self, owner_id: str | None = None) -> list[LSWChecklistInstance]:
        """Get all overdue items."""
        today = date.today()
        items = []
        
        for instance in self._instances.values():
            if instance.status not in [LSWItemStatus.COMPLETED, LSWItemStatus.SKIPPED]:
                if instance.scheduled_date < today:
                    if owner_id:
                        checklist = self._get_checklist_for_instance(instance)
                        if checklist and checklist.owner_id == owner_id:
                            items.append(instance)
                    else:
                        items.append(instance)
        
        return items
    
    def _get_checklist_for_instance(self, instance: LSWChecklistInstance) -> LSWChecklist | None:
        """Find the checklist containing an instance."""
        for checklist in self._checklists.values():
            if any(i.id == instance.id for i in checklist.items):
                return checklist
        return None
    
    # --------------------------------------------------------------------------
    # Instance Actions
    # --------------------------------------------------------------------------
    
    def start_item(
        self,
        instance_id: str,
    ) -> LSWChecklistInstance | None:
        """Mark an item as in progress."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        instance.status = LSWItemStatus.IN_PROGRESS
        instance.started_at = datetime.now()
        return instance
    
    def complete_item(
        self,
        instance_id: str,
        completed_by_id: str,
        notes: str = "",
        evidence_attachment_ids: list[str] | None = None,
        actual_duration_minutes: int | None = None,
        findings: list[dict[str, Any]] | None = None,
    ) -> LSWChecklistInstance | None:
        """Mark an item as complete."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        instance.status = LSWItemStatus.COMPLETED
        instance.completed_at = datetime.now()
        instance.completed_by_id = completed_by_id
        instance.notes = notes
        
        if evidence_attachment_ids:
            instance.evidence_attachment_ids = evidence_attachment_ids
        
        if actual_duration_minutes:
            instance.actual_duration_minutes = actual_duration_minutes
        elif instance.started_at:
            # Calculate from start time
            delta = datetime.now() - instance.started_at
            instance.actual_duration_minutes = int(delta.total_seconds() / 60)
        
        if findings:
            instance.findings = findings
        
        # Update checklist totals
        self._update_checklist_totals(instance)
        
        return instance
    
    def complete_sub_item(
        self,
        instance_id: str,
        sub_item: str,
    ) -> LSWChecklistInstance | None:
        """Mark a sub-item as complete."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        if sub_item not in instance.sub_items_completed:
            instance.sub_items_completed.append(sub_item)
        
        return instance
    
    def skip_item(
        self,
        instance_id: str,
        reason: str,
    ) -> LSWChecklistInstance | None:
        """Skip an item with a reason."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        instance.status = LSWItemStatus.SKIPPED
        instance.skip_reason = reason
        instance.completed_at = datetime.now()
        
        self._update_checklist_totals(instance)
        
        return instance
    
    def defer_item(
        self,
        instance_id: str,
        defer_to: date,
        reason: str = "",
    ) -> LSWChecklistInstance | None:
        """Defer an item to a later date."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        instance.status = LSWItemStatus.DEFERRED
        instance.deferred_to = defer_to
        instance.skip_reason = reason
        
        return instance
    
    def add_finding(
        self,
        instance_id: str,
        finding: dict[str, Any],
    ) -> LSWChecklistInstance | None:
        """Add a finding/observation to an item."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        instance.findings.append(finding)
        return instance
    
    def link_generated_task(
        self,
        instance_id: str,
        task_id: str,
    ) -> LSWChecklistInstance | None:
        """Link a task generated from this LSW item."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        if task_id not in instance.generated_task_ids:
            instance.generated_task_ids.append(task_id)
        
        return instance
    
    def link_generated_a3(
        self,
        instance_id: str,
        a3_id: str,
    ) -> LSWChecklistInstance | None:
        """Link an A3 generated from this LSW item."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        if a3_id not in instance.generated_a3_ids:
            instance.generated_a3_ids.append(a3_id)
        
        return instance
    
    def _update_checklist_totals(self, instance: LSWChecklistInstance) -> None:
        """Update checklist summary after an item changes."""
        checklist = self._get_checklist_for_instance(instance)
        if not checklist:
            return
        
        completed = sum(1 for i in checklist.items if i.status == LSWItemStatus.COMPLETED)
        skipped = sum(1 for i in checklist.items if i.status == LSWItemStatus.SKIPPED)
        overdue = sum(1 for i in checklist.items if i.status == LSWItemStatus.OVERDUE)
        
        checklist.completed_count = completed
        checklist.skipped_count = skipped
        checklist.overdue_count = overdue
        
        total_actual = sum(
            i.actual_duration_minutes or 0
            for i in checklist.items
            if i.status == LSWItemStatus.COMPLETED
        )
        checklist.total_actual_minutes = total_actual
    
    # --------------------------------------------------------------------------
    # Status Updates
    # --------------------------------------------------------------------------
    
    def update_overdue_items(self) -> list[LSWChecklistInstance]:
        """Mark past-due items as overdue."""
        today = date.today()
        updated = []
        
        for instance in self._instances.values():
            if instance.status in [LSWItemStatus.PENDING, LSWItemStatus.DUE]:
                if instance.scheduled_date < today:
                    instance.status = LSWItemStatus.OVERDUE
                    updated.append(instance)
                elif instance.scheduled_date == today:
                    if instance.status == LSWItemStatus.PENDING:
                        instance.status = LSWItemStatus.DUE
        
        return updated
    
    def get_due_reminders(self) -> list[LSWReminder]:
        """Get reminders that are due to be sent."""
        now = datetime.now()
        due = []
        
        for reminder in self._reminders.values():
            if not reminder.sent and reminder.reminder_time <= now:
                due.append(reminder)
        
        return due
    
    def mark_reminder_sent(self, reminder_id: str) -> LSWReminder | None:
        """Mark a reminder as sent."""
        reminder = self._reminders.get(reminder_id)
        if reminder:
            reminder.sent = True
            reminder.sent_at = datetime.now()
        return reminder
    
    # --------------------------------------------------------------------------
    # Analytics
    # --------------------------------------------------------------------------
    
    def get_compliance_stats(
        self,
        owner_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Get LSW compliance statistics for a date range."""
        total = 0
        completed = 0
        skipped = 0
        on_time = 0
        
        by_category: dict[str, dict[str, int]] = {}
        
        for checklist in self._checklists.values():
            if checklist.owner_id != owner_id:
                continue
            if checklist.date < start_date or checklist.date > end_date:
                continue
            
            for item in checklist.items:
                template = self._templates.get(item.template_id)
                if not template:
                    continue
                
                total += 1
                
                cat_key = template.category.value
                if cat_key not in by_category:
                    by_category[cat_key] = {"total": 0, "completed": 0, "on_time": 0}
                by_category[cat_key]["total"] += 1
                
                if item.status == LSWItemStatus.COMPLETED:
                    completed += 1
                    by_category[cat_key]["completed"] += 1
                    
                    # Check if completed on scheduled date
                    if item.completed_at and item.completed_at.date() <= item.scheduled_date:
                        on_time += 1
                        by_category[cat_key]["on_time"] += 1
                
                elif item.status == LSWItemStatus.SKIPPED:
                    skipped += 1
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        on_time_rate = (on_time / completed * 100) if completed > 0 else 0
        
        return {
            "owner_id": owner_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_items": total,
            "completed": completed,
            "skipped": skipped,
            "pending": total - completed - skipped,
            "completion_rate": round(completion_rate, 1),
            "on_time_rate": round(on_time_rate, 1),
            "by_category": by_category,
        }
    
    def get_findings_summary(
        self,
        owner_id: str | None,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Get all findings from LSW items in a date range."""
        findings = []
        
        for checklist in self._checklists.values():
            if owner_id and checklist.owner_id != owner_id:
                continue
            if checklist.date < start_date or checklist.date > end_date:
                continue
            
            for item in checklist.items:
                for finding in item.findings:
                    findings.append({
                        "date": checklist.date.isoformat(),
                        "owner_id": checklist.owner_id,
                        "item_id": item.id,
                        "template_id": item.template_id,
                        **finding,
                    })
        
        return findings


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def build_lsw_template(
    name: str,
    description: str,
    category: str,
    frequency: str,
    **kwargs: Any,
) -> LSWChecklistTemplate:
    """Build an LSW template from parameters."""
    return LSWChecklistTemplate(
        id=kwargs.get("id", str(uuid4())),
        name=name,
        description=description,
        category=LSWCategory(category),
        frequency=LSWFrequency(frequency),
        estimated_duration_minutes=kwargs.get("estimated_duration_minutes", 15),
        required=kwargs.get("required", True),
        preferred_time=kwargs.get("preferred_time"),
        days_of_week=[DayOfWeek(d) for d in kwargs.get("days_of_week", [])],
        day_of_month=kwargs.get("day_of_month"),
        week_of_month=kwargs.get("week_of_month"),
        role_id=kwargs.get("role_id"),
        owner_id=kwargs.get("owner_id"),
        requires_notes=kwargs.get("requires_notes", False),
        requires_evidence=kwargs.get("requires_evidence", False),
        evidence_prompt=kwargs.get("evidence_prompt", ""),
        sub_items=kwargs.get("sub_items", []),
        linked_area_id=kwargs.get("linked_area_id"),
        linked_kpi_id=kwargs.get("linked_kpi_id"),
        is_active=kwargs.get("is_active", True),
        effective_from=kwargs.get("effective_from"),
        effective_until=kwargs.get("effective_until"),
        custom_fields=kwargs.get("custom_fields", {}),
    )


def get_default_template_ids() -> list[str]:
    """Get IDs of default LSW templates."""
    return [
        "daily-gemba",
        "daily-tier1",
        "daily-safety",
        "weekly-tier2",
        "weekly-coaching",
        "weekly-process-audit",
        "monthly-tier3",
        "monthly-standard-review",
        "monthly-training-check",
        "monthly-recognition",
    ]

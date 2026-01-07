"""
Digest & Snapshot Export Service.

Handles scheduled generation and export of digest documents:
- Daily "Today Snapshot" PDF for each manager
- Weekly "Week in Review" / "HQ Share Pack" PDF
- Obeya Snapshot exports
- Configurable export schedules and recipients
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, time
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
import hashlib


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class DigestType(str, Enum):
    """Types of digest exports."""
    
    TODAY_SNAPSHOT = "today_snapshot"
    WEEK_IN_REVIEW = "week_in_review"
    OBEYA_SNAPSHOT = "obeya_snapshot"
    HQ_SHARE_PACK = "hq_share_pack"
    MONTHLY_SUMMARY = "monthly_summary"
    CUSTOM = "custom"


class DigestFrequency(str, Enum):
    """Frequency of digest generation."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


class DigestDeliveryChannel(str, Enum):
    """Channels for digest delivery."""
    
    IN_APP = "in_app"
    EMAIL = "email"
    STORAGE = "storage"  # Save to S3/storage
    WEBHOOK = "webhook"


class DigestStatus(str, Enum):
    """Status of a digest generation job."""
    
    SCHEDULED = "scheduled"
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class DigestFormat(str, Enum):
    """Output format for digests."""
    
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    EXCEL = "excel"


class WeekDay(str, Enum):
    """Days of the week for scheduling."""
    
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# --------------------------------------------------------------------------
# Data Classes
# --------------------------------------------------------------------------

@dataclass
class DigestSchedule:
    """Schedule configuration for digest generation."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    frequency: DigestFrequency = DigestFrequency.DAILY
    
    # Daily schedule
    time_of_day: time = field(default_factory=lambda: time(6, 0))  # 6:00 AM default
    timezone: str = "Africa/Casablanca"
    
    # Weekly/monthly specific
    day_of_week: WeekDay | None = None  # For weekly
    day_of_month: int | None = None  # For monthly (1-28)
    
    # Control
    is_active: bool = True
    skip_weekends: bool = False
    skip_holidays: bool = False
    
    # Next run tracking
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None


@dataclass
class DigestRecipient:
    """Recipient configuration for digest delivery."""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    email: str = ""
    name: str = ""
    
    # Delivery preferences
    channels: list[DigestDeliveryChannel] = field(
        default_factory=lambda: [DigestDeliveryChannel.IN_APP]
    )
    format_preference: DigestFormat = DigestFormat.PDF
    
    # Filters
    include_sections: list[str] = field(default_factory=list)  # Empty = all
    exclude_sections: list[str] = field(default_factory=list)
    
    # Control
    is_active: bool = True
    last_delivered_at: datetime | None = None


@dataclass
class DigestSection:
    """A section within a digest."""
    
    id: str
    title: str
    content_type: str  # "priorities", "risks", "commitments", etc.
    order: int
    
    # Content data
    data: dict[str, Any] = field(default_factory=dict)
    
    # Display options
    include_in_toc: bool = True
    page_break_before: bool = False
    max_items: int | None = None
    
    # Status
    is_empty: bool = False


@dataclass
class TodayDigestContent:
    """Content for a Today Snapshot digest."""
    
    user_id: UUID
    user_name: str
    snapshot_date: date
    
    # Top priorities (max 3)
    top_priorities: list[dict[str, Any]] = field(default_factory=list)
    
    # Risks by category
    risks_by_category: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    top_risks: list[dict[str, Any]] = field(default_factory=list)
    
    # Commitments
    overdue_commitments: list[dict[str, Any]] = field(default_factory=list)
    due_today_commitments: list[dict[str, Any]] = field(default_factory=list)
    upcoming_commitments: list[dict[str, Any]] = field(default_factory=list)
    
    # Abnormalities
    abnormality_counts: dict[str, int] = field(default_factory=dict)
    critical_abnormalities: list[dict[str, Any]] = field(default_factory=list)
    
    # LSW status
    lsw_completion_rate: float = 0.0
    lsw_overdue_items: list[dict[str, Any]] = field(default_factory=list)
    
    # Quick metrics
    metrics: list[dict[str, Any]] = field(default_factory=list)
    
    # Greeting
    greeting: str = ""


@dataclass
class WeekInReviewContent:
    """Content for a Week in Review / HQ Share Pack digest."""
    
    period_start: date
    period_end: date
    generated_by: UUID
    generated_by_name: str
    
    # Executive summary
    executive_summary: str = ""
    key_highlights: list[str] = field(default_factory=list)
    key_concerns: list[str] = field(default_factory=list)
    
    # Pipeline metrics
    pipeline_summary: dict[str, Any] = field(default_factory=dict)
    new_opportunities: int = 0
    closed_won: int = 0
    closed_lost: int = 0
    pipeline_value: float = 0.0
    pipeline_change: float = 0.0
    
    # Quote metrics
    quotes_issued: int = 0
    quotes_pending: int = 0
    quote_cycle_time_avg_days: float = 0.0
    win_rate: float = 0.0
    
    # RFQ metrics
    rfqs_received: int = 0
    rfqs_completed: int = 0
    rfq_completeness_avg: float = 0.0
    
    # Quality/Risk summary
    open_risks: list[dict[str, Any]] = field(default_factory=list)
    new_risks: int = 0
    closed_risks: int = 0
    
    # A3/Problem solving
    open_a3s: list[dict[str, Any]] = field(default_factory=list)
    a3s_closed: int = 0
    a3s_opened: int = 0
    
    # Obeya red items
    obeya_red_items: list[dict[str, Any]] = field(default_factory=list)
    
    # LSW adherence
    lsw_completion_rates: dict[str, float] = field(default_factory=dict)
    
    # Actions for next week
    next_week_priorities: list[str] = field(default_factory=list)


@dataclass
class ObeyaDigestContent:
    """Content for an Obeya Snapshot digest."""
    
    snapshot_date: date
    
    # SQDCP categories
    safety_items: list[dict[str, Any]] = field(default_factory=list)
    quality_items: list[dict[str, Any]] = field(default_factory=list)
    delivery_items: list[dict[str, Any]] = field(default_factory=list)
    cost_items: list[dict[str, Any]] = field(default_factory=list)
    people_items: list[dict[str, Any]] = field(default_factory=list)
    
    # Red item summary
    red_item_count: int = 0
    red_items: list[dict[str, Any]] = field(default_factory=list)
    
    # Trends
    trends: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    
    # Countermeasures due
    countermeasures_due: list[dict[str, Any]] = field(default_factory=list)
    countermeasures_overdue: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DigestConfiguration:
    """Full configuration for a digest subscription."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    digest_type: DigestType = DigestType.TODAY_SNAPSHOT
    
    # Schedule
    schedule: DigestSchedule = field(default_factory=DigestSchedule)
    
    # Recipients
    recipients: list[DigestRecipient] = field(default_factory=list)
    
    # Content configuration
    sections: list[str] = field(default_factory=list)  # Section IDs to include
    custom_branding: dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    
    # Filters
    account_filter: list[UUID] | None = None  # Filter by accounts
    owner_filter: list[UUID] | None = None  # Filter by owners
    date_range_days: int = 7  # For historical data
    
    # Control
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: UUID | None = None
    updated_at: datetime | None = None


@dataclass
class GeneratedDigest:
    """A generated digest document."""
    
    id: UUID = field(default_factory=uuid4)
    configuration_id: UUID | None = None
    digest_type: DigestType = DigestType.TODAY_SNAPSHOT
    
    # Content
    title: str = ""
    content_base64: str = ""
    content_hash: str = ""
    format: DigestFormat = DigestFormat.PDF
    size_bytes: int = 0
    page_count: int = 0
    
    # Period
    period_start: date | None = None
    period_end: date | None = None
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generated_by: UUID | None = None
    generation_time_ms: float = 0.0
    
    # Status
    status: DigestStatus = DigestStatus.COMPLETED
    error_message: str = ""
    
    # Storage
    storage_path: str = ""
    expires_at: datetime | None = None
    
    # Delivery tracking
    delivery_status: dict[str, str] = field(default_factory=dict)  # recipient_id -> status


@dataclass
class DigestJob:
    """A scheduled digest generation job."""
    
    # Required fields first (no defaults)
    configuration_id: UUID
    scheduled_at: datetime
    
    # Fields with defaults
    id: UUID = field(default_factory=uuid4)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Status
    status: DigestStatus = DigestStatus.SCHEDULED
    retry_count: int = 0
    max_retries: int = 3
    error_message: str = ""
    
    # Result
    digest_id: UUID | None = None


@dataclass
class DigestDeliveryResult:
    """Result of digest delivery to a recipient."""
    
    # Required fields first (no defaults)
    digest_id: UUID
    recipient_id: UUID
    channel: DigestDeliveryChannel
    
    # Fields with defaults
    id: UUID = field(default_factory=uuid4)
    delivered_at: datetime | None = None
    
    # Status
    success: bool = False
    error_message: str = ""
    
    # Email specific
    email_message_id: str = ""


# --------------------------------------------------------------------------
# Section Builders
# --------------------------------------------------------------------------

def _build_priorities_section(
    priorities: list[dict[str, Any]],
    max_items: int = 3,
) -> DigestSection:
    """Build the Top Priorities section."""
    items = priorities[:max_items]
    return DigestSection(
        id="priorities",
        title="Top Priorities",
        content_type="priorities",
        order=1,
        data={
            "items": items,
            "total_count": len(priorities),
        },
        is_empty=len(items) == 0,
    )


def _build_risks_section(
    risks: list[dict[str, Any]],
    risks_by_category: dict[str, list[dict[str, Any]]],
    max_items: int = 10,
) -> DigestSection:
    """Build the Risks section."""
    return DigestSection(
        id="risks",
        title="Top Risks",
        content_type="risks",
        order=2,
        data={
            "items": risks[:max_items],
            "by_category": risks_by_category,
            "total_count": len(risks),
        },
        is_empty=len(risks) == 0,
    )


def _build_commitments_section(
    overdue: list[dict[str, Any]],
    due_today: list[dict[str, Any]],
    upcoming: list[dict[str, Any]],
) -> DigestSection:
    """Build the Commitments section."""
    return DigestSection(
        id="commitments",
        title="Commitments",
        content_type="commitments",
        order=3,
        data={
            "overdue": overdue,
            "due_today": due_today,
            "upcoming": upcoming,
            "overdue_count": len(overdue),
            "due_today_count": len(due_today),
            "upcoming_count": len(upcoming),
        },
        is_empty=len(overdue) + len(due_today) + len(upcoming) == 0,
    )


def _build_abnormalities_section(
    counts: dict[str, int],
    critical: list[dict[str, Any]],
) -> DigestSection:
    """Build the Abnormalities section."""
    total_count = sum(counts.values())
    return DigestSection(
        id="abnormalities",
        title="Abnormalities",
        content_type="abnormalities",
        order=4,
        data={
            "counts": counts,
            "critical": critical,
            "total_count": total_count,
        },
        is_empty=total_count == 0,
    )


def _build_lsw_section(
    completion_rate: float,
    overdue_items: list[dict[str, Any]],
) -> DigestSection:
    """Build the LSW Checklist section."""
    return DigestSection(
        id="lsw",
        title="Leadership Standard Work",
        content_type="lsw",
        order=5,
        data={
            "completion_rate": completion_rate,
            "overdue_items": overdue_items,
            "overdue_count": len(overdue_items),
        },
        is_empty=False,  # Always show LSW status
    )


def _build_metrics_section(
    metrics: list[dict[str, Any]],
) -> DigestSection:
    """Build the Quick Metrics section."""
    return DigestSection(
        id="metrics",
        title="Key Metrics",
        content_type="metrics",
        order=6,
        data={
            "items": metrics,
        },
        is_empty=len(metrics) == 0,
    )


def _build_pipeline_section(
    summary: dict[str, Any],
) -> DigestSection:
    """Build the Pipeline Summary section."""
    return DigestSection(
        id="pipeline",
        title="Pipeline Summary",
        content_type="pipeline",
        order=1,
        data=summary,
        page_break_before=False,
        is_empty=False,
    )


def _build_obeya_section(
    red_items: list[dict[str, Any]],
    by_category: dict[str, list[dict[str, Any]]],
) -> DigestSection:
    """Build the Obeya Summary section."""
    return DigestSection(
        id="obeya",
        title="Obeya Red Items",
        content_type="obeya",
        order=7,
        data={
            "red_items": red_items,
            "by_category": by_category,
            "red_count": len(red_items),
        },
        is_empty=len(red_items) == 0,
    )


def _build_a3_section(
    open_a3s: list[dict[str, Any]],
    opened: int,
    closed: int,
) -> DigestSection:
    """Build the A3/Problem Solving section."""
    return DigestSection(
        id="a3",
        title="Problem Solving (A3)",
        content_type="a3",
        order=8,
        data={
            "open_items": open_a3s,
            "opened_this_period": opened,
            "closed_this_period": closed,
            "open_count": len(open_a3s),
        },
        is_empty=len(open_a3s) == 0 and opened == 0 and closed == 0,
    )


# --------------------------------------------------------------------------
# Digest Export Service
# --------------------------------------------------------------------------

class DigestExportService:
    """
    Service for managing digest configurations, scheduling, and generation.
    
    Provides:
    - Digest configuration management
    - Schedule management
    - Content generation
    - Delivery orchestration
    """
    
    def __init__(self) -> None:
        """Initialize the digest export service."""
        self._configurations: dict[UUID, DigestConfiguration] = {}
        self._digests: dict[UUID, GeneratedDigest] = {}
        self._jobs: dict[UUID, DigestJob] = {}
        self._delivery_results: dict[UUID, list[DigestDeliveryResult]] = {}
    
    # --------------------------------------------------------------------------
    # Configuration Management
    # --------------------------------------------------------------------------
    
    def create_configuration(
        self,
        name: str,
        digest_type: DigestType,
        schedule: DigestSchedule,
        recipients: list[DigestRecipient],
        *,
        description: str = "",
        sections: list[str] | None = None,
        language: str = "en",
        created_by: UUID | None = None,
    ) -> DigestConfiguration:
        """Create a new digest configuration."""
        config = DigestConfiguration(
            name=name,
            description=description,
            digest_type=digest_type,
            schedule=schedule,
            recipients=recipients,
            sections=sections or [],
            language=language,
            created_by=created_by,
        )
        
        # Calculate next run time
        config.schedule.next_run_at = self._calculate_next_run(config.schedule)
        
        self._configurations[config.id] = config
        return config
    
    def get_configuration(self, config_id: UUID) -> DigestConfiguration | None:
        """Get a digest configuration by ID."""
        return self._configurations.get(config_id)
    
    def update_configuration(
        self,
        config_id: UUID,
        updates: dict[str, Any],
    ) -> DigestConfiguration | None:
        """Update a digest configuration."""
        config = self._configurations.get(config_id)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.utcnow()
        
        # Recalculate next run if schedule changed
        if "schedule" in updates:
            config.schedule.next_run_at = self._calculate_next_run(config.schedule)
        
        return config
    
    def delete_configuration(self, config_id: UUID) -> bool:
        """Delete a digest configuration."""
        if config_id not in self._configurations:
            return False
        
        del self._configurations[config_id]
        return True
    
    def list_configurations(
        self,
        digest_type: DigestType | None = None,
        active_only: bool = True,
        created_by: UUID | None = None,
    ) -> list[DigestConfiguration]:
        """List digest configurations with optional filters."""
        configs = list(self._configurations.values())
        
        if digest_type:
            configs = [c for c in configs if c.digest_type == digest_type]
        
        if active_only:
            configs = [c for c in configs if c.is_active]
        
        if created_by:
            configs = [c for c in configs if c.created_by == created_by]
        
        return configs
    
    # --------------------------------------------------------------------------
    # Recipient Management
    # --------------------------------------------------------------------------
    
    def add_recipient(
        self,
        config_id: UUID,
        recipient: DigestRecipient,
    ) -> DigestConfiguration | None:
        """Add a recipient to a configuration."""
        config = self._configurations.get(config_id)
        if not config:
            return None
        
        config.recipients.append(recipient)
        config.updated_at = datetime.utcnow()
        return config
    
    def remove_recipient(
        self,
        config_id: UUID,
        recipient_id: UUID,
    ) -> DigestConfiguration | None:
        """Remove a recipient from a configuration."""
        config = self._configurations.get(config_id)
        if not config:
            return None
        
        config.recipients = [
            r for r in config.recipients if r.id != recipient_id
        ]
        config.updated_at = datetime.utcnow()
        return config
    
    def update_recipient(
        self,
        config_id: UUID,
        recipient_id: UUID,
        updates: dict[str, Any],
    ) -> DigestRecipient | None:
        """Update a recipient's settings."""
        config = self._configurations.get(config_id)
        if not config:
            return None
        
        for recipient in config.recipients:
            if recipient.id == recipient_id:
                for key, value in updates.items():
                    if hasattr(recipient, key):
                        setattr(recipient, key, value)
                config.updated_at = datetime.utcnow()
                return recipient
        
        return None
    
    # --------------------------------------------------------------------------
    # Schedule Management
    # --------------------------------------------------------------------------
    
    def _calculate_next_run(
        self,
        schedule: DigestSchedule,
        from_time: datetime | None = None,
    ) -> datetime:
        """Calculate the next run time for a schedule."""
        now = from_time or datetime.utcnow()
        
        # Start with today at the scheduled time
        next_run = datetime.combine(now.date(), schedule.time_of_day)
        
        # If we've already passed that time today, start from tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)
        
        if schedule.frequency == DigestFrequency.DAILY:
            # Skip weekends if configured
            if schedule.skip_weekends:
                while next_run.weekday() >= 5:  # Saturday=5, Sunday=6
                    next_run += timedelta(days=1)
        
        elif schedule.frequency == DigestFrequency.WEEKLY:
            if schedule.day_of_week:
                target_day = {
                    WeekDay.MONDAY: 0,
                    WeekDay.TUESDAY: 1,
                    WeekDay.WEDNESDAY: 2,
                    WeekDay.THURSDAY: 3,
                    WeekDay.FRIDAY: 4,
                    WeekDay.SATURDAY: 5,
                    WeekDay.SUNDAY: 6,
                }[schedule.day_of_week]
                
                days_ahead = target_day - next_run.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)
        
        elif schedule.frequency == DigestFrequency.BIWEEKLY:
            if schedule.day_of_week:
                target_day = {
                    WeekDay.MONDAY: 0,
                    WeekDay.TUESDAY: 1,
                    WeekDay.WEDNESDAY: 2,
                    WeekDay.THURSDAY: 3,
                    WeekDay.FRIDAY: 4,
                    WeekDay.SATURDAY: 5,
                    WeekDay.SUNDAY: 6,
                }[schedule.day_of_week]
                
                days_ahead = target_day - next_run.weekday()
                if days_ahead <= 0:
                    days_ahead += 14
                else:
                    # Still need to be 2 weeks out
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)
        
        elif schedule.frequency == DigestFrequency.MONTHLY:
            if schedule.day_of_month:
                day = min(schedule.day_of_month, 28)  # Cap at 28 for safety
                
                # Try this month first
                try:
                    next_run = next_run.replace(day=day)
                    if next_run <= now:
                        # Move to next month
                        if next_run.month == 12:
                            next_run = next_run.replace(year=next_run.year + 1, month=1)
                        else:
                            next_run = next_run.replace(month=next_run.month + 1)
                except ValueError:
                    # Invalid day for this month, try next month
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1, day=day)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1, day=day)
        
        return next_run
    
    def get_pending_jobs(
        self,
        as_of: datetime | None = None,
    ) -> list[DigestConfiguration]:
        """Get configurations that are due to run."""
        now = as_of or datetime.utcnow()
        
        pending = []
        for config in self._configurations.values():
            if not config.is_active:
                continue
            
            if config.schedule.next_run_at and config.schedule.next_run_at <= now:
                pending.append(config)
        
        return pending
    
    def update_schedule_after_run(
        self,
        config_id: UUID,
    ) -> DigestSchedule | None:
        """Update schedule after a successful run."""
        config = self._configurations.get(config_id)
        if not config:
            return None
        
        config.schedule.last_run_at = datetime.utcnow()
        config.schedule.next_run_at = self._calculate_next_run(config.schedule)
        
        return config.schedule
    
    # --------------------------------------------------------------------------
    # Content Generation
    # --------------------------------------------------------------------------
    
    def build_today_digest_content(
        self,
        user_id: UUID,
        user_name: str,
        snapshot_date: date,
        *,
        priorities: list[dict[str, Any]] | None = None,
        risks: list[dict[str, Any]] | None = None,
        risks_by_category: dict[str, list[dict[str, Any]]] | None = None,
        overdue_commitments: list[dict[str, Any]] | None = None,
        due_today_commitments: list[dict[str, Any]] | None = None,
        upcoming_commitments: list[dict[str, Any]] | None = None,
        abnormality_counts: dict[str, int] | None = None,
        critical_abnormalities: list[dict[str, Any]] | None = None,
        lsw_completion_rate: float = 0.0,
        lsw_overdue_items: list[dict[str, Any]] | None = None,
        metrics: list[dict[str, Any]] | None = None,
    ) -> TodayDigestContent:
        """Build content for a Today Snapshot digest."""
        # Generate greeting based on time of day
        hour = datetime.utcnow().hour
        if hour < 12:
            greeting = f"Good morning, {user_name}"
        elif hour < 17:
            greeting = f"Good afternoon, {user_name}"
        else:
            greeting = f"Good evening, {user_name}"
        
        return TodayDigestContent(
            user_id=user_id,
            user_name=user_name,
            snapshot_date=snapshot_date,
            top_priorities=priorities or [],
            risks_by_category=risks_by_category or {},
            top_risks=risks or [],
            overdue_commitments=overdue_commitments or [],
            due_today_commitments=due_today_commitments or [],
            upcoming_commitments=upcoming_commitments or [],
            abnormality_counts=abnormality_counts or {},
            critical_abnormalities=critical_abnormalities or [],
            lsw_completion_rate=lsw_completion_rate,
            lsw_overdue_items=lsw_overdue_items or [],
            metrics=metrics or [],
            greeting=greeting,
        )
    
    def build_week_in_review_content(
        self,
        period_start: date,
        period_end: date,
        generated_by: UUID,
        generated_by_name: str,
        *,
        executive_summary: str = "",
        key_highlights: list[str] | None = None,
        key_concerns: list[str] | None = None,
        pipeline_summary: dict[str, Any] | None = None,
        new_opportunities: int = 0,
        closed_won: int = 0,
        closed_lost: int = 0,
        pipeline_value: float = 0.0,
        pipeline_change: float = 0.0,
        quotes_issued: int = 0,
        quotes_pending: int = 0,
        quote_cycle_time_avg_days: float = 0.0,
        win_rate: float = 0.0,
        rfqs_received: int = 0,
        rfqs_completed: int = 0,
        rfq_completeness_avg: float = 0.0,
        open_risks: list[dict[str, Any]] | None = None,
        new_risks: int = 0,
        closed_risks: int = 0,
        open_a3s: list[dict[str, Any]] | None = None,
        a3s_closed: int = 0,
        a3s_opened: int = 0,
        obeya_red_items: list[dict[str, Any]] | None = None,
        lsw_completion_rates: dict[str, float] | None = None,
        next_week_priorities: list[str] | None = None,
    ) -> WeekInReviewContent:
        """Build content for a Week in Review digest."""
        return WeekInReviewContent(
            period_start=period_start,
            period_end=period_end,
            generated_by=generated_by,
            generated_by_name=generated_by_name,
            executive_summary=executive_summary,
            key_highlights=key_highlights or [],
            key_concerns=key_concerns or [],
            pipeline_summary=pipeline_summary or {},
            new_opportunities=new_opportunities,
            closed_won=closed_won,
            closed_lost=closed_lost,
            pipeline_value=pipeline_value,
            pipeline_change=pipeline_change,
            quotes_issued=quotes_issued,
            quotes_pending=quotes_pending,
            quote_cycle_time_avg_days=quote_cycle_time_avg_days,
            win_rate=win_rate,
            rfqs_received=rfqs_received,
            rfqs_completed=rfqs_completed,
            rfq_completeness_avg=rfq_completeness_avg,
            open_risks=open_risks or [],
            new_risks=new_risks,
            closed_risks=closed_risks,
            open_a3s=open_a3s or [],
            a3s_closed=a3s_closed,
            a3s_opened=a3s_opened,
            obeya_red_items=obeya_red_items or [],
            lsw_completion_rates=lsw_completion_rates or {},
            next_week_priorities=next_week_priorities or [],
        )
    
    def build_obeya_digest_content(
        self,
        snapshot_date: date,
        *,
        safety_items: list[dict[str, Any]] | None = None,
        quality_items: list[dict[str, Any]] | None = None,
        delivery_items: list[dict[str, Any]] | None = None,
        cost_items: list[dict[str, Any]] | None = None,
        people_items: list[dict[str, Any]] | None = None,
        red_items: list[dict[str, Any]] | None = None,
        trends: dict[str, list[dict[str, Any]]] | None = None,
        countermeasures_due: list[dict[str, Any]] | None = None,
        countermeasures_overdue: list[dict[str, Any]] | None = None,
    ) -> ObeyaDigestContent:
        """Build content for an Obeya Snapshot digest."""
        all_red_items = red_items or []
        
        return ObeyaDigestContent(
            snapshot_date=snapshot_date,
            safety_items=safety_items or [],
            quality_items=quality_items or [],
            delivery_items=delivery_items or [],
            cost_items=cost_items or [],
            people_items=people_items or [],
            red_item_count=len(all_red_items),
            red_items=all_red_items,
            trends=trends or {},
            countermeasures_due=countermeasures_due or [],
            countermeasures_overdue=countermeasures_overdue or [],
        )
    
    def build_sections_from_today_content(
        self,
        content: TodayDigestContent,
    ) -> list[DigestSection]:
        """Build digest sections from Today content."""
        sections = [
            _build_priorities_section(content.top_priorities),
            _build_risks_section(content.top_risks, content.risks_by_category),
            _build_commitments_section(
                content.overdue_commitments,
                content.due_today_commitments,
                content.upcoming_commitments,
            ),
            _build_abnormalities_section(
                content.abnormality_counts,
                content.critical_abnormalities,
            ),
            _build_lsw_section(
                content.lsw_completion_rate,
                content.lsw_overdue_items,
            ),
            _build_metrics_section(content.metrics),
        ]
        
        return [s for s in sections if not s.is_empty or s.id in ("lsw", "metrics")]
    
    def build_sections_from_week_content(
        self,
        content: WeekInReviewContent,
    ) -> list[DigestSection]:
        """Build digest sections from Week in Review content."""
        sections = [
            DigestSection(
                id="executive_summary",
                title="Executive Summary",
                content_type="summary",
                order=1,
                data={
                    "summary": content.executive_summary,
                    "highlights": content.key_highlights,
                    "concerns": content.key_concerns,
                },
                is_empty=not content.executive_summary,
            ),
            _build_pipeline_section({
                "new_opportunities": content.new_opportunities,
                "closed_won": content.closed_won,
                "closed_lost": content.closed_lost,
                "pipeline_value": content.pipeline_value,
                "pipeline_change": content.pipeline_change,
            }),
            DigestSection(
                id="quoting",
                title="Quoting Activity",
                content_type="quoting",
                order=3,
                data={
                    "quotes_issued": content.quotes_issued,
                    "quotes_pending": content.quotes_pending,
                    "cycle_time_avg_days": content.quote_cycle_time_avg_days,
                    "win_rate": content.win_rate,
                },
                is_empty=False,
            ),
            DigestSection(
                id="rfq",
                title="RFQ Activity",
                content_type="rfq",
                order=4,
                data={
                    "received": content.rfqs_received,
                    "completed": content.rfqs_completed,
                    "completeness_avg": content.rfq_completeness_avg,
                },
                is_empty=False,
            ),
            _build_risks_section(content.open_risks, {}),
            _build_a3_section(content.open_a3s, content.a3s_opened, content.a3s_closed),
            _build_obeya_section(content.obeya_red_items, {}),
            DigestSection(
                id="next_week",
                title="Priorities for Next Week",
                content_type="priorities",
                order=10,
                data={
                    "items": content.next_week_priorities,
                },
                is_empty=len(content.next_week_priorities) == 0,
            ),
        ]
        
        return sections
    
    # --------------------------------------------------------------------------
    # Digest Generation
    # --------------------------------------------------------------------------
    
    def generate_today_digest(
        self,
        content: TodayDigestContent,
        config: DigestConfiguration | None = None,
        generated_by: UUID | None = None,
    ) -> GeneratedDigest:
        """Generate a Today Snapshot digest."""
        start_time = datetime.utcnow()
        
        sections = self.build_sections_from_today_content(content)
        
        # Build content structure
        content_data = {
            "type": DigestType.TODAY_SNAPSHOT.value,
            "title": f"Today Snapshot - {content.snapshot_date.strftime('%B %d, %Y')}",
            "greeting": content.greeting,
            "user_name": content.user_name,
            "snapshot_date": content.snapshot_date.isoformat(),
            "sections": [
                {
                    "id": s.id,
                    "title": s.title,
                    "content_type": s.content_type,
                    "order": s.order,
                    "data": s.data,
                }
                for s in sections
            ],
        }
        
        # Simulate PDF content (in real implementation, use PDF library)
        content_json = str(content_data)
        content_base64 = hashlib.sha256(content_json.encode()).hexdigest()[:100]
        
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds() * 1000
        
        digest = GeneratedDigest(
            configuration_id=config.id if config else None,
            digest_type=DigestType.TODAY_SNAPSHOT,
            title=f"Today Snapshot - {content.snapshot_date.strftime('%B %d, %Y')}",
            content_base64=content_base64,
            content_hash=hashlib.sha256(content_base64.encode()).hexdigest(),
            format=DigestFormat.PDF,
            size_bytes=len(content_base64),
            page_count=max(1, len(sections)),
            period_start=content.snapshot_date,
            period_end=content.snapshot_date,
            generated_by=generated_by or content.user_id,
            generation_time_ms=generation_time,
            status=DigestStatus.COMPLETED,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        
        self._digests[digest.id] = digest
        return digest
    
    def generate_week_in_review_digest(
        self,
        content: WeekInReviewContent,
        config: DigestConfiguration | None = None,
    ) -> GeneratedDigest:
        """Generate a Week in Review digest."""
        start_time = datetime.utcnow()
        
        sections = self.build_sections_from_week_content(content)
        
        # Build content structure
        content_data = {
            "type": DigestType.WEEK_IN_REVIEW.value,
            "title": f"Week in Review - {content.period_start.strftime('%b %d')} to {content.period_end.strftime('%b %d, %Y')}",
            "period_start": content.period_start.isoformat(),
            "period_end": content.period_end.isoformat(),
            "generated_by": content.generated_by_name,
            "sections": [
                {
                    "id": s.id,
                    "title": s.title,
                    "content_type": s.content_type,
                    "order": s.order,
                    "data": s.data,
                }
                for s in sections
            ],
        }
        
        content_json = str(content_data)
        content_base64 = hashlib.sha256(content_json.encode()).hexdigest()[:100]
        
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds() * 1000
        
        digest = GeneratedDigest(
            configuration_id=config.id if config else None,
            digest_type=DigestType.WEEK_IN_REVIEW,
            title=f"Week in Review - {content.period_start.strftime('%b %d')} to {content.period_end.strftime('%b %d, %Y')}",
            content_base64=content_base64,
            content_hash=hashlib.sha256(content_base64.encode()).hexdigest(),
            format=DigestFormat.PDF,
            size_bytes=len(content_base64),
            page_count=max(2, len(sections)),
            period_start=content.period_start,
            period_end=content.period_end,
            generated_by=content.generated_by,
            generation_time_ms=generation_time,
            status=DigestStatus.COMPLETED,
            expires_at=datetime.utcnow() + timedelta(days=90),
        )
        
        self._digests[digest.id] = digest
        return digest
    
    def generate_obeya_digest(
        self,
        content: ObeyaDigestContent,
        config: DigestConfiguration | None = None,
        generated_by: UUID | None = None,
    ) -> GeneratedDigest:
        """Generate an Obeya Snapshot digest."""
        start_time = datetime.utcnow()
        
        # Build sections
        sections = [
            DigestSection(
                id="sqdcp",
                title="SQDCP Overview",
                content_type="sqdcp",
                order=1,
                data={
                    "safety": content.safety_items,
                    "quality": content.quality_items,
                    "delivery": content.delivery_items,
                    "cost": content.cost_items,
                    "people": content.people_items,
                },
                is_empty=False,
            ),
            _build_obeya_section(content.red_items, {
                "safety": [i for i in content.safety_items if i.get("is_red")],
                "quality": [i for i in content.quality_items if i.get("is_red")],
                "delivery": [i for i in content.delivery_items if i.get("is_red")],
                "cost": [i for i in content.cost_items if i.get("is_red")],
                "people": [i for i in content.people_items if i.get("is_red")],
            }),
            DigestSection(
                id="countermeasures",
                title="Countermeasures",
                content_type="countermeasures",
                order=3,
                data={
                    "due": content.countermeasures_due,
                    "overdue": content.countermeasures_overdue,
                    "due_count": len(content.countermeasures_due),
                    "overdue_count": len(content.countermeasures_overdue),
                },
                is_empty=len(content.countermeasures_due) + len(content.countermeasures_overdue) == 0,
            ),
        ]
        
        content_data = {
            "type": DigestType.OBEYA_SNAPSHOT.value,
            "title": f"Obeya Snapshot - {content.snapshot_date.strftime('%B %d, %Y')}",
            "snapshot_date": content.snapshot_date.isoformat(),
            "red_item_count": content.red_item_count,
            "sections": [
                {
                    "id": s.id,
                    "title": s.title,
                    "content_type": s.content_type,
                    "order": s.order,
                    "data": s.data,
                }
                for s in sections
            ],
        }
        
        content_json = str(content_data)
        content_base64 = hashlib.sha256(content_json.encode()).hexdigest()[:100]
        
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds() * 1000
        
        digest = GeneratedDigest(
            configuration_id=config.id if config else None,
            digest_type=DigestType.OBEYA_SNAPSHOT,
            title=f"Obeya Snapshot - {content.snapshot_date.strftime('%B %d, %Y')}",
            content_base64=content_base64,
            content_hash=hashlib.sha256(content_base64.encode()).hexdigest(),
            format=DigestFormat.PDF,
            size_bytes=len(content_base64),
            page_count=max(1, len(sections)),
            period_start=content.snapshot_date,
            period_end=content.snapshot_date,
            generated_by=generated_by,
            generation_time_ms=generation_time,
            status=DigestStatus.COMPLETED,
            expires_at=datetime.utcnow() + timedelta(days=60),
        )
        
        self._digests[digest.id] = digest
        return digest
    
    def generate_hq_share_pack(
        self,
        week_content: WeekInReviewContent,
        obeya_content: ObeyaDigestContent,
        config: DigestConfiguration | None = None,
    ) -> GeneratedDigest:
        """Generate an HQ Share Pack (combined Week in Review + Obeya)."""
        start_time = datetime.utcnow()
        
        week_sections = self.build_sections_from_week_content(week_content)
        
        # Add obeya sections
        obeya_sections = [
            DigestSection(
                id="obeya_summary",
                title="Obeya Summary",
                content_type="obeya_summary",
                order=20,
                page_break_before=True,
                data={
                    "red_count": obeya_content.red_item_count,
                    "red_items": obeya_content.red_items[:5],  # Top 5
                    "countermeasures_overdue": len(obeya_content.countermeasures_overdue),
                },
                is_empty=False,
            ),
        ]
        
        all_sections = week_sections + obeya_sections
        
        content_data = {
            "type": DigestType.HQ_SHARE_PACK.value,
            "title": f"HQ Share Pack - Week of {week_content.period_start.strftime('%B %d, %Y')}",
            "period_start": week_content.period_start.isoformat(),
            "period_end": week_content.period_end.isoformat(),
            "sections": [
                {
                    "id": s.id,
                    "title": s.title,
                    "content_type": s.content_type,
                    "order": s.order,
                    "data": s.data,
                }
                for s in all_sections
            ],
        }
        
        content_json = str(content_data)
        content_base64 = hashlib.sha256(content_json.encode()).hexdigest()[:100]
        
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds() * 1000
        
        digest = GeneratedDigest(
            configuration_id=config.id if config else None,
            digest_type=DigestType.HQ_SHARE_PACK,
            title=f"HQ Share Pack - Week of {week_content.period_start.strftime('%B %d, %Y')}",
            content_base64=content_base64,
            content_hash=hashlib.sha256(content_base64.encode()).hexdigest(),
            format=DigestFormat.PDF,
            size_bytes=len(content_base64),
            page_count=max(4, len(all_sections)),
            period_start=week_content.period_start,
            period_end=week_content.period_end,
            generated_by=week_content.generated_by,
            generation_time_ms=generation_time,
            status=DigestStatus.COMPLETED,
            expires_at=datetime.utcnow() + timedelta(days=90),
        )
        
        self._digests[digest.id] = digest
        return digest
    
    # --------------------------------------------------------------------------
    # Digest Retrieval
    # --------------------------------------------------------------------------
    
    def get_digest(self, digest_id: UUID) -> GeneratedDigest | None:
        """Get a generated digest by ID."""
        return self._digests.get(digest_id)
    
    def list_digests(
        self,
        digest_type: DigestType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        generated_by: UUID | None = None,
        status: DigestStatus | None = None,
        limit: int = 50,
    ) -> list[GeneratedDigest]:
        """List generated digests with optional filters."""
        digests = list(self._digests.values())
        
        if digest_type:
            digests = [d for d in digests if d.digest_type == digest_type]
        
        if start_date:
            digests = [
                d for d in digests
                if d.period_start and d.period_start >= start_date
            ]
        
        if end_date:
            digests = [
                d for d in digests
                if d.period_end and d.period_end <= end_date
            ]
        
        if generated_by:
            digests = [d for d in digests if d.generated_by == generated_by]
        
        if status:
            digests = [d for d in digests if d.status == status]
        
        # Sort by generated_at descending
        digests = sorted(digests, key=lambda d: d.generated_at, reverse=True)
        
        return digests[:limit]
    
    def delete_digest(self, digest_id: UUID) -> bool:
        """Delete a generated digest."""
        if digest_id not in self._digests:
            return False
        
        del self._digests[digest_id]
        return True
    
    def cleanup_expired_digests(self) -> int:
        """Remove expired digests and return count removed."""
        now = datetime.utcnow()
        expired_ids = [
            digest_id
            for digest_id, digest in self._digests.items()
            if digest.expires_at and digest.expires_at < now
        ]
        
        for digest_id in expired_ids:
            del self._digests[digest_id]
        
        return len(expired_ids)
    
    # --------------------------------------------------------------------------
    # Job Management
    # --------------------------------------------------------------------------
    
    def create_job(
        self,
        config_id: UUID,
        scheduled_at: datetime,
    ) -> DigestJob:
        """Create a digest generation job."""
        job = DigestJob(
            configuration_id=config_id,
            scheduled_at=scheduled_at,
            status=DigestStatus.SCHEDULED,
        )
        
        self._jobs[job.id] = job
        return job
    
    def get_job(self, job_id: UUID) -> DigestJob | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def start_job(self, job_id: UUID) -> DigestJob | None:
        """Mark a job as started."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        job.status = DigestStatus.GENERATING
        job.started_at = datetime.utcnow()
        return job
    
    def complete_job(
        self,
        job_id: UUID,
        digest_id: UUID,
    ) -> DigestJob | None:
        """Mark a job as completed."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        job.status = DigestStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.digest_id = digest_id
        return job
    
    def fail_job(
        self,
        job_id: UUID,
        error_message: str,
    ) -> DigestJob | None:
        """Mark a job as failed."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        job.retry_count += 1
        
        if job.retry_count >= job.max_retries:
            job.status = DigestStatus.FAILED
        else:
            job.status = DigestStatus.PENDING  # Will retry
        
        job.error_message = error_message
        job.completed_at = datetime.utcnow()
        return job
    
    def list_jobs(
        self,
        config_id: UUID | None = None,
        status: DigestStatus | None = None,
        limit: int = 50,
    ) -> list[DigestJob]:
        """List jobs with optional filters."""
        jobs = list(self._jobs.values())
        
        if config_id:
            jobs = [j for j in jobs if j.configuration_id == config_id]
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by scheduled_at descending
        jobs = sorted(jobs, key=lambda j: j.scheduled_at, reverse=True)
        
        return jobs[:limit]
    
    # --------------------------------------------------------------------------
    # Delivery
    # --------------------------------------------------------------------------
    
    def record_delivery(
        self,
        digest_id: UUID,
        recipient_id: UUID,
        channel: DigestDeliveryChannel,
        success: bool,
        error_message: str = "",
        email_message_id: str = "",
    ) -> DigestDeliveryResult:
        """Record a delivery attempt."""
        result = DigestDeliveryResult(
            digest_id=digest_id,
            recipient_id=recipient_id,
            channel=channel,
            delivered_at=datetime.utcnow() if success else None,
            success=success,
            error_message=error_message,
            email_message_id=email_message_id,
        )
        
        if digest_id not in self._delivery_results:
            self._delivery_results[digest_id] = []
        
        self._delivery_results[digest_id].append(result)
        
        # Update digest delivery status
        digest = self._digests.get(digest_id)
        if digest:
            digest.delivery_status[str(recipient_id)] = "delivered" if success else "failed"
        
        return result
    
    def get_delivery_results(
        self,
        digest_id: UUID,
    ) -> list[DigestDeliveryResult]:
        """Get all delivery results for a digest."""
        return self._delivery_results.get(digest_id, [])
    
    # --------------------------------------------------------------------------
    # Statistics
    # --------------------------------------------------------------------------
    
    def get_statistics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get digest generation statistics."""
        digests = list(self._digests.values())
        
        if start_date:
            digests = [
                d for d in digests
                if d.generated_at.date() >= start_date
            ]
        
        if end_date:
            digests = [
                d for d in digests
                if d.generated_at.date() <= end_date
            ]
        
        # Count by type
        by_type: dict[str, int] = {}
        for digest in digests:
            type_key = digest.digest_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
        
        # Count by status
        by_status: dict[str, int] = {}
        for digest in digests:
            status_key = digest.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
        
        # Average generation time
        gen_times = [d.generation_time_ms for d in digests if d.generation_time_ms > 0]
        avg_gen_time = sum(gen_times) / len(gen_times) if gen_times else 0.0
        
        # Total size
        total_size = sum(d.size_bytes for d in digests)
        
        return {
            "total_digests": len(digests),
            "by_type": by_type,
            "by_status": by_status,
            "average_generation_time_ms": avg_gen_time,
            "total_size_bytes": total_size,
            "active_configurations": len([
                c for c in self._configurations.values() if c.is_active
            ]),
        }


# --------------------------------------------------------------------------
# Convenience Functions
# --------------------------------------------------------------------------

def create_daily_today_schedule(
    time_of_day: time = time(6, 0),
    timezone: str = "Africa/Casablanca",
    skip_weekends: bool = False,
) -> DigestSchedule:
    """Create a daily Today Snapshot schedule."""
    return DigestSchedule(
        name="Daily Today Snapshot",
        frequency=DigestFrequency.DAILY,
        time_of_day=time_of_day,
        timezone=timezone,
        skip_weekends=skip_weekends,
        is_active=True,
    )


def create_weekly_review_schedule(
    day_of_week: WeekDay = WeekDay.FRIDAY,
    time_of_day: time = time(17, 0),
    timezone: str = "Africa/Casablanca",
) -> DigestSchedule:
    """Create a weekly Week in Review schedule."""
    return DigestSchedule(
        name="Weekly Week in Review",
        frequency=DigestFrequency.WEEKLY,
        time_of_day=time_of_day,
        timezone=timezone,
        day_of_week=day_of_week,
        is_active=True,
    )


def create_monthly_summary_schedule(
    day_of_month: int = 1,
    time_of_day: time = time(9, 0),
    timezone: str = "Africa/Casablanca",
) -> DigestSchedule:
    """Create a monthly summary schedule."""
    return DigestSchedule(
        name="Monthly Summary",
        frequency=DigestFrequency.MONTHLY,
        time_of_day=time_of_day,
        timezone=timezone,
        day_of_month=day_of_month,
        is_active=True,
    )


def create_email_recipient(
    email: str,
    name: str,
    user_id: UUID | None = None,
) -> DigestRecipient:
    """Create an email recipient for digests."""
    return DigestRecipient(
        user_id=user_id,
        email=email,
        name=name,
        channels=[DigestDeliveryChannel.EMAIL, DigestDeliveryChannel.IN_APP],
        format_preference=DigestFormat.PDF,
        is_active=True,
    )


def create_in_app_recipient(
    user_id: UUID,
    name: str,
) -> DigestRecipient:
    """Create an in-app only recipient for digests."""
    return DigestRecipient(
        user_id=user_id,
        name=name,
        channels=[DigestDeliveryChannel.IN_APP],
        format_preference=DigestFormat.PDF,
        is_active=True,
    )

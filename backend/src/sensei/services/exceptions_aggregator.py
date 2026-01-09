"""
Exceptions Aggregator Service

Provides a unified view of all exceptions, red items, and critical alerts
across the entire system. Implements "Exceptions-First" dashboard navigation
to surface critical issues immediately.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class ExceptionSeverity(str, Enum):
    """Exception severity levels."""
    CRITICAL = "critical"  # Immediate action required (< 1 hour)
    HIGH = "high"          # Urgent (< 4 hours)
    MEDIUM = "medium"      # Important (< 24 hours)
    LOW = "low"            # Standard (< 1 week)


class ExceptionCategory(str, Enum):
    """Exception source categories."""
    ANDON = "andon"               # Shop floor alerts
    QUOTE = "quote"               # Quote issues
    PRODUCTION = "production"     # Production problems
    QUALITY = "quality"           # Quality issues (NCRs, CAPAs)
    A3 = "a3"                     # A3 escalations
    OBEYA = "obeya"               # Obeya item alerts
    TASK = "task"                 # Overdue tasks
    TRAINING = "training"         # Training gaps
    RFQ = "rfq"                   # RFQ issues
    APPROVAL = "approval"         # Pending approvals
    COMPLIANCE = "compliance"     # Compliance issues
    BACKUP = "backup"             # Backup failures


class ExceptionStatus(str, Enum):
    """Exception status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    BLOCKED = "blocked"


@dataclass
class ExceptionItem:
    """Represents a single exception/red item."""
    id: str
    title: str
    description: str
    category: ExceptionCategory
    severity: ExceptionSeverity
    status: ExceptionStatus
    created_at: datetime
    source: str = "manual"  # Track origin: "manual" or source name
    due_date: Optional[datetime] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    department: Optional[str] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    source_url: Optional[str] = None
    resolution_time_minutes: Optional[int] = None
    escalated_at: Optional[datetime] = None
    escalated_to: Optional[str] = None
    blocked_reason: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_overdue(self) -> bool:
        """Check if exception is past due date."""
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date
    
    @property
    def time_to_due(self) -> Optional[timedelta]:
        """Get time remaining until due."""
        if not self.due_date:
            return None
        return self.due_date - datetime.now(timezone.utc)
    
    @property
    def age_minutes(self) -> int:
        """Get age of exception in minutes."""
        delta = datetime.now(timezone.utc) - self.created_at
        return int(delta.total_seconds() / 60)
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score for sorting (higher = more urgent)."""
        score = 0
        
        # Severity weight (0-100)
        severity_weights = {
            ExceptionSeverity.CRITICAL: 100,
            ExceptionSeverity.HIGH: 70,
            ExceptionSeverity.MEDIUM: 40,
            ExceptionSeverity.LOW: 10,
        }
        score += severity_weights.get(self.severity, 0)
        
        # Overdue penalty (adds up to 50)
        if self.is_overdue and self.due_date:
            overdue_hours = (datetime.now(timezone.utc) - self.due_date).total_seconds() / 3600
            score += min(50, int(overdue_hours * 5))
        
        # Escalation bonus (add 30)
        if self.status == ExceptionStatus.ESCALATED:
            score += 30
        
        # Blocked bonus (add 20)
        if self.status == ExceptionStatus.BLOCKED:
            score += 20
        
        return score


@dataclass
class ExceptionSummary:
    """Summary of exceptions for navigation badges."""
    total_open: int = 0
    critical_count: int = 0
    high_count: int = 0
    overdue_count: int = 0
    escalated_count: int = 0
    blocked_count: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExceptionTrend:
    """Exception trend data for charts."""
    period: str  # e.g., "2026-01-08"
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    resolved: int = 0
    created: int = 0


@dataclass
class NavigationBadge:
    """Badge info for navigation items."""
    module: str
    count: int
    severity: ExceptionSeverity
    tooltip: str


ExceptionSource = Callable[[], list[ExceptionItem]]


class ExceptionsAggregator:
    """
    Aggregates exceptions from all system modules.
    
    Provides a unified view for the exceptions-first dashboard
    and navigation badges throughout the application.
    """
    
    def __init__(self):
        self._sources: dict[str, ExceptionSource] = {}
        self._exceptions: list[ExceptionItem] = []
        self._last_refresh: Optional[datetime] = None
        self._cache_ttl_seconds: int = 30
        self._listeners: list[Callable[[ExceptionSummary], None]] = []
    
    def register_source(
        self,
        name: str,
        source: ExceptionSource,
    ) -> None:
        """Register an exception source (e.g., andon, quality, etc.)."""
        self._sources[name] = source
    
    def unregister_source(self, name: str) -> None:
        """Unregister an exception source."""
        self._sources.pop(name, None)
    
    def add_listener(self, listener: Callable[[ExceptionSummary], None]) -> None:
        """Add a listener for exception updates."""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[ExceptionSummary], None]) -> None:
        """Remove a listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _notify_listeners(self, summary: ExceptionSummary) -> None:
        """Notify all listeners of updates."""
        for listener in self._listeners:
            try:
                listener(summary)
            except Exception:
                pass  # Don't let listener errors break the flow
    
    def refresh(self, force: bool = False) -> None:
        """Refresh exceptions from all sources."""
        now = datetime.now(timezone.utc)
        
        if not force and self._last_refresh:
            elapsed = (now - self._last_refresh).total_seconds()
            if elapsed < self._cache_ttl_seconds:
                return
        
        # Get IDs of manually added exceptions (those not from sources)
        manual_exceptions = [e for e in self._exceptions if e.source == "manual"]
        
        all_exceptions: list[ExceptionItem] = []
        
        for source_name, source_fn in self._sources.items():
            try:
                exceptions = source_fn()
                all_exceptions.extend(exceptions)
            except Exception:
                # Log error but continue with other sources
                pass
        
        # Preserve manually added exceptions
        all_exceptions.extend(manual_exceptions)
        
        # Sort by priority score (highest first)
        all_exceptions.sort(key=lambda e: e.priority_score, reverse=True)
        
        self._exceptions = all_exceptions
        self._last_refresh = now
        
        # Notify listeners
        summary = self._get_summary_internal()
        self._notify_listeners(summary)
    
    def add_exception(self, exception: ExceptionItem) -> None:
        """Add a new exception manually."""
        self._exceptions.append(exception)
        self._exceptions.sort(key=lambda e: e.priority_score, reverse=True)
        
        summary = self._get_summary_internal()
        self._notify_listeners(summary)
    
    def update_exception(
        self,
        exception_id: str,
        updates: dict[str, Any],
    ) -> Optional[ExceptionItem]:
        """Update an existing exception."""
        for exception in self._exceptions:
            if exception.id == exception_id:
                for key, value in updates.items():
                    if hasattr(exception, key):
                        setattr(exception, key, value)
                
                # Re-sort after update
                self._exceptions.sort(key=lambda e: e.priority_score, reverse=True)
                
                summary = self._get_summary_internal()
                self._notify_listeners(summary)
                
                return exception
        return None
    
    def resolve_exception(
        self,
        exception_id: str,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ExceptionItem]:
        """Mark an exception as resolved."""
        return self.update_exception(exception_id, {
            "status": ExceptionStatus.RESOLVED,
            "resolution_time_minutes": self._calculate_resolution_time(exception_id),
        })
    
    def escalate_exception(
        self,
        exception_id: str,
        escalate_to: str,
        reason: Optional[str] = None,
    ) -> Optional[ExceptionItem]:
        """Escalate an exception."""
        return self.update_exception(exception_id, {
            "status": ExceptionStatus.ESCALATED,
            "escalated_at": datetime.now(timezone.utc),
            "escalated_to": escalate_to,
        })
    
    def acknowledge_exception(self, exception_id: str) -> Optional[ExceptionItem]:
        """Acknowledge an exception."""
        return self.update_exception(exception_id, {
            "status": ExceptionStatus.ACKNOWLEDGED,
        })
    
    def _calculate_resolution_time(self, exception_id: str) -> int:
        """Calculate resolution time in minutes."""
        for exception in self._exceptions:
            if exception.id == exception_id:
                return exception.age_minutes
        return 0
    
    def get_all(
        self,
        category: Optional[ExceptionCategory] = None,
        severity: Optional[ExceptionSeverity] = None,
        status: Optional[ExceptionStatus] = None,
        overdue_only: bool = False,
        limit: int = 100,
    ) -> list[ExceptionItem]:
        """Get all exceptions with optional filters."""
        self.refresh()
        
        results = self._exceptions
        
        if category:
            results = [e for e in results if e.category == category]
        
        if severity:
            results = [e for e in results if e.severity == severity]
        
        if status:
            results = [e for e in results if e.status == status]
        
        if overdue_only:
            results = [e for e in results if e.is_overdue]
        
        return results[:limit]
    
    def get_critical(self, limit: int = 10) -> list[ExceptionItem]:
        """Get critical and high severity exceptions."""
        self.refresh()
        
        results = [
            e for e in self._exceptions
            if e.severity in (ExceptionSeverity.CRITICAL, ExceptionSeverity.HIGH)
            and e.status not in (ExceptionStatus.RESOLVED,)
        ]
        
        return results[:limit]
    
    def get_overdue(self, limit: int = 10) -> list[ExceptionItem]:
        """Get overdue exceptions."""
        return self.get_all(overdue_only=True, limit=limit)
    
    def get_escalated(self, limit: int = 10) -> list[ExceptionItem]:
        """Get escalated exceptions."""
        return self.get_all(status=ExceptionStatus.ESCALATED, limit=limit)
    
    def get_by_category(self, category: ExceptionCategory, limit: int = 20) -> list[ExceptionItem]:
        """Get exceptions by category."""
        return self.get_all(category=category, limit=limit)
    
    def _get_summary_internal(self) -> ExceptionSummary:
        """Get summary without triggering refresh (for internal use)."""
        open_exceptions = [
            e for e in self._exceptions
            if e.status not in (ExceptionStatus.RESOLVED,)
        ]
        
        by_category: dict[str, int] = {}
        for category in ExceptionCategory:
            count = len([e for e in open_exceptions if e.category == category])
            if count > 0:
                by_category[category.value] = count
        
        return ExceptionSummary(
            total_open=len(open_exceptions),
            critical_count=len([e for e in open_exceptions if e.severity == ExceptionSeverity.CRITICAL]),
            high_count=len([e for e in open_exceptions if e.severity == ExceptionSeverity.HIGH]),
            overdue_count=len([e for e in open_exceptions if e.is_overdue]),
            escalated_count=len([e for e in open_exceptions if e.status == ExceptionStatus.ESCALATED]),
            blocked_count=len([e for e in open_exceptions if e.status == ExceptionStatus.BLOCKED]),
            by_category=by_category,
            last_updated=datetime.now(timezone.utc),
        )
    
    def get_summary(self) -> ExceptionSummary:
        """Get summary of all exceptions for badges/navigation."""
        self.refresh()
        return self._get_summary_internal()
    
    def get_navigation_badges(self) -> list[NavigationBadge]:
        """Get badges for main navigation items."""
        self.refresh()
        
        badges: list[NavigationBadge] = []
        
        # Group by category and find highest severity
        category_data: dict[str, tuple[int, ExceptionSeverity]] = {}
        
        for exception in self._exceptions:
            if exception.status == ExceptionStatus.RESOLVED:
                continue
            
            cat = exception.category.value
            if cat not in category_data:
                category_data[cat] = (1, exception.severity)
            else:
                count, sev = category_data[cat]
                # Keep highest severity
                new_sev = sev
                if exception.severity == ExceptionSeverity.CRITICAL:
                    new_sev = ExceptionSeverity.CRITICAL
                elif exception.severity == ExceptionSeverity.HIGH and sev != ExceptionSeverity.CRITICAL:
                    new_sev = ExceptionSeverity.HIGH
                category_data[cat] = (count + 1, new_sev)
        
        # Map categories to navigation modules
        category_module_map = {
            "andon": "production",
            "production": "production",
            "quote": "quotes",
            "rfq": "pipeline",
            "quality": "quality",
            "a3": "a3",
            "obeya": "obeya",
            "task": "tasks",
            "training": "training",
            "approval": "approvals",
            "compliance": "compliance",
            "backup": "admin",
        }
        
        module_data: dict[str, tuple[int, ExceptionSeverity]] = {}
        
        for cat, (count, sev) in category_data.items():
            module = category_module_map.get(cat, cat)
            if module not in module_data:
                module_data[module] = (count, sev)
            else:
                existing_count, existing_sev = module_data[module]
                new_sev = existing_sev
                if sev == ExceptionSeverity.CRITICAL:
                    new_sev = ExceptionSeverity.CRITICAL
                elif sev == ExceptionSeverity.HIGH and existing_sev != ExceptionSeverity.CRITICAL:
                    new_sev = ExceptionSeverity.HIGH
                module_data[module] = (existing_count + count, new_sev)
        
        for module, (count, severity) in module_data.items():
            badges.append(NavigationBadge(
                module=module,
                count=count,
                severity=severity,
                tooltip=f"{count} issue{'s' if count != 1 else ''} requiring attention",
            ))
        
        return badges
    
    def get_trends(self, days: int = 7) -> list[ExceptionTrend]:
        """Get exception trends for the last N days."""
        self.refresh()
        
        now = datetime.now(timezone.utc)
        trends: list[ExceptionTrend] = []
        
        for i in range(days - 1, -1, -1):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Count exceptions created on this day
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            created_on_day = [
                e for e in self._exceptions
                if day_start <= e.created_at < day_end
            ]
            
            trend = ExceptionTrend(
                period=date_str,
                critical=len([e for e in created_on_day if e.severity == ExceptionSeverity.CRITICAL]),
                high=len([e for e in created_on_day if e.severity == ExceptionSeverity.HIGH]),
                medium=len([e for e in created_on_day if e.severity == ExceptionSeverity.MEDIUM]),
                low=len([e for e in created_on_day if e.severity == ExceptionSeverity.LOW]),
                resolved=len([e for e in created_on_day if e.status == ExceptionStatus.RESOLVED]),
                created=len(created_on_day),
            )
            trends.append(trend)
        
        return trends


# Singleton instance
_aggregator_instance: Optional[ExceptionsAggregator] = None


def get_exceptions_aggregator() -> ExceptionsAggregator:
    """Get the singleton exceptions aggregator instance."""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = ExceptionsAggregator()
    return _aggregator_instance


# Factory function for creating exceptions from various sources
def create_exception(
    title: str,
    description: str,
    category: ExceptionCategory,
    severity: ExceptionSeverity,
    source_entity_type: Optional[str] = None,
    source_entity_id: Optional[str] = None,
    source_url: Optional[str] = None,
    owner_id: Optional[str] = None,
    owner_name: Optional[str] = None,
    department: Optional[str] = None,
    due_date: Optional[datetime] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ExceptionItem:
    """Factory function to create an exception item."""
    return ExceptionItem(
        id=str(uuid4()),
        title=title,
        description=description,
        category=category,
        severity=severity,
        status=ExceptionStatus.OPEN,
        created_at=datetime.now(timezone.utc),
        due_date=due_date,
        owner_id=owner_id,
        owner_name=owner_name,
        department=department,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        source_url=source_url,
        tags=tags or [],
        metadata=metadata or {},
    )

"""
Exceptions Aggregator Service

Provides a unified view of all exceptions, red items, and critical alerts
across the entire system. Implements "Exceptions-First" dashboard navigation
to surface critical issues immediately.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from sensei.core.enums import Severity as ExceptionSeverity, WorkflowStatus as ExceptionStatus, EntityType as ExceptionCategory
from sensei.models.exception import ExceptionRecord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update
from sensei.core.redis import redis_client


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
        self._redis = None if os.environ.get("PYTEST_CURRENT_TEST") else redis_client
        self._memory_cache: dict[str, str] = {}

    async def _safe_redis_get(self, key: str) -> Optional[str]:
        if self._redis is None:
            value = self._memory_cache.get(key)
        else:
            try:
                value = await self._redis.get(key)
            except Exception:
                value = self._memory_cache.get(key)
        if isinstance(value, bytes):
            return value.decode()
        return value

    async def _safe_redis_set(self, key: str, value: str) -> None:
        if self._redis is None:
            self._memory_cache[key] = value
        else:
            try:
                await self._redis.set(key, value)
            except Exception:
                self._memory_cache[key] = value

    def _item_to_dict(self, item: ExceptionItem) -> dict[str, Any]:
        d = asdict(item)
        # Handle enums and datetimes
        d["category"] = item.category.value
        d["severity"] = item.severity.value
        d["status"] = item.status.value
        if item.created_at:
            d["created_at"] = item.created_at.isoformat()
        if item.due_date:
            d["due_date"] = item.due_date.isoformat()
        if item.escalated_at:
            d["escalated_at"] = item.escalated_at.isoformat()
        return d

    def _dict_to_item(self, d: dict[str, Any]) -> ExceptionItem:
        d["category"] = ExceptionCategory(d["category"])
        d["severity"] = ExceptionSeverity(d["severity"])
        d["status"] = ExceptionStatus(d["status"])
        if d.get("created_at"):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if d.get("due_date"):
            d["due_date"] = datetime.fromisoformat(d["due_date"])
        if d.get("escalated_at"):
            d["escalated_at"] = datetime.fromisoformat(d["escalated_at"])
        return ExceptionItem(**d)

    async def _save_to_redis(self, exceptions: list[ExceptionItem]) -> None:
        data = [self._item_to_dict(e) for e in exceptions]
        await self._safe_redis_set("exceptions:aggregated", json.dumps(data))
        await self._safe_redis_set("exceptions:last_refresh", datetime.now(timezone.utc).isoformat())

    async def _load_from_redis(self) -> tuple[list[ExceptionItem], Optional[datetime]]:
        data = await self._safe_redis_get("exceptions:aggregated")
        last_refresh_str = await self._safe_redis_get("exceptions:last_refresh")
        
        last_refresh = None
        if last_refresh_str:
            last_refresh = datetime.fromisoformat(last_refresh_str)
            
        if not data:
            return [], last_refresh
            
        items = json.loads(data)
        return [self._dict_to_item(i) for i in items], last_refresh
    
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
    
    async def refresh(self, db: AsyncSession, force: bool = False) -> None:
        """Refresh exceptions from all sources and database."""
        now = datetime.now(timezone.utc)
        
        # 0. Try loading from Redis first
        redis_exceptions, last_refresh = await self._load_from_redis()
        
        if not force and last_refresh:
            elapsed = (now - last_refresh).total_seconds()
            if elapsed < self._cache_ttl_seconds:
                self._exceptions = redis_exceptions
                self._last_refresh = last_refresh
                return
        
        all_exceptions: list[ExceptionItem] = []
        
        # 1. Load manual and persisted exceptions from database
        result = await db.execute(select(ExceptionRecord))
        db_records = result.scalars().all()
        
        for rec in db_records:
            # Handle potentially missing created_at from mock or newly created objects
            created_at = rec.created_at or now
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
                
            item = ExceptionItem(
                id=rec.id,
                title=rec.title,
                description=rec.description,
                category=ExceptionCategory(rec.category),
                severity=ExceptionSeverity(rec.severity),
                status=ExceptionStatus(rec.status),
                created_at=created_at,
                source=rec.source,
                due_date=rec.due_date,
                owner_id=rec.owner_id,
                owner_name=rec.owner_name,
                department=rec.department,
                source_entity_type=rec.source_entity_type,
                source_entity_id=rec.source_entity_id,
                source_url=rec.source_url,
                resolution_time_minutes=rec.resolution_time_minutes,
                escalated_at=rec.escalated_at,
                escalated_to=rec.escalated_to,
                blocked_reason=rec.blocked_reason,
                tags=rec.tags,
                metadata=rec.metadata_json,
            )
            all_exceptions.append(item)
        
        # 2. Get exceptions from dynamic sources
        for source_name, source_fn in self._sources.items():
            try:
                # If the source function is async, await it
                if hasattr(source_fn, "__call__") and hasattr(source_fn, "__await__"):
                     exceptions = await source_fn()
                else:
                     exceptions = source_fn()
                all_exceptions.extend(exceptions)
            except Exception:
                # Log error but continue with other sources
                pass
        
        # Sort by priority score (highest first)
        all_exceptions.sort(key=lambda e: e.priority_score, reverse=True)
        
        self._exceptions = all_exceptions
        self._last_refresh = now
        
        # 3. Save to Redis for other workers
        await self._save_to_redis(all_exceptions)
        
        # Notify listeners
        summary = self._get_summary_internal()
        self._notify_listeners(summary)

    async def add_exception(self, db: AsyncSession, exception: ExceptionItem) -> None:
        """Add a new exception manually and persist to database."""
        # Persist to DB
        record = ExceptionRecord(
            id=exception.id,
            title=exception.title,
            description=exception.description,
            category=exception.category.value,
            severity=exception.severity.value,
            status=exception.status.value,
            source=exception.source,
            due_date=exception.due_date,
            owner_id=exception.owner_id,
            owner_name=exception.owner_name,
            department=exception.department,
            source_entity_type=exception.source_entity_type,
            source_entity_id=exception.source_entity_id,
            source_url=exception.source_url,
            tags=exception.tags,
            metadata_json=exception.metadata,
        )
        db.add(record)
        await db.commit()
        
        # Add to local cache
        self._exceptions.append(exception)
        self._exceptions.sort(key=lambda e: e.priority_score, reverse=True)
        
        # Update Redis
        await self._save_to_redis(self._exceptions)
        
        summary = self._get_summary_internal()
        self._notify_listeners(summary)

    async def update_exception(
        self,
        db: AsyncSession,
        exception_id: str,
        updates: dict[str, Any],
    ) -> Optional[ExceptionItem]:
        """Update an existing exception and persist to database."""
        # Update in DB
        db_updates = {}
        for key, value in updates.items():
            if key == "category" or key == "severity" or key == "status":
                 db_updates[key] = value.value if hasattr(value, "value") else value
            elif key == "metadata":
                 db_updates["metadata_json"] = value
            else:
                 db_updates[key] = value

        await db.execute(
            sql_update(ExceptionRecord)
            .where(ExceptionRecord.id == exception_id)
            .values(**db_updates)
        )
        await db.commit()

        # Update in local cache
        found_exception = None
        for exception in self._exceptions:
            if exception.id == exception_id:
                for key, value in updates.items():
                    if hasattr(exception, key):
                        setattr(exception, key, value)
                
                # Re-sort after update
                self._exceptions.sort(key=lambda e: e.priority_score, reverse=True)
                found_exception = exception
                break
        
        if found_exception:
            await self._save_to_redis(self._exceptions)
            summary = self._get_summary_internal()
            self._notify_listeners(summary)
            return found_exception
        
        # If not in cache but in DB, refresh
        await self.refresh(db, force=True)
        for exception in self._exceptions:
            if exception.id == exception_id:
                return exception
                
        return None

    async def resolve_exception(
        self,
        db: AsyncSession,
        exception_id: str,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ExceptionItem]:
        """Mark an exception as resolved."""
        # Find exception to calculate age
        age = 0
        for e in self._exceptions:
            if e.id == exception_id:
                age = e.age_minutes
                break
        
        return await self.update_exception(db, exception_id, {
            "status": ExceptionStatus.RESOLVED,
            "resolution_time_minutes": age,
        })

    async def escalate_exception(
        self,
        db: AsyncSession,
        exception_id: str,
        escalate_to: str,
        reason: Optional[str] = None,
    ) -> Optional[ExceptionItem]:
        """Escalate an exception."""
        return await self.update_exception(db, exception_id, {
            "status": ExceptionStatus.ESCALATED,
            "escalated_at": datetime.now(timezone.utc),
            "escalated_to": escalate_to,
        })

    async def acknowledge_exception(self, db: AsyncSession, exception_id: str) -> Optional[ExceptionItem]:
        """Acknowledge an exception."""
        return await self.update_exception(db, exception_id, {
            "status": ExceptionStatus.ACKNOWLEDGED,
        })

    async def get_all(
        self,
        db: AsyncSession,
        category: Optional[ExceptionCategory] = None,
        severity: Optional[ExceptionSeverity] = None,
        status: Optional[ExceptionStatus] = None,
        overdue_only: bool = False,
        limit: int = 100,
    ) -> list[ExceptionItem]:
        """Get all exceptions with optional filters."""
        await self.refresh(db)
        
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

    async def get_critical(self, db: AsyncSession, limit: int = 10) -> list[ExceptionItem]:
        """Get critical and high severity exceptions."""
        await self.refresh(db)
        
        results = [
            e for e in self._exceptions
            if e.severity in (ExceptionSeverity.CRITICAL, ExceptionSeverity.HIGH)
            and e.status not in (ExceptionStatus.RESOLVED,)
        ]
        
        return results[:limit]

    async def get_overdue(self, db: AsyncSession, limit: int = 10) -> list[ExceptionItem]:
        """Get overdue exceptions."""
        return await self.get_all(db, overdue_only=True, limit=limit)

    async def get_escalated(self, db: AsyncSession, limit: int = 10) -> list[ExceptionItem]:
        """Get escalated exceptions."""
        return await self.get_all(db, status=ExceptionStatus.ESCALATED, limit=limit)

    async def get_by_category(self, db: AsyncSession, category: ExceptionCategory, limit: int = 20) -> list[ExceptionItem]:
        """Get exceptions by category."""
        return await self.get_all(db, category=category, limit=limit)

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

    async def get_summary(self, db: AsyncSession) -> ExceptionSummary:
        """Get summary of all exceptions for badges/navigation."""
        await self.refresh(db)
        return self._get_summary_internal()

    async def get_navigation_badges(self, db: AsyncSession) -> list[NavigationBadge]:
        """Get badges for main navigation items."""
        await self.refresh(db)
        
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

    async def get_trends(self, db: AsyncSession, days: int = 7) -> list[ExceptionTrend]:
        """Get exception trends for the last N days."""
        await self.refresh(db)
        
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

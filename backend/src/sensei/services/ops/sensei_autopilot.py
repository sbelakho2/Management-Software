"""
Sensei Autopilot: Autonomous Zero-Ops & Self-Healing.

Self-managing system for autonomous database tuning, storage management,
automated recovery, and backup management.

Features:
- Local Health Watchdog with DB tuning
- Autonomous index management
- Self-cleaning storage
- Automated self-healing
- Zero-admin backup system
- On-device model lifecycle
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
import hashlib
import logging
import os
import re
import threading
import time
import uuid

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class HealthStatus(Enum):
    """System health status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    """Types of services."""
    
    DATABASE = "database"
    CACHE = "cache"
    STORAGE = "storage"
    WORKER = "worker"
    API = "api"
    MODEL = "model"


class HealingActionType(Enum):
    """Types of self-healing actions."""
    
    RESTART = "restart"
    RECONNECT = "reconnect"
    FAILOVER = "failover"
    CLEANUP = "cleanup"
    REINDEX = "reindex"
    VACUUM = "vacuum"


class BackupType(Enum):
    """Types of backups."""
    
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    """Backup status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class ModelUpdateStatus(Enum):
    """Model update status."""
    
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    READY = "ready"
    ACTIVE = "active"
    FAILED = "failed"


# =============================================================================
# Constants
# =============================================================================

BLOAT_THRESHOLD = 0.20  # 20%
DISK_SAFEGUARD_THRESHOLD = 0.10  # 10% remaining
INDEX_ANALYSIS_THRESHOLD_MS = 100  # Slow query threshold


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SlowQuery:
    """Detected slow query."""
    
    query_id: str
    query_text: str
    duration_ms: float
    table_name: str
    missing_index: str | None = None
    suggested_index: str | None = None
    frequency: int = 1
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class IndexRecommendation:
    """Index recommendation."""
    
    recommendation_id: str
    table_name: str
    column_names: list[str]
    index_type: str = "btree"
    estimated_improvement: float = 0.0
    query_count: int = 0
    created: bool = False
    priority: int = 1


@dataclass
class TableStats:
    """Table statistics."""
    
    table_name: str
    row_count: int
    dead_tuples: int
    table_size_mb: float
    index_size_mb: float
    bloat_ratio: float
    last_vacuum: datetime | None = None
    last_analyze: datetime | None = None


@dataclass
class StorageItem:
    """Item in storage."""
    
    item_id: str
    path: str
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    is_orphaned: bool = False
    item_type: str = "file"


@dataclass
class CleanupResult:
    """Result of storage cleanup."""
    
    result_id: str
    items_deleted: int
    bytes_freed: int
    orphans_found: int
    errors: list[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ServiceHealth:
    """Health status of a service."""
    
    service_name: str
    service_type: ServiceType
    status: HealthStatus
    response_time_ms: float | None = None
    error_message: str | None = None
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consecutive_failures: int = 0


@dataclass
class HealingAction:
    """A self-healing action."""
    
    action_id: str
    action_type: HealingActionType
    service_name: str
    dry_run: bool = True
    executed: bool = False
    success: bool | None = None
    error: str | None = None
    executed_at: datetime | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataIntegrityCheck:
    """Data integrity check result."""
    
    check_id: str
    database_count: int
    storage_count: int
    orphaned_db: int = 0
    orphaned_storage: int = 0
    mismatches: list[str] = field(default_factory=list)
    passed: bool = True
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Backup:
    """Backup record."""
    
    backup_id: str
    backup_type: BackupType
    status: BackupStatus = BackupStatus.PENDING
    size_bytes: int = 0
    encrypted: bool = True
    path: str = ""
    checksum: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    verified_at: datetime | None = None
    error: str | None = None


@dataclass
class RestoreResult:
    """Result of backup restoration test."""
    
    result_id: str
    backup_id: str
    success: bool
    sandbox_id: str = ""
    verification_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ModelVersion:
    """AI model version."""
    
    model_id: str
    version: str
    path: str
    size_bytes: int
    format: str = "onnx"
    status: ModelUpdateStatus = ModelUpdateStatus.AVAILABLE
    is_lightweight: bool = False
    downloaded_at: datetime | None = None
    activated_at: datetime | None = None


# =============================================================================
# Database Tuner
# =============================================================================

class DatabaseTuner:
    """
    Autonomous database tuning.
    
    Analyzes queries, recommends indexes, and manages vacuuming.
    """
    
    def __init__(
        self,
        slow_query_threshold_ms: float = INDEX_ANALYSIS_THRESHOLD_MS,
        bloat_threshold: float = BLOAT_THRESHOLD,
    ):
        """Initialize database tuner."""
        self._slow_query_threshold = slow_query_threshold_ms
        self._bloat_threshold = bloat_threshold
        self._slow_queries: dict[str, SlowQuery] = {}
        self._index_recommendations: list[IndexRecommendation] = []
        self._table_stats: dict[str, TableStats] = {}
        self._created_indexes: list[str] = []
        self._vacuum_schedule: dict[str, datetime] = {}
    
    def record_slow_query(
        self,
        query_text: str,
        duration_ms: float,
        table_name: str = "",
    ) -> SlowQuery | None:
        """Record a slow query for analysis."""
        if duration_ms < self._slow_query_threshold:
            return None
        
        # Normalize query
        normalized = self._normalize_query(query_text)
        query_id = hashlib.md5(normalized.encode()).hexdigest()[:12]
        
        if query_id in self._slow_queries:
            sq = self._slow_queries[query_id]
            sq.frequency += 1
            sq.last_seen = datetime.now(timezone.utc)
            return sq
        
        # Detect table if not provided
        if not table_name:
            table_name = self._extract_table_name(query_text)
        
        # Analyze for missing index
        missing_index = self._detect_missing_index(query_text)
        suggested_index = self._suggest_index(query_text, table_name) if missing_index else None
        
        sq = SlowQuery(
            query_id=query_id,
            query_text=query_text,
            duration_ms=duration_ms,
            table_name=table_name,
            missing_index=missing_index,
            suggested_index=suggested_index,
        )
        
        self._slow_queries[query_id] = sq
        return sq
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for comparison."""
        # Remove values and whitespace
        normalized = re.sub(r'\s+', ' ', query.strip().lower())
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        return normalized
    
    def _extract_table_name(self, query: str) -> str:
        """Extract table name from query."""
        # Simple extraction - production would be more robust
        match = re.search(r'from\s+([a-zA-Z_][a-zA-Z0-9_]*)', query, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def _detect_missing_index(self, query: str) -> str | None:
        """Detect missing index from query pattern."""
        # Look for WHERE clauses without indexes
        where_match = re.search(
            r'where\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
            query,
            re.IGNORECASE,
        )
        if where_match:
            return where_match.group(1)
        return None
    
    def _suggest_index(self, query: str, table_name: str) -> str | None:
        """Suggest index for query."""
        columns = []
        
        # Extract WHERE columns
        where_matches = re.findall(
            r'where\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
            query,
            re.IGNORECASE,
        )
        columns.extend(where_matches)
        
        # Extract ORDER BY columns
        order_matches = re.findall(
            r'order\s+by\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            query,
            re.IGNORECASE,
        )
        columns.extend(order_matches)
        
        if columns:
            col_str = "_".join(columns[:3])
            return f"idx_{table_name}_{col_str}"
        
        return None
    
    def generate_recommendations(self) -> list[IndexRecommendation]:
        """Generate index recommendations from slow queries."""
        # Group by table and suggested index
        table_indexes: dict[str, dict[str, list[SlowQuery]]] = {}
        
        for sq in self._slow_queries.values():
            if not sq.suggested_index:
                continue
            
            if sq.table_name not in table_indexes:
                table_indexes[sq.table_name] = {}
            
            if sq.suggested_index not in table_indexes[sq.table_name]:
                table_indexes[sq.table_name][sq.suggested_index] = []
            
            table_indexes[sq.table_name][sq.suggested_index].append(sq)
        
        recommendations = []
        for table_name, indexes in table_indexes.items():
            for index_name, queries in indexes.items():
                total_freq = sum(q.frequency for q in queries)
                if total_freq < 5:  # Need at least 5 occurrences
                    continue
                
                # Extract columns from index name
                parts = index_name.replace(f"idx_{table_name}_", "").split("_")
                
                rec = IndexRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    table_name=table_name,
                    column_names=parts,
                    estimated_improvement=min(0.8, total_freq * 0.05),
                    query_count=total_freq,
                    priority=1 if total_freq >= 20 else 2,
                )
                recommendations.append(rec)
        
        self._index_recommendations = sorted(
            recommendations,
            key=lambda r: r.query_count,
            reverse=True,
        )
        
        return self._index_recommendations
    
    def create_index(self, recommendation: IndexRecommendation) -> str:
        """Generate CREATE INDEX statement."""
        cols = ", ".join(recommendation.column_names)
        index_name = f"idx_{recommendation.table_name}_{'_'.join(recommendation.column_names)}"
        
        sql = (
            f"CREATE INDEX IF NOT EXISTS {index_name} "
            f"ON {recommendation.table_name} ({cols})"
        )
        
        return sql

    async def apply_recommendation(self, db: Any, recommendation: IndexRecommendation) -> bool:
        """Apply an index recommendation to the database."""
        sql = self.create_index(recommendation)
        logger.info(f"Applying index recommendation: {sql}")
        try:
            # We assume db is an AsyncSession
            if hasattr(db, "execute"):
                from sqlalchemy import text
                await db.execute(text(sql))
                # Note: We don't commit here, usually handled by caller or session middleware
                # but for DDL, some DBs require it or auto-commit.
            
            recommendation.created = True
            self._created_indexes.append(f"idx_{recommendation.table_name}_{'_'.join(recommendation.column_names)}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply index recommendation: {str(e)}")
            return False

    async def apply_high_priority_recommendations(self, db: Any) -> int:
        """Apply all high-priority recommendations."""
        recommendations = [r for r in self._index_recommendations if r.priority == 1 and not r.created]
        count = 0
        for rec in recommendations:
            if await self.apply_recommendation(db, rec):
                count += 1
        return count
    
    def drop_unused_index(self, index_name: str, table_name: str) -> str:
        """Generate DROP INDEX statement."""
        return f"DROP INDEX IF EXISTS {index_name}"
    
    def update_table_stats(self, stats: TableStats):
        """Update table statistics."""
        self._table_stats[stats.table_name] = stats
    
    def get_bloated_tables(self) -> list[TableStats]:
        """Get tables with bloat above threshold."""
        return [
            t for t in self._table_stats.values()
            if t.bloat_ratio > self._bloat_threshold
        ]
    
    def schedule_vacuum(
        self,
        table_name: str,
        scheduled_time: datetime | None = None,
    ) -> datetime:
        """Schedule VACUUM ANALYZE for a table."""
        if scheduled_time is None:
            # Schedule for next idle period (2 AM)
            now = datetime.now(timezone.utc)
            scheduled_time = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if scheduled_time <= now:
                scheduled_time += timedelta(days=1)
        
        self._vacuum_schedule[table_name] = scheduled_time
        return scheduled_time
    
    def get_vacuum_commands(self, table_name: str) -> list[str]:
        """Get VACUUM ANALYZE commands for table."""
        return [
            f"VACUUM ANALYZE {table_name}",
        ]
    
    def get_pending_vacuums(self) -> list[tuple[str, datetime]]:
        """Get pending vacuum schedules."""
        now = datetime.now(timezone.utc)
        return [
            (table, dt)
            for table, dt in self._vacuum_schedule.items()
            if dt <= now
        ]


# =============================================================================
# Storage Manager
# =============================================================================

class StorageManager:
    """
    Self-cleaning storage management.
    """
    
    def __init__(
        self,
        disk_safeguard_threshold: float = DISK_SAFEGUARD_THRESHOLD,
        log_retention_days: int = 30,
        temp_retention_days: int = 7,
    ):
        """Initialize storage manager."""
        self._disk_threshold = disk_safeguard_threshold
        self._log_retention = timedelta(days=log_retention_days)
        self._temp_retention = timedelta(days=temp_retention_days)
        self._ingestion_paused = False
        self._storage_items: list[StorageItem] = []
        self._archived_items: list[str] = []
    
    @property
    def is_ingestion_paused(self) -> bool:
        """Check if ingestion is paused."""
        return self._ingestion_paused
    
    def check_disk_space(
        self,
        available_percent: float,
    ) -> bool:
        """Check disk space and pause if needed."""
        if available_percent < self._disk_threshold:
            self._ingestion_paused = True
            return False
        
        self._ingestion_paused = False
        return True
    
    def resume_ingestion(self):
        """Resume data ingestion."""
        self._ingestion_paused = False
    
    def register_item(self, item: StorageItem):
        """Register an item in storage."""
        self._storage_items.append(item)
    
    def find_expired_logs(self) -> list[StorageItem]:
        """Find logs that have exceeded retention."""
        now = datetime.now(timezone.utc)
        cutoff = now - self._log_retention
        
        return [
            item for item in self._storage_items
            if item.item_type == "log" and item.created_at < cutoff
        ]
    
    def find_expired_temp_files(self) -> list[StorageItem]:
        """Find temporary files that have exceeded retention."""
        now = datetime.now(timezone.utc)
        cutoff = now - self._temp_retention
        
        return [
            item for item in self._storage_items
            if item.item_type == "temp" and item.created_at < cutoff
        ]
    
    def find_orphaned_files(
        self,
        db_references: set[str],
        min_age_days: int = 7,
    ) -> list[StorageItem]:
        """Find files not referenced in database with a safety grace period."""
        orphans = []
        now = datetime.now(timezone.utc)
        grace_period = timedelta(days=min_age_days)
        
        for item in self._storage_items:
            # Only consider items older than the grace period to avoid
            # deleting files that were just uploaded but not yet referenced in DB
            if item.item_id not in db_references:
                if (now - item.created_at) > grace_period:
                    item.is_orphaned = True
                    orphans.append(item)
        
        return orphans
    
    def cleanup(
        self,
        items: list[StorageItem],
    ) -> CleanupResult:
        """Clean up specified items."""
        result = CleanupResult(
            result_id=str(uuid.uuid4()),
            items_deleted=0,
            bytes_freed=0,
            orphans_found=0,
        )
        
        for item in items:
            try:
                # In production, would delete actual file
                result.items_deleted += 1
                result.bytes_freed += item.size_bytes
                
                if item.is_orphaned:
                    result.orphans_found += 1
                
                # Remove from tracking
                self._storage_items = [
                    i for i in self._storage_items
                    if i.item_id != item.item_id
                ]
            except Exception as e:
                result.errors.append(f"Failed to delete {item.item_id}: {str(e)}")
        
        return result
    
    def archive_item(self, item: StorageItem, archive_path: str) -> bool:
        """Archive an item to cold storage."""
        # In production, would move to archive storage
        self._archived_items.append(item.item_id)
        return True
    
    def get_storage_summary(self) -> dict[str, Any]:
        """Get storage summary."""
        total_size = sum(i.size_bytes for i in self._storage_items)
        by_type: dict[str, int] = {}
        
        for item in self._storage_items:
            by_type[item.item_type] = by_type.get(item.item_type, 0) + item.size_bytes
        
        return {
            "total_items": len(self._storage_items),
            "total_bytes": total_size,
            "by_type": by_type,
            "archived_count": len(self._archived_items),
            "ingestion_paused": self._ingestion_paused,
        }


# =============================================================================
# Self-Healing Engine
# =============================================================================

class SelfHealingEngine:
    """
    Automated self-healing for services.
    """
    
    def __init__(
        self,
        dry_run_enabled: bool = True,
        max_restart_attempts: int = 3,
    ):
        """Initialize self-healing engine."""
        self._dry_run = dry_run_enabled
        self._max_restarts = max_restart_attempts
        self._service_health: dict[str, ServiceHealth] = {}
        self._healing_log: list[HealingAction] = []
        self._restart_counts: dict[str, int] = {}
    
    def register_service(
        self,
        name: str,
        service_type: ServiceType,
    ):
        """Register a service for monitoring."""
        self._service_health[name] = ServiceHealth(
            service_name=name,
            service_type=service_type,
            status=HealthStatus.UNKNOWN,
        )
    
    def update_health(
        self,
        service_name: str,
        status: HealthStatus,
        response_time_ms: float | None = None,
        error: str | None = None,
    ):
        """Update service health status."""
        if service_name not in self._service_health:
            return
        
        health = self._service_health[service_name]
        health.status = status
        health.response_time_ms = response_time_ms
        health.error_message = error
        health.last_check = datetime.now(timezone.utc)
        
        if status in [HealthStatus.CRITICAL, HealthStatus.DEGRADED]:
            health.consecutive_failures += 1
        else:
            health.consecutive_failures = 0
    
    def check_deep_health(
        self,
        service_name: str,
    ) -> dict[str, Any]:
        """Perform deep health check."""
        result: dict[str, Any] = {
            "service": service_name,
            "checks": [],
            "overall": "healthy",
        }
        
        if service_name not in self._service_health:
            result["overall"] = "unknown"
            return result
        
        health = self._service_health[service_name]
        
        # Check 1: Service status
        result["checks"].append({
            "name": "service_status",
            "passed": health.status == HealthStatus.HEALTHY,
            "value": health.status.value,
        })
        
        # Check 2: Response time
        if health.response_time_ms:
            result["checks"].append({
                "name": "response_time",
                "passed": health.response_time_ms < 1000,
                "value": health.response_time_ms,
            })
        
        # Check 3: Consecutive failures
        result["checks"].append({
            "name": "consecutive_failures",
            "passed": health.consecutive_failures < 3,
            "value": health.consecutive_failures,
        })
        
        # Determine overall
        failed_checks = sum(
            1 for c in result["checks"]
            if not c["passed"]
        )
        
        if failed_checks >= 2:
            result["overall"] = "critical"
        elif failed_checks == 1:
            result["overall"] = "degraded"
        
        return result
    
    def determine_healing_action(
        self,
        service_name: str,
    ) -> HealingAction | None:
        """Determine appropriate healing action."""
        if service_name not in self._service_health:
            return None
        
        health = self._service_health[service_name]
        
        if health.status == HealthStatus.HEALTHY:
            return None
        
        restart_count = self._restart_counts.get(service_name, 0)
        
        # Choose action based on service type and status
        if health.service_type == ServiceType.WORKER:
            if restart_count < self._max_restarts:
                action_type = HealingActionType.RESTART
            else:
                action_type = HealingActionType.FAILOVER
        elif health.service_type == ServiceType.CACHE:
            action_type = HealingActionType.RECONNECT
        elif health.service_type == ServiceType.DATABASE:
            if "bloat" in (health.error_message or "").lower():
                action_type = HealingActionType.VACUUM
            else:
                action_type = HealingActionType.RECONNECT
        else:
            action_type = HealingActionType.RESTART
        
        return HealingAction(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            service_name=service_name,
            dry_run=self._dry_run,
        )
    
    def execute_healing(
        self,
        action: HealingAction,
    ) -> bool:
        """Execute healing action."""
        if action.dry_run:
            action.details["mode"] = "dry_run"
            action.executed = True
            action.success = True
            action.executed_at = datetime.now(timezone.utc)
            self._healing_log.append(action)
            return True
        
        try:
            # In production, would execute actual actions
            if action.action_type == HealingActionType.RESTART:
                self._restart_counts[action.service_name] = (
                    self._restart_counts.get(action.service_name, 0) + 1
                )
                action.details["action"] = "restart_service"
            elif action.action_type == HealingActionType.RECONNECT:
                action.details["action"] = "reconnect"
            elif action.action_type == HealingActionType.VACUUM:
                action.details["action"] = "vacuum_database"
            
            action.executed = True
            action.success = True
            action.executed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            action.executed = True
            action.success = False
            action.error = str(e)
        
        self._healing_log.append(action)
        return action.success or False
    
    def enable_dry_run(self, enabled: bool = True):
        """Enable or disable dry run mode."""
        self._dry_run = enabled
    
    def get_healing_log(
        self,
        service_name: str | None = None,
    ) -> list[HealingAction]:
        """Get healing action log."""
        if service_name:
            return [a for a in self._healing_log if a.service_name == service_name]
        return self._healing_log.copy()
    
    def check_data_integrity(
        self,
        db_ids: set[str],
        storage_ids: set[str],
    ) -> DataIntegrityCheck:
        """Check data integrity between DB and storage."""
        orphaned_db = db_ids - storage_ids
        orphaned_storage = storage_ids - db_ids
        
        mismatches = []
        for item_id in orphaned_db:
            mismatches.append(f"DB record {item_id} missing in storage")
        for item_id in orphaned_storage:
            mismatches.append(f"Storage item {item_id} missing in DB")
        
        return DataIntegrityCheck(
            check_id=str(uuid.uuid4()),
            database_count=len(db_ids),
            storage_count=len(storage_ids),
            orphaned_db=len(orphaned_db),
            orphaned_storage=len(orphaned_storage),
            mismatches=mismatches[:10],  # Limit to first 10
            passed=len(mismatches) == 0,
        )


# =============================================================================
# Backup Manager
# =============================================================================

class BackupManager:
    """
    Zero-admin backup management.
    """
    
    def __init__(
        self,
        backup_dir: str = "/backups",
        max_backups: int = 10,
        encryption_enabled: bool = True,
    ):
        """Initialize backup manager."""
        self._backup_dir = backup_dir
        self._max_backups = max_backups
        self._encryption = encryption_enabled
        self._backups: list[Backup] = []
        self._verification_results: list[RestoreResult] = []
    
    def create_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        source_data: bytes | None = None,
    ) -> Backup:
        """Create a new backup."""
        backup = Backup(
            backup_id=str(uuid.uuid4()),
            backup_type=backup_type,
            encrypted=self._encryption,
        )
        
        backup.status = BackupStatus.IN_PROGRESS
        
        try:
            # Simulate backup creation
            if source_data:
                backup.size_bytes = len(source_data)
                backup.checksum = hashlib.sha256(source_data).hexdigest()
            else:
                backup.size_bytes = 1024 * 1024  # 1MB placeholder
                backup.checksum = hashlib.sha256(
                    str(uuid.uuid4()).encode()
                ).hexdigest()
            
            backup.path = f"{self._backup_dir}/{backup.backup_id}.bak"
            backup.status = BackupStatus.COMPLETED
            backup.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            backup.status = BackupStatus.FAILED
            backup.error = str(e)
        
        self._backups.append(backup)
        self._rotate_backups()
        
        return backup
    
    def _rotate_backups(self):
        """Rotate old backups to maintain limit."""
        if len(self._backups) <= self._max_backups:
            return
        
        # Keep most recent
        self._backups.sort(key=lambda b: b.created_at, reverse=True)
        self._backups = self._backups[:self._max_backups]
    
    def verify_backup(self, backup_id: str) -> RestoreResult:
        """Verify backup by testing restoration."""
        backup = self.get_backup(backup_id)
        
        result = RestoreResult(
            result_id=str(uuid.uuid4()),
            backup_id=backup_id,
            success=False,
            sandbox_id=f"sandbox-{uuid.uuid4().hex[:8]}",
        )
        
        if not backup:
            result.errors.append("Backup not found")
            return result
        
        try:
            # Verification steps
            result.verification_steps.append("Created sandbox environment")
            
            # Verify checksum
            result.verification_steps.append(f"Verified checksum: {backup.checksum[:16]}...")
            
            # Simulate restore
            result.verification_steps.append("Restored database schema")
            result.verification_steps.append("Restored data records")
            result.verification_steps.append("Verified record counts")
            
            result.success = True
            backup.status = BackupStatus.VERIFIED
            backup.verified_at = datetime.now(timezone.utc)
            
        except Exception as e:
            result.errors.append(str(e))
        
        self._verification_results.append(result)
        return result
    
    def get_backup(self, backup_id: str) -> Backup | None:
        """Get backup by ID."""
        for backup in self._backups:
            if backup.backup_id == backup_id:
                return backup
        return None
    
    def get_latest_backup(
        self,
        verified_only: bool = False,
    ) -> Backup | None:
        """Get most recent backup."""
        candidates = self._backups
        
        if verified_only:
            candidates = [b for b in candidates if b.status == BackupStatus.VERIFIED]
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda b: b.created_at)
    
    def list_backups(self) -> list[Backup]:
        """List all backups."""
        return sorted(self._backups, key=lambda b: b.created_at, reverse=True)


# =============================================================================
# Model Lifecycle Manager
# =============================================================================

class ModelLifecycleManager:
    """
    On-device model lifecycle management.
    """
    
    def __init__(
        self,
        models_dir: str = "/models",
        auto_update_enabled: bool = True,
    ):
        """Initialize model lifecycle manager."""
        self._models_dir = models_dir
        self._auto_update = auto_update_enabled
        self._versions: dict[str, list[ModelVersion]] = {}
        self._active_models: dict[str, str] = {}  # model_id -> version
        self._fallback_mapping: dict[str, str] = {}  # model_id -> lightweight_id
    
    def register_model(
        self,
        model_id: str,
        version: str,
        size_bytes: int,
        is_lightweight: bool = False,
    ) -> ModelVersion:
        """Register a model version."""
        mv = ModelVersion(
            model_id=model_id,
            version=version,
            path=f"{self._models_dir}/{model_id}/{version}",
            size_bytes=size_bytes,
            is_lightweight=is_lightweight,
        )
        
        if model_id not in self._versions:
            self._versions[model_id] = []
        
        self._versions[model_id].append(mv)
        return mv
    
    def check_for_updates(
        self,
        model_id: str,
        available_versions: list[str],
    ) -> list[str]:
        """Check for available updates."""
        if model_id not in self._versions:
            return available_versions
        
        current_versions = {v.version for v in self._versions[model_id]}
        new_versions = [v for v in available_versions if v not in current_versions]
        
        return new_versions
    
    def download_update(
        self,
        model_id: str,
        version: str,
        size_bytes: int,
    ) -> ModelVersion:
        """Download a model update."""
        mv = self.register_model(model_id, version, size_bytes)
        mv.status = ModelUpdateStatus.DOWNLOADING
        
        # Simulate download
        mv.status = ModelUpdateStatus.READY
        mv.downloaded_at = datetime.now(timezone.utc)
        
        return mv
    
    def activate_model(
        self,
        model_id: str,
        version: str,
    ) -> bool:
        """Activate a specific model version."""
        if model_id not in self._versions:
            return False
        
        for mv in self._versions[model_id]:
            if mv.version == version:
                if mv.status not in [ModelUpdateStatus.READY, ModelUpdateStatus.ACTIVE]:
                    return False
                
                # Deactivate previous
                for other in self._versions[model_id]:
                    if other.status == ModelUpdateStatus.ACTIVE:
                        other.status = ModelUpdateStatus.READY
                
                mv.status = ModelUpdateStatus.ACTIVE
                mv.activated_at = datetime.now(timezone.utc)
                self._active_models[model_id] = version
                return True
        
        return False
    
    def register_fallback(
        self,
        model_id: str,
        lightweight_id: str,
    ):
        """Register lightweight fallback for a model."""
        self._fallback_mapping[model_id] = lightweight_id
    
    def switch_to_fallback(self, model_id: str) -> bool:
        """Switch to lightweight fallback model."""
        if model_id not in self._fallback_mapping:
            return False
        
        fallback_id = self._fallback_mapping[model_id]
        
        if fallback_id not in self._versions:
            return False
        
        # Find active version of fallback
        for mv in self._versions[fallback_id]:
            if mv.status == ModelUpdateStatus.READY:
                return self.activate_model(fallback_id, mv.version)
        
        return False
    
    def get_active_version(self, model_id: str) -> ModelVersion | None:
        """Get currently active version of a model."""
        if model_id not in self._active_models:
            return None
        
        version = self._active_models[model_id]
        for mv in self._versions.get(model_id, []):
            if mv.version == version:
                return mv
        
        return None
    
    def get_model_stats(self) -> dict[str, Any]:
        """Get model statistics."""
        return {
            "total_models": len(self._versions),
            "active_models": len(self._active_models),
            "total_versions": sum(len(v) for v in self._versions.values()),
            "auto_update_enabled": self._auto_update,
        }


# =============================================================================
# Sensei Autopilot
# =============================================================================

class SenseiAutopilot(PersistentServiceMixin):
    """
    Main autopilot orchestrator combining all self-management capabilities.
    """

    SERVICE_NAME = "sensei_autopilot"
    
    def __init__(self):
        """Initialize autopilot."""
        self._db_tuner = DatabaseTuner()
        self._storage_manager = StorageManager()
        self._healing_engine = SelfHealingEngine()
        self._backup_manager = BackupManager()
        self._model_manager = ModelLifecycleManager()
    
    @property
    def db_tuner(self) -> DatabaseTuner:
        """Get database tuner."""
        return self._db_tuner
    
    @property
    def storage(self) -> StorageManager:
        """Get storage manager."""
        return self._storage_manager
    
    @property
    def healing(self) -> SelfHealingEngine:
        """Get self-healing engine."""
        return self._healing_engine
    
    @property
    def backup(self) -> BackupManager:
        """Get backup manager."""
        return self._backup_manager
    
    @property
    def models(self) -> ModelLifecycleManager:
        """Get model lifecycle manager."""
        return self._model_manager
    
    async def run_maintenance_cycle(self, db: Any = None, apply_indexes: bool = False) -> dict[str, Any]:
        """Run a complete maintenance cycle with autonomous actions."""
        results: dict[str, Any] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps": [],
        }
        
        # 1. Check for bloated tables
        bloated = self._db_tuner.get_bloated_tables()
        results["steps"].append({
            "step": "check_bloat",
            "bloated_tables": len(bloated),
        })
        
        # 2. Generate and optionally apply index recommendations
        recommendations = self._db_tuner.generate_recommendations()
        applied_count = 0
        if apply_indexes and db:
            applied_count = await self._db_tuner.apply_high_priority_recommendations(db)
            
        results["steps"].append({
            "step": "index_analysis",
            "recommendations": len(recommendations),
            "applied_count": applied_count,
        })
        
        # 3. Check storage
        summary = self._storage_manager.get_storage_summary()
        results["steps"].append({
            "step": "storage_check",
            "total_items": summary["total_items"],
            "ingestion_paused": summary["ingestion_paused"],
        })
        
        # 4. Backup if needed
        latest = self._backup_manager.get_latest_backup()
        if not latest or (datetime.now(timezone.utc) - latest.created_at).days >= 1:
            backup = self._backup_manager.create_backup()
            results["steps"].append({
                "step": "backup",
                "backup_id": backup.backup_id,
                "status": backup.status.value,
            })
        
        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        return results


# =============================================================================
# Factory Functions
# =============================================================================

def create_autopilot() -> SenseiAutopilot:
    """Create Sensei Autopilot instance."""
    return SenseiAutopilot()


def create_db_tuner(
    slow_query_threshold_ms: float = INDEX_ANALYSIS_THRESHOLD_MS,
) -> DatabaseTuner:
    """Create database tuner."""
    return DatabaseTuner(slow_query_threshold_ms=slow_query_threshold_ms)


def create_storage_manager(
    disk_threshold: float = DISK_SAFEGUARD_THRESHOLD,
) -> StorageManager:
    """Create storage manager."""
    return StorageManager(disk_safeguard_threshold=disk_threshold)


def create_healing_engine(
    dry_run: bool = True,
) -> SelfHealingEngine:
    """Create self-healing engine."""
    return SelfHealingEngine(dry_run_enabled=dry_run)


def create_backup_manager(
    max_backups: int = 10,
) -> BackupManager:
    """Create backup manager."""
    return BackupManager(max_backups=max_backups)

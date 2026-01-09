"""
Tests for Sensei Autopilot: Autonomous Zero-Ops & Self-Healing.

Tests cover:
- Local Health Watchdog
- Autonomous database tuning
- Index recommendations
- Self-cleaning storage
- Automated self-healing
- Zero-admin backup system
- On-device model lifecycle
"""

import pytest
from datetime import datetime, timezone, timedelta

from sensei.services.sensei_autopilot import (
    # Enums
    HealthStatus,
    ServiceType,
    HealingActionType,
    BackupType,
    BackupStatus,
    ModelUpdateStatus,
    # Data models
    SlowQuery,
    IndexRecommendation,
    TableStats,
    StorageItem,
    CleanupResult,
    ServiceHealth,
    HealingAction,
    DataIntegrityCheck,
    Backup,
    RestoreResult,
    ModelVersion,
    # Components
    DatabaseTuner,
    StorageManager,
    SelfHealingEngine,
    BackupManager,
    ModelLifecycleManager,
    SenseiAutopilot,
    # Factory functions
    create_autopilot,
    create_db_tuner,
    create_storage_manager,
    create_healing_engine,
    create_backup_manager,
    # Constants
    BLOAT_THRESHOLD,
    DISK_SAFEGUARD_THRESHOLD,
    INDEX_ANALYSIS_THRESHOLD_MS,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def db_tuner() -> DatabaseTuner:
    """Create database tuner for testing."""
    return DatabaseTuner()


@pytest.fixture
def storage_manager() -> StorageManager:
    """Create storage manager for testing."""
    return StorageManager()


@pytest.fixture
def healing_engine() -> SelfHealingEngine:
    """Create self-healing engine for testing."""
    return SelfHealingEngine(dry_run_enabled=True)


@pytest.fixture
def backup_manager() -> BackupManager:
    """Create backup manager for testing."""
    return BackupManager(max_backups=5)


@pytest.fixture
def model_manager() -> ModelLifecycleManager:
    """Create model lifecycle manager for testing."""
    return ModelLifecycleManager()


@pytest.fixture
def autopilot() -> SenseiAutopilot:
    """Create autopilot for testing."""
    return SenseiAutopilot()


@pytest.fixture
def sample_storage_items() -> list[StorageItem]:
    """Sample storage items."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=60)
    
    return [
        StorageItem(
            item_id="file-001",
            path="/data/file1.txt",
            size_bytes=1024,
            created_at=now,
            last_accessed=now,
            item_type="file",
        ),
        StorageItem(
            item_id="log-001",
            path="/logs/app.log",
            size_bytes=5000,
            created_at=old,
            last_accessed=old,
            item_type="log",
        ),
        StorageItem(
            item_id="temp-001",
            path="/tmp/temp.dat",
            size_bytes=2000,
            created_at=old,
            last_accessed=old,
            item_type="temp",
        ),
    ]


# =============================================================================
# Test Enums
# =============================================================================

class TestEnums:
    """Test enum values."""
    
    def test_health_status_values(self):
        """Test health status enum."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.CRITICAL.value == "critical"
    
    def test_service_type_values(self):
        """Test service type enum."""
        assert ServiceType.DATABASE.value == "database"
        assert ServiceType.CACHE.value == "cache"
        assert ServiceType.WORKER.value == "worker"
    
    def test_healing_action_type_values(self):
        """Test healing action type enum."""
        assert HealingActionType.RESTART.value == "restart"
        assert HealingActionType.VACUUM.value == "vacuum"
    
    def test_backup_type_values(self):
        """Test backup type enum."""
        assert BackupType.FULL.value == "full"
        assert BackupType.INCREMENTAL.value == "incremental"
    
    def test_backup_status_values(self):
        """Test backup status enum."""
        assert BackupStatus.COMPLETED.value == "completed"
        assert BackupStatus.VERIFIED.value == "verified"
    
    def test_model_update_status_values(self):
        """Test model update status enum."""
        assert ModelUpdateStatus.ACTIVE.value == "active"
        assert ModelUpdateStatus.READY.value == "ready"


# =============================================================================
# Test Database Tuner
# =============================================================================

class TestDatabaseTuner:
    """Test database tuner."""
    
    def test_record_slow_query_below_threshold(self, db_tuner):
        """Test query below threshold not recorded."""
        result = db_tuner.record_slow_query(
            "SELECT * FROM users",
            duration_ms=50,  # Below 100ms threshold
        )
        
        assert result is None
    
    def test_record_slow_query_above_threshold(self, db_tuner):
        """Test query above threshold is recorded."""
        result = db_tuner.record_slow_query(
            "SELECT * FROM users WHERE email = 'test@test.com'",
            duration_ms=200,
        )
        
        assert result is not None
        assert result.duration_ms == 200
    
    def test_record_slow_query_frequency(self, db_tuner):
        """Test frequency tracking."""
        query = "SELECT * FROM orders WHERE status = 'pending'"
        
        db_tuner.record_slow_query(query, 150)
        result = db_tuner.record_slow_query(query, 180)
        
        assert result.frequency == 2
    
    def test_extract_table_name(self, db_tuner):
        """Test table name extraction."""
        table = db_tuner._extract_table_name(
            "SELECT * FROM orders WHERE id = 1"
        )
        
        assert table == "orders"
    
    def test_detect_missing_index(self, db_tuner):
        """Test missing index detection."""
        missing = db_tuner._detect_missing_index(
            "SELECT * FROM users WHERE email = 'test@test.com'"
        )
        
        assert missing == "email"
    
    def test_suggest_index(self, db_tuner):
        """Test index suggestion."""
        index = db_tuner._suggest_index(
            "SELECT * FROM users WHERE status = 'active' ORDER BY created_at",
            "users",
        )
        
        assert index is not None
        assert "users" in index
    
    def test_generate_recommendations(self, db_tuner):
        """Test recommendation generation."""
        # Add slow queries
        for i in range(10):
            db_tuner.record_slow_query(
                "SELECT * FROM products WHERE category = 'electronics'",
                duration_ms=200,
            )
        
        recommendations = db_tuner.generate_recommendations()
        
        # Should have recommendation for products.category
        assert len(recommendations) > 0
    
    def test_create_index(self, db_tuner):
        """Test CREATE INDEX statement generation."""
        rec = IndexRecommendation(
            recommendation_id="rec-001",
            table_name="users",
            column_names=["email", "status"],
        )
        
        sql = db_tuner.create_index(rec)
        
        assert "CREATE INDEX" in sql
        assert "users" in sql
        assert rec.created is True
    
    def test_drop_unused_index(self, db_tuner):
        """Test DROP INDEX statement generation."""
        sql = db_tuner.drop_unused_index("idx_old", "users")
        
        assert "DROP INDEX" in sql
        assert "idx_old" in sql
    
    def test_update_table_stats(self, db_tuner):
        """Test updating table stats."""
        stats = TableStats(
            table_name="users",
            row_count=10000,
            dead_tuples=500,
            table_size_mb=100,
            index_size_mb=20,
            bloat_ratio=0.05,
        )
        
        db_tuner.update_table_stats(stats)
        
        assert "users" in db_tuner._table_stats
    
    def test_get_bloated_tables(self, db_tuner):
        """Test getting bloated tables."""
        db_tuner.update_table_stats(TableStats(
            table_name="orders",
            row_count=50000,
            dead_tuples=15000,
            table_size_mb=500,
            index_size_mb=100,
            bloat_ratio=0.30,  # Above threshold
        ))
        
        bloated = db_tuner.get_bloated_tables()
        
        assert len(bloated) == 1
        assert bloated[0].table_name == "orders"
    
    def test_schedule_vacuum(self, db_tuner):
        """Test vacuum scheduling."""
        scheduled = db_tuner.schedule_vacuum("users")
        
        assert scheduled is not None
        assert "users" in db_tuner._vacuum_schedule
    
    def test_get_vacuum_commands(self, db_tuner):
        """Test vacuum command generation."""
        commands = db_tuner.get_vacuum_commands("orders")
        
        assert len(commands) > 0
        assert "VACUUM" in commands[0]


# =============================================================================
# Test Storage Manager
# =============================================================================

class TestStorageManager:
    """Test storage manager."""
    
    def test_check_disk_space_ok(self, storage_manager):
        """Test disk space check when OK."""
        result = storage_manager.check_disk_space(0.20)  # 20% free
        
        assert result is True
        assert not storage_manager.is_ingestion_paused
    
    def test_check_disk_space_low(self, storage_manager):
        """Test disk space check when low."""
        result = storage_manager.check_disk_space(0.05)  # 5% free
        
        assert result is False
        assert storage_manager.is_ingestion_paused
    
    def test_resume_ingestion(self, storage_manager):
        """Test resuming ingestion."""
        storage_manager.check_disk_space(0.05)  # Pause
        storage_manager.resume_ingestion()
        
        assert not storage_manager.is_ingestion_paused
    
    def test_register_item(self, storage_manager):
        """Test registering storage item."""
        item = StorageItem(
            item_id="test-001",
            path="/test/file.txt",
            size_bytes=1024,
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
        )
        
        storage_manager.register_item(item)
        
        assert len(storage_manager._storage_items) == 1
    
    def test_find_expired_logs(self, storage_manager, sample_storage_items):
        """Test finding expired logs."""
        for item in sample_storage_items:
            storage_manager.register_item(item)
        
        expired = storage_manager.find_expired_logs()
        
        assert len(expired) == 1
        assert expired[0].item_id == "log-001"
    
    def test_find_expired_temp_files(self, storage_manager, sample_storage_items):
        """Test finding expired temp files."""
        for item in sample_storage_items:
            storage_manager.register_item(item)
        
        expired = storage_manager.find_expired_temp_files()
        
        assert len(expired) == 1
        assert expired[0].item_id == "temp-001"
    
    def test_find_orphaned_files(self, storage_manager, sample_storage_items):
        """Test finding orphaned files."""
        for item in sample_storage_items:
            storage_manager.register_item(item)
        
        db_refs = {"file-001"}  # Only file-001 referenced
        orphans = storage_manager.find_orphaned_files(db_refs)
        
        assert len(orphans) == 2
        assert all(o.is_orphaned for o in orphans)
    
    def test_cleanup(self, storage_manager, sample_storage_items):
        """Test cleanup."""
        for item in sample_storage_items:
            storage_manager.register_item(item)
        
        result = storage_manager.cleanup(sample_storage_items)
        
        assert result.items_deleted == 3
        assert result.bytes_freed > 0
        assert len(storage_manager._storage_items) == 0
    
    def test_archive_item(self, storage_manager, sample_storage_items):
        """Test archiving item."""
        item = sample_storage_items[0]
        
        result = storage_manager.archive_item(item, "/archive/")
        
        assert result is True
        assert item.item_id in storage_manager._archived_items
    
    def test_get_storage_summary(self, storage_manager, sample_storage_items):
        """Test storage summary."""
        for item in sample_storage_items:
            storage_manager.register_item(item)
        
        summary = storage_manager.get_storage_summary()
        
        assert summary["total_items"] == 3
        assert summary["total_bytes"] > 0
        assert "file" in summary["by_type"]


# =============================================================================
# Test Self-Healing Engine
# =============================================================================

class TestSelfHealingEngine:
    """Test self-healing engine."""
    
    def test_register_service(self, healing_engine):
        """Test service registration."""
        healing_engine.register_service("redis", ServiceType.CACHE)
        
        assert "redis" in healing_engine._service_health
    
    def test_update_health_healthy(self, healing_engine):
        """Test updating healthy status."""
        healing_engine.register_service("api", ServiceType.API)
        healing_engine.update_health("api", HealthStatus.HEALTHY, 50.0)
        
        health = healing_engine._service_health["api"]
        assert health.status == HealthStatus.HEALTHY
        assert health.consecutive_failures == 0
    
    def test_update_health_critical(self, healing_engine):
        """Test updating critical status."""
        healing_engine.register_service("db", ServiceType.DATABASE)
        healing_engine.update_health(
            "db",
            HealthStatus.CRITICAL,
            error="Connection refused",
        )
        
        health = healing_engine._service_health["db"]
        assert health.consecutive_failures == 1
    
    def test_check_deep_health(self, healing_engine):
        """Test deep health check."""
        healing_engine.register_service("worker", ServiceType.WORKER)
        healing_engine.update_health("worker", HealthStatus.HEALTHY, 100.0)
        
        result = healing_engine.check_deep_health("worker")
        
        assert result["overall"] == "healthy"
        assert len(result["checks"]) > 0
    
    def test_determine_healing_action_healthy(self, healing_engine):
        """Test no action for healthy service."""
        healing_engine.register_service("api", ServiceType.API)
        healing_engine.update_health("api", HealthStatus.HEALTHY)
        
        action = healing_engine.determine_healing_action("api")
        
        assert action is None
    
    def test_determine_healing_action_worker(self, healing_engine):
        """Test restart action for worker."""
        healing_engine.register_service("worker", ServiceType.WORKER)
        healing_engine.update_health("worker", HealthStatus.CRITICAL)
        
        action = healing_engine.determine_healing_action("worker")
        
        assert action is not None
        assert action.action_type == HealingActionType.RESTART
    
    def test_determine_healing_action_cache(self, healing_engine):
        """Test reconnect action for cache."""
        healing_engine.register_service("redis", ServiceType.CACHE)
        healing_engine.update_health("redis", HealthStatus.DEGRADED)
        
        action = healing_engine.determine_healing_action("redis")
        
        assert action is not None
        assert action.action_type == HealingActionType.RECONNECT
    
    def test_execute_healing_dry_run(self, healing_engine):
        """Test healing execution in dry run."""
        action = HealingAction(
            action_id="act-001",
            action_type=HealingActionType.RESTART,
            service_name="worker",
            dry_run=True,
        )
        
        result = healing_engine.execute_healing(action)
        
        assert result is True
        assert action.executed is True
        assert action.details["mode"] == "dry_run"
    
    def test_execute_healing_real(self, healing_engine):
        """Test healing execution for real."""
        healing_engine.enable_dry_run(False)
        
        action = HealingAction(
            action_id="act-002",
            action_type=HealingActionType.RESTART,
            service_name="worker",
            dry_run=False,
        )
        
        result = healing_engine.execute_healing(action)
        
        assert result is True
        assert action.details["action"] == "restart_service"
    
    def test_get_healing_log(self, healing_engine):
        """Test getting healing log."""
        action = HealingAction(
            action_id="act-001",
            action_type=HealingActionType.RESTART,
            service_name="worker",
            dry_run=True,
        )
        healing_engine.execute_healing(action)
        
        log = healing_engine.get_healing_log()
        
        assert len(log) == 1
    
    def test_check_data_integrity(self, healing_engine):
        """Test data integrity check."""
        db_ids = {"a", "b", "c", "d"}
        storage_ids = {"b", "c", "e", "f"}
        
        result = healing_engine.check_data_integrity(db_ids, storage_ids)
        
        assert result.orphaned_db == 2  # a, d
        assert result.orphaned_storage == 2  # e, f
        assert result.passed is False


# =============================================================================
# Test Backup Manager
# =============================================================================

class TestBackupManager:
    """Test backup manager."""
    
    def test_create_backup(self, backup_manager):
        """Test creating backup."""
        backup = backup_manager.create_backup()
        
        assert backup.status == BackupStatus.COMPLETED
        assert backup.checksum != ""
        assert backup.encrypted is True
    
    def test_create_backup_with_data(self, backup_manager):
        """Test creating backup with data."""
        data = b"Test backup data"
        backup = backup_manager.create_backup(source_data=data)
        
        assert backup.size_bytes == len(data)
    
    def test_backup_rotation(self, backup_manager):
        """Test backup rotation."""
        # Create more than max_backups
        for i in range(7):
            backup_manager.create_backup()
        
        assert len(backup_manager._backups) == 5  # max_backups
    
    def test_verify_backup(self, backup_manager):
        """Test backup verification."""
        backup = backup_manager.create_backup()
        
        result = backup_manager.verify_backup(backup.backup_id)
        
        assert result.success is True
        assert backup.status == BackupStatus.VERIFIED
        assert len(result.verification_steps) > 0
    
    def test_verify_backup_not_found(self, backup_manager):
        """Test verifying non-existent backup."""
        result = backup_manager.verify_backup("nonexistent")
        
        assert result.success is False
        assert "not found" in result.errors[0].lower()
    
    def test_get_backup(self, backup_manager):
        """Test getting backup by ID."""
        backup = backup_manager.create_backup()
        
        found = backup_manager.get_backup(backup.backup_id)
        
        assert found is not None
        assert found.backup_id == backup.backup_id
    
    def test_get_latest_backup(self, backup_manager):
        """Test getting latest backup."""
        backup_manager.create_backup()
        latest = backup_manager.create_backup()
        
        found = backup_manager.get_latest_backup()
        
        assert found.backup_id == latest.backup_id
    
    def test_get_latest_verified_backup(self, backup_manager):
        """Test getting latest verified backup."""
        backup1 = backup_manager.create_backup()
        backup_manager.verify_backup(backup1.backup_id)
        backup_manager.create_backup()  # Not verified
        
        found = backup_manager.get_latest_backup(verified_only=True)
        
        assert found.backup_id == backup1.backup_id
    
    def test_list_backups(self, backup_manager):
        """Test listing backups."""
        backup_manager.create_backup()
        backup_manager.create_backup()
        
        backups = backup_manager.list_backups()
        
        assert len(backups) == 2
        # Should be sorted newest first
        assert backups[0].created_at >= backups[1].created_at


# =============================================================================
# Test Model Lifecycle Manager
# =============================================================================

class TestModelLifecycleManager:
    """Test model lifecycle manager."""
    
    def test_register_model(self, model_manager):
        """Test registering model."""
        mv = model_manager.register_model(
            model_id="bert",
            version="1.0.0",
            size_bytes=500000,
        )
        
        assert mv.model_id == "bert"
        assert mv.version == "1.0.0"
        assert "bert" in model_manager._versions
    
    def test_check_for_updates(self, model_manager):
        """Test checking for updates."""
        model_manager.register_model("bert", "1.0.0", 500000)
        
        available = ["1.0.0", "1.1.0", "2.0.0"]
        new = model_manager.check_for_updates("bert", available)
        
        assert "1.1.0" in new
        assert "2.0.0" in new
        assert "1.0.0" not in new
    
    def test_download_update(self, model_manager):
        """Test downloading update."""
        mv = model_manager.download_update("bert", "1.1.0", 600000)
        
        assert mv.status == ModelUpdateStatus.READY
        assert mv.downloaded_at is not None
    
    def test_activate_model(self, model_manager):
        """Test activating model."""
        model_manager.download_update("bert", "1.0.0", 500000)
        
        result = model_manager.activate_model("bert", "1.0.0")
        
        assert result is True
        assert model_manager._active_models["bert"] == "1.0.0"
    
    def test_activate_model_deactivates_previous(self, model_manager):
        """Test activating new version deactivates old."""
        model_manager.download_update("bert", "1.0.0", 500000)
        model_manager.activate_model("bert", "1.0.0")
        
        model_manager.download_update("bert", "1.1.0", 600000)
        model_manager.activate_model("bert", "1.1.0")
        
        versions = model_manager._versions["bert"]
        v1 = next(v for v in versions if v.version == "1.0.0")
        v2 = next(v for v in versions if v.version == "1.1.0")
        
        assert v1.status == ModelUpdateStatus.READY
        assert v2.status == ModelUpdateStatus.ACTIVE
    
    def test_register_fallback(self, model_manager):
        """Test registering fallback."""
        model_manager.register_fallback("bert-large", "bert-tiny")
        
        assert model_manager._fallback_mapping["bert-large"] == "bert-tiny"
    
    def test_switch_to_fallback(self, model_manager):
        """Test switching to fallback."""
        model_manager.download_update("bert-large", "1.0.0", 1000000)
        model_manager.activate_model("bert-large", "1.0.0")
        
        model_manager.download_update("bert-tiny", "1.0.0", 100000)
        model_manager.register_fallback("bert-large", "bert-tiny")
        
        result = model_manager.switch_to_fallback("bert-large")
        
        assert result is True
    
    def test_get_active_version(self, model_manager):
        """Test getting active version."""
        model_manager.download_update("bert", "1.0.0", 500000)
        model_manager.activate_model("bert", "1.0.0")
        
        active = model_manager.get_active_version("bert")
        
        assert active is not None
        assert active.version == "1.0.0"
        assert active.status == ModelUpdateStatus.ACTIVE
    
    def test_get_model_stats(self, model_manager):
        """Test getting model stats."""
        model_manager.download_update("bert", "1.0.0", 500000)
        model_manager.download_update("bert", "1.1.0", 600000)
        model_manager.activate_model("bert", "1.0.0")
        
        stats = model_manager.get_model_stats()
        
        assert stats["total_models"] == 1
        assert stats["total_versions"] == 2
        assert stats["active_models"] == 1


# =============================================================================
# Test Sensei Autopilot
# =============================================================================

class TestSenseiAutopilot:
    """Test Sensei Autopilot integration."""
    
    def test_components_accessible(self, autopilot):
        """Test all components are accessible."""
        assert autopilot.db_tuner is not None
        assert autopilot.storage is not None
        assert autopilot.healing is not None
        assert autopilot.backup is not None
        assert autopilot.models is not None
    
    def test_run_maintenance_cycle(self, autopilot):
        """Test running maintenance cycle."""
        results = autopilot.run_maintenance_cycle()
        
        assert "started_at" in results
        assert "completed_at" in results
        assert "steps" in results
        assert len(results["steps"]) >= 3
    
    def test_maintenance_cycle_includes_backup(self, autopilot):
        """Test maintenance cycle creates backup."""
        results = autopilot.run_maintenance_cycle()
        
        # Should have backup step
        backup_step = next(
            (s for s in results["steps"] if s.get("step") == "backup"),
            None,
        )
        
        assert backup_step is not None
        assert "backup_id" in backup_step


# =============================================================================
# Test Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_autopilot(self):
        """Test creating autopilot."""
        autopilot = create_autopilot()
        
        assert autopilot is not None
        assert isinstance(autopilot, SenseiAutopilot)
    
    def test_create_db_tuner(self):
        """Test creating db tuner."""
        tuner = create_db_tuner()
        
        assert tuner is not None
        assert tuner._slow_query_threshold == INDEX_ANALYSIS_THRESHOLD_MS
    
    def test_create_db_tuner_custom(self):
        """Test creating db tuner with custom threshold."""
        tuner = create_db_tuner(slow_query_threshold_ms=50.0)
        
        assert tuner._slow_query_threshold == 50.0
    
    def test_create_storage_manager(self):
        """Test creating storage manager."""
        manager = create_storage_manager()
        
        assert manager is not None
    
    def test_create_healing_engine(self):
        """Test creating healing engine."""
        engine = create_healing_engine()
        
        assert engine is not None
        assert engine._dry_run is True
    
    def test_create_backup_manager(self):
        """Test creating backup manager."""
        manager = create_backup_manager()
        
        assert manager is not None


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_query_normalization(self, db_tuner):
        """Test normalizing empty query."""
        normalized = db_tuner._normalize_query("")
        
        assert normalized == ""
    
    def test_query_without_table(self, db_tuner):
        """Test query without FROM clause."""
        table = db_tuner._extract_table_name("SELECT 1")
        
        assert table == ""
    
    def test_query_without_where(self, db_tuner):
        """Test query without WHERE clause."""
        missing = db_tuner._detect_missing_index("SELECT * FROM users")
        
        assert missing is None
    
    def test_cleanup_empty_list(self, storage_manager):
        """Test cleanup with empty list."""
        result = storage_manager.cleanup([])
        
        assert result.items_deleted == 0
        assert result.bytes_freed == 0
    
    def test_health_service_not_registered(self, healing_engine):
        """Test updating health for unregistered service."""
        healing_engine.update_health("unknown", HealthStatus.HEALTHY)
        
        assert "unknown" not in healing_engine._service_health
    
    def test_backup_type_incremental(self, backup_manager):
        """Test incremental backup."""
        backup = backup_manager.create_backup(BackupType.INCREMENTAL)
        
        assert backup.backup_type == BackupType.INCREMENTAL
    
    def test_activate_nonexistent_model(self, model_manager):
        """Test activating non-existent model."""
        result = model_manager.activate_model("nonexistent", "1.0.0")
        
        assert result is False
    
    def test_healing_action_vacuum(self, healing_engine):
        """Test vacuum action for database bloat."""
        healing_engine.register_service("db", ServiceType.DATABASE)
        healing_engine.update_health(
            "db",
            HealthStatus.DEGRADED,
            error="Table bloat detected",
        )
        
        action = healing_engine.determine_healing_action("db")
        
        assert action is not None
        assert action.action_type == HealingActionType.VACUUM


# =============================================================================
# Test Constants
# =============================================================================

class TestConstants:
    """Test module constants."""
    
    def test_bloat_threshold(self):
        """Test bloat threshold value."""
        assert BLOAT_THRESHOLD == 0.20
    
    def test_disk_safeguard_threshold(self):
        """Test disk safeguard threshold."""
        assert DISK_SAFEGUARD_THRESHOLD == 0.10
    
    def test_index_analysis_threshold(self):
        """Test index analysis threshold."""
        assert INDEX_ANALYSIS_THRESHOLD_MS == 100

"""
Tests for Database Backup and Restore Service

Validates automated backups, restore operations, RPO/RTO tracking,
and disaster recovery capabilities.
"""

import gzip
import hashlib
import json
import tempfile
from datetime import datetime, timedelta
from datetime import timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from sensei.services.core.database_backup import (
    BackupMetadata,
    BackupSchedule,
    BackupStatus,
    BackupStrategy,
    DatabaseBackupService,
    RestoreStatus,
    RestoreTest,
)


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Create temporary backup directory"""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = Mock()
    return session


@pytest.fixture
def mock_db_session_factory(mock_db_session):
    """Create mock database session factory"""
    return lambda: mock_db_session


@pytest.fixture
def service(temp_backup_dir, mock_db_session_factory):
    """Create database backup service"""
    return DatabaseBackupService(
        db_session_factory=mock_db_session_factory,
        backup_storage_path=str(temp_backup_dir),
        database_url="postgresql://user:pass@localhost:5432/testdb"
    )


class TestDatabaseBackupService:
    """Test DatabaseBackupService"""
    
    def test_service_initialization(self, service, temp_backup_dir):
        """Test service initialization"""
        assert service.backup_storage_path == temp_backup_dir
        assert service.compression_enabled is True
        assert service.encryption_enabled is False
        assert service.verify_backups is True
        assert service.target_rpo_hours == 24
        assert service.target_rto_minutes == 30
        assert service.backups == []
        assert service.restore_tests == []
    
    def test_parse_database_url(self, service):
        """Test parsing database URL"""
        config = service._parse_database_url()
        
        assert config["user"] == "user"
        assert config["password"] == "pass"
        assert config["host"] == "localhost"
        assert config["port"] == "5432"
        assert config["database"] == "testdb"
    
    def test_generate_backup_id(self, service):
        """Test backup ID generation"""
        backup_id1 = service._generate_backup_id()
        backup_id2 = service._generate_backup_id()
        
        assert backup_id1.startswith("backup_")
        assert backup_id2.startswith("backup_")
        assert backup_id1 != backup_id2  # Should be unique
    
    def test_calculate_checksum(self, service, tmp_path):
        """Test file checksum calculation"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        checksum = service._calculate_checksum(test_file)
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex digest
        
        # Verify checksum is consistent
        checksum2 = service._calculate_checksum(test_file)
        assert checksum == checksum2
    
    def test_compress_file(self, service, tmp_path):
        """Test file compression"""
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.txt.gz"
        
        # Create larger content that benefits from compression
        content = "test content for compression " * 1000
        input_file.write_text(content)
        
        service._compress_file(input_file, output_file)
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        # For larger files, compression should be effective
        assert output_file.stat().st_size < input_file.stat().st_size
    
    def test_decompress_file(self, service, tmp_path):
        """Test file decompression"""
        input_file = tmp_path / "input.txt"
        compressed_file = tmp_path / "compressed.txt.gz"
        output_file = tmp_path / "output.txt"
        
        original_content = "test content for compression and decompression"
        input_file.write_text(original_content)
        
        # Compress
        service._compress_file(input_file, compressed_file)
        
        # Decompress
        service._decompress_file(compressed_file, output_file)
        
        assert output_file.exists()
        assert output_file.read_text() == original_content
    
    @patch('sensei.services.core.database_backup.subprocess.run')
    def test_create_backup_success(self, mock_subprocess, service, temp_backup_dir):
        """Test successful backup creation"""
        # Mock successful pg_dump that creates the backup file
        def mock_pg_dump(command, env, capture_output, text, timeout):
            # Extract the output file path from command
            file_idx = command.index("-f") + 1
            output_file = Path(command[file_idx])
            
            # Create the backup file
            output_file.write_text("-- PostgreSQL database dump\n" * 1000)
            
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            return mock_result
        
        mock_subprocess.side_effect = mock_pg_dump
        
        metadata = service.create_backup(BackupStrategy.FULL)
        
        assert metadata.strategy == BackupStrategy.FULL
        assert metadata.status in (BackupStatus.VERIFIED, BackupStatus.COMPLETED)
        assert metadata.database_name == "testdb"
        assert metadata.checksum != ""
        assert len(service.backups) == 1
    
    @patch('sensei.services.core.database_backup.subprocess.run')
    def test_create_backup_pg_dump_failure(self, mock_subprocess, service):
        """Test backup creation when pg_dump fails"""
        # Mock failed pg_dump
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection failed"
        mock_subprocess.return_value = mock_result
        
        metadata = service.create_backup(BackupStrategy.FULL)
        
        assert metadata.status == BackupStatus.FAILED
        assert "pg_dump failed" in metadata.error_message
    
    def test_verify_backup_success(self, service, tmp_path):
        """Test backup verification success"""
        backup_file = tmp_path / "backup.sql.gz"
        backup_file.write_text("backup content")
        
        checksum = service._calculate_checksum(backup_file)
        
        metadata = BackupMetadata(
            backup_id="test123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc),
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum=checksum,
            encryption_enabled=False,
            status=BackupStatus.COMPLETED,
            file_path=str(backup_file)
        )
        
        result = service._verify_backup(metadata)
        assert result is True
    
    def test_verify_backup_file_not_found(self, service):
        """Test backup verification when file doesn't exist"""
        metadata = BackupMetadata(
            backup_id="test123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc),
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum="abc123",
            encryption_enabled=False,
            status=BackupStatus.COMPLETED,
            file_path="/nonexistent/file.sql.gz"
        )
        
        result = service._verify_backup(metadata)
        assert result is False
    
    def test_verify_backup_checksum_mismatch(self, service, tmp_path):
        """Test backup verification with checksum mismatch"""
        backup_file = tmp_path / "backup.sql.gz"
        backup_file.write_text("backup content")
        
        metadata = BackupMetadata(
            backup_id="test123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc),
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum="wrong_checksum",
            encryption_enabled=False,
            status=BackupStatus.COMPLETED,
            file_path=str(backup_file)
        )
        
        result = service._verify_backup(metadata)
        assert result is False
    
    def test_apply_retention_policy(self, service, tmp_path):
        """Test applying retention policy"""
        # Create old and recent backups
        old_backup = BackupMetadata(
            backup_id="old123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc) - timedelta(days=40),
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum="abc",
            encryption_enabled=False,
            status=BackupStatus.COMPLETED,
            file_path=str(tmp_path / "old.sql.gz")
        )
        
        recent_backup = BackupMetadata(
            backup_id="recent123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc) - timedelta(days=10),
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum="def",
            encryption_enabled=False,
            status=BackupStatus.COMPLETED,
            file_path=str(tmp_path / "recent.sql.gz")
        )
        
        # Create backup files
        Path(old_backup.file_path).write_text("old")
        Path(recent_backup.file_path).write_text("recent")
        
        service.backups = [old_backup, recent_backup]
        
        # Apply 30-day retention
        removed = service.apply_retention_policy(retention_days=30)
        
        assert removed == 1
        assert len(service.backups) == 1
        assert service.backups[0].backup_id == "recent123"
        assert not Path(old_backup.file_path).exists()
        assert Path(recent_backup.file_path).exists()
    
    def test_get_rpo_status_no_backups(self, service):
        """Test RPO status with no backups"""
        status = service.get_rpo_status()
        
        assert status["status"] == "critical"
        assert "No backups available" in status["message"]
        assert status["within_target"] is False
    
    def test_get_rpo_status_within_target(self, service):
        """Test RPO status within target"""
        backup = BackupMetadata(
            backup_id="test123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=12),  # 12 hours ago
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum="abc",
            encryption_enabled=False,
            status=BackupStatus.VERIFIED,
            file_path="/path/backup.sql.gz"
        )
        
        service.backups = [backup]
        
        status = service.get_rpo_status()
        
        assert status["status"] == "healthy"
        assert status["within_target"] is True
        assert status["hours_since_backup"] < 24
    
    def test_get_rpo_status_outside_target(self, service):
        """Test RPO status outside target"""
        backup = BackupMetadata(
            backup_id="test123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=50),  # 50 hours ago
            database_name="testdb",
            size_bytes=1000,
            compressed_size_bytes=500,
            checksum="abc",
            encryption_enabled=False,
            status=BackupStatus.VERIFIED,
            file_path="/path/backup.sql.gz"
        )
        
        service.backups = [backup]
        
        status = service.get_rpo_status()
        
        assert status["status"] == "critical"
        assert status["within_target"] is False
        assert status["hours_since_backup"] > 24
    
    def test_get_rto_status_no_tests(self, service):
        """Test RTO status with no restore tests"""
        status = service.get_rto_status()
        
        assert status["status"] == "unknown"
        assert "No restore tests" in status["message"]
        assert status["within_target"] is False
    
    def test_get_rto_status_within_target(self, service):
        """Test RTO status within target"""
        restore_test = RestoreTest(
            test_id="test123",
            backup_id="backup123",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=20),
            end_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            status=RestoreStatus.SUCCESS,
            rto_seconds=900,  # 15 minutes
            verification_passed=True
        )
        
        service.restore_tests = [restore_test]
        
        status = service.get_rto_status()
        
        assert status["status"] == "healthy"
        assert status["within_target"] is True
        assert status["rto_seconds"] == 900
    
    def test_get_rto_status_outside_target(self, service):
        """Test RTO status outside target"""
        restore_test = RestoreTest(
            test_id="test123",
            backup_id="backup123",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=50),
            end_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            status=RestoreStatus.SUCCESS,
            rto_seconds=2700,  # 45 minutes (exceeds 30 minute target)
            verification_passed=True
        )
        
        service.restore_tests = [restore_test]
        
        status = service.get_rto_status()
        
        assert status["status"] == "warning"
        assert status["within_target"] is False
        assert status["rto_seconds"] == 2700
    
    def test_get_backup_summary(self, service, tmp_path):
        """Test getting backup summary"""
        # Add some backups
        backup1 = BackupMetadata(
            backup_id="b1",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc),
            database_name="testdb",
            size_bytes=1024 * 1024 * 10,  # 10MB
            compressed_size_bytes=1024 * 1024 * 5,  # 5MB
            checksum="abc",
            encryption_enabled=False,
            status=BackupStatus.VERIFIED,
            file_path=str(tmp_path / "b1.sql.gz")
        )
        
        backup2 = BackupMetadata(
            backup_id="b2",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc),
            database_name="testdb",
            size_bytes=1024 * 1024 * 8,  # 8MB
            compressed_size_bytes=1024 * 1024 * 4,  # 4MB
            checksum="def",
            encryption_enabled=False,
            status=BackupStatus.FAILED,
            file_path=str(tmp_path / "b2.sql.gz")
        )
        
        service.backups = [backup1, backup2]
        
        summary = service.get_backup_summary()
        
        assert summary["total_backups"] == 2
        assert summary["successful_backups"] == 1
        assert summary["failed_backups"] == 1
        assert summary["total_size_mb"] == 9.0  # 5MB + 4MB
        assert summary["compression_enabled"] is True
        assert summary["encryption_enabled"] is False
        assert "rpo_status" in summary
        assert "rto_status" in summary


class TestBackupMetadata:
    """Test BackupMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating backup metadata"""
        metadata = BackupMetadata(
            backup_id="test123",
            strategy=BackupStrategy.FULL,
            timestamp=datetime.now(timezone.utc),
            database_name="testdb",
            size_bytes=1024 * 1024,
            compressed_size_bytes=512 * 1024,
            checksum="abc123",
            encryption_enabled=False,
            status=BackupStatus.COMPLETED,
            file_path="/path/backup.sql.gz"
        )
        
        assert metadata.backup_id == "test123"
        assert metadata.strategy == BackupStrategy.FULL
        assert metadata.database_name == "testdb"
        assert metadata.status == BackupStatus.COMPLETED


class TestRestoreTest:
    """Test RestoreTest dataclass"""
    
    def test_restore_test_creation(self):
        """Test creating restore test"""
        start = datetime.now(timezone.utc)
        end = start + timedelta(minutes=15)
        
        test = RestoreTest(
            test_id="test123",
            backup_id="backup123",
            start_time=start,
            end_time=end,
            status=RestoreStatus.SUCCESS,
            rto_seconds=900,
            verification_passed=True,
            test_database="test_restore_db"
        )
        
        assert test.test_id == "test123"
        assert test.backup_id == "backup123"
        assert test.status == RestoreStatus.SUCCESS
        assert test.rto_seconds == 900
        assert test.verification_passed is True


class TestBackupSchedule:
    """Test BackupSchedule dataclass"""
    
    def test_schedule_creation(self):
        """Test creating backup schedule"""
        schedule = BackupSchedule(
            name="Daily Full Backup",
            strategy=BackupStrategy.FULL,
            frequency="daily",
            retention_days=30,
            enabled=True,
            last_run=datetime.now(timezone.utc) - timedelta(days=1),
            next_run=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        assert schedule.name == "Daily Full Backup"
        assert schedule.strategy == BackupStrategy.FULL
        assert schedule.frequency == "daily"
        assert schedule.retention_days == 30
        assert schedule.enabled is True

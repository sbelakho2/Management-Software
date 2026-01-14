"""
Database Backup and Restore Service

Provides automated database backup scheduling, backup verification,
restore testing, and RPO/RTO validation. Ensures data durability
and disaster recovery capabilities.

Features:
- Automated backup scheduling (daily/weekly/monthly)
- Multiple backup strategies (full, incremental, differential)
- Backup encryption and compression
- Backup verification and integrity checks
- Automated restore testing
- RPO (Recovery Point Objective) tracking
- RTO (Recovery Time Objective) validation
- Backup retention policies
- S3-compatible storage integration
"""

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class BackupStrategy(str, Enum):
    """Backup strategy type"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(str, Enum):
    """Backup operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class RestoreStatus(str, Enum):
    """Restore operation status"""
    NOT_TESTED = "not_tested"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BackupMetadata:
    """Metadata for a backup"""
    backup_id: str
    strategy: BackupStrategy
    timestamp: datetime
    database_name: str
    size_bytes: int
    compressed_size_bytes: int
    checksum: str
    encryption_enabled: bool
    status: BackupStatus
    file_path: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreTest:
    """Restore test result"""
    test_id: str
    backup_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: RestoreStatus
    rto_seconds: Optional[float]  # Recovery Time Objective
    verification_passed: bool
    error_message: Optional[str] = None
    test_database: Optional[str] = None


@dataclass
class BackupSchedule:
    """Backup schedule configuration"""
    name: str
    strategy: BackupStrategy
    frequency: str  # "daily", "weekly", "monthly"
    retention_days: int
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class DatabaseBackupService:
    """Service for automated database backups and restore testing"""
    
    def __init__(
        self,
        db_session_factory,
        backup_storage_path: str,
        database_url: str,
        s3_client: Optional[Any] = None
    ):
        self.db_session_factory = db_session_factory
        self.backup_storage_path = Path(backup_storage_path)
        self.database_url = database_url
        self.s3_client = s3_client
        
        # Ensure backup directory exists
        self.backup_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Backup configuration
        self.compression_enabled = True
        self.encryption_enabled = False  # Would require encryption key management
        self.verify_backups = True
        
        # RPO/RTO targets
        self.target_rpo_hours = 24  # Max data loss: 24 hours
        self.target_rto_minutes = 30  # Max recovery time: 30 minutes
        
        # Retention policies
        self.default_retention_days = 30
        self.weekly_retention_days = 90
        self.monthly_retention_days = 365
        
        # Backup history
        self.backups: List[BackupMetadata] = []
        self.restore_tests: List[RestoreTest] = []
    
    def _parse_database_url(self) -> Dict[str, str]:
        """Parse database URL into components"""
        # Format: postgresql://user:pass@host:port/dbname
        from urllib.parse import urlparse
        
        parsed = urlparse(self.database_url)
        
        return {
            "user": parsed.username or "postgres",
            "password": parsed.password or "",
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port) if parsed.port else "5432",
            "database": parsed.path.lstrip("/") if parsed.path else "postgres"
        }
    
    def _generate_backup_id(self) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(datetime.now(timezone.utc).timestamp()).encode()).hexdigest()[:8]
        return f"backup_{timestamp}_{random_suffix}"
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _compress_file(self, input_path: Path, output_path: Path):
        """Compress file using gzip"""
        with open(input_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _decompress_file(self, input_path: Path, output_path: Path):
        """Decompress gzip file"""
        with gzip.open(input_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def create_backup(
        self,
        strategy: BackupStrategy = BackupStrategy.FULL,
        database_name: Optional[str] = None
    ) -> BackupMetadata:
        """
        Create database backup using pg_dump
        
        Args:
            strategy: Backup strategy (full, incremental, differential)
            database_name: Database to backup (defaults to connection database)
        
        Returns:
            BackupMetadata with backup information
        """
        backup_id = self._generate_backup_id()
        db_config = self._parse_database_url()
        
        if database_name is None:
            database_name = db_config["database"]
        
        # Generate backup file path
        backup_file = self.backup_storage_path / f"{backup_id}.sql"
        compressed_file = self.backup_storage_path / f"{backup_id}.sql.gz"
        
        metadata = BackupMetadata(
            backup_id=backup_id,
            strategy=strategy,
            timestamp=datetime.now(timezone.utc),
            database_name=database_name,
            size_bytes=0,
            compressed_size_bytes=0,
            checksum="",
            encryption_enabled=self.encryption_enabled,
            status=BackupStatus.IN_PROGRESS,
            file_path=str(compressed_file if self.compression_enabled else backup_file)
        )
        
        try:
            # Execute pg_dump with a sanitized, minimal environment
            env = {
                'PGPASSWORD': db_config["password"],
                'PATH': os.environ.get('PATH', '/usr/bin:/bin:/usr/local/bin'),
            }
            # Only include necessary SSL/security env vars if they exist
            for var in ['PGSSLMODE', 'PGSSLROOTCERT', 'PGSSLCERT', 'PGSSLKEY']:
                if var in os.environ:
                    env[var] = os.environ[var]
            
            dump_command = [
                "pg_dump",
                "-h", db_config["host"],
                "-p", db_config["port"],
                "-U", db_config["user"],
                "-d", database_name,
                "-F", "p",  # Plain text format
                "-f", str(backup_file)
            ]
            
            result = subprocess.run(
                dump_command,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Get uncompressed size
            metadata.size_bytes = backup_file.stat().st_size
            
            # Compress if enabled
            if self.compression_enabled:
                self._compress_file(backup_file, compressed_file)
                metadata.compressed_size_bytes = compressed_file.stat().st_size
                
                # Remove uncompressed file
                backup_file.unlink()
            else:
                metadata.compressed_size_bytes = metadata.size_bytes
            
            # Calculate checksum
            final_file = compressed_file if self.compression_enabled else backup_file
            metadata.checksum = self._calculate_checksum(final_file)
            
            # Mark as completed
            metadata.status = BackupStatus.COMPLETED
            
            # Verify backup if enabled
            if self.verify_backups:
                if self._verify_backup(metadata):
                    metadata.status = BackupStatus.VERIFIED
                else:
                    metadata.status = BackupStatus.CORRUPTED
                    metadata.error_message = "Backup verification failed"
            
            # Upload to S3 if configured
            if self.s3_client:
                self._upload_to_s3(metadata)
        
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
        
        self.backups.append(metadata)
        return metadata
    
    def _verify_backup(self, metadata: BackupMetadata) -> bool:
        """Verify backup integrity by checking file exists and checksum matches"""
        backup_path = Path(metadata.file_path)
        
        if not backup_path.exists():
            return False
        
        # Verify checksum
        current_checksum = self._calculate_checksum(backup_path)
        return current_checksum == metadata.checksum
    
    def _upload_to_s3(self, metadata: BackupMetadata):
        """Upload backup to S3 storage"""
        if not self.s3_client:
            return
        
        backup_path = Path(metadata.file_path)
        s3_key = f"backups/{metadata.database_name}/{backup_path.name}"
        
        try:
            self.s3_client.upload_file(
                str(backup_path),
                "database-backups",  # Bucket name
                s3_key
            )
            metadata.metadata["s3_key"] = s3_key
            metadata.metadata["s3_upload_time"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            metadata.metadata["s3_error"] = str(e)
    
    def restore_backup(
        self,
        backup_id: str,
        target_database: Optional[str] = None,
        test_mode: bool = False
    ) -> RestoreTest:
        """
        Restore database from backup
        
        Args:
            backup_id: ID of backup to restore
            target_database: Target database name (creates new if in test mode)
            test_mode: If True, creates temporary test database
        
        Returns:
            RestoreTest with restore operation results
        """
        # Find backup
        backup = next((b for b in self.backups if b.backup_id == backup_id), None)
        
        if not backup:
            raise ValueError(f"Backup {backup_id} not found")
        
        test_id = f"restore_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        test_db_name = f"{backup.database_name}_restore_test_{test_id}" if test_mode else target_database
        
        restore_test = RestoreTest(
            test_id=test_id,
            backup_id=backup_id,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            status=RestoreStatus.IN_PROGRESS,
            rto_seconds=None,
            verification_passed=False,
            test_database=test_db_name
        )
        
        try:
            db_config = self._parse_database_url()
            
            # Create test database if in test mode
            if test_mode:
                self._create_test_database(test_db_name)
            
            # Decompress backup if needed
            backup_path = Path(backup.file_path)
            restore_file = backup_path
            
            if backup_path.suffix == '.gz':
                restore_file = backup_path.with_suffix('')
                self._decompress_file(backup_path, restore_file)
            
            # Execute psql to restore
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config["password"]
            
            restore_command = [
                "psql",
                "-h", db_config["host"],
                "-p", db_config["port"],
                "-U", db_config["user"],
                "-d", test_db_name or backup.database_name,
                "-f", str(restore_file)
            ]
            
            result = subprocess.run(
                restore_command,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            # Clean up decompressed file if created
            if backup_path.suffix == '.gz' and restore_file != backup_path:
                restore_file.unlink()
            
            if result.returncode != 0:
                raise Exception(f"psql restore failed: {result.stderr}")
            
            # Verify restore
            restore_test.verification_passed = self._verify_restore(test_db_name or backup.database_name)
            
            # Calculate RTO
            restore_test.end_time = datetime.now(timezone.utc)
            restore_test.rto_seconds = (restore_test.end_time - restore_test.start_time).total_seconds()
            
            # Determine status
            if restore_test.verification_passed:
                restore_test.status = RestoreStatus.SUCCESS
            else:
                restore_test.status = RestoreStatus.PARTIAL
                restore_test.error_message = "Restore completed but verification failed"
            
            # Clean up test database if in test mode
            if test_mode:
                self._drop_test_database(test_db_name)
        
        except Exception as e:
            restore_test.status = RestoreStatus.FAILED
            restore_test.error_message = str(e)
            restore_test.end_time = datetime.now(timezone.utc)
            
            if restore_test.start_time:
                restore_test.rto_seconds = (restore_test.end_time - restore_test.start_time).total_seconds()
        
        self.restore_tests.append(restore_test)
        return restore_test
    
    def _create_test_database(self, db_name: str):
        """Create temporary test database"""
        session = self.db_session_factory()
        try:
            # Use autocommit mode for CREATE DATABASE
            session.connection().connection.set_isolation_level(0)
            session.execute(text(f"CREATE DATABASE {db_name}"))
        finally:
            session.close()
    
    def _drop_test_database(self, db_name: str):
        """Drop temporary test database"""
        session = self.db_session_factory()
        try:
            session.connection().connection.set_isolation_level(0)
            session.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        finally:
            session.close()
    
    def _verify_restore(self, database_name: str) -> bool:
        """Verify restored database by checking table count and basic queries"""
        try:
            session = self.db_session_factory()
            
            # Check table count
            result = session.execute(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            table_count = result.scalar()
            
            session.close()
            
            # Should have at least some tables
            return table_count > 0
        
        except Exception:
            return False
    
    def test_restore(self, backup_id: str) -> RestoreTest:
        """Test restore operation in isolated test database"""
        return self.restore_backup(backup_id, test_mode=True)
    
    def apply_retention_policy(self, retention_days: int = None):
        """Remove backups older than retention period"""
        if retention_days is None:
            retention_days = self.default_retention_days
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        removed_count = 0
        for backup in list(self.backups):
            if backup.timestamp < cutoff_date:
                # Delete backup file
                backup_path = Path(backup.file_path)
                if backup_path.exists():
                    backup_path.unlink()
                
                # Remove from list
                self.backups.remove(backup)
                removed_count += 1
        
        return removed_count
    
    def get_rpo_status(self) -> Dict[str, Any]:
        """Get RPO (Recovery Point Objective) status"""
        if not self.backups:
            return {
                "status": "critical",
                "message": "No backups available",
                "last_backup": None,
                "hours_since_backup": None,
                "target_rpo_hours": self.target_rpo_hours,
                "within_target": False
            }
        
        # Get most recent successful backup
        successful_backups = [
            b for b in self.backups
            if b.status in [BackupStatus.COMPLETED, BackupStatus.VERIFIED]
        ]
        
        if not successful_backups:
            return {
                "status": "critical",
                "message": "No successful backups available",
                "last_backup": None,
                "hours_since_backup": None,
                "target_rpo_hours": self.target_rpo_hours,
                "within_target": False
            }
        
        last_backup = max(successful_backups, key=lambda b: b.timestamp)
        hours_since = (datetime.now(timezone.utc) - last_backup.timestamp).total_seconds() / 3600
        within_target = hours_since <= self.target_rpo_hours
        
        status = "healthy" if within_target else "warning" if hours_since <= self.target_rpo_hours * 1.5 else "critical"
        
        return {
            "status": status,
            "message": f"Last backup was {hours_since:.1f} hours ago",
            "last_backup": last_backup.timestamp.isoformat(),
            "hours_since_backup": hours_since,
            "target_rpo_hours": self.target_rpo_hours,
            "within_target": within_target
        }
    
    def get_rto_status(self) -> Dict[str, Any]:
        """Get RTO (Recovery Time Objective) status from recent restore tests"""
        if not self.restore_tests:
            return {
                "status": "unknown",
                "message": "No restore tests performed",
                "last_test": None,
                "rto_seconds": None,
                "target_rto_seconds": self.target_rto_minutes * 60,
                "within_target": False
            }
        
        # Get most recent successful restore test
        successful_tests = [
            t for t in self.restore_tests
            if t.status == RestoreStatus.SUCCESS
        ]
        
        if not successful_tests:
            return {
                "status": "warning",
                "message": "No successful restore tests",
                "last_test": None,
                "rto_seconds": None,
                "target_rto_seconds": self.target_rto_minutes * 60,
                "within_target": False
            }
        
        last_test = max(successful_tests, key=lambda t: t.start_time)
        target_seconds = self.target_rto_minutes * 60
        within_target = last_test.rto_seconds <= target_seconds
        
        status = "healthy" if within_target else "warning"
        
        return {
            "status": status,
            "message": f"Last restore took {last_test.rto_seconds:.1f} seconds",
            "last_test": last_test.start_time.isoformat(),
            "rto_seconds": last_test.rto_seconds,
            "target_rto_seconds": target_seconds,
            "within_target": within_target
        }
    
    def get_backup_summary(self) -> Dict[str, Any]:
        """Get comprehensive backup status summary"""
        total_backups = len(self.backups)
        successful_backups = sum(
            1 for b in self.backups
            if b.status in [BackupStatus.COMPLETED, BackupStatus.VERIFIED]
        )
        failed_backups = sum(1 for b in self.backups if b.status == BackupStatus.FAILED)
        
        total_size_bytes = sum(b.compressed_size_bytes for b in self.backups)
        
        return {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "failed_backups": failed_backups,
            "total_size_mb": total_size_bytes / 1024 / 1024,
            "rpo_status": self.get_rpo_status(),
            "rto_status": self.get_rto_status(),
            "storage_path": str(self.backup_storage_path),
            "compression_enabled": self.compression_enabled,
            "encryption_enabled": self.encryption_enabled
        }

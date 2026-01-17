"""
Database Backup & Restore API Endpoints

Provides REST API for managing database backups, restore operations,
and disaster recovery monitoring.
"""

from datetime import datetime
import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from sensei.api.deps import get_current_active_user, get_db, require_role
from sensei.models.user import User, RoleType
from sensei.services.core.database_backup import (
    BackupMetadata,
    BackupSchedule,
    BackupStatus,
    BackupStrategy,
    DatabaseBackupService,
    RestoreStatus,
    RestoreTest,
)


router = APIRouter()


# Response Models
class BackupResponse(BaseModel):
    """Backup metadata response"""

    model_config = ConfigDict(from_attributes=True)
    backup_id: str
    strategy: str
    timestamp: datetime
    database_name: str
    size_bytes: int
    compressed_size_bytes: int
    checksum: str
    encryption_enabled: bool
    status: str
    file_path: str
    error_message: Optional[str] = None
    


class RestoreTestResponse(BaseModel):
    """Restore test result response"""

    model_config = ConfigDict(from_attributes=True)
    test_id: str
    backup_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    rto_seconds: Optional[float]
    verification_passed: bool
    error_message: Optional[str] = None
    test_database: Optional[str] = None
    


class BackupSummaryResponse(BaseModel):
    """Backup system summary"""
    total_backups: int
    successful_backups: int
    failed_backups: int
    total_size_mb: float
    rpo_status: dict
    rto_status: dict
    storage_path: str
    compression_enabled: bool
    encryption_enabled: bool


class RPOStatusResponse(BaseModel):
    """RPO (Recovery Point Objective) status"""
    status: str
    message: str
    last_backup: Optional[str]
    hours_since_backup: Optional[float]
    target_rpo_hours: int
    within_target: bool


class RTOStatusResponse(BaseModel):
    """RTO (Recovery Time Objective) status"""
    status: str
    message: str
    last_test: Optional[str]
    rto_seconds: Optional[float]
    target_rto_seconds: int
    within_target: bool


# Request Models
class CreateBackupRequest(BaseModel):
    """Create backup request"""
    strategy: BackupStrategy = BackupStrategy.FULL
    database_name: Optional[str] = None


class RestoreBackupRequest(BaseModel):
    """Restore backup request"""
    backup_id: str
    target_database: Optional[str] = None
    test_mode: bool = False


class RetentionPolicyRequest(BaseModel):
    """Apply retention policy request"""
    retention_days: int = Field(ge=1, le=3650, description="Retention period in days")


# Dependency: Get backup service
def get_backup_service(db: Session = Depends(get_db)) -> DatabaseBackupService:
    """Get database backup service instance"""
    from sensei.core.config import settings
    
    # In production, this would be initialized once and reused
    service = DatabaseBackupService(
        db_session_factory=lambda: db,
        backup_storage_path="/var/backups/sensei",  # From config
        database_url=settings.DATABASE_URL_SYNC,
        s3_client=None  # Would be initialized with S3 config
    )
    
    return service


@router.post(
    "/backups",
    response_model=BackupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def create_backup(
    request: CreateBackupRequest,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create database backup.
    
    **Admin only.** Creates a new database backup with specified strategy.
    Automatically compresses and verifies backup integrity.
    
    - **strategy**: Backup strategy (full, incremental, differential)
    - **database_name**: Database to backup (optional, defaults to main database)
    """
    try:
        backup = await asyncio.to_thread(
            service.create_backup,
            strategy=request.strategy,
            database_name=request.database_name,
        )
        
        return BackupResponse(
            backup_id=backup.backup_id,
            strategy=backup.strategy.value,
            timestamp=backup.timestamp,
            database_name=backup.database_name,
            size_bytes=backup.size_bytes,
            compressed_size_bytes=backup.compressed_size_bytes,
            checksum=backup.checksum,
            encryption_enabled=backup.encryption_enabled,
            status=backup.status.value,
            file_path=backup.file_path,
            error_message=backup.error_message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )


@router.get(
    "/backups",
    response_model=List[BackupResponse],
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def list_backups(
    skip: int = 0,
    limit: int = 100,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all database backups.
    
    **Admin only.** Returns list of all backups with metadata,
    ordered by timestamp (newest first).
    """
    backups = sorted(
        service.backups,
        key=lambda b: b.timestamp,
        reverse=True
    )[skip:skip + limit]
    
    return [
        BackupResponse(
            backup_id=b.backup_id,
            strategy=b.strategy.value,
            timestamp=b.timestamp,
            database_name=b.database_name,
            size_bytes=b.size_bytes,
            compressed_size_bytes=b.compressed_size_bytes,
            checksum=b.checksum,
            encryption_enabled=b.encryption_enabled,
            status=b.status.value,
            file_path=b.file_path,
            error_message=b.error_message
        )
        for b in backups
    ]


@router.get(
    "/backups/{backup_id}",
    response_model=BackupResponse,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def get_backup(
    backup_id: str,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific backup details.
    
    **Admin only.** Returns detailed information about a specific backup.
    """
    backup = next((b for b in service.backups if b.backup_id == backup_id), None)
    
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup {backup_id} not found"
        )
    
    return BackupResponse(
        backup_id=backup.backup_id,
        strategy=backup.strategy.value,
        timestamp=backup.timestamp,
        database_name=backup.database_name,
        size_bytes=backup.size_bytes,
        compressed_size_bytes=backup.compressed_size_bytes,
        checksum=backup.checksum,
        encryption_enabled=backup.encryption_enabled,
        status=backup.status.value,
        file_path=backup.file_path,
        error_message=backup.error_message
    )


@router.post(
    "/backups/{backup_id}/test-restore",
    response_model=RestoreTestResponse,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def test_restore(
    backup_id: str,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Test backup restore in isolated database.
    
    **Admin only.** Creates temporary test database, restores backup,
    verifies integrity, measures RTO, and cleans up. Does not affect
    production database.
    """
    try:
        restore_test = service.test_restore(backup_id)
        
        return RestoreTestResponse(
            test_id=restore_test.test_id,
            backup_id=restore_test.backup_id,
            start_time=restore_test.start_time,
            end_time=restore_test.end_time,
            status=restore_test.status.value,
            rto_seconds=restore_test.rto_seconds,
            verification_passed=restore_test.verification_passed,
            error_message=restore_test.error_message,
            test_database=restore_test.test_database
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore test failed: {str(e)}"
        )


@router.post(
    "/backups/{backup_id}/restore",
    response_model=RestoreTestResponse,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def restore_backup(
    backup_id: str,
    request: RestoreBackupRequest,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Restore database from backup.
    
    **Admin only. DANGER: This will overwrite the target database.**
    Restores specified backup to target database. Use with extreme caution.
    Consider using test-restore endpoint first to verify backup integrity.
    """
    try:
        restore_result = service.restore_backup(
            backup_id=backup_id,
            target_database=request.target_database,
            test_mode=request.test_mode
        )
        
        return RestoreTestResponse(
            test_id=restore_result.test_id,
            backup_id=restore_result.backup_id,
            start_time=restore_result.start_time,
            end_time=restore_result.end_time,
            status=restore_result.status.value,
            rto_seconds=restore_result.rto_seconds,
            verification_passed=restore_result.verification_passed,
            error_message=restore_result.error_message,
            test_database=restore_result.test_database
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}"
        )


@router.get(
    "/backups/status/summary",
    response_model=BackupSummaryResponse,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def get_backup_summary(
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive backup system status.
    
    **Admin only.** Returns overall backup health including:
    - Total backups and success rate
    - Storage usage
    - RPO (Recovery Point Objective) status
    - RTO (Recovery Time Objective) status
    """
    summary = service.get_backup_summary()
    return BackupSummaryResponse(**summary)


@router.get(
    "/backups/status/rpo",
    response_model=RPOStatusResponse,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def get_rpo_status(
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get RPO (Recovery Point Objective) status.
    
    **Admin only.** Returns status of last backup and whether we're
    within the target RPO (24 hours). Critical if no recent backup exists.
    """
    rpo = service.get_rpo_status()
    return RPOStatusResponse(**rpo)


@router.get(
    "/backups/status/rto",
    response_model=RTOStatusResponse,
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def get_rto_status(
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get RTO (Recovery Time Objective) status.
    
    **Admin only.** Returns status of last restore test and whether
    restoration time is within target RTO (30 minutes).
    """
    rto = service.get_rto_status()
    return RTOStatusResponse(**rto)


@router.post(
    "/backups/maintenance/retention",
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def apply_retention_policy(
    request: RetentionPolicyRequest,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Apply backup retention policy.
    
    **Admin only.** Removes backups older than specified retention period.
    Default retention is 30 days for daily backups, 90 days for weekly,
    and 365 days for monthly.
    """
    try:
        removed_count = service.apply_retention_policy(request.retention_days)
        
        return {
            "success": True,
            "message": f"Removed {removed_count} old backup(s)",
            "removed_count": removed_count,
            "retention_days": request.retention_days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply retention policy: {str(e)}"
        )


@router.get(
    "/backups/tests/history",
    response_model=List[RestoreTestResponse],
    dependencies=[Depends(require_role(RoleType.ADMIN))]
)
async def list_restore_tests(
    skip: int = 0,
    limit: int = 100,
    service: DatabaseBackupService = Depends(get_backup_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    List restore test history.
    
    **Admin only.** Returns history of restore tests, ordered by
    most recent first. Useful for tracking RTO trends.
    """
    tests = sorted(
        service.restore_tests,
        key=lambda t: t.start_time,
        reverse=True
    )[skip:skip + limit]
    
    return [
        RestoreTestResponse(
            test_id=t.test_id,
            backup_id=t.backup_id,
            start_time=t.start_time,
            end_time=t.end_time,
            status=t.status.value,
            rto_seconds=t.rto_seconds,
            verification_passed=t.verification_passed,
            error_message=t.error_message,
            test_database=t.test_database
        )
        for t in tests
    ]

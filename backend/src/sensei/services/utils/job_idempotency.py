"""
Job Idempotency Service.

Ensures background jobs are idempotent and retry-safe. Provides:
- Idempotency key management for job deduplication
- Job state tracking to prevent duplicate execution
- Retry-safe job execution with status tracking
- Lock management for concurrent job execution
- Result caching for completed jobs
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Any, Generic, TypeVar, Callable, Awaitable, Dict, List
from uuid import UUID, uuid4
import hashlib
import json
import asyncio


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Type variable for job results
T = TypeVar("T")


class JobStatus(str, Enum):
    """Status of a job execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class JobType(str, Enum):
    """Types of background jobs."""
    
    PDF_GENERATION = "pdf_generation"
    EMAIL_DRAFT = "email_draft"
    EMAIL_SEND = "email_send"
    STALE_DETECTION = "stale_detection"
    NOTIFICATION = "notification"
    REPORT_GENERATION = "report_generation"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    SYNC = "sync"
    CLEANUP = "cleanup"
    SCHEDULED_TASK = "scheduled_task"
    WEBHOOK = "webhook"
    AUDIT_LOG = "audit_log"


class LockStatus(str, Enum):
    """Status of a job lock."""
    
    ACQUIRED = "acquired"
    LOCKED_BY_OTHER = "locked_by_other"
    RELEASED = "released"
    EXPIRED = "expired"


class RetryStrategy(str, Enum):
    """Retry strategies for failed jobs."""
    
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class IdempotencyKey:
    """Represents an idempotency key for a job."""
    
    key: str
    job_type: JobType
    created_at: datetime = field(default_factory=_utcnow)
    expires_at: Optional[datetime] = None
    payload_hash: Optional[str] = None
    
    @classmethod
    def generate(
        cls,
        job_type: JobType,
        *args: Any,
        ttl_hours: int = 24,
        **kwargs: Any
    ) -> "IdempotencyKey":
        """Generate an idempotency key from job parameters."""
        # Create deterministic hash from job type and parameters
        payload = {
            "job_type": job_type.value,
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
        }
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        key = f"idempotency:{job_type.value}:{payload_hash[:16]}"
        
        return cls(
            key=key,
            job_type=job_type,
            created_at=_utcnow(),
            expires_at=_utcnow() + timedelta(hours=ttl_hours),
            payload_hash=payload_hash
        )
    
    @classmethod
    def from_explicit_key(
        cls,
        explicit_key: str,
        job_type: JobType,
        ttl_hours: int = 24
    ) -> "IdempotencyKey":
        """Create idempotency key from an explicit key value."""
        key = f"idempotency:{job_type.value}:{explicit_key}"
        return cls(
            key=key,
            job_type=job_type,
            created_at=_utcnow(),
            expires_at=_utcnow() + timedelta(hours=ttl_hours),
            payload_hash=hashlib.sha256(explicit_key.encode()).hexdigest()
        )
    
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return _utcnow() > self.expires_at


@dataclass
class JobLock:
    """Represents a lock on a job for concurrent execution control."""
    
    lock_id: str
    job_key: str
    owner_id: str
    acquired_at: datetime = field(default_factory=_utcnow)
    expires_at: Optional[datetime] = None
    status: LockStatus = LockStatus.ACQUIRED
    
    @classmethod
    def create(
        cls,
        job_key: str,
        owner_id: Optional[str] = None,
        ttl_seconds: int = 300
    ) -> "JobLock":
        """Create a new job lock."""
        return cls(
            lock_id=str(uuid4()),
            job_key=job_key,
            owner_id=owner_id or str(uuid4()),
            acquired_at=_utcnow(),
            expires_at=_utcnow() + timedelta(seconds=ttl_seconds),
            status=LockStatus.ACQUIRED
        )
    
    def is_expired(self) -> bool:
        """Check if the lock has expired."""
        if self.expires_at is None:
            return False
        return _utcnow() > self.expires_at
    
    def is_owned_by(self, owner_id: str) -> bool:
        """Check if the lock is owned by the given owner."""
        return self.owner_id == owner_id


@dataclass
class RetryConfig:
    """Configuration for job retry behavior."""
    
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    initial_delay_seconds: int = 5
    max_delay_seconds: int = 300
    backoff_multiplier: float = 2.0
    retry_on_errors: Optional[List[str]] = None
    
    def get_delay_for_attempt(self, attempt: int) -> int:
        """Calculate delay for a given retry attempt."""
        if self.strategy == RetryStrategy.NONE:
            return 0
        
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0
        
        if self.strategy == RetryStrategy.FIXED_DELAY:
            return self.initial_delay_seconds
        
        if self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.initial_delay_seconds * attempt
            return min(delay, self.max_delay_seconds)
        
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = int(self.initial_delay_seconds * (self.backoff_multiplier ** (attempt - 1)))
            return min(delay, self.max_delay_seconds)
        
        return self.initial_delay_seconds
    
    def should_retry(self, attempt: int, error: Optional[Exception] = None) -> bool:
        """Determine if a job should be retried."""
        if self.strategy == RetryStrategy.NONE:
            return False
        
        if attempt >= self.max_retries:
            return False
        
        if error and self.retry_on_errors:
            error_type = type(error).__name__
            return error_type in self.retry_on_errors
        
        return True


@dataclass
class JobRecord:
    """Record of a job execution."""
    
    id: UUID = field(default_factory=uuid4)
    idempotency_key: str = ""
    job_type: JobType = JobType.SCHEDULED_TASK
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    result_hash: Optional[str] = None
    result_cached: bool = False
    result_expires_at: Optional[datetime] = None
    payload_hash: Optional[str] = None
    owner_id: Optional[str] = None
    lock_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def mark_started(self, owner_id: Optional[str] = None) -> None:
        """Mark the job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = _utcnow()
        self.attempt_count += 1
        if owner_id:
            self.owner_id = owner_id
    
    def mark_completed(self, result_hash: Optional[str] = None) -> None:
        """Mark the job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = _utcnow()
        if result_hash:
            self.result_hash = result_hash
            self.result_cached = True
    
    def mark_failed(self, error: str) -> None:
        """Mark the job as failed."""
        self.status = JobStatus.FAILED
        self.last_error = error
        self.last_error_at = _utcnow()
    
    def mark_retrying(self, error: str) -> None:
        """Mark the job for retry."""
        self.status = JobStatus.RETRYING
        self.last_error = error
        self.last_error_at = _utcnow()
    
    def mark_cancelled(self) -> None:
        """Mark the job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = _utcnow()
    
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or _utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.EXPIRED
        )
    
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status in (JobStatus.FAILED, JobStatus.RETRYING)
            and self.attempt_count < self.max_attempts
        )


@dataclass
class JobResult(Generic[T]):
    """Result of a job execution."""
    
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    cached: bool = False
    execution_time_ms: Optional[float] = None
    attempt_number: int = 1
    
    @classmethod
    def success_result(
        cls,
        value: T,
        execution_time_ms: Optional[float] = None,
        cached: bool = False,
        attempt_number: int = 1
    ) -> "JobResult[T]":
        """Create a successful result."""
        return cls(
            success=True,
            value=value,
            cached=cached,
            execution_time_ms=execution_time_ms,
            attempt_number=attempt_number
        )
    
    @classmethod
    def failure_result(
        cls,
        error: str,
        error_type: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        attempt_number: int = 1
    ) -> "JobResult[T]":
        """Create a failed result."""
        return cls(
            success=False,
            error=error,
            error_type=error_type,
            execution_time_ms=execution_time_ms,
            attempt_number=attempt_number
        )


@dataclass
class JobExecutionStats:
    """Statistics for job executions."""
    
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    retrying_jobs: int = 0
    cancelled_jobs: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_retry_attempts: int = 0
    average_duration_ms: Optional[float] = None
    
    def add_job_completion(self, duration_ms: float, cached: bool = False) -> None:
        """Update stats with a completed job."""
        self.completed_jobs += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Update average duration
        if self.average_duration_ms is None:
            self.average_duration_ms = duration_ms
        else:
            total = self.average_duration_ms * (self.completed_jobs - 1)
            self.average_duration_ms = (total + duration_ms) / self.completed_jobs


class JobIdempotencyService:
    """
    Service for ensuring job idempotency and retry safety.
    
    Provides mechanisms to:
    - Generate and validate idempotency keys
    - Track job execution state
    - Manage locks for concurrent execution
    - Cache job results
    - Handle retries with configurable strategies
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._jobs: Dict[str, JobRecord] = {}
        self._locks: Dict[str, JobLock] = {}
        self._results: Dict[str, Any] = {}
        self._stats: Dict[JobType, JobExecutionStats] = {}
        self._default_retry_config = RetryConfig()
    
    # Key Management
    
    def generate_idempotency_key(
        self,
        job_type: JobType,
        *args: Any,
        ttl_hours: int = 24,
        **kwargs: Any
    ) -> IdempotencyKey:
        """Generate an idempotency key for a job."""
        return IdempotencyKey.generate(
            job_type,
            *args,
            ttl_hours=ttl_hours,
            **kwargs
        )
    
    def generate_key_from_explicit(
        self,
        explicit_key: str,
        job_type: JobType,
        ttl_hours: int = 24
    ) -> IdempotencyKey:
        """Generate an idempotency key from an explicit key value."""
        return IdempotencyKey.from_explicit_key(
            explicit_key,
            job_type,
            ttl_hours=ttl_hours
        )
    
    def validate_key(self, key: IdempotencyKey) -> bool:
        """Validate an idempotency key."""
        if not key.key:
            return False
        if key.is_expired():
            return False
        return True
    
    # Job Registration and Tracking
    
    def register_job(
        self,
        idempotency_key: IdempotencyKey,
        max_attempts: int = 3,
        owner_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> JobRecord:
        """Register a new job or return existing job for the key."""
        key = idempotency_key.key
        
        # Check if job already exists
        if key in self._jobs:
            existing = self._jobs[key]
            if existing.is_terminal():
                # Job completed, return cached record
                return existing
            # Job in progress
            return existing
        
        # Create new job record
        job = JobRecord(
            idempotency_key=key,
            job_type=idempotency_key.job_type,
            payload_hash=idempotency_key.payload_hash,
            max_attempts=max_attempts,
            owner_id=owner_id,
            metadata=metadata or {}
        )
        
        self._jobs[key] = job
        self._update_stats(idempotency_key.job_type, pending_increment=1)
        
        return job
    
    def get_job(self, idempotency_key: str) -> Optional[JobRecord]:
        """Get a job record by idempotency key."""
        return self._jobs.get(idempotency_key)
    
    def get_job_by_id(self, job_id: UUID) -> Optional[JobRecord]:
        """Get a job record by job ID."""
        for job in self._jobs.values():
            if job.id == job_id:
                return job
        return None
    
    def list_jobs(
        self,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[JobRecord]:
        """List jobs with optional filtering."""
        jobs = list(self._jobs.values())
        
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    def update_job_status(
        self,
        idempotency_key: str,
        status: JobStatus,
        error: Optional[str] = None,
        result_hash: Optional[str] = None
    ) -> Optional[JobRecord]:
        """Update job status."""
        job = self._jobs.get(idempotency_key)
        if not job:
            return None
        
        old_status = job.status
        
        if status == JobStatus.RUNNING:
            job.mark_started()
            self._update_stats(job.job_type, pending_increment=-1, running_increment=1)
        elif status == JobStatus.COMPLETED:
            job.mark_completed(result_hash)
            self._update_stats(job.job_type, running_increment=-1, completed_increment=1)
        elif status == JobStatus.FAILED:
            job.mark_failed(error or "Unknown error")
            self._update_stats(job.job_type, running_increment=-1, failed_increment=1)
        elif status == JobStatus.RETRYING:
            job.mark_retrying(error or "Unknown error")
            self._update_stats(job.job_type, retrying_increment=1)
        elif status == JobStatus.CANCELLED:
            job.mark_cancelled()
            if old_status == JobStatus.RUNNING:
                self._update_stats(job.job_type, running_increment=-1, cancelled_increment=1)
            else:
                self._update_stats(job.job_type, cancelled_increment=1)
        
        return job
    
    # Lock Management
    
    def acquire_lock(
        self,
        job_key: str,
        owner_id: Optional[str] = None,
        ttl_seconds: int = 300
    ) -> Optional[JobLock]:
        """Acquire a lock for a job."""
        # Check if lock exists and is not expired
        existing_lock = self._locks.get(job_key)
        if existing_lock and not existing_lock.is_expired():
            # Lock held by someone else
            return None
        
        # Create new lock
        lock = JobLock.create(job_key, owner_id, ttl_seconds)
        self._locks[job_key] = lock
        
        return lock
    
    def release_lock(
        self,
        job_key: str,
        owner_id: str
    ) -> bool:
        """Release a lock for a job."""
        lock = self._locks.get(job_key)
        if not lock:
            return True  # No lock to release
        
        if not lock.is_owned_by(owner_id):
            return False  # Can't release someone else's lock
        
        lock.status = LockStatus.RELEASED
        del self._locks[job_key]
        
        return True
    
    def check_lock(self, job_key: str) -> Optional[JobLock]:
        """Check the status of a lock."""
        lock = self._locks.get(job_key)
        if lock and lock.is_expired():
            lock.status = LockStatus.EXPIRED
            del self._locks[job_key]
            return None
        return lock
    
    def extend_lock(
        self,
        job_key: str,
        owner_id: str,
        additional_seconds: int = 300
    ) -> bool:
        """Extend a lock's expiration time."""
        lock = self._locks.get(job_key)
        if not lock:
            return False
        
        if not lock.is_owned_by(owner_id):
            return False
        
        if lock.expires_at:
            lock.expires_at = _utcnow() + timedelta(seconds=additional_seconds)
        
        return True
    
    # Result Caching
    
    def cache_result(
        self,
        idempotency_key: str,
        result: Any,
        ttl_hours: int = 24
    ) -> str:
        """Cache a job result."""
        # Generate result hash
        result_str = json.dumps(result, default=str, sort_keys=True)
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]
        
        cache_key = f"result:{idempotency_key}"
        self._results[cache_key] = {
            "result": result,
            "result_hash": result_hash,
            "cached_at": _utcnow(),
            "expires_at": _utcnow() + timedelta(hours=ttl_hours)
        }
        
        # Update job record
        job = self._jobs.get(idempotency_key)
        if job:
            job.result_hash = result_hash
            job.result_cached = True
            job.result_expires_at = _utcnow() + timedelta(hours=ttl_hours)
        
        return result_hash
    
    def get_cached_result(
        self,
        idempotency_key: str
    ) -> Optional[Any]:
        """Get a cached job result."""
        cache_key = f"result:{idempotency_key}"
        cached = self._results.get(cache_key)
        
        if not cached:
            return None
        
        # Check expiration
        if cached.get("expires_at") and _utcnow() > cached["expires_at"]:
            del self._results[cache_key]
            return None
        
        return cached.get("result")
    
    def invalidate_cache(self, idempotency_key: str) -> bool:
        """Invalidate cached result for a job."""
        cache_key = f"result:{idempotency_key}"
        if cache_key in self._results:
            del self._results[cache_key]
            
            # Update job record
            job = self._jobs.get(idempotency_key)
            if job:
                job.result_cached = False
                job.result_hash = None
            
            return True
        return False
    
    # Idempotent Job Execution
    
    async def execute_idempotent(
        self,
        idempotency_key: IdempotencyKey,
        job_func: Callable[[], Awaitable[T]],
        retry_config: Optional[RetryConfig] = None,
        lock_ttl_seconds: int = 300,
        cache_result: bool = True,
        cache_ttl_hours: int = 24
    ) -> JobResult[T]:
        """
        Execute a job with idempotency guarantees.
        
        If the job has already completed for this key, returns cached result.
        If the job is running, waits for completion.
        If the job hasn't run, executes it with lock protection.
        """
        key = idempotency_key.key
        retry_cfg = retry_config or self._default_retry_config
        owner_id = str(uuid4())
        
        # Check for existing job
        existing_job = self._jobs.get(key)
        if existing_job:
            if existing_job.status == JobStatus.COMPLETED:
                # Return cached result
                cached = self.get_cached_result(key)
                if cached is not None:
                    return JobResult.success_result(
                        cached,
                        cached=True,
                        attempt_number=existing_job.attempt_count
                    )
            
            if existing_job.status == JobStatus.RUNNING:
                # Wait for job to complete (with timeout)
                return await self._wait_for_job(key, timeout_seconds=300)
        
        # Register new job
        job = self.register_job(idempotency_key, retry_cfg.max_retries, owner_id)
        
        # Acquire lock
        lock = self.acquire_lock(key, owner_id, lock_ttl_seconds)
        if not lock:
            # Another process is executing this job
            return await self._wait_for_job(key, timeout_seconds=300)
        
        start_time = _utcnow()
        current_attempt = 0
        last_error: Optional[Exception] = None
        
        try:
            while current_attempt < retry_cfg.max_retries:
                current_attempt += 1
                job.mark_started(owner_id)
                
                try:
                    # Execute the job
                    result = await job_func()
                    
                    # Job succeeded
                    execution_time = (_utcnow() - start_time).total_seconds() * 1000
                    job.mark_completed()
                    
                    if cache_result:
                        self.cache_result(key, result, cache_ttl_hours)
                    
                    self._record_completion(job.job_type, execution_time, cached=False)
                    
                    return JobResult.success_result(
                        result,
                        execution_time_ms=execution_time,
                        attempt_number=current_attempt
                    )
                    
                except Exception as e:
                    last_error = e
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    
                    if retry_cfg.should_retry(current_attempt, e):
                        job.mark_retrying(error_msg)
                        delay = retry_cfg.get_delay_for_attempt(current_attempt)
                        
                        # Extend lock for retry
                        self.extend_lock(key, owner_id, delay + lock_ttl_seconds)
                        
                        if delay > 0:
                            await asyncio.sleep(delay)
                    else:
                        # Final failure
                        execution_time = (_utcnow() - start_time).total_seconds() * 1000
                        job.mark_failed(error_msg)
                        
                        return JobResult.failure_result(
                            error_msg,
                            error_type=type(e).__name__,
                            execution_time_ms=execution_time,
                            attempt_number=current_attempt
                        )
            
            # Max retries exceeded
            execution_time = (_utcnow() - start_time).total_seconds() * 1000
            error_msg = f"Max retries ({retry_cfg.max_retries}) exceeded"
            if last_error:
                error_msg += f": {type(last_error).__name__}: {str(last_error)}"
            job.mark_failed(error_msg)
            
            return JobResult.failure_result(
                error_msg,
                execution_time_ms=execution_time,
                attempt_number=current_attempt
            )
            
        finally:
            # Release lock
            self.release_lock(key, owner_id)
    
    async def _wait_for_job(
        self,
        idempotency_key: str,
        timeout_seconds: int = 300,
        poll_interval: float = 0.5
    ) -> JobResult[Any]:
        """Wait for a job to complete."""
        start_time = _utcnow()
        
        while (_utcnow() - start_time).total_seconds() < timeout_seconds:
            job = self._jobs.get(idempotency_key)
            
            if not job:
                return JobResult.failure_result("Job not found")
            
            if job.status == JobStatus.COMPLETED:
                cached = self.get_cached_result(idempotency_key)
                return JobResult.success_result(
                    cached,
                    cached=True,
                    attempt_number=job.attempt_count
                )
            
            if job.is_terminal():
                return JobResult.failure_result(
                    job.last_error or "Job failed",
                    attempt_number=job.attempt_count
                )
            
            await asyncio.sleep(poll_interval)
        
        return JobResult.failure_result(
            f"Timeout waiting for job after {timeout_seconds}s"
        )
    
    # Retry Management
    
    def schedule_retry(
        self,
        idempotency_key: str,
        delay_seconds: int = 0
    ) -> Optional[JobRecord]:
        """Schedule a job for retry."""
        job = self._jobs.get(idempotency_key)
        if not job:
            return None
        
        if not job.can_retry():
            return None
        
        job.status = JobStatus.PENDING
        self._update_stats(job.job_type, retrying_increment=-1, pending_increment=1)
        
        return job
    
    def get_retry_config(self, job_type: JobType) -> RetryConfig:
        """Get retry configuration for a job type."""
        # Type-specific defaults
        configs: Dict[JobType, RetryConfig] = {
            JobType.PDF_GENERATION: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=3,
                initial_delay_seconds=10
            ),
            JobType.EMAIL_SEND: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                initial_delay_seconds=30
            ),
            JobType.WEBHOOK: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                initial_delay_seconds=5,
                max_delay_seconds=3600
            ),
            JobType.DATA_EXPORT: RetryConfig(
                strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=3,
                initial_delay_seconds=60
            ),
        }
        
        return configs.get(job_type, self._default_retry_config)
    
    # Statistics
    
    def get_stats(self, job_type: Optional[JobType] = None) -> JobExecutionStats:
        """Get execution statistics."""
        if job_type:
            return self._stats.get(job_type, JobExecutionStats())
        
        # Aggregate all stats
        total = JobExecutionStats()
        for stats in self._stats.values():
            total.total_jobs += stats.total_jobs
            total.pending_jobs += stats.pending_jobs
            total.running_jobs += stats.running_jobs
            total.completed_jobs += stats.completed_jobs
            total.failed_jobs += stats.failed_jobs
            total.retrying_jobs += stats.retrying_jobs
            total.cancelled_jobs += stats.cancelled_jobs
            total.cache_hits += stats.cache_hits
            total.cache_misses += stats.cache_misses
            total.total_retry_attempts += stats.total_retry_attempts
        
        return total
    
    def _update_stats(
        self,
        job_type: JobType,
        pending_increment: int = 0,
        running_increment: int = 0,
        completed_increment: int = 0,
        failed_increment: int = 0,
        retrying_increment: int = 0,
        cancelled_increment: int = 0
    ) -> None:
        """Update statistics for a job type."""
        if job_type not in self._stats:
            self._stats[job_type] = JobExecutionStats()
        
        stats = self._stats[job_type]
        
        if pending_increment > 0:
            stats.total_jobs += pending_increment
        stats.pending_jobs += pending_increment
        stats.running_jobs += running_increment
        stats.completed_jobs += completed_increment
        stats.failed_jobs += failed_increment
        stats.retrying_jobs += retrying_increment
        stats.cancelled_jobs += cancelled_increment
        
        if retrying_increment > 0:
            stats.total_retry_attempts += retrying_increment
    
    def _record_completion(
        self,
        job_type: JobType,
        duration_ms: float,
        cached: bool
    ) -> None:
        """Record job completion for stats."""
        if job_type not in self._stats:
            self._stats[job_type] = JobExecutionStats()
        
        self._stats[job_type].add_job_completion(duration_ms, cached)
    
    # Cleanup
    
    def cleanup_expired(self) -> int:
        """Clean up expired jobs and locks."""
        cleaned = 0
        now = _utcnow()
        
        # Clean expired jobs
        expired_jobs = [
            key for key, job in self._jobs.items()
            if job.result_expires_at and now > job.result_expires_at
            and job.is_terminal()
        ]
        for key in expired_jobs:
            del self._jobs[key]
            cleaned += 1
        
        # Clean expired locks
        expired_locks = [
            key for key, lock in self._locks.items()
            if lock.is_expired()
        ]
        for key in expired_locks:
            del self._locks[key]
            cleaned += 1
        
        # Clean expired results
        expired_results = [
            key for key, cached in self._results.items()
            if cached.get("expires_at") and now > cached["expires_at"]
        ]
        for key in expired_results:
            del self._results[key]
            cleaned += 1
        
        return cleaned
    
    def clear_all(self) -> None:
        """Clear all job records, locks, and cached results."""
        self._jobs.clear()
        self._locks.clear()
        self._results.clear()
        self._stats.clear()


# Convenience functions for common job types

def create_pdf_idempotency_key(
    document_type: str,
    entity_id: UUID,
    version: Optional[int] = None
) -> IdempotencyKey:
    """Create idempotency key for PDF generation."""
    return IdempotencyKey.generate(
        JobType.PDF_GENERATION,
        document_type,
        str(entity_id),
        version=version,
        ttl_hours=24
    )


def create_email_idempotency_key(
    recipient: str,
    subject: str,
    template_id: Optional[str] = None
) -> IdempotencyKey:
    """Create idempotency key for email drafts."""
    return IdempotencyKey.generate(
        JobType.EMAIL_DRAFT,
        recipient,
        subject,
        template_id=template_id or "default",
        ttl_hours=1
    )


def create_notification_idempotency_key(
    recipient_id: UUID,
    notification_type: str,
    entity_id: UUID
) -> IdempotencyKey:
    """Create idempotency key for notifications."""
    return IdempotencyKey.generate(
        JobType.NOTIFICATION,
        str(recipient_id),
        notification_type,
        str(entity_id),
        ttl_hours=1
    )


def create_stale_detection_idempotency_key(
    entity_type: str,
    run_date: Optional[str] = None
) -> IdempotencyKey:
    """Create idempotency key for stale detection jobs."""
    date_str = run_date or _utcnow().strftime("%Y-%m-%d")
    return IdempotencyKey.generate(
        JobType.STALE_DETECTION,
        entity_type,
        date_str,
        ttl_hours=24
    )

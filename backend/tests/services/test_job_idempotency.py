"""
Tests for Job Idempotency Service.

Comprehensive tests covering:
- Idempotency key generation and validation
- Job registration and tracking
- Lock management for concurrent execution
- Result caching
- Retry strategies and execution
- Statistics and cleanup
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sensei.services.utils.job_idempotency import (
    JobIdempotencyService,
    IdempotencyKey,
    JobLock,
    JobRecord,
    JobResult,
    JobExecutionStats,
    RetryConfig,
    JobStatus,
    JobType,
    LockStatus,
    RetryStrategy,
    create_pdf_idempotency_key,
    create_email_idempotency_key,
    create_notification_idempotency_key,
    create_stale_detection_idempotency_key,
)


# ============================================================================
# IdempotencyKey Tests
# ============================================================================

class TestIdempotencyKey:
    """Tests for IdempotencyKey dataclass."""
    
    def test_generate_key_basic(self):
        """Test basic key generation."""
        key = IdempotencyKey.generate(
            JobType.PDF_GENERATION,
            "quote",
            "123"
        )
        
        assert key.key.startswith("idempotency:pdf_generation:")
        assert key.job_type == JobType.PDF_GENERATION
        assert key.payload_hash is not None
        assert len(key.payload_hash) == 64  # SHA256 hex
        assert key.created_at is not None
        assert key.expires_at is not None
    
    def test_generate_key_with_kwargs(self):
        """Test key generation with keyword arguments."""
        key = IdempotencyKey.generate(
            JobType.EMAIL_DRAFT,
            "user@example.com",
            subject="Hello",
            template_id="template_1"
        )
        
        assert key.key.startswith("idempotency:email_draft:")
        assert key.job_type == JobType.EMAIL_DRAFT
    
    def test_generate_key_deterministic(self):
        """Test that same parameters generate same key."""
        key1 = IdempotencyKey.generate(
            JobType.PDF_GENERATION,
            "quote",
            "123"
        )
        key2 = IdempotencyKey.generate(
            JobType.PDF_GENERATION,
            "quote",
            "123"
        )
        
        assert key1.payload_hash == key2.payload_hash
        assert key1.key == key2.key
    
    def test_generate_key_different_params(self):
        """Test that different parameters generate different keys."""
        key1 = IdempotencyKey.generate(
            JobType.PDF_GENERATION,
            "quote",
            "123"
        )
        key2 = IdempotencyKey.generate(
            JobType.PDF_GENERATION,
            "quote",
            "456"
        )
        
        assert key1.payload_hash != key2.payload_hash
        assert key1.key != key2.key
    
    def test_generate_key_different_types(self):
        """Test that different job types generate different keys."""
        key1 = IdempotencyKey.generate(
            JobType.PDF_GENERATION,
            "data"
        )
        key2 = IdempotencyKey.generate(
            JobType.EMAIL_DRAFT,
            "data"
        )
        
        assert key1.key != key2.key
        assert key1.job_type != key2.job_type
    
    def test_generate_key_custom_ttl(self):
        """Test key generation with custom TTL."""
        key = IdempotencyKey.generate(
            JobType.NOTIFICATION,
            "test",
            ttl_hours=48
        )
        
        expected_expiry = _utcnow() + timedelta(hours=48)
        assert abs((key.expires_at - expected_expiry).total_seconds()) < 5
    
    def test_from_explicit_key(self):
        """Test creating key from explicit value."""
        key = IdempotencyKey.from_explicit_key(
            "my-explicit-key-123",
            JobType.WEBHOOK
        )
        
        assert "my-explicit-key-123" in key.key
        assert key.job_type == JobType.WEBHOOK
    
    def test_is_expired_false(self):
        """Test that fresh key is not expired."""
        key = IdempotencyKey.generate(
            JobType.STALE_DETECTION,
            "test"
        )
        
        assert key.is_expired() is False
    
    def test_is_expired_true(self):
        """Test that old key is expired."""
        key = IdempotencyKey.generate(
            JobType.STALE_DETECTION,
            "test",
            ttl_hours=0
        )
        key.expires_at = _utcnow() - timedelta(hours=1)
        
        assert key.is_expired() is True
    
    def test_is_expired_no_expiry(self):
        """Test key with no expiration."""
        key = IdempotencyKey.generate(JobType.CLEANUP, "test")
        key.expires_at = None
        
        assert key.is_expired() is False


# ============================================================================
# JobLock Tests
# ============================================================================

class TestJobLock:
    """Tests for JobLock dataclass."""
    
    def test_create_lock(self):
        """Test lock creation."""
        lock = JobLock.create(
            job_key="test-job-key",
            owner_id="owner-123"
        )
        
        assert lock.lock_id is not None
        assert lock.job_key == "test-job-key"
        assert lock.owner_id == "owner-123"
        assert lock.status == LockStatus.ACQUIRED
        assert lock.acquired_at is not None
        assert lock.expires_at is not None
    
    def test_create_lock_auto_owner(self):
        """Test lock creation with auto-generated owner."""
        lock = JobLock.create(job_key="test-key")
        
        assert lock.owner_id is not None
        assert len(lock.owner_id) == 36  # UUID format
    
    def test_create_lock_custom_ttl(self):
        """Test lock creation with custom TTL."""
        lock = JobLock.create(
            job_key="test-key",
            ttl_seconds=600
        )
        
        expected_expiry = _utcnow() + timedelta(seconds=600)
        assert abs((lock.expires_at - expected_expiry).total_seconds()) < 5
    
    def test_is_expired_false(self):
        """Test that fresh lock is not expired."""
        lock = JobLock.create(
            job_key="test-key",
            ttl_seconds=300
        )
        
        assert lock.is_expired() is False
    
    def test_is_expired_true(self):
        """Test that old lock is expired."""
        lock = JobLock.create(
            job_key="test-key",
            ttl_seconds=0
        )
        lock.expires_at = _utcnow() - timedelta(seconds=1)
        
        assert lock.is_expired() is True
    
    def test_is_owned_by_correct_owner(self):
        """Test ownership check with correct owner."""
        lock = JobLock.create(
            job_key="test-key",
            owner_id="owner-123"
        )
        
        assert lock.is_owned_by("owner-123") is True
    
    def test_is_owned_by_wrong_owner(self):
        """Test ownership check with wrong owner."""
        lock = JobLock.create(
            job_key="test-key",
            owner_id="owner-123"
        )
        
        assert lock.is_owned_by("owner-456") is False


# ============================================================================
# RetryConfig Tests
# ============================================================================

class TestRetryConfig:
    """Tests for RetryConfig dataclass."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.max_retries == 3
        assert config.initial_delay_seconds == 5
    
    def test_get_delay_none_strategy(self):
        """Test delay with no retry strategy."""
        config = RetryConfig(strategy=RetryStrategy.NONE)
        
        assert config.get_delay_for_attempt(1) == 0
        assert config.get_delay_for_attempt(5) == 0
    
    def test_get_delay_immediate_strategy(self):
        """Test delay with immediate retry strategy."""
        config = RetryConfig(strategy=RetryStrategy.IMMEDIATE)
        
        assert config.get_delay_for_attempt(1) == 0
        assert config.get_delay_for_attempt(3) == 0
    
    def test_get_delay_fixed_strategy(self):
        """Test delay with fixed delay strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.FIXED_DELAY,
            initial_delay_seconds=10
        )
        
        assert config.get_delay_for_attempt(1) == 10
        assert config.get_delay_for_attempt(5) == 10
    
    def test_get_delay_linear_backoff(self):
        """Test delay with linear backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_delay_seconds=5,
            max_delay_seconds=100
        )
        
        assert config.get_delay_for_attempt(1) == 5
        assert config.get_delay_for_attempt(2) == 10
        assert config.get_delay_for_attempt(3) == 15
        assert config.get_delay_for_attempt(30) == 100  # Capped at max
    
    def test_get_delay_exponential_backoff(self):
        """Test delay with exponential backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=5,
            backoff_multiplier=2.0,
            max_delay_seconds=100
        )
        
        assert config.get_delay_for_attempt(1) == 5
        assert config.get_delay_for_attempt(2) == 10
        assert config.get_delay_for_attempt(3) == 20
        assert config.get_delay_for_attempt(4) == 40
        assert config.get_delay_for_attempt(5) == 80
        assert config.get_delay_for_attempt(6) == 100  # Capped at max
    
    def test_should_retry_under_max(self):
        """Test should_retry when under max attempts."""
        config = RetryConfig(max_retries=3)
        
        assert config.should_retry(1) is True
        assert config.should_retry(2) is True
    
    def test_should_retry_at_max(self):
        """Test should_retry when at max attempts."""
        config = RetryConfig(max_retries=3)
        
        assert config.should_retry(3) is False
        assert config.should_retry(4) is False
    
    def test_should_retry_no_strategy(self):
        """Test should_retry with no retry strategy."""
        config = RetryConfig(strategy=RetryStrategy.NONE)
        
        assert config.should_retry(1) is False
    
    def test_should_retry_specific_errors(self):
        """Test should_retry with specific error types."""
        config = RetryConfig(
            max_retries=3,
            retry_on_errors=["TimeoutError", "ConnectionError"]
        )
        
        assert config.should_retry(1, TimeoutError()) is True
        assert config.should_retry(1, ValueError()) is False


# ============================================================================
# JobRecord Tests
# ============================================================================

class TestJobRecord:
    """Tests for JobRecord dataclass."""
    
    def test_create_job_record(self):
        """Test job record creation."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        
        assert job.id is not None
        assert job.status == JobStatus.PENDING
        assert job.attempt_count == 0
        assert job.created_at is not None
    
    def test_mark_started(self):
        """Test marking job as started."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        
        job.mark_started("owner-123")
        
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
        assert job.attempt_count == 1
        assert job.owner_id == "owner-123"
    
    def test_mark_completed(self):
        """Test marking job as completed."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_started()
        
        job.mark_completed("result-hash-123")
        
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result_hash == "result-hash-123"
        assert job.result_cached is True
    
    def test_mark_failed(self):
        """Test marking job as failed."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_started()
        
        job.mark_failed("Something went wrong")
        
        assert job.status == JobStatus.FAILED
        assert job.last_error == "Something went wrong"
        assert job.last_error_at is not None
    
    def test_mark_retrying(self):
        """Test marking job for retry."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_started()
        
        job.mark_retrying("Temporary failure")
        
        assert job.status == JobStatus.RETRYING
        assert job.last_error == "Temporary failure"
    
    def test_mark_cancelled(self):
        """Test marking job as cancelled."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        
        job.mark_cancelled()
        
        assert job.status == JobStatus.CANCELLED
        assert job.completed_at is not None
    
    def test_duration_seconds(self):
        """Test duration calculation."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_started()
        job.started_at = _utcnow() - timedelta(seconds=10)
        job.mark_completed()
        
        duration = job.duration_seconds()
        assert duration is not None
        assert 9 < duration < 11
    
    def test_duration_seconds_not_started(self):
        """Test duration when not started."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        
        assert job.duration_seconds() is None
    
    def test_is_terminal_completed(self):
        """Test is_terminal for completed job."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_completed()
        
        assert job.is_terminal() is True
    
    def test_is_terminal_failed(self):
        """Test is_terminal for failed job."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_failed("Error")
        
        assert job.is_terminal() is True
    
    def test_is_terminal_running(self):
        """Test is_terminal for running job."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_started()
        
        assert job.is_terminal() is False
    
    def test_can_retry_failed_under_max(self):
        """Test can_retry for failed job under max attempts."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION,
            max_attempts=3
        )
        job.mark_started()  # attempt 1
        job.mark_failed("Error")
        
        assert job.can_retry() is True
    
    def test_can_retry_at_max(self):
        """Test can_retry when at max attempts."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION,
            max_attempts=3
        )
        job.attempt_count = 3
        job.mark_failed("Error")
        
        assert job.can_retry() is False
    
    def test_can_retry_completed(self):
        """Test can_retry for completed job."""
        job = JobRecord(
            idempotency_key="test-key",
            job_type=JobType.PDF_GENERATION
        )
        job.mark_completed()
        
        assert job.can_retry() is False


# ============================================================================
# JobResult Tests
# ============================================================================

class TestJobResult:
    """Tests for JobResult dataclass."""
    
    def test_success_result(self):
        """Test creating success result."""
        result = JobResult.success_result(
            value={"data": "test"},
            execution_time_ms=150.5
        )
        
        assert result.success is True
        assert result.value == {"data": "test"}
        assert result.error is None
        assert result.execution_time_ms == 150.5
        assert result.cached is False
    
    def test_success_result_cached(self):
        """Test creating cached success result."""
        result = JobResult.success_result(
            value="cached-data",
            cached=True
        )
        
        assert result.success is True
        assert result.cached is True
    
    def test_failure_result(self):
        """Test creating failure result."""
        result = JobResult.failure_result(
            error="Something went wrong",
            error_type="ValueError"
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.error_type == "ValueError"
        assert result.value is None
    
    def test_result_with_attempt_number(self):
        """Test result with attempt number."""
        result = JobResult.success_result(
            value="data",
            attempt_number=3
        )
        
        assert result.attempt_number == 3


# ============================================================================
# JobExecutionStats Tests
# ============================================================================

class TestJobExecutionStats:
    """Tests for JobExecutionStats dataclass."""
    
    def test_default_stats(self):
        """Test default statistics."""
        stats = JobExecutionStats()
        
        assert stats.total_jobs == 0
        assert stats.completed_jobs == 0
        assert stats.cache_hits == 0
        assert stats.average_duration_ms is None
    
    def test_add_job_completion(self):
        """Test adding job completion."""
        stats = JobExecutionStats()
        
        stats.add_job_completion(100.0)
        
        assert stats.completed_jobs == 1
        assert stats.cache_misses == 1
        assert stats.average_duration_ms == 100.0
    
    def test_add_job_completion_cached(self):
        """Test adding cached job completion."""
        stats = JobExecutionStats()
        
        stats.add_job_completion(50.0, cached=True)
        
        assert stats.completed_jobs == 1
        assert stats.cache_hits == 1
        assert stats.cache_misses == 0
    
    def test_average_duration_multiple(self):
        """Test average duration with multiple completions."""
        stats = JobExecutionStats()
        
        stats.add_job_completion(100.0)
        stats.add_job_completion(200.0)
        stats.add_job_completion(300.0)
        
        assert stats.completed_jobs == 3
        assert stats.average_duration_ms == 200.0


# ============================================================================
# JobIdempotencyService Tests
# ============================================================================

class TestJobIdempotencyService:
    """Tests for JobIdempotencyService."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return JobIdempotencyService()
    
    # Key Management Tests
    
    def test_generate_idempotency_key(self, service):
        """Test generating idempotency key via service."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "quote",
            "123"
        )
        
        assert key is not None
        assert key.job_type == JobType.PDF_GENERATION
    
    def test_generate_key_from_explicit(self, service):
        """Test generating key from explicit value."""
        key = service.generate_key_from_explicit(
            "my-key-123",
            JobType.WEBHOOK
        )
        
        assert "my-key-123" in key.key
    
    def test_validate_key_valid(self, service):
        """Test validating a valid key."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "test"
        )
        
        assert service.validate_key(key) is True
    
    def test_validate_key_expired(self, service):
        """Test validating an expired key."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "test",
            ttl_hours=0
        )
        key.expires_at = _utcnow() - timedelta(hours=1)
        
        assert service.validate_key(key) is False
    
    def test_validate_key_empty(self, service):
        """Test validating an empty key."""
        key = IdempotencyKey(
            key="",
            job_type=JobType.PDF_GENERATION
        )
        
        assert service.validate_key(key) is False
    
    # Job Registration Tests
    
    def test_register_job_new(self, service):
        """Test registering a new job."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "doc-123"
        )
        
        job = service.register_job(key)
        
        assert job is not None
        assert job.idempotency_key == key.key
        assert job.status == JobStatus.PENDING
    
    def test_register_job_existing(self, service):
        """Test registering job with existing key returns same job."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "doc-123"
        )
        
        job1 = service.register_job(key)
        job2 = service.register_job(key)
        
        assert job1.id == job2.id
    
    def test_register_job_with_metadata(self, service):
        """Test registering job with metadata."""
        key = service.generate_idempotency_key(
            JobType.EMAIL_SEND,
            "email-123"
        )
        
        job = service.register_job(
            key,
            metadata={"recipient": "test@example.com"}
        )
        
        assert job.metadata["recipient"] == "test@example.com"
    
    def test_get_job(self, service):
        """Test getting a job by key."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "doc-123"
        )
        service.register_job(key)
        
        job = service.get_job(key.key)
        
        assert job is not None
        assert job.idempotency_key == key.key
    
    def test_get_job_not_found(self, service):
        """Test getting a non-existent job."""
        job = service.get_job("non-existent-key")
        
        assert job is None
    
    def test_get_job_by_id(self, service):
        """Test getting a job by ID."""
        key = service.generate_idempotency_key(
            JobType.PDF_GENERATION,
            "doc-123"
        )
        registered = service.register_job(key)
        
        job = service.get_job_by_id(registered.id)
        
        assert job is not None
        assert job.id == registered.id
    
    def test_list_jobs(self, service):
        """Test listing jobs."""
        # Register multiple jobs
        for i in range(5):
            key = service.generate_idempotency_key(
                JobType.PDF_GENERATION,
                f"doc-{i}"
            )
            service.register_job(key)
        
        jobs = service.list_jobs()
        
        assert len(jobs) == 5
    
    def test_list_jobs_by_type(self, service):
        """Test listing jobs by type."""
        key1 = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        key2 = service.generate_idempotency_key(JobType.EMAIL_SEND, "2")
        service.register_job(key1)
        service.register_job(key2)
        
        pdf_jobs = service.list_jobs(job_type=JobType.PDF_GENERATION)
        
        assert len(pdf_jobs) == 1
    
    def test_list_jobs_by_status(self, service):
        """Test listing jobs by status."""
        key1 = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        key2 = service.generate_idempotency_key(JobType.PDF_GENERATION, "2")
        
        job1 = service.register_job(key1)
        service.register_job(key2)
        
        job1.mark_completed()
        
        pending_jobs = service.list_jobs(status=JobStatus.PENDING)
        
        assert len(pending_jobs) == 1
    
    def test_update_job_status_running(self, service):
        """Test updating job status to running."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        
        job = service.update_job_status(key.key, JobStatus.RUNNING)
        
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
    
    def test_update_job_status_completed(self, service):
        """Test updating job status to completed."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        service.update_job_status(key.key, JobStatus.RUNNING)
        
        job = service.update_job_status(
            key.key,
            JobStatus.COMPLETED,
            result_hash="abc123"
        )
        
        assert job.status == JobStatus.COMPLETED
        assert job.result_hash == "abc123"
    
    def test_update_job_status_failed(self, service):
        """Test updating job status to failed."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        
        job = service.update_job_status(
            key.key,
            JobStatus.FAILED,
            error="Connection timeout"
        )
        
        assert job.status == JobStatus.FAILED
        assert job.last_error == "Connection timeout"
    
    # Lock Management Tests
    
    def test_acquire_lock(self, service):
        """Test acquiring a lock."""
        lock = service.acquire_lock("job-key-123", "owner-1")
        
        assert lock is not None
        assert lock.status == LockStatus.ACQUIRED
        assert lock.owner_id == "owner-1"
    
    def test_acquire_lock_already_held(self, service):
        """Test acquiring lock that's already held."""
        service.acquire_lock("job-key-123", "owner-1")
        
        lock2 = service.acquire_lock("job-key-123", "owner-2")
        
        assert lock2 is None
    
    def test_acquire_lock_after_expiry(self, service):
        """Test acquiring lock after previous expired."""
        lock1 = service.acquire_lock("job-key-123", "owner-1", ttl_seconds=0)
        lock1.expires_at = _utcnow() - timedelta(seconds=1)
        
        lock2 = service.acquire_lock("job-key-123", "owner-2")
        
        assert lock2 is not None
        assert lock2.owner_id == "owner-2"
    
    def test_release_lock(self, service):
        """Test releasing a lock."""
        service.acquire_lock("job-key-123", "owner-1")
        
        released = service.release_lock("job-key-123", "owner-1")
        
        assert released is True
        
        # Should be able to acquire again
        lock2 = service.acquire_lock("job-key-123", "owner-2")
        assert lock2 is not None
    
    def test_release_lock_wrong_owner(self, service):
        """Test releasing lock with wrong owner."""
        service.acquire_lock("job-key-123", "owner-1")
        
        released = service.release_lock("job-key-123", "owner-2")
        
        assert released is False
    
    def test_check_lock_exists(self, service):
        """Test checking existing lock."""
        service.acquire_lock("job-key-123", "owner-1")
        
        lock = service.check_lock("job-key-123")
        
        assert lock is not None
    
    def test_check_lock_expired(self, service):
        """Test checking expired lock."""
        lock = service.acquire_lock("job-key-123", "owner-1", ttl_seconds=0)
        lock.expires_at = _utcnow() - timedelta(seconds=1)
        
        result = service.check_lock("job-key-123")
        
        assert result is None
    
    def test_extend_lock(self, service):
        """Test extending a lock."""
        service.acquire_lock("job-key-123", "owner-1", ttl_seconds=60)
        
        extended = service.extend_lock("job-key-123", "owner-1", 300)
        
        assert extended is True
        
        lock = service.check_lock("job-key-123")
        assert lock.expires_at > _utcnow() + timedelta(seconds=200)
    
    def test_extend_lock_wrong_owner(self, service):
        """Test extending lock with wrong owner."""
        service.acquire_lock("job-key-123", "owner-1")
        
        extended = service.extend_lock("job-key-123", "owner-2", 300)
        
        assert extended is False
    
    # Result Caching Tests
    
    def test_cache_result(self, service):
        """Test caching a result."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        
        result_hash = service.cache_result(
            key.key,
            {"pdf_url": "https://example.com/doc.pdf"}
        )
        
        assert result_hash is not None
        assert len(result_hash) == 16
    
    def test_get_cached_result(self, service):
        """Test getting cached result."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        service.cache_result(key.key, {"data": "cached"})
        
        result = service.get_cached_result(key.key)
        
        assert result == {"data": "cached"}
    
    def test_get_cached_result_not_found(self, service):
        """Test getting non-existent cached result."""
        result = service.get_cached_result("non-existent")
        
        assert result is None
    
    def test_get_cached_result_expired(self, service):
        """Test getting expired cached result."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        service.cache_result(key.key, {"data": "cached"}, ttl_hours=0)
        
        # Manually expire
        cache_key = f"result:{key.key}"
        service._results[cache_key]["expires_at"] = _utcnow() - timedelta(hours=1)
        
        result = service.get_cached_result(key.key)
        
        assert result is None
    
    def test_invalidate_cache(self, service):
        """Test invalidating cached result."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        service.cache_result(key.key, {"data": "cached"})
        
        invalidated = service.invalidate_cache(key.key)
        
        assert invalidated is True
        assert service.get_cached_result(key.key) is None
    
    def test_invalidate_cache_not_found(self, service):
        """Test invalidating non-existent cache."""
        invalidated = service.invalidate_cache("non-existent")
        
        assert invalidated is False
    
    # Idempotent Execution Tests
    
    @pytest.mark.asyncio
    async def test_execute_idempotent_success(self, service):
        """Test successful idempotent execution."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        
        async def job_func():
            return {"pdf_url": "https://example.com/doc.pdf"}
        
        result = await service.execute_idempotent(key, job_func)
        
        assert result.success is True
        assert result.value == {"pdf_url": "https://example.com/doc.pdf"}
        assert result.cached is False
    
    @pytest.mark.asyncio
    async def test_execute_idempotent_cached(self, service):
        """Test idempotent execution returns cached result."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        
        call_count = 0
        
        async def job_func():
            nonlocal call_count
            call_count += 1
            return {"pdf_url": "https://example.com/doc.pdf"}
        
        # First execution
        result1 = await service.execute_idempotent(key, job_func)
        
        # Second execution should use cache
        result2 = await service.execute_idempotent(key, job_func)
        
        assert call_count == 1  # Job only executed once
        assert result2.success is True
        assert result2.cached is True
    
    @pytest.mark.asyncio
    async def test_execute_idempotent_failure(self, service):
        """Test idempotent execution with failure."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        
        async def job_func():
            raise ValueError("Generation failed")
        
        retry_config = RetryConfig(strategy=RetryStrategy.NONE)
        result = await service.execute_idempotent(key, job_func, retry_config)
        
        assert result.success is False
        assert "ValueError" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_idempotent_retry_success(self, service):
        """Test idempotent execution with retry succeeds."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        
        attempt_count = 0
        
        async def job_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary failure")
            return {"success": True}
        
        retry_config = RetryConfig(
            strategy=RetryStrategy.IMMEDIATE,
            max_retries=3
        )
        result = await service.execute_idempotent(key, job_func, retry_config)
        
        assert result.success is True
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_idempotent_retry_exhausted(self, service):
        """Test idempotent execution exhausts retries."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        
        async def job_func():
            raise ValueError("Always fails")
        
        retry_config = RetryConfig(
            strategy=RetryStrategy.IMMEDIATE,
            max_retries=2
        )
        result = await service.execute_idempotent(key, job_func, retry_config)
        
        assert result.success is False
        assert "Max retries" in result.error or "ValueError" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_idempotent_no_cache(self, service):
        """Test idempotent execution without caching."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        
        call_count = 0
        
        async def job_func():
            nonlocal call_count
            call_count += 1
            return {"data": call_count}
        
        # First execution without cache
        result1 = await service.execute_idempotent(key, job_func, cache_result=False)
        
        assert result1.success is True
        assert call_count == 1
    
    # Retry Management Tests
    
    def test_schedule_retry(self, service):
        """Test scheduling a retry."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        job = service.register_job(key)
        job.mark_started()
        job.mark_failed("Temporary error")
        
        scheduled = service.schedule_retry(key.key)
        
        assert scheduled is not None
        assert scheduled.status == JobStatus.PENDING
    
    def test_schedule_retry_cannot_retry(self, service):
        """Test scheduling retry when not allowed."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        job = service.register_job(key, max_attempts=1)
        job.mark_started()
        job.mark_failed("Error")
        
        scheduled = service.schedule_retry(key.key)
        
        assert scheduled is None
    
    def test_get_retry_config_pdf(self, service):
        """Test getting retry config for PDF jobs."""
        config = service.get_retry_config(JobType.PDF_GENERATION)
        
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.max_retries == 3
    
    def test_get_retry_config_email(self, service):
        """Test getting retry config for email jobs."""
        config = service.get_retry_config(JobType.EMAIL_SEND)
        
        assert config.max_retries == 5
    
    def test_get_retry_config_default(self, service):
        """Test getting retry config for unknown type."""
        config = service.get_retry_config(JobType.CLEANUP)
        
        assert config is not None
    
    # Statistics Tests
    
    def test_get_stats_empty(self, service):
        """Test getting stats when empty."""
        stats = service.get_stats()
        
        assert stats.total_jobs == 0
    
    def test_get_stats_with_jobs(self, service):
        """Test getting stats with jobs."""
        key1 = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        key2 = service.generate_idempotency_key(JobType.PDF_GENERATION, "2")
        
        service.register_job(key1)
        service.register_job(key2)
        
        stats = service.get_stats()
        
        assert stats.total_jobs == 2
        assert stats.pending_jobs == 2
    
    def test_get_stats_by_type(self, service):
        """Test getting stats by job type."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        
        stats = service.get_stats(JobType.PDF_GENERATION)
        
        assert stats.total_jobs == 1
        
        email_stats = service.get_stats(JobType.EMAIL_SEND)
        assert email_stats.total_jobs == 0
    
    # Cleanup Tests
    
    def test_cleanup_expired_jobs(self, service):
        """Test cleaning up expired jobs."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        job = service.register_job(key)
        job.mark_completed()
        job.result_expires_at = _utcnow() - timedelta(hours=1)
        
        cleaned = service.cleanup_expired()
        
        assert cleaned >= 1
        assert service.get_job(key.key) is None
    
    def test_cleanup_expired_locks(self, service):
        """Test cleaning up expired locks."""
        lock = service.acquire_lock("job-key", "owner", ttl_seconds=0)
        lock.expires_at = _utcnow() - timedelta(seconds=1)
        
        cleaned = service.cleanup_expired()
        
        assert cleaned >= 1
        assert service.check_lock("job-key") is None
    
    def test_clear_all(self, service):
        """Test clearing all data."""
        key = service.generate_idempotency_key(JobType.PDF_GENERATION, "1")
        service.register_job(key)
        service.acquire_lock("lock-1", "owner")
        service.cache_result(key.key, {"data": "test"})
        
        service.clear_all()
        
        assert len(service._jobs) == 0
        assert len(service._locks) == 0
        assert len(service._results) == 0


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Tests for convenience key generation functions."""
    
    def test_create_pdf_idempotency_key(self):
        """Test PDF idempotency key creation."""
        entity_id = uuid4()
        key = create_pdf_idempotency_key("quote", entity_id, version=1)
        
        assert key.job_type == JobType.PDF_GENERATION
        assert "pdf_generation" in key.key
    
    def test_create_pdf_idempotency_key_no_version(self):
        """Test PDF idempotency key without version."""
        entity_id = uuid4()
        key = create_pdf_idempotency_key("qualification", entity_id)
        
        assert key.job_type == JobType.PDF_GENERATION
    
    def test_create_email_idempotency_key(self):
        """Test email idempotency key creation."""
        key = create_email_idempotency_key(
            "test@example.com",
            "Quote Ready",
            "quote_template"
        )
        
        assert key.job_type == JobType.EMAIL_DRAFT
    
    def test_create_email_idempotency_key_no_template(self):
        """Test email idempotency key without template."""
        key = create_email_idempotency_key(
            "test@example.com",
            "Quote Ready"
        )
        
        assert key.job_type == JobType.EMAIL_DRAFT
    
    def test_create_notification_idempotency_key(self):
        """Test notification idempotency key creation."""
        recipient_id = uuid4()
        entity_id = uuid4()
        key = create_notification_idempotency_key(
            recipient_id,
            "quote_approved",
            entity_id
        )
        
        assert key.job_type == JobType.NOTIFICATION
    
    def test_create_stale_detection_idempotency_key(self):
        """Test stale detection idempotency key creation."""
        key = create_stale_detection_idempotency_key("opportunity")
        
        assert key.job_type == JobType.STALE_DETECTION
    
    def test_create_stale_detection_idempotency_key_with_date(self):
        """Test stale detection key with specific date."""
        key = create_stale_detection_idempotency_key(
            "rfq",
            run_date="2024-01-15"
        )
        
        assert key.job_type == JobType.STALE_DETECTION


# ============================================================================
# Integration Tests
# ============================================================================

class TestJobIdempotencyIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return JobIdempotencyService()
    
    @pytest.mark.asyncio
    async def test_complete_pdf_generation_workflow(self, service):
        """Test complete PDF generation workflow."""
        entity_id = uuid4()
        key = create_pdf_idempotency_key("quote", entity_id, version=1)
        
        async def generate_pdf():
            await asyncio.sleep(0.01)  # Simulate work
            return {
                "pdf_url": f"https://storage.example.com/quotes/{entity_id}.pdf",
                "generated_at": _utcnow().isoformat()
            }
        
        # First generation
        result1 = await service.execute_idempotent(key, generate_pdf)
        assert result1.success is True
        assert result1.cached is False
        
        # Second request returns cached
        result2 = await service.execute_idempotent(key, generate_pdf)
        assert result2.success is True
        assert result2.cached is True
        
        # Verify job record
        job = service.get_job(key.key)
        assert job.status == JobStatus.COMPLETED
        assert job.attempt_count == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_job_execution(self, service):
        """Test that concurrent requests don't duplicate work."""
        key = service.generate_idempotency_key(JobType.DATA_EXPORT, "report-1")
        execution_count = 0
        
        async def slow_job():
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.1)
            return {"data": f"result-{execution_count}"}
        
        # Start multiple concurrent executions
        tasks = [
            service.execute_idempotent(key, slow_job)
            for _ in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Job should only execute once
        successful = [r for r in results if r.success]
        assert len(successful) >= 1
        assert execution_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, service):
        """Test retry with exponential backoff."""
        key = service.generate_idempotency_key(JobType.WEBHOOK, "webhook-1")
        
        attempts = []
        
        async def flaky_webhook():
            attempts.append(_utcnow())
            if len(attempts) < 3:
                raise ConnectionError("Service unavailable")
            return {"status": "delivered"}
        
        retry_config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=3,
            initial_delay_seconds=0.01,  # Fast for testing
            backoff_multiplier=2.0
        )
        
        result = await service.execute_idempotent(
            key,
            flaky_webhook,
            retry_config=retry_config
        )
        
        assert result.success is True
        assert len(attempts) == 3
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, service):
        """Test that statistics are properly tracked."""
        # Execute multiple jobs
        for i in range(5):
            key = service.generate_idempotency_key(
                JobType.PDF_GENERATION,
                f"doc-{i}"
            )
            
            async def job_func():
                return {"id": i}
            
            await service.execute_idempotent(key, job_func)
        
        stats = service.get_stats(JobType.PDF_GENERATION)
        
        assert stats.total_jobs == 5
        assert stats.completed_jobs == 5
        assert stats.average_duration_ms is not None
    
    def test_lock_prevents_duplicate_registration(self, service):
        """Test that locks prevent duplicate work."""
        job_key = "unique-job-123"
        
        # First worker acquires lock
        lock1 = service.acquire_lock(job_key, "worker-1")
        assert lock1 is not None
        
        # Second worker cannot acquire
        lock2 = service.acquire_lock(job_key, "worker-2")
        assert lock2 is None
        
        # First worker releases
        service.release_lock(job_key, "worker-1")
        
        # Now second worker can acquire
        lock3 = service.acquire_lock(job_key, "worker-2")
        assert lock3 is not None
    
    def test_job_lifecycle(self, service):
        """Test complete job lifecycle."""
        key = service.generate_idempotency_key(JobType.DATA_IMPORT, "batch-1")
        
        # Register
        job = service.register_job(key)
        assert job.status == JobStatus.PENDING
        
        # Start
        service.update_job_status(key.key, JobStatus.RUNNING)
        job = service.get_job(key.key)
        assert job.status == JobStatus.RUNNING
        
        # Complete
        service.update_job_status(
            key.key,
            JobStatus.COMPLETED,
            result_hash="abc123"
        )
        job = service.get_job(key.key)
        assert job.status == JobStatus.COMPLETED
        assert job.is_terminal() is True
